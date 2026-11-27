"""The Ghosts of Creuss — every faction component (RULES.md 62.19).

Texts in docstrings are quotes from the assets (``catalog.faction_bundle("ghost")``, units
``ghost_flagship`` / ``ghost_mech``, breakthrough ``ghostbt``). Rulings: ``docs/rules_tirules/
F_creuss.md`` (cross-checked: ``R_wormholes``, ``R_neighbors``, ``C_agendas``, ``R_entropic_scars``,
``R_abilities``, ``C_technology``, ``F_mentak``, ``F_muaat``, ``F_saar``, ``F_winnu``).
Engine points used/added for Creuss: player-dependent adjacency (``adjacency.extra_for_player``,
RULES.md 61.7), immunity to wormhole laws (``movement.wormhole_laws_immune``), wormholes carried
by units (``board.unit_wormholes``), Creuss wormhole tokens as faction tokens (RULES.md 61.6,
``faction_tokens.CREUSS_WORMHOLES``) and the system swap (``core/system_swap``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    battle,
    board_graph,
    capacity,
    cooperative,
    entropic_scar,
    faction_components,
    faction_tokens,
    fracture,
    leaders,
    production,
    promissory_play,
    rules_hooks,
    system_swap,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count
from src.core.faction_setup import OFF_BOARD_HOME
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import ActiveCombat, GameState
from src.core.hex_grid import HexGrid
from src.core.hooks import card_labels
from src.core.hooks.card_helpers import place_from_reinforcements
from src.core.nexus import ACTIVE_PLANET_ID, LOCKED_PLANET_ID
from src.core.production import reinforcements_left
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_ADJACENCY_EXTRA_FOR_PLAYER,
    POINT_BOARD_UNIT_WORMHOLES,
    POINT_MOVEMENT_EXTRA_ADJACENT,
    POINT_MOVEMENT_MOVE_VALUE,
    POINT_MOVEMENT_MOVES_SEPARATELY,
    POINT_MOVEMENT_WORMHOLE_LAWS_IMMUNE,
    POINT_PRODUCTION_COST,
    POINT_PRODUCTION_SYSTEM_VALUE,
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
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

FACTION = "ghost"
QUANTUM = "quantum_entanglement"
SLIPSTREAM = "slipstream"
CREUSS_GATE = "creuss_gate"
SPLICER = "ds"
GENERATOR = "wg"
AGENT = "ghostagent"
COMMANDER = "ghostcommander"
HERO = "ghosthero"
IFF = "iff"
FLAGSHIP = "ghost_flagship"
MECH = "ghost_mech"
BREAKTHROUGH = "ghostbt"

TAIVRA_LINK = f"leaders:{AGENT}:link"  # global effect: the hub system of this tactical action
IFF_PLAYED = f"promissory_notes:{IFF}:played"  # once per timing window (R_abilities)
_LINKED = ("ALPHA", "BETA")  # Quantum Entanglement / Slipstream / Sai Seravus unlock
_DELTA = "DELTA"
_SPACE = "space"
_FIGHTER = "fighter"
_DAMAGED_SUFFIX = ":damaged"
_COMMANDER_SYSTEMS = 3  # "Have units in 3 systems"
_SLIPSTREAM_BONUS = 1  # "Apply +1 to the move value"
_MAX_ROOM = 64  # safety cap of the free-capacity scan (no board holds more)


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _grid(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    """The game map (bound by the API - all tiles); in unit tests - a grid from the state."""
    return board_graph.bound_grid() or grid_from_state(state, registry)


def creuss_player(state: GameState) -> str | None:
    """The Creuss player at the table (owner of the wormhole tokens), or None."""
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


def _system_option(state: GameState, registry: StaticDataRegistry, position: str) -> dict[str, Any]:
    return oi.option(position, card_labels.describe_system(state, registry, position))


def _real_systems(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Board positions holding a real system tile (no hyperlanes, no empty slots)."""
    found: list[str] = []
    for position in board_graph.board_positions(state):
        definition = registry.systems.get(board_graph.system_id_at(state, position))
        if definition is None or (definition.name or "").strip().lower() == "hyperlane":
            continue
        found.append(position)
    return found


# ======================================================================= Creuss wormhole tokens


def token_kinds(registry: StaticDataRegistry) -> list[str]:
    """Creuss wormhole tokens of the active sources (alpha/beta base, gamma PoK) - asset data."""
    from src.core.components import ComponentCategory

    tokens = registry.catalog.all(ComponentCategory.TOKEN)
    return [kind for kind in faction_tokens.CREUSS_WORMHOLES if kind in tokens]


def token_position(state: GameState, owner: str, kind: str) -> str | None:
    """System with the owner's token ``kind`` on the board, or None (in reinforcements)."""
    found = faction_tokens.tokens_of(state, owner, kind)
    return found[0][0] if found else None


def _token_label(kind: str) -> str:
    return f"{faction_tokens.CREUSS_WORMHOLES[kind].lower()} wormhole token"


def token_options(
    state: GameState, registry: StaticDataRegistry, owner: str
) -> list[dict[str, Any]]:
    """Chips "place <type> token" (in reinforcements) / "move <type> token (from system X)"."""
    options: list[dict[str, Any]] = []
    for kind in token_kinds(registry):
        where = token_position(state, owner, kind)
        label = f"Place the {_token_label(kind)}" if where is None else (
            f"Move the {_token_label(kind)} (now in "
            f"{card_labels.describe_system(state, registry, where)})"
        )
        options.append(oi.option(kind, label))
    return options


def _auto_token(state: GameState, registry: StaticDataRegistry, owner: str) -> str | None:
    """⚠️ ASSUMPTION (RULES.md 62.19): the first token in reinforcements, else the first one."""
    kinds = token_kinds(registry)
    spare = [k for k in kinds if token_position(state, owner, k) is None]
    pool = spare or kinds
    return pool[0] if pool else None


def _home_positions(state: GameState, registry: StaticDataRegistry) -> set[str]:
    """Home systems of the players and of eliminated players (F_creuss WG Ω 1, IFF 4)."""
    homes = board_graph.home_positions(state, registry)
    ids = board_graph.home_system_ids(state, registry)
    homes |= {pos for pos in board_graph.board_positions(state)
              if board_graph.system_id_at(state, pos) in ids}
    return homes


def _foreign_ships(state: GameState, player_id: str, position: str) -> bool:
    """Another player's ships in the system - neutral ships count too (F_creuss WG Ω 3)."""
    system = state.systems.get(position)
    if system is None:
        return False
    return any(
        owner != player_id and any(n > 0 and is_space_unit(bt) for bt, n in units.items())
        for owner, units in system.space_units.items()
    )


def token_systems(state: GameState, registry: StaticDataRegistry, resolver: str) -> list[str]:
    """Wormhole Generator / Creuss IFF: "into either a system that contains a planet you control
    or a non-home system that does not contain another player's ships" (``resolver`` = "you").

    The Fracture is allowed (IFF 5, WG Ω 2); an entropic scar too (the token is discarded - Ω 4).
    """
    homes = _home_positions(state, registry)
    found: list[str] = []
    for position in _real_systems(state, registry):
        system = state.systems.get(position)
        owns_planet = system is not None and resolver in system.planet_owners.values()
        if owns_planet or (position not in homes and not _foreign_ships(state, resolver, position)):
            found.append(position)
    return found


def _auto_system(state: GameState, candidates: list[str], resolver: str) -> str | None:
    """⚠️ ASSUMPTION (RULES.md 62.19): the first legal system with the resolver's units, else the
    first legal system (board order)."""
    with_units = [pos for pos in candidates if _has_units(state, resolver, pos)]
    pool = with_units or candidates
    return pool[0] if pool else None


def place_or_move_token(
    state: GameState, registry: StaticDataRegistry, owner: str, kind: str, position: str
) -> str:
    """Places a Creuss token from reinforcements or moves it (MUTATES ``state``); the ONE place for
    Wormhole Generator, Creuss IFF and Icarus Drive. Returns a note for the feed.

    Into the same system = the token stays (WG 2.1). Into an entropic scar: discarded to the Creuss
    reinforcements (R_entropic_scars 4.1/4.2).
    """
    if kind not in token_kinds(registry):
        raise ValueError("Choose a Creuss wormhole token ('token').")
    board_graph.ensure_system(state, position)
    source = token_position(state, owner, kind)
    if source == position:
        return f"{_token_label(kind)} stays in system {position}"
    if source is None:
        faction_tokens.place(state, owner, kind, position, _SPACE)
    else:
        faction_tokens.move(state, owner, kind, (source, _SPACE), position, _SPACE)
    if not entropic_scar.accepts_wormhole_token(state, position, registry):
        faction_tokens.remove(state, position, _SPACE, kind)
        return f"{_token_label(kind)} discarded in the entropic scar {position}"
    return f"{_token_label(kind)} to system {position}"


def _token_inputs(
    state: GameState, registry: StaticDataRegistry, owner: str, systems: list[str], resolver: str
) -> list[dict[str, Any]]:
    return [
        oi.choice("token", "Creuss wormhole token", token_options(state, registry, owner),
                  auto=_auto_token(state, registry, owner)),
        oi.choice("position", "System for the wormhole token",
                  [_system_option(state, registry, pos) for pos in systems],
                  auto=_auto_system(state, systems, resolver)),
    ]


# =========================================================================== Quantum Entanglement


@register(POINT_ADJACENCY_EXTRA_FOR_PLAYER, HookSource(SOURCE_FACTION, FACTION), HookKind.FORBID,
          covers=f"abilities:{QUANTUM}")
def quantum_entanglement(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> set[str]:
    """Quantum Entanglement: You treat all systems that contain either an alpha or beta wormhole as
    adjacent to each other (layer 3 - only for Creuss, RULES.md 61.7)."""
    grid = ctx.get("grid")
    if not isinstance(grid, HexGrid):
        return set()
    linked = grid.wormhole_positions("ALPHA") | grid.wormhole_positions("BETA")
    position = str(ctx.get("position") or "")
    return linked - {position} if position in linked else set()


@register(POINT_MOVEMENT_WORMHOLE_LAWS_IMMUNE, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers=f"abilities:{QUANTUM}")
def entanglement_unstoppable(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Game effects cannot prevent you from using this ability (Enforced Travel Ban, Nexus
    Sovereignty - F_creuss QE 1, C_agendas)."""
    return True


# ===================================================================================== Slipstream


@register(POINT_MOVEMENT_MOVE_VALUE, HookSource(SOURCE_FACTION, FACTION), HookKind.MODIFY,
          covers=f"abilities:{SLIPSTREAM}")
def slipstream(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Slipstream: During your tactical actions: Apply +1 to the move value of each of your ships
    that starts its movement in your home system or in a system that contains either an alpha or
    beta wormhole. (Not the Creuss Gate, not gamma or delta - F_creuss slipstream 2.)"""
    registry = _registry()
    start = str(ctx.get("from") or "")
    if not start or state.active_system is None:
        return 0
    home = board_graph.home_positions_by_player(state, registry).get(player_id, [])
    if start in home or board_graph.wormholes_at(state, registry, start) & set(_LINKED):
        return _SLIPSTREAM_BONUS
    return 0


# Creuss Gate: board setup (RULES.md 17 - gate 17 on the home slot, home 51 off-board, the gate is
# not a home system: ``board_graph.home_system_ids``; frontier token: ``place_frontier_tokens``).
rules_hooks.declare_core_rule(f"abilities:{CREUSS_GATE}")


# ============================================================================= Dimensional Splicer


def _opponent(combat: ActiveCombat, player_id: str) -> str:
    return combat.defender if player_id == combat.attacker else combat.attacker


def _space_combat(state: GameState, player_id: str) -> ActiveCombat | None:
    combat = state.active_combat
    if combat is None or combat.kind != _SPACE:
        return None
    if player_id not in (combat.attacker, combat.defender):
        return None
    return combat


def _enemy_targets(
    state: GameState, combat: ActiveCombat, player_id: str
) -> dict[tuple[str, bool], int]:
    """Opponent's ships ``(type, damaged) -> count`` - Creuss picks the exact ship (F_creuss 3)."""
    system = state.systems.get(combat.position)
    victim = _opponent(combat, player_id)
    units = system.space_units.get(victim, {}) if system is not None else {}
    found: dict[tuple[str, bool], int] = {}
    for bt, n in units.items():
        if n <= 0 or not is_space_unit(bt):
            continue
        hurt = damaged_count(system, _SPACE, victim, bt)
        if n - hurt > 0:
            found[(bt, False)] = n - hurt
        if hurt > 0:
            found[(bt, True)] = hurt
    return found


def _splicer_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    combat = _space_combat(state, player_id)
    return (
        ctx.get("kind") == _SPACE
        and combat is not None
        and bool(board_graph.wormholes_at(state, _registry(), combat.position))
        and _has_ships(state, player_id, combat.position)
        and bool(_enemy_targets(state, combat, player_id))
    )


def _target_value(base_type: str, damaged: bool) -> str:
    return f"{base_type}{_DAMAGED_SUFFIX}" if damaged else base_type


def splicer_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The opponent's ship that takes the hit (Creuss chooses; damaged copies are separate).

    ⚠️ ASSUMPTION "Auto" (RULES.md 62.19): the most expensive ship that cannot cancel the hit
    (damaged or without SUSTAIN DAMAGE), else the most expensive ship.
    """
    combat = state.active_combat
    if combat is None:
        return []
    victim = _opponent(combat, player_id)
    owner = state.players.get(victim)
    options: list[dict[str, Any]] = []
    ranked: list[tuple[bool, float, str]] = []
    for (bt, hurt), n in sorted(_enemy_targets(state, combat, player_id).items()):
        meta = oi.unit_meta(bt, victim, owner.faction if owner else None,
                            owner.color if owner else None, n)
        meta["damaged"] = hurt
        name = unit_name(state, registry, victim, bt)
        value = _target_value(bt, hurt)
        options.append(oi.option(value, f"{name} (damaged)" if hurt else name, meta=meta))
        unit = resolve_unit_variant(
            registry, owner.faction if owner else None, owner.technologies if owner else [], bt
        )
        cancels = bool(unit is not None and unit.sustain_damage and not hurt)
        cost = float(unit.cost or 0) if unit is not None else 0.0
        ranked.append((cancels, -cost, value))
    auto = min(ranked)[2] if ranked else None
    return [oi.choice("target", "Opponent's ship you assign the hit to", options, auto=auto)]


@on_event(
    GameEvent.COMBAT, Moment.START, HookSource(SOURCE_TECHNOLOGY, SPLICER),
    optional=True, condition=_splicer_ready, inputs=splicer_inputs,
    covers=f"technologies:{SPLICER}", label="Dimensional Splicer",
)
def dimensional_splicer(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dimensional Splicer: At the start of space combat in a system that contains a wormhole and 1
    or more of your ships, you may produce 1 hit and assign it to 1 of your opponent's ships.

    One hit even with several wormholes (F_creuss 2); the opponent only decides whether THAT ship
    uses SUSTAIN DAMAGE (5) or plays Shields Holding (4) in the ASSIGN step."""
    combat = _space_combat(state, player_id)
    if combat is None:
        raise ValueError("Dimensional Splicer is used at the start of a space combat you fight in.")
    raw = str((ctx.get("params") or {}).get("target") or "")
    hurt = raw.endswith(_DAMAGED_SUFFIX)
    target = raw[: -len(_DAMAGED_SUFFIX)] if hurt else raw
    if (target, hurt) not in _enemy_targets(state, combat, player_id):
        raise ValueError("Choose 1 of your opponent's ships in the active system.")
    battle.add_start_hits(
        state, _opponent(combat, player_id), 1, only=[target], damaged=hurt, chooser=player_id,
        label="Dimensional Splicer",
    )
    ability_notes.note(state, player_id, f"technologies:{SPLICER}", "1 hit")


# ============================================================================= Wormhole Generator


def _generator_helps(state: GameState, owner: str) -> list[str]:
    return [pid for pid in state.players if pid != owner]


# Cooperative (RULES.md 54.15 e): another player may ask / pay for a wormhole token. ACTION:
# requested only during the Creuss' turn and uses the Creuss' component action; the Creuss picks
# the token and the system (owner_picks).
cooperative.register_pull_component(
    "technology", GENERATOR, _generator_helps, mutual=True, owner_picks=True
)


@register_effect_inputs(f"technologies:{GENERATOR}")
def generator_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    return _token_inputs(state, registry, player_id, token_systems(state, registry, player_id),
                         player_id)


@register_effect(f"technologies:{GENERATOR}")
def wormhole_generator(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Wormhole Generator: ACTION: Exhaust this card to place or move a Creuss wormhole token into
    either a system that contains a planet you control or a non-home system that does not contain
    another player's ships."""
    player = state.players[player_id]
    if GENERATOR in player.exhausted_technologies:
        raise ValueError("Wormhole Generator is exhausted.")
    position = str(params.get("position") or "")
    if position not in token_systems(state, registry, player_id):
        raise ValueError("Choose a system with a planet you control or a non-home system "
                         "without another player's ships.")
    # "Exhaust this card" - also inside an entropic scar (F_creuss WG Ω 4).
    faction_components.pay_cost(state, registry, player_id, faction_components.TECHNOLOGY,
                                GENERATOR)
    detail = place_or_move_token(state, registry, player_id, str(params.get("token") or ""),
                                 position)
    ability_notes.note(state, player_id, f"technologies:{GENERATOR}", detail)


# ========================================================================= Creuss IFF (promissory)


@promissory_play.condition(IFF)
def _iff_condition(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, window: OpenWindow
) -> str | None:
    if window.subject != player_id:
        return "Creuss IFF is played at the start of your turn during the action phase."
    if active_effects.has_effect(state, player_id, IFF_PLAYED):
        return "Creuss IFF was already played in this timing window."  # R_abilities, F_creuss 1.1
    if creuss_player(state) is None:
        return "The Creuss player is not in the game."
    return None


@register_effect_inputs(f"promissory_notes:{IFF}")
def iff_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    owner = creuss_player(state)
    if owner is None:
        return []
    return _token_inputs(state, registry, owner, token_systems(state, registry, player_id),
                         player_id)


@register_effect(f"promissory_notes:{IFF}")
def creuss_iff(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Creuss IFF: At the start of your turn during the action phase: Place or move a Creuss
    wormhole token into either a system that contains a planet you control or a non-home system
    that does not contain another player's ships. Then, return this card to the Creuss player
    (return - ``promissory_play``; works without Wormhole Generator - F_creuss 3)."""
    owner = creuss_player(state)
    if owner is None:
        raise ValueError("The Creuss player is not in the game.")
    position = str(params.get("position") or "")
    if position not in token_systems(state, registry, player_id):
        raise ValueError("Choose a system with a planet you control or a non-home system "
                         "without another player's ships.")
    active_effects.add_effect(state, IFF_PLAYED, Duration.TURN, owner=player_id)
    detail = place_or_move_token(state, registry, owner, str(params.get("token") or ""), position)
    ability_notes.note(state, player_id, f"promissory_notes:{IFF}", detail)


# ============================================================================ Hil Colish (flagship)


@register(POINT_BOARD_UNIT_WORMHOLES, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.FORBID,
          covers=f"units:{FLAGSHIP}")
def hil_colish(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Hil Colish: This ship's system contains a delta wormhole. (Not a token - an entropic scar
    does not cancel it, F_creuss 9; "may move before or after your other ships" = order of the
    fleet moves, the map is re-synced before each one - RULES.md 62.19.)"""
    return {
        f"{position}|{_DELTA}" for position, system in state.systems.items()
        if system.space_units.get(player_id, {}).get("flagship", 0) > 0
    }


@register(POINT_MOVEMENT_MOVES_SEPARATELY, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.PERMIT,
          covers=f"units:{FLAGSHIP}")
def hil_colish_moves_separately(
    _state: GameState, _player_id: str, ctx: Mapping[str, Any]
) -> bool:
    """During movement, this ship may move before or after your other ships (separate fleet move;
    an Ion Storm it used flips right after it - C_exploration_cards ion-storm 2.1)."""
    return ctx.get("base_type") == "flagship"


# ============================================================================== Icarus Drive (mech)


def _mechs(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """``(position, zone)`` of every Creuss mech on the board (one entry per mech)."""
    found: list[tuple[str, str]] = []
    for position, system in sorted(state.systems.items()):
        found += [(position, _SPACE)] * system.space_units.get(player_id, {}).get("mech", 0)
        for planet, by in sorted(system.planet_units.items()):
            found += [(position, planet)] * by.get(player_id, {}).get("mech", 0)
    return found


def _icarus_ready(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return bool(_mechs(state, player_id)) and bool(token_kinds(_registry()))


def icarus_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The mech to remove (on the map - it need not be in the active system, F_creuss 1) and the
    token. ⚠️ ASSUMPTION "Auto": the first mech in board order (RULES.md 62.19)."""
    seen: dict[tuple[str, str], int] = {}
    options: list[dict[str, Any]] = []
    for position, zone in _mechs(state, player_id):
        index = seen.get((position, zone), 0)
        seen[(position, zone)] = index + 1
        options.append(oi.option(
            f"{position}|{zone}|{index}", unit_name(state, registry, player_id, "mech"),
            meta=oi.unit_at(state, player_id, "mech", position=position,
                            planet=None if zone == _SPACE else zone),
        ))
    return [
        oi.choice("mech", "Icarus Drive to remove", options,
                  auto=options[0]["value"] if options else None),
        oi.choice("token", "Creuss wormhole token", token_options(state, registry, player_id),
                  auto=_auto_token(state, registry, player_id)),
    ]


# Cooperative (RULES.md 54.15 e): the activating player may ask / pay for the token in the mech's
# system; the Creuss is still offered it (mutual) and picks the mech and the token.
cooperative.register_pull(f"units:{MECH}", mutual=True, owner_picks=True)


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_UNIT, MECH),
    optional=True, condition=_icarus_ready, inputs=icarus_inputs, covers=f"units:{MECH}",
    label="Icarus Drive: wormhole token",
)
def icarus_drive(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Icarus Drive: After any player activates a system, you may remove this unit from the game
    board to place or move a Creuss wormhole token into this system (the MECH's system - F_creuss
    2; the WG system rules do not apply)."""
    registry = _registry()
    params = ctx.get("params") or {}
    position, _, rest = str(params.get("mech") or "").partition("|")
    zone = rest.partition("|")[0]
    if (position, zone) not in _mechs(state, player_id):
        raise ValueError("Choose 1 of your mechs on the game board ('mech').")
    unit_ops.remove_units(state, state.systems[position], zone, player_id, "mech", 1,
                          UnitCause.REMOVED)
    detail = place_or_move_token(state, registry, player_id, str(params.get("token") or ""),
                                 position)
    ability_notes.note(state, player_id, f"units:{MECH}", detail)


# ========================================================================= Emissary Taivra (agent)


def _taivra_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    position = str(ctx.get("position") or "")
    registry = _registry()
    return (
        bool(position)
        and bool(board_graph.wormholes_at(state, registry, position) - {_DELTA})
        and leaders.is_ready(state, registry, player_id, AGENT)
    )


# Cooperative agent (RULES.md 54.15): helps "that player" - requested, not pushed.
cooperative.register_pull(f"leaders:{AGENT}")


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    optional=True, condition=_taivra_ready, covers=f"leaders:{AGENT}",
    label="Emissary Taivra: link wormholes",
)
def emissary_taivra(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Emissary Taivra: After a player activates a system that contains a non-delta wormhole: You
    may exhaust this card; if you do, that system is adjacent to all other systems that contain a
    wormhole during this tactical action (global effect - ``action_adjacency``, all players)."""
    position = str(ctx.get("position") or "")
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT,
                                {"position": position})
    active_effects.add_effect(state, TAIVRA_LINK, Duration.TACTICAL_ACTION,
                              data={"position": position, "by": player_id})
    ability_notes.note(state, player_id, f"leaders:{AGENT}", f"system {position} linked")


def _wormhole_positions(grid: HexGrid) -> set[str]:
    found: set[str] = set()
    for kind in ("ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA", "ETA", "IOTA", "THETA"):
        found |= grid.wormhole_positions(kind)
    return found


@register(POINT_MOVEMENT_EXTRA_ADJACENT, HookSource(SOURCE_EFFECT, TAIVRA_LINK), HookKind.FORBID)
def taivra_link(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> set[str]:
    """The linked system is adjacent to every other system with ANY wormhole (delta, epsilon,
    inactive Wormhole Nexus - F_creuss taivra 1, 3) for the rest of the tactical action."""
    grid = board_graph.bound_grid()
    if grid is None:
        return set()
    hubs = {str(e.data.get("position")) for e in state.active_effects if e.key == TAIVRA_LINK}
    wormholes = _wormhole_positions(grid)
    position = str(ctx.get("position") or "")
    found: set[str] = set()
    if position in hubs:
        found |= wormholes - {position}
    if position in wormholes:
        found |= hubs - {position}
    return found


# ======================================================================= Sai Seravus (commander)


@leaders.register_unlock(COMMANDER)
def _seravus_unlocked(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have units in 3 systems that contain alpha or beta wormholes (tokens count - 6)."""
    return sum(
        1 for position in state.systems
        if _has_units(state, player_id, position)
        and board_graph.wormholes_at(state, registry, position) & set(_LINKED)
    ) >= _COMMANDER_SYSTEMS


def moved_through_wormhole(
    state: GameState, registry: StaticDataRegistry, route: list[str]
) -> bool:
    """Whether a route used a wormhole: a hop between 2 systems that both contain a wormhole and do
    not share an edge (wormhole edge, Quantum Entanglement, Taivra). A system crossed without
    using its wormhole does not count (F_creuss seravus 3). ⚠️ ASSUMPTION (RULES.md 62.19)."""
    grid = _grid(state, registry)
    for a, b in zip(route, route[1:], strict=False):
        if not (board_graph.wormholes_at(state, registry, a)
                and board_graph.wormholes_at(state, registry, b)):
            continue
        if a not in grid.positions or b not in grid.positions or grid.distance(a, b) != 1:
            return True
    return False


def _carriers(state: GameState, registry: StaticDataRegistry, player_id: str,
              ships: Mapping[str, Any]) -> int:
    player = state.players[player_id]
    total = 0
    for base_type, count in ships.items():
        unit = resolve_unit_variant(registry, player.faction, player.technologies, base_type)
        if unit is not None and (unit.capacity_value or 0) > 0:
            total += int(count)
    return total


def _fighter_room(state: GameState, registry: StaticDataRegistry, player_id: str,
                  position: str) -> int:
    """Fighters that still fit the unused capacity in the system (dock fighter room too - 1.2;
    Fighter II overflow does not create room - "unused capacity")."""
    report = capacity.capacity_report(state, registry, position, player_id)
    report.fighters_overflow_to_fleet = False
    have = report.cargo.get(_FIGHTER, 0)
    room = 0
    while room < _MAX_ROOM and report.excess_for({**report.cargo, _FIGHTER: have + room + 1}) == 0:
        room += 1
    return room


def seravus_limit(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """How many fighters Sai Seravus may place after this move (0 = no offer)."""
    if ctx.get("player") != player_id:
        return 0
    registry = _registry()
    route = [str(p) for p in ctx.get("route") or []]
    position = str(ctx.get("position") or "")
    if not position or not moved_through_wormhole(state, registry, route):
        return 0
    left = reinforcements_left(state, player_id, _FIGHTER)
    limit = min(_carriers(state, registry, player_id, ctx.get("ships") or {}),
                _fighter_room(state, registry, player_id, position))
    return limit if left is None else min(limit, left)


def _seravus_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return seravus_limit(state, player_id, ctx) > 0


def seravus_inputs(
    state: GameState, _registry_: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION "Auto" = the maximum (RULES.md 62.19)."""
    most = seravus_limit(state, player_id, ctx)
    return [oi.number("fighters", "Fighters to place with your ships", 0, most, auto=most)]


@on_event(
    GameEvent.SHIPS_MOVED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_seravus_ready, inputs=seravus_inputs, covers=f"leaders:{COMMANDER}",
    label="Sai Seravus: place fighters",
)
def sai_seravus(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Sai Seravus: After your ships move: For each ship that has a capacity value and moved through
    1 or more wormholes, you may place 1 fighter from your reinforcements with that ship if you have
    unused capacity in the active system (any kind of move - F_creuss seravus 2)."""
    count = int((ctx.get("params") or {}).get("fighters", 0) or 0)
    if count <= 0:
        return
    if count > seravus_limit(state, player_id, ctx):
        raise ValueError("Too many fighters for your ships and their unused capacity.")
    position = str(ctx["position"])
    place_from_reinforcements(state, state.systems[position], _SPACE, player_id, _FIGHTER, count)
    ability_notes.note(state, player_id, f"leaders:{COMMANDER}", f"placed {count} fighter(s)")


# ============================================= Riftwalker Meian — Singularity Reactor (hero)


def _never_swapped(state: GameState, registry: StaticDataRegistry, position: str) -> bool:
    """The Creuss system, Ahk Creuxx (off-board homes, also the Rebellion home - F_creuss 3), the
    Wormhole Nexus and The Fracture."""
    if fracture.is_fracture_position(position):
        return True
    system_id = board_graph.system_id_at(state, position)
    if system_id in OFF_BOARD_HOME.values():
        return True
    definition = registry.systems.get(system_id)
    planets = set(definition.planets) if definition is not None else set()
    return bool(planets & {ACTIVE_PLANET_ID, LOCKED_PLANET_ID})


def swap_candidates(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    """Systems that contain wormholes or your units, minus the never-swapped ones."""
    return [
        position for position in _real_systems(state, registry)
        if not _never_swapped(state, registry, position)
        and (board_graph.wormholes_at(state, registry, position)
             or _has_units(state, player_id, position))
    ]


def _unit_count(state: GameState, player_id: str, position: str) -> int:
    system = state.systems.get(position)
    if system is None:
        return 0
    return sum(system.space_units.get(player_id, {}).values()) + sum(
        n for by in system.planet_units.values() for n in by.get(player_id, {}).values()
    )


@faction_components.blocker("leader", HERO)
def _hero_blocker(state: GameState, registry: StaticDataRegistry, player_id: str) -> str | None:
    if len(swap_candidates(state, registry, player_id)) < 2:
        return "You need 2 systems that contain wormholes or your units to swap."
    return None


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """2 systems on the map. ⚠️ ASSUMPTION "Auto" (RULES.md 62.19): first = the candidate with the
    most of your units, second = the first other candidate in board order."""
    candidates = swap_candidates(state, registry, player_id)
    options = [_system_option(state, registry, pos) for pos in candidates]
    first = max(candidates, key=lambda p: (_unit_count(state, player_id, p), -candidates.index(p)),
                default=None)
    second = next((p for p in candidates if p != first), None)
    return [
        oi.choice("first", "First system to swap", options, auto=first),
        oi.choice("second", "Second system to swap", options, auto=second),
    ]


@register_effect(f"leaders:{HERO}")
def singularity_reactor(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Riftwalker Meian — Singularity Reactor: ACTION: Swap the positions of any 2 non-Fracture
    systems that contain wormholes or your units, other than the Creuss system, Ahk Creuxx system,
    or the Wormhole Nexus. Then, purge this card (purge - ``faction_components``).

    Units and tokens move with their systems (F_creuss 1, 2) - ``system_swap``."""
    first, second = str(params.get("first") or ""), str(params.get("second") or "")
    candidates = swap_candidates(state, registry, player_id)
    if first not in candidates or second not in candidates:
        raise ValueError("Choose 2 systems that contain wormholes or your units.")
    system_swap.swap_systems(state, first, second)
    ability_notes.note(state, player_id, f"leaders:{HERO}", f"systems {first} and {second} swapped")


# ================================================================ Particle Synthesis (breakthrough)


@register(POINT_PRODUCTION_SYSTEM_VALUE, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
          HookKind.MODIFY, covers=f"breakthroughs:{BREAKTHROUGH}")
def particle_synthesis_production(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Each wormhole in a system that contains your ships gains PRODUCTION 1 as if it were a unit
    you control (each one, also of the same type; the Hil Colish delta too - F_creuss 1, 2)."""
    position = str(ctx.get("position") or "")
    if not position or not _has_ships(state, player_id, position):
        return 0
    return len(board_graph.wormhole_list(state, _registry(), position))


@register(POINT_PRODUCTION_COST, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH), HookKind.MODIFY,
          covers=f"breakthroughs:{BREAKTHROUGH}")
def particle_synthesis_cost(state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Reduce the combined cost of units you produce in systems that contain wormholes by 1 for each
    wormhole in that system (the production system - ``production.production_system``)."""
    position = production.production_system(state)
    if position is None:
        return 0
    return -len(board_graph.wormhole_list(state, _registry(), position))
