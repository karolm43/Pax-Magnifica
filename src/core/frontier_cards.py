"""Karty frontier leżące u gracza: Enigmatic Device (zakładka Action cards na ręce).

Karta z eksploracji frontier trafia do ``PlayerState.frontier_cards`` (jawnie, jak relikt) i jest
zagrywana jak karta akcji: przeciągnięciem z ręki, jako AKCJA KOMPONENTU tury (RULES.md 31.8,
``component_action``). Efekt i formularz rejestruje ``core/hooks/frontier_cards.py`` pod kluczem
``explores:<id>``. Funkcje CZYSTE (``state -> state``); zasady jak w ``relic_cards``.

Źródło reguł: ``docs/rules_tirules/C_exploration_cards.md`` (Enigmatic Device).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import component_action, exploration, offer_inputs, rules_hooks
from src.core.components import ComponentCategory, ExplorationDef
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry


def effect_key(card_id: str) -> str:
    """Klucz karty frontier w rejestrze efektów (``explores:<id>``)."""
    return f"{ComponentCategory.EXPLORATION.value}:{card_id}"


def card_def(registry: StaticDataRegistry, card_id: str) -> ExplorationDef:
    """Definicja karty frontier z katalogu (``ValueError``, gdy nieznana)."""
    card = registry.catalog.get(ComponentCategory.EXPLORATION, card_id)
    if not isinstance(card, ExplorationDef):
        raise ValueError(f"Unknown frontier card: {card_id}")
    return card


def purge_card(state: GameState, player_id: str, card_id: str) -> None:
    """Purge karty frontier gracza: znika z jego strefy i NIE wraca do talii (mutuje ``state``)."""
    player = state.players[player_id]
    if card_id not in player.frontier_cards:
        raise ValueError("You do not have that frontier card in your play area.")
    cards = list(player.frontier_cards)
    cards.remove(card_id)
    player.frontier_cards = cards
    exploration.purge_cards(state, [card_id])


def block_reason(
    state: GameState, registry: StaticDataRegistry, player_id: str, card_id: str
) -> str | None:
    """Powód, dla którego ACTION karty nie można teraz zagrać (``None`` = można)."""
    from src.core.hooks import frontier_cards as hooks  # lokalnie: hooki importują ten moduł

    if card_id in hooks.ENIGMATIC_DEVICE_IDS and not hooks.can_pay(state, registry, player_id):
        return (
            "Enigmatic Device needs 6 resources available - you do not have enough ready "
            "planets or trade goods."
        )
    return None


def form(
    state: GameState, registry: StaticDataRegistry, player_id: str, card_id: str
) -> dict[str, Any]:
    """Opis karty i formularza jej ACTION (kształt zgodny z ``relic_actions.form``)."""
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    card = card_def(registry, card_id)
    if card_id not in player.frontier_cards:
        raise ValueError(f"You do not have {card.name} in your play area.")
    key = effect_key(card_id)
    inputs_fn = rules_hooks.inputs_for(key)
    inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    return {
        "relic_id": card_id,
        "name": card.name or card_id,
        "text": " ".join(card.texts.values()),
        "kind": "action",
        "implemented": rules_hooks.effect_for(key) is not None,
        "inputs": inputs,
        "exhausted": False,
        "summary": None,
    }


def playability(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Karty frontier gracza i czy ich ACTION można zagrać TERAZ (nie mutuje stanu)."""
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    rows: list[dict[str, Any]] = []
    for card_id in dict.fromkeys(player.frontier_cards):
        info = form(state, registry, player_id, card_id)
        row: dict[str, Any] = {
            "relic_id": card_id,
            "kind": "action",
            "playable": False,
            "reason": None,
            "implemented": info["implemented"],
            "exhausted": False,
        }
        rows.append(row)
        try:
            component_action.play_component_action(
                state, player_id, card_id, fire_after=False, run_effect=False
            )
        except ValueError as exc:
            row["reason"] = str(exc)
            continue
        reason = block_reason(state, registry, player_id, card_id)
        if reason is not None:
            row["reason"] = reason
        elif info["implemented"] and not offer_inputs.has_legal_answer(info["inputs"]):
            row["reason"] = "No legal choice for this card right now."
        else:
            row["playable"] = True
    return rows


def run_action_effect(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any] | None,
) -> bool:
    """Wykonuje efekt ACTION karty frontier na ``state`` (KLON wołającego), jeśli zakodowany.

    Returns:
        True, gdy efekt zastosowano; False, gdy to nie karta frontier gracza albo brak efektu.
    """
    player = state.players[player_id]
    if card_id not in player.frontier_cards:
        return False
    key = effect_key(card_id)
    effect = rules_hooks.effect_for(key)
    if effect is None:
        return False
    inputs_fn = rules_hooks.inputs_for(key)
    inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    effect(state, registry, player_id, offer_inputs.validate_params(inputs, params or {}))
    return True


def play_frontier_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    actor_id: str | None = None,
) -> tuple[GameState, bool]:
    """Aktywny gracz zagrywa ACTION karty frontier (jego akcja w turze) - ``(stan, implemented)``.

    Raises:
        ValueError: Karta nie jest gracza, nie ta tura/faza, złe parametry, za mało zasobów.
    """
    if actor_id is not None and actor_id != player_id:
        raise ValueError(f"{actor_id} cannot play a card for {player_id}.")
    info = form(state, registry, player_id, card_id)
    reason = block_reason(state, registry, player_id, card_id)
    if reason is not None:
        raise ValueError(reason)
    new_state = component_action.play_component_action(state, player_id, card_id, params=params)
    return new_state, bool(info["implemented"])
