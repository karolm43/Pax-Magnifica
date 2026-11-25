"""Siły naziemne, które są statkami — JEDNO miejsce reguły (RULES.md 43.1a, 62.15).

Z-Grav Eidolon (rewers mecha Naaz-Rokha): „If this unit is in the space area of the active system,
it is also a ship” - tylko w kroku walki kosmicznej, w aktywnym systemie, w przestrzeni
(F_naaz_rokha eidolon 1). Eidolon Maximum (przełom): „This unit is both a ship and ground force”.
Kto ma taką jednostkę, mówi hook FORBID ``combat.space_ground_variant`` (zbiór id wariantów, których
wartości obowiązują) - tu nie ma nazw frakcji.

``finished_combat=True`` pyta o walkę, która właśnie się skończyła (cele „na koniec walki
kosmicznej”: Demonstrate Your Power liczy Z-Grav, który walczył - eidolon 5). Bez flagi rewers już
nie obowiązuje (sprawdzenie pojemności po walce liczy mechy jako ładunek - eidolon 6).
"""

from __future__ import annotations

from src.core import floating_structures, rules_hooks
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit


def space_ground_variants(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
    *,
    finished_combat: bool = False,
) -> dict[str, str]:
    """``{typ bazowy: id wariantu}`` sił naziemnych gracza w przestrzeni systemu, które TERAZ są
    statkami (z wartościami tego wariantu). Pusty słownik = tylko zwykłe statki."""
    if player_id not in state.players:
        return {}
    ctx = {"position": position, "finished_combat": finished_combat}
    found: dict[str, str] = {}
    for unit_id in sorted(rules_hooks.forbidden(
        rules_hooks.POINT_COMBAT_SPACE_GROUND_VARIANT, state, player_id, ctx
    )):
        unit = registry.units.get(unit_id)
        if unit is not None and not is_space_unit(unit.base_type):
            found[unit.base_type] = unit.id
    return found


def planet_ships(
    state: GameState, registry: StaticDataRegistry, player_id: str, position: str
) -> dict[str, tuple[str, int]]:
    """Siły naziemne gracza NA PLANECIE, które są statkami także tam (Eidolon Maximum: „is
    considered a ship for all relevant game effects”, F_naaz_rokha eidolon-maximum 2.1-2.2):
    ``{typ bazowy: (planeta, sztuki)}``. Z-Grav Eidolon nie - jest statkiem tylko w przestrzeni.

    ⚠️ ASSUMPTION: jeden egzemplarz na typ (Maximum jest jedyny); przy kilku planetach bierzemy
    pierwszą (alfabetycznie), a typ stojący w przestrzeni ma pierwszeństwo.
    """
    system = state.systems.get(position)
    if system is None or player_id not in state.players:
        return {}
    in_space = system.space_units.get(player_id, {})
    found: dict[str, tuple[str, int]] = {}
    for base_type in space_ground_variants(state, registry, player_id, position):
        if base_type in in_space or not floating_structures.ground_moves_as_ship(
            state, player_id, base_type
        ):
            continue
        for planet in sorted(system.planet_units):
            count = system.planet_units[planet].get(player_id, {}).get(base_type, 0)
            if count > 0:
                found[base_type] = (planet, count)
                break
    return found


def has_planet_ships(state: GameState, player_id: str, position: str) -> bool:
    """Czy gracz ma w systemie siłę naziemną-statek na planecie (Eidolon Maximum) - dla blokad,
    przelotu i obowiązkowej walki kosmicznej. Bez zbindowanego rejestru: nie."""
    registry = rules_hooks.bound_registry()
    return registry is not None and bool(planet_ships(state, registry, player_id, position))


def space_ships(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
    *,
    finished_combat: bool = False,
) -> dict[str, int]:
    """Statki gracza w przestrzeni systemu ``{typ: sztuki}`` razem z siłami naziemnymi, które są
    teraz statkami (Assault Cannon, Demonstrate Your Power) - także te stojące na planecie
    (Eidolon Maximum: blokuje, liczy się do celów, blokuje doki)."""
    system = state.systems.get(position)
    if system is None:
        return {}
    as_ships = space_ground_variants(
        state, registry, player_id, position, finished_combat=finished_combat
    )
    ships = {
        bt: n for bt, n in system.space_units.get(player_id, {}).items()
        if n > 0 and (is_space_unit(bt) or bt in as_ships)
    }
    for base_type, (_planet, count) in planet_ships(state, registry, player_id, position).items():
        ships[base_type] = ships.get(base_type, 0) + count
    return ships


def ground_force_types(state: GameState, player_id: str, position: str) -> frozenset[str]:
    """Statki gracza, które w inwazji w systemie ``position`` lądują i walczą jak siły naziemne
    (Matriarch Naalu: myśliwce - RULES.md 62.16). Hook FORBID ``invasion.ground_force_types``."""
    if player_id not in state.players:
        return frozenset()
    return frozenset(
        bt for bt in rules_hooks.forbidden(
            rules_hooks.POINT_INVASION_GROUND_FORCE_TYPES, state, player_id,
            {"position": position},
        )
        if is_space_unit(bt)
    )


def structure_ground_forces(state: GameState, player_id: str) -> frozenset[str]:
    """Struktury gracza, które są też siłami naziemnymi (Hel-Titan: ``pds`` - RULES.md 62.18).

    Hook FORBID ``units.structure_ground_forces``; bronią planety, walczą na niej i ją utrzymują.
    """
    if player_id not in state.players:
        return frozenset()
    return frozenset(
        rules_hooks.forbidden(rules_hooks.POINT_UNIT_STRUCTURE_GROUND_FORCES, state, player_id)
    )


def movable_ground_force_types(state: GameState, player_id: str) -> tuple[str, ...]:
    """Ground forces that effects like Decoy Operation / Transit Diodes may relocate without
    transporting: infantry, mechs and structure-ground-forces (Hel-Titan; F_ul heltitan 2)."""
    return ("infantry", "mech", *sorted(structure_ground_forces(state, player_id)))
