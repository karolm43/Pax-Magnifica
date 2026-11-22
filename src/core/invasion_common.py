"""Inwazja: modele i wspólne pomocniki (planety, obrońcy, tarcza planetarna) — RULES.md 52.

Najniższa warstwa inwazji: korzystają z niej ``invasion_bombard``, ``invasion_defense``
i ``invasion``.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core import (
    battle,
    entropic_scar,
    rules_hooks,
    space_cannon,
    triggers,
)
from src.core.combat import resolve_unit_variant
from src.core.dice import DIE_SIDES
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
    SystemState,
)
from src.core.hex_grid import HexGrid
from src.core.models import UnitDef
from src.core.neutral import variant_key
from src.core.registry import StaticDataRegistry
from src.core.system_planets import planets_of_system

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


def _ground_in_zone(
    system: SystemState, zone: str, player_id: str, extra: frozenset[str] = frozenset()
) -> dict[str, int]:
    """Siły naziemne gracza w strefie (``"space"`` = ładunek w przestrzeni albo planeta).

    ``extra`` = statki, które w tej inwazji są siłami naziemnymi (``ship_roles.ground_force_types``
    atakującego - Matriarch: myśliwce, RULES.md 62.16).
    """
    if zone == "space":
        units = system.space_units.get(player_id, {})
    else:
        units = system.planet_units.get(zone, {}).get(player_id, {})
    return {bt: n for bt, n in units.items() if n > 0 and (bt in GROUND_FORCES or bt in extra)}


def attacker_ground_types(state: GameState) -> frozenset[str]:
    """Statki atakującego, które w trwającej inwazji lądują jak siły naziemne (Matriarch)."""
    invasion = state.invasion
    if invasion is None:
        return frozenset()
    from src.core import ship_roles  # lokalnie: ship_roles -> rules_hooks -> hooki

    return ship_roles.ground_force_types(state, invasion.attacker, invasion.position)


def system_planets(
    state: GameState, registry: StaticDataRegistry, position: str
) -> list[str]:
    """Id planet systemu (z definicji kafelka + planety dołożone w grze, np. Thunder's Edge)."""
    return planets_of_system(state, registry, position)


def unit_variant(
    state: GameState, registry: StaticDataRegistry, player_id: str, base_type: str
) -> UnitDef | None:
    faction, techs, breakthrough, flipped = variant_key(state, registry, player_id)  # 50.3
    return resolve_unit_variant(registry, faction, techs, base_type, breakthrough, flipped)


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
            if entropic_scar.unit_abilities_blocked(state, position, registry):
                continue  # Entropic Scar: PLANETARY SHIELD nie działa w bliźnie (RULES.md 1.5)
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
    # War sun atakującego albo 2RAM (L1Z1X, RULES.md 62.12): tarcza nie blokuje bombardowania.
    ignores = _attacker_ignores_shield(state, registry) or rules_hooks.permits(
        rules_hooks.POINT_BOMBARDMENT_IGNORES_SHIELD, state, invasion.attacker
    )
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


def _ground_units(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    planet: str,
    player_id: str,
) -> dict[str, battle.CombatUnit]:
    """Jednostki walczące gracza na planecie (jak w walce naziemnej: wariant, uszkodzenia)."""
    inv = _inv(state)
    units = battle.combat_units(
        state, grid, registry, kind="ground", position=inv.position, planet=planet,
        player_id=player_id,
    )
    # Trafienia bombardowania i Space Cannon Defense to zdolności jednostek (Eidolon Maximum).
    return {u.base_type: u for u in battle.ability_hit_targets(state, player_id, units)}


def _sustain_events(state: GameState, player_id: str, used: dict[str, int]) -> None:
    """``UNIT_SUSTAIN_DAMAGE/AFTER`` dla każdego typu, który użył Sustain Damage (MUTUJE)."""
    for base_type, count in used.items():
        if count > 0:
            triggers.fire(
                state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject=player_id,
                ctx={"player": player_id, "base_type": base_type, "count": count},
            )
