"""Podglądy skutku kart akcji liczone z bieżącego stanu gracza (``register_effect_preview``).

Odpowiedź ``GET /action-card/{id}/inputs`` ma pole ``summary`` („dotyczy: …"): krótko, ile
planet/jednostek obejmie karta i co z tego wyjdzie. Liczby pochodzą ze stanu i rejestru
(``planet_stats``, ``exploration``). Podgląd jest TYLKO informacją (nie zmienia stanu).
"""

from __future__ import annotations

from src.core import command_tokens, planet_stats
from src.core.game_state import GameState
from src.core.hooks import card_labels
from src.core.hooks.card_helpers import controlled, with_trait
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect_preview


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _names(state: GameState, registry: StaticDataRegistry, planets: list[str]) -> str:
    return ", ".join(card_labels.planet_name(registry, p) for p in planets) or "none"


@register_effect_preview("action_cards:industrial_initiative")
def industrial_preview(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    planets = with_trait(state, registry, player_id, "industrial")
    names = _names(state, registry, planets)
    return (
        f"You control {_plural(len(planets), 'industrial planet')} ({names})"
        f" → +{_plural(len(planets), 'trade good')}"
    )


@register_effect_preview("action_cards:economic_initiative")
def economic_preview(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    planets = with_trait(state, registry, player_id, "cultural")
    exhausted = [p for p in planets if p in state.players[player_id].exhausted_planets]
    names = _names(state, registry, planets)
    return (
        f"You control {_plural(len(planets), 'cultural planet')} ({names})"
        f" → {len(exhausted)} exhausted will be readied"
    )


@register_effect_preview("action_cards:messiah")
def messiah_preview(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    planets = controlled(state, player_id)
    left = reinforcements_left(state, player_id, "infantry")
    stock = "no reinforcement limit" if left is None else f"{left} infantry in reinforcements"
    return (
        f"1 infantry on each of your {_plural(len(planets), 'planet')} "
        f"({_names(state, registry, planets)}); {stock}"
    )


@register_effect_preview("action_cards:harness")
def harness_preview(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    player = state.players[player_id]
    return (
        f"You have {player.commodities}/{player.commodity_value} commodities → "
        f"replenished to {player.commodity_value}"
    )


@register_effect_preview("action_cards:rally")
def rally_preview(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    left = command_tokens.reinforcements(state, player_id)
    return f"{_plural(left, 'command token')} in reinforcements → up to 2 go to your fleet pool"


@register_effect_preview("action_cards:mining_initiative")
def mining_preview(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    planets = controlled(state, player_id)
    if not planets:
        return "You control no planets"
    best = max(planets, key=lambda p: planet_stats.resources_of(state, registry, p))
    value = planet_stats.resources_of(state, registry, best)
    return (
        f"1 of your {_plural(len(planets), 'planet')} → trade goods equal to its resources "
        f"(best: {card_labels.planet_name(registry, best)} +{value})"
    )


@register_effect_preview("action_cards:f_deployment")
def deployment_preview(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    left = reinforcements_left(state, player_id, "infantry")
    stock = "no reinforcement limit" if left is None else f"{left} infantry in reinforcements"
    own = _plural(len(controlled(state, player_id)), "planet")
    return f"3 infantry on 1 of your {own}; {stock}"
