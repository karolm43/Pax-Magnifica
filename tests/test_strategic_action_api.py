"""Testy API akcji strategicznej (E8-T3): /strategy/play + /strategy/secondary."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.game_state import GameState, PlayerState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    return GameState(
        active_player_id="p1",
        seating_order=["p1", "p2", "p3"],
        players={
            "p1": PlayerState(player_id="p1", color="red", strategy_cards=[1]),
            "p2": PlayerState(player_id="p2", color="green"),
            "p3": PlayerState(player_id="p3", color="blue"),
        },
    )


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    app = create_app(
        registry=registry, store=EventStore(":memory:"), initial_state=_state()
    )
    return TestClient(app)


def _pending(client: TestClient) -> dict[str, Any] | None:
    data = client.get("/api/public/game/g/web-data").json()
    pw: dict[str, Any] | None = data["gameState"]["pendingWindow"]
    return pw


def test_play_resolves_primary_and_opens_window(client: TestClient) -> None:
    resp = client.post("/strategy/play", json={"player_id": "p1", "initiative": 1})
    assert resp.status_code == 200
    # Primary Leadership: +3 żetony taktyczne (start 3 → 6).
    state = resp.json()["state"]
    assert state["players"]["p1"]["tactical_cc"] == 6
    # Okno secondary otwarte, kolejka p2,p3 jako kolory.
    pw = _pending(client)
    assert pw is not None
    assert pw["windowType"] == "STRATEGY_SECONDARY"
    assert pw["queue"] == ["green", "blue"]
    assert pw["currentResponderId"] == "p2"


def test_secondary_flow_through_queue(client: TestClient) -> None:
    client.post("/strategy/play", json={"player_id": "p1", "initiative": 1})
    r1 = client.post(
        "/strategy/secondary", json={"player_id": "p2", "execute": True}
    )
    assert r1.status_code == 200
    pw = _pending(client)
    assert pw is not None
    assert pw["currentResponderId"] == "p3"
    r2 = client.post(
        "/strategy/secondary", json={"player_id": "p3", "execute": False}
    )
    assert r2.status_code == 200
    # Okno zamknięte po ostatnim respondencie.
    assert _pending(client) is None


def test_secondary_out_of_order_rejected(client: TestClient) -> None:
    client.post("/strategy/play", json={"player_id": "p1", "initiative": 1})
    resp = client.post(
        "/strategy/secondary", json={"player_id": "p3", "execute": True}
    )
    assert resp.status_code == 422


def test_play_card_not_owned_rejected(client: TestClient) -> None:
    resp = client.post("/strategy/play", json={"player_id": "p1", "initiative": 4})
    assert resp.status_code == 422
