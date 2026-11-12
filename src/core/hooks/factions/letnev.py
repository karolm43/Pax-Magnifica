"""Barony of Letnev — komplet komponentów frakcji (RULES.md 62.2).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("letnev")``, ``units``).
Rulingi: ``docs/rules_tirules/F_letnev.md``. Gracz decyduje sam (RULES.md 56).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    battle,
    economy,
    faction_components,
    faction_units,
    leaders,
    payment,
    promissory_play,
    rules_hooks,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.damage import set_damaged
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import CombatStep, GameState, WindowType
from src.core.production import reinforcements_left
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_COMBAT_BONUS_DICE,
    POINT_COMBAT_SINGLE_UNIT_BONUS,
    POINT_COMBAT_SUSTAIN_CANCELS,
    POINT_FLEET_POOL_CAPACITY,
    POINT_FLEET_POOL_UNLIMITED,
    POINT_MOVEMENT_MATCH_HIGHEST,
    POINT_SPACE_CANNON_DEFENSE_IMMUNE,
    POINT_STRIPS_PLANETARY_SHIELD,
    SOURCE_BREAKTHROUGH,
    SOURCE_EFFECT,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_TECHNOLOGY,
    SOURCE_UNIT,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

FACTION = "letnev"
AGENT = "letnevagent"
COMMANDER = "letnevcommander"
HERO = "letnevhero"
FLAGSHIP = "letnev_flagship"
MECH = "letnev_mech"
WAR_FUNDING = "war_funding"
BREAKTHROUGH = "letnevbt"

MUNITIONS_PAID = "abilities:munitions"  # 2 TG zapłacone w tej rundzie walki
AGENT_DIE = f"leaders:{AGENT}:die"  # +1 kość dla wskazanego statku (data: base_type)
HERO_EFFECT = f"leaders:{HERO}"  # bez limitu floty do końca rundy gry
GRAVLEASH = f"breakthroughs:{BREAKTHROUGH}:ship"  # data: base_type
_ARMADA_BONUS = 2  # „2 more than the number of tokens in your fleet pool”
_MUNITIONS_COST = 2  # „spend 2 trade goods”
_DEPLOY_COST = 2  # „spend 2 resources”
_COMMANDER_SHIPS = 5  # „Have 5 non-fighter ships in 1 system.”
_YES = "yes"
_NO = "no"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _participant(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return player_id in (ctx.get("attacker"), ctx.get("defender"))


def _opponent_of(state: GameState, player_id: str) -> str | None:
    combat = state.active_combat
    if combat is None or player_id not in (combat.attacker, combat.defender):
        return None
    return combat.defender if combat.attacker == player_id else combat.attacker


def _dice_window_open(state: GameState) -> bool:
    """Rzuty rundy walki leżą na stole, nikt nie przypisał strat (jak narzędzia reliktów)."""
    combat = state.active_combat
    window = state.pending_window
    return (
        combat is not None
        and combat.step is CombatStep.ASSIGN
        and window is not None
        and window.window_type is WindowType.COMBAT_ASSIGN_HITS
        and window.cursor == 0
        and not combat.afb_assign
        and bool(combat.log)
        and combat.log[-1].get("phase") == "COMBAT"
        and not combat.log[-1].get("losses")
    )


def _dice_options(state: GameState, owner: str) -> list[dict[str, Any]]:
    combat = state.active_combat
    rolls = combat.rolls.get(owner, []) if combat is not None else []
    options: list[dict[str, Any]] = []
    for index, entry in enumerate(rolls):
        for die, value in enumerate(entry["dice"]):
            meta = oi.die_meta(value, int(entry.get("hitsOn", 0)), str(entry.get("baseType", "")))
            options.append(oi.option(f"{index}:{die}", f"{entry['name']}: {value}", meta=meta))
    return options


def _chosen(values: Any) -> set[tuple[int, int]]:
    chosen: set[tuple[int, int]] = set()
    for token in values or []:
        left, right = str(token).split(":")
        chosen.add((int(left), int(right)))
    return chosen


# ------------------------------------------------------------------------------------- Armada


@register(
    POINT_FLEET_POOL_CAPACITY, HookSource(SOURCE_FACTION, FACTION), HookKind.MODIFY,
    covers="abilities:armada",
)
def armada(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Armada: The maximum number of non-fighter ships you can have in each system is equal to 2
    more than the number of tokens in your fleet pool."""
    return _ARMADA_BONUS


# -------------------------------------------------------------------------- Munitions Reserves


def _munitions_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("kind") == "space"
        and _participant(state, player_id, ctx)
        and economy.spendable_trade_goods(state, player_id) >= _MUNITIONS_COST
        and not active_effects.has_effect(state, player_id, MUNITIONS_PAID)
    )


@on_event(
    GameEvent.COMBAT_ROUND, Moment.START, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_munitions_ready, covers="abilities:munitions",
    label="Munitions Reserves: spend 2 TG to reroll this round",
)
def munitions_pay(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Munitions Reserves: At the start of each round of space combat: You may spend 2 trade goods
    to re-roll any number of your dice during that combat round."""
    economy.spend_as_trade_goods(state, player_id, _MUNITIONS_COST)
    active_effects.add_effect(state, MUNITIONS_PAID, Duration.COMBAT_ROUND, owner=player_id)


@faction_components.window_use("ability", "munitions")
def _munitions_window(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> str | None:
    if not active_effects.has_effect(state, player_id, MUNITIONS_PAID):
        return "Pay 2 trade goods at the start of the space combat round first."
    if not _dice_window_open(state):
        return "Reroll after the combat roll, before hits are assigned."
    return None


@register_effect_inputs("abilities:munitions")
def munitions_inputs(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = _dice_options(state, player_id)
    return [oi.multi("dice", "Dice to reroll", options, 1, max(1, len(options)))]


@register_effect("abilities:munitions")
def munitions_reroll(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    battle.reroll_combat_dice(
        state, player_id, _chosen(params.get("dice")), "munitions", "Munitions Reserves"
    )
    active_effects.remove_by_key(state, MUNITIONS_PAID, owner=player_id)  # raz na rundę


# ------------------------------------------------------------------- technologie frakcyjne


@register(
    POINT_COMBAT_SUSTAIN_CANCELS, HookSource(SOURCE_TECHNOLOGY, "nes"), HookKind.MODIFY,
    covers="technologies:nes",
)
def non_euclidean_shielding(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Non-Euclidean Shielding: When 1 of your units uses SUSTAIN DAMAGE, cancel 2 hits instead
    of 1."""
    return 1


@register(
    POINT_SPACE_CANNON_DEFENSE_IMMUNE, HookSource(SOURCE_TECHNOLOGY, "l4"), HookKind.PERMIT,
    covers="technologies:l4",
)
def l4_disruptors(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """L4 Disruptors: During an invasion, units cannot use SPACE CANNON against your units."""
    return True


# ---------------------------------------------------------------------------- Arc Secundus


@register(
    POINT_STRIPS_PLANETARY_SHIELD, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.PERMIT,
    covers=f"units:{FLAGSHIP}",
)
def arc_secundus_shields(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Arc Secundus: Other player's units in this system lose PLANETARY SHIELD."""
    position = str(ctx.get("position"))
    return faction_units.has_unit_in(state, _registry(), player_id, FLAGSHIP, position)


def _flagship_in_combat(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("kind") != "space" or not _participant(state, player_id, ctx):
        return False
    position = str(ctx.get("position"))
    return faction_units.has_unit_in(state, _registry(), player_id, FLAGSHIP, position)


@on_event(
    GameEvent.COMBAT_ROUND, Moment.START, HookSource(SOURCE_UNIT, FLAGSHIP),
    condition=_flagship_in_combat, label="Arc Secundus: repair",
)
def arc_secundus_repair(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Arc Secundus: At the start of each space combat round, repair this ship."""
    set_damaged(state.systems[str(ctx["position"])], "space", player_id, "flagship", 0)


# --------------------------------------------------------------------------- Dunlain Reaper


def _deploy_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("kind") != "ground" or not _participant(state, player_id, ctx):
        return False
    if faction_units.variant_of(state, _registry(), player_id, "mech") != MECH:
        return False
    system = state.systems.get(str(ctx.get("position")))
    planet = str(ctx.get("planet") or "")
    infantry = system.planet_units.get(planet, {}).get(player_id, {}).get("infantry", 0) if (
        system is not None
    ) else 0
    left = reinforcements_left(state, player_id, "mech")
    ready = payment.ready_planet_values(state, _registry(), player_id, "resources")
    funds = sum(ready.values()) + economy.spendable_trade_goods(state, player_id)
    return infantry > 0 and (left is None or left > 0) and funds >= _DEPLOY_COST


def deploy_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Płatność 2 zasobów: planety do wyczerpania + TG (jeden widżet płatności w UI)."""
    ready = payment.ready_planet_values(state, registry, player_id, "resources")
    planets = [
        (p, registry.planets[p].name if p in registry.planets else p, v)
        for p, v in sorted(ready.items())
    ]
    spendable = economy.spendable_trade_goods(state, player_id)
    planet = str(ctx.get("planet") or "")
    where = registry.planets[planet].name if planet in registry.planets else planet
    return [
        oi.payment_planets(
            planets, "resources", _DEPLOY_COST,
            hint=f"Replace 1 infantry on {where} with 1 mech: pay {_DEPLOY_COST} resources.",
        ),
        oi.number("trade_goods", "Trade goods to spend", 0, min(spendable, _DEPLOY_COST)),
    ]


@on_event(
    GameEvent.COMBAT_ROUND, Moment.START, HookSource(SOURCE_UNIT, MECH),
    optional=True, condition=_deploy_ready, inputs=deploy_inputs,
    covers=f"units:{MECH}", label="Dunlain Reaper: DEPLOY",
)
def dunlain_reaper(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dunlain Reaper — DEPLOY: At the start of a round of ground combat, you may spend 2
    resources to replace 1 of your infantry in that combat with 1 mech."""
    registry = _registry()
    params = ctx.get("params", {})
    planets = [str(p) for p in params.get("planets") or []]
    trade_goods = int(params.get("trade_goods") or 0)
    paid = payment.validate_payment(state, registry, player_id, "resources", planets, trade_goods)
    if paid < _DEPLOY_COST:
        raise ValueError(f"Spend at least {_DEPLOY_COST} resources (you chose {paid}).")
    payment.apply_payment(state, player_id, planets, trade_goods)
    system = state.systems[str(ctx["position"])]
    planet = str(ctx["planet"])
    unit_ops.remove_units(state, system, planet, player_id, "infantry", 1, UnitCause.REMOVED)
    unit_ops.place_units(state, system, planet, player_id, "mech", 1, UnitCause.PLACED)


# ----------------------------------------------------------------------------- War Funding

promissory_play.any_subject(WAR_FUNDING)


@promissory_play.condition(WAR_FUNDING)
def _war_funding_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> str | None:
    combat = state.active_combat
    if combat is None or combat.kind != "space" or _opponent_of(state, player_id) is None:
        return "War Funding is played in your space combat."
    if not _dice_window_open(state):
        return "Play it after both players roll, before hits are assigned."
    return None


@register_effect_inputs(f"promissory_notes:{WAR_FUNDING}")
def war_funding_inputs(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    own = _dice_options(state, player_id)
    return [
        oi.choice(
            "opponent", "Reroll all of your opponent's dice?",
            [oi.option(_YES, "Yes"), oi.option(_NO, "No")], always=True,
        ),
        oi.multi("dice", "Your dice to reroll", own, 0, len(own)),
    ]


@register_effect(f"promissory_notes:{WAR_FUNDING}")
def war_funding(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """War Funding: After you and your opponent roll dice during space combat: You may reroll all
    of your opponent's dice. You may reroll any number of your dice. Then, return this card."""
    opponent = _opponent_of(state, player_id)
    combat = state.active_combat
    if opponent is None or combat is None:
        raise ValueError("War Funding is played in your space combat.")
    if params.get("opponent") == _YES:
        everything = {
            (index, die)
            for index, entry in enumerate(combat.rolls.get(opponent, []))
            for die in range(len(entry["dice"]))
        }
        if everything:
            battle.reroll_combat_dice(
                state, opponent, everything, "war_funding", "War Funding", roller=player_id
            )
    own = _chosen(params.get("dice"))
    if own:
        battle.reroll_combat_dice(state, player_id, own, "war_funding", "War Funding")


# --------------------------------------------------------------------------- Viscount Unlenn


def _agent_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("kind") == "space" and leaders.is_ready(state, _registry(), player_id, AGENT)


def agent_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    system = state.systems.get(str(ctx.get("position")))
    options: list[dict[str, Any]] = []
    # Najpierw własne statki (najczęstszy wybór), potem przeciwnika.
    owners = sorted(
        (system.space_units if system is not None else {}).items(),
        key=lambda item: (item[0] != player_id, item[0]),
    )
    for owner, units in owners:
        player = state.players.get(owner)
        if player is None:
            continue
        faction = registry.factions.get(player.faction or "")
        who = faction.name if faction is not None else owner
        for base_type, count in sorted(units.items()):
            if count > 0 and is_space_unit(base_type):
                label = f"{unit_name(state, registry, owner, base_type)} - {who}"
                meta = oi.unit_meta(base_type, owner, player.faction, player.color, count)
                options.append(oi.option(f"{owner}|{base_type}", label, meta=meta))
    return [oi.choice("ship", "Ship that rolls 1 additional die", options, always=True)]


@on_event(
    GameEvent.COMBAT_ROUND, Moment.START, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_agent_ready, inputs=agent_inputs,
    covers=f"leaders:{AGENT}", label="Viscount Unlenn",
)
def viscount_unlenn(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Viscount Unlenn: At the start of a space combat round: You may exhaust this card to choose 1
    ship in the active system: that ship rolls 1 additional die during this combat round."""
    choice = str(ctx.get("params", {}).get("ship") or "")
    owner, _, base_type = choice.partition("|")
    if owner not in state.players or not base_type:
        raise ValueError("Choose a ship in the active system.")
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT)
    active_effects.add_effect(
        state, AGENT_DIE, Duration.COMBAT_ROUND, owner=owner, data={"base_type": base_type}
    )


@register(POINT_COMBAT_BONUS_DICE, HookSource(SOURCE_EFFECT, AGENT_DIE), HookKind.MODIFY)
def viscount_die(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    if ctx.get("kind") != "space":
        return 0
    return sum(
        1
        for e in active_effects.effects_for(state, player_id, AGENT_DIE)
        if e.data.get("base_type") == ctx.get("base_type")
    )


# ------------------------------------------------------------------------ Rear Admiral Farran


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 5 non-fighter ships in 1 system."""
    for system in state.systems.values():
        ships = system.space_units.get(player_id, {})
        if sum(n for bt, n in ships.items() if is_space_unit(bt) and bt != "fighter") >= (
            _COMMANDER_SHIPS
        ):
            return True
    return False


def _own_sustain(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


@on_event(
    GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_own_sustain, covers=f"leaders:{COMMANDER}",
    label="Rear Admiral Farran: gain trade goods",
)
def rear_admiral_farran(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Rear Admiral Farran: After 1 of your units uses SUSTAIN DAMAGE: You may gain 1 trade good
    (po 1 TG na każde użycie — F_letnev)."""
    economy.gain_trade_goods(state, player_id, int(ctx.get("count", 1)))


# -------------------------------------------------------------------------- Darktalon Treilla


@register_effect(f"leaders:{HERO}")
def dark_matter_affinity(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Darktalon Treilla: ACTION: Place this card near the game board; the number of non-fighter
    ships you can have in systems is not limited by laws or by the number of command tokens in your
    fleet pool during this game round. At the end of that game round, purge this card."""
    active_effects.add_effect(state, HERO_EFFECT, Duration.ROUND, owner=player_id)


@register(POINT_FLEET_POOL_UNLIMITED, HookSource(SOURCE_EFFECT, HERO_EFFECT), HookKind.PERMIT)
def hero_no_fleet_limit(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return True


# --------------------------------------------------------------------- Gravleash Maneuvers


def _ship_types(state: GameState, player_id: str, position: str) -> list[str]:
    system = state.systems.get(position)
    ships = system.space_units.get(player_id, {}) if system is not None else {}
    return sorted(bt for bt, n in ships.items() if n > 0 and is_space_unit(bt))


def _gravleash_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("kind") == "space"
        and _participant(state, player_id, ctx)
        and bool(_ship_types(state, player_id, str(ctx.get("position"))))
    )


def gravleash_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    position = str(ctx.get("position"))
    types = _ship_types(state, player_id, position)
    player = state.players[player_id]
    ships = state.systems[position].space_units.get(player_id, {})
    options = [
        oi.option(
            bt, unit_name(state, registry, player_id, bt),
            meta=oi.unit_meta(bt, player_id, player.faction, player.color, ships.get(bt, 0)),
        )
        for bt in types
    ]
    return [
        oi.choice(
            "ship", f"Ship that gets +{len(types)} to its roll", options,
            hint=f"+{len(types)} = number of your ship types in this combat.",
        )
    ]


@on_event(
    GameEvent.COMBAT_ROUND, Moment.START, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    condition=_gravleash_ready, decide=True, inputs=gravleash_inputs,
    covers=f"breakthroughs:{BREAKTHROUGH}", label="Gravleash Maneuvers",
)
def gravleash(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Gravleash Maneuvers: Before you roll dice during space combat, apply +X to the results of 1
    of your ship's rolls, where X is the number of ship types you have in the combat.

    Druga klauzula (ruch): PERMIT ``movement.match_highest`` niżej.
    """
    base_type = str(ctx.get("params", {}).get("ship") or "")
    active_effects.add_effect(
        state, GRAVLEASH, Duration.COMBAT_ROUND, owner=player_id,
        data={"base_type": base_type, "position": str(ctx.get("position"))},
    )


@register(POINT_COMBAT_SINGLE_UNIT_BONUS, HookSource(SOURCE_EFFECT, GRAVLEASH), HookKind.MODIFY)
def gravleash_bonus(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    if ctx.get("kind") != "space":
        return 0
    for effect in active_effects.effects_for(state, player_id, GRAVLEASH):
        if effect.data.get("base_type") == ctx.get("base_type"):
            return len(_ship_types(state, player_id, str(ctx.get("position"))))
    return 0


@register(
    POINT_MOVEMENT_MATCH_HIGHEST, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH), HookKind.PERMIT
)
def gravleash_movement(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Gravleash Maneuvers: During movement, your non-fighter ships' move values are equal to the
    highest move value amongst moving ships in the system they started in."""
    return True
