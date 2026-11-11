"""Zdolności „ACTION:” kart legendarnych planet jako akcja komponentu (RULES.md 60.3).

Odpowiednik ``relic_actions`` / ``relic_cards`` dla kart zdolności legendarnych. Zdolność z
nagłówkiem ``ACTION:`` w tekście planety zagrywa się przez
``component_action.play_component_action(component_id="planet:<id>")`` (zużywa akcję tury);
karta zostaje u gracza i się wyczerpuje. Pozostałe zdolności (koniec tury, pas, kontrola planety)
działają przez oferty hooków (``core/hooks/planets_legendary.py``).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

from src.core import legendary_planets, offer_inputs, rules_hooks
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

COMPONENT_PREFIX = "planet:"  # id komponentu w akcji komponentu: "planet:<id planety>"
_ACTION_HEADER = re.compile(r"(?:^|[\n.]\s*)ACTION\s*:", re.IGNORECASE)

BlockerFn = Callable[[GameState, StaticDataRegistry, str], str | None]
_BLOCKERS: dict[str, BlockerFn] = {}


def blocker(planet_id: str) -> Callable[[BlockerFn], BlockerFn]:
    """Rejestruje dodatkowy warunek zagrywalności ACTION planety (powód odmowy albo ``None``)."""

    def decorate(fn: BlockerFn) -> BlockerFn:
        if planet_id in _BLOCKERS:
            raise ValueError(f"Blocker already registered for {planet_id}.")
        _BLOCKERS[planet_id] = fn
        return fn

    return decorate


def effect_key(planet_id: str) -> str:
    """Klucz komponentu w rejestrze efektów (``planets:<id>``)."""
    return f"planets:{planet_id}"


def component_id(planet_id: str) -> str:
    """Id komponentu przekazywane do akcji komponentu."""
    return f"{COMPONENT_PREFIX}{planet_id}"


def planet_of(component: str) -> str | None:
    """Id planety z id komponentu (``None``, gdy to nie karta zdolności legendarnej)."""
    if not component.startswith(COMPONENT_PREFIX):
        return None
    return component.removeprefix(COMPONENT_PREFIX)


def is_action_planet(registry: StaticDataRegistry, planet_id: str) -> bool:
    """Czy zdolność legendarna planety ma nagłówek „ACTION:”."""
    planet = registry.planets.get(planet_id)
    return bool(planet and _ACTION_HEADER.search(planet.legendary_ability_text or ""))


def block_reason(
    state: GameState, registry: StaticDataRegistry, player_id: str, planet_id: str
) -> str | None:
    """Powód, dla którego karta nie może teraz wykonać swojej ACTION (``None`` = może)."""
    rules_hooks.effect_for(effect_key(planet_id))  # wymusza załadowanie pakietu hooków
    if not legendary_planets.is_ready(state, player_id, planet_id):
        return "This legendary planet ability card is exhausted (or not yours)."
    fn = _BLOCKERS.get(planet_id)
    return fn(state, registry, player_id) if fn is not None else None


def form(
    state: GameState, registry: StaticDataRegistry, player_id: str, planet_id: str
) -> dict[str, Any]:
    """Opis karty zdolności dla UI: rodzaj, czy silnik ją automatyzuje i wejścia formularza.

    Raises:
        ValueError: Nieznana planeta / gracz jej nie kontroluje / brak zdolności legendarnej.
    """
    player = state.players.get(player_id)
    planet = registry.planets.get(planet_id)
    if player is None or planet is None or not planet.legendary_ability_name:
        raise ValueError(f"Unknown legendary planet: {planet_id}")
    if planet_id not in player.controlled_planets:
        raise ValueError(f"You do not control {planet.name}.")
    key = effect_key(planet_id)
    action = is_action_planet(registry, planet_id)
    inputs: list[dict[str, Any]] = []
    if action and rules_hooks.effect_for(key) is not None:
        inputs_fn = rules_hooks.inputs_for(key)
        inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    covered = key in rules_hooks.covered_components()
    implemented = rules_hooks.effect_for(key) is not None if action else covered
    return {
        "planet_id": planet_id,
        "name": planet.legendary_ability_name,
        "planet_name": planet.name,
        "text": planet.legendary_ability_text or "",
        "kind": "action" if action else "passive",
        "implemented": implemented,
        "inputs": inputs,
        "exhausted": planet_id in player.exhausted_legendaries,
    }


def playability(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Karty zdolności legendarnych gracza z informacją, które ACTION można zagrać TERAZ.

    ``passive`` = działa samo (oferty hooków, bez przycisku). Nie mutuje stanu.
    """
    from src.core import component_action  # lokalnie: component_action importuje ten moduł

    rows: list[dict[str, Any]] = []
    for planet_id in legendary_planets.legendary_planets_of(state, registry, player_id):
        info = form(state, registry, player_id, planet_id)
        row: dict[str, Any] = {
            "planet_id": planet_id,
            "name": info["name"],
            "kind": info["kind"],
            "playable": False,
            "reason": None,
            "implemented": info["implemented"],
            "exhausted": info["exhausted"],
        }
        rows.append(row)
        if info["kind"] != "action":
            row["reason"] = "Passive - it works on its own (offers appear at the right moment)."
            continue
        try:
            component_action.play_component_action(
                state, player_id, component_id(planet_id), fire_after=False, run_effect=False
            )
        except ValueError as exc:
            row["reason"] = str(exc)
            continue
        reason = block_reason(state, registry, player_id, planet_id)
        if reason is not None:
            row["reason"] = reason
        elif info["implemented"] and not offer_inputs.has_legal_answer(info["inputs"]):
            row["reason"] = "No legal target for this ability right now."
        else:
            row["playable"] = True
    return rows


def run_action_effect(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    component: str,
    params: Mapping[str, Any] | None,
) -> bool:
    """Wykonuje efekt „ACTION:” karty zdolności legendarnej na ``state`` (KLON wołającego).

    Returns:
        True, gdy silnik zastosował efekt; False, gdy ``component`` nie jest taką kartą albo efekt
        nie jest zakodowany (akcja zostaje zapisana, skutek rozstrzyga operator).

    Raises:
        ValueError: Karta niegotowa / wybory spoza legalnych opcji.
    """
    planet_id = planet_of(component)
    if planet_id is None:
        return False
    player = state.players[player_id]
    if planet_id not in player.controlled_planets or not is_action_planet(registry, planet_id):
        raise ValueError(f"{component} is not an ACTION legendary planet ability you control.")
    key = effect_key(planet_id)
    effect = rules_hooks.effect_for(key)
    if effect is None:
        return False
    reason = block_reason(state, registry, player_id, planet_id)
    if reason is not None:
        raise ValueError(reason)
    inputs_fn = rules_hooks.inputs_for(key)
    inputs = inputs_fn(state, registry, player_id) if inputs_fn is not None else []
    effect(state, registry, player_id, offer_inputs.validate_params(inputs, params or {}))
    return True


def play_planet_ability(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    planet_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    actor_id: str | None = None,
) -> tuple[GameState, bool]:
    """Aktywny gracz zagrywa ACTION swojej karty zdolności legendarnej (akcja komponentu).

    Błąd na dowolnym etapie = ``ValueError`` i ZERO zmian (praca na klonie).

    Returns:
        ``(nowy stan, implemented)``.
    """
    from src.core import component_action  # lokalnie: component_action importuje ten moduł

    if actor_id is not None and actor_id != player_id:
        raise ValueError(f"{actor_id} cannot play a legendary planet ability for {player_id}.")
    info = form(state, registry, player_id, planet_id)
    if info["kind"] != "action":
        raise ValueError(f"{info['name']} has no ACTION - it works on its own.")
    reason = block_reason(state, registry, player_id, planet_id)
    if reason is not None:
        raise ValueError(reason)
    new_state = component_action.play_component_action(
        state, player_id, component_id(planet_id), params=params
    )
    return new_state, bool(info["implemented"])
