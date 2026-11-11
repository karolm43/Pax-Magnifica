"""Żeton Ion Storm (karta frontier): wormhole zmieniający stronę po użyciu (R: C_exploration_cards).

Żeton leży w systemie (``SystemState.ion_storm`` = "ALPHA"/"BETA") i jest wormholem tej strony
(graf: ``SystemState.token_wormholes``). Gdy w kroku ruchu albo odwrotu akcji taktycznej statki
przejdą przez ten wormhole, na KOŃCU kroku żeton obraca się na drugą stronę. Ruch poza tymi
krokami (np. Skilled Retreat) żetonu nie obraca. Funkcje mutują przekazany ``state`` (klon).

Adjacency != traversability: ``HexGrid`` trzyma czyste sąsiedztwo; tu rozstrzygamy tylko, czy
konkretny ruch SKORZYSTAŁ z wormhole (a nie z sąsiedztwa geometrycznego).

⚠ ZAŁOŻENIA: (1) użycie wykrywamy dla ruchu, którego koniec (źródło albo aktywny system) jest
systemem z żetonem, a drugi koniec ma wormhole tej samej strony i nie sąsiaduje geometrycznie;
trasy wielokrokowe przez Ion Storm jako system pośredni nie są wykrywane; (2) gdy system z żetonem
ma też własny wormhole tego samego typu, zakładamy użycie żetonu.
"""

from __future__ import annotations

from src.core import board_graph
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

_OTHER_SIDE = {"ALPHA": "BETA", "BETA": "ALPHA"}


def uses_ion_storm(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, from_pos: str, to_pos: str
) -> str | None:
    """Pozycja systemu z Ion Storm, jeśli ruch ``from_pos -> to_pos`` idzie jego wormhole."""
    for storm_pos, other in ((from_pos, to_pos), (to_pos, from_pos)):
        system = state.systems.get(storm_pos)
        if system is None or not system.ion_storm:
            continue
        if grid.link_kind(storm_pos, other) != "wormhole":
            continue
        if system.ion_storm in board_graph.wormholes_at(state, registry, other):
            return storm_pos
    return None


def note_move(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, from_pos: str, to_pos: str
) -> None:
    """Zapamiętuje, że w tej akcji ruch skorzystał z Ion Storm (flip na końcu kroku)."""
    storm_pos = uses_ion_storm(state, grid, registry, from_pos, to_pos)
    if storm_pos is not None and storm_pos not in state.ion_storm_used:
        state.ion_storm_used = [*state.ion_storm_used, storm_pos]


def flip_used(state: GameState) -> list[str]:
    """Obraca żetony użyte w kroku (koniec Move Ships / Retreat); zwraca ich pozycje."""
    flipped: list[str] = []
    for position in state.ion_storm_used:
        system = state.systems.get(position)
        if system is not None and system.ion_storm in _OTHER_SIDE:
            system.ion_storm = _OTHER_SIDE[system.ion_storm]
            flipped.append(position)
    state.ion_storm_used = []
    return flipped
