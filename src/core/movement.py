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

from src.core.combat import resolve_unit_variant
from src.core.game_state import GameState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

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

# Alias technologii Antimass Deflectors (z danych: assets/.../technologies/pok.json →
# "amd"; nie z pamięci). Pozwala ruch przez/na asteroid field (RULES.md 1.1).
# Weryfikowany testem względem rejestru.
_ANTIMASS_ALIAS = "amd"

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
    has_antimass: bool,
) -> bool:
    """Czy węzeł POŚREDNI trasy jest przejezdny dla gracza (R4 + R6).

    Węzeł pośredni (nie start, nie cel): bez statków obcego gracza, bez supernowej,
    asteroid tylko z Antimass, nebula nieprzejezdna jako węzeł pośredni (wejście do
    nebuli tylko gdy jest systemem aktywnym = celem — RULES.md 1.2).
    """
    anomalies = grid.anomalies_at(position)
    if _SUPERNOVA in anomalies:
        return False
    if _ASTEROID in anomalies and not has_antimass:
        return False
    if _NEBULA in anomalies:
        return False
    if _ships_of_other_players(state.systems.get(position), player_id):
        return False
    return True


def _target_passable(
    grid: HexGrid, position: str, *, has_antimass: bool
) -> bool:
    """Czy CEL (aktywny system) jest przejezdny anomalicznie (R6).

    Cel może mieć obce statki (tam dojdzie do walki). Ale supernova zawsze blokuje,
    a asteroid wymaga Antimass. Nebula jako cel jest dozwolona (wejście tylko do
    aktywnego — a cel nim jest).
    """
    anomalies = grid.anomalies_at(position)
    if _SUPERNOVA in anomalies:
        return False
    if _ASTEROID in anomalies and not has_antimass:
        return False
    return True


def _shortest_legal_distance(
    grid: HexGrid,
    state: GameState,
    from_pos: str,
    to_pos: str,
    player_id: str,
    *,
    has_antimass: bool,
) -> int | None:
    """Długość najkrótszej LEGALNEJ trasy (liczba wejść) albo None, gdy brak.

    BFS po krawędziach sąsiedztwa grafu. Węzły POŚREDNIE muszą być przejezdne
    (``_node_passable_intermediate``); cel sprawdzany osobno (``_target_passable``).
    Długość = liczba systemów, w które statek WCHODZI (R2: ≤ moveValue).
    """
    if from_pos == to_pos:
        return 0
    if not _target_passable(grid, to_pos, has_antimass=has_antimass):
        return None
    # BFS: kolejka (pozycja, dystans). Odwiedzamy sąsiadów; do celu wchodzimy wprost,
    # przez węzeł pośredni tylko gdy przejezdny.
    visited = {from_pos}
    queue: deque[tuple[str, int]] = deque([(from_pos, 0)])
    while queue:
        pos, dist = queue.popleft()
        for neighbor in sorted(grid.neighbors(pos)):
            if neighbor in visited:
                continue
            if neighbor == to_pos:
                return dist + 1
            if _node_passable_intermediate(
                grid, state, neighbor, player_id, has_antimass=has_antimass
            ):
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return None


def _has_antimass(state: GameState, player_id: str) -> bool:
    """Czy gracz posiada technologię Antimass Deflectors (alias z danych)."""
    player = state.players.get(player_id)
    if player is None:
        return False
    return _ANTIMASS_ALIAS in player.technologies


def can_move(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    from_pos: str,
    base_type: str,
    player_id: str,
) -> tuple[bool, str]:
    """Sprawdza, czy ruch stosu ``base_type`` ze ``from_pos`` do aktywnego jest legalny.

    Zwraca ``(True, "")`` gdy legalny, albo ``(False, powód)``. Egzekwuje R1–R6
    (RULES.md 32.1). Nie mutuje stanu.
    """
    active = state.active_system
    if active is None:
        return False, "No active system - movement is only allowed during a tactical action (R1)."
    if not is_space_unit(base_type):
        return False, f"Unit {base_type} is not a ship - it cannot move."

    # R2: wartość ruchu z WARIANTU jednostki gracza (nie bazowego) — uwzględnia
    # ulepszenia wg posiadanych technologii. Np. Fighter II (tech ff2) ma moveValue=2,
    # podczas gdy bazowy fighter porusza się tylko transportem (moveValue=None).
    # Spójne z doborem wariantu w walce/produkcji (RULES.md 10/20).
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    unit = resolve_unit_variant(registry, faction_id, technologies, base_type)
    move_value = unit.move_value if unit is not None else None
    if not move_value or move_value <= 0:
        return False, (
            f"Unit {base_type} has no move value "
            "(porusza się transportem — capacity, TODO)."
        )

    # R3: start nie z własnym CC (wyjątek: aktywny system).
    source = state.systems.get(from_pos)
    if (
        from_pos != active
        and source is not None
        and player_id in source.command_tokens
    ):
        return False, "A ship cannot move out of a system containing its own command token (R3)."

    has_antimass = _has_antimass(state, player_id)
    dist = _shortest_legal_distance(
        grid, state, from_pos, active, player_id, has_antimass=has_antimass
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

    # Zdejmij ze źródła.
    src = new_state.systems[from_pos]
    src.space_units[player_id][base_type] -= count
    if src.space_units[player_id][base_type] <= 0:
        del src.space_units[player_id][base_type]
    if not src.space_units[player_id]:
        del src.space_units[player_id]

    # Dodaj do aktywnego (utwórz system/wpisy, gdy trzeba).
    dest = new_state.systems.get(active)
    if dest is None:
        system_id = grid.system_id_at(active) if active in grid.positions else ""
        dest = SystemState(position=active, system_id=system_id)
        new_state.systems[active] = dest
    dest.space_units.setdefault(player_id, {}).setdefault(base_type, 0)
    dest.space_units[player_id][base_type] += count
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
) -> dict[str, list[str]]:
    """Mapa {pozycja źródłowa -> lista base_type statków, które mogą ruszyć stamtąd}.

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
            ok, _ = can_move(state, grid, registry, position, base_type, player_id)
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
) -> GameState:
    """Ruch FLOTY (statki + ładunek) ze źródła do aktywnego systemu — RULES.md 32.3.

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

    # Statki: walidacja legalności + dostępności (R1–R6, policzone per typ).
    for base_type, count in ships.items():
        ok, reason = can_move(state, grid, registry, from_pos, base_type, player_id)
        if not ok:
            raise ValueError(reason)
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
        # T4: pickup z systemu z własnym CC zabroniony (wyjątek: aktywny system).
        if (
            from_pos != active
            and source is not None
            and player_id in source.command_tokens
        ):
            raise ValueError(
                "Cannot pick up units from a system containing your own command token (T4)."
            )
        # Zsumuj żądania po (typ, strefa) — i waliduj dostępność w tej strefie.
        needed_by_key: dict[tuple[str, str], int] = {}
        for item in cargo_items:
            if item.base_type not in _CARGO_BASE_TYPES:
                raise ValueError(
                    f"Unit {item.base_type} cannot be transported "
                    "(only fighters and ground forces)."
                )
            # Myśliwiec stoi w przestrzeni — nie zbiera się go z planety.
            if item.base_type == "fighter" and item.from_zone != "space":
                raise ValueError("Fighters can only be picked up from space.")
            needed_by_key[(item.base_type, item.from_zone)] = (
                needed_by_key.get((item.base_type, item.from_zone), 0) + item.count
            )
        for (base_type, zone), count in needed_by_key.items():
            available = _available_in_zone(source, player_id, base_type, zone)
            if available < count:
                where = "space" if zone == "space" else f"planet {zone}"
                raise ValueError(
                    f"Not enough {base_type} to transport from {where} in {from_pos}: "
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
    src = new_state.systems.get(from_pos)
    assert src is not None  # gwarantowane: dostępność sprawdzona wyżej

    def _take_space(base_type: str, count: int) -> None:
        """Zdejmuje ``count`` jednostek gracza ``base_type`` z PRZESTRZENI źródła."""
        src.space_units[player_id][base_type] -= count
        if src.space_units[player_id][base_type] <= 0:
            del src.space_units[player_id][base_type]
        if not src.space_units[player_id]:
            del src.space_units[player_id]

    def _take_planet(planet: str, base_type: str, count: int) -> None:
        """Zdejmuje ``count`` sił naziemnych gracza z PLANETY źródła (pickup transportu)."""
        by_player = src.planet_units[planet]
        by_player[player_id][base_type] -= count
        if by_player[player_id][base_type] <= 0:
            del by_player[player_id][base_type]
        if not by_player[player_id]:
            del by_player[player_id]

    # Zdejmij statki (zawsze z przestrzeni).
    for base_type, count in ships.items():
        _take_space(base_type, count)
    # Zdejmij ładunek z jego strefy źródłowej (przestrzeń lub planeta).
    for item in cargo_items:
        if item.from_zone == "space":
            _take_space(item.base_type, item.count)
        else:
            _take_planet(item.from_zone, item.base_type, item.count)

    # Dodaj do aktywnego (utwórz system/wpisy, gdy trzeba). WSZYSTKO ląduje w
    # PRZESTRZENI celu (T2) — ładunek na statku, do czasu lądowania w kroku INWAZJA.
    dest = new_state.systems.get(active)
    if dest is None:
        system_id = grid.system_id_at(active) if active in grid.positions else ""
        dest = SystemState(position=active, system_id=system_id)
        new_state.systems[active] = dest
    moved: dict[str, int] = dict(ships)
    for item in cargo_items:
        moved[item.base_type] = moved.get(item.base_type, 0) + item.count
    for base_type, count in moved.items():
        dest.space_units.setdefault(player_id, {}).setdefault(base_type, 0)
        dest.space_units[player_id][base_type] += count
    return new_state
