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

from src.core import card_draw, component_action, reaction_cards, rules_hooks, triggers
from src.core.components import ActionCardDef, ComponentCategory, ComponentRef
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.timing_spec import TriggerKind


def effect_key(card_id: str) -> str:
    """Klucz komponentu karty akcji w rejestrze efektów (``kategoria:id``)."""
    return f"{ComponentCategory.ACTION_CARD.value}:{card_id}"


def card_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, card_id: str
) -> tuple[bool, list[dict[str, Any]]]:
    """Opis wyborów do formularza zagrania karty: ``(implemented, wejścia)``.

    ``implemented=False`` = karta bez efektu w silniku (zagranie = ręczne rozstrzygnięcie).

    Raises:
        ValueError: Karta nieznana albo nie ma jej w ręce gracza.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if card_id not in player.private.action_cards:
        raise ValueError(f"You do not have the action card {card_id}.")
    if not isinstance(registry.catalog.get(ComponentCategory.ACTION_CARD, card_id), ActionCardDef):
        raise ValueError(f"Unknown action card: {card_id}")
    key = effect_key(card_id)
    if rules_hooks.effect_for(key) is None:
        return False, []
    inputs_fn = rules_hooks.inputs_for(key)
    return True, (inputs_fn(state, registry, player_id) if inputs_fn is not None else [])


def _has_legal_choices(inputs: list[dict[str, Any]]) -> bool:
    """Czy każde wymagane wejście formularza ma dość opcji (inaczej: nie do rozstrzygnięcia)."""
    for item in inputs:
        options = item.get("options")
        if not isinstance(options, list):
            continue  # wejście liczbowe - zawsze do spełnienia
        need = int(item["min"]) if item.get("kind") == "multi" else 1
        if len(options) < need:
            return False
    return True


def playability(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Które karty z ręki gracza można zagrać TERAZ jako akcję (do przeciągania z ręki w UI).

    Dla każdej unikalnej karty: ``card_id``, ``playable``, ``reason`` (gdy nie), ``implemented``.
    Karta jest zagrywalna, gdy: ma okno ACTION, tura/faza/okno pozwalają na akcję komponentu
    (te same walidacje co ``play_action_card``) i - gdy silnik ją automatyzuje - istnieją
    legalne cele dla każdego wymaganego wyboru (R_action_cards: nie można zagrać karty,
    której nie da się w pełni rozstrzygnąć). Nie mutuje stanu.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    result: list[dict[str, Any]] = []
    for card_id in dict.fromkeys(player.private.action_cards):
        entry: dict[str, Any] = {
            "card_id": card_id, "playable": False, "reason": None, "implemented": False,
        }
        result.append(entry)
        spec = registry.catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, card_id))
        if spec is None or spec.trigger is not TriggerKind.ACTION:
            # Karta reakcji: zagrywalna, gdy silnik ma TERAZ otwarte pasujące okno (RULES.md 53.5).
            ok, reason, _window = reaction_cards.available(state, registry, player_id, card_id)
            implemented, inputs = card_inputs(state, registry, player_id, card_id)
            entry["implemented"] = implemented
            if not ok:
                entry["reason"] = reason
            elif implemented and not _has_legal_choices(inputs):
                entry["reason"] = "No legal target for this card right now."
            else:
                entry["playable"] = True
            continue
        try:
            component_action.play_component_action(
                state, player_id, card_id, fire_after=False
            )
        except ValueError as exc:
            entry["reason"] = str(exc)
            continue
        implemented, inputs = card_inputs(state, registry, player_id, card_id)
        entry["implemented"] = implemented
        if implemented and not _has_legal_choices(inputs):
            entry["reason"] = "No legal target for this card right now."
            continue
        entry["playable"] = True
    return result


def _play_reaction_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any],
) -> tuple[GameState, bool]:
    """Zagranie karty REAKCJI (when/after/before/at start/at end) w otwartym oknie.

    To NIE jest akcja tury: nie zużywa akcji i może ją zagrać każdy gracz, któremu pasuje okno
    (``reaction_cards.available``). Efekt dostaje okno w ``params["__window"]``. Praca na klonie:
    błąd = zero zmian.
    """
    ok, reason, window = reaction_cards.available(state, registry, player_id, card_id)
    if not ok or window is None:
        raise ValueError(reason or "There is no open window for this card right now.")
    new_state = state.clone()
    triggers.fire(
        new_state, GameEvent.ACTION_CARD_PLAYED, Moment.WHEN, subject=player_id,
        ctx={"player": player_id, "card": card_id},
    )
    effect = rules_hooks.effect_for(effect_key(card_id))
    if effect is not None:
        with_window = {**params, reaction_cards.WINDOW_KEY: window.as_dict()}
        effect(new_state, registry, player_id, with_window)
    card_draw.discard_specific_action_cards(new_state, player_id, [card_id])
    return new_state, effect is not None


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
        return _play_reaction_card(state, registry, player_id, card_id, params or {})

    new_state = component_action.play_component_action(
        state, player_id, card_id, fire_after=False
    )
    triggers.fire(
        new_state, GameEvent.ACTION_CARD_PLAYED, Moment.WHEN, subject=player_id,
        ctx={"player": player_id, "card": card_id},
    )
    effect = rules_hooks.effect_for(effect_key(card_id))
    if effect is not None:
        effect(new_state, registry, player_id, params or {})
    card_draw.discard_specific_action_cards(new_state, player_id, [card_id])
    triggers.fire(
        new_state, GameEvent.COMPONENT_ACTION, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "component": card_id},
    )
    return new_state, effect is not None
