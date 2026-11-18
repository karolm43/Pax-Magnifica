"""Stosy kart talii: zawartość (talia / odrzucone / purge) i ręczne przenoszenie (debug).

Obsługuje talie eksploracji (cultural / hazardous / industrial / frontier) i talię kart akcji.
Stan jest jedynym źródłem prawdy: karta dobrana znika z talii, odrzucona trafia na stos
odrzuconych, purge'owana na wspólny ``DecksState.purged``.

``move_card`` to NARZĘDZIE DEBUG (God-Mode, RULES.md 46.4): omija reguły, pozwala ustawić
„jaka karta będzie następna" (``top``) albo przenieść kartę między stosami. Funkcje czyste
(``state -> state``), tasowanie przez ``next_rng`` (seedowalne).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core import exploration
from src.core.components import ActionCardDef, ComponentCategory, ExplorationDef
from src.core.dice import next_rng
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

# Talie eksploracji obsługiwane przez widok (frontier — talia istnieje, choć żetony frontier
# nie są jeszcze eksplorowane).
EXPLORE_DECKS: tuple[str, ...] = (*exploration.PLANET_DECKS, "frontier")
MOVE_TARGETS = frozenset({"top", "deck", "discard", "purged"})


@dataclass(frozen=True)
class DeckPiles:
    """Zawartość jednej talii: karty w talii (kolejność = od góry), odrzucone."""

    deck: list[str]
    discard: list[str]


def explore_piles(state: GameState, registry: StaticDataRegistry, deck: str) -> DeckPiles:
    """Stosy talii eksploracji; talia jeszcze niezasiana = pełna, nietknięta."""
    decks = state.decks
    discard = list(decks.exploration_discard.get(deck, []))
    if deck in decks.exploration_deck:
        return DeckPiles(list(decks.exploration_deck[deck]), discard)
    # Niezasiana talia = pełna pula (bez tego, co już odrzucono / purge'owano).
    gone = {*discard, *decks.purged}
    return DeckPiles(
        [c for c in exploration.deck_card_ids(registry, deck, state) if c not in gone], discard
    )


def action_piles(state: GameState) -> DeckPiles:
    """Stosy talii kart akcji."""
    return DeckPiles(list(state.decks.action_card_deck), list(state.decks.action_card_discard))


def _kind_of(registry: StaticDataRegistry, card_id: str) -> tuple[str, str]:
    """(rodzaj talii, klucz) karty: ``("explore", "cultural")`` albo ``("action", "action")``."""
    card = registry.catalog.get(ComponentCategory.EXPLORATION, card_id)
    if isinstance(card, ExplorationDef) and card.type:
        return "explore", card.type.lower()
    action = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
    if isinstance(action, ActionCardDef):
        return "action", "action"
    raise ValueError(f"Unknown card: {card_id}.")


def _detach(state: GameState, kind: str, key: str, card_id: str) -> bool:
    """Wyciąga kartę z talii / odrzuconych / purge; ``True``, gdy gdzieś leżała."""
    decks = state.decks
    piles: list[list[str]] = [decks.purged]
    if kind == "explore":
        piles += [decks.exploration_deck.get(key, []), decks.exploration_discard.get(key, [])]
    else:
        piles += [decks.action_card_deck, decks.action_card_discard]
    for pile in piles:
        if card_id in pile:
            pile.remove(card_id)
            return True
    return False


def move_card(
    state: GameState, registry: StaticDataRegistry, card_id: str, target: str
) -> GameState:
    """Przenosi kartę na stos ``target`` (``top`` = wierzch talii, ``deck`` = w losowe miejsce).

    Karta musi leżeć w którymś ze stosów swojej talii (talia / odrzucone / purge) —
    karty w ręce gracza, przyczepione do planety albo właśnie ujawnione zostają nietknięte.

    Raises:
        ValueError: Nieznana karta / cel albo karta nie leży w żadnym stosie.
    """
    if target not in MOVE_TARGETS:
        raise ValueError(f"Unknown target pile: {target}.")
    kind, key = _kind_of(registry, card_id)
    new_state = state.clone()
    if kind == "explore":
        exploration.seed_deck(new_state, registry, key)
    if not _detach(new_state, kind, key, card_id):
        raise ValueError("This card is not in the deck, discard or purge pile.")

    decks = new_state.decks
    if target == "purged":
        decks.purged.append(card_id)
    elif target == "discard":
        if kind == "explore":
            decks.exploration_discard.setdefault(key, []).append(card_id)
        else:
            decks.action_card_discard.append(card_id)
    else:
        deck = decks.exploration_deck[key] if kind == "explore" else decks.action_card_deck
        if target == "top":
            deck.insert(0, card_id)
        else:
            deck.insert(next_rng(new_state).randint(0, len(deck)), card_id)
    return new_state
