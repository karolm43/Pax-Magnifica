"""Testy czytelnych komunikatów błędów (core/error_text + middleware API)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import error_text
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="sol"),
            "p10": PlayerState(player_id="p10", color="blue", faction="arborec"),
        },
    )


def test_humanize_replaces_player_ids_with_faction_and_colour(
    registry: StaticDataRegistry,
) -> None:
    text = error_text.humanize("It is not p10's turn (active: p1).", _state(), registry)
    assert "p10" not in text and "p1)" not in text
    assert "(blue)" in text and "(red)" in text


def test_humanize_leaves_words_that_only_contain_an_id(registry: StaticDataRegistry) -> None:
    assert error_text.humanize("p1x and step-p1 stay", _state(), registry) == "p1x and step-p1 stay"


def test_validation_errors_are_flattened() -> None:
    text = error_text.flatten_validation_errors(
        [{"loc": ("body", "faction"), "msg": "Field required"}]
    )
    assert text == "The request is invalid - faction: Field required."


def test_api_humanizes_rule_errors_for_the_player(registry: StaticDataRegistry) -> None:
    client = TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=_state())
    )
    response = client.post(
        "/tactical/fleet-pool/resolve", json={"faction": "p1", "remove": []}
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, str) and "No fleet pool check is pending" in detail


def test_api_validation_error_detail_is_a_string(registry: StaticDataRegistry) -> None:
    client = TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=_state())
    )
    response = client.post("/tactical/fleet-pool/resolve", json={"remove": "oops"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
