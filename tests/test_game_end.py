"""Testy wykrywania końca gry po progu VP (niezależnie od źródła punktów)."""

from __future__ import annotations

from src.core import game_end
from src.core.game_state import GameState, PlayerState


def _state(vps: dict[str, int]) -> GameState:
    players = {
        pid: PlayerState(player_id=pid, color=pid, victory_points=vp)
        for pid, vp in vps.items()
    }
    return GameState(players=players, seating_order=list(vps), speaker_id="p1")


def test_no_winner_below_threshold() -> None:
    state = game_end.apply_victory(_state({"p1": 9, "p2": 4}))
    assert state.winner_id is None


def test_ten_vp_from_any_source_ends_the_game() -> None:
    state = game_end.apply_victory(_state({"p1": 3, "p2": 10}))
    assert state.winner_id == "p2"
    assert state.end_reason == "victory_points"


def test_highest_score_wins_when_several_cross_the_line() -> None:
    state = game_end.apply_victory(_state({"p1": 10, "p2": 11}))
    assert state.winner_id == "p2"


def test_existing_winner_is_not_overwritten() -> None:
    state = _state({"p1": 12, "p2": 10})
    state.winner_id = "p2"
    assert game_end.apply_victory(state).winner_id == "p2"
