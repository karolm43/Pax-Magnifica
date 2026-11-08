"""Efekty kart akcji z oknem ACTION (RULES.md 53). Treść kart: ``assets/data/action_cards``.

Każdy efekt zmienia stan WYŁĄCZNIE przez funkcje centralne (economy, exhaust, unit_ops - RULES.md
43.1a) i mutuje przekazany klon. Teksty kart w docstringach to dosłowne cytaty z assetów.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import economy, exhaust, exploration, objectives, unit_ops
from src.core.game_state import GameState, SystemState
from src.core.planet_stats import resources_of
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect
from src.core.unit_ops import UnitCause

_INFANTRY = "infantry"


def _controlled(state: GameState, player_id: str) -> list[str]:
    """Planety kontrolowane przez gracza (w kolejności systemów na mapie)."""
    owners = objectives.planet_owners(state)
    return [planet for planet, owner in owners.items() if owner == player_id]


def _with_trait(
    state: GameState, registry: StaticDataRegistry, player_id: str, trait: str
) -> list[str]:
    return [
        planet
        for planet in _controlled(state, player_id)
        if trait in exploration.planet_traits(registry, planet)
    ]


def _planet_param(state: GameState, player_id: str, params: Mapping[str, Any]) -> str:
    planet = params.get("planet")
    if not isinstance(planet, str) or planet not in _controlled(state, player_id):
        raise ValueError("Choose 1 planet you control ('planet').")
    return planet


def _system_of(state: GameState, planet: str) -> SystemState:
    for system in state.systems.values():
        if planet in system.planet_owners:
            return system
    raise ValueError(f"Planet {planet} is not on the board.")


def _place_infantry(state: GameState, player_id: str, planet: str, count: int) -> None:
    """Stawia piechotę z rezerwy na planecie (limit rezerwy - jak przy produkcji)."""
    left = reinforcements_left(state, player_id, _INFANTRY)
    if left is not None and left < count:
        raise ValueError(f"Not enough infantry in reinforcements: {left} < {count}.")
    unit_ops.place_units(
        state, _system_of(state, planet), planet, player_id, _INFANTRY, count, UnitCause.PLACED
    )


@register_effect("action_cards:industrial_initiative")
def industrial_initiative(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Industrial Initiative: Gain 1 trade good for each industrial planet you control."""
    count = len(_with_trait(state, registry, player_id, "industrial"))
    economy.gain_trade_goods(state, player_id, count)


@register_effect("action_cards:economic_initiative")
def economic_initiative(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Economic Initiative: Ready each cultural planet you control."""
    exhaust.ready_planets(state, player_id, _with_trait(state, registry, player_id, "cultural"))


@register_effect("action_cards:mining_initiative")
def mining_initiative(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Mining Initiative: Gain trade goods equal to the resource value of 1 planet you control."""
    planet = _planet_param(state, player_id, params)
    economy.gain_trade_goods(state, player_id, resources_of(state, registry, planet))


@register_effect("action_cards:f_deployment")
def frontline_deployment(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Frontline Deployment: Place 3 infantry from your reinforcements on 1 planet you control."""
    _place_infantry(state, player_id, _planet_param(state, player_id, params), 3)


@register_effect("action_cards:messiah")
def rise_of_a_messiah(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Rise of a Messiah: Place 1 infantry from your reinforcements on each planet you control."""
    for planet in _controlled(state, player_id):
        _place_infantry(state, player_id, planet, 1)
