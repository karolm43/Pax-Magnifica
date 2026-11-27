"""Push vs Pull: cooperative effects ("boosts") and atomic binding deals - RULES.md 54.15."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import (
    cooperative,
    faction_components,
    offers,
    rules_hooks,
    step_settle,
    triggers,
)
from src.core.event_store import EventStore
from src.core.game_state import ControlType, GameState
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from tests.factions.test_saar import FAR, PLAIN, RIVAL, _activate, _mendosa_state
from tests.rulings import ruling

MENDOSA = "leaders:saaragent"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _neighbours(state: GameState) -> GameState:
    """p2 also has a destroyer next to Saar's home: the two are neighbours (paid deals)."""
    state.systems[PLAIN].space_units = {"p2": {"destroyer": 1}}
    state.players["p2"].trade_goods = 5
    state.players["p2"].commodities = 2
    return state


def _activated(registry: StaticDataRegistry, **owner: Any) -> GameState:
    state = _neighbours(_mendosa_state())
    if owner:
        state = cooperative.configure(state, "p1", MENDOSA, **owner)
    return _activate(state, registry, FAR, pid="p2")


def _boost(state: GameState, registry: StaticDataRegistry, pid: str = "p2") -> dict[str, Any]:
    rows = cooperative.available(state, registry, grid_from_state(state, registry), pid)
    assert [r["name"] for r in rows] == ["Captain Mendosa"]
    return rows[0]


def _request(state: GameState, registry: StaticDataRegistry, tg: int = 0, comm: int = 0,
             now: float = 100.0) -> GameState:
    row = _boost(state, registry)
    return cooperative.request(
        state, registry, grid_from_state(state, registry), "p2", row["id"],
        trade_goods=tg, commodities=comm, now=now,
    )


def _deal(state: GameState) -> Any:
    found = cooperative.deals(state)
    assert len(found) == 1
    return found[0][0]


def _accept(state: GameState, registry: StaticDataRegistry, pid: str,
            params: dict[str, Any] | None = None) -> GameState:
    offer = _deal(state)
    grid = grid_from_state(state, registry)
    return offers.accept(state, grid, registry, pid, offer.id,
                         params if params is not None else {"ship": f"{RIVAL}|dreadnought"})


# --- Pull: no blocking window on another player's event ------------------------------------------


def test_pull_agent_does_not_ask_the_owner_on_another_players_event(
    registry: StaticDataRegistry,
) -> None:
    state = _activated(registry)
    assert triggers.offers_for(state, "p1") == []
    assert state.pending_window is None  # nothing blocks the active player
    row = _boost(state, registry)
    assert row["owner"] == "p1" and row["mode"] == cooperative.ASK and row["payable"]


def test_owner_using_it_on_their_own_activation_keeps_the_offer(
    registry: StaticDataRegistry,
) -> None:
    state = _mendosa_state()
    state.systems[PLAIN].space_units = {"p1": {"destroyer": 1}}
    state = _activate(state, registry, FAR, pid="p1")
    assert [o.label for o in triggers.offers_for(state, "p1")] == [
        "Captain Mendosa: increase a ship's move value"
    ]
    assert state.boosts == []


def test_push_agent_still_offers_the_owner(registry: StaticDataRegistry) -> None:
    """Cabal's agent is hostile ("capture 1 unit from their reinforcements") - not pull."""
    assert not cooperative.is_pull("leaders:cabalagent")
    assert cooperative.is_pull(MENDOSA)
    assert cooperative.is_pull("leaders:winnuagent")


# --- Ask me: request -> owner decides -> atomic --------------------------------------------------


@ruling("leaders:saaragent#1", "R_deals/rules-reference/3", "R_deals/notes/1")
def test_ask_request_paid_deal_is_atomic(registry: StaticDataRegistry) -> None:
    state = _request(_activated(registry), registry, tg=2, comm=1)
    offer = _deal(state)
    assert offer.player_id == "p1" and state.pending_window is not None  # the owner decides
    assert state.players["p2"].trade_goods == 5  # nothing paid yet
    after = _accept(state, registry, "p1")
    assert after.players["p1"].leader_states["saaragent"] == "exhausted"
    assert after.players["p2"].trade_goods == 3 and after.players["p2"].commodities == 1
    assert after.players["p1"].trade_goods == 3  # 2 TG + 1 commodity -> 3 TG
    assert "p1" in after.players["p2"].transacted_with  # a normal transaction (R_deals)
    assert after.pending_window is None and after.boosts == []


def test_declined_request_transfers_nothing(registry: StaticDataRegistry) -> None:
    state = _request(_activated(registry), registry, tg=2)
    grid = grid_from_state(state, registry)
    after = offers.decline(state, grid, registry, "p1", _deal(state).id)
    assert after.players["p2"].trade_goods == 5 and after.players["p1"].trade_goods == 0
    assert after.players["p1"].leader_states["saaragent"] == "unlocked"
    assert cooperative.deals(after) == [] and after.pending_window is None


def test_requester_can_withdraw(registry: StaticDataRegistry) -> None:
    state = _request(_activated(registry), registry, tg=1)
    after = cooperative.decline(state, "p2", _deal(state).id)
    assert cooperative.deals(after) == [] and after.players["p2"].trade_goods == 5


def test_unanswered_request_lapses(registry: StaticDataRegistry) -> None:
    state = _request(_activated(registry), registry, tg=1, now=100.0)
    assert cooperative.expire(state, 105.0) is state
    after = cooperative.expire(state, 100.0 + state.reaction_window_seconds)
    assert cooperative.deals(after) == [] and after.players["p2"].trade_goods == 5


@ruling("R_deals/rules-reference/2")
def test_failed_effect_changes_nothing(registry: StaticDataRegistry) -> None:
    """Atomic: the effect fails (a ship that is not an option) - the payment is not made."""
    state = _request(_activated(registry), registry, tg=2)
    with pytest.raises(ValueError):
        _accept(state, registry, "p1", {"ship": "000|warsun"})
    assert state.players["p2"].trade_goods == 5


@ruling("R_deals/rules-reference/1")
def test_paid_deal_needs_a_legal_transaction(registry: StaticDataRegistry) -> None:
    state = _mendosa_state()  # not neighbours
    state.players["p2"].trade_goods = 5
    state = _activate(state, registry, FAR, pid="p2")
    assert _boost(state, registry)["payable"] is False
    with pytest.raises(ValueError, match="transaction"):
        _request(state, registry, tg=1)
    free = _request(state, registry)  # a free deal is always possible
    assert _accept(free, registry, "p1").players["p1"].leader_states["saaragent"] == "exhausted"


def test_one_request_at_a_time(registry: StaticDataRegistry) -> None:
    state = _request(_activated(registry), registry)
    with pytest.raises(ValueError, match="already"):
        _request(state, registry)


# --- Standing offer / Self-only ------------------------------------------------------------------


def test_standing_offer_goes_to_the_requester(registry: StaticDataRegistry) -> None:
    state = _activated(registry, mode=cooperative.STANDING, price=2)
    row = _boost(state, registry)
    assert row["mode"] == cooperative.STANDING and row["price"] == 2 and not row["free"]
    state = _request(state, registry, tg=2)
    offer = _deal(state)
    assert offer.player_id == "p2" and offer.owner_id == "p1"  # p2 picks the ship
    after = _accept(state, registry, "p2")
    assert after.players["p1"].trade_goods == 2 and after.players["p2"].trade_goods == 3
    assert after.players["p1"].leader_states["saaragent"] == "exhausted"


def test_standing_offer_below_price_asks_the_owner(registry: StaticDataRegistry) -> None:
    state = _request(_activated(registry, mode=cooperative.STANDING, price=3), registry, tg=1)
    assert _deal(state).player_id == "p1"


def test_standing_offer_free_for_allies(registry: StaticDataRegistry) -> None:
    state = _activated(registry, mode=cooperative.STANDING, price=3, free_for=["p2"])
    assert _boost(state, registry)["free"] is True
    state = _request(state, registry)
    assert _deal(state).player_id == "p2"
    assert _accept(state, registry, "p2").players["p2"].trade_goods == 5


def test_self_only_is_never_listed(registry: StaticDataRegistry) -> None:
    state = _activated(registry, mode=cooperative.SELF)
    grid = grid_from_state(state, registry)
    assert cooperative.available(state, registry, grid, "p2") == []
    assert state.boosts == [] and triggers.offers_for(state, "p1") == []


def test_configure_validates(registry: StaticDataRegistry) -> None:
    state = _mendosa_state()
    with pytest.raises(ValueError, match="cooperative"):
        cooperative.configure(state, "p1", "leaders:cabalagent", mode=cooperative.ASK)
    with pytest.raises(ValueError, match="mode"):
        cooperative.configure(state, "p1", MENDOSA, mode="maybe")
    with pytest.raises(ValueError, match="price"):
        cooperative.configure(state, "p1", MENDOSA, mode=cooperative.STANDING, price=99)
    rows = cooperative.owned(state, registry, "p1")
    assert [(r["source"], r["mode"]) for r in rows] == [(MENDOSA, cooperative.ASK)]


# --- Lifetime, bots, Watch -----------------------------------------------------------------------


def test_boost_lapses_when_the_game_moves_on(registry: StaticDataRegistry) -> None:
    before = _activated(registry)
    kept = step_settle.settle_step(before, registry, 0.0, "boost:request", before=before)
    assert kept.boosts != []
    moved = step_settle.settle_step(before, registry, 0.0, "tactical:move", before=before)
    assert moved.boosts == []


def test_exhausted_agent_is_not_listed(registry: StaticDataRegistry) -> None:
    state = _activated(registry)
    state.players["p1"].leader_states["saaragent"] = "exhausted"
    assert cooperative.available(state, registry, grid_from_state(state, registry), "p2") == []


def test_bot_owner_accepts_a_paid_request(registry: StaticDataRegistry) -> None:
    state = _activated(registry)
    state.players["p1"].control_type = ControlType.BOT
    with pytest.raises(ValueError, match="declines"):
        _request(state, registry)
    paid = _request(state, registry, tg=1)
    assert _deal(paid).player_id == "p2"  # accepted: the requester picks the details


def test_watch_restores_the_unprompted_offer(registry: StaticDataRegistry) -> None:
    state = _neighbours(_mendosa_state())
    state.active_player_id = "p2"
    state = cooperative.set_watch(state, "p1", "turn")
    assert cooperative.watching(state, "p1")
    state = _activate(state, registry, FAR, pid="p2")
    assert len(triggers.offers_for(state, "p1")) == 1 and state.boosts == []
    off = cooperative.set_watch(state, "p1", None)
    assert not cooperative.watching(off, "p1")
    with pytest.raises(ValueError):
        cooperative.set_watch(state, "p1", "forever")


def test_watch_lapses_with_the_turn(registry: StaticDataRegistry) -> None:
    state = _mendosa_state()
    state.active_player_id = "p2"
    state = cooperative.set_watch(state, "p1", "turn")
    state.active_player_id = "p1"
    assert not cooperative.watching(state, "p1")
    cooperative.prune_watch(state)
    assert state.players["p1"].private.reaction_prefs.watch is None


# --- Window-use components (Berekar Berekon) -----------------------------------------------------


def test_window_component_helping_only_others_is_not_prompted(
    registry: StaticDataRegistry,
) -> None:
    state = _mendosa_state()
    key = faction_components.effect_key("leader", "winnuagent")
    assert cooperative.component_for_others(state, "p1", key) is False  # nobody produces
    helps = cooperative._PULL_COMPONENTS[key]
    try:
        cooperative._PULL_COMPONENTS[key] = lambda _s, _o: ["p2"]
        assert cooperative.component_for_others(state, "p1", key) is True
        cooperative._PULL_COMPONENTS[key] = lambda _s, _o: ["p1"]
        assert cooperative.component_for_others(state, "p1", key) is False  # own production
        cooperative._PULL_COMPONENTS[key] = lambda _s, _o: ["p2"]
        watched = cooperative.set_watch(state, "p1", "turn")
        assert cooperative.component_for_others(watched, "p1", key) is False
    finally:
        cooperative._PULL_COMPONENTS[key] = helps


# --- API -----------------------------------------------------------------------------------------


def test_api_boost_flow(registry: StaticDataRegistry) -> None:
    state = _activated(registry)
    clock = [100.0]
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state,
                     now=lambda: clock[0])
    client, service = TestClient(app), app.state.service
    listing = client.get("/boosts", params={"player_id": "p2"}).json()
    assert [r["name"] for r in listing["available"]] == ["Captain Mendosa"]
    boost_id = listing["available"][0]["id"]
    owned = client.get("/boosts", params={"player_id": "p1"}).json()["owned"]
    assert owned[0]["source"] == MENDOSA
    body = {"player_id": "p2", "boost_id": boost_id, "trade_goods": 1}
    response = client.post("/boosts/request", json=body, headers={"X-Actor-Id": "p2"})
    assert response.status_code == 200, response.text
    outgoing = client.get("/boosts", params={"player_id": "p2"}).json()["outgoing"]
    assert outgoing[0]["owner"] == "p1" and outgoing[0]["tradeGoods"] == 1
    offer_view = client.get("/offers", params={"player_id": "p1"}).json()["offers"][0]
    assert offer_view["deal"]["requester"] == "p2" and offer_view["name"] == "Captain Mendosa"
    accept = {"actor_id": "p1", "offer_id": offer_view["id"],
              "params": {"ship": f"{RIVAL}|dreadnought"}}
    assert client.post("/offers/accept", json=accept).status_code == 200
    current = service.current_state()
    assert current.players["p1"].trade_goods == 1
    assert current.players["p1"].leader_states["saaragent"] == "exhausted"
    settings = {"player_id": "p1", "source": MENDOSA, "mode": "standing", "price": 2}
    assert client.post("/boosts/settings", json=settings,
                       headers={"X-Actor-Id": "p1"}).status_code == 200
    bad = {"player_id": "p1", "source": MENDOSA, "mode": "x"}
    headers = {"X-Actor-Id": "p1"}
    assert client.post("/boosts/settings", json=bad, headers=headers).status_code == 422
    watch = {"player_id": "p1", "until": "turn"}
    assert client.post("/boosts/watch", json=watch, headers=headers).status_code == 200
    assert client.get("/boosts", params={"player_id": "p1"}).json()["watch"] == "turn"


def test_api_unanswered_request_lapses_on_the_next_post(registry: StaticDataRegistry) -> None:
    state = _activated(registry)
    clock = [100.0]
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state,
                     now=lambda: clock[0])
    client, service = TestClient(app), app.state.service
    boost_id = client.get("/boosts", params={"player_id": "p2"}).json()["available"][0]["id"]
    body = {"player_id": "p2", "boost_id": boost_id, "trade_goods": 1}
    assert client.post("/boosts/request", json=body,
                       headers={"X-Actor-Id": "p2"}).status_code == 200
    clock[0] = 100.0 + state.reaction_window_seconds + 1
    client.post("/boosts/watch", json={"player_id": "p1", "until": None},
                headers={"X-Actor-Id": "p1"})
    current = service.current_state()
    assert cooperative.deals(current) == [] and current.players["p2"].trade_goods == 5
