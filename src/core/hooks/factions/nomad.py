"""The Nomad — every faction component (RULES.md 62.21).

Texts in docstrings are quotes from the assets (``catalog.faction_bundle("nomad")``, units
``nomad_flagship`` / ``nomad_flagship2`` / ``nomad_mech``, breakthrough ``nomadbt``). Rulings:
``docs/rules_tirules/F_nomad.md`` (cross-checked: ``R_leaders``, ``R_transactions``,
``R_trade_goods``, ``R_transport``, ``C_promissory_notes``, ``C_action_cards``, ``F_mentak``,
``F_hacan``, ``F_letnev``).
Engine points used/added for the Nomad: ``movement.unit_extra_adjacent`` (Memoria),
``production.free_types`` (Navarch Feng), ``combat.champion`` (The Cavalry), ``combat.hit_shields``
(Quantum Manipulator), ``from_supply`` of ``TRADE_GOODS_GAINED`` + trade goods on a leader card
(Artuno), ``COMPONENT_READIED`` of leaders (``exhaust.ready_leader``), ``transaction.grant_pair``
(Temporal Command Suite), ``battle.rewind_roll_step`` (The Thundarian), ``position`` of
``TURN/END`` (Field Marshal Mercer) and ``base_type`` of ``movement.ignore_own_command_token``
(Ahk-Syl Siven).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    battle,
    board_graph,
    cooperative,
    economy,
    exhaust,
    faction_components,
    leaders,
    promissory_notes,
    promissory_play,
    rules_hooks,
    transaction,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.hooks.card_labels import planet_name, relic_name
from src.core.hooks.reactions_agenda import predictions
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_COMBAT_CHAMPION,
    POINT_COMBAT_HIT_SHIELDS,
    POINT_MOVEMENT_IGNORE_OWN_CC,
    POINT_MOVEMENT_UNIT_EXTRA_ADJACENT,
    POINT_PRODUCTION_FREE_TYPES,
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
from src.core.state_grid import grid_from_state
from src.core.unit_ops import UnitCause

FACTION = "nomad"
THE_COMPANY = "the_company"
FUTURE_SIGHT = "future_sight"
MEMORIA_II = "m2"
TCS = "tcs"
MERCER = "nomadagentmercer"
THUNDARIAN = "nomadagentthundarian"
ARTUNO = "nomadagentartuno"
COMMANDER = "nomadcommander"
HERO = "nomadhero"
CAVALRY = "cavalry"
FLAGSHIP = "nomad_flagship"
FLAGSHIP_II = "nomad_flagship2"
MECH = "nomad_mech"
BREAKTHROUGH = "nomadbt"

TIME_WARP = f"leaders:{HERO}:time_warp"  # effect: the flagship leaves command-token systems
CAVALRY_KEY = f"promissory_notes:{CAVALRY}:ship"  # effect: 1 ship with the flagship's values
_FLAGSHIP = "flagship"
_MECH = "mech"
_FIGHTER = "fighter"
_GROUND = ("infantry", "mech")
_MERCER_FORCES = 2  # "up to 2 of their ground forces"
_FUTURE_SIGHT_TG = 1  # "Gain 1 trade good"
_FEUD = "|"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _grid(state: GameState) -> HexGrid:
    return board_graph.bound_grid() or grid_from_state(state, _registry())


def nomad_player(state: GameState) -> str | None:
    """The Nomad player at the table (owner of The Cavalry), or None."""
    return next((pid for pid, p in sorted(state.players.items()) if p.faction == FACTION), None)


def _name(state: GameState, player_id: str) -> str:
    player = state.players.get(player_id)
    return (player.display_name or player.faction or player_id) if player else player_id


def _is_agent(registry: StaticDataRegistry, leader_id: str) -> bool:
    leader = registry.leaders.get(leader_id)
    return leader is not None and leader.type == "agent"


def agents(state: GameState, registry: StaticDataRegistry) -> list[tuple[str, str, str]]:
    """Every agent at the table as ``(owner, leader id, state)`` - seating order, sheet order."""
    order = [p for p in state.seating_order if p in state.players] or sorted(state.players)
    found: list[tuple[str, str, str]] = []
    for pid in order:
        for leader_id in leaders.leaders_of(registry, state.players[pid]):
            if _is_agent(registry, leader_id):
                found.append((pid, leader_id, leaders.state_of(state, registry, pid, leader_id)))
    return found


def _agent_owner(state: GameState, registry: StaticDataRegistry, leader_id: str) -> str | None:
    return next((pid for pid, lid, _ in agents(state, registry) if lid == leader_id), None)


def _leader_option(
    state: GameState, registry: StaticDataRegistry, owner: str, leader_id: str
) -> dict[str, Any]:
    leader = registry.leaders.get(leader_id)
    name = leader.name if leader is not None else leader_id
    if owner != nomad_player(state):
        name = f"{name} ({_name(state, owner)})"
    return oi.option(f"{owner}{_FEUD}{leader_id}", name, ref=("leader", leader_id))


# The Company: the data's leader list holds all three agents (RULES.md 62.21).
rules_hooks.declare_core_rule(f"abilities:{THE_COMPANY}")


# =================================================================================== Future Sight


def _future_sight_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    outcome = str(ctx.get("outcome") or "")
    agenda = state.agenda
    if not outcome or agenda is None:
        return False
    vote = agenda.votes.get(player_id)
    voted = vote is not None and vote.outcome == outcome and vote.votes >= 1
    predicted = any(predicted == outcome for _card, predicted in predictions(state, player_id))
    return voted or predicted


@on_event(
    GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    condition=_future_sight_ready, covers=f"abilities:{FUTURE_SIGHT}", label="Future Sight",
)
def future_sight(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Future Sight: During the Agenda phase, after an outcome that you voted for or predicted is
    resolved: Gain 1 trade good (one, however many predictions match - future-sight 2)."""
    economy.gain_trade_goods(state, player_id, _FUTURE_SIGHT_TG, cause=f"abilities:{FUTURE_SIGHT}")
    ability_notes.note(state, player_id, f"abilities:{FUTURE_SIGHT}", "+1 trade good")


# ======================================================================== Memoria / Memoria II


def _mech_systems(state: GameState, player_id: str) -> set[str]:
    found: set[str] = set()
    for position, system in state.systems.items():
        if system.space_units.get(player_id, {}).get(_MECH, 0) > 0 or any(
            by.get(player_id, {}).get(_MECH, 0) > 0 for by in system.planet_units.values()
        ):
            found.add(position)
    return found


def _memoria_adjacent(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> set[str]:
    """You may treat this unit as if it were adjacent to systems that contain 1 or more of your
    mechs (only the flagship - memoria 1; movement only, not board adjacency - 2, 3, 4)."""
    if ctx.get("base_type") != _FLAGSHIP:
        return set()
    return _mech_systems(state, player_id)


register(POINT_MOVEMENT_UNIT_EXTRA_ADJACENT, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.FORBID,
         covers=f"units:{FLAGSHIP}")(_memoria_adjacent)
register(POINT_MOVEMENT_UNIT_EXTRA_ADJACENT, HookSource(SOURCE_UNIT, FLAGSHIP_II), HookKind.FORBID,
         covers=f"units:{FLAGSHIP_II}")(_memoria_adjacent)
# Memoria II (unit upgrade): its values come from the data (``resolve_unit_variant``), its ability
# is the Memoria II unit's hook above.
rules_hooks.declare_core_rule(f"technologies:{MEMORIA_II}")


# ====================================================================== Temporal Command Suite


def _exhausted_agent(
    state: GameState, ctx: Mapping[str, Any]
) -> tuple[str, str, str] | None:
    """``(kind, owner, id)`` of the agent that has just become exhausted, if it still is: a leader
    agent, or a relic that is an agent (JR-XS455-O - C_relics jrxs455o 1.1)."""
    registry = _registry()
    # A copied agent (Ssruu, RULES.md 62.22) exhausted its proxy: that card is "that agent".
    kind, _, component = str(ctx.get("proxy") or ctx.get("component") or "").partition(":")
    if kind == "leaders" and _is_agent(registry, component):
        owner = _agent_owner(state, registry, component)
        if owner is not None and leaders.state_of(
            state, registry, owner, component
        ) == leaders.EXHAUSTED:
            return kind, owner, component
    if kind == "relics" and ctx.get("agent"):
        owner = str(ctx.get("player") or "")
        player = state.players.get(owner)
        if player is not None and component in player.exhausted_relics:
            return kind, owner, component
    return None


def _tcs_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    player = state.players[player_id]
    return (
        TCS in player.technologies and TCS not in player.exhausted_technologies
        and _exhausted_agent(state, ctx) is not None
    )


@on_event(
    GameEvent.COMPONENT_EXHAUSTED, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, TCS),
    optional=True, condition=_tcs_ready, covers=f"technologies:{TCS}",
    label="Temporal Command Suite: ready that agent",
)
def temporal_command_suite(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Temporal Command Suite: After any player's agent becomes exhausted, you may exhaust this
    card to ready that agent; if you ready another player's agent, you may perform a transaction
    with that player (no neighbours, any player's turn - tcs 1-3)."""
    registry = _registry()
    found = _exhausted_agent(state, ctx)
    if found is None:
        raise ValueError("That agent is not exhausted any more.")
    kind, owner, component = found
    faction_components.pay_cost(state, registry, player_id, "technology", TCS)
    if kind == "relics":
        exhaust.ready_relic(state, owner, component)
        detail = f"{relic_name(registry, component)} readied"
    else:
        exhaust.ready_leader(state, owner, component)
        detail = f"{registry.leaders[component].name} readied"
    if owner != player_id:
        transaction.grant_pair(state, player_id, owner, source=f"technologies:{TCS}")
        detail += f"; you may make a transaction with {_name(state, owner)}"
    ability_notes.note(state, player_id, f"technologies:{TCS}", detail)


# ======================================================================== Field Marshal Mercer


def _controlled_planets(state: GameState, player_id: str, position: str) -> list[str]:
    system = state.systems.get(position)
    if system is None:
        return []
    return sorted(p for p, owner in system.planet_owners.items() if owner == player_id)


def _ground_forces(state: GameState, player_id: str) -> list[tuple[str, str, str, int]]:
    """``(position, zone, base_type, count)`` of the player's ground forces on the board."""
    found: list[tuple[str, str, str, int]] = []
    for position in sorted(state.systems):
        system = state.systems[position]
        zones = [("space", system.space_units.get(player_id, {}))] + [
            (planet, by.get(player_id, {})) for planet, by in sorted(system.planet_units.items())
        ]
        for zone, units in zones:
            for base_type in _GROUND:
                if units.get(base_type, 0) > 0:
                    found.append((position, zone, base_type, units[base_type]))
    return found


def _mercer_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    target = str(ctx.get("player") or "")
    position = str(ctx.get("position") or "")
    return (
        target in state.players and bool(position)
        and leaders.is_ready(state, _registry(), player_id, MERCER)
        and bool(_controlled_planets(state, target, position))
        and bool(_ground_forces(state, target))
    )


# Cooperative agent (RULES.md 54.15): the player whose turn ends requests it.
cooperative.register_pull(f"leaders:{MERCER}")


@on_event(
    GameEvent.TURN, Moment.END, HookSource(SOURCE_LEADER, MERCER), optional=True,
    condition=_mercer_ready, covers=f"leaders:{MERCER}",
    label="Field Marshal Mercer: let that player move 2 ground forces",
)
def mercer(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Field Marshal Mercer: At the end of a player's turn: You may exhaust this card to allow that
    player to remove up to 2 of their ground forces from the game board and place them on planets
    they control in the active system (that player chooses - their decision below)."""
    faction_components.pay_cost(
        state, _registry(), player_id, "leader", MERCER,
        {"target": str(ctx["player"]), "position": str(ctx["position"])},
    )


def _mercer_target(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def _mercer_granted(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    return str(ctx.get("target") or "") in state.players and bool(ctx.get("position"))


def mercer_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Forces and their planets - manual choices, no "Auto" (user decision 2026-11-27)."""
    position = str(ctx["position"])
    options: list[dict[str, Any]] = []
    for pos, zone, base_type, count in _ground_forces(state, decider):
        planet = zone if zone != "space" else None
        for index in range(min(count, _MERCER_FORCES)):
            options.append(oi.option(
                f"{pos}{_FEUD}{zone}{_FEUD}{base_type}{_FEUD}{index}",
                unit_name(state, registry, decider, base_type),
                meta=oi.unit_at(state, decider, base_type, position=pos, planet=planet),
            ))
    planets = [
        oi.option(p, planet_name(registry, p), ref=("planet", p))
        for p in _controlled_planets(state, decider, position)
    ]
    return [
        oi.multi("forces", "Ground forces to place in the active system (up to 2)", options,
                 0, min(_MERCER_FORCES, len(options))),
        *[oi.choice(f"planet_{n}", f"Ground force {n} goes to", planets, optional=True)
          for n in range(1, _MERCER_FORCES + 1)],
    ]


@on_event(
    GameEvent.COMPONENT_EXHAUSTED, Moment.AFTER, HookSource(SOURCE_LEADER, MERCER),
    where={"component": f"leaders:{MERCER}"}, condition=_mercer_granted, decide=True,
    decider=_mercer_target, inputs=mercer_inputs,
    label="Field Marshal Mercer: place up to 2 ground forces",
)
def mercer_place(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    """The player Mercer helped moves up to 2 ground forces onto planets they control in the
    active system (damaged mechs stay damaged - mercer 5)."""
    target = str(ctx["decider"])
    position = str(ctx["position"])
    params = ctx.get("params") or {}
    chosen = [str(v) for v in params.get("forces") or []]
    if len(chosen) > _MERCER_FORCES:
        raise ValueError(f"Choose up to {_MERCER_FORCES} ground forces.")
    planets = _controlled_planets(state, target, position)
    dest_system = state.systems[position]
    for n, value in enumerate(chosen, start=1):
        pos, zone, base_type, _index = value.split(_FEUD)
        planet = str(params.get(f"planet_{n}") or "")
        if not planet:
            raise ValueError(f"Choose the planet for ground force {n}.")
        if planet not in planets:
            raise ValueError("Place the ground forces on planets you control in the active system.")
        source = state.systems.get(pos)
        units = (
            source.space_units.get(target, {}) if source is not None and zone == "space"
            else source.planet_units.get(zone, {}).get(target, {}) if source is not None else {}
        )
        if base_type not in _GROUND or units.get(base_type, 0) < 1:
            raise ValueError("Choose your own ground forces on the game board.")
        assert source is not None
        unit_ops.transfer_units(state, source, zone, dest_system, planet, target, base_type, 1,
                                UnitCause.PLACED)
    ability_notes.note(state, target, f"leaders:{MERCER}",
                       f"{len(chosen)} ground force(s) placed in system {position}")


# ================================================================================ The Thundarian


def _thundarian_helps(state: GameState, _owner: str) -> list[str]:
    combat = state.active_combat
    return [] if combat is None else [combat.attacker, combat.defender]


# Cooperative agent (RULES.md 54.15): either combatant may ask / pay for the re-roll; the Nomad
# fighting the combat is prompted as before.
cooperative.register_pull_component("leader", THUNDARIAN, _thundarian_helps)


@faction_components.window_use("leader", THUNDARIAN)
def _thundarian_window(
    state: GameState, _registry_: StaticDataRegistry, _player_id: str
) -> str | None:
    if not battle.roll_step_open(state):
        return "Use it after the combat dice are rolled, before any hit is assigned."
    return None


@register_effect(f"leaders:{THUNDARIAN}")
def thundarian(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """The Thundarian: After the "Roll Dice" step of combat: You may exhaust this card. If you do,
    hits are not assigned to either player's units. Return to the start of this combat round's
    "Roll Dice" step (any combat - thundarian 1; round effects stay - 2, 3)."""
    combat = state.active_combat
    battle.rewind_roll_step(state)
    where = f" in system {combat.position}" if combat is not None else ""
    ability_notes.note(state, player_id, f"leaders:{THUNDARIAN}",
                       f"combat dice rolled again{where}")


# ============================================================================ Artuno the Betrayer


def _artuno_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    amount = int(ctx.get("amount") or 0)
    return (
        ctx.get("player") == player_id and bool(ctx.get("from_supply")) and amount > 0
        and leaders.is_ready(state, _registry(), player_id, ARTUNO)
        and state.players[player_id].trade_goods >= amount
    )


@on_event(
    GameEvent.TRADE_GOODS_GAINED, Moment.AFTER, HookSource(SOURCE_LEADER, ARTUNO), optional=True,
    condition=_artuno_ready, covers=f"leaders:{ARTUNO}",
    label="Artuno the Betrayer: put those trade goods on this card",
)
def artuno_stash(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Artuno the Betrayer: When you gain trade goods from the supply: You may exhaust this card to
    place an equal number of trade goods on this card (one gain only - artuno 1)."""
    amount = int(ctx["amount"])
    faction_components.pay_cost(state, _registry(), player_id, "leader", ARTUNO)
    economy.stash_on_leader(state, player_id, ARTUNO, amount)


def _artuno_readied(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


@on_event(
    GameEvent.COMPONENT_READIED, Moment.AFTER, HookSource(SOURCE_LEADER, ARTUNO),
    where={"component": f"leaders:{ARTUNO}"}, condition=_artuno_readied,
    covers=f"leaders:{ARTUNO}", label="Artuno the Betrayer: gain the trade goods on it",
)
def artuno_payout(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """When this card readies, gain the trade goods on this card (not from the supply - 3)."""
    gained = economy.release_from_leader(state, player_id, ARTUNO)
    if gained:
        ability_notes.note(state, player_id, f"leaders:{ARTUNO}", f"+{gained} trade goods")


# =========================================================================== Navarch Feng


@leaders.register_unlock(COMMANDER)
def _feng_unlocked(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 1 scored secret objective (an objective made public by Classified Document
    Leaks is not a secret any more - feng 2)."""
    return len(state.players[player_id].scored_secrets) >= 1


@register(POINT_PRODUCTION_FREE_TYPES, HookSource(SOURCE_LEADER, COMMANDER), HookKind.FORBID,
          covers=f"leaders:{COMMANDER}")
def navarch_feng(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Navarch Feng: When you produce: You can produce your flagship without spending resources
    (its cost stays 8 - feng 1)."""
    return {_FLAGSHIP}


# ================================================================ Ahk-Syl Siven — Time Warp


@register_effect(f"leaders:{HERO}")
def time_warp(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Ahk-Syl Siven — Probability Matrix: Time Warp: ACTION: Place this card near the game board;
    your flagship and units it transports can move out of systems that contain your command tokens
    during this game round. At the end of that game round, purge this card.

    ⚠️ ASSUMPTION (RULES.md 62.21): purged on use, the effect lasts to the end of the round."""
    areas: dict[str, str] = {}
    for position, system in sorted(state.systems.items()):
        if player_id in system.command_tokens:
            areas[position] = "time_warp_token"
    for position, system in sorted(state.systems.items()):
        if system.space_units.get(player_id, {}).get(_FLAGSHIP, 0) > 0:
            areas[position] = "time_warp"
    active_effects.add_effect(
        state, TIME_WARP, Duration.ROUND, owner=player_id,
        data={"areas": areas},
    )
    ability_notes.note(state, player_id, f"leaders:{HERO}",
                       "your flagship may leave systems with your command tokens this round")


@register(POINT_MOVEMENT_IGNORE_OWN_CC, HookSource(SOURCE_EFFECT, TIME_WARP), HookKind.PERMIT)
def time_warp_move(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Only the flagship (and the units it transports - the move passes it as the carrier)."""
    return ctx.get("base_type") == _FLAGSHIP


# ================================================================================= The Cavalry

promissory_play.any_subject(CAVALRY)


def _opponent(state: GameState, player_id: str) -> str | None:
    combat = state.active_combat
    if combat is None or player_id not in (combat.attacker, combat.defender):
        return None
    return combat.defender if player_id == combat.attacker else combat.attacker


def _cavalry_ships(state: GameState, player_id: str) -> list[battle.CombatUnit]:
    return [
        u for u in battle.side_units(state, _grid(state), _registry(), player_id)
        if u.base_type != _FIGHTER
    ]


@promissory_play.condition(CAVALRY)
def _cavalry_condition(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> str | None:
    combat = state.active_combat
    opponent = _opponent(state, player_id)
    if combat is None or combat.kind != "space" or opponent is None:
        return "The Cavalry is played at the start of your space combat."
    if opponent == nomad_player(state):
        return "The Cavalry is played in a space combat against a player other than the Nomad."
    if active_effects.has_effect(state, player_id, CAVALRY_KEY):
        return "The Cavalry is already in this combat."
    if not _cavalry_ships(state, player_id):
        return "You have no non-fighter ship in this combat."
    return None


@register_effect_inputs(f"promissory_notes:{CAVALRY}")
def cavalry_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.21): "Auto" = the group with the worst combat value."""
    ships = _cavalry_ships(state, player_id) if state.active_combat is not None else []
    player = state.players[player_id]
    options = [
        oi.option(u.base_type, u.name,
                  meta=oi.unit_meta(u.base_type, player_id, player.faction, player.color, u.count))
        for u in ships
    ]
    worst = max(ships, key=lambda u: (u.base_hits_on, u.base_type)).base_type if ships else None
    return [oi.choice("ship", "Ship that fights as the Nomad's flagship", options, always=True,
                      auto=worst)]


def flagship_values(state: GameState, registry: StaticDataRegistry, nomad: str) -> str:
    """The Nomad's flagship variant (Memoria II with ``m2``): ``hits|dice|afb|afb dice``."""
    player = state.players.get(nomad)
    unit = resolve_unit_variant(
        registry, FACTION, list(player.technologies) if player else [], _FLAGSHIP
    )
    if unit is None or unit.combat_hits_on is None:
        raise ValueError("The Nomad's flagship has no combat value.")
    afb = "" if unit.afb_hits_on is None else str(unit.afb_hits_on)
    return _FEUD.join([str(unit.combat_hits_on), str(unit.combat_die_count or 1), afb,
                       str(unit.afb_die_count or 0)])


@register_effect(f"promissory_notes:{CAVALRY}")
def cavalry(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """The Cavalry: At the start of a space combat against a player other than the Nomad: During
    this combat, treat 1 of your non-fighter ships as if it has the SUSTAIN DAMAGE ability, combat
    value, and ANTI-FIGHTER BARRAGE value of the Nomad's flagship. Return this card to the Nomad
    player at the end of the combat (it lies in your play area until then)."""
    ship = str(params.get("ship") or "")
    if ship not in {u.base_type for u in _cavalry_ships(state, player_id)}:
        raise ValueError("Choose 1 of your non-fighter ships in this combat.")
    owner = str(params.get("__owner") or nomad_player(state) or "")
    note = str(params.get("__note") or CAVALRY)
    name, _text = promissory_play.note_text(state, registry, note)
    active_effects.add_effect(
        state, CAVALRY_KEY, Duration.COMBAT, owner=player_id,
        data={"base_type": ship, "values": flagship_values(state, registry, owner),
              "note": note, "nomad": owner, "label": name},
    )
    promissory_notes.place_in_play(state, player_id, note)


@register(POINT_COMBAT_CHAMPION, HookSource(SOURCE_EFFECT, CAVALRY_KEY), HookKind.FORBID,
          covers=f"promissory_notes:{CAVALRY}")
def cavalry_champion(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    return {
        _FEUD.join([str(e.data["base_type"]), str(e.data["values"]), str(e.data.get("label"))])
        for e in state.active_effects if e.key == CAVALRY_KEY and e.owner == player_id
    }


@on_event(GameEvent.COMBAT, Moment.END, HookSource(SOURCE_EFFECT, CAVALRY_KEY),
          label="The Cavalry: return to the Nomad")
def cavalry_return(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Return this card to the Nomad player at the end of the combat (also after a retreat)."""
    for effect in [e for e in state.active_effects
                   if e.key == CAVALRY_KEY and e.owner == player_id]:
        note, nomad = str(effect.data["note"]), str(effect.data["nomad"])
        if note in state.players[player_id].promissory_notes_in_play and nomad in state.players:
            promissory_notes.return_from_play(state, player_id, nomad, note)


# ========================================================================= Quantum Manipulator


@register(POINT_COMBAT_HIT_SHIELDS, HookSource(SOURCE_UNIT, MECH), HookKind.FORBID,
          covers=f"units:{MECH}")
def quantum_manipulator(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Quantum Manipulator: While this unit is in a space area during combat, you may use its
    SUSTAIN DAMAGE ability to cancel a hit that is produced against your ships in this system."""
    return {_MECH}


# ============================================================================ Thunder's Paradox


def _paradox_pairs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> tuple[list[str], list[tuple[str, str]]]:
    everyone = agents(state, registry)
    own = [lid for pid, lid, st in everyone if pid == player_id and st == leaders.UNLOCKED]
    exhausted = [(pid, lid) for pid, lid, st in everyone if st == leaders.EXHAUSTED]
    mine_first = sorted(exhausted, key=lambda x: x[0] != player_id)
    return own, mine_first


def _paradox_ready(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    own, exhausted = _paradox_pairs(state, _registry(), player_id)
    return bool(own) and bool(exhausted)


def paradox_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Both agents - manual choices, no "Auto" (user decision 2026-11-27)."""
    own, exhausted = _paradox_pairs(state, registry, player_id)
    mine = [_leader_option(state, registry, player_id, lid) for lid in own]
    others = [_leader_option(state, registry, pid, lid) for pid, lid in exhausted]
    return [
        oi.choice("exhaust", "Your agent to exhaust", mine, always=True),
        oi.choice("ready", "Agent to ready", others, always=True),
    ]


def _paradox_helps(state: GameState, owner: str, _ctx: Mapping[str, Any]) -> list[str]:
    """Other players with an exhausted agent (they may ask / pay to have it readied)."""
    _own, exhausted = _paradox_pairs(state, _registry(), owner)
    return [pid for pid, _lid in exhausted if pid != owner]


def _agent_holder(_state: GameState, _owner: str, value: str) -> str | None:
    return value.partition(_FEUD)[0] or None


# Cooperative (RULES.md 54.15): the Nomad is still offered it (mutual) and picks the agent it
# exhausts; the readied agent must be the requester's.
cooperative.register_pull(
    f"breakthroughs:{BREAKTHROUGH}", _paradox_helps, mutual=True, target="ready",
    target_of=_agent_holder, owner_picks=True,
)


@on_event(
    GameEvent.TURN, Moment.START, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH), optional=True,
    condition=_paradox_ready, inputs=paradox_inputs, covers=f"breakthroughs:{BREAKTHROUGH}",
    label="Thunder's Paradox: exhaust an agent to ready another",
)
def thunders_paradox(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Thunder's Paradox: At the start of any player's turn, you may exhaust 1 of your agents to
    ready any other agent (any player's - thunders-paradox 1)."""
    registry = _registry()
    params = ctx.get("params") or {}
    own, exhausted = _paradox_pairs(state, registry, player_id)
    spend = str(params.get("exhaust") or (f"{player_id}{_FEUD}{own[0]}" if own else ""))
    ready = str(params.get("ready") or (_FEUD.join(exhausted[0]) if exhausted else ""))
    spend_owner, _, spend_id = spend.partition(_FEUD)
    ready_owner, _, ready_id = ready.partition(_FEUD)
    if spend_owner != player_id or spend_id not in own:
        raise ValueError("Exhaust 1 of your readied agents.")
    if (ready_owner, ready_id) not in exhausted:
        raise ValueError("Ready an exhausted agent.")
    leaders.exhaust_announced(state, player_id, spend_id)
    exhaust.ready_leader(state, ready_owner, ready_id)
    ability_notes.note(
        state, player_id, f"breakthroughs:{BREAKTHROUGH}",
        f"{registry.leaders[spend_id].name} exhausted, {registry.leaders[ready_id].name} readied",
    )
