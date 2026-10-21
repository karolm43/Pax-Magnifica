"""Testy przepływu faz i tur (Etap E1) — czyste funkcje ``turn_flow``."""

from __future__ import annotations

from src.core import turn_flow
from src.core.game_state import GameState, Phase, PlayerState


def _state_with_players() -> GameState:
    """Stan z 3 graczami i przypisanymi kartami strategii (inicjatywa)."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", strategy_cards=[1]),
            "p2": PlayerState(player_id="p2", strategy_cards=[3]),
            "p3": PlayerState(player_id="p3", strategy_cards=[5]),
        },
    )


def test_turn_order_by_initiative() -> None:
    state = _state_with_players()
    assert turn_flow.turn_order(state) == ["p1", "p2", "p3"]


def test_turn_order_no_cards_falls_back_to_id() -> None:
    state = GameState(
        players={
            "pb": PlayerState(player_id="pb"),
            "pa": PlayerState(player_id="pa"),
        }
    )
    assert turn_flow.turn_order(state) == ["pa", "pb"]


def test_end_turn_advances_to_next() -> None:
    state = _state_with_players()
    nxt = turn_flow.end_turn(state)
    assert nxt.active_player_id == "p2"
    # Wejście nie jest mutowane.
    assert state.active_player_id == "p1"


def test_pass_skips_passed_players() -> None:
    state = _state_with_players()
    # p2 pasuje — po p1 tura powinna trafić do p3 (p2 pominięty).
    state.players["p2"].passed = True
    nxt = turn_flow.end_turn(state)
    assert nxt.active_player_id == "p3"


def test_pass_turn_marks_and_advances() -> None:
    state = _state_with_players()
    nxt = turn_flow.pass_turn(state)  # p1 pasuje
    assert nxt.players["p1"].passed is True
    assert nxt.active_player_id == "p2"


def test_all_passed_ends_action_phase() -> None:
    state = _state_with_players()
    state.players["p2"].passed = True
    state.players["p3"].passed = True
    # p1 pasuje jako ostatni → faza akcji się kończy (status).
    nxt = turn_flow.pass_turn(state)
    assert nxt.phase is Phase.STATUS
    assert nxt.active_player_id is None


def test_next_phase_cycles_and_sets_active_on_action() -> None:
    state = GameState(phase=Phase.STRATEGY, players=_state_with_players().players)
    nxt = turn_flow.next_phase(state)
    assert nxt.phase is Phase.ACTION
    assert nxt.active_player_id == "p1"  # najniższa inicjatywa


def test_next_round_resets_passes() -> None:
    state = _state_with_players()
    state.players["p1"].passed = True
    state.phase = Phase.STATUS
    nxt = turn_flow.next_round(state)
    assert nxt.round_number == state.round_number + 1
    assert nxt.phase is Phase.STRATEGY
    assert all(not p.passed for p in nxt.players.values())
