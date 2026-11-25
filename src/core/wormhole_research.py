"""Wormhole Research (agenda, "For") - deferred destruction of ships in alpha/beta systems.

C_agendas (Wormhole Research): the research offers and the Anti-Intellectual Revolution destruction
come FIRST; the doomed ships may be picked for Anti-Intellectual Revolution, and capacity is
resolved before Wormhole Research destroys ships (so e.g. fighters removed for lack of capacity are
not captured by The Terror Between). The destruction therefore waits as an active effect until the
speaker continues past the agenda (``agenda_phase.continue_agenda`` -> ``settle``), which is only
possible once every player decision is resolved.
"""

from __future__ import annotations

from src.core import active_effects, board_graph, capacity, unit_ops
from src.core.game_events import Duration
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

EFFECT_KEY = "agendas:wormhole_research:destroy"
_ALPHA_BETA = {"ALPHA", "BETA"}
_GROUND_FORCES = ("infantry", "mech")


def doomed_positions(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Systems containing an alpha or beta wormhole (a delta+alpha nexus counts - C_agendas)."""
    return [
        pos for pos in state.systems
        if board_graph.wormholes_at(state, registry, pos) & _ALPHA_BETA
    ]


def schedule(state: GameState) -> None:
    """Marks the destruction as owed (idempotent)."""
    if not any(e.key == EFFECT_KEY for e in state.active_effects):
        active_effects.add_effect(state, EFFECT_KEY, Duration.PHASE)


def is_scheduled(state: GameState) -> bool:
    return any(e.key == EFFECT_KEY for e in state.active_effects)


def settle(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Resolves capacity, then destroys the ships (MUTATES a clone; returns the new state).

    A capacity excess with a real choice opens the CAPACITY window and the destruction waits for
    the next call (the speaker continues again once the window is closed).
    """
    if not is_scheduled(state):
        return state
    work = state
    for position in doomed_positions(work, registry):
        work = capacity.open_capacity_check(work, registry, position)
        if work.pending_window is not None:
            return work
    if work is state:
        work = state.clone()
    active_effects.remove_by_key(work, EFFECT_KEY)
    for position in doomed_positions(work, registry):
        system = work.systems[position]
        doomed: list[tuple[str, str, int, UnitCause]] = []
        for player, units in system.space_units.items():
            for base_type, count in units.items():
                if count <= 0:
                    continue
                # Ships are destroyed; ground forces in space are removed without "destroyed"
                # (lack of capacity). Structures (Saar Floating Factory) are not ships and stay.
                if is_space_unit(base_type):
                    doomed.append((player, base_type, count, UnitCause.DESTROYED))
                elif base_type in _GROUND_FORCES:
                    doomed.append((player, base_type, count, UnitCause.REMOVED))
        # Flagships last: the ships are destroyed together, so a flagship that captures
        # destroyed units (The Terror Between) is still there when the others go.
        doomed.sort(key=lambda d: d[1] == "flagship")
        for player, base_type, count, cause in doomed:
            unit_ops.remove_units(work, system, "space", player, base_type, count, cause)
    return work
