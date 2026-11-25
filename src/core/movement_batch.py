"""Batched "Move Ships" step: the whole flight plan is declared first, then flown (RULES.md 32.4).

R_movement: "The active player declares which of their ships are moving before any ships move.
Those ships arrive in the active system simultaneously." The UI stages several legs (one per
source system / route) and sends them together. This module validates the WHOLE plan before
anything is committed: if any leg is illegal, nothing moves and the error names the leg.

Each leg is executed with ``movement.move_fleet`` (single source of movement rules) on the state
left by the previous leg, so per-action limits (one-ship move bonuses, Ion Storm, cargo
availability) carry across legs exactly like separate moves. The result keeps one state per leg
(the API commits them as separate snapshots so the Activity feed and the flight replay show every
leg, and one "Undo movement" reverts them all).

Simultaneity guard (R_movement: "all movement is simultaneous"): ships that arrived in the active
system through an earlier leg of the same plan cannot be moved again by a later leg.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.movement import CargoPickup, move_fleet
from src.core.registry import StaticDataRegistry


@dataclass(frozen=True)
class MoveLeg:
    """One leg of a flight plan: ships (and their cargo) flying from one source system."""

    from_pos: str
    ships: dict[str, int]
    cargo: list[CargoPickup] = field(default_factory=list)
    gravity_drive: bool = False
    tempesta: bool = False
    imperator: bool = False
    route: list[str] | None = None
    ion_storm_token: bool | None = None


@dataclass(frozen=True)
class BatchResult:
    """States after each executed leg (the last one = state after the whole flight plan)."""

    legs: list[MoveLeg]
    states: list[GameState]

    @property
    def final(self) -> GameState:
        return self.states[-1]


def _ships_in_active(state: GameState, player_id: str) -> dict[str, int]:
    active = state.active_system
    system = state.systems.get(active) if active is not None else None
    if system is None:
        return {}
    return dict(system.space_units.get(player_id, {}))


def move_batch(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    legs: list[MoveLeg],
) -> BatchResult:
    """Validates and executes a whole flight plan (all legs or nothing).

    Raises:
        ValueError: Empty plan, or any leg is illegal - the message names the failing leg
            (``Leg 2 (from 0203): ...``); the input state is never modified.
    """
    if not legs:
        raise ValueError("The flight plan is empty - stage at least one ship to move.")
    # Ships that were already in the active system before the plan (they may "leave and
    # return"); ships flown in by an earlier leg are not in this budget.
    home_budget = _ships_in_active(state, player_id)
    current = state
    states: list[GameState] = []
    for index, leg in enumerate(legs, start=1):
        where = f"Leg {index} (from {leg.from_pos})"
        if leg.from_pos == state.active_system:
            for base_type, count in leg.ships.items():
                if count <= 0:
                    continue
                left = home_budget.get(base_type, 0)
                if count > left:
                    raise ValueError(
                        f"{where}: ships that arrived with this flight plan cannot move again "
                        "- all ships move simultaneously."
                    )
                home_budget[base_type] = left - count
        try:
            current = move_fleet(
                current,
                grid,
                registry,
                leg.from_pos,
                leg.ships,
                list(leg.cargo),
                player_id,
                gravity_drive=leg.gravity_drive,
                tempesta=leg.tempesta,
                imperator=leg.imperator,
                route=leg.route,
                ion_storm_token=leg.ion_storm_token,
            )
        except ValueError as exc:
            raise ValueError(f"{where}: {exc}") from exc
        states.append(current)
    return BatchResult(legs=list(legs), states=states)
