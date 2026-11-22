"""Żeton „0” Naalu: gracz z żetonem ma inicjatywę 0 — JEDYNE miejsce zmiany (RULES.md 62.16).

R_initiative_order: „A player who has the Naalu "0" token has the initiative number "0".” Żeton
jest efektem trwałym gracza (``active_effects``), a nie znacznikiem na karcie strategii, więc
zamiana kart (Imperial Arbiter) go nie zabiera (F_naalu telepathic 1, gift 1). Kładą go
Telepathic albo Gift of Prescience na końcu fazy strategii; znika na końcu fazy statusu, gdy karty
strategii wracają na stół (R_elimination: także po eliminacji Naalu). Funkcje MUTUJĄ przekazany
stan (klon).
"""

from __future__ import annotations

from src.core import active_effects
from src.core.game_events import Duration
from src.core.game_state import GameState

ZERO_TOKEN = "initiative.zero_token"
ZERO = 0  # „has the initiative number "0"”


def holder(state: GameState) -> str | None:
    """Gracz z żetonem „0” (``None`` = nikt)."""
    for effect in state.active_effects:
        if effect.key == ZERO_TOKEN and effect.owner in state.players:
            return effect.owner
    return None


def place(state: GameState, player_id: str) -> None:
    """Kładzie żeton „0” u gracza (żeton jest jeden - zdejmuje go poprzedniemu posiadaczowi)."""
    clear(state)
    active_effects.add_effect(state, ZERO_TOKEN, Duration.ROUND, owner=player_id)


def clear(state: GameState) -> None:
    """Zdejmuje żeton „0” (koniec fazy statusu)."""
    active_effects.remove_by_key(state, ZERO_TOKEN)


def initiative(state: GameState, player_id: str) -> int | None:
    """Inicjatywa gracza: 0 z żetonem, inaczej najniższa karta strategii (``None`` = bez karty)."""
    if holder(state) == player_id:
        return ZERO
    cards = state.players[player_id].strategy_cards
    return min(cards) if cards else None
