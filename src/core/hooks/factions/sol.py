"""Federation of Sol — komplet komponentów frakcji (RULES.md 62.4).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("sol")``, ``units``).
Rulingi: ``docs/rules_tirules/F_sol.md``. Spec Ops II korzysta z mechanizmu Infantry II
(``hooks/technologies_passive.py``, próg z tekstu karty). Gracz decyduje sam (RULES.md 56).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    command_tokens,
    cooperative,
    economy,
    entropic_scar,
    faction_components,
    faction_units,
    leaders,
    payment,
    promissory_play,
    rules_hooks,
    triggers,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState
from src.core.planet_stats import resources_of
from src.core.production import reinforcements_left
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_COMBAT_BONUS_DICE,
    POINT_PRODUCTION_FREE_CARGO,
    POINT_STATUS_COMMAND_TOKENS,
    SOURCE_BREAKTHROUGH,
    SOURCE_EFFECT,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_UNIT,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.unit_ops import UnitCause

FACTION = "sol"
AGENT = "solagent"
COMMANDER = "solcommander"
HERO = "solhero"
FLAGSHIP = "sol_flagship"
MECH = "sol_mech"
MILITARY_SUPPORT = "ms"
BREAKTHROUGH = "solbt"
ORBITAL_DROP = "orbital_drop"

AGENT_DIE = f"leaders:{AGENT}:die"  # +1 kość dla wskazanej siły naziemnej (data: base_type)
# Military Support zagrana w tej turze Sola (F_sol: nie dwa razy w jednym oknie czasowym).
SUPPORT_PLAYED = f"promissory_notes:{MILITARY_SUPPORT}:played"
_DROP_INFANTRY = 2  # „place 2 infantry”
_DEPLOY_COST = 3  # „spend 3 resources to place 1 mech”
_NOTE_INFANTRY = 2  # Military Support: „place 2 infantry”
_COMMANDER_RESOURCES = 12  # „combined total of at least 12 resources”
_GROUND = ("infantry", "mech")
_NONE = "none"

rules_hooks.declare_data_driven("technologies:ac2")  # Advanced Carrier II: same statystyki


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _planet_name(registry: Any, planet: str) -> str:
    return registry.planets[planet].name if planet in registry.planets else planet


def _controlled(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """``(pozycja, planeta)`` planet kontrolowanych przez gracza."""
    return sorted(
        (position, planet)
        for position, system in state.systems.items()
        for planet, owner in system.planet_owners.items()
        if owner == player_id
    )


def _place_infantry(
    state: GameState, player_id: str, position: str, zone: str, wanted: int
) -> None:
    """Stawia do ``wanted`` piechoty z rezerwy (ile jest — rezerwa piechoty ma żetony zastępcze)."""
    left = reinforcements_left(state, player_id, "infantry")
    count = wanted if left is None else min(wanted, left)
    if count > 0:
        unit_ops.place_units(
            state, state.systems[position], zone, player_id, "infantry", count, UnitCause.PLACED
        )


# ------------------------------------------------------------------ Orbital Drop + mech


@faction_components.blocker("ability", ORBITAL_DROP)
def _drop_blocker(state: GameState, _registry: StaticDataRegistry, player_id: str) -> str | None:
    if not command_tokens.can_spend_strategy_token(state, player_id):  # także Scepter
        return "Orbital Drop needs 1 command token in your strategy pool."
    if not _controlled(state, player_id):
        return "You control no planet."
    return None


@register_effect_inputs(f"abilities:{ORBITAL_DROP}")
def drop_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [
        oi.option(f"{position}|{planet}", _planet_name(registry, planet))
        for position, planet in _controlled(state, player_id)
    ]
    return [
        oi.choice("planet", "Planet for 2 infantry", options),
        *command_tokens.strategy_token_input(state, player_id),  # Scepter of Emelpar
    ]


@register_effect(f"abilities:{ORBITAL_DROP}")
def orbital_drop(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Orbital Drop: ACTION: Spend 1 token from your strategy pool to place 2 infantry from your
    reinforcements on 1 planet you control."""
    position, _, planet = str(params.get("planet") or "").partition("|")
    system = state.systems.get(position)
    if system is None or system.planet_owners.get(planet) != player_id:
        raise ValueError("Choose a planet you control.")
    command_tokens.spend_strategy_token(state, player_id, source=params.get("token_source"))
    _place_infantry(state, player_id, position, planet, _DROP_INFANTRY)
    triggers.fire(
        state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "ability": f"abilities:{ORBITAL_DROP}",
             "position": position, "planet": planet},
    )


def _funds(state: GameState, player_id: str) -> int:
    ready = payment.ready_planet_values(state, _registry(), player_id, "resources")
    return sum(ready.values()) + economy.spendable_trade_goods(state, player_id)


def _deploy_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("player") != player_id:
        return False
    if entropic_scar.unit_abilities_blocked(state, str(ctx.get("position"))):
        return False  # DEPLOY nie działa w bliźnie entropicznej (RULES.md 1.5)
    if faction_units.variant_of(state, _registry(), player_id, "mech") != MECH:
        return False
    left = reinforcements_left(state, player_id, "mech")
    return (left is None or left > 0) and _funds(state, player_id) >= _DEPLOY_COST


def deploy_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Płatność 3 zasobów: planety do wyczerpania + TG (jeden widżet płatności w UI)."""
    ready = payment.ready_planet_values(state, registry, player_id, "resources")
    planets = [(p, _planet_name(registry, p), v) for p, v in sorted(ready.items())]
    spendable = economy.spendable_trade_goods(state, player_id)
    where = _planet_name(registry, str(ctx.get("planet") or ""))
    return [
        oi.payment_planets(
            planets, "resources", _DEPLOY_COST,
            hint=f"Place 1 mech on {where}: pay {_DEPLOY_COST} resources.",
        ),
        oi.number("trade_goods", "Trade goods to spend", 0, min(spendable, _DEPLOY_COST)),
    ]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_UNIT, MECH),
    where={"ability": f"abilities:{ORBITAL_DROP}"}, optional=True, condition=_deploy_ready,
    inputs=deploy_inputs, covers=f"units:{MECH}", label="ZS Thunderbolt M2: DEPLOY",
)
def thunderbolt_deploy(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """ZS Thunderbolt M2 — DEPLOY: After you use your Orbital Drop faction ability, you may spend
    3 resources to place 1 mech on that planet."""
    registry = _registry()
    params = ctx.get("params", {})
    planets = [str(p) for p in params.get("planets") or []]
    trade_goods = int(params.get("trade_goods") or 0)
    paid = payment.validate_payment(state, registry, player_id, "resources", planets, trade_goods)
    if paid < _DEPLOY_COST:
        raise ValueError(f"Spend at least {_DEPLOY_COST} resources (you chose {paid}).")
    payment.apply_payment(state, player_id, planets, trade_goods)
    system = state.systems[str(ctx["position"])]
    unit_ops.place_units(state, system, str(ctx["planet"]), player_id, "mech", 1, UnitCause.PLACED)


# ---------------------------------------------------------------------------- Versatile


@register(
    POINT_STATUS_COMMAND_TOKENS, HookSource(SOURCE_FACTION, FACTION), HookKind.MODIFY,
    covers="abilities:versatile",
)
def versatile(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Versatile: When you gain command tokens during the status phase: Gain 1 additional command
    token."""
    return 1


# ------------------------------------------------------------------------- Genesis (flagowiec)


@on_event(
    GameEvent.PHASE, Moment.END, HookSource(SOURCE_UNIT, FLAGSHIP), where={"phase": "status"},
    covers=f"units:{FLAGSHIP}", label="Genesis: infantry",
)
def genesis(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Genesis: At the end of the status phase, place 1 infantry from your reinforcements in this
    system's space area (obowiązkowo — F_sol)."""
    for position in faction_units.positions_with(state, _registry(), player_id, FLAGSHIP):
        system = state.systems[position]
        if system.space_units.get(player_id, {}).get("flagship", 0) > 0:
            _place_infantry(state, player_id, position, "space", 1)


# ---------------------------------------------------------------------- Evelyn DeLouis


def _ground_forces(state: GameState, ctx: Mapping[str, Any]) -> list[tuple[str, str, int]]:
    """``(gracz, typ, liczba)`` sił naziemnych na planecie walki."""
    system = state.systems.get(str(ctx.get("position")))
    planet = str(ctx.get("planet") or "")
    if system is None or not planet:
        return []
    found: list[tuple[str, str, int]] = []
    for owner, units in sorted(system.planet_units.get(planet, {}).items()):
        for base_type in _GROUND:
            if units.get(base_type, 0) > 0:
                found.append((owner, base_type, units[base_type]))
    return found


def _agent_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("kind") == "ground"
        and leaders.is_ready(state, _registry(), player_id, AGENT)
        and bool(_ground_forces(state, ctx))
    )


def agent_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    forces = sorted(_ground_forces(state, ctx), key=lambda f: (f[0] != player_id, f[0], f[1]))
    for owner, base_type, count in forces:
        player = state.players.get(owner)
        if player is None:
            continue
        faction = registry.factions.get(player.faction or "")
        who = faction.name if faction is not None else owner
        meta = oi.unit_meta(base_type, owner, player.faction, player.color, count)
        options.append(oi.option(
            f"{owner}|{base_type}", f"{unit_name(state, registry, owner, base_type)} - {who}",
            meta=meta,
        ))
    return [oi.choice("unit", "Ground force that rolls 1 additional die", options, always=True)]


# Cooperative agent (RULES.md 54.15): helps "that player" - requested, not pushed.
cooperative.register_pull(f"leaders:{AGENT}", cooperative.combatants)


@on_event(
    GameEvent.COMBAT_ROUND, Moment.START, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_agent_ready, inputs=agent_inputs,
    covers=f"leaders:{AGENT}", label="Evelyn DeLouis",
)
def evelyn_delouis(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Evelyn DeLouis: At the start of a ground combat round: You may exhaust this card to choose 1
    ground force in the active system: that ground force rolls 1 additional die during this combat
    round."""
    owner, _, base_type = str(ctx.get("params", {}).get("unit") or "").partition("|")
    if owner not in state.players or base_type not in _GROUND:
        raise ValueError("Choose a ground force in this combat.")
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT)
    active_effects.add_effect(
        state, AGENT_DIE, Duration.COMBAT_ROUND, owner=owner, data={"base_type": base_type}
    )


@register(POINT_COMBAT_BONUS_DICE, HookSource(SOURCE_EFFECT, AGENT_DIE), HookKind.MODIFY)
def evelyn_die(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    if ctx.get("kind") != "ground":
        return 0
    return sum(
        1
        for e in active_effects.effects_for(state, player_id, AGENT_DIE)
        if e.data.get("base_type") == ctx.get("base_type")
    )


# ----------------------------------------------------------------------- Claire Gibson


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Control planets that have a combined total of at least 12 resources."""
    total = sum(resources_of(state, registry, p) for _, p in _controlled(state, player_id))
    return total >= _COMMANDER_RESOURCES


def _defends_own_planet(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("kind") != "ground" or ctx.get("defender") != player_id:
        return False
    system = state.systems.get(str(ctx.get("position")))
    planet = str(ctx.get("planet") or "")
    if system is None or system.planet_owners.get(planet) != player_id:
        return False
    left = reinforcements_left(state, player_id, "infantry")
    return left is None or left > 0


@on_event(
    GameEvent.COMBAT, Moment.START, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_defends_own_planet, covers=f"leaders:{COMMANDER}",
    label="Claire Gibson: place 1 infantry",
)
def claire_gibson(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Claire Gibson: At the start of a ground combat on a planet you control: You may place 1
    infantry from your reinforcements on that planet."""
    _place_infantry(state, player_id, str(ctx["position"]), str(ctx["planet"]), 1)


# ------------------------------------------------------------ Jace X — Helio Command Array


@register_effect(f"leaders:{HERO}")
def helio_command_array(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Jace X, 4th Air Legion — Helio Command Array: ACTION: Remove each of your command tokens
    from the game board and return them to your reinforcements. Then, purge this card."""
    for system in state.systems.values():
        while player_id in system.command_tokens:
            command_tokens.remove_from_board(state, system, player_id)


# --------------------------------------------------------------------- Military Support


@promissory_play.condition(MILITARY_SUPPORT)
def _support_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> str | None:
    if window.subject not in state.players:
        return "Military Support is played at the start of the Sol player's turn."
    if active_effects.has_effect(state, player_id, SUPPORT_PLAYED):
        return "Military Support was already played at the start of this turn."
    return None


@register_effect_inputs(f"promissory_notes:{MILITARY_SUPPORT}")
def support_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [oi.option(_NONE, "Do not place")] + [
        oi.option(f"{position}|{planet}", _planet_name(registry, planet))
        for position, planet in _controlled(state, player_id)
    ]
    return [oi.choice("planet", "Place 2 infantry on", options)]


@register_effect(f"promissory_notes:{MILITARY_SUPPORT}")
def military_support(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Military Support: At the start of the Sol player's turn: Remove 1 token from the Sol
    player's strategy pool, if able, and return it to their reinforcements. Then, you may place 2
    infantry from your reinforcements on any planet you control. Then, return this card.

    Odzyskana transakcją w tym samym oknie nie zagra się drugi raz (F_sol) - znacznik do końca
    tury Sola (``Duration.TURN``).
    """
    active_effects.add_effect(state, SUPPORT_PLAYED, Duration.TURN)  # karta, nie gracz
    owner = params.get("__owner")
    if isinstance(owner, str) and owner in state.players and state.players[owner].strategic_cc > 0:
        command_tokens.spend_to_reinforcements(state, owner, "strategic")
    choice = str(params.get("planet") or _NONE)
    if choice == _NONE:
        return
    position, _, planet = choice.partition("|")
    system = state.systems.get(position)
    if system is None or system.planet_owners.get(planet) != player_id:
        raise ValueError("Choose a planet you control.")
    _place_infantry(state, player_id, position, planet, _NOTE_INFANTRY)


# --------------------------------------------------------------- Bellum Gloriosum (BT)


@register(
    POINT_PRODUCTION_FREE_CARGO, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH), HookKind.PERMIT,
    covers=f"breakthroughs:{BREAKTHROUGH}",
)
def bellum_gloriosum(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Bellum Gloriosum: When you produce a ship that has capacity, you may also produce any
    combination of ground forces or fighters up to that ship's capacity; they do not count against
    your PRODUCTION limit."""
    return True
