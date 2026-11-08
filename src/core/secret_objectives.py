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


def secret_count(state: GameState, player_id: str) -> int:
    """Ile tajnych celów liczy się do limitu: ręka + zdobyte."""
    player = state.players[player_id]
    return len(player.private.secret_objectives) + len(player.scored_secrets)


def over_limit_after_draw(state: GameState, player_id: str) -> bool:
    """Czy po dobraniu 1 tajnego celu gracz przekroczy limit (i jest co dobrać)."""
    has_cards = bool(state.decks.secret_objective_deck)
    return has_cards and secret_count(state, player_id) >= SECRET_LIMIT


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
