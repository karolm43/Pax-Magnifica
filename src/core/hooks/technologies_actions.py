"""Technologie z akcją komponentu, zdolnościami poza akcją i ofertami „may” (RULES.md 57).

Gracz zawsze decyduje sam: akcje i zdolności dostają formularz z opcjami liczonymi przez silnik,
oferty „may” trafiają do okna decyzji (RULES.md 56). Efekty zmieniają stan wyłącznie przez punkty
centralne (płatności, wyczerpywanie, jednostki, żetony, eksploracja, produkcja).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    command_tokens,
    control,
    economy,
    exhaust,
    exploration,
    exploration_frontier,
    production,
    rules_hooks,
    ship_roles,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, ProductionGrant
from src.core.planet_stats import planet_stats, resources_of
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    SOURCE_TECHNOLOGY,
    HookSource,
    on_event,
    register_ability,
    register_ability_inputs,
    register_effect,
    register_effect_inputs,
)
from src.core.system_planets import planets_of_system
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE
from src.core.unit_ops import UnitCause

SLING_RELAY = "sr"
PSYCHOARCHAEOLOGY = "pa"
DARK_ENERGY_TAP = "det"
SCANLINK = "sdn"
SELF_ASSEMBLY = "sar"
INTEGRATED_ECONOMY = "ie"
TRANSIT_DIODES = "td"
PREDICTIVE_INTELLIGENCE = "pi"

# Efekty realizowane jako jawny wybór gracza w regule bazowej (parametr przy strzale/produkcji).
rules_hooks.declare_player_option("technologies:gls", "technologies:aida")

# Opcja „nic" w slotach (id niepuste, bo puste id nie daje się wybrać w polu formularza).
NONE = oi.option("", "- none -", option_id="none")
_TD_SLOTS = 4  # „up to 4 of your ground forces"
_UNLIMITED_UNITS = 99  # Integrated Economy: „any number of units" (ogranicza koszt)


def _src(alias: str) -> HookSource:
    return HookSource(SOURCE_TECHNOLOGY, alias)


def _planet_name(registry: StaticDataRegistry, planet_id: str) -> str:
    planet = registry.planets.get(planet_id)
    return planet.name if planet is not None else planet_id


def _own_event(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


def _ready(state: GameState, player_id: str, tech_id: str) -> bool:
    player = state.players[player_id]
    return tech_id in player.technologies and tech_id not in player.exhausted_technologies


def _has_specialty(state: GameState, registry: StaticDataRegistry, planet_id: str) -> bool:
    stats = planet_stats(state, registry, planet_id)
    return stats is not None and bool(stats.tech_specialties)


# --- Sling Relay: ACTION -> produkcja 1 statku ------------------------------------------------


def _dock_systems(state: GameState, player_id: str) -> list[str]:
    """Pozycje systemów, w których gracz ma dok (na planecie)."""
    return sorted(
        pos
        for pos, system in state.systems.items()
        if any(
            by_player.get(player_id, {}).get("spacedock", 0) > 0
            for by_player in system.planet_units.values()
        )
    )


@register_effect_inputs(f"technologies:{SLING_RELAY}")
def sling_relay_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """System z Twoim dokiem, w którym wyprodukujesz statek."""
    options = []
    for pos in _dock_systems(state, player_id):
        names = ", ".join(
            _planet_name(registry, p) for p in planets_of_system(state, registry, pos)
        )
        options.append(oi.option(pos, f"{names or 'System'} ({pos})"))
    return [oi.choice("system", "System with one of your space docks", options)]


@register_effect(f"technologies:{SLING_RELAY}")
def sling_relay(
    state: GameState, _registry: Any, player_id: str, params: Mapping[str, Any]
) -> None:
    """Sling Relay: wyczerp kartę, by wyprodukować 1 statek w systemie z Twoim dokiem.

    Jednostka musi być opłacona (okno produkcji), a karta jest już wyczerpana (C_technology).
    """
    if not _ready(state, player_id, SLING_RELAY):
        raise ValueError("Sling Relay is not ready.")
    system = str(params.get("system", ""))
    if system not in _dock_systems(state, player_id):
        raise ValueError("Choose a system that contains one of your space docks.")
    if state.production_grant is not None:
        raise ValueError("Another production is still open - finish it first.")
    exhaust.exhaust_technology(state, player_id, SLING_RELAY)
    state.production_grant = ProductionGrant(
        player_id=player_id, position=system, units=1, free=True, ships_only=True,
        source="Sling Relay", mandatory=True,
    )


# --- Psychoarchaeology: 1 TG za wyczerpaną planetę ze specjalnością (poza akcją) ----------------


@register_ability_inputs(PSYCHOARCHAEOLOGY)
def psychoarchaeology_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Gotowe planety ze specjalnością technologii, które możesz wyczerpać za 1 TG każda."""
    player = state.players[player_id]
    planets = [
        p
        for p in player.controlled_planets
        if p not in player.exhausted_planets and _has_specialty(state, registry, p)
    ]
    options = [oi.option(p, _planet_name(registry, p)) for p in planets]
    return [oi.multi("planets", "Planets to exhaust (1 trade good each)", options, 1, len(options))]


@register_ability(PSYCHOARCHAEOLOGY)
def psychoarchaeology(
    state: GameState, registry: Any, player_id: str, params: Mapping[str, Any]
) -> None:
    """Psychoarchaeology: w fazie akcji wyczerp planety ze specjalnością, by zdobyć po 1 TG.

    Nie jest akcją. Nie można w trakcie rozstrzygania innej zdolności (okno, oferty, walka...).
    """
    if state.phase.name != "ACTION":
        raise ValueError("Psychoarchaeology can only be used during the action phase.")
    if (
        state.pending_window is not None
        or state.pending_offers
        or state.pending_strategy is not None
        or state.active_combat is not None
        or state.exploration is not None
    ):
        raise ValueError("Finish resolving the current ability first.")
    for planet in params.get("planets", []):
        exhaust.exhaust_planets(state, player_id, [planet])
        economy.gain_trade_goods(state, player_id, 1)  # po jednym, jak w C_technology


# --- Dark Energy Tap: eksploracja żetonu frontier po akcji taktycznej ----------------------------


def _frontier_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return _own_event(state, player_id, ctx) and exploration_frontier.can_explore_frontier(
        state, player_id, str(ctx.get("position", ""))
    )


@on_event(
    GameEvent.TACTICAL_ACTION,
    Moment.END,
    _src(DARK_ENERGY_TAP),
    condition=_frontier_ready,
    covers=f"technologies:{DARK_ENERGY_TAP}",
    label="Dark Energy Tap: explore the frontier token",
)
def dark_energy_tap(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dark Energy Tap: po akcji taktycznej w systemie z żetonem frontier i Twoim statkiem
    zbadaj ten żeton (obowiązkowo - C_technology). Karta trafia do okna eksploracji."""
    exploration_frontier.start_frontier(
        state, exploration.bound_registry(), player_id, str(ctx["position"])
    )


# --- Scanlink Drone Network: eksploracja planety przy aktywacji ----------------------------------


def _explorable_own_planets(
    state: GameState, registry: StaticDataRegistry, player_id: str, position: str
) -> list[str]:
    system = state.systems.get(position)
    if system is None:
        return []
    return [
        planet
        for planet in planets_of_system(state, registry, position)
        if exploration.explorable(registry, planet)
        and any(n > 0 for n in system.planet_units.get(planet, {}).get(player_id, {}).values())
    ]


def scanlink_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Planety aktywowanego systemu, na których masz jednostki i które można zbadać."""
    planets = _explorable_own_planets(state, registry, player_id, str(ctx["position"]))
    return [
        oi.choice("planet", "Planet to explore",
                  [oi.option(p, _planet_name(registry, p)) for p in planets])
    ]


def _scanlink_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    registry = rules_hooks.bound_registry()
    return (
        _own_event(state, player_id, ctx)
        and registry is not None
        and bool(_explorable_own_planets(state, registry, player_id, str(ctx["position"])))
    )


@on_event(
    GameEvent.SYSTEM_ACTIVATED,
    Moment.AFTER,
    _src(SCANLINK),
    optional=True,
    condition=_scanlink_ready,
    covers=f"technologies:{SCANLINK}",
    label="Scanlink Drone Network: explore a planet",
    inputs=scanlink_inputs,
)
def scanlink(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Scanlink Drone Network: przy aktywacji systemu możesz zbadać 1 planetę z Twoimi
    jednostkami (okno eksploracji)."""
    exploration.start_exploration(
        state, exploration.bound_registry(), player_id, str(ctx["position"]),
        [str(ctx["params"]["planet"])],
    )


# --- Self-Assembly Routines: mech po PRODUCTION --------------------------------------------------


def _mech_planets(
    state: GameState, registry: StaticDataRegistry, player_id: str, position: str
) -> list[str]:
    system = state.systems.get(position)
    if system is None:
        return []
    return [p for p, owner in sorted(system.planet_owners.items()) if owner == player_id]


def _movable_mechs(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """(system, strefa) z mechem gracza w systemie BEZ jego żetonu dowodzenia (C_technology)."""
    result: list[tuple[str, str]] = []
    for pos, system in sorted(state.systems.items()):
        if player_id in system.command_tokens:
            continue
        if system.space_units.get(player_id, {}).get("mech", 0) > 0:
            result.append((pos, "space"))
        for zone in sorted(system.planet_units):
            if system.planet_units[zone].get(player_id, {}).get("mech", 0) > 0:
                result.append((pos, zone))
    return result


def _mech_source_id(pos: str, zone: str) -> str:
    return f"{pos}|{zone}"


def self_assembly_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    planets = _mech_planets(state, registry, player_id, str(ctx["position"]))
    inputs = [
        oi.choice("planet", "Planet to place the mech on",
                  [oi.option(p, _planet_name(registry, p)) for p in planets])
    ]
    if production.reinforcements_left(state, player_id, "mech") == 0:
        # Rezerwa pusta: mecha trzeba zdjąć z planszy (system bez Twojego żetonu dowodzenia).
        inputs.append(
            oi.choice(
                "from",
                "No mech in reinforcements - take one from",
                [
                    oi.option(
                        _mech_source_id(pos, zone),
                        f"{pos} - {'space' if zone == 'space' else _planet_name(registry, zone)}",
                    )
                    for pos, zone in _movable_mechs(state, player_id)
                ],
            )
        )
    return inputs


def _self_assembly_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    registry = rules_hooks.bound_registry()
    left = production.reinforcements_left(state, player_id, "mech")
    return (
        _own_event(state, player_id, ctx)
        and _ready(state, player_id, SELF_ASSEMBLY)
        and registry is not None
        and bool(_mech_planets(state, registry, player_id, str(ctx["position"])))
        and (left is None or left > 0 or bool(_movable_mechs(state, player_id)))
    )


@on_event(
    GameEvent.PRODUCTION_USED,
    Moment.AFTER,
    _src(SELF_ASSEMBLY),
    optional=True,
    condition=_self_assembly_ready,
    covers=f"technologies:{SELF_ASSEMBLY}",
    label="Self-Assembly Routines: place a mech",
    inputs=self_assembly_inputs,
)
def self_assembly_mech(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Self-Assembly Routines: po PRODUCTION wyczerp kartę, by postawić 1 mecha z rezerwy
    na planecie, którą kontrolujesz w tym systemie. Gdy rezerwa jest pusta, mecha zdejmujesz
    z dowolnego systemu bez Twojego żetonu dowodzenia (C_technology); stawiany nieuszkodzony."""
    exhaust.exhaust_technology(state, player_id, SELF_ASSEMBLY)
    system = state.systems[str(ctx["position"])]
    if production.reinforcements_left(state, player_id, "mech") == 0:
        source = str(ctx["params"].get("from", ""))
        pos, _, zone = source.partition("|")
        if (pos, zone) not in _movable_mechs(state, player_id):
            raise ValueError("Choose a mech in a system without your command token.")
        unit_ops.remove_units(
            state, state.systems[pos], zone, player_id, "mech", 1, UnitCause.REMOVED
        )
    unit_ops.place_units(
        state, system, str(ctx["params"]["planet"]), player_id, "mech", 1, UnitCause.PLACED
    )


# --- Integrated Economy: produkcja po zdobyciu planety -------------------------------------------


def _ie_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    registry = rules_hooks.bound_registry()
    return (
        _own_event(state, player_id, ctx)
        and registry is not None
        and state.production_grant is None
        and resources_of(state, registry, str(ctx["planet"])) > 0
    )


@on_event(
    GameEvent.PLANET_CONTROL_GAINED,
    Moment.AFTER,
    _src(INTEGRATED_ECONOMY),
    optional=True,
    condition=_ie_ready,
    covers=f"technologies:{INTEGRATED_ECONOMY}",
    label="Integrated Economy: produce units on the planet",
)
def integrated_economy(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Integrated Economy: po zdobyciu planety możesz wyprodukować dowolną liczbę jednostek
    o łącznym koszcie ≤ wartości zasobów planety (jednostki trzeba opłacić; okno produkcji)."""
    registry = exploration.bound_registry()
    planet = str(ctx["planet"])
    state.production_grant = ProductionGrant(
        player_id=player_id, position=str(ctx["position"]), units=_UNLIMITED_UNITS,
        free=True, zone=planet, max_cost=float(resources_of(state, registry, planet)),
        source="Integrated Economy",
    )


# --- Transit Diodes: do 4 sił naziemnych na początku tury ------------------------------------


def _td_stacks(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[tuple[str, str, str, int]]:
    """(system, strefa, typ, liczba) sił naziemnych gracza (na planetach i w kosmosie)."""
    result: list[tuple[str, str, str, int]] = []
    movable = ship_roles.movable_ground_force_types(state, player_id)
    for pos, system in sorted(state.systems.items()):
        for base_type, count in sorted(system.space_units.get(player_id, {}).items()):
            if count > 0 and base_type in movable:
                result.append((pos, "space", base_type, count))
        for zone in sorted(system.planet_units):
            for base_type, count in sorted(system.planet_units[zone].get(player_id, {}).items()):
                if count > 0 and base_type in movable:
                    result.append((pos, zone, base_type, count))
    return result


def _td_targets(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """(system, planeta) planet kontrolowanych przez gracza."""
    return [
        (pos, planet)
        for pos, system in sorted(state.systems.items())
        for planet, owner in sorted(system.planet_owners.items())
        if owner == player_id
    ]


def transit_diodes_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Cztery sloty: która siła naziemna (skąd) i na którą Twoją planetę."""
    stacks = []
    for pos, zone, base_type, count in _td_stacks(state, registry, player_id):
        place = "in space" if zone == "space" else f"on {_planet_name(registry, zone)}"
        stacks.append(
            oi.option(
                f"{pos}|{zone}|{base_type}",
                f"{base_type.title()} {place} ({pos}) x{count}",
                meta={
                    "position": pos,
                    "zone": zone,
                    "baseType": base_type,
                    "asyncId": ASYNC_ID_BY_BASE_TYPE.get(base_type, base_type),
                    "count": count,
                    "placeName": "space" if zone == "space" else _planet_name(registry, zone),
                },
            )
        )
    targets = [
        oi.option(
            f"{pos}|{planet}",
            f"{_planet_name(registry, planet)} ({pos})",
            meta={"position": pos, "planet": planet, "name": _planet_name(registry, planet)},
        )
        for pos, planet in _td_targets(state, player_id)
    ]
    inputs: list[dict[str, Any]] = []
    for slot in range(1, _TD_SLOTS + 1):
        inputs.append(
            oi.choice(f"unit{slot}", f"Ground force {slot}", [NONE, *stacks])
        )
        inputs.append(
            oi.choice(
                f"to{slot}", f"Destination planet {slot}", [NONE, *targets]
            )
        )
    return inputs


def _td_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    registry = rules_hooks.bound_registry()
    return (
        state.phase.name == "ACTION"
        and _ready(state, player_id, TRANSIT_DIODES)
        and registry is not None
        and bool(_td_stacks(state, registry, player_id))
        and bool(_td_targets(state, player_id))
    )


def _td_turn_start(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return _own_event(state, player_id, ctx) and _td_ready(state, player_id, ctx)


def _td_first_turn(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return state.active_player_id == player_id and _td_ready(state, player_id, ctx)


def transit_diodes(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Transit Diodes: na początku Twojej tury w fazie akcji wyczerp kartę i przenieś do 4 sił
    naziemnych z planszy na planety, które kontrolujesz (także z różnych systemów).
    Uszkodzony mech zostaje uszkodzony."""
    params = ctx["params"]
    moves: list[tuple[str, str, str, str, str]] = []
    for slot in range(1, _TD_SLOTS + 1):
        unit, dest = str(params.get(f"unit{slot}", "")), str(params.get(f"to{slot}", ""))
        if bool(unit) != bool(dest):
            raise ValueError(f"Slot {slot}: choose both the ground force and the planet.")
        if unit:
            pos, zone, base_type = unit.split("|")
            dest_pos, planet = dest.split("|")
            moves.append((pos, zone, base_type, dest_pos, planet))
    if not moves:
        raise ValueError("Choose at least one ground force to move.")
    taken: dict[tuple[str, str, str], int] = {}
    for pos, zone, base_type, _dest_pos, _planet in moves:
        key = (pos, zone, base_type)
        taken[key] = taken.get(key, 0) + 1
        if taken[key] > unit_ops.count_in_zone(state.systems.get(pos), zone, player_id, base_type):
            raise ValueError("You chose more ground forces than are in that place.")
    exhaust.exhaust_technology(state, player_id, TRANSIT_DIODES)
    for pos, zone, base_type, dest_pos, planet in moves:
        unit_ops.transfer_units(
            state, state.systems[pos], zone, state.systems[dest_pos], planet, player_id,
            base_type, 1,
        )
        control.recompute_from_units(state, dest_pos, planet)


on_event(
    GameEvent.TURN, Moment.START, _src(TRANSIT_DIODES), optional=True,
    condition=_td_turn_start, label="Transit Diodes: move ground forces",
    inputs=transit_diodes_inputs,
)(transit_diodes)
on_event(
    GameEvent.PHASE, Moment.START, _src(TRANSIT_DIODES), optional=True,
    where={"phase": "action"}, condition=_td_first_turn, covers=f"technologies:{TRANSIT_DIODES}",
    label="Transit Diodes: move ground forces", inputs=transit_diodes_inputs,
)(transit_diodes)


# --- Predictive Intelligence: przerozdzielenie żetonów na końcu tury -------------------------


def predictive_intelligence_inputs(
    state: GameState, _registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Nowy rozdział WSZYSTKICH żetonów z arkusza (suma musi się zgadzać)."""
    total = command_tokens.sheet_total(state, player_id)
    player = state.players[player_id]
    hint = (
        f"Distribute exactly {total} tokens (now: tactic {player.tactical_cc}, "
        f"fleet {player.fleet_cc}, strategy {player.strategic_cc})."
    )
    return [
        oi.number("tactical", "Tactic pool", 0, total, hint),
        oi.number("fleet", "Fleet pool", 0, total),
        oi.number("strategic", "Strategy pool", 0, total),
    ]


@on_event(
    GameEvent.TURN,
    Moment.END,
    _src(PREDICTIVE_INTELLIGENCE),
    optional=True,
    condition=lambda s, p, c: c.get("player") == p and _ready(s, p, PREDICTIVE_INTELLIGENCE),
    label="Predictive Intelligence: redistribute command tokens",
    inputs=predictive_intelligence_inputs,
    covers=f"technologies:{PREDICTIVE_INTELLIGENCE}",
)
def predictive_intelligence(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Predictive Intelligence: na końcu tury wyczerp kartę, by przerozdzielić żetony dowodzenia.

    Druga zdolność (+3 głosy w agendzie, opcjonalna) jest w ``agenda_phase.cast_vote``
    (parametr ``use_predictive``), bo to decyzja gracza przy oddawaniu głosu. Zmniejszenie puli
    floty może wymagać zwrotu statków (okno fleet pool).
    """
    params = ctx["params"]
    pools = {name: int(params[name]) for name in ("tactical", "fleet", "strategic")}
    if sum(pools.values()) != command_tokens.sheet_total(state, player_id):
        raise ValueError("Distribute exactly all of your command tokens.")
    exhaust.exhaust_technology(state, player_id, PREDICTIVE_INTELLIGENCE)
    command_tokens.set_pools(state, player_id, pools)

