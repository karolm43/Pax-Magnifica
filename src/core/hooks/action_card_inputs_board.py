"""Opisy wyborów (formularz) dla kart z ``action_cards_board`` (RULES.md 53).

Format wejść jak w ``action_card_inputs`` (``choice`` / ``multi`` / ``number``). Legalne cele liczą
te same funkcje co walidacja efektu (``action_cards_board.*_targets``), więc UI i silnik się
zgadzają. Brak legalnego celu = pusta lista opcji, co blokuje kartę w ``action_cards.playability``.
"""

from __future__ import annotations

from src.core import board_graph, economy, payment
from src.core.game_state import GameState, SystemState
from src.core.hooks import card_labels
from src.core.hooks.action_card_inputs import (
    Input,
    _choice,
    _multi,
    _number,
    _option,
    _planet_label,
    _player_label,
    _system_label,
    board_source_inputs,
)
from src.core.hooks.action_cards_board import (
    conscription_required,
    conscription_systems,
    exchange_planets,
    ghost_ship_targets,
    jamming_targets,
    mercenary_targets,
    pirate_targets,
    strategy_cards_in_reach,
)
from src.core.offer_inputs import as_payment
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import register_effect_inputs

_PIRATE_CONTRACTS = ("piratecontract1", "piratecontract2", "piratecontract3", "piratecontract4")
_STRATEGIZE_CARDS = ("strategize1", "strategize2", "strategize3", "strategize4")
_PIRATE_FLEET_COST = 3  # „Spend 3 resources”


def _label(state: GameState, registry: StaticDataRegistry, position: str) -> str:
    """Etykieta systemu także wtedy, gdy nie ma jeszcze wpisu w stanie (pusty system na mapie)."""
    system = state.systems.get(position)
    if system is None:
        system = SystemState(position=position, system_id=board_graph.system_id_at(state, position))
    return _system_label(registry, system)


def _position_choice(
    state: GameState,
    registry: StaticDataRegistry,
    positions: list[str],
    label: str,
    hint: str = "",
) -> Input:
    options = [_option(p, _label(state, registry, p)) for p in positions]
    return _choice("position", label, options, hint=hint)


@register_effect_inputs("action_cards:f_conscription")
def conscription_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    eligible = conscription_systems(state, registry, player_id)
    required = conscription_required(state, player_id, len(eligible))
    if not required:
        return []  # R_action_cards: „each” = także zero systemów, bez wyboru
    options = [_option(p, _label(state, registry, p)) for p in eligible]
    # min = max = liczba myśliwców do postawienia.
    hint = "One fighter in each listed system; with fewer fighters, choose where."
    return [_multi("positions", "Systems receiving a fighter", options, required, required, hint)]


@register_effect_inputs("action_cards:ghost_ship")
def ghost_ship_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    targets = ghost_ship_targets(state, registry, player_id)
    hint = "Pick the non-home system with a wormhole that receives the card's effect."
    return [
        _position_choice(state, registry, targets, "Non-home system with a wormhole", hint),
        *board_source_inputs(state, registry, player_id, "destroyer"),
    ]


@register_effect_inputs("action_cards:jamming")
def jamming_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = []
    for position, other in jamming_targets(state, registry, player_id):
        label = (
            f"{_label(state, registry, position)}: token of "
            f"{_player_label(state, registry, other)}"
        )
        value = {"position": position, "player": other}
        options.append(_option(value, label, f"{position}:{other}"))
    hint = "Pick the system and the player whose command token there is affected by the card."
    return [
        _choice("target", "System and player whose token is placed", options, merge=True, hint=hint)
    ]


@register_effect_inputs("action_cards:mercenarycontract")
def mercenary_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    options = []
    for position, planet in mercenary_targets(state, registry, player_id):
        system = state.systems.get(position)
        owner = system.planet_owners.get(planet) if system is not None else None
        suffix = f" · controlled by {_player_label(state, registry, owner)}" if owner else ""
        value = {"position": position, "planet": planet}
        label = f"{_planet_label(state, registry, planet)}{suffix}"
        options.append(_option(value, label, planet))
    hint = "Pick the planet without units that the card targets; it costs 2 trade goods."
    return [
        _choice(
            "target", "Planet without units (costs 2 trade goods)", options, merge=True, hint=hint
        )
    ]


def _pirate_inputs(state: GameState, registry: StaticDataRegistry) -> Input:
    targets = pirate_targets(state, registry)
    hint = "Pick the system without non-neutral ships that the card targets (see the card text)."
    return _position_choice(state, registry, targets, "System without non-neutral ships", hint)


@register_effect_inputs("action_cards:piratecontract1")
def pirate_contract_inputs(
    state: GameState, registry: StaticDataRegistry, _player_id: str
) -> list[Input]:
    return [_pirate_inputs(state, registry)]


for _contract_id in _PIRATE_CONTRACTS[1:]:
    register_effect_inputs(f"action_cards:{_contract_id}")(pirate_contract_inputs)


@register_effect_inputs("action_cards:piratefleet")
def pirate_fleet_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    ready = payment.ready_planet_values(state, registry, player_id, "resources")
    planets = [
        _option(p, _planet_label(state, registry, p, f"spend {value} resources"), p)
        for p, value in ready.items()
        if value > 0
    ]
    spendable = economy.spendable_trade_goods(state, player_id)
    can_pay = sum(ready.values()) + spendable >= _PIRATE_FLEET_COST
    return [
        _pirate_inputs(state, registry),
        # Za mało zasobów = wymagany wybór bez opcji, co blokuje kartę.
        as_payment(
            _multi(
                "planets",
                "Planets to exhaust",
                planets if can_pay else [],
                0 if can_pay else 1,
                len(planets),
                f"Spend at least {_PIRATE_FLEET_COST} resources.",
            ),
            ready, "resources", _PIRATE_FLEET_COST,
        ),
        _number(
            "trade_goods",
            "Trade goods to spend",
            0,
            spendable,
            f"Trade goods you spend towards the {_PIRATE_FLEET_COST} resources.",
        ),
    ]


@register_effect_inputs("action_cards:exchangeprogram")
def exchange_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    mine = exchange_planets(state, player_id)
    options = []
    for partner in (pid for pid in state.players if pid != player_id):
        who = _player_label(state, registry, partner)
        value: dict[str, object] = {"player": partner, "agreed": False}
        label = f"{who}: no agreement, each discards 1 fleet pool token"
        options.append(_option(value, label, f"{partner}:no"))
        for _pos_a, theirs in exchange_planets(state, partner):
            for _pos_b, my_planet in mine:
                value = {
                    "player": partner,
                    "agreed": True,
                    "their_planet": theirs,
                    "my_planet": my_planet,
                }
                label = (
                    f"{who}: agreed, your infantry to {_planet_label(state, registry, theirs)}, "
                    f"theirs to {_planet_label(state, registry, my_planet)}"
                )
                options.append(_option(value, label, f"{partner}:{theirs}:{my_planet}"))
    hint = "Pick the other player and the outcome of your negotiation (swap planets or no deal)."
    return [
        _choice("target", "Player and result of the negotiation", options, merge=True, hint=hint)
    ]


def _strategy_card_options(
    state: GameState, registry: StaticDataRegistry
) -> list[dict[str, object]]:
    """Karty w zasięgu: nazwa + inicjatywa, pełny tekst karty w UI z odnośnika ``ref``."""
    return [
        _option(
            initiative,
            card_labels.describe_strategy_card(registry, initiative),
            ref=("strategy", initiative),
        )
        for initiative in strategy_cards_in_reach(state, registry)
    ]


def _initiative_input(state: GameState, registry: StaticDataRegistry) -> Input:
    options = _strategy_card_options(state, registry)
    hint = (
        "Pick the strategy card the action card applies to - each tile shows its primary and "
        "secondary ability; click the info button for the full card."
    )
    return _choice("initiative", "Readied or unchosen strategy card", options, hint=hint)


@register_effect_inputs("action_cards:overrule")
def overrule_inputs(state: GameState, registry: StaticDataRegistry, _player_id: str) -> list[Input]:
    return [_initiative_input(state, registry)]


@register_effect_inputs("action_cards:strategize1")
def strategize_inputs(
    state: GameState, registry: StaticDataRegistry, _player_id: str
) -> list[Input]:
    return [_initiative_input(state, registry)]


for _strategize_id in _STRATEGIZE_CARDS[1:]:
    register_effect_inputs(f"action_cards:{_strategize_id}")(strategize_inputs)
