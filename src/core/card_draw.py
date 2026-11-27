"""Dobieranie kart z talii wspólnych (karty akcji, agendy) — czyste operacje na klonie.

Wspólne dla eksploracji, kart strategii (Politics) i fazy statusu. Pusta talia dobierana
tasuje się z własnego stosu odrzuconych (seedowalny RNG stanu — ``core/dice.py``).
"""

from __future__ import annotations

from collections import Counter

from src.core import triggers
from src.core.dice import next_rng
from src.core.game_events import GameEvent, Moment
from src.core.game_state import ActionCardReveal, ActionDiscardTrace, GameState
from src.core.registry import StaticDataRegistry


def reshuffle_action_deck_if_empty(state: GameState) -> None:
    """Pusta talia kart akcji = stos odrzuconych od razu tasowany w nową talię (mutuje ``state``).

    C_relics (The Codex): „The action card discard is shuffled to form a new action card deck as
    soon as the action card deck has zero cards in it" - nie dopiero przy następnym dobraniu.
    """
    decks = state.decks
    if not decks.action_card_deck and decks.action_card_discard:
        reshuffled = list(decks.action_card_discard)
        next_rng(state).shuffle(reshuffled)
        decks.action_card_deck = reshuffled
        decks.action_card_discard = []


def draw_action_card(state: GameState, player_id: str) -> bool:
    """Dobiera kartę akcji do ręki gracza (mutuje ``state``); False, gdy talie puste."""
    return draw_action_cards(state, player_id, 1) == 1


def draw_action_cards(state: GameState, player_id: str, count: int) -> int:
    """Draws ``count`` action cards as ONE draw (mutates ``state``); returns how many were drawn.

    One draw fires one ``ACTION_CARDS_DRAWN`` WHEN/AFTER pair with ``amount`` = the cards drawn:
    "when you draw 1 or more action cards" happens once per draw (Scheming, RULES.md 62.22).
    """
    if count <= 0:
        return 0
    reshuffle_action_deck_if_empty(state)
    if not state.decks.action_card_deck:
        return 0
    triggers.fire(
        state, GameEvent.ACTION_CARDS_DRAWN, Moment.WHEN, subject=player_id,
        ctx={"player": player_id, "amount": count},
    )
    drawn = sum(1 for _ in range(count) if draw_without_event(state, player_id))
    if drawn:
        triggers.fire(
            state, GameEvent.ACTION_CARDS_DRAWN, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "amount": drawn},
        )
    return drawn


def draw_without_event(state: GameState, player_id: str) -> bool:
    """Moves the top action card into the hand WITHOUT announcing a draw (mutates ``state``): the
    extra card of an ongoing draw (Scheming's "1 additional" - RULES.md 62.22). False = no cards."""
    decks = state.decks
    reshuffle_action_deck_if_empty(state)
    if not decks.action_card_deck:
        return False
    state.players[player_id].private.action_cards.append(decks.action_card_deck.pop(0))
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


def discard_chosen_action_cards(state: GameState, player_id: str, card_ids: list[str]) -> None:
    """Odrzuca WSKAZANE karty akcji z ręki gracza (mutuje; koszt celów typu „odrzuć karty”).

    Raises:
        ValueError: Karty nie ma w ręce gracza (albo wskazano ją dwa razy).
    """
    hand = list(state.players[player_id].private.action_cards)
    for card_id in card_ids:
        if card_id not in hand:
            raise ValueError(f"You do not have the action card '{card_id}' in hand.")
        hand.remove(card_id)
    state.players[player_id].private.action_cards = hand
    state.decks.action_card_discard.extend(card_ids)
    _record_discards(state, player_id, list(card_ids))


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


def take_from_hand_to_table(state: GameState, player_id: str, card_id: str) -> None:
    """Zdejmuje kartę akcji z ręki na stół (``held_play``; mutuje); ``ValueError`` bez karty."""
    hand = state.players[player_id].private.action_cards
    if card_id not in hand:
        raise ValueError(f"You do not have the action card {card_id}.")
    hand.remove(card_id)


def return_table_card_to_hand(state: GameState, player_id: str, card_id: str) -> None:
    """Odkłada kartę ze stołu (``held_play``) do ręki, by przeszła zwykłą ścieżką (mutuje)."""
    state.players[player_id].private.action_cards.append(card_id)


def reveal_action_cards(state: GameState, player_id: str, cards: list[str]) -> GameState:
    """The player shows everyone the chosen action cards from their hand (pure; new state).

    R_action_cards/notes/3: "A player may choose to reveal any or all of the action cards in their
    hand." Any time, any phase; the cards stay in the hand. ``GameState.action_card_reveal``
    makes the cards public (Activity feed).

    Raises:
        ValueError: Unknown player, no cards chosen, or a card that is not in the hand.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if not cards:
        raise ValueError("Choose at least one action card to reveal.")
    missing = Counter(cards) - Counter(player.private.action_cards)
    if missing:
        raise ValueError(f"You can only reveal action cards from your hand ({sorted(missing)}).")
    new_state = state.clone()
    previous = state.action_card_reveal
    new_state.action_card_reveal = ActionCardReveal(
        seq=(previous.seq if previous is not None else 0) + 1, player=player_id, cards=list(cards)
    )
    return new_state


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


def place_on_legendary_card(state: GameState, planet_id: str, card_id: str) -> None:
    """Przenosi kartę akcji ze stosu odrzuconych NA kartę zdolności legendarnej (jawnie; mutuje).

    Dok 'N Pic's Salvage Yard (Garbozia): karta leży na karcie zdolności, nie liczy się do limitu
    ręki i zostaje przy niej, gdy karta zmienia kontrolera (``GameState.legendary_cards``).

    Raises:
        ValueError: Karty nie ma na stosie odrzuconych.
    """
    discard = state.decks.action_card_discard
    if card_id not in discard:
        raise ValueError(f"The action card {card_id} is not in the discard pile.")
    index = len(discard) - 1 - discard[::-1].index(card_id)
    discard.pop(index)
    state.legendary_cards[planet_id] = [*state.legendary_cards.get(planet_id, []), card_id]


SALVAGE_YARD_PLANET = "garbozia"


def salvage_yard_cards(state: GameState, player_id: str) -> list[str]:
    """Action cards the player may play from Dok 'N Pic's Salvage Yard (they control Garbozia).

    C_legendary_planets: the card need not be readied (an exhausted card still works) and a new
    controller of Garbozia may play the cards that stayed on it.
    """
    player = state.players.get(player_id)
    if player is None or SALVAGE_YARD_PLANET not in player.controlled_planets:
        return []
    return list(state.legendary_cards.get(SALVAGE_YARD_PLANET, []))


def borrow_salvage_yard_card(state: GameState, player_id: str, card_id: str) -> None:
    """Moves ``card_id`` from the Salvage Yard into the hand so it is played "as if in hand".

    The card is PURGED (not discarded) when it leaves the hand again
    (``discard_specific_action_cards``). Callers work on a clone (mutates ``state``).

    Raises:
        ValueError: The player does not control the Salvage Yard or the card is not on it.
    """
    if card_id not in salvage_yard_cards(state, player_id):
        raise ValueError(f"The action card {card_id} is not on your Dok 'N Pic's Salvage Yard.")
    on_card = list(state.legendary_cards[SALVAGE_YARD_PLANET])
    on_card.remove(card_id)
    if on_card:
        state.legendary_cards[SALVAGE_YARD_PLANET] = on_card
    else:
        del state.legendary_cards[SALVAGE_YARD_PLANET]
    state.players[player_id].private.action_cards.append(card_id)
    state.salvage_yard_borrowed[player_id] = [
        *state.salvage_yard_borrowed.get(player_id, []), card_id
    ]


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
    borrowed = list(state.salvage_yard_borrowed.get(player_id, []))
    discarded: list[str] = []
    for card_id in card_ids:
        if card_id in borrowed:  # played from the Salvage Yard: purged, not discarded
            borrowed.remove(card_id)
        else:
            discarded.append(card_id)
    if borrowed:
        state.salvage_yard_borrowed[player_id] = borrowed
    else:
        state.salvage_yard_borrowed.pop(player_id, None)
    state.decks.action_card_discard.extend(discarded)
    _record_discards(state, player_id, discarded)


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


def discard_random_action_cards(state: GameState, player_id: str, count: int) -> list[str]:
    """Discards ``count`` RANDOM action cards from the hand (all of them if fewer; mutates).

    Seedable engine RNG (Undo/Redo safe) - Kyver, Blade and Key (RULES.md 62.22).
    """
    hand = state.players[player_id].private.action_cards
    rng = next_rng(state)
    chosen: list[str] = []
    pool = list(hand)
    for _ in range(min(count, len(pool))):
        chosen.append(pool.pop(rng.randrange(len(pool))))
    if chosen:
        discard_specific_action_cards(state, player_id, chosen)
    return chosen


def seed_action_deck(state: GameState, cards: list[str]) -> None:
    """Ustawia talię kart akcji (po potasowaniu przez wołającego) i czyści odrzucone (setup)."""
    state.decks.action_card_deck = cards
    state.decks.action_card_discard = []


def rearrange_agenda_top(
    state: GameState,
    peeked: int,
    top: list[str],
    bottom: list[str],
    owner_id: str | None = None,
) -> None:
    """Układa ``peeked`` wierzchnich agend: ``top`` na górę, ``bottom`` na spód (Politics).

    Wiedza o talii (RULES.md 53.5.a1): inni gracze tracą pewność (nie wiedzą, gdzie trafiły
    karty), ``owner_id`` zna nową górę (``top`` + to, co znał dalej) i nowy spód.
    """
    decks = state.decks
    rest = decks.agenda_deck[peeked:]
    decks.agenda_deck = [*top, *rest, *bottom]
    for pid, player in state.players.items():
        private = player.private
        if pid == owner_id:
            private.agenda_peek = [*top, *private.agenda_peek[peeked:]]
            private.agenda_peek_bottom = [*private.agenda_peek_bottom, *bottom]
        else:
            private.agenda_peek = []
            private.agenda_peek_bottom = []


def peek_agenda_top(state: GameState, player_id: str, count: int) -> list[str]:
    """Zapisuje graczowi PRYWATNY podgląd ``count`` wierzchnich agend (Insider Information).

    Wynik trafia do ``private.agenda_peek`` (projekcja widoczności czyści go innym graczom);
    dłuższa wiedza z wcześniejszego podglądu zostaje (RULES.md 53.5.a1). Talia się nie zmienia.
    Mutuje ``state``.
    """
    top = list(state.decks.agenda_deck[:count])
    private = state.players[player_id].private
    if private.agenda_peek[: len(top)] != top:
        private.agenda_peek = []  # wiedza nieaktualna - zastępuje ją świeży podgląd
    if len(private.agenda_peek) < len(top):
        private.agenda_peek = top
    return top


def _forget_drawn_agenda(state: GameState, card: str) -> None:
    """Agenda zdjęta z wierzchu talii wypada z wiedzy graczy (RULES.md 53.5.a1).

    Znana góra przesuwa się o kartę; jeśli dobrana karta NIE była pierwszą znaną, wiedza o
    górze była nieaktualna - znika. Karta znana ze spodu (krótka talia) też wypada.
    """
    for player in state.players.values():
        private = player.private
        if private.agenda_peek:
            private.agenda_peek = (
                private.agenda_peek[1:] if private.agenda_peek[0] == card else []
            )
        if card in private.agenda_peek_bottom:
            private.agenda_peek_bottom = [c for c in private.agenda_peek_bottom if c != card]


def _forget_agenda_deck(state: GameState) -> None:
    """Talia agend przetasowana: nikt nie zna już jej kolejności."""
    for player in state.players.values():
        player.private.agenda_peek = []
        player.private.agenda_peek_bottom = []


def ensure_agenda_deck(state: GameState, registry: StaticDataRegistry) -> None:
    """Leniwie zasiewa talię agend (talia wybranego wariantu, potasowana).

    Skład talii zależy od modułów wariantów gry (``core/variants``, np. talia Absol):
    bez modułu = pełna talia aktywnych źródeł. Talia powstaje raz: dopóki
    ``agenda_deck_seeded`` jest False. Potem pusta talia nie jest już zasiewana (agendy
    zużyte w fazie agendy trafiają na stos odrzuconych).
    """
    from src.core.objectives import deck_card_ids  # lokalnie: objectives importuje card_draw

    decks = state.decks
    if decks.agenda_deck_seeded:
        return
    cards = deck_card_ids(registry, "agenda", state)
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
        _forget_agenda_deck(state)
    if not decks.agenda_deck:
        return None
    card = decks.agenda_deck.pop(0)
    _forget_drawn_agenda(state, card)
    return card


def discard_agenda(state: GameState, agenda_id: str) -> None:
    """Kładzie agendę na stosie odrzuconych (dyrektywa, „Against", odrzucona bez wyniku)."""
    state.decks.agenda_discard.append(agenda_id)


def take_agenda_from_discard(state: GameState, agenda_id: str) -> bool:
    """Zdejmuje agendę ze stosu odrzuconych (wraca do gry jako prawo); False, gdy jej tam nie ma."""
    if agenda_id not in state.decks.agenda_discard:
        return False
    state.decks.agenda_discard.remove(agenda_id)
    return True
