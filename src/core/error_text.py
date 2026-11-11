"""Czytelne komunikaty błędów dla gracza (warstwa prezentacji nad ``ValueError`` z ``core/``).

Reguły w ``core/`` rzucają krótkie angielskie komunikaty z surowymi identyfikatorami
(``It is not p2's turn (active: p1)``). Gracz nie wie, kim jest ``p2``. Ten moduł zamienia
identyfikatory graczy na ``Frakcja (kolor)`` w gotowym tekście, bez ruszania logiki reguł
i bez zmiany kontraktu ``detail: string``. Funkcje CZYSTE, bez HTTP.

Zakres celowo wąski: tylko ID GRACZY (``state.players``) - te nie kolidują ze zwykłymi słowami.
Id planet/kart/technologii opisuje kod, który rzuca błąd (``hooks/card_labels``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry


def _player_label(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    """``Frakcja (kolor)``; samo id, gdy gracz nie ma frakcji."""
    player = state.players.get(player_id)
    if player is None:
        return player_id
    faction = registry.factions.get(player.faction) if player.faction else None
    if faction is None:
        return f"{player.color} player" if player.color else player_id
    return f"{faction.name} ({player.color})" if player.color else faction.name


def humanize(message: str, state: GameState | None, registry: StaticDataRegistry | None) -> str:
    """Zamienia id graczy w komunikacie na ``Frakcja (kolor)``; reszta tekstu bez zmian."""
    if state is None or registry is None or not state.players:
        return message
    labels = {pid: _player_label(state, registry, pid) for pid in state.players}
    # Najdłuższe id najpierw (p10 przed p1); granice słów chronią przed wnętrzem innych słów.
    ids = sorted(labels, key=len, reverse=True)
    pattern = re.compile(r"(?<![\w-])(" + "|".join(re.escape(pid) for pid in ids) + r")(?![\w-])")
    return pattern.sub(lambda m: labels[m.group(1)], message)


def flatten_validation_errors(errors: Sequence[Mapping[str, Any]]) -> str:
    """Spłaszcza listę błędów walidacji Pydantic/FastAPI do jednego zdania dla gracza."""
    parts: list[str] = []
    for error in errors:
        loc = [str(p) for p in error.get("loc", ()) if p not in ("body", "query", "path")]
        field = ".".join(loc)
        message = str(error.get("msg", "Invalid value"))
        parts.append(f"{field}: {message}" if field else message)
    if not parts:
        return "The request is invalid."
    return "The request is invalid - " + "; ".join(parts) + "."
