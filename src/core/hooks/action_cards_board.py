"""Efekty kart akcji (okno ACTION): plansza, neutralni, żetony, karty strategii (RULES.md 53).

Zmiany stanu wyłącznie przez funkcje centralne (RULES.md 43.1a): ``unit_ops`` (+
``card_helpers.place_from_reinforcements``), ``command_tokens``, ``economy``/``payment``,
``control``, ``strategic_action``. Mapę (systemy bez wpisu w stanie, systemy domowe, wormhole,
sąsiedztwo) czyta ``board_graph``. Teksty kart w docstringach to cytaty z
assetów kart akcji (``registry.catalog``).

Funkcje ``*_targets`` / ``*_systems`` liczą LEGALNE cele - korzystają z nich i efekty (walidacja),
i formularze (``action_card_inputs_board``), więc wybór w UI i walidacja w silniku się zgadzają.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    board_graph,
    capacity,
    command_tokens,
    control,
    economy,
    payment,
    strategic_action,
    strategy_phase,
    unit_ops,
)
from src.core.game_state import GameState, SystemState
from src.core.hooks.card_helpers import (
    controlled,
    other_player_param,
    place_from_reinforcements,
    require_reinforcements,
)
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.planet_stats import attachment_defs
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect
from src.core.strategy_cards import CARDS
from src.core.unit_ops import UnitCause

_MERCENARY_COST = 2  # „Spend 2 trade goods”
_MERCENARY_INFANTRY = 2  # „place 2 neutral infantry”
_PIRATE_FLEET_COST = 3  # „Spend 3 resources”
# „1 neutral carrier, 1 neutral cruiser, 1 neutral destroyer, and 2 neutral fighters”
_PIRATE_FLEET: tuple[tuple[str, int], ...] = (
    ("carrier", 1),
    ("cruiser", 1),
    ("destroyer", 1),
    ("fighter", 2),
)
_DMZ_ATTACHMENT = "dmz"  # Demilitarized Zone: na planetę nie można stawiać jednostek
_GROUND_FORCES = ("infantry", "mech")  # siły naziemne (Exchange Program)
_PIRATE_CONTRACTS = ("piratecontract1", "piratecontract2", "piratecontract3", "piratecontract4")
_STRATEGIZE_CARDS = ("strategize1", "strategize2", "strategize3", "strategize4")


# --------------------------------------------------------------------------- pomocnicze


def _ships(system: SystemState | None, player_id: str) -> int:
    """Liczba statków (jednostek w przestrzeni) gracza w systemie."""
    if system is None:
        return 0
    return sum(n for n in system.space_units.get(player_id, {}).values() if n > 0)


def _has_other_players_ships(state: GameState, position: str, player_id: str) -> bool:
    """Czy w systemie są statki INNYCH graczy (neutralni też są „innym graczem”)."""
    system = state.systems.get(position)
    if system is None:
        return False
    return any(pid != player_id and _ships(system, pid) > 0 for pid in system.space_units)


def _has_non_neutral_ships(state: GameState, position: str) -> bool:
    """Czy w systemie są statki któregokolwiek gracza (poza neutralnymi)."""
    system = state.systems.get(position)
    if system is None:
        return False
    return any(pid != NEUTRAL_PLAYER_ID and _ships(system, pid) > 0 for pid in system.space_units)


def _position_param(params: Mapping[str, Any], allowed: list[str], what: str) -> str:
    position = params.get("position")
    if not isinstance(position, str) or position not in allowed:
        raise ValueError(f"Choose {what} ('position').")
    return position


def _place_neutral(
    state: GameState, system: SystemState, zone: str, base_type: str, count: int
) -> None:
    """Stawia jednostki neutralne (bez rezerwy i bez haków „postawiono”; to nie gracz)."""
    unit_ops.place_units(state, system, zone, NEUTRAL_PLAYER_ID, base_type, count, UnitCause.SETUP)


# ---------------------------------------------------------------------- Fighter Conscription


def conscription_systems(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[str]:
    """Systemy, w których wolno postawić myśliwca (Fighter Conscription).

    Własny space dock albo jednostka z pojemnością i brak statków innych graczy (z neutralnymi).
    """
    result: list[str] = []
    for position in state.systems:
        if _has_other_players_ships(state, position, player_id):
            continue
        report = capacity.capacity_report(state, registry, position, player_id)
        if report.general > 0 or report.fighter_only > 0:
            result.append(position)
    return result


def conscription_required(state: GameState, player_id: str, eligible: int) -> int:
    """Ile myśliwców faktycznie da się postawić: wszystkie systemy albo tyle, ile w rezerwie."""
    left = reinforcements_left(state, player_id, "fighter")
    return eligible if left is None else min(eligible, left)


@register_effect("action_cards:f_conscription")
def fighter_conscription(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Fighter Conscription: Place 1 fighter from your reinforcements in each system that
    contains 1 or more of your space docks or units that have capacity. They cannot be placed in
    systems that contain other players' ships.

    Gdy w rezerwie jest mniej myśliwców niż systemów, gracz wskazuje (``positions``), gdzie je
    postawić. Postawiony myśliwiec może przekroczyć pojemność (ruling) - wtedy otwiera się okno
    ``CAPACITY`` (⚠ ZAŁOŻENIE: jedno okno naraz, dla pierwszego systemu z nadwyżką).
    """
    eligible = conscription_systems(state, registry, player_id)
    if not eligible:
        raise ValueError("You have no system where a fighter can be placed.")
    required = conscription_required(state, player_id, len(eligible))
    if required < 1:
        raise ValueError("You have no fighters in your reinforcements.")
    chosen = params.get("positions")
    if chosen is None and required == len(eligible):
        chosen = eligible
    if (
        not isinstance(chosen, list)
        or len(set(chosen)) != len(chosen)
        or len(chosen) != required
        or any(position not in eligible for position in chosen)
    ):
        raise ValueError(f"Choose exactly {required} eligible systems ('positions').")
    for position in chosen:
        place_from_reinforcements(state, state.systems[position], "space", player_id, "fighter", 1)
    for position in chosen:
        checked = capacity.open_capacity_check(state, registry, position)
        if checked.pending_window is not None:
            state.pending_window = checked.pending_window
            break


# ------------------------------------------------------------------------------ Ghost Ship


def ghost_ship_targets(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    """Systemy dla Ghost Ship: nie-domowe, z wormholem, bez statków innych graczy.

    Wymaga destroyera w rezerwie (⚠ ZAŁOŻENIE: bez wariantu „zdejmij z planszy” z rulingu).
    """
    if reinforcements_left(state, player_id, "destroyer") == 0:
        return []
    return [
        position
        for position in board_graph.non_home_systems(state, registry)
        if board_graph.wormholes_at(state, registry, position)
        and not _has_other_players_ships(state, position, player_id)
    ]


@register_effect("action_cards:ghost_ship")
def ghost_ship(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Ghost Ship: Place 1 destroyer from your reinforcements in a non-home system that contains a
    wormhole and does not contain other players' ships.
    """
    targets = ghost_ship_targets(state, registry, player_id)
    position = _position_param(
        params, targets, "a non-home system with a wormhole and no other players' ships"
    )
    system = board_graph.ensure_system(state, position)
    place_from_reinforcements(state, system, "space", player_id, "destroyer", 1)


# ------------------------------------------------------------------------- Signal Jamming


def jamming_targets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str]]:
    """Pary ``(system, gracz)`` dla Signal Jamming.

    System nie-domowy z własnym statkiem albo sąsiadujący z takim; gracz inny niż zagrywający,
    z żetonem w rezerwie i bez żetonu w tym systemie (⚠ ZAŁOŻENIE: gracz z żetonem na miejscu
    nie jest celem, bo żeton nie może się zdublować).
    """
    result: list[tuple[str, str]] = []
    for position in board_graph.non_home_systems(state, registry):
        near = {position, *board_graph.adjacent_positions(position)}
        if not any(_ships(state.systems.get(pos), player_id) > 0 for pos in near):
            continue
        system = state.systems.get(position)
        placed = system.command_tokens if system is not None else []
        result.extend(
            (position, other)
            for other in state.players
            if other != player_id
            and command_tokens.reinforcements(state, other) > 0
            and other not in placed
        )
    return result


@register_effect("action_cards:jamming")
def signal_jamming(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Signal Jamming: Choose 1 non-home system that contains or is adjacent to 1 of your ships.
    Place a command token from another player's reinforcements in that system.
    """
    target = other_player_param(state, player_id, params)
    targets = jamming_targets(state, registry, player_id)
    position = params.get("position")
    if (position, target) not in targets:
        raise ValueError(
            "Choose a non-home system with or next to your ship where that player can get a "
            "token ('position', 'player')."
        )
    system = board_graph.ensure_system(state, str(position))
    command_tokens.place_on_board_from_reinforcements(state, system, target)


# ---------------------------------------------------------------------- Mercenary Contract


def _planet_is_empty(system: SystemState | None, planet: str) -> bool:
    """Planeta bez żadnych jednostek (struktury, siły naziemne; także neutralnych)."""
    if system is None:
        return True
    by_player = system.planet_units.get(planet, {})
    return not any(count > 0 for units in by_player.values() for count in units.values())


def _is_demilitarized(state: GameState, registry: StaticDataRegistry, planet: str) -> bool:
    return any(a.id == _DMZ_ATTACHMENT for a in attachment_defs(state, registry, planet))


def mercenary_targets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str]]:
    """Pary ``(system, planeta)`` dla Mercenary Contract.

    Planeta nie-domowa, bez jednostek, nie Twoja i nie DMZ (notka karty); wymaga 2 TG.
    """
    if economy.spendable_trade_goods(state, player_id) < _MERCENARY_COST:
        return []
    result: list[tuple[str, str]] = []
    for position in board_graph.non_home_systems(state, registry):
        definition = registry.systems.get(board_graph.system_id_at(state, position))
        system = state.systems.get(position)
        for planet in definition.planets if definition else []:
            owner = system.planet_owners.get(planet) if system is not None else None
            if (
                owner != player_id
                and _planet_is_empty(system, planet)
                and not _is_demilitarized(state, registry, planet)
            ):
                result.append((position, planet))
    return result


@register_effect("action_cards:mercenarycontract")
def mercenary_contract(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Mercenary Contract: Spend 2 trade goods to place 2 neutral infantry on any non-home planet
    that contains no units; if that planet was owned by another player, they return its planet
    card to the planet card deck.
    """
    planet = params.get("planet")
    position = params.get("position")
    if (position, planet) not in mercenary_targets(state, registry, player_id):
        raise ValueError(
            "Choose a non-home planet with no units that is not yours (and has no DMZ) "
            "('position', 'planet'); you need 2 trade goods."
        )
    economy.spend_as_trade_goods(state, player_id, _MERCENARY_COST)
    system = board_graph.ensure_system(state, str(position))
    if system.planet_owners.get(str(planet)) is not None:
        # Poprzedni kontroler oddaje kartę planety do talii (traci kontrolę, planeta się odświeża).
        control.set_planet_control(state, str(position), str(planet), None, registry)
    _place_neutral(state, system, str(planet), "infantry", _MERCENARY_INFANTRY)


# ------------------------------------------------------------------ Pirate Contract / Fleet


def pirate_targets(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Systemy dla piratów: nie-domowe i bez statków żadnego gracza (poza neutralnymi)."""
    return [
        position
        for position in board_graph.non_home_systems(state, registry)
        if not _has_non_neutral_ships(state, position)
    ]


def pirate_contract(
    state: GameState, registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Pirate Contract: Place 1 neutral destroyer in a non-home system that contains no
    non-neutral ships.
    """
    position = _position_param(
        params, pirate_targets(state, registry), "a non-home system with no non-neutral ships"
    )
    _place_neutral(state, board_graph.ensure_system(state, position), "space", "destroyer", 1)


for _contract_id in _PIRATE_CONTRACTS:  # 4 kopie karty, ten sam efekt
    register_effect(f"action_cards:{_contract_id}")(pirate_contract)


@register_effect("action_cards:piratefleet")
def pirate_fleet(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Pirate Fleet: Spend 3 resources to place 1 neutral carrier, 1 neutral cruiser, 1 neutral
    destroyer, and 2 neutral fighters in a non-home system that contains no non-neutral ships.
    """
    position = _position_param(
        params, pirate_targets(state, registry), "a non-home system with no non-neutral ships"
    )
    planets, trade_goods = payment.parse_payment(dict(params))
    paid = payment.validate_payment(state, registry, player_id, "resources", planets, trade_goods)
    if paid < _PIRATE_FLEET_COST:
        raise ValueError(f"Spend at least {_PIRATE_FLEET_COST} resources (you chose {paid}).")
    payment.apply_payment(state, player_id, planets, trade_goods)
    system = board_graph.ensure_system(state, position)
    for base_type, count in _PIRATE_FLEET:
        _place_neutral(state, system, "space", base_type, count)


# ------------------------------------------------------------------------ Exchange Program


def _ground_forces(system: SystemState | None, planet: str, player_id: str) -> int:
    if system is None:
        return 0
    units = system.planet_units.get(planet, {}).get(player_id, {})
    return sum(units.get(base_type, 0) for base_type in _GROUND_FORCES)


def exchange_planets(state: GameState, owner_id: str) -> list[tuple[str, str]]:
    """Planety kontrolowane przez ``owner_id`` z jego siłami naziemnymi: ``(system, planeta)``."""
    result: list[tuple[str, str]] = []
    for planet in controlled(state, owner_id):
        for position, system in state.systems.items():
            if planet in system.planet_owners and _ground_forces(system, planet, owner_id) > 0:
                result.append((position, planet))
    return result


@register_effect("action_cards:exchangeprogram")
def exchange_program(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Exchange Program: Choose another player. You and that player may agree to place 1 infantry
    from each of your reinforcements into coexistence on a planet the other player controls that
    contains their ground forces; if no agreement is reached, you each discard 1 token from your
    fleet pool.

    ⚠ ZAŁOŻENIE: zgoda partnera to parametr ``agreed`` zgłaszany przez zagrywającego (jak zgoda
    w transakcjach). Przy zgodzie zagrywający wskazuje obie planety: ``their_planet`` (kontrolowana
    przez partnera, z jego siłami naziemnymi) i ``my_planet`` (jego własna, z jego siłami
    naziemnymi); każdy stawia 1 piechotę z rezerwy na planecie drugiego (koegzystencja - kontrola
    planety się nie zmienia). Bez zgody każdy odrzuca 1 żeton z fleet pool do rezerwy (kto nie ma
    żetonu w fleet pool, nic nie odrzuca).
    """
    partner = other_player_param(state, player_id, params)
    agreed = params.get("agreed")
    if not isinstance(agreed, bool):
        raise ValueError("State whether the players reached an agreement ('agreed').")
    if not agreed:
        for pid in (player_id, partner):
            if command_tokens.pool_count(state, pid, "fleet") > 0:
                command_tokens.spend_to_reinforcements(state, pid, "fleet", 1)
        return
    theirs = exchange_planets(state, partner)
    mine = exchange_planets(state, player_id)
    their_planet = params.get("their_planet")
    my_planet = params.get("my_planet")
    their_target = next((pair for pair in theirs if pair[1] == their_planet), None)
    my_target = next((pair for pair in mine if pair[1] == my_planet), None)
    if their_target is None or my_target is None:
        raise ValueError(
            "Choose a planet the other player controls and a planet you control, each with its "
            "owner's ground forces ('their_planet', 'my_planet')."
        )
    require_reinforcements(state, player_id, "infantry", 1)
    require_reinforcements(state, partner, "infantry", 1)
    place_from_reinforcements(
        state, state.systems[their_target[0]], their_target[1], player_id, "infantry", 1
    )
    place_from_reinforcements(
        state, state.systems[my_target[0]], my_target[1], partner, "infantry", 1
    )


# ------------------------------------------------------ Overrule / Strategize (karty strategii)


def strategy_cards_in_reach(state: GameState, registry: StaticDataRegistry) -> list[int]:
    """Inicjatywy kart strategii „readied or unchosen”: niewyczerpane (wybrane) albo niewybrane."""
    exhausted = {i for p in state.players.values() for i in p.exhausted_strategy_cards}
    return [
        initiative
        for initiative in strategy_phase.available_initiatives(registry)
        if initiative in CARDS and initiative not in exhausted
    ]


def _initiative_param(
    state: GameState, registry: StaticDataRegistry, params: Mapping[str, Any]
) -> int:
    initiative = params.get("initiative")
    if (
        isinstance(initiative, bool)
        or not isinstance(initiative, int)
        or initiative not in strategy_cards_in_reach(state, registry)
    ):
        raise ValueError("Choose a readied or unchosen strategy card ('initiative').")
    return initiative


@register_effect("action_cards:overrule")
def overrule(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Overrule: Perform the primary ability of a readied or unchosen strategy card.

    Efekt otwiera wieloetapowe primary tej karty (``pending_strategy`` z ``no_secondary``) albo
    stosuje je od razu; gracz kończy je zwykłym ``submit_primary_step``. Karta strategii NIE jest
    wyczerpywana, a pozostali gracze nie dostają okna secondary (⚠ ZAŁOŻENIE: notka karty mówi, że
    przy Trade nie wskazuje się graczy do secondary, więc secondary nie następuje wcale).
    """
    initiative = _initiative_param(state, registry, params)
    strategic_action.begin_overrule_primary(
        state, registry, player_id, initiative, grid=board_graph.bound_grid()
    )


def strategize(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Strategize: Perform the secondary ability of any readied or unchosen strategy card.

    Efekt otwiera okno ``STRATEGY_SECONDARY`` z jednym respondentem (zagrywającym); dalej to
    zwykłe secondary - z kosztem żetonu ze strategy pool poza Leadership (notka karty).
    """
    initiative = _initiative_param(state, registry, params)
    strategic_action.begin_strategize_secondary(state, player_id, initiative)


for _strategize_id in _STRATEGIZE_CARDS:  # 4 kopie karty, ten sam efekt
    register_effect(f"action_cards:{_strategize_id}")(strategize)
