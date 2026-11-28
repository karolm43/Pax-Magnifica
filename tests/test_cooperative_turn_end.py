"""Turn-end cooperative effects requested during the turn, and debt-token payments - RULES.md
54.15 f (Garv and Gunn, Field Marshal Mercer)."""

from __future__ import annotations

from typing import Any

import pytest

from src.core import cooperative, offers, rules_hooks, triggers
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from tests.factions.test_naaz import THIBAH, _state
from tests.rulings import ruling

GARV = "Garv and Gunn"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _p2_turn(acted: bool = True) -> GameState:
    """p1 = Naaz-Rokha (Garv and Gunn ready), p2 = the active player with Thibah to explore."""
    state = _state()
    state.active_player_id = "p2"
    state.players["p2"].took_action_this_turn = acted
    return state


def _rows(state: GameState, registry: StaticDataRegistry, pid: str = "p2") -> list[dict[str, Any]]:
    return cooperative.available(state, registry, grid_from_state(state, registry), pid)


def _request(state: GameState, registry: StaticDataRegistry, **pay: int) -> GameState:
    row = next(r for r in _rows(state, registry) if r["name"] == GARV)
    return cooperative.request(
        state, registry, grid_from_state(state, registry), "p2", row["id"], now=0.0, **pay
    )


def _accept_deal(state: GameState, registry: StaticDataRegistry, pid: str = "p1") -> GameState:
    offer = cooperative.deals(state)[0][0]
    return offers.accept(state, grid_from_state(state, registry), registry, pid, offer.id, {})


@ruling("leaders:naazagent#1")
def test_garv_and_gunn_is_a_boost_during_my_turn(registry: StaticDataRegistry) -> None:
    assert GARV not in [r["name"] for r in _rows(_p2_turn(acted=False), registry)]
    state = _p2_turn()
    assert [r["name"] for r in _rows(state, registry)] == [GARV]
    assert _rows(state, registry, "p1") == []  # never offered to its owner as a boost
    state = _accept_deal(_request(state, registry), registry)
    assert state.players["p1"].leader_states.get("naazagent") == "exhausted"
    explore = [o for o in triggers.offers_for(state, "p2") if "explore 1 of your" in o.label]
    assert explore, "the player whose turn it is picks the planet"
    state = triggers.accept_offer(state, "p2", explore[0].id, {"planet": THIBAH})
    assert state.exploration is not None and state.exploration.player_id == "p2"
    assert _rows(state, registry) == []  # exhausted: gone


def test_turn_end_boost_not_listed_on_someone_elses_turn(registry: StaticDataRegistry) -> None:
    state = _p2_turn()
    state.active_player_id = "p1"
    assert _rows(state, registry) == []


@ruling("R_deals/rules-reference/1")
def test_debt_tokens_pay_without_a_transaction(registry: StaticDataRegistry) -> None:
    state = _p2_turn()
    state.players["p2"].transacted_with = ["p1"]  # no transaction between them this turn
    state.players["p2"].trade_goods = 3
    row = _rows(state, registry)[0]
    assert row["payable"] is False  # no trade goods / commodities now
    with pytest.raises(ValueError, match="transaction"):
        _request(state, registry, trade_goods=1)
    state = _request(state, registry, debt_tokens=2)
    view = cooperative.deal_view(cooperative.deals(state)[0][0])
    assert view is not None and view["debtTokens"] == 2
    assert state.debt_tokens == {}  # nothing given before the owner accepts
    after = _accept_deal(state, registry)
    assert after.debt_tokens == {"p1": {"p2": 2}}  # p2's tokens held by the Naaz-Rokha
    assert after.players["p1"].trade_goods == 0


def test_debt_tokens_count_towards_a_standing_price(registry: StaticDataRegistry) -> None:
    state = cooperative.configure(
        _p2_turn(), "p1", "leaders:naazagent", mode=cooperative.STANDING, price=2
    )
    state = _request(state, registry, debt_tokens=2)
    offer = cooperative.deals(state)[0][0]
    assert offer.player_id == "p2"  # accepted at once: the requester confirms
    after = _accept_deal(state, registry, "p2")
    assert after.debt_tokens == {"p1": {"p2": 2}}
    assert after.players["p1"].leader_states.get("naazagent") == "exhausted"


def test_declined_deal_gives_no_debt_tokens(registry: StaticDataRegistry) -> None:
    state = _request(_p2_turn(), registry, debt_tokens=3)
    offer = cooperative.deals(state)[0][0]
    after = offers.decline(state, grid_from_state(state, registry), registry, "p1", offer.id)
    assert after.debt_tokens == {} and cooperative.deals(after) == []
