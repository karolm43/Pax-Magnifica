"""Efekty kart akcji z oknem ACTION: ekonomia i stawianie piechoty (RULES.md 53).

Treść kart: ``assets/data/action_cards``. Każdy efekt zmienia stan WYŁĄCZNIE przez funkcje
centralne (economy, exhaust, unit_ops - RULES.md 43.1a) i mutuje przekazany klon. Teksty kart
w docstringach to dosłowne cytaty z assetów. Pozostałe karty: ``action_cards_units`` (jednostki)
i ``action_cards_other`` (żetony, karty, prawa, wpływ).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import economy, exhaust
from src.core.game_state import GameState
from src.core.hooks.card_helpers import (
    controlled,
    own_planet_param,
    place_from_reinforcements,
    system_of_planet,
    with_trait,
)
from src.core.planet_stats import resources_of
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect

_INFANTRY = "infantry"


@register_effect("action_cards:industrial_initiative")
def industrial_initiative(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Industrial Initiative: Gain 1 trade good for each industrial planet you control."""
    industrial = with_trait(state, registry, player_id, "industrial")
    economy.gain_trade_goods(state, player_id, len(industrial))


@register_effect("action_cards:economic_initiative")
def economic_initiative(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Economic Initiative: Ready each cultural planet you control."""
    exhaust.ready_planets(state, player_id, with_trait(state, registry, player_id, "cultural"))


@register_effect("action_cards:mining_initiative")
def mining_initiative(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Mining Initiative: Gain trade goods equal to the resource value of 1 planet you control."""
    planet = own_planet_param(state, player_id, params)
    economy.gain_trade_goods(state, player_id, resources_of(state, registry, planet))


@register_effect("action_cards:f_deployment")
def frontline_deployment(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Frontline Deployment: Place 3 infantry from your reinforcements on 1 planet you control."""
    planet = own_planet_param(state, player_id, params)
    system = system_of_planet(state, planet)
    place_from_reinforcements(state, system, planet, player_id, _INFANTRY, 3)


@register_effect("action_cards:messiah")
def rise_of_a_messiah(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Rise of a Messiah: Place 1 infantry from your reinforcements on each planet you control."""
    for planet in controlled(state, player_id):
        place_from_reinforcements(
            state, system_of_planet(state, planet), planet, player_id, _INFANTRY, 1
        )
