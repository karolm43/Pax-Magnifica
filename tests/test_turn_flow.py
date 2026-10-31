"""Testy przepływu faz i tur (Etap E1) — czyste funkcje ``turn_flow``."""

from __future__ import annotations

import pytest

from src.core import turn_flow
from src.core.game_state import GameState, Phase, PlayerState


def _state_with_players() -> GameState:
    """Stan z 3 graczami, kartami strategii i JUŻ wykonaną akcją strategiczną.

    ``exhausted_strategy_cards`` = karta zagrana, więc gracz może pasować (RULES.md 31.2).
    """
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(
                player_id="p1", strategy_cards=[1], exhausted_strategy_cards=[1]
            ),
            "p2": PlayerState(
                player_id="p2", strategy_cards=[3], exhausted_strategy_cards=[3]
            ),
            "p3": PlayerState(
                player_id="p3", strategy_cards=[5], exhausted_strategy_cards=[5]
            ),
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
    # 3 graczy → Pick_Count=2 (RULES.md 13): przejście STRATEGY→ACTION wymaga, by
    # KAŻDY gracz miał komplet (2 karty), inaczej ``ensure_strategy_complete`` rzuca.
    # Każdemu nadajemy po 2 karty; aktywny po przejściu = najniższa inicjatywa (p1).
    state = GameState(
        phase=Phase.STRATEGY,
        seating_order=["p1", "p2", "p3"],
        speaker_id="p1",
        players={
            "p1": PlayerState(player_id="p1", strategy_cards=[1, 2]),
            "p2": PlayerState(player_id="p2", strategy_cards=[3, 4]),
            "p3": PlayerState(player_id="p3", strategy_cards=[5, 6]),
        },
    )
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


def test_next_round_sets_active_to_speaker() -> None:
    # Nowa runda zaczyna fazę strategii: wybór otwiera mówca (RULES.md 24).
    state = _state_with_players()
    state.seating_order = ["p1", "p2", "p3"]
    state.speaker_id = "p3"
    state.phase = Phase.STATUS
    # Symuluj przełom rundy: karty wyczyszczone przed next_round (jak w flow.py).
    for p in state.players.values():
        p.strategy_cards = []
    nxt = turn_flow.next_round(state)
    assert nxt.active_player_id == "p3"  # mówca wybiera pierwszy


def test_next_phase_into_strategy_sets_speaker() -> None:
    # Agenda → Strategia: aktywny = mówca (speaker order), nie inicjatywa.
    state = _state_with_players()
    state.seating_order = ["p1", "p2", "p3"]
    state.speaker_id = "p2"
    state.phase = Phase.AGENDA
    for p in state.players.values():
        p.strategy_cards = []
    nxt = turn_flow.next_phase(state)
    assert nxt.phase is Phase.STRATEGY
    assert nxt.active_player_id == "p2"


# --- Walidacja flow (RULES.md 31.2, E8-T4) --------------------------------


def test_end_turn_wrong_phase_rejected() -> None:
    state = _state_with_players()
    state.phase = Phase.STRATEGY
    with pytest.raises(ValueError, match="tylko w fazie akcji"):
        turn_flow.end_turn(state, "p1")


def test_end_turn_wrong_player_rejected() -> None:
    state = _state_with_players()
    with pytest.raises(ValueError, match="To nie tura"):
        turn_flow.end_turn(state, "p2")  # aktywny jest p1


def test_pass_before_strategic_action_rejected() -> None:
    state = _state_with_players()
    # p1 ma kartę, ale jej NIE zagrał (brak exhausted).
    state.players["p1"].exhausted_strategy_cards = []
    with pytest.raises(ValueError, match="akcji strategicznej"):
        turn_flow.pass_turn(state, "p1")


def test_pass_without_strategy_card_allowed() -> None:
    # Gracz bez karty strategii może pasować (nie ma czego zagrać).
    state = _state_with_players()
    state.players["p1"].strategy_cards = []
    state.players["p1"].exhausted_strategy_cards = []
    nxt = turn_flow.pass_turn(state, "p1")
    assert nxt.players["p1"].passed is True


def test_initiative_order_alias() -> None:
    state = _state_with_players()
    assert turn_flow.initiative_order(state) == turn_flow.turn_order(state)


# --- Testy brzegowe refaktoryzacji po przeglądzie semantycznym (znalezisko #7) ---


def test_next_phase_rejects_seating_players_mismatch() -> None:
    """Przejście STRATEGY→ACTION przy rozjeździe seating_order↔players
    (znalezisko #1, realna ścieżka God-Mode): ``next_phase`` daje czytelny
    ValueError o niespójnym stanie ZANIM dojdzie do ``strict_initiative_order``
    (dawniej padało mylącym „Gracz X nie ma przypisanej karty strategii.").
    """
    state = GameState(
        phase=Phase.STRATEGY,
        seating_order=["p1", "p2"],  # p3 celowo poza listą miejsc
        speaker_id="p1",
        players={
            "p1": PlayerState(player_id="p1", strategy_cards=[1, 2]),
            "p2": PlayerState(player_id="p2", strategy_cards=[3, 4]),
            "p3": PlayerState(player_id="p3", strategy_cards=[5, 6]),
        },
    )
    with pytest.raises(ValueError, match="nie pokrywa się z graczami"):
        turn_flow.next_phase(state)


def test_next_phase_strategy_to_action_consistent_state_ok() -> None:
    """Regresja po #1: spójny, kompletny stan 3 graczy (seating_order == players)
    przechodzi STRATEGY→ACTION bez błędu — aktywny = najniższa inicjatywa.
    """
    state = GameState(
        phase=Phase.STRATEGY,
        seating_order=["p1", "p2", "p3"],
        speaker_id="p1",
        players={
            "p1": PlayerState(player_id="p1", strategy_cards=[1, 2]),
            "p2": PlayerState(player_id="p2", strategy_cards=[3, 4]),
            "p3": PlayerState(player_id="p3", strategy_cards=[5, 6]),
        },
    )
    nxt = turn_flow.next_phase(state)
    assert nxt.phase is Phase.ACTION
    assert nxt.active_player_id == "p1"
