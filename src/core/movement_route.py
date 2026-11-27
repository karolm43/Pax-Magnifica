"""Podgląd trasy ruchu taktycznego dla UI: trasa, alternatywy, waypointy, statki, ładunek.

Czysta funkcja ``state -> raport`` (zero mutacji, zero HTTP). Reguły ruchu zostają w
``core/movement.py``; tu tylko składamy z nich widok „nawigacji": którędy polecą statki,
jakie są inne legalne trasy, które statki tę trasę udźwigną i jaki ładunek leży po drodze
(R_transport: statek zabiera ładunek z systemu startu i z każdego systemu, przez który
przechodzi — RULES.md 32.3 T3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import TypedDict

from src.core import floating_structures, ion_storm, movement, rules_hooks
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

# Ile skoków ponad najkrótszą trasę pokazujemy jako alternatywy (bez wpływu na legalność).
_EXTRA_HOPS = 2
# Twardy limit długości tras w podglądzie (graf TI4 jest mały, ale DFS rośnie wykładniczo).
_MAX_PREVIEW_LEN = 6
_MAX_ALTERNATIVES = 6


# Premie +1 do ruchu jednego statku, które gracz włącza świadomie (przełącznik w UI).
BONUS_GRAVITY_DRIVE = "gravity_drive"
BONUS_TEMPESTA = "tempesta"
BONUS_IMPERATOR = "imperator"
_BONUSES = (BONUS_GRAVITY_DRIVE, BONUS_TEMPESTA, BONUS_IMPERATOR)
# Zestawy premii od najmniejszych: pojedyncze, pary, wszystkie.
_BONUS_COMBOS: tuple[tuple[str, ...], ...] = tuple(
    combo for size in range(1, len(_BONUSES) + 1) for combo in combinations(_BONUSES, size)
)


class _BonusFlags(TypedDict):
    boost: bool
    tempesta: bool
    imperator: bool


def _flags(combo: tuple[str, ...] | list[str]) -> _BonusFlags:
    """Zestaw premii → argumenty ``movement.can_move`` / ``_effective_move_value``."""
    return {
        "boost": BONUS_GRAVITY_DRIVE in combo,
        "tempesta": BONUS_TEMPESTA in combo,
        "imperator": BONUS_IMPERATOR in combo,
    }


@dataclass(frozen=True)
class RouteShip:
    """Statek ze źródła: czy i jak dolatuje wybraną trasą oraz ile ładunku uniesie.

    ``alone`` = dolatuje sam, bez premii. ``with_ships`` = typy statków, z którymi dolatuje bez
    premii, jeśli lecą razem (Gravleash Maneuvers: ruch równy najwyższemu z ruszających).
    ``bonus_options`` = zestawy premii (Gravity Drive / Ionian Fuel Refinery), z którymi dolatuje;
    ``bonus_max`` = ile sztuk wolno wtedy ruszyć (premia działa na 1 statek, chyba że Gravleash).
    ``moves_separately`` = the ship may move before or after the player's other ships (PERMIT
    ``movement.moves_separately``, Hil Colish - RULES.md 62.19): the flight plan asks which.
    """

    base_type: str
    count: int
    capacity: int
    reachable: bool
    alone: bool
    with_ships: list[str]
    bonus_options: list[list[str]]
    bonus_max: int
    reason: str
    moves_separately: bool = False


@dataclass
class RouteReport:
    """Wynik podglądu trasy."""

    active: str | None
    route: list[str] | None
    reason: str
    alternatives: list[list[str]] = field(default_factory=list)
    waypoints: list[str] = field(default_factory=list)
    ships: list[RouteShip] = field(default_factory=list)
    # Premie do ruchu, które gracz może teraz włączyć (posiada je i nie zużył w tej akcji).
    bonuses: list[str] = field(default_factory=list)
    cargo: list[movement.RouteCargo] = field(default_factory=list)
    # Systemy trasy będące gravity rift (+1 do ruchu, rzut d10: 1–3 usuwa statek).
    rift_nodes: list[str] = field(default_factory=list)
    # Czy statki rzucają za te szczeliny (Circlet of the Void: +1 bez rzutu).
    rift_rolls: bool = True
    # Ion Storm w systemie z własnym wormholem tego typu: gracz wybiera wormhole (pozycja żetonu).
    ion_storm_choice: str | None = None


def route_report(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    via: list[str],
    player_id: str,
) -> RouteReport:
    """Raport trasy ze ``from_pos`` do aktywnego systemu, przez waypointy ``via`` (kolejność).

    Premie +1 do ruchu (Gravity Drive, Ionian Fuel Refinery) są brane pod uwagę, jeśli gracz
    może ich teraz użyć — raport mówi, który statek ich potrzebuje, a o włączeniu decyduje gracz.
    """
    active = state.active_system
    if active is None:
        return RouteReport(None, None, "No active system.")
    if from_pos == active:
        return RouteReport(active, None, "The ships are already in the active system.")

    own = state.systems.get(from_pos)
    by_type = own.space_units.get(player_id, {}) if own is not None else {}
    # Przejezdność zależy od typu statku (Corsair: przelot przez obce statki, RULES.md 62.8).
    # Najpierw trasa dla całej floty (""), potem trasy poszczególnych typów ze źródła.
    kinds = ["", *sorted(
        bt for bt, n in by_type.items()
        if n > 0 and floating_structures.moves_as_ship(state, player_id, bt)
    )]

    def first_route(waypoints: list[str]) -> list[str] | None:
        for kind in kinds:
            found = movement.route_through(state, grid, from_pos, waypoints, player_id, kind)
            if found is not None:
                return found
        return None

    shortest = first_route([])
    if shortest is None:
        return RouteReport(active, None, "No legal route to the active system (R4/R6).")

    route = first_route(via)
    reason = "" if route is not None else "No legal route through the chosen waypoints."

    bonuses = available_bonuses(state, grid, registry, from_pos, player_id)

    # Najdalszy zasięg statków ze źródła (z dostępnymi premiami) wyznacza, jak długie
    # alternatywy ma sens pokazywać.
    reach = 0
    for base_type, count in by_type.items():
        if count <= 0 or not floating_structures.moves_as_ship(state, player_id, base_type):
            continue
        move_value = movement._effective_move_value(
            state, grid, registry, from_pos, base_type, player_id,
            **_flags(bonuses), companions=list(by_type),
        )
        if move_value:
            reach = max(reach, move_value)
    # +2 zapasu na trasy przez gravity rift (każda szczelina daje +1 do ruchu).
    max_len = min(max(reach + 2, len(shortest)), _MAX_PREVIEW_LEN + 1)
    max_len = min(max_len, len(shortest) - 1 + _EXTRA_HOPS)
    all_routes: list[list[str]] = []
    for kind in kinds:
        for candidate in movement.legal_routes(
            state, grid, from_pos, player_id, max_len=max_len, base_type=kind,
        ):
            if candidate not in all_routes:
                all_routes.append(candidate)
    all_routes.sort(key=len)
    alternatives = all_routes[:_MAX_ALTERNATIVES]
    # Aktualna trasa zawsze jest na liście (pierwsza), nawet gdy wypadła z limitu.
    if route is not None and route not in alternatives:
        alternatives = [route, *alternatives[: _MAX_ALTERNATIVES - 1]]
    waypoints = sorted(
        {node for r in all_routes for node in r[1:-1]} | set(via) - {from_pos, active}
    )

    ships = _ships(state, grid, registry, from_pos, route, player_id, bonuses)
    # A flagship in the source may carry units out of systems with your command tokens
    # (Ahk-Syl Siven, RULES.md 62.21) - the move itself checks that it really carries them.
    source = state.systems.get(from_pos)
    carrier = (
        "flagship" if source is not None
        and source.space_units.get(player_id, {}).get("flagship", 0) > 0 else ""
    )
    cargo = movement.route_cargo(state, registry, route, player_id, carrier) if route else []
    # Fighter II ze startu: dolatujący sam jest na liście statków ORAZ ładunku - gracz wybiera,
    # które sztuki lecą same (liczą się do fleet pool w celu), a które jadą na nosicielu
    # (R_gravity_rift: „for each fighter, they must choose if that fighter is moving itself or
    # being transported"). Te same sztuki nie trafią w oba miejsca naraz - pilnuje ``move_fleet``
    # (dostępność ładunku ze startu minus lecące same), a w UI wspólny limit ``routeTypes``.
    # Myśliwiec, który sam nie doleci, jest tylko ładunkiem.
    ships = [s for s in ships if s.reachable or s.base_type not in movement.CARGO_BASE_TYPES]
    rifts = movement.rift_nodes(state, grid, route, player_id) if route else []
    return RouteReport(
        active, route, reason, alternatives, waypoints, ships, bonuses, cargo, rifts,
        movement.rift_rolls(state, player_id),
        ion_storm.choice_needed(state, grid, registry, from_pos, active),
    )


def available_bonuses(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    player_id: str,
) -> list[str]:
    """Premie +1 do ruchu, których gracz może teraz użyć dla statków z ``from_pos``.

    Bez sprawdzania nazw technologii/kart: premia jest dostępna, gdy nie została zużyta w tej
    akcji, a hook ``movement.move_value`` faktycznie podnosi z nią ruch któregoś statku
    (Gravity Drive - technologia; Ionian Fuel Refinery - efekt wyczerpanej karty Tempesty;
    Imperator - przełom Winnu po aktywacji systemu z planetą legendarną).
    """
    own = state.systems.get(from_pos)
    types = [
        bt for bt, n in (own.space_units.get(player_id, {}) if own else {}).items()
        if n > 0 and floating_structures.moves_as_ship(state, player_id, bt)
    ]

    def lifts(bonus: str) -> bool:
        for base_type in types:
            plain = movement._effective_move_value(
                state, grid, registry, from_pos, base_type, player_id,
                boost=False, tempesta=False,
            )
            boosted = movement._effective_move_value(
                state, grid, registry, from_pos, base_type, player_id, **_flags([bonus]),
            )
            if plain is not None and boosted is not None and boosted > plain:
                return True
        return False

    used = {
        BONUS_GRAVITY_DRIVE: state.gravity_drive_used,
        BONUS_TEMPESTA: state.tempesta_used,
        BONUS_IMPERATOR: state.imperator_used,
    }
    return [bonus for bonus in _BONUSES if not used[bonus] and lifts(bonus)]


def _ships(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    route: list[str] | None,
    player_id: str,
    bonuses: list[str],
) -> list[RouteShip]:
    """Statki gracza w ``from_pos`` z oceną, czy (i jak) dolecą trasą ``route``."""
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
        if count <= 0 or not floating_structures.moves_as_ship(state, player_id, base_type):
            continue
        # Nie ruszają się same (np. bazowy myśliwiec, struktury): pomijamy na liście statków.
        if movement._effective_move_value(
            state, grid, registry, from_pos, base_type, player_id,
            boost=False, tempesta=False,
        ) is None:
            continue
        capacity = movement._capacity_provided(registry, faction_id, technologies, base_type)
        separately = rules_hooks.permits(
            rules_hooks.POINT_MOVEMENT_MOVES_SEPARATELY, state, player_id,
            {"base_type": base_type},
        )
        if route is None:
            result.append(
                RouteShip(
                    base_type, count, capacity, False, False, [], [], 1, "No legal route.",
                    moves_separately=separately,
                )
            )
            continue
        def ok(
            companions: list[str], combo: tuple[str, ...] = (), base_type: str = base_type
        ) -> tuple[bool, str]:
            return movement.can_move(
                state, grid, registry, from_pos, base_type, player_id,
                **_flags(combo),
                route=route, companions=companions,
            )

        alone, reason = ok([base_type])
        # Gravleash: z którymi towarzyszami (lecącymi razem) statek dolatuje bez premii.
        with_ships = (
            []
            if alone
            else [other for other in together if other != base_type and ok([base_type, other])[0]]
        )
        # Premie: tylko dostępne zestawy; gdy dolatuje i bez nich, nie ma czego proponować.
        bonus_options = (
            []
            if alone
            else [
                list(combo)
                for combo in _BONUS_COMBOS
                if all(b in bonuses for b in combo) and ok(together, combo)[0]
            ]
        )
        # Premia działa na jeden statek, chyba że ruch wyrównuje się do najwyższego (Gravleash).
        matched = base_type != "fighter" and rules_hooks.permits(
            rules_hooks.POINT_MOVEMENT_MATCH_HIGHEST, state, player_id
        )
        reachable = alone or bool(with_ships) or bool(bonus_options)
        result.append(
            RouteShip(
                base_type=base_type,
                count=count,
                capacity=capacity,
                reachable=reachable,
                alone=alone,
                with_ships=with_ships,
                bonus_options=bonus_options,
                bonus_max=count if matched else 1,
                reason="" if reachable else reason,
                moves_separately=separately,
            )
        )
    return result
