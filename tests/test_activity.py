"""Testy feedu aktywności (``core.activity``) i endpointu ``/history/activity``."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.activity import derive_activity
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState
from src.core.registry import StaticDataRegistry


def _state() -> GameState:
    return GameState(
        round_number=2,
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", faction="arborec", color="green"),
            "p2": PlayerState(player_id="p2", faction="sol", color="blue"),
        },
    )


def test_strategy_pick_names_actor_and_card() -> None:
    after = _state()
    entry = derive_activity("strategy:pick:p2:3", _state(), after)
    assert entry is not None
    assert (entry.kind, entry.action) == ("strategy", "strategy.pick")
    assert entry.actor_id == "p2"
    assert entry.subject == "3"


def test_turn_pass_actor_is_previous_active_player() -> None:
    before = _state()
    after = _state()
    after.active_player_id = "p2"
    entry = derive_activity("turn:pass", before, after)
    assert entry is not None
    assert entry.actor_id == "p1"
    assert entry.target_id == "p2"


def test_internal_step_without_effect_is_hidden() -> None:
    assert derive_activity("tactical:step", _state(), _state()) is None


def test_internal_step_with_effect_surfaces_facts() -> None:
    before = _state()
    after = _state()
    after.players["p1"].technologies = ["neural_motivator"]
    entry = derive_activity("strategy:primary-step:p1", before, after)
    assert entry is not None
    assert entry.kind == "misc"
    assert [(f.type, f.player_id, f.value) for f in entry.facts] == [
        ("tech", "p1", "neural_motivator")
    ]


def test_vp_and_planet_facts_from_diff() -> None:
    before = _state()
    after = _state()
    after.players["p1"].victory_points = 1
    after.players["p1"].controlled_planets = ["jord"]
    entry = derive_activity("status:score:x", before, after)
    assert entry is not None
    types = {(f.type, f.value, f.delta) for f in entry.facts}
    assert ("vp", None, 1) in types
    assert ("planet_gained", "jord", None) in types


def test_godmode_without_effect_is_hidden() -> None:
    assert derive_activity("god-mode-patch", _state(), _state()) is None


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=_state())
    return TestClient(app)


def test_activity_endpoint_lists_players_and_entries(client: TestClient) -> None:
    client.post("/turn/pass")
    data = client.get("/history/activity").json()
    assert data["players"]["p1"]["faction"] == "arborec"
    actions = [e["activity"]["action"] for e in data["entries"]]
    assert "turn.pass" in actions
    assert all(e["created_at"] is not None for e in data["entries"])
