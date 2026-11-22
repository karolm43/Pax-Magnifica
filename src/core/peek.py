"""Stały podgląd ukrytych informacji przez zdolność gracza — JEDNO miejsce (RULES.md 62.16).

M'aban (commander Naalu): „At any time: You may look at your neighbors' hands of promissory notes
and the top and bottom card of the agenda deck.” „W każdej chwili” = podgląd stały, nie akcja:
właściciel dostaje te karty w swoim widoku (web-data), inni nie. Rodzaje podglądu daje hook FORBID
``info.peek`` (``NEIGHBORS_PROMISSORY``, ``AGENDA_TOP``, ``AGENDA_BOTTOM``) - bez nazw frakcji.

F_naalu M'aban Ω: bez podglądu talii agend, gdy ktoś rozstrzyga primary Politics (1); ukryta agenda
Covert Legislation leży już poza talią (``agenda.covert_card``), więc wierzchnia karta to następna
(2). Funkcja nie mutuje stanu.
"""

from __future__ import annotations

from typing import Any

from src.core import neighbors, rules_hooks
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.strategy_cards import politics

NEIGHBORS_PROMISSORY = "neighbors_promissory"
AGENDA_TOP = "agenda_top"
AGENDA_BOTTOM = "agenda_bottom"


def kinds(state: GameState, player_id: str) -> frozenset[str]:
    """Rodzaje podglądu, które gracz ma teraz (hooki ``info.peek``)."""
    if player_id not in state.players:
        return frozenset()
    return rules_hooks.forbidden(rules_hooks.POINT_INFO_PEEK, state, player_id)


def _politics_resolving(state: GameState) -> bool:
    pending = state.pending_strategy
    return pending is not None and pending.initiative == politics.INITIATIVE


def view(state: GameState, grid: HexGrid, player_id: str | None) -> dict[str, Any] | None:
    """Podgląd gracza ``{neighbors: {gracz: [notki]}, agendaTop, agendaBottom}`` albo ``None``.

    Liczone na PEŁNYM stanie (przed projekcją widoczności) - zwraca tylko to, co gracz może
    zobaczyć. Pusta talia / brak sąsiadów = puste pola.
    """
    if player_id is None:
        return None
    allowed = kinds(state, player_id)
    if not allowed:
        return None
    result: dict[str, Any] = {"neighbors": {}, "agendaTop": None, "agendaBottom": None}
    if NEIGHBORS_PROMISSORY in allowed:
        result["neighbors"] = {
            pid: list(state.players[pid].private.promissory_notes)
            for pid in sorted(neighbors.neighbors_of(player_id, state, grid))
            if pid in state.players
        }
    deck = state.decks.agenda_deck
    if deck and not _politics_resolving(state):
        if AGENDA_TOP in allowed:
            result["agendaTop"] = deck[0]
        if AGENDA_BOTTOM in allowed:
            result["agendaBottom"] = deck[-1]
    return result
