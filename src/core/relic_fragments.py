"""Fragmenty reliktów leżące w strefie gracza — JEDYNE miejsce zmiany (RULES.md 43.1a, C9).

Pole chronione przez strażnika (``tests/test_central_points.py``): ``relic_fragments``.
Funkcje MUTUJĄ przekazany stan — wołający pracuje na klonie. Punkt zaczepienia hooków:
zdobycie i przekazanie fragmentu (np. frakcje liczące fragmenty jako dowolny typ).
"""

from __future__ import annotations

from src.core.game_state import GameState


def gain(state: GameState, player_id: str, card_id: str) -> None:
    """Kładzie fragment (kartę eksploracji) odkryty w strefie gracza."""
    state.players[player_id].relic_fragments.append(card_id)


def transfer(state: GameState, giver_id: str, receiver_id: str, card_id: str) -> None:
    """Przenosi fragment ze strefy ``giver_id`` do strefy ``receiver_id`` (transakcja).

    Raises:
        ValueError: Gdy dawca nie ma takiego fragmentu.
    """
    giver_zone = state.players[giver_id].relic_fragments
    if card_id not in giver_zone:
        raise ValueError(f"Player {giver_id} does not have the relic fragment '{card_id}'.")
    giver_zone.remove(card_id)
    state.players[receiver_id].relic_fragments.append(card_id)
