"""Testy API fazy statusu: cele w web-data, endpointy /status/*, krok 8 przez /phase/next."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    return TestClient(create_app(registry=registry, store=EventStore(":memory:")))


def _web(client: TestClient) -> dict[str, Any]:
    return client.get("/api/public/game/g/web-data").json()  # type: ignore[no-any-return]


def _new_game_in_status(client: TestClient) -> None:
    """Nowa gra 3-osobowa; God-Mode ustawia karty strategii i wchodzi w STATUS."""
    resp = client.post(
        "/game/new",
        json={
            "players": [
                {"faction_id": "sol"},
                {"faction_id": "hacan"},
                {"faction_id": "arborec"},
            ]
        },
    )
    assert resp.status_code == 200
    cards = {"p1": [1, 4], "p2": [2, 5], "p3": [3, 6]}
    state = client.get("/state").json()["state"]
    patched = {
        pid: {**state["players"][pid], "strategy_cards": c}
        for pid, c in cards.items()
    }
    client.post("/god-mode/patch", json={"phase": "ACTION", "players": patched})
    # Wejście w STATUS ścieżką silnika (inicjuje kroki) z pominięciem pasów fazy akcji.
    assert client.post("/phase/skip").status_code == 200
    assert client.get("/state").json()["state"]["phase"] == "STATUS"


def test_new_game_exposes_objectives_in_web_data(client: TestClient) -> None:
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}, {"faction_id": "hacan"}]},
    )
    data = _web(client)
    objectives = data["objectives"]
    revealed1 = [o for o in objectives["stage1Objectives"] if o["revealed"]]
    hidden1 = [o for o in objectives["stage1Objectives"] if not o["revealed"]]
    assert len(revealed1) == 2 and len(hidden1) == 3
    assert len(objectives["stage2Objectives"]) == 5
    assert all(not o["revealed"] and o["name"] == "UNREVEALED"
               for o in objectives["stage2Objectives"])
    # Zakryte cele nie zdradzają identyfikatora karty.
    assert all(o["key"].startswith("UNREVEALED_") for o in hidden1)
    assert all(o["pointValue"] == 1 for o in revealed1)
    assert data["cardPool"]["actionCardDeckSize"] > 0
    assert set(data["scoreBreakdowns"]) == {p["faction"] for p in data["playerData"]}


def test_status_flow_via_endpoints(client: TestClient) -> None:
    _new_game_in_status(client)
    game_state = _web(client)["gameState"]
    assert game_state["status"]["step"] == "SCORE_OBJECTIVES"
    assert game_state["canAdvancePhase"] is False
    scoreable = game_state["status"]["scoreablePublic"]["p1"]
    assert len(scoreable) == 2

    # Punktowanie: tylko gracz, którego kolej; limit 1 cel publiczny.
    assert client.post(
        "/status/score",
        json={"player_id": "p2", "kind": "public", "objective_id": scoreable[0]},
    ).status_code == 422
    ok = client.post(
        "/status/score",
        json={"player_id": "p1", "kind": "public", "objective_id": scoreable[0]},
    )
    assert ok.status_code == 200
    assert client.post(
        "/status/score",
        json={"player_id": "p1", "kind": "public", "objective_id": scoreable[1]},
    ).status_code == 422
    data = _web(client)
    p1 = next(p for p in data["playerData"] if p["discordId"] == "p1")
    assert p1["totalVps"] == 1
    scored = next(o for o in data["objectives"]["stage1Objectives"] if o["key"] == scoreable[0])
    assert scored["scoredFactions"] == [p1["faction"]]
    entries = data["scoreBreakdowns"][p1["faction"]]["entries"]
    assert any(e["type"] == "PO_1" and e["state"] == "SCORED" for e in entries)

    for pid in ("p1", "p2", "p3"):
        assert client.post("/status/finish-scoring", json={"player_id": pid}).status_code == 200
    status = _web(client)["gameState"]["status"]
    assert status["step"] == "REDISTRIBUTE"
    assert status["unassignedCc"] == {"p1": 2, "p2": 2, "p3": 2}

    # Zła suma → 422; poprawna dla każdego → COMPLETE i dostępny Next phase.
    assert client.post(
        "/status/redistribute",
        json={"player_id": "p1", "tactical": 1, "fleet": 1, "strategic": 1},
    ).status_code == 422
    assert client.post("/phase/next", json={"player_id": "p1"}).status_code == 422
    for pid in ("p1", "p2", "p3"):
        resp = client.post(
            "/status/redistribute",
            json={"player_id": pid, "tactical": 4, "fleet": 3, "strategic": 3},
        )
        assert resp.status_code == 200
    assert _web(client)["gameState"]["canAdvancePhase"] is True

    # Krok 8: karty wracają, bez Custodians — nowa runda od fazy strategii.
    resp = client.post("/phase/next", json={"player_id": "p1"})
    assert resp.status_code == 200
    state = resp.json()["state"]
    assert state["phase"] == "STRATEGY" and state["round_number"] == 2
    assert state["status"] is None


def test_status_goes_to_agenda_when_custodians_removed(client: TestClient) -> None:
    _new_game_in_status(client)
    client.post("/god-mode/patch", json={"custodians_removed": True})
    for pid in ("p1", "p2", "p3"):
        client.post("/status/finish-scoring", json={"player_id": pid})
    for pid in ("p1", "p2", "p3"):
        client.post(
            "/status/redistribute",
            json={"player_id": pid, "tactical": 4, "fleet": 3, "strategic": 3},
        )
    state = client.post("/phase/next", json={"player_id": "p1"}).json()["state"]
    assert state["phase"] == "AGENDA" and state["round_number"] == 1
    # Karty strategii wróciły do puli, a koniec agendy nie psuje nowej rundy.
    assert client.post("/round/next").status_code == 200


def test_status_endpoints_reject_outside_status_phase(client: TestClient) -> None:
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}, {"faction_id": "hacan"}]},
    )
    resp = client.post("/status/finish-scoring", json={"player_id": "p1"})
    assert resp.status_code == 422
    assert "status phase" in resp.json()["detail"].lower()
