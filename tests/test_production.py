"""Testy walidacji produkcji (E8-T6): limit, budżet, blokada statków (RULES.md 33.2)."""

from __future__ import annotations

import pytest

from src.core import production
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.production import ProductionOrder
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.build_edges()
    return grid


def _state_with_dock_on_jord(
    *, trade_goods: int = 0, exhausted: bool = False
) -> GameState:
    """Gracz p1 z dokiem na Jord (res=4 → PRODUCTION 4+2=6) w aktywnym systemie 000."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={
            "p1": PlayerState(
                player_id="p1",
                faction="sol",
                trade_goods=trade_goods,
                exhausted_planets=["jord"] if exhausted else [],
            )
        },
        systems={
            "000": SystemState(
                position="000",
                system_id="18",
                planet_owners={"jord": "p1"},
                planet_units={"jord": {"p1": {"spacedock": 1}}},
            )
        },
    )


def test_production_limit_dock_plus_planet_resources(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord()
    # Bazowy dok "+2" na Jord (res 4) → limit 6.
    assert production.production_limit(state, grid, registry, "p1") == 6


def test_budget_counts_ready_planets_and_tg(registry: StaticDataRegistry) -> None:
    state = _state_with_dock_on_jord(trade_goods=3)
    # Jord gotowa (res 4) + 3 TG = 7.
    assert production.available_budget(state, registry, "p1") == 7


def test_budget_excludes_exhausted_planet(registry: StaticDataRegistry) -> None:
    state = _state_with_dock_on_jord(trade_goods=3, exhausted=True)
    # Jord wyczerpana → tylko 3 TG.
    assert production.available_budget(state, registry, "p1") == 3


def test_validate_ok_within_limit_and_budget(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=10)
    # 1 destroyer (koszt 1, limit 1 szt.) — mieści się (limit 6, budżet 4+10).
    production.validate_production(
        state, grid, registry, "p1", [ProductionOrder("destroyer", 1)]
    )


def test_validate_rejects_over_limit(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=100)
    # 7 infantry > limit 6 (każda sztuka liczy do limitu).
    with pytest.raises(ValueError, match="Limit produkcji"):
        production.validate_production(
            state, grid, registry, "p1", [ProductionOrder("infantry", 7)]
        )


def test_validate_rejects_over_budget(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=0)
    # Dreadnought kosztuje 4; budżet = 4 (Jord) → ok. Dwa = 8 > 4 → ale limit 6 ok,
    # budżet nie. Sprawdźmy koszt: użyjmy cruiserów (koszt 2 każdy): 3×2=6 > budżet 4.
    with pytest.raises(ValueError, match="Za mało zasobów"):
        production.validate_production(
            state, grid, registry, "p1", [ProductionOrder("cruiser", 3)]
        )


def test_validate_rejects_ships_when_enemy_present(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=100)
    # Dodaj obce statki w aktywnym systemie → blokada statków.
    state.systems["000"].space_units["p2"] = {"destroyer": 1}
    state.players["p2"] = PlayerState(player_id="p2")
    with pytest.raises(ValueError, match="blokada"):
        production.validate_production(
            state, grid, registry, "p1", [ProductionOrder("destroyer", 1)]
        )
    # Ale siły naziemne można produkować mimo blokady.
    production.validate_production(
        state, grid, registry, "p1", [ProductionOrder("infantry", 2)]
    )


def test_validate_no_active_system_rejected(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord()
    state.active_system = None
    with pytest.raises(ValueError, match="aktywnego systemu"):
        production.validate_production(
            state, grid, registry, "p1", [ProductionOrder("infantry", 1)]
        )


def test_dual_production_cost_pairs(registry: StaticDataRegistry) -> None:
    grid = _grid()
    # 2 infantry = 1 koszt (para). Koszt infantry = 1 → 1 zasób. Budżet 4 (Jord).
    state = _state_with_dock_on_jord()
    production.validate_production(
        state, grid, registry, "p1", [ProductionOrder("infantry", 2)]
    )
