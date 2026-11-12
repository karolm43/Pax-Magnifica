"""Efekty kart frontier zagrywanych z ręki (zakładka Action cards): Enigmatic Device.

Enigmatic Device (ed1/ed2): ACTION: You may spend 6 resources and purge this card to research 1
technology. Wzorzec płatności + badania jak Reveal Prototype (``reactions_combat``): najpierw
walidacja planu badania (bez mutacji), potem płatność, potem badanie. Błąd na dowolnym etapie
cofa całą akcję (efekt pracuje na klonie). Źródło: ``C_exploration_cards.md`` (Enigmatic Device:
nie da się zagrać bez 6 dostępnych zasobów).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import economy, frontier_cards, payment, technology
from src.core.game_state import GameState
from src.core.hooks.action_card_inputs import (
    Input,
    _choice,
    _multi,
    _number,
    _option,
    _planet_label,
)
from src.core.offer_inputs import as_payment
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect, register_effect_inputs

ENIGMATIC_DEVICE_IDS = ("ed1", "ed2")
_COST = 6  # „spend 6 resources"


def can_pay(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Czy gracz ma dostępne 6 zasobów (gotowe planety + trade goods) - wymóg zagrania."""
    ready = payment.ready_planet_values(state, registry, player_id, "resources")
    return sum(ready.values()) + economy.spendable_trade_goods(state, player_id) >= _COST


def _inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    affordable = can_pay(state, registry, player_id)
    techs = technology.researchable_techs(state, registry, player_id) if affordable else []
    ready = payment.ready_planet_values(state, registry, player_id, "resources")
    spendable = economy.spendable_trade_goods(state, player_id)
    skips = [
        _option(planet, _planet_label(state, registry, planet, "skips 1 prerequisite"))
        for planet in technology.specialty_planets(state, registry, player_id)
    ]
    if technology.aida_ready(state, player_id):
        skips.append(_option(technology.AIDA_SKIP, "AI Development Algorithm (unit upgrades)"))
    pay_planets = [
        _option(p, _planet_label(state, registry, p, f"spend {value} resources"), p)
        for p, value in ready.items()
        if value > 0
    ]
    return [
        _choice(
            "technology", "Technology to research",
            [_option(t.id, t.name or t.id) for t in techs],
            hint=f"Costs {_COST} resources.",
        ),
        _multi("skips", "Skips: exhaust to ignore a prerequisite", skips, 0, len(skips)),
        as_payment(
            _multi(
                "planets", "Planets to exhaust", pay_planets, 0, len(pay_planets),
                f"Spend at least {_COST} resources.",
            ),
            ready, "resources", _COST,
        ),
        _number("trade_goods", "Trade goods to spend", 0, spendable),
    ]


def _action(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any],
    card_id: str,
) -> None:
    tech_id = params.get("technology")
    if not isinstance(tech_id, str) or not tech_id:
        raise ValueError("Choose the technology to research ('technology').")
    skips = params.get("skips", [])
    if not isinstance(skips, list) or not all(isinstance(s, str) for s in skips):
        raise ValueError("'skips' must be a list of ids.")
    planets, trade_goods = payment.parse_payment(dict(params))
    plan = technology.plan_research(state, registry, player_id, tech_id, list(skips))
    technology.pay_research(
        state, registry, player_id, _COST, planets, trade_goods, skip_planets=tuple(skips)
    )
    frontier_cards.purge_card(state, player_id, card_id)
    technology.apply_research(state, player_id, plan)


def _register(card_id: str) -> None:
    key = frontier_cards.effect_key(card_id)

    def effect(
        state: GameState, registry: StaticDataRegistry, player_id: str,
        params: Mapping[str, Any],
    ) -> None:
        """Enigmatic Device: ACTION: spend 6 resources and purge this card to research 1
        technology.
        """
        _action(state, registry, player_id, params, card_id)

    register_effect(key)(effect)
    register_effect_inputs(key)(_inputs)


for _card_id in ENIGMATIC_DEVICE_IDS:
    _register(_card_id)
