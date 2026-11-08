"""Testy szkieletu wieloetapowego primary + kosztu secondary (E8-T5, RULES.md 30.5/30.6)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import strategic_action, turn_flow
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState, WindowType
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    """Trzech graczy; p1 aktywny z kartą Trade (5), p2/p3 mają commodity_value 3 i 2."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2", "p3"],
        players={
            "p1": PlayerState(
                player_id="p1", color="red", strategy_cards=[5], commodity_value=4
            ),
            "p2": PlayerState(player_id="p2", color="green", commodity_value=3),
            "p3": PlayerState(player_id="p3", color="blue", commodity_value=2),
        },
    )


def test_trade_initiative_matches_registry(registry: StaticDataRegistry) -> None:
    cards = {c.name: c.initiative for c in registry.strategy_card_set()}
    assert cards["Trade"] == strategic_action._TRADE_INITIATIVE


def test_trade_play_waits_for_choice(registry: StaticDataRegistry) -> None:
    new = strategic_action.play_strategy_card(_state(), registry, "p1", 5)
    assert new.pending_strategy is not None
    assert new.pending_strategy.step == "choose_free_players"
    assert new.pending_window is None  # secondary dopiero po primary
    assert new.players["p1"].trade_goods == 0  # efekt jeszcze nie zastosowany


def test_end_turn_blocked_while_primary_pending(registry: StaticDataRegistry) -> None:
    new = strategic_action.play_strategy_card(_state(), registry, "p1", 5)
    with pytest.raises(ValueError, match="primary ability"):
        turn_flow.end_turn(new, "p1")


def test_primary_step_only_by_owner(registry: StaticDataRegistry) -> None:
    new = strategic_action.play_strategy_card(_state(), registry, "p1", 5)
    with pytest.raises(ValueError, match="Only p1"):
        strategic_action.submit_primary_step(new, registry, "p2", {"players": []})


@pytest.mark.parametrize(
    "payload",
    [{"players": ["p1"]}, {"players": ["zz"]}, {"players": ["p2", "p2"]}, {"players": "p2"}],
)
def test_primary_step_rejects_bad_payload(
    registry: StaticDataRegistry, payload: dict[str, object]
) -> None:
    new = strategic_action.play_strategy_card(_state(), registry, "p1", 5)
    with pytest.raises(ValueError):
        strategic_action.submit_primary_step(new, registry, "p1", payload)
    assert new.pending_strategy is not None  # stan nietknięty


def test_trade_primary_applies_and_opens_window(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(), registry, "p1", 5)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"players": ["p3"]})
    assert state.pending_strategy is None
    assert state.players["p1"].trade_goods == 3
    assert state.players["p1"].commodities == 4
    window = state.pending_window
    assert window is not None and window.window_type is WindowType.STRATEGY_SECONDARY
    assert window.queue == ["p2", "p3"]
    assert window.context == {"initiative": 5, "free": "p3", "cost": 1}


def _after_primary(registry: StaticDataRegistry, free: list[str]) -> GameState:
    state = strategic_action.play_strategy_card(_state(), registry, "p1", 5)
    return strategic_action.submit_primary_step(state, registry, "p1", {"players": free})


def test_follow_costs_strategy_token_and_replenishes(registry: StaticDataRegistry) -> None:
    state = _after_primary(registry, [])
    before = state.players["p2"]
    pool, reinf = before.strategic_cc, before.cc_reinf
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    assert state.players["p2"].commodities == 3
    assert state.players["p2"].strategic_cc == pool - 1
    assert state.players["p2"].cc_reinf == reinf + 1


def test_follow_without_token_rejected_but_pass_allowed(registry: StaticDataRegistry) -> None:
    state = _after_primary(registry, [])
    state.players["p2"].strategic_cc = 0
    with pytest.raises(ValueError, match="strategy pool"):
        strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    assert state.pending_window is not None and state.pending_window.cursor == 0
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=False)
    assert state.pending_window is not None and state.pending_window.cursor == 1


def test_free_player_follows_without_token_and_cannot_pass(
    registry: StaticDataRegistry,
) -> None:
    state = _after_primary(registry, ["p2"])
    state.players["p2"].strategic_cc = 0
    with pytest.raises(ValueError, match="must resolve"):
        strategic_action.resolve_secondary(state, registry, "p2", execute=False)
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    assert state.players["p2"].commodities == 3
    assert state.players["p2"].strategic_cc == 0


def test_passed_player_can_still_follow(registry: StaticDataRegistry) -> None:
    state = _after_primary(registry, [])
    state.players["p2"].passed = True
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    assert state.players["p2"].commodities == 3


def test_leadership_secondary_costs_nothing(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].strategy_cards = [1]
    state = strategic_action.play_strategy_card(state, registry, "p1", 1)
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    state = strategic_action.submit_primary_step(state, registry, "p1", {"tactical": 3})
    pool = state.players["p2"].strategic_cc
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    assert state.players["p2"].strategic_cc == pool


def test_trade_solo_without_respondents_opens_no_window(registry: StaticDataRegistry) -> None:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1"],
        players={"p1": PlayerState(player_id="p1", color="red", strategy_cards=[5])},
    )
    state = strategic_action.play_strategy_card(state, registry, "p1", 5)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"players": []})
    assert state.pending_window is None and state.pending_strategy is None
    assert state.players["p1"].trade_goods == 3


def test_api_primary_step_flow(registry: StaticDataRegistry) -> None:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=_state())
    client = TestClient(app)
    played = client.post("/strategy/play", json={"player_id": "p1", "initiative": 5})
    assert played.status_code == 200
    data = client.get("/api/public/game/g/web-data").json()["gameState"]
    assert data["pendingStrategy"]["step"] == "choose_free_players"
    assert data["pendingStrategy"]["ownerId"] == "p1"
    bad = client.post(
        "/strategy/primary-step", json={"player_id": "p2", "payload": {"players": []}}
    )
    assert bad.status_code == 422
    ok = client.post(
        "/strategy/primary-step", json={"player_id": "p1", "payload": {"players": ["p2"]}}
    )
    assert ok.status_code == 200
    data = client.get("/api/public/game/g/web-data").json()["gameState"]
    assert data["pendingStrategy"] is None
    assert data["pendingWindow"]["windowType"] == "STRATEGY_SECONDARY"
    assert data["pendingWindow"]["context"]["free"] == "p2"
