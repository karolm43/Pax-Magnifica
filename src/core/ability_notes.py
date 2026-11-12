"""Notatki o zdolnościach działających AUTOMATYCZNIE (RULES.md 62.3, decyzja użytkownika).

Zdolność „you may”, która zawsze się opłaca (Analytical, Brilliant), silnik stosuje sam - ale gracz
ma to zobaczyć. Notatka trafia do feedu Activity jako fakt ``ability_used`` (``core/activity.py``),
a powiadomienie pokazuje się także samemu graczowi. Lista ograniczona do ostatnich wpisów.
"""

from __future__ import annotations

from src.core import rules_hooks
from src.core.game_state import GameState

_KEEP = 30  # tyle ostatnich notatek trzyma stan (feed liczy różnicę po ``seq``)


def note(state: GameState, player_id: str, component: str, detail: str = "") -> None:
    """Dopisuje notatkę „gracz użył komponentu ``component``” (MUTUJE klon)."""
    state.ability_note_seq += 1
    entry = {
        "seq": str(state.ability_note_seq), "player": player_id,
        "component": component, "detail": detail,
    }
    state.ability_notes = [*state.ability_notes[-(_KEEP - 1):], entry]


def note_point(state: GameState, player_id: str, point: str, detail: str = "") -> None:
    """Notatka dla każdego komponentu gracza, którego hook działa w punkcie ``point``."""
    for hook in rules_hooks.hooks_at(point, state, player_id):
        if hook.covers:
            note(state, player_id, hook.covers, detail)
