"""Technologie „you may" - gracz DECYDUJE ofertą (RULES.md 56), nigdy automatycznie.

Hook ``optional`` tworzy ofertę dla właściciela technologii; odpowiedź (przyjęcie z wyborami albo
odmowa) przychodzi z UI (``POST /offers/accept|decline``). Legalne opcje liczy silnik.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import exhaust, rules_hooks, unit_ops
from src.core import offer_inputs as oi
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.planet_stats import planet_stats
from src.core.rules_hooks import SOURCE_TECHNOLOGY, HookSource, on_event

DACXIVE_ALIAS = "dxa"
BIO_STIMS_ALIAS = "bs"


def _source(alias: str) -> HookSource:
    return HookSource(SOURCE_TECHNOLOGY, alias)


# --- Dacxive Animators -----------------------------------------------------------------------


def _won_ground_combat(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("kind") == "ground" and ctx.get("winner") == player_id


@on_event(
    GameEvent.COMBAT_WON,
    Moment.AFTER,
    _source(DACXIVE_ALIAS),
    optional=True,
    condition=_won_ground_combat,
    covers=f"technologies:{DACXIVE_ALIAS}",
    label="Dacxive Animators: place 1 infantry",
)
def dacxive_animators(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dacxive Animators: po wygranej walce naziemnej możesz postawić 1 piechotę na tej planecie."""
    system = state.systems.get(str(ctx["position"]))
    if system is not None:
        unit_ops.place_units(state, system, str(ctx["planet"]), player_id, "infantry", 1)


# --- Bio-Stims -------------------------------------------------------------------------------


def _bio_stims_targets(state: GameState, registry: Any, player_id: str) -> list[dict[str, Any]]:
    """Wyczerpane planety ze specjalnością technologii i wyczerpane INNE technologie gracza."""
    player = state.players[player_id]
    options: list[dict[str, Any]] = []
    for planet_id in player.exhausted_planets:
        stats = planet_stats(state, registry, planet_id)
        if planet_id in player.controlled_planets and stats is not None and stats.tech_specialties:
            planet = registry.planets.get(planet_id)
            name = planet.name if planet is not None else planet_id
            options.append(oi.option(f"planet:{planet_id}", f"Ready planet {name}"))
    for tech_id in player.exhausted_technologies:
        if tech_id == BIO_STIMS_ALIAS:
            continue
        tech = registry.technologies.get(tech_id)
        options.append(
            oi.option(f"tech:{tech_id}", f"Ready technology {tech.name if tech else tech_id}")
        )
    return options


def _bio_stims_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    registry = rules_hooks.bound_registry()
    player = state.players[player_id]
    return (
        ctx.get("player") == player_id
        and BIO_STIMS_ALIAS not in player.exhausted_technologies
        and registry is not None
        and bool(_bio_stims_targets(state, registry, player_id))
    )


def bio_stims_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Co odświeżyć: planetę ze specjalnością albo inną technologię (liczy silnik)."""
    return [
        oi.choice(
            "target", "Ready one of your exhausted components",
            _bio_stims_targets(state, registry, player_id),
        )
    ]


@on_event(
    GameEvent.TURN,
    Moment.END,
    _source(BIO_STIMS_ALIAS),
    optional=True,
    condition=_bio_stims_ready,
    covers=f"technologies:{BIO_STIMS_ALIAS}",
    label="Bio-Stims: exhaust to ready a planet or technology",
    inputs=bio_stims_inputs,
)
def bio_stims(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Bio-Stims: na końcu tury możesz wyczerpać kartę, by odświeżyć planetę ze specjalnością
    technologii albo inną swoją technologię."""
    target = str(ctx.get("params", {}).get("target", ""))
    kind, _, ident = target.partition(":")
    exhaust.exhaust_technology(state, player_id, BIO_STIMS_ALIAS)
    if kind == "planet":
        exhaust.ready_planets(state, player_id, [ident])
    elif kind == "tech":
        exhaust.ready_technology(state, player_id, ident)
