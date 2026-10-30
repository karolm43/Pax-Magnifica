"""Testy okien czasowych (core/timing.py) — mechanika kolejki reagujących."""

from __future__ import annotations

import pytest

from src.core import timing
from src.core.game_state import GameState, PlayerState, TimingWindow, WindowType


def _state_with_players(ids: list[str], seating: list[str] | None = None) -> GameState:
    """Stan z graczami ``ids`` i opcjonalną kolejnością zasiadania."""
    return GameState(
        players={pid: PlayerState(player_id=pid) for pid in ids},
        seating_order=seating if seating is not None else list(ids),
    )


# --- build_response_queue ------------------------------------------------


def test_queue_starts_after_initiator_clockwise() -> None:
    state = _state_with_players(["p1", "p2", "p3", "p4"])
    # Inicjator p2 → kolejka p3, p4, p1 (po inicjatorze, zgodnie z zegarem; p2 pominięty).
    assert timing.build_response_queue(state, "p2") == ["p3", "p4", "p1"]


def test_queue_wraps_around_table() -> None:
    state = _state_with_players(["p1", "p2", "p3"])
    assert timing.build_response_queue(state, "p3") == ["p1", "p2"]


def test_queue_can_include_initiator_last() -> None:
    state = _state_with_players(["p1", "p2", "p3"])
    assert timing.build_response_queue(state, "p1", include_initiator=True) == [
        "p2",
        "p3",
        "p1",
    ]


def test_queue_no_initiator_is_full_table() -> None:
    state = _state_with_players(["p1", "p2", "p3"])
    assert timing.build_response_queue(state, None) == ["p1", "p2", "p3"]


def test_queue_falls_back_to_sorted_ids_when_no_seating() -> None:
    state = GameState(players={p: PlayerState(player_id=p) for p in ("b", "a", "c")})
    # seating puste → sortuje po id; inicjator "a" pominięty.
    assert timing.build_response_queue(state, "a") == ["b", "c"]


def test_queue_ignores_unknown_initiator() -> None:
    state = _state_with_players(["p1", "p2"])
    # Inicjator spoza stołu → pełny stół (bez include) z pominięciem go (nieobecny).
    assert timing.build_response_queue(state, "x") == ["p1", "p2"]


# --- open_window / current_responder -------------------------------------


def test_open_window_sets_pending_and_first_responder() -> None:
    state = _state_with_players(["p1", "p2", "p3"])
    new = timing.open_window(
        state, WindowType.STRATEGY_SECONDARY, ["p2", "p3"], context={"initiative": 1}
    )
    assert new.pending_window is not None
    assert new.pending_window.window_type == WindowType.STRATEGY_SECONDARY
    assert new.pending_window.context == {"initiative": 1}
    assert timing.current_responder(new) == "p2"
    # Oryginał nienaruszony (czysta funkcja).
    assert state.pending_window is None


def test_open_window_rejects_nested_window() -> None:
    state = _state_with_players(["p1", "p2"])
    opened = timing.open_window(state, WindowType.REACTION, ["p2"])
    with pytest.raises(ValueError, match="już trwa"):
        timing.open_window(opened, WindowType.REACTION, ["p1"])


def test_current_responder_none_without_window() -> None:
    state = _state_with_players(["p1"])
    assert timing.current_responder(state) is None


# --- respond_current / completion / close --------------------------------


def test_respond_advances_queue_in_order() -> None:
    state = _state_with_players(["p1", "p2", "p3"])
    s = timing.open_window(state, WindowType.STRATEGY_SECONDARY, ["p2", "p3"])
    s = timing.respond_current(s, "p2")
    assert timing.current_responder(s) == "p3"
    assert s.pending_window is not None
    assert s.pending_window.responded == ["p2"]
    assert not timing.is_window_complete(s)

    s = timing.respond_current(s, "p3")
    assert timing.current_responder(s) is None
    assert timing.is_window_complete(s)


def test_respond_out_of_order_rejected() -> None:
    state = _state_with_players(["p1", "p2", "p3"])
    s = timing.open_window(state, WindowType.STRATEGY_SECONDARY, ["p2", "p3"])
    with pytest.raises(ValueError, match="poza kolejnością"):
        timing.respond_current(s, "p3")  # kolej p2, nie p3


def test_respond_without_window_rejected() -> None:
    state = _state_with_players(["p1"])
    with pytest.raises(ValueError, match="Brak otwartego okna"):
        timing.respond_current(state, "p1")


def test_respond_on_complete_window_rejected() -> None:
    state = _state_with_players(["p1", "p2"])
    s = timing.open_window(state, WindowType.REACTION, ["p2"])
    s = timing.respond_current(s, "p2")  # okno zakończone
    with pytest.raises(ValueError, match="już zakończone"):
        timing.respond_current(s, "p2")


def test_close_window_clears_pending() -> None:
    state = _state_with_players(["p1", "p2"])
    s = timing.open_window(state, WindowType.REACTION, ["p2"])
    s = timing.close_window(s)
    assert s.pending_window is None
    assert not timing.is_window_complete(s)


def test_close_window_idempotent_without_window() -> None:
    state = _state_with_players(["p1"])
    s = timing.close_window(state)
    assert s.pending_window is None


# --- serializacja --------------------------------------------------------


def test_window_json_roundtrip() -> None:
    window = TimingWindow(
        window_type=WindowType.COMBAT_ASSIGN_HITS,
        queue=["p1", "p2"],
        cursor=1,
        responded=["p1"],
        context={"position": "101"},
    )
    state = GameState(
        players={"p1": PlayerState(player_id="p1"), "p2": PlayerState(player_id="p2")},
        pending_window=window,
    )
    restored = GameState.model_validate_json(state.model_dump_json())
    assert restored == state
    assert restored.pending_window is not None
    assert restored.pending_window.current_responder == "p2"
