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
