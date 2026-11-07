"""Testy limitu pojemności w przestrzeni (RULES.md 39.6): wyliczenie, okno, usuwanie, API."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import battle, capacity, tactical
from src.core.combat import resolve_unit_variant
from src.core.event_store import EventStore
from src.core.game_state import (
    CombatStep,
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
    grid.place_system("000", "18", anomalies=set())
    grid.place_system("101", "20", anomalies=set())
    grid.build_edges()
    return grid


def _state(
    space: dict[str, dict[str, int]],
    planet: dict[str, dict[str, int]] | None = None,
    *,
    step: TacticalStep = TacticalStep.MOVEMENT,
) -> GameState:
    center = SystemState(position="000", system_id="18")
    for pid, by_type in space.items():
        center.space_units[pid] = dict(by_type)
    for pid, by_type in (planet or {}).items():
        center.planet_units.setdefault("pl", {})[pid] = dict(by_type)
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=step,
        seating_order=["p1", "p2"],
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2")},
        systems={"000": center},
        rng_seed=1,
    )


def _carrier_capacity(registry: StaticDataRegistry) -> int:
    carrier = resolve_unit_variant(registry, None, [], "carrier")
    assert carrier is not None and carrier.capacity_value
    return carrier.capacity_value


# ------------------------------------------------------------------------ wyliczenie


def test_report_counts_fighters_and_ground_forces_in_space(
    registry: StaticDataRegistry,
) -> None:
    cap = _carrier_capacity(registry)
    state = _state({"p1": {"carrier": 1, "fighter": cap, "infantry": 2}})
    report = capacity.capacity_report(state, registry, "000", "p1")
    assert report.general == cap
    assert report.cargo == {"fighter": cap, "infantry": 2}
    assert report.excess == 2


def test_ground_forces_on_planets_do_not_count(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"cruiser": 1}}, planet={"p1": {"infantry": 5, "mech": 2}})
    assert capacity.capacity_report(state, registry, "000", "p1").excess == 0


def test_space_dock_holds_fighters_only(registry: StaticDataRegistry) -> None:
    dock = resolve_unit_variant(registry, None, [], "spacedock")
    assert dock is not None and dock.capacity_value  # dane: dok ma capacityValue
    state = _state(
        {"p1": {"fighter": dock.capacity_value, "infantry": 1}},
        planet={"p1": {"spacedock": 1}},
    )
    report = capacity.capacity_report(state, registry, "000", "p1")
    assert report.fighter_only == dock.capacity_value
    assert report.excess == 1  # myśliwce na doku, ale piechota w przestrzeni nie ma miejsca


# ---------------------------------------------------------------------------- okno


def test_next_step_opens_capacity_window_and_blocks(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"cruiser": 1, "fighter": 2}})
    checked = tactical.next_step(state, registry)
    window = checked.pending_window
    assert window is not None and window.window_type is WindowType.CAPACITY
    assert window.queue == ["p1"]
    assert checked.tactical_step is TacticalStep.MOVEMENT  # krok zostaje
    with pytest.raises(ValueError, match="exceed capacity"):
        tactical.next_step(checked, registry)
    resolved = capacity.resolve_capacity(checked, registry, "p1", {"fighter": 2})
    assert resolved.pending_window is None
    assert resolved.systems["000"].space_units["p1"] == {"cruiser": 1}
    advanced = tactical.next_step(resolved, registry)
    assert advanced.tactical_step is TacticalStep.SPACE_CANNON


def test_removal_must_be_exact(registry: StaticDataRegistry) -> None:
    cap = _carrier_capacity(registry)
    state = _state({"p1": {"carrier": 1, "fighter": cap + 1, "mech": 1}})
    checked = capacity.open_capacity_check(state, registry, "000")
    with pytest.raises(ValueError, match="Still over"):
        capacity.resolve_capacity(checked, registry, "p1", {"fighter": 1})
    with pytest.raises(ValueError, match="more units"):
        capacity.resolve_capacity(checked, registry, "p1", {"fighter": 3})
    with pytest.raises(ValueError, match="Only fighters"):
        capacity.resolve_capacity(checked, registry, "p1", {"carrier": 1})
    done = capacity.resolve_capacity(checked, registry, "p1", {"fighter": 1, "mech": 1})
    assert done.systems["000"].space_units["p1"] == {"carrier": 1, "fighter": cap}


def test_auto_removal_prefers_cheapest(registry: StaticDataRegistry) -> None:
    cap = _carrier_capacity(registry)
    state = _state({"p1": {"carrier": 1, "fighter": cap, "mech": 1}})
    report = capacity.capacity_report(state, registry, "000", "p1")
    fighter = resolve_unit_variant(registry, None, [], "fighter")
    mech = resolve_unit_variant(registry, None, [], "mech")
    assert fighter is not None and mech is not None
    cheaper = "fighter" if (fighter.cost or 0) < (mech.cost or 0) else "mech"
    assert capacity.auto_removal(report) == {cheaper: 1}


def test_combat_end_opens_capacity_for_winner(registry: StaticDataRegistry) -> None:
    """Zwycięzca z samymi myśliwcami wygrywa walkę, potem traci je przez capacity (C3)."""
    grid = _grid()
    state = _state(
        {"p1": {"fighter": 6, "carrier": 1}, "p2": {"fighter": 1}},
        step=TacticalStep.SPACE_COMBAT,
    )
    started = battle.start_combat(state, grid, registry)
    for seed in range(1, 600):
        candidate = started.clone()
        candidate.rng_seed = seed
        rolled = battle.roll_round(candidate, grid, registry)
        combat = rolled.active_combat
        assert combat is not None
        # p1 trafia myśliwca p2, p2 trafia carriera p1 → p1 zostaje z samymi myśliwcami.
        if combat.pending_hits.get("p2", 0) >= 1 and combat.pending_hits.get("p1", 0) == 1:
            break
    else:
        raise AssertionError("no seed")
    after_p2 = battle.assign_combat_hits(
        rolled, grid, registry, "p2", sustain={}, destroy={"fighter": 1}, destroy_damaged={}
    )
    done = battle.assign_combat_hits(
        after_p2, grid, registry, "p1", sustain={}, destroy={"carrier": 1}, destroy_damaged={}
    )
    combat = done.active_combat
    assert combat is not None and combat.step is CombatStep.DONE and combat.winner == "p1"
    window = done.pending_window
    assert window is not None and window.window_type is WindowType.CAPACITY
    cleared = capacity.resolve_capacity(done, registry, "p1", {"fighter": 6})
    assert "p1" not in cleared.systems["000"].space_units


# --------------------------------------------------------------------------- API


def test_api_capacity_flow(registry: StaticDataRegistry) -> None:
    state = capacity.open_capacity_check(
        _state({"p1": {"cruiser": 1, "fighter": 1, "infantry": 1}}), registry, "000"
    )
    client = TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    )
    view: dict[str, Any] = client.get("/tactical/capacity").json()
    assert view["active"] is True and view["playerId"] == "p1"
    assert view["excess"] == 2
    assert {c["baseType"] for c in view["cargo"]} == {"fighter", "infantry"}
    assert sum(view["suggestion"].values()) == 2
    bad = client.post(
        "/tactical/capacity/resolve",
        json={"faction": "p1", "remove": [{"baseType": "fighter", "count": 1}]},
    )
    assert bad.status_code == 422
    ok = client.post(
        "/tactical/capacity/resolve",
        json={
            "faction": "p1",
            "remove": [{"baseType": "fighter", "count": 1}, {"baseType": "infantry"}],
        },
    )
    assert ok.status_code == 200
    assert client.get("/tactical/capacity").json()["active"] is False
