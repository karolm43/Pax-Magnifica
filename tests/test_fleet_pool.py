"""Testy fleet pool (RULES.md 42): liczenie, okno przy zmianie kroku, usuwanie, API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import fleet_pool, production, tactical
from src.core.event_store import EventStore
from src.core.game_state import (
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.build_edges()
    return grid


def _state(
    ships: dict[str, int],
    *,
    pool: int = 3,
    step: TacticalStep = TacticalStep.MOVEMENT,
) -> GameState:
    system = SystemState(position="000", system_id="18")
    system.space_units["p1"] = dict(ships)
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=step,
        seating_order=["p1"],
        players={"p1": PlayerState(player_id="p1", color="p1", fleet_cc=pool)},
        systems={"000": system},
        rng_seed=1,
    )


def test_report_ignores_fighters_and_planets(registry: StaticDataRegistry) -> None:
    state = _state({"cruiser": 2, "fighter": 9, "infantry": 4}, pool=3)
    state.systems["000"].planet_units["pl"] = {"p1": {"infantry": 3}}
    report = fleet_pool.fleet_report(state, "000", "p1")
    assert report.ships == {"cruiser": 2}
    assert report.total == 2 and report.excess == 0


def test_excess_counts_all_non_fighter_ships() -> None:
    state = _state({"cruiser": 3, "destroyer": 2, "fighter": 5}, pool=3)
    report = fleet_pool.fleet_report(state, "000", "p1")
    assert report.total == 5 and report.excess == 2


def test_next_step_opens_window_and_blocks_until_resolved(
    registry: StaticDataRegistry,
) -> None:
    state = _state({"cruiser": 3, "destroyer": 2}, pool=3)
    opened = tactical.next_step(state, registry)
    assert opened.pending_window is not None
    assert opened.pending_window.window_type is WindowType.FLEET_POOL
    assert opened.tactical_step is TacticalStep.MOVEMENT  # krok zostaje
    with pytest.raises(ValueError, match="fleet pool"):
        tactical.next_step(opened, registry)

    done = fleet_pool.resolve_fleet_pool(opened, registry, "p1", {"destroyer": 2})
    assert done.pending_window is None
    assert done.systems["000"].space_units["p1"] == {"cruiser": 3}
    assert tactical.next_step(done, registry).tactical_step is not TacticalStep.MOVEMENT


def test_no_window_within_pool(registry: StaticDataRegistry) -> None:
    state = _state({"carrier": 2, "fighter": 6}, pool=3)
    moved = tactical.next_step(state, registry)
    assert moved.pending_window is None


def test_resolve_requires_exact_removal(registry: StaticDataRegistry) -> None:
    opened = tactical.next_step(_state({"cruiser": 3, "destroyer": 2}, pool=3), registry)
    with pytest.raises(ValueError, match="remove 1 more"):
        fleet_pool.resolve_fleet_pool(opened, registry, "p1", {"destroyer": 1})
    with pytest.raises(ValueError, match="more ships than"):
        fleet_pool.resolve_fleet_pool(opened, registry, "p1", {"destroyer": 2, "cruiser": 1})
    with pytest.raises(ValueError, match="only 2 destroyer"):
        fleet_pool.resolve_fleet_pool(opened, registry, "p1", {"destroyer": 3})
    with pytest.raises(ValueError, match="non-fighter ships"):
        fleet_pool.resolve_fleet_pool(opened, registry, "p1", {"fighter": 2})


def test_auto_removal_prefers_cheapest(registry: StaticDataRegistry) -> None:
    state = _state({"dreadnought": 2, "destroyer": 2}, pool=2)
    report = fleet_pool.fleet_report(state, "000", "p1")
    assert fleet_pool.auto_removal(state, registry, "p1", report) == {"destroyer": 2}


def test_production_over_pool_is_allowed_then_forced_out(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = _state({"cruiser": 3}, pool=3, step=TacticalStep.PRODUCTION)
    state.players["p1"].faction = "sol"
    state.players["p1"].trade_goods = 20
    state.systems["000"].planet_owners["jord"] = "p1"
    state.systems["000"].planet_units["jord"] = {"p1": {"spacedock": 1}}
    state = production.produce(
        state, grid, registry, "p1", [production.ProductionOrder("destroyer", 1)]
    )
    assert fleet_pool.fleet_report(state, "000", "p1").excess == 1  # produkcja nie blokuje
    opened = tactical.next_step(state, registry)
    assert opened.pending_window is not None
    assert opened.tactical_step is TacticalStep.PRODUCTION


def test_fleet_pool_api(registry: StaticDataRegistry) -> None:
    state = _state({"cruiser": 3, "destroyer": 2}, pool=3)
    client = TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    )
    warn = client.get("/tactical/fleet-pool").json()
    assert warn["active"] is False and warn["known"] is True
    assert warn["pool"] == 3 and warn["total"] == 5 and warn["excess"] == 2

    assert client.post("/tactical/step/next").status_code == 200
    window = client.get("/tactical/fleet-pool").json()
    assert window["active"] is True and window["excess"] == 2
    assert window["suggestion"] == {"destroyer": 2}

    bad = client.post(
        "/tactical/fleet-pool/resolve",
        json={"faction": "p1", "remove": [{"baseType": "destroyer", "count": 1}]},
    )
    assert bad.status_code == 422
    good = client.post(
        "/tactical/fleet-pool/resolve",
        json={"faction": "p1", "remove": [{"baseType": "destroyer", "count": 2}]},
    )
    assert good.status_code == 200
    assert client.get("/tactical/fleet-pool").json()["active"] is False


def test_fleet_pool_view_reports_dock_fighter_slots(registry: StaticDataRegistry) -> None:
    """Dok daje miejsca TYLKO dla myśliwców (capacity) - widok zwraca je do prognozy."""
    state = _state({"carrier": 1, "fighter": 6}, pool=3)
    state.systems["000"].planet_units["pl"] = {"p1": {"spacedock": 1}}
    client = TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    )
    cap = client.get("/tactical/fleet-pool").json()["capacity"]
    assert cap["fighterOnly"] == 3 and cap["general"] == 4
    assert cap["fighters"] == 6 and cap["otherLoad"] == 0 and cap["excess"] == 0


# --- Stały nadzór limitów poza aktywacją (core/limits.py) ---------------------------------


def _outside_activation(ships: dict[str, int]) -> GameState:
    """Nadwyżka statków w systemie, ale BEZ trwającej akcji taktycznej (efekt karty/reliktu)."""
    state = _state(ships, pool=3)
    state.tactical_step = None
    state.active_system = None
    return state


def test_enforce_limits_opens_window_outside_activation(registry: StaticDataRegistry) -> None:
    from src.core import limits

    state = limits.enforce_limits(_outside_activation({"cruiser": 3, "destroyer": 2}), registry)
    window = state.pending_window
    assert window is not None and window.window_type is WindowType.FLEET_POOL
    assert window.context["position"] == "000" and window.queue == ["p1"]


def test_enforce_limits_noop_within_pool_and_in_active_system(
    registry: StaticDataRegistry,
) -> None:
    from src.core import limits

    ok = limits.enforce_limits(_outside_activation({"cruiser": 3}), registry)
    assert ok.pending_window is None
    # Aktywny system trwającej akcji ma własną bramkę kroków - nadzór go pomija.
    active = _state({"cruiser": 3, "destroyer": 2}, pool=3)
    assert limits.enforce_limits(active, registry).pending_window is None


def test_service_commit_enforces_limits_but_god_mode_is_exempt(
    registry: StaticDataRegistry,
) -> None:
    from src.api.connection_manager import ConnectionManager
    from src.api.state_service import StateService
    from src.core import rules_hooks

    rules_hooks.bind_registry(registry)
    service = StateService(EventStore(":memory:"), ConnectionManager())
    over = _outside_activation({"cruiser": 3, "destroyer": 2})
    service.replace_state(over, label="god-mode-patch")
    assert service.current_state().pending_window is None
    service.replace_state(over, label="action-card:x")
    window = service.current_state().pending_window
    assert window is not None and window.window_type is WindowType.FLEET_POOL
