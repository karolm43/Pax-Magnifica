"""Arborec — hooki frakcji. Teksty zdolności: ``assets/data/abilities`` (nie z pamięci)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core.game_state import GameState
from src.core.rules_hooks import (
    POINT_PRODUCTION_FORBIDS,
    SOURCE_FACTION,
    HookKind,
    HookSource,
    register,
)


@register(POINT_PRODUCTION_FORBIDS, HookSource(SOURCE_FACTION, "arborec"), HookKind.FORBID)
def arborec_dock_no_infantry(
    _state: GameState, _player_id: str, ctx: Mapping[str, Any]
) -> tuple[str, ...]:
    """Arborec: wartość PRODUCTION doków nie służy do produkcji piechoty (R_production).

    Piechota Arborec ma własne PRODUCTION 1 i nadal może produkować (RULES.md 33).
    """
    return ("infantry",) if ctx.get("producer_type") == "spacedock" else ()
