"""Inwazja: Bombardment → Commit Ground Forces → Space Cannon Defense → Ground Combat →
Establish Control (RULES.md 40).

Krok INVASION akcji taktycznej. Stan w ``GameState.invasion`` (``InvasionState``), podkroki w
``InvasionPhase``. Walka naziemna to istniejący silnik ``core/battle.py`` (kind="ground") — tu
tylko wskazujemy planety do walki i zapamiętujemy wynik (remis → obrońca zachowuje kontrolę).

Funkcje CZYSTE (``state -> state``), rzuty przez ``core/dice.py`` (seedowalne). Twarda walidacja:
``ValueError`` → HTTP 422. Wartości (Bombardment, Planetary Shield, Space Cannon) z WARIANTU
jednostki gracza (``combat.resolve_unit_variant``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.core import (
    battle,
    chronicle,
    control,
    custodians,
    exhaust,
    exploration,
    extra_dice,
    planet_stats,
    rules_hooks,
    space_cannon,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.dice import DIE_SIDES, count_hits, roll_dice
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.models import UnitDef
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry
from src.core.system_planets import planets_of_system
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

# Siły naziemne (mogą lądować i walczyć na planecie); struktury (pds/spacedock) NIE.
GROUND_FORCES = frozenset({"infantry", "mech"})
_DMZ_REASON = "Units cannot be committed to a planet with the Demilitarized Zone."


# ----------------------------------------------------------------------------- modele


@dataclass(frozen=True)
class BombardGroup:
    """Grupa statków gracza z Bombardment (jeden typ) — wartości z wariantu."""

    base_type: str
    unit_id: str
    name: str
    count: int
    hits_on: int
    dice_per_unit: int

    @property
    def total_dice(self) -> int:
        return self.count * self.dice_per_unit

    @property
    def expected_hits(self) -> float:
        chance = max(0, min(DIE_SIDES, DIE_SIDES + 1 - self.hits_on)) / DIE_SIDES
        return round(self.total_dice * chance, 2)


@dataclass(frozen=True)
class PlanetInfo:
    """Planeta aktywnego systemu z punktu widzenia inwazji."""

    planet: str
    owner: str | None
    defenders: list[str]  # gracze (≠ atakujący) z siłami naziemnymi na planecie
    shielded: bool  # Planetary Shield (blokuje Bombardment, chyba że war sun)
    has_space_cannon: bool  # ktoś ≠ atakujący ma tu Space Cannon (Defense)
    # Na planecie stoi jednostka z tarczą, nawet gdy ją łamie war sun / odbiera Arc Secundus
    # (UI pokazuje wtedy zapadającą się kopułę).
    has_shield: bool = False


@dataclass(frozen=True)
class BombardAssignment:
    """Przydział ``count`` statków typu ``base_type`` do bombardowania ``planet``."""

    base_type: str
    planet: str
    count: int

    @property
    def key(self) -> str:
        """Identyfikator przydziału (typ|planeta) - wybór jednostki Plasma Scoring."""
        return f"{self.base_type}|{self.planet}"


# --------------------------------------------------------------------------- pomocnicze


def _inv(state: GameState) -> InvasionState:
    if state.invasion is None:
        raise ValueError("No invasion is in progress.")
    return state.invasion


def _phase(state: GameState, expected: InvasionPhase, name: str) -> InvasionState:
    invasion = _inv(state)
    if invasion.phase is not expected:
        raise ValueError(f"{name} is not the current invasion step.")
    return invasion


def _system(state: GameState) -> SystemState:
    invasion = _inv(state)
    system = state.systems.get(invasion.position)
    if system is None:
        raise ValueError("The active system has no units.")
    return system


def _ground_in_zone(system: SystemState, zone: str, player_id: str) -> dict[str, int]:
    """Siły naziemne gracza w strefie (``"space"`` = ładunek w przestrzeni albo planeta)."""
    if zone == "space":
        units = system.space_units.get(player_id, {})
    else:
        units = system.planet_units.get(zone, {}).get(player_id, {})
    return {bt: n for bt, n in units.items() if n > 0 and bt in GROUND_FORCES}


def system_planets(
    state: GameState, registry: StaticDataRegistry, position: str
) -> list[str]:
    """Id planet systemu (z definicji kafelka + planety dołożone w grze, np. Thunder's Edge)."""
    return planets_of_system(state, registry, position)


def unit_variant(
    state: GameState, registry: StaticDataRegistry, player_id: str, base_type: str
) -> UnitDef | None:
    player = state.players.get(player_id)
    return resolve_unit_variant(
        registry,
        player.faction if player is not None else None,
        player.technologies if player is not None else [],
        base_type,
        player.breakthrough_unlocked if player is not None else False,
    )


def _defenders(
    state: GameState, planet: str, position: str, attacker: str
) -> list[str]:
    """Gracze ≠ atakujący z siłami naziemnymi na planecie."""
    system = state.systems.get(position)
    if system is None:
        return []
    return sorted(
        pid
        for pid in system.planet_units.get(planet, {})
        if pid != attacker and _ground_in_zone(system, planet, pid)
    )


def _attacker_ignores_shield(state: GameState, registry: StaticDataRegistry) -> bool:
    """Czy atakujący ma w przestrzeni jednostkę z ``disablesPlanetaryShield`` (war sun) — I4."""
    invasion = _inv(state)
    system = _system(state)
    for bt, count in system.space_units.get(invasion.attacker, {}).items():
        if count <= 0:
            continue
        unit = unit_variant(state, registry, invasion.attacker, bt)
        if unit is not None and unit.disables_planetary_shield:
            return True
    return False


def _shield_stripped(state: GameState, position: str, owner: str) -> bool:
    """Czy INNY gracz w systemie ``position`` odbiera jednostkom ``owner`` PLANETARY SHIELD."""
    system = state.systems.get(position)
    if system is None:
        return False
    others = set(system.space_units) | {
        pid for by_player in system.planet_units.values() for pid in by_player
    }
    return any(
        rules_hooks.permits(
            rules_hooks.POINT_STRIPS_PLANETARY_SHIELD, state, other, {"position": position},
        )
        for other in sorted(others)
        if other != owner and other in state.players
    )


def planet_shield(
    state: GameState,
    registry: StaticDataRegistry,
    position: str,
    planet: str,
    exclude: str | None = None,
) -> tuple[bool, bool]:
    """``(jest, działa)``: czy na planecie stoi jednostka z Planetary Shield i czy tarcza działa.

    „Jest” = jednostka z PLANETARY SHIELD (poza graczem ``exclude``, np. atakującym). „Działa” =
    tarczy nie odebrał Disable (PDS na czas inwazji) ani efekt innego gracza w systemie
    (Arc Secundus). War sun atakującego to osobna sprawa (``_attacker_ignores_shield``).
    Funkcja nie wymaga trwającej inwazji (mapa pokazuje tarcze stale).
    """
    system = state.systems.get(position)
    present = active = False
    if system is None:
        return present, active
    for pid, by_type in system.planet_units.get(planet, {}).items():
        if pid == exclude:
            continue
        for bt, count in by_type.items():
            if count <= 0:
                continue
            unit = unit_variant(state, registry, pid, bt)
            if unit is None or not unit.planetary_shield:
                continue
            present = True
            if bt == "pds" and space_cannon.pds_disabled(state, pid):
                continue  # Disable: PDS przeciwnika traci Planetary Shield na czas inwazji
            if _shield_stripped(state, position, pid):
                continue  # Arc Secundus: jednostki innych graczy w systemie tracą tarczę
            active = True
    return present, active


def planet_infos(state: GameState, registry: StaticDataRegistry) -> list[PlanetInfo]:
    """Planety aktywnego systemu: właściciel, obrońcy (siły naziemne), tarcza, Space Cannon."""
    invasion = _inv(state)
    system = _system(state)
    ignores = _attacker_ignores_shield(state, registry)
    infos: list[PlanetInfo] = []
    for planet in system_planets(state, registry, invasion.position):
        has_shield, shield_up = planet_shield(
            state, registry, invasion.position, planet, exclude=invasion.attacker
        )
        has_cannon = any(
            space_cannon.zone_shooters(state, registry, pid, invasion.position, planet)
            for pid in system.planet_units.get(planet, {})
            if pid != invasion.attacker
        )
        infos.append(
            PlanetInfo(
                planet=planet,
                owner=system.planet_owners.get(planet),
                defenders=_defenders(state, planet, invasion.position, invasion.attacker),
                shielded=(not ignores) and shield_up,
                has_space_cannon=has_cannon,
                has_shield=has_shield,
            )
        )
    return infos


# ------------------------------------------------------------------------------ początek


def _enter(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, phase: InvasionPhase
) -> GameState:
    """Wchodzi w podkrok (MUTUJE klon) i pomija te, w których nie ma nic do roboty."""
    new_state = state.clone()
    inv = _inv(new_state)
    inv.phase = phase
    inv.last_commit = {}  # okno „po zaangażowaniu” (Ghost Squad, Parley) żyje tylko w COMMIT
    if phase is InvasionPhase.SPACE_CANNON_DEFENSE and not defense_planets(new_state, registry):
        return _enter(new_state, grid, registry, InvasionPhase.GROUND_COMBAT)
    if phase is InvasionPhase.GROUND_COMBAT and not combat_planets(new_state, registry):
        return _enter(new_state, grid, registry, InvasionPhase.ESTABLISH)
    if phase is InvasionPhase.ESTABLISH:
        _establish_control(new_state, registry)
    return new_state


def begin_invasion(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Otwiera inwazję przy wejściu w krok INVASION (None, gdy nie ma co robić).

    Pomija Bombardment, gdy nikt nie może bombardować, a przy braku sił naziemnych w
    przestrzeni (nic do lądowania) w ogóle nie otwiera okna inwazji.
    """
    active = state.active_system
    attacker = state.active_player_id
    if state.tactical_step is not TacticalStep.INVASION or active is None or attacker is None:
        raise ValueError("Invasion starts in the INVASION step of a tactical action.")
    if state.invasion is not None:
        return state.clone()
    new_state = state.clone()
    new_state.invasion = InvasionState(position=active, attacker=attacker)
    system = new_state.systems.get(active)
    landable = system is not None and bool(_ground_in_zone(system, "space", attacker))
    # RULES.md 40.1 I7a: sporna planeta (siły aktywnego obok cudzych, np. po Crash Landing) też
    # otwiera inwazję - walka naziemna wybucha bez lądowania.
    landable = landable or bool(_contested(new_state, registry, active, attacker))
    # Lądowanie prosto z planet (G'hom Sek'kus) - także bez statków i sił w przestrzeni (F_norr).
    landable = landable or rules_hooks.permits(
        rules_hooks.POINT_INVASION_COMMIT_FROM_PLANETS, new_state, attacker
    )
    # Tekklar Conditioning (RULES.md 62.1): prosto do Commit Ground Forces, bez Bombardment.
    skip_bombard = rules_hooks.permits(
        rules_hooks.POINT_INVASION_SKIP_BOMBARDMENT, new_state, attacker
    )
    if skip_bombard or not bombard_groups(new_state, registry):
        if not landable:
            new_state.invasion = None
            return new_state
        triggers.fire(
            new_state, GameEvent.INVASION, Moment.START, subject=attacker,
            ctx={"position": active, "player": attacker},
        )
        return _enter(new_state, grid, registry, InvasionPhase.COMMIT)
    triggers.fire(
        new_state, GameEvent.INVASION, Moment.START, subject=attacker,
        ctx={"position": active, "player": attacker},
    )
    return new_state


def clear_invasion(state: GameState) -> GameState:
    """Zamyka inwazję (wyjście z kroku, koniec akcji) — nie rusza jednostek.

    Emituje ``INVASION`` / ``END``: wygasają efekty „do końca inwazji” (Blitz, Bunker, Disable).
    """
    new_state = state.clone()
    if new_state.invasion is not None:
        triggers.fire(
            new_state, GameEvent.INVASION, Moment.END, subject=new_state.invasion.attacker,
            ctx={"position": new_state.invasion.position, "player": new_state.invasion.attacker},
        )
    new_state.invasion = None
    return new_state


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
        and not (banned and banned & set(exploration.planet_traits(registry, i.planet)))
    ]


def granted_bombard_hits_on(state: GameState) -> int | None:
    """Próg trafień Bombardment nadanego statkom bez niego (Blitz) albo ``None`` (brak efektu)."""
    values = rules_hooks.forbidden(
        rules_hooks.POINT_BOMBARDMENT_GRANTED, state, _inv(state).attacker
    )
    numbers = [int(v) for v in values if str(v).isdigit()]
    return min(numbers) if numbers else None


def _bombard_modifier(state: GameState, planet: str) -> int:
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
    groups: list[BombardGroup] = []
    granted = granted_bombard_hits_on(state)
    for bt, count in sorted(system.space_units.get(invasion.attacker, {}).items()):
        if count <= 0 or not is_space_unit(bt):
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
        modifier = _bombard_modifier(state, item.planet)
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


def _ground_units(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    planet: str,
    player_id: str,
) -> dict[str, battle.CombatUnit]:
    """Jednostki walczące gracza na planecie (jak w walce naziemnej: wariant, uszkodzenia)."""
    inv = _inv(state)
    return {
        u.base_type: u
        for u in battle.combat_units(
            state,
            grid,
            registry,
            kind="ground",
            position=inv.position,
            planet=planet,
            player_id=player_id,
        )
    }


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
    _sustain_events(new_state, defender, battle.sustained_of(plan, sustain))
    del new_inv.bombard_pending[planet]
    return new_state


# ----------------------------------------------------------------------- commit ground


def commit_ground_forces(
    state: GameState,
    registry: StaticDataRegistry,
    commits: dict[str, dict[str, int]],
) -> GameState:
    """Ląduje siły naziemne z przestrzeni na planety: ``{planeta: {base_type: liczba}}`` (I2).

    Jednostki od tej chwili stoją NA planecie (liczą się dla efektów gry). Można wołać wiele
    razy; razem nie można zlądować więcej, niż stoi w przestrzeni. Uszkodzenia jadą z
    jednostkami. Kontrolę planety ustala dopiero Establish Control.

    Raises:
        ValueError: Zły podkrok, planeta spoza systemu, to nie siła naziemna, brak jednostek.
    """
    inv = _phase(state, InvasionPhase.COMMIT, "Commit Ground Forces")
    _require_tactical_commit(inv)
    planets = set(system_planets(state, registry, inv.position))
    sealed = custodians.landing_blocked(state, registry, inv.position)
    system = _system(state)
    # Parley: siły zwrócone do przestrzeni nie mogą w tej akcji lądować na inną planetę.
    available = {
        bt: n - inv.parley_locked.get(bt, 0)
        for bt, n in _ground_in_zone(system, "space", inv.attacker).items()
    }
    wanted: dict[str, int] = {}
    for planet, by_type in commits.items():
        for base_type, count in by_type.items():
            if count <= 0:
                continue
            if planet not in planets:
                raise ValueError(f"{planet} is not a planet of the active system.")
            if planet in sealed:
                raise ValueError(
                    "The Custodians token blocks landing on Mecatol Rex - "
                    "remove it first (spend 6 influence)."
                )
            if planet_stats.is_demilitarized(state, planet):
                raise ValueError(_DMZ_REASON)
            if base_type not in GROUND_FORCES:
                raise ValueError(f"{base_type} is not a ground force.")
            wanted[base_type] = wanted.get(base_type, 0) + count
    if not wanted:
        raise ValueError("Choose ground forces to commit.")
    for base_type, count in wanted.items():
        if count > available.get(base_type, 0):
            raise ValueError(
                f"Only {available.get(base_type, 0)} {base_type} in the space area."
            )

    new_state = state.clone()
    new_inv = _inv(new_state)
    new_system = _system(new_state)
    commit_ctx = {"player": new_inv.attacker, "position": new_inv.position, "units": dict(wanted)}
    new_inv.last_commit = {}  # okno „po zaangażowaniu” dotyczy TEGO zaangażowania
    triggers.fire(
        new_state, GameEvent.UNITS_COMMITTED, Moment.WHEN, subject=new_inv.attacker,
        ctx=commit_ctx,
    )
    for planet, by_type in commits.items():
        for base_type, count in by_type.items():
            if count <= 0:
                continue
            # Lądowanie: z przestrzeni na planetę, uszkodzenia jadą razem z jednostkami.
            unit_ops.transfer_units(
                new_state, new_system, "space", new_system, planet, new_inv.attacker,
                base_type, count,
            )
            landed = new_inv.committed.setdefault(planet, {})
            landed[base_type] = landed.get(base_type, 0) + count
            latest = new_inv.last_commit.setdefault(planet, {})
            latest[base_type] = latest.get(base_type, 0) + count
    triggers.fire(
        new_state, GameEvent.UNITS_COMMITTED, Moment.AFTER, subject=new_inv.attacker,
        ctx=commit_ctx,
    )
    return new_state


def commit_from_planets(
    state: GameState,
    registry: StaticDataRegistry,
    moves: list[tuple[str, str, str, str]],
) -> GameState:
    """Lądowanie sił naziemnych PROSTO z planet (nie z przestrzeni) — RULES.md 62.1.

    ``moves`` = ``[(pozycja źródła, planeta źródła, base_type, planeta celu)]``; po 1 jednostce na
    wpis. Legalność źródeł (np. „up to 1 from each planet”, sąsiedztwo, żetony) sprawdza efekt
    komponentu, który to umożliwia (G'hom Sek'kus); tu: krok COMMIT, cel w aktywnym systemie,
    Custodians, typ siły naziemnej i dostępność jednostki. Emituje ``UNITS_COMMITTED`` jak zwykłe
    lądowanie.

    Raises:
        ValueError: Zły podkrok, cel spoza aktywnego systemu, brak jednostki na planecie źródła.
    """
    new_state = state.clone()
    apply_commit_from_planets(new_state, registry, moves)
    return new_state


def apply_commit_from_planets(
    new_state: GameState,
    registry: StaticDataRegistry,
    moves: list[tuple[str, str, str, str]],
) -> None:
    """Jak :func:`commit_from_planets`, ale MUTUJE ``new_state`` (efekty komponentów na klonie)."""
    inv = _phase(new_state, InvasionPhase.COMMIT, "Commit Ground Forces")
    _require_tactical_commit(inv)
    planets = set(system_planets(new_state, registry, inv.position))
    sealed = custodians.landing_blocked(new_state, registry, inv.position)
    if not moves:
        raise ValueError("Choose ground forces to commit.")
    new_inv = _inv(new_state)
    target_system = _system(new_state)
    wanted: dict[str, int] = {}
    for _pos, _src, base_type, _dest in moves:
        wanted[base_type] = wanted.get(base_type, 0) + 1
    commit_ctx = {"player": new_inv.attacker, "position": new_inv.position, "units": wanted}
    new_inv.last_commit = {}
    triggers.fire(
        new_state, GameEvent.UNITS_COMMITTED, Moment.WHEN, subject=new_inv.attacker,
        ctx=commit_ctx,
    )
    for position, source_planet, base_type, dest in moves:
        if dest not in planets:
            raise ValueError(f"{dest} is not a planet of the active system.")
        if dest in sealed:
            raise ValueError(
                "The Custodians token blocks landing on Mecatol Rex - remove it first."
            )
        if planet_stats.is_demilitarized(new_state, dest):
            raise ValueError(_DMZ_REASON)
        if base_type not in GROUND_FORCES:
            raise ValueError(f"{base_type} is not a ground force.")
        source = new_state.systems.get(position)
        have = (
            source.planet_units.get(source_planet, {}).get(new_inv.attacker, {}).get(base_type, 0)
            if source is not None
            else 0
        )
        if source is None or have <= 0:
            raise ValueError(f"No {base_type} of yours on {source_planet}.")
        unit_ops.transfer_units(
            new_state, source, source_planet, target_system, dest, new_inv.attacker,
            base_type, 1,
        )
        landed = new_inv.committed.setdefault(dest, {})
        landed[base_type] = landed.get(base_type, 0) + 1
        latest = new_inv.last_commit.setdefault(dest, {})
        latest[base_type] = latest.get(base_type, 0) + 1
    triggers.fire(
        new_state, GameEvent.UNITS_COMMITTED, Moment.AFTER, subject=new_inv.attacker,
        ctx=commit_ctx,
    )


# ------------------------------------------------------------------- żeton Custodians


def custodians_block_reason(state: GameState, registry: StaticDataRegistry) -> str | None:
    """Dlaczego aktywny gracz NIE może teraz zdjąć żetonu Custodians (``None`` = może).

    Żeton wolno zdjąć przed Commit Ground Forces (Bombardment albo początek Commit, zanim
    cokolwiek wylądowało), gdy leży na Mecatol Rex i gracz ma siły naziemne do zlądowania.
    """
    inv = _inv(state)
    if not custodians.mecatol_planets(state, registry, inv.position):
        return "This is not the Mecatol Rex system."
    if not custodians.on_board(state):
        return "The Custodians token has already been removed."
    if inv.phase not in (InvasionPhase.BOMBARDMENT, InvasionPhase.COMMIT) or inv.committed:
        return "The token can be removed only before the Commit Ground Forces step."
    if not _ground_in_zone(_system(state), "space", inv.attacker):
        return "You need ground forces in orbit to land on Mecatol Rex."
    return None


def claim_custodians(
    state: GameState,
    registry: StaticDataRegistry,
    planets: list[str],
    trade_goods: int,
) -> GameState:
    """Aktywny gracz zdejmuje żeton Custodians za 6 wpływu (+1 VP, faza agendy w grze).

    Od tej chwili musi zlądować co najmniej jedną siłę naziemną na Mecatol Rex
    (``advance`` nie wypuści z Commit bez tego).

    Raises:
        ValueError: Zły moment, brak sił naziemnych, żeton już zdjęty, zła płatność.
    """
    inv = _inv(state)
    reason = custodians_block_reason(state, registry)
    if reason is not None:
        raise ValueError(reason)
    new_state = custodians.remove_token(state, registry, inv.attacker, planets, trade_goods)
    _inv(new_state).custodians_claimed = True
    return new_state


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


def _sustain_events(state: GameState, player_id: str, used: dict[str, int]) -> None:
    """``UNIT_SUSTAIN_DAMAGE/AFTER`` dla każdego typu, który użył Sustain Damage (MUTUJE)."""
    for base_type, count in used.items():
        if count > 0:
            triggers.fire(
                state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject=player_id,
                ctx={"player": player_id, "base_type": base_type, "count": count},
            )


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


# ------------------------------------------------------------------------- ground combat


def _contested(
    state: GameState, registry: StaticDataRegistry, position: str, attacker: str
) -> list[str]:
    """Planety systemu, na których ``attacker`` i inny gracz mają siły naziemne (I7 / I7a).

    Nie patrzy na ``committed``: siły mogły trafić na planetę bez lądowania (Crash Landing,
    koegzystencja) - walka i tak wybucha w kroku Invasion (decyzja użytkownika, RULES.md 40.1).
    """
    system = state.systems.get(position)
    if system is None:
        return []
    return [
        p
        for p in system_planets(state, registry, position)
        if _ground_in_zone(system, p, attacker) and _defenders(state, p, position, attacker)
    ]


def combat_planets(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Planety, na których atakujący i inny gracz mają siły naziemne — tu toczy się walka (I7)."""
    inv = _inv(state)
    return _contested(state, registry, inv.position, inv.attacker)


# ------------------------------------------------------------------------ establish control


def _establish_control(state: GameState, registry: StaticDataRegistry) -> None:
    """Establish Control (I5) — MUTUJE ``state`` (klon): przejęcie planet, struktury, karta.

    Planety przejęte bez wcześniejszego właściciela są EKSPLOROWANE (RULES.md 46): otwiera się
    okno eksploracji, które blokuje zamknięcie inwazji do rozstrzygnięcia kart.
    """
    inv = _inv(state)
    system = _system(state)
    attacker = state.players.get(inv.attacker)
    results: list[dict[str, Any]] = []
    # Planety lądowania + planety walki bez lądowania (Crash Landing - RULES.md 40.1 I7a).
    for planet in sorted(set(inv.committed) | set(inv.combat_results)):
        owner = system.planet_owners.get(planet)
        combat_result = inv.combat_results.get(planet)
        attacker_present = bool(_ground_in_zone(system, planet, inv.attacker))
        result: dict[str, Any] = {
            "planet": planet,
            "previousOwner": owner,
            "outcome": "lost",
            "destroyedStructures": {},
            "explore": False,
        }
        if attacker_present and owner == inv.attacker:
            result["outcome"] = "already_controlled"
        elif attacker_present:
            destroyed: dict[str, dict[str, int]] = {}
            for pid in list(system.planet_units.get(planet, {})):
                if pid == inv.attacker:
                    continue
                structures = {
                    bt: n
                    for bt, n in system.planet_units[planet][pid].items()
                    if n > 0 and bt not in GROUND_FORCES and not is_space_unit(bt)
                }
                # Struktury przeciwnika znikają przy zdobyciu planety (nie wracają przez rezerwę).
                for bt, n in structures.items():
                    unit_ops.remove_units(
                        state, system, planet, pid, bt, n, UnitCause.DESTROYED
                    )
                if structures:
                    destroyed[pid] = structures
            control.set_planet_control(state, inv.position, planet, inv.attacker, registry)
            if attacker is not None:
                # Zdobyta planeta zostaje wyczerpana (zachowanie bez zmian, RULES.md 21/40).
                exhaust.exhaust_planets(state, inv.attacker, [planet])
            result["outcome"] = "captured"
            if owner is not None and owner in state.players:
                chronicle.record_conquest(state, inv.attacker, owner, planet)
            result["destroyedStructures"] = destroyed
            result["explore"] = owner is None and exploration.explorable(registry, planet)
        elif combat_result is not None and combat_result.get("outcome") == "draw":
            defender = str(combat_result["defender"])
            result["outcome"] = "retained"
            if owner != defender:
                control.set_planet_control(state, inv.position, planet, defender)
        results.append(result)
    inv.results = results
    explored = [str(r["planet"]) for r in results if r["explore"]]
    if explored:
        exploration.start_exploration(state, registry, inv.attacker, inv.position, explored)


# --------------------------------------------------------------- inwazja komponentu (62.10)


def _require_tactical_commit(inv: InvasionState) -> None:
    if inv.source:
        raise ValueError(
            "Only the units committed by the ability take part in this invasion "
            "(ground forces in the space area cannot be committed)."
        )


def _has_capacity_ship(state: GameState, system: SystemState, player_id: str) -> bool:
    registry = rules_hooks.bound_registry()
    if registry is None:
        return False
    for base_type, count in system.space_units.get(player_id, {}).items():
        unit = unit_variant(state, registry, player_id, base_type) if count > 0 else None
        if unit is not None and unit.is_ship and (unit.capacity_value or 0) > 0:
            return True
    return False


def _open_component(
    state: GameState,
    attacker: str,
    source: str,
    position: str,
    committed: dict[str, dict[str, int]],
    queue: list[dict[str, Any]],
) -> None:
    """Otwiera inwazję komponentu w systemie ``position`` w kroku COMMIT (MUTUJE ``state``).

    Jednostki już stoją na planetach (zaangażowane przez efekt); okno „po zaangażowaniu”
    (Ghost Squad, Parley) dotyczy tego zaangażowania. Bez zdarzenia startu inwazji i bez
    aktywacji systemu (F_yin Ω).
    """
    landed = {planet: dict(by_type) for planet, by_type in committed.items()}
    state.invasion = InvasionState(
        position=position, attacker=attacker, phase=InvasionPhase.COMMIT,
        committed=landed, last_commit={p: dict(b) for p, b in landed.items()},
        source=source, queue=list(queue),
    )
    units: dict[str, int] = {}
    for by_type in landed.values():
        for base_type, count in by_type.items():
            units[base_type] = units.get(base_type, 0) + count
    triggers.fire(
        state, GameEvent.UNITS_COMMITTED, Moment.AFTER, subject=attacker,
        ctx={"player": attacker, "position": position, "units": units},
    )


def start_component_invasion(
    state: GameState,
    attacker: str,
    source: str,
    commits: dict[str, dict[str, dict[str, int]]],
) -> None:
    """Inwazja komponentu poza akcją taktyczną (Quantum Dissemination) — MUTUJE ``state``.

    ``commits`` = ``{pozycja: {planeta: {base_type: n}}}`` jednostek JUŻ postawionych na
    planetach. Systemy rozstrzygane po kolei (kolejność pozycji), każdy w oknie inwazji od kroku
    Commit Ground Forces, potem Ground Combat i Establish Control (RULES.md 62.10).

    Raises:
        ValueError: Trwa inna inwazja albo brak zaangażowanych jednostek.
    """
    if state.invasion is not None:
        raise ValueError("Another invasion is in progress.")
    order = [pos for pos in sorted(commits) if commits[pos]]
    if not order:
        raise ValueError("No ground forces were committed.")
    queue = [{"position": pos, "committed": commits[pos]} for pos in order[1:]]
    _open_component(state, attacker, source, order[0], commits[order[0]], queue)


# ------------------------------------------------------------------------------ nawigacja


def advance(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Przechodzi do następnego podkroku inwazji; z ESTABLISH — zamyka inwazję.

    Raises:
        ValueError: Gdy bieżący podkrok jest nierozstrzygnięty (oczekujące straty, trwa walka,
            niewykorzystane Space Cannon Defense, planeta czeka na walkę).
    """
    inv = _inv(state)
    if inv.phase is InvasionPhase.BOMBARDMENT:
        if inv.bombard_pending:
            raise ValueError("Assign the bombardment hits first.")
        return _enter(state, grid, registry, InvasionPhase.COMMIT)
    if inv.phase is InvasionPhase.COMMIT:
        if inv.custodians_claimed and not any(
            p in inv.committed for p in custodians.mecatol_planets(state, registry, inv.position)
        ):
            raise ValueError(
                "You removed the Custodians token - commit at least one ground force "
                "to Mecatol Rex."
            )
        if not inv.committed and not combat_planets(state, registry):
            # Brak lądowania i spornych planet: od razu do Establish Control — I2 / I7a.
            return _enter(state, grid, registry, InvasionPhase.ESTABLISH)
        if inv.source:
            # Quantum Dissemination: „Players cannot use SPACE CANNON against these units” i tylko
            # Commit / Ground Combat / Establish Control (F_yin Ω, RULES.md 62.10).
            return _enter(state, grid, registry, InvasionPhase.GROUND_COMBAT)
        return _enter(state, grid, registry, InvasionPhase.SPACE_CANNON_DEFENSE)
    if inv.phase is InvasionPhase.SPACE_CANNON_DEFENSE:
        if inv.defense_pending:
            raise ValueError("Assign the Space Cannon hits first.")
        if _defense_open(inv, state, registry):
            raise ValueError("Resolve (or decline) Space Cannon Defense on every planet first.")
        return _enter(state, grid, registry, InvasionPhase.GROUND_COMBAT)
    if inv.phase is InvasionPhase.GROUND_COMBAT:
        if state.active_combat is not None:
            raise ValueError("Finish and close the ground combat first.")
        if combat_planets(state, registry):
            raise ValueError("Ground combat is still to be fought on a planet.")
        return _enter(state, grid, registry, InvasionPhase.ESTABLISH)
    if state.exploration is not None:
        raise ValueError("Finish exploring the captured planets first.")
    closed = clear_invasion(state)
    if inv.queue:
        # Inwazja komponentu: kolejny system z kolejki (RULES.md 62.10).
        nxt, *rest = inv.queue
        _open_component(
            closed, inv.attacker, inv.source, str(nxt["position"]), nxt["committed"], rest
        )
    return closed


# ------------------------------------------------- reakcje kart (RULES.md 53.5.d, MUTUJĄ stan)
# Efekty kart akcji grane W REAKCJI na okno inwazji pracują na klonie wołającego (jak
# ``register_effect``), więc poniższe funkcje zmieniają przekazany ``state`` w miejscu.


def parley_return(state: GameState, planet: str) -> dict[str, int]:
    """Parley: zwraca siły zaangażowane OSTATNIO na ``planet`` do przestrzeni aktywnego systemu.

    Źródło: C_action_cards (Parley) - dotyczy sił tylko JEDNEJ planety, a zwrócone jednostki
    nie mogą w tej akcji lądować na inną planetę (``parley_locked``). ⚠ ZAŁOŻENIE: „zaangażowane
    jednostki” = ostatnie zaangażowanie na tę planetę (``last_commit``), bez tych, które
    zdążyły zniknąć. Zwraca ``{base_type: liczba}`` faktycznie zwróconych.

    Raises:
        ValueError: Zły podkrok albo brak świeżo zaangażowanych sił na planecie.
    """
    inv = _phase(state, InvasionPhase.COMMIT, "Commit Ground Forces")
    latest = inv.last_commit.get(planet)
    if not latest:
        raise ValueError(f"No units were just committed to {planet}.")
    system = _system(state)
    returned: dict[str, int] = {}
    # Quantum Dissemination (F_yin Ω): bez statków z pojemnością w systemie piechota schodzi z
    # planszy; z nimi wraca do przestrzeni (limit pojemności sprawdzany później).
    to_board = not inv.source or _has_capacity_ship(state, system, inv.attacker)
    for base_type, count in sorted(latest.items()):
        here = _ground_in_zone(system, planet, inv.attacker).get(base_type, 0)
        move = min(count, here)
        if move <= 0:
            continue
        if to_board:
            unit_ops.transfer_units(
                state, system, planet, system, "space", inv.attacker, base_type, move
            )
        else:
            unit_ops.remove_units(state, system, planet, inv.attacker, base_type, move)
        returned[base_type] = move
        landed = inv.committed.get(planet, {})
        landed[base_type] = landed.get(base_type, 0) - move
        if landed[base_type] <= 0:
            del landed[base_type]
        inv.parley_locked[base_type] = inv.parley_locked.get(base_type, 0) + move
    if not returned:
        raise ValueError(f"The committed units are no longer on {planet}.")
    if not inv.committed.get(planet):
        inv.committed.pop(planet, None)
    del inv.last_commit[planet]
    return returned


def _bombard_log_entry(inv: InvasionState, planet: str) -> dict[str, Any]:
    for entry in reversed(inv.log):
        if entry.get("phase") == "BOMBARDMENT" and entry.get("planet") == planet:
            found: dict[str, Any] = entry
            return found
    raise ValueError(f"No bombardment roll was made against {planet}.")


def _defense_log_entry(inv: InvasionState, planet: str) -> dict[str, Any]:
    for entry in reversed(inv.log):
        if entry.get("phase") == "DEFENSE" and entry.get("planet") == planet:
            found: dict[str, Any] = entry
            return found
    raise ValueError(f"No Space Cannon Defense roll was made on {planet}.")


def defense_roller(state: GameState, planet: str) -> str:
    """Gracz, który rzucił Space Cannon Defense na ``planet`` (z dziennika inwazji)."""
    return str(_defense_log_entry(_inv(state), planet)["defender"])


def cancel_defense_hits(state: GameState, planet: str, count: int = 1) -> int:
    """Anuluje do ``count`` trafień Space Cannon Defense czekających na ``planet``.

    Bez trafień planeta jest rozstrzygnięta (jak po rzucie bez trafień). Zwraca anulowane.

    Raises:
        ValueError: Brak trafień do przypisania na planecie.
    """
    inv = _inv(state)
    pending = inv.defense_pending.get(planet, 0)
    if pending <= 0:
        raise ValueError(f"There are no Space Cannon hits to cancel on {planet}.")
    cancelled = min(max(0, count), pending)
    entry = _defense_log_entry(inv, planet)
    entry["hits"] = pending - cancelled
    entry["cancelled"] = int(entry.get("cancelled", 0)) + cancelled
    if pending - cancelled > 0:
        inv.defense_pending[planet] = pending - cancelled
    else:
        del inv.defense_pending[planet]
        inv.defense_resolved.append(planet)
    return cancelled


def pending_defense_entries(state: GameState) -> tuple[str, list[dict[str, Any]]] | None:
    """Rzuty Space Cannon Defense czekające na straty jako płaska lista wpisów (kolejność jak
    w :func:`reroll_pending_defense`) i strzelający; ``None`` = brak."""
    inv = state.invasion
    if inv is None or not inv.defense_pending:
        return None
    entries = [_defense_log_entry(inv, p) for p in sorted(inv.defense_pending)]
    flat = [dict(roll) for entry in entries for roll in entry["rolls"]]
    return str(entries[0]["defender"]), flat


def pending_bombardment_entries(state: GameState) -> tuple[str, list[dict[str, Any]]] | None:
    """Rzuty Bombardment czekające na straty (płasko, kolejność jak przy przerzucie)."""
    inv = state.invasion
    if inv is None or not inv.bombard_pending:
        return None
    entries = [_bombard_log_entry(inv, p) for p in sorted(inv.bombard_pending)]
    return inv.attacker, [dict(roll) for entry in entries for roll in entry["rolls"]]


def reroll_pending_defense(
    state: GameState,
    picks: set[tuple[int, int]] | None = None,
    source: tuple[str, str] = ("scramble_frequency", "Scramble Frequency"),
) -> int:
    """Scramble Frequency na Space Cannon Defense: przerzuca kości rzutów czekających na straty.

    ⚠ ZAŁOŻENIE: gdy trafienia czekają na kilku planetach, przerzucane są wszystkie rzuty.
    Planeta bez trafień po przerzucie jest rozstrzygnięta. Zwraca sumę trafień po przerzucie.

    Raises:
        ValueError: Brak rzutu Space Cannon Defense czekającego na przypisanie strat.
    """
    inv = _inv(state)
    planets = sorted(inv.defense_pending)
    if not planets:
        raise ValueError("There is no Space Cannon Defense roll to reroll.")
    entries = [_defense_log_entry(inv, p) for p in planets]
    flat = [dict(roll) for entry in entries for roll in entry["rolls"]]
    roller = str(entries[0]["defender"])
    fresh, total = space_cannon.reroll_entries(
        state, flat, roller=roller, picks=picks, source=source
    )
    cursor = 0
    for planet, entry in zip(planets, entries, strict=True):
        size = len(entry["rolls"])
        mine = fresh[cursor : cursor + size]
        cursor += size
        hits = sum(int(r["hits"]) for r in mine)
        entry.update({"rolls": mine, "hits": hits, "rerolled": True})
        if hits > 0:
            inv.defense_pending[planet] = hits
        else:
            del inv.defense_pending[planet]
            inv.defense_resolved.append(planet)
    return total


def reroll_pending_bombardment(
    state: GameState,
    picks: set[tuple[int, int]] | None = None,
    source: tuple[str, str] = ("scramble_frequency", "Scramble Frequency"),
) -> int:
    """Scramble Frequency na Bombardment: przerzuca kości rzutów czekających na straty.

    ⚠ ZAŁOŻENIE: przerzucane są rzuty wszystkich planet, na których trafienia wciąż czekają na
    przypisanie (to jedno użycie Bombardment). Planeta bez trafień po przerzucie jest wolna.
    Zwraca sumę trafień po przerzucie.

    Raises:
        ValueError: Brak rzutu Bombardment czekającego na przypisanie strat.
    """
    inv = _inv(state)
    planets = sorted(inv.bombard_pending)
    if not planets:
        raise ValueError("There is no Bombardment roll to reroll.")
    entries = [_bombard_log_entry(inv, p) for p in planets]
    flat = [dict(roll) for entry in entries for roll in entry["rolls"]]

    def multiplier(roll: dict[str, Any]) -> int:
        return rules_hooks.modify(
            rules_hooks.POINT_COMBAT_HIT_MULTIPLIER, state, inv.attacker, 1,
            {"kind": "bombardment", "base_type": roll.get("baseType")},
        )

    fresh, total = space_cannon.reroll_entries(
        state, flat, roller=inv.attacker, multiplier=multiplier, picks=picks, source=source
    )
    cursor = 0
    for planet, entry in zip(planets, entries, strict=True):
        size = len(entry["rolls"])
        mine = fresh[cursor : cursor + size]
        cursor += size
        hits = sum(int(r["hits"]) for r in mine)
        entry.update({"rolls": mine, "hits": hits, "rerolled": True})
        if hits > 0:
            inv.bombard_pending[planet] = hits
        else:
            del inv.bombard_pending[planet]
    return total
