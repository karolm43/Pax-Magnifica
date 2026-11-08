"""Siła armii gracza (panel „Army Strength" w player area) — czyste funkcje.

Liczy per gracz, osobno dla sił NAZIEMNYCH i KOSMICZNYCH, trzy metryki:

- **Resource value** — suma kosztów (``UnitDef.cost``) jednostek na planszy,
- **Hit points** — 1 na jednostkę, +1 gdy ma Sustain Damage,
- **Combat strength** — oczekiwana liczba trafień jednej rundy walki:
  ``kości * (11 - combat_hits_on) / 10``.

Liczą się tylko jednostki bojowe: statki (przestrzeń) oraz piechota/mechy (planety).
Struktury (PDS, dok kosmiczny) pomijamy — nie są częścią armii. Dane liczbowe czytamy
z ``UnitDef`` przez rejestr (zero hardkodowania); wariant jednostki wybiera
``resolve_unit_variant`` (ulepszenia/frakcyjne wg technologii gracza).

Wynik służy też do rankingu 1/2/3 miejsca po stronie frontendu (``calculateArmyRankings``).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.combat import resolve_unit_variant
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry


@dataclass
class ArmyStrength:
    """Metryki armii jednego gracza (ground/space)."""

    space_res: float = 0.0
    ground_res: float = 0.0
    space_health: float = 0.0
    ground_health: float = 0.0
    space_combat: float = 0.0
    ground_combat: float = 0.0


def army_strength_by_player(
    state: GameState, registry: StaticDataRegistry
) -> dict[str, ArmyStrength]:
    """Liczy ``ArmyStrength`` dla każdego gracza ze stanu (przestrzeń + planety)."""
    result: dict[str, ArmyStrength] = {pid: ArmyStrength() for pid in state.players}

    def add(player_id: str, base_type: str, count: int, *, space: bool) -> None:
        player = state.players.get(player_id)
        if player is None or count <= 0:
            return
        unit = resolve_unit_variant(
            registry,
            player.faction,
            player.technologies,
            base_type,
            player.breakthrough_unlocked,
        )
        if unit is None or unit.is_structure:
            return
        hits_on = unit.combat_hits_on
        dice = unit.combat_die_count
        if hits_on is None or dice is None:
            return  # brak wartości walki (placeholder, struktura) — nie jest armią
        res = (unit.cost or 0.0) * count
        health = (2.0 if unit.sustain_damage else 1.0) * count
        combat = count * dice * (11 - hits_on) / 10
        stats = result[player_id]
        if space:
            stats.space_res += res
            stats.space_health += health
            stats.space_combat += combat
        else:
            stats.ground_res += res
            stats.ground_health += health
            stats.ground_combat += combat

    for system in state.systems.values():
        for player_id, by_type in system.space_units.items():
            for base_type, count in by_type.items():
                add(player_id, base_type, count, space=True)
        for by_player in system.planet_units.values():
            for player_id, by_type in by_player.items():
                for base_type, count in by_type.items():
                    add(player_id, base_type, count, space=False)
    return result
