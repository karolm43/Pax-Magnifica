"""Inwazja: bombardowanie (Bombardment) — grupy, cele, rzuty i przydział trafień (RULES.md 52).

Wydzielone z ``invasion.py``; warstwa pod przebiegiem inwazji."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    battle,
    chronicle_log,
    entropic_scar,
    exploration,
    extra_dice,
    rules_hooks,
    triggers,
)
from src.core.dice import count_hits, roll_dice
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
)
from src.core.hex_grid import HexGrid
from src.core.invasion_common import (
    BombardAssignment,
    BombardGroup,
    _defenders,
    _ground_units,
    _inv,
    _phase,
    _sustain_events,
    _system,
    planet_infos,
    unit_variant,
)
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

# ------------------------------------------------------------------------- bombardment


def bombard_targets(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Planety, które wolno bombardować: cudze siły naziemne i brak tarczy (I3/I4).

    X-89 ΩΩ (hook PERMIT) dodaje planety kontrolowane przez INNEGO gracza, ale bez sił
    naziemnych (C_technology: "may roll for bombardment against a planet that contains no
    ground forces"). ⚠ ZAŁOŻENIE: planeta niczyja i własna atakującego nie są celem.
    """
    attacker = _inv(state).attacker
    empty_ok = rules_hooks.permits(rules_hooks.POINT_BOMBARD_EMPTY_PLANETS, state, attacker)
    # Conventions of War (FORBID cech planet): bez BOMBARDMENT na planetach kulturowych.
    banned = rules_hooks.forbidden(
        rules_hooks.POINT_BOMBARDMENT_FORBIDDEN_TRAITS, state, attacker
    )
    return [
        i.planet
        for i in planet_infos(state, registry)
        if not i.shielded
        and (i.defenders or (empty_ok and i.owner is not None and i.owner != attacker))
        and not (banned and banned & set(exploration.planet_traits(registry, i.planet, state)))
    ]


def granted_bombard_hits_on(state: GameState) -> int | None:
    """Próg trafień Bombardment nadanego statkom bez niego (Blitz) albo ``None`` (brak efektu)."""
    values = rules_hooks.forbidden(
        rules_hooks.POINT_BOMBARDMENT_GRANTED, state, _inv(state).attacker
    )
    numbers = [int(v) for v in values if str(v).isdigit()]
    return min(numbers) if numbers else None


def bombard_modifier(state: GameState, planet: str) -> int:
    """Modyfikator wyniku kości bombardowania przeciw planecie (Bunker kontrolującego: -4)."""
    inv = _inv(state)
    owner = _system(state).planet_owners.get(planet)
    if owner is None or owner == inv.attacker:
        return 0
    return rules_hooks.modify(
        rules_hooks.POINT_BOMBARDMENT_ROLL_MODIFIER, state, owner, 0,
        {"planet": planet, "attacker": inv.attacker},
    )


def bombard_groups(state: GameState, registry: StaticDataRegistry) -> list[BombardGroup]:
    """Statki atakującego z Bombardment w aktywnym systemie (puste, gdy brak celu)."""
    invasion = _inv(state)
    system = _system(state)
    if not bombard_targets(state, registry):
        return []
    if entropic_scar.unit_abilities_blocked(state, invasion.position, registry):
        return []  # Entropic Scar: BOMBARDMENT ani przez, ani w jednostki w bliźnie (RULES.md 1.5)
    groups: list[BombardGroup] = []
    granted = granted_bombard_hits_on(state)
    units = dict(system.space_units.get(invasion.attacker, {}))
    ground = ground_bombarders(state, invasion.attacker, invasion.position)
    units.update(ground)  # przestrzeń + planety systemu (``ground_bombarders`` liczy obie)
    for bt, count in sorted(units.items()):
        if count <= 0 or not (is_space_unit(bt) or bt in ground):
            continue
        unit = unit_variant(state, registry, invasion.attacker, bt)
        if unit is None:
            continue
        if not unit.bombard_hits_on or unit.bombard_hits_on <= 0:
            # Blitz: statki niefighterowe bez Bombardment zyskują je (1 kość) do końca inwazji.
            if granted is not None and bt != "fighter":
                groups.append(
                    BombardGroup(
                        base_type=bt, unit_id=unit.id, name=unit.name, count=count,
                        hits_on=granted, dice_per_unit=1,
                    )
                )
            continue
        groups.append(
            BombardGroup(
                base_type=bt,
                unit_id=unit.id,
                name=unit.name,
                count=count,
                hits_on=unit.bombard_hits_on,
                dice_per_unit=unit.bombard_die_count or 1,
            )
        )
    return groups


def ground_bombarder_types(state: GameState, player_id: str) -> set[str]:
    """Typy sił naziemnych gracza bombardujące „jak statek” (Annihilator, RULES.md 62.12)."""
    point = rules_hooks.POINT_BOMBARDMENT_GROUND_UNITS
    return {str(bt) for bt in rules_hooks.forbidden(point, state, player_id)}


def ground_bombarders(
    state: GameState, player_id: str, position: str, *, exclude_planet: str | None = None
) -> dict[str, int]:
    """Siły naziemne gracza w systemie, które mogą bombardować jak statek (przestrzeń + planety).

    ``exclude_planet`` - planeta, na której toczy się walka naziemna (tam walczą - F_lizix)."""
    types = ground_bombarder_types(state, player_id)
    system = state.systems.get(position)
    found: dict[str, int] = {}
    if not types or system is None:
        return found
    zones = [system.space_units.get(player_id, {})] + [
        by_player.get(player_id, {})
        for planet, by_player in system.planet_units.items()
        if planet != exclude_planet
    ]
    for units in zones:
        for bt in types:
            if units.get(bt, 0) > 0:
                found[bt] = found.get(bt, 0) + units[bt]
    return found


def plasma_bombard_dice(state: GameState) -> int:
    """Ile kości dodałby Plasma Scoring jednej jednostce bombardującej (0 = brak technologii)."""
    inv = _inv(state)
    return max(
        0,
        rules_hooks.modify(
            rules_hooks.POINT_BOMBARDMENT_EXTRA_DICE, state, inv.attacker, 0,
            {"position": inv.position},
        ),
    )


def bombard(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    assignments: list[BombardAssignment],
    plasma_unit: str | None = None,
    extra_picks: Mapping[str, str] | None = None,
) -> GameState:
    """Bombardowanie: rzut dla każdego przydziału; trafienia czekają na przypisanie strat (I3).

    ``plasma_unit`` = ``BombardAssignment.key`` przydziału, którego jednostka rzuca 1 kością
    więcej dzięki Plasma Scoring (decyzja gracza; ``None`` = bez dodatkowej kości).

    Reguła „wszystko albo nic": jeśli gracz bombarduje, MUSI użyć każdej jednostki z
    Bombardment w systemie (R_bombardment, Notes) — suma przydziałów per typ = liczba statków.
    Każda jednostka wybiera JEDNĄ planetę (jej kości nie dzielą się między planety).

    Raises:
        ValueError: Zły podkrok, już bombardowano, nielegalna planeta, nie użyto wszystkich.
    """
    invasion = _phase(state, InvasionPhase.BOMBARDMENT, "Bombardment")
    if invasion.bombarded:
        raise ValueError("Bombardment has already been resolved in this invasion.")
    groups = {g.base_type: g for g in bombard_groups(state, registry)}
    if not groups:
        raise ValueError("No unit can bombard a planet here.")
    targets = set(bombard_targets(state, registry))
    used: dict[str, int] = {}
    for item in assignments:
        if item.count <= 0:
            continue
        if item.base_type not in groups:
            raise ValueError(f"{item.base_type} cannot bombard here.")
        if item.planet not in targets:
            raise ValueError(f"{item.planet} cannot be bombarded.")
        used[item.base_type] = used.get(item.base_type, 0) + item.count
    if not used:
        raise ValueError("Assign at least one unit - or skip the bombardment.")
    for base_type, group in groups.items():
        if used.get(base_type, 0) != group.count:
            raise ValueError(
                "If you bombard you must use every unit with Bombardment: "
                f"assign all {group.count} {group.name}."
            )
    for planet in {a.planet for a in assignments if a.count > 0}:
        if len(_defenders(state, planet, invasion.position, invasion.attacker)) > 1:
            raise ValueError(
                f"More than one defender on {planet} - resolve it with God-Mode."
            )

    rolled = state
    by_planet: dict[str, dict[str, Any]] = {}
    # Dodatkowe kości dla JEDNEJ jednostki na źródło (Plasma Scoring, commander Argent,
    # Strike Wing Ambuscade: „may”) - każde źródło przydział wskazany przez gracza
    # (``extra_picks``; ``plasma_unit`` = wszystkie źródła jednemu przydziałowi).
    sources = extra_dice.sources(
        state, _inv(state).attacker, rules_hooks.POINT_BOMBARDMENT_EXTRA_DICE,
        {"position": _inv(state).position},
    )
    live = {i.key: groups[i.base_type].hits_on for i in assignments if i.count > 0}
    if plasma_unit:
        if not sources:
            raise ValueError("Plasma Scoring is not available.")
        if plasma_unit not in live:
            raise ValueError("Plasma Scoring: choose one of the bombarding units.")
        picks = {e.key: plasma_unit for e in sources}
    else:
        picks = dict(extra_picks or {})
    extra_by_item = extra_dice.assign(sources, live, picks)
    for item in assignments:
        if item.count <= 0:
            continue
        group = groups[item.base_type]
        bonus = extra_by_item.pop(item.key, 0)
        rolled, dice = roll_dice(rolled, item.count * group.dice_per_unit + bonus)
        modifier = bombard_modifier(state, item.planet)
        # Hook MODIFY: mnożnik trafień bombardowania (X-89 ΩΩ: podwójne trafienia).
        hits = count_hits([d + modifier for d in dice], group.hits_on) * rules_hooks.modify(
            rules_hooks.POINT_COMBAT_HIT_MULTIPLIER, state, _inv(state).attacker, 1,
            {"kind": "bombardment", "base_type": item.base_type},
        )
        entry = by_planet.setdefault(item.planet, {"rolls": [], "hits": 0})
        entry["rolls"].append(
            {
                "baseType": item.base_type,
                "name": group.name,
                "count": item.count,
                "hitsOn": group.hits_on,
                "dice": dice,
                "hits": hits,
                "modifier": modifier,
            }
        )
        entry["hits"] += hits

    new_state = rolled.clone()
    inv = _inv(new_state)
    inv.bombarded = True
    triggers.fire(
        new_state, GameEvent.UNIT_ABILITY_USED, Moment.AFTER, subject=inv.attacker,
        ctx={"ability": "bombardment", "player": inv.attacker, "position": inv.position,
             "planets": sorted(by_planet)},
    )
    for planet, entry in by_planet.items():
        defenders = _defenders(new_state, planet, inv.position, inv.attacker)
        defender = defenders[0] if defenders else None
        inv.log.append(
            {
                "phase": "BOMBARDMENT",
                "planet": planet,
                "defender": defender,
                "rolls": entry["rolls"],
                "hits": entry["hits"],
                "losses": {},
                "sustained": {},
            }
        )
        if defender is not None and entry["hits"] > 0:
            units = _ground_units(new_state, grid, registry, planet, defender)
            if sum(u.count + u.sustainable for u in units.values()) > 0:
                inv.bombard_pending[planet] = entry["hits"]
                if defender == NEUTRAL_PLAYER_ID:
                    _auto_assign_neutral_bombard(new_state, grid, registry, planet)
    return new_state


def _auto_assign_neutral_bombard(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, planet: str
) -> None:
    """Straty neutralnych po bombardowaniu przypisuje silnik (R_neutral_units); MUTUJE state."""
    inv = _inv(state)
    units = _ground_units(state, grid, registry, planet, NEUTRAL_PLAYER_ID)
    required = required_bombard_hits(state, grid, registry, planet)
    costs = {
        bt: (registry.units[u.unit_id].cost or 0.0)
        for bt, u in units.items()
        if u.unit_id in registry.units
    }
    sustain, destroy, destroy_damaged = battle.neutral_loss_choice(
        list(units.values()), costs, required
    )
    plan = battle.plan_losses(units, sustain, destroy, destroy_damaged, required)
    battle.apply_losses(state, inv.position, planet, NEUTRAL_PLAYER_ID, units, plan)
    for entry in reversed(inv.log):
        if entry.get("phase") == "BOMBARDMENT" and entry.get("planet") == planet:
            entry["losses"] = battle.losses_of(units, plan)
            entry["sustained"] = battle.sustained_of(plan, sustain)
            break
    del inv.bombard_pending[planet]




def required_bombard_hits(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, planet: str
) -> int:
    """Ile trafień obrońca musi pokryć na planecie: min(trafienia, jednostki + Sustain)."""
    inv = _inv(state)
    pending = inv.bombard_pending.get(planet, 0)
    if pending <= 0:
        return 0
    defender = bombard_defender(inv, planet)
    units = _ground_units(state, grid, registry, planet, defender)
    cancels = battle.sustain_cancels(state, defender)
    return min(pending, sum(u.count + cancels * u.sustainable for u in units.values()))


def bombard_defender(inv: InvasionState, planet: str) -> str:
    for entry in reversed(inv.log):
        if entry.get("phase") == "BOMBARDMENT" and entry.get("planet") == planet:
            return str(entry["defender"])
    raise ValueError(f"No bombardment hits are waiting on {planet}.")


def assign_bombard_hits(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    planet: str,
    player_id: str,
    *,
    sustain: dict[str, int],
    destroy: dict[str, int],
    destroy_damaged: dict[str, int],
) -> GameState:
    """Obrońca planety niszczy własne siły naziemne za trafienia bombardowania (I3 Step 2).

    Raises:
        ValueError: Brak oczekujących trafień na planecie, zły gracz, zła liczba/typ strat.
    """
    inv = _phase(state, InvasionPhase.BOMBARDMENT, "Bombardment")
    if inv.bombard_pending.get(planet, 0) <= 0:
        raise ValueError(f"There are no bombardment hits to assign on {planet}.")
    defender = bombard_defender(inv, planet)
    if player_id != defender:
        raise ValueError("Only the player controlling the planet assigns the hits.")
    units = _ground_units(state, grid, registry, planet, defender)
    required = required_bombard_hits(state, grid, registry, planet)
    plan = battle.plan_losses(
        units, sustain, destroy, destroy_damaged, required,
        battle.sustain_cancels(state, defender),
    )

    new_state = state.clone()
    new_inv = _inv(new_state)
    battle.apply_losses(new_state, new_inv.position, planet, defender, units, plan)
    for entry in reversed(new_inv.log):
        if entry.get("phase") == "BOMBARDMENT" and entry.get("planet") == planet:
            entry["losses"] = battle.losses_of(units, plan)
            entry["sustained"] = battle.sustained_of(plan, sustain)
            break
    chronicle_log.record_fire(
        new_state, new_inv.attacker, defender, "bombardment", battle.losses_of(units, plan)
    )
    _sustain_events(new_state, defender, battle.sustained_of(plan, sustain))
    del new_inv.bombard_pending[planet]
    return new_state
