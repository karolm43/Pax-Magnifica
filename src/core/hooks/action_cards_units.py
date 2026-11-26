"""Efekty kart akcji z oknem ACTION: jednostki na planszy (RULES.md 53).

Postawienie / zniszczenie / zdjęcie jednostek idzie wyłącznie przez ``unit_ops`` (RULES.md 43.1a),
a losowanie przez seedowalny RNG silnika (``dice.next_rng``). Teksty kart w docstringach to cytaty
z ``assets/data/action_cards``. Karty o liczbie celów „1 lub 2” wymagają co najmniej jednego.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import board_reinforcements, economy, unit_ops
from src.core.dice import DIE_SIDES, next_rng, record_table_roll
from src.core.fleet_pool import unit_cost
from src.core.game_state import GameState
from src.core.hooks.card_helpers import (
    other_player_param,
    place_from_reinforcements,
    place_one_or_from_board,
    system_of_planet,
    system_param,
)
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect
from src.core.unit_ops import UnitCause

_PLAGUE_HITS_ON = 6  # „each result of 6 or greater” (karta Plague)
_SHOOTABLE = ("dreadnought", "cruiser", "destroyer")  # cele Lucky Shot


def _has_ships(state: GameState, player_id: str, position: str) -> bool:
    system = state.systems.get(position)
    ships = system.space_units.get(player_id, {}) if system is not None else {}
    return any(count > 0 for count in ships.values())


@register_effect("action_cards:war_effort")
def war_effort(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """War Effort: Place 1 cruiser from your reinforcements in a system that contains 1 or more of
    your ships.

    C_action_cards war-effort/1: with no cruiser left, one is taken from the board (``source``).
    """
    system = system_param(state, params)
    if not _has_ships(state, player_id, system.position):
        raise ValueError("Choose a system that contains 1 or more of your ships ('position').")
    place_one_or_from_board(state, system, "space", player_id, "cruiser", params.get("source"))


@register_effect("action_cards:lucky")
def lucky_shot(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Lucky Shot: Destroy 1 dreadnought, cruiser, or destroyer in a system that contains a planet
    you control.
    """
    system = system_param(state, params)
    if player_id not in system.planet_owners.values():
        raise ValueError("Choose a system that contains a planet you control ('position').")
    owner = other_player_param(state, player_id, params, "owner")
    base_type = params.get("base_type")
    if base_type not in _SHOOTABLE:
        raise ValueError("Choose a dreadnought, cruiser or destroyer ('base_type').")
    if unit_ops.count_in_zone(system, "space", owner, str(base_type)) < 1:
        raise ValueError(f"{owner} has no {base_type} in that system.")
    unit_ops.remove_units(state, system, "space", owner, str(base_type), 1, UnitCause.DESTROYED)


@register_effect("action_cards:cripple")
def cripple_defenses(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Cripple Defenses: Choose 1 planet. Destroy each PDS on that planet."""
    planet = params.get("planet")
    if not isinstance(planet, str):
        raise ValueError("Choose 1 planet ('planet').")
    system = system_of_planet(state, planet)
    for owner in list(system.planet_units.get(planet, {})):
        count = unit_ops.count_in_zone(system, planet, owner, "pds")
        if count:
            unit_ops.remove_units(state, system, planet, owner, "pds", count, UnitCause.DESTROYED)


@register_effect("action_cards:plague")
def plague(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Plague: Choose 1 planet controlled by another player. Roll 1 die for each infantry on that
    planet. For each result of 6 or greater, destroy 1 of those units.
    """
    planet = params.get("planet")
    if not isinstance(planet, str):
        raise ValueError("Choose 1 planet controlled by another player ('planet').")
    system = system_of_planet(state, planet)
    owner = system.planet_owners.get(planet)
    if owner is None or owner == player_id:
        raise ValueError("Choose 1 planet controlled by another player ('planet').")
    infantry = unit_ops.count_in_zone(system, planet, owner, "infantry")
    rng = next_rng(state)
    results = [rng.randint(1, DIE_SIDES) for _ in range(infantry)]
    hits = sum(1 for value in results if value >= _PLAGUE_HITS_ON)
    if results:
        record_table_roll(
            state,
            player_id,
            "plague",
            "Plague",
            results,
            hits_on=_PLAGUE_HITS_ON,
            summary=f"{hits} of {infantry} infantry destroyed.",
        )
    if hits:
        unit_ops.remove_units(state, system, planet, owner, "infantry", hits, UnitCause.DESTROYED)


def refit_shortfall(state: GameState, player_id: str, count: int) -> int:
    """Ilu mechów z ``count`` brakuje w rezerwie (trzeba je zdjąć z planszy)."""
    left = reinforcements_left(state, player_id, "mech")
    return 0 if left is None else max(0, count - max(0, left))


@register_effect("action_cards:refit")
def refit_troops(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Refit Troops: Choose 1 or 2 of your infantry on the game board. Replace each of those
    infantry with mechs.
    """
    planets = params.get("planets")
    if not isinstance(planets, list) or not 1 <= len(planets) <= 2:
        raise ValueError("Choose 1 or 2 of your infantry ('planets': one planet id per infantry).")
    for planet in set(planets):
        if not isinstance(planet, str):
            raise ValueError("'planets' must contain planet ids.")
        system = system_of_planet(state, planet)
        have = unit_ops.count_in_zone(system, planet, player_id, "infantry")
        if have < planets.count(planet):
            raise ValueError(f"You do not have that many infantry on {planet}.")
    # C_action_cards: gdy mechów w rezerwie brak, zdejmuje się mecha z systemu bez własnego
    # żetonu i stawia go (nieuszkodzonego) w miejsce piechoty.
    short = refit_shortfall(state, player_id, len(planets))
    sources = params.get("sources") or []
    if not isinstance(sources, list) or len(sources) < short:
        raise ValueError(
            f"Not enough mechs in reinforcements - choose {short} of your mechs on the board "
            "in systems without your command token ('sources')."
        )
    for source in sources[:short]:
        board_reinforcements.take_from_board(state, player_id, "mech", str(source))
    for planet in planets:
        system = system_of_planet(state, planet)
        unit_ops.take_units(state, system, planet, player_id, "infantry", 1, UnitCause.REMOVED)
        place_from_reinforcements(state, system, planet, player_id, "mech", 1)


@register_effect("action_cards:scuttle")
def scuttle(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Scuttle: Choose 1 or 2 of your non-fighter ships on the game board and return them to your
    reinforcements. Gain trade goods equal to the combined cost of those ships.
    """
    ships = params.get("ships")
    if not isinstance(ships, list) or not 1 <= len(ships) <= 2:
        raise ValueError("Choose 1 or 2 of your non-fighter ships ('ships').")
    chosen: list[tuple[str, str]] = []
    for item in ships:
        position = item.get("position") if isinstance(item, dict) else None
        base_type = item.get("base_type") if isinstance(item, dict) else None
        if not isinstance(position, str) or not isinstance(base_type, str):
            raise ValueError("Each ship needs 'position' and 'base_type'.")
        chosen.append((position, base_type))
    for position, base_type in set(chosen):
        system = state.systems.get(position)
        have = unit_ops.count_in_zone(system, "space", player_id, base_type)
        if base_type == "fighter" or have < chosen.count((position, base_type)):
            raise ValueError(f"You do not have that non-fighter ship ({base_type}) in {position}.")
    gained = 0.0
    for position, base_type in chosen:
        gained += unit_cost(state, registry, player_id, base_type)
        unit_ops.remove_units(
            state, state.systems[position], "space", player_id, base_type, 1, UnitCause.REMOVED
        )
    economy.gain_trade_goods(state, player_id, int(gained))
