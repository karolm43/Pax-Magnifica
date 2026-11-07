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
    with pytest.raises(ValueError, match="Production limit exceeded"):
        production.validate_production(
            state, grid, registry, "p1", [ProductionOrder("infantry", 7)]
        )


def test_validate_rejects_over_budget(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=0)
    # Dreadnought kosztuje 4; budżet = 4 (Jord) → ok. Dwa = 8 > 4 → ale limit 6 ok,
    # budżet nie. Sprawdźmy koszt: użyjmy cruiserów (koszt 2 każdy): 3×2=6 > budżet 4.
    with pytest.raises(ValueError, match="Not enough resources"):
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
    with pytest.raises(ValueError, match="blockade"):
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
    with pytest.raises(ValueError, match="No active system"):
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


# --- produce(): płatność, limit wspólny dla akcji, strefy, rezerwa (RULES.md 33.3) ---


def test_produce_exhausts_planet_and_places_units(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=3)
    new = production.produce(
        state, grid, registry, "p1", [ProductionOrder("cruiser", 1)],
        production.Spend(planets=("jord",)),
    )
    assert new.systems["000"].space_units["p1"]["cruiser"] == 1
    assert "jord" in new.players["p1"].exhausted_planets
    assert new.players["p1"].trade_goods == 3  # TG nietknięte
    assert new.production_used == 1
    # Stan wejściowy bez zmian.
    assert state.players["p1"].exhausted_planets == []


def test_produce_auto_pay_prefers_planets_then_tg(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=5)
    # Dreadnought kosztuje 4 → pokrywa go sama Jord (res 4), TG zostają.
    new = production.produce(
        state, grid, registry, "p1", [ProductionOrder("dreadnought", 1)]
    )
    assert new.players["p1"].exhausted_planets == ["jord"]
    assert new.players["p1"].trade_goods == 5


def test_produce_rejects_underpayment(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=10)
    with pytest.raises(ValueError, match="Payment too low"):
        production.produce(
            state, grid, registry, "p1", [ProductionOrder("dreadnought", 1)],
            production.Spend(trade_goods=2),
        )


def test_produce_limit_is_shared_across_calls(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=20)
    state = production.produce(
        state, grid, registry, "p1", [ProductionOrder("fighter", 5)],
        production.Spend(trade_goods=3),
    )
    assert state.production_used == 5
    # Limit 6, wyprodukowano 5 → kolejne 2 nie wejdą.
    with pytest.raises(ValueError, match="Production limit exceeded"):
        production.produce(
            state, grid, registry, "p1", [ProductionOrder("fighter", 2)],
            production.Spend(trade_goods=1),
        )


def test_produce_ground_requires_producing_planet(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=5)
    with pytest.raises(ValueError, match="requires a planet"):
        production.produce(
            state, grid, registry, "p1", [ProductionOrder("infantry", 2)]
        )
    with pytest.raises(ValueError, match="Cannot place"):
        production.produce(
            state, grid, registry, "p1", [ProductionOrder("infantry", 2, zone="nowhere")]
        )
    new = production.produce(
        state, grid, registry, "p1", [ProductionOrder("infantry", 2, zone="jord")]
    )
    assert new.systems["000"].planet_units["jord"]["p1"]["infantry"] == 2


def test_produce_respects_reinforcements(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=20)
    state.systems["000"].space_units["p1"] = {"flagship": 1}
    with pytest.raises(ValueError, match="reinforcements"):
        production.produce(
            state, grid, registry, "p1", [ProductionOrder("flagship", 1)]
        )
    assert production.reinforcements_left(state, "p1", "infantry") is None


def test_split_infantry_pays_one_pair(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state_with_dock_on_jord(trade_goods=0)
    state.systems["000"].planet_units["jord"]["p1"]["pds"] = 1
    # 2 piechoty rozbite na 1+1 = jedna para = jeden koszt (1), nie dwa.
    orders = [
        ProductionOrder("infantry", 1, zone="jord"),
        ProductionOrder("infantry", 1, zone="jord"),
    ]
    assert production.order_cost(state, registry, "p1", orders) == 1
    production.validate_production(state, grid, registry, "p1", orders)


def test_production_view_and_produce_api(registry: StaticDataRegistry) -> None:
    from fastapi.testclient import TestClient

    from src.api.app import create_app
    from src.core.event_store import EventStore

    state = _state_with_dock_on_jord(trade_goods=2)
    client = TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    )
    view = client.get("/tactical/production/view").json()
    assert view["active"] is True
    assert view["limit"] == 6 and view["remaining"] == 6
    assert view["groundZones"] == ["jord"]
    assert view["tradeGoods"] == 2
    jord = next(p for p in view["planets"] if p["planet"] == "jord")
    assert jord["resources"] == 4 and jord["exhausted"] is False
    assert all(u["baseType"] not in ("pds", "spacedock") for u in view["units"])

    resp = client.post(
        "/tactical/produce",
        json={
            "faction": "sol",
            "orders": [{"baseType": "infantry", "count": 2, "zone": "jord"}],
            "spend": {"planets": ["jord"], "tradeGoods": 0},
        },
    )
    assert resp.status_code == 200
    after = client.get("/tactical/production/view").json()
    assert after["used"] == 2 and after["remaining"] == 4
    assert next(p for p in after["planets"] if p["planet"] == "jord")["exhausted"] is True

    bad = client.post(
        "/tactical/produce",
        json={"faction": "sol", "orders": [{"baseType": "infantry", "count": 2, "zone": "jord"}],
              "spend": {"planets": ["jord"]}},
    )
    assert bad.status_code == 422
