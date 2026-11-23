"""The Vuil'raith Cabal — komplet komponentów frakcji (RULES.md 62.17).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("cabal")``, ``units``).
Rulingi: ``docs/rules_tirules/F_vuilraith.md``. Mechanika przechwytywania: ``core/capture.py``
(RULES.md 61.5). Gracz decyduje sam (RULES.md 56).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    board_graph,
    capture,
    economy,
    exhaust,
    faction_components,
    faction_units,
    fracture,
    leaders,
    map_anomalies,
    promissory_play,
    rules_hooks,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.dice import DIE_SIDES, next_rng, record_table_roll
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_BREAKTHROUGH_FRACTURE_NO_ROLL,
    POINT_CAPTURE_DESTROYED,
    POINT_MAP_GRAVITY_RIFTS,
    POINT_MOVEMENT_MOVE_VALUE,
    POINT_MOVEMENT_RIFT_EXTRA_BONUS,
    POINT_MOVEMENT_RIFT_NO_ROLL,
    POINT_PRODUCTION_CAPTURED_FREE,
    POINT_PRODUCTION_FREE_SMALL_UNITS,
    POINT_TECHNOLOGY_CAPTURED_SKIP,
    SOURCE_BREAKTHROUGH,
    SOURCE_EFFECT,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_UNIT,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.state_grid import grid_from_state
from src.core.unit_catalog import is_space_unit

FACTION = "cabal"
AGENT = "cabalagent"
COMMANDER = "cabalcommander"
HERO = "cabalhero"
FLAGSHIP = "cabal_flagship"
MECH = "cabal_mech"
DOCK = "cabal_spacedock"
DOCK_II = "cabal_spacedock2"
DT2 = "dt2"
VORTEX = "vtx"
CRUCIBLE = "crucible"
BREAKTHROUGH = "cabalbt"

CRUCIBLE_EFFECT = f"promissory_notes:{CRUCIBLE}"  # do końca akcji taktycznej posiadacza
CRUCIBLE_PLAYED = f"promissory_notes:{CRUCIBLE}:played"  # F_vuilraith Crucible 4
ANCHOR_EFFECT = f"leaders:{HERO}:anchor"  # usunięte przez nadwyżkę ładunku -> przechwycone
INGRESS_WINDOW = f"breakthroughs:{BREAKTHROUGH}:ingress"  # „After this card enters play”
_RIFT_CAPTURE_ON = 3  # Dimensional Anchor: „on a 1-3, capture that unit”
_FREE_SMALL = 2  # That Which Molds Flesh: „Up to 2 of those units”
_RIFTS_TO_UNLOCK = 3  # „Have units in 3 gravity rifts.”
_INGRESS_MOVES = 2  # „move up to 2 ingress tokens”
_NONE = "none"
_CARGO = ("fighter", "infantry", "mech")
# Typy, które mogą trafić na arkusz (bez struktur) - kolejność = wyświetlanie.
_UNIT_TYPES = (
    "fighter", "infantry", "mech", "destroyer", "cruiser", "carrier", "dreadnought",
    "flagship", "warsun",
)


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _grid(state: GameState) -> HexGrid:
    """Siatka aplikacji (zsynchronizowana z anomaliami jednostek) albo odtworzona ze stanu."""
    grid = board_graph.bound_grid()
    if grid is None:
        return grid_from_state(state, _registry())
    map_anomalies.sync_grid(grid, state)
    return grid


def _faction_name(state: GameState, player_id: str) -> str:
    player = state.players.get(player_id)
    faction = _registry().factions.get(player.faction or "") if player is not None else None
    return faction.name if faction is not None else player_id


def _dock_positions(state: GameState, player_id: str) -> list[str]:
    """Systemy z dokiem gracza (Dimensional Tear) - na planecie albo w przestrzeni."""
    found = []
    for position, system in state.systems.items():
        if system.space_units.get(player_id, {}).get("spacedock", 0) > 0 or any(
            units.get(player_id, {}).get("spacedock", 0) > 0
            for units in system.planet_units.values()
        ):
            found.append(position)
    return sorted(found)


def _tear_positions(state: GameState) -> list[str]:
    """Systemy z Dimensional Tear dowolnego gracza z tym wariantem doku."""
    registry = _registry()
    found: set[str] = set()
    for pid in state.players:
        if faction_units.variant_of(state, registry, pid, "spacedock") in (DOCK, DOCK_II):
            found |= set(_dock_positions(state, pid))
    return sorted(found)


# ------------------------------------------------------------- Dimensional Tear (dok, dt2)


def _tears(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Dimensional Tear: This system is a gravity rift; your ships do not roll for this gravity
    rift. Place a dimensional tear token beneath this unit as a reminder.

    Pojemność „Up to N fighters” bierze ``capacity`` z tekstu zdolności (dane bez liczby)."""
    return set(_dock_positions(state, player_id))


for _variant, _covers in ((DOCK, f"units:{DOCK}"), (DOCK_II, f"technologies:{DT2}")):
    register(POINT_MAP_GRAVITY_RIFTS, HookSource(SOURCE_UNIT, _variant), HookKind.FORBID,
             covers=_covers)(_tears)
    register(POINT_MOVEMENT_RIFT_NO_ROLL, HookSource(SOURCE_UNIT, _variant), HookKind.FORBID,
             covers=_covers)(_tears)


# ---------------------------------------------------------------------------- Devour


@register(POINT_CAPTURE_DESTROYED, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers="abilities:devour")
def devour(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Devour: Capture your opponent's non-structure units that are destroyed during combat."""
    combat = state.active_combat
    owner = ctx.get("player")
    if combat is None or combat.position != ctx.get("position") or owner == player_id:
        return False
    sides = (combat.attacker, combat.defender)
    return player_id in sides and owner in sides


# ------------------------------------------------------------- The Terror Between (flagowiec)


def _flagship_lost_now(state: GameState, player_id: str, position: str) -> bool:
    """F_vuilraith flagowiec 1: zniszczony w tej samej rundzie walki nadal przechwytuje."""
    combat = state.active_combat
    return combat is not None and combat.position == position and any(
        d.get("player") == player_id and d.get("base_type") == "flagship"
        for d in combat.destroyed_ships
    )


@register(POINT_CAPTURE_DESTROYED, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.PERMIT,
          covers=f"units:{FLAGSHIP}")
def terror_between(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """The Terror Between: Capture all other non-structure units that are destroyed in this
    system, including your own (także poza walką - ruling 2)."""
    position = str(ctx.get("position") or "")
    if ctx.get("player") == player_id and ctx.get("base_type") == "flagship":
        return False  # „all OTHER units”
    system = state.systems.get(position)
    here = faction_units.count_in_system(system, player_id, "flagship") > 0
    return here or _flagship_lost_now(state, player_id, position)


# ------------------------------------------------------------------- Reanimator (mech)


@register(POINT_CAPTURE_DESTROYED, HookSource(SOURCE_UNIT, MECH), HookKind.PERMIT,
          covers=f"units:{MECH}")
def reanimator(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Reanimator: When your infantry on this planet are destroyed, place them on your faction
    sheet; those units are captured (każda przyczyna - ruling 2)."""
    if ctx.get("player") != player_id or ctx.get("base_type") != "infantry":
        return False
    system = state.systems.get(str(ctx.get("position") or ""))
    zone = str(ctx.get("zone") or "")
    if system is None or zone == "space":
        return False
    return unit_ops.count_in_zone(system, zone, player_id, "mech") > 0


# --------------------------------------------------------------- Amalgamation / Riftmeld


@register(POINT_PRODUCTION_CAPTURED_FREE, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers="abilities:amalgamation")
def amalgamation(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Amalgamation: When you produce a unit: You may return 1 captured unit of that type to
    produce that unit without spending resources (pole ``captured`` produkcji)."""
    return True


@register(POINT_TECHNOLOGY_CAPTURED_SKIP, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers="abilities:riftmeld")
def riftmeld(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Riftmeld: When you research a unit upgrade technology: You may return 1 captured unit of
    that type to ignore all of the technology's prerequisites (skip ``captured:<właściciel>``)."""
    return True


# ----------------------------------------------------------------------------- Vortex


def _vortex_targets(state: GameState, player_id: str) -> list[tuple[str, str, str, str]]:
    """``(właściciel, typ, pozycja, strefa)`` celów Vortex: cudza jednostka (nie struktura) w
    systemie SĄSIEDNIM do systemu z dokiem gracza, typ dostępny w rezerwie właściciela."""
    grid = _grid(state)
    docks = set(_dock_positions(state, player_id))
    near: set[str] = set()
    for dock in docks:
        near |= {n for n in grid.neighbors(dock) if n != dock}
    found: list[tuple[str, str, str, str]] = []
    for position in sorted(near):
        system = state.systems.get(position)
        if system is None:
            continue
        zones = [("space", system.space_units), *(
            (planet, by_player) for planet, by_player in sorted(system.planet_units.items())
        )]
        for zone, by_player in zones:
            for owner, units in sorted(by_player.items()):
                if owner == player_id or owner not in state.players:
                    continue
                for base_type, count in sorted(units.items()):
                    if count > 0 and capture.can_capture_from_reinforcements(
                        state, player_id, owner, base_type
                    ):
                        found.append((owner, base_type, position, zone))
    return found


@register_effect_inputs(f"technologies:{VORTEX}")
def vortex_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = []
    for owner, base_type, position, zone in _vortex_targets(state, player_id):
        meta = oi.unit_at(state, owner, base_type, position=position,
                          planet=None if zone == "space" else zone)
        label = f"{unit_name(state, registry, owner, base_type)} - {_faction_name(state, owner)}"
        options.append(oi.option(f"{owner}|{base_type}|{position}|{zone}", label, meta=meta))
    return [oi.choice("unit", "Unit whose type you capture from reinforcements", options)]


@register_effect(f"technologies:{VORTEX}")
def vortex(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Vortex: ACTION: Exhaust this card to choose another player's non-structure unit in a
    system that is adjacent to 1 or more of your space docks. Capture 1 unit of that type from
    that player's reinforcements."""
    owner, base_type, position, zone = (str(params.get("unit") or "").split("|") + ["", "", ""])[:4]
    if (owner, base_type, position, zone) not in _vortex_targets(state, player_id):
        raise ValueError("Choose another player's unit next to your space dock.")
    if VORTEX in state.players[player_id].exhausted_technologies:
        raise ValueError("Vortex is exhausted.")
    exhaust.exhaust_technology(state, player_id, VORTEX)
    capture.from_reinforcements(state, player_id, owner, base_type)
    capture.note_capture(state, player_id, f"technologies:{VORTEX}", owner, base_type, 1)


# -------------------------------------------------------------- The Stillness of Stars


def _agent_options(state: GameState, player_id: str, target: str) -> list[dict[str, Any]]:
    """Typy z rezerwy ``target`` o koszcie ≤ commodity value (bez jednostek bez kosztu)."""
    registry = _registry()
    owner = state.players[target]
    value = economy.commodity_value(state, target)
    options: list[dict[str, Any]] = []
    for base_type in _UNIT_TYPES:
        unit = resolve_unit_variant(registry, owner.faction, owner.technologies, base_type)
        if unit is None or unit.cost is None:
            continue
        if unit.required_tech_id and unit.required_tech_id not in owner.technologies:
            continue  # War Sun bez ulepszenia nie ma kosztu (ruling 2)
        if float(unit.cost) > value or not capture.can_capture_from_reinforcements(
            state, player_id, target, base_type
        ):
            continue
        meta = oi.unit_meta(base_type, target, owner.faction, owner.color)
        options.append(oi.option(base_type, unit.name, meta=meta))
    return options


def _agent_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    target = ctx.get("player")
    return (
        isinstance(target, str) and target != player_id and target in state.players
        and leaders.is_ready(state, _registry(), player_id, AGENT)
    )


def agent_inputs(
    state: GameState, _registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    target = str(ctx.get("player"))
    options = _agent_options(state, player_id, target)
    if not options:
        options = [oi.option(_NONE, "No unit can be captured")]
    return [oi.choice("unit", f"Unit to capture from {_faction_name(state, target)}'s "
                              "reinforcements", options, always=True)]


@on_event(
    GameEvent.COMMODITIES_REPLENISHED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_agent_ready, inputs=agent_inputs, covers=f"leaders:{AGENT}",
    label="The Stillness of Stars",
)
def stillness_of_stars(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The Stillness of Stars: After another player replenishes commodities: You may exhaust this
    card to convert their commodities to trade goods and capture 1 unit from their reinforcements
    that has a cost equal to or lower than their commodity value."""
    target = str(ctx["player"])
    choice = str(ctx.get("params", {}).get("unit") or _NONE)
    allowed = {o["value"] for o in _agent_options(state, player_id, target)}
    if choice != _NONE and choice not in allowed:
        raise ValueError("That unit cannot be captured.")
    if choice == _NONE and allowed:
        raise ValueError("Choose a unit to capture.")
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT, ctx)
    commodities = state.players[target].commodities
    if commodities > 0:
        # Zamiana to nie „zdobycie” TG (ruling 6: Pillage nie reaguje) - przyczyna ``convert``.
        economy.convert_commodities_to_trade_goods(state, target, commodities)
    if choice != _NONE:
        capture.from_reinforcements(state, player_id, target, choice)
        capture.note_capture(state, player_id, f"leaders:{AGENT}", target, choice, 1)


# -------------------------------------------------------------- That Which Molds Flesh


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have units in 3 gravity rifts (także Dimensional Tear)."""
    grid = _grid(state)
    rifts = 0
    for position, system in state.systems.items():
        if map_anomalies.GRAVITY_RIFT not in grid.anomalies_at(position):
            continue
        if any(n > 0 for n in system.space_units.get(player_id, {}).values()) or any(
            n > 0 for units in system.planet_units.values()
            for n in units.get(player_id, {}).values()
        ):
            rifts += 1
    return rifts >= _RIFTS_TO_UNLOCK


@register(POINT_PRODUCTION_FREE_SMALL_UNITS, HookSource(SOURCE_LEADER, COMMANDER),
          HookKind.MODIFY, covers=f"leaders:{COMMANDER}")
def molds_flesh(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """That Which Molds Flesh: When you produce fighter or infantry units: Up to 2 of those units
    do not count against your PRODUCTION limit."""
    return _FREE_SMALL


# ------------------------------------------------- It Feeds on Carrion — Dimensional Anchor


@register_effect(f"leaders:{HERO}")
def dimensional_anchor(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """It Feeds on Carrion — Dimensional Anchor: ACTION: Each other player rolls a die for each of
    his non-fighter ships that are in or adjacent to a system that contains a dimensional tear. on
    a 1-3, capture that unit. If this causes a player's ground forces or fighter to be removed,
    also capture those units. Then, purge this card."""
    grid = _grid(state)
    tears = _tear_positions(state)
    zone_of: set[str] = set(tears)
    for tear in tears:
        zone_of |= set(grid.neighbors(tear))
    blocking = capture.blockaders(state, player_id)  # ruling 2: blokujący Tear nie rzucają
    rng = next_rng(state)
    touched: list[str] = []
    for owner in sorted(state.players):
        if owner == player_id or owner in blocking:
            continue
        results: list[int] = []
        for position in sorted(zone_of):
            system = state.systems.get(position)
            if system is None:
                continue
            for base_type, count in sorted(system.space_units.get(owner, {}).items()):
                if base_type == "fighter" or not is_space_unit(base_type) or count <= 0:
                    continue
                if base_type in capture.STRUCTURES:
                    continue
                rolls = [rng.randint(1, DIE_SIDES) for _ in range(count)]  # raz na statek (3)
                results.extend(rolls)
                hit = sum(1 for r in rolls if r <= _RIFT_CAPTURE_ON)
                taken = capture.from_board(state, player_id, owner, position, "space", base_type,
                                           hit)
                capture.note_capture(state, player_id, f"leaders:{HERO}", owner, base_type, taken)
                if taken and position not in touched:
                    touched.append(position)
        if results:
            record_table_roll(
                state, owner, "dimensional_anchor", "Dimensional Anchor", results,
                hit_values=list(range(1, _RIFT_CAPTURE_ON + 1)),
            )
    if touched:
        # Nadwyżka ładunku: okno CAPACITY (właściciel wybiera - ruling 4); usunięte trafią do Cabal.
        active_effects.add_effect(state, ANCHOR_EFFECT, Duration.TURN, owner=player_id,
                                  data={"positions": touched})


def _anchor_removal(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("base_type") not in _CARGO or ctx.get("player") == player_id:
        return False
    return any(
        ctx.get("position") in e.data.get("positions", [])
        for e in active_effects.effects_for(state, player_id, ANCHOR_EFFECT)
    )


@on_event(
    GameEvent.UNIT_REMOVED, Moment.AFTER, HookSource(SOURCE_EFFECT, ANCHOR_EFFECT),
    condition=_anchor_removal, covers=f"leaders:{HERO}", label="Dimensional Anchor: capture",
)
def anchor_capture(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dimensional Anchor: usunięte siły naziemne / myśliwce (nadwyżka ładunku) są przechwycone."""
    owner, base_type = str(ctx["player"]), str(ctx["base_type"])
    taken = capture.capture_removed(state, player_id, owner, base_type, int(ctx.get("count", 1)))
    capture.note_capture(state, player_id, f"leaders:{HERO}", owner, base_type, taken)


# --------------------------------------------------------------------------- Crucible


@promissory_play.condition(CRUCIBLE)
def _crucible_condition(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, _window: OpenWindow
) -> str | None:
    if active_effects.has_effect(state, _player_id, CRUCIBLE_PLAYED):
        return "Crucible was already played in this timing window."
    return None


@register_effect(f"promissory_notes:{CRUCIBLE}")
def crucible(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Crucible: After you activate a system: Your ships do not roll for gravity rifts during this
    movement, apply an additional +1 to the move values of your ships that would move out of or
    through a gravity rift instead. Then, return this card to the Vuil'raith player."""
    active_effects.add_effect(state, CRUCIBLE_EFFECT, Duration.TACTICAL_ACTION, owner=player_id)
    active_effects.add_effect(state, CRUCIBLE_PLAYED, Duration.TURN, owner=player_id)


@register(POINT_MOVEMENT_RIFT_EXTRA_BONUS, HookSource(SOURCE_EFFECT, CRUCIBLE_EFFECT),
          HookKind.PERMIT)
def crucible_bonus(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return True


# ----------------------------------------------------------- Al'raith Ix Ianovar (przełom)


@register(POINT_BREAKTHROUGH_FRACTURE_NO_ROLL, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
          HookKind.PERMIT, covers=f"breakthroughs:{BREAKTHROUGH}")
def fracture_without_roll(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Al'raith Ix Ianovar: This breakthrough causes The Fracture to enter play without a roll,
    if it is not already in play."""
    return True


@on_event(
    GameEvent.COMPONENT_GAINED, Moment.WHEN, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    where={"component": f"breakthroughs:{BREAKTHROUGH}"}, covers=f"breakthroughs:{BREAKTHROUGH}",
    label="Al'raith Ix Ianovar: ingress tokens",
)
def _open_ingress_window(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """After this card enters play, move up to 2 ingress tokens into systems that contain gravity
    rifts - okno do końca tury (po rozłożeniu wszystkich ingressów, ruling 1.2)."""
    active_effects.add_effect(state, INGRESS_WINDOW, Duration.TURN, owner=player_id)


def _ingress_systems(state: GameState) -> list[str]:
    return sorted(p for p, s in state.systems.items() if s.ingress_token)


def _rift_targets(state: GameState) -> list[str]:
    """Systemy ze szczeliną (także Dimensional Tear) bez ingressu, poza kaflami The Fracture."""
    grid = _grid(state)
    return sorted(
        p for p in grid.positions
        if map_anomalies.GRAVITY_RIFT in grid.anomalies_at(p)
        and not fracture.is_fracture_position(p)
        and not (state.systems.get(p) is not None and state.systems[p].ingress_token)
    )


@faction_components.window_use("breakthrough", BREAKTHROUGH)
def _ingress_window(state: GameState, _registry: StaticDataRegistry, player_id: str) -> str | None:
    if not active_effects.has_effect(state, player_id, INGRESS_WINDOW):
        return "Al'raith Ix Ianovar moves ingress tokens right after it enters play."
    if not state.fracture.in_play or state.fracture.pending:
        return "Place all ingress tokens first."
    if not _ingress_systems(state) or not _rift_targets(state):
        return "There is no ingress token to move into a gravity rift."
    return None


@register_effect_inputs(f"breakthroughs:{BREAKTHROUGH}")
def ingress_inputs(
    state: GameState, _registry: StaticDataRegistry, _player_id: str
) -> list[dict[str, Any]]:
    sources = [oi.option(_NONE, "Do not move")] + [
        oi.option(p, f"Ingress token in system {p}", meta={"position": p})
        for p in _ingress_systems(state)
    ]
    targets = [oi.option(_NONE, "Do not move")] + [
        oi.option(p, f"Gravity rift in system {p}", meta={"position": p})
        for p in _rift_targets(state)
    ]
    inputs: list[dict[str, Any]] = []
    for n in range(1, _INGRESS_MOVES + 1):
        inputs.append(oi.choice(f"from_{n}", f"Ingress token {n}: move from", sources))
        inputs.append(oi.choice(f"to_{n}", f"Ingress token {n}: move to", targets))
    return inputs


@register_effect(f"breakthroughs:{BREAKTHROUGH}")
def move_ingress(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """…move up to 2 ingress tokens into systems that contain gravity rifts."""
    moves = []
    for n in range(1, _INGRESS_MOVES + 1):
        src = str(params.get(f"from_{n}") or _NONE)
        dst = str(params.get(f"to_{n}") or _NONE)
        if (src == _NONE) != (dst == _NONE):
            raise ValueError("Choose both the ingress token and the gravity rift.")
        if src != _NONE:
            moves.append((src, dst))
    for src, dst in moves:
        if src not in _ingress_systems(state) or dst not in _rift_targets(state):
            raise ValueError("Move an ingress token into a gravity rift without one.")
        state.systems[src].ingress_token = False
        board_graph.ensure_system(state, dst).ingress_token = True
    active_effects.remove_by_key(state, INGRESS_WINDOW, owner=player_id)


@register(POINT_MOVEMENT_MOVE_VALUE, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
          HookKind.MODIFY, covers=f"breakthroughs:{BREAKTHROUGH}")
def fracture_move(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    """Apply +1 to the MOVE value of each of your ships that start their movement in The
    Fracture."""
    return 1 if fracture.is_fracture_position(str(ctx.get("from") or "")) else 0
