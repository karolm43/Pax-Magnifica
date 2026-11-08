"""Testy końca gry: limit rund (10) oraz głosowanie epilogu (honorowe / niehonorowe)."""

from __future__ import annotations

import pytest

from src.core import epilogue, status_phase
from src.core.game_state import (
    ControlType,
    GameState,
    Phase,
    PlayerState,
    StatusPhaseState,
    StatusStep,
)
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _ended(bots: tuple[str, ...] = ()) -> GameState:
    players = {
        pid: PlayerState(
            player_id=pid,
            color=pid,
            control_type=ControlType.BOT if pid in bots else ControlType.HUMAN,
        )
        for pid in ("p1", "p2", "p3")
    }
    return GameState(
        phase=Phase.STATUS,
        seating_order=["p1", "p2", "p3"],
        speaker_id="p1",
        players=players,
        winner_id="p1",
        end_reason="victory_points",
    )


def test_winner_does_not_vote_and_is_excluded() -> None:
    state = _ended()
    assert epilogue.voters(state) == ["p2", "p3"]
    with pytest.raises(ValueError, match="winner does not vote"):
        epilogue.cast_vote(state, "p1", epilogue.HONORABLE)


def test_vote_requires_finished_game_and_valid_choice() -> None:
    running = _ended()
    running.winner_id = None
    with pytest.raises(ValueError, match="not ended"):
        epilogue.cast_vote(running, "p2", epilogue.HONORABLE)
    with pytest.raises(ValueError, match="honorable"):
        epilogue.cast_vote(_ended(), "p2", "maybe")


def test_majority_decides_and_double_vote_rejected() -> None:
    state = epilogue.cast_vote(_ended(), "p2", epilogue.DISHONORABLE)
    assert state.epilogue is not None and state.epilogue.result is None
    with pytest.raises(ValueError, match="already voted"):
        epilogue.cast_vote(state, "p2", epilogue.HONORABLE)
    state = epilogue.cast_vote(state, "p3", epilogue.DISHONORABLE)
    assert state.epilogue is not None and state.epilogue.result == epilogue.DISHONORABLE


def test_tie_is_decided_by_the_runner_up() -> None:
    base = _ended()
    base.players["p2"].victory_points = 7  # drugie miejsce
    base.players["p3"].victory_points = 4
    assert epilogue.runner_up(base) == "p2"
    state = epilogue.cast_vote(base, "p2", epilogue.DISHONORABLE)
    state = epilogue.cast_vote(state, "p3", epilogue.HONORABLE)
    assert state.epilogue is not None and state.epilogue.result == epilogue.DISHONORABLE
    # Odwrotnie: drugie miejsce ma p3 i głosuje honorowo.
    base.players["p2"].victory_points = 3
    base.players["p3"].victory_points = 8
    state = epilogue.cast_vote(base, "p2", epilogue.DISHONORABLE)
    state = epilogue.cast_vote(state, "p3", epilogue.HONORABLE)
    assert state.epilogue is not None and state.epilogue.result == epilogue.HONORABLE


def test_bots_vote_automatically_and_open_is_idempotent() -> None:
    state = epilogue.open_vote(_ended(bots=("p2", "p3")))
    assert state.epilogue is not None
    assert set(state.epilogue.votes) == {"p2", "p3"}
    assert state.epilogue.result in epilogue.CHOICES
    again = epilogue.open_vote(state)
    assert again.epilogue == state.epilogue


def test_open_with_one_human_voter_waits_for_them() -> None:
    state = epilogue.open_vote(_ended(bots=("p3",)))
    assert state.epilogue is not None
    assert list(state.epilogue.votes) == ["p3"]
    assert state.epilogue.result is None


def test_round_limit_ends_game_with_vp_leader(registry: StaticDataRegistry) -> None:
    state = _ended()
    state.winner_id = None
    state.end_reason = None
    state.round_number = 10
    state.players["p3"].victory_points = 6
    state.players["p2"].victory_points = 4
    state.status = StatusPhaseState(step=StatusStep.COMPLETE)
    out = status_phase.finish_status(state, registry)
    assert out.winner_id == "p3"
    assert out.end_reason == "round_limit"
    assert out.round_number == 10
