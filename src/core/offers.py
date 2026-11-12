"""Oferty i decyzje graczy: widok dla UI i odpowiedzi (RULES.md 56). Funkcje CZYSTE.

Cienka warstwa nad ``core/triggers`` (oferty powstają w ``fire``, a przyjęcie/odmowa to
``accept_offer``/``decline_offer``): buduje opis oferty dla formularza (legalne opcje liczy silnik
na bieżącym stanie) i po odpowiedzi wznawia przepływy, które czekały na decyzje (walka w kroku
``TRIGGERS``). Silnik nigdy nie wybiera za gracza.
"""

from __future__ import annotations

from typing import Any

from src.core import battle, rules_hooks, triggers
from src.core.components import ComponentCategory
from src.core.game_state import GameState, PendingOffer
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

# Rodzaj komponentu (prefiks ``covers``) -> etykieta w nagłówku decyzji.
_KIND_LABELS = {
    "technologies": "Technology",
    "abilities": "Faction ability",
    "breakthroughs": "Breakthrough",
    "units": "Unit ability",
    "relics": "Relic",
    "promissory_notes": "Promissory note",
    "planets": "Legendary planet",
    "action_cards": "Action card",
    "agendas": "Law",
}


def _component(registry: StaticDataRegistry, covers: str | None) -> tuple[str, str, str]:
    """``(nazwa, tekst, rodzaj)`` komponentu hooka z assetów; pusto, gdy brak danych.

    Rodzaj to krótka etykieta do nagłówka okna decyzji (np. „Agent”, „Faction ability”).
    """
    from src.core import faction_components  # lokalnie: faction_components -> ... -> offers

    if not covers or ":" not in covers:
        return "", "", ""
    category, component = covers.split(":", 1)
    kind = _KIND_LABELS.get(category, "")
    if category == "technologies":
        tech = registry.technologies.get(component)
        return (tech.name, tech.text or "", kind) if tech is not None else ("", "", kind)
    if category in ("abilities", "leaders", "breakthroughs"):
        singular = {"abilities": "ability", "leaders": "leader", "breakthroughs": "breakthrough"}
        try:
            name, text = faction_components.describe(registry, singular[category], component)
        except ValueError:
            return "", "", kind
        if category == "leaders":
            leader = registry.leaders.get(component)
            kind = (leader.type.capitalize() if leader is not None else "") or "Leader"
        return name, text, kind
    if category == "units":
        unit = registry.units.get(component)
        if unit is None:
            return "", "", kind
        return unit.name, unit.ability or "", kind
    if category == "planets":
        planet = registry.planets.get(component)
        if planet is None:
            return "", "", kind
        return (
            planet.legendary_ability_name or planet.name,
            planet.legendary_ability_text or "",
            kind,
        )
    for entry_category in ComponentCategory:
        if entry_category.value == category:
            entry = registry.catalog.get(entry_category, component)
            if entry is not None:
                text = " ".join(t for t in entry.texts.values() if t)
                return entry.name or "", text, kind
    return "", "", kind


def offer_view(
    state: GameState, registry: StaticDataRegistry, offer: PendingOffer
) -> dict[str, Any]:
    """Opis oferty do UI: nazwa i tekst karty, czy obowiązkowa oraz wejścia formularza."""
    hook = rules_hooks.hook_by_seq(offer.hook_seq)
    inputs: list[dict[str, Any]] = []
    name, text, kind = ("", "", "")
    if hook is not None:
        name, text, kind = _component(registry, hook.covers)
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
