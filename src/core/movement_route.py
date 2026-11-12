"""Podgląd trasy ruchu taktycznego dla UI: trasa, alternatywy, waypointy, statki, ładunek.

Czysta funkcja ``state -> raport`` (zero mutacji, zero HTTP). Reguły ruchu zostają w
``core/movement.py``; tu tylko składamy z nich widok „nawigacji": którędy polecą statki,
jakie są inne legalne trasy, które statki tę trasę udźwigną i jaki ładunek leży po drodze
(R_transport: statek zabiera ładunek z systemu startu i z każdego systemu, przez który
przechodzi — RULES.md 32.3 T3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core import movement
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

# Ile skoków ponad najkrótszą trasę pokazujemy jako alternatywy (bez wpływu na legalność).
_EXTRA_HOPS = 2
# Twardy limit długości tras w podglądzie (graf TI4 jest mały, ale DFS rośnie wykładniczo).
_MAX_PREVIEW_LEN = 6
_MAX_ALTERNATIVES = 6


@dataclass(frozen=True)
class RouteShip:
    """Statek ze źródła: czy dolatuje wybraną trasą i ile ładunku uniesie."""

    base_type: str
    count: int
    capacity: int
    reachable: bool
    # Dolatuje tylko z premią +1 do ruchu (Gravity Drive / Ionian Fuel Refinery): tylko 1 sztuka.
    boosted: bool
    reason: str


@dataclass
class RouteReport:
    """Wynik podglądu trasy."""

    active: str | None
    route: list[str] | None
    reason: str
    alternatives: list[list[str]] = field(default_factory=list)
    waypoints: list[str] = field(default_factory=list)
    ships: list[RouteShip] = field(default_factory=list)
    cargo: list[movement.RouteCargo] = field(default_factory=list)


def route_report(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    via: list[str],
    player_id: str,
    *,
    gravity_drive: bool = False,
    tempesta: bool = False,
) -> RouteReport:
    """Raport trasy ze ``from_pos`` do aktywnego systemu, przez waypointy ``via`` (kolejność)."""
    active = state.active_system
    if active is None:
        return RouteReport(None, None, "No active system.")
    if from_pos == active:
        return RouteReport(active, None, "The ships are already in the active system.")

    shortest = movement.route_through(state, grid, from_pos, [], player_id)
    if shortest is None:
        return RouteReport(active, None, "No legal route to the active system (R4/R6).")

    route = movement.route_through(state, grid, from_pos, via, player_id)
    reason = "" if route is not None else "No legal route through the chosen waypoints."

    boost = gravity_drive and not state.gravity_drive_used
    tempesta_on = tempesta and not state.tempesta_used

    # Najdalszy zasięg statków ze źródła wyznacza, jak długie alternatywy ma sens pokazywać.
    own = state.systems.get(from_pos)
    by_type = own.space_units.get(player_id, {}) if own is not None else {}
    reach = 0
    for base_type, count in by_type.items():
        if count <= 0 or not is_space_unit(base_type):
            continue
        move_value = movement._effective_move_value(
            state, grid, registry, from_pos, base_type, player_id,
            boost=boost, tempesta=tempesta_on, companions=list(by_type),
        )
        if move_value:
            reach = max(reach, move_value)
    max_len = min(max(reach, len(shortest) - 1 + 1), _MAX_PREVIEW_LEN)
    max_len = min(max_len, len(shortest) - 1 + _EXTRA_HOPS)
    all_routes = movement.legal_routes(state, grid, from_pos, player_id, max_len=max_len)
    alternatives = all_routes[:_MAX_ALTERNATIVES]
    # Aktualna trasa zawsze jest na liście (pierwsza), nawet gdy wypadła z limitu.
    if route is not None and route not in alternatives:
        alternatives = [route, *alternatives[: _MAX_ALTERNATIVES - 1]]
    waypoints = sorted(
        {node for r in all_routes for node in r[1:-1]} | set(via) - {from_pos, active}
    )

    ships = _ships(
        state, grid, registry, from_pos, route, player_id,
        boost=boost, tempesta=tempesta_on,
    )
    cargo = movement.route_cargo(state, registry, route, player_id) if route else []
    return RouteReport(active, route, reason, alternatives, waypoints, ships, cargo)


def _ships(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    route: list[str] | None,
    player_id: str,
    *,
    boost: bool,
    tempesta: bool,
) -> list[RouteShip]:
    """Statki gracza w ``from_pos`` z oceną, czy dolecą trasą ``route``."""
    own = state.systems.get(from_pos)
    if own is None:
        return []
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    result: list[RouteShip] = []
    # Statki startujące razem z tego systemu (Gravleash Maneuvers wyrównuje ich ruch).
    together = [bt for bt, n in own.space_units.get(player_id, {}).items() if n > 0]
    for base_type, count in sorted(own.space_units.get(player_id, {}).items()):
        if count <= 0 or not is_space_unit(base_type):
            continue
        # Nie ruszają się same (np. bazowy myśliwiec, struktury): pomijamy na liście statków.
        if movement._effective_move_value(
            state, grid, registry, from_pos, base_type, player_id,
            boost=False, tempesta=False,
        ) is None:
            continue
        capacity = movement._capacity_provided(registry, faction_id, technologies, base_type)
        if route is None:
            result.append(
                RouteShip(base_type, count, capacity, False, False, "No legal route.")
            )
            continue
        plain, reason = movement.can_move(
            state, grid, registry, from_pos, base_type, player_id, route=route,
            companions=together,
        )
        boosted = False
        if not plain and (boost or tempesta):
            boosted = movement.can_move(
                state, grid, registry, from_pos, base_type, player_id,
                boost=boost, tempesta=tempesta, route=route, companions=together,
            )[0]
        result.append(
            RouteShip(
                base_type, count, capacity, plain or boosted, boosted and not plain,
                "" if plain or boosted else reason,
            )
        )
    return result
