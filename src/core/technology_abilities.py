"""Użycie zdolności technologii przez gracza: formularz, akcja komponentu i zdolności poza akcją.

RULES.md 57. Gracz zawsze decyduje sam: silnik opisuje wybory (``offer_inputs``) i waliduje
odpowiedź względem legalnych opcji. Dwa rodzaje użycia:

* ``action`` - „ACTION:” technologii, wykonywane jako akcja komponentu (``component_action``);
* ``free`` - zdolność bez akcji (np. Psychoarchaeology), używana w fazie akcji przez przycisk.

Efekty rejestrują moduły ``core/hooks`` (``register_effect`` / ``register_ability``).
"""

from __future__ import annotations

from typing import Any

from src.core import offer_inputs, rules_hooks
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry


def _tech_key(tech_id: str) -> str:
    return f"technologies:{tech_id}"


def form(
    state: GameState, registry: StaticDataRegistry, player_id: str, tech_id: str
) -> dict[str, Any]:
    """Opis użycia technologii: rodzaj, czy silnik ją automatyzuje i wejścia formularza.

    Raises:
        ValueError: Nieznana technologia albo gracz jej nie posiada.
    """
    player = state.players.get(player_id)
    tech = registry.technologies.get(tech_id)
    if player is None or tech is None:
        raise ValueError(f"Unknown technology or player: {tech_id}")
    if tech_id not in player.technologies:
        raise ValueError(f"You do not own {tech.name}.")
    free = rules_hooks.ability_for(tech_id)
    if free is not None:
        _fn, inputs_fn = free
        kind, implemented = "free", True
        inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    else:
        effect = rules_hooks.effect_for(_tech_key(tech_id))
        inputs_fn = rules_hooks.inputs_for(_tech_key(tech_id))
        kind, implemented = "action", effect is not None
        inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    return {
        "tech_id": tech_id, "name": tech.name, "text": tech.text or "", "kind": kind,
        "implemented": implemented, "inputs": inputs,
        "exhausted": tech_id in player.exhausted_technologies,
    }


def free_abilities(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Zdolności poza akcją, które gracz posiada (z informacją, czy da się ich użyć teraz)."""
    player = state.players.get(player_id)
    if player is None:
        return []
    result: list[dict[str, Any]] = []
    for tech_id in rules_hooks.all_abilities():
        if tech_id not in player.technologies:
            continue
        info = form(state, registry, player_id, tech_id)
        reason = ""
        if state.phase.name != "ACTION":
            reason = "Only during the action phase."
        elif not offer_inputs.has_legal_answer(info["inputs"]):
            reason = "Nothing to use it on right now."
        result.append({**info, "usable": not reason, "reason": reason})
    return result


def use_free_ability(
    state: GameState,
    registry: StaticDataRegistry,
    actor_id: str,
    tech_id: str,
    params: dict[str, Any] | None = None,
) -> GameState:
    """Gracz używa zdolności poza akcją (nie zużywa akcji tury). Zwraca nowy stan.

    Raises:
        ValueError: Brak technologii/zdolności, zły stan gry albo odpowiedź spoza legalnych opcji.
    """
    info = form(state, registry, actor_id, tech_id)
    ability = rules_hooks.ability_for(tech_id)
    if ability is None:
        raise ValueError(f"{info['name']} has no ability that can be used outside an action.")
    cleaned = offer_inputs.validate_params(info["inputs"], params or {})
    new_state = state.clone()
    ability[0](new_state, registry, actor_id, cleaned)
    return new_state


def run_action_effect(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    tech_id: str,
    params: dict[str, Any] | None,
) -> bool:
    """Wykonuje efekt „ACTION:” technologii na ``state`` (KLON wołającego), jeśli jest zakodowany.

    Returns:
        True, gdy silnik zastosował efekt; False dla technologii bez zakodowanego efektu
        (akcja zostaje tylko zapisana, skutek rozstrzyga operator).
    """
    effect = rules_hooks.effect_for(_tech_key(tech_id))
    player = state.players[player_id]
    if effect is None or tech_id not in player.technologies:
        return False
    inputs_fn = rules_hooks.inputs_for(_tech_key(tech_id))
    inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    effect(state, registry, player_id, offer_inputs.validate_params(inputs, params or {}))
    return True
