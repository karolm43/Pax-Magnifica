"""Optional auto-assignment of combat hits (RULES.md 54.14). Pure.

A player may pick a PRIVATE policy (``ReactionPrefs.auto_hits``):

* ``off`` (default) - the player always assigns hits by hand;
* ``sustain`` - hits are covered with SUSTAIN DAMAGE only; when a unit would have to be destroyed,
  the player is asked;
* ``cheap`` - SUSTAIN DAMAGE first, then the cheapest fodder (cost <= ``CHEAP_MAX_COST``:
  fighters, infantry); destroying anything more valuable is left to the player.

The policy automates ONLY the allocation. The plan goes through the normal
``battle.assign_combat_hits`` - "before you assign hits" events, SUSTAIN DAMAGE events, the
protective pause after the last side's SUSTAIN DAMAGE (54.10a), Direct Hit / Reflective
Shielding windows and every post-assignment hook fire exactly as for a manual assignment.

The engine never auto-assigns when the player has a real choice to make first: a reaction card or
faction component usable right now (Shields Holding, agents), a pending "you may" offer of theirs,
directed hits (``hit_targets``), an open reaction pause or Sabotage window, or a bot (bots decide
through ``src/engine``).
"""

from __future__ import annotations

import math

from src.core import battle, reaction_prefs, reaction_window
from src.core.battle_units import CombatUnit
from src.core.game_state import ControlType, GameState, WindowType
from src.core.registry import StaticDataRegistry

# ⚠️ ASSUMPTION (54.14 a): "cheap fodder" = units costing at most 0.5 (fighters, infantry).
CHEAP_MAX_COST = 0.5
# Safety net: one settle never assigns more than this many times (both sides, chained windows).
_MAX_ROUNDS = 4

Plan = tuple[dict[str, int], dict[str, int], dict[str, int]]


def suggest(
    units: list[CombatUnit],
    costs: dict[str, float | None],
    required: int,
    cancels: int,
    policy: str,
) -> Plan | None:
    """The policy's plan ``(sustain, destroy, destroy_damaged)`` or ``None`` = ask the player.

    SUSTAIN DAMAGE goes on hit shields first, then on the most expensive units (they are the ones
    worth protecting). ``cheap`` then destroys fodder, cheapest and weakest first, damaged copies
    before undamaged ones are irrelevant for fodder (no SUSTAIN DAMAGE).
    """
    if policy not in (reaction_prefs.AUTO_HITS_SUSTAIN, reaction_prefs.AUTO_HITS_CHEAP):
        return None
    if required <= 0:
        return None
    sustain: dict[str, int] = {}
    left = required
    granted_left = 1  # SUSTAIN DAMAGE granted by a component: at most 1 per assignment

    def value(unit: CombatUnit) -> float:
        cost = costs.get(unit.base_type)
        return math.inf if cost is None else float(cost)

    order = sorted(units, key=lambda u: (not u.shield, -value(u), u.base_type))
    for unit in order:
        spare = unit.sustainable
        if not unit.sustain:
            spare = min(spare, granted_left)
        uses = min(spare, math.ceil(left / cancels)) if left > 0 else 0
        if uses <= 0:
            continue
        sustain[unit.base_type] = uses
        if not unit.sustain:
            granted_left -= uses
        left -= uses * cancels
    if left <= 0:
        return sustain, {}, {}
    if policy != reaction_prefs.AUTO_HITS_CHEAP:
        return None
    destroy: dict[str, int] = {}
    destroy_damaged: dict[str, int] = {}
    fodder = sorted(
        (u for u in units if not u.shield and value(u) <= CHEAP_MAX_COST),
        key=lambda u: (value(u), -u.base_hits_on, u.base_type),
    )
    for unit in fodder:
        damaged_after = unit.damaged + sustain.get(unit.base_type, 0)
        undamaged = unit.count - damaged_after
        take = min(undamaged, left)
        if take > 0:
            destroy[unit.base_type] = take
            left -= take
        take = min(damaged_after, left)
        if take > 0:
            destroy_damaged[unit.base_type] = take
            left -= take
        if left <= 0:
            break
    if left > 0:
        return None  # something valuable would die - the player decides
    if left < 0:
        return None  # the sustain overshoot only works without losses (``plan_losses``)
    return sustain, destroy, destroy_damaged


def _policy(state: GameState, player_id: str) -> str:
    player = state.players.get(player_id)
    if player is None or player.control_type is ControlType.BOT:
        return reaction_prefs.AUTO_HITS_OFF
    return player.private.reaction_prefs.auto_hits


def _assigner(state: GameState, registry: StaticDataRegistry) -> str | None:
    """The player whose hits the engine may assign now, or ``None``."""
    window = state.pending_window
    combat = state.active_combat
    if (
        combat is None
        or window is None
        or window.window_type is not WindowType.COMBAT_ASSIGN_HITS
        or state.reaction_pause is not None
        or state.held_play is not None
    ):
        return None
    player_id = window.current_responder
    if player_id is None or _policy(state, player_id) == reaction_prefs.AUTO_HITS_OFF:
        return None
    if player_id in combat.hit_targets or player_id in combat.stepwise_assign:
        return None
    if any(offer.player_id == player_id for offer in state.pending_offers):
        return None
    if reaction_window.has_playable_reaction(state, registry, player_id):
        return None  # Shields Holding, an agent... - the player may want to act first
    return player_id


def settle(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Assigns hits for players whose policy covers them (new state, or the same one).

    Called after every step (``step_settle``), so the engine simulation of bots sees the same.
    """
    from src.core.state_grid import grid_from_state  # local: avoids an import cycle

    result = state
    for _ in range(_MAX_ROUNDS):
        player_id = _assigner(result, registry)
        if player_id is None:
            return result
        grid = grid_from_state(result, registry)
        units = battle.assign_units(result, grid, registry, player_id)
        costs = {
            u.base_type: (registry.units[u.unit_id].cost if u.unit_id in registry.units else None)
            for u in units
        }
        required = battle.required_hits(result, grid, registry, player_id)
        plan = suggest(
            units, costs, required, battle.sustain_cancels(result, player_id),
            _policy(result, player_id),
        )
        if plan is None:
            return result
        sustain, destroy, destroy_damaged = plan
        try:
            result = battle.assign_combat_hits(
                result, grid, registry, player_id,
                sustain=sustain, destroy=destroy, destroy_damaged=destroy_damaged,
            )
        except ValueError:
            return result  # the engine refused the plan - the player assigns by hand
    return result
