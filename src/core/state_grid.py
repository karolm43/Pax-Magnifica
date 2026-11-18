"""Graf mapy odtwarzany ze STANU gry (dla efektów kart, które nie dostają ``HexGrid``).

Efekty kart akcji mają sygnaturę ``(state, registry, player_id, params)`` - bez siatki mapy.
Karty, którym potrzebne jest sąsiedztwo (sąsiedzi graczy, systemy przyległe), składają
tę samą siatkę co ``AppContext.current_grid``, ale z tego, co jest w ``GameState``:
współrzędne z tabeli pozycji AsyncTI4, wormhole i anomalie z rejestru, żetony wormhole,
portale The Fracture i strona Wormhole Nexus ze stanu.

⚠ ZAŁOŻENIE: system, którego nie ma w ``state.systems`` (nikt go nie dotknął, brak żetonu
frontier), nie jest w siatce. Sąsiedztwo graczy i tak wymaga obecności po obu stronach, a
żeton frontier zawsze leży w stanie, więc wynik zgadza się z siatką aplikacji. Hyperlane'y
nie są uwzględniane (jak w ``core/neighbors.py``).
"""

from __future__ import annotations

from src.core import fracture, nexus, tile_swap
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.positions import load_positions
from src.core.registry import StaticDataRegistry


def grid_from_state(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    """Buduje ``HexGrid`` z systemów obecnych w ``state`` (czysta funkcja, nie mutuje stanu)."""
    coords = load_positions()
    grid = HexGrid()
    for position, system in state.systems.items():
        hex_coord = coords.get(position)
        if hex_coord is None:
            continue  # pozycje poza tabelą (np. kafle The Fracture) dokłada fracture.sync_grid
        definition = registry.systems.get(system.system_id)
        grid.place_system(
            position,
            system.system_id,
            wormholes=list(definition.wormholes) if definition is not None else [],
            anomalies=set(definition.anomalies) if definition is not None else set(),
            hex_override=hex_coord,
        )
    grid.build_edges()
    grid.sync_token_wormholes(
        {pos: s.token_wormholes() for pos, s in state.systems.items() if s.token_wormholes()}
    )
    fracture.sync_grid(grid, state, registry)
    nexus.sync_grid(grid, state, registry)
    tile_swap.sync_grid(grid, state, registry)
    return grid
