"""Coexistence (block I4): ``core/coexistence.py`` + invasion (RULES.md 40.1 I7b, R_coexistence)."""

from __future__ import annotations

import pytest

from src.core import battle, coexistence, invasion
from src.core.game_state import GameState, InvasionPhase, PlayerState
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_invasion import _PL1
from tests.test_invasion import _grid as inv_grid
from tests.test_invasion import _state as inv_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _three_players() -> GameState:
    """p1 invades; p2 controls the planet; p3 coexists on it by choice (with a PDS)."""
    state = inv_state(
        {"p1": {"carrier": 1, "infantry": 2}},
        {_PL1: {"p2": {"infantry": 1}, "p3": {"infantry": 1, "pds": 1}}},
        {_PL1: "p2"},
    )
    state.players["p3"] = PlayerState(player_id="p3", color="p3")
    state.seating_order = ["p1", "p2", "p3"]
    coexistence.choose(state, "000", _PL1, "p3")
    return state


def test_choose_marks_only_a_non_controller() -> None:
    state = _three_players()
    coexistence.choose(state, "000", _PL1, "p2")  # the controller is not marked
    assert coexistence.peaceful(state, "000", _PL1) == {"p3"}
    assert coexistence.coexisting_players(state, "000", _PL1) == ["p3"]
    assert coexistence.partners(state, "p3") == {"p2"}
    assert coexistence.partners(state, "p2") == {"p3"}


@ruling("R_coexistence/notes/14", "R_coexistence/notes/15")
def test_invader_fights_the_controller_and_the_coexisting_player_remains(
    registry: StaticDataRegistry,
) -> None:
    grid = inv_grid()
    state = invasion.begin_invasion(_three_players(), grid, registry)
    assert state.invasion is not None and state.invasion.phase is InvasionPhase.COMMIT
    state = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 2}})
    assert invasion.combat_planets(state, registry) == [_PL1]
    state = invasion.advance(state, grid, registry)  # Space Cannon Defense (none) -> combat
    started = battle.start_combat(state, grid, registry, _PL1)
    assert started.active_combat is not None and started.active_combat.defender == "p2"
    # p1 wins: p2's units are gone; Establish Control keeps p3 (and its PDS) coexisting.
    won = state.clone()
    del won.systems["000"].planet_units[_PL1]["p2"]
    assert won.invasion is not None
    won.invasion.combat_results = {_PL1: {"attacker": "p1", "defender": "p2", "winner": "p1"}}
    invasion._establish_control(won, registry)
    assert won.systems["000"].planet_owners[_PL1] == "p1"
    assert won.systems["000"].planet_units[_PL1]["p3"] == {"infantry": 1, "pds": 1}
    assert coexistence.peaceful(won, "000", _PL1) == {"p3"}


@ruling("R_coexistence/notes/12")
def test_controller_committing_forces_starts_combat_against_coexisting_player() -> None:
    state = _three_players()
    calm = coexistence.fighting(state, "000", _PL1, "p2", ["p3"], committed=False)
    assert calm == []  # the controller does not have to fight
    assert coexistence.fighting(state, "000", _PL1, "p2", ["p3"], committed=True) == ["p3"]


@ruling("R_coexistence/notes/13")
def test_coexisting_player_starts_combat_by_committing() -> None:
    state = _three_players()
    assert coexistence.fighting(state, "000", _PL1, "p3", ["p2"], committed=False) == []
    assert coexistence.fighting(state, "000", _PL1, "p3", ["p2"], committed=True) == ["p2"]
