"""Jednostki frakcyjne ze zdolnością (flagowce, mechy, ulepszenia frakcyjne) — RULES.md 61.3.

Pomocnik dla hooków ``SOURCE_UNIT``: źródło mówi tylko, że gracz UŻYWA danego wariantu jednostki;
zdolność „in this system" / „this unit" wymaga sprawdzenia, czy jednostka faktycznie jest w danym
systemie (przestrzeń albo planeta). Wariant gracza liczy ``combat.resolve_unit_variant``.
"""

from __future__ import annotations

from src.core.combat import resolve_unit_variant
from src.core.game_state import GameState, SystemState
from src.core.registry import StaticDataRegistry


def variant_of(
    state: GameState, registry: StaticDataRegistry, player_id: str, base_type: str
) -> str | None:
    """Id wariantu jednostki ``base_type``, którego używa gracz (``None``, gdy brak)."""
    player = state.players[player_id]
    unit = resolve_unit_variant(
        registry, player.faction, player.technologies, base_type, player.breakthrough_unlocked,
        player.breakthrough_flipped,
    )
    return unit.id if unit is not None else None


def count_in_system(system: SystemState | None, player_id: str, base_type: str) -> int:
    """Ile jednostek ``base_type`` gracza jest w systemie (przestrzeń + planety)."""
    if system is None:
        return 0
    total = system.space_units.get(player_id, {}).get(base_type, 0)
    for units in system.planet_units.values():
        total += units.get(player_id, {}).get(base_type, 0)
    return total


def has_unit_in(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    unit_id: str,
    position: str | None,
) -> bool:
    """Czy gracz ma w systemie ``position`` jednostkę w wariancie ``unit_id``."""
    unit = registry.units.get(unit_id)
    if unit is None or position is None:
        return False
    if variant_of(state, registry, player_id, unit.base_type) != unit_id:
        return False
    return count_in_system(state.systems.get(position), player_id, unit.base_type) > 0


def positions_with(
    state: GameState, registry: StaticDataRegistry, player_id: str, unit_id: str
) -> list[str]:
    """Systemy, w których gracz ma jednostkę w wariancie ``unit_id``."""
    unit = registry.units.get(unit_id)
    if unit is None or variant_of(state, registry, player_id, unit.base_type) != unit_id:
        return []
    return [
        position
        for position, system in state.systems.items()
        if count_in_system(system, player_id, unit.base_type) > 0
    ]
