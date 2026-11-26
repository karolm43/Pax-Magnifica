"""Ruch: przejezdność, ścieżki i trasy (anomalie, wormhole, blokady, szczeliny) — RULES.md 32.

Warstwa pod ``movement.py`` (graf = czyste sąsiedztwo, blokady liczone tutaj);
``movement`` eksportuje te nazwy dalej.
"""

from __future__ import annotations

from collections import deque

from src.core import board_graph, rules_hooks, ship_roles
from src.core.game_state import GameState, MoveCargo, MoveLoss, MoveRecord
from src.core.hex_grid import HexGrid
from src.core.unit_catalog import is_space_unit

# Anomalie znaczące dla przejezdności węzłów POŚREDNICH trasy (RULES.md 32.1 R6).
_SUPERNOVA = "SUPERNOVA"
_ASTEROID = "ASTEROID_FIELD"
_NEBULA = "NEBULA"
_GRAVITY_RIFT = "GRAVITY_RIFT"

# Gravity rift (R_gravity_rift): rzut d10 dla każdego statku wychodzącego ze szczeliny lub
# przez nią przelatującego; wynik 1–3 usuwa statek z planszy (wraca do rezerwy).
_RIFT_REMOVED_ON = 3
# Ile skoków ponad długość najkrótszej trasy sprawdzamy, szukając trasy przez szczeliny.
_RIFT_SEARCH_EXTRA = 3
_RIFT_SEARCH_CAP = 7


def _ships_of_other_players(state: GameState, position: str, player_id: str) -> bool:
    """Czy w systemie stoją statki INNEGO gracza (blokada R4).

    Only ships block: a Floating Factory (Saar space dock in the space area) or ordinary ground
    forces do not (F_saar floating-factory/12). Eidolon Maximum on a planet is a ship, so it
    blocks too (F_naaz_rokha eidolon-maximum 2.2).
    """
    system = state.systems.get(position)
    if system is None:
        return False
    for owner, by_type in system.space_units.items():
        if owner == player_id:
            continue
        if any(count > 0 and is_space_unit(bt) for bt, count in by_type.items()):
            return True
    return any(
        other != player_id and ship_roles.has_planet_ships(state, other, position)
        for other in state.players
    )


def passage_blocked(state: GameState, position: str, player_id: str) -> bool:
    """Czy inny gracz zabrania ``player_id`` przelotu statkami PRZEZ system (hook
    ``movement.passage_blocked`` pytany o każdego innego gracza; Aerie Hololattice). Dotyczy
    węzłów pośrednich trasy - nie celu. Wyjątki przelotu (Light/Wave Deflector) tego nie znoszą."""
    return any(
        rules_hooks.permits(
            rules_hooks.POINT_MOVEMENT_PASSAGE_BLOCKED, state, other,
            {"position": position, "mover": player_id},
        )
        for other in state.players
        if other != player_id
    )


def _node_passable_intermediate(
    grid: HexGrid,
    state: GameState,
    position: str,
    player_id: str,
    *,
    can_enter_asteroids: bool,
    from_pos: str | None = None,
    ignore_anomalies: bool = False,
    base_type: str = "",
) -> bool:
    """Czy węzeł POŚREDNI trasy jest przejezdny dla gracza (R4 + R6).

    Węzeł pośredni (nie start, nie cel): bez statków obcego gracza, bez supernowej,
    asteroid tylko z Antimass, nebula nieprzejezdna jako węzeł pośredni (wejście do
    nebuli tylko gdy jest systemem aktywnym = celem — RULES.md 1.2).
    ``ignore_anomalies`` (Nav Suite) pomija blokady anomalii; ``from_pos`` trafia do hooka
    „przelot przez obce statki" (In The Silence Of Space: dotyczy statków z wybranego systemu).
    """
    anomalies = set() if ignore_anomalies else grid.anomalies_at(position)
    if _SUPERNOVA in anomalies and not can_pass_supernova(state, player_id):
        return False  # Gashlai Physiology: przelot przez supernowe (RULES.md 62.13)
    if _ASTEROID in anomalies and not can_enter_asteroids:
        return False
    if _NEBULA in anomalies and not rules_hooks.permits(
        rules_hooks.POINT_MOVEMENT_THROUGH_NEBULA, state, player_id
    ):
        return False  # Shared Research: przelot przez mgławicę (wejście nadal tylko do aktywnej)
    if passage_blocked(state, position, player_id):
        return False  # Aerie Hololattice: przelot przez system ze strukturami Argent (F_argent)
    if _ships_of_other_players(state, position, player_id) and not rules_hooks.permits(
        rules_hooks.POINT_MOVEMENT_PASS_FOREIGN_SHIPS,
        state,
        player_id,
        {"position": position, "from": from_pos, "base_type": base_type},
    ):
        return False
    return True


def _target_passable(
    grid: HexGrid,
    position: str,
    *,
    can_enter_asteroids: bool,
    ignore_anomalies: bool = False,
    into_supernova: bool = False,
) -> bool:
    """Czy CEL (aktywny system) jest przejezdny anomalicznie (R6).

    Cel może mieć obce statki (tam dojdzie do walki). Supernowa blokuje (poza ``into_supernova``
    — Magmus Reactor), a asteroid wymaga Antimass. Nebula jako cel jest dozwolona (wejście tylko
    do aktywnego — a cel nim jest). ``ignore_anomalies`` (Nav Suite) pomija te blokady.
    """
    if ignore_anomalies:
        return True
    anomalies = grid.anomalies_at(position)
    if _SUPERNOVA in anomalies and not into_supernova:
        return False
    if _ASTEROID in anomalies and not can_enter_asteroids:
        return False
    return True


_WORMHOLE_TYPES = ("ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA", "ETA", "IOTA", "THETA")


def wormhole_link_blocked(
    grid: HexGrid, state: GameState, player_id: str, a: str, b: str
) -> bool:
    """Czy krawędź ``a``-``b`` istnieje TYLKO dzięki wormholom, które nie działają w ruchu.

    Hook FORBID ``movement.wormholes_blocked`` (prawa Enforced Travel Ban, Nexus Sovereignty -
    RULES.md 51.6) zwraca typy wormholi bez efektu dla tej krawędzi. Sąsiedztwo geometryczne
    i portale zostają. Dotyczy ruchu i odwrotu (C_agendas), nie efektów „adjacent".
    """
    if grid.link_kind(a, b) != "wormhole":
        return False
    blocked = rules_hooks.forbidden(
        rules_hooks.POINT_MOVEMENT_WORMHOLES_BLOCKED, state, player_id,
        {"position": a, "neighbor": b},
    )
    if not blocked:
        return False
    shared = {
        t for t in _WORMHOLE_TYPES
        if a in grid.wormhole_positions(t) and b in grid.wormhole_positions(t)
    }
    return bool(shared) and shared <= {t.upper() for t in blocked}


def _neighbors_for_move(
    grid: HexGrid, state: GameState, position: str, player_id: str
) -> set[str]:
    """Sąsiedzi systemu na potrzeby RUCHU gracza: graf mapy + efekty tej akcji.

    Lost Star Chart (hook PERMIT): systemy z wormholem alpha i beta sąsiadują ze sobą w tej
    akcji. Graf mapy (czyste sąsiedztwo) zostaje nietknięty - to osobna warstwa (RULES.md 1/3).
    """
    result = {
        n for n in grid.neighbors(position)
        if not wormhole_link_blocked(grid, state, player_id, position, n)
    }
    if rules_hooks.permits(rules_hooks.POINT_MOVEMENT_ALPHA_BETA_ADJACENT, state, player_id):
        alpha = grid.wormhole_positions("ALPHA")
        beta = grid.wormhole_positions("BETA")
        if position in alpha:
            result |= beta
        if position in beta:
            result |= alpha
        result.discard(position)
    # Hook FORBID: systemy dodatkowo sąsiadujące w tej aktywacji (Spatial Conduit Cylinder).
    extra = rules_hooks.forbidden(
        rules_hooks.POINT_MOVEMENT_EXTRA_ADJACENT, state, player_id, {"position": position}
    )
    if extra:
        result |= set(extra) - {position}
    # Player-dependent adjacency (RULES.md 61.7): added AFTER the wormhole-law filter - these are
    # not map wormhole links (F_creuss: Enforced Travel Ban does not affect Quantum Entanglement).
    result |= board_graph.extra_adjacent_for_player(state, player_id, position, grid)
    return result


def _ignores_own_command_token(state: GameState, player_id: str) -> bool:
    """Czy gracz może ruszać i transportować jednostki z systemów ze SWOIM żetonem (Dominus Orb)."""
    return rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_OWN_CC, state, player_id)


def _ignores_anomalies(state: GameState, player_id: str) -> bool:
    """Czy gracz ignoruje efekty anomalii w RUCHU (Nav Suite: tylko w kroku Movement; Circlet of
    the Void) - blokady przejazdu, mgławica, rzut za szczelinę."""
    return rules_hooks.permits(
        rules_hooks.POINT_MOVEMENT_IGNORE_ANOMALIES, state, player_id
    ) or rules_hooks.permits(
        rules_hooks.POINT_MOVEMENT_IGNORE_ANOMALIES_KEEP_RIFT, state, player_id
    )


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
    base_type: str = "",
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
            into_supernova=can_enter_supernova(state, player_id),
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
        base_type=base_type,
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
                base_type=base_type,
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
    base_type: str = "",
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
        base_type=base_type,
    )
    return None if path is None else len(path) - 1


def route_through(
    state: GameState,
    grid: HexGrid,
    from_pos: str,
    via: list[str],
    player_id: str,
    base_type: str = "",
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
            base_type=base_type,
        )
        if segment is None:
            return None
        path.extend(segment[1:])
    if len(set(path)) != len(path):
        return None
    return path


def route_error(
    state: GameState, grid: HexGrid, route: list[str], player_id: str, base_type: str = ""
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
            base_type=base_type,
        ):
            return f"The route passes through system {node}, which blocks movement (R4/R6)."
    if not _target_passable(
        grid, active, can_enter_asteroids=ast, ignore_anomalies=ignore,
        into_supernova=can_enter_supernova(state, player_id),
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
    base_type: str = "",
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
        grid, active, can_enter_asteroids=ast, ignore_anomalies=ignore,
        into_supernova=can_enter_supernova(state, player_id),
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
                base_type=base_type,
            ):
                walk([*path, neighbor])

    walk([from_pos])
    found.sort(key=lambda p: (len(p), p))
    return found


def rift_nodes(
    state: GameState, grid: HexGrid, route: list[str], player_id: str
) -> list[str]:
    """Systemy trasy będące gravity rift, z których statek WYCHODZI albo przez które przelatuje -
    każdy daje +1 do ruchu.

    Cel trasy (aktywny system) się nie liczy: wejście do szczeliny nie daje +1 ani rzutu
    (R_gravity_rift). Nav Suite ignoruje efekty anomalii, więc zwraca pustą listę („Those ships
    will not get +1”, C_action_cards); Circlet of the Void premię zachowuje (C_relics).
    """
    if rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_ANOMALIES, state, player_id):
        return []
    return [node for node in route[:-1] if _GRAVITY_RIFT in grid.anomalies_at(node)]


def rift_bonus(state: GameState, grid: HexGrid, route: list[str], player_id: str) -> int:
    """Premia ruchu z gravity rift na trasie: +1 za każdą RÓŻNĄ szczelinę, z której statek wychodzi
    lub przez którą przelatuje (ta sama szczelina wielokrotnie = +1 raz, ale rzut za każde wyjście
    - R_gravity_rift notes/2, F_vuilraith dimensional-tear/2), plus JEDNO +1, gdy jest choć jedna
    szczelina i działa efekt Crucible (F_vuilraith crucible/2)."""
    nodes = set(rift_nodes(state, grid, route, player_id))
    # Nav Suite zeruje zwykłe +1, ale Crucible nadal daje swoje +1 (F_vuilraith Crucible 6).
    through = any(_GRAVITY_RIFT in grid.anomalies_at(node) for node in route[:-1])
    extra = through and rules_hooks.permits(
        rules_hooks.POINT_MOVEMENT_RIFT_EXTRA_BONUS, state, player_id
    )
    return len(nodes) + (1 if extra else 0)


def rift_rolls(state: GameState, player_id: str) -> bool:
    """Czy statki gracza rzucają za szczeliny w tym ruchu (Nav Suite / Circlet / Crucible: nie)."""
    return not _ignores_anomalies(state, player_id) and not rules_hooks.permits(
        rules_hooks.POINT_MOVEMENT_RIFT_EXTRA_BONUS, state, player_id
    )


def rolls_at(state: GameState, player_id: str, position: str) -> bool:
    """Czy jednostki gracza rzucają za szczelinę w position (Dimensional Tear własny: nie)."""
    return rift_rolls(state, player_id) and position not in rules_hooks.forbidden(
        rules_hooks.POINT_MOVEMENT_RIFT_NO_ROLL, state, player_id
    )


def rift_roll_nodes(
    state: GameState, grid: HexGrid, route: list[str], player_id: str
) -> list[str]:
    """Szczeliny trasy, za które statki gracza RZUCAJĄ (R_gravity_rift; bez własnych Dimensional
    Tear i bez rzutów pod Nav Suite / Crucible)."""
    if not rift_rolls(state, player_id):
        return []
    return [n for n in rift_nodes(state, grid, route, player_id) if rolls_at(state, player_id, n)]


def _rift_route_within(
    state: GameState,
    grid: HexGrid,
    from_pos: str,
    player_id: str,
    move_value: int,
    base_type: str = "",
) -> list[str] | None:
    """Trasa, na którą statek o ``move_value`` zdąży dzięki +1 za każdą szczelinę (albo None)."""
    if not any(_GRAVITY_RIFT in grid.anomalies_at(p) for p in grid.positions):
        return None
    candidates = legal_routes(
        state, grid, from_pos, player_id,
        max_len=min(move_value + _RIFT_SEARCH_EXTRA, _RIFT_SEARCH_CAP), cap=120,
        base_type=base_type,
    )
    for candidate in candidates:
        if len(candidate) - 1 <= move_value + rift_bonus(state, grid, candidate, player_id):
            return candidate
    return None


def _can_enter_asteroids(state: GameState, player_id: str) -> bool:
    """Czy gracz może wchodzić w pola asteroid (hook PERMIT, np. Antimass Deflectors)."""
    return rules_hooks.permits(rules_hooks.POINT_MOVEMENT_ENTER_ASTEROIDS, state, player_id)


def can_enter_supernova(state: GameState, player_id: str) -> bool:
    """Czy jednostki gracza wchodzą DO supernowej (Magmus Reactor; R_space_combat: także odwrót)."""
    return rules_hooks.permits(rules_hooks.POINT_MOVEMENT_INTO_SUPERNOVA, state, player_id)


def can_pass_supernova(state: GameState, player_id: str) -> bool:
    """Czy statki gracza przelatują PRZEZ supernowe (Gashlai Physiology; wejście daje też Magmus
    Reactor - przelot to wejście i wyjście)."""
    return rules_hooks.permits(
        rules_hooks.POINT_MOVEMENT_THROUGH_SUPERNOVA, state, player_id
    ) or can_enter_supernova(state, player_id)


def build_move_record(
    grid: HexGrid,
    route: list[str],
    player_id: str,
    ships: dict[str, int],
    cargo: list[tuple[str, int, str, str]],
    lost: list[MoveLoss] | None = None,
    boosted: list[str] | None = None,
) -> MoveRecord:
    """Presentation record of a confirmed fleet move (``GameState.last_move``).

    ``cargo`` items are ``(base_type, count, from_zone, from_position)``. Hops are classified
    from the map graph: ``lane`` for plain adjacency, otherwise the link kind (``wormhole`` /
    ``portal``), or ``jump`` for adjacency granted by a hook (Lost Star Chart, Conduit).
    ``lost`` = units a gravity rift removed on the way, with the rift they were lost in.
    ``boosted`` = base types of ships that spent the Gravity Drive bonus on this move.
    """
    hops: list[str] = []
    for a, b in zip(route, route[1:], strict=False):
        kind = grid.link_kind(a, b)
        hops.append("lane" if kind == "adjacent" else (kind or "jump"))
    anomalies = {
        pos: sorted(found)
        for pos in dict.fromkeys(route)
        if (found := grid.anomalies_at(pos))
    }
    return MoveRecord(
        player_id=player_id,
        route=list(route),
        hops=hops,
        anomalies=anomalies,
        ships={bt: n for bt, n in ships.items() if n > 0},
        cargo=[
            MoveCargo(base_type=bt, count=n, from_zone=zone, from_position=pos)
            for bt, n, zone, pos in cargo
            if n > 0
        ],
        lost=[loss for loss in lost or [] if loss.count > 0],
        boosted=list(boosted or []),
    )
