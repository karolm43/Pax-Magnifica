"""Testy punktów zaczepienia H2 (RULES.md 43): ruch, walka, produkcja, płatność.

Każdy punkt testowany parą: BEZ wyjątku (reguła bazowa) i Z wyjątkiem (zmieniony wynik).
Hooki testowe rejestrujemy w ``temporary_hooks`` pod frakcją ``sol`` (z danych, nie z pamięci).
"""

from __future__ import annotations

import pytest

from src.core import battle, economy, movement, payment, production, rules_hooks
from src.core.game_state import (
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.production import ProductionOrder
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import HookKind, HookSource
from tests.test_production import _grid as production_grid
from tests.test_production import _state_with_dock_on_jord

SOL = HookSource(rules_hooks.SOURCE_FACTION, "sol")


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _ring_grid() -> HexGrid:
    grid = HexGrid()
    for position, system_id in (("000", "18"), ("101", "20"), ("201", "21")):
        grid.place_system(position, system_id)
    grid.build_edges()
    return grid


def _movement_state(ship: str, enemy_between: bool = False) -> GameState:
    systems = {
        "201": SystemState(position="201", system_id="21", space_units={"p1": {ship: 1}}),
    }
    if enemy_between:
        systems["101"] = SystemState(
            position="101", system_id="20", space_units={"p2": {"fighter": 1}}
        )
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={
            "p1": PlayerState(player_id="p1", faction="sol"),
            "p2": PlayerState(player_id="p2"),
        },
        systems=systems,
    )


def test_move_value_hook_extends_range(registry: StaticDataRegistry) -> None:
    grid = _ring_grid()
    assert not grid.are_adjacent("201", "000")  # trasa 201 -> 101 -> 000 = 2 wejścia
    state = _movement_state("carrier")  # carrier: ruch 1
    ok, _ = movement.can_move(state, grid, registry, "201", "carrier", "p1")
    assert not ok
    with rules_hooks.temporary_hooks():
        rules_hooks.register(rules_hooks.POINT_MOVEMENT_MOVE_VALUE, SOL, HookKind.MODIFY)(
            lambda _s, _p, _c: 1
        )
        ok, _ = movement.can_move(state, grid, registry, "201", "carrier", "p1")
        assert ok
        # Inny gracz (bez źródła) nadal ma bazowy zasięg.
        other = _movement_state("carrier")
        other.players["p1"].faction = "arborec"
        ok, _ = movement.can_move(other, grid, registry, "201", "carrier", "p1")
        assert not ok


def test_pass_foreign_ships_hook_unblocks_route(registry: StaticDataRegistry) -> None:
    grid = _ring_grid()
    state = _movement_state("destroyer", enemy_between=True)  # destroyer: ruch 2
    ok, _ = movement.can_move(state, grid, registry, "201", "destroyer", "p1")
    assert not ok  # 101 zablokowane statkami obcego gracza
    with rules_hooks.temporary_hooks():
        rules_hooks.register(
            rules_hooks.POINT_MOVEMENT_PASS_FOREIGN_SHIPS, SOL, HookKind.PERMIT
        )(lambda _s, _p, _c: True)
        ok, _ = movement.can_move(state, grid, registry, "201", "destroyer", "p1")
        assert ok


def _battle_state() -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=TacticalStep.SPACE_COMBAT,
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="sol"),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems={
            "000": SystemState(
                position="000",
                system_id="18",
                space_units={"p1": {"cruiser": 1}, "p2": {"cruiser": 1}},
            )
        },
        rng_seed=1,
    )


def test_combat_roll_modifier_hook(registry: StaticDataRegistry) -> None:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.build_edges()
    base = battle.combat_units(
        _battle_state(), grid, registry, kind="space", position="000", planet=None,
        player_id="p1",
    )[0]
    assert base.modifier == 0
    with rules_hooks.temporary_hooks():
        rules_hooks.register(rules_hooks.POINT_COMBAT_ROLL_MODIFIER, SOL, HookKind.MODIFY)(
            lambda _s, _p, c: 1 if c["base_type"] == "cruiser" else 0
        )
        buffed = battle.combat_units(
            _battle_state(), grid, registry, kind="space", position="000", planet=None,
            player_id="p1",
        )[0]
        enemy = battle.combat_units(
            _battle_state(), grid, registry, kind="space", position="000", planet=None,
            player_id="p2",
        )[0]
    assert buffed.modifier == 1 and buffed.hits_on == base.hits_on - 1
    assert enemy.modifier == 0  # p2 nie ma źródła hooka


def test_production_value_hook_changes_limit(registry: StaticDataRegistry) -> None:
    grid = production_grid()
    state = _state_with_dock_on_jord()
    assert production.production_limit(state, grid, registry, "p1") == 6
    with rules_hooks.temporary_hooks():
        rules_hooks.register(rules_hooks.POINT_PRODUCTION_VALUE, SOL, HookKind.MODIFY)(
            lambda _s, _p, c: 2 if c["base_type"] == "spacedock" else 0
        )
        assert production.production_limit(state, grid, registry, "p1") == 8


def test_production_cost_hook_changes_cost(registry: StaticDataRegistry) -> None:
    state = _state_with_dock_on_jord()
    orders = [ProductionOrder("infantry", 2, zone="jord")]
    base = production.order_cost(state, registry, "p1", orders)
    with rules_hooks.temporary_hooks():
        rules_hooks.register(rules_hooks.POINT_PRODUCTION_COST, SOL, HookKind.MODIFY)(
            lambda _s, _p, _c: -1
        )
        assert production.order_cost(state, registry, "p1", orders) == max(0.0, base - 1)


def test_commodities_as_trade_goods_hook_in_payment_and_budget(
    registry: StaticDataRegistry,
) -> None:
    state = _state_with_dock_on_jord(trade_goods=1)
    state.players["p1"].commodities = 2
    # Bez wyjątku: commodities nie są wydawalne jak TG.
    assert economy.spendable_trade_goods(state, "p1") == 1
    with pytest.raises(ValueError, match="Not enough trade goods"):
        payment.validate_payment(state, registry, "p1", "resources", [], 3)
    budget_base = production.available_budget(state, registry, "p1")
    with rules_hooks.temporary_hooks():
        rules_hooks.register(rules_hooks.POINT_PAYMENT_COMMODITIES_AS_TG, SOL, HookKind.PERMIT)(
            lambda _s, _p, _c: True
        )
        assert economy.spendable_trade_goods(state, "p1") == 3
        assert production.available_budget(state, registry, "p1") == budget_base + 2
        assert payment.validate_payment(state, registry, "p1", "resources", [], 3) == 3
        spent = state.clone()
        payment.apply_payment(spent, "p1", [], 3)  # najpierw 1 TG, potem 2 commodities
        assert spent.players["p1"].trade_goods == 0
        assert spent.players["p1"].commodities == 0
