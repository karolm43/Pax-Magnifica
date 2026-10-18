"""Testy HexGrid — współrzędne kubiczne, sąsiedztwo, wormhole, anomalie."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.core.hex_grid import Hex, HexGrid, position_to_hex

# --- Współrzędne kubiczne ------------------------------------------------


def test_center_is_origin() -> None:
    assert position_to_hex("000") == Hex(0, 0, 0)


def test_ring1_all_distance_one() -> None:
    center = position_to_hex("000")
    for i in range(1, 7):
        pos = f"10{i}"
        assert position_to_hex(pos).distance(center) == 1


def test_ring_distance_matches_ring_number() -> None:
    center = position_to_hex("000")
    assert position_to_hex("201").distance(center) == 2
    assert position_to_hex("301").distance(center) == 3


def test_invalid_position_raises() -> None:
    with pytest.raises(ValueError):
        position_to_hex("abc")
    with pytest.raises(ValueError):
        position_to_hex("12")


@given(
    q=st.integers(min_value=-10, max_value=10),
    r=st.integers(min_value=-10, max_value=10),
)
def test_cube_invariant_holds(q: int, r: int) -> None:
    """Dla każdego poprawnego heksa zachodzi q+r+s=0."""
    h = Hex(q, r, -q - r)
    assert h.q + h.r + h.s == 0


def test_invalid_cube_raises() -> None:
    with pytest.raises(ValueError):
        Hex(1, 1, 1)


# --- Sąsiedztwo geometryczne --------------------------------------------


def test_adjacent_geometric() -> None:
    grid = HexGrid()
    grid.place_system("000", "18")  # Mecatol
    grid.place_system("101", "s1")
    grid.place_system("102", "s2")
    grid.build_edges()
    # 101 i 102 sasiaduja z centrum
    assert grid.are_adjacent("000", "101")
    assert grid.are_adjacent("000", "102")
    # Centrum ma pozycje sasiednie
    assert "101" in grid.neighbors("000")


def test_distance_query() -> None:
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("201", "s")
    assert grid.distance("000", "201") == 2


# --- Wormhole ------------------------------------------------------------


def test_wormhole_adjacency() -> None:
    """Dwa odległe systemy z tym samym wormholem są sąsiednie."""
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("201", "wh_a", wormholes=["ALPHA"])
    grid.place_system("305", "wh_b", wormholes=["ALPHA"])
    grid.build_edges()
    # Geometrycznie dalekie...
    assert grid.distance("201", "305") > 1
    # ...ale polaczone wormholem
    assert grid.are_adjacent("201", "305")


def test_different_wormholes_not_adjacent() -> None:
    grid = HexGrid()
    grid.place_system("201", "a", wormholes=["ALPHA"])
    grid.place_system("305", "b", wormholes=["BETA"])
    grid.build_edges()
    assert not grid.are_adjacent("201", "305")


# --- Anomalie ------------------------------------------------------------


def test_supernova_is_impassable_but_still_adjacent() -> None:
    """Supernova jest nieprzejezdna dla RUCHU, ale sąsiedztwo pozostaje.

    Patrz docs/RULES.md 1.3: sąsiedztwo (adjacency) != przejezdność. Supernova
    blokuje ruch, lecz nadal sąsiaduje (potrzebne dla efektów 'w sąsiednim systemie').
    """
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("101", "nova", anomalies={"SUPERNOVA"})
    grid.build_edges()
    assert grid.is_impassable("101")
    assert grid.are_adjacent("000", "101")  # sąsiedztwo istnieje mimo supernowej


def test_nebula_not_impassable() -> None:
    """Nebula nie jest bezwarunkowo nieprzejezdna (warunki w warstwie ruchu)."""
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("101", "neb", anomalies={"NEBULA"})
    grid.build_edges()
    assert not grid.is_impassable("101")
    assert grid.are_adjacent("000", "101")
    assert grid.anomalies_at("101") == {"NEBULA"}


def test_anomalies_recorded() -> None:
    """Anomalie są dostępne jako metadane systemu."""
    grid = HexGrid()
    grid.place_system("101", "rift", anomalies={"GRAVITY_RIFT"})
    grid.place_system("102", "ast", anomalies={"ASTEROID_FIELD"})
    assert grid.anomalies_at("101") == {"GRAVITY_RIFT"}
    assert grid.anomalies_at("102") == {"ASTEROID_FIELD"}
    assert grid.anomalies_at("999") == set()  # nieznany system
