"""Tajne cele: talia, ręka, kandydaci i zdobyte — JEDYNE miejsce zmiany (RULES.md 43.1a, C9).

Pola stanu chronione przez strażnika (``tests/test_central_points.py``):
``decks.secret_objective_deck``, ``private.secret_objectives`` (ręka),
``private.secret_candidates`` (dwa cele z setupu, z których zostaje jeden) i
``scored_secrets`` (zdobyte, jawne). Funkcje MUTUJĄ przekazany stan — wołający pracuje na klonie.

Punkt zaczepienia hooków: limit ręki, dobór dodatkowy i zwrot nadmiaru przechodzą tędy.
Importuje tylko ``game_state`` i ``dice`` (zero zależności od ``objectives``/kart strategii).
"""

from __future__ import annotations

import random

from src.core import rules_hooks
from src.core.dice import next_rng
from src.core.game_state import GameState

SECRET_LIMIT = 3  # „more than three secret objective cards" (R_objective_cards)
DRAWN = "drawn"  # wartość ``give_back``: oddaj świeżo dobraną kartę


def seed_deck(state: GameState, cards: list[str]) -> None:
    """Ustawia talię tajnych celów (po potasowaniu przez wołającego) — setup."""
    state.decks.secret_objective_deck = cards


def deal_candidates(state: GameState, player_id: str, count: int) -> None:
    """Rozdaje graczowi do ``count`` kandydatów (setup interaktywny: zostaje jeden)."""
    deck = state.decks.secret_objective_deck
    state.players[player_id].private.secret_candidates = [
        deck.pop(0) for _ in range(min(count, len(deck)))
    ]


def deal_one_to_hand(state: GameState, player_id: str) -> None:
    """Rozdaje graczowi jeden tajny cel prosto do ręki (setup bez wyboru)."""
    deck = state.decks.secret_objective_deck
    if deck:
        state.players[player_id].private.secret_objectives = [deck.pop(0)]


def choose_candidate(
    state: GameState, player_id: str, objective_id: str, rng: random.Random
) -> None:
    """Wybrany kandydat idzie do ręki, pozostali wracają do talii (tasowanie)."""
    private = state.players[player_id].private
    returned = [c for c in private.secret_candidates if c != objective_id]
    private.secret_objectives = [*private.secret_objectives, objective_id]
    private.secret_candidates = []
    deck = [*state.decks.secret_objective_deck, *returned]
    rng.shuffle(deck)
    state.decks.secret_objective_deck = deck


def score(state: GameState, player_id: str, objective_id: str) -> None:
    """Przenosi tajny cel z ręki do zdobytych (jawnych). Punkty przyznaje wołający."""
    player = state.players[player_id]
    player.private.secret_objectives = [
        o for o in player.private.secret_objectives if o != objective_id
    ]
    player.scored_secrets = [*player.scored_secrets, objective_id]


def discard_unscored(state: GameState, player_id: str, objective_id: str) -> None:
    """Odrzuca NIEZDOBYTY tajny cel z ręki: wraca do talii, która jest tasowana (mutuje).

    ⚠️ ZAŁOŻENIE: tajne cele nie mają stosu odrzuconych — jak przy zwrocie nadmiaru
    (``draw``) odrzucony cel wraca do talii i talia jest tasowana (RULES.md 50).

    Raises:
        ValueError: Cel spoza ręki (zdobyte tajne cele odrzucić nie można).
    """
    private = state.players[player_id].private
    if objective_id not in private.secret_objectives:
        raise ValueError("You can only discard an UNSCORED secret objective from your hand.")
    private.secret_objectives.remove(objective_id)
    state.decks.secret_objective_deck.append(objective_id)
    next_rng(state).shuffle(state.decks.secret_objective_deck)


def secret_count(state: GameState, player_id: str) -> int:
    """Ile tajnych celów liczy się do limitu: ręka + zdobyte."""
    player = state.players[player_id]
    return len(player.private.secret_objectives) + len(player.scored_secrets)


def secret_limit(state: GameState, player_id: str) -> int:
    """Limit tajnych celów gracza: 3 + modyfikatory (The Obsidian: +1) - punkt ``secret.limit``."""
    return rules_hooks.modify(
        rules_hooks.POINT_SECRET_OBJECTIVE_LIMIT, state, player_id, SECRET_LIMIT
    )


def over_limit_after_draw(state: GameState, player_id: str) -> bool:
    """Czy po dobraniu 1 tajnego celu gracz przekroczy limit (i jest co dobrać)."""
    has_cards = bool(state.decks.secret_objective_deck)
    return has_cards and secret_count(state, player_id) >= secret_limit(state, player_id)


def draw(state: GameState, player_id: str, give_back: str | None) -> None:
    """Dobiera tajny cel; przy nadmiarze zwraca wskazany i tasuje talię.

    Raises:
        ValueError: Nadmiar bez wskazania zwrotu, zwrot celu spoza ręki albo zdobytego.
    """
    decks = state.decks
    private = state.players[player_id].private
    if not decks.secret_objective_deck:
        return  # brak kart do dobrania - nic się nie dzieje
    must_return = over_limit_after_draw(state, player_id)
    if must_return and give_back is None:
        raise ValueError(
            "You would hold more than 3 secret objectives - choose an unscored one to return."
        )
    if give_back is not None and not must_return:
        raise ValueError("You are not over the secret objective limit - nothing to return.")
    if give_back is not None and give_back != DRAWN and give_back not in private.secret_objectives:
        raise ValueError("You can only return an UNSCORED secret objective from your hand.")
    drawn = decks.secret_objective_deck.pop(0)
    private.secret_objectives.append(drawn)
    if give_back is not None:
        target = drawn if give_back == DRAWN else give_back
        private.secret_objectives.remove(target)
        decks.secret_objective_deck.append(target)
        next_rng(state).shuffle(decks.secret_objective_deck)


def draw_to_hand(state: GameState, player_id: str) -> str | None:
    """Dobiera tajny cel do ręki BEZ zwrotu nadmiaru; zwraca id albo ``None`` (pusta talia).

    C_agendas (Search Warrant): dobrana karta jest odkryta, ZANIM gracz wybierze, którą oddać -
    nadmiar oddaje potem wołający (``excess`` + ``discard_unscored``).
    """
    deck = state.decks.secret_objective_deck
    if not deck:
        return None
    drawn = deck.pop(0)
    state.players[player_id].private.secret_objectives.append(drawn)
    return drawn


def excess(state: GameState, player_id: str) -> int:
    """Ile tajnych celów gracz ma ponad limit (do oddania z ręki)."""
    return max(0, secret_count(state, player_id) - secret_limit(state, player_id))


def transfer(state: GameState, giver_id: str, receiver_id: str, objective_id: str) -> None:
    """Przenosi NIEZDOBYTY tajny cel z ręki ``giver_id`` do ręki ``receiver_id`` (mutuje).

    Raises:
        ValueError: Gracz nie ma tego celu w ręce (zdobyte, jawne cele nie podlegają wymianie).
    """
    hand = state.players[giver_id].private.secret_objectives
    if objective_id not in hand:
        raise ValueError(f"{giver_id} does not have the unscored secret objective {objective_id}.")
    hand.remove(objective_id)
    state.players[receiver_id].private.secret_objectives.append(objective_id)


def reveal_hand(state: GameState, viewer_id: str, owner_id: str) -> list[str]:
    """Pokazuje ``viewer_id`` wszystkie tajne cele z ręki ``owner_id`` (migawka, mutuje).

    Zapis ląduje w prywatnym polu oglądającego (``private.revealed_secrets``), więc projekcja
    widoczności ukrywa go przed pozostałymi graczami.
    """
    shown = list(state.players[owner_id].private.secret_objectives)
    state.players[viewer_id].private.revealed_secrets[owner_id] = shown
    return shown


def remove_from_deck(state: GameState, objective_id: str) -> None:
    """Zdejmuje konkretny cel z talii tajnych celów (np. Neuraloop ujawnia go jako publiczny)."""
    if objective_id in state.decks.secret_objective_deck:
        state.decks.secret_objective_deck.remove(objective_id)


def return_to_deck(state: GameState, objective_id: str) -> None:
    """Wkłada cel do talii tajnych celów i tasuje ją (seedowalnie; mutuje)."""
    state.decks.secret_objective_deck.append(objective_id)
    next_rng(state).shuffle(state.decks.secret_objective_deck)


def release_scored(state: GameState, player_id: str, objective_id: str) -> None:
    """Zdobyty tajny cel przestaje być tajnym celem gracza (Classified Document Leaks).

    Punkt zostaje u gracza; cel nie liczy się już do limitu tajnych celów (C_agendas).
    """
    player = state.players[player_id]
    player.scored_secrets = [s for s in player.scored_secrets if s != objective_id]
