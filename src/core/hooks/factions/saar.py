"""The Clan of Saar — komplet komponentów frakcji (RULES.md 62.14).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("saar")``, ``units``,
``breakthroughs/te_breakthroughs.json``). Rulingi: ``docs/rules_tirules/F_saar.md`` (krzyżowo
``R_blockaded`` - blokada pływającego doku, ``R_construction``, ``C_action_cards`` - Direct Hit,
``C_objectives`` - Improve Infrastructure / Protect the Border).
Punkty silnika dodane dla Saar: struktura pływająca (``units.floating_structure`` +
``core/floating_structures``), blokada aktywacji (``tactical.activation_blocked``), wartość ruchu
jednego statku (``movement.single_ship_value``), cele bez planet domowych
(``objectives.ignore_home_control``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    board_graph,
    board_reinforcements,
    economy,
    entropic_scar,
    exploration,
    faction_components,
    floating_structures,
    leaders,
    payment,
    production,
    promissory_play,
    rules_hooks,
    triggers,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count, set_damaged
from src.core.dice import DIE_SIDES, next_rng, record_table_roll
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, InvasionPhase, Phase, ProductionGrant, WindowType
from src.core.hex_grid import HexGrid
from src.core.hooks import card_labels
from src.core.hooks.card_helpers import system_of_planet
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_MOVEMENT_SINGLE_SHIP_VALUE,
    POINT_OBJECTIVES_IGNORE_HOME_CONTROL,
    POINT_TACTICAL_ACTIVATION_BLOCKED,
    POINT_UNIT_FLOATING_STRUCTURE,
    SOURCE_BREAKTHROUGH,
    SOURCE_EFFECT,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_TECHNOLOGY,
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
from src.core.unit_ops import UnitCause

FACTION = "saar"
SCAVENGE = "scavenge"
NOMADIC = "nomadic"
FLOATING_FACTORY = "saar_spacedock"
FLOATING_FACTORY_2 = "saar_spacedock2"
FFAC2 = "ffac2"
CHAOS_MAPPING = "cm"
AGENT = "saaragent"
COMMANDER = "saarcommander"
HERO = "saarhero"
MECH = "saar_mech"
RAGH = "ragh"
BREAKTHROUGH = "saarbt"

SCAVENGE_LATER = f"abilities:{SCAVENGE}:after_explore"  # TG po eksploracji (F_saar scavenge 2)
ZETA_LATER = f"units:{MECH}:after_explore"  # DEPLOY po eksploracji (F_saar zeta 2)
MENDOSA = f"leaders:{AGENT}"  # efekt: wartość ruchu 1 statku aktywnego gracza
DEORBIT_ASSIGN = "deorbit_assign"  # decyzja Saar: przypisanie trafień Deorbit Barrage
DEORBIT_SUSTAIN = "deorbit_sustain"  # decyzja właściciela: Sustain Damage na trafienia
DEORBIT_KEY = f"breakthroughs:{BREAKTHROUGH}:hits"
SUSTAIN_KEY = f"breakthroughs:{BREAKTHROUGH}:sustain"
_DEORBIT_HITS_ON = 4  # „for each roll of 4 or greater”
_DEORBIT_RANGE = 2  # „a planet up to 2 systems away from an asteroid field”
_COMMANDER_DOCKS = 3  # „Have 3 space docks on the game board.”
_SPACEDOCK = "spacedock"
_ASTEROID = "ASTEROID_FIELD"
_SPACE = "space"
_NONE = "none"
_GROUND = ("infantry", "mech")
_ROWL_TYPES = ("fighter", "infantry")  # „When you produce fighters or infantry”
_ARMAGEDDON_TYPES = ("infantry", "fighter")  # „Destroy all other players' infantry and fighters”


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _grid(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    """Siatka mapy gry (wszystkie kafle); bez niej (testy jednostkowe) - z systemów stanu."""
    return board_graph.bound_grid() or grid_from_state(state, registry)


def _own_event(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


def _system_option(state: GameState, registry: StaticDataRegistry, position: str) -> dict[str, Any]:
    return oi.option(position, card_labels.describe_system(state, registry, position))


def _planet_option(state: GameState, registry: StaticDataRegistry, planet: str) -> dict[str, Any]:
    return oi.option(planet, card_labels.describe_planet(state, registry, planet))


def _is_asteroid_field(state: GameState, registry: StaticDataRegistry, position: str) -> bool:
    system = state.systems.get(position)
    definition = registry.systems.get(system.system_id) if system is not None else None
    return definition is not None and _ASTEROID in definition.anomalies


def _has_ships(state: GameState, player_id: str, position: str) -> bool:
    system = state.systems.get(position)
    return system is not None and floating_structures.has_ships(system, player_id)


def dock_places(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """``(pozycja, strefa)`` doków gracza na planszy (pływający: strefa ``space``)."""
    found: list[tuple[str, str]] = []
    for position, system in sorted(state.systems.items()):
        if system.space_units.get(player_id, {}).get(_SPACEDOCK, 0) > 0:
            found.append((position, _SPACE))
        for planet, by_player in sorted(system.planet_units.items()):
            if by_player.get(player_id, {}).get(_SPACEDOCK, 0) > 0:
                found.append((position, planet))
    return found


# ------------------------------------------------------------ Floating Factory I/II (dok)


def _floating(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    """This unit is placed in the space area instead of on a planet. This unit can move and
    retreat as if it were a ship (``core/floating_structures``)."""
    return ctx.get("base_type") == _SPACEDOCK


register(POINT_UNIT_FLOATING_STRUCTURE, HookSource(SOURCE_UNIT, FLOATING_FACTORY),
         HookKind.PERMIT, covers=f"units:{FLOATING_FACTORY}")(_floating)
register(POINT_UNIT_FLOATING_STRUCTURE, HookSource(SOURCE_UNIT, FLOATING_FACTORY_2),
         HookKind.PERMIT, covers=f"technologies:{FFAC2}")(_floating)


def _has_floating(state: GameState, player_id: str, position: str) -> bool:
    return bool(floating_structures.floating_in(state, player_id, position))


def _arrival_blockade(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Statki wleciały do systemu z dokiem (albo wyleciały z niego) - F_saar FF 11, 10."""
    places = {str(ctx.get("position") or ""), str(ctx.get("from") or "")}
    return any(_has_floating(state, player_id, pos) for pos in places if pos)


def _combat_end_blockade(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("kind") == _SPACE and _has_floating(state, player_id, str(ctx.get("position")))


def _destroyed_outside_assignment(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Ostatni statek zniszczony POZA równoczesnym przypisywaniem strat rundy (Direct Hit -
    F_saar FF 7, 7.1); straty rundy rozstrzyga koniec walki (6.1)."""
    window = state.pending_window
    assigning = window is not None and window.window_type is WindowType.COMBAT_ASSIGN_HITS
    return (
        not assigning
        and ctx.get("player") == player_id
        and ctx.get("zone") == _SPACE
        and is_space_unit(str(ctx.get("base_type") or ""))
        and _has_floating(state, player_id, str(ctx.get("position")))
    )


def _destroy_blockaded(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """If this unit is blockaded, it is destroyed."""
    places = sorted({str(ctx.get("position") or ""), str(ctx.get("from") or "")} - {""})
    for position in places:
        lost = floating_structures.destroy_blockaded(state, position).get(player_id, {})
        if lost:
            ability_notes.note(state, player_id, f"units:{FLOATING_FACTORY}",
                               f"blockaded and destroyed in system {position}")


for _unit_id in (FLOATING_FACTORY, FLOATING_FACTORY_2):
    _src = HookSource(SOURCE_UNIT, _unit_id)
    on_event(GameEvent.SHIPS_MOVED, Moment.AFTER, _src, condition=_arrival_blockade,
             label="Floating Factory: blockaded")(_destroy_blockaded)
    on_event(GameEvent.COMBAT, Moment.END, _src, condition=_combat_end_blockade,
             label="Floating Factory: blockaded")(_destroy_blockaded)
    on_event(GameEvent.UNIT_DESTROYED, Moment.AFTER, _src,
             condition=_destroyed_outside_assignment,
             label="Floating Factory: blockaded")(_destroy_blockaded)


# ---------------------------------------------------------------------------- Scavenge


def will_explore(state: GameState, ctx: Mapping[str, Any]) -> bool:
    """Planeta bez poprzedniego kontrolera, zaraz eksplorowana (Establish Control inwazji)."""
    inv = state.invasion
    return (
        ctx.get("previous") is None
        and inv is not None
        and inv.phase is InvasionPhase.ESTABLISH
        and exploration.explorable(_registry(), str(ctx.get("planet")))
    )


def _later(state: GameState, key: str, player_id: str, planet: Any) -> list[Any]:
    return [
        e for e in state.active_effects
        if e.key == key and e.owner == player_id and e.data.get("planet") == planet
    ]


def _wait_for_exploration(state: GameState, key: str, player_id: str, ctx: Mapping[str, Any]
                          ) -> None:
    active_effects.add_effect(
        state, key, Duration.TACTICAL_ACTION, owner=player_id,
        data={"planet": str(ctx.get("planet")), "position": str(ctx.get("position") or "")},
    )


@on_event(
    GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    condition=_own_event, covers=f"abilities:{SCAVENGE}", label="Scavenge",
)
def scavenge(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Scavenge: After you gain control of a planet: Gain 1 trade good.

    Każda planeta osobno (F_saar 1); planeta niczyja - TG po jej eksploracji (2, 2.1)."""
    if will_explore(state, ctx):
        _wait_for_exploration(state, SCAVENGE_LATER, player_id, ctx)
        return
    economy.gain_trade_goods(state, player_id, 1, cause=f"abilities:{SCAVENGE}")


def _scavenge_waiting(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return bool(_later(state, SCAVENGE_LATER, player_id, ctx.get("planet")))


@on_event(
    GameEvent.PLANET_EXPLORED, Moment.AFTER, HookSource(SOURCE_EFFECT, SCAVENGE_LATER),
    condition=_scavenge_waiting, label="Scavenge",
)
def scavenge_after_exploration(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """TG ze Scavenge po eksploracji zdobytej planety (F_saar scavenge 2)."""
    for effect in _later(state, SCAVENGE_LATER, player_id, ctx.get("planet")):
        active_effects.remove_effect(state, effect.id)
        economy.gain_trade_goods(state, player_id, 1, cause=f"abilities:{SCAVENGE}")


# ----------------------------------------------------------------------------- Nomadic


@register(POINT_OBJECTIVES_IGNORE_HOME_CONTROL, HookSource(SOURCE_FACTION, FACTION),
          HookKind.PERMIT, covers=f"abilities:{NOMADIC}")
def nomadic(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Nomadic: You can score objectives even if you do not control the planets in your home
    system."""
    return True


# ------------------------------------------------------------------------ Chaos Mapping


@register(POINT_TACTICAL_ACTIVATION_BLOCKED, HookSource(SOURCE_TECHNOLOGY, CHAOS_MAPPING),
          HookKind.PERMIT, covers=f"technologies:{CHAOS_MAPPING}")
def chaos_mapping_blocks(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Other players cannot activate asteroid fields that contain 1 or more of your ships.

    Tylko statki (pływający dok i siły naziemne nie blokują - F_saar cm 5)."""
    position = str(ctx.get("position") or "")
    return (
        ctx.get("activator") != player_id
        and _is_asteroid_field(state, _registry(), position)
        and _has_ships(state, player_id, position)
    )


def chaos_mapping_systems(state: GameState, player_id: str) -> list[str]:
    """Systemy z jednostką gracza, która ma PRODUCTION."""
    registry = _registry()
    return sorted(
        position for position in state.systems
        if production.producers(state, registry, player_id, position)
    )


def _chaos_ready(state: GameState, player_id: str) -> bool:
    return (
        state.phase is Phase.ACTION
        and state.production_grant is None
        and bool(chaos_mapping_systems(state, player_id))
    )


def _chaos_turn_start(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and _chaos_ready(state, player_id)


def _chaos_first_turn(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return state.active_player_id == player_id and _chaos_ready(state, player_id)


def chaos_mapping_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [oi.choice("position", "System with your unit that has PRODUCTION", [
        _system_option(state, registry, pos) for pos in chaos_mapping_systems(state, player_id)
    ], always=True)]


def chaos_mapping_produce(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Chaos Mapping: At the start of your turn during the action phase, you may produce 1 unit
    in a system that contains at least 1 of your units that has PRODUCTION.

    Jednostka płatna (F_saar cm 1), bez wyczerpania - co turę (3), także w turze pasu (3.1)."""
    position = str((ctx.get("params") or {}).get("position") or "")
    if position not in chaos_mapping_systems(state, player_id):
        raise ValueError("Choose a system that contains your unit with PRODUCTION.")
    # „produce” poza akcją taktyczną (jak Umbat): grant ``free`` = bez użycia PRODUCTION i bez
    # aktywnego systemu, limit 1 sztuki; jednostka płatna, siły naziemne na planecie gracza w
    # systemie albo w przestrzeni.
    state.production_grant = ProductionGrant(
        player_id=player_id, position=position, units=1, free=True, source="Chaos Mapping",
    )


on_event(
    GameEvent.TURN, Moment.START, HookSource(SOURCE_TECHNOLOGY, CHAOS_MAPPING), optional=True,
    condition=_chaos_turn_start, inputs=chaos_mapping_inputs,
    covers=f"technologies:{CHAOS_MAPPING}", label="Chaos Mapping: produce 1 unit",
)(chaos_mapping_produce)
on_event(
    GameEvent.PHASE, Moment.START, HookSource(SOURCE_TECHNOLOGY, CHAOS_MAPPING), optional=True,
    where={"phase": "action"}, condition=_chaos_first_turn, inputs=chaos_mapping_inputs,
    label="Chaos Mapping: produce 1 unit",
)(chaos_mapping_produce)


# ------------------------------------------------------------------ Captain Mendosa (agent)


def _move_value(state: GameState, registry: StaticDataRegistry, owner: str, base_type: str
                ) -> int:
    player = state.players.get(owner)
    if player is None:
        return 0
    unit = resolve_unit_variant(registry, player.faction, player.technologies, base_type)
    return int(unit.move_value or 0) if unit is not None else 0


def highest_move_value(state: GameState, registry: StaticDataRegistry) -> int:
    """Najwyższa wartość ruchu statku na planszy (wartość z wariantu - bez premii wyzwalanych po
    aktywacji: Flank Speed, Gravity Drive, szczelina - F_saar mendosa 2.1, 2.2)."""
    best = 0
    for system in state.systems.values():
        for owner, units in system.space_units.items():
            for base_type, count in units.items():
                if count > 0 and is_space_unit(base_type):
                    best = max(best, _move_value(state, registry, owner, base_type))
    return best


def mendosa_ships(state: GameState, registry: StaticDataRegistry, activator: str
                  ) -> list[tuple[str, str]]:
    """``(pozycja, typ)`` statków aktywnego gracza poza aktywnym systemem z ruchem niższym niż
    najwyższy na planszy."""
    best = highest_move_value(state, registry)
    found: list[tuple[str, str]] = []
    for position, system in sorted(state.systems.items()):
        if position == state.active_system:
            continue
        for base_type, count in sorted(system.space_units.get(activator, {}).items()):
            if count > 0 and is_space_unit(base_type) and (
                _move_value(state, registry, activator, base_type) < best
            ):
                found.append((position, base_type))
    return found


def _mendosa_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    registry = _registry()
    activator = str(ctx.get("player") or "")
    return (
        activator in state.players
        and leaders.is_ready(state, registry, player_id, AGENT)
        and bool(mendosa_ships(state, registry, activator))
    )


def mendosa_inputs(
    state: GameState, registry: Any, _player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Statek aktywnego gracza wybrany na mapie."""
    activator = str(ctx.get("player") or "")
    options = [
        oi.option(f"{pos}|{bt}", unit_name(state, registry, activator, bt),
                  meta=oi.unit_at(state, activator, bt, position=pos))
        for pos, bt in mendosa_ships(state, registry, activator)
    ]
    return [oi.choice("ship", "Ship whose move value increases", options)]


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_mendosa_ready, inputs=mendosa_inputs, covers=f"leaders:{AGENT}",
    label="Captain Mendosa: increase a ship's move value",
)
def captain_mendosa(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Captain Mendosa: When a player activates a system: You may exhaust this card to increase
    the move value of 1 of that player's ships to match the move value of the ship on the game
    board that has the highest move value.

    Wartość docelowa ustalona w chwili użycia (F_saar mendosa 2); nadpisuje regułę mgławicy (3)."""
    registry = _registry()
    activator = str(ctx.get("player") or "")
    pick = str((ctx.get("params") or {}).get("ship") or "")
    position, _, base_type = pick.partition("|")
    if (position, base_type) not in mendosa_ships(state, registry, activator):
        raise ValueError("Choose 1 of the active player's ships outside the active system.")
    value = highest_move_value(state, registry)
    faction_components.pay_cost(state, registry, player_id, "leader", AGENT,
                                {"target": activator})
    active_effects.add_effect(
        state, MENDOSA, Duration.TACTICAL_ACTION, owner=activator,
        data={"position": position, "base_type": base_type, "value": value, "used": False},
    )
    ability_notes.note(state, player_id, f"leaders:{AGENT}",
                       f"{unit_name(state, registry, activator, base_type)} in system "
                       f"{position}: move value {value}")


def _mendosa_effects(state: GameState, player_id: str) -> list[Any]:
    return [e for e in state.active_effects if e.key == MENDOSA and e.owner == player_id]


@register(POINT_MOVEMENT_SINGLE_SHIP_VALUE, HookSource(SOURCE_EFFECT, MENDOSA), HookKind.MODIFY)
def mendosa_value(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Wartość ruchu wybranego statku (punkt ``movement.single_ship_value``)."""
    for effect in _mendosa_effects(state, player_id):
        data = effect.data
        if (
            not data.get("used")
            and data.get("position") == ctx.get("from")
            and data.get("base_type") == ctx.get("base_type")
        ):
            return int(data.get("value") or 0)
    return 0


def _mendosa_moved(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    ships = ctx.get("ships") or {}
    return ctx.get("player") == player_id and any(
        not e.data.get("used") and e.data.get("position") == ctx.get("from")
        and int(ships.get(e.data.get("base_type"), 0)) > 0
        for e in _mendosa_effects(state, player_id)
    )


@on_event(GameEvent.SHIPS_MOVED, Moment.AFTER, HookSource(SOURCE_EFFECT, MENDOSA),
          condition=_mendosa_moved, label="Captain Mendosa: ship moved")
def mendosa_spent(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Wybrany statek ruszył - premia dotyczy tylko jego (1 statek)."""
    ships = ctx.get("ships") or {}
    for effect in _mendosa_effects(state, player_id):
        if effect.data.get("position") == ctx.get("from") and int(
            ships.get(effect.data.get("base_type"), 0)
        ) > 0:
            effect.data = {**effect.data, "used": True}


# --------------------------------------------------------------- Rowl Sarrig (commander)


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 3 space docks on the game board (pływające też - stoją na planszy)."""
    total = sum(
        system.space_units.get(player_id, {}).get(_SPACEDOCK, 0)
        + sum(by.get(player_id, {}).get(_SPACEDOCK, 0) for by in system.planet_units.values())
        for system in state.systems.values()
    )
    return total >= _COMMANDER_DOCKS


def rowl_destinations(state: GameState, player_id: str) -> dict[str, str]:
    """System -> strefa niezablokowanego doku gracza (pływający: przestrzeń)."""
    found: dict[str, str] = {}
    for position, zone in dock_places(state, player_id):
        if not floating_structures.is_blockaded(state, player_id, position):
            found.setdefault(position, zone)
    return found


def _rowl_units(ctx: Mapping[str, Any]) -> list[tuple[str, str, int]]:
    """``(strefa, typ, sztuki)`` wyprodukowanych myśliwców / piechoty."""
    zones = ctx.get("zones") or {}
    return [
        (str(zone), bt, int(n))
        for zone, by_type in sorted(zones.items())
        for bt, n in sorted(by_type.items())
        if bt in _ROWL_TYPES and int(n) > 0
    ]


def _rowl_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    position = str(ctx.get("position") or "")
    return (
        ctx.get("player") == player_id
        and bool(_rowl_units(ctx))
        and any(pos != position for pos in rowl_destinations(state, player_id))
    )


def rowl_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Ruch wyprodukowanych sztuk do systemów z dokami - przeciąganie na mapie."""
    position = str(ctx.get("position") or "")
    units = [
        oi.option(f"{zone}|{bt}|{i}", unit_name(state, registry, player_id, bt),
                  meta=oi.unit_at(state, player_id, bt, position=position,
                                  planet=None if zone == _SPACE else zone))
        for zone, bt, n in _rowl_units(ctx)
        for i in range(n)
    ]
    dests = sorted(rowl_destinations(state, player_id))
    return [oi.unit_moves("moves", "Place the units at your space docks", units, dests)]


@on_event(
    GameEvent.UNITS_PRODUCED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_rowl_ready, inputs=rowl_inputs, covers=f"leaders:{COMMANDER}",
    label="Rowl Sarrig: place at your space docks",
)
def rowl_sarrig(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Rowl Sarrig: When you produce fighters or infantry: You may place each of those units at
    any of your space docks that are not blockaded."""
    position = str(ctx.get("position") or "")
    produced = {(zone, bt): n for zone, bt, n in _rowl_units(ctx)}
    dests = rowl_destinations(state, player_id)
    used: dict[tuple[str, str], int] = {}
    seen: set[str] = set()
    moves: list[tuple[str, str, str]] = []
    for value in (ctx.get("params") or {}).get("moves") or []:
        unit, dest = oi.split_move(str(value))
        zone, bt, _ = unit.split("|", 2)
        if unit in seen or dest not in dests:
            raise ValueError("Place each unit at most once, at a space dock that is not "
                             "blockaded.")
        seen.add(unit)
        used[(zone, bt)] = used.get((zone, bt), 0) + 1
        if used[(zone, bt)] > produced.get((zone, bt), 0):
            raise ValueError("You can place only the units you just produced.")
        moves.append((zone, bt, dest))
    source = state.systems[position]
    for zone, bt, dest in moves:
        target_zone = _SPACE if bt == "fighter" else dests[dest]
        unit_ops.transfer_units(state, source, zone, state.systems[dest], target_zone,
                                player_id, bt, 1)
    if moves:
        ability_notes.note(state, player_id, f"leaders:{COMMANDER}",
                           f"placed {len(moves)} unit(s) at space docks")


# ------------------------------------------------- Gurno Aggero — Armageddon Relay (hero)


def armageddon_systems(state: GameState, player_id: str) -> list[str]:
    """Systemy sąsiednie do systemu z dokiem gracza (system nie sąsiaduje sam ze sobą -
    F_saar gurno 1)."""
    grid = _grid(state, _registry())
    docks = {pos for pos, _ in dock_places(state, player_id)}
    return sorted(
        pos for pos in grid.positions
        if any(pos != dock and grid.are_adjacent(pos, dock) for dock in docks)
    )


@faction_components.blocker("leader", HERO)
def _hero_blocker(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> str | None:
    if not armageddon_systems(state, player_id):
        return "You have no space dock on the game board."
    return None


@register_effect_inputs(f"leaders:{HERO}")
def armageddon_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    return [oi.choice("position", "System adjacent to 1 of your space docks", [
        _system_option(state, registry, pos) for pos in armageddon_systems(state, player_id)
    ], always=True)]


@register_effect(f"leaders:{HERO}")
def armageddon_relay(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Gurno Aggero — Armageddon Relay: ACTION: Choose 1 system that is adjacent to 1 of your
    space docks. Destroy all other players' infantry and fighters in that system. Then, purge this
    card (purge - ``faction_components``)."""
    position = str(params.get("position") or "")
    if position not in armageddon_systems(state, player_id):
        raise ValueError("Choose a system adjacent to 1 of your space docks.")
    system = state.systems.get(position)
    if system is None:
        return
    destroyed = 0
    zones = [(_SPACE, system.space_units), *(
        (planet, by) for planet, by in sorted(system.planet_units.items())
    )]
    for zone, by_player in zones:
        for owner, units in sorted(by_player.items()):
            if owner == player_id:
                continue
            for base_type in _ARMAGEDDON_TYPES:
                count = units.get(base_type, 0)
                if count > 0:
                    unit_ops.remove_units(state, system, zone, owner, base_type, count,
                                          UnitCause.DESTROYED)
                    destroyed += count
    ability_notes.note(state, player_id, f"leaders:{HERO}",
                       f"destroyed {destroyed} infantry and fighters in system {position}")


# ------------------------------------------------------------------ Scavenger Zeta (mech)


def _zeta_possible(state: GameState, player_id: str) -> bool:
    return board_reinforcements.can_place(state, player_id, "mech")


def _zeta_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Bez wymogu TG w chwili oferty: Scavenge z tego samego przejęcia może opłacić DEPLOY
    (F_saar zeta 1) - zapłata sprawdzana przy przyjęciu oferty."""
    if ctx.get("player") != player_id:
        return False
    scar = any(
        entropic_scar.unit_abilities_blocked(state, position)
        for position, system in state.systems.items()
        if ctx.get("planet") in system.planet_owners or ctx.get("planet") in system.planet_units
    )
    if scar:
        return False  # DEPLOY nie działa w bliźnie entropicznej (RULES.md 1.5)
    return _zeta_possible(state, player_id)


def _mech_source_inputs(state: GameState, registry: Any, player_id: str
                        ) -> list[dict[str, Any]]:
    if not board_reinforcements.needs_board_source(state, player_id, "mech"):
        return []
    options = board_reinforcements.map_source_options(state, registry, player_id, "mech")
    return [oi.choice("source", "No mech left in reinforcements - take one from the board",
                      options)]


def zeta_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return _mech_source_inputs(state, registry, player_id)


def _deploy_zeta(state: GameState, player_id: str, planet: str, params: Mapping[str, Any]
                 ) -> None:
    if economy.spendable_trade_goods(state, player_id) < 1:
        raise ValueError("Scavenger Zeta: you need 1 trade good to DEPLOY.")
    system = system_of_planet(state, planet)
    source = params.get("source")
    economy.spend_trade_goods(state, player_id, 1)
    board_reinforcements.place_unit(state, system, planet, player_id, "mech",
                                    source=str(source) if source else None)
    ability_notes.note(state, player_id, f"units:{MECH}", f"DEPLOY on {planet}")


def _zeta_now(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return _zeta_ready(state, player_id, ctx) and not will_explore(state, ctx)


def _zeta_wait(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return _zeta_ready(state, player_id, ctx) and will_explore(state, ctx)


@on_event(
    GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, HookSource(SOURCE_UNIT, MECH),
    optional=True, condition=_zeta_now, inputs=zeta_inputs, covers=f"units:{MECH}",
    label="Scavenger Zeta: DEPLOY",
)
def scavenger_zeta(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Scavenger Zeta — DEPLOY: After you gain control of a planet, you may spend 1 trade good to
    place 1 mech on that planet (każda planeta osobno - F_saar zeta 3)."""
    _deploy_zeta(state, player_id, str(ctx.get("planet")), ctx.get("params") or {})


@on_event(
    GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, HookSource(SOURCE_UNIT, MECH),
    condition=_zeta_wait, label="Scavenger Zeta: after exploration",
)
def zeta_wait_for_exploration(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Planeta niczyja: DEPLOY dopiero po eksploracji (F_saar zeta 2)."""
    _wait_for_exploration(state, ZETA_LATER, player_id, ctx)


def _zeta_waiting(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return bool(_later(state, ZETA_LATER, player_id, ctx.get("planet"))) and _zeta_possible(
        state, player_id
    )


@on_event(
    GameEvent.PLANET_EXPLORED, Moment.AFTER, HookSource(SOURCE_EFFECT, ZETA_LATER),
    optional=True, condition=_zeta_waiting, inputs=zeta_inputs, label="Scavenger Zeta: DEPLOY",
)
def scavenger_zeta_after_exploration(
    state: GameState, player_id: str, ctx: Mapping[str, Any]
) -> None:
    planet = str(ctx.get("planet"))
    for effect in _later(state, ZETA_LATER, player_id, planet):
        active_effects.remove_effect(state, effect.id)
    _deploy_zeta(state, player_id, planet, ctx.get("params") or {})


# ------------------------------------------------------------------- Ragh's Call (notka)


def _saar_owner(state: GameState, registry: StaticDataRegistry) -> str | None:
    return promissory_play.resolve(state, registry, RAGH)[1]


def ragh_planets(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Planety z ostatniego zaangażowania, na których stoją siły naziemne Saar."""
    inv = state.invasion
    owner = _saar_owner(state, registry)
    if inv is None or owner is None:
        return []
    system = state.systems.get(inv.position)
    if system is None:
        return []
    return sorted(
        planet for planet in inv.last_commit
        if any(system.planet_units.get(planet, {}).get(owner, {}).get(bt, 0) > 0
               for bt in _GROUND)
    )


def ragh_destinations(state: GameState, registry: StaticDataRegistry) -> list[str]:
    owner = _saar_owner(state, registry)
    if owner is None:
        return []
    inv = state.invasion
    return sorted(
        planet for system in state.systems.values()
        for planet, controller in system.planet_owners.items()
        if controller == owner and not (
            inv is not None and system.position == inv.position and planet in inv.last_commit
        )
    )


@promissory_play.condition(RAGH)
def _ragh_condition(
    state: GameState, registry: StaticDataRegistry, _player_id: str, _window: Any
) -> str | None:
    if not ragh_planets(state, registry):
        return "None of your committed units landed on a planet with the Saar player's forces."
    if not ragh_destinations(state, registry):
        return "The Saar player controls no other planet to receive their ground forces."
    return None


@register_effect_inputs(f"promissory_notes:{RAGH}")
def ragh_inputs(
    state: GameState, registry: StaticDataRegistry, _player_id: str
) -> list[dict[str, Any]]:
    return [
        oi.choice("planet", "Planet you committed units to", [
            _planet_option(state, registry, p) for p in ragh_planets(state, registry)
        ]),
        oi.choice("destination", "Planet controlled by the Saar player", [
            _planet_option(state, registry, p) for p in ragh_destinations(state, registry)
        ], always=True),
    ]


@register_effect(f"promissory_notes:{RAGH}")
def raghs_call(
    state: GameState, registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Ragh's Call: After you commit 1 or more units to land on a planet: Remove all of the Saar
    player's ground forces from that planet and place them on a planet controlled by the Saar
    player. Then, return this card to the Saar player (zwrot - ``promissory_play``).

    Wszystkie na JEDNĄ planetę (F_saar 3), uszkodzenia zostają (4); walki naziemnej nie będzie
    (1), PDS zostają (2)."""
    owner = _saar_owner(state, registry)
    planet = str(params.get("planet") or "")
    dest = str(params.get("destination") or "")
    if owner is None or planet not in ragh_planets(state, registry):
        raise ValueError("Choose a planet you committed units to that has Saar ground forces.")
    if dest not in ragh_destinations(state, registry):
        raise ValueError("Choose a planet controlled by the Saar player.")
    source, target = system_of_planet(state, planet), system_of_planet(state, dest)
    for base_type in _GROUND:
        count = source.planet_units.get(planet, {}).get(owner, {}).get(base_type, 0)
        if count > 0:  # uszkodzenia jadą z jednostkami (unit_ops)
            unit_ops.transfer_units(state, source, planet, target, dest, owner, base_type, count)


# ------------------------------------------------------------- Deorbit Barrage (przełom)


def deorbit_planets(state: GameState, player_id: str) -> list[str]:
    """Planety do 2 systemów od pola asteroid z własnymi statkami (z jednostką naziemną)."""
    registry = _registry()
    grid = _grid(state, registry)
    fields = [
        pos for pos in state.systems
        if _is_asteroid_field(state, registry, pos) and _has_ships(state, player_id, pos)
    ]
    found: set[str] = set()
    for position, system in state.systems.items():
        if position not in grid.positions:
            continue
        if not any(field in grid.positions and grid.distance(field, position) <= _DEORBIT_RANGE
                   for field in fields):
            continue
        for planet in system.planet_owners.keys() | system.planet_units.keys():
            if _ground_targets(state, planet):
                found.add(planet)
    return sorted(found)


def _ground_targets(state: GameState, planet: str) -> dict[str, dict[str, int]]:
    """``{gracz: {typ: sztuki}}`` sił naziemnych na planecie."""
    try:
        system = system_of_planet(state, planet)
    except ValueError:
        return {}
    return {
        owner: {bt: units.get(bt, 0) for bt in _GROUND if units.get(bt, 0) > 0}
        for owner, units in sorted(system.planet_units.get(planet, {}).items())
        if any(units.get(bt, 0) > 0 for bt in _GROUND)
    }


@faction_components.blocker("breakthrough", BREAKTHROUGH)
def _deorbit_blocker(state: GameState, _registry_: StaticDataRegistry, player_id: str
                     ) -> str | None:
    if not deorbit_planets(state, player_id):
        return ("No planet with ground forces is up to 2 systems away from an asteroid field "
                "that contains your ships.")
    return None


@register_effect_inputs(f"breakthroughs:{BREAKTHROUGH}")
def deorbit_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Planeta na mapie + płatność „any amount” (planety + TG) - kwota przed rzutem (F_saar 1)."""
    ready = payment.ready_planet_values(state, registry, player_id, "resources")
    planets = [
        (p, registry.planets[p].name if p in registry.planets else p, v)
        for p, v in sorted(ready.items())
    ]
    spendable = economy.spendable_trade_goods(state, player_id)
    return [
        oi.choice("planet", "Planet up to 2 systems from an asteroid field with your ships", [
            _planet_option(state, registry, p) for p in deorbit_planets(state, player_id)
        ], always=True),
        oi.payment_planets(planets, "resources", 0, hint=(
            "Spend any amount of resources: roll 1 die for each resource spent.")),
        oi.number("trade_goods", "Trade goods to spend", 0, spendable),
    ]


@register_effect(f"breakthroughs:{BREAKTHROUGH}")
def deorbit_barrage(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Deorbit Barrage: ACTION: Exhaust this card and spend any amount of resources to choose a
    planet up to 2 systems away from an asteroid field that contains your ships; roll a number of
    dice equal to the amount spent and assign 1 hit to a ground force on that planet for each roll
    of 4 or greater (wyczerpanie - ``faction_components``; trafienia przypisuje Saar - F_saar 2)."""
    planet = str(params.get("planet") or "")
    if planet not in deorbit_planets(state, player_id):
        raise ValueError("Choose a planet with ground forces up to 2 systems away from an "
                         "asteroid field that contains your ships.")
    planets = [str(p) for p in params.get("planets") or []]
    trade_goods = int(params.get("trade_goods") or 0)
    amount = payment.validate_payment(state, registry, player_id, "resources", planets,
                                      trade_goods)
    payment.apply_payment(state, player_id, planets, trade_goods)
    rng = next_rng(state)
    results = [rng.randint(1, DIE_SIDES) for _ in range(amount)]
    hits = sum(1 for value in results if value >= _DEORBIT_HITS_ON)
    if results:
        record_table_roll(state, player_id, "deorbit_barrage", "Deorbit Barrage", results,
                          hits_on=_DEORBIT_HITS_ON, summary=f"{hits} hit(s) on {planet}.")
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                       f"spent {amount}, {hits} hit(s) on {planet}")
    if hits <= 0:
        return
    active_effects.add_effect(state, DEORBIT_KEY, Duration.TURN, owner=player_id,
                              data={"planet": planet, "hits": hits})
    faction_components.ability_used(state, player_id, DEORBIT_ASSIGN, player_id)


def _deorbit_pending(state: GameState, player_id: str) -> Any:
    return next(
        (e for e in state.active_effects if e.key == DEORBIT_KEY and e.owner == player_id), None
    )


def deorbit_assign_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Każde trafienie = 1 siła naziemna na planecie (kilka trafień w tę samą - F_saar 3.1)."""
    effect = _deorbit_pending(state, player_id)
    if effect is None:
        return []
    planet = str(effect.data["planet"])
    position = system_of_planet(state, planet).position
    options = [
        oi.option(f"{owner}|{bt}", unit_name(state, registry, owner, bt),
                  meta=oi.unit_at(state, owner, bt, position=position, planet=planet))
        for owner, units in _ground_targets(state, planet).items()
        for bt in units
    ]
    return [
        oi.choice(f"hit{i + 1}", f"Hit {i + 1}: ground force on {planet}", options)
        for i in range(int(effect.data["hits"]))
    ]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    where={"ability": DEORBIT_ASSIGN}, decide=True, inputs=deorbit_assign_inputs,
    label="Deorbit Barrage: assign hits",
)
def deorbit_assign(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Saar przypisuje trafienia; jednostki z Sustain Damage - decyzja ich właściciela (3)."""
    if ctx.get("player") != player_id:
        return
    effect = _deorbit_pending(state, player_id)
    if effect is None:
        return
    planet = str(effect.data["planet"])
    targets = _ground_targets(state, planet)
    params = ctx.get("params") or {}
    chosen: dict[tuple[str, str], int] = {}
    for i in range(int(effect.data["hits"])):
        pick = str(params.get(f"hit{i + 1}") or "")
        owner, _, base_type = pick.partition("|")
        if base_type not in targets.get(owner, {}):
            raise ValueError("Assign each hit to a ground force on that planet.")
        chosen[(owner, base_type)] = chosen.get((owner, base_type), 0) + 1
    active_effects.remove_effect(state, effect.id)
    system = system_of_planet(state, planet)
    by_owner: dict[str, dict[str, int]] = {}
    for (owner, base_type), hits in sorted(chosen.items()):
        by_owner.setdefault(owner, {})[base_type] = hits
    for owner, hits_by_type in sorted(by_owner.items()):
        if any(_healthy_sustainers(state, owner, planet, bt) > 0 for bt in hits_by_type):
            active_effects.add_effect(
                state, SUSTAIN_KEY, Duration.TURN, owner=owner,
                data={"planet": planet, "hits": hits_by_type, "by": player_id},
            )
            faction_components.ability_used(state, player_id, DEORBIT_SUSTAIN, owner)
            continue
        for base_type, hits in sorted(hits_by_type.items()):
            _destroy_ground(state, system, planet, owner, base_type, hits)


def _healthy_sustainers(state: GameState, owner: str, planet: str, base_type: str) -> int:
    """Nieuszkodzone sztuki z Sustain Damage (wariant właściciela)."""
    registry = _registry()
    player = state.players.get(owner)
    unit = resolve_unit_variant(
        registry, player.faction if player else None, player.technologies if player else [],
        base_type,
    )
    if unit is None or not unit.sustain_damage:
        return 0
    system = system_of_planet(state, planet)
    total = system.planet_units.get(planet, {}).get(owner, {}).get(base_type, 0)
    return max(0, total - damaged_count(system, planet, owner, base_type))


def _destroy_ground(state: GameState, system: Any, planet: str, owner: str, base_type: str,
                    hits: int) -> None:
    """Trafienia bez Sustain Damage niszczą: najpierw uszkodzone sztuki (już po Sustain)."""
    count = min(hits, system.planet_units.get(planet, {}).get(owner, {}).get(base_type, 0))
    if count > 0:
        unit_ops.remove_units(state, system, planet, owner, base_type, count,
                              UnitCause.DESTROYED)


def _sustain_effect(state: GameState, owner: str) -> Any:
    return next(
        (e for e in state.active_effects if e.key == SUSTAIN_KEY and e.owner == owner), None
    )


def _target_decides(_state: GameState, _owner: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def deorbit_sustain_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Ile trafień anulować Sustain Damage - osobno dla każdego trafionego typu."""
    effect = _sustain_effect(state, decider)
    if effect is None:
        return []
    planet = str(effect.data["planet"])
    inputs: list[dict[str, Any]] = []
    for base_type, hits in sorted(effect.data["hits"].items()):
        most = min(int(hits), _healthy_sustainers(state, decider, planet, base_type))
        if most > 0:
            name = unit_name(state, registry, decider, base_type)
            inputs.append(oi.number(
                base_type, f"Use SUSTAIN DAMAGE: {name} ({hits} hit(s))", 0, most,
                hint="Each use cancels 1 Deorbit Barrage hit.",
            ))
    return inputs


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    where={"ability": DEORBIT_SUSTAIN}, decide=True, decider=_target_decides,
    inputs=deorbit_sustain_inputs, label="Deorbit Barrage: SUSTAIN DAMAGE",
)
def deorbit_sustain(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Właściciel trafionej jednostki decyduje o Sustain Damage (F_saar deorbit 3)."""
    if ctx.get("player") != player_id:
        return
    owner = str(ctx["target"])
    effect = _sustain_effect(state, owner)
    if effect is None:
        return
    planet = str(effect.data["planet"])
    hits_by_type = {str(bt): int(n) for bt, n in effect.data["hits"].items()}
    active_effects.remove_effect(state, effect.id)
    params = ctx.get("params") or {}
    system = system_of_planet(state, planet)
    for base_type, hits in sorted(hits_by_type.items()):
        healthy = _healthy_sustainers(state, owner, planet, base_type)
        sustain = int(params.get(base_type) or 0)
        if sustain < 0 or sustain > min(hits, healthy):
            raise ValueError("You cannot use SUSTAIN DAMAGE that many times.")
        if sustain:
            set_damaged(system, planet, owner, base_type,
                        damaged_count(system, planet, owner, base_type) + sustain)
            triggers.fire(state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject=owner,
                          ctx={"player": owner, "base_type": base_type, "count": sustain})
        _destroy_ground(state, system, planet, owner, base_type, hits - sustain)
