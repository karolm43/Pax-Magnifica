"""Testy transakcji między graczami i żetonów długu — RULES.md 47.

Reguła (tirules2.com → ``docs/rules_tirules/R_transactions.md``): aktywny gracz robi do jednej
transakcji z każdym sąsiadem w turze; oddaje TG/commodities (+1 notka), dostaje TG/commodities/
fragmenty (+1 notka); commodity staje się u odbiorcy trade goodem.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import action_budget, debt, transaction, turn_flow
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


def test_debt_tokens_give_and_return() -> None:
    state = _state()
    state = debt.give_debt_tokens(state, "p1", "p2", 3)
    state = debt.give_debt_tokens(state, "p1", "p2", 1)
    assert state.debt_tokens == {"p2": {"p1": 4}}
    state = debt.return_debt_tokens(state, "p2", "p1", 3)
    assert debt.held_tokens(state, "p2", "p1") == 1
    state = debt.return_debt_tokens(state, "p2", "p1", 1)
    assert state.debt_tokens == {}


def test_debt_tokens_validation_and_no_neighbor_needed() -> None:
    state = _state()
    # p3 nie jest sąsiadem p1 — obietnice i tak działają (nie reguła TI4).
    assert debt.give_debt_tokens(state, "p1", "p3", 2).debt_tokens == {"p3": {"p1": 2}}
    with pytest.raises(ValueError, match="only 0 held"):
        debt.return_debt_tokens(state, "p2", "p1", 1)
    with pytest.raises(ValueError, match="at least 1"):
        debt.give_debt_tokens(state, "p1", "p2", 0)
    with pytest.raises(ValueError, match="different players"):
        debt.give_debt_tokens(state, "p1", "p1", 1)
    with pytest.raises(ValueError, match="Unknown player"):
        debt.give_debt_tokens(state, "p1", "zzz", 1)


# ------------------------------- endpoint ------------------------------------


@pytest.fixture
def client() -> TestClient:
    from src.core.event_store import EventStore
    from src.core.registry import StaticDataRegistry

    app = create_app(
        registry=StaticDataRegistry(), store=EventStore(":memory:"), initial_state=_state()
    )
    return TestClient(app)


def _sit(client: TestClient, player: str, partner: str) -> None:
    body = {"player_id": player, "partner_id": partner}
    assert client.post("/transactions/table/open", json=body).status_code == 200


def _put(client: TestClient, player: str, partner: str, **side: object) -> int:
    body = {"player_id": player, "partner_id": partner, "side": side}
    return int(client.post("/transactions/table/side", json=body).status_code)


def _ready(client: TestClient, player: str, partner: str, ready: bool = True) -> int:
    body = {"player_id": player, "partner_id": partner, "ready": ready}
    return int(client.post("/transactions/table/ready", json=body).status_code)


def _tg(client: TestClient, color: str) -> int:
    data = client.get("/api/public/game/g/web-data").json()
    return int(next(p for p in data["playerData"] if p["color"] == color)["tg"])


def test_stol_wymiana_po_dwoch_ready(client: TestClient) -> None:
    """RULES.md 47.1b: każdy kładzie swoje, dwa Ready = wymiana; zmiana zdejmuje Ready."""
    # Stół otwiera SĄSIAD aktywnego („either player may initiate”).
    _sit(client, "p2", "p1")
    assert _put(client, "p1", "p2", trade_goods=2) == 200
    assert _put(client, "p2", "p1", commodities=1) == 200
    # Widok p1: jego strona i to, co POŁOŻYŁ partner (nie jego ręka).
    view = client.get("/transactions/state?player=p1").json()
    table = view["tables"][0]
    assert table["partner"] == "p2" and table["components"] is True
    assert table["mine"]["tradeGoods"] == 2 and table["theirs"]["commodities"] == 1
    assert _ready(client, "p1", "p2") == 200
    # Zmiana stołu zdejmuje Ready obu.
    assert _put(client, "p2", "p1", commodities=2) == 200
    table = client.get("/transactions/state?player=p1").json()["tables"][0]
    assert table["myReady"] is False
    assert _ready(client, "p2", "p1") == 200
    assert _tg(client, "red") == 3  # jedno Ready - nic nie przeszło
    assert _ready(client, "p1", "p2") == 200
    # p1: 3 - 2 + 2 (commodities od p2 -> TG); p2: 1 + 2.
    assert (_tg(client, "red"), _tg(client, "blue")) == (3, 3)
    assert client.get("/transactions/state?player=p1").json()["tables"] == []
    # Druga transakcja z tym samym partnerem w turze — komponentów nie da się położyć.
    _sit(client, "p1", "p2")
    assert _put(client, "p1", "p2", trade_goods=1) == 422


def test_stol_tylko_wlasne_rzeczy_i_tylko_strona(client: TestClient) -> None:
    _sit(client, "p1", "p2")
    # Nie da się położyć cudzej notki ani więcej TG, niż się ma.
    assert _put(client, "p1", "p2", promissory_note="blue_ps") == 422
    assert _put(client, "p1", "p2", trade_goods=9) == 422
    # Kłaść może tylko strona stołu (aktor = gracz z treści).
    resp = client.post(
        "/transactions/table/side",
        json={"player_id": "p1", "partner_id": "p2", "side": {"trade_goods": 1}},
        headers={"X-Actor-Id": "p2"},
    )
    assert resp.status_code == 403
    # Zamknięcie stołu - nic nie przechodzi.
    body = {"player_id": "p2", "partner_id": "p1"}
    assert client.post("/transactions/table/close", json=body).status_code == 200
    assert client.get("/transactions/state?player=p1").json()["tables"] == []


def test_stol_z_nie_sasiadem_tylko_dlug(client: TestClient) -> None:
    """RULES.md 47.1b/47.3: dług na stole bez sąsiedztwa, bez zużycia limitu transakcji."""
    _sit(client, "p1", "p3")
    assert _put(client, "p1", "p3", trade_goods=1) == 422
    assert _put(client, "p1", "p3", debt_tokens=2) == 200
    assert _ready(client, "p1", "p3") == 200
    assert _ready(client, "p3", "p1") == 200
    data = client.get("/api/public/game/g/web-data").json()
    p3 = next(p for p in data["playerData"] if p["color"] == "green")
    assert p3["debtTokens"] == {"red": 2}
    assert data["gameState"]["transactionTables"] == []


def test_stol_dlug_i_komponenty_razem(client: TestClient) -> None:
    _sit(client, "p1", "p2")
    assert _put(client, "p1", "p2", trade_goods=1) == 200
    assert _put(client, "p2", "p1", debt_tokens=3) == 200
    _ready(client, "p1", "p2")
    _ready(client, "p2", "p1")
    data = client.get("/api/public/game/g/web-data").json()
    p1 = next(p for p in data["playerData"] if p["color"] == "red")
    assert p1["debtTokens"] == {"blue": 3} and p1["transactedWith"] == ["blue"]


def test_stol_jawna_tylko_para() -> None:
    from src.core import transaction_table

    state = transaction_table.open_table(_state(), "p1", "p2")
    state = transaction_table.set_side(
        state, _grid(), "p1", "p2", TransactionSide(promissory_note="red_ceasefire")
    )
    assert state.transaction_tables[0].sides["p1"]["promissory_note"] == "red_ceasefire"
    # Stół ginie z nową turą.
    action_budget.reset_turn(state, "p2")
    assert state.transaction_tables == []


def test_bot_ocenia_stol_po_ready_czlowieka() -> None:
    from src.core import transaction_table
    from src.core.game_state import ControlType

    state = _state()
    state.players["p2"].control_type = ControlType.BOT
    state = transaction_table.open_table(state, "p1", "p2")
    gift = transaction_table.set_side(state, _grid(), "p1", "p2", TransactionSide(trade_goods=1))
    done = transaction_table.set_ready(gift, _grid(), "p1", "p2", True)
    assert done.players["p2"].trade_goods == 2  # prezent przyjęty
    assert done.transaction_tables == []


def test_endpoint_debt_tokens_return(client: TestClient) -> None:
    ok = client.post("/debt/give", json={"issuer_id": "p1", "holder_id": "p3", "count": 3})
    assert ok.status_code == 200
    back = client.post("/debt/return", json={"issuer_id": "p1", "holder_id": "p3", "count": 5})
    assert back.status_code == 422
    done = client.post("/debt/return", json={"issuer_id": "p1", "holder_id": "p3", "count": 3})
    assert done.status_code == 200
