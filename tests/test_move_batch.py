"""Batched Move Ships step and guided step entry (RULES.md 32.4, 19.1)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.actor import ACTOR_HEADER
from src.api.app import create_app
from src.api.demo_map import build_demo_grid
from src.core import invasion, movement_batch, tactical
from src.core.event_store import EventStore
from src.core.game_state import (
    GameState,
    InvasionPhase,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    TimingWindow,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_invasion import _PL1, _grid
from tests.test_invasion import _state as invasion_state

P1 = {ACTOR_HEADER: "p1"}


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _sources(grid: HexGrid) -> tuple[str, str]:
    """Two plain systems adjacent to the active ``000`` (no anomalies, so no rift rolls)."""
    plain = sorted(p for p in grid.neighbors("000") if not grid.anomalies_at(p))
    assert len(plain) >= 2
    return plain[0], plain[1]


def _plan_state(grid: HexGrid) -> GameState:
    a, b = _sources(grid)
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=TacticalStep.MOVEMENT,
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", faction="sol", color="red"),
            "p2": PlayerState(player_id="p2", faction="arborec", color="blue"),
        },
        systems={
            a: SystemState(
                position=a, system_id=grid.system_id_at(a),
                space_units={"p1": {"carrier": 1, "infantry": 2}},
            ),
            b: SystemState(
                position=b, system_id=grid.system_id_at(b), space_units={"p1": {"cruiser": 1}}
            ),
        },
    )


def _client(registry: StaticDataRegistry, state: GameState) -> TestClient:
    return TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    )


def _space(client: TestClient, position: str) -> dict[str, int]:
    systems = client.get("/state").json()["state"]["systems"]
    return dict(systems.get(position, {}).get("space_units", {}).get("p1", {}))


def _legs(a: str, b: str) -> list[dict[str, Any]]:
    return [
        {
            "faction": "sol", "fromPosition": a,
            "ships": [{"baseType": "carrier", "count": 1}],
            "cargo": [{"baseType": "infantry", "count": 2}],
        },
        {"faction": "sol", "fromPosition": b, "ships": [{"baseType": "cruiser", "count": 1}]},
    ]


@ruling("R_movement/rules-reference/4")
def test_flight_plan_moves_all_legs_and_one_undo_reverts_it(
    registry: StaticDataRegistry,
) -> None:
    grid = build_demo_grid(registry)
    a, b = _sources(grid)
    client = _client(registry, _plan_state(grid))
    res = client.post("/tactical/move-batch", json={"faction": "sol", "legs": _legs(a, b)},
                      headers=P1)
    assert res.status_code == 200, res.text
    assert _space(client, "000") == {"carrier": 1, "infantry": 2, "cruiser": 1}
    labels = [e["label"] for e in client.get("/history").json()["entries"]][-2:]
    assert [lbl.split(":")[2] for lbl in labels] == [a, b]
    assert len({lbl.split(":")[3] for lbl in labels}) == 1  # one shared flight-plan tag
    # One "Undo movement" reverts the whole plan.
    assert client.post("/tactical/undo-move", headers=P1).status_code == 200
    assert _space(client, "000") == {}
    assert _space(client, a) == {"carrier": 1, "infantry": 2}
    assert _space(client, b) == {"cruiser": 1}


@ruling("R_movement/rules-reference/4")
def test_illegal_leg_rejects_the_whole_plan(registry: StaticDataRegistry) -> None:
    grid = build_demo_grid(registry)
    a, b = _sources(grid)
    client = _client(registry, _plan_state(grid))
    legs = _legs(a, b)
    legs[1]["ships"] = [{"baseType": "cruiser", "count": 5}]  # only 1 cruiser there
    res = client.post("/tactical/move-batch", json={"faction": "sol", "legs": legs}, headers=P1)
    assert res.status_code == 422
    assert f"Leg 2 (from {b})" in res.json()["detail"]
    assert _space(client, "000") == {}  # the legal first leg did not move either
    assert _space(client, a) == {"carrier": 1, "infantry": 2}


def test_empty_plan_and_other_players_plan_are_rejected(registry: StaticDataRegistry) -> None:
    grid = build_demo_grid(registry)
    a, b = _sources(grid)
    client = _client(registry, _plan_state(grid))
    empty = client.post("/tactical/move-batch", json={"faction": "sol", "legs": []}, headers=P1)
    assert empty.status_code == 422
    other = client.post(
        "/tactical/move-batch", json={"faction": "sol", "legs": _legs(a, b)},
        headers={ACTOR_HEADER: "p2"},
    )
    assert other.status_code == 403


@ruling("R_movement/notes/3")
def test_ships_arriving_with_the_plan_cannot_move_again(registry: StaticDataRegistry) -> None:
    """All movement is simultaneous: a later leg cannot fly ships an earlier leg brought in."""
    grid = build_demo_grid(registry)
    a, _b = _sources(grid)
    state = _plan_state(grid)
    legs = [
        movement_batch.MoveLeg(from_pos=a, ships={"carrier": 1}),
        movement_batch.MoveLeg(from_pos="000", ships={"carrier": 1}, route=["000", a, "000"]),
    ]
    with pytest.raises(ValueError, match="Leg 2 .*simultaneously"):
        movement_batch.move_batch(state, grid, registry, "p1", legs)


def test_player_undo_reverts_whole_flight_plan(registry: StaticDataRegistry) -> None:
    grid = build_demo_grid(registry)
    a, b = _sources(grid)
    client = _client(registry, _plan_state(grid))
    res = client.post("/tactical/move-batch", json={"faction": "sol", "legs": _legs(a, b)},
                      headers=P1)
    assert res.status_code == 200, res.text
    undo = client.post("/undo/mine", json={"player_id": "p1"}, headers=P1)
    assert undo.status_code == 200, undo.text
    assert _space(client, "000") == {}
    assert _space(client, a) == {"carrier": 1, "infantry": 2}


@ruling("R_tactical_action/rules-reference/3")
def test_entering_space_combat_starts_it(registry: StaticDataRegistry) -> None:
    """RULES.md 19.1: no "Start space combat" click - the combat opens with the step."""
    state = invasion_state({"p1": {"cruiser": 1}, "p2": {"destroyer": 1}})
    state.tactical_step = TacticalStep.SPACE_CANNON
    client = _client(registry, state)
    assert client.post("/tactical/step/next", headers=P1).status_code == 200
    after = client.get("/state").json()["state"]
    assert after["tactical_step"] == TacticalStep.SPACE_COMBAT.value
    assert after["active_combat"] is not None
    # One step, labelled with the opened event (Activity feed: "space combat started").
    assert client.get("/history").json()["entries"][-1]["label"] == "battle:start:space"


def test_entering_invasion_begins_it_and_it_can_be_skipped(
    registry: StaticDataRegistry,
) -> None:
    state = invasion_state({"p1": {"carrier": 1, "infantry": 2}})
    state.tactical_step = TacticalStep.SPACE_COMBAT
    client = _client(registry, state)
    assert client.post("/tactical/step/next", headers=P1).status_code == 200
    view = client.get("/tactical/invasion").json()
    assert view["active"] is True and view["phase"] == InvasionPhase.COMMIT.value
    # "Skip invasion": nothing lands, the invasion closes, the step can be left.
    assert client.post("/tactical/invasion/skip", headers=P1).status_code == 200
    assert client.get("/tactical/invasion").json()["active"] is False
    assert _space(client, "000") == {"carrier": 1, "infantry": 2}
    assert client.post("/tactical/step/next", headers=P1).status_code == 200


def test_invasion_cannot_be_skipped_after_committing(registry: StaticDataRegistry) -> None:
    state = invasion_state({"p1": {"carrier": 1, "infantry": 2}})
    grid = _grid()
    begun = tactical.auto_open_step(state, grid, registry)
    assert begun is not None and begun[1] == "invasion:begin"
    committed = invasion.commit_ground_forces(begun[0], registry, {_PL1: {"infantry": 1}})
    with pytest.raises(ValueError, match="already committed"):
        tactical.decline_invasion(committed, grid, registry)


def test_auto_open_waits_for_open_window(registry: StaticDataRegistry) -> None:
    state = invasion_state({"p1": {"cruiser": 1}, "p2": {"destroyer": 1}})
    state.tactical_step = TacticalStep.SPACE_COMBAT
    state.pending_window = TimingWindow(window_type=WindowType.CAPACITY, queue=["p1"])
    assert tactical.auto_open_step(state, _grid(), registry) is None
