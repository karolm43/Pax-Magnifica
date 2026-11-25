"""Struktury pływające — struktura w przestrzeni, która rusza się jak statek (RULES.md 62.14).

Jedno miejsce reguły (RULES.md 43.1a) dla tekstu jednostki: „This unit is placed in the space area
instead of on a planet. This unit can move and retreat as if it were a ship. If this unit is
blockaded, it is destroyed.” (Floating Factory, Clan of Saar). Kto ma taką strukturę, mówi hook
PERMIT ``units.floating_structure`` (``ctx["base_type"]``) jednostki frakcyjnej — tu nie ma nazw
frakcji.

Struktura pływająca NIE staje się statkiem (``unit_catalog.is_space_unit`` = False): nie walczy,
nie przyjmuje trafień, nie liczy się do puli floty i nie blokuje. Rusza się i wycofuje jak statek
(``moves_as_ship``), a zablokowana (R_blockaded: w systemie są statki innego gracza, a nie ma
własnych statków) ginie (``destroy_blockaded``).
"""

from __future__ import annotations

from src.core import rules_hooks
from src.core.game_state import GameState, SystemState
from src.core.unit_catalog import is_space_unit

SPACE = "space"
_STRUCTURES = ("pds", "spacedock")
_GROUND = ("infantry", "mech")


def floats(state: GameState, player_id: str, base_type: str) -> bool:
    """Czy struktura ``base_type`` gracza stoi w przestrzeni i rusza się jak statek."""
    if base_type not in _STRUCTURES or player_id not in state.players:
        return False
    return rules_hooks.permits(
        rules_hooks.POINT_UNIT_FLOATING_STRUCTURE, state, player_id, {"base_type": base_type}
    )


def ground_moves_as_ship(state: GameState, player_id: str, base_type: str) -> bool:
    """Siła naziemna, która jest też statkiem (Eidolon Maximum, RULES.md 62.15): w przestrzeni
    rusza się sama ze swoją wartością ruchu, liczy się do puli floty, nie do pojemności."""
    if base_type not in _GROUND or player_id not in state.players:
        return False
    return rules_hooks.permits(
        rules_hooks.POINT_UNIT_GROUND_MOVES_AS_SHIP, state, player_id, {"base_type": base_type}
    )


GROUND_SHIP_POOLS = ("fleet", "capacity")


def ground_ship_in_fleet_pool(state: GameState, player_id: str, base_type: str) -> bool:
    """Siła naziemna-statek liczy się do puli floty (a nie do pojemności) - wybór gracza
    (F_naaz_rokha eidolon-maximum 3: „either capacity or fleet pool”; domyślnie pula floty)."""
    return (
        ground_moves_as_ship(state, player_id, base_type)
        and state.players[player_id].ground_ship_pool != "capacity"
    )


def choose_ground_ship_pool(state: GameState, player_id: str, pool: str) -> GameState:
    """Gracz wybiera, do czego liczy się jego siła naziemna-statek w przestrzeni: ``fleet``,
    ``capacity`` albo ``auto`` (= pula floty). Nowy stan; nadwyżkę egzekwują zwykłe okna limitów.

    Raises:
        ValueError: Nieznany gracz albo wartość.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player {player_id}.")
    choice = "fleet" if pool == "auto" else pool
    if choice not in GROUND_SHIP_POOLS:
        raise ValueError("Choose 'fleet', 'capacity' or 'auto'.")
    new_state = state.clone()
    new_state.players[player_id].ground_ship_pool = choice
    return new_state


def moves_as_ship(state: GameState, player_id: str, base_type: str) -> bool:
    """Statek, struktura pływająca albo siła naziemna-statek (ruch i odwrót „as if it were a
    ship”)."""
    return (
        is_space_unit(base_type)
        or floats(state, player_id, base_type)
        or ground_moves_as_ship(state, player_id, base_type)
    )


def landing_zone(state: GameState, player_id: str, base_type: str, zone: str) -> str:
    """Strefa, w której jednostka faktycznie staje: pływająca struktura zamiast planety - przestrzeń
    systemu tej planety („placed in the space area instead of on a planet”)."""
    if zone != SPACE and floats(state, player_id, base_type):
        return SPACE
    return zone


def has_ships(system: SystemState, player_id: str) -> bool:
    units = system.space_units.get(player_id, {})
    return any(n > 0 and is_space_unit(bt) for bt, n in units.items())


def is_blockaded(state: GameState, player_id: str, position: str) -> bool:
    """R_blockaded: w systemie nie ma statków gracza, a są statki innego gracza."""
    from src.core import ship_roles  # lokalnie: ship_roles importuje ten moduł

    system = state.systems.get(position)

    if system is None:
        return False

    def _ships(owner: str) -> bool:  # Eidolon Maximum na planecie też jest statkiem
        return has_ships(system, owner) or ship_roles.has_planet_ships(state, owner, position)

    if _ships(player_id):
        return False
    return any(owner != player_id and _ships(owner) for owner in {*system.space_units,
                                                                  *state.players})


def floating_in(state: GameState, player_id: str, position: str) -> dict[str, int]:
    """Struktury pływające gracza w przestrzeni systemu ``{base_type: sztuki}``."""
    system = state.systems.get(position)
    if system is None:
        return {}
    return {
        bt: n for bt, n in system.space_units.get(player_id, {}).items()
        if n > 0 and bt in _STRUCTURES and floats(state, player_id, bt)
    }


def destroy_blockaded(state: GameState, position: str) -> dict[str, dict[str, int]]:
    """Niszczy zablokowane struktury pływające w systemie (MUTUJE ``state``).

    Zwraca ``{gracz: {typ: sztuki}}`` zniszczonych. Wołane w chwilach, w których blokada może
    powstać: wlot statków, koniec walki kosmicznej, zniszczenie statku poza przypisywaniem strat.
    """
    from src.core import unit_ops  # lokalnie: unit_ops importuje ten moduł

    destroyed: dict[str, dict[str, int]] = {}
    system = state.systems.get(position)
    if system is None:
        return destroyed
    for owner in sorted(system.space_units):
        if not is_blockaded(state, owner, position):
            continue
        for base_type, count in sorted(floating_in(state, owner, position).items()):
            unit_ops.remove_units(
                state, system, SPACE, owner, base_type, count, unit_ops.UnitCause.DESTROYED
            )
            destroyed.setdefault(owner, {})[base_type] = count
    return destroyed
