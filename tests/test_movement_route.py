"""Testy trasy ruchu: wybór trasy, waypointy, alternatywy i ładunek po drodze (RULES.md 32.3 T3)."""

from __future__ import annotations

import pytest

from src.core import movement, movement_route
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid(anomalies: dict[str, set[str]] | None = None) -> HexGrid:
    """Centrum 000 + pierścień 1 (101–106) + część pierścienia 2 (201–204)."""
    anomalies = anomalies or {}
    grid = HexGrid()
    for pos in ["000", "101", "102", "103", "106", "201", "202", "203", "204"]:
        grid.place_system(pos, "20", anomalies=anomalies.get(pos, set()))
    grid.build_edges()
    return grid


def _state(systems: dict[str, SystemState]) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={
            "p1": PlayerState(player_id="p1", color="red", technologies=["cv2"]),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems=systems,
    )


def _carrier_at_202(**extra: SystemState) -> GameState:
    """Carrier II (ruch 2, capacity 6) w 202 — dwie równorzędne trasy: przez 101 albo przez 102."""
    return _state(
        {
            "202": SystemState(position="202", system_id="x", space_units={"p1": {"carrier": 1}}),
            **extra,
        }
    )


def test_route_through_waypoint_picks_requested_branch() -> None:
    state = _carrier_at_202()
    grid = _grid()
    assert movement.route_through(state, grid, "202", ["101"], "p1") == ["202", "101", "000"]
    assert movement.route_through(state, grid, "202", ["102"], "p1") == ["202", "102", "000"]


def test_route_through_blocked_waypoint_returns_none() -> None:
    state = _carrier_at_202(
        **{"101": SystemState(position="101", system_id="x", space_units={"p2": {"cruiser": 1}})}
    )
    assert movement.route_through(state, _grid(), "202", ["101"], "p1") is None
    # Bez waypointu BFS omija zablokowany system.
    assert movement.route_through(state, _grid(), "202", [], "p1") == ["202", "102", "000"]


def test_route_error_detects_gaps_and_blocks() -> None:
    state = _carrier_at_202(
        **{"101": SystemState(position="101", system_id="x", space_units={"p2": {"cruiser": 1}})}
    )
    grid = _grid()
    assert movement.route_error(state, grid, ["202", "102", "000"], "p1") is None
    assert "not adjacent" in (movement.route_error(state, grid, ["202", "000"], "p1") or "")
    assert "blocks movement" in (
        movement.route_error(state, grid, ["202", "101", "000"], "p1") or ""
    )
    assert "end at the active" in (movement.route_error(state, grid, ["202", "102"], "p1") or "")


def test_legal_routes_lists_alternatives_sorted_by_length() -> None:
    routes = movement.legal_routes(_carrier_at_202(), _grid(), "202", "p1", max_len=3)
    assert routes[0] in (["202", "101", "000"], ["202", "102", "000"])
    assert ["202", "101", "000"] in routes and ["202", "102", "000"] in routes
    assert ["202", "201", "101", "000"] in routes
    assert [len(r) for r in routes] == sorted(len(r) for r in routes)
    # Krótsze limity odcinają dłuższe trasy.
    short = movement.legal_routes(_carrier_at_202(), _grid(), "202", "p1", max_len=2)
    assert all(len(r) == 3 for r in short)


def test_move_fleet_uses_chosen_route_for_range(registry: StaticDataRegistry) -> None:
    state = _carrier_at_202()
    grid = _grid()
    # Trasa przez 201 ma 3 skoki, a Carrier II ma ruch 2.
    with pytest.raises(ValueError, match="Range too short"):
        movement.move_fleet(
            state, grid, registry, "202", {"carrier": 1}, [], "p1",
            route=["202", "201", "101", "000"],
        )
    moved = movement.move_fleet(
        state, grid, registry, "202", {"carrier": 1}, [], "p1", route=["202", "101", "000"]
    )
    assert moved.systems["000"].space_units["p1"]["carrier"] == 1


def test_pickup_along_route_takes_units_from_passed_system(
    registry: StaticDataRegistry,
) -> None:
    state = _carrier_at_202(
        **{
            "101": SystemState(
                position="101",
                system_id="x",
                space_units={"p1": {"fighter": 2}},
                planet_units={"pl": {"p1": {"infantry": 3}}},
            )
        }
    )
    grid = _grid()
    route = ["202", "101", "000"]
    cargo = [
        movement.CargoPickup("fighter", 2, "space", "101"),
        movement.CargoPickup("infantry", 2, "pl", "101"),
    ]
    moved = movement.move_fleet(
        state, grid, registry, "202", {"carrier": 1}, cargo, "p1", route=route
    )
    dest = moved.systems["000"].space_units["p1"]
    assert dest["carrier"] == 1 and dest["fighter"] == 2 and dest["infantry"] == 2
    # Z mijanego systemu zabrano tylko to, co wskazano.
    assert moved.systems["101"].planet_units["pl"]["p1"]["infantry"] == 1
    assert "fighter" not in moved.systems["101"].space_units.get("p1", {})


def test_pickup_requires_system_on_route(registry: StaticDataRegistry) -> None:
    state = _carrier_at_202(
        **{"101": SystemState(position="101", system_id="x", space_units={"p1": {"fighter": 1}})}
    )
    cargo = [movement.CargoPickup("fighter", 1, "space", "101")]
    # Bez trasy pickup z innego systemu niż start jest zabroniony.
    with pytest.raises(ValueError, match="not on the route"):
        movement.move_fleet(state, _grid(), registry, "202", {"carrier": 1}, cargo, "p1")
    # Trasa przez 102 nie mija 101.
    with pytest.raises(ValueError, match="not on the route"):
        movement.move_fleet(
            state, _grid(), registry, "202", {"carrier": 1}, cargo, "p1",
            route=["202", "102", "000"],
        )


def test_pickup_blocked_by_own_command_token(registry: StaticDataRegistry) -> None:
    state = _carrier_at_202(
        **{
            "101": SystemState(
                position="101",
                system_id="x",
                space_units={"p1": {"fighter": 1}},
                command_tokens=["p1"],
            )
        }
    )
    cargo = [movement.CargoPickup("fighter", 1, "space", "101")]
    with pytest.raises(ValueError, match="command token"):
        movement.move_fleet(
            state, _grid(), registry, "202", {"carrier": 1}, cargo, "p1",
            route=["202", "101", "000"],
        )
    # Raport trasy pomija taki system.
    assert movement.route_cargo(state, registry, ["202", "101", "000"], "p1") == []


def test_route_report_ships_cargo_and_waypoints(registry: StaticDataRegistry) -> None:
    state = _carrier_at_202(
        **{
            "101": SystemState(
                position="101", system_id="x", space_units={"p1": {"fighter": 2}}
            )
        }
    )
    report = movement_route.route_report(state, _grid(), registry, "202", ["101"], "p1")
    assert report.route == ["202", "101", "000"]
    assert report.reason == ""
    assert {"101", "102"} <= set(report.waypoints)
    assert report.alternatives[0] == ["202", "101", "000"]
    (ship,) = report.ships
    assert ship.base_type == "carrier" and ship.reachable and ship.capacity > 0
    assert [(c.position, c.base_type, c.count) for c in report.cargo] == [("101", "fighter", 2)]


def test_route_report_marks_ship_out_of_range(registry: StaticDataRegistry) -> None:
    state = _carrier_at_202()
    report = movement_route.route_report(
        state, _grid(), registry, "202", ["201"], "p1"
    )
    assert report.route == ["202", "201", "101", "000"]
    assert not report.ships[0].reachable
    assert "Range too short" in report.ships[0].reason


def test_route_report_unreachable_waypoints_keep_alternatives(
    registry: StaticDataRegistry,
) -> None:
    state = _carrier_at_202(
        **{"101": SystemState(position="101", system_id="x", space_units={"p2": {"cruiser": 1}})}
    )
    report = movement_route.route_report(state, _grid(), registry, "202", ["101"], "p1")
    assert report.route is None and "waypoints" in report.reason
    assert report.alternatives and report.alternatives[0] == ["202", "102", "000"]


def test_move_route_endpoint_and_move_with_route(registry: StaticDataRegistry) -> None:
    from fastapi.testclient import TestClient

    from src.api.app import create_app
    from src.core.event_store import EventStore

    state = _state(
        {
            "101": SystemState(
                position="101", system_id="x", space_units={"p1": {"carrier": 1, "fighter": 2}}
            )
        }
    )
    state.players["p1"].faction = "sol"
    client = TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    )
    view = client.get("/tactical/move-route", params={"faction": "sol", "from_position": "101"})
    assert view.status_code == 200
    body = view.json()
    assert body["route"] == ["101", "000"] and body["reason"] == ""
    assert [s["baseType"] for s in body["ships"]] == ["carrier"]
    assert [(c["position"], c["baseType"], c["count"]) for c in body["cargo"]] == [
        ("101", "fighter", 2)
    ]

    moved = client.post(
        "/tactical/move",
        json={
            "faction": "sol",
            "fromPosition": "101",
            "ships": [{"baseType": "carrier", "count": 1}],
            "cargo": [{"baseType": "fighter", "count": 2, "fromPosition": "101"}],
            "route": ["101", "000"],
        },
    )
    assert moved.status_code == 200

    # Trasa nie kończąca się w aktywnym systemie jest odrzucana jako 422 z powodem.
    bad = client.post(
        "/tactical/move",
        json={
            "faction": "sol",
            "fromPosition": "101",
            "ships": [{"baseType": "carrier", "count": 1}],
            "route": ["101", "102"],
        },
    )
    assert bad.status_code == 422
