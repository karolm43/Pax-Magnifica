"""Walka: jednostki w walce i liczenie trafień (CombatUnit, side_units, Sustain) — RULES.md 39.

Warstwa POD ``battle.py`` (bez zależności od przebiegu walki); ``battle`` eksportuje te nazwy dalej.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core import (
    entropic_scar,
    rules_hooks,
    ship_roles,
)
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count
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

    @property
    def total_dice(self) -> int:
        return self.count * self.dice_per_unit + self.bonus_dice

    @property
    def sustainable(self) -> int:
        """Ile egzemplarzy może jeszcze użyć Sustain Damage (własnego albo nadanego)."""
        return self.count - self.damaged if self.sustain else self.granted

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
    no_sustain = sustain_denied(state, player_id, position, zone)
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
    for base_type, count in sorted(_units_map(system, zone, player_id).items()):
        if count <= 0:
            continue
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
        units.append(
            CombatUnit(
                base_type=base_type,
                unit_id=unit.id,
                name=unit.name,
                count=count,
                damaged=damaged_count(system, zone, player_id, base_type),
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
                    min(1, count - damaged_count(system, zone, player_id, base_type))
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
            )
        )
    return units


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
    units = side_units(state, grid, registry, player_id)
    return min(pending, absorbable_hits(units, sustain_cancels(state, player_id)))


def absorbable_hits(units: list[CombatUnit], cancels: int) -> int:
    """Ile trafień strona może jeszcze pochłonąć: jednostki + użycia Sustain Damage × ``cancels``.

    Nadany Sustain Damage (Void Shielding) pochłania najwyżej 1 dodatkowe użycie naraz. To samo
    „życie" pokazuje okno walki (pasek HP), więc licznik strat i pasek zawsze się zgadzają.
    """
    return sum(
        u.count + (cancels * u.sustainable if u.sustain else 0) for u in units
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
