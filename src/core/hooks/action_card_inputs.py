"""Opisy wyborów gracza (formularz w UI) dla kart akcji z efektem (RULES.md 53).

Każda karta wymagająca decyzji rejestruje funkcję ``(state, registry, player_id) -> [input]``
przez ``rules_hooks.register_effect_inputs``. Frontend NIE zna kart - renderuje formularz
z tych opisów, a legalne opcje (własne planety, systemy z żetonem, cele...) liczy silnik
na bieżącym stanie.

Format wejścia (``dict``), pole ``kind``:
* ``choice`` - jedna opcja z ``options``; ``merge=True`` wkleja słownik opcji do parametrów;
* ``multi``  - ``min``..``max`` opcji (każda z unikalnym ``id``, wartość może się powtarzać);
* ``number`` - liczba całkowita ``min``..``max``.
Opcja: ``{"id": str, "value": Any, "label": str}``. Klucz ``key`` = nazwa parametru efektu.
"""

from __future__ import annotations

from typing import Any

from src.core import economy, payment, secret_objectives
from src.core.components import ComponentCategory
from src.core.fleet_pool import unit_name
from src.core.game_state import GameState, SystemState
from src.core.hooks.card_helpers import controlled
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect_inputs
from src.core.unit_ops import count_in_zone

Input = dict[str, Any]

_SHOOTABLE = ("dreadnought", "cruiser", "destroyer")
_MAX_PICKS = 2  # „1 or 2” (Refit Troops, Scuttle)


def _option(value: Any, label: str, option_id: str | None = None) -> dict[str, Any]:
    return {"id": str(value) if option_id is None else option_id, "value": value, "label": label}


def _choice(
    key: str, label: str, options: list[dict[str, Any]], *, merge: bool = False, hint: str = ""
) -> Input:
    return {
        "key": key,
        "kind": "choice",
        "label": label,
        "options": options,
        "merge": merge,
        "hint": hint,
    }


def _multi(
    key: str, label: str, options: list[dict[str, Any]], minimum: int, maximum: int, hint: str = ""
) -> Input:
    return {
        "key": key,
        "kind": "multi",
        "label": label,
        "options": options,
        "min": minimum,
        "max": maximum,
        "hint": hint,
    }


def _number(key: str, label: str, minimum: int, maximum: int, hint: str = "") -> Input:
    return {
        "key": key,
        "kind": "number",
        "label": label,
        "min": minimum,
        "max": maximum,
        "hint": hint,
    }


def _planet_name(registry: StaticDataRegistry, planet_id: str) -> str:
    planet = registry.planets.get(planet_id)
    return planet.name if planet is not None else planet_id


def _system_label(registry: StaticDataRegistry, system: SystemState) -> str:
    definition = registry.systems.get(system.system_id)
    names = [_planet_name(registry, p) for p in (definition.planets if definition else [])]
    return f"{', '.join(names)} ({system.position})" if names else f"Tile {system.position}"


def _player_label(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    player = state.players[player_id]
    faction = registry.factions.get(player.faction) if player.faction else None
    name = faction.name if faction is not None else player_id
    return f"{name} ({player.color})" if player.color else name


def _others(state: GameState, player_id: str) -> list[str]:
    return [pid for pid in state.players if pid != player_id]


def _own_planets(state: GameState, registry: StaticDataRegistry, player_id: str) -> Input:
    options = [_option(p, _planet_name(registry, p)) for p in controlled(state, player_id)]
    return _choice("planet", "Planet you control", options)


@register_effect_inputs("action_cards:mining_initiative")
def mining_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    return [_own_planets(state, registry, player_id)]


@register_effect_inputs("action_cards:f_deployment")
def deployment_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    return [_own_planets(state, registry, player_id)]


@register_effect_inputs("action_cards:unexpected")
def unexpected_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    systems = [s for s in state.systems.values() if player_id in s.command_tokens]
    options = [_option(s.position, _system_label(registry, s)) for s in systems]
    return [_choice("position", "System with your command token", options)]


@register_effect_inputs("action_cards:war_effort")
def war_effort_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    systems = [
        s
        for s in state.systems.values()
        if any(n > 0 for n in s.space_units.get(player_id, {}).values())
    ]
    options = [_option(s.position, _system_label(registry, s)) for s in systems]
    return [_choice("position", "System with your ships", options)]


@register_effect_inputs("action_cards:insub")
def insubordination_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    options = [
        _option(pid, _player_label(state, registry, pid))
        for pid in _others(state, player_id)
        if state.players[pid].tactical_cc > 0
    ]
    return [_choice("player", "Player (needs a token in the tactic pool)", options)]


@register_effect_inputs("action_cards:spy")
def spy_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = [
        _option(pid, _player_label(state, registry, pid))
        for pid in _others(state, player_id)
        if state.players[pid].private.action_cards
    ]
    return [_choice("player", "Player who has action cards", options)]


@register_effect_inputs("action_cards:repeal")
def repeal_inputs(state: GameState, registry: StaticDataRegistry, _player_id: str) -> list[Input]:
    options = []
    for law in sorted(state.decks.agenda_laws):
        card = registry.catalog.get(ComponentCategory.AGENDA, law)
        options.append(_option(law, card.name if card is not None and card.name else law))
    return [_choice("law", "Law in play", options)]


@register_effect_inputs("action_cards:impersonation")
def impersonation_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    ready = payment.ready_planet_values(state, registry, player_id, "influence")
    planets = [
        _option(p, f"{_planet_name(registry, p)} ({value} influence)", p)
        for p, value in ready.items()
        if value > 0
    ]
    inputs = [
        _multi(
            "planets", "Planets to exhaust", planets, 0, len(planets), "Spend at least 3 influence."
        ),
        _number(
            "trade_goods",
            "Trade goods to spend",
            0,
            economy.spendable_trade_goods(state, player_id),
        ),
    ]
    if secret_objectives.over_limit_after_draw(state, player_id):
        hand = state.players[player_id].private.secret_objectives
        options = [_option(secret_objectives.DRAWN, "The card you just drew")]
        options += [_option(card, card) for card in hand]
        inputs.append(
            _choice("return", "Return an unscored secret objective (over the limit)", options)
        )
    return inputs


@register_effect_inputs("action_cards:cripple")
def cripple_inputs(state: GameState, registry: StaticDataRegistry, _player_id: str) -> list[Input]:
    planets = {
        planet
        for system in state.systems.values()
        for planet, by_player in system.planet_units.items()
        if any(units.get("pds", 0) > 0 for units in by_player.values())
    }
    options = [_option(p, _planet_name(registry, p)) for p in sorted(planets)]
    return [_choice("planet", "Planet with a PDS", options)]


@register_effect_inputs("action_cards:plague")
def plague_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = []
    for system in state.systems.values():
        for planet, owner in system.planet_owners.items():
            if owner != player_id and count_in_zone(system, planet, owner, "infantry") > 0:
                label = (
                    f"{_planet_name(registry, planet)} ({_player_label(state, registry, owner)})"
                )
                options.append(_option(planet, label))
    return [_choice("planet", "Planet controlled by another player", options)]


@register_effect_inputs("action_cards:lucky")
def lucky_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = []
    for system in state.systems.values():
        if player_id not in system.planet_owners.values():
            continue
        for owner in _others(state, player_id):
            for base_type in _SHOOTABLE:
                if count_in_zone(system, "space", owner, base_type) > 0:
                    target = {"position": system.position, "owner": owner, "base_type": base_type}
                    ship = unit_name(state, registry, owner, base_type)
                    label = (
                        f"{ship} of {_player_label(state, registry, owner)} "
                        f"in {_system_label(registry, system)}"
                    )
                    options.append(_option(target, label, f"{system.position}:{owner}:{base_type}"))
    return [_choice("target", "Ship to destroy", options, merge=True)]


@register_effect_inputs("action_cards:refit")
def refit_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = []
    for planet in controlled(state, player_id):
        for system in state.systems.values():
            have = count_in_zone(system, planet, player_id, "infantry")
            for index in range(have):
                label = f"{_planet_name(registry, planet)}: infantry {index + 1}"
                options.append(_option(planet, label, f"{planet}#{index}"))
    return [_multi("planets", "Infantry to replace with mechs", options, 1, _MAX_PICKS)]


@register_effect_inputs("action_cards:scuttle")
def scuttle_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = []
    for system in state.systems.values():
        for base_type, count in sorted(system.space_units.get(player_id, {}).items()):
            if base_type == "fighter":
                continue
            for index in range(count):
                value = {"position": system.position, "base_type": base_type}
                label = (
                    f"{unit_name(state, registry, player_id, base_type)} "
                    f"in {_system_label(registry, system)}"
                )
                options.append(_option(value, label, f"{system.position}:{base_type}#{index}"))
    return [_multi("ships", "Ships to return (not fighters)", options, 1, _MAX_PICKS)]
