"""Promissory notes: ręka i strefa gry — JEDYNE miejsce zmiany (RULES.md 43.1a, C9).

Pola chronione przez strażnika (``tests/test_central_points.py``): ``private.promissory_notes``
(ręka, tajna) i ``promissory_notes_in_play`` (strefa gry, jawna). Funkcje MUTUJĄ przekazany
stan — wołający pracuje na klonie. Walidacja legalności transakcji zostaje w ``transaction.py``;
tu tylko sama zmiana stanu (punkt zaczepienia hooków: zagranie, przekazanie, zwrot notki).
"""

from __future__ import annotations

from src.core import triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState


def set_hand(state: GameState, player_id: str, notes: list[str]) -> None:
    """Ustawia rękę promissory notes gracza (setup: wspólne + frakcyjna)."""
    state.players[player_id].private.promissory_notes = list(notes)


def transfer(state: GameState, giver_id: str, receiver_id: str, note_id: str) -> None:
    """Przenosi notkę z ręki ``giver_id`` do ręki ``receiver_id`` (transakcja).

    Raises:
        ValueError: Gdy dawca nie trzyma notki w ręce.
    """
    giver_hand = state.players[giver_id].private.promissory_notes
    if note_id not in giver_hand:
        raise ValueError(f"Player {giver_id} does not hold the promissory note '{note_id}'.")
    giver_hand.remove(note_id)
    state.players[receiver_id].private.promissory_notes.append(note_id)
    triggers.fire(
        state, GameEvent.COMPONENT_GAINED, Moment.WHEN, subject=receiver_id,
        ctx={"player": receiver_id, "component": f"promissory_notes:{note_id}"},
    )
    # „When you receive this card … place it faceup in your play area" (RULES.md 61.2).
    from src.core import promissory_play  # lokalnie: promissory_play importuje ten moduł

    promissory_play.on_received(state, receiver_id, note_id)


def place_in_play(state: GameState, holder_id: str, note_id: str) -> None:
    """Notka z ręki ``holder_id`` ląduje odkryta w jego strefie gry (Alliance, SftT…)."""
    hand = state.players[holder_id].private.promissory_notes
    if note_id in hand:
        hand.remove(note_id)
    player = state.players[holder_id]
    if note_id not in player.promissory_notes_in_play:
        player.promissory_notes_in_play = [*player.promissory_notes_in_play, note_id]


def return_from_hand(state: GameState, holder_id: str, owner_id: str, note_id: str) -> None:
    """Zagrana notka wraca z ręki gracza do ręki właściciela (R_promissory_notes)."""
    hand = state.players[holder_id].private.promissory_notes
    if note_id not in hand:
        raise ValueError(f"Player {holder_id} does not hold the promissory note '{note_id}'.")
    hand.remove(note_id)
    state.players[owner_id].private.promissory_notes.append(note_id)


def return_from_play(state: GameState, holder_id: str, owner_id: str, note_id: str) -> None:
    """Notka ze strefy gry gracza wraca do ręki właściciela (warunek z tekstu notki)."""
    player = state.players[holder_id]
    if note_id not in player.promissory_notes_in_play:
        raise ValueError(f"Player {holder_id} has no '{note_id}' in their play area.")
    player.promissory_notes_in_play = [n for n in player.promissory_notes_in_play if n != note_id]
    state.players[owner_id].private.promissory_notes.append(note_id)


def discard_from_hand(state: GameState, holder_id: str, note_id: str) -> None:
    """Notka z ręki gracza znika z gry (purge)."""
    hand = state.players[holder_id].private.promissory_notes
    if note_id in hand:
        hand.remove(note_id)


def remove_from_play(state: GameState, holder_id: str, note_id: str) -> None:
    """Notka ze strefy gry gracza wraca do pudełka (eliminacja właściciela, R_elimination)."""
    player = state.players[holder_id]
    player.promissory_notes_in_play = [n for n in player.promissory_notes_in_play if n != note_id]
