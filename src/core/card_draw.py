"""Dobieranie kart z talii wspólnych (karty akcji, agendy) — czyste operacje na klonie.

Wspólne dla eksploracji, kart strategii (Politics) i fazy statusu. Pusta talia dobierana
tasuje się z własnego stosu odrzuconych (seedowalny RNG stanu — ``core/dice.py``).
"""

from __future__ import annotations

from src.core.dice import next_rng
from src.core.game_state import GameState
from src.core.objectives import deck_card_ids
from src.core.registry import StaticDataRegistry

_AGENDA_DECK = "agenda"


def draw_action_card(state: GameState, player_id: str) -> bool:
    """Dobiera kartę akcji do ręki gracza (mutuje ``state``); False, gdy talie puste."""
    decks = state.decks
    if not decks.action_card_deck and decks.action_card_discard:
        reshuffled = list(decks.action_card_discard)
        next_rng(state).shuffle(reshuffled)
        decks.action_card_deck = reshuffled
        decks.action_card_discard = []
    if not decks.action_card_deck:
        return False
    state.players[player_id].private.action_cards.append(decks.action_card_deck.pop(0))
    return True


def ensure_agenda_deck(state: GameState, registry: StaticDataRegistry) -> None:
    """Leniwie zasiewa talię agend (pełna talia aktywnych źródeł, potasowana).

    Talia powstaje raz: dopóki ``agenda_deck_seeded`` jest False. Potem pusta talia nie
    jest już zasiewana (agendy zużyte w fazie agendy trafiają na stos odrzuconych).
    """
    decks = state.decks
    if decks.agenda_deck_seeded:
        return
    cards = deck_card_ids(registry, _AGENDA_DECK)
    next_rng(state).shuffle(cards)
    decks.agenda_deck = cards
    decks.agenda_discard = []
    decks.agenda_deck_seeded = True
