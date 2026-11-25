"""Action card rulings — ``docs/rules_tirules/C_action_cards.md`` (cards not covered elsewhere).

Each test tags the points it checks with ``@ruling(...)`` (guard ``tests/test_ruling_coverage.py``).
Basic card behaviour lives in ``tests/test_reactions_*.py``; statuses without a test are in
``tests/rulings_status.json``.
"""

from __future__ import annotations

import pytest

from src.core import action_cards, agenda_phase, board_graph, invasion
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.invasion import BombardAssignment
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_reactions_agenda import DIRECTIVE, LAW, _hand, _state
from tests.test_reactions_combat import (
    _assign_state,
    _can,
)
from tests.test_reactions_combat import _bound_grid as _bound_grid  # noqa: F401 - autouse fixture
from tests.test_reactions_combat import _play as _play_combat
from tests.test_reactions_combat import grid as grid  # noqa: F401 - fixture
from tests.test_reactions_invasion import _PL1, _PL2, _begin, _seek
from tests.test_reactions_invasion import _grid as _invasion_grid
from tests.test_reactions_invasion import _hand as _invasion_hand
from tests.test_reactions_invasion import _play as _play_invasion
from tests.test_reactions_invasion import _state as _invasion_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


# ============================================================================ Insider Information


@ruling("C_action_cards/insider-information/2")
def test_insider_looks_past_the_covert_legislation_draw(registry: StaticDataRegistry) -> None:
    """Covert Legislation resolves first: the speaker's hidden draw is already off the deck."""
    deck = [agenda_phase.COVERT_LEGISLATION, LAW, DIRECTIVE, LAW, DIRECTIVE, LAW]
    state = _state(registry, deck)
    _hand(state, "p1", "insider")
    state = agenda_phase.reveal_agenda(state, registry, "p2")
    assert state.agenda is not None and state.agenda.covert_card == LAW  # the speaker's draw
    new, implemented = action_cards.play_action_card(state, registry, "p1", "insider", {})
    assert implemented
    assert new.players["p1"].private.agenda_peek == [DIRECTIVE, LAW, DIRECTIVE]


# ============================================================================ Scramble Frequency


@ruling("C_action_cards/scramble-frequency/1")
def test_scramble_rerolls_dice_against_every_planet(registry: StaticDataRegistry) -> None:
    grid = _invasion_grid()
    board_graph.bind_grid_provider(lambda: grid)
    try:

        def make(seed: int) -> GameState:
            state = _invasion_state(
                {"p1": {"dreadnought": 4, "infantry": 1}},
                {_PL1: {"p2": {"infantry": 5}}, _PL2: {"p2": {"infantry": 5}}},
                {_PL1: "p2", _PL2: "p2"},
                seed=seed,
            )
            _invasion_hand(state, "p2", "scramble")
            started = _begin(state, grid, registry)
            plan = [BombardAssignment("dreadnought", _PL1, 2),
                    BombardAssignment("dreadnought", _PL2, 2)]
            return invasion.bombard(started, grid, registry, plan)

        rolled = _seek(
            make,
            lambda st: bool(st.invasion and {_PL1, _PL2} <= set(st.invasion.bombard_pending)),
        )
        new = _play_invasion(rolled, registry, "p2", "scramble")
    finally:
        board_graph.bind_grid_provider(None)
    assert new.invasion is not None
    by_planet = {entry["planet"]: entry for entry in new.invasion.log if "rerolled" in entry}
    assert set(by_planet) == {_PL1, _PL2}  # one use rerolled the dice of both planets
    assert all(entry["rerolled"] is True for entry in by_planet.values())


# ============================================================================ Shields Holding


@ruling("C_action_cards/shields-holding/2")
def test_each_player_may_play_shields_holding_in_the_same_window(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _assign_state(grid, registry, ["sh1"], ["sh2"])
    combat = state.active_combat
    assert combat is not None
    before = dict(combat.pending_hits)
    assert _can(state, registry, "p1", "sh1") and _can(state, registry, "p2", "sh2")
    after_p2 = _play_combat(state, registry, "p2", "sh2", {"count": 1})
    assert _can(after_p2, registry, "p1", "sh1")  # p2's card does not use up p1's
    after_both = _play_combat(after_p2, registry, "p1", "sh1", {"count": 1})
    assert after_both.active_combat is not None
    pending = after_both.active_combat.pending_hits
    assert pending["p1"] == before["p1"] - 1 and pending["p2"] == before["p2"] - 1
