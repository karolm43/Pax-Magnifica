"""Win-probability estimate for the system hover tooltip (core/combat_odds.py)."""

from __future__ import annotations

import pytest

from src.core import combat_odds
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18", anomalies=set())
    grid.build_edges()
    return grid


def _state(space: dict[str, dict[str, int]]) -> GameState:
    center = SystemState(position="000", system_id="18")
    center.space_units = {pid: dict(units) for pid, units in space.items()}
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        seating_order=["p1", "p2"],
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2")},
        systems={"000": center},
    )


def test_bigger_fleet_is_favoured(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"dreadnought": 3}, "p2": {"cruiser": 1}})
    (zone,) = combat_odds.system_odds(state, _grid(), registry, "000")
    assert zone.zone == "space" and zone.attacker == "p1"
    assert zone.attacker_win > 0.95
    assert zone.attacker_win + zone.defender_win + zone.draw == pytest.approx(1, abs=0.01)


def test_symmetric_fleets_are_even_and_stable(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"cruiser": 2}, "p2": {"cruiser": 2}})
    first = combat_odds.system_odds(state, _grid(), registry, "000")
    assert abs(first[0].attacker_win - first[0].defender_win) < 0.06
    assert first == combat_odds.system_odds(state, _grid(), registry, "000")  # seeded


def test_no_odds_without_two_sides(registry: StaticDataRegistry) -> None:
    assert combat_odds.system_odds(
        _state({"p1": {"cruiser": 2}}), _grid(), registry, "000"
    ) == []
    assert combat_odds.system_odds(_state({}), _grid(), registry, "999") == []
