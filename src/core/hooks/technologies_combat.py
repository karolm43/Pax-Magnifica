"""Hooki technologii bojowych (walka, bombardowanie, ruch statków) — RULES.md 55.

Wersje kart z errata wybiera ``technology.generic_pool`` (codex4 > codex1 > base), więc efekt
rejestrujemy dla wersji WYGRYWAJĄCEJ; starsze wersje są zastąpione (``declare_superseded``).
Technologie z wyborem gracza („may”) są w ``technologies_choices.py``.

Wybory gracza (ofiara Assault Cannon, cel Magen, naprawa Duranium Armor) NIGDY nie są
automatyczne (RULES.md 56): hook ``decide`` pyta właściwego gracza ofertą, a stosuje wynik od
razu tylko wtedy, gdy jest dokładnie jedna legalna odpowiedź.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import exhaust, rules_hooks, unit_ops
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count, set_damaged
from src.core.fleet_pool import unit_name
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


def _unit_label(state: GameState, player_id: str, base_type: str) -> str:
    registry = rules_hooks.bound_registry()
    return unit_name(state, registry, player_id, base_type) if registry is not None else base_type


def _combat_zone(ctx: Mapping[str, Any]) -> str:
    return "space" if ctx["kind"] == "space" else str(ctx["planet"])


def _repairable(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> list[str]:
    """Typy uszkodzonych jednostek gracza w walce, które w tej rundzie nie użyły Sustain Damage."""
    system = state.systems.get(str(ctx["position"]))
    if system is None:
        return []
    zone = _combat_zone(ctx)
    units = (
        system.space_units.get(player_id, {})
        if zone == "space"
        else system.planet_units.get(zone, {}).get(player_id, {})
    )
    used = ctx.get("sustained", {}).get(player_id, {})
    return sorted(
        base_type
        for base_type in units
        if damaged_count(system, zone, player_id, base_type) - used.get(base_type, 0) > 0
    )


def duranium_armor_inputs(
    state: GameState, _registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Wybór gracza: którą uszkodzoną jednostkę naprawić (liczy silnik)."""
    return [
        oi.choice(
            "unit",
            "Damaged unit to repair",
            [
                oi.option(bt, _unit_label(state, player_id, bt))
                for bt in _repairable(state, player_id, ctx)
            ],
        )
    ]


@on_event(
    GameEvent.COMBAT_ROUND,
    Moment.END,
    _source(DURANIUM_ARMOR_ALIAS),
    where={"phase": "combat"},
    condition=_participant,
    covers=f"technologies:{DURANIUM_ARMOR_ALIAS}",
    label="Duranium Armor",
    inputs=duranium_armor_inputs,
    decide=True,
)
def duranium_armor(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Duranium Armor: w każdej rundzie walki po przypisaniu strat naprawia 1 uszkodzoną jednostkę.

    Obowiązkowe (C_technology), także gdy przeciwnik nie zadał trafień. Naprawiana jednostka
    NIE użyła w tej rundzie Sustain Damage. Wybór należy do gracza (pytamy tylko przy ≥2 typach).
    """
    system = state.systems.get(str(ctx["position"]))
    unit = ctx.get("params", {}).get("unit")
    if system is None or unit is None:
        return
    zone = _combat_zone(ctx)
    set_damaged(system, zone, player_id, unit, damaged_count(system, zone, player_id, unit) - 1)


# --- Warfare: start walki ------------------------------------------------------------------


def _assault_cannon_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Warunek Assault Cannon: strona walki kosmicznej ma ≥3 statki niemyśliwskie (sprawdzane
    w chwili rozstrzygania, więc straty z wcześniejszego hooka mogą go odebrać)."""
    if ctx.get("kind") != "space" or not _participant(state, player_id, ctx):
        return False
    system = state.systems.get(str(ctx["position"]))
    ships = system.space_units.get(player_id, {}) if system is not None else {}
    return sum(n for bt, n in ships.items() if bt != _FIGHTER and is_space_unit(bt)) >= 3


def _assault_cannon_victim(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> str:
    """Decyduje OFIARA: to ona wybiera, który jej statek niemyśliwski zostaje zniszczony."""
    return _opponent(player_id, ctx)


def assault_cannon_inputs(
    state: GameState, _registry: Any, decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Statki niemyśliwskie ofiary w systemie (neutralni - wg reguły: najtańszy)."""
    system = state.systems.get(str(ctx["position"]))
    ships = [
        bt
        for bt, n in sorted((system.space_units.get(decider, {}) if system else {}).items())
        if n > 0 and bt != _FIGHTER and is_space_unit(bt)
    ]
    if decider not in state.players and ships:  # jednostki neutralne nie podejmują decyzji
        ships = [min(ships, key=lambda bt: (_unit_cost(state, decider, bt), bt))]
    return [
        oi.choice(
            "ship",
            "Non-fighter ship to destroy",
            [oi.option(bt, _unit_label(state, decider, bt)) for bt in ships],
        )
    ]


@on_event(
    GameEvent.COMBAT,
    Moment.START,
    _source(ASSAULT_CANNON_ALIAS),
    condition=_assault_cannon_ready,
    covers=f"technologies:{ASSAULT_CANNON_ALIAS}",
    label="Assault Cannon",
    inputs=assault_cannon_inputs,
    decide=True,
    decider=_assault_cannon_victim,
)
def assault_cannon(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Assault Cannon: na początku walki kosmicznej przeciwnik niszczy 1 swój statek niemyśliwski.

    Obowiązkowe. Statek wybiera OFIARA (oferta obowiązkowa, gdy ma realny wybór).
    Sustain Damage nie chroni przed tym zniszczeniem (C_technology).
    """
    victim = str(ctx["decider"])
    ship = ctx.get("params", {}).get("ship")
    system = state.systems.get(str(ctx["position"]))
    if system is None or ship is None:
        return
    unit_ops.remove_units(state, system, "space", victim, ship, 1, UnitCause.DESTROYED)


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


def _magen_targets(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> list[str]:
    opponent = _opponent(player_id, ctx)
    system = state.systems.get(str(ctx["position"]))
    if system is None:
        return []
    forces = system.planet_units.get(str(ctx["planet"]), {}).get(opponent, {})
    return sorted(bt for bt, n in forces.items() if n > 0 and bt in _GROUND)


def magen_inputs(
    state: GameState, _registry: Any, player_id: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Wybór właściciela: w którą siłę naziemną przeciwnika trafia hit."""
    opponent = _opponent(player_id, ctx)
    return [
        oi.choice(
            "target",
            "Opponent's ground force to hit",
            [
                oi.option(bt, _unit_label(state, opponent, bt))
                for bt in _magen_targets(state, player_id, ctx)
            ],
            "Produce 1 hit and assign it to 1 of your opponent's ground forces.",
            # Druga klauzula jest obowiązkowa: gracz ma ją ZOBACZYĆ, nawet gdy cel jest jeden.
            always=True,
        )
    ]


@on_event(
    GameEvent.COMBAT,
    Moment.START,
    _source(MAGEN_ALIAS),
    condition=_magen_ground_ready,
    covers=f"technologies:{MAGEN_ALIAS}",
    label="Magen Defense Grid: hit",
    inputs=magen_inputs,
    decide=True,
)
def magen_hit(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Magen Defense Grid ΩΩ: na początku walki naziemnej na planecie z Twoją strukturą
    zadaj 1 trafienie siłom naziemnym przeciwnika.

    Cel wybiera właściciel technologii. Trafiona jednostka z nieużytym Sustain Damage
    anuluje trafienie (zostaje uszkodzona), reszta ginie (C_technology).
    """
    opponent = _opponent(player_id, ctx)
    system = state.systems.get(str(ctx["position"]))
    planet = str(ctx["planet"])
    target = ctx.get("params", {}).get("target")
    if system is None or target is None:
        return
    undamaged = (
        system.planet_units.get(planet, {}).get(opponent, {}).get(target, 0)
        - damaged_count(system, planet, opponent, target)
    )
    if _has_sustain(state, opponent, target) and undamaged > 0:
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


@register(
    rules_hooks.POINT_BOMBARD_EMPTY_PLANETS,
    _source(X89_ALIAS),
    HookKind.PERMIT,
    covers=f"technologies:{X89_ALIAS}",
)
def x89_bombard_empty_planets(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> bool:
    """X-89 ΩΩ: wolno bombardować planetę bez sił naziemnych (C_technology)."""
    return True


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

    Dotyczy też planet bez sił naziemnych (``x89_bombard_empty_planets``).
    """
    for planet in ctx.get("planets", []):
        for pid, player in state.players.items():
            if planet in player.controlled_planets:
                exhaust.exhaust_planets(state, pid, [planet])
