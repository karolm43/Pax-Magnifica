"""Testy API inwazji (RULES.md 40): okno, lądowanie, przejście przez podkroki."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import invasion
from src.core.event_store import EventStore
from src.core.game_state import GameState, InvasionPhase, TacticalStep
from src.core.registry import StaticDataRegistry
from tests.test_invasion import _PL1, _PL2, _grid, _state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _client(registry: StaticDataRegistry, state: GameState) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    return TestClient(app)


def test_no_invasion_view_when_inactive(registry: StaticDataRegistry) -> None:
    client = _client(registry, _state({"p1": {"infantry": 1}}))
    assert client.get("/tactical/invasion").json()["active"] is False


def test_api_commit_defense_and_establish(registry: StaticDataRegistry) -> None:
    state = invasion.begin_invasion(
        _state(
            {"p1": {"carrier": 1, "infantry": 3}},
            {_PL1: {"p2": {"spacedock": 1}}},
            {_PL1: "p2"},
        ),
        _grid(),
        registry,
    )
    client = _client(registry, state)

    view: dict[str, Any] = client.get("/tactical/invasion").json()
    assert view["active"] is True
    assert view["phase"] == InvasionPhase.COMMIT.value
    assert [(u["baseType"], u["count"]) for u in view["cargo"]] == [("infantry", 3)]
    planets = {p["planet"]: p for p in view["planets"]}
    assert set(planets) == {_PL1, _PL2}
    assert planets[_PL1]["owner"] == "p2"
    assert planets[_PL1]["structures"]["p2"][0]["baseType"] == "spacedock"

    bad = client.post(
        "/tactical/invasion/commit",
        json={"commits": [{"planet": _PL1, "baseType": "infantry", "count": 9}]},
    )
    assert bad.status_code == 422
    ok = client.post(
        "/tactical/invasion/commit",
        json={
            "commits": [
                {"planet": _PL1, "baseType": "infantry", "count": 2},
                {"planet": _PL2, "baseType": "infantry", "count": 1},
            ]
        },
    )
    assert ok.status_code == 200
    committed = client.get("/tactical/invasion").json()
    assert committed["cargo"] == []
    assert {p["planet"]: p["committed"] for p in committed["planets"]} == {
        _PL1: {"infantry": 2},
        _PL2: {"infantry": 1},
    }

    assert client.post("/tactical/invasion/next").status_code == 200  # → Establish
    done = client.get("/tactical/invasion").json()
    assert done["phase"] == InvasionPhase.ESTABLISH.value
    outcomes = {r["planet"]: r["outcome"] for r in done["results"]}
    assert outcomes == {_PL1: "captured", _PL2: "captured"}
    assert done["results"][0]["explore"] in (True, False)

    assert client.post("/tactical/invasion/next").status_code == 200  # zamknięcie
    assert client.get("/tactical/invasion").json()["active"] is False


def test_api_invasion_starts_on_button_and_is_simple_without_defenders(
    registry: StaticDataRegistry,
) -> None:
    state = _state({"p1": {"infantry": 2}})
    state.tactical_step = TacticalStep.SPACE_COMBAT
    client = _client(registry, state)
    assert client.post("/tactical/step/next").status_code == 200
    # Wejście w krok NIE otwiera inwazji - robi to przycisk.
    assert client.get("/tactical/invasion").json()["active"] is False
    assert client.post("/tactical/invasion/begin").status_code == 200
    view = client.get("/tactical/invasion").json()
    assert view["active"] is True
    assert view["simple"] is True
    assert view["phase"] == InvasionPhase.COMMIT.value
    # Z kroku INVASION nie wolno wyjść w trakcie inwazji.
    assert client.post("/tactical/step/next").status_code == 422


def test_api_invasion_not_simple_with_defenders_and_nothing_to_begin(
    registry: StaticDataRegistry,
) -> None:
    empty = _client(registry, _state({"p1": {"cruiser": 1}}))
    assert empty.post("/tactical/invasion/begin").status_code == 422
    state = _state(
        {"p1": {"infantry": 2}}, {_PL1: {"p2": {"infantry": 1}}}, {_PL1: "p2"}
    )
    client = _client(registry, state)
    assert client.post("/tactical/invasion/begin").status_code == 200
    assert client.get("/tactical/invasion").json()["simple"] is False
