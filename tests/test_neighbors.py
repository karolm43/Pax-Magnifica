"""Testy sąsiedztwa graczy (Neighbors) — RULES.md 2 / R_neighbors.

Reguła (źródło: tirules2.com → ``docs/rules_tirules/R_neighbors.md``): dwóch
graczy jest sąsiadami, jeśli obaj mają jednostkę lub kontrolują planetę w tym
samym systemie LUB w systemach wzajemnie sąsiednich (sąsiedztwo przez wormhole
wliczone). Stan budowany jawnie (nie z pamięci reguł).
"""

from __future__ import annotations

from src.core.game_state import GameState, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.neighbors import neighbors_by_player, neighbors_of
from tests.rulings import ruling


def _ring_grid() -> HexGrid:
    """Centrum 000 + pierścień 1 (101..106) — każdy z 101.. sąsiaduje z 000."""
    grid = HexGrid()
    grid.place_system("000", "18")
    for pos in ("101", "102", "103", "104", "105", "106"):
        grid.place_system(pos, "20")
    grid.build_edges()
    return grid


def _two_players() -> dict[str, PlayerState]:
    return {
        "p1": PlayerState(player_id="p1", color="red"),
        "p2": PlayerState(player_id="p2", color="blue"),
    }


def test_same_system_are_neighbors() -> None:
    grid = _ring_grid()
    state = GameState(
        players=_two_players(),
        systems={
            "000": SystemState(
                position="000",
                system_id="18",
                space_units={"p1": {"destroyer": 1}, "p2": {"carrier": 1}},
            ),
        },
    )
    assert neighbors_of("p1", state, grid) == {"p2"}
    assert neighbors_of("p2", state, grid) == {"p1"}


def test_adjacent_systems_are_neighbors() -> None:
    grid = _ring_grid()
    state = GameState(
        players=_two_players(),
        systems={
            "000": SystemState(
                position="000", system_id="18", space_units={"p1": {"cruiser": 1}}
            ),
            "101": SystemState(
                position="101", system_id="20", space_units={"p2": {"cruiser": 1}}
            ),
        },
    )
    assert neighbors_of("p1", state, grid) == {"p2"}


def test_non_adjacent_systems_not_neighbors() -> None:
    grid = _ring_grid()
    # 101 i 104 leżą po przeciwnych stronach pierścienia — nie sąsiadują.
    assert not grid.are_adjacent("101", "104")
    state = GameState(
        players=_two_players(),
        systems={
            "101": SystemState(
                position="101", system_id="20", space_units={"p1": {"cruiser": 1}}
            ),
            "104": SystemState(
                position="104", system_id="20", space_units={"p2": {"cruiser": 1}}
            ),
        },
    )
    assert neighbors_of("p1", state, grid) == set()
    assert neighbors_of("p2", state, grid) == set()


def test_planet_control_counts_without_units() -> None:
    grid = _ring_grid()
    state = GameState(
        players=_two_players(),
        systems={
            "000": SystemState(
                position="000",
                system_id="18",
                planet_owners={"mr": "p1"},
                space_units={"p2": {"cruiser": 1}},
            ),
        },
    )
    # p1 jest obecny tylko przez kontrolę planety — nadal sąsiad p2 w tym systemie.
    assert neighbors_of("p1", state, grid) == {"p2"}


def test_empty_unit_stacks_do_not_count() -> None:
    grid = _ring_grid()
    state = GameState(
        players=_two_players(),
        systems={
            "000": SystemState(
                position="000",
                system_id="18",
                space_units={"p1": {"destroyer": 0}, "p2": {"carrier": 1}},
            ),
        },
    )
    # p1 ma wpis z zerową liczebnością = brak obecności → brak sąsiedztwa.
    assert neighbors_of("p1", state, grid) == set()
    assert neighbors_of("p2", state, grid) == set()


def test_player_is_not_own_neighbor() -> None:
    grid = _ring_grid()
    state = GameState(
        players={"p1": PlayerState(player_id="p1", color="red")},
        systems={
            "000": SystemState(
                position="000", system_id="18", space_units={"p1": {"destroyer": 2}}
            ),
            "101": SystemState(
                position="101", system_id="20", space_units={"p1": {"cruiser": 1}}
            ),
        },
    )
    assert neighbors_of("p1", state, grid) == set()


def test_neighbors_by_player_is_symmetric() -> None:
    grid = _ring_grid()
    state = GameState(
        players=_two_players(),
        systems={
            "000": SystemState(
                position="000", system_id="18", space_units={"p1": {"cruiser": 1}}
            ),
            "101": SystemState(
                position="101", system_id="20", space_units={"p2": {"cruiser": 1}}
            ),
        },
    )
    result = neighbors_by_player(state, grid)
    assert result == {"p1": {"p2"}, "p2": {"p1"}}


@ruling("R_neutral_units/notes/8")
def test_neutral_units_are_nobodys_neighbor() -> None:
    """R_neutral_units: „there is no neutral player” - neutralne statki obok gracza (Pirate
    Contract) nie robią z „neutral” sąsiada (wcześniej KeyError w postępie Push Boundaries)."""
    grid = _ring_grid()
    state = GameState(
        players=_two_players(),
        systems={
            "000": SystemState(
                position="000", system_id="18", space_units={"p1": {"carrier": 1}}
            ),
            "101": SystemState(
                position="101", system_id="20", space_units={"neutral": {"destroyer": 1}}
            ),
        },
    )

    assert neighbors_of("p1", state, grid) == set()
    assert neighbors_by_player(state, grid) == {"p1": set(), "p2": set()}
