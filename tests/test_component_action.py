"""Testy akcji komponentu (RULES.md 31.8): core ``component_action`` + endpoint.

Szkielet T-component: akcja komponentu NIE wykonuje mechaniki konkretnego komponentu —
rejestruje tylko, że gracz wykonał akcję w tej turze (``took_action_this_turn``), tak jak
akcja strategiczna/taktyczna. Testy pilnują walidacji (faza/tura/okno/jedna akcja/pas) i
tego, że sukces odblokowuje zakończenie tury.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import component_action
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState, TimingWindow, WindowType
from src.core.registry import StaticDataRegistry


def _state() -> GameState:
    """Faza akcji, aktywny p1 (świeża tura: nie działał, nie spasował)."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", strategy_cards=[1]),
            "p2": PlayerState(player_id="p2", color="green", strategy_cards=[3]),
        },
    )


# --------------------------- core (czysta funkcja) ---------------------------


def test_component_action_marks_action_taken() -> None:
    state = _state()
    new_state = component_action.play_component_action(state, "p1", "direct_hit")
    assert new_state.players["p1"].took_action_this_turn is True
    # Wejście nie jest mutowane (czysta funkcja).
    assert state.players["p1"].took_action_this_turn is False


def test_component_action_player_id_optional() -> None:
    new_state = component_action.play_component_action(_state())
    assert new_state.players["p1"].took_action_this_turn is True


def test_component_action_outside_action_phase_rejected() -> None:
    state = _state()
    state.phase = Phase.STRATEGY
    with pytest.raises(ValueError, match="action phase"):
        component_action.play_component_action(state, "p1")


def test_component_action_wrong_player_rejected() -> None:
    with pytest.raises(ValueError, match="not p2's turn"):
        component_action.play_component_action(_state(), "p2")


def test_component_action_blocked_by_open_window() -> None:
    state = _state()
    state.pending_window = TimingWindow(
        window_type=WindowType.STRATEGY_SECONDARY, queue=["p2"]
    )
    with pytest.raises(ValueError, match="timing window is open"):
        component_action.play_component_action(state, "p1")


def test_component_action_rejected_after_acting() -> None:
    state = _state()
    state.players["p1"].took_action_this_turn = True
    with pytest.raises(ValueError, match="already took an action"):
        component_action.play_component_action(state, "p1")


def test_component_action_rejected_after_pass() -> None:
    state = _state()
    state.players["p1"].passed = True
    with pytest.raises(ValueError, match="passed"):
        component_action.play_component_action(state, "p1")


# ------------------------------- endpoint ------------------------------------


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    app = create_app(
        registry=registry, store=EventStore(":memory:"), initial_state=_state()
    )
    return TestClient(app)


def test_endpoint_component_action_unlocks_end_turn(client: TestClient) -> None:
    # Akcja komponentu → oznaczona akcja tury.
    resp = client.post(
        "/tactical/component-action",
        json={"player_id": "p1", "component_id": "direct_hit"},
    )
    assert resp.status_code == 200
    data = client.get("/api/public/game/g/web-data").json()
    p1 = next(p for p in data["playerData"] if p["color"] == "red")
    assert p1["tookActionThisTurn"] is True
    # End turn teraz przechodzi (po akcji) — p2 staje się aktywny.
    end = client.post("/turn/end", json={"player_id": "p1"})
    assert end.status_code == 200


def test_endpoint_component_action_rejected_after_acting(client: TestClient) -> None:
    client.post("/tactical/component-action", json={"player_id": "p1"})
    # Druga akcja w tej samej turze — 422 (jedna akcja na turę).
    resp = client.post("/tactical/component-action", json={"player_id": "p1"})
    assert resp.status_code == 422
