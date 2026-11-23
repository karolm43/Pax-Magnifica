"""Anomalie nadawane przez jednostki w trakcie gry (RULES.md 62.17 — Dimensional Tear).

Kafel mapy ma swoje anomalie z danych; jednostki mogą DODAĆ anomalię systemowi („This system is a
gravity rift”). Takie anomalie liczy się ze stanu i synchronizuje z ``HexGrid`` przy każdym odczycie
mapy (jak żetony wormhole) — zniszczenie jednostki od razu kończy efekt (F_vuilraith, ruling 6).
"""

from __future__ import annotations

from src.core import rules_hooks
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid

GRAVITY_RIFT = "GRAVITY_RIFT"


def extra_anomalies(state: GameState) -> dict[str, set[str]]:
    """``{pozycja: anomalie}`` nadane przez jednostki graczy (hook FORBID ``map.gravity_rifts``)."""
    found: dict[str, set[str]] = {}
    for player_id in sorted(state.players):
        for position in rules_hooks.forbidden(
            rules_hooks.POINT_MAP_GRAVITY_RIFTS, state, player_id
        ):
            found.setdefault(str(position), set()).add(GRAVITY_RIFT)
    return found


def sync_grid(grid: HexGrid, state: GameState) -> None:
    """Ustawia w siatce anomalie z jednostek wg stanu."""
    grid.sync_extra_anomalies(extra_anomalies(state))
