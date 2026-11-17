"""Transakcje w fazie agendy — RULES.md 47.5 (``docs/rules_tirules/R_transactions.md``).

„While resolving each agenda during the agenda phase, a player may perform one transaction with
each other player. Players do not need to be neighbors.” (R_transactions, R_agenda_phase: „Each
pair of players may resolve one transaction during each agenda”). Rulingi: agenda odrzucona
i zastąpiona (R_transactions notes) oraz Miscount Disclosed (C_agendas) dają nową transakcję.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import agenda_phase, transaction
from src.core.game_state import (
    AgendaPhaseState,
    AgendaStep,
    GameState,
    Phase,
    PlayerState,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.build_edges()
    return grid


def _state(step: AgendaStep = AgendaStep.VOTE, agenda_id: str | None = "revolution") -> GameState:
    """Faza agendy, nikt z nikim nie sąsiaduje; aktywny (głosujący) jest p2."""
    players = {
        p: PlayerState(player_id=p, color=c, trade_goods=3, commodities=2)
        for p, c in (("p1", "red"), ("p2", "blue"), ("p3", "green"))
    }
    players["p1"].private.promissory_notes = ["red_ceasefire"]
    return GameState(
        phase=Phase.AGENDA,
        active_player_id="p2",
        speaker_id="p2",
        seating_order=["p1", "p2", "p3"],
        players=players,
        agenda=AgendaPhaseState(step=step, agenda_id=agenda_id),
    )


def test_agenda_transakcja_z_kazdym_bez_sasiedztwa() -> None:
    """Dowolna para (żaden nie jest aktywny ani sąsiadem) wymienia komponenty przy agendzie."""
    state = _state()
    assert not transaction.reachable(state, _grid(), "p1", "p3")
    assert transaction.components_allowed(state, _grid(), "p1", "p3")
    new = transaction.resolve_transaction(
        state, _grid(), "p3",
        TransactionSide(trade_goods=1, promissory_note="red_ceasefire"),
        TransactionSide(commodities=2),
        player_id="p1",
    )
    assert new.players["p1"].trade_goods == 3 - 1 + 2  # commodities p3 -> TG u p1
    assert new.players["p3"].private.promissory_notes == ["red_ceasefire"]
    # Limit liczony dla PARY: odnotowany po obu stronach.
    assert new.players["p1"].transacted_with == ["p3"]
    assert new.players["p3"].transacted_with == ["p1"]


def test_agenda_jedna_transakcja_pary_na_agende() -> None:
    first = transaction.resolve_transaction(
        _state(), _grid(), "p3", TransactionSide(trade_goods=1), TransactionSide(), "p1"
    )
    for player, partner in (("p1", "p3"), ("p3", "p1")):
        assert not transaction.components_allowed(first, _grid(), player, partner)
        with pytest.raises(ValueError, match="during this agenda"):
            transaction.resolve_transaction(
                first, _grid(), partner, TransactionSide(trade_goods=1), TransactionSide(),
                player,
            )
    # Inne pary bez zmian.
    assert transaction.components_allowed(first, _grid(), "p1", "p2")
    assert transaction.components_allowed(first, _grid(), "p2", "p3")


def test_agenda_poza_rozstrzyganiem_agendy_tylko_dlug() -> None:
    """Między agendami (krok ujawniania) i po obu agendach transakcji nie ma."""
    for state in (_state(AgendaStep.REVEAL, None), _state(AgendaStep.COMPLETE, None)):
        assert not transaction.agenda_window(state)
        assert not transaction.components_allowed(state, _grid(), "p1", "p3")
        with pytest.raises(ValueError, match="while an agenda is resolved"):
            transaction.resolve_transaction(
                state, _grid(), "p3", TransactionSide(trade_goods=1), TransactionSide(), "p1"
            )


def test_agenda_kazdy_krok_agendy_otwarty() -> None:
    for step in (AgendaStep.VOTE, AgendaStep.TIEBREAK, AgendaStep.COUNTED, AgendaStep.RESOLVED):
        assert transaction.agenda_window(_state(step))


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def test_agenda_miscount_disclosed_daje_nowa_transakcje(registry: StaticDataRegistry) -> None:
    """C_agendas (Miscount Disclosed): transakcja przy Miscount nie blokuje transakcji przy
    ponownym głosowaniu nad prawem; to samo przy agendzie odrzuconej i zastąpionej."""
    state = _state(AgendaStep.RESOLVED, "miscount")
    state.decks.agenda_laws = {"conscription": "for"}
    state.agenda.revote_law = "conscription"  # type: ignore[union-attr]
    done = transaction.resolve_transaction(
        state, _grid(), "p3", TransactionSide(trade_goods=1), TransactionSide(), "p1"
    )
    assert not transaction.components_allowed(done, _grid(), "p1", "p3")
    revote = agenda_phase.continue_agenda(done, registry, "p2")
    assert revote.agenda is not None and revote.agenda.agenda_id == "conscription"
    assert transaction.components_allowed(revote, _grid(), "p1", "p3")


# ------------------------------------------------------------------ stół przez API (47.1b)


@pytest.fixture
def client() -> TestClient:
    from src.core.event_store import EventStore

    app = create_app(
        registry=StaticDataRegistry(), store=EventStore(":memory:"), initial_state=_state()
    )
    return TestClient(app)


def _post(client: TestClient, path: str, **body: object) -> int:
    return int(client.post(f"/transactions/table/{path}", json=body).status_code)


def test_agenda_stol_wymiana_bez_sasiedztwa(client: TestClient) -> None:
    """Scenariusz przez API: p1 i p3 (nie sąsiedzi, żaden aktywny) siadają i wymieniają."""
    assert _post(client, "open", player_id="p3", partner_id="p1") == 200
    view = client.get("/transactions/state?player=p1").json()
    assert view["tables"][0]["components"] is True
    partner = next(p for p in view["partners"] if p["playerId"] == "p3")
    assert partner["components"] is True and partner["neighbor"] is False
    assert _post(client, "side", player_id="p1", partner_id="p3", side={"trade_goods": 2}) == 200
    assert _post(client, "ready", player_id="p1", partner_id="p3", ready=True) == 200
    assert _post(client, "ready", player_id="p3", partner_id="p1", ready=True) == 200
    data = client.get("/api/public/game/g/web-data").json()
    tg = {p["color"]: p["tg"] for p in data["playerData"]}
    assert (tg["red"], tg["green"]) == (1, 5)
    view = client.get("/transactions/state?player=p3").json()
    assert next(p for p in view["partners"] if p["playerId"] == "p1")["done"] is True
    # Feed: aktor = gracz zaczynający stół, nie aktywny p2.
    entries = client.get("/history/activity").json()["entries"]
    deal = [e["activity"] for e in entries if e["activity"]["action"] == "transaction"]
    assert deal and (deal[-1]["actor_id"], deal[-1]["target_id"]) == ("p3", "p1")
