"""Obserwacja bota: dokładnie to, co dostaje klient człowieka na tym miejscu (RULES.md 65.2).

Klient sieciowy widzi ścisłą projekcję stanu (``visibility.project_strict``) i, przez osobne
endpointy GET, WŁASNE monity liczone przez ``core/`` na pełnym stanie: opcje bieżącego kroku
karty strategii (``strategic_action.step_options`` — np. agendy podejrzane przez Politics) i
własne oferty z legalnymi opcjami (``offers.offers_view``). Bot dostaje to samo, nic więcej.

``observe`` jest jedynym miejscem warstwy bota, które dotyka pełnego stanu; zwraca dane
serializowalne (gotowe do wysłania do procesu roboczego w B2).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.core import offers, strategic_action, visibility
from src.core.game_state import GameState
from src.engine.actions import EngineContext


class Observation(BaseModel):
    """Widok jednego gracza: projekcja stanu + jego prywatne monity."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    view: GameState
    # Zegar serwera w chwili obserwacji (okna o stałej długości: kiedy wolno je zamknąć).
    now: float = 0.0
    # Monit karty strategii dla TEGO gracza (primary właściciela albo secondary respondenta).
    strategy_prompt: dict[str, Any] | None = None
    # Oferty czekające na TEGO gracza (opis + wejścia formularza z legalnymi opcjami).
    offers: list[dict[str, Any]] = Field(default_factory=list)


def observe(state: GameState, ctx: EngineContext, player_id: str) -> Observation:
    """Buduje obserwację gracza ``player_id`` z pełnego stanu (czysta funkcja)."""
    return Observation(
        player_id=player_id,
        now=ctx.now,
        view=visibility.project_strict(state, player_id),
        strategy_prompt=strategic_action.step_options(state, ctx.registry, player_id, ctx.grid),
        offers=offers.offers_view(state, ctx.registry, player_id),
    )
