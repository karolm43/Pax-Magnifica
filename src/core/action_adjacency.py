"""Sąsiedztwo systemów w trakcie akcji taktycznej — dla WSZYSTKICH graczy (RULES.md 62.3, 62.7).

Graf mapy (``HexGrid``) trzyma czyste sąsiedztwo. Niektóre efekty aktywnego gracza dodają
sąsiedztwo na czas jego akcji taktycznej (hook FORBID ``movement.extra_adjacent``: Spatial
Conduit Cylinder, Lazax Gate Folding). Rulingi (F_jol_nar, F_winnu) mówią, że takie sąsiedztwo
działa dla wszystkich graczy w tej akcji: Deep Space Cannon innych graczy, odwroty, sąsiedztwo
graczy (neighbors). Ta warstwa jest JEDNYM miejscem, które to liczy (RULES.md 43.1a).

Ruch aktywnego gracza liczy ``movement._neighbors_for_move`` (ten sam punkt + efekty ruchu).
"""

from __future__ import annotations

from src.core import rules_hooks
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid


def extra_adjacent(state: GameState, position: str) -> frozenset[str]:
    """Systemy dodatkowo sąsiadujące z ``position`` w bieżącej akcji taktycznej (bez grafu)."""
    active = state.active_player_id
    if state.tactical_step is None or active is None or active not in state.players:
        return frozenset()
    extra = rules_hooks.forbidden(
        rules_hooks.POINT_MOVEMENT_EXTRA_ADJACENT, state, active, {"position": position}
    )
    return frozenset(extra - {position})


def neighbors(state: GameState, grid: HexGrid, position: str) -> set[str]:
    """Sąsiedzi systemu w tej chwili gry: graf mapy + sąsiedztwo z akcji taktycznej."""
    return set(grid.neighbors(position)) | extra_adjacent(state, position)


def are_adjacent(state: GameState, grid: HexGrid, a: str, b: str) -> bool:
    """Czy dwa systemy sąsiadują teraz (graf mapy albo efekt bieżącej akcji taktycznej)."""
    if grid.are_adjacent(a, b):
        return True
    return b in extra_adjacent(state, a) or a in extra_adjacent(state, b)
