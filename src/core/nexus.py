"""Wormhole Nexus (kafelek 82): flip na stronę aktywną (alpha + beta + gamma).

Źródło: docs/rules_tirules/R_wormhole_nexus.md. Nexus zaczyna grę stroną nieaktywną (82a, tylko
gamma). Gdy w systemie pojawi się jakakolwiek jednostka (statek, wojska, struktura) albo ktoś
przejmie planetę Mallice, kafelek odwraca się na stronę aktywną (82b). Jednostki i żetony
przechodzą na aktywną stronę.

Flip jest zapisany w stanie (``SystemState.system_id`` = ``82b``), więc Undo/Redo działa samo;
mapa (``HexGrid``) jest z niego synchronizowana przez ``sync_grid``.

⚠️ ZAŁOŻENIE: reguła mówi, że po ruchu statku flip następuje dopiero na końcu kroku Movement
(wpływa to tylko na okno Space Cannon Offense po ruchu). Tu flip następuje przy zapisie stanu
po akcji (ruch/produkcja/inwazja/God-Mode), czyli po całym kroku ruchu.
"""

from __future__ import annotations

from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

NEXUS_LOCKED_ID = "82a"
NEXUS_ACTIVE_ID = "82b"
LOCKED_PLANET_ID = "lockedmallice"
ACTIVE_PLANET_ID = "mallice"


def _rename_key[V](data: dict[str, V], old: str, new: str) -> None:
    if old in data:
        data[new] = data.pop(old)


def activate_nexus(state: GameState) -> GameState:
    """Zwraca stan, w którym zajęty Nexus 82a jest odwrócony na 82b (bez zmian, gdy nie trzeba)."""
    targets = [
        pos
        for pos, system in state.systems.items()
        if system.system_id == NEXUS_LOCKED_ID
        and (
            any(units for units in system.space_units.values())
            or any(
                units for by_player in system.planet_units.values() for units in by_player.values()
            )
            or system.planet_owners
        )
    ]
    if not targets:
        return state
    new_state = state.clone()
    for pos in targets:
        system = new_state.systems[pos]
        system.system_id = NEXUS_ACTIVE_ID
        _rename_key(system.planet_units, LOCKED_PLANET_ID, ACTIVE_PLANET_ID)
        _rename_key(system.planet_owners, LOCKED_PLANET_ID, ACTIVE_PLANET_ID)
        _rename_key(system.damaged_units, LOCKED_PLANET_ID, ACTIVE_PLANET_ID)
    for player in new_state.players.values():
        player.controlled_planets = [
            ACTIVE_PLANET_ID if p == LOCKED_PLANET_ID else p for p in player.controlled_planets
        ]
        player.exhausted_planets = [
            ACTIVE_PLANET_ID if p == LOCKED_PLANET_ID else p for p in player.exhausted_planets
        ]
    _rename_key(new_state.planet_attachments, LOCKED_PLANET_ID, ACTIVE_PLANET_ID)
    inv = new_state.invasion
    if inv is not None:
        # Quantum Dissemination na Mallice przed odwróceniem (F_yin Ω): zaangażowana piechota
        # zostaje przypisana do tej samej planety po flipie (Establish Control ją przejmie).
        for zone in (inv.committed, inv.last_commit, inv.combat_results):
            _rename_key(zone, LOCKED_PLANET_ID, ACTIVE_PLANET_ID)
        for queued in inv.queue:
            _rename_key(queued.get("committed", {}), LOCKED_PLANET_ID, ACTIVE_PLANET_ID)
    return new_state


def sync_grid(grid: HexGrid, state: GameState, registry: StaticDataRegistry) -> None:
    """Ustawia na mapie stronę Nexusa zgodną ze stanem (aktywna po flipie, nieaktywna po Undo)."""
    for pos in sorted(grid.positions):
        current = grid.system_id_at(pos)
        if current not in (NEXUS_LOCKED_ID, NEXUS_ACTIVE_ID):
            continue
        system = state.systems.get(pos)
        wanted = system.system_id if system and system.system_id in (
            NEXUS_LOCKED_ID,
            NEXUS_ACTIVE_ID,
        ) else NEXUS_LOCKED_ID
        if wanted == current:
            continue
        definition = registry.systems.get(wanted)
        if definition is None:
            continue
        grid.swap_system_tile(
            pos, wanted, list(definition.wormholes), set(definition.anomalies)
        )
