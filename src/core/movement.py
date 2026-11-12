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

from collections import deque
from dataclasses import dataclass

from src.core import ion_storm, rules_hooks, triggers, unit_ops
from src.core.combat import resolve_unit_variant
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

# Jednostki, które mogą być ŁADUNKIEM transportu (R_transport): myśliwce i siły
# naziemne. To jedyne jednostki zajmujące capacity (``capacityUsed``). Źródło:
# R_capacity/R_transport — „fighters and ground forces". Trzymane jawnie, bo to
# reguła klasy jednostek, nie dane liczbowe (te czytamy z UnitDef).
_CARGO_BASE_TYPES = frozenset({"fighter", "infantry", "mech"})


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

# Anomalie znaczące dla przejezdności węzłów POŚREDNICH trasy (RULES.md 32.1 R6).
_SUPERNOVA = "SUPERNOVA"
_ASTEROID = "ASTEROID_FIELD"
_NEBULA = "NEBULA"


def _ships_of_other_players(system: SystemState | None, player_id: str) -> bool:
    """Czy w przestrzeni systemu stoją statki INNEGO gracza (blokada R4)."""
    if system is None:
        return False
    for owner, by_type in system.space_units.items():
        if owner == player_id:
            continue
        if any(count > 0 for count in by_type.values()):
            return True
    return False


def _node_passable_intermediate(
    grid: HexGrid,
    state: GameState,
    position: str,
    player_id: str,
    *,
    can_enter_asteroids: bool,
    from_pos: str | None = None,
    ignore_anomalies: bool = False,
) -> bool:
    """Czy węzeł POŚREDNI trasy jest przejezdny dla gracza (R4 + R6).

    Węzeł pośredni (nie start, nie cel): bez statków obcego gracza, bez supernowej,
    asteroid tylko z Antimass, nebula nieprzejezdna jako węzeł pośredni (wejście do
    nebuli tylko gdy jest systemem aktywnym = celem — RULES.md 1.2).
    ``ignore_anomalies`` (Nav Suite) pomija blokady anomalii; ``from_pos`` trafia do hooka
    „przelot przez obce statki" (In The Silence Of Space: dotyczy statków z wybranego systemu).
    """
    anomalies = set() if ignore_anomalies else grid.anomalies_at(position)
    if _SUPERNOVA in anomalies:
        return False
    if _ASTEROID in anomalies and not can_enter_asteroids:
        return False
    if _NEBULA in anomalies:
        return False
    if _ships_of_other_players(
        state.systems.get(position), player_id
    ) and not rules_hooks.permits(
        rules_hooks.POINT_MOVEMENT_PASS_FOREIGN_SHIPS,
        state,
        player_id,
        {"position": position, "from": from_pos},
    ):
        return False
    return True


def _target_passable(
    grid: HexGrid,
    position: str,
    *,
    can_enter_asteroids: bool,
    ignore_anomalies: bool = False,
) -> bool:
    """Czy CEL (aktywny system) jest przejezdny anomalicznie (R6).

    Cel może mieć obce statki (tam dojdzie do walki). Ale supernova zawsze blokuje,
    a asteroid wymaga Antimass. Nebula jako cel jest dozwolona (wejście tylko do
    aktywnego — a cel nim jest). ``ignore_anomalies`` (Nav Suite) pomija te blokady.
    """
    if ignore_anomalies:
        return True
    anomalies = grid.anomalies_at(position)
    if _SUPERNOVA in anomalies:
        return False
    if _ASTEROID in anomalies and not can_enter_asteroids:
        return False
    return True


def _neighbors_for_move(
    grid: HexGrid, state: GameState, position: str, player_id: str
) -> set[str]:
    """Sąsiedzi systemu na potrzeby RUCHU gracza: graf mapy + efekty tej akcji.

    Lost Star Chart (hook PERMIT): systemy z wormholem alpha i beta sąsiadują ze sobą w tej
    akcji. Graf mapy (czyste sąsiedztwo) zostaje nietknięty - to osobna warstwa (RULES.md 1/3).
    """
    result = set(grid.neighbors(position))
    if rules_hooks.permits(rules_hooks.POINT_MOVEMENT_ALPHA_BETA_ADJACENT, state, player_id):
        alpha = grid.wormhole_positions("ALPHA")
        beta = grid.wormhole_positions("BETA")
        if position in alpha:
            result |= beta
        if position in beta:
            result |= alpha
        result.discard(position)
    return result


def _ignores_own_command_token(state: GameState, player_id: str) -> bool:
    """Czy gracz może ruszać i transportować jednostki z systemów ze SWOIM żetonem (Dominus Orb)."""
    return rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_OWN_CC, state, player_id)


def _ignores_anomalies(state: GameState, player_id: str) -> bool:
    """Czy gracz ignoruje efekty anomalii w RUCHU (Nav Suite: tylko w kroku Movement)."""
    return rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_ANOMALIES, state, player_id)


def shortest_legal_path(
    grid: HexGrid,
    state: GameState,
    from_pos: str,
    to_pos: str,
    player_id: str,
    *,
    can_enter_asteroids: bool,
    ignore_anomalies: bool = False,
    goal_is_target: bool = True,
) -> list[str] | None:
    """Najkrótsza LEGALNA trasa jako lista systemów (od ``from_pos`` do ``to_pos``) albo None.

    BFS po krawędziach sąsiedztwa grafu. Węzły POŚREDNIE muszą być przejezdne
    (``_node_passable_intermediate``). Koniec trasy sprawdzany osobno: dla celu ruchu
    (aktywny system, ``goal_is_target=True``) przez ``_target_passable``, dla punktu
    pośredniego wybranego przez gracza (waypoint) jak dla węzła pośredniego.
    """
    if from_pos == to_pos:
        return [from_pos]
    if goal_is_target:
        if not _target_passable(
            grid,
            to_pos,
            can_enter_asteroids=can_enter_asteroids,
            ignore_anomalies=ignore_anomalies,
        ):
            return None
    elif not _node_passable_intermediate(
        grid,
        state,
        to_pos,
        player_id,
        can_enter_asteroids=can_enter_asteroids,
        from_pos=from_pos,
        ignore_anomalies=ignore_anomalies,
    ):
        return None
    # BFS z rodzicami. Do celu wchodzimy wprost, przez węzeł pośredni tylko gdy przejezdny.
    parent: dict[str, str] = {}
    visited = {from_pos}
    queue: deque[str] = deque([from_pos])
    while queue:
        pos = queue.popleft()
        for neighbor in sorted(_neighbors_for_move(grid, state, pos, player_id)):
            if neighbor in visited:
                continue
            if neighbor == to_pos:
                path = [to_pos, pos]
                while path[-1] != from_pos:
                    path.append(parent[path[-1]])
                return path[::-1]
            if _node_passable_intermediate(
                grid,
                state,
                neighbor,
                player_id,
                can_enter_asteroids=can_enter_asteroids,
                from_pos=from_pos,
                ignore_anomalies=ignore_anomalies,
            ):
                visited.add(neighbor)
                parent[neighbor] = pos
                queue.append(neighbor)
    return None


def _shortest_legal_distance(
    grid: HexGrid,
    state: GameState,
    from_pos: str,
    to_pos: str,
    player_id: str,
    *,
    can_enter_asteroids: bool,
    ignore_anomalies: bool = False,
) -> int | None:
    """Długość najkrótszej LEGALNEJ trasy (liczba wejść) albo None, gdy brak.

    Długość = liczba systemów, w które statek WCHODZI (R2: ≤ moveValue).
    """
    path = shortest_legal_path(
        grid,
        state,
        from_pos,
        to_pos,
        player_id,
        can_enter_asteroids=can_enter_asteroids,
        ignore_anomalies=ignore_anomalies,
    )
    return None if path is None else len(path) - 1


def route_through(
    state: GameState,
    grid: HexGrid,
    from_pos: str,
    via: list[str],
    player_id: str,
) -> list[str] | None:
    """Najkrótsza legalna trasa ``from_pos`` → ``via[0]`` → … → aktywny system.

    Punkty ``via`` to waypointy wybrane przez gracza (jak w nawigacji): trasa przechodzi
    przez nie w podanej kolejności, a odcinki między nimi są najkrótsze. Zwraca None, gdy
    którykolwiek odcinek jest nielegalny albo trasa wracałaby do tego samego systemu.
    """
    active = state.active_system
    if active is None:
        return None
    ast = _can_enter_asteroids(state, player_id)
    ignore = _ignores_anomalies(state, player_id)
    stops = [from_pos, *[v for v in dict.fromkeys(via) if v not in (from_pos, active)], active]
    path = [from_pos]
    for start, end in zip(stops, stops[1:], strict=False):
        segment = shortest_legal_path(
            grid,
            state,
            start,
            end,
            player_id,
            can_enter_asteroids=ast,
            ignore_anomalies=ignore,
            goal_is_target=end == active,
        )
        if segment is None:
            return None
        path.extend(segment[1:])
    if len(set(path)) != len(path):
        return None
    return path


def route_error(
    state: GameState, grid: HexGrid, route: list[str], player_id: str
) -> str | None:
    """Powód nielegalności gotowej trasy (lista systemów od źródła do aktywnego) albo None."""
    active = state.active_system
    if active is None:
        return "No active system - movement is only allowed during a tactical action (R1)."
    if len(route) < 2 or route[-1] != active:
        return "The route must end at the active system."
    if len(set(route)) != len(route):
        return "The route cannot visit the same system twice."
    ast = _can_enter_asteroids(state, player_id)
    ignore = _ignores_anomalies(state, player_id)
    for start, end in zip(route, route[1:], strict=False):
        if end not in _neighbors_for_move(grid, state, start, player_id):
            return f"Systems {start} and {end} are not adjacent (R4)."
    for node in route[1:-1]:
        if not _node_passable_intermediate(
            grid,
            state,
            node,
            player_id,
            can_enter_asteroids=ast,
            from_pos=route[0],
            ignore_anomalies=ignore,
        ):
            return f"The route passes through system {node}, which blocks movement (R4/R6)."
    if not _target_passable(
        grid, active, can_enter_asteroids=ast, ignore_anomalies=ignore
    ):
        return "The active system cannot be entered (R6)."
    return None


def legal_routes(
    state: GameState,
    grid: HexGrid,
    from_pos: str,
    player_id: str,
    *,
    max_len: int,
    cap: int = 300,
) -> list[list[str]]:
    """Wszystkie proste legalne trasy ``from_pos`` → aktywny system o długości ≤ ``max_len``.

    Posortowane rosnąco po długości, potem leksykograficznie. ``cap`` ogranicza liczbę
    zebranych tras (podgląd dla UI, nie wyczerpujące przeszukiwanie).
    """
    active = state.active_system
    if active is None or from_pos == active or max_len < 1:
        return []
    ast = _can_enter_asteroids(state, player_id)
    ignore = _ignores_anomalies(state, player_id)
    target_ok = _target_passable(
        grid, active, can_enter_asteroids=ast, ignore_anomalies=ignore
    )
    if not target_ok:
        return []
    found: list[list[str]] = []

    def walk(path: list[str]) -> None:
        if len(found) >= cap:
            return
        for neighbor in sorted(_neighbors_for_move(grid, state, path[-1], player_id)):
            if neighbor in path:
                continue
            if neighbor == active:
                found.append([*path, neighbor])
                continue
            # Wejście do węzła pośredniego zostawia jeszcze jeden skok do celu.
            if len(path) + 1 > max_len:
                continue
            if _node_passable_intermediate(
                grid,
                state,
                neighbor,
                player_id,
                can_enter_asteroids=ast,
                from_pos=from_pos,
                ignore_anomalies=ignore,
            ):
                walk([*path, neighbor])

    walk([from_pos])
    found.sort(key=lambda p: (len(p), p))
    return found


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
    """
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    ignore_cc = _ignores_own_command_token(state, player_id)
    result: list[RouteCargo] = []
    for position in route[:-1]:
        system = state.systems.get(position)
        if system is None:
            continue
        if player_id in system.command_tokens and not ignore_cc and position != route[0]:
            continue
        zones: list[tuple[str, dict[str, int]]] = [
            ("space", system.space_units.get(player_id, {}))
        ]
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


def _can_enter_asteroids(state: GameState, player_id: str) -> bool:
    """Czy gracz może wchodzić w pola asteroid (hook PERMIT, np. Antimass Deflectors)."""
    return rules_hooks.permits(rules_hooks.POINT_MOVEMENT_ENTER_ASTEROIDS, state, player_id)


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
) -> int | None:
    """Wartość ruchu statku ``base_type`` startującego z ``from_pos`` (None = nie rusza się sam).

    R2: wartość z WARIANTU jednostki gracza (ulepszenia wg technologii; np. Fighter II ma
    moveValue=2, bazowy myśliwiec jedzie tylko transportem). R7: start w mgławicy daje 1
    (Nav Suite to znosi). Potem hook MODIFY (technologie, zdolności, premie ``boost``).
    """
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    unit = resolve_unit_variant(registry, faction_id, technologies, base_type)
    move_value = unit.move_value if unit is not None else None
    if not move_value or move_value <= 0:
        return None
    # R7 (R_nebula, RULES.md 32.1): statek ZACZYNAJĄCY krok ruchu w mgławicy traktuje swoją
    # wartość ruchu jako 1; inne efekty (Gravity Drive — hook niżej) mogą ją podnieść.
    if _NEBULA in grid.anomalies_at(from_pos) and not _ignores_anomalies(state, player_id):
        move_value = 1
    result = rules_hooks.modify(
        rules_hooks.POINT_MOVEMENT_MOVE_VALUE, state, player_id, move_value,
        {"base_type": base_type, "boost": boost, "tempesta": tempesta},
    )
    return int(result)


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
    route: list[str] | None = None,
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
    if not is_space_unit(base_type):
        return False, f"Unit {base_type} is not a ship - it cannot move."
    from src.core import promissory_play  # lokalnie: unikamy cyklu importów

    if promissory_play.ceasefire_blocks(state, player_id):
        return False, "Ceasefire: you cannot move units into the active system."

    move_value = _effective_move_value(
        state, grid, registry, from_pos, base_type, player_id,
        boost=boost, tempesta=tempesta,
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
        error = route_error(state, grid, route, player_id)
        if error is not None:
            return False, error
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
        )
    if dist is None:
        return False, "No legal route to the active system (R4/R6)."
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
) -> GameState:
    """Wykonuje legalny ruch ``count`` statków ``base_type`` ze źródła do aktywnego systemu.

    Twardo waliduje (``can_move``); przenosi jednostki w ``space_units`` (zdejmuje ze
    źródła, dodaje do aktywnego). TODO (rozbudowa): transport sił naziemnych/myśliwców
    przez capacity; ruch wielu typów naraz; wybór trasy pod gravity rift.

    Raises:
        ValueError: Gdy ruch nielegalny (R1–R6) albo brak tylu statków w źródle.
    """
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
    ion_storm.note_move(new_state, grid, registry, from_pos, active)
    triggers.fire(new_state, GameEvent.SHIPS_MOVED, Moment.AFTER, subject=player_id, ctx=moved_ctx)
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
            if count <= 0 or not is_space_unit(base_type):
                continue
            ok, _ = can_move(
                state, grid, registry, position, base_type, player_id,
                boost=gravity_drive and not state.gravity_drive_used,
                tempesta=tempesta and not state.tempesta_used,
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
    route: list[str] | None = None,
) -> GameState:
    """Ruch FLOTY (statki + ładunek) ze źródła do aktywnego systemu — RULES.md 32.3.

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

    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    source = state.systems.get(from_pos)
    if route is not None:
        if not route or route[0] != from_pos:
            raise ValueError("The route must start at the system the ships move from.")
        route_problem = route_error(state, grid, route, player_id)
        if route_problem is not None:
            raise ValueError(route_problem)

    # Statki: walidacja legalności + dostępności (R1–R6, policzone per typ). Premia jednorazowa
    # dla JEDNEGO statku w akcji (Gravity Drive, RULES.md 55.6) działa WYŁĄCZNIE na życzenie
    # gracza (``gravity_drive=True``), tylko tam, gdzie bez niej ruch jest nielegalny, i nie
    # dla grupy większej niż 1.
    boost_spent = state.gravity_drive_used
    tempesta_spent = state.tempesta_used
    for base_type, count in ships.items():
        ok, reason = can_move(
            state, grid, registry, from_pos, base_type, player_id, route=route
        )
        if not ok:
            # Premie to osobne zdolności (Gravity Drive, Ionian Fuel Refinery): próbujemy
            # pojedynczą, potem obie naraz; zużywa się tylko to, co było potrzebne.
            can_gd = gravity_drive and not boost_spent
            can_tp = tempesta and not tempesta_spent
            chosen = next(
                (
                    (gd, tp)
                    for gd, tp in ((True, False), (False, True), (True, True))
                    if (can_gd or not gd)
                    and (can_tp or not tp)
                    and can_move(
                        state, grid, registry, from_pos, base_type, player_id,
                        boost=gd, tempesta=tp, route=route,
                    )[0]
                ),
                None,
            )
            if chosen is None:
                raise ValueError(reason)
            if count != 1:
                raise ValueError(
                    f"{reason} A +1 move bonus extends the move of only 1 ship per action."
                )
            boost_spent = boost_spent or chosen[0]
            tempesta_spent = tempesta_spent or chosen[1]
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
            if pickup_pos != from_pos and (route is None or pickup_pos not in route[:-1]):
                raise ValueError(
                    f"System {pickup_pos} is not on the route - ships cannot pick up units there."
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
    new_state.gravity_drive_used = boost_spent
    new_state.tempesta_used = tempesta_spent
    src = new_state.systems.get(from_pos)
    assert src is not None  # gwarantowane: dostępność sprawdzona wyżej

    # Cel (utwórz system, gdy trzeba). WSZYSTKO ląduje w PRZESTRZENI celu (T2) — ładunek
    # na statku, do czasu lądowania w kroku INWAZJA.
    dest = new_state.systems.get(active)
    if dest is None:
        system_id = grid.system_id_at(active) if active in grid.positions else ""
        dest = SystemState(position=active, system_id=system_id)
        new_state.systems[active] = dest

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
    # „po ruchu do systemu" (Rescue) - patrz ``core/hooks/reactions_tactical.py``.
    new_state.tactical_moved = True
    ion_storm.note_move(new_state, grid, registry, from_pos, active)
    if ships:
        moved_ctx = {
            "player": player_id, "position": active, "from": from_pos,
            "base_type": next(iter(ships)),
        }
        triggers.fire(
            new_state, GameEvent.SHIPS_MOVED, Moment.AFTER, subject=player_id, ctx=moved_ctx
        )
    return new_state
