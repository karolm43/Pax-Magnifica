"""Planety systemu — statyczne (``SystemDef.planets``) + dołożone w trakcie gry.

Thunder's Edge (RULES.md 50) kładzie się na system bez planet, więc lista planet systemu nie
jest już wyłącznie daną statyczną: ``SystemState.added_planets`` dokłada planety. Moduły,
którym zależy na PEŁNEJ liście planet systemu (inwazja, cele, mapa), czytają ją stąd.
"""

from __future__ import annotations

from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


def planets_of_system(
    state: GameState,
    registry: StaticDataRegistry,
    position: str,
    grid: HexGrid | None = None,
) -> list[str]:
    """Wszystkie planety systemu na ``position`` (statyczne, potem dołożone; bez duplikatów).

    ``system_id`` bierzemy z ``grid`` (źródło prawdy o kafelku na pozycji), a bez niego ze stanu.
    """
    system_state = state.systems.get(position)
    if grid is not None and position in grid.positions:
        system_id = grid.system_id_at(position)  # mapa jest źródłem prawdy o kafelku
    elif system_state is not None:
        system_id = system_state.system_id
    else:
        return []
    definition = registry.systems.get(system_id)
    planets = list(definition.planets) if definition is not None else []
    if system_state is not None:
        for planet in system_state.added_planets:
            if planet not in planets:
                planets.append(planet)
        # Zniszczona planeta (Stellar Converter) znika z systemu - system bez innych planet
        # liczy się jako system bez planet (C_relics).
        planets = [p for p in planets if p not in system_state.destroyed_planets]
    return planets
