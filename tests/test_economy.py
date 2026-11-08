"""Testy ``core/economy``: trade goods i commodities (RULES.md 43.1a; R_trade_goods)."""

from __future__ import annotations

import pytest

from src.core import economy
from src.core.game_state import GameState, PlayerState


def _state(trade_goods: int = 2, commodities: int = 1) -> GameState:
    p1 = PlayerState(
        player_id="p1", color="red",
        trade_goods=trade_goods, commodities=commodities, commodity_value=3,
    )
    p2 = PlayerState(player_id="p2", color="blue", trade_goods=0, commodities=0, commodity_value=2)
    return GameState(players={"p1": p1, "p2": p2})


def test_zdobycie_i_wydanie_trade_goods() -> None:
    state = _state()
    economy.gain_trade_goods(state, "p1", 3)
    economy.spend_trade_goods(state, "p1", 4)
    assert state.players["p1"].trade_goods == 1


def test_wydanie_wiecej_niz_masz_jest_bledem_i_nie_zmienia_stanu() -> None:
    state = _state()
    with pytest.raises(ValueError, match="Not enough trade goods"):
        economy.spend_trade_goods(state, "p1", 3)
    assert state.players["p1"].trade_goods == 2


def test_ujemne_kwoty_i_nieznany_gracz_sa_bledem() -> None:
    state = _state()
    with pytest.raises(ValueError):
        economy.gain_trade_goods(state, "p1", -1)
    with pytest.raises(ValueError, match="Unknown player"):
        economy.gain_trade_goods(state, "nikt", 1)


def test_commodities_nie_przekraczaja_commodity_value() -> None:
    state = _state()
    assert economy.commodity_gap(state, "p1") == 2
    assert economy.gain_commodities(state, "p1", 5) == 2
    assert state.players["p1"].commodities == 3
    assert economy.gain_commodities(state, "p1", 1) == 0


def test_replenish_uzupelnia_do_wartosci_ale_nie_zabiera_nadwyzki() -> None:
    state = _state()
    economy.replenish_commodities(state, "p1")
    assert state.players["p1"].commodities == 3
    state.players["p1"].commodities = 5
    economy.replenish_commodities(state, "p1")
    assert state.players["p1"].commodities == 5


def test_konwersja_commodities_na_trade_goods() -> None:
    state = _state()
    economy.convert_commodities_to_trade_goods(state, "p1", 1)
    assert (state.players["p1"].commodities, state.players["p1"].trade_goods) == (0, 3)
    with pytest.raises(ValueError, match="Not enough commodities"):
        economy.convert_commodities_to_trade_goods(state, "p1", 1)


def test_oddanie_commodities_innemu_graczowi_daje_mu_trade_goods() -> None:
    state = _state(trade_goods=2, commodities=2)
    economy.give_to_player(state, "p1", "p2", trade_goods=1, commodities=2)
    p1, p2 = state.players["p1"], state.players["p2"]
    assert (p1.trade_goods, p1.commodities) == (1, 0)
    assert (p2.trade_goods, p2.commodities) == (3, 0)
