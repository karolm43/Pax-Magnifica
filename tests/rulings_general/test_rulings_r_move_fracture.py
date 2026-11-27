"""Movement, transport, capacity and The Fracture — rulings ``R_movement.md``, ``R_transport.md``,
``R_capacity.md`` and ``R_fracture.md`` point by point.

Central points: ``src/core/movement.py`` / ``movement_paths.py`` (tactical movement, RULES.md 32),
``src/core/direct_move.py`` (ability movement), ``src/core/retreat.py``, ``src/core/capacity.py`` +
``src/core/limits.py`` (RULES.md 39.6), ``src/core/fracture.py`` + ``src/core/expeditions.py``
(RULES.md 50). Statuses without a test: ``tests/rulings_status.json``.

Some rulings are already exercised by older scenario tests; those are re-run here under their
ruling id (imported with a private alias, so pytest does not collect them twice).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    board_graph,
    capacity,
    control,
    direct_move,
    expeditions,
    exploration,
    fracture,
    limits,
    movement,
    retreat,
    rules_hooks,
    space_cannon,
    tactical,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.dice import DIE_SIDES, next_rng
from src.core.game_state import (
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid, position_to_hex
from src.core.hooks import relics_actions
from src.core.hooks.factions import l1z1x, yin
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause
from tests.factions.test_cabal import (
    test_przelom_fracture_bez_rzutu_z_synergia as _cabal_breakthrough_without_roll,
)
from tests.factions.test_empyrean import (
    test_multiverse_shift_w_the_fracture as _multiverse_shift_in_fracture,
)
from tests.rulings import ruling
from tests.test_capacity import (
    test_combat_end_opens_capacity_for_winner as _combat_end_capacity,
)
from tests.test_invasion import (
    test_commit_moves_ground_forces_from_space_to_planet as _commit_ground_forces,
)
from tests.test_move_batch import (
    test_ships_arriving_with_the_plan_cannot_move_again as _batch_simultaneous,
)
from tests.test_thunders_edge import _claim_five, _pay, _specialty_systems
from tests.test_thunders_edge import _grid as _te_grid
from tests.test_thunders_edge import _state as _te_state

CARGO_PLANET = "pl"  # any planet id: units on it are only data for the movement code


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(None)
    yield
    board_graph.bind_grid_provider(previous)


# ===================================================================================== helpers


def _grid(*positions: str, anomalies: dict[str, set[str]] | None = None) -> HexGrid:
    """Real AsyncTI4 positions: ``301 - 201 - 101 - 000`` is a line (each touches the next)."""
    grid = HexGrid()
    for position in positions:
        grid.place_system(position, "19", anomalies=(anomalies or {}).get(position, set()))
    grid.build_edges()
    return grid


def _line() -> HexGrid:
    grid = _grid("000", "101", "201", "301")
    assert not grid.are_adjacent("201", "000") and not grid.are_adjacent("301", "101")
    return grid


def _state(
    units: dict[str, dict[str, dict[str, int]]],
    *,
    techs: tuple[str, ...] = (),
    planets: dict[str, dict[str, dict[str, int]]] | None = None,
    step: TacticalStep = TacticalStep.MOVEMENT,
) -> GameState:
    """p1 active in ``000``. ``units`` = ``{position: {player: {type: n}}}`` in space;
    ``planets`` = ``{position: {player: {type: n}}}`` on planet ``CARGO_PLANET``."""
    systems: dict[str, SystemState] = {}
    for position in {*units, *(planets or {}), "000"}:
        system = SystemState(position=position, system_id="19")
        for pid, by_type in units.get(position, {}).items():
            system.space_units[pid] = dict(by_type)
        for pid, by_type in (planets or {}).get(position, {}).items():
            system.planet_units.setdefault(CARGO_PLANET, {})[pid] = dict(by_type)
        systems[position] = system
    systems["000"].command_tokens = ["p1"]  # the active player activated the system
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=step,
        seating_order=["p1", "p2", "p3"],
        players={
            "p1": PlayerState(player_id="p1", color="red", technologies=list(techs)),
            "p2": PlayerState(player_id="p2", color="blue"),
            "p3": PlayerState(player_id="p3", color="green"),
        },
        systems=systems,
        rng_seed=1,
    )


def _value(registry: StaticDataRegistry, base_type: str, techs: tuple[str, ...] = ()) -> Any:
    unit = resolve_unit_variant(registry, None, list(techs), base_type)
    assert unit is not None
    return unit


def _space(state: GameState, position: str, pid: str = "p1") -> dict[str, int]:
    system = state.systems.get(position)
    return dict(system.space_units.get(pid, {})) if system is not None else {}


def _pickup(base_type: str, count: int, zone: str = "space",
            at: str | None = None) -> movement.CargoPickup:
    return movement.CargoPickup(base_type=base_type, count=count, from_zone=zone, from_position=at)


# ================================================================== R_movement: tactical moves


@ruling("R_movement/rules-reference/1")
def test_move_value_comes_from_the_players_unit_variant(registry: StaticDataRegistry) -> None:
    grid = _line()
    base, upgraded = _value(registry, "carrier"), _value(registry, "carrier", ("cv2",))
    assert base.move_value < upgraded.move_value == 2  # Carrier II card (assets)
    state = _state({"201": {"p1": {"carrier": 1}}})
    ok, reason = movement.can_move(state, grid, registry, "201", "carrier", "p1")
    assert not ok and "Range too short" in reason
    state.players["p1"].technologies = ["cv2"]
    assert movement.can_move(state, grid, registry, "201", "carrier", "p1") == (True, "")


@ruling("R_movement/rules-reference/2", "R_movement/rules-reference/2.1")
def test_any_number_of_ships_move_and_all_end_in_the_active_system(
    registry: StaticDataRegistry,
) -> None:
    grid = _line()
    state = _state({"101": {"p1": {"destroyer": 2, "cruiser": 1, "carrier": 1}}})
    moved = movement.move_fleet(
        state, grid, registry, "101", {"destroyer": 2, "cruiser": 1}, [], "p1"
    )
    assert _space(moved, "000") == {"destroyer": 2, "cruiser": 1}
    assert _space(moved, "101") == {"carrier": 1}  # a ship may also stay put
    with pytest.raises(ValueError, match="must end at the active system"):
        movement.move_fleet(state, grid, registry, "201", {"cruiser": 1}, [], "p1",
                            route=["201", "101"])


@ruling("R_movement/rules-reference/2.2", "R_movement/notes/5")
def test_other_players_ships_block_passage_fighters_alone_too(
    registry: StaticDataRegistry,
) -> None:
    grid = _line()
    for blocker in ({"destroyer": 1}, {"fighter": 1}):
        state = _state({"201": {"p1": {"cruiser": 1}}, "101": {"p2": dict(blocker)}})
        ok, reason = movement.can_move(state, grid, registry, "201", "cruiser", "p1")
        assert not ok and "No legal route" in reason, blocker
    # Fighter II (own move value) blocks just the same.
    state = _state({"201": {"p1": {"cruiser": 1}}, "101": {"p2": {"fighter": 1}}})
    state.players["p2"].technologies = ["ff2"]
    assert not movement.can_move(state, grid, registry, "201", "cruiser", "p1")[0]


@ruling("R_movement/notes/6")
def test_other_players_ground_forces_and_pds_do_not_block(registry: StaticDataRegistry) -> None:
    grid = _line()
    state = _state(
        {"201": {"p1": {"cruiser": 1}}},
        planets={"101": {"p2": {"infantry": 2, "mech": 1, "pds": 1}}},
    )
    assert movement.can_move(state, grid, registry, "201", "cruiser", "p1") == (True, "")


@ruling("R_movement/rules-reference/2.3", "R_movement/rules-reference/2.4")
def test_own_command_token_stops_departure_but_not_passage(registry: StaticDataRegistry) -> None:
    grid = _line()
    state = _state({"201": {"p1": {"cruiser": 1}}, "101": {}})
    state.systems["101"].command_tokens = ["p1"]
    assert movement.can_move(state, grid, registry, "201", "cruiser", "p1") == (True, "")
    state.systems["201"].command_tokens = ["p1"]
    ok, reason = movement.can_move(state, grid, registry, "201", "cruiser", "p1")
    assert not ok and "command token" in reason


@ruling("R_movement/rules-reference/2.5")
def test_ship_may_leave_the_active_system_and_come_back(registry: StaticDataRegistry) -> None:
    """Carrier II (move 2) leaves the active system, picks up infantry next door and returns."""
    grid = _line()
    state = _state(
        {"000": {"p1": {"carrier": 1}}, "101": {"p1": {"infantry": 2}}}, techs=("cv2",)
    )
    route = ["000", "101", "000"]
    moved = movement.move_fleet(
        state, grid, registry, "000", {"carrier": 1}, [_pickup("infantry", 2, at="101")], "p1",
        route=route,
    )
    assert _space(moved, "000") == {"carrier": 1, "infantry": 2}
    assert _space(moved, "101") == {}
    # Base carrier (move 1) cannot: the round trip enters 2 systems.
    state.players["p1"].technologies = []
    with pytest.raises(ValueError, match="Range too short"):
        movement.move_fleet(state, grid, registry, "000", {"carrier": 1}, [], "p1", route=route)


@ruling("R_movement/rules-reference/2.6")
def test_path_of_adjacent_systems_within_move_value(registry: StaticDataRegistry) -> None:
    grid = _line()
    cruiser = _value(registry, "cruiser").move_value
    state = _state({"201": {"p1": {"cruiser": 1}}, "301": {"p1": {"cruiser": 1}}})
    with pytest.raises(ValueError, match="not adjacent"):
        movement.move_fleet(state, grid, registry, "201", {"cruiser": 1}, [], "p1",
                            route=["201", "000"])
    assert cruiser == 2  # assets: a cruiser enters at most 2 systems
    ok, reason = movement.can_move(state, grid, registry, "301", "cruiser", "p1")
    assert not ok and "Range too short" in reason  # 301 -> 201 -> 101 -> 000 = 3 systems
    assert movement.can_move(state, grid, registry, "201", "cruiser", "p1") == (True, "")


@ruling("R_movement/rules-reference/3", "R_transport/rules-reference/2",
        "R_transport/rules-reference/1.1")
def test_capacity_ship_transports_cargo_into_the_space_area(registry: StaticDataRegistry) -> None:
    grid = _line()
    state = _state(
        {"101": {"p1": {"carrier": 1, "fighter": 2}}}, planets={"101": {"p1": {"infantry": 2}}}
    )
    moved = movement.move_fleet(
        state, grid, registry, "101", {"carrier": 1},
        [_pickup("fighter", 2), _pickup("infantry", 2, CARGO_PLANET)], "p1",
    )
    # Everything travels with the carrier and ends in the SPACE area (no landing while moving).
    assert _space(moved, "000") == {"carrier": 1, "fighter": 2, "infantry": 2}
    assert "p1" not in moved.systems["101"].planet_units.get(CARGO_PLANET, {})
    assert _space(moved, "101") == {}


@ruling("R_movement/rules-reference/4", "R_movement/notes/3", "R_transport/notes/5")
def test_fighter_ii_cannot_both_move_and_be_transported(registry: StaticDataRegistry) -> None:
    grid = _line()
    state = _state({"101": {"p1": {"carrier": 1, "fighter": 2}}}, techs=("ff2",))
    # The same fighters cannot fly on their own AND ride the carrier in one move.
    with pytest.raises(ValueError, match="Not enough fighter"):
        movement.move_fleet(state, grid, registry, "101", {"carrier": 1, "fighter": 2},
                            [_pickup("fighter", 2)], "p1")
    # …and ships flown in by one leg of the flight plan cannot move again (simultaneous moves).
    _batch_simultaneous(registry)


@ruling("R_movement/notes/4")
def test_ships_only_move_into_the_destination(registry: StaticDataRegistry) -> None:
    grid = _line()
    state = _state({"201": {"p1": {"cruiser": 1}}, "101": {}})
    moved = movement.move_fleet(state, grid, registry, "201", {"cruiser": 1}, [], "p1")
    assert _space(moved, "101") == {}  # moved THROUGH 101, never stopped there
    assert _space(moved, "000") == {"cruiser": 1}
    assert moved.last_move is not None
    assert moved.last_move.route == ["201", "101", "000"]


@ruling("R_movement/rules-reference/5")
def test_space_cannon_offense_follows_the_move_ships_step(registry: StaticDataRegistry) -> None:
    state = _state({"000": {"p1": {"cruiser": 1}}})
    assert tactical.next_step(state, registry).tactical_step is TacticalStep.SPACE_CANNON


@ruling("R_movement/rules-reference/6", "R_movement/notes/2", "R_transport/notes/4")
def test_ability_movement_ignores_move_value_and_own_command_tokens(
    registry: StaticDataRegistry,
) -> None:
    """Shared ability movement (Helix Protocol, Dark Space Navigation): no move value, no route,
    cargo may leave a system with the player's own command token."""
    state = _state({"301": {"p1": {"carrier": 1, "infantry": 2}}})
    state.systems["301"].command_tokens = ["p1"]
    grid = _line()
    board_graph.bind_grid_provider(lambda: grid)
    assert _value(registry, "carrier").move_value < 3  # 301 is 3 systems away from 000
    direct_move.apply_moves(
        state, registry, "p1", {"000": {"301": {"carrier": 1, "infantry": 2}}},
        fighters_free=False,
    )
    assert _space(state, "000") == {"carrier": 1, "infantry": 2}
    assert _space(state, "301") == {}


@ruling("R_movement/notes/8")
def test_anomaly_restrictions_apply_to_ability_movement(registry: StaticDataRegistry) -> None:
    supernova = next(s for s, d in registry.systems.items() if "SUPERNOVA" in d.anomalies)
    asteroids = next(s for s, d in registry.systems.items()
                     if set(d.anomalies) == {"ASTEROID_FIELD"})
    grid = HexGrid()
    for position, sid in (("000", "19"), ("101", supernova), ("102", asteroids)):
        grid.place_system(position, sid, anomalies=set(registry.systems[sid].anomalies),
                          hex_override=position_to_hex(position))
    grid.build_edges()
    state = _state({"000": {"p1": {"dreadnought": 1}}})
    state.players["p1"].faction = "l1z1x"
    for position, sid in (("101", supernova), ("102", asteroids)):
        state.systems[position] = SystemState(position=position, system_id=sid)
    assert movement.entry_blocked(grid, state, "101", "p1") is not None
    assert movement.entry_blocked(grid, state, "102", "p1") is not None
    board_graph.bind_grid_provider(lambda: grid)
    # Dark Space Navigation (L1Z1X hero): never into a supernova, asteroids only with Antimass.
    targets = l1z1x.hero_destinations(state, "p1")
    assert "101" not in targets and "102" not in targets and "000" in targets
    state.players["p1"].technologies = ["amd"]
    assert movement.entry_blocked(grid, state, "102", "p1") is None
    assert "102" in l1z1x.hero_destinations(state, "p1")


# ======================================================================= R_movement: retreats


def _retreat_state() -> GameState:
    state = _state(
        {"000": {"p1": {"cruiser": 1}, "p2": {"carrier": 1, "fighter": 2, "infantry": 1}},
         "101": {"p2": {"destroyer": 1}}, "201": {"p2": {"destroyer": 1}}},
        step=TacticalStep.SPACE_COMBAT,
    )
    state.players["p2"].technologies = ["gd"]  # Gravity Drive: +1 move (irrelevant for retreats)
    return state


@ruling("R_movement/notes/1")
def test_retreat_goes_only_to_an_adjacent_system(registry: StaticDataRegistry) -> None:
    grid = _line()
    assert retreat.retreat_destinations(_retreat_state(), grid, "000", "p2") == ["101"]


@ruling("R_movement/notes/2.1", "R_transport/notes/3")
def test_retreat_transports_units_out_of_the_active_system(registry: StaticDataRegistry) -> None:
    grid = _line()
    state = _retreat_state()
    state.systems["000"].command_tokens = ["p1", "p2"]  # the active system holds p2's token too
    result = retreat.retreat_in_place(state, grid, registry, "000", "p2", "101")
    assert result.moved.get("carrier") == 1
    assert _space(state, "101", "p2") == {"destroyer": 1, "carrier": 1, "fighter": 2,
                                          "infantry": 1}
    assert _space(state, "000", "p2") == {}


# ================================================================================ R_transport


@ruling("R_transport/rules-reference/1")
def test_pickup_from_start_systems_moved_through_and_the_active_system(
    registry: StaticDataRegistry,
) -> None:
    grid = _line()
    state = _state(
        {"201": {"p1": {"carrier": 1, "fighter": 1}}, "101": {"p1": {"fighter": 1}}},
        techs=("cv2",),
        planets={"000": {"p1": {"infantry": 1}}, "101": {"p1": {"infantry": 1}}},
    )
    cargo = [
        _pickup("fighter", 1),  # start system
        _pickup("fighter", 1, at="101"),  # system moved through (space)
        _pickup("infantry", 1, CARGO_PLANET, at="101"),  # … and its planet
        _pickup("infantry", 1, CARGO_PLANET, at="000"),  # planet of the active system
    ]
    moved = movement.move_fleet(state, grid, registry, "201", {"carrier": 1}, cargo, "p1",
                                route=["201", "101", "000"])
    assert _space(moved, "000") == {"carrier": 1, "fighter": 2, "infantry": 2}
    with pytest.raises(ValueError, match="not on the route"):
        movement.move_fleet(state, grid, registry, "201", {"carrier": 1},
                            [_pickup("fighter", 1, at="301")], "p1",
                            route=["201", "101", "000"])


@ruling("R_transport/rules-reference/1.2")
def test_cargo_of_a_ship_removed_by_a_gravity_rift_is_removed(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid("000", "101", anomalies={"101": {"GRAVITY_RIFT"}})
    base = _state({"101": {"p1": {"carrier": 1, "infantry": 2}}})
    for seed in range(1, 300):
        state = base.clone()
        state.rng_seed = seed
        moved = movement.move_fleet(state, grid, registry, "101", {"carrier": 1},
                                    [_pickup("infantry", 2)], "p1")
        if "carrier" not in _space(moved, "000"):
            break
    else:
        raise AssertionError("no seed removed the carrier")
    assert _space(moved, "000") == {}  # its infantry did not arrive…
    assert _space(moved, "101") == {}  # …and is not left behind either: off the board


@ruling("R_transport/rules-reference/3")
def test_no_pickup_from_own_command_token_systems_except_the_active_one(
    registry: StaticDataRegistry,
) -> None:
    grid = _line()
    state = _state(
        {"201": {"p1": {"carrier": 1}}, "101": {"p1": {"infantry": 1}}}, techs=("cv2",),
        planets={"000": {"p1": {"infantry": 1}}},
    )
    state.systems["101"].command_tokens = ["p1"]
    route = ["201", "101", "000"]
    with pytest.raises(ValueError, match="own command token"):
        movement.move_fleet(state, grid, registry, "201", {"carrier": 1},
                            [_pickup("infantry", 1, at="101")], "p1", route=route)
    # The active system always holds the token - its planets are still a legal pickup.
    moved = movement.move_fleet(state, grid, registry, "201", {"carrier": 1},
                                [_pickup("infantry", 1, CARGO_PLANET, at="000")], "p1",
                                route=route)
    assert _space(moved, "000") == {"carrier": 1, "infantry": 1}


@ruling("R_transport/rules-reference/4")
def test_ground_forces_land_during_the_invasion_step(registry: StaticDataRegistry) -> None:
    _commit_ground_forces(registry)


@ruling("R_transport/notes/2")
def test_pickup_from_an_active_system_planet_without_a_chosen_route(
    registry: StaticDataRegistry,
) -> None:
    """Fix: without an explicit route the active system's planets were refused as a pickup."""
    grid = _line()
    state = _state({"101": {"p1": {"carrier": 1}}}, planets={"000": {"p1": {"infantry": 2}}})
    moved = movement.move_fleet(state, grid, registry, "101", {"carrier": 1},
                                [_pickup("infantry", 2, CARGO_PLANET, at="000")], "p1")
    # The infantry is now in space, ready to invade another planet of the system.
    assert _space(moved, "000") == {"carrier": 1, "infantry": 2}
    assert "p1" not in moved.systems["000"].planet_units.get(CARGO_PLANET, {})


# ---------------------------------------------- the carrier example (R_transport + R_capacity)


def _example() -> GameState:
    """Carrier (capacity 4) with 4 fighters in 101; 8 infantry on the planet; nothing else."""
    return _state({"101": {"p1": {"carrier": 1, "fighter": 4}}},
                  planets={"101": {"p1": {"infantry": 8}}})


def _carrier_leaves(
    registry: StaticDataRegistry, fighters: int, infantry: int
) -> GameState:
    cargo = []
    if fighters:
        cargo.append(_pickup("fighter", fighters))
    if infantry:
        cargo.append(_pickup("infantry", infantry, CARGO_PLANET))
    moved = movement.move_fleet(_example(), _line(), registry, "101", {"carrier": 1}, cargo, "p1")
    # Limits are checked right away (``StateService`` calls this after every action).
    return limits.enforce_limits(moved, registry)


@ruling("R_transport/notes/1", "R_transport/notes/1.1", "R_transport/notes/1.1.1",
        "R_transport/notes/1.1.2", "R_transport/notes/1.1.3", "R_transport/notes/1.1.4",
        "R_transport/notes/1.1.5", "R_capacity/notes/2", "R_capacity/notes/2.1",
        "R_capacity/notes/2.1.1", "R_capacity/notes/2.1.2", "R_capacity/notes/2.1.3",
        "R_capacity/notes/2.1.4", "R_capacity/notes/2.1.5")
@pytest.mark.parametrize(
    ("fighters", "infantry", "arrived", "fighters_left"),
    [
        (4, 0, {"fighter": 4}, 0),  # 1.1.1: the four fighters
        (0, 4, {"infantry": 4}, 0),  # 1.1.2: four infantry, the fighters are removed
        (2, 2, {"fighter": 2, "infantry": 2}, 0),  # 1.1.3: two and two
        (0, 0, {}, 0),  # 1.1.4: nothing - all four fighters are removed
    ],
)
def test_carrier_example(
    registry: StaticDataRegistry,
    fighters: int,
    infantry: int,
    arrived: dict[str, int],
    fighters_left: int,
) -> None:
    assert _value(registry, "carrier").capacity_value == 4  # the example's carrier (assets)
    after = _carrier_leaves(registry, fighters, infantry)
    assert _space(after, "000") == {"carrier": 1, **arrived}
    assert _space(after, "101").get("fighter", 0) == fighters_left
    assert after.systems["101"].planet_units[CARGO_PLANET]["p1"] == {"infantry": 8 - infantry}
    assert after.pending_window is None  # the removal had no choice - done immediately


@ruling("R_transport/notes/1.1.5", "R_capacity/notes/2.1.5", "R_capacity/rules-reference/1")
def test_carrier_cannot_pick_up_more_than_its_capacity(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="Capacity exceeded"):
        _carrier_leaves(registry, 0, 8)
    with pytest.raises(ValueError, match="Capacity exceeded"):
        _carrier_leaves(registry, 4, 1)  # combined fighters + ground forces


# ================================================================================= R_capacity


@ruling("R_capacity/rules-reference/2")
def test_combined_capacity_of_all_ships_in_the_system(registry: StaticDataRegistry) -> None:
    cap = _value(registry, "carrier").capacity_value
    state = _state({"000": {"p1": {"carrier": 2, "cruiser": 1, "fighter": 2 * cap}}})
    report = capacity.capacity_report(state, registry, "000", "p1")
    assert report.general == 2 * cap and report.excess == 0
    state.systems["000"].space_units["p1"]["infantry"] = 1
    assert capacity.capacity_report(state, registry, "000", "p1").excess == 1


@ruling("R_capacity/rules-reference/3", "R_capacity/rules-reference/3.1",
        "R_capacity/notes/1.1")
def test_excess_is_removed_by_the_players_choice_before_space_cannon(
    registry: StaticDataRegistry,
) -> None:
    cap = _value(registry, "carrier").capacity_value
    state = _state({"000": {"p1": {"carrier": 1, "fighter": cap, "infantry": 1}}})
    checked = tactical.next_step(state, registry)
    window = checked.pending_window
    assert window is not None and window.window_type is WindowType.CAPACITY
    assert checked.tactical_step is TacticalStep.MOVEMENT  # Space Cannon waits
    for choice in ({"infantry": 1}, {"fighter": 1}):  # the player picks what goes
        resolved = capacity.resolve_capacity(checked, registry, "p1", choice)
        assert resolved.pending_window is None
        assert tactical.next_step(resolved, registry).tactical_step is TacticalStep.SPACE_CANNON


@ruling("R_capacity/rules-reference/3.2")
def test_ground_forces_on_planets_do_not_count(registry: StaticDataRegistry) -> None:
    state = _state({"000": {"p1": {"cruiser": 1}}},
                   planets={"000": {"p1": {"infantry": 6, "mech": 2}}})
    assert capacity.capacity_report(state, registry, "000", "p1").excess == 0


@ruling("R_capacity/rules-reference/3.3", "R_capacity/notes/1.3")
def test_no_capacity_during_combat_excess_removed_after(registry: StaticDataRegistry) -> None:
    state = _state({"000": {"p1": {"cruiser": 1, "fighter": 3}, "p2": {"destroyer": 1}}},
                   step=TacticalStep.SPACE_COMBAT)
    from src.core import battle

    started = battle.start_combat(state, _line(), registry)
    assert capacity.combat_in_progress(started, "000")
    assert capacity.players_with_excess(started, registry, "000") == []
    # A space combat won with fighters only - they are removed once the winner is known.
    _combat_end_capacity(registry)


@ruling("R_capacity/rules-reference/4")
def test_cargo_is_not_assigned_to_specific_ships(registry: StaticDataRegistry) -> None:
    cap = _value(registry, "carrier").capacity_value
    state = _state({"101": {"p1": {"carrier": 2, "fighter": 2 * cap}}})
    grid = _line()
    # Either carrier may take any fighters; the ones staying share the other carrier's capacity.
    moved = movement.move_fleet(state, grid, registry, "101", {"carrier": 1},
                                [_pickup("fighter", cap)], "p1")
    assert capacity.capacity_report(moved, registry, "101", "p1").excess == 0
    empty = movement.move_fleet(state, grid, registry, "101", {"carrier": 1}, [], "p1")
    assert capacity.capacity_report(empty, registry, "101", "p1").excess == cap


@ruling("R_capacity/notes/1")
def test_capacity_is_checked_immediately_outside_the_active_system(
    registry: StaticDataRegistry,
) -> None:
    state = _state({"000": {"p1": {"cruiser": 1}}, "101": {"p1": {"cruiser": 1, "fighter": 2}}})
    after = limits.enforce_limits(state, registry)
    assert _space(after, "101") == {"cruiser": 1}  # no choice: removed at once, no window


@ruling("R_capacity/notes/1.2")
def test_space_cannon_kills_the_carrier_excess_goes_before_the_next_roll(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid("000")
    base = _state({"000": {"p1": {"carrier": 1, "fighter": 2, "infantry": 2}}},
                  planets={"000": {"p2": {"pds": 1}, "p3": {"pds": 1}}},
                  step=TacticalStep.SPACE_CANNON)
    opened = space_cannon.open_offense(base, grid, registry)
    assert opened.pending_window is not None and opened.pending_window.queue == ["p2", "p3"]
    for seed in range(1, 200):
        candidate = opened.clone()
        candidate.rng_seed = seed
        fired = space_cannon.fire_offense(candidate, grid, registry, "p2", "p1")
        pending = space_cannon.pending_hits(fired)
        if pending is not None and pending.hits == 1:
            break
    else:
        raise AssertionError("no seed with exactly 1 hit")
    after = space_cannon.assign_hits(fired, "p1", {"carrier": 1}, registry=registry)
    window = after.pending_window
    # The capacity window interrupts Space Cannon before p3 rolls.
    assert window is not None and window.window_type is WindowType.CAPACITY
    assert window.queue == ["p1"]
    resolved = capacity.resolve_capacity(after, registry, "p1", {"fighter": 2, "infantry": 2})
    assert _space(resolved, "000") == {}
    resumed = resolved.pending_window
    assert resumed is not None and resumed.window_type is WindowType.SPACE_CANNON
    assert resumed.current_responder == "p3"  # only now does the next player roll


@ruling("R_capacity/notes/3")
def test_units_removed_for_capacity_are_not_destroyed(registry: StaticDataRegistry) -> None:
    state = _state({"000": {"p1": {"cruiser": 1, "infantry": 2}}}, techs=("inf2",))
    after = tactical.next_step(state, registry)  # the step gate removes the forced excess
    assert _space(after, "000") == {"cruiser": 1}
    roll = after.table_roll
    assert roll is None or roll.get("kind") != "infantry_ii"  # Infantry II never rolls
    # Contrast: a DESTROYED infantry does roll for Infantry II.
    destroyed = state.clone()
    unit_ops.remove_units(destroyed, destroyed.systems["000"], "space", "p1", "infantry", 1,
                          UnitCause.DESTROYED)
    assert destroyed.table_roll is not None and destroyed.table_roll["kind"] == "infantry_ii"


# ================================================================================= R_fracture


def _fracture(registry: StaticDataRegistry, breakthrough: str | None = None,
              ) -> tuple[GameState, HexGrid]:
    grid = _te_grid(registry)
    state = fracture.enter_play(_te_state(registry, grid), registry, grid, "p1", breakthrough)
    fracture.sync_grid(grid, state, registry)
    return state, grid


@ruling("R_fracture/notes/1", "R_fracture/notes/3", "R_fracture/notes/3.1",
        "R_fracture/notes/3.2", "R_fracture/notes/3.3")
def test_fracture_systems_lie_beyond_the_board_on_its_edge(registry: StaticDataRegistry) -> None:
    grid = _te_grid(registry)
    board = set(grid.positions)
    edge_before = {p for p in board if grid.is_edge(p)}
    state = fracture.enter_play(_te_state(registry, grid), registry, grid, "p1")
    fracture.sync_grid(grid, state, registry)
    frac = set(fracture.FRACTURE_POSITIONS)
    assert frac <= grid.positions and not frac & board  # additional systems
    # Placement has no mechanical effect: no geometric contact with the regular map.
    assert all(n in frac for pos in frac for n in grid.neighbors(pos)
               if grid.link_kind(pos, n) == "adjacent")
    assert all(grid.is_edge(pos) for pos in frac)  # every Fracture system is an edge system
    assert {p for p in board if grid.is_edge(p)} == edge_before  # the map's edge is unchanged


@ruling("R_fracture/notes/2", "R_fracture/notes/2.1")
def test_breakthrough_roll_of_1_or_10_brings_the_fracture(registry: StaticDataRegistry) -> None:
    assert fracture.roll_success(registry) == frozenset({1, DIE_SIDES}) and DIE_SIDES == 10
    grid = _te_grid(registry)
    base = _te_state(registry, grid)
    seen: dict[int, bool] = {}
    for seed in range(1, 400):
        probe = base.clone()
        probe.rng_seed = seed
        result = next_rng(probe).randint(1, DIE_SIDES)
        if result in seen:
            continue
        start = base.clone()
        start.rng_seed = seed
        rolled = fracture.breakthrough_roll(start, registry, grid, "p1", "arborecbt")
        seen[result] = rolled.fracture.in_play
        if len(seen) == DIE_SIDES:
            break
    assert seen == {r: r in (1, 10) for r in range(1, 11)}  # "0" face = 10 = success
    # Other effects bring it in too (no roll).
    assert fracture.enter_play(base, registry, grid, "p2").fracture.in_play


@ruling("R_fracture/notes/4")
def test_fracture_systems_are_no_targets_while_out_of_play(registry: StaticDataRegistry) -> None:
    grid = _te_grid(registry)
    state = _te_state(registry, grid)
    state.players["p1"].faction = "l1z1x"
    board_graph.bind_grid_provider(lambda: grid)
    frac = set(fracture.FRACTURE_POSITIONS)
    styx_planets = {"styx", "cocytus", "lethe", "phlegethon"}
    assert not frac & set(l1z1x.hero_destinations(state, "p1"))
    assert not styx_planets & {p for _, p in yin.dissemination_targets(state, registry)}
    entered = fracture.enter_play(state, registry, grid, "p1")
    fracture.sync_grid(grid, entered, registry)
    assert frac & set(l1z1x.hero_destinations(entered, "p1"))  # empty Fracture systems
    assert styx_planets & {p for _, p in yin.dissemination_targets(entered, registry)}


@ruling("R_fracture/notes/5")
def test_sixth_expedition_places_thunders_edge_before_the_final_ingress(
    registry: StaticDataRegistry,
) -> None:
    """Fix: the breakthrough roll of the sixth expedition used to put the final ingress on
    Mecatol Rex before Thunder's Edge existed."""
    grid = _te_grid(registry)
    for seed in range(1, 300):
        base = _te_state(registry, grid, seed=seed)
        base.players["p1"].took_action_this_turn = True
        state = _claim_five(base, grid, registry)
        done = expeditions.perform_expedition(state, registry, grid, "p1", "tradeGoods", _pay())
        if done.fracture.in_play:
            break
    else:
        raise AssertionError("no seed rolled the Fracture into play")
    assert done.expeditions.pending_placement is not None
    assert not done.systems["000"].ingress_token  # Mecatol does not get it
    assert fracture.extra_ingress_deferred(done)
    target = expeditions.thunders_edge_targets(done, registry, grid)[0]
    placed = expeditions.place_thunders_edge(done, registry, grid, "p1", target)
    assert placed.systems[target].ingress_token  # final ingress in the Thunder's Edge system
    assert not placed.systems["000"].ingress_token
    assert not fracture.extra_ingress_deferred(placed)


@ruling("R_fracture/notes/6")
def test_attachments_may_go_to_fracture_planets(registry: StaticDataRegistry) -> None:
    state, _grid_ = _fracture(registry)
    control.set_planet_control(state, "frac1", "cocytus", "p1", registry)
    assert "cocytus" in relics_actions._nanoforge_planets(state, registry, "p1")
    exploration.attach_to_planet(state, "cocytus", "nanoforge")
    assert "nanoforge" in state.planet_attachments.get("cocytus", [])


@ruling("R_fracture/notes/7")
def test_neutral_units_are_placed_from_the_tile_backs(registry: StaticDataRegistry) -> None:
    state, _grid_ = _fracture(registry)
    for position, tile in zip(fracture.FRACTURE_POSITIONS, fracture.FRACTURE_TILE_IDS,
                              strict=True):
        system = state.systems[position]
        for zone, units in fracture.NEUTRAL_SETUP.get(tile, {}).items():
            placed = (system.space_units if zone == "space"
                      else system.planet_units[zone]).get(NEUTRAL_PLAYER_ID)
            assert placed == units, (tile, zone)


@ruling("R_fracture/notes/8")
def test_no_frontier_tokens_when_the_fracture_enters(registry: StaticDataRegistry) -> None:
    state, _grid_ = _fracture(registry)
    assert not any(state.systems[p].frontier_token for p in fracture.FRACTURE_POSITIONS)
    _multiverse_shift_in_fracture(registry)  # Multiverse Shift does place them there


@ruling("R_fracture/notes/9", "R_fracture/notes/9.1")
def test_ingress_and_egress_are_adjacent_both_ways(registry: StaticDataRegistry) -> None:
    state, grid = _fracture(registry)
    far = next(p for p in sorted(grid.positions)
               if p not in fracture.FRACTURE_POSITIONS and p != "000"
               and not grid.are_adjacent(p, "000") and grid.distance(p, "000") >= 3)
    state.systems[far].ingress_token = True
    fracture.sync_grid(grid, state, registry)
    egress = [p for p in fracture.FRACTURE_POSITIONS
              if registry.systems[grid.system_id_at(p)].has_egress]
    assert len(egress) >= 2
    for e in egress:
        assert grid.are_adjacent("000", e) and grid.are_adjacent(far, e)
    assert not grid.are_adjacent(egress[0], egress[1])  # egress - egress: no
    assert not grid.are_adjacent("000", far)  # ingress - ingress: no
    # A cruiser (move 2) goes ingress -> egress -> ingress.
    state.active_system = "000"
    state.systems[far].space_units["p1"] = {"cruiser": 1}
    route = [far, egress[0], "000"]
    ok, reason = movement.can_move(state, grid, registry, far, "cruiser", "p1", route=route)
    assert ok, reason


@ruling("R_fracture/notes/10", "R_fracture/notes/10.1")
def test_synergy_ingress_three_per_color_or_as_many_as_possible(
    registry: StaticDataRegistry,
) -> None:
    state, grid = _fracture(registry, "arborecbt")
    colors = [c for c in registry.breakthroughs["arborecbt"].synergy]
    assert {c.color: c.remaining for c in state.fracture.pending} == dict.fromkeys(colors, 3)
    # Only one system per specialty colour: as many as possible, placed without a choice.
    few = HexGrid()
    few.place_system("000", "18", hex_override=position_to_hex("000"))
    by_color: dict[str, str] = {}
    for sid in _specialty_systems(registry):
        for planet in registry.systems[sid].planets:
            info = registry.planets.get(planet)
            for color in (info.tech_specialties or []) if info is not None else []:
                by_color.setdefault(color.upper(), sid)
    for index, sid in enumerate(sorted(set(by_color.values()))):
        position = f"10{index + 1}"
        few.place_system(position, sid, hex_override=position_to_hex(position))
    few.build_edges()
    entered = fracture.enter_play(_te_state(registry, few), registry, few, "p1", "arborecbt")
    assert entered.fracture.pending == []
    for color in colors:
        assert all(entered.systems[p].ingress_token
                   for p in few.positions
                   if p != "000" and by_color.get(color) == few.system_id_at(p))


@ruling("R_fracture/notes/10.2")
def test_alraith_ix_ianovar_places_ingress_as_if_rolled(registry: StaticDataRegistry) -> None:
    _cabal_breakthrough_without_roll(registry)


@ruling("R_fracture/notes/11")
def test_no_synergy_one_ingress_per_colour(registry: StaticDataRegistry) -> None:
    assert [c for c in registry.breakthroughs["nekrobt"].synergy if c != "NONE"] == []
    for breakthrough in (None, "nekrobt"):
        state, _grid_ = _fracture(registry, breakthrough)
        assert {c.color: c.remaining for c in state.fracture.pending} == dict.fromkeys(
            ("BIOTIC", "CYBERNETIC", "PROPULSION", "WARFARE"), 1
        )


@ruling("R_fracture/notes/12", "R_fracture/notes/14")
def test_one_ingress_per_system(registry: StaticDataRegistry) -> None:
    two = next(
        sid for sid in _specialty_systems(registry)
        if sum(1 for p in registry.systems[sid].planets
               if (info := registry.planets.get(p)) is not None and info.tech_specialties) >= 2
    )
    grid = HexGrid()
    grid.place_system("000", "18", hex_override=position_to_hex("000"))
    grid.place_system("101", two, hex_override=position_to_hex("101"))
    grid.build_edges()
    state = _te_state(registry, grid)
    colors = {
        s.upper() for p in registry.systems[two].planets
        if (info := registry.planets.get(p)) is not None for s in (info.tech_specialties or [])
    }
    for color in colors:
        assert fracture.ingress_candidates(state, registry, grid, color) == ["101"]
    state.systems["101"].ingress_token = True
    for color in colors:  # a system with an ingress is never a candidate again
        assert fracture.ingress_candidates(state, registry, grid, color) == []


@ruling("R_fracture/notes/13")
def test_final_ingress_on_thunders_edge_or_mecatol_rex(registry: StaticDataRegistry) -> None:
    state, _grid_ = _fracture(registry)
    assert state.systems["000"].ingress_token  # no Thunder's Edge: Mecatol Rex
    grid = _te_grid(registry)
    base = _te_state(registry, grid)
    target = expeditions.thunders_edge_targets(base, registry, grid)[0]
    base.expeditions.thunders_edge_position = target
    entered = fracture.enter_play(base, registry, grid, "p1")
    assert entered.systems[target].ingress_token and not entered.systems["000"].ingress_token


@ruling("R_fracture/notes/15")
def test_first_control_of_a_fracture_planet_draws_a_relic(registry: StaticDataRegistry) -> None:
    state, _grid_ = _fracture(registry)
    control.set_planet_control(state, "frac1", "cocytus", "p1", registry)
    assert len(state.players["p1"].relics) == 1
    control.set_planet_control(state, "frac1", "cocytus", "p2", registry)  # had a controller
    assert state.players["p2"].relics == []
