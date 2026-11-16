"""Testy API okien czasowych (E8-T2): /window/open, /close (bez ogólnego /respond) + web-data."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.game_state import GameState, PlayerState, WindowType
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state_three_players() -> GameState:
    """Trzech graczy z kolorami i kolejnością zasiadania."""
    return GameState(
        players={
            "p1": PlayerState(player_id="p1", color="red"),
            "p2": PlayerState(player_id="p2", color="green"),
            "p3": PlayerState(player_id="p3", color="blue"),
        },
        seating_order=["p1", "p2", "p3"],
    )


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    app = create_app(
        registry=registry,
        store=EventStore(":memory:"),
        initial_state=_state_three_players(),
    )
    return TestClient(app)


def _web_data(client: TestClient, viewer: str = "p1") -> dict[str, Any]:
    """Pobiera web-data z perspektywy ``viewer`` (domyślnie ``p1``).

    Stan testowy ma graczy, ale nie ustawia aktywnego — po integracji projekcji
    widoczności (R6) endpoint wymaga wtedy jawnego ``viewing_player`` (R6.7).
    """
    data: dict[str, Any] = client.get(
        "/api/public/game/g/web-data",
        params={"viewing_player": viewer},
    ).json()
    return data


def test_web_data_pending_window_null_by_default(client: TestClient) -> None:
    data = _web_data(client)
    assert data["gameState"]["pendingWindow"] is None


def test_open_window_exposes_responder_as_color(client: TestClient) -> None:
    # Okno z inicjatorem p1 → kolejka p2, p3 (po inicjatorze, zgodnie z zegarem).
    resp = client.post(
        "/window/open",
        json={
            "window_type": "STRATEGY_SECONDARY",
            "initiator_id": "p1",
            "context": {"initiative": 1},
        },
    )
    assert resp.status_code == 200
    pw = _web_data(client)["gameState"]["pendingWindow"]
    assert pw is not None
    assert pw["windowType"] == "STRATEGY_SECONDARY"
    assert pw["currentResponder"] == "green"  # p2 jako kolor
    assert pw["currentResponderId"] == "p2"
    assert pw["queue"] == ["green", "blue"]
    assert pw["remaining"] == 2
    assert pw["context"] == {"initiative": 1}
    assert pw["isComplete"] is False


def test_generic_respond_endpoint_removed(client: TestClient) -> None:
    """Ogólnej odpowiedzi w oknie nie ma: omijała decyzję okna i nie zamykała go (gra stawała)."""
    client.post("/window/open", json={"window_type": "REACTION", "queue": ["p2"]})
    resp = client.post("/window/respond", json={"player_id": "p2"})
    assert resp.status_code in (404, 405)


def test_open_rejects_unknown_window_type(client: TestClient) -> None:
    resp = client.post("/window/open", json={"window_type": "NONSENSE"})
    assert resp.status_code == 422


def test_open_rejects_nested_window(client: TestClient) -> None:
    client.post("/window/open", json={"window_type": "REACTION", "queue": ["p2"]})
    resp = client.post(
        "/window/open", json={"window_type": "REACTION", "queue": ["p3"]}
    )
    assert resp.status_code == 422


def test_close_window_clears_pending(client: TestClient) -> None:
    client.post("/window/open", json={"window_type": "REACTION", "queue": ["p2"]})
    resp = client.post("/window/close")
    assert resp.status_code == 200
    pw = _web_data(client)["gameState"]["pendingWindow"]
    assert pw is None


def test_all_window_types_accepted(client: TestClient) -> None:
    for wt in WindowType:
        client.post("/window/close")
        resp = client.post(
            "/window/open", json={"window_type": wt.value, "queue": ["p2"]}
        )
        assert resp.status_code == 200, wt.value
