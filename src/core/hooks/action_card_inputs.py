"""Opisy wyborów gracza (formularz w UI) dla kart akcji z efektem (RULES.md 53).

Każda karta wymagająca decyzji rejestruje funkcję ``(state, registry, player_id) -> [input]``
przez ``rules_hooks.register_effect_inputs``. Frontend NIE zna kart - renderuje formularz
z tych opisów, a legalne opcje (własne planety, systemy z żetonem, cele...) liczy silnik
na bieżącym stanie.

Format wejścia (``dict``), pole ``kind``:
* ``choice`` - jedna opcja z ``options``; ``merge=True`` wkleja słownik opcji do parametrów;
* ``multi``  - ``min``..``max`` opcji (każda z unikalnym ``id``, wartość może się powtarzać);
* ``number`` - liczba całkowita ``min``..``max``.
Opcja: ``{"id": str, "value": Any, "label": str, "meta"?: {"ref": {"kind", "id"}}}`` - ``ref``
wskazuje komponent gry (karta strategii, relikt...), którego pełny opis UI pokazuje przy opcji.
Klucz ``key`` = nazwa parametru efektu.
"""

from __future__ import annotations

from typing import Any

from src.core import economy, payment, planet_stats, secret_objectives
from src.core.components import ComponentCategory
from src.core.fleet_pool import unit_name
from src.core.game_state import GameState, SystemState
from src.core.hooks import card_labels
from src.core.hooks.card_helpers import controlled
from src.core.offer_inputs import as_payment, unit_at
from src.core.offer_inputs import option as as_option
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect_inputs
from src.core.unit_ops import count_in_zone

Input = dict[str, Any]

_SHOOTABLE = ("dreadnought", "cruiser", "destroyer")
_MAX_PICKS = 2  # „1 or 2” (Refit Troops, Scuttle)


def _option(
    value: Any,
    label: str,
    option_id: str | None = None,
    *,
    ref: tuple[str, str | int] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Opcja formularza; ``ref`` = komponent gry, którego dotyczy (``offer_inputs.option``),
    ``meta`` = dane graficzne (np. ``offer_inputs.unit_at``: jednostka w miejscu)."""
    return as_option(value, label, option_id, meta=meta, ref=ref)


def _choice(
    key: str,
    label: str,
    options: list[dict[str, Any]],
    *,
    merge: bool = False,
    hint: str = "",
    plain_list: bool = False,
) -> Input:
    field: Input = {
        "key": key,
        "kind": "choice",
        "label": label,
        "options": options,
        "merge": merge,
        "hint": hint,
    }
    if plain_list:
        # Technologie do ODDANIA: zwykła lista kafelków z opisem (nie okno drzewa badania).
        field["display"] = "list"
    return field


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


def _number(
    key: str, label: str, minimum: int, maximum: int, hint: str = "", *, auto: int | None = None
) -> Input:
    """Pole liczbowe formularza karty; ``auto`` = wartość opcji „Auto” (``offer_inputs.number``)."""
    item: Input = {
        "key": key,
        "kind": "number",
        "label": label,
        "min": minimum,
        "max": maximum,
        "hint": hint,
    }
    if auto is not None:
        item["auto"] = max(minimum, min(maximum, auto))
    return item


def _planet_name(registry: StaticDataRegistry, planet_id: str) -> str:
    planet = registry.planets.get(planet_id)
    return planet.name if planet is not None else planet_id


def _planet_label(
    state: GameState, registry: StaticDataRegistry, planet_id: str, effect: str = ""
) -> str:
    """Planeta z zasobami/wpływem/cechami/systemem (+ ``effect`` = „→ skutek”)."""
    return card_labels.describe_planet(state, registry, planet_id, effect=effect)


def _system_label(registry: StaticDataRegistry, system: SystemState) -> str:
    """System: pozycja + planety ze statystykami (bazowymi)."""
    return card_labels.describe_system_state(registry, system)


def _player_label(state: GameState, registry: StaticDataRegistry, player_id: str) -> str:
    return card_labels.describe_player(state, registry, player_id)


def _others(state: GameState, player_id: str) -> list[str]:
    return [pid for pid in state.players if pid != player_id]


def _mining_effect(state: GameState, registry: StaticDataRegistry, planet: str) -> str:
    """Skutek Mining Initiative dla planety (zasoby = tyle trade goods)."""
    value = planet_stats.resources_of(state, registry, planet)
    return f"+{value} trade good{'' if value == 1 else 's'}"


@register_effect_inputs("action_cards:mining_initiative")
def mining_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = [
        _option(p, _planet_label(state, registry, p, _mining_effect(state, registry, p)))
        for p in controlled(state, player_id)
    ]
    hint = (
        "Pick the planet whose resource value you gain as trade goods "
        "(the number after the arrow)."
    )
    return [_choice("planet", "Planet you control", options, hint=hint)]


@register_effect_inputs("action_cards:f_deployment")
def deployment_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    options = [_option(p, _planet_label(state, registry, p)) for p in controlled(state, player_id)]
    return [_choice("planet", "Planet you control", options)]


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
        _option(
            pid,
            f"{_player_label(state, registry, pid)} · "
            f"{state.players[pid].tactical_cc} token(s) in the tactic pool",
        )
        for pid in _others(state, player_id)
        if state.players[pid].tactical_cc > 0
    ]
    return [
        _choice(
            "player",
            "Player (needs a token in the tactic pool)",
            options,
            hint="Pick the player whose tactic-pool command token the card affects.",
        )
    ]


@register_effect_inputs("action_cards:spy")
def spy_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = [
        _option(
            pid,
            f"{_player_label(state, registry, pid)} · "
            f"{len(state.players[pid].private.action_cards)} action card(s) in hand",
        )
        for pid in _others(state, player_id)
        if state.players[pid].private.action_cards
    ]
    return [
        _choice(
            "player",
            "Player who has action cards",
            options,
            hint="Pick the player whose action cards the card targets.",
        )
    ]


@register_effect_inputs("action_cards:repeal")
def repeal_inputs(state: GameState, registry: StaticDataRegistry, _player_id: str) -> list[Input]:
    options = []
    for law in sorted(state.decks.agenda_laws):
        card = registry.catalog.get(ComponentCategory.AGENDA, law)
        options.append(_option(law, card.name if card is not None and card.name else law))
    return [
        _choice(
            "law",
            "Law in play",
            options,
            hint="Pick the law currently in play that the card affects (see the card text).",
        )
    ]


@register_effect_inputs("action_cards:impersonation")
def impersonation_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    ready = payment.ready_planet_values(state, registry, player_id, "influence")
    planets = [
        _option(p, _planet_label(state, registry, p, f"spend {value} influence"), p)
        for p, value in ready.items()
        if value > 0
    ]
    inputs = [
        as_payment(
            _multi(
                "planets",
                "Planets to exhaust",
                planets,
                0,
                len(planets),
                "Exhaust ready planets (and/or trade goods) to pay at least 3 influence.",
            ),
            ready, "influence", 3,
        ),
        _number(
            "trade_goods",
            "Trade goods to spend",
            0,
            economy.spendable_trade_goods(state, player_id),
            "Trade goods you spend towards the 3 influence payment.",
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
    options = [_option(p, _planet_label(state, registry, p)) for p in sorted(planets)]
    return [
        _choice(
            "planet",
            "Planet with a PDS",
            options,
            hint="Pick the planet with a PDS that the card targets (see the card text).",
        )
    ]


@register_effect_inputs("action_cards:plague")
def plague_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = []
    for system in state.systems.values():
        for planet, owner in system.planet_owners.items():
            if owner != player_id and count_in_zone(system, planet, owner, "infantry") > 0:
                have = count_in_zone(system, planet, owner, "infantry")
                label = (
                    f"{_planet_label(state, registry, planet)} · "
                    f"{_player_label(state, registry, owner)} · {have} infantry"
                )
                options.append(_option(planet, label))
    return [
        _choice(
            "planet",
            "Planet controlled by another player",
            options,
            hint="Pick the planet controlled by another player that the card targets "
            "(owner and infantry count are shown).",
        )
    ]


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
                    meta = unit_at(state, owner, base_type, position=system.position)
                    options.append(_option(
                        target, label, f"{system.position}:{owner}:{base_type}", meta=meta
                    ))
    return [_choice("target", "Ship to destroy", options, merge=True)]


@register_effect_inputs("action_cards:refit")
def refit_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = []
    for planet in controlled(state, player_id):
        for system in state.systems.values():
            have = count_in_zone(system, planet, player_id, "infantry")
            for index in range(have):
                label = (
                    f"{unit_name(state, registry, player_id, 'infantry')} "
                    f"on {_planet_label(state, registry, planet)}"
                )
                meta = unit_at(state, player_id, "infantry", planet=planet)
                options.append(_option(planet, label, f"{planet}#{index}", meta=meta))
    return [
        _multi(
            "planets",
            "Infantry to replace with mechs",
            options,
            1,
            _MAX_PICKS,
            "Pick 1 or 2 of your infantry; each is replaced with a mech on the same planet.",
        )
    ]


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
                meta = unit_at(state, player_id, base_type, position=system.position)
                options.append(
                    _option(value, label, f"{system.position}:{base_type}#{index}", meta=meta)
                )
    return [_multi("ships", "Ships to return (not fighters)", options, 1, _MAX_PICKS)]
