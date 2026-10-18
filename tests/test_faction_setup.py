"""Testy setupu frakcji: parser startingFleet, umiejscowienie, plan setupu."""

from __future__ import annotations

import pytest

from src.core.faction_setup import (
    apply_setup_to_state,
    build_setup_plan,
    parse_starting_fleet,
)
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import Placement, placement_of


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


# --- Klasyfikacja umiejscowienia (RULES.md 2b) ---------------------------


def test_placement_ships_vs_ground() -> None:
    assert placement_of("warsun") is Placement.SPACE  # mimo isShip=False w danych
    assert placement_of("fighter") is Placement.SPACE
    assert placement_of("mech") is Placement.PLANET  # mimo isShip=True w danych
    assert placement_of("infantry") is Placement.PLANET
    assert placement_of("pds") is Placement.PLANET
    assert placement_of("spacedock") is Placement.PLANET


# --- Parser startingFleet (RULES.md 2c) ----------------------------------


def test_parse_fleet_counts_and_placement() -> None:
    entries = parse_starting_fleet("cv,2 dd,2 ff,4 inf c,sd c", ["creuss"])
    by_type = {e.base_type: e for e in entries}
    assert by_type["carrier"].count == 1
    assert by_type["destroyer"].count == 2
    assert by_type["fighter"].count == 2
    assert by_type["infantry"].count == 4
    assert by_type["infantry"].placement is Placement.PLANET
    assert by_type["carrier"].placement is Placement.SPACE


def test_parse_fleet_invalid_code_raises() -> None:
    with pytest.raises(ValueError):
        parse_starting_fleet("3 zzz x", ["planet"])


# --- Plan setupu per frakcja ---------------------------------------------


def test_setup_plan_arborec(registry: StaticDataRegistry) -> None:
    plan = build_setup_plan(registry.factions["arborec"])
    assert plan.home_system == "05"
    assert plan.space_units == {"carrier": 1, "cruiser": 1, "fighter": 2}
    assert plan.planet_units["nestphar"] == {
        "infantry": 4,
        "pds": 1,
        "spacedock": 1,
    }


def test_setup_plan_xxcha_suffix_collision(registry: StaticDataRegistry) -> None:
    """Xxcha: planety archonren/archontau rozróżnione sufiksami ar/at."""
    plan = build_setup_plan(registry.factions["xxcha"])
    assert "archontau" in plan.planet_units
    assert "archonren" in plan.planet_units
    assert plan.planet_units["archontau"]["pds"] == 1
    assert plan.planet_units["archonren"]["spacedock"] == 1


def test_all_factions_setup_no_crash(registry: StaticDataRegistry) -> None:
    """Każda aktywna frakcja parsuje się i buduje plan bez wyjątku."""
    for faction in registry.factions.values():
        plan = build_setup_plan(faction)
        # Suma jednostek dodatnia dla frakcji z flotą startową.
        if faction.starting_fleet:
            total = sum(plan.space_units.values()) + sum(
                sum(u.values()) for u in plan.planet_units.values()
            )
            assert total > 0


# --- Nanoszenie setupu na stan -------------------------------------------


def test_apply_setup_to_state(registry: StaticDataRegistry) -> None:
    state = apply_setup_to_state(
        GameState(),
        player_id="red",
        color="red",
        faction=registry.factions["arborec"],
        home_position="301",
    )
    assert "red" in state.players
    assert state.players["red"].faction == "arborec"
    assert state.players["red"].color == "red"
    system = state.systems["301"]
    assert system.space_units["red"]["carrier"] == 1
    assert system.planet_units["nestphar"]["red"]["infantry"] == 4
    assert system.planet_owners["nestphar"] == "red"
