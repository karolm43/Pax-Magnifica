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

from src.core.combat import resolve_unit_variant
from src.core.game_state import GameState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

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
