"""Walka: jednostki w walce i liczenie trafień (CombatUnit, side_units, Sustain) — RULES.md 39.

Warstwa POD ``battle.py`` (bez zależności od przebiegu walki); ``battle`` eksportuje te nazwy dalej.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src.core import (
    entropic_scar,
    rules_hooks,
    ship_roles,
)
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count, sustain_spent
from src.core.dice import DIE_SIDES
from src.core.game_state import (
    ActiveCombat,
    GameState,
    SystemState,
)
from src.core.hex_grid import HexGrid
from src.core.neutral import variant_key
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

# Anomalia dająca obrońcy +1 do rzutów combat w walce kosmicznej (R_nebula; RULES.md 39 W6).
_NEBULA = "NEBULA"
_FIGHTER = "fighter"


@dataclass(frozen=True)
class CombatUnit:
    """Grupa jednostek gracza w walce (jeden typ) — wartości z wariantu gracza."""

    base_type: str
    unit_id: str
    name: str
    count: int
    damaged: int
    hits_on: int  # próg PO modyfikatorze (np. mgławica: obrońca 6 → 5)
    base_hits_on: int  # próg z danych
    modifier: int  # +N do wyniku rzutu (mgławica: +1 obrońcy)
    dice_per_unit: int
    sustain: bool
    afb_hits_on: int | None
    afb_dice: int
    # Sustain Damage NADANY przez komponent jednostce bez własnego (Metali Void Shielding): ile
    # egzemplarzy może go teraz użyć. Łącznie wolno użyć najwyżej 1 takiego (zob. ``plan_losses``).
    granted: int = 0
    # Dodatkowe kości dla całej grupy (nie na egzemplarz) — agent Letnev (RULES.md 62.2).
    bonus_dice: int = 0
    # +X do wyników kości JEDNEGO egzemplarza (pierwszego w grupie) — Gravleash Maneuvers.
    single_bonus: int = 0
    # Strefa jednostki, gdy różni się od strefy walki (Eidolon Maximum na planecie w walce
    # kosmicznej); pusty = strefa walki.
    zone: str = ""
    # A non-ship unit that only cancels hits against its owner's ships with SUSTAIN DAMAGE: no
    # dice, never destroyed by these hits, does not keep a side alive (Quantum Manipulator).
    shield: bool = False
    # ONE ship of the group fights with other values (The Cavalry, RULES.md 62.21): combat value
    # and dice, AFB value and dice, and SUSTAIN DAMAGE while it is undamaged.
    champion_hits_on: int | None = None
    champion_dice: int = 0
    champion_afb_hits_on: int | None = None
    champion_afb_dice: int = 0
    champion_sustain: bool = False
    champion_label: str = ""
    # Undamaged units of the group that already used SUSTAIN DAMAGE in this timing window and were
    # repaired since (Dynamo): they cannot use it again in the window (F_empyrean dynamo 1).
    spent: int = 0

    @property
    def total_dice(self) -> int:
        if self.champion_hits_on is not None and self.count > 0:
            return (self.count - 1) * self.dice_per_unit + self.champion_dice + self.bonus_dice
        return self.count * self.dice_per_unit + self.bonus_dice

    @property
    def sustainable(self) -> int:
        """Ile egzemplarzy może jeszcze użyć Sustain Damage (własnego albo nadanego).

        Units that already used it in this timing window (``spent``, repaired since) cannot
        (F_empyrean dynamo 1, C_action_cards reflective-shielding 1.1)."""
        if self.sustain:
            return max(0, self.count - self.damaged - self.spent)
        return self.granted + (1 if self.champion_sustain else 0)

    @property
    def has_afb(self) -> bool:
        """Whether the group rolls Anti-Fighter Barrage (its own or its champion's)."""
        return self.afb_hits_on is not None or self.champion_afb_hits_on is not None

    @property
    def expected_hits(self) -> float:
        chance = max(0, min(DIE_SIDES, DIE_SIDES + 1 - self.hits_on)) / DIE_SIDES
        return round(self.total_dice * chance, 2)


def _zone(kind: str, planet: str | None) -> str:
    return "space" if kind == "space" else (planet or "")


def _units_map(system: SystemState | None, zone: str, player_id: str) -> dict[str, int]:
    if system is None:
        return {}
    if zone == "space":
        return system.space_units.get(player_id, {})
    return system.planet_units.get(zone, {}).get(player_id, {})


def combat_units(
    state: GameState,
    grid: HexGrid | None,
    registry: StaticDataRegistry,
    *,
    kind: str,
    position: str,
    planet: str | None,
    player_id: str,
    defender: bool = False,
) -> list[CombatUnit]:
    """Jednostki gracza biorące udział w walce (W2/W3), z wartościami jego wariantu.

    Kosmiczna: statki w przestrzeni z wartością combat. Naziemna: siły naziemne na
    planecie z wartością combat (struktury bez combat pomijane). ``defender`` włącza
    modyfikator mgławicy (+1, tylko walka kosmiczna — W6).
    """
    system = state.systems.get(position)
    # Wariant gracza albo neutralnych (ulepszone jednostki - RULES.md 50.3).
    faction, techs, breakthrough, flipped = variant_key(state, registry, player_id)
    zone = _zone(kind, planet)
    terrain_modifier = (
        1
        if defender and kind == "space" and grid is not None
        and _NEBULA in grid.anomalies_at(position)
        else 0
    )
    # Entropic Scar (RULES.md 1.5): w bliźnie żadna zdolność jednostek (tu AFB) nie działa.
    scar = entropic_scar.unit_abilities_blocked(state, position, registry)
    as_ships = (
        ship_roles.space_ground_variants(state, registry, player_id, position)
        if kind == "space" else {}
    )
    # Statki walczące na planecie jak siły naziemne (Matriarch: myśliwce - RULES.md 62.16).
    as_ground = (
        ship_roles.ground_force_types(state, player_id, position) if kind != "space"
        else frozenset()
    )
    units: list[CombatUnit] = []
    # {typ: (liczba, strefa)}; w walce kosmicznej także statek-siła naziemna stojący na planecie
    # (Eidolon Maximum walczy w kosmosie, nawet gdy jest na planecie - F_naaz_rokha 2.1).
    in_zone = {bt: (n, zone) for bt, n in _units_map(system, zone, player_id).items() if n > 0}
    if kind == "space":
        for bt, (planet_zone, n) in ship_roles.planet_ships(
            state, registry, player_id, position
        ).items():
            in_zone.setdefault(bt, (n, planet_zone))
    for base_type, (count, unit_zone) in sorted(in_zone.items()):
        no_sustain = sustain_denied(state, player_id, position, unit_zone)
        if base_type in as_ships:
            unit = registry.units.get(as_ships[base_type])
        elif base_type not in as_ground and is_space_unit(base_type) != (kind == "space"):
            continue
        else:
            unit = resolve_unit_variant(
                registry, faction, techs, base_type, breakthrough, flipped
            )
        if unit is None or unit.combat_hits_on is None:
            continue
        # Hooki MODIFY: +N do wyniku rzutu i dodatkowe kości (zdolności, technologie) obok
        # terenu (mgławica).
        hook_ctx = {
            "kind": kind, "position": position, "planet": planet,
            "defender": defender, "base_type": base_type,
        }
        modifier = terrain_modifier + rules_hooks.modify(
            rules_hooks.POINT_COMBAT_ROLL_MODIFIER, state, player_id, 0, hook_ctx
        )
        extra_dice = rules_hooks.modify(
            rules_hooks.POINT_COMBAT_EXTRA_DICE, state, player_id, 0, hook_ctx
        )
        bonus_dice = rules_hooks.modify(
            rules_hooks.POINT_COMBAT_BONUS_DICE, state, player_id, 0, hook_ctx
        )
        single_bonus = rules_hooks.modify(
            rules_hooks.POINT_COMBAT_SINGLE_UNIT_BONUS, state, player_id, 0, hook_ctx
        )
        champion = (
            _champion(state, player_id, base_type, hook_ctx)
            if kind == "space" and base_type != _FIGHTER else None
        )
        group_damaged = damaged_count(system, unit_zone, player_id, base_type)
        # Repaired after SUSTAIN DAMAGE in this window (Dynamo): no second use (dynamo 1).
        spent = min(count - group_damaged,
                    sustain_spent(state, position, unit_zone, player_id, base_type))
        units.append(
            CombatUnit(
                base_type=base_type,
                unit_id=unit.id,
                name=unit.name,
                count=count,
                damaged=damaged_count(system, unit_zone, player_id, base_type),
                hits_on=unit.combat_hits_on - modifier,
                base_hits_on=unit.combat_hits_on,
                modifier=modifier,
                # 0 kości dozwolone (Salai Sai Corian bez statków niemyśliwskich przeciwnika).
                dice_per_unit=max(0, (unit.combat_die_count or 1) + extra_dice),
                sustain=unit.sustain_damage and not no_sustain and base_type not in (
                    rules_hooks.forbidden(rules_hooks.POINT_UNIT_SUSTAIN_LOST, state, player_id)
                ),
                afb_hits_on=unit.afb_hits_on if kind == "space" and not scar else None,
                afb_dice=unit.afb_die_count or 1,
                granted=(
                    min(1, count - group_damaged - spent)
                    if kind == "space"
                    and not no_sustain
                    and base_type != _FIGHTER
                    and not unit.sustain_damage
                    and rules_hooks.permits(
                        rules_hooks.POINT_COMBAT_GRANTED_SUSTAIN, state, player_id, hook_ctx
                    )
                    else 0
                ),
                bonus_dice=max(0, bonus_dice),
                single_bonus=single_bonus,
                zone=unit_zone if unit_zone != zone else "",
                spent=spent,
                **_champion_fields(
                    champion, unit.sustain_damage, no_sustain, group_damaged + spent, scar
                ),
            )
        )
    return units


def _champion(
    state: GameState, player_id: str, base_type: str, hook_ctx: Mapping[str, Any]
) -> tuple[int, int, int | None, int, str] | None:
    """Values ONE ship of this group fights with (hook ``combat.champion`` - The Cavalry)."""
    for raw in sorted(rules_hooks.forbidden(
        rules_hooks.POINT_COMBAT_CHAMPION, state, player_id, hook_ctx
    )):
        parts = str(raw).split("|")
        if len(parts) < 5 or parts[0] != base_type:
            continue
        afb = int(parts[3]) if parts[3] else None
        label = parts[5] if len(parts) > 5 else ""
        return int(parts[1]), int(parts[2]), afb, int(parts[4] or 0), label
    return None


def _champion_fields(
    champion: tuple[int, int, int | None, int, str] | None,
    own_sustain: bool,
    no_sustain: bool,
    damaged: int,
    scar: bool,
) -> dict[str, Any]:
    if champion is None:
        return {}
    hits_on, dice, afb_hits_on, afb_dice, label = champion
    return {
        "champion_hits_on": hits_on,
        "champion_dice": dice,
        "champion_afb_hits_on": None if scar else afb_hits_on,
        "champion_afb_dice": afb_dice,
        # A damaged ship of a type without SUSTAIN DAMAGE is the champion itself (F_nomad
        # the-cavalry 2.1): it cannot use the ability again.
        "champion_sustain": not own_sustain and not no_sustain and damaged == 0,
        "champion_label": label,
    }


def damaged_with_sustain(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
    zone: str,
    base_type: str,
) -> int:
    """How many of the player's DAMAGED units of a group currently have SUSTAIN DAMAGE
    ("repair all of your units that have SUSTAIN DAMAGE" - Emergency Repairs).

    Own ability (variant; lost / denied ability does not count). A type without it has it only
    through The Cavalry while the combat lasts: then the damaged ship is the champion itself, so
    at most 1 (F_nomad the-cavalry 2, 2.4).
    """
    system = state.systems.get(position)
    damaged = damaged_count(system, zone, player_id, base_type)
    if damaged <= 0:
        return 0
    faction, techs, breakthrough, flipped = variant_key(state, registry, player_id)
    unit = resolve_unit_variant(registry, faction, techs, base_type, breakthrough, flipped)
    if unit is not None and unit.sustain_damage:
        lost = base_type in rules_hooks.forbidden(
            rules_hooks.POINT_UNIT_SUSTAIN_LOST, state, player_id
        )
        return 0 if lost or sustain_denied(state, player_id, position, zone) else damaged
    combat = state.active_combat
    if (
        combat is None or combat.kind != "space" or combat.position != position
        or zone != "space" or base_type == _FIGHTER
        or player_id not in (combat.attacker, combat.defender)
    ):
        return 0
    hook_ctx = {"kind": "space", "position": position, "planet": combat.planet,
                "defender": player_id == combat.defender, "base_type": base_type}
    return 1 if _champion(state, player_id, base_type, hook_ctx) is not None else 0


def hit_shields(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[CombatUnit]:
    """The player's non-ship units that may cancel hits against their ships in the ONGOING space
    combat (hook ``combat.hit_shields`` - Quantum Manipulator, RULES.md 62.21).

    Not a combatant: no dice, only SUSTAIN DAMAGE. Only Entropic Scar stops it (a unit ability);
    "other players' ships lose SUSTAIN DAMAGE" (Fourth Moon) does not - it is not a ship (2.1).
    """
    combat = state.active_combat
    if combat is None or combat.kind != "space" or player_id not in (
        combat.attacker, combat.defender
    ):
        return []
    types = rules_hooks.forbidden(
        rules_hooks.POINT_COMBAT_HIT_SHIELDS, state, player_id, {"position": combat.position}
    )
    if not types or entropic_scar.unit_abilities_blocked(state, combat.position, registry):
        return []
    system = state.systems.get(combat.position)
    own = system.space_units.get(player_id, {}) if system is not None else {}
    faction, techs, breakthrough, flipped = variant_key(state, registry, player_id)
    shields: list[CombatUnit] = []
    for base_type in sorted(types):
        count = own.get(base_type, 0)
        if count <= 0 or is_space_unit(base_type):
            continue
        unit = resolve_unit_variant(registry, faction, techs, base_type, breakthrough, flipped)
        if unit is None or not unit.sustain_damage:
            continue
        damaged = damaged_count(system, "space", player_id, base_type)
        shields.append(CombatUnit(
            base_type=base_type, unit_id=unit.id, name=unit.name, count=count,
            damaged=damaged,
            hits_on=DIE_SIDES + 1, base_hits_on=DIE_SIDES + 1, modifier=0, dice_per_unit=0,
            sustain=True, afb_hits_on=None, afb_dice=0, shield=True,
            spent=min(count - damaged,
                      sustain_spent(state, combat.position, "space", player_id, base_type)),
        ))
    return shields


def assign_units(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player_id: str
) -> list[CombatUnit]:
    """Rows of the player's hit assignment: units in the combat + hit shields (62.21)."""
    return [*side_units(state, grid, registry, player_id), *hit_shields(state, registry, player_id)]


def ability_hit_targets(
    state: GameState, player_id: str, units: list[CombatUnit]
) -> list[CombatUnit]:
    """Jednostki, którym wolno przypisać trafienia ze ZDOLNOŚCI jednostek (Space Cannon,
    bombardowanie). Odporne (Eidolon Maximum) odpadają: trafienia idą na inne jednostki grupy,
    a bez nich przepadają (F_naaz_rokha eidolon-maximum 2)."""
    immune = rules_hooks.forbidden(rules_hooks.POINT_COMBAT_ABILITY_HIT_IMMUNE, state, player_id)
    return [u for u in units if u.base_type not in immune] if immune else units


def sustain_denied(state: GameState, player_id: str, position: str, zone: str) -> bool:
    """Czy jednostki gracza w strefie systemu tracą SUSTAIN DAMAGE (hook innego gracza).

    Punkt ``combat.sustain_denied`` pytany o KAŻDEGO innego gracza (Fourth Moon: statki w
    systemie, Moll Terminus: siły naziemne na planecie — RULES.md 62.8). Jedno miejsce dla walki,
    Space Cannon i inwazji (wszystkie biorą jednostki z ``combat_units``).
    """
    if entropic_scar.unit_abilities_blocked(state, position):
        return True  # Entropic Scar: SUSTAIN DAMAGE to zdolność jednostki (RULES.md 1.5)
    ctx = {"victim": player_id, "position": position, "zone": zone}
    return any(
        rules_hooks.permits(rules_hooks.POINT_COMBAT_SUSTAIN_DENIED, state, other, ctx)
        for other in state.players
        if other != player_id
    )


def side_units(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player_id: str
) -> list[CombatUnit]:
    """Jednostki gracza w TRWAJĄCEJ walce (z modyfikatorem obrońcy)."""
    combat = _combat(state)
    return combat_units(
        state,
        grid,
        registry,
        kind=combat.kind,
        position=combat.position,
        planet=combat.planet,
        player_id=player_id,
        defender=player_id == combat.defender,
    )


def required_hits(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player_id: str
) -> int:
    """Ile trafień gracz musi pokryć: min(trafienia, jednostki + Sustain Damage) — W7."""
    combat = _combat(state)
    pending = combat.pending_hits.get(player_id, 0)
    units = assign_units(state, grid, registry, player_id)
    return min(pending, absorbable_hits(units, sustain_cancels(state, player_id)))


def absorbable_hits(units: list[CombatUnit], cancels: int) -> int:
    """Ile trafień strona może jeszcze pochłonąć: jednostki + użycia Sustain Damage × ``cancels``.

    Nadany Sustain Damage (Void Shielding) pochłania najwyżej 1 dodatkowe użycie naraz. To samo
    „życie" pokazuje okno walki (pasek HP), więc licznik strat i pasek zawsze się zgadzają.
    """
    return sum(
        (0 if u.shield else u.count) + (cancels * u.sustainable if u.sustain else 0)
        + (cancels if not u.sustain and u.champion_sustain else 0)
        for u in units
    ) + (cancels if any(u.granted > 0 for u in units) else 0)


def sustain_cancels(state: GameState, player_id: str) -> int:
    """Ile trafień anuluje jedno użycie Sustain Damage gracza (1; Non-Euclidean Shielding: 2)."""
    return 1 + max(
        0, rules_hooks.modify(rules_hooks.POINT_COMBAT_SUSTAIN_CANCELS, state, player_id, 0, {})
    )


def _combat(state: GameState) -> ActiveCombat:
    if state.active_combat is None:
        raise ValueError("No combat is in progress.")
    return state.active_combat
