"""Wormhole Nexus: flip 82a → 82b po pojawieniu się jednostki (R_wormhole_nexus)."""

import pytest

from src.core.game_state import GameState, PlayerState, SystemState
from src.core.hex_grid import Hex, HexGrid
from src.core.nexus import activate_nexus, sync_grid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(system: SystemState) -> GameState:
    return GameState(
        players={"p1": PlayerState(player_id="p1", color="red")},
        systems={system.position: system},
    )


def test_pusty_nexus_nie_odwraca_sie() -> None:
    state = _state(SystemState(position="tl", system_id="82a"))
    assert activate_nexus(state).systems["tl"].system_id == "82a"


def test_statek_odwraca_nexus_i_przenosi_planete() -> None:
    system = SystemState(
        position="tl",
        system_id="82a",
        space_units={"p1": {"destroyer": 1}},
        planet_units={"lockedmallice": {"p1": {"infantry": 2}}},
        planet_owners={"lockedmallice": "p1"},
    )
    state = _state(system)
    state.players["p1"].controlled_planets = ["lockedmallice"]
    result = activate_nexus(state)
    flipped = result.systems["tl"]
    assert flipped.system_id == "82b"
    assert flipped.planet_owners == {"mallice": "p1"}
    assert flipped.planet_units == {"mallice": {"p1": {"infantry": 2}}}
    assert result.players["p1"].controlled_planets == ["mallice"]
    assert state.systems["tl"].system_id == "82a"  # oryginał nietknięty


def test_sync_grid_zmienia_wormhole_i_wraca_po_undo(registry: StaticDataRegistry) -> None:
    grid = HexGrid()
    grid.place_system("tl", "82a", wormholes=["GAMMA"], hex_override=Hex(40, -20, -20))
    active = activate_nexus(
        _state(SystemState(position="tl", system_id="82a", space_units={"p1": {"destroyer": 1}}))
    )
    sync_grid(grid, active, registry)
    assert grid.system_id_at("tl") == "82b"
    sync_grid(grid, _state(SystemState(position="tl", system_id="82a")), registry)
    assert grid.system_id_at("tl") == "82a"
