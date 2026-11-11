"""Efekty „ACTION:” reliktów (RULES.md 59).

Zakres: Codex, Dynamis Core, Book of Latvinia, Circlet of the Void, Nano-Forge,
Stellar Converter, The Silver Flame.

Relikt z akcją jest zagrywany jako akcja komponentu (``core/relic_cards.py``) i - w odróżnieniu od
karty akcji - zostaje przed graczem: wyczerpuje się albo jest purge'owany przez własny efekt.
Legalne cele liczy silnik (te same listy widzi formularz i walidacja); gracz decyduje sam.
Teksty w docstringach to dosłowne cytaty z ``assets/data/relics``; przypadki brzegowe:
``docs/rules_tirules/C_relics.md``. Zmiany stanu tylko przez punkty centralne (RULES.md 43.1a).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

from src.core import (
    card_draw,
    control,
    custodians,
    economy,
    exhaust,
    exploration,
    exploration_frontier,
    fracture,
    objectives,
    payment,
    relics,
    strategy_phase,
    technology,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.components import ComponentCategory
from src.core.dice import DIE_SIDES, next_rng, record_table_roll
from src.core.fleet_pool import unit_name
from src.core.game_state import GameState, SystemState
from src.core.hooks import card_labels
from src.core.hooks import card_targets_economy as targets
from src.core.hooks.card_helpers import controlled
from src.core.planet_stats import is_legendary, planet_stats
from src.core.registry import StaticDataRegistry
from src.core.relic_actions import blocker
from src.core.rules_hooks import register_effect, register_effect_inputs
from src.core.state_grid import grid_from_state
from src.core.strategy_cards.common import (
    STRUCTURE_LIMIT_PER_PLANET,
    place_structure,
    placeable_structures,
)
from src.core.system_planets import planets_of_system
from src.core.unit_ops import UnitCause

_CODEX_MAX = 3  # „up to 3 action cards”
_SILVER_FLAME_WIN = 10  # „if the result is a 10” (0 na d10 = 10)


def _text(params: Mapping[str, Any], key: str, message: str) -> str:
    value = params.get(key)
    if not isinstance(value, str):
        raise ValueError(message)
    return value


def _system_with_planet(
    state: GameState, registry: StaticDataRegistry, planet: str
) -> SystemState:
    """System, w którym leży planeta (także niczyja i bez jednostek); ``ValueError`` bez niej."""
    for position, system in state.systems.items():
        if planet in planets_of_system(state, registry, position):
            return system
    raise ValueError(f"Planet {planet} is not on the board.")


def _ready_blocker(state: GameState, player_id: str, relic_id: str, name: str) -> str | None:
    """Wspólny warunek reliktów „Exhaust this card”: relikt jest gotowy."""
    if not relics.is_ready(state, player_id, relic_id):
        return f"{name} is exhausted."
    return None


# --- The Codex -------------------------------------------------------------------------------


@register_effect_inputs("relics:codex")
def codex_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Karty akcji ze stosu odrzuconych (jawny stos; kopie tej samej karty liczone osobno)."""
    del player_id
    discard = state.decks.action_card_discard
    totals = Counter(discard)
    seen: Counter[str] = Counter()
    options = []
    for card_id in discard:
        seen[card_id] += 1
        card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
        name = (card.name if card is not None else None) or card_id
        label = f"{name} (copy {seen[card_id]})" if totals[card_id] > 1 else name
        options.append(oi.option(card_id, label, option_id=f"{card_id}#{seen[card_id]}"))
    return [
        oi.multi(
            "cards", "Action cards to take from the discard pile", options,
            0, min(_CODEX_MAX, len(options)), "Up to 3 cards; the pile is public.",
        )
    ]


@register_effect("relics:codex")
def codex(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """The Codex: ACTION: Purge this card to take up to 3 action cards of your choice from the
    action card discard pile.
    """
    del registry
    wanted = list(params.get("cards", []))
    available = Counter(state.decks.action_card_discard)
    for card_id, count in Counter(wanted).items():
        if count > available[card_id]:
            raise ValueError("That action card is not in the discard pile.")
    if len(wanted) > _CODEX_MAX:
        raise ValueError(f"Take at most {_CODEX_MAX} action cards.")
    for card_id in wanted:
        card_draw.take_from_discard(state, player_id, card_id)
    relics.purge_relic(state, player_id, "codex")


# --- Dynamis Core ----------------------------------------------------------------------------


@register_effect("relics:dynamiscore")
def dynamis_core(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Dynamis Core: ACTION: Gain trade goods equal to your commodity value, then purge this
    card.

    Commodity value liczymy PRZED purge (z bonusem karty); po purge nadmiar commodities wraca do
    puli (``on_lost``, C_relics).
    """
    del registry, params
    economy.gain_trade_goods(state, player_id, economy.commodity_value(state, player_id))
    relics.purge_relic(state, player_id, "dynamiscore")


# --- Book of Latvinia ------------------------------------------------------------------------


def _all_specialties(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Czy gracz kontroluje planety ze WSZYSTKIMI czterema typami specjalności technologii."""
    found: set[str] = set()
    for planet in controlled(state, player_id):
        stats = planet_stats(state, registry, planet)
        if stats is not None:
            found.update(s.upper() for s in stats.tech_specialties)
    return set(technology.COLORS) <= found


@register_effect("relics:bookoflatvinia")
def book_of_latvinia(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Book of Latvinia: ACTION: Purge this card; if you control planets that have all 4 types of
    technology specialties, gain 1 victory point. Otherwise, gain the speaker token.

    Obowiązkowe: przy wszystkich czterech typach gracz MUSI wziąć punkt (nie może wybrać mówcy).
    """
    del params
    relics.purge_relic(state, player_id, "bookoflatvinia")
    if _all_specialties(state, registry, player_id):
        objectives.award_points(state, player_id, 1)
    else:
        strategy_phase.set_speaker(state, player_id)


# --- Circlet of the Void ---------------------------------------------------------------------


def _circlet_positions(state: GameState, player_id: str) -> list[str]:
    """Systemy z żetonem frontier bez statków INNYCH graczy (jednostki neutralne nie liczą się)."""
    result: list[str] = []
    for position, system in state.systems.items():
        if not system.frontier_token:
            continue
        foreign = any(
            owner != player_id and owner in state.players and any(n > 0 for n in units.values())
            for owner, units in system.space_units.items()
        )
        if not foreign:
            result.append(position)
    return result


@blocker("circletofthevoid")
def _circlet_blocker(state: GameState, registry: StaticDataRegistry, player_id: str) -> str | None:
    del registry
    return _ready_blocker(state, player_id, "circletofthevoid", "Circlet of the Void")


@register_effect_inputs("relics:circletofthevoid")
def circlet_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Frontier w systemie bez cudzych statków."""
    return [
        oi.choice(
            "position", "Frontier token to explore",
            [
                oi.option(pos, card_labels.describe_system(state, registry, pos))
                for pos in _circlet_positions(state, player_id)
            ],
        )
    ]


@register_effect("relics:circletofthevoid")
def circlet_of_the_void(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Circlet of the Void: ACTION: Exhaust this card to explore a frontier token in a system that
    does not contain any other players' ships.
    """
    position = _text(params, "position", "Choose a system with a frontier token.")
    if position not in _circlet_positions(state, player_id):
        raise ValueError("Choose a frontier token in a system without other players' ships.")
    exhaust.exhaust_relic(state, player_id, "circletofthevoid")
    exploration_frontier.start_frontier(state, registry, player_id, position)


# --- Nano-Forge ------------------------------------------------------------------------------


def _nanoforge_planets(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    """Własne planety nielegendarne i nie-domowe."""
    homes = targets.home_planet_ids(state, registry)
    return [
        planet
        for planet in controlled(state, player_id)
        if planet not in homes and not is_legendary(state, registry, planet)
    ]


@register_effect_inputs("relics:nanoforge")
def nanoforge_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Planeta, do której przyczepiasz kartę (+2/+2 i legenda)."""
    return [
        oi.choice(
            "planet", "Planet to attach Nano-Forge to",
            [
                oi.option(
                    planet,
                    card_labels.describe_planet(
                        state, registry, planet, effect="+2 resources, +2 influence, legendary"
                    ),
                )
                for planet in _nanoforge_planets(state, registry, player_id)
            ],
        )
    ]


@register_effect("relics:nanoforge")
def nano_forge(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Nano-Forge: ACTION: Attach this card to a non-legendary, non-home planet you control, its
    resource and influence values are increased by 2 and it is a legendary planet. This action
    cannot be performed once attached.

    Karta schodzi z reliktów gracza i zostaje przy planecie (``planet_attachments``) niezależnie
    od zmiany kontroli; wartości i legendarność liczy ``planet_stats`` z attachmentu ``nanoforge``.
    """
    planet = _text(params, "planet", "Choose 1 non-legendary, non-home planet you control.")
    if planet not in _nanoforge_planets(state, registry, player_id):
        raise ValueError("Choose 1 non-legendary, non-home planet you control ('planet').")
    relics.detach(state, player_id, "nanoforge")
    exploration.attach_to_planet(state, planet, "nanoforge")


# --- Stellar Converter -----------------------------------------------------------------------


def _converter_planets(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str]]:
    """Planety do zniszczenia jako ``(planeta, pozycja systemu)``.

    Non-home, nielegendarne, nie Mecatol Rex, w systemie SĄSIEDNIM do systemu z jednostką gracza
    z BOMBARDMENT (jednostka i planeta nie mogą być w tym samym systemie), nie własne planety.
    """
    sources = {s.position for s in targets.bombardment_systems(state, registry, player_id)}
    if not sources:
        return []
    grid = grid_from_state(state, registry)
    homes = targets.home_planet_ids(state, registry)
    result: list[tuple[str, str]] = []
    for position, system in state.systems.items():
        if custodians.is_mecatol_position(state, position):
            continue
        if not any(src != position and grid.are_adjacent(position, src) for src in sources):
            continue
        for planet in planets_of_system(state, registry, position, grid):
            if (
                planet in homes
                or is_legendary(state, registry, planet)
                or system.planet_owners.get(planet) == player_id
            ):
                continue
            result.append((planet, position))
    return result


@register_effect_inputs("relics:stellarconverter")
def stellar_converter_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Planety do zniszczenia (z kontrolerem w opisie)."""
    options = []
    for planet, _position in _converter_planets(state, registry, player_id):
        system = _system_with_planet(state, registry, planet)
        owner = system.planet_owners.get(planet)
        effect = (
            f"destroyed (controlled by {card_labels.describe_player(state, registry, owner)})"
            if owner in state.players
            else "destroyed"
        )
        options.append(
            oi.option(planet, card_labels.describe_planet(state, registry, planet, effect=effect))
        )
    return [oi.choice("planet", "Planet to destroy", options)]


@register_effect("relics:stellarconverter")
def stellar_converter(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Stellar Converter: ACTION: Choose 1 non-home, non-legendary planet other than Mecatol Rex in
    a system that is adjacent to 1 or more of your units that have BOMBARDMENT, destroy all units on
    that planet and purge its attachments and its planet card. Then, place the destroyed planet
    token on that planet and purge this card.

    Zniszczone jednostki giną (UNIT_DESTROYED), planeta traci kontrolera i wychodzi z gry
    (``SystemState.destroyed_planets``): system bez innych planet liczy się jako bez planet.
    """
    planet = _text(params, "planet", "Choose 1 planet to destroy.")
    if planet not in {p for p, _pos in _converter_planets(state, registry, player_id)}:
        raise ValueError(
            "Choose a non-home, non-legendary planet (not Mecatol Rex) in a system adjacent to "
            "your unit with BOMBARDMENT ('planet')."
        )
    system = _system_with_planet(state, registry, planet)
    for owner, units in list(system.planet_units.get(planet, {}).items()):
        for base_type, count in list(units.items()):
            unit_ops.remove_units(
                state, system, planet, owner, base_type, count, UnitCause.DESTROYED
            )
    unit_ops.clear_planet(system, planet)
    control.set_planet_control(state, system.position, planet, None, registry)
    exploration.purge_planet_attachments(state, planet)
    system.destroyed_planets = [*system.destroyed_planets, planet]
    relics.purge_relic(state, player_id, "stellarconverter")


# --- The Silver Flame ------------------------------------------------------------------------


@register_effect("relics:thesilverflame")
def the_silver_flame(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """The Silver Flame: ACTION: Roll 1 die and purge this card; if the result is a 10, gain 1
    victory point. Otherwise, purge your home system and all units in it; you cannot score public
    objectives. Put The Fracture into play if it is not already.

    Rzut jest fizyczną kością w UI (``record_table_roll``); wynik liczy silnik (0 na d10 = 10).
    „Purge home system": jednostki znikają, planety wychodzą z gry i tracą kontrolera, więc gracz
    nie spełnia warunku celów publicznych (kontrola wszystkich planet domowych).
    """
    del params
    player = state.players[player_id]
    result = next_rng(state).randint(1, DIE_SIDES)
    won = result == _SILVER_FLAME_WIN
    record_table_roll(
        state, player_id, "relic", "The Silver Flame", [result], hit_values=[_SILVER_FLAME_WIN],
        summary=(
            "A 10! The Silver Flame grants 1 victory point."
            if won
            else "The Silver Flame consumes your home system."
        ),
    )
    relics.purge_relic(state, player_id, "thesilverflame")
    if won:
        objectives.award_points(state, player_id, 1)
        return
    home = state.systems.get(player.home_position or "")
    if home is not None:
        for owner, units in list(home.space_units.items()):
            for base_type, count in list(units.items()):
                unit_ops.remove_units(state, home, "space", owner, base_type, count)
        for planet in planets_of_system(state, registry, home.position):
            for owner, units in list(home.planet_units.get(planet, {}).items()):
                for base_type, count in list(units.items()):
                    unit_ops.remove_units(state, home, planet, owner, base_type, count)
            unit_ops.clear_planet(home, planet)
            control.set_planet_control(state, home.position, planet, None, registry)
            home.destroyed_planets = [*home.destroyed_planets, planet]
    grid = grid_from_state(state, registry)
    fracture.put_into_play(state, registry, grid, player_id)


# --- JR-XS455-O ------------------------------------------------------------------------------

_TITAN_COST = 3  # „spend 3 resources”
_DECLINE = "none"


@blocker("titanprototype")
def _titan_blocker(state: GameState, registry: StaticDataRegistry, player_id: str) -> str | None:
    del registry
    return _ready_blocker(state, player_id, "titanprototype", "JR-XS455-O")


@register_effect_inputs("relics:titanprototype")
def titan_prototype_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Gracz, jego odpowiedź (struktura albo odmowa) i płatność zasobami.

    ⚠ ZAŁOŻENIE: decyzję wskazanego gracza podaje formularz (tryb lokalny / ustalenie przy stole);
    silnik waliduje, że płatność i planeta należą do wskazanego gracza.
    """
    del player_id
    players = [
        oi.option(pid, card_labels.describe_player(state, registry, pid)) for pid in state.players
    ]
    placements = [oi.option(_DECLINE, "Decline - that player gains 1 trade good")]
    planets: list[dict[str, Any]] = []
    max_tg = 0
    for pid in state.players:
        who = card_labels.describe_player(state, registry, pid)
        for planet, structures in placeable_structures(state, pid).items():
            for structure in structures:
                placements.append(
                    oi.option(
                        f"{pid}|{planet}|{structure}",
                        f"{who}: {unit_name(state, registry, pid, structure)} on "
                        f"{card_labels.planet_name(registry, planet)}",
                    )
                )
        for planet, value in payment.ready_planet_values(state, registry, pid, "resources").items():
            planets.append(
                oi.option(planet, f"{who}: {card_labels.planet_name(registry, planet)} ({value})")
            )
        max_tg = max(max_tg, state.players[pid].trade_goods)
    return [
        oi.choice("player", "Player who is offered the structure", players),
        oi.choice("placement", "Their answer", placements),
        oi.multi("planets", "Planets they exhaust (3 resources)", planets, 0, len(planets)),
        oi.number("trade_goods", "Trade goods they spend", 0, max_tg),
    ]


@register_effect("relics:titanprototype")
def jr_xs455_o(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """JR-XS455-O: ACTION: Exhaust this agent and choose a player, that player may spend 3
    resources to place a structure on a planet they control. If they do not, they gain 1 trade
    good.

    Agent: wyczerpanie to wyczerpanie reliktu (odświeża się w statusie, C_relics). Wskazany gracz
    (także sam właściciel) płaci 3 zasoby i stawia strukturę ALBO odmawia i bierze 1 TG.
    """
    target = _text(params, "player", "Choose a player.")
    if target not in state.players:
        raise ValueError("Choose a player at the table ('player').")
    placement = _text(params, "placement", "Choose their answer.")
    exhaust.exhaust_relic(state, player_id, "titanprototype")
    if placement == _DECLINE:
        economy.gain_trade_goods(state, target, 1)
        return
    owner, planet, structure = placement.split("|")
    if owner != target or structure not in STRUCTURE_LIMIT_PER_PLANET:
        raise ValueError("The structure must be placed by the chosen player ('placement').")
    planets, trade_goods = payment.parse_payment(dict(params))
    paid = payment.validate_payment(state, registry, target, "resources", planets, trade_goods)
    if paid < _TITAN_COST:
        raise ValueError(f"Spend at least {_TITAN_COST} resources (chosen: {paid}).")
    place_structure(state, target, planet, structure)
    payment.apply_payment(state, target, planets, trade_goods)
