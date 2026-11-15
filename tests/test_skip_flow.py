"""Testy przeskoku fazy (God-Mode, ``core/skip_flow``) — nie zmienia zwykłego przepływu."""

from __future__ import annotations

import pytest

from src.core import objectives, skip_flow, turn_flow
from src.core.game_state import GameState, Phase, PlayerState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(phase: Phase = Phase.STRATEGY) -> GameState:
    return GameState(
        phase=phase,
        seating_order=["p1", "p2", "p3"],
        speaker_id="p1",
        active_player_id="p1",
        players={pid: PlayerState(player_id=pid) for pid in ("p1", "p2", "p3")},
    )


def test_skip_strategy_autopicks_and_enters_action(registry: StaticDataRegistry) -> None:
    out = skip_flow.skip_phase(_state(), registry)
    assert out.phase is Phase.ACTION
    # 3 graczy => 2 karty na gracza, wszystkie unikalne.
    cards = [c for p in out.players.values() for c in p.strategy_cards]
    assert len(cards) == 6 and len(set(cards)) == 6
    assert out.active_player_id is not None


def test_normal_next_phase_still_gated(registry: StaticDataRegistry) -> None:
    # Zwykły przepływ nietknięty: bez wyboru kart nadal 422/ValueError.
    with pytest.raises(ValueError):
        turn_flow.next_phase(_state())


def test_skip_action_ignores_passes(registry: StaticDataRegistry) -> None:
    state = skip_flow.skip_phase(_state(), registry)
    out = skip_flow.skip_phase(state, registry)
    assert out.phase is Phase.STATUS


def test_skip_status_without_custodians_starts_next_round(
    registry: StaticDataRegistry,
) -> None:
    """R_status_phase krok 8: bez zdjętego Custodians nie ma agendy — nowa runda."""
    state = objectives.setup_objectives(_state(), registry)
    state = skip_flow.skip_phase(state, registry)  # -> ACTION
    state = skip_flow.skip_phase(state, registry)  # -> STATUS
    assert state.phase is Phase.STATUS
    out = skip_flow.skip_phase(state, registry)  # kroki 1-8
    assert out.phase is Phase.STRATEGY
    assert out.round_number == state.round_number + 1
    assert all(not p.strategy_cards for p in out.players.values())


def test_skip_agenda_starts_next_round(registry: StaticDataRegistry) -> None:
    state = objectives.setup_objectives(_state(), registry)
    state.custodians_removed = True
    state = skip_flow.skip_phase(state, registry)  # -> ACTION
    state = skip_flow.skip_phase(state, registry)  # -> STATUS
    state = skip_flow.skip_phase(state, registry)  # -> AGENDA (Custodians zdjęty)
    assert state.phase is Phase.AGENDA
    out = skip_flow.skip_phase(state, registry)
    assert out.phase is Phase.STRATEGY
    assert out.round_number == state.round_number + 1


def test_skip_player_hands_turn_without_action(registry: StaticDataRegistry) -> None:
    state = skip_flow.skip_phase(_state(), registry)  # -> ACTION
    first = state.active_player_id
    assert first is not None
    out = skip_flow.skip_player(state)
    order = turn_flow.turn_order(out)
    assert out.active_player_id == order[(order.index(first) + 1) % 3]
    # Nikt nie spasował, nikt nie „zrobił akcji" — tylko przesunięcie tury.
    assert not any(p.passed for p in out.players.values())
    assert not out.players[out.active_player_id].took_action_this_turn


def test_skip_player_skips_passed_and_cycles_when_all_passed(
    registry: StaticDataRegistry,
) -> None:
    state = skip_flow.skip_phase(_state(), registry)  # -> ACTION
    order = turn_flow.turn_order(state)
    state.active_player_id = order[0]
    state.players[order[1]].passed = True
    assert skip_flow.skip_player(state).active_player_id == order[2]
    for p in state.players.values():
        p.passed = True
    assert skip_flow.skip_player(state).active_player_id == order[1]


def test_skip_player_only_in_action_phase() -> None:
    with pytest.raises(ValueError):
        skip_flow.skip_player(_state(Phase.STRATEGY))
