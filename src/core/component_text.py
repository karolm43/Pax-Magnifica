"""Nazwa, tekst i rodzaj komponentu gry z assetów — po kluczu ``<kategoria>:<id>[:...]``.

Wspólne dla okien decyzji (oferty) i panelu efektów stałych: klucz ``covers`` hooka albo
``ActiveEffect.key`` (np. ``leaders:letnevhero``, ``leaders:letnevagent:die``) zamieniamy na
czytelną nazwę i tekst karty, zamiast pokazywać surowe id. Funkcje CZYSTE.
"""

from __future__ import annotations

from typing import Any

from src.core.components import ComponentCategory
from src.core.game_state import GameState
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
    "explores": "Exploration",
    "strategy_cards": "Strategy card",
    "galactic_events": "Galactic event",
}

# Zakres trwania efektu (``Duration``) -> krótki opis „do kiedy” w panelu efektów.
SCOPE_LABELS = {
    "turn": "this turn",
    "tactical_action": "this tactical action",
    "invasion": "this invasion",
    "agenda": "this agenda",
    "combat": "this combat",
    "combat_round": "this combat round",
    "phase": "this phase",
    "round": "this game round",
    "game": "rest of the game",
    "while_in_play": "while in play",
}


def describe_component(registry: StaticDataRegistry, covers: str | None) -> tuple[str, str, str]:
    """``(nazwa, tekst, rodzaj)`` komponentu hooka z assetów; pusto, gdy brak danych.

    Rodzaj to krótka etykieta do nagłówka okna decyzji (np. „Agent”, „Faction ability”).
    """
    from src.core import faction_components  # lokalnie: faction_components -> ... -> offers

    if not covers or ":" not in covers:
        return "", "", ""
    # Klucz efektu może mieć dopisek po drugim dwukropku (``leaders:letnevagent:die``).
    category, component = covers.split(":", 2)[:2]
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


def active_effects_view(state: GameState, registry: StaticDataRegistry) -> list[dict[str, Any]]:
    """Efekty trwałe w grze do panelu przy planszy: nazwa, rodzaj, tekst, właściciel, zakres.

    ``detail`` = czego dotyczy efekt, gdy zapisał to w danych (np. statek, który dostał kość
    agenta: ``base_type`` -> nazwa jednostki właściciela; system ``position``).
    """
    from src.core.fleet_pool import unit_name  # lokalnie: fleet_pool importuje hooki

    rows: list[dict[str, Any]] = []
    for effect in state.active_effects:
        name, text, kind = describe_component(registry, effect.key)
        details: list[str] = []
        base_type = effect.data.get("base_type")
        if isinstance(base_type, str) and base_type:
            owner = effect.owner or state.active_player_id or ""
            details.append(
                unit_name(state, registry, owner, base_type) if owner in state.players
                else base_type
            )
        position = effect.data.get("position")
        if isinstance(position, str) and position:
            details.append(f"system {position}")
        rows.append({
            "id": effect.id,
            "key": effect.key,
            "name": name or _fallback_name(effect.key),
            "kind": kind,
            "text": text,
            "owner": effect.owner,
            "scope": effect.scope,
            "until": SCOPE_LABELS.get(effect.scope, effect.scope),
            "detail": ", ".join(details),
            "round": effect.created_round,
        })
    return rows


def _fallback_name(key: str) -> str:
    """Nazwa z klucza, gdy komponentu nie ma w assetach (``foo:bar_baz`` -> „Bar baz”)."""
    parts = key.split(":")
    raw = parts[1] if len(parts) > 1 else parts[0]
    return raw.replace("_", " ").capitalize()
