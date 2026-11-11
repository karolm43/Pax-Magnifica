"""Karta reakcji Sabotage (sabo1..sabo4): anulowanie zagrania karty akcji czekającego w held_play.

Sabotage: „When another player plays an action card other than 'Sabotage': Cancel that action card."
Okno istnieje tylko, gdy cudza karta (inna niż Sabotage) czeka w ``GameState.held_play``
(``core/card_hold.py``, RULES.md 53.6). Efekt: karta czekająca idzie na odrzucone, jej efekt się
nie wykonuje, a akcja zagrywającego pozostaje zużyta. Samą Sabotage odrzuca zwykła ścieżka
``action_cards`` (jak każdą zagraną kartę reakcji).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import card_hold
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.reaction_cards import OTHER, OpenWindow, declare_reaction, window_provider
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect


@window_provider
def card_waiting(state: GameState) -> list[OpenWindow]:
    """Okno „gracz zagrywa kartę akcji": cudza karta (nie Sabotage) czeka w ``held_play``."""
    held = state.held_play
    if held is None or card_hold.is_sabotage(held.card_id):
        return []
    return [
        OpenWindow(
            GameEvent.ACTION_CARD_PLAYED, Moment.WHEN,
            {"player": held.player_id, "card": held.card_id},
        )
    ]


def _can_respond(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    """Sabotage zagra tylko uprawniony (z kartą w ręce przy zagraniu), który nie spasował."""
    held = state.held_play
    return held is not None and card_hold.can_respond(held, player_id)


declare_reaction(
    *card_hold.SABOTAGE_IDS,
    points=((GameEvent.ACTION_CARD_PLAYED, Moment.WHEN),),
    subject=OTHER,
    condition=_can_respond,
)


def _cancel(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """Anuluje czekającą kartę (``card_hold.cancel_in_place``)."""
    card_hold.cancel_in_place(state)


for _card in card_hold.SABOTAGE_IDS:
    register_effect(f"action_cards:{_card}")(_cancel)
