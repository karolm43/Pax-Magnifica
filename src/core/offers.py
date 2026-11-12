"""Oferty i decyzje graczy: widok dla UI i odpowiedzi (RULES.md 56). Funkcje CZYSTE.

Cienka warstwa nad ``core/triggers`` (oferty powstają w ``fire``, a przyjęcie/odmowa to
``accept_offer``/``decline_offer``): buduje opis oferty dla formularza (legalne opcje liczy silnik
na bieżącym stanie) i po odpowiedzi wznawia przepływy, które czekały na decyzje (walka w kroku
``TRIGGERS``). Silnik nigdy nie wybiera za gracza.
"""

from __future__ import annotations

from typing import Any

from src.core import battle, rules_hooks, triggers
from src.core.component_text import describe_component
from src.core.game_state import GameState, PendingOffer
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


def offer_view(
    state: GameState, registry: StaticDataRegistry, offer: PendingOffer
) -> dict[str, Any]:
    """Opis oferty do UI: nazwa i tekst karty, czy obowiązkowa oraz wejścia formularza."""
    hook = rules_hooks.hook_by_seq(offer.hook_seq)
    inputs: list[dict[str, Any]] = []
    name, text, kind = ("", "", "")
    if hook is not None:
        name, text, kind = describe_component(registry, hook.covers)
        if hook.inputs is not None:
            inputs = hook.inputs(state, registry, offer.player_id, offer.ctx)
    return {
        "id": offer.id,
        "player_id": offer.player_id,
        "owner_id": offer.owner_id or offer.player_id,
        "name": name or offer.label,
        "label": offer.label,
        "text": text,
        "kind": kind,
        "mandatory": offer.mandatory,
        "inputs": inputs,
    }


def offers_view(
    state: GameState, registry: StaticDataRegistry, player_id: str | None = None
) -> list[dict[str, Any]]:
    """Oferty czekające na decyzję (wszystkich albo jednego gracza)."""
    return [
        offer_view(state, registry, o)
        for o in state.pending_offers
        if player_id is None or o.player_id == player_id
    ]


def _resume(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Wznawia przepływy zaparkowane na decyzjach (dziś: walka w kroku TRIGGERS)."""
    return battle.resume_after_triggers(state, grid, registry)


def accept(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    actor_id: str,
    offer_id: str,
    params: dict[str, Any] | None = None,
) -> GameState:
    """Gracz przyjmuje ofertę z wyborami; po niej wznawiamy czekające przepływy."""
    return _resume(triggers.accept_offer(state, actor_id, offer_id, params), grid, registry)


def decline(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, actor_id: str, offer_id: str
) -> GameState:
    """Gracz odmawia („may"); decyzji obowiązkowej nie można odrzucić."""
    return _resume(triggers.decline_offer(state, actor_id, offer_id), grid, registry)
