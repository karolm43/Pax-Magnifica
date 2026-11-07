"""Testy API eksploracji (RULES.md 46): okno po Establish Control, wybór planety, karta."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import invasion
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from tests.test_exploration import _CULT, _IND, _grid, _state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _client(registry: StaticDataRegistry, state: GameState) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    return TestClient(app)


def _established(registry: StaticDataRegistry) -> GameState:
    grid = _grid()
    state = invasion.begin_invasion(_state({"infantry": 2}), grid, registry)
    state = invasion.commit_ground_forces(
        state, registry, {_CULT: {"infantry": 1}, _IND: {"infantry": 1}}
    )
    return invasion.advance(state, grid, registry)


def _body(option: dict[str, Any]) -> dict[str, Any]:
    params = option["params"]
    return {"option": option["id"], "param": params[0]["id"] if params else None}


def test_inactive_view(registry: StaticDataRegistry) -> None:
    client = _client(registry, _state())
    assert client.get("/exploration").json()["active"] is False


def test_full_flow_through_endpoints(registry: StaticDataRegistry) -> None:
    client = _client(registry, _established(registry))
    view: dict[str, Any] = client.get("/exploration").json()
    assert view["active"] is True and view["current"] is None and view["done"] is False
    assert {q["planet"]: q["traits"] for q in view["queue"]} == {
        _CULT: ["cultural"],
        _IND: ["industrial"],
    }
    # Sygnał w web-data dla okna na froncie.
    web = client.get("/api/public/game/g/web-data").json()
    assert web["gameState"]["activeExploration"] == {"system": "000"}

    # Zamknięcie inwazji jest zablokowane, dopóki trwa eksploracja.
    assert client.post("/tactical/invasion/next").status_code == 422
    assert client.post("/exploration/draw", json={"planet": "mr"}).status_code == 422

    assert client.post("/exploration/draw", json={"planet": _IND}).status_code == 200
    view = client.get("/exploration").json()
    current = view["current"]
    assert current["planet"] == _IND and current["card"]["deck"] == "industrial"
    assert current["card"]["name"] and current["card"]["text"]
    assert client.post("/exploration/finish").status_code == 422

    option = next(o for o in current["options"] if o["enabled"])
    body = _body(option)
    assert client.post("/exploration/resolve", json=body).status_code == 200

    # Druga (ostatnia) planeta ujawnia kartę sama.
    view = client.get("/exploration").json()
    assert view["current"]["planet"] == _CULT and len(view["log"]) == 1
    option = next(o for o in view["current"]["options"] if o["enabled"])
    body = _body(option)
    assert client.post("/exploration/resolve", json=body).status_code == 200

    view = client.get("/exploration").json()
    assert view["done"] is True and len(view["log"]) == 2
    assert client.post("/exploration/finish").status_code == 200
    assert client.get("/exploration").json()["active"] is False
    assert client.post("/tactical/invasion/next").status_code == 200


def test_attachment_appears_as_token_entity_in_web_data(registry: StaticDataRegistry) -> None:
    state = _state()
    client = _client(registry, state)
    tiles = client.get("/api/public/game/g/web-data").json()["tileUnitData"]
    planet = next(p for t in tiles.values() for p in t["planets"])
    state.planet_attachments = {planet: ["ds"]}  # Dyson Sphere
    tiles = _client(registry, state).get("/api/public/game/g/web-data").json()["tileUnitData"]
    entities = next(t["planets"][planet] for t in tiles.values() if planet in t["planets"])[
        "entities"
    ]
    assert {"entityId": "dysonsphere", "entityType": "attachment", "count": 1} in entities[
        "neutral"
    ]
