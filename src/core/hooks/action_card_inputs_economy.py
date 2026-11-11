"""Opisy wyborów (formularz) dla kart z ``action_cards_economy`` (RULES.md 53).

Format wejść: patrz ``action_card_inputs``. Legalne opcje liczy ``card_targets_economy`` - te
same listy, względem których efekt waliduje wybór. Brak legalnej opcji (pusta lista) blokuje
zagranie karty w ``action_cards.playability``.
"""

from __future__ import annotations

from typing import Any

from src.core import economy, payment, technology
from src.core.components import ComponentCategory
from src.core.fleet_pool import unit_name
from src.core.game_state import GameState
from src.core.hooks import card_targets_economy as targets
from src.core.hooks.action_card_inputs import (
    Input,
    _choice,
    _multi,
    _number,
    _option,
    _planet_name,
    _player_label,
    _system_label,
)
from src.core.models import TechnologyDef
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect_inputs
from src.core.unit_ops import count_in_zone

_FOCUSED_COST = 4
_PLAGIARIZE_COST = 5
_UNSTABLE_MAX = 3
_DECK_LABELS = {"cultural": "Cultural", "hazardous": "Hazardous", "industrial": "Industrial"}


def _tech_options(techs: list[TechnologyDef]) -> list[dict[str, Any]]:
    return [_option(t.id, t.name or t.id) for t in techs]


def _skip_input(state: GameState, registry: StaticDataRegistry, player_id: str) -> Input:
    """Planety ze specjalnością (i AIDA), którymi można pokryć brakujące prerekwizyty."""
    options = [
        _option(planet, f"{_planet_name(registry, planet)} (technology specialty)")
        for planet in technology.specialty_planets(state, registry, player_id)
    ]
    if technology.aida_ready(state, player_id):
        options.append(_option(technology.AIDA_SKIP, "AI Development Algorithm (unit upgrades)"))
    return _multi(
        "skips",
        "Skips: exhaust to ignore a prerequisite",
        options,
        0,
        len(options),
        "Only the symbols you are missing; an unnecessary skip is refused.",
    )


@register_effect_inputs("action_cards:arch_expedition")
def arch_expedition_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    options = [
        _option(deck, f"{_DECK_LABELS.get(deck, deck)} exploration deck")
        for deck in targets.matching_decks(state, registry, player_id)
    ]
    return [_choice("deck", "Exploration deck (matches a planet you control)", options)]


@register_effect_inputs("action_cards:brilliance")
def brilliance_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    options = [
        _option(
            {"mode": "ready_planet", "planet": planet},
            f"Ready {_planet_name(registry, planet)}",
            f"ready:{planet}",
        )
        for planet in targets.specialty_planets_owned(state, registry, player_id)
    ]
    for pid in targets.breakthrough_targets(state, registry):
        who = "yourself" if pid == player_id else _player_label(state, registry, pid)
        options.append(
            _option(
                {"mode": "breakthrough", "player": pid},
                f"Gain the breakthrough: {who}",
                f"breakthrough:{pid}",
            )
        )
    return [_choice("effect", "Ready a planet or give a breakthrough", options, merge=True)]


@register_effect_inputs("action_cards:divert_funding")
def divert_funding_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    returnable = targets.returnable_techs(state, registry, player_id)
    researchable = targets.divert_research_options(state, registry, player_id)
    return [
        _choice("return_technology", "Technology to return", _tech_options(returnable)),
        _choice(
            "technology",
            "Technology to research",
            _tech_options(researchable) if returnable else [],
            hint="The returned technology does not count towards prerequisites.",
        ),
        _skip_input(state, registry, player_id),
    ]


@register_effect_inputs("action_cards:f_researched")
def focused_research_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    can_pay = economy.spendable_trade_goods(state, player_id) >= _FOCUSED_COST
    researchable = technology.researchable_techs(state, registry, player_id) if can_pay else []
    return [
        _choice(
            "technology",
            "Technology to research",
            _tech_options(researchable),
            hint=f"Costs {_FOCUSED_COST} trade goods.",
        ),
        _skip_input(state, registry, player_id),
    ]


@register_effect_inputs("action_cards:plagiarize")
def plagiarize_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    ready = payment.ready_planet_values(state, registry, player_id, "influence")
    spendable = economy.spendable_trade_goods(state, player_id)
    affordable = sum(ready.values()) + spendable >= _PLAGIARIZE_COST
    options = []
    if affordable:
        for tech_id, owners in targets.plagiarize_options(state, registry, player_id).items():
            tech = registry.technologies[tech_id]
            who = ", ".join(_player_label(state, registry, pid) for pid in owners)
            options.append(_option(tech_id, f"{tech.name or tech_id} ({who})"))
    planets = [
        _option(p, f"{_planet_name(registry, p)} ({value} influence)", p)
        for p, value in ready.items()
        if value > 0
    ]
    return [
        _choice("technology", "Technology owned by a neighbor", options),
        _multi(
            "planets", "Planets to exhaust", planets, 0, len(planets),
            f"Spend at least {_PLAGIARIZE_COST} influence.",
        ),
        _number("trade_goods", "Trade goods to spend", 0, spendable),
    ]


@register_effect_inputs("action_cards:seize")
def seize_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = []
    for pid in targets.neighbor_ids(state, registry, player_id):
        for card_id in dict.fromkeys(state.players[pid].relic_fragments):
            card = registry.catalog.get(ComponentCategory.EXPLORATION, card_id)
            name = card.name if card is not None and card.name else card_id
            options.append(
                _option(
                    {"player": pid, "fragment": card_id},
                    f"{name} from {_player_label(state, registry, pid)}",
                    f"{pid}:{card_id}",
                )
            )
    return [_choice("target", "Relic fragment to take from a neighbor", options, merge=True)]


@register_effect_inputs("action_cards:uprising")
def uprising_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = [
        _option(planet, f"{_planet_name(registry, planet)} ({_player_label(state, registry, o)})")
        for planet, o in targets.uprising_targets(state, registry, player_id)
    ]
    return [_choice("planet", "Non-home planet controlled by another player", options)]


@register_effect_inputs("action_cards:probe")
def probe_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = [
        _option(position, f"Frontier token in {_system_label(registry, state.systems[position])}")
        for position in targets.probe_systems(state, registry, player_id)
    ]
    return [_choice("position", "Frontier token to explore", options)]


@register_effect_inputs("action_cards:unstable")
def unstable_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    options = []
    most = 0
    for planet, owner in targets.hazardous_planets(state, registry):
        for system in state.systems.values():
            if planet in system.planet_owners:
                have = count_in_zone(system, planet, owner, "infantry")
                most = max(most, have)
                label = (
                    f"{_planet_name(registry, planet)} ({_player_label(state, registry, owner)}, "
                    f"{have} infantry)"
                )
                options.append(_option(planet, label))
    return [
        _choice("planet", "Hazardous planet", options),
        _number("count", "Infantry to destroy (up to 3)", 0, min(_UNSTABLE_MAX, most)),
    ]


@register_effect_inputs("action_cards:tactical")
def tactical_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = [
        _option(s.position, _system_label(registry, s))
        for s in targets.bombardment_systems(state, registry, player_id)
    ]
    return [_choice("position", "System with your Bombardment units", options)]


@register_effect_inputs("action_cards:meltdown")
def meltdown_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = [
        _option(
            {"planet": planet, "owner": owner},
            f"{unit_name(state, registry, owner, targets.SPACE_DOCK)} on "
            f"{_planet_name(registry, planet)} ({_player_label(state, registry, owner)})",
            f"{planet}:{owner}",
        )
        for planet, owner in targets.meltdown_targets(state, registry, player_id)
    ]
    return [_choice("target", "Space dock to destroy", options, merge=True)]

