"""Emirates of Hacan — komplet komponentów frakcji (RULES.md 62.6), konwencja par."""

from __future__ import annotations

import pytest

from src.core import production, rules_hooks, strategic_action, transaction
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import hacan
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide
from tests.factions.completeness import missing_components


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("101", "20")
    grid.place_system("301", "21")  # daleko - bez sąsiedztwa z 000
    grid.build_edges()
    return grid


def _state(faction: str = "hacan") -> GameState:
    """p1 (aktywny, ``faction``) w 000; p2 (sol) daleko w 301 — nie są sąsiadami."""
    p1 = PlayerState(player_id="p1", color="red", faction=faction, trade_goods=3)
    p1.private.action_cards = ["sabo1"]
    p2 = PlayerState(player_id="p2", color="blue", faction="sol", trade_goods=1)
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18", space_units={"p1": {"cruiser": 1}}),
            "301": SystemState(position="301", system_id="21", space_units={"p2": {"cruiser": 1}}),
        },
    )


def test_kompletnosc_hacan(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "hacan") == []


def test_guild_ships_transakcja_bez_sasiedztwa(registry: StaticDataRegistry) -> None:
    side = TransactionSide(trade_goods=1)
    assert transaction.can_transact_with(_state(), _grid(), "p1", "p2")
    with pytest.raises(ValueError, match="neighbor"):
        transaction.validate_transaction(_state("letnev"), _grid(), "p2", side, TransactionSide())


def test_arbiters_karty_akcji_w_transakcji(registry: StaticDataRegistry) -> None:
    side = TransactionSide(action_cards=("sabo1",))
    done = transaction.resolve_transaction(_state(), _grid(), "p2", side, TransactionSide())
    assert done.players["p2"].private.action_cards == ["sabo1"]
    other = _state("letnev")
    other.systems["301"].space_units = {}
    other.systems["000"].space_units["p2"] = {"cruiser": 1}  # sąsiedzi, ale bez Arbiters
    with pytest.raises(ValueError, match="Arbiters"):
        transaction.validate_transaction(other, _grid(), "p2", side, TransactionSide())


def test_masters_of_trade_secondary_trade_bez_zetonu(registry: StaticDataRegistry) -> None:
    state = _state()
    state.active_player_id = "p2"
    assert strategic_action.secondary_without_token(state, "p1", 5)
    assert not strategic_action.secondary_without_token(state, "p1", 7)
    state.players["p1"].faction = "letnev"
    assert not strategic_action.secondary_without_token(state, "p1", 5)


def test_pride_of_kenara_planeta_w_transakcji(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].controlled_planets = ["mr"]
    state.systems["000"].planet_owners = {"mr": "p1"}
    state.systems["000"].planet_units = {"mr": {"p1": {"mech": 1, "infantry": 1}}}
    state.systems["101"] = SystemState(position="101", system_id="20")
    planet20 = registry.systems["20"].planets[0]
    state.systems["101"].planet_owners = {planet20: "p1"}
    assert transaction.tradable_planets(state, "p1") == ["mr"]
    side = TransactionSide(planets=(f"mr>{planet20}",))
    done = transaction.resolve_transaction(state, _grid(), "p2", side, TransactionSide())
    assert done.systems["000"].planet_owners["mr"] == "p2"
    assert done.systems["101"].planet_units[planet20]["p1"] == {"mech": 1, "infantry": 1}
    # Bez mecha planety nie da się oddać.
    state.systems["000"].planet_units = {"mr": {"p1": {"infantry": 1}}}
    with pytest.raises(ValueError, match="cannot trade"):
        transaction.validate_transaction(state, _grid(), "p2", side, TransactionSide())


def test_harrugh_gefhara_koszt_zero(registry: StaticDataRegistry) -> None:
    order = [production.ProductionOrder(base_type="cruiser", count=1)]
    state = _state()
    assert production.order_cost(state, registry, "p1", order) > 0
    hacan.galactic_securities_net(state, registry, "p1", {})
    assert production.order_cost(state, registry, "p1", order) == 0


def test_auto_factories_przy_trzech_statkach(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    before = state.players["p1"].fleet_cc
    ctx = {"player": "p1", "units": {"cruiser": 2, "fighter": 3}}
    assert not hacan._many_ships(state, "p1", ctx)
    ctx = {"player": "p1", "units": {"cruiser": 2, "destroyer": 1}}
    assert hacan._many_ships(state, "p1", ctx)
    hacan.auto_factories(state, "p1", ctx)
    assert state.players["p1"].fleet_cc == before + 1
