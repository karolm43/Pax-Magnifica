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

from src.core import economy, frontier_cards, payment, research_offer, technology
from src.core import offer_inputs as oi
from src.core.game_state import GameState
from src.core.hooks.action_card_inputs import (
    Input,
    _option,
)
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import declare_data_driven, register_effect, register_effect_inputs

# Karty działające w regule bazowej, bez hooka (RULES.md 54.8): Ion Storm - żeton wormhole
# obracany po ruchu (``core/ion_storm.py``); Demilitarized Zone - czyszczenie planety przy
# dołączeniu (``exploration._apply_attach``) i zakaz stawiania jednostek (karty strategii/akcji).
declare_data_driven("explores:ion", "explores:dmz")

ENIGMATIC_DEVICE_IDS = ("ed1", "ed2")
_COST = 6  # „spend 6 resources"


def can_pay(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Czy gracz ma dostępne 6 zasobów (gotowe planety + TG, z możliwą zniżką Doctor Sucaban
    przed zapłatą - ``research_offer.potential_discount``) - wymóg zagrania."""
    ready = payment.ready_planet_values(state, registry, player_id, "resources")
    need = max(0, _COST - research_offer.potential_discount(state, registry, player_id))
    return sum(ready.values()) + economy.spendable_trade_goods(state, player_id) >= need


def _inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    affordable = can_pay(state, registry, player_id)
    techs = technology.researchable_techs(state, registry, player_id) if affordable else []
    return [
        oi.info(
            "research_after",
            "After playing, choose the technology in the research window.",
            [_option(t.id, t.name or t.id) for t in techs],
            hint=f"Costs {_COST} resources (Doctor Sucaban can lower it before you pay).",
        )
    ]


def _action(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any],
    card_id: str,
) -> None:
    """Zużywa kartę i otwiera okno badania (technologia i zapłata - ``core/research_offer``)."""
    if not can_pay(state, registry, player_id) or not technology.researchable_techs(
        state, registry, player_id
    ):
        raise ValueError(f"You need {_COST} resources and a technology you can research.")
    frontier_cards.purge_card(state, player_id, card_id)
    research_offer.begin(state, player_id, _DECISION, _COST)


_DECISION = "enigmatic_device"
research_offer.register_decision(
    _DECISION, "Enigmatic Device: research 1 technology", frontier_cards.effect_key("ed1")
)


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
