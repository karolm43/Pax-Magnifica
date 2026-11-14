"""Efekty kart akcji z oknem ACTION: technologie, relikty, planety, ekonomia (RULES.md 53).

Zmiany stanu wyłącznie przez funkcje centralne (RULES.md 43.1a): ``technology`` (badanie, zdobycie,
zwrot), ``economy`` (TG), ``payment`` (wpływ), ``exhaust``, ``relic_fragments``, ``exploration``,
``unit_ops``, ``expeditions.gain_breakthrough``. Teksty kart w docstringach to dosłowne cytaty
z ``assets/data/action_cards``; legalne cele liczy ``card_targets_economy`` (te same listy
pokazuje formularz). Reguły: ``docs/rules/R53.md`` (podsekcja „grupa ekonomia").
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    economy,
    exhaust,
    expeditions,
    exploration,
    exploration_frontier,
    payment,
    relic_fragments,
    research_offer,
    technology,
    triggers,
    unit_ops,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState
from src.core.hooks import card_targets_economy as targets
from src.core.hooks.card_helpers import system_of_planet, system_param
from src.core.planet_stats import resources_of
from src.core.reaction_cards import card_effect_source
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import bound_registry, on_event, register_effect
from src.core.state_grid import grid_from_state
from src.core.unit_ops import UnitCause

_REVEAL = 3  # „Reveal the top 3 cards”
_FOCUSED_COST = 4  # „Spend 4 trade goods”
# Krok „zbadaj” Focused Research: decyzja gracza po zagraniu karty (okno badania).
_FOCUSED_RESEARCH = "f_researched_research"
_FOCUSED_KEY = f"action_cards:{_FOCUSED_RESEARCH}"
_PLAGIARIZE_COST = 5  # „Spend 5 influence”
_UNSTABLE_MAX = 3  # „up to 3 infantry”


def _text(params: Mapping[str, Any], key: str, message: str) -> str:
    value = params.get(key)
    if not isinstance(value, str):
        raise ValueError(message)
    return value


def _str_list(params: Mapping[str, Any], key: str) -> list[str]:
    value = params.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"'{key}' must be a list of ids.")
    return list(value)


@register_effect("action_cards:arch_expedition")
def archaeological_expedition(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Archaeological Expedition: Reveal the top 3 cards of an exploration deck that matches a
    planet you control; gain any relic fragments that you reveal and discard the rest.
    """
    deck = _text(params, "deck", "Choose an exploration deck that matches a planet you control.")
    if deck not in targets.matching_decks(state, registry, player_id):
        raise ValueError("Choose an exploration deck that matches a planet you control ('deck').")
    exploration.reveal_fragments(state, registry, player_id, deck, _REVEAL)


@register_effect("action_cards:brilliance")
def brilliance(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Brilliance: Ready 1 of your planets that has a technology specialty or choose 1 player to
    gain their breakthrough.

    ``mode`` = ``ready_planet`` (+ ``planet``) albo ``breakthrough`` (+ ``player``, może być sam
    grający - C_action_cards). Zdobycie przełomu robi też rzut na The Fracture.
    """
    mode = params.get("mode")
    if mode == "ready_planet":
        planet = _text(params, "planet", "Choose 1 of your planets with a technology specialty.")
        if planet not in targets.specialty_planets_owned(state, registry, player_id):
            raise ValueError("Choose 1 of your planets with a technology specialty ('planet').")
        exhaust.ready_planets(state, player_id, [planet])
    elif mode == "breakthrough":
        target = _text(params, "player", "Choose 1 player to gain their breakthrough.")
        if target not in targets.breakthrough_targets(state, registry):
            raise ValueError(
                "Choose a player whose faction has a breakthrough they have not gained ('player')."
            )
        expeditions.gain_breakthrough(state, registry, grid_from_state(state, registry), target)
    else:
        raise ValueError("Choose 'ready_planet' or 'breakthrough' ('mode').")


@register_effect("action_cards:divert_funding")
def divert_funding(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Divert Funding: Return a non-unit upgrade, non-faction technology that you own to your
    technology deck. Then, research another technology.

    Zwrócona technologia nie liczy się do prerekwizytów i nie może być badana ponownie.
    """
    returned = _text(params, "return_technology", "Choose a technology to return.")
    if returned not in {t.id for t in targets.returnable_techs(state, registry, player_id)}:
        raise ValueError(
            "Choose a non-unit upgrade, non-faction technology you own ('return_technology')."
        )
    tech_id = _text(params, "technology", "Choose a technology to research.")
    if tech_id == returned:
        raise ValueError("You cannot research the technology you just returned.")
    technology.return_technology(state, player_id, returned)
    plan = technology.plan_research(state, registry, player_id, tech_id, _str_list(params, "skips"))
    technology.apply_research(state, player_id, plan)


@register_effect("action_cards:f_researched")
def focused_research(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Focused Research: Spend 4 trade goods to research 1 technology

    Technologię i zapłatę wybiera się PO zagraniu, w oknie badania (``core/research_offer``):
    w tym czasie Doctor Sucaban obniża koszt przed zapłatą (RULES.md 62.3), dlatego kartę wolno
    zagrać także z mniej niż 4 TG, gdy zniżka może pokryć różnicę.
    """
    if not targets.focused_research_options(state, registry, player_id):
        raise ValueError(
            f"You need {_FOCUSED_COST} trade goods and a technology you can research."
        )
    # Efekt trwały = źródło hooka decyzji (gracz „ma” je do czasu odpowiedzi w oknie badania).
    active_effects.add_effect(
        state, _FOCUSED_KEY, Duration.TURN, owner=player_id
    )
    triggers.fire(
        state, GameEvent.ACTION_CARD_PLAYED, Moment.AFTER, subject=player_id,
        ctx={
            "player": player_id, "card": _FOCUSED_RESEARCH,
            **research_offer.offer_ctx(_FOCUSED_COST, trade_goods_only=True),
        },
    )


def _focused_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [
        research_offer.research_input(
            state, registry, decider, _FOCUSED_COST, trade_goods_only=True,
            label="Focused Research: research 1 technology",
        )
    ]


@on_event(
    GameEvent.ACTION_CARD_PLAYED, Moment.AFTER, card_effect_source(_FOCUSED_RESEARCH),
    where={"card": _FOCUSED_RESEARCH}, inputs=_focused_inputs, decide=True,
    label="Focused Research: research 1 technology",
)
def _focused_research_pay(state: GameState, owner_id: str, ctx: Mapping[str, Any]) -> None:
    research_offer.resolve(state, bound_registry(), owner_id, ctx)
    active_effects.remove_by_key(state, _FOCUSED_KEY, owner=owner_id)


@register_effect("action_cards:plagiarize")
def plagiarize(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Plagiarize: Spend 5 influence and choose a non-faction technology owned by 1 of your
    neighbors. Gain that technology.

    Zdobycie ignoruje prerekwizyty (C_action_cards).
    """
    tech_id = _text(params, "technology", "Choose a technology owned by a neighbor.")
    if tech_id not in targets.plagiarize_options(state, registry, player_id):
        raise ValueError(
            "Choose a non-faction technology owned by one of your neighbors ('technology')."
        )
    planets, trade_goods = payment.parse_payment(dict(params))
    paid = payment.validate_payment(state, registry, player_id, "influence", planets, trade_goods)
    if paid < _PLAGIARIZE_COST:
        raise ValueError(f"Spend at least {_PLAGIARIZE_COST} influence (you chose {paid}).")
    payment.apply_payment(state, player_id, planets, trade_goods)
    technology.grant_technology(state, player_id, tech_id)


@register_effect("action_cards:seize")
def seize_artifact(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Seize Artifact: Choose 1 of your neighbors that has 1 or more relic fragments. That player
    must give you 1 relic fragment of your choice.
    """
    target = _text(params, "player", "Choose 1 of your neighbors that has a relic fragment.")
    if target not in targets.neighbor_ids(state, registry, player_id):
        raise ValueError("Choose 1 of your neighbors ('player').")
    fragment = _text(params, "fragment", "Choose 1 relic fragment of that player.")
    relic_fragments.transfer(state, target, player_id, fragment)


@register_effect("action_cards:uprising")
def uprising(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Uprising: Exhaust 1 non-home planet controlled by another player. Then gain trade goods
    equal to its resource value.
    """
    planet = _text(params, "planet", "Choose 1 non-home planet controlled by another player.")
    owners = dict(targets.uprising_targets(state, registry, player_id))
    if planet not in owners:
        raise ValueError(
            "Choose 1 ready, non-home planet controlled by another player ('planet')."
        )
    exhaust.exhaust_planets(state, owners[planet], [planet])
    economy.gain_trade_goods(state, player_id, resources_of(state, registry, planet))


@register_effect("action_cards:probe")
def exploration_probe(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Exploration Probe: Explore a frontier token that is in or adjacent to a system that
    contains 1 or more of your ships.

    Karta z talii frontier otwiera okno eksploracji (jak Dark Energy Tap).
    """
    position = _text(params, "position", "Choose a system with a frontier token.")
    if position not in targets.probe_systems(state, registry, player_id):
        raise ValueError(
            "Choose a frontier token in or adjacent to a system with your ships ('position')."
        )
    exploration_frontier.start_frontier(state, registry, player_id, position)


@register_effect("action_cards:unstable")
def unstable_planet(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Unstable Planet: Choose 1 hazardous planet. Exhaust that planet and destroy up to 3
    infantry on it.

    ⚠ ZAŁOŻENIE: giną piechoty kontrolera planety; ``count`` to wybór gracza (0..3, nie więcej
    niż stoi na planecie).
    """
    planet = _text(params, "planet", "Choose 1 hazardous planet.")
    owners = dict(targets.hazardous_planets(state, registry))
    if planet not in owners:
        raise ValueError("Choose 1 hazardous planet controlled by a player ('planet').")
    count = params.get("count", 0)
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= _UNSTABLE_MAX:
        raise ValueError(f"'count' must be a number from 0 to {_UNSTABLE_MAX}.")
    owner = owners[planet]
    system = system_of_planet(state, planet)
    have = unit_ops.count_in_zone(system, planet, owner, "infantry")
    if count > have:
        raise ValueError(f"There are only {have} infantry on that planet ('count').")
    exhaust.exhaust_planets(state, owner, [planet])
    if count:
        unit_ops.remove_units(state, system, planet, owner, "infantry", count, UnitCause.DESTROYED)


@register_effect("action_cards:tactical")
def tactical_bombardment(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Tactical Bombardment: Choose 1 system that contains 1 or more of your units that have
    BOMBARDMENT. Exhaust each planet controlled by other players in that system.

    Można wybrać system bez gotowych cudzych planet (C_action_cards).
    """
    system = system_param(state, params)
    if system.position not in {
        s.position for s in targets.bombardment_systems(state, registry, player_id)
    }:
        raise ValueError("Choose a system with 1 or more of your units with Bombardment.")
    for planet, owner in system.planet_owners.items():
        if owner != player_id and owner in state.players:
            exhaust.exhaust_planets(state, owner, [planet])


@register_effect("action_cards:meltdown")
def reactor_meltdown(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Reactor Meltdown: Destroy 1 space dock in a non-home system.

    Nie wolno zniszczyć własnego doku ani doku w cudzym systemie domowym (C_action_cards).
    """
    planet = _text(params, "planet", "Choose the planet with a space dock to destroy.")
    owner = _text(params, "owner", "Choose the owner of the space dock.")
    if (planet, owner) not in targets.meltdown_targets(state, registry, player_id):
        raise ValueError("Choose another player's space dock in a non-home system.")
    unit_ops.remove_units(
        state, system_of_planet(state, planet), planet, owner, targets.SPACE_DOCK, 1,
        UnitCause.DESTROYED,
    )
