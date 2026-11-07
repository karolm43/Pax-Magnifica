"""Testy transakcji między graczami i żetonów obietnic — RULES.md 47.

Reguła (tirules2.com → ``docs/rules_tirules/R_transactions.md``): aktywny gracz robi do jednej
transakcji z każdym sąsiadem w turze; oddaje TG/commodities (+1 notka), dostaje TG/commodities/
fragmenty (+1 notka); commodity staje się u odbiorcy trade goodem.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import promises, transaction, turn_flow
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.transaction import TransactionSide


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18")
    for pos in ("101", "102"):
        grid.place_system(pos, "20")
    grid.build_edges()
    return grid


def _state() -> GameState:
    """p1 (aktywny) sąsiaduje z p2 (ten sam system); p3 jest daleko (brak obecności)."""
    p1 = PlayerState(player_id="p1", color="red", trade_goods=3, commodities=2)
    p1.private.promissory_notes = ["red_ceasefire"]
    p2 = PlayerState(player_id="p2", color="blue", trade_goods=1, commodities=2)
    p2.relic_fragments = ["crf1"]
    p2.private.promissory_notes = ["blue_sftt", "blue_ps"]
    p3 = PlayerState(player_id="p3", color="green")
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2", "p3"],
        players={"p1": p1, "p2": p2, "p3": p3},
        systems={
            "000": SystemState(
                position="000",
                system_id="18",
                space_units={"p1": {"cruiser": 1}, "p2": {"cruiser": 1}},
            ),
        },
    )


def test_transaction_moves_goods_and_converts_commodities() -> None:
    state = _state()
    new = transaction.resolve_transaction(
        state,
        _grid(),
        "p2",
        give=TransactionSide(trade_goods=2, commodities=1, promissory_note="red_ceasefire"),
        receive=TransactionSide(
            commodities=2, promissory_note="blue_ps", relic_fragments=("crf1",)
        ),
    )
    p1, p2 = new.players["p1"], new.players["p2"]
    # p1: 3-2 TG + 2 przyjęte commodities (-> TG); commodities 2-1.
    assert (p1.trade_goods, p1.commodities) == (3, 1)
    # p2: 1 + 2 + 1 = 4 TG (commodity od p1 -> TG); oddał 2 commodities.
    assert (p2.trade_goods, p2.commodities) == (4, 0)
    assert p1.private.promissory_notes == ["blue_ps"]
    assert p2.private.promissory_notes == ["blue_sftt", "red_ceasefire"]
    assert p1.relic_fragments == ["crf1"] and p2.relic_fragments == []
    assert p1.transacted_with == ["p2"]
    # Czysta funkcja: wejście bez zmian.
    assert state.players["p1"].trade_goods == 3


def test_one_transaction_per_neighbor_per_turn() -> None:
    first = transaction.resolve_transaction(
        _state(), _grid(), "p2", TransactionSide(trade_goods=1), TransactionSide()
    )
    with pytest.raises(ValueError, match="already made a transaction"):
        transaction.resolve_transaction(
            first, _grid(), "p2", TransactionSide(trade_goods=1), TransactionSide()
        )


def test_non_neighbor_rejected() -> None:
    with pytest.raises(ValueError, match="neighbor"):
        transaction.resolve_transaction(
            _state(), _grid(), "p3", TransactionSide(trade_goods=1), TransactionSide()
        )


def test_cannot_give_more_than_owned() -> None:
    with pytest.raises(ValueError, match="trade goods"):
        transaction.resolve_transaction(
            _state(), _grid(), "p2", TransactionSide(trade_goods=9), TransactionSide()
        )
    with pytest.raises(ValueError, match="relic fragment"):
        transaction.resolve_transaction(
            _state(), _grid(), "p2", TransactionSide(), TransactionSide(relic_fragments=("x",))
        )
    with pytest.raises(ValueError, match="promissory note"):
        transaction.resolve_transaction(
            _state(),
            _grid(),
            "p2",
            TransactionSide(promissory_note="blue_ps"),
            TransactionSide(),
        )


def test_empty_and_wrong_phase_and_wrong_player_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        transaction.resolve_transaction(
            _state(), _grid(), "p2", TransactionSide(), TransactionSide()
        )
    state = _state()
    state.phase = Phase.STRATEGY
    with pytest.raises(ValueError, match="action phase"):
        transaction.resolve_transaction(
            state, _grid(), "p2", TransactionSide(trade_goods=1), TransactionSide()
        )
    with pytest.raises(ValueError, match="not p2's turn"):
        transaction.resolve_transaction(
            _state(), _grid(), "p1", TransactionSide(trade_goods=1), TransactionSide(), "p2"
        )


def test_allowed_during_open_timing_window_and_after_pass() -> None:
    """Transakcję wolno rozstrzygnąć w dowolnym momencie tury (także w trakcie walki)."""
    state = _state()
    state.players["p1"].passed = True
    new = transaction.resolve_transaction(
        state, _grid(), "p2", TransactionSide(trade_goods=1), TransactionSide()
    )
    assert new.players["p2"].trade_goods == 2


def test_new_turn_resets_transacted_with() -> None:
    state = transaction.resolve_transaction(
        _state(), _grid(), "p2", TransactionSide(trade_goods=1), TransactionSide()
    )
    state.players["p1"].took_action_this_turn = True
    state.players["p1"].strategy_cards = [1]
    state.players["p2"].strategy_cards = [2]
    state.players["p3"].strategy_cards = [3]
    after = turn_flow.end_turn(state, "p1")
    assert after.players["p1"].transacted_with == ["p2"]  # reset dopiero w jego NASTĘPNEJ turze
    assert after.players["p2"].transacted_with == []


def test_promise_tokens_give_and_return() -> None:
    state = _state()
    state = promises.give_promise_tokens(state, "p1", "p2", 3)
    state = promises.give_promise_tokens(state, "p1", "p2", 1)
    assert state.promise_tokens == {"p2": {"p1": 4}}
    state = promises.return_promise_tokens(state, "p2", "p1", 3)
    assert promises.held_tokens(state, "p2", "p1") == 1
    state = promises.return_promise_tokens(state, "p2", "p1", 1)
    assert state.promise_tokens == {}


def test_promise_tokens_validation_and_no_neighbor_needed() -> None:
    state = _state()
    # p3 nie jest sąsiadem p1 — obietnice i tak działają (nie reguła TI4).
    assert promises.give_promise_tokens(state, "p1", "p3", 2).promise_tokens == {"p3": {"p1": 2}}
    with pytest.raises(ValueError, match="only 0 held"):
        promises.return_promise_tokens(state, "p2", "p1", 1)
    with pytest.raises(ValueError, match="at least 1"):
        promises.give_promise_tokens(state, "p1", "p2", 0)
    with pytest.raises(ValueError, match="different players"):
        promises.give_promise_tokens(state, "p1", "p1", 1)
    with pytest.raises(ValueError, match="Unknown player"):
        promises.give_promise_tokens(state, "p1", "zzz", 1)


# ------------------------------- endpoint ------------------------------------


@pytest.fixture
def client() -> TestClient:
    from src.core.event_store import EventStore
    from src.core.registry import StaticDataRegistry

    app = create_app(
        registry=StaticDataRegistry(), store=EventStore(":memory:"), initial_state=_state()
    )
    return TestClient(app)


def test_endpoint_transaction_and_web_data(client: TestClient) -> None:
    resp = client.post(
        "/transactions/resolve",
        json={"partner_id": "p2", "give": {"trade_goods": 2}, "receive": {"commodities": 1}},
    )
    assert resp.status_code == 200
    data = client.get("/api/public/game/g/web-data").json()
    p1 = next(p for p in data["playerData"] if p["color"] == "red")
    p2 = next(p for p in data["playerData"] if p["color"] == "blue")
    # p1: 3 - 2 + 1 (commodity od p2 -> TG); p2: 1 + 2 = 3.
    assert (p1["tg"], p2["tg"]) == (2, 3)
    assert p1["transactedWith"] == ["blue"]
    # Druga transakcja z tym samym partnerem w turze — 422 z powodem.
    again = client.post(
        "/transactions/resolve", json={"partner_id": "p2", "give": {"trade_goods": 1}}
    )
    assert again.status_code == 422
    assert "already made a transaction" in again.json()["detail"]


def test_endpoint_promise_tokens_roundtrip(client: TestClient) -> None:
    ok = client.post("/promises/give", json={"issuer_id": "p1", "holder_id": "p3", "count": 3})
    assert ok.status_code == 200
    data = client.get("/api/public/game/g/web-data").json()
    p3 = next(p for p in data["playerData"] if p["color"] == "green")
    assert p3["promiseTokensHeld"] == {"red": 3}
    back = client.post("/promises/return", json={"issuer_id": "p1", "holder_id": "p3", "count": 5})
    assert back.status_code == 422
    done = client.post("/promises/return", json={"issuer_id": "p1", "holder_id": "p3", "count": 3})
    assert done.status_code == 200
