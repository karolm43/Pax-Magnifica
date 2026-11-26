"""Ruch statków w akcji taktycznej: walidacja legalności + wykonanie (Etap E8-T5).

Pierwsza twarda egzekucja mechaniki taktycznej (RULES.md 29.1): ruch przestaje być
tylko God-Mode. Reguły R1–R6 spisane w RULES.md 32 (źródło: LRR R_movement /
R_tactical_action). Funkcje CZYSTE (``state -> state`` przez klon), bez HTTP.

Zakres T5 („make it exist first", z haczykami pod rozbudowę): ruch POJEDYNCZEGO stosu
jednego typu statku ze źródła do aktywnego systemu. Transport (capacity), wybór trasy
pod gravity rift i ruch zdolnościami — TODO (oznaczone). Pathfinding: BFS szukający
istnienia legalnej trasy o długości ≤ moveValue (węzły pośrednie respektują R4/R6).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from itertools import combinations as _combinations
from typing import Any

from src.core import floating_structures, ion_storm, rules_hooks, timing, triggers, unit_ops
from src.core.combat import player_variant, resolve_unit_variant
from src.core.dice import DIE_SIDES, next_rng, record_table_roll
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, MoveLoss, SystemState
from src.core.hex_grid import HexGrid
from src.core.movement_paths import (
    _GRAVITY_RIFT,
    _NEBULA,
    _RIFT_REMOVED_ON,
    _RIFT_SEARCH_CAP,
    _RIFT_SEARCH_EXTRA,
    _SUPERNOVA,
    _ignores_own_command_token,
    _rift_route_within,
    _shortest_legal_distance,
    _target_passable,
)
from src.core.movement_paths import _can_enter_asteroids as _can_enter_asteroids
from src.core.movement_paths import _ignores_anomalies as _ignores_anomalies
from src.core.movement_paths import _neighbors_for_move as _neighbors_for_move
from src.core.movement_paths import _node_passable_intermediate as _node_passable_intermediate
from src.core.movement_paths import build_move_record as build_move_record
from src.core.movement_paths import can_enter_supernova as can_enter_supernova
from src.core.movement_paths import can_pass_supernova as can_pass_supernova
from src.core.movement_paths import legal_routes as legal_routes
from src.core.movement_paths import passage_blocked as passage_blocked
from src.core.movement_paths import rift_bonus as rift_bonus
from src.core.movement_paths import rift_nodes as rift_nodes
from src.core.movement_paths import rift_roll_nodes as rift_roll_nodes
from src.core.movement_paths import rift_rolls as rift_rolls
from src.core.movement_paths import rolls_at as rolls_at
from src.core.movement_paths import route_error as route_error
from src.core.movement_paths import route_through as route_through
from src.core.movement_paths import shortest_legal_path as shortest_legal_path
from src.core.movement_paths import wormhole_link_blocked as wormhole_link_blocked
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause

# Jednostki, które mogą być ŁADUNKIEM transportu (R_transport): myśliwce i siły
# naziemne. To jedyne jednostki zajmujące capacity (``capacityUsed``). Źródło:
# R_capacity/R_transport — „fighters and ground forces". Trzymane jawnie, bo to
# reguła klasy jednostek, nie dane liczbowe (te czytamy z UnitDef).
_CARGO_BASE_TYPES = frozenset({"fighter", "infantry", "mech"})
CARGO_BASE_TYPES = _CARGO_BASE_TYPES  # publiczny alias (podgląd trasy)
_FIGHTER = "fighter"  # Gravleash: „non-fighter ships”


@dataclass(frozen=True)
class CargoPickup:
    """Pozycja ładunku do zabrania: typ, liczba i STREFA źródłowa (RULES.md 32.3 T3).

    ``from_zone`` = ``"space"`` (ładunek z przestrzeni systemu źródłowego) albo id
    planety w tym systemie (statek zabiera piechotę/mecha z planety). Myśliwce
    pobiera się tylko z przestrzeni (nie stoją na planetach).
    """

    base_type: str
    count: int
    from_zone: str = "space"
    # System, z którego zabieramy ładunek: None = system startu ruchu. Inny system musi
    # leżeć NA TRASIE (R_transport: „each system it moves through").
    from_position: str | None = None

@dataclass(frozen=True)
class RouteCargo:
    """Ładunek do zabrania w systemie na trasie (UI rysuje go na trasie)."""

    position: str
    zone: str
    base_type: str
    count: int
    capacity_used: int


def route_cargo(
    state: GameState,
    registry: StaticDataRegistry,
    route: list[str],
    player_id: str,
) -> list[RouteCargo]:
    """Myśliwce i siły naziemne gracza do zabrania w systemach trasy (bez celu).

    Źródło: R_transport — statek zabiera ładunek z systemu startu i z każdego systemu,
    przez który przechodzi (RULES.md 32.3 T3). Systemy z WŁASNYM żetonem dowodzenia są
    pominięte (T4), chyba że efekt to znosi (Dominus Orb). Myśliwce tylko z przestrzeni.
    Ostatni element trasy to aktywny system: statek może zabrać stamtąd siły naziemne z planet
    (R_transport: „the active system"), więc jest on ostatnim punktem poboru.
    """
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    ignore_cc = _ignores_own_command_token(state, player_id)
    result: list[RouteCargo] = []
    for position in route:
        system = state.systems.get(position)
        if system is None:
            continue
        # Cel trasy (aktywny system): T4 go nie dotyczy, a ładunek w jego przestrzeni już tam jest -
        # do zabrania zostają tylko siły naziemne z planet (np. do inwazji na inną planetę).
        is_destination = position == route[-1]
        if (
            player_id in system.command_tokens
            and not ignore_cc
            and position != route[0]
            and not is_destination
        ):
            continue
        zones: list[tuple[str, dict[str, int]]] = (
            [] if is_destination else [("space", system.space_units.get(player_id, {}))]
        )
        zones += [
            (planet, by_player.get(player_id, {}))
            for planet, by_player in sorted(system.planet_units.items())
        ]
        for zone, units in zones:
            for base_type, count in sorted(units.items()):
                if count <= 0 or base_type not in _CARGO_BASE_TYPES:
                    continue
                if base_type == "fighter" and zone != "space":
                    continue
                result.append(
                    RouteCargo(
                        position=position,
                        zone=zone,
                        base_type=base_type,
                        count=count,
                        capacity_used=_capacity_used(
                            registry, faction_id, technologies, base_type
                        ),
                    )
                )
    return result








def _effective_move_value(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    base_type: str,
    player_id: str,
    *,
    boost: bool,
    tempesta: bool,
    imperator: bool = False,
    companions: Iterable[str] | None = None,
    single: bool = True,
) -> int | None:
    """Wartość ruchu statku ``base_type`` startującego z ``from_pos`` (None = nie rusza się sam).

    ``companions`` = typy statków ruszających RAZEM z tego samego systemu: z PERMIT
    ``movement.match_highest`` statek niemyśliwski dostaje najwyższą z ich wartości (Gravleash).

    R2: wartość z WARIANTU jednostki gracza (ulepszenia wg technologii; np. Fighter II ma
    moveValue=2, bazowy myśliwiec jedzie tylko transportem). R7: start w mgławicy daje 1
    (Nav Suite to znosi). Potem hook MODIFY (technologie, zdolności, premie ``boost``).
    """
    player = state.players.get(player_id)
    unit = player_variant(registry, player, base_type) if player is not None else None
    move_value = unit.move_value if unit is not None else None
    if not move_value or move_value <= 0:
        return None
    # R7 (R_nebula, RULES.md 32.1): statek ZACZYNAJĄCY krok ruchu w mgławicy traktuje swoją
    # wartość ruchu jako 1; inne efekty (Gravity Drive — hook niżej) mogą ją podnieść.
    if (
        _NEBULA in grid.anomalies_at(from_pos)
        and not _ignores_anomalies(state, player_id)
        and not rules_hooks.permits(rules_hooks.POINT_MOVEMENT_NEBULA_IGNORED, state, player_id)
    ):  # Voidborn (RULES.md 62.20): nebulae do not affect the player's movement
        move_value = 1
    if single:
        # Wartość JEDNEGO statku podniesiona do zadanej (Captain Mendosa, RULES.md 62.14): po
        # regule mgławicy (F_saar mendosa 3), przed premiami MODIFY. ``single=False`` = stos
        # większy niż 1 sztuka - premia dotyczy tylko jednego statku.
        move_value = max(move_value, single_ship_target(state, player_id, from_pos, base_type))
    result = int(
        rules_hooks.modify(
            rules_hooks.POINT_MOVEMENT_MOVE_VALUE, state, player_id, move_value,
            {
                "base_type": base_type, "boost": boost, "tempesta": tempesta,
                "imperator": imperator, "from": from_pos,
            },
        )
    )
    others = [bt for bt in companions or () if bt != base_type]
    if (
        others
        and base_type != _FIGHTER
        and rules_hooks.permits(rules_hooks.POINT_MOVEMENT_MATCH_HIGHEST, state, player_id)
    ):
        # F_letnev: premia jednego statku (Gravity Drive, Ionian Fuel Refinery) podnosi też
        # wartość, do której wyrównują pozostałe — towarzysz liczony z tą samą premią.
        for other in others:
            value = _effective_move_value(
                state, grid, registry, from_pos, other, player_id,
                boost=boost, tempesta=tempesta, imperator=imperator,
            )
            if value is not None:
                result = max(result, value)
    return result


def single_ship_target(state: GameState, player_id: str, from_pos: str, base_type: str) -> int:
    """Docelowa wartość ruchu jednego statku ``base_type`` z ``from_pos`` (0 = brak efektu)."""
    return int(rules_hooks.modify(
        rules_hooks.POINT_MOVEMENT_SINGLE_SHIP_VALUE, state, player_id, 0,
        {"from": from_pos, "base_type": base_type},
    ))


def can_move(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    base_type: str,
    player_id: str,
    *,
    boost: bool = False,
    tempesta: bool = False,
    imperator: bool = False,
    route: list[str] | None = None,
    companions: Iterable[str] | None = None,
    single: bool = True,
) -> tuple[bool, str]:
    """Sprawdza, czy ruch stosu ``base_type`` ze ``from_pos`` do aktywnego jest legalny.

    Zwraca ``(True, "")`` gdy legalny, albo ``(False, powód)``. Egzekwuje R1–R6
    (RULES.md 32.1). Nie mutuje stanu. ``boost=True`` pozwala hookom dać premię jednorazową
    dla JEDNEGO statku (Gravity Drive); wołający sam pilnuje, że dotyczy to jednego statku.
    ``route`` = trasa wybrana przez gracza (lista systemów od źródła do aktywnego):
    gdy podana, jest walidowana i jej długość zastępuje najkrótszą trasę z BFS.
    """
    active = state.active_system
    if active is None:
        return False, "No active system - movement is only allowed during a tactical action (R1)."
    if not floating_structures.moves_as_ship(state, player_id, base_type):
        return False, f"Unit {base_type} is not a ship - it cannot move."
    from src.core import promissory_play  # lokalnie: unikamy cyklu importów

    if promissory_play.ceasefire_blocks(state, player_id):
        return False, "Ceasefire: you cannot move units into the active system."
    from src.core import production  # lokalnie: unikamy cyklu importów

    waiting = production.foreign_grant_reason(state, player_id)
    if waiting is not None:
        return False, waiting

    move_value = _effective_move_value(
        state, grid, registry, from_pos, base_type, player_id,
        boost=boost, tempesta=tempesta, imperator=imperator, companions=companions,
        single=single,
    )
    if move_value is None:
        return False, (
            f"Unit {base_type} has no move value "
            "(porusza się transportem — capacity, TODO)."
        )
    ignore_anomalies = _ignores_anomalies(state, player_id)

    # R3: start nie z własnym CC (wyjątek: aktywny system).
    source = state.systems.get(from_pos)
    if (
        from_pos != active
        and source is not None
        and player_id in source.command_tokens
        and not _ignores_own_command_token(state, player_id)
    ):
        return False, "A ship cannot move out of a system containing its own command token (R3)."

    dist: int | None
    if route is not None:
        if route[0] != from_pos:
            return False, "The route must start at the system the ships move from."
        error = route_error(state, grid, route, player_id, base_type)
        if error is not None:
            return False, error
        # Każda szczelina, z której statek wychodzi lub przez którą przelatuje, daje +1 do ruchu.
        move_value += rift_bonus(state, grid, route, player_id)
        dist = len(route) - 1
    else:
        dist = _shortest_legal_distance(
            grid,
            state,
            from_pos,
            active,
            player_id,
            can_enter_asteroids=_can_enter_asteroids(state, player_id),
            ignore_anomalies=ignore_anomalies,
            base_type=base_type,
        )
    if dist is None:
        return False, "No legal route to the active system (R4/R6)."
    if (
        route is None
        and dist > move_value
        and _rift_route_within(state, grid, from_pos, player_id, move_value, base_type)
        is not None
    ):
        return True, ""  # dłuższa trasa przez gravity rift (+1 za każdą) mieści się w zasięgu
    if dist > move_value:
        return False, (
            f"Range too short: route {dist} > moveValue {move_value} (R2)."
        )
    return True, ""


def move_ships(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    base_type: str,
    count: int,
    player_id: str,
    ion_storm_token: bool | None = None,
) -> GameState:
    """Wykonuje legalny ruch ``count`` statków ``base_type`` ze źródła do aktywnego systemu.

    Twardo waliduje (``can_move``); przenosi jednostki w ``space_units`` (zdejmuje ze
    źródła, dodaje do aktywnego). TODO (rozbudowa): transport sił naziemnych/myśliwców
    przez capacity; ruch wielu typów naraz; wybór trasy pod gravity rift.

    Raises:
        ValueError: Gdy ruch nielegalny (R1–R6) albo brak tylu statków w źródle.
    """
    timing.require_no_limit_window(state)  # nadwyżka puli floty najpierw (RULES.md 42.1)
    if count <= 0:
        raise ValueError("The number of ships to move must be positive.")
    ok, reason = can_move(state, grid, registry, from_pos, base_type, player_id)
    if not ok:
        raise ValueError(reason)

    source = state.systems.get(from_pos)
    available = 0
    if source is not None:
        available = source.space_units.get(player_id, {}).get(base_type, 0)
    if available < count:
        raise ValueError(
            f"Not enough {base_type} ships in {from_pos}: have {available}, requested {count}."
        )

    active = state.active_system
    assert active is not None  # zagwarantowane przez can_move
    new_state = state.clone()

    src = new_state.systems[from_pos]

    # Cel: aktywny system (utwórz, gdy trzeba). Ta ścieżka nie przenosi uszkodzeń (jak dotąd).
    dest = new_state.systems.get(active)
    if dest is None:
        system_id = grid.system_id_at(active) if active in grid.positions else ""
        dest = SystemState(position=active, system_id=system_id)
        new_state.systems[active] = dest
    moved_ctx = {"player": player_id, "position": active, "from": from_pos, "base_type": base_type}
    triggers.fire(new_state, GameEvent.SHIPS_MOVED, Moment.WHEN, subject=player_id, ctx=moved_ctx)
    unit_ops.take_units(new_state, src, "space", player_id, base_type, count, UnitCause.MOVED)
    unit_ops.place_units(new_state, dest, "space", player_id, base_type, count, UnitCause.MOVED)
    new_state.tactical_moved = True
    new_state.tactical_none_arrived = False
    new_state.last_move = build_move_record(
        grid, [from_pos, active], player_id, {base_type: count}, []
    )
    ion_storm.note_move(new_state, grid, registry, from_pos, active, ion_storm_token)
    _flip_after_separate_move(new_state, player_id, {base_type: count})
    fire_ships_moved(new_state, player_id, active, from_pos, {base_type: count})
    return new_state


def _capacity_provided(
    registry: StaticDataRegistry,
    faction_id: str | None,
    technologies: list[str],
    base_type: str,
) -> int:
    """Pojemność transportowa jednego statku ``base_type`` (wariant gracza) — RULES.md 32.3 T1.

    Czyta ``capacityValue`` z WARIANTU jednostki (uwzględnia ulepszenia). Zwraca 0,
    gdy jednostka nie ma pojemności (np. destroyer, cruiser) lub jest nieznana.
    """
    unit = resolve_unit_variant(registry, faction_id, technologies, base_type)
    if unit is None or unit.capacity_value is None:
        return 0
    return max(unit.capacity_value, 0)


def _capacity_used(
    registry: StaticDataRegistry,
    faction_id: str | None,
    technologies: list[str],
    base_type: str,
) -> int:
    """Ile capacity zajmuje jedna jednostka ładunku ``base_type`` (RULES.md 32.3 T1).

    Czyta ``capacityUsed`` z wariantu (fighter/infantry/mech = zwykle 1). Gdy pole
    puste, a jednostka jest ładunkiem (``_CARGO_BASE_TYPES``), przyjmujemy 1
    (bezpieczny domyślny — ładunek zawsze coś zajmuje). Dla nie-ładunku: 0.
    """
    unit = resolve_unit_variant(registry, faction_id, technologies, base_type)
    if unit is not None and unit.capacity_used is not None:
        return max(unit.capacity_used, 0)
    return 1 if base_type in _CARGO_BASE_TYPES else 0


def legal_move_sources(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    *,
    gravity_drive: bool = False,
    tempesta: bool = False,
    imperator: bool = False,
) -> dict[str, list[str]]:
    """Mapa {pozycja źródłowa -> lista base_type statków, które mogą ruszyć stamtąd}.

    ``gravity_drive=True`` = gracz zamierza użyć Gravity Drive (premia dla jednego statku), o ile
    jeszcze jej w tej akcji nie zużył.

    Dla każdego systemu (poza aktywnym), w którym gracz ma statki, sprawdza które
    typy statków mają legalną trasę do aktywnego systemu (``can_move``, R1–R6). System
    trafia do wyniku tylko, gdy ma ≥1 ruszalny statek. Służy podglądowi zasięgu/ścieżki
    w UI (które heksy są legalnym źródłem ruchu). Nie mutuje stanu.

    Myśliwce bez własnego ruchu (ładunek) NIE trafiają tu jako „ruszalny statek" —
    jadą transportem, więc o legalności ich systemu źródłowego decyduje nosiciel.
    """
    active = state.active_system
    if active is None:
        return {}
    result: dict[str, list[str]] = {}
    for position, system in state.systems.items():
        if position == active:
            continue
        by_type = system.space_units.get(player_id, {})
        movable: list[str] = []
        for base_type, count in sorted(by_type.items()):
            if count <= 0 or not floating_structures.moves_as_ship(state, player_id, base_type):
                continue
            ok, _ = can_move(
                state, grid, registry, position, base_type, player_id,
                boost=gravity_drive and not state.gravity_drive_used,
                tempesta=tempesta and not state.tempesta_used,
                imperator=imperator and not state.imperator_used,
                companions=[bt for bt, n in by_type.items() if n > 0],
            )
            if ok:
                movable.append(base_type)
        if movable:
            result[position] = movable
    return result


def _available_in_zone(
    source: SystemState | None, player_id: str, base_type: str, zone: str
) -> int:
    """Liczba jednostek gracza ``base_type`` w danej strefie źródła (space/planeta)."""
    if source is None:
        return 0
    if zone == "space":
        return source.space_units.get(player_id, {}).get(base_type, 0)
    return source.planet_units.get(zone, {}).get(player_id, {}).get(base_type, 0)


def single_ship_type(ships: dict[str, int]) -> str:
    """Typ statku, gdy rusza jeden typ (np. sam Corsair), inaczej ``""``.

    Wyjątki przejezdności dla jednego typu (``movement.pass_foreign_ships`` z ``base_type``,
    RULES.md 62.8) liczą się dla trasy grupy tylko wtedy, gdy cała grupa to ten typ; legalność
    każdego typu i tak sprawdza ``can_move``.
    """
    types = [bt for bt, n in ships.items() if n > 0]
    return types[0] if len(types) == 1 else ""


def _auto_route(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    ships: dict[str, int],
    player_id: str,
) -> list[str] | None:
    """Trasa dla ruchu bez trasy podanej przez gracza.

    Najkrótsza legalna, o ile starczy na nią zasięgu wszystkim statkom; w przeciwnym razie
    pierwsza dłuższa trasa, na którą starczy dzięki +1 za gravity rift. Gdy żadna nie pasuje,
    zwraca najkrótszą (reszta walidacji zgłosi właściwy powód odmowy).
    """
    only = single_ship_type(ships)
    shortest = route_through(state, grid, from_pos, [], player_id, only)
    if shortest is None or not ships:
        return shortest
    candidates = [
        shortest,
        *legal_routes(
            state, grid, from_pos, player_id,
            max_len=min(len(shortest) - 1 + _RIFT_SEARCH_EXTRA, _RIFT_SEARCH_CAP), cap=120,
            base_type=only,
        ),
    ]
    for candidate in candidates:
        if all(
            can_move(
                state, grid, registry, from_pos, bt, player_id,
                route=candidate, companions=list(ships),
            )[0]
            for bt in ships
        ):
            return candidate
    return shortest


def entry_blocked(grid: HexGrid, state: GameState, position: str, player_id: str) -> str | None:
    """Czy jednostki gracza mogą wejść do systemu ``position`` spoza ruchu statków (R6).

    Dla przemieszczeń innych niż ruch (G'hom Sek'kus: siły z sąsiednich systemów). Supernowa
    blokuje zawsze, pole asteroid bez Antimass Deflectors (F_norr). Zwraca powód albo ``None``.
    """
    if _target_passable(
        grid, position, can_enter_asteroids=_can_enter_asteroids(state, player_id),
        into_supernova=can_enter_supernova(state, player_id),
    ):
        return None
    if _SUPERNOVA in grid.anomalies_at(position):
        return "Units cannot enter a supernova."
    return "Units cannot enter an asteroid field without Antimass Deflectors."


def is_gravity_rift(grid: HexGrid, position: str) -> bool:
    return _GRAVITY_RIFT in grid.anomalies_at(position)


def roll_rift_exit(
    state: GameState, player_id: str, units: dict[str, int], position: str | None = None
) -> dict[str, int]:
    """Rzut d10 za każdą jednostkę wychodzącą z gravity rift POZA ruchem statków (MUTUJE klon).

    R_gravity_rift; F_norr: siły naziemne przesuwane G'hom Sek'kus z systemu ze szczeliną rzucają
    na usunięcie. 1–3 = jednostka usunięta. Zwraca ``{typ: ile usuniętych}``; usunięcie z planszy
    robi wołający (zna strefę). Jeden wpis rzutu „na stół”. position = szczelina, z której
    jednostki wychodzą (własny Dimensional Tear: bez rzutu - RULES.md 62.17).
    """
    if _ignores_anomalies(state, player_id):
        return {}
    if position is not None and not rolls_at(state, player_id, position):
        return {}
    rng = next_rng(state)
    rolls: list[int] = []
    lost: dict[str, int] = {}
    for base_type in sorted(units):
        results = [rng.randint(1, DIE_SIDES) for _ in range(units[base_type])]
        rolls.extend(results)
        gone = sum(1 for r in results if r <= _RIFT_REMOVED_ON)
        if gone:
            lost[base_type] = gone
    if rolls:
        record_table_roll(
            state, player_id, "gravity_rift", "Gravity Rift", rolls,
            hit_values=list(range(1, _RIFT_REMOVED_ON + 1)),
            summary=(
                f"{sum(lost.values())} unit(s) removed by the gravity rift."
                if lost
                else "All units got through the gravity rift."
            ),
        )
    return lost


def _resolve_rift_losses(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    route: list[str],
    ships: dict[str, int],
    cargo: list[CargoPickup],
    from_pos: str,
    player_id: str,
) -> tuple[dict[str, int], list[CargoPickup], list[MoveLoss]]:
    """Rzuty gravity rift dla ruchu wzdłuż ``route`` (R_gravity_rift) — MUTUJE ``state`` (klon).

    Każdy statek wychodzący ze szczeliny albo przez nią przelatujący rzuca d10; 1–3 usuwa go
    z planszy (do rezerwy). Wszystkie rzuty są zapisane jednym wpisem „na stół". Ładunek jest
    zabierany po drodze w kolejności systemów: statki usunięte przez szczelinę zabierają ze sobą
    ładunek, który ponad ich pojemność już załadowano (najpóźniej załadowany znika pierwszy),
    a ładunek z dalszych systemów, na który zabrakło pojemności, zostaje na miejscu.
    Zwraca (statki, ładunek), które faktycznie docierają do celu, oraz straty z systemem
    szczeliny, w którym przepadły (``MoveLoss``; tylko prezentacja - animacja pochłonięcia).

    ⚠️ ZAŁOŻENIE: ładunek nie jest przypisany do konkretnych statków (pojemność jest wspólna), więc
    nadwyżkę ponad pojemność ocalałych usuwamy od ostatnio załadowanego — źródło reguł tego nie
    rozstrzyga, wymaga potwierdzenia.
    """
    rifts = rift_roll_nodes(state, grid, route, player_id)
    if not rifts:
        return ships, cargo, []
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    survivors = dict(ships)
    lost_ships: dict[str, int] = {}
    loaded: list[CargoPickup] = []
    removed_cargo: list[CargoPickup] = []
    losses: list[MoveLoss] = []
    rolls: list[int] = []
    rng = next_rng(state)

    def provided() -> int:
        return sum(
            _capacity_provided(registry, faction_id, technologies, bt) * n
            for bt, n in survivors.items()
        )

    def per_unit(base_type: str) -> int:
        return _capacity_used(registry, faction_id, technologies, base_type)

    def used() -> int:
        return sum(per_unit(c.base_type) * c.count for c in loaded)

    for node in route:
        for item in cargo:
            if (item.from_position or from_pos) != node:
                continue
            unit = per_unit(item.base_type)
            room = max(provided() - used(), 0)
            take = item.count if unit <= 0 else min(item.count, room // unit)
            if take > 0:
                loaded.append(replace(item, count=take, from_position=node))
        if node not in rifts:
            continue
        for base_type in sorted(survivors):
            results = [rng.randint(1, DIE_SIDES) for _ in range(survivors[base_type])]
            rolls.extend(results)
            gone = sum(1 for r in results if r <= _RIFT_REMOVED_ON)
            if gone:
                survivors[base_type] -= gone
                lost_ships[base_type] = lost_ships.get(base_type, 0) + gone
                losses.append(MoveLoss(base_type=base_type, count=gone, at=node))
        excess = used() - provided()
        while excess > 0 and loaded:
            last = loaded[-1]
            unit = max(per_unit(last.base_type), 1)
            drop = min(last.count, -(-excess // unit))
            removed_cargo.append(replace(last, count=drop))
            losses.append(MoveLoss(base_type=last.base_type, count=drop, at=node))
            excess -= drop * unit
            if drop == last.count:
                loaded.pop()
            else:
                loaded[-1] = replace(last, count=last.count - drop)

    record_table_roll(
        state, player_id, "gravity_rift", "Gravity Rift", rolls,
        hit_values=list(range(1, _RIFT_REMOVED_ON + 1)),
        summary=(
            f"{sum(lost_ships.values())} ship(s) removed by the gravity rift."
            if lost_ships
            else "All ships got through the gravity rift."
        ),
    )
    origin = state.systems[from_pos]
    for base_type, n in lost_ships.items():
        unit_ops.remove_units(state, origin, "space", player_id, base_type, n, UnitCause.REMOVED)
    for item in removed_cargo:
        unit_ops.remove_units(
            state,
            state.systems[item.from_position or from_pos],
            item.from_zone,
            player_id,
            item.base_type,
            item.count,
            UnitCause.REMOVED,
        )
    return {bt: n for bt, n in survivors.items() if n > 0}, loaded, losses


def move_fleet(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    ships: dict[str, int],
    cargo: list[CargoPickup] | dict[str, int],
    player_id: str,
    *,
    gravity_drive: bool = False,
    tempesta: bool = False,
    imperator: bool = False,
    route: list[str] | None = None,
    ion_storm_token: bool | None = None,
) -> GameState:
    """Ruch FLOTY (statki + ładunek) ze źródła do aktywnego systemu — RULES.md 32.3.

    ``ion_storm_token`` = wybór gracza, którego wormholu używa przy Ion Storm w systemie
    z własnym wormholem tego typu (``ion_storm.choice_needed``; C_exploration_cards).

    ``route`` = trasa wybrana przez gracza (systemy od źródła do aktywnego). Bez niej statki
    jadą najkrótszą legalną trasą, a ładunek wolno zabrać tylko ze źródła. Z trasą ładunek
    można zabrać także z systemów, przez które statki przelatują (``CargoPickup.from_position``).

    ``ships`` = statki RUSZAJĄCE (``{base_type: count}``), każdy walidowany jak w
    ``can_move`` (R1–R6). ``cargo`` = myśliwce/siły naziemne przewożone razem — lista
    ``CargoPickup`` z STREFĄ źródłową (przestrzeń lub PLANETA systemu źródłowego, T3).
    Dla zgodności wstecznej przyjmuje też ``{base_type: count}`` (strefa = przestrzeń).
    Ładunek ląduje w PRZESTRZENI celu (T2) — siły naziemne zejdą na planetę dopiero w
    Commit Ground Forces.

    Zasady egzekwowane (twarde, ValueError):
    - każdy statek ruszający musi być legalny (``can_move``) i dostępny w źródle;
    - ładunek tylko z ``_CARGO_BASE_TYPES`` i dostępny w swojej strefie źródłowej;
    - myśliwce pobiera się tylko z przestrzeni (nie z planet);
    - pickup z systemu z WŁASNYM CC zabroniony, chyba że to aktywny system (T4);
    - suma ``capacityUsed`` ładunku ≤ suma ``capacityValue`` statków ruszających (T1/T5).

    Raises:
        ValueError: Przy złamaniu którejkolwiek reguły albo braku jednostek w źródle.
    """
    ships = {bt: c for bt, c in ships.items() if c > 0}
    # Normalizacja ładunku do listy ``CargoPickup`` (zgodność wsteczna z dict).
    cargo_items: list[CargoPickup]
    if isinstance(cargo, dict):
        cargo_items = [
            CargoPickup(base_type=bt, count=c) for bt, c in cargo.items() if c > 0
        ]
    else:
        cargo_items = [c for c in cargo if c.count > 0]
    if not ships and not cargo_items:
        raise ValueError("Nothing to move (no ships and no cargo).")

    active = state.active_system
    if active is None:
        raise ValueError(
            "No active system - movement is only allowed during a tactical action (R1)."
        )
    if not ships and from_pos == active:
        return _load_in_active_system(state, registry, player_id, cargo_items)

    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    source = state.systems.get(from_pos)
    if route is not None:
        if not route or route[0] != from_pos:
            raise ValueError("The route must start at the system the ships move from.")
        route_problem = route_error(state, grid, route, player_id, single_ship_type(ships))
        if route_problem is not None:
            raise ValueError(route_problem)

    # Trasa, którą faktycznie polecą statki (do szczelin grawitacyjnych): wybrana przez gracza
    # albo — gdy jej nie podał — najkrótsza, na którą wszystkie statki starczy zasięgu.
    plan_route = route or (_auto_route(state, grid, registry, from_pos, ships, player_id))

    # Statki: walidacja legalności + dostępności (R1–R6, policzone per typ). Premia jednorazowa
    # dla JEDNEGO statku w akcji (Gravity Drive, RULES.md 55.6) działa WYŁĄCZNIE na życzenie
    # gracza (``gravity_drive=True``), tylko tam, gdzie bez niej ruch jest nielegalny, i nie
    # dla grupy większej niż 1.
    # Premie „+1 dla jednego statku” to osobne zdolności (Gravity Drive, Ionian Fuel Refinery,
    # Imperator) — każda z własną flagą zużycia; mogą trafić na różne statki albo na ten sam.
    wanted = {"boost": gravity_drive, "tempesta": tempesta, "imperator": imperator}
    spent = {
        "boost": state.gravity_drive_used,
        "tempesta": state.tempesta_used,
        "imperator": state.imperator_used,
    }
    this_move = dict.fromkeys(wanted, False)
    # Ship types that spent Gravity Drive in this move (shown by the flight replay).
    boosted_types: list[str] = []
    # Gravleash Maneuvers: premia trafia na 1 statek, a reszta grupy (niemyśliwska) wyrównuje do
    # jego wartości (F_letnev) — premia zużyta w TYM ruchu działa więc na kolejne typy statków.
    group_matches = rules_hooks.permits(
        rules_hooks.POINT_MOVEMENT_MATCH_HIGHEST, state, player_id
    )
    for base_type, count in ships.items():
        ok, reason = can_move(
            state, grid, registry, from_pos, base_type, player_id, route=plan_route,
            companions=list(ships),
        )
        if not ok:
            # Najpierw pojedyncze premie, potem pary, na końcu wszystkie; zużywa się tylko to,
            # co było potrzebne.
            shared = group_matches and base_type != _FIGHTER
            usable = [
                name for name in wanted
                if wanted[name] and (not spent[name] or (shared and this_move[name]))
            ]
            combos = [
                combo
                for size in range(1, len(usable) + 1)
                for combo in _combinations(usable, size)
            ]
            chosen = next(
                (
                    combo
                    for combo in combos
                    if can_move(
                        state, grid, registry, from_pos, base_type, player_id,
                        boost="boost" in combo, tempesta="tempesta" in combo,
                        imperator="imperator" in combo,
                        route=plan_route, companions=list(ships),
                    )[0]
                ),
                None,
            )
            if chosen is None:
                raise ValueError(reason)
            # Gravleash Maneuvers: premię dostaje 1 statek, reszta (niemyśliwska) wyrównuje do
            # jego wartości (F_letnev) — limit „1 statek” nie blokuje grupy.
            if count != 1 and not shared:
                raise ValueError(
                    f"{reason} A +1 move bonus extends the move of only 1 ship per action."
                )
            for name in chosen:
                this_move[name] = True
                spent[name] = True
            if "boost" in chosen:
                boosted_types.append(base_type)
        if count > 1 and single_ship_target(state, player_id, from_pos, base_type) > 0:
            # Captain Mendosa podnosi ruch tylko 1 statku: stos > 1 sztuki musi zdążyć bez tego.
            flags = {name: this_move[name] for name in this_move}
            ok_plain, _ = can_move(
                state, grid, registry, from_pos, base_type, player_id, route=plan_route,
                companions=list(ships), single=False, boost=flags["boost"],
                tempesta=flags["tempesta"], imperator=flags["imperator"],
            )
            if not ok_plain:
                raise ValueError(
                    "That move value increase applies to only 1 ship - move that ship alone."
                )
        available = _available_in_zone(source, player_id, base_type, "space")
        if available < count:
            raise ValueError(
                f"Not enough {base_type} ships in {from_pos}: "
                f"have {available}, requested {count}."
            )

    if cargo_items:
        # Ładunek wymaga statku-nosiciela ruszającego w tym samym ruchu.
        if not ships:
            raise ValueError(
                "Cargo (fighters / ground forces) needs a transporting ship moving with it."
            )
        # Zsumuj żądania po (system, typ, strefa) — i waliduj dostępność w tej strefie.
        needed_by_key: dict[tuple[str, str, str], int] = {}
        for item in cargo_items:
            if item.base_type not in _CARGO_BASE_TYPES:
                raise ValueError(
                    f"Unit {item.base_type} cannot be transported "
                    "(only fighters and ground forces)."
                )
            # Myśliwiec stoi w przestrzeni — nie zbiera się go z planety.
            if item.base_type == "fighter" and item.from_zone != "space":
                raise ValueError("Fighters can only be picked up from space.")
            pickup_pos = item.from_position or from_pos
            # Pickup po drodze: system musi leżeć na wybranej trasie (R_transport), poza celem.
            # Aktywny system (koniec trasy) też jest punktem poboru, ale tylko z planet.
            if pickup_pos != from_pos and (route is None or pickup_pos not in route):
                raise ValueError(
                    f"System {pickup_pos} is not on the route - ships cannot pick up units there."
                )
            if pickup_pos == active and item.from_zone == "space":
                raise ValueError(
                    "Units in space of the active system are already there - "
                    "ships can only pick up ground forces from its planets."
                )
            key = (pickup_pos, item.base_type, item.from_zone)
            needed_by_key[key] = needed_by_key.get(key, 0) + item.count
        # T4: pickup z systemu z własnym CC zabroniony (wyjątek: aktywny system).
        for pickup_pos in {k[0] for k in needed_by_key}:
            pickup_system = state.systems.get(pickup_pos)
            if (
                pickup_pos != active
                and pickup_system is not None
                and player_id in pickup_system.command_tokens
                and not _ignores_own_command_token(state, player_id)
            ):
                raise ValueError(
                    "Cannot pick up units from a system containing your own command token (T4)."
                )
        for (pickup_pos, base_type, zone), count in needed_by_key.items():
            available = _available_in_zone(
                state.systems.get(pickup_pos), player_id, base_type, zone
            )
            # Te same jednostki nie mogą lecieć jednocześnie same i jako ładunek (Fighter II ze
            # startu wybrany jako statek I jako ładunek tworzyłby myśliwce z niczego).
            if pickup_pos == from_pos and zone == "space":
                available -= ships.get(base_type, 0)
            if available < count:
                where = "space" if zone == "space" else f"planet {zone}"
                raise ValueError(
                    f"Not enough {base_type} to transport from {where} in {pickup_pos}: "
                    f"have {available}, requested {count}."
                )

        # T1/T5: ładunek ≤ wolna pojemność statków ruszających.
        provided = sum(
            _capacity_provided(registry, faction_id, technologies, bt) * c
            for bt, c in ships.items()
        )
        if cargo_items and provided <= 0:
            # Ładunek o zerowym capacityUsed (Aerie Sentinel) nadal wymaga statku z pojemnością
            # (F_argent: „cannot be transported by a ship without a capacity value”).
            raise ValueError("Only ships with a capacity value can transport units.")
        needed = sum(
            _capacity_used(registry, faction_id, technologies, item.base_type)
            * item.count
            for item in cargo_items
        )
        if needed > provided:
            raise ValueError(
                f"Capacity exceeded: cargo needs {needed}, moving ships provide {provided}."
            )

    new_state = state.clone()
    new_state.gravity_drive_used = spent["boost"]
    new_state.tempesta_used = spent["tempesta"]
    new_state.imperator_used = spent["imperator"]
    src = new_state.systems.get(from_pos)
    assert src is not None  # gwarantowane: dostępność sprawdzona wyżej

    # Cel (utwórz system, gdy trzeba). WSZYSTKO ląduje w PRZESTRZENI celu (T2) — ładunek
    # na statku, do czasu lądowania w kroku INWAZJA.
    dest = new_state.systems.get(active)
    if dest is None:
        system_id = grid.system_id_at(active) if active in grid.positions else ""
        dest = SystemState(position=active, system_id=system_id)
        new_state.systems[active] = dest

    # Gravity rift na trasie: rzuty usuwają część statków (i przewożony nimi ładunek).
    losses: list[MoveLoss] = []
    if plan_route is not None:
        ships, cargo_items, losses = _resolve_rift_losses(
            new_state, grid, registry, plan_route, ships, cargo_items, from_pos, player_id
        )

    # Statki (zawsze z przestrzeni) — uszkodzenia jadą razem z nimi (RULES.md 39.3).
    for base_type, count in ships.items():
        unit_ops.transfer_units(
            new_state, src, "space", dest, "space", player_id, base_type, count
        )
    # Ładunek z jego strefy źródłowej (przestrzeń lub planeta) trafia do przestrzeni celu.
    for item in cargo_items:
        pickup_src = new_state.systems[item.from_position or from_pos]
        unit_ops.transfer_units(
            new_state,
            pickup_src,
            item.from_zone,
            dest,
            "space",
            player_id,
            item.base_type,
            item.count,
        )
    # Pierwszy ruch w akcji zamyka okno „po aktywacji systemu" kart reakcji i otwiera okno
    # „po ruchu do systemu" (Rescue) - patrz ``core/hooks/reactions_tactical.py``. A move whose
    # every ship a gravity rift removed moves nothing INTO the system: it keeps that window shut
    # unless ships arrived earlier (C_action_cards/experimental-battlestation/3.3).
    new_state.tactical_none_arrived = not ships and not ships_arrived(state)
    new_state.tactical_moved = True
    new_state.last_move = build_move_record(
        grid, plan_route or [from_pos, active], player_id, dict(ships),
        [(c.base_type, c.count, c.from_zone, c.from_position or from_pos) for c in cargo_items],
        losses,
        [bt for bt in boosted_types if ships.get(bt, 0) > 0],
    )
    ion_storm.note_move(new_state, grid, registry, from_pos, active, ion_storm_token)
    _flip_after_separate_move(new_state, player_id, ships)
    if ships:
        fire_ships_moved(
            new_state, player_id, active, from_pos, dict(ships), route=plan_route
        )
    return new_state


def _load_in_active_system(
    state: GameState, registry: StaticDataRegistry, player_id: str, cargo: list[CargoPickup]
) -> GameState:
    """Ground forces on planets of the active system board ships ALREADY in its space area.

    C_promissory_notes/ceasefire/3: under Ceasefire the active player's ships cannot move, yet
    ships with capacity already in the active system may transport ground forces from its planets
    into its space area (they may then commit to invade). ⚠️ ASSUMPTION: only offered under
    Ceasefire - without it ships in the active system do not move, so there is no transport.
    """
    from src.core import capacity, promissory_play  # lokalnie: unikamy cyklu importów

    active = state.active_system
    assert active is not None
    if not promissory_play.ceasefire_blocks(state, player_id):
        raise ValueError(
            "Cargo (fighters / ground forces) needs a transporting ship moving with it."
        )
    system = state.systems.get(active)
    wanted: dict[tuple[str, str], int] = {}
    for item in cargo:
        if item.base_type not in _CARGO_BASE_TYPES or item.base_type == "fighter":
            raise ValueError("Only ground forces can be loaded from planets of the active system.")
        if item.from_zone == "space" or item.from_position not in (None, active):
            raise ValueError("Choose ground forces on planets of the active system.")
        key = (item.from_zone, item.base_type)
        wanted[key] = wanted.get(key, 0) + item.count
    for (zone, base_type), count in wanted.items():
        have = _available_in_zone(system, player_id, base_type, zone)
        if have < count:
            raise ValueError(
                f"Not enough {base_type} to transport from planet {zone}: have {have}, "
                f"requested {count}."
            )
    report = capacity.capacity_report(state, registry, active, player_id)
    if report.general <= 0:
        raise ValueError("Only ships with a capacity value can transport units.")
    player = state.players[player_id]
    loaded = dict(report.cargo)
    for (_zone, base_type), count in wanted.items():
        loaded[base_type] = loaded.get(base_type, 0) + count
        report.cost.setdefault(
            base_type, _capacity_used(registry, player.faction, player.technologies, base_type)
        )
    if report.excess_for(loaded) > 0:
        raise ValueError("Capacity exceeded: the ships in the active system cannot carry that.")
    new_state = state.clone()
    dest = new_state.systems[active]
    for (zone, base_type), count in wanted.items():
        unit_ops.transfer_units(
            new_state, dest, zone, dest, "space", player_id, base_type, count
        )
    return new_state


def _flip_after_separate_move(
    state: GameState, player_id: str, ships: Mapping[str, int]
) -> None:
    """A ship that moves before / after the other ships (Hil Colish, PERMIT
    ``movement.moves_separately``): an Ion Storm it used flips right after its move - "the token
    flips after the flagship moves" (C_exploration_cards ion-storm 2.1, RULES.md 62.19)."""
    if any(
        rules_hooks.permits(
            rules_hooks.POINT_MOVEMENT_MOVES_SEPARATELY, state, player_id, {"base_type": bt}
        )
        for bt, n in ships.items() if n > 0
    ):
        ion_storm.flip_used(state)


def ships_arrived(state: GameState) -> bool:
    """Whether the active player has moved ships INTO the active system in this tactical action.

    Ships lost to a gravity rift on the way do not count (C_action_cards/experimental-
    battlestation/3.3); one surviving move is enough.
    """
    return state.tactical_moved and not state.tactical_none_arrived


def fire_ships_moved(
    state: GameState,
    player_id: str,
    position: str,
    from_pos: str,
    ships: Mapping[str, int],
    *,
    route: list[str] | None = None,
    kind: str = "tactical",
) -> None:
    """JEDYNE miejsce emisji ``SHIPS_MOVED/AFTER`` (MUTUJE ``state``): statki gracza weszły do
    systemu ``position``.

    ``ctx``: ``from`` (system startowy), ``ships`` (typ -> liczba), ``route`` (trasa od startu do
    celu, gdy znana), ``kind`` = ``tactical`` (ruch akcji taktycznej) | ``retreat`` (odwrót) |
    ``direct`` (ruch komponentem: Helix Protocol, Dark Space Navigation). F_muaat Nova Seed 1:
    „any method of movement”.
    """
    moved = {bt: n for bt, n in ships.items() if n > 0}
    if not moved:
        return
    ctx: dict[str, Any] = {
        "player": player_id, "position": position, "from": from_pos,
        "base_type": next(iter(moved)), "ships": moved, "kind": kind,
        "route": list(route) if route else [from_pos, position],
    }
    triggers.fire(state, GameEvent.SHIPS_MOVED, Moment.AFTER, subject=player_id, ctx=ctx)
