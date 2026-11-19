"""Inwazja: Space Cannon Defense — strzały obrońcy do lądujących sił (RULES.md 38, krok inwazji).

Wydzielone z ``invasion.py``; warstwa pod przebiegiem inwazji."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    battle,
    rules_hooks,
    space_cannon,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
)
from src.core.hex_grid import HexGrid
from src.core.invasion_common import (
    _ground_in_zone,
    _ground_units,
    _inv,
    _phase,
    _sustain_events,
    _system,
)
from src.core.registry import StaticDataRegistry

# ----------------------------------------------------------------- space cannon defense


def defense_planets(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Planety z lądowaniem, na których obrońca ma Space Cannon i atakujący wciąż ma siły (I3)."""
    inv = _inv(state)
    system = _system(state)
    result: list[str] = []
    # L4 Disruptors: w inwazji Space Cannon nie strzela w jednostki atakującego (RULES.md 62.2).
    if rules_hooks.permits(rules_hooks.POINT_SPACE_CANNON_DEFENSE_IMMUNE, state, inv.attacker):
        return result
    if inv.source:
        # Quantum Dissemination: „Players cannot use SPACE CANNON against these units” (F_yin Ω).
        return result
    for planet in sorted(inv.committed):
        if not _ground_in_zone(system, planet, inv.attacker):
            continue
        if any(
            space_cannon.zone_shooters(state, registry, pid, inv.position, planet)
            for pid in system.planet_units.get(planet, {})
            if pid != inv.attacker
        ):
            result.append(planet)
    return result


def defense_shooters(
    state: GameState, registry: StaticDataRegistry, planet: str
) -> list[space_cannon.SpaceCannonShooter]:
    inv = _inv(state)
    system = _system(state)
    shooters: list[space_cannon.SpaceCannonShooter] = []
    for pid in sorted(system.planet_units.get(planet, {})):
        if pid != inv.attacker:
            shooters.extend(
                space_cannon.zone_shooters(state, registry, pid, inv.position, planet)
            )
    return shooters


def undefended_open(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Planety, na których Space Cannon Defense jeszcze nie rzucono (okna „przed rzutem”)."""
    return _defense_open(_inv(state), state, registry)


def _defense_open(inv: InvasionState, state: GameState, registry: StaticDataRegistry) -> list[str]:
    return [
        p
        for p in defense_planets(state, registry)
        if p not in inv.defense_resolved and p not in inv.defense_pending
    ]


def defense_fire(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    planet: str,
    plasma_unit: str | None = None,
    extra_picks: Mapping[str, str] | None = None,
) -> GameState:
    """Space Cannon Defense: strzelcy na ``planet`` rzucają w zlądowane siły atakującego (I3).

    ``plasma_unit`` = ``SpaceCannonShooter.key`` grupy z dodatkową kością (Plasma Scoring).

    Raises:
        ValueError: Zły podkrok, planeta bez strzelców albo już rozstrzygnięta.
    """
    inv = _phase(state, InvasionPhase.SPACE_CANNON_DEFENSE, "Space Cannon Defense")
    if planet not in _defense_open(inv, state, registry):
        raise ValueError(f"Space Cannon Defense on {planet} is not available.")
    shooters = defense_shooters(state, registry, planet)
    rolled, cannon_rolls, total = space_cannon.roll_cannon(
        state, shooters, inv.attacker, plasma_unit, extra_picks
    )
    rolls: list[dict[str, Any]] = [
        {
            "baseType": r.shooter.base_type,
            "name": r.shooter.name,
            "owner": r.shooter.player_id,
            "count": r.shooter.count,
            "hitsOn": r.shooter.hits_on,
            "dice": r.dice,
            "hits": r.hits,
            "modifier": r.modifier,
            "extraDice": r.extra_dice,
        }
        for r in cannon_rolls
    ]
    new_state = rolled.clone()
    new_inv = _inv(new_state)
    triggers.fire(
        new_state, GameEvent.UNIT_ABILITY_USED, Moment.AFTER, subject=shooters[0].player_id,
        ctx={"ability": "space_cannon", "player": shooters[0].player_id, "planet": planet},
    )
    new_inv.log.append(
        {
            "phase": "DEFENSE",
            "planet": planet,
            "defender": shooters[0].player_id,
            "rolls": rolls,
            "hits": total,
            "passed": False,
            "losses": {},
            "sustained": {},
        }
    )
    units = _ground_units(new_state, grid, registry, planet, new_inv.attacker)
    absorbable = sum(u.count + u.sustainable for u in units.values())
    if total > 0 and absorbable > 0:
        new_inv.defense_pending[planet] = total
    else:
        new_inv.defense_resolved.append(planet)
    return new_state


def defense_pass(state: GameState, registry: StaticDataRegistry, planet: str) -> GameState:
    """Obrońca rezygnuje z Space Cannon Defense na ``planet`` (zdolność jest opcjonalna)."""
    inv = _phase(state, InvasionPhase.SPACE_CANNON_DEFENSE, "Space Cannon Defense")
    if planet not in _defense_open(inv, state, registry):
        raise ValueError(f"Space Cannon Defense on {planet} is not available.")
    new_state = state.clone()
    new_inv = _inv(new_state)
    new_inv.log.append(
        {
            "phase": "DEFENSE",
            "planet": planet,
            "defender": None,
            "rolls": [],
            "hits": 0,
            "passed": True,
            "losses": {},
            "sustained": {},
        }
    )
    new_inv.defense_resolved.append(planet)
    return new_state




def required_defense_hits(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, planet: str
) -> int:
    """Ile trafień atakujący musi pokryć na zlądowanych siłach: min(trafienia, HP)."""
    inv = _inv(state)
    pending = inv.defense_pending.get(planet, 0)
    if pending <= 0:
        return 0
    units = _ground_units(state, grid, registry, planet, inv.attacker)
    cancels = battle.sustain_cancels(state, inv.attacker)
    return min(pending, sum(u.count + cancels * u.sustainable for u in units.values()))


def assign_defense_hits(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    planet: str,
    *,
    sustain: dict[str, int],
    destroy: dict[str, int],
    destroy_damaged: dict[str, int],
) -> GameState:
    """Atakujący pokrywa trafienia Space Cannon Defense na zlądowanych siłach (I3)."""
    inv = _phase(state, InvasionPhase.SPACE_CANNON_DEFENSE, "Space Cannon Defense")
    if inv.defense_pending.get(planet, 0) <= 0:
        raise ValueError(f"There are no Space Cannon hits to assign on {planet}.")
    units = _ground_units(state, grid, registry, planet, inv.attacker)
    required = required_defense_hits(state, grid, registry, planet)
    plan = battle.plan_losses(
        units, sustain, destroy, destroy_damaged, required,
        battle.sustain_cancels(state, inv.attacker),
    )

    new_state = state.clone()
    new_inv = _inv(new_state)
    battle.apply_losses(new_state, new_inv.position, planet, new_inv.attacker, units, plan)
    for entry in reversed(new_inv.log):
        if entry.get("phase") == "DEFENSE" and entry.get("planet") == planet:
            entry["losses"] = battle.losses_of(units, plan)
            entry["sustained"] = battle.sustained_of(plan, sustain)
            break
    _sustain_events(new_state, new_inv.attacker, battle.sustained_of(plan, sustain))
    del new_inv.defense_pending[planet]
    new_inv.defense_resolved.append(planet)
    return new_state
