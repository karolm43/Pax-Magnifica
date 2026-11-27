"""Oferty i decyzje graczy: widok dla UI i odpowiedzi (RULES.md 56). Funkcje CZYSTE.

Cienka warstwa nad ``core/triggers`` (oferty powstają w ``fire``, a przyjęcie/odmowa to
``accept_offer``/``decline_offer``): buduje opis oferty dla formularza (legalne opcje liczy silnik
na bieżącym stanie) i po odpowiedzi wznawia przepływy, które czekały na decyzje (walka w kroku
``TRIGGERS``). Silnik nigdy nie wybiera za gracza.
"""

from __future__ import annotations

from typing import Any

from src.core import battle, cooperative, rules_hooks, triggers
from src.core.component_text import describe_component
from src.core.game_state import GameState, PendingOffer
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


def offer_view(
    state: GameState, registry: StaticDataRegistry, offer: PendingOffer
) -> dict[str, Any]:
    """Opis oferty do UI: nazwa i tekst karty, czy obowiązkowa oraz wejścia formularza."""
    deal = cooperative.deal_view(offer)
    hook = (
        None if offer.hook_seq == cooperative.COMPONENT_HOOK
        else rules_hooks.hook_by_seq(offer.hook_seq)
    )
    inputs: list[dict[str, Any]] = []
    name, text, kind = ("", "", "")
    # Źródło („technologies:asc"…) - UI pokazuje kafelek komponentu (np. karta technologii).
    source = hook.covers if hook is not None and hook.covers else ""
    if hook is not None:
        name, text, kind = describe_component(registry, hook.covers)
        if hook.inputs is not None:
            # A deal answers the OWNER's form, even when the requester picks (54.15).
            who = str(deal["owner"]) if deal is not None else offer.player_id
            inputs = hook.inputs(state, registry, who, offer.ctx)
    elif deal is not None:
        # Requested window-use component (RULES.md 54.15): the component's own form.
        source = str(offer.ctx[cooperative.DEAL]["source"])
        name, text, kind = describe_component(registry, source)
        inputs_fn = rules_hooks.inputs_for(source)
        if inputs_fn is not None:
            inputs = inputs_fn(state, registry, deal["owner"])
    if deal is not None:
        inputs = cooperative.deal_inputs(state, offer, inputs)  # only the requester's options
    return {
        "id": offer.id,
        "player_id": offer.player_id,
        "owner_id": offer.owner_id or offer.player_id,
        "name": name or offer.label,
        "label": offer.label,
        "text": text,
        "kind": kind,
        "source": source,
        "mandatory": offer.mandatory,
        "inputs": inputs,
        # Requested cooperative effect (RULES.md 54.15): who asks and what they pay.
        "deal": deal,
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
    """Gracz przyjmuje ofertę z wyborami; po niej wznawiamy czekające przepływy.

    A deal (requested cooperative effect, RULES.md 54.15) pays and resolves in the same step.
    """
    offer = next((o for o in state.pending_offers if o.id == offer_id), None)
    if offer is not None and cooperative.is_deal(offer):
        accepted = cooperative.accept(state, registry, grid, actor_id, offer_id, params)
        return _resume(accepted, grid, registry)
    return _resume(triggers.accept_offer(state, actor_id, offer_id, params), grid, registry)


def decline(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, actor_id: str, offer_id: str
) -> GameState:
    """Gracz odmawia („may"); decyzji obowiązkowej nie można odrzucić."""
    offer = next((o for o in state.pending_offers if o.id == offer_id), None)
    if offer is not None and cooperative.is_deal(offer):
        return _resume(cooperative.decline(state, actor_id, offer_id), grid, registry)
    return _resume(triggers.decline_offer(state, actor_id, offer_id), grid, registry)
