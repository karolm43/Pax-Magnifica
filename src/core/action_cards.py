"""Zagrywanie kart akcji w fazie akcji (RULES.md 53): ręka -> walidacja -> efekt -> odrzucone.

Zakres: karty z oknem ``ACTION`` (zagrywane JAKO akcja komponentu, R_component_action). Karty
reakcji (when/after/before/instead) wymagają modelu STOP i predykatów zagrywalności
(RULES.md 43.4) - tu odrzucane z jasnym komunikatem. Funkcja jest CZYSTA (``state -> state``).

Efekt karty to funkcja zarejestrowana przez ``rules_hooks.register_effect("action_cards:<id>")``
(pakiet ``core/hooks/action_cards.py``). Karta BEZ efektu nie blokuje gry (RULES.md 43.1 pkt 7,
43.3): idzie na stos odrzuconych, liczy się jako akcja, a wynik zwraca ``implemented=False`` -
operator rozstrzyga skutek ręcznie (God-Mode).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import card_draw, component_action, rules_hooks
from src.core.components import ActionCardDef, ComponentCategory, ComponentRef
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.timing_spec import TriggerKind


def effect_key(card_id: str) -> str:
    """Klucz komponentu karty akcji w rejestrze efektów (``kategoria:id``)."""
    return f"{ComponentCategory.ACTION_CARD.value}:{card_id}"


def play_action_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    actor_id: str | None = None,
) -> tuple[GameState, bool]:
    """Aktywny gracz zagrywa kartę akcji z oknem ``ACTION`` (jego akcja w turze).

    Kolejność: walidacje (czyja tura, faza, okno, jedna akcja - przez ``component_action``;
    karta w ręce; okno karty) -> efekt na klonie -> odrzucenie karty. Błąd na dowolnym etapie
    = ``ValueError`` i ZERO zmian (praca na klonie).

    Returns:
        ``(nowy stan, implemented)``; ``implemented=False`` = karta nie ma jeszcze efektu w silniku
        (zagrana i odrzucona, skutek rozstrzyga operator).

    Raises:
        ValueError: Karta nieznana / spoza ręki / nie ma okna ACTION, nie ta tura, złe parametry.
    """
    if actor_id is not None and actor_id != player_id:
        raise ValueError(f"{actor_id} cannot play a card for {player_id}.")
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if card_id not in player.private.action_cards:
        raise ValueError(f"You do not have the action card {card_id}.")
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
    if not isinstance(card, ActionCardDef):
        raise ValueError(f"Unknown action card: {card_id}")
    spec = registry.catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, card_id))
    if spec is None or spec.trigger is not TriggerKind.ACTION:
        raise ValueError(
            f"{card.name or card_id} is a timing/reaction card - it cannot be played as an "
            "action (reactions need the STOP flow, RULES.md 43.4)."
        )

    new_state = component_action.play_component_action(state, player_id, card_id)
    effect = rules_hooks.effect_for(effect_key(card_id))
    if effect is not None:
        effect(new_state, registry, player_id, params or {})
    card_draw.discard_specific_action_cards(new_state, player_id, [card_id])
    return new_state, effect is not None
