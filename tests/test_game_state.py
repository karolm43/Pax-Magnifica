"""Testy GameState i EventStore — serializacja, Undo/Redo, God-Mode."""

from __future__ import annotations

from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState, SystemState

# --- GameState -----------------------------------------------------------


def test_gamestate_defaults() -> None:
    state = GameState()
    assert state.round_number == 1
    assert state.phase == Phase.STRATEGY
    assert state.players == {}


def test_gamestate_json_roundtrip() -> None:
    state = GameState(
        round_number=3,
        phase=Phase.ACTION,
        active_player_id="p1",
        players={"p1": PlayerState(player_id="p1", victory_points=4, trade_goods=2)},
        systems={
            "000": SystemState(
                position="000",
                system_id="18",
                planet_owners={"mr": "p1"},
            )
        },
    )
    restored = GameState.model_validate_json(state.model_dump_json())
    assert restored == state
    assert restored.players["p1"].victory_points == 4


def test_gamestate_clone_is_independent() -> None:
    state = GameState(players={"p1": PlayerState(player_id="p1", victory_points=1)})
    clone = state.clone()
    clone.players["p1"].victory_points = 99
    assert state.players["p1"].victory_points == 1  # oryginał nienaruszony


# --- EventStore ----------------------------------------------------------


def _state_with_vp(vp: int) -> GameState:
    return GameState(players={"p1": PlayerState(player_id="p1", victory_points=vp)})


def test_commit_and_current() -> None:
    store = EventStore()
    store.commit(_state_with_vp(0), label="start")
    current = store.current()
    assert current is not None
    assert current.players["p1"].victory_points == 0
    store.close()


def test_undo_restores_previous() -> None:
    store = EventStore()
    store.commit(_state_with_vp(0), "start")
    store.commit(_state_with_vp(5), "scored")
    assert store.current().players["p1"].victory_points == 5  # type: ignore[union-attr]

    restored = store.undo()
    assert restored is not None
    assert restored.players["p1"].victory_points == 0
    store.close()


def test_redo_reapplies() -> None:
    store = EventStore()
    store.commit(_state_with_vp(0), "start")
    store.commit(_state_with_vp(5), "scored")
    store.undo()
    redone = store.redo()
    assert redone is not None
    assert redone.players["p1"].victory_points == 5
    store.close()


def test_commit_after_undo_truncates_redo() -> None:
    """God-Mode: po cofnięciu nowa zmiana obcina gałąź redo."""
    store = EventStore()
    store.commit(_state_with_vp(0), "start")
    store.commit(_state_with_vp(5), "scored")
    store.undo()  # wracamy do vp=0
    store.commit(_state_with_vp(3), "manual-fix")  # nowa gałąź
    assert store.current().players["p1"].victory_points == 3  # type: ignore[union-attr]
    assert not store.can_redo()  # stara gałąź (vp=5) obcięta
    store.close()


def test_undo_redo_flags() -> None:
    store = EventStore()
    assert not store.can_undo()
    assert not store.can_redo()
    store.commit(_state_with_vp(0), "s0")
    assert not store.can_undo()
    store.commit(_state_with_vp(1), "s1")
    assert store.can_undo()
    assert not store.can_redo()
    store.undo()
    assert store.can_redo()
    store.close()


def test_undo_at_start_returns_none() -> None:
    store = EventStore()
    store.commit(_state_with_vp(0), "start")
    assert store.undo() is None  # brak wcześniejszej migawki
    store.close()
