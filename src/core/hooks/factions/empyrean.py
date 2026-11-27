"""The Empyrean — every faction component (RULES.md 62.20).

Texts in docstrings are quotes from the assets (``catalog.faction_bundle("empyrean")``, units
``empyrean_flagship`` / ``empyrean_mech``, breakthrough ``empyreanbt``). Rulings:
``docs/rules_tirules/F_empyrean.md`` (cross-checked: ``R_nebula``, ``R_frontier_tokens``,
``R_fracture``, ``R_neighbors``, ``C_promissory_notes``, ``C_action_cards``, ``F_argent``,
``F_muaat``, ``F_mentak``, ``F_xxcha``).
Engine points used/added for Empyrean: ``movement.nebula_ignored`` (Voidborn), the adjacency cut
layer ``adjacency.cut_for_player`` (Void Tether, layer 4 of RULES.md 61.7), the Void Tether border
token (``faction_tokens.VOID_TETHER``), ``COMMODITIES_GIVEN`` from ``economy.give_to_player``
(Dark Pact), ``position`` in ``UNIT_SUSTAIN_DAMAGE`` (Dynamo) and the frontier queue of the
exploration window (Multiverse Shift).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    agenda_phase,
    board_graph,
    card_hold,
    command_tokens,
    cooperative,
    economy,
    exploration_frontier,
    faction_components,
    faction_tokens,
    leaders,
    neighbors,
    payment,
    promissory_notes,
    promissory_play,
    rules_hooks,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.damage import damaged_count, set_damaged
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.hooks import card_labels
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_ACTION_CARD_CANCELLER,
    POINT_ADJACENCY_CUT_FOR_PLAYER,
    POINT_MOVEMENT_MOVE_VALUE,
    POINT_MOVEMENT_NEBULA_IGNORED,
    POINT_MOVEMENT_PASS_FOREIGN_SHIPS,
    POINT_MOVEMENT_THROUGH_NEBULA,
    SOURCE_BREAKTHROUGH,
    SOURCE_EFFECT,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_PROMISSORY,
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
from src.core.system_planets import planets_of_system
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

FACTION = "empyrean"
VOIDBORN = "voidborn"
AETHERPASSAGE = "aetherpassage"
DARK_WHISPERS = "dark_whispers"
VOIDWATCH = "vw"
AETHERSTREAM = "as"
AGENT = "empyreanagent"
COMMANDER = "empyreancommander"
HERO = "empyreanhero"
DARK_PACT = "dark_pact"
BLOOD_PACT = "blood_pact"
FLAGSHIP = "empyrean_flagship"
MECH = "empyrean_mech"
BREAKTHROUGH = "empyreanbt"

PASSAGE = f"abilities:{AETHERPASSAGE}:allowed"  # effect: owner may fly through Empyrean ships
STREAM = f"technologies:{AETHERSTREAM}:boost"  # effect: +1 move value of the owner's ships
TETHER_ALLOWED = f"breakthroughs:{BREAKTHROUGH}:allowed"  # effect: the owner ignores the cut
BLOOD_DONE = f"promissory_notes:{BLOOD_PACT}:applied"  # once per agenda
VOID_TETHER = faction_tokens.VOID_TETHER
_NEW_TOKEN = "new"
_SPACE = "space"
_POOLS = (("tactical", "Tactic pool"), ("fleet", "Fleet pool"), ("strategic", "Strategy pool"))
_AUTO_POOL = "tactical"  # ⚠️ ASSUMPTION (RULES.md 62.20): Acamar "Auto" = Tactic pool
_AETHERSTREAM_BONUS = 1  # "apply +1 to the move value"
_BLOOD_VOTES = 4  # "cast 4 additional votes"
_REPAIR_COST = 2  # "spend 2 influence to repair that unit"
_AGENT_TOKENS = 1  # "that player gains 1 command token"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _grid(state: GameState) -> HexGrid:
    """The game map (bound by the API - all tiles); in unit tests - a grid from the state."""
    return board_graph.bound_grid() or grid_from_state(state, _registry())


def empyrean_player(state: GameState) -> str | None:
    """The Empyrean player at the table (owner of the faction notes), or None."""
    return next((pid for pid, p in sorted(state.players.items()) if p.faction == FACTION), None)


def _has_units(state: GameState, player_id: str, position: str) -> bool:
    system = state.systems.get(position)
    if system is None:
        return False
    if any(n > 0 for n in system.space_units.get(player_id, {}).values()):
        return True
    return any(n > 0 for by in system.planet_units.values() for n in by.get(player_id, {}).values())


def _has_ships(state: GameState, player_id: str, position: str) -> bool:
    system = state.systems.get(position)
    own = system.space_units.get(player_id, {}) if system is not None else {}
    return any(n > 0 and is_space_unit(bt) for bt, n in own.items())


def _ships_anywhere(state: GameState, player_id: str) -> bool:
    return any(_has_ships(state, player_id, position) for position in state.systems)


def _effect_for(state: GameState, key: str, owner: str) -> bool:
    return any(e.key == key and e.owner == owner for e in state.active_effects)


def _system_option(state: GameState, registry: StaticDataRegistry, position: str) -> dict[str, Any]:
    return oi.option(position, card_labels.describe_system(state, registry, position))


def _no_planets(state: GameState, registry: StaticDataRegistry, position: str) -> bool:
    """A system without planets (a planet destroyed by the Stellar Converter does not count -
    F_empyrean acamar 1, procyon 1; the CURRENT tile decides - F_muaat nova-seed 8)."""
    grid = board_graph.bound_grid()
    source = None if position in state.systems else grid
    return not planets_of_system(state, registry, position, source)


def _real_systems(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Board positions holding a real system tile (no hyperlanes, no empty slots)."""
    found: list[str] = []
    for position in board_graph.board_positions(state):
        definition = registry.systems.get(board_graph.system_id_at(state, position))
        if definition is None or (definition.name or "").strip().lower() == "hyperlane":
            continue
        found.append(position)
    return found


# ======================================================================================= Voidborn


@register(POINT_MOVEMENT_THROUGH_NEBULA, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers=f"abilities:{VOIDBORN}")
def voidborn_through(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Voidborn: Nebulae do not affect your ships' movement (a nebula may be crossed)."""
    return True


@register(POINT_MOVEMENT_NEBULA_IGNORED, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers=f"abilities:{VOIDBORN}")
def voidborn_move_value(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Voidborn: a ship starting in a nebula keeps its move value (also outside the Movement step
    - F_empyrean voidborn 1; the nebula stays an anomaly and keeps the defender's +1 - 2)."""
    return True


# Dark Whispers: setup deals every note of the faction list (``deal_promissory_notes``).
rules_hooks.declare_core_rule(f"abilities:{DARK_WHISPERS}")


# ================================================================================== Aetherpassage


def _passage_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    activator = str(ctx.get("player") or "")
    return (
        bool(activator) and activator != player_id and activator in state.players
        and _ships_anywhere(state, player_id)
        and not _effect_for(state, PASSAGE, activator)
    )


# Cooperative (RULES.md 54.15): the activating player requests passage.
cooperative.register_pull(f"abilities:{AETHERPASSAGE}")


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_passage_ready, covers=f"abilities:{AETHERPASSAGE}",
    label="Aetherpassage: let them move through your ships",
)
def aetherpassage(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Aetherpassage: After a player activates a system: You may allow that player to move their
    ships through systems that contain your ships (decided only after the activation -
    F_empyrean aetherpassage 1)."""
    activator = str(ctx["player"])
    active_effects.add_effect(state, PASSAGE, Duration.TACTICAL_ACTION, owner=activator,
                              data={"by": player_id})
    ability_notes.note(state, player_id, f"abilities:{AETHERPASSAGE}",
                       f"{_name(state, activator)} may move through your ships")


@register(POINT_MOVEMENT_PASS_FOREIGN_SHIPS, HookSource(SOURCE_EFFECT, PASSAGE), HookKind.PERMIT)
def passage_through_ships(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Only the granting Empyrean player's ships may be flown through (another rival's still
    block)."""
    grantors = {
        str(e.data.get("by")) for e in state.active_effects
        if e.key == PASSAGE and e.owner == player_id
    }
    system = state.systems.get(str(ctx.get("position") or ""))
    if system is None or not grantors:
        return False
    others = {
        owner for owner, units in system.space_units.items()
        if owner != player_id and any(n > 0 and is_space_unit(bt) for bt, n in units.items())
    }
    return bool(others) and others <= grantors


def _name(state: GameState, player_id: str) -> str:
    player = state.players.get(player_id)
    return (player.display_name or player.faction or player_id) if player else player_id


# ====================================================================================== Voidwatch


def _voidwatch_mover(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    """"A player moves ships" = the player who moved them (F_mahact benediction 2.1)."""
    return str(ctx.get("mover") or ctx["player"])


def _voidwatch_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    mover = str(ctx.get("mover") or ctx.get("player") or "")
    return (
        bool(mover) and mover != player_id and mover in state.players
        and _has_units(state, player_id, str(ctx.get("position") or ""))
        and bool(state.players[mover].private.promissory_notes)
    )


def _note_option(state: GameState, registry: StaticDataRegistry, note_id: str) -> dict[str, Any]:
    name, _text = promissory_play.note_text(state, registry, note_id)
    return oi.option(note_id, name, ref=("promissory", note_id))


def voidwatch_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The mover picks the note (F_empyrean voidwatch 1). ⚠️ ASSUMPTION "Auto" = the first note in
    their hand (RULES.md 62.20)."""
    hand = list(state.players[decider].private.promissory_notes)
    options = [_note_option(state, registry, note) for note in hand]
    return [oi.choice("note", "Promissory note you give to the Empyrean player", options,
                      always=True, auto=hand[0] if hand else None)]


@on_event(
    GameEvent.SHIPS_MOVED, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, VOIDWATCH),
    condition=_voidwatch_ready, decide=True, decider=_voidwatch_mover, inputs=voidwatch_inputs,
    covers=f"technologies:{VOIDWATCH}", label="Voidwatch: give a promissory note",
)
def voidwatch(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Voidwatch: After a player moves ships into a system that contains 1 or more of your units,
    they must give you 1 promissory note from their hand, if able (not a transaction - F_empyrean
    voidwatch 2)."""
    mover = str(ctx.get("decider") or ctx["player"])
    hand = state.players[mover].private.promissory_notes
    note = str((ctx.get("params") or {}).get("note") or (hand[0] if hand else ""))
    if note not in hand:
        raise ValueError("Choose a promissory note from your hand.")
    promissory_notes.transfer(state, mover, player_id, note)
    ability_notes.note(state, player_id, f"technologies:{VOIDWATCH}",
                       f"{_name(state, mover)} gave a promissory note")


# =================================================================================== Aetherstream


def _anomaly_adjacent(state: GameState, activator: str, position: str) -> bool:
    """A system adjacent to the active one (the ACTIVATING player's adjacency - a Void Tether
    cut counts unless allowed, F_empyrean aetherstream 2) contains an anomaly (nebula too)."""
    grid = _grid(state)
    if position not in grid.positions:
        return False
    return any(
        grid.anomalies_at(near)
        for near in board_graph.neighbors_for_player(state, grid, activator, position)
    )


def _stream_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    activator = str(ctx.get("player") or "")
    if not activator or activator not in state.players or _effect_for(state, STREAM, activator):
        return False
    if activator != player_id and activator not in neighbors.neighbors_of(
        player_id, state, _grid(state)
    ):
        return False
    return _anomaly_adjacent(state, activator, str(ctx.get("position") or ""))


# Cooperative (RULES.md 54.15): a neighbour activating requests the +1; own activation unchanged.
cooperative.register_pull(f"technologies:{AETHERSTREAM}")


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, AETHERSTREAM),
    optional=True, condition=_stream_ready, covers=f"technologies:{AETHERSTREAM}",
    label="Aetherstream: +1 move value",
)
def aetherstream(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Aetherstream: After you or one of your neighbors activates a system that is adjacent to an
    anomaly, you may apply +1 to the move value of all of that player's ships during this tactical
    action (decided after the activation - F_empyrean aetherstream 1)."""
    activator = str(ctx["player"])
    active_effects.add_effect(state, STREAM, Duration.TACTICAL_ACTION, owner=activator,
                              data={"by": player_id})
    ability_notes.note(state, player_id, f"technologies:{AETHERSTREAM}",
                       f"+1 move value for {_name(state, activator)}")


@register(POINT_MOVEMENT_MOVE_VALUE, HookSource(SOURCE_EFFECT, STREAM), HookKind.MODIFY)
def aetherstream_bonus(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> int:
    return _AETHERSTREAM_BONUS if _effect_for(state, STREAM, player_id) else 0


# ============================================================================== Acamar (agent)


def _acamar_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    mover = str(ctx.get("player") or "")
    position = str(ctx.get("position") or "")
    registry = _registry()
    return (
        bool(mover) and mover in state.players and bool(position)
        and leaders.is_ready(state, registry, player_id, AGENT)
        and _no_planets(state, registry, position)
        and command_tokens.reinforcements(state, mover) > 0
    )


# Cooperative agent (RULES.md 54.15): helps "that player" - requested, not pushed.
cooperative.register_pull(f"leaders:{AGENT}")


@on_event(
    GameEvent.SHIPS_MOVED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_acamar_ready, covers=f"leaders:{AGENT}",
    label="Acamar: give that player 1 command token",
)
def acamar(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Acamar: After a player moves ships into a system that does not contain any planets: You may
    exhaust this card; that player gains 1 command token (its pool = that player's decision)."""
    faction_components.pay_cost(
        state, _registry(), player_id, "leader", AGENT,
        {"target": str(ctx["player"]), "position": str(ctx["position"])},
    )


def _acamar_target(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def _acamar_granted(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    target = str(ctx.get("target") or "")
    return target in state.players and "position" in ctx


def acamar_inputs(
    _state: GameState, _registry_: Any, _decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION "Auto" = the Tactic pool (RULES.md 62.20)."""
    options = [oi.option(pool, label) for pool, label in _POOLS]
    return [oi.choice("pool", "Pool for your new command token (Acamar)", options, always=True,
                      auto=_AUTO_POOL)]


@on_event(
    GameEvent.COMPONENT_EXHAUSTED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    where={"component": f"leaders:{AGENT}"}, condition=_acamar_granted, decide=True,
    decider=_acamar_target, inputs=acamar_inputs, label="Acamar: place your command token",
)
def acamar_gain(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    target = str(ctx["decider"])
    pool = str((ctx.get("params") or {}).get("pool") or _AUTO_POOL)
    if pool not in dict(_POOLS):
        raise ValueError("Choose the pool for the command token.")
    if command_tokens.reinforcements(state, target) < _AGENT_TOKENS:
        return  # nothing left to gain
    command_tokens.gain_from_reinforcements(state, target, {pool: _AGENT_TOKENS})


# =========================================================================== Xuange (commander)


@leaders.register_unlock(COMMANDER)
def _xuange_unlocked(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Be neighbors with all other players (on the board - agenda-phase transactions do not
    make players neighbors, F_empyrean xuange 1)."""
    others = set(state.players) - {player_id}
    if not others:
        return False
    grid = board_graph.bound_grid() or grid_from_state(state, registry)
    return others <= neighbors.neighbors_of(player_id, state, grid)


def _xuange_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    mover = str(ctx.get("player") or "")
    system = state.systems.get(str(ctx.get("position") or ""))
    return (
        bool(mover) and mover != player_id and system is not None
        and player_id in system.command_tokens
    )


@on_event(
    GameEvent.SHIPS_MOVED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_xuange_ready, covers=f"leaders:{COMMANDER}",
    label="Xuange: return your command token",
)
def xuange(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Xuange: After another player moves ships into a system that contains 1 of your command
    tokens: You may return that token to your reinforcements (only the system moved into - 5)."""
    position = str(ctx["position"])
    command_tokens.remove_from_board(state, state.systems[position], player_id)
    ability_notes.note(state, player_id, f"leaders:{COMMANDER}",
                       f"command token returned from system {position}")


# ========================================================= Conservator Procyon — Multiverse Shift


def planetless_systems(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Real board systems without planets (The Fracture too - F_empyrean procyon 2)."""
    return [pos for pos in _real_systems(state, registry) if _no_planets(state, registry, pos)]


@register_effect(f"leaders:{HERO}")
def multiverse_shift(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Conservator Procyon — Multiverse Shift: ACTION: Place 1 frontier token in each system that
    does not contain any planets and does not already have a frontier token. Then, explore each
    frontier token that is in a system that contains 1 or more of your ships. Then, purge this card
    (purge - ``faction_components``).

    The explorations follow each other in one exploration window (``frontier_queue``).
    ⚠️ ASSUMPTION (RULES.md 62.20): board order of positions."""
    placed = 0
    for position in planetless_systems(state, registry):
        system = board_graph.ensure_system(state, position)
        if not system.frontier_token:
            system.frontier_token = True
            placed += 1
    explore = [
        position for position in sorted(state.systems)
        if exploration_frontier.can_explore_frontier(state, player_id, position)
    ]
    if explore:
        exploration_frontier.start_frontier(state, registry, player_id, explore[0])
        assert state.exploration is not None
        state.exploration.frontier_queue = explore[1:]
    ability_notes.note(state, player_id, f"leaders:{HERO}",
                       f"{placed} frontier token(s) placed, {len(explore)} to explore")


# ====================================================================== Dark Pact / Blood Pact


def _note_owner(state: GameState, note: str) -> str | None:
    try:
        _template, owner = promissory_play.resolve(state, _registry(), note)
    except ValueError:
        return None
    return owner


@register_effect(f"promissory_notes:{DARK_PACT}")
def dark_pact(
    _state: GameState, _registry_: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """Dark Pact: ACTION: Place this card faceup in your play area (placing -
    ``promissory_play``; the effect works while the card lies there)."""


@register_effect(f"promissory_notes:{BLOOD_PACT}")
def blood_pact(
    _state: GameState, _registry_: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """Blood Pact: ACTION: Place this card faceup in your play area."""


def _dark_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("player") != player_id:
        return False
    if DARK_PACT not in state.players[player_id].promissory_notes_in_play:
        return False
    owner = _note_owner(state, DARK_PACT)
    given = int(ctx.get("commodities") or 0)
    return (
        owner is not None and ctx.get("to") == owner
        and given > 0 and given == economy.commodity_value(state, player_id)
    )


@on_event(
    GameEvent.COMMODITIES_GIVEN, Moment.AFTER, HookSource(SOURCE_PROMISSORY, DARK_PACT),
    condition=_dark_ready, covers=f"promissory_notes:{DARK_PACT}",
    label="Dark Pact: you each gain 1 trade good",
)
def dark_pact_bonus(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dark Pact: When you give a number of commodities to the Empyrean player equal to your maximum
    commodity value, you each gain 1 trade good (with the commodities - F_empyrean dark-pact 3;
    the same cause, so Pillage sees one hand-over - 4)."""
    owner = str(ctx["to"])
    cause = str(ctx.get("cause") or "transaction")
    economy.gain_trade_goods(state, player_id, 1, cause=cause)
    economy.gain_trade_goods(state, owner, 1, cause=cause)
    ability_notes.note(state, player_id, f"promissory_notes:{DARK_PACT}", "you each gain 1 TG")


def _blood_ready(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    agenda = state.agenda
    if agenda is None or BLOOD_PACT not in state.players[player_id].promissory_notes_in_play:
        return False
    owner = _note_owner(state, BLOOD_PACT)
    if owner is None or owner == player_id or _effect_for(state, BLOOD_DONE, player_id):
        return False
    mine, theirs = agenda.votes.get(player_id), agenda.votes.get(owner)
    return (
        mine is not None and theirs is not None and mine.outcome == theirs.outcome
        and mine.votes > 0 and theirs.votes > 0
        and not agenda_phase.single_vote(state, player_id)
    )


@on_event(
    GameEvent.AGENDA_VOTES_CAST, Moment.AFTER, HookSource(SOURCE_PROMISSORY, BLOOD_PACT),
    condition=_blood_ready, covers=f"promissory_notes:{BLOOD_PACT}",
    label="Blood Pact: 4 additional votes",
)
def blood_pact_votes(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Blood Pact: When you and the Empyrean player cast votes for the same outcome, cast 4
    additional votes for that outcome (both must cast >= 1 vote - F_empyrean blood-pact 1)."""
    agenda_phase.add_votes(state, _registry(), player_id, _BLOOD_VOTES)
    active_effects.add_effect(state, BLOOD_DONE, Duration.AGENDA, owner=player_id)
    ability_notes.note(state, player_id, f"promissory_notes:{BLOOD_PACT}", "+4 votes")


def _activated_empyrean_system(note: str) -> Any:
    def ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
        owner = _note_owner(state, note)
        return (
            ctx.get("player") == player_id and owner is not None and owner != player_id
            and note in state.players[player_id].promissory_notes_in_play
            and _has_units(state, owner, str(ctx.get("position") or ""))
        )

    return ready


def _return_note(state: GameState, player_id: str, note: str) -> None:
    owner = _note_owner(state, note)
    if owner is not None:
        promissory_notes.return_from_play(state, player_id, owner, note)


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_PROMISSORY, DARK_PACT),
    condition=_activated_empyrean_system(DARK_PACT), covers=f"promissory_notes:{DARK_PACT}",
    label="Dark Pact returns to the Empyrean player",
)
def dark_pact_return(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """If you activate a system that contains 1 or more of the Empyrean player's units, return this
    card to the Empyrean player (structures only count too - F_empyrean dark-pact 6)."""
    _return_note(state, player_id, DARK_PACT)


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_PROMISSORY, BLOOD_PACT),
    condition=_activated_empyrean_system(BLOOD_PACT), covers=f"promissory_notes:{BLOOD_PACT}",
    label="Blood Pact returns to the Empyrean player",
)
def blood_pact_return(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """If you activate a system that contains 1 or more of the Empyrean player's units, return this
    card to the Empyrean player (F_empyrean blood-pact 2, 3)."""
    _return_note(state, player_id, BLOOD_PACT)


# ============================================================================ Dynamo (flagship)


def _flagship_positions(state: GameState, player_id: str) -> list[str]:
    return sorted(
        position for position, system in state.systems.items()
        if system.space_units.get(player_id, {}).get("flagship", 0) > 0
    )


def _repairable(state: GameState, ctx: Mapping[str, Any]) -> int:
    """Damaged units of the type that just used SUSTAIN DAMAGE, capped by that use's count."""
    system = state.systems.get(str(ctx.get("position") or ""))
    if system is None:
        return 0
    zone = str(ctx.get("zone") or _SPACE)
    hurt = damaged_count(system, zone, str(ctx.get("player")), str(ctx.get("base_type")))
    return min(hurt, int(ctx.get("count") or 1))


def _funds(state: GameState, player_id: str) -> int:
    ready = payment.ready_planet_values(state, _registry(), player_id, "influence")
    return sum(ready.values()) + economy.spendable_trade_goods(state, player_id)


def _dynamo_in_range(state: GameState, player_id: str, position: str) -> bool:
    if not position:
        return False
    grid = _grid(state)
    for here in _flagship_positions(state, player_id):
        if here == position:
            return True
        if here in grid.positions and position in board_graph.neighbors_for_player(
            state, grid, player_id, here
        ):
            return True
    return False


def dynamo_limit(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """How many units the Dynamo may repair now (0 = no offer)."""
    if not _dynamo_in_range(state, player_id, str(ctx.get("position") or "")):
        return 0
    return min(_repairable(state, ctx), _funds(state, player_id) // _REPAIR_COST)


def _dynamo_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return dynamo_limit(state, player_id, ctx) > 0


def auto_payment(
    state: GameState, registry: StaticDataRegistry, player_id: str, cost: int
) -> tuple[list[str], int]:
    """⚠️ ASSUMPTION "Auto" payment (RULES.md 62.20): the smallest single ready planet that covers
    the cost, else the largest planets first, the rest in trade goods (least influence wasted)."""
    ready = payment.ready_planet_values(state, registry, player_id, "influence")
    covering = sorted((v, p) for p, v in ready.items() if v >= cost)
    if covering:
        return [covering[0][1]], 0
    chosen: list[str] = []
    paid = 0
    for value, planet in sorted(((v, p) for p, v in ready.items() if v > 0), reverse=True):
        if paid >= cost:
            break
        chosen.append(planet)
        paid += value
    return chosen, max(0, cost - paid)


def _mark_repaired(state: GameState, owner: str, base_type: str) -> None:
    """The combat's Sustain Damage record keeps the repaired unit: a Direct Hit played in the same
    window still destroys it (F_empyrean dynamo 3)."""
    combat = state.active_combat
    if combat is None:
        return
    combat.sustained_ships = [
        {**entry, "repaired": True}
        if entry.get("player") == owner and entry.get("base_type") == base_type else entry
        for entry in combat.sustained_ships
    ]


def dynamo_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Units to repair + influence (2 per unit). ⚠️ ASSUMPTION "Auto" = as many as affordable."""
    most = dynamo_limit(state, player_id, ctx)
    ready = payment.ready_planet_values(state, registry, player_id, "influence")
    planets = [(p, card_labels.describe_planet(state, registry, p), v)
               for p, v in sorted(ready.items())]
    spendable = economy.spendable_trade_goods(state, player_id)
    owner = str(ctx.get("player"))
    name = unit_name(state, registry, owner, str(ctx.get("base_type")))
    return [
        oi.number("repairs", f"{name}: units to repair", 1, max(1, most), auto=most),
        oi.payment_planets(planets, "influence", _REPAIR_COST * max(1, most),
                           hint=f"Pay {_REPAIR_COST} influence for each unit you repair."),
        oi.number("trade_goods", "Trade goods to spend", 0, spendable, auto=0),
    ]


# Cooperative (RULES.md 54.15): the damaged unit's owner requests the repair; the Empyrean pays
# the influence, so it picks the planets (owner_picks). Repairing own units is unchanged.
cooperative.register_pull(f"units:{FLAGSHIP}", owner_picks=True)


@on_event(
    GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, HookSource(SOURCE_UNIT, FLAGSHIP),
    optional=True, condition=_dynamo_ready, inputs=dynamo_inputs, covers=f"units:{FLAGSHIP}",
    label="Dynamo: repair for 2 influence",
)
def dynamo(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dynamo: After any player's unit in this system or an adjacent system uses SUSTAIN DAMAGE,
    you may spend 2 influence to repair that unit (each repair paid on its own - F_empyrean
    dynamo 4, 4.1; damage without SUSTAIN DAMAGE gives no offer - 2)."""
    registry = _registry()
    params = ctx.get("params") or {}
    repairs = int(params.get("repairs") or dynamo_limit(state, player_id, ctx))
    if repairs < 1 or repairs > dynamo_limit(state, player_id, ctx):
        raise ValueError("You cannot repair that many units.")
    cost = _REPAIR_COST * repairs
    planets = [str(p) for p in params.get("planets") or []]
    trade_goods = int(params.get("trade_goods") or 0)
    if not planets and not trade_goods:
        planets, trade_goods = auto_payment(state, registry, player_id, cost)
    paid = payment.validate_payment(state, registry, player_id, "influence", planets, trade_goods)
    if paid < cost:
        raise ValueError(f"Spend at least {cost} influence (you chose {paid}).")
    payment.apply_payment(state, player_id, planets, trade_goods)
    system = state.systems[str(ctx["position"])]
    zone, owner = str(ctx.get("zone") or _SPACE), str(ctx["player"])
    base_type = str(ctx["base_type"])
    hurt = damaged_count(system, zone, owner, base_type)
    set_damaged(system, zone, owner, base_type, hurt - repairs)
    _mark_repaired(state, owner, base_type)
    ability_notes.note(state, player_id, f"units:{FLAGSHIP}",
                       f"repaired {repairs} {unit_name(state, registry, owner, base_type)}")


# ============================================================================== Watcher (mech)


def watcher_mechs(state: GameState, player_id: str, rival: str) -> list[tuple[str, str]]:
    """``(position, zone)`` of every Empyrean mech in or adjacent to a system with ``rival``'s
    units (Empyrean's adjacency; one entry per mech) - F_empyrean watcher 2."""
    grid = _grid(state)
    rival_systems = {pos for pos in state.systems if _has_units(state, rival, pos)}
    found: list[tuple[str, str]] = []
    for position, system in sorted(state.systems.items()):
        near = {position}
        if position in grid.positions:
            near |= board_graph.neighbors_for_player(state, grid, player_id, position)
        if not near & rival_systems:
            continue
        found += [(position, _SPACE)] * system.space_units.get(player_id, {}).get("mech", 0)
        for planet, by in sorted(system.planet_units.items()):
            found += [(position, planet)] * by.get(player_id, {}).get("mech", 0)
    return found


@register(POINT_ACTION_CARD_CANCELLER, HookSource(SOURCE_UNIT, MECH), HookKind.PERMIT,
          covers=f"units:{MECH}")
def watcher_canceller(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Public: a Watcher in / next to the card player's units - the hold window opens."""
    rival = str(ctx.get("player") or "")
    return bool(rival) and rival != player_id and bool(watcher_mechs(state, player_id, rival))


def _watcher_helps(state: GameState, owner: str) -> list[str]:
    """Third players may ask / pay the Empyrean to cancel the held card (not its player)."""
    held = state.held_play
    if held is None:
        return []
    rival, _card = card_hold.target_of(held)
    return [pid for pid in state.players if pid not in (owner, rival)]


# Cooperative (RULES.md 54.15 e): a third player may ask / pay for the cancel; the Empyrean is
# still prompted (mutual) and picks the Watcher.
cooperative.register_pull_component("unit", MECH, _watcher_helps, mutual=True, owner_picks=True)


@faction_components.window_use("unit", MECH, holds=True)
def _watcher_window(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> str | None:
    held = state.held_play
    if held is None:
        return "The Watcher cancels an action card another player plays."
    rival, _card = card_hold.target_of(held)
    if rival == player_id:
        return "You cannot cancel your own action card."
    if not card_hold.can_respond(held, player_id):
        return "You can no longer respond to this card."
    if not watcher_mechs(state, player_id, rival):
        return "No Watcher is in or adjacent to a system with that player's units."
    return None


@register_effect_inputs(f"units:{MECH}")
def watcher_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """The Watcher to remove (on the map). ⚠️ ASSUMPTION "Auto" = the first one (board order)."""
    held = state.held_play
    if held is None:
        return []
    rival, _card = card_hold.target_of(held)
    seen: dict[tuple[str, str], int] = {}
    options: list[dict[str, Any]] = []
    for position, zone in watcher_mechs(state, player_id, rival):
        index = seen.get((position, zone), 0)
        seen[(position, zone)] = index + 1
        options.append(oi.option(
            f"{position}|{zone}|{index}", unit_name(state, registry, player_id, "mech"),
            meta=oi.unit_at(state, player_id, "mech", position=position,
                            planet=None if zone == _SPACE else zone),
        ))
    return [oi.choice("mech", "Watcher to remove", options,
                      auto=options[0]["value"] if options else None)]


@register_effect(f"units:{MECH}")
def watcher(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Watcher: You may remove this unit from a system that contains or is adjacent to another
    player's units to cancel an action card played by that player (Sabotage too - 1; no costs
    paid - 3; an ACTION card returns the action - 8)."""
    held = state.held_play
    if held is None:
        raise ValueError("There is no action card to cancel.")
    rival, _card = card_hold.target_of(held)
    eligible = watcher_mechs(state, player_id, rival)
    position, _, rest = str(params.get("mech") or "").partition("|")
    zone = rest.partition("|")[0]
    if not position and eligible:
        position, zone = eligible[0]
    if (position, zone) not in eligible:
        raise ValueError("Choose a Watcher in or adjacent to a system with that player's units.")
    unit_ops.remove_units(state, state.systems[position], zone, player_id, "mech", 1,
                          UnitCause.REMOVED)
    card_hold.cancel_by_component(state)
    ability_notes.note(state, player_id, f"units:{MECH}", "action card cancelled")


# ======================================================================= Void Tether (breakthrough)


def tether_tokens(state: GameState, owner: str) -> list[tuple[str, str]]:
    """``(a, b)`` borders that hold the owner's Void Tether tokens."""
    return [(a, b) for a, b, who in faction_tokens.borders(state, VOID_TETHER) if who == owner]


def border_neighbors(state: GameState, position: str) -> list[str]:
    """Systems that share an EDGE with ``position`` (hex distance 1 - not a wormhole link)."""
    grid = _grid(state)
    if position not in grid.positions:
        return []
    return sorted(
        other for other in grid.positions
        if other != position and grid.distance(position, other) == 1
    )


def _presence(state: GameState, player_id: str, position: str) -> bool:
    system = state.systems.get(position)
    return _has_units(state, player_id, position) or (
        system is not None and player_id in system.planet_owners.values()
    )


def _tether_place_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    position = str(ctx.get("position") or "")
    if ctx.get("player") != player_id or not position:
        return False
    if faction_tokens.supply_left(state, player_id, VOID_TETHER) <= 0 and not tether_tokens(
        state, player_id
    ):
        return False
    grid = _grid(state)
    near = {position}
    if position in grid.positions:
        near |= board_graph.neighbors_for_player(state, grid, player_id, position)
    if not any(_presence(state, player_id, pos) for pos in near):
        return False
    return bool(border_neighbors(state, position))


def _token_value(a: str, b: str) -> str:
    return f"{a}|{b}"


def tether_inputs(
    state: GameState, registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The token (new / one already placed) and the border = the other system, picked on the map.

    ⚠️ ASSUMPTION "Auto" (RULES.md 62.20): a token from supply, else the first placed one; the first
    neighbouring system with another player's units, else the first neighbour."""
    position = str(ctx.get("position") or "")
    tokens: list[dict[str, Any]] = []
    if faction_tokens.supply_left(state, player_id, VOID_TETHER) > 0:
        tokens.append(oi.option(_NEW_TOKEN, "Place a Void Tether token from your supply"))
    for a, b in tether_tokens(state, player_id):
        tokens.append(oi.option(
            _token_value(a, b),
            f"Move the Void Tether between {card_labels.describe_system(state, registry, a)} and "
            f"{card_labels.describe_system(state, registry, b)}",
        ))
    others = border_neighbors(state, position)
    rivals = [
        pos for pos in others
        if any(_has_units(state, pid, pos) for pid in state.players if pid != player_id)
    ]
    return [
        oi.choice("token", "Void Tether token", tokens,
                  auto=tokens[0]["value"] if tokens else None),
        oi.choice("border", "Border: the system on the other side",
                  [_system_option(state, registry, pos) for pos in others],
                  auto=next(iter(rivals or others), None)),
    ]


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    optional=True, condition=_tether_place_ready, inputs=tether_inputs,
    covers=f"breakthroughs:{BREAKTHROUGH}", label="Void Tether: place a token on a border",
)
def void_tether_place(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Void Tether: When you activate a system that contains or is adjacent to a unit or planet you
    control, you may place or move 1 of your void tether tokens onto a border that system shares
    with another system."""
    position = str(ctx["position"])
    params = ctx.get("params") or {}
    other = str(params.get("border") or "")
    if other not in border_neighbors(state, position):
        raise ValueError("Choose a system that shares a border with the active system.")
    token = str(params.get("token") or _NEW_TOKEN)
    target = faction_tokens.border_zone(position, other)
    board_graph.ensure_system(state, target[0])
    if token == _NEW_TOKEN:
        faction_tokens.place(state, player_id, VOID_TETHER, *target)
    else:
        a, _, b = token.partition("|")
        if (a, b) not in tether_tokens(state, player_id):
            raise ValueError("Choose one of your Void Tether tokens.")
        source = faction_tokens.border_zone(a, b)
        if source == target:
            return
        faction_tokens.move(state, player_id, VOID_TETHER, source, *target)
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                       f"Void Tether between {position} and {other}")


def _tether_allow_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    activator = str(ctx.get("player") or "")
    return (
        bool(activator) and activator != player_id and activator in state.players
        and bool(tether_tokens(state, player_id))
        and not any(e.key == TETHER_ALLOWED and e.owner == activator
                    and e.data.get("by") == player_id for e in state.active_effects)
    )


# Cooperative (RULES.md 54.15): the activating player requests the crossing. The placement hook
# shares the key but fires only on the Empyrean's own activation (owner = beneficiary: unchanged).
cooperative.register_pull(f"breakthroughs:{BREAKTHROUGH}")


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    optional=True, condition=_tether_allow_ready, covers=f"breakthroughs:{BREAKTHROUGH}",
    label="Void Tether: allow them to cross your tethers",
)
def void_tether_allow(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """...other players do not treat those systems as adjacent to each other unless you allow it.
    ⚠️ ASSUMPTION (RULES.md 62.20): the permission lasts for that player's tactical action."""
    activator = str(ctx["player"])
    active_effects.add_effect(state, TETHER_ALLOWED, Duration.TACTICAL_ACTION, owner=activator,
                              data={"by": player_id})
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                       f"{_name(state, activator)} may cross your Void Tethers")


# Every player owns the cut (it binds OTHER players than the token's owner - RULES.md 61.7 layer 4).
_TETHER_CUT = rules_hooks.declare_rule_source(f"breakthroughs:{BREAKTHROUGH}:cut")


@register(POINT_ADJACENCY_CUT_FOR_PLAYER, _TETHER_CUT, HookKind.FORBID,
          covers=f"breakthroughs:{BREAKTHROUGH}")
def void_tether_cut(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> set[str]:
    """...other players do not treat those systems as adjacent to each other unless you allow it
    (even with matching wormholes - void-tether 1; the tokens stay after elimination - 2)."""
    position = str(ctx.get("position") or "")
    found: set[str] = set()
    for a, b, owner in faction_tokens.borders(state, VOID_TETHER):
        if owner == player_id or position not in (a, b):
            continue
        if any(e.key == TETHER_ALLOWED and e.owner == player_id and e.data.get("by") == owner
               for e in state.active_effects):
            continue
        found.add(b if position == a else a)
    return found
