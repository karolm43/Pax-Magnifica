"""Wspólna baza katalogu akcji bota: kontekst, klasa bazowa i kontrola aktora jak w routerach.

Osobny moduł, żeby katalog mógł być podzielony na pliki tematyczne (``actions`` — szkielet rundy,
``actions_tactical`` — akcja taktyczna, walka, inwazja, karty) bez cyklicznych importów.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.core import actor as actor_rules
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@dataclass(frozen=True)
class EngineContext:
    """Zależności stosowania akcji: dane statyczne, siatka mapy i zegar serwera.

    ``now`` = czas serwera w sekundach (wstrzykiwany, nigdy ``time.time()`` - RULES.md 65.5);
    potrzebny oknom o stałej długości (pauza reakcji, hold-play) i zegarowi szachowemu.
    """

    registry: StaticDataRegistry
    grid: HexGrid
    now: float = 0.0


class ActionBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    player_id: str


Guard = Callable[[GameState, str], None]
Apply = Callable[[GameState, EngineContext, Any], GameState]


def claimed(what: str) -> Guard:
    """Kontrola jak ``actor_rules.check(state, actor, player_id, None, what)`` w routerze."""
    return lambda state, pid: actor_rules.check(state, pid, pid, None, what)


def entitled(allowed: Callable[[GameState], list[str | None]], what: str) -> Guard:
    """Kontrola jak ``actor_rules.require(state, actor, allowed(state), what)`` w routerze."""
    return lambda state, pid: actor_rules.require(state, pid, allowed(state), what)


def checked(allowed: Callable[[GameState], list[str | None]], what: str) -> Guard:
    """Kontrola jak ``actor_rules.check(state, actor, None, allowed, what)`` w routerze."""
    return lambda state, pid: actor_rules.check(state, pid, None, allowed, what)
