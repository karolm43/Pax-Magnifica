"""The Xxcha Kingdom — komplet komponentów frakcji (RULES.md 62.9).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("xxcha")``, ``units``,
``leaders/te_leaders.json``). Rulingi: ``docs/rules_tirules/F_xxcha.md``. Punkty silnika dodane dla
Xxcha: płatność „flex” (``payment.flex_spend``), głosy za planetę i głos nie do zablokowania
(``agenda.votes_per_planet``, ``agenda.vote_unblockable``), anulujący kartę akcji bez karty w ręce
(``action_cards.canceller`` + ``card_hold.cancel_by_component``, także Sabotage czekające na
Instinct Training) i technologia z oknem użycia (``faction_components`` rodzaj ``technology``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    agenda_phase,
    card_hold,
    command_tokens,
    control,
    exhaust,
    exploration,
    faction_components,
    invasion,
    leaders,
    promissory_play,
    reaction_cards,
    rules_hooks,
    tactical,
    triggers,
    turn_flow,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.action_adjacency import neighbors
from src.core.fleet_pool import unit_name
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.hooks.card_helpers import controlled, place_from_reinforcements, system_of_planet
from src.core.map_string import MECATOL_SYSTEM_ID
from src.core.planet_stats import influence_of
from src.core.production import reinforcements_left
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_ACTION_CARD_CANCELLER,
    POINT_AGENDA_VOTE_UNBLOCKABLE,
    POINT_AGENDA_VOTES_PER_PLANET,
    POINT_PAYMENT_FLEX_SPEND,
    SOURCE_BREAKTHROUGH,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_TECHNOLOGY,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.state_grid import grid_from_state
from src.core.strategy_cards import diplomacy
from src.core.strategy_cards.common import place_structure, structure_problem
from src.core.unit_ops import UnitCause

FACTION = "xxcha"
AGENT = "xxchaagent"
COMMANDER = "xxchacommander"
HERO = "xxchahero-te"  # Thunder's Edge zastępuje Codex (decyzja użytkownika 2026-11-16)
FLAGSHIP = "xxcha_flagship"
MECH = "xxcha_mech"
FAVOR = "favor"
INSTINCT = "it"
NULLIFICATION = "nf"
BREAKTHROUGH = "xxchabt"
PEACE_ACCORDS = "peace_accords"
QUASH = "quash"

_COMMANDER_INFLUENCE = 12  # „combined total of at least 12 influence”
_HERO_UNITS = 4  # „up to 4 PDS or mechs”
_HERO_TYPES = ("pds", "mech")
_QUASH_WINDOW = (GameEvent.AGENDA_REVEALED, Moment.WHEN)  # „When an agenda is revealed”
_NONE = "none"
_INFANTRY = "infantry"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _name(registry: Any, state: GameState, player_id: str) -> str:
    player = state.players.get(player_id)
    faction = registry.factions.get(player.faction or "") if player is not None else None
    return faction.name if faction is not None else player_id


def _planet_name(registry: Any, planet: str) -> str:
    definition = registry.planets.get(planet)
    return definition.name if definition is not None else planet


def _xxcha_players(state: GameState) -> list[str]:
    return [pid for pid, p in state.players.items() if p.faction == FACTION]


def _has_strategy_token(state: GameState, player_id: str) -> bool:
    """Czy gracz może WYDAĆ żeton z puli strategicznej (także przez Scepter of Emelpar)."""
    return command_tokens.can_spend_strategy_token(state, player_id)


def _token_source_inputs(
    state: GameState, _registry: Any, player_id: str, *_ctx: Any
) -> list[dict[str, Any]]:
    """Wybór „pula czy Scepter of Emelpar" (C_relics: Scepter działa przy zdolnościach frakcji)."""
    return command_tokens.strategy_token_input(state, player_id)


def _source(params: Mapping[str, Any]) -> object:
    return params.get("token_source")


def _position_of(state: GameState, planet: str) -> str | None:
    for position, system in state.systems.items():
        if planet in system.planet_owners or planet in system.planet_units:
            return position
    return None


def _near_own_planets(state: GameState, player_id: str) -> set[str]:
    """Systemy „adjacent to a planet you control”: system planety i systemy z nim sąsiadujące
    (F_xxcha: „A planet is adjacent to both the system it is in, and every system adjacent")."""
    grid = grid_from_state(state, _registry())
    own = {
        position for position, system in state.systems.items()
        if player_id in system.planet_owners.values()
    }
    near = set(own)
    for position in own:
        near |= neighbors(state, grid, position)
    return near


def _planet_has_units(state: GameState, position: str, planet: str) -> bool:
    system = state.systems[position]
    zone = system.planet_units.get(planet, {})
    return any(n > 0 for units in zone.values() for n in units.values())


# ------------------------------------------------------------------------- Peace Accords


def peace_targets(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """``[(pozycja, planeta)]`` legalne dla Peace Accords (nie Mecatol, bez jednostek, w systemie
    przy planecie Xxcha, jeszcze nie Xxcha)."""
    registry = _registry()
    found: list[tuple[str, str]] = []
    for position in sorted(_near_own_planets(state, player_id)):
        system = state.systems.get(position)
        definition = registry.systems.get(system.system_id) if system is not None else None
        if system is None or definition is None or system.system_id == MECATOL_SYSTEM_ID:
            continue
        for planet in definition.planets or []:
            if system.planet_owners.get(planet) == player_id:
                continue
            if _planet_has_units(state, position, planet):
                continue
            found.append((position, planet))
    return found


def _after_own_diplomacy(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("player") == player_id
        and ctx.get("initiative") == diplomacy.INITIATIVE
        and bool(peace_targets(state, player_id))
    )


def peace_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options = []
    for position, planet in peace_targets(state, player_id):
        owner = state.systems[position].planet_owners.get(planet)
        whose = f" (from {_name(registry, state, owner)})" if owner else ""
        options.append(oi.option(
            f"{position}|{planet}", f"{_planet_name(registry, planet)}{whose}",
            ref=("planet", planet),
        ))
    return [oi.choice("planet", "Planet you gain control of", options)]


@on_event(
    GameEvent.STRATEGIC_ACTION, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_after_own_diplomacy, inputs=peace_inputs,
    covers=f"abilities:{PEACE_ACCORDS}", label="Peace Accords",
)
def peace_accords(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Peace Accords: After you resolve the primary or secondary ability of the "Diplomacy"
    strategy card: You may gain control of 1 planet other than Mecatol Rex that does not contain
    any units and is in a system that is adjacent to a planet you control.

    F_xxcha: planeta niekontrolowana - Xxcha ją eksploruje; zdobyta wyczerpana.
    """
    position, _, planet = str(ctx.get("params", {}).get("planet") or "").partition("|")
    if (position, planet) not in peace_targets(state, player_id):
        raise ValueError("Choose a planet without units next to a planet you control.")
    registry = _registry()
    previous = state.systems[position].planet_owners.get(planet)
    control.set_planet_control(state, position, planet, player_id, registry)
    exhaust.exhaust_planets(state, player_id, [planet])
    if previous is None and exploration.explorable(registry, planet):
        exploration.start_exploration(state, registry, player_id, position, [planet])


# ------------------------------------------------------------------------------- Quash


def _agenda_revealed_open(state: GameState) -> bool:
    return any(
        (w.event, w.moment) == _QUASH_WINDOW for w in reaction_cards.open_windows(state)
    )


@faction_components.window_use("ability", QUASH)
def _quash_window(state: GameState, _registry: StaticDataRegistry, player_id: str) -> str | None:
    if not _agenda_revealed_open(state):
        return "Quash is used when an agenda is revealed."
    if not _has_strategy_token(state, player_id):
        return "Quash needs 1 command token in your strategy pool."
    if not state.decks.agenda_deck:
        return "The agenda deck is empty."
    return None


register_effect_inputs(f"abilities:{QUASH}")(_token_source_inputs)


@register_effect(f"abilities:{QUASH}")
def quash(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Quash: When an agenda is revealed: You may spend 1 token from your strategy pool to discard
    that agenda and reveal 1 agenda from the top of the deck. Players vote on this agenda instead.

    F_xxcha: Political Secret zagrane wcześniej wraca bez efektu na nowej agendzie (efekty
    ``AGENDA`` wygasają w ``veto_agenda``); nowa agenda = nowe transakcje; Quash wolno użyć znów.
    """
    command_tokens.spend_strategy_token(state, player_id, source=_source(params))
    agenda_phase.veto_agenda(state, registry)


# --------------------------------------------------------------- Political Favor (notka)


@promissory_play.condition(FAVOR)
def _favor_condition(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, _window: OpenWindow
) -> str | None:
    owners = _xxcha_players(state)
    # „Remove 1 token" to nie wydanie - Scepter of Emelpar nie dotyczy, liczy się sama pula.
    if not owners or command_tokens.pool_count(state, owners[0], "strategic") < 1:
        return "The Xxcha player has no command token in their strategy pool."  # F_xxcha
    if not state.decks.agenda_deck:
        return "The agenda deck is empty."
    return None


@register_effect(f"promissory_notes:{FAVOR}")
def political_favor(
    state: GameState, registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Political Favor: When an agenda is revealed: Remove 1 token from the Xxcha player's strategy
    pool and return it to their reinforcements. Then, discard the revealed agenda and reveal 1
    agenda from the top of the deck. Players vote on this agenda instead. Then, return this card
    to the Xxcha player (zwrot robi ``promissory_play``)."""
    owner = params.get("__owner")
    if not isinstance(owner, str) or owner not in state.players:
        raise ValueError("The Xxcha player is not in the game.")
    command_tokens.spend_strategy_token(state, owner)
    agenda_phase.veto_agenda(state, registry)


# ------------------------------------------------------------ Instinct Training (tech)


def _instinct_ready(state: GameState, player_id: str) -> bool:
    player = state.players[player_id]
    return (
        INSTINCT in player.technologies
        and INSTINCT not in player.exhausted_technologies
        and _has_strategy_token(state, player_id)
    )


@register(
    POINT_ACTION_CARD_CANCELLER, HookSource(SOURCE_TECHNOLOGY, INSTINCT), HookKind.PERMIT,
    covers=f"technologies:{INSTINCT}",
)
def instinct_canceller(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Jawne: gotowa technologia i żeton w strategy pool - okno anulowania się otwiera."""
    return ctx.get("player") != player_id and _instinct_ready(state, player_id)


@faction_components.window_use("technology", INSTINCT, holds=True)
def _instinct_window(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> str | None:
    held = state.held_play
    if held is None:
        return "Instinct Training is used when another player plays an action card."
    target_player, _card = card_hold.target_of(held)
    if target_player == player_id:
        return "You cannot cancel your own action card."
    if not card_hold.can_respond(held, player_id):
        return "You can no longer respond to this card."
    if not _has_strategy_token(state, player_id):
        return "Instinct Training needs 1 command token in your strategy pool."
    return None


register_effect_inputs(f"technologies:{INSTINCT}")(_token_source_inputs)


@register_effect(f"technologies:{INSTINCT}")
def instinct_training(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Instinct Training: You may exhaust this card and spend 1 token from your strategy pool when
    another player plays an action card; cancel that action card.

    F_xxcha: także Sabotage; bez kosztów anulowanej karty; anulowana karta ACTION oddaje akcję
    tury (wyczerpanie technologii płaci ``faction_components.pay_cost``).
    """
    command_tokens.spend_strategy_token(state, player_id, source=_source(params))
    card_hold.cancel_by_component(state)


# ---------------------------------------------------------- Nullification Field (tech)


def _nullification_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    active = ctx.get("player")
    system = state.systems.get(str(ctx.get("position")))
    player = state.players[player_id]
    return (
        active != player_id
        and active == state.active_player_id
        and system is not None
        and any(n > 0 for n in system.space_units.get(player_id, {}).values())
        and NULLIFICATION not in player.exhausted_technologies
        and _has_strategy_token(state, player_id)
    )


def _adopt(dst: GameState, src: GameState) -> None:
    dst.__dict__.update(src.__dict__)


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, NULLIFICATION),
    optional=True, condition=_nullification_ready, inputs=_token_source_inputs,
    covers=f"technologies:{NULLIFICATION}",
    label="Nullification Field: end that player's turn",
)
def nullification_field(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Nullification Field: After another player activates a system that contains 1 or more of your
    ships, you may exhaust this card and spend 1 token from your strategy pool; immediately end
    that player's turn.

    F_xxcha: potem nikt nie używa zdolności „after … activates a system” (czekające oferty tego
    okna znikają); zdolności „at the end of your turn” działają (zwykły koniec tury).
    """
    active = str(ctx.get("player") or "")
    if active != state.active_player_id or state.active_system is None:
        raise ValueError("That player's tactical action is already over.")
    exhaust.exhaust_technology(state, player_id, NULLIFICATION)
    command_tokens.spend_strategy_token(
        state, player_id, source=_source(ctx.get("params", {}))
    )
    triggers.drop_offers(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER)
    # F_ul coalescence 4: walka naziemna Titanów i tak się odbywa (tylko ona, bez innych kroków).
    forced = invasion.begin_forced_combat(state, grid_from_state(state, _registry()), _registry())
    if forced.invasion is not None:
        _adopt(state, forced)
        return
    _adopt(state, tactical.end_tactical_action(state))
    if state.pending_window is None and not state.pending_offers:
        _adopt(state, turn_flow.end_turn(state, active, registry=_registry(), forced=True))


# --------------------------------------------------------------- Ggrocuto Rinn (agent)


def _exhausted_planets(state: GameState) -> list[tuple[str, str, str]]:
    """``[(pozycja, planeta, kontrolujący)]`` wyczerpanych planet na planszy."""
    found: list[tuple[str, str, str]] = []
    for pid, player in state.players.items():
        for planet in player.exhausted_planets:
            position = _position_of(state, planet)
            if position is not None and state.systems[position].planet_owners.get(planet) == pid:
                found.append((position, planet, pid))
    return sorted(found)


@faction_components.blocker("leader", AGENT)
def _agent_blocker(state: GameState, _registry: StaticDataRegistry, _player_id: str) -> str | None:
    if not _exhausted_planets(state):
        return "There is no exhausted planet to ready."  # F_xxcha: cel musi być wyczerpany
    return None


@register_effect_inputs(f"leaders:{AGENT}")
def agent_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Planeta do odnowienia; przy planecie obok planety Xxcha także „usuń 1 piechotę” (wybór)."""
    near = _near_own_planets(state, player_id)
    options: list[dict[str, Any]] = []
    for position, planet, _owner in _exhausted_planets(state):
        name = _planet_name(registry, planet)
        options.append(oi.option(f"{position}|{planet}|{_NONE}", f"Ready {name}"))
        if position not in near:
            continue
        for pid, units in sorted(state.systems[position].planet_units.get(planet, {}).items()):
            if units.get(_INFANTRY, 0) > 0:
                who = _name(registry, state, pid)
                options.append(oi.option(
                    f"{position}|{planet}|{pid}",
                    f"Ready {name} and remove 1 infantry ({who})",
                ))
    return [oi.choice("planet", "Planet to ready", options)]


@register_effect(f"leaders:{AGENT}")
def ggrocuto_rinn(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Ggrocuto Rinn: ACTION: Exhaust this card to ready any planet; if that planet is in a system
    that is adjacent to a planet you control, you may remove 1 infantry from that planet and return
    it to its reinforcements."""
    position, _, rest = str(params.get("planet") or "").partition("|")
    planet, _, infantry_owner = rest.partition("|")
    owner = next(
        (pid for pos, p, pid in _exhausted_planets(state) if (pos, p) == (position, planet)), None
    )
    if owner is None:
        raise ValueError("Choose an exhausted planet.")
    exhaust.ready_planets(state, owner, [planet])
    if infantry_owner and infantry_owner != _NONE:
        if position not in _near_own_planets(state, player_id):
            raise ValueError("That planet is not adjacent to a planet you control.")
        system = state.systems[position]
        if unit_ops.count_in_zone(system, planet, infantry_owner, _INFANTRY) < 1:
            raise ValueError("There is no such infantry on that planet.")
        unit_ops.remove_units(
            state, system, planet, infantry_owner, _INFANTRY, 1, UnitCause.REMOVED
        )


# ----------------------------------------------------------------- Elder Qanoj (commander)


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Control planets that have a combined total of at least 12 influence."""
    total = sum(influence_of(state, registry, p) for p in controlled(state, player_id))
    return total >= _COMMANDER_INFLUENCE


@register(
    POINT_AGENDA_VOTES_PER_PLANET, HookSource(SOURCE_LEADER, COMMANDER), HookKind.MODIFY,
    covers=f"leaders:{COMMANDER}",
)
def qanoj_votes(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Elder Qanoj: Each planet you exhaust to cast votes provides 1 additional vote (także planeta
    z 0 wpływu - F_xxcha)."""
    return 1


@register(
    POINT_AGENDA_VOTE_UNBLOCKABLE, HookSource(SOURCE_LEADER, COMMANDER), HookKind.PERMIT,
    covers=f"leaders:{COMMANDER}",
)
def qanoj_unblockable(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Elder Qanoj: Game effects cannot prevent you from voting on an agenda (F_xxcha: Political
    Secret Xxcha blokuje karty akcji i Quash, ale nie głos; ridery i głos w tej samej agendzie)."""
    return True


# -------------------------------------------------- Xxekir Grom — Planetary Defense Nexus (hero)


def _pds_room(state: GameState, player_id: str, planet: str) -> int:
    """Ile PDS zmieści się jeszcze na planecie (limit struktur, Homeland Defense Act, rezerwa)."""
    probe = state.clone()
    room = 0
    while room < _HERO_UNITS and structure_problem(probe, player_id, planet, "pds") is None:
        place_structure(probe, player_id, planet, "pds")
        room += 1
    return room


def _hero_slots(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """``[(typ, planeta)]`` - jedna pozycja na KAŻDĄ jednostkę, którą wolno teraz postawić."""
    slots: list[tuple[str, str]] = []
    for planet in controlled(state, player_id):
        slots += [("pds", planet)] * _pds_room(state, player_id, planet)
        slots += [("mech", planet)] * _HERO_UNITS
    return slots


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Jednostki do postawienia (do 4, dowolne połączenie PDS i mechów, kilka na planetę).

    Jedna opcja na sztukę z ``unit_at`` (jednostka + planeta): UI pokazuje planety na mapie, a na
    wybranej planecie licznik PDS i licznik mechów (``GroupedMapField``), nie listę.
    """
    options: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], int] = {}
    for base_type, planet in _hero_slots(state, player_id):
        left = reinforcements_left(state, player_id, base_type)
        index = seen.get((base_type, planet), 0)
        if left is not None and index >= left:
            continue
        seen[(base_type, planet)] = index + 1
        label = (
            f"{unit_name(state, registry, player_id, base_type)} on "
            f"{_planet_name(registry, planet)}"
        )
        options.append(oi.option(
            f"{base_type}|{planet}|{index}", label,
            meta=oi.unit_at(state, player_id, base_type, planet=planet),
        ))
    most = min(_HERO_UNITS, len(options))
    return [oi.multi("units", "PDS and mechs to place (up to 4)", options, 1, max(1, most))]


@register_effect(f"leaders:{HERO}")
def planetary_defense_nexus(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Xxekir Grom — Planetary Defense Nexus: ACTION: Place any combination of up to 4 PDS or mechs
    onto planets you control; ready each planet that you place a unit on. Then, purge this card.

    F_xxcha: wolno stawiać na gotowej planecie i kilka jednostek na jednej planecie. Purge -
    ``leaders.pay_usage`` (tekst karty).
    """
    chosen = [str(v) for v in params.get("units") or []]
    if not 1 <= len(chosen) <= _HERO_UNITS:
        raise ValueError("Choose 1 to 4 PDS or mechs to place.")
    own = set(controlled(state, player_id))
    readied: list[str] = []
    for value in chosen:
        base_type, _, rest = value.partition("|")
        planet = rest.partition("|")[0]
        if base_type not in _HERO_TYPES or planet not in own:
            raise ValueError("Place PDS or mechs on planets you control.")
        if base_type == "pds":
            place_structure(state, player_id, planet, "pds")
        else:
            place_from_reinforcements(
                state, system_of_planet(state, planet), planet, player_id, "mech", 1
            )
        if planet not in readied:
            readied.append(planet)
    exhaust.ready_planets(state, player_id, readied)


# ------------------------------------------------------------- Loncara Ssodu, Indomitus


# SPACE CANNON na sąsiednie systemy: pole ``deep_space_cannon`` jednostki w danych, czytane przez
# ``core/space_cannon`` (jak PDS II). F_xxcha: kolejność Space Cannon Offense / Defense - reguła
# ogólna silnika (zniszczona jednostka nie strzela; Defense tylko nieaktywni gracze).
rules_hooks.declare_data_driven(f"units:{FLAGSHIP}", f"units:{MECH}")


# ------------------------------------------------------------------- Archon's Gift (BT)


@register(
    POINT_PAYMENT_FLEX_SPEND, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH), HookKind.PERMIT,
    covers=f"breakthroughs:{BREAKTHROUGH}",
)
def archons_gift(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Archon's Gift: You can spend influence as if it were resources. You can spend resources as if
    it were influence.

    F_xxcha: planeta daje jedno ALBO drugie (większą wartość, ``payment.ready_planet_values``),
    tylko przy wydawaniu - nie PRODUCTION doku, Integrated Economy, Elder Qanoj, Establish
    Hegemony / Hoard Raw Materials, Mining Initiative ani Uprising (``planet_stats`` bez zmian).
    """
    return True
