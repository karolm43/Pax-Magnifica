"""Testy mapy demonstracyjnej i eksportu geometrii HexGrid."""

from __future__ import annotations

import pytest

from src.api.demo_map import build_demo_grid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def test_demo_grid_has_center(registry: StaticDataRegistry) -> None:
    grid = build_demo_grid(registry)
    assert "000" in grid.positions
    assert grid.coordinates("000") == (0, 0, 0)


def test_demo_grid_center_is_mecatol(registry: StaticDataRegistry) -> None:
    grid = build_demo_grid(registry)
    # System 18 = Mecatol Rex w danych AsyncTI4 (jeśli obecny w rejestrze).
    if "18" in registry.systems:
        assert grid.system_id_at("000") == "18"


def test_demo_grid_ring_adjacent_to_center(registry: StaticDataRegistry) -> None:
    grid = build_demo_grid(registry)
    ring = grid.positions - {"000"}
    assert ring  # pierścień nie jest pusty
    # Każda pozycja pierścienia 1 sąsiaduje geometrycznie z centrum.
    for pos in ring:
        assert grid.are_adjacent("000", pos)


def test_demo_grid_edges_well_formed(registry: StaticDataRegistry) -> None:
    grid = build_demo_grid(registry)
    for a, b, kind in grid.edges():
        assert a < b  # krawędzie w porządku kanonicznym
        assert kind in {"adjacent", "wormhole"}


def test_demo_grid_tiles_valid_cube(registry: StaticDataRegistry) -> None:
    grid = build_demo_grid(registry)
    for pos in grid.positions:
        q, r, s = grid.coordinates(pos)
        assert q + r + s == 0


def test_demo_tiles_image_files_exist(registry: StaticDataRegistry) -> None:
    """Każdy kafelek demo-mapy ma grafikę obecną na dysku (assets/tiles).

    Weryfikuje realne mapowanie imagePath -> plik (nie zgadywanie). Grafiki są
    poza repo (.gitignore), więc test działa tylko lokalnie z pełnymi assetami.
    """
    from src import config

    grid = build_demo_grid(registry)
    for pos in grid.positions:
        system = registry.systems[grid.system_id_at(pos)]
        assert system.image_path, f"system {system.id} bez imagePath"
        tile_file = config.TILES_DIR / system.image_path
        assert tile_file.is_file(), f"brak grafiki kafelka: {tile_file}"
