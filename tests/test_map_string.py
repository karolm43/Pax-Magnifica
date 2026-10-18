"""Testy parsera map stringa AsyncTI4 i budowy grafu z pozycji aliasu."""

from __future__ import annotations

import pytest

from src.core.map_string import (
    MECATOL_SYSTEM_ID,
    build_grid_from_map_string,
    parse_map_string,
)
from src.core.positions import load_positions, ordered_positions
from src.core.registry import StaticDataRegistry

# Przykładowy map string (3 pierścienie, 36 pozycji, z pustymi miejscami "0").
SAMPLE = (
    "72 66 77 26 27 34 50 69 76 31 35 37 78 62 75 67 38 65 "
    "0 28 79 0 48 64 0 44 29 0 25 47 0 39 49 0 41 40"
)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


# --- Tabela pozycji ------------------------------------------------------


def test_positions_center_and_ring1() -> None:
    coords = load_positions()
    assert coords["000"].distance(coords["000"]) == 0
    for pos in ["101", "102", "103", "104", "105", "106"]:
        assert coords[pos].distance(coords["000"]) == 1


def test_ordered_positions_skip_center_and_sorted() -> None:
    ordered = ordered_positions()
    assert "000" not in ordered
    assert ordered[:6] == ["101", "102", "103", "104", "105", "106"]
    assert ordered == sorted(ordered, key=int)


# --- Parser --------------------------------------------------------------


def test_parse_adds_center_by_default() -> None:
    tiles = parse_map_string(SAMPLE)
    assert tiles[0].position == "000"
    assert tiles[0].tile_id == MECATOL_SYSTEM_ID


def test_parse_skips_empty_tokens_but_keeps_position_order() -> None:
    tiles = parse_map_string(SAMPLE, include_center=False)
    # 36 tokenów: 30 kafelków systemów + 6 pustych "0" na rogach = 6 slotów domowych.
    systems = [t for t in tiles if not t.is_home_slot]
    homes = [t for t in tiles if t.is_home_slot]
    assert len(systems) == 30
    assert len(homes) == 6
    # Pierwszy kafelek trafia na 101.
    assert systems[0].position == "101"
    assert systems[0].tile_id == "72"
    # Puste "0" na rogach 301/.../316 to sloty domowe (nie przesuwają kafelków).
    positions = {t.position: t for t in tiles}
    assert positions["301"].is_home_slot
    assert positions["301"].home_color == "red"
    assert positions["302"].tile_id == "28"  # kafelek po pierwszym rogu idzie na 302


def test_parse_home_slots_colors() -> None:
    tiles = parse_map_string(SAMPLE, include_center=False)
    homes = {t.position: t.home_color for t in tiles if t.is_home_slot}
    assert homes == {
        "301": "red",
        "304": "green",
        "307": "white",
        "310": "blue",
        "313": "purple",
        "316": "yellow",
    }


def test_parse_empty_raises() -> None:
    with pytest.raises(ValueError):
        parse_map_string("   ")


def test_parse_too_long_raises() -> None:
    too_long = " ".join(["1"] * 1000)
    with pytest.raises(ValueError):
        parse_map_string(too_long)


# --- Budowa grafu --------------------------------------------------------


def test_build_grid_center_adjacency(registry: StaticDataRegistry) -> None:
    grid = build_grid_from_map_string(SAMPLE, registry)
    assert "000" in grid.positions
    assert grid.neighbors("000") == {"101", "102", "103", "104", "105", "106"}


def test_build_grid_all_tiles_known(registry: StaticDataRegistry) -> None:
    """Wszystkie kafelki-systemy przykładowego stringa są w rejestrze.

    Sloty domowe mają pseudo-id i są pomijane w tej weryfikacji.
    """
    tiles = parse_map_string(SAMPLE, include_center=False)
    unknown = [
        t.tile_id
        for t in tiles
        if not t.is_home_slot and t.tile_id not in registry.systems
    ]
    assert unknown == []


def test_build_grid_includes_home_slots(registry: StaticDataRegistry) -> None:
    """Graf zawiera 6 slotów domowych na rogach pierścienia 3."""
    grid = build_grid_from_map_string(SAMPLE, registry)
    for corner in ["301", "304", "307", "310", "313", "316"]:
        assert corner in grid.positions
        assert grid.system_id_at(corner) == "__home__"


def test_build_grid_positions_valid_cube(registry: StaticDataRegistry) -> None:
    grid = build_grid_from_map_string(SAMPLE, registry)
    for pos in grid.positions:
        q, r, s = grid.coordinates(pos)
        assert q + r + s == 0
