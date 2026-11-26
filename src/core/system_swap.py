"""Swapping the positions of two system tiles during the game — ONE place (RULES.md 62.19).

Riftwalker Meian (Creuss hero, *Singularity Reactor*): "Swap the positions of any 2 … systems".
F_creuss: "Any units in either system are moved with their system." and "Any tokens on either
system are moved with their system." — the whole ``SystemState`` (units, control, damage,
command / frontier / faction / wormhole tokens, attached planets) travels with its tile.

The map (``HexGrid``) follows ``GameState.replaced_tiles`` (``tile_swap.sync_grid``, the same
mechanism as Nova Seed), so Undo restores the layout. A player's ``home_position`` (also of an
eliminated player) follows its tile. Functions MUTATE the given state (the caller works on a clone).
"""

from __future__ import annotations

from src.core import board_graph
from src.core.game_state import GameState


def swap_systems(state: GameState, a: str, b: str) -> None:
    """Exchanges the systems at positions ``a`` and ``b`` (MUTATES ``state``).

    Raises:
        ValueError: The same position twice or a position without a system tile.
    """
    if a == b:
        raise ValueError("Choose 2 different systems.")
    tile_a, tile_b = board_graph.system_id_at(state, a), board_graph.system_id_at(state, b)
    if not tile_a or not tile_b:
        raise ValueError("Both positions must hold a system tile.")
    first = board_graph.ensure_system(state, a)
    second = board_graph.ensure_system(state, b)
    state.systems[a] = second.model_copy(update={"position": a}, deep=True)
    state.systems[b] = first.model_copy(update={"position": b}, deep=True)
    state.replaced_tiles[a] = tile_b
    state.replaced_tiles[b] = tile_a
    moved = {a: b, b: a}
    for player in state.players.values():
        if player.home_position in moved:
            player.home_position = moved[player.home_position]
    for gone in state.eliminated_players:
        if gone.home_position in moved:
            gone.home_position = moved[gone.home_position]
