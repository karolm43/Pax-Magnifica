"""Zdolności legendarnych planet (RULES.md 60): karty zdolności w strefie gracza.

Źródłem hooka jest karta zdolności legendarnej gracza, który kontroluje planetę
(``SOURCE_PLANET``). Zdolności „you may” to oferty w oknie decyzji (RULES.md 56) - gracz zawsze
decyduje sam, a legalne opcje liczy silnik. Wyczerpanie dotyczy karty zdolności, nie karty
planety (``exhaust.exhaust_legendary``). Teksty w docstringach to dosłowne cytaty z
``assets/planets``; przypadki brzegowe: ``docs/rules_tirules/R_legendary_planets.md`` i
``C_legendary_planets.md``.

Niezrealizowane (⚠ patrz RULES.md 60.6): granie kart akcji leżących na Dok 'N Pic's Salvage Yard
(Garbozia) oraz STAR FORGE Muaat (The Nucleus - wspólna funkcja z ``factions/muaat``).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

from src.core import (
    active_effects,
    card_draw,
    command_tokens,
    control,
    economy,
    exhaust,
    expeditions,
    exploration,
    legendary_planets,
    objectives,
    secret_objectives,
    turn_flow,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.components import ComponentCategory
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, SystemState
from src.core.hooks import card_labels
from src.core.hooks import card_targets_economy as targets
from src.core.hooks.card_helpers import controlled, require_reinforcements, system_of_planet
from src.core.planet_abilities import blocker as planet_blocker
from src.core.planet_stats import is_legendary
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_MOVEMENT_MOVE_VALUE,
    SOURCE_EFFECT,
    SOURCE_PLANET,
    HookKind,
    HookSource,
    bound_registry,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.state_grid import grid_from_state
from src.core.system_planets import planets_of_system
from src.core.unit_catalog import is_space_unit

Params = Mapping[str, Any]
Inputs = list[dict[str, Any]]
EffectFn = Callable[[GameState, StaticDataRegistry, str, str, Params], None]
InputsFn = Callable[[GameState, StaticDataRegistry, str, str], Inputs]

_FIGHTERS_MAX = 2  # „up to 2 fighters” (Flight Academy)
_INFANTRY_MAX = 2  # „up to 2 infantry” (The Atrament)
_MALLICE_TRADE_GOODS = 2  # „gain 2 trade goods” (Exterrix Headquarters)
_FAVOUR_COMMAND_TOKENS = 2  # „Gain 2 command tokens” (Custodian's Favour)
_TEMPESTA_EFFECT = "planets:tempesta"  # efekt na czas akcji taktycznej (+1 do ruchu)

_PASS = (GameEvent.PLAYER_PASSED, Moment.WHEN)  # „when you pass”
_TURN_END = (GameEvent.TURN, Moment.END)  # „at the end of your turn”


def _src(planet_id: str) -> HookSource:
    return HookSource(SOURCE_PLANET, planet_id)


def _planet_label(registry: StaticDataRegistry, planet_id: str) -> str:
    planet = registry.planets.get(planet_id)
    return (planet.legendary_ability_name if planet is not None else None) or planet_id


def _register_timed(
    planet_ids: tuple[str, ...],
    when: tuple[GameEvent, Moment],
    effect: EffectFn,
    inputs: InputsFn | None = None,
    *,
    text: str,
    extra: Callable[[GameState, StaticDataRegistry, str, str], bool] | None = None,
) -> None:
    """Rejestruje zdolność „exhaust this card at <moment>”: oferta dla właściciela karty.

    Oferta pojawia się tylko, gdy karta jest gotowa, a gracz ma legalną odpowiedź na każdy wybór.
    Efekt sprawdza gotowość jeszcze raz (stan mógł się zmienić do przyjęcia oferty) i wyczerpuje
    kartę zdolności.
    """
    event, moment = when
    for planet_id in planet_ids:
        _register_one(planet_id, event, moment, effect, inputs, text, extra)


def _register_one(
    planet_id: str,
    event: GameEvent,
    moment: Moment,
    effect: EffectFn,
    inputs: InputsFn | None,
    text: str,
    extra: Callable[[GameState, StaticDataRegistry, str, str], bool] | None,
) -> None:
    def condition(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
        registry = bound_registry()
        if registry is None or ctx.get("player") != player_id:
            return False
        if not legendary_planets.is_ready(state, player_id, planet_id):
            return False
        if extra is not None and not extra(state, registry, player_id, planet_id):
            return False
        return inputs is None or oi.has_legal_answer(inputs(state, registry, player_id, planet_id))

    def offer_inputs(
        state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
    ) -> Inputs:
        return inputs(state, registry, decider, planet_id) if inputs is not None else []

    def run(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
        registry = bound_registry()
        if registry is None or not legendary_planets.is_ready(state, player_id, planet_id):
            raise ValueError(f"{planet_id}: the legendary planet ability card is not ready.")
        effect(state, registry, player_id, planet_id, ctx.get("params", {}))
        exhaust.exhaust_legendary(state, player_id, planet_id)

    run.__doc__ = text
    on_event(
        event,
        moment,
        _src(planet_id),
        optional=True,
        condition=condition,
        covers=f"planets:{planet_id}",
        label=f"{planet_id}: " + text.split(":", 1)[0],
        inputs=offer_inputs if inputs is not None else None,
    )(run)


# --- Exterrix Headquarters (Mallice) ----------------------------------------------------------


def _mallice_inputs(state: GameState, registry: StaticDataRegistry, pid: str, _p: str) -> Inputs:
    del registry
    options = [oi.option("trade_goods", f"Gain {_MALLICE_TRADE_GOODS} trade goods")]
    if state.players[pid].commodities > 0:
        options.append(oi.option("convert", "Convert all of your commodities to trade goods"))
    return [oi.choice("mode", "Exterrix Headquarters", options)]


def _mallice(
    state: GameState, _registry: StaticDataRegistry, pid: str, _planet: str, params: Params
) -> None:
    if params.get("mode") == "convert":
        economy.convert_commodities_to_trade_goods(state, pid, state.players[pid].commodities)
    else:
        economy.gain_trade_goods(state, pid, _MALLICE_TRADE_GOODS)


_register_timed(
    ("mallice", "lockedmallice"), _TURN_END, _mallice, _mallice_inputs,
    text=(
        "Exterrix Headquarters: You may exhaust this card at the end of your turn to gain 2 trade "
        "goods or convert all of your commodities to trade goods."
    ),
)


# --- Flight Academies (Illusion, Mirage, Phantasm) --------------------------------------------


def _fleet_positions(state: GameState, pid: str) -> list[str]:
    """Systemy z co najmniej jednym statkiem gracza."""
    return [
        position
        for position, system in state.systems.items()
        if any(count > 0 for count in system.space_units.get(pid, {}).values())
    ]


def _academy_inputs(state: GameState, registry: StaticDataRegistry, pid: str, _p: str) -> Inputs:
    positions = _fleet_positions(state, pid)
    left = reinforcements_left(state, pid, "fighter")
    maximum = _FIGHTERS_MAX if left is None else min(_FIGHTERS_MAX, left)
    return [
        oi.choice(
            "position", "System with your ships",
            [
                oi.option(pos, card_labels.describe_system(state, registry, pos))
                for pos in positions
            ],
        ),
        oi.number("count", "Fighters to place (up to 2)", 1 if maximum else 0, maximum),
    ]


def _academy(
    state: GameState, _registry: StaticDataRegistry, pid: str, _planet: str, params: Params
) -> None:
    position = str(params.get("position", ""))
    count = int(params.get("count", 0))
    if position not in _fleet_positions(state, pid):
        raise ValueError("Choose a system that contains 1 or more of your ships ('position').")
    if not 1 <= count <= _FIGHTERS_MAX:
        raise ValueError("Place 1 or 2 fighters ('count').")
    require_reinforcements(state, pid, "fighter", count)
    unit_ops.place_units(state, state.systems[position], "space", pid, "fighter", count)


_register_timed(
    ("illusion", "mirage", "phantasm"), _TURN_END, _academy, _academy_inputs,
    text=(
        "Flight Academy: You may exhaust this card at the end of your turn to place up to 2 "
        "fighters from your reinforcements in any system that contains 1 or more of your ships."
    ),
)


# --- Imperial Arms Vault (Hope's End) ---------------------------------------------------------


def _unit_planets(state: GameState, pid: str) -> list[str]:
    """Planety gracza, na których wolno stawiać jednostki (Custodia Vigilia nie przyjmuje ich)."""
    return [p for p in controlled(state, pid) if p != legendary_planets.CUSTODIAN_FAVOUR_PLANET]


def _mech_sources(state: GameState, pid: str) -> list[tuple[str, str]]:
    """Mechy gracza w systemach BEZ jego żetonu dowodzenia: ``(pozycja, planeta)``."""
    found: list[tuple[str, str]] = []
    for position, system in state.systems.items():
        if pid in system.command_tokens:
            continue
        for zone, by_player in system.planet_units.items():
            if by_player.get(pid, {}).get("mech", 0) > 0:
                found.append((position, zone))
    return found


def _vault_inputs(state: GameState, registry: StaticDataRegistry, pid: str, _p: str) -> Inputs:
    empty = reinforcements_left(state, pid, "mech") == 0
    sources = _mech_sources(state, pid)
    options: list[dict[str, Any]] = []
    if state.decks.action_card_deck or state.decks.action_card_discard:
        options.append(oi.option("card", "Draw 1 action card"))
    if not empty or sources:
        options.extend(
            oi.option(f"mech:{planet}", "Place 1 mech on " + card_labels.describe_planet(
                state, registry, planet
            ))
            for planet in _unit_planets(state, pid)
        )
    inputs = [oi.choice("choice", "Imperial Arms Vault", options)]
    if empty:
        # Rezerwa mechów pusta: mech schodzi z planszy (C_legendary_planets / R_legendary_planets).
        from_options = [oi.option("", "Not needed (drawing an action card)")] + [
            oi.option(
                f"{position}|{zone}",
                "Move the mech from " + card_labels.describe_planet(state, registry, zone),
            )
            for position, zone in sources
        ]
        inputs.append(oi.choice("from", "Mech to take from the board", from_options))
    return inputs


def _vault(
    state: GameState, _registry: StaticDataRegistry, pid: str, _planet: str, params: Params
) -> None:
    choice = str(params.get("choice", ""))
    if choice == "card":
        card_draw.draw_action_card(state, pid)
        return
    planet = choice.removeprefix("mech:")
    if not choice.startswith("mech:") or planet not in _unit_planets(state, pid):
        raise ValueError("Choose a planet you control for the mech ('choice').")
    if reinforcements_left(state, pid, "mech") == 0:
        taken = str(params.get("from", ""))
        position, _, zone = taken.partition("|")
        if (position, zone) not in _mech_sources(state, pid):
            raise ValueError("Choose a mech on the board to move ('from').")
        unit_ops.remove_units(state, state.systems[position], zone, pid, "mech", 1)
    unit_ops.place_units(state, system_of_planet(state, planet), planet, pid, "mech", 1)


_register_timed(
    ("hopesend",), _TURN_END, _vault, _vault_inputs,
    text=(
        "Imperial Arms Vault: You may exhaust this card at the end of your turn to place 1 mech "
        "from your reinforcements on any planet you control or draw 1 action card."
    ),
)


# --- The Atrament (Primor) --------------------------------------------------------------------


def _atrament_inputs(state: GameState, registry: StaticDataRegistry, pid: str, _p: str) -> Inputs:
    return [
        oi.choice(
            "planet", "Planet for the infantry",
            [
                oi.option(p, card_labels.describe_planet(state, registry, p))
                for p in _unit_planets(state, pid)
            ],
        ),
        oi.number("count", "Infantry to place (up to 2)", 1, _INFANTRY_MAX),
    ]


def _atrament(
    state: GameState, _registry: StaticDataRegistry, pid: str, _planet: str, params: Params
) -> None:
    planet = str(params.get("planet", ""))
    count = int(params.get("count", 0))
    if planet not in _unit_planets(state, pid) or not 1 <= count <= _INFANTRY_MAX:
        raise ValueError("Choose 1 planet you control and place 1 or 2 infantry on it.")
    unit_ops.place_units(state, system_of_planet(state, planet), planet, pid, "infantry", count)


_register_timed(
    ("primor",), _TURN_END, _atrament, _atrament_inputs,
    text=(
        "The Atrament: You may exhaust this card at the end of your turn to place up to 2 "
        "infantry from your reinforcements on any planet you control."
    ),
)


# --- The Acropolis (Emelpar) ------------------------------------------------------------------


def _acropolis_targets(
    state: GameState, registry: StaticDataRegistry, own_planet: str
) -> list[tuple[str, str, str]]:
    """Wyczerpane komponenty (nie karty strategii) wszystkich graczy: ``(rodzaj, właściciel, id)``.

    Bez samej karty The Acropolis. Karta zdolności legendarnej innej planety jest komponentem
    (R_legendary_planets zabrania tylko odświeżania jej efektami „ready a planet").
    """
    found: list[tuple[str, str, str]] = []
    for owner, player in state.players.items():
        found += [("planet", owner, p) for p in player.exhausted_planets]
        found += [("tech", owner, t) for t in player.exhausted_technologies]
        found += [("relic", owner, r) for r in player.exhausted_relics]
        found += [("legendary", owner, p) for p in player.exhausted_legendaries if p != own_planet]
        found += [
            ("leader", owner, leader)
            for leader, leader_state in player.leader_states.items()
            if leader_state == "exhausted"
        ]
        if player.breakthrough_exhausted:
            found.append(("breakthrough", owner, "breakthrough"))
    return found


def _acropolis_label(
    state: GameState, registry: StaticDataRegistry, kind: str, owner: str, ident: str
) -> str:
    who = card_labels.describe_player(state, registry, owner)
    if kind == "planet" or kind == "legendary":
        name = card_labels.planet_name(registry, ident)
        what = f"legendary ability {name}" if kind == "legendary" else f"planet {name}"
    elif kind == "tech":
        tech = registry.technologies.get(ident)
        what = f"technology {tech.name if tech else ident}"
    elif kind == "relic":
        what = f"relic {ident}"
    elif kind == "leader":
        leader = registry.leaders.get(ident)
        what = f"leader {leader.name if leader else ident}"
    else:
        what = "breakthrough"
    return f"Ready {what} ({who})"


def _acropolis_inputs(
    state: GameState, registry: StaticDataRegistry, _pid: str, planet: str
) -> Inputs:
    return [
        oi.choice(
            "target", "Component to ready",
            [
                oi.option(
                    f"{kind}|{owner}|{ident}",
                    _acropolis_label(state, registry, kind, owner, ident),
                )
                for kind, owner, ident in _acropolis_targets(state, registry, planet)
            ],
        )
    ]


def _acropolis(
    state: GameState, registry: StaticDataRegistry, _pid: str, planet: str, params: Params
) -> None:
    kind, _, rest = str(params.get("target", "")).partition("|")
    owner, _, ident = rest.partition("|")
    if (kind, owner, ident) not in _acropolis_targets(state, registry, planet):
        raise ValueError("Choose an exhausted component that is not a strategy card ('target').")
    if kind == "planet":
        exhaust.ready_planets(state, owner, [ident])
    elif kind == "tech":
        exhaust.ready_technology(state, owner, ident)
    elif kind == "relic":
        exhaust.ready_relic(state, owner, ident)
    elif kind == "legendary":
        exhaust.ready_legendary(state, owner, ident)
    elif kind == "leader":
        exhaust.ready_leader(state, owner, ident)
    else:
        exhaust.ready_breakthrough(state, owner)


_register_timed(
    ("emelpar",), _TURN_END, _acropolis, _acropolis_inputs,
    text=(
        "The Acropolis: You may exhaust this card at the end of your turn to ready another "
        "component that isn't a strategy card."
    ),
)


# --- Maxis Central Control (Faunus) -----------------------------------------------------------


def _faunus_targets(state: GameState, registry: StaticDataRegistry, pid: str) -> list[str]:
    """Planety bez jednostek i attachmentów, nie domowe, nie legendarne, nie własne."""
    grid = grid_from_state(state, registry)
    homes = targets.home_planet_ids(state, registry)
    result: list[str] = []
    for position in sorted(grid.positions):
        system = state.systems.get(position)
        for planet in planets_of_system(state, registry, position, grid):
            if (
                planet in homes
                or is_legendary(state, registry, planet)
                or (system is not None and system.planet_owners.get(planet) == pid)
                or state.planet_attachments.get(planet)
            ):
                continue
            units = system.planet_units.get(planet, {}) if system is not None else {}
            if any(n > 0 for by_type in units.values() for n in by_type.values()):
                continue
            result.append(planet)
    return result


def _faunus_inputs(state: GameState, registry: StaticDataRegistry, pid: str, _p: str) -> Inputs:
    return [
        oi.choice(
            "planet", "Planet to take control of",
            [
                oi.option(p, card_labels.describe_planet(state, registry, p))
                for p in _faunus_targets(state, registry, pid)
            ],
        )
    ]


def _faunus(
    state: GameState, registry: StaticDataRegistry, pid: str, _planet: str, params: Params
) -> None:
    planet = str(params.get("planet", ""))
    if planet not in _faunus_targets(state, registry, pid):
        raise ValueError(
            "Choose a non-home, non-legendary planet without units or attachments ('planet')."
        )
    grid = grid_from_state(state, registry)
    position = next(
        pos for pos in sorted(grid.positions)
        if planet in planets_of_system(state, registry, pos, grid)
    )
    if position not in state.systems:
        state.systems[position] = SystemState(
            position=position, system_id=grid.system_id_at(position)
        )
    previous = state.systems[position].planet_owners.get(planet)
    control.set_planet_control(state, position, planet, pid, registry)
    # C_legendary_planets: planeta, która nie miała kontrolera, jest eksplorowana.
    if previous is None:
        exploration.start_exploration(state, registry, pid, position, [planet])


_register_timed(
    ("faunus",), _PASS, _faunus, _faunus_inputs,
    text=(
        "Maxis Central Control: You may exhaust this card when you pass to gain control of a "
        "non-home, non-legendary planet that contains no units and has no attachments."
    ),
)


# --- Dok 'N Pic's Salvage Yard (Garbozia) -----------------------------------------------------


def _salvage_inputs(state: GameState, registry: StaticDataRegistry, _pid: str, _p: str) -> Inputs:
    options = []
    for card_id in dict.fromkeys(state.decks.action_card_discard):
        card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
        options.append(oi.option(card_id, (card.name if card is not None else None) or card_id))
    return [oi.choice("card", "Action card from the discard pile", options)]


def _salvage(
    state: GameState, _registry: StaticDataRegistry, _pid: str, planet: str, params: Params
) -> None:
    card_id = str(params.get("card", ""))
    if card_id not in state.decks.action_card_discard:
        raise ValueError("Choose an action card from the discard pile ('card').")
    card_draw.place_on_legendary_card(state, planet, card_id)


_register_timed(
    ("garbozia",), _PASS, _salvage, _salvage_inputs,
    text=(
        "Dok 'N Pic's Salvage Yard: You may exhaust this card when you pass to place 1 action "
        "card from the discard pile faceup on this card."
    ),
)


# --- Aeurex Mechanica (Industrex) -------------------------------------------------------------


def _upgraded_ships(state: GameState, registry: StaticDataRegistry, pid: str) -> list[str]:
    """Typy statków, dla których gracz ma technologię ulepszenia jednostki (wariant ulepszony)."""
    player = state.players[pid]
    owned = {t.lower() for t in player.technologies}
    ships = sorted({u.base_type for u in registry.units.values() if is_space_unit(u.base_type)})
    result: list[str] = []
    for base_type in ships:
        variant = resolve_unit_variant(
            registry, player.faction, player.technologies, base_type, player.breakthrough_unlocked,
        player.breakthrough_flipped,
        )
        required = variant.required_tech_id if variant is not None else None
        if required is not None and required.lower() in owned:
            left = reinforcements_left(state, pid, base_type)
            if left is None or left > 0:
                result.append(base_type)
    return result


def _mechanica_inputs(state: GameState, registry: StaticDataRegistry, pid: str, _p: str) -> Inputs:
    ships = [
        oi.option(base_type, unit_name(state, registry, pid, base_type))
        for base_type in _upgraded_ships(state, registry, pid)
    ]
    positions = _fleet_positions(state, pid)
    return [
        oi.choice("ship", "Ship matching your unit upgrade technology", ships),
        oi.choice(
            "position", "System with your ships",
            [
                oi.option(pos, card_labels.describe_system(state, registry, pos))
                for pos in positions
            ],
        ),
    ]


def _mechanica(
    state: GameState, registry: StaticDataRegistry, pid: str, _planet: str, params: Params
) -> None:
    ship = str(params.get("ship", ""))
    position = str(params.get("position", ""))
    if ship not in _upgraded_ships(state, registry, pid):
        raise ValueError("Choose a ship that matches a unit upgrade technology you own ('ship').")
    if position not in _fleet_positions(state, pid):
        raise ValueError("Choose a system that contains 1 or more of your ships ('position').")
    unit_ops.place_units(state, state.systems[position], "space", pid, ship, 1)


_register_timed(
    ("industrex",), _PASS, _mechanica, _mechanica_inputs,
    text=(
        "Aeurex Mechanica: You may exhaust this card when you pass to place 1 ship that matches "
        "a unit upgrade technology you own from your reinforcements into a system that contains "
        "your ships."
    ),
)


# --- The Galactic Council (Mecatol Rex, Thunder's Edge) ---------------------------------------


def _council_inputs(state: GameState, registry: StaticDataRegistry, pid: str, _p: str) -> Inputs:
    options = []
    for objective_id in state.players[pid].private.secret_objectives:
        definition = objectives.objective_def(registry, objective_id)
        options.append(
            oi.option(objective_id, (definition.name if definition else None) or objective_id)
        )
    return [oi.choice("objective", "Secret objective to discard", options)]


def _council(
    state: GameState, _registry: StaticDataRegistry, pid: str, _planet: str, params: Params
) -> None:
    objective_id = str(params.get("objective", ""))
    if objective_id not in state.players[pid].private.secret_objectives:
        raise ValueError("Choose an unscored secret objective from your hand ('objective').")
    # C_legendary_planets: najpierw odrzucenie (tasowanie do talii), dopiero potem dobranie - może
    # to być ten sam cel.
    secret_objectives.discard_unscored(state, pid, objective_id)
    secret_objectives.draw(state, pid, None)


_register_timed(
    ("mrte",), _TURN_END, _council, _council_inputs,
    text=(
        "The Galactic Council: You may exhaust this card at the end of your turn and discard 1 "
        "secret objective to draw 1 secret objective."
    ),
)


# --- 4X41D "Hyperion" VI / Barren Husk (Ordinian) ---------------------------------------------


def _hyperion_inputs(state: GameState, registry: StaticDataRegistry, pid: str, _p: str) -> Inputs:
    del registry
    if command_tokens.reinforcements(state, pid) > 0:
        names = {"tactical": "Tactic", "fleet": "Fleet", "strategic": "Strategy"}
        options = [oi.option(pool, f"{names[pool]} pool") for pool in command_tokens.POOLS]
    else:
        options = [oi.option("", "No command token in your reinforcements")]
    return [oi.choice("pool", "Pool for the command token", options)]


def _hyperion(
    state: GameState, _registry: StaticDataRegistry, pid: str, _planet: str, params: Params
) -> None:
    pool = str(params.get("pool", ""))
    card_draw.draw_action_card(state, pid)
    if pool:
        command_tokens.gain_from_reinforcements(state, pid, {pool: 1})


_register_timed(
    ("ordinian", "ordinianc4"), _PASS, _hyperion, _hyperion_inputs,
    text=(
        "Hyperion: You may exhaust this card when you pass to draw 1 action card and gain 1 "
        "command token."
    ),
)


# --- A Song Like Marrow (Styx) ----------------------------------------------------------------

_STYX = "styx"


def _styx_gained(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    del state
    return ctx.get("planet") == _STYX and ctx.get("player") == player_id


@on_event(
    GameEvent.PLANET_CONTROL_GAINED,
    Moment.AFTER,
    _src(_STYX),
    condition=_styx_gained,
    covers=f"planets:{_STYX}",
    label="A Song Like Marrow: gain 1 victory point",
)
def styx_gained(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """A Song Like Marrow: When you gain this card, gain 1 victory point."""
    del ctx
    objectives.award_points(state, player_id, 1, source=f"planets:{_STYX}")


@on_event(
    GameEvent.PLANET_CONTROL_LOST,
    Moment.WHEN,
    _src(_STYX),
    condition=_styx_gained,
    covers=f"planets:{_STYX}",
    label="A Song Like Marrow: lose 1 victory point",
)
def styx_lost(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """A Song Like Marrow: When you lose this card, lose 1 victory point.

    Hook odpala się WHEN utraty kontroli (karta jest jeszcze u gracza); w ``ctx["player"]`` jest
    gracz tracący planetę.
    """
    del ctx
    objectives.award_points(state, player_id, -1, source=f"planets:{_STYX}")


# --- Custodian's Favour (Custodia Vigilia) ----------------------------------------------------
# Część „While you control Mecatol Rex, it gains SPACE CANNON 5 and PRODUCTION 3” działa w
# ``space_cannon`` i ``production`` (``legendary_planets.mecatol_grants_planet``); tu druga
# klauzula.

_FAVOUR = legendary_planets.CUSTODIAN_FAVOUR_PLANET


def _favour_amount(state: GameState, player_id: str) -> int:
    return min(_FAVOUR_COMMAND_TOKENS, command_tokens.reinforcements(state, player_id))


def _favour_scored_by_other(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    del state
    return ctx.get("player") not in (None, player_id)


def _favour_inputs(
    state: GameState, _registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> Inputs:
    """Pula dla każdego żetonu (tyle, ile gracz ma w rezerwie, najwyżej 2)."""
    amount = _favour_amount(state, decider)
    names = {"tactical": "Tactic", "fleet": "Fleet", "strategic": "Strategy"}
    options = [
        oi.option(pool, f"{names[pool]} pool", f"{pool}#{index}")
        for pool in command_tokens.POOLS
        for index in range(amount)
    ]
    return [oi.multi("pools", "Pools for the command tokens", options, amount, amount)]


@on_event(
    GameEvent.IMPERIAL_VICTORY_POINT,
    Moment.AFTER,
    _src(_FAVOUR),
    condition=_favour_scored_by_other,
    covers=f"planets:{_FAVOUR}",
    label="Custodian's Favour: gain 2 command tokens",
    inputs=_favour_inputs,
    decide=True,
)
def custodians_favour(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Custodian's Favour: Gain 2 command tokens when another player scores a victory point with
    the second clause of the 'Imperial' strategy card.

    Żetony z rezerwy (R_command_tokens: bez rezerwy nie zyskasz); pulę każdego wybiera gracz.
    """
    amount = _favour_amount(state, player_id)
    pools = ctx.get("params", {}).get("pools", [])
    if len(pools) != amount or any(pool not in command_tokens.POOLS for pool in pools):
        raise ValueError(f"Choose a pool for each of the {amount} command tokens ('pools').")
    if amount:
        command_tokens.gain_from_reinforcements(state, player_id, dict(Counter(pools)))


# --- Ionian Fuel Refinery (Tempesta) ----------------------------------------------------------


def _tempesta(
    state: GameState, _registry: StaticDataRegistry, pid: str, _planet: str, _params: Params
) -> None:
    active_effects.add_effect(state, _TEMPESTA_EFFECT, Duration.TACTICAL_ACTION, owner=pid)


_register_timed(
    ("tempesta",), (GameEvent.SYSTEM_ACTIVATED, Moment.AFTER), _tempesta,
    text=(
        "Ionian Fuel Refinery: You may exhaust this card after you activate a system to apply +1 "
        "to the move value of 1 of your ships during this tactical action."
    ),
)


def _tempesta_boost(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    """Ionian Fuel Refinery: +1 do wartości ruchu JEDNEGO statku w tej akcji taktycznej.

    Własny przełącznik gracza (``tempesta`` w kontekście), niezależny od Gravity Drive;
    ``movement.move_fleet`` pilnuje jednego statku flagą ``GameState.tempesta_used``.
    """
    return 1 if ctx.get("tempesta") else 0


register(
    POINT_MOVEMENT_MOVE_VALUE,
    HookSource(SOURCE_EFFECT, _TEMPESTA_EFFECT),
    HookKind.MODIFY,
    covers="planets:tempesta",
)(_tempesta_boost)


# --- The Nucleus (Avernus) --------------------------------------------------------------------

_NUCLEUS = "avernus"


def _war_sun_positions(state: GameState, pid: str) -> list[str]:
    from src.core.hooks.factions import muaat  # lokalnie: moduł frakcji importuje hooki ogólne

    return muaat.war_sun_positions(state, pid)


@planet_blocker(_NUCLEUS)
def _nucleus_blocker(state: GameState, registry: StaticDataRegistry, pid: str) -> str | None:
    del registry
    if not _war_sun_positions(state, pid):  # F_muaat Avernus 3: także inny kontroler Avernus
        return "You need a war sun on the game board to use Star Forge."
    return None


@register_effect_inputs(f"planets:{_NUCLEUS}")
def nucleus_inputs(state: GameState, registry: StaticDataRegistry, pid: str) -> Inputs:
    """System z własnym war sunem i wybór: 2 myśliwce albo 1 niszczyciel (z rezerwy)."""
    from src.core.hooks.factions import muaat

    return muaat.forge_inputs(state, registry, pid)


@register_effect(f"planets:{_NUCLEUS}")
def nucleus(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Params
) -> None:
    """The Nucleus: ACTION: Exhaust this card to use the Embers of Muaat's STAR FORGE faction
    ability without spending a command token.

    Ten sam skutek co Star Forge (``muaat.resolve_star_forge``): mech Ember Colossus działa
    (F_muaat Avernus 2), Magmus nie - nie wydano żetonu (1). Inny kontroler Avernus tylko z war
    sunem na planszy (3).
    """
    del registry
    from src.core.hooks.factions import muaat

    muaat.resolve_star_forge(state, player_id, params, source=f"planets:{_NUCLEUS}")
    exhaust.exhaust_legendary(state, player_id, _NUCLEUS)


# --- Jupiter Brain (Thunder's Edge) -----------------------------------------------------------

_THUNDERS_EDGE = "thundersedge"


def _thunders_edge_gained(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("planet") == _THUNDERS_EDGE and ctx.get("player") == player_id


@on_event(
    GameEvent.PLANET_CONTROL_GAINED,
    Moment.AFTER,
    _src(_THUNDERS_EDGE),
    condition=_thunders_edge_gained,
    covers=f"planets:{_THUNDERS_EDGE}",
    label="Jupiter Brain: gain your breakthrough",
)
def jupiter_brain_gained(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Jupiter Brain: Gain your breakthrough when you gain this card if you do not already have
    it.

    Jak każde zdobycie przełomu: odblokowanie i rzut na The Fracture (``expeditions``).
    """
    del ctx
    registry = bound_registry()
    if registry is not None:
        expeditions.gain_breakthrough(
            state, registry, grid_from_state(state, registry), player_id
        )


def _jupiter(
    state: GameState, _registry: StaticDataRegistry, pid: str, _planet: str, _params: Params
) -> None:
    window = state.turn_end_window
    if window is None or window.ended_player != pid:
        raise ValueError("You can perform the extra action only right after your own turn.")
    turn_flow.begin_bonus_action(state, pid)


_register_timed(
    (_THUNDERS_EDGE,), _TURN_END, _jupiter,
    text=(
        "Jupiter Brain: You may exhaust this card at the end of your turn to perform another "
        "action."
    ),
)
