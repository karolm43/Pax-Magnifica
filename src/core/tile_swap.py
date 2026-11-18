"""Wymiana kafla systemu w trakcie gry (Nova Seed Muaat - RULES.md 62.13).

Kafel na pozycji zmienia się na inny (np. supernowa ``81``): ``SystemState.system_id`` i
``GameState.replaced_tiles`` trzymają nowy kafel, mapa (``HexGrid``) jest z nich synchronizowana
przez :func:`sync_grid` (jak strona Wormhole Nexus - ``core/nexus``). Kafel sprzed wymiany
pamięta mapa (``HexGrid.tile_originals``), więc Undo przywraca układ.

F_muaat Nova Seed 3: żetony dowodzenia, żeton frontier i jednostki gracza zostają na nowym
kaflu; pozostałe żetony (wormhole, Ion Storm, ingress, planety-żetony jak Mirage / Avernus)
przepadają. Planety starego kafla wychodzą z gry: tracą kontrolera, załączniki są purge.
Decyzja użytkownika (RULES.md 62.13): siły naziemne gracza z planet kafla trafiają do przestrzeni,
jego struktury z tych planet wracają do rezerwy.
"""

from __future__ import annotations

from src.core import control, exploration, unit_ops
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.system_planets import planets_of_system
from src.core.unit_ops import UnitCause

_SPACE = "space"
_STRUCTURES = ("pds", "spacedock")


def replace_tile(
    state: GameState, registry: StaticDataRegistry, position: str, system_id: str
) -> list[str]:
    """Wymienia kafel na ``position`` na ``system_id`` (MUTUJE ``state``). Zwraca usunięte planety.

    Jednostki na planetach trzeba zniszczyć wcześniej (wołający decyduje, czyje giną); tu
    zostają już tylko jednostki, które przechodzą na nowy kafel.

    Raises:
        ValueError: Nieznany system albo kafel.
    """
    system = state.systems.get(position)
    if system is None:
        raise ValueError(f"Unknown system {position}.")
    if system_id not in registry.systems:
        raise ValueError(f"Unknown system tile {system_id}.")
    planets = planets_of_system(state, registry, position)
    for planet in planets:
        for owner, units in list(system.planet_units.get(planet, {}).items()):
            for base_type, count in list(units.items()):
                if count <= 0:
                    continue
                if base_type not in _STRUCTURES:
                    unit_ops.transfer_units(
                        state, system, planet, system, _SPACE, owner, base_type, count
                    )
                else:
                    unit_ops.remove_units(
                        state, system, planet, owner, base_type, count, UnitCause.REMOVED
                    )
        unit_ops.clear_planet(system, planet)
        if system.planet_owners.get(planet) is not None:
            control.set_planet_control(state, position, planet, None, registry)
        exploration.purge_planet_attachments(state, planet)
    system.added_planets = []
    system.destroyed_planets = []
    system.wormhole_tokens = []
    system.ion_storm = None
    system.ingress_token = False
    system.system_id = system_id
    state.replaced_tiles[position] = system_id
    return planets


def sync_grid(grid: HexGrid, state: GameState, registry: StaticDataRegistry) -> None:
    """Kafle mapy zgodne ze stanem: wymienione wg ``replaced_tiles``, cofnięte (Undo) z powrotem."""
    for position in sorted(grid.tile_originals):
        if position in state.replaced_tiles:
            continue
        _swap(grid, registry, position, grid.tile_originals.pop(position))
    for position, system_id in sorted(state.replaced_tiles.items()):
        if position not in grid.positions:
            continue
        current = grid.system_id_at(position)
        if current == system_id:
            continue
        grid.tile_originals.setdefault(position, current)
        _swap(grid, registry, position, system_id)


def _swap(grid: HexGrid, registry: StaticDataRegistry, position: str, system_id: str) -> None:
    definition = registry.systems.get(system_id)
    if definition is None:
        return
    grid.swap_system_tile(
        position, system_id, list(definition.wormholes), set(definition.anomalies)
    )
