"""Efekty kart akcji z oknem ACTION: żetony, karty, prawa, wpływ (RULES.md 53).

Zmiany stanu wyłącznie przez funkcje centralne (``command_tokens``, ``card_draw``, ``payment``,
``secret_objectives``, ``agenda_phase`` - RULES.md 43.1a). Teksty kart w docstringach to cytaty
z ``assets/data/action_cards``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import agenda_phase, card_draw, command_tokens, payment, secret_objectives
from src.core.game_state import GameState
from src.core.hooks.card_helpers import other_player_param, system_param
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect

_IMPERSONATION_COST = 3  # „Spend 3 influence”


@register_effect("action_cards:unexpected")
def unexpected_action(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Unexpected Action: Remove 1 of your command tokens from the game board and return it to your
    reinforcements.
    """
    command_tokens.remove_from_board(state, system_param(state, params), player_id)


@register_effect("action_cards:insub")
def insubordination(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Insubordination: Remove 1 token from another player's tactic pool and return it to their
    reinforcements.
    """
    target = other_player_param(state, player_id, params)
    command_tokens.spend_to_reinforcements(state, target, "tactical", 1)


@register_effect("action_cards:spy")
def spy(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Spy: Choose 1 player. That player gives you 1 random action card from their hand."""
    target = other_player_param(state, player_id, params)
    card_draw.take_random_action_card(state, target, player_id)


@register_effect("action_cards:repeal")
def repeal_law(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Repeal Law: Discard 1 law from play."""
    law = params.get("law")
    if not isinstance(law, str):
        raise ValueError("Choose 1 law in play ('law').")
    agenda_phase.repeal_law(state, law)


@register_effect("action_cards:impersonation")
def impersonation(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Impersonation: Spend 3 influence to draw 1 secret objective."""
    planets, trade_goods = payment.parse_payment(dict(params))
    paid = payment.validate_payment(state, registry, player_id, "influence", planets, trade_goods)
    if paid < _IMPERSONATION_COST:
        raise ValueError(f"Spend at least {_IMPERSONATION_COST} influence (you chose {paid}).")
    give_back = params.get("return")
    if give_back is not None and not isinstance(give_back, str):
        raise ValueError("'return' must be a secret objective id or 'drawn'.")
    secret_objectives.draw(state, player_id, give_back)
    payment.apply_payment(state, player_id, planets, trade_goods)
