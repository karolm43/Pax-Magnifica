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

from dataclasses import dataclass
from typing import Any

from src.core import battle, chronicle, exhaust, exploration, space_cannon
from src.core.combat import resolve_unit_variant
from src.core.damage import move_damage
from src.core.dice import DIE_SIDES, count_hits, roll_dice
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.models import UnitDef
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

# Siły naziemne (mogą lądować i walczyć na planecie); struktury (pds/spacedock) NIE.
GROUND_FORCES = frozenset({"infantry", "mech"})


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
    has_shield: bool = False  # na planecie stoi jednostka z tarczą (nawet gdy war sun ją łamie)


@dataclass(frozen=True)
class BombardAssignment:
    """Przydział ``count`` statków typu ``base_type`` do bombardowania ``planet``."""

    base_type: str
    planet: str
    count: int


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
    """Id planet systemu (z definicji kafelka)."""
    system = state.systems.get(position)
    if system is None:
        return []
    definition = registry.systems.get(system.system_id)
    return list(definition.planets) if definition is not None else []


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


def _planet_shielded(
    state: GameState, registry: StaticDataRegistry, planet: str
) -> bool:
    """Czy na planecie stoi jednostka innego gracza z Planetary Shield (I4)."""
    invasion = _inv(state)
    system = _system(state)
    for pid, by_type in system.planet_units.get(planet, {}).items():
        if pid == invasion.attacker:
            continue
        for bt, count in by_type.items():
            if count <= 0:
                continue
            unit = unit_variant(state, registry, pid, bt)
            if unit is not None and unit.planetary_shield:
                return True
    return False


def planet_infos(state: GameState, registry: StaticDataRegistry) -> list[PlanetInfo]:
    """Planety aktywnego systemu: właściciel, obrońcy (siły naziemne), tarcza, Space Cannon."""
    invasion = _inv(state)
    system = _system(state)
    ignores = _attacker_ignores_shield(state, registry)
    infos: list[PlanetInfo] = []
    for planet in system_planets(state, registry, invasion.position):
        has_shield = _planet_shielded(state, registry, planet)
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
                shielded=(not ignores) and has_shield,
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
    if not bombard_groups(new_state, registry):
        if not landable:
            new_state.invasion = None
            return new_state
        return _enter(new_state, grid, registry, InvasionPhase.COMMIT)
    return new_state


def clear_invasion(state: GameState) -> GameState:
    """Zamyka inwazję (wyjście z kroku, koniec akcji) — nie rusza jednostek."""
    new_state = state.clone()
    new_state.invasion = None
    return new_state


# ------------------------------------------------------------------------- bombardment


def bombard_targets(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Planety, które wolno bombardować: są na nich cudze siły naziemne i brak tarczy (I3/I4)."""
    return [i.planet for i in planet_infos(state, registry) if i.defenders and not i.shielded]


def bombard_groups(state: GameState, registry: StaticDataRegistry) -> list[BombardGroup]:
    """Statki atakującego z Bombardment w aktywnym systemie (puste, gdy brak celu)."""
    invasion = _inv(state)
    system = _system(state)
    if not bombard_targets(state, registry):
        return []
    groups: list[BombardGroup] = []
    for bt, count in sorted(system.space_units.get(invasion.attacker, {}).items()):
        if count <= 0 or not is_space_unit(bt):
            continue
        unit = unit_variant(state, registry, invasion.attacker, bt)
        if unit is None or not unit.bombard_hits_on or unit.bombard_hits_on <= 0:
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


def bombard(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    assignments: list[BombardAssignment],
) -> GameState:
    """Bombardowanie: rzut dla każdego przydziału; trafienia czekają na przypisanie strat (I3).

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
    for item in assignments:
        if item.count <= 0:
            continue
        group = groups[item.base_type]
        rolled, dice = roll_dice(rolled, item.count * group.dice_per_unit)
        hits = count_hits(dice, group.hits_on)
        entry = by_planet.setdefault(item.planet, {"rolls": [], "hits": 0})
        entry["rolls"].append(
            {
                "baseType": item.base_type,
                "name": group.name,
                "count": item.count,
                "hitsOn": group.hits_on,
                "dice": dice,
                "hits": hits,
            }
        )
        entry["hits"] += hits

    new_state = rolled.clone()
    inv = _inv(new_state)
    inv.bombarded = True
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
    return new_state


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
    return min(pending, sum(u.count + u.sustainable for u in units.values()))


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
    plan = battle.plan_losses(units, sustain, destroy, destroy_damaged, required)

    new_state = state.clone()
    new_inv = _inv(new_state)
    battle.apply_losses(new_state, new_inv.position, planet, defender, units, plan)
    for entry in reversed(new_inv.log):
        if entry.get("phase") == "BOMBARDMENT" and entry.get("planet") == planet:
            entry["losses"] = battle.losses_of(units, plan)
            entry["sustained"] = battle.sustained_of(plan, sustain)
            break
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
    planets = set(system_planets(state, registry, inv.position))
    system = _system(state)
    available = _ground_in_zone(system, "space", inv.attacker)
    wanted: dict[str, int] = {}
    for planet, by_type in commits.items():
        for base_type, count in by_type.items():
            if count <= 0:
                continue
            if planet not in planets:
                raise ValueError(f"{planet} is not a planet of the active system.")
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
    space = new_system.space_units[new_inv.attacker]
    for planet, by_type in commits.items():
        for base_type, count in by_type.items():
            if count <= 0:
                continue
            before = space[base_type]
            space[base_type] = before - count
            if space[base_type] <= 0:
                del space[base_type]
            dest = new_system.planet_units.setdefault(planet, {}).setdefault(
                new_inv.attacker, {}
            )
            dest[base_type] = dest.get(base_type, 0) + count
            move_damage(
                new_system, "space", new_system, planet, new_inv.attacker, base_type, count, before
            )
            landed = new_inv.committed.setdefault(planet, {})
            landed[base_type] = landed.get(base_type, 0) + count
    if not space:
        del new_system.space_units[new_inv.attacker]
    return new_state


# ----------------------------------------------------------------- space cannon defense


def defense_planets(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Planety z lądowaniem, na których obrońca ma Space Cannon i atakujący wciąż ma siły (I3)."""
    inv = _inv(state)
    system = _system(state)
    result: list[str] = []
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
) -> GameState:
    """Space Cannon Defense: strzelcy na ``planet`` rzucają w zlądowane siły atakującego (I3).

    Raises:
        ValueError: Zły podkrok, planeta bez strzelców albo już rozstrzygnięta.
    """
    inv = _phase(state, InvasionPhase.SPACE_CANNON_DEFENSE, "Space Cannon Defense")
    if planet not in _defense_open(inv, state, registry):
        raise ValueError(f"Space Cannon Defense on {planet} is not available.")
    shooters = defense_shooters(state, registry, planet)
    rolled = state
    rolls: list[dict[str, Any]] = []
    total = 0
    for shooter in shooters:
        rolled, dice = roll_dice(rolled, shooter.total_dice)
        hits = count_hits(dice, shooter.hits_on)
        total += hits
        rolls.append(
            {
                "baseType": shooter.base_type,
                "name": shooter.name,
                "owner": shooter.player_id,
                "count": shooter.count,
                "hitsOn": shooter.hits_on,
                "dice": dice,
                "hits": hits,
            }
        )
    new_state = rolled.clone()
    new_inv = _inv(new_state)
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
    return min(pending, sum(u.count + u.sustainable for u in units.values()))


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
    plan = battle.plan_losses(units, sustain, destroy, destroy_damaged, required)

    new_state = state.clone()
    new_inv = _inv(new_state)
    battle.apply_losses(new_state, new_inv.position, planet, new_inv.attacker, units, plan)
    for entry in reversed(new_inv.log):
        if entry.get("phase") == "DEFENSE" and entry.get("planet") == planet:
            entry["losses"] = battle.losses_of(units, plan)
            entry["sustained"] = battle.sustained_of(plan, sustain)
            break
    del new_inv.defense_pending[planet]
    new_inv.defense_resolved.append(planet)
    return new_state


# ------------------------------------------------------------------------- ground combat


def combat_planets(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Planety, na których atakujący i inny gracz mają siły naziemne — tu toczy się walka (I4)."""
    inv = _inv(state)
    system = _system(state)
    return [
        p
        for p in system_planets(state, registry, inv.position)
        if _ground_in_zone(system, p, inv.attacker)
        and _defenders(state, p, inv.position, inv.attacker)
    ]


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
    for planet in sorted(inv.committed):
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
                for bt in structures:
                    del system.planet_units[planet][pid][bt]
                if not system.planet_units[planet][pid]:
                    del system.planet_units[planet][pid]
                if structures:
                    destroyed[pid] = structures
            system.planet_owners[planet] = inv.attacker
            if owner is not None and owner in state.players:
                prev = state.players[owner]
                prev.controlled_planets = [p for p in prev.controlled_planets if p != planet]
                exhaust.ready_planets(state, owner, [planet])
            if attacker is not None:
                if planet not in attacker.controlled_planets:
                    attacker.controlled_planets.append(planet)
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
                system.planet_owners[planet] = defender
        results.append(result)
    inv.results = results
    explored = [str(r["planet"]) for r in results if r["explore"]]
    if explored:
        exploration.start_exploration(state, registry, inv.attacker, inv.position, explored)


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
        if not inv.committed:
            # Brak lądowania: od razu do Establish Control (nic do rozstrzygania) — I2.
            return _enter(state, grid, registry, InvasionPhase.ESTABLISH)
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
    return clear_invasion(state)
