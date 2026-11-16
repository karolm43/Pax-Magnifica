"""Akcje reliktów („ACTION:”) - formularz i wykonanie efektu (RULES.md 59).

Relikt z nagłówkiem ``ACTION`` w tekście karty jest zagrywany jako akcja komponentu
(``component_action``), ale - w odróżnieniu od karty akcji - NIE schodzi z ręki: zostaje przed
graczem, wyczerpuje się albo jest purge'owany przez własny efekt. Efekty rejestrują moduły
``core/hooks/relics_*.py`` przez ``rules_hooks.register_effect("relics:<id>")``.

Moduł jest niezależny od ``component_action`` (ten go woła), żeby nie tworzyć cyklu importów.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from src.core import offer_inputs, rules_hooks
from src.core.components import ComponentCategory, RelicDef
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

# Nagłówek akcji komponentu na początku akapitu (tekst reliktu bywa wielolinijkowy, z „> ”).
_ACTION_HEADER = re.compile(r"(?:^|\n)[>\s]*ACTION:", re.IGNORECASE)


# Powód, dla którego ACTION reliktu nie da się TERAZ użyć (np. wyczerpany, brak celu) albo None.
BlockerFn = Callable[[GameState, StaticDataRegistry, str], str | None]
_BLOCKERS: dict[str, BlockerFn] = {}


def blocker(relic_id: str) -> Callable[[BlockerFn], BlockerFn]:
    """Rejestruje warunek zagrywalności ACTION reliktu (zwraca powód odmowy albo ``None``).

    Ten sam warunek widzi UI (przeciąganie z zakładki Relics) i silnik przy zagraniu.
    """

    def decorate(fn: BlockerFn) -> BlockerFn:
        if relic_id in _BLOCKERS:
            raise ValueError(f"Blocker already registered for {relic_id}.")
        _BLOCKERS[relic_id] = fn
        return fn

    return decorate


def block_reason(
    state: GameState, registry: StaticDataRegistry, player_id: str, relic_id: str
) -> str | None:
    """Powód, dla którego relikt nie może teraz wykonać swojej ACTION (``None`` = może)."""
    rules_hooks.effect_for(effect_key(relic_id))  # wymusza załadowanie pakietu hooków
    fn = _BLOCKERS.get(relic_id)
    return fn(state, registry, player_id) if fn is not None else None


def effect_key(relic_id: str) -> str:
    """Klucz komponentu reliktu w rejestrze efektów (``relics:<id>``)."""
    return f"{ComponentCategory.RELIC.value}:{relic_id}"


def relic_def(registry: StaticDataRegistry, relic_id: str) -> RelicDef:
    """Definicja reliktu z katalogu.

    Raises:
        ValueError: Nieznany relikt.
    """
    card = registry.catalog.get(ComponentCategory.RELIC, relic_id)
    if not isinstance(card, RelicDef):
        raise ValueError(f"Unknown relic: {relic_id}")
    return card


def relic_text(registry: StaticDataRegistry, relic_id: str) -> str:
    """Pełny tekst karty reliktu (z assetów)."""
    return " ".join(relic_def(registry, relic_id).texts.values())


def is_action_relic(registry: StaticDataRegistry, relic_id: str) -> bool:
    """Czy relikt ma zdolność „ACTION:” (zagrywaną jako akcja komponentu)."""
    card = registry.catalog.get(ComponentCategory.RELIC, relic_id)
    if not isinstance(card, RelicDef):
        return False
    return any(_ACTION_HEADER.search(text) for text in card.texts.values())


def form(
    state: GameState, registry: StaticDataRegistry, player_id: str, relic_id: str
) -> dict[str, Any]:
    """Opis reliktu dla UI: rodzaj, czy silnik go automatyzuje i wejścia formularza ACTION.

    ``kind``: ``action`` (zagrywany jako akcja) albo ``passive`` (działa sam / reaguje na
    zdarzenia). ``implemented`` dla ACTION = jest zakodowany efekt; dla pasywnego = relikt ma
    hook albo jest oznaczony jako zrealizowany z danych (``rules_hooks.covered_components``).

    Raises:
        ValueError: Nieznany relikt albo gracz go nie posiada.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    card = relic_def(registry, relic_id)
    if relic_id not in player.relics:
        raise ValueError(f"You do not have the relic {card.name}.")
    key = effect_key(relic_id)
    action = is_action_relic(registry, relic_id)
    inputs: list[dict[str, Any]] = []
    if action and rules_hooks.effect_for(key) is not None:
        inputs_fn = rules_hooks.inputs_for(key)
        # Tekst reliktu pokazuje okno raz - bez kopii w podpowiedzi każdego pola.
        inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    implemented = (
        rules_hooks.effect_for(key) is not None
        if action
        else key in rules_hooks.covered_components()
    )
    preview = rules_hooks.preview_for(key)
    return {
        "relic_id": relic_id,
        "name": card.name or relic_id,
        "text": " ".join(card.texts.values()),
        "kind": "action" if action else "passive",
        "implemented": implemented,
        "inputs": inputs,
        "exhausted": relic_id in player.exhausted_relics,
        "summary": preview(state, registry, player_id) if preview is not None else None,
    }


def run_action_effect(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    relic_id: str,
    params: dict[str, Any] | None,
) -> bool:
    """Wykonuje efekt „ACTION:” reliktu na ``state`` (KLON wołającego), jeśli jest zakodowany.

    Returns:
        True, gdy silnik zastosował efekt; False, gdy ``relic_id`` nie jest reliktem gracza z
        akcją albo efekt nie jest zakodowany (akcja zostaje tylko zapisana - skutek rozstrzyga
        operator).

    Raises:
        ValueError: Odpowiedź gracza spoza legalnych opcji albo efekt odrzucił stan gry.
    """
    player = state.players[player_id]
    if relic_id not in player.relics or not is_action_relic(registry, relic_id):
        return False
    key = effect_key(relic_id)
    effect = rules_hooks.effect_for(key)
    if effect is None:
        return False
    reason = block_reason(state, registry, player_id, relic_id)
    if reason is not None:
        raise ValueError(reason)
    inputs_fn = rules_hooks.inputs_for(key)
    inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    effect(state, registry, player_id, offer_inputs.validate_params(inputs, params or {}))
    return True
