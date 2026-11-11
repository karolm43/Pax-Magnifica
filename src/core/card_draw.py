"""Dobieranie kart z talii wspólnych (karty akcji, agendy) — czyste operacje na klonie.

Wspólne dla eksploracji, kart strategii (Politics) i fazy statusu. Pusta talia dobierana
tasuje się z własnego stosu odrzuconych (seedowalny RNG stanu — ``core/dice.py``).
"""

from __future__ import annotations

from src.core import triggers
from src.core.dice import next_rng
from src.core.game_events import GameEvent, Moment
from src.core.game_state import ActionDiscardTrace, GameState
from src.core.registry import StaticDataRegistry


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
    triggers.fire(
        state,
        GameEvent.ACTION_CARDS_DRAWN,
        Moment.WHEN,
        subject=player_id,
        ctx={"player": player_id, "amount": 1},
    )
    state.players[player_id].private.action_cards.append(decks.action_card_deck.pop(0))
    triggers.fire(
        state,
        GameEvent.ACTION_CARDS_DRAWN,
        Moment.AFTER,
        subject=player_id,
        ctx={"player": player_id, "amount": 1},
    )
    return True


def discard_action_cards(state: GameState, player_id: str, count: int) -> list[str]:
    """Odrzuca ``count`` pierwszych kart akcji z ręki gracza na stos odrzuconych (mutuje).

    Returns:
        Odrzucone karty (kolejność z ręki).
    """
    hand = state.players[player_id].private.action_cards
    discarded = hand[:count]
    state.players[player_id].private.action_cards = hand[count:]
    state.decks.action_card_discard.extend(discarded)
    _record_discards(state, player_id, discarded)
    return discarded


def _record_discards(state: GameState, player_id: str, cards: list[str]) -> None:
    """Zapisuje ślad odrzucenia (okno „po odrzuceniu karty akcji”) i emituje zdarzenie (mutuje)."""
    for card in cards:
        state.last_action_discard = ActionDiscardTrace(player=player_id, card=card)
        triggers.fire(
            state,
            GameEvent.ACTION_CARD_DISCARDED,
            Moment.AFTER,
            subject=player_id,
            ctx={"player": player_id, "card": card},
        )


def take_from_discard(state: GameState, player_id: str, card_id: str) -> None:
    """Przenosi kartę akcji ze stosu odrzuconych do ręki gracza (Reverse Engineer; mutuje).

    Raises:
        ValueError: Karty nie ma na stosie odrzuconych.
    """
    discard = state.decks.action_card_discard
    if card_id not in discard:
        raise ValueError(f"The action card {card_id} is not in the discard pile.")
    # Bierzemy ostatnie wystąpienie (wierzch stosu) - kopie tej samej karty są nierozróżnialne.
    index = len(discard) - 1 - discard[::-1].index(card_id)
    discard.pop(index)
    state.players[player_id].private.action_cards.append(card_id)


def transfer_action_card(state: GameState, from_id: str, to_id: str, card_id: str) -> None:
    """Przenosi WSKAZANĄ kartę akcji z ręki ``from_id`` do ręki ``to_id`` (mutuje).

    Raises:
        ValueError: Gracz ``from_id`` nie ma tej karty.
    """
    hand = state.players[from_id].private.action_cards
    if card_id not in hand:
        raise ValueError(f"{from_id} does not have the action card {card_id}.")
    hand.remove(card_id)
    state.players[to_id].private.action_cards.append(card_id)


def discard_specific_action_cards(
    state: GameState, player_id: str, card_ids: list[str]
) -> None:
    """Odrzuca WSKAZANE karty akcji z ręki gracza na stos odrzuconych (mutuje).

    Raises:
        ValueError: Karta spoza ręki albo duplikat (karty o tym samym id liczymy osobno).
    """
    hand = list(state.players[player_id].private.action_cards)
    for card_id in card_ids:
        if card_id not in hand:
            raise ValueError(f"You do not have the action card {card_id}.")
        hand.remove(card_id)
    state.players[player_id].private.action_cards = hand
    state.decks.action_card_discard.extend(card_ids)
    _record_discards(state, player_id, list(card_ids))


def take_random_action_card(state: GameState, from_id: str, to_id: str) -> str:
    """Przenosi LOSOWĄ kartę akcji z ręki ``from_id`` do ręki ``to_id`` (np. Spy).

    Losowanie przez seedowalny RNG silnika (Undo/Redo bezpieczne). Mutuje ``state``.

    Raises:
        ValueError: Gdy ``from_id`` nie ma kart akcji.
    """
    hand = state.players[from_id].private.action_cards
    if not hand:
        raise ValueError(f"{from_id} has no action cards.")
    card = hand.pop(next_rng(state).randrange(len(hand)))
    state.players[to_id].private.action_cards.append(card)
    return card


def seed_action_deck(state: GameState, cards: list[str]) -> None:
    """Ustawia talię kart akcji (po potasowaniu przez wołającego) i czyści odrzucone (setup)."""
    state.decks.action_card_deck = cards
    state.decks.action_card_discard = []


def rearrange_agenda_top(
    state: GameState, peeked: int, top: list[str], bottom: list[str]
) -> None:
    """Układa ``peeked`` wierzchnich agend: ``top`` na górę, ``bottom`` na spód (Politics)."""
    decks = state.decks
    rest = decks.agenda_deck[peeked:]
    decks.agenda_deck = [*top, *rest, *bottom]


def peek_agenda_top(state: GameState, player_id: str, count: int) -> list[str]:
    """Zapisuje graczowi PRYWATNY podgląd ``count`` wierzchnich agend (Insider Information).

    Wynik trafia do ``private.agenda_peek`` (projekcja widoczności czyści go innym graczom).
    Talia się nie zmienia. Mutuje ``state``.
    """
    top = list(state.decks.agenda_deck[:count])
    state.players[player_id].private.agenda_peek = top
    return top


def clear_agenda_peek(state: GameState) -> None:
    """Czyści podglądy agend wszystkich graczy (koniec fazy agendy). Mutuje ``state``."""
    for player in state.players.values():
        player.private.agenda_peek = []


def ensure_agenda_deck(state: GameState, registry: StaticDataRegistry) -> None:
    """Leniwie zasiewa talię agend (talia wybranego wariantu, potasowana).

    Wariant (``decks.agenda_variant``): ``standard`` = pełna talia aktywnych źródeł, albo
    fanowska talia wybrana w setupie. Talia powstaje raz: dopóki ``agenda_deck_seeded`` jest
    False. Potem pusta talia nie jest już zasiewana (agendy zużyte w fazie agendy trafiają
    na stos odrzuconych).
    """
    from src.core.objectives import agenda_deck_ids  # lokalnie: objectives importuje card_draw

    decks = state.decks
    if decks.agenda_deck_seeded:
        return
    cards = agenda_deck_ids(registry, decks.agenda_variant)
    next_rng(state).shuffle(cards)
    decks.agenda_deck = cards
    decks.agenda_discard = []
    decks.agenda_deck_seeded = True


def draw_agenda(state: GameState, registry: StaticDataRegistry) -> str | None:
    """Ściąga wierzchnią agendę z talii (mutuje ``state``); ``None``, gdy brak kart.

    Pusta talia tasuje stos odrzuconych (⚠️ ZAŁOŻENIE jak dla kart akcji - RULES.md 51;
    prawa leżące w grze NIE są w stosie odrzuconych, więc nie wracają do talii).
    """
    ensure_agenda_deck(state, registry)
    decks = state.decks
    if not decks.agenda_deck and decks.agenda_discard:
        reshuffled = list(decks.agenda_discard)
        next_rng(state).shuffle(reshuffled)
        decks.agenda_deck = reshuffled
        decks.agenda_discard = []
    if not decks.agenda_deck:
        return None
    return decks.agenda_deck.pop(0)


def discard_agenda(state: GameState, agenda_id: str) -> None:
    """Kładzie agendę na stosie odrzuconych (dyrektywa, „Against", odrzucona bez wyniku)."""
    state.decks.agenda_discard.append(agenda_id)
