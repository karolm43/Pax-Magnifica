"""Test helpers for cooperative ("pull") effects - RULES.md 54.15.

A pull agent used on another player's event is no longer offered to its owner: the beneficiary
requests it (a boost) and the request becomes the owner's offer. Faction tests use these helpers to
reach the offer they used to get directly.
"""

from __future__ import annotations

from src.core import cooperative
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state


def names(state: GameState, registry: StaticDataRegistry, beneficiary: str) -> list[str]:
    """Names of the boosts ``beneficiary`` may request now."""
    grid = grid_from_state(state, registry)
    return [r["name"] for r in cooperative.available(state, registry, grid, beneficiary)]


def request(
    state: GameState,
    registry: StaticDataRegistry,
    beneficiary: str,
    name: str,
    trade_goods: int = 0,
) -> GameState:
    """``beneficiary`` requests the boost called ``name`` (free by default) - new state with the
    owner's offer (``ask``) or the requester's (standing offer / bot owner)."""
    grid = grid_from_state(state, registry)
    rows = cooperative.available(state, registry, grid, beneficiary)
    row = next((r for r in rows if name in r["name"]), None)
    assert row is not None, f"No boost '{name}' for {beneficiary}: {[r['name'] for r in rows]}"
    return cooperative.request(
        state, registry, grid, beneficiary, row["id"], trade_goods=trade_goods, now=0.0
    )
