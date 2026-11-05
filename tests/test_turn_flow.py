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


def test_all_passed_hands_turn_to_speaker_without_auto_transition() -> None:
    state = _state_with_players()
    state.speaker_id = "p2"
    state.players["p2"].passed = True
    state.players["p3"].passed = True
    # p1 pasuje jako ostatni → faza akcji NIE przechodzi automatycznie (RULES.md
    # 31.4: brak auto-tranzycji, przejście ogłasza mówca). Faza wciąż ACTION,
    # aktywny = MÓWCA (zawsze czyjaś tura — nigdy None).
    nxt = turn_flow.pass_turn(state)
    assert nxt.phase is Phase.ACTION
    assert nxt.active_player_id == "p2"
    assert nxt.players["p1"].passed is True


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
    with pytest.raises(ValueError, match="only be ended/passed during the action phase"):
        turn_flow.end_turn(state, "p1")


def test_end_turn_wrong_player_rejected() -> None:
    state = _state_with_players()
    with pytest.raises(ValueError, match="It is not"):
        turn_flow.end_turn(state, "p2")  # aktywny jest p1


def test_pass_before_strategic_action_rejected() -> None:
    state = _state_with_players()
    # p1 ma kartę, ale jej NIE zagrał (brak exhausted).
    state.players["p1"].exhausted_strategy_cards = []
    with pytest.raises(ValueError, match="strategic action"):
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
    with pytest.raises(ValueError, match="does not match the players"):
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


def test_next_phase_action_to_status_sets_initiative_first() -> None:
    """RULES.md 31.4 (decyzja projektowa): wejście w STATUS NIE zostawia None.

    Odejście od LRR „no active player" — aktywny = pierwszy gracz w INITIATIVE
    ORDER (najniższy numer karty), by UI/bot zawsze miały wskazanego gracza.
    """
    state = _state_with_players()  # p1=[1], p2=[3], p3=[5]
    state.speaker_id = "p2"
    nxt = turn_flow.next_phase(state)  # ACTION -> STATUS
    assert nxt.phase is Phase.STATUS
    assert nxt.active_player_id == "p1"  # inicjatywa 1


def test_next_phase_status_to_agenda_sets_initiative_first() -> None:
    """RULES.md 31.4: wejście w AGENDA też wskazuje pierwszego wg inicjatywy."""
    state = _state_with_players()
    state.phase = Phase.STATUS
    state.speaker_id = "p3"
    nxt = turn_flow.next_phase(state)  # STATUS -> AGENDA
    assert nxt.phase is Phase.AGENDA
    assert nxt.active_player_id == "p1"


def test_end_turn_only_active_unpassed_keeps_turn() -> None:
    """end_turn (NIE pas) nie wyczerpuje aktywnego gracza: gdy p2/p3 spasowali,
    a p1 tylko kończy turę, tura wraca do p1 (jedyny niespasowany). Faza ACTION,
    aktywny nigdy None (RULES.md 31.4)."""
    state = _state_with_players()
    state.speaker_id = "p3"
    state.players["p2"].passed = True
    state.players["p3"].passed = True
    nxt = turn_flow.end_turn(state)  # p1 kończy turę, ale NIE pasuje
    assert nxt.phase is Phase.ACTION
    assert nxt.active_player_id == "p1"


def test_pass_last_player_hands_to_speaker_no_transition() -> None:
    """RULES.md 31.4: gdy OSTATNI niespasowany gracz PASUJE, faza NIE przechodzi
    automatycznie do statusu — zostaje ACTION, a aktywny = mówca (ogłosi tranzycję)."""
    state = _state_with_players()
    state.speaker_id = "p3"
    state.players["p2"].passed = True
    state.players["p3"].passed = True
    nxt = turn_flow.pass_turn(state)  # p1 pasuje jako ostatni → wszyscy spasowali
    assert nxt.phase is Phase.ACTION
    assert nxt.active_player_id == "p3"  # mówca
    assert nxt.players["p1"].passed is True


def test_advance_active_player_status_rotates_initiative() -> None:
    # W fazie statusu „następny gracz" przesuwa aktywnego wg inicjatywy (p1→p2→p3→p1).
    state = _state_with_players()
    state.phase = Phase.STATUS
    state.active_player_id = "p1"
    s2 = turn_flow.advance_active_player(state)
    assert s2.active_player_id == "p2"
    s3 = turn_flow.advance_active_player(s2)
    assert s3.active_player_id == "p3"
    # Zawijanie: po ostatnim wraca pierwszy.
    s4 = turn_flow.advance_active_player(s3)
    assert s4.active_player_id == "p1"


def test_advance_active_player_agenda_allowed() -> None:
    state = _state_with_players()
    state.phase = Phase.AGENDA
    state.active_player_id = "p2"
    assert turn_flow.advance_active_player(state).active_player_id == "p3"


def test_advance_active_player_rejects_action_phase() -> None:
    # Poza STATUS/AGENDA (np. ACTION) „następny gracz" jest niedozwolony.
    state = _state_with_players()  # phase=ACTION
    with pytest.raises(ValueError, match="status/agenda"):
        turn_flow.advance_active_player(state)


def test_advance_active_player_checks_identity() -> None:
    state = _state_with_players()
    state.phase = Phase.STATUS
    state.active_player_id = "p1"
    # Podany gracz musi być aktywnym (spójnie z end_turn/pass_turn).
    with pytest.raises(ValueError, match="not p2's turn"):
        turn_flow.advance_active_player(state, "p2")
    # Aktywny gracz przechodzi bez błędu.
    assert turn_flow.advance_active_player(state, "p1").active_player_id == "p2"
