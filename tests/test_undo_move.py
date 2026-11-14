"""„Undo last move” aktywnego gracza (RULES.md 44.1a) i wyłączenie limitu ręki (53.8)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.actor import ACTOR_HEADER
from src.api.app import create_app
from src.core import hand_limit, rules_hooks
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _client(registry: StaticDataRegistry) -> TestClient:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={
            "p1": PlayerState(player_id="p1", faction="sol", color="red"),
            "p2": PlayerState(player_id="p2", faction="arborec", color="blue"),
        },
        systems={
            "101": SystemState(
                position="101", system_id="20", space_units={"p1": {"carrier": 1}}
            )
        },
    )
    return TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    )


def _move(client: TestClient) -> None:
    res = client.post(
        "/tactical/move",
        json={
            "faction": "sol",
            "fromPosition": "101",
            "ships": [{"baseType": "carrier", "count": 1}],
        },
        headers={ACTOR_HEADER: "p1"},
    )
    assert res.status_code == 200, res.text


def _carrier_at(client: TestClient, position: str) -> int:
    systems = client.get("/state").json()["state"]["systems"]
    return int(systems.get(position, {}).get("space_units", {}).get("p1", {}).get("carrier", 0))


def test_active_player_undoes_own_move(registry: StaticDataRegistry) -> None:
    client = _client(registry)
    _move(client)
    assert _carrier_at(client, "000") == 1
    # Inny gracz nie cofnie cudzego ruchu.
    other = client.post("/tactical/undo-move", headers={ACTOR_HEADER: "p2"})
    assert other.status_code == 403
    res = client.post("/tactical/undo-move", headers={ACTOR_HEADER: "p1"})
    assert res.status_code == 200
    assert _carrier_at(client, "101") == 1 and _carrier_at(client, "000") == 0
    # Ostatnia zmiana nie jest już ruchem — nic do cofnięcia.
    again = client.post("/tactical/undo-move", headers={ACTOR_HEADER: "p1"})
    assert again.status_code == 422


def test_hand_limit_can_be_disabled(registry: StaticDataRegistry) -> None:
    state = GameState(players={"p1": PlayerState(player_id="p1")})
    rules_hooks.bind_registry(registry)
    assert hand_limit.action_card_limit(state, "p1") is not None
    state.action_card_limit_disabled = True
    assert hand_limit.action_card_limit(state, "p1") is None
    assert hand_limit.action_card_excess(state, "p1") == 0
