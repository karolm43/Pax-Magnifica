"""Bluff auto-pass and "unless something changes" pre-passes - RULES.md 54.13."""

from __future__ import annotations

import pytest

from src.core import reaction_pause, reaction_prefs, reaction_window, visibility
from src.core.game_state import GameState, Phase, PlayerState
from src.core.registry import StaticDataRegistry
from tests.test_reactions_agenda import DIRECTIVE, LAW, _revealed


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _agenda(registry: StaticDataRegistry) -> GameState:
    """Revealed agenda: p1 holds a rider (asked), p3 holds a card that does not fit (auto-pass)."""
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["lead_rider"], "p3": ["salvage"]})
    state.quick_reaction_windows = True
    state.reaction_jitter_seconds = 8.0
    state.rng_seed = 42
    return state


# --- defaults -------------------------------------------------------------------------------------


def test_default_window_is_20_seconds() -> None:
    assert reaction_window.DEFAULT_SECONDS == 20
    assert GameState().reaction_window_seconds == 20
    assert reaction_window.configure(GameState(), 60).reaction_window_seconds == 60


# --- bluff auto-pass -----------------------------------------------------------------------------


def test_bluff_offset_is_private_random_and_never_zero() -> None:
    state = GameState(quick_reaction_windows=True, reaction_jitter_seconds=8.0, rng_seed=7)
    offsets = {reaction_window.bluff_offset(state, f"w{i}", "p1") for i in range(40)}
    assert len(offsets) > 30  # random per window
    assert all(8.0 * reaction_window.BLUFF_MIN_FRACTION <= t <= 8.0 for t in offsets)
    # Deterministic for (seed, window, player): Undo / replay give the same moment.
    assert reaction_window.bluff_offset(state, "w1", "p1") == reaction_window.bluff_offset(
        state, "w1", "p1"
    )
    other_seed = state.model_copy(update={"rng_seed": 8})
    assert reaction_window.bluff_offset(other_seed, "w1", "p1") != reaction_window.bluff_offset(
        state, "w1", "p1"
    )


def test_auto_passer_lands_at_a_scheduled_moment(registry: StaticDataRegistry) -> None:
    state = _agenda(registry)
    reaction_pause.sync(state, registry, now=100.0)
    pause = state.reaction_pause
    assert pause is not None and pause.passed == ["p3"]
    assert set(pause.auto_pass_at) == {"p3"}
    assert 2.0 <= pause.auto_pass_at["p3"] <= 8.0
    assert pause.closes_after is None  # p1 still decides
    state = reaction_pause.pass_pause(state, "p1")
    pause = state.reaction_pause
    assert pause is not None  # everyone passed - but not at 0.0 s
    assert pause.closes_after == pause.auto_pass_at["p3"]
    assert pause.seconds == reaction_window.window_seconds(state)  # public length unchanged
    assert not reaction_pause.expired(pause, 100.0 + 1.0)
    assert reaction_pause.expired(pause, 100.0 + pause.closes_after)


def test_without_quick_windows_nothing_is_scheduled(registry: StaticDataRegistry) -> None:
    state = _agenda(registry)
    state.quick_reaction_windows = False
    reaction_pause.sync(state, registry, now=100.0)
    pause = state.reaction_pause
    assert pause is not None and pause.auto_pass_at == {} and pause.closes_after is None


def test_bluff_schedule_is_redacted(registry: StaticDataRegistry) -> None:
    state = _agenda(registry)
    reaction_pause.sync(state, registry, now=100.0)
    state = reaction_pause.pass_pause(state, "p1")
    for viewer in ("p1", "p2", "p3", None):
        seen = state.clone()
        visibility.redact_reaction_windows(seen, viewer)
        assert seen.reaction_pause is not None
        assert seen.reaction_pause.auto_pass_at == {} and seen.reaction_pause.closes_after is None


# --- "unless something changes" ------------------------------------------------------------------


def _three() -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2", "p3"],
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2", "p3")},
    )


def test_conditional_pre_pass_lapses_on_another_players_move() -> None:
    state = reaction_prefs.update(
        _three(), "p2", declare={reaction_prefs.SABOTAGE: reaction_prefs.UNTIL_TURN},
        unless_changes=True,
    )
    assert reaction_prefs.declares_pass(state, "p2", reaction_prefs.SABOTAGE)
    reaction_prefs.note_change(state, "p2", "played an action card")  # own move: still live
    assert reaction_prefs.declares_pass(state, "p2", reaction_prefs.SABOTAGE)
    reaction_prefs.note_change(state, "p1", "played an action card")
    assert not reaction_prefs.declares_pass(state, "p2", reaction_prefs.SABOTAGE)
    reaction_prefs.prune(state)
    prefs = state.players["p2"].private.reaction_prefs
    assert prefs.passes == {}
    assert [(n.category, n.actor, n.reason) for n in prefs.notices] == [
        (reaction_prefs.SABOTAGE, "p1", "played an action card")
    ]
    cleared = reaction_prefs.update(state, "p2", clear_notices=True)
    assert cleared.players["p2"].private.reaction_prefs.notices == []


def test_plain_pre_pass_ignores_moves() -> None:
    state = reaction_prefs.update(
        _three(), "p2", declare={reaction_prefs.SABOTAGE: reaction_prefs.UNTIL_TURN}
    )
    reaction_prefs.note_change(state, "p1", "played an action card")
    assert reaction_prefs.declares_pass(state, "p2", reaction_prefs.SABOTAGE)


def test_always_is_never_conditional() -> None:
    state = reaction_prefs.update(
        _three(), "p2", declare={reaction_prefs.SABOTAGE: reaction_prefs.UNTIL_ALWAYS},
        unless_changes=True,
    )
    reaction_prefs.note_change(state, "p1", "used an agent")
    assert reaction_prefs.declares_pass(state, "p2", reaction_prefs.SABOTAGE)


def test_forgotten_moves_cancel_conservatively() -> None:
    """More moves than the log keeps: the engine cannot tell who made the forgotten ones, so the
    conditional pre-pass lapses (asking again is the safe side)."""
    state = reaction_prefs.update(
        _three(), "p2", declare={reaction_prefs.ALL: reaction_prefs.UNTIL_ROUND},
        unless_changes=True,
    )
    for _ in range(40):
        reaction_prefs.note_change(state, "p2", "x")
    assert not reaction_prefs.declares_pass(state, "p2", reaction_prefs.SABOTAGE)


def test_auto_hits_policy_is_validated() -> None:
    state = reaction_prefs.update(_three(), "p2", auto_hits=reaction_prefs.AUTO_HITS_CHEAP)
    assert state.players["p2"].private.reaction_prefs.auto_hits == "cheap"
    with pytest.raises(ValueError, match="policy"):
        reaction_prefs.update(state, "p2", auto_hits="everything")
