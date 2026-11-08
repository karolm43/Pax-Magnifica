"""Hooki technologii. Aliasy technologii pochodzą z danych (``assets/.../technologies``)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core.game_state import GameState
from src.core.rules_hooks import (
    POINT_MOVEMENT_ENTER_ASTEROIDS,
    SOURCE_TECHNOLOGY,
    HookKind,
    HookSource,
    register,
)

# Alias Antimass Deflectors (z danych: technologies/pok.json -> "amd"; nie z pamięci).
# Weryfikowany testem względem rejestru (tests/test_movement.py).
ANTIMASS_ALIAS = "amd"


@register(
    POINT_MOVEMENT_ENTER_ASTEROIDS,
    HookSource(SOURCE_TECHNOLOGY, ANTIMASS_ALIAS),
    HookKind.PERMIT,
    covers=f"technologies:{ANTIMASS_ALIAS}",
)
def antimass_enter_asteroids(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> bool:
    """Antimass Deflectors: statki mogą wchodzić do pól asteroid i przez nie przechodzić."""
    return True
