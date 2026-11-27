"""Queued strategy card secondary decisions (parallel queueing) - RULES.md 30.13."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import strategic_action, visibility
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState, WindowType
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _four() -> GameState:
    """p1 active with Leadership; p2, p3, p4 answer clockwise."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2", "p3", "p4"],
        players={
            "p1": PlayerState(player_id="p1", color="red", strategy_cards=[1]),
            "p2": PlayerState(player_id="p2", color="green"),
            "p3": PlayerState(player_id="p3", color="blue"),
            "p4": PlayerState(player_id="p4", color="yellow"),
        },
    )


def _played(registry: StaticDataRegistry) -> GameState:
    """Leadership played, primary still being resolved."""
    return strategic_action.play_strategy_card(_four(), registry, "p1", 1)


def _finish_primary(state: GameState, registry: StaticDataRegistry) -> GameState:
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    return strategic_action.submit_primary_step(state, registry, "p1", {"tactical": 3})


def test_players_may_queue_while_the_primary_resolves(registry: StaticDataRegistry) -> None:
    state = _played(registry)
    assert strategic_action.queue_order(state) == (1, ["p2", "p3", "p4"])
    options = strategic_action.queue_options(state, registry, "p3")
    assert options is not None and options["ahead"] == ["p2"] and options["queued"] is None
    assert strategic_action.queue_options(state, registry, "p1") is None  # the active player
    with pytest.raises(ValueError, match="not waiting"):
        strategic_action.queue_secondary(state, "p1", execute=False)


def test_queued_decisions_resolve_in_clockwise_order(registry: StaticDataRegistry) -> None:
    state = _played(registry)
    state = strategic_action.queue_secondary(state, "p3", execute=False)
    state = strategic_action.queue_secondary(state, "p4", execute=False)
    state = _finish_primary(state, registry)
    window = state.pending_window
    assert window is not None and window.window_type is WindowType.STRATEGY_SECONDARY
    assert window.current_responder == "p2"  # p2 did not queue: the order is kept
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=False)
    assert state.pending_window is None  # p3 and p4 resolved right after, in order
    assert state.secondary_queue == {}


def test_queue_again_replaces_and_unqueue_withdraws(registry: StaticDataRegistry) -> None:
    state = _played(registry)
    state = strategic_action.queue_secondary(state, "p2", execute=True)
    state = strategic_action.queue_secondary(state, "p2", execute=False)
    assert state.secondary_queue["p2"].execute is False
    withdrawn = strategic_action.cancel_queued_secondary(state, "p2")
    assert withdrawn.secondary_queue == {}
    assert strategic_action.cancel_queued_secondary(withdrawn, "p2") is withdrawn


def test_illegal_queued_decision_falls_back_to_asking(registry: StaticDataRegistry) -> None:
    """A queued Follow that no longer fits (3 tokens without the influence to pay for them) is
    dropped when the window reaches the player, who is then asked normally."""
    state = _played(registry)
    state = strategic_action.queue_secondary(state, "p2", execute=True, payload={"tactical": 3})
    state = _finish_primary(state, registry)
    window = state.pending_window
    assert window is not None and window.current_responder == "p2"
    assert "p2" not in state.secondary_queue


def test_queue_is_private_until_it_resolves(registry: StaticDataRegistry) -> None:
    state = strategic_action.queue_secondary(_played(registry), "p3", execute=True)
    mine = state.clone()
    visibility.redact_reaction_windows(mine, "p3")
    assert mine.secondary_queue["p3"].execute is True
    theirs = state.clone()
    visibility.redact_reaction_windows(theirs, "p2")
    queued = theirs.secondary_queue["p3"]
    assert queued.hidden and queued.execute is False and queued.payload == {}


def test_new_strategic_action_clears_the_queue(registry: StaticDataRegistry) -> None:
    state = strategic_action.queue_secondary(_played(registry), "p3", execute=False)
    state = _finish_primary(state, registry)
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=False)
    assert state.secondary_queue == {}


def test_nothing_to_queue_outside_a_strategic_action(registry: StaticDataRegistry) -> None:
    assert strategic_action.queue_order(_four()) is None
    with pytest.raises(ValueError, match="No strategy card"):
        strategic_action.queue_secondary(_four(), "p2", execute=False)


def test_api_queue_endpoints(registry: StaticDataRegistry) -> None:
    app = create_app(
        registry=registry, store=EventStore(":memory:"), initial_state=_played(registry)
    )
    client, service = TestClient(app), app.state.service
    options = client.get("/strategy/queue-options", params={"player_id": "p3"}).json()
    assert options["initiative"] == 1 and options["ahead"] == ["p2"]
    body = {"player_id": "p3", "execute": False}
    assert client.post("/strategy/secondary/queue", json=body,
                       headers={"X-Actor-Id": "p3"}).status_code == 200
    assert "p3" in service.current_state().secondary_queue
    assert client.post("/strategy/secondary/unqueue", json=body,
                       headers={"X-Actor-Id": "p3"}).status_code == 200
    assert service.current_state().secondary_queue == {}
    bad = client.post("/strategy/secondary/queue", json={"player_id": "p1", "execute": False},
                      headers={"X-Actor-Id": "p1"})
    assert bad.status_code == 422
