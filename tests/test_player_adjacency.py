"""Player-dependent adjacency (RULES.md 61.7, block I3) and the map-adjacency rulings it builds on.

Layer 3 (hook ``adjacency.extra_for_player``) is read in ONE place (``board_graph``) and used by
movement, retreats, Space Cannon (offense + range lens), neighbors and transactions. The tests
register a temporary Quantum-Entanglement-like hook ("alpha and beta systems are adjacent for
me") on a test faction - the real Creuss hook comes in block B15.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from src.core import board_graph, neighbors, retreat, rules_hooks, space_cannon, transaction
from src.core.game_state import GameState, PlayerState, SystemState
from src.core.hex_grid import Hex, HexGrid
from src.core.movement_paths import shortest_legal_path
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import HookKind, HookSource
from tests.rulings import ruling

_FACTION = "test_entangled"
_ALPHA = "301"  # Lodor (26) - alpha wormhole
_BETA = "310"  # Quann (25) - beta wormhole, far from 301
_MID = "000"  # Mecatol Rex (18)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def entangled() -> Iterator[None]:
    """Temporary layer-3 hook: alpha and beta systems are adjacent for ``_FACTION`` only."""
    with rules_hooks.temporary_hooks():

        @rules_hooks.register(
            rules_hooks.POINT_ADJACENCY_EXTRA_FOR_PLAYER,
            HookSource(rules_hooks.SOURCE_FACTION, _FACTION),
            HookKind.FORBID,
        )
        def _alpha_beta(_s: GameState, _p: str, ctx: Mapping[str, Any]) -> set[str]:
            grid = ctx["grid"]
            linked = grid.wormhole_positions("ALPHA") | grid.wormhole_positions("BETA")
            position = str(ctx["position"])
            # Includes ``position`` itself on purpose: board_graph must drop it.
            return set(linked) if position in linked else set()

        yield


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system(_MID, "18", hex_override=Hex(0, 0, 0))
    grid.place_system(_ALPHA, "26", wormholes=["ALPHA"], hex_override=Hex(3, -3, 0))
    grid.place_system(_BETA, "25", wormholes=["BETA"], hex_override=Hex(-3, 3, 0))
    grid.build_edges()
    return grid


def _state(faction: str = _FACTION) -> GameState:
    return GameState(
        players={
            "p1": PlayerState(player_id="p1", color="red", faction=faction),
            "p2": PlayerState(player_id="p2", color="blue", faction="sol"),
        },
        systems={
            _MID: SystemState(position=_MID, system_id="18"),
            _ALPHA: SystemState(position=_ALPHA, system_id="26"),
            _BETA: SystemState(position=_BETA, system_id="25"),
        },
    )


# ======================================================================= central point (layer 3)


def test_without_hook_player_adjacency_is_the_map_graph() -> None:
    state, grid = _state(), _grid()
    assert board_graph.extra_adjacent_for_player(state, "p1", _ALPHA, grid) == frozenset()
    assert board_graph.neighbors_for_player(state, grid, "p1", _ALPHA) == grid.neighbors(_ALPHA)
    assert not board_graph.are_adjacent_for_player(state, grid, "p1", _ALPHA, _BETA)


@pytest.mark.usefixtures("entangled")
def test_hook_adds_adjacency_only_for_its_owner() -> None:
    state, grid = _state(), _grid()
    assert board_graph.extra_adjacent_for_player(state, "p1", _ALPHA, grid) == {_BETA}
    assert board_graph.extra_adjacent_for_player(state, "p1", _BETA, grid) == {_ALPHA}
    assert _BETA in board_graph.neighbors_for_player(state, grid, "p1", _ALPHA)
    assert board_graph.are_adjacent_for_player(state, grid, "p1", _BETA, _ALPHA)
    # Other players see the plain map; the map graph itself is untouched.
    assert board_graph.extra_adjacent_for_player(state, "p2", _ALPHA, grid) == frozenset()
    assert not board_graph.are_adjacent_for_player(state, grid, "p2", _ALPHA, _BETA)
    assert not grid.are_adjacent(_ALPHA, _BETA)
    # Unknown player -> no hook lookup at all.
    assert board_graph.extra_adjacent_for_player(state, "ghost", _ALPHA, grid) == frozenset()


@ruling("R_adjacency/rules-reference/2.1", "R_wormholes/notes/3")
@pytest.mark.usefixtures("entangled")
def test_a_system_is_not_adjacent_to_itself_even_through_player_adjacency() -> None:
    state, grid = _state(), _grid()
    assert _ALPHA not in board_graph.extra_adjacent_for_player(state, "p1", _ALPHA, grid)
    assert _ALPHA not in board_graph.neighbors_for_player(state, grid, "p1", _ALPHA)
    assert not board_graph.are_adjacent_for_player(state, grid, "p1", _ALPHA, _ALPHA)
    twin = HexGrid()  # two wormholes of the same type in one system
    twin.place_system(_ALPHA, "26", wormholes=["ALPHA", "ALPHA"], hex_override=Hex(0, 0, 0))
    twin.build_edges()
    assert not twin.are_adjacent(_ALPHA, _ALPHA)


@pytest.mark.usefixtures("entangled")
def test_bound_grid_is_used_when_none_is_given() -> None:
    state, grid = _state(), _grid()
    board_graph.bind_grid_provider(lambda: grid)
    try:
        assert board_graph.extra_adjacent_for_player(state, "p1", _ALPHA) == {_BETA}
    finally:
        board_graph.bind_grid_provider(None)


# ========================================================================= movement and retreat


def _path(state: GameState, grid: HexGrid, player: str) -> list[str] | None:
    return shortest_legal_path(grid, state, _ALPHA, _BETA, player, can_enter_asteroids=False)


def test_movement_without_hook_has_no_route() -> None:
    assert _path(_state(), _grid(), "p1") is None


@pytest.mark.usefixtures("entangled")
def test_movement_uses_the_moving_players_adjacency() -> None:
    state, grid = _state(), _grid()
    assert _path(state, grid, "p1") == [_ALPHA, _BETA]
    assert _path(state, grid, "p2") is None


def test_retreat_without_hook_stays_on_the_map_graph() -> None:
    state, grid = _state(), _grid()
    state.systems[_BETA].planet_owners = {"quann": "p1"}
    assert _BETA not in retreat.retreat_destinations(state, grid, _ALPHA, "p1")


@pytest.mark.usefixtures("entangled")
def test_retreat_uses_the_retreating_players_adjacency() -> None:
    state, grid = _state(), _grid()
    state.systems[_BETA].planet_owners = {"quann": "p1"}
    assert _BETA in retreat.retreat_destinations(state, grid, _ALPHA, "p1")
    state.systems[_BETA].planet_owners = {"quann": "p2"}
    assert _BETA not in retreat.retreat_destinations(state, grid, _ALPHA, "p2")


# =================================================================================== Space Cannon


def _cannon_state(owner: str) -> GameState:
    """``owner`` has a PDS (PDS II: Deep Space Cannon) on Quann; the beta system's enemy is the
    other player with a ship in the active alpha system."""
    state = _state()
    other = "p2" if owner == "p1" else "p1"
    state.players[owner].technologies = ["pds2"]
    state.systems[_BETA].planet_units = {"quann": {owner: {"pds": 1}}}
    state.systems[_ALPHA].space_units = {other: {"cruiser": 1}}
    state.active_system = _ALPHA
    state.active_player_id = other
    return state


def test_deep_space_cannon_without_hook_does_not_reach(registry: StaticDataRegistry) -> None:
    state, grid = _cannon_state("p1"), _grid()
    assert space_cannon.offense_shooters(state, grid, registry, "p1") == []


@pytest.mark.usefixtures("entangled")
def test_deep_space_cannon_uses_the_shooters_adjacency(registry: StaticDataRegistry) -> None:
    grid = _grid()
    own = _cannon_state("p1")
    shooters = space_cannon.offense_shooters(own, grid, registry, "p1")
    assert shooters and all(s.remote and s.position == _BETA for s in shooters)
    assert space_cannon.coverage(own, grid, registry)[_ALPHA]["p1"][0] == 1
    # The other player cannot use p1's adjacency against p1's units (F_creuss QE ruling).
    foreign = _cannon_state("p2")
    assert space_cannon.offense_shooters(foreign, grid, registry, "p2") == []
    assert "p2" not in space_cannon.coverage(foreign, grid, registry).get(_ALPHA, {})


@ruling("R_wormholes/rules-reference/2")
def test_pds_upgrade_fires_space_cannon_through_wormholes(registry: StaticDataRegistry) -> None:
    grid = HexGrid()
    grid.place_system(_ALPHA, "26", wormholes=["ALPHA"], hex_override=Hex(3, -3, 0))
    grid.place_system(_BETA, "26", wormholes=["ALPHA"], hex_override=Hex(-3, 3, 0))
    grid.build_edges()
    state = _cannon_state("p2")
    state.players["p2"].faction = "sol"
    state.systems[_BETA] = SystemState(
        position=_BETA, system_id="26", planet_units={"lodor": {"p2": {"pds": 1}}}
    )
    assert grid.are_adjacent(_ALPHA, _BETA)
    shooters = space_cannon.offense_shooters(state, grid, registry, "p2")
    assert shooters and all(s.remote for s in shooters)
    state.players["p2"].technologies = []  # PDS I: no Deep Space Cannon -> no shot through
    assert space_cannon.offense_shooters(state, grid, registry, "p2") == []


@ruling("R_adjacency/rules-reference/3")
def test_a_planet_is_adjacent_to_its_own_system(registry: StaticDataRegistry) -> None:
    """A PDS on a planet uses SPACE CANNON against its own system without Deep Space Cannon."""
    state = _cannon_state("p2")
    state.players["p2"].technologies = []
    state.systems[_ALPHA].planet_units = {"lodor": {"p2": {"pds": 1}}}
    shooters = space_cannon.offense_shooters(state, _grid(), registry, "p2")
    assert shooters and all(not s.remote and s.position == _ALPHA for s in shooters)


# ================================================================== neighbors and transactions


def _split_state() -> GameState:
    state = _state()
    state.systems[_ALPHA].space_units = {"p1": {"carrier": 1}}
    state.systems[_BETA].space_units = {"p2": {"carrier": 1}}
    return state


def test_neighbors_without_hook_need_map_adjacency() -> None:
    state, grid = _split_state(), _grid()
    assert neighbors.neighbors_by_player(state, grid) == {"p1": set(), "p2": set()}
    assert not transaction.reachable(state, grid, "p1", "p2")


@pytest.mark.usefixtures("entangled")
def test_player_adjacency_makes_both_players_neighbors() -> None:
    """F_creuss: "the Creuss player and that player are neighbors" - symmetric, both ways."""
    grid = _grid()
    for state in (_split_state(), _swap(_split_state())):
        assert neighbors.neighbors_of("p1", state, grid) == {"p2"}
        assert neighbors.neighbors_of("p2", state, grid) == {"p1"}
        assert transaction.reachable(state, grid, "p2", "p1")


def _swap(state: GameState) -> GameState:
    """The hook owner sits in the beta system, the other player in the alpha one."""
    state.systems[_ALPHA].space_units = {"p2": {"carrier": 1}}
    state.systems[_BETA].space_units = {"p1": {"carrier": 1}}
    return state


@pytest.mark.usefixtures("entangled")
def test_player_adjacency_of_a_third_player_does_not_link_others() -> None:
    state, grid = _split_state(), _grid()
    state.players["p3"] = PlayerState(player_id="p3", color="green", faction=_FACTION)
    state.players["p1"].faction = "sol"
    assert neighbors.neighbors_by_player(state, grid) == {"p1": set(), "p2": set(), "p3": set()}


@ruling("R_adjacency/rules-reference/1", "R_wormholes/rules-reference/3")
def test_matching_wormholes_are_adjacent_and_make_neighbors() -> None:
    grid = HexGrid()
    grid.place_system(_ALPHA, "26", wormholes=["ALPHA"], hex_override=Hex(3, -3, 0))
    grid.place_system(_BETA, "26", wormholes=["ALPHA"], hex_override=Hex(-3, 3, 0))
    grid.place_system(_MID, "25", wormholes=["BETA"], hex_override=Hex(0, 6, -6))
    grid.build_edges()
    assert grid.are_adjacent(_ALPHA, _BETA)
    assert not grid.are_adjacent(_ALPHA, _MID)  # alpha and beta do not match
    state = _split_state()
    assert neighbors.neighbors_of("p1", state, grid) == {"p2"}
    assert transaction.reachable(state, grid, "p1", "p2")
