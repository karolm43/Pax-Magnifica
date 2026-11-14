"""Umowy kroku 3 Trade przy stole transakcji: wskazanie za cenę, wash, dług — RULES.md 47.4."""

from __future__ import annotations

import pytest

from src.core import strategic_action, transaction_table
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.build_edges()
    return grid


def _state() -> GameState:
    """p1 (Trade, aktywny) sąsiaduje z p2 (wspólny system); p3 jest daleko."""
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
        systems={
            "000": SystemState(
                position="000", system_id="18",
                space_units={"p1": {"cruiser": 1}, "p2": {"cruiser": 1}},
            ),
        },
    )


def _agree(
    state: GameState, holder_side: TransactionSide, player: str, player_side: TransactionSide
) -> GameState:
    grid = _grid()
    state = transaction_table.open_table(state, player, "p1")
    state = transaction_table.set_side(state, grid, "p1", player, holder_side)
    state = transaction_table.set_side(state, grid, player, "p1", player_side)
    state = transaction_table.set_ready(state, grid, "p1", player, True)
    return transaction_table.set_ready(state, grid, player, "p1", True)


def _play(registry: StaticDataRegistry) -> GameState:
    return strategic_action.play_strategy_card(_state(), registry, "p1", 5)


def test_wash_minus_jeden_po_uzupelnieniu(registry: StaticDataRegistry) -> None:
    """Umowa: p2 wskazany za wash −1; po uzupełnieniu stół sam się otwiera, obaj Ready."""
    state = _agree(
        _play(registry), TransactionSide(trade_secondary=True), "p2", TransactionSide(wash=1)
    )
    assert transaction_table.deal_players(state) == ["p2"]
    assert state.transaction_tables == []  # umowa zawarta, nic jeszcze nie przeszło
    # p1 nie zaznacza p2 - umowa i tak go wskazuje.
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"players": []}, grid=_grid()
    )
    assert state.players["p2"].commodities == 3  # darmowe secondary rozstrzygnięte
    table = transaction_table.find_table(state, "p1", "p2")
    assert table is not None and table.prefilled
    # p2 oddaje 3 commodities, p1 oddaje 3 − 1 = 2 TG (ma 3 z primary).
    assert transaction_table.side_of(table, "p2").commodities == 3
    assert transaction_table.side_of(table, "p1").trade_goods == 2
    grid = _grid()
    state = transaction_table.set_ready(state, grid, "p1", "p2", True)
    state = transaction_table.set_ready(state, grid, "p2", "p1", True)
    # p1: 3 − 2 + 3 (commodities -> TG) = 4; p2: 2 TG, 0 commodities.
    assert state.players["p1"].trade_goods == 4
    assert (state.players["p2"].trade_goods, state.players["p2"].commodities) == (2, 0)


def test_nie_sasiad_placi_dlugiem(registry: StaticDataRegistry) -> None:
    """Nie-sąsiad: wash niemożliwy, cena = żetony długu (przechodzą od razu)."""
    state = _play(registry)
    grid = _grid()
    state = transaction_table.open_table(state, "p1", "p3")
    state = transaction_table.set_side(
        state, grid, "p1", "p3", TransactionSide(trade_secondary=True)
    )
    with pytest.raises(ValueError, match="debt tokens"):
        transaction_table.set_side(state, grid, "p3", "p1", TransactionSide(wash=0))
    state = _agree(
        state, TransactionSide(trade_secondary=True), "p3", TransactionSide(debt_tokens=2)
    )
    assert state.debt_tokens == {"p1": {"p3": 2}}
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"players": []}, grid=grid
    )
    # p3 wskazany umową (darmowe secondary w swojej kolejce, po decyzji p2).
    assert state.pending_window is not None
    assert state.pending_window.context["free"] == "p3"
    assert state.trade_deals == {}  # nic do wymiany po uzupełnieniu


def test_umowa_tylko_dla_posiadacza_w_kroku_3(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = transaction_table.open_table(_state(), "p1", "p2")
    with pytest.raises(ValueError, match="Trade holder"):
        transaction_table.set_side(state, grid, "p1", "p2", TransactionSide(trade_secondary=True))
    played = transaction_table.open_table(_play(registry), "p1", "p2")
    with pytest.raises(ValueError, match="Trade holder"):
        transaction_table.set_side(played, grid, "p2", "p1", TransactionSide(trade_secondary=True))
