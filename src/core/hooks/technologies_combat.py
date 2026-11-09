"""Hooki technologii bojowych (walka, bombardowanie, ruch statków) — RULES.md 55.

Wersje kart z errata wybiera ``technology.generic_pool`` (codex4 > codex1 > base), więc efekt
rejestrujemy dla wersji WYGRYWAJĄCEJ; starsze wersje są zastąpione (``declare_superseded``).
Technologie z wyborem gracza („may”) są w ``technologies_choices.py``.

⚠ ZAŁOŻENIE (RULES.md 55.7): wybory, które w grze należą do gracza, a których UI jeszcze nie
potrafi zapytać (okno wyboru), rozstrzygamy deterministycznie NA KORZYŚĆ DECYDUJĄCEGO:
Assault Cannon - ofiara traci swój najtańszy statek niemyśliwski; Magen Defense Grid - właściciel
trafia najcenniejszą siłę naziemną, która nie może anulować trafienia Sustain Damage;
Duranium Armor - naprawiana jest najdroższa uszkodzona jednostka.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import exhaust, rules_hooks, unit_ops
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count, set_damaged
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.rules_hooks import (
    POINT_COMBAT_HIT_MULTIPLIER,
    POINT_MOVEMENT_MOVE_VALUE,
    SOURCE_TECHNOLOGY,
    HookKind,
    HookSource,
    on_event,
    register,
)
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

# Aliasy z danych (technologies/pok.json; nie z pamięci). Weryfikowane testem względem rejestru.
GRAVITY_DRIVE_ALIAS = "gd"
DURANIUM_ARMOR_ALIAS = "da"
ASSAULT_CANNON_ALIAS = "asc"
MAGEN_ALIAS = "md"  # Magen Defense Grid ΩΩ (codex4); md_base i md_c1 są zastąpione
X89_ALIAS = "x89c4"  # X-89 Bacterial Weapon ΩΩ (codex4); x89_base i x89 są zastąpione

rules_hooks.declare_superseded("technologies:md_base", "technologies:md_c1")
rules_hooks.declare_superseded("technologies:x89_base", "technologies:x89")

_STRUCTURES = ("pds", "spacedock")
_GROUND = ("infantry", "mech")
_FIGHTER = "fighter"


def _source(alias: str) -> HookSource:
    return HookSource(SOURCE_TECHNOLOGY, alias)


def _participant(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Warunek: gracz jest stroną trwającej walki."""
    return player_id in (ctx.get("attacker"), ctx.get("defender"))


def _opponent(player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["defender"] if ctx.get("attacker") == player_id else ctx["attacker"])


def _unit_cost(state: GameState, player_id: str, base_type: str) -> float:
    """Koszt wariantu jednostki gracza (0 dla nieznanej/neutralnej) - do wyboru celów hooków."""
    registry = rules_hooks.bound_registry()
    player = state.players.get(player_id)
    if registry is None:
        return 0.0
    unit = resolve_unit_variant(
        registry,
        player.faction if player is not None else None,
        player.technologies if player is not None else [],
        base_type,
        player.breakthrough_unlocked if player is not None else False,
    )
    return float(unit.cost or 0.0) if unit is not None else 0.0


def _has_sustain(state: GameState, player_id: str, base_type: str) -> bool:
    registry = rules_hooks.bound_registry()
    player = state.players.get(player_id)
    if registry is None:
        return False
    unit = resolve_unit_variant(
        registry,
        player.faction if player is not None else None,
        player.technologies if player is not None else [],
        base_type,
        player.breakthrough_unlocked if player is not None else False,
    )
    return bool(unit is not None and unit.sustain_damage)


# --- Propulsion --------------------------------------------------------------------------


@register(
    POINT_MOVEMENT_MOVE_VALUE,
    _source(GRAVITY_DRIVE_ALIAS),
    HookKind.MODIFY,
    covers=f"technologies:{GRAVITY_DRIVE_ALIAS}",
)
def gravity_drive_move_value(
    _state: GameState, _player_id: str, ctx: Mapping[str, Any]
) -> int:
    """Gravity Drive: po aktywacji +1 do wartości ruchu JEDNEGO statku w tej akcji.

    Premia jest jednorazowa na akcję taktyczną i dotyczy jednego statku - pilnuje tego
    ``movement.move_fleet`` (flaga ``boost`` w kontekście i ``GameState.gravity_drive_used``).
    """
    return 1 if ctx.get("boost") else 0


# --- Warfare: naprawa ----------------------------------------------------------------------


@on_event(
    GameEvent.COMBAT_ROUND,
    Moment.END,
    _source(DURANIUM_ARMOR_ALIAS),
    where={"phase": "combat"},
    condition=_participant,
    covers=f"technologies:{DURANIUM_ARMOR_ALIAS}",
    label="Duranium Armor",
)
def duranium_armor(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Duranium Armor: w każdej rundzie walki po przypisaniu strat naprawia 1 uszkodzoną jednostkę.

    Obowiązkowe (C_technology), także gdy przeciwnik nie zadał trafień. Naprawić można tylko
    jednostkę biorącą udział w walce, która w TEJ rundzie nie użyła Sustain Damage: od uszkodzonych
    danego typu odejmujemy te, które właśnie użyły zdolności.
    """
    system = state.systems.get(str(ctx["position"]))
    if system is None:
        return
    zone = "space" if ctx["kind"] == "space" else str(ctx["planet"])
    units = (
        system.space_units.get(player_id, {})
        if zone == "space"
        else system.planet_units.get(zone, {}).get(player_id, {})
    )
    used = ctx.get("sustained", {}).get(player_id, {})
    candidates = [
        base_type
        for base_type in units
        if damaged_count(system, zone, player_id, base_type) - used.get(base_type, 0) > 0
    ]
    if not candidates:
        return
    target = max(candidates, key=lambda bt: (_unit_cost(state, player_id, bt), bt))
    set_damaged(system, zone, player_id, target, damaged_count(system, zone, player_id, target) - 1)


# --- Warfare: start walki ------------------------------------------------------------------


def _assault_cannon_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Warunek Assault Cannon: strona walki kosmicznej ma ≥3 statki niemyśliwskie (sprawdzane
    w chwili rozstrzygania, więc straty z wcześniejszego hooka przeciwnika mogą go odebrać)."""
    if ctx.get("kind") != "space" or not _participant(state, player_id, ctx):
        return False
    system = state.systems.get(str(ctx["position"]))
    ships = system.space_units.get(player_id, {}) if system is not None else {}
    return sum(n for bt, n in ships.items() if bt != _FIGHTER and is_space_unit(bt)) >= 3


@on_event(
    GameEvent.COMBAT,
    Moment.START,
    _source(ASSAULT_CANNON_ALIAS),
    condition=_assault_cannon_ready,
    covers=f"technologies:{ASSAULT_CANNON_ALIAS}",
    label="Assault Cannon",
)
def assault_cannon(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Assault Cannon: na początku walki kosmicznej przeciwnik niszczy 1 swój statek niemyśliwski.

    Obowiązkowe. Wybór statku należy do przeciwnika - ⚠ ZAŁOŻENIE: traci najtańszy (RULES.md 55.7).
    Sustain Damage nie chroni przed tym zniszczeniem (C_technology).
    """
    opponent = _opponent(player_id, ctx)
    system = state.systems.get(str(ctx["position"]))
    if system is None:
        return
    ships = {
        bt: n
        for bt, n in system.space_units.get(opponent, {}).items()
        if n > 0 and bt != _FIGHTER and is_space_unit(bt)
    }
    if not ships:
        return
    victim = min(ships, key=lambda bt: (_unit_cost(state, opponent, bt), bt))
    unit_ops.remove_units(state, system, "space", opponent, victim, 1, UnitCause.DESTROYED)


# --- Warfare: Magen Defense Grid ΩΩ ---------------------------------------------------------


def _structures_on(system: Any, zone: str, player_id: str) -> int:
    units = system.planet_units.get(zone, {}).get(player_id, {})
    return sum(units.get(bt, 0) for bt in _STRUCTURES)


@on_event(
    GameEvent.SYSTEM_ACTIVATED,
    Moment.WHEN,
    _source(MAGEN_ALIAS),
    covers=f"technologies:{MAGEN_ALIAS}",
    label="Magen Defense Grid: infantry",
)
def magen_place_infantry(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Magen Defense Grid ΩΩ: aktywacja systemu z Twoimi strukturami → 1 piechota przy każdej.

    Niezależnie od tego, kto aktywuje (C_technology); piechota trafia na planetę struktury.
    ⚠ Struktura w przestrzeni (Saar, Floating Factory) nie jest modelowana.
    """
    system = state.systems.get(str(ctx["position"]))
    if system is None:
        return
    for zone in sorted(system.planet_units):
        count = _structures_on(system, zone, player_id)
        if count > 0:
            unit_ops.place_units(state, system, zone, player_id, "infantry", count)


def _magen_ground_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("kind") != "ground" or not _participant(state, player_id, ctx):
        return False
    system = state.systems.get(str(ctx["position"]))
    return system is not None and _structures_on(system, str(ctx["planet"]), player_id) > 0


@on_event(
    GameEvent.COMBAT,
    Moment.START,
    _source(MAGEN_ALIAS),
    condition=_magen_ground_ready,
    covers=f"technologies:{MAGEN_ALIAS}",
    label="Magen Defense Grid: hit",
)
def magen_hit(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Magen Defense Grid ΩΩ: na początku walki naziemnej na planecie z Twoją strukturą
    zadaj 1 trafienie siłom naziemnym przeciwnika.

    Wybór celu należy do właściciela technologii. ⚠ ZAŁOŻENIE (RULES.md 55.7): trafiamy
    najcenniejszą siłę, która NIE może anulować trafienia przez Sustain Damage; gdy wszystkie mogą,
    trafiona jednostka używa Sustain Damage (zostaje uszkodzona).
    """
    opponent = _opponent(player_id, ctx)
    system = state.systems.get(str(ctx["position"]))
    planet = str(ctx["planet"])
    if system is None:
        return
    forces = {
        bt: n
        for bt, n in system.planet_units.get(planet, {}).get(opponent, {}).items()
        if n > 0 and bt in _GROUND
    }
    if not forces:
        return

    def can_absorb(base_type: str) -> bool:
        undamaged = forces[base_type] - damaged_count(system, planet, opponent, base_type)
        return _has_sustain(state, opponent, base_type) and undamaged > 0

    pool = [bt for bt in forces if not can_absorb(bt)] or list(forces)
    target = max(pool, key=lambda bt: (_unit_cost(state, opponent, bt), bt))
    if can_absorb(target):
        set_damaged(
            system, planet, opponent, target, damaged_count(system, planet, opponent, target) + 1
        )
    else:
        unit_ops.remove_units(state, system, planet, opponent, target, 1, UnitCause.DESTROYED)


# --- Biotic: X-89 Bacterial Weapon ΩΩ --------------------------------------------------------


@register(
    POINT_COMBAT_HIT_MULTIPLIER,
    _source(X89_ALIAS),
    HookKind.MODIFY,
    covers=f"technologies:{X89_ALIAS}",
)
def x89_double_hits(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    """X-89 ΩΩ: podwaja trafienia z bombardowania i z rzutów w walce NAZIEMNEJ.

    Jednostki naziemne walczące jak statki w walce kosmicznej nie podwajają (C_technology).
    """
    return 1 if ctx.get("kind") in ("ground", "bombardment") else 0


@on_event(
    GameEvent.UNIT_ABILITY_USED,
    Moment.AFTER,
    _source(X89_ALIAS),
    where={"ability": "bombardment"},
    condition=lambda _s, pid, ctx: ctx.get("player") == pid,
    covers=f"technologies:{X89_ALIAS}",
    label="X-89: exhaust planets",
)
def x89_exhaust_planets(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    """X-89 ΩΩ: każda planeta, przeciw której użyto BOMBARDMENT, zostaje wyczerpana.

    ⚠ Bombardowanie planety bez sił naziemnych (dozwolone przez tę kartę) nie jest modelowane.
    """
    for planet in ctx.get("planets", []):
        for pid, player in state.players.items():
            if planet in player.controlled_planets:
                exhaust.exhaust_planets(state, pid, [planet])
