"""Win-probability estimate for a contested zone (hover tooltip; read-only, no state change).

Monte Carlo over the same ``CombatUnit`` groups the real combat uses (``battle_units``), so
upgrades, faction variants, hooks, damage already taken and the nebula bonus are all included.
Seeded: the same board always shows the same percentages.

⚠️ ASSUMPTION (estimate, not a ruling — the real combat is interactive):
- both sides roll every round until one has no units left (rounds are capped);
- every hit is covered by the owner as the cheapest legal choice: Sustain Damage on the
  cheapest undamaged unit that has it, otherwise destroy the cheapest unit;
- Anti-Fighter Barrage is resolved once before round 1 (destroys fighters only);
- NOT modelled: Space Cannon, Bombardment, retreats, action cards, rerolls, per-unit
  single-roll bonuses and component-granted Sustain Damage.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from src.core import battle_units
from src.core.battle_units import CombatUnit
from src.core.dice import DIE_SIDES
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

TRIALS = 1500
MAX_ROUNDS = 40
SEED = 4  # fixed: tooltip numbers must not flicker between hovers
_FIGHTER = "fighter"


@dataclass
class _Group:
    """Mutable copy of one ``CombatUnit`` group for a single simulated fight."""

    base_type: str
    count: int
    damaged: int
    sustain: bool
    chance: float  # P(a die hits)
    dice_per_unit: int
    bonus_dice: int
    cost: float

    @property
    def dice(self) -> int:
        return self.count * self.dice_per_unit + (self.bonus_dice if self.count else 0)


@dataclass(frozen=True)
class ZoneOdds:
    """Outcome shares for one contested zone; ``attacker_win + defender_win + draw`` = 1."""

    zone: str  # "space" or a planet id
    kind: str  # "space" | "ground"
    attacker: str  # player id
    defender: str  # player id
    attacker_win: float
    defender_win: float
    draw: float


def _chance(hits_on: int) -> float:
    return max(0, min(DIE_SIDES, DIE_SIDES + 1 - hits_on)) / DIE_SIDES


def _groups(units: list[CombatUnit], costs: dict[str, float]) -> list[_Group]:
    return [
        _Group(
            base_type=u.base_type, count=u.count, damaged=u.damaged, sustain=u.sustain,
            chance=_chance(u.hits_on), dice_per_unit=u.dice_per_unit, bonus_dice=u.bonus_dice,
            cost=costs.get(u.base_type, 0.0),
        )
        for u in units
    ]


def _alive(groups: list[_Group]) -> bool:
    return any(g.count > 0 for g in groups)


def _take_hits(groups: list[_Group], hits: int, cancels: int) -> None:
    """Covers ``hits`` the way a sensible owner would: cheapest first, Sustain before loss."""
    while hits > 0:
        live = [g for g in groups if g.count > 0]
        if not live:
            return
        group = min(live, key=lambda g: (g.cost, g.base_type))
        if group.sustain and group.count - group.damaged > 0:
            group.damaged += 1
            hits -= cancels
        else:
            group.count -= 1
            if group.damaged > group.count:
                group.damaged = group.count
            hits -= 1


def _roll(rng: random.Random, groups: list[_Group]) -> int:
    return sum(rng.binomialvariate(g.dice, g.chance) for g in groups if g.dice > 0)


def _afb(
    rng: random.Random, source: list[CombatUnit], target: list[_Group]
) -> None:
    """Anti-Fighter Barrage: its hits destroy only the opponent's fighters."""
    hits = sum(
        rng.binomialvariate(u.count * u.afb_dice, _chance(u.afb_hits_on))
        for u in source
        if u.afb_hits_on is not None
    )
    for group in target:
        if group.base_type == _FIGHTER:
            group.count = max(0, group.count - hits)
            group.damaged = min(group.damaged, group.count)


def simulate(
    attacker: list[CombatUnit],
    defender: list[CombatUnit],
    costs: dict[str, float],
    cancels: tuple[int, int] = (1, 1),
    *,
    trials: int = TRIALS,
    afb: bool = False,
) -> tuple[float, float, float]:
    """Returns ``(attacker_win, defender_win, draw)`` shares over ``trials`` simulated fights."""
    rng = random.Random(SEED)
    wins = [0, 0, 0]  # attacker, defender, draw
    for _ in range(trials):
        a, d = _groups(attacker, costs), _groups(defender, costs)
        if afb:
            _afb(rng, attacker, d)
            _afb(rng, defender, a)
        for _round in range(MAX_ROUNDS):
            if not (_alive(a) and _alive(d)):
                break
            hits_on_d, hits_on_a = _roll(rng, a), _roll(rng, d)
            _take_hits(d, hits_on_d, cancels[1])
            _take_hits(a, hits_on_a, cancels[0])
        a_alive, d_alive = _alive(a), _alive(d)
        wins[0 if a_alive and not d_alive else 1 if d_alive and not a_alive else 2] += 1
    return tuple(round(w / trials, 3) for w in wins)  # type: ignore[return-value]


def _sides(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry,
    position: str, zone: str, attacker: str,
) -> list[tuple[str, list[CombatUnit]]]:
    system = state.systems[position]
    by_player = (
        system.space_units if zone == "space"
        else system.planet_units.get(zone, {})
    )
    result: list[tuple[str, list[CombatUnit]]] = []
    for player_id in sorted(by_player):
        units = battle_units.combat_units(
            state, grid, registry,
            kind="space" if zone == "space" else "ground",
            position=position,
            planet=None if zone == "space" else zone,
            player_id=player_id,
            defender=player_id != attacker,
        )
        if units:
            result.append((player_id, units))
    return result


def _pick_attacker(
    state: GameState, position: str, zone: str, present: list[str]
) -> str:
    """Active player when this is their activated system, else the one with a command token."""
    system = state.systems[position]
    if state.active_system == position and state.active_player_id in present:
        return str(state.active_player_id)
    tokened = [p for p in present if p in system.command_tokens]
    if len(tokened) == 1:
        return tokened[0]
    owner = system.planet_owners.get(zone) if zone != "space" else None
    others = [p for p in present if p != owner]
    return others[0] if others else present[0]


def system_odds(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, position: str
) -> list[ZoneOdds]:
    """Odds for every zone of ``position`` that holds exactly two fighting sides."""
    system = state.systems.get(position)
    if system is None:
        return []
    zones = ["space", *sorted(system.planet_units)]
    result: list[ZoneOdds] = []
    for zone in zones:
        pool = (
            system.space_units if zone == "space" else system.planet_units.get(zone, {})
        )
        present = [
            p for p, by_type in pool.items()
            if any(c > 0 and (is_space_unit(bt) == (zone == "space")) for bt, c in by_type.items())
        ]
        if len(present) != 2:
            continue
        attacker = _pick_attacker(state, position, zone, sorted(present))
        sides = _sides(state, grid, registry, position, zone, attacker)
        if len(sides) != 2:
            continue
        sides.sort(key=lambda s: s[0] != attacker)  # attacker first
        (a_id, a_units), (d_id, d_units) = sides
        costs = {
            u.base_type: (registry.units[u.unit_id].cost or 0.0)
            for u in (*a_units, *d_units)
            if u.unit_id in registry.units
        }
        a_win, d_win, draw = simulate(
            a_units, d_units, costs,
            (battle_units.sustain_cancels(state, a_id), battle_units.sustain_cancels(state, d_id)),
            afb=zone == "space",
        )
        result.append(ZoneOdds(
            zone=zone, kind="space" if zone == "space" else "ground",
            attacker=a_id, defender=d_id,
            attacker_win=a_win, defender_win=d_win, draw=draw,
        ))
    return result
