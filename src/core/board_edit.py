"""Edycja planszy God-Mode — czyste funkcje nad ``GameState`` (bez HTTP).

Operator (człowiek) ustawia stan fizycznej planszy bez sprawdzania zasad TI4:
jednostki w przestrzeni i na planetach, kontrola planet, pola gracza. To warstwa
``core`` (patrz docs/ARCHITEKTURA_KODU.md): funkcje przyjmują ``state`` (+ ``grid``/
``registry`` gdy potrzeba), zwracają NOWY ``GameState`` (przez ``clone``) albo rzucają
``ValueError`` (błąd domenowy, mapowany na HTTP w warstwie ``api``). Zero importów
FastAPI — dzięki temu te same funkcje wywoła i endpoint, i (w przyszłości) bot AI.

Reguły tożsamości/kontroli planet (opcja A, jedno źródło prawdy) opisano w RULES.md 11/12.
"""

from __future__ import annotations

from src.core.game_state import GameState, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE, BASE_TYPE_BY_ASYNC_ID


def validate_base_type(base_type: str) -> None:
    """Sprawdza, że ``baseType`` jest w katalogu (inaczej cicho ginie w web-data).

    Raises:
        ValueError: Gdy typ spoza ``ASYNC_ID_BY_BASE_TYPE`` (Bug 5).
    """
    if base_type not in ASYNC_ID_BY_BASE_TYPE:
        raise ValueError(f"Nieznany baseType: {base_type}")


def base_type_for_async(async_id: str) -> str:
    """Zwraca ``baseType`` dla ``asyncId`` z edytora.

    Raises:
        ValueError: Gdy ``asyncId`` nieznany.
    """
    base_type = BASE_TYPE_BY_ASYNC_ID.get(async_id)
    if base_type is None:
        raise ValueError(f"Nieznany asyncId: {async_id}")
    return base_type


def system_id_for(position: str, grid: HexGrid) -> str:
    """System ID z grida dla pozycji (lub pusty, gdy brak systemu na pozycji)."""
    if position in grid.positions:
        return str(grid.system_id_at(position))
    return ""


def resolve_player_id(faction_key: str, state: GameState) -> str:
    """Mapuje klucz z ``tileUnitData`` na ``player_id`` (RULES.md 11).

    Priorytet: 1) dokładne ``player_id``; 2) frakcja, ale TYLKO gdy jednoznaczna.
    Przy kolizji frakcji nie zgadujemy — zwracamy klucz bez zmian.
    """
    if faction_key in state.players:
        return faction_key
    matches = [
        pid for pid, player in state.players.items() if player.faction == faction_key
    ]
    if len(matches) == 1:
        return matches[0]
    return faction_key


def _zone_bucket(system: SystemState, zone: str, player_id: str) -> dict[str, int]:
    """Modyfikowalny słownik jednostek gracza w strefie (``"space"`` / id planety)."""
    if zone == "space":
        return system.space_units.setdefault(player_id, {})
    by_player = system.planet_units.setdefault(zone, {})
    return by_player.setdefault(player_id, {})


def _prune_zone(system: SystemState, zone: str, player_id: str) -> None:
    """Usuwa puste słowniki jednostek po edycji (porządek)."""
    if zone == "space":
        if not system.space_units.get(player_id):
            system.space_units.pop(player_id, None)
        return
    by_player = system.planet_units.get(zone)
    if by_player is not None:
        if not by_player.get(player_id):
            by_player.pop(player_id, None)
        if not by_player:
            system.planet_units.pop(zone, None)


def _get_or_make_system(
    state: GameState, position: str, grid: HexGrid
) -> SystemState:
    """Zwraca system ze stanu lub tworzy nowy (z system_id z grida)."""
    return state.systems.get(position) or SystemState(
        position=position, system_id=system_id_for(position, grid)
    )


def planet_position(
    planet_id: str, state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> str | None:
    """Pozycja ``RPP`` systemu zawierającego daną planetę (grid+rejestr, potem stan)."""
    for position in grid.positions:
        system = registry.systems.get(system_id_for(position, grid))
        if system is not None and planet_id in system.planets:
            return str(position)
    for position, sys_state in state.systems.items():
        system = registry.systems.get(sys_state.system_id)
        if system is not None and planet_id in system.planets:
            return str(position)
    return None


# --- Operacje wysokiego poziomu (zwracają nowy stan) ---------------------------


def set_space_units(
    state: GameState,
    grid: HexGrid,
    position: str,
    changes: list[tuple[str, str, int]],
) -> GameState:
    """Ustawia liczbę jednostek w przestrzeni systemu (``changes`` = [(player, base, count)]).

    ``count <= 0`` usuwa dany typ. Waliduje ``baseType``.

    Raises:
        ValueError: Gdy któryś ``baseType`` spoza katalogu.
    """
    for _player, base_type, _count in changes:
        validate_base_type(base_type)
    new_state = state.clone()
    system = _get_or_make_system(new_state, position, grid)
    for player_id, base_type, count in changes:
        bucket = system.space_units.setdefault(player_id, {})
        if count <= 0:
            bucket.pop(base_type, None)
        else:
            bucket[base_type] = count
        if not bucket:
            system.space_units.pop(player_id, None)
    new_state.systems[position] = system
    return new_state


def set_planet_units(
    state: GameState,
    grid: HexGrid,
    position: str,
    planet: str,
    changes: list[tuple[str, str, int]],
    owner_id: str | None = None,
) -> GameState:
    """Ustawia jednostki naziemne na planecie (+ opcjonalnie właściciela).

    Raises:
        ValueError: Gdy któryś ``baseType`` spoza katalogu.
    """
    for _player, base_type, _count in changes:
        validate_base_type(base_type)
    new_state = state.clone()
    system = _get_or_make_system(new_state, position, grid)
    by_player = system.planet_units.setdefault(planet, {})
    for player_id, base_type, count in changes:
        bucket = by_player.setdefault(player_id, {})
        if count <= 0:
            bucket.pop(base_type, None)
        else:
            bucket[base_type] = count
        if not bucket:
            by_player.pop(player_id, None)
    if owner_id is not None:
        system.planet_owners[planet] = owner_id
    new_state.systems[position] = system
    return new_state


def edit_units(
    state: GameState,
    grid: HexGrid,
    position: str,
    zone: str,
    faction_key: str,
    async_id: str,
    delta: int,
) -> GameState:
    """Dodaje/odejmuje jednostki w strefie systemu (delta, w terminach asyncId).

    Raises:
        ValueError: Gdy ``asyncId`` nieznany.
    """
    base_type = base_type_for_async(async_id)
    new_state = state.clone()
    player_id = resolve_player_id(faction_key, new_state)
    system = _get_or_make_system(new_state, position, grid)
    bucket = _zone_bucket(system, zone, player_id)
    new_count = max(0, bucket.get(base_type, 0) + delta)
    if new_count == 0:
        bucket.pop(base_type, None)
    else:
        bucket[base_type] = new_count
    _prune_zone(system, zone, player_id)
    new_state.systems[position] = system
    return new_state


def move_units(
    state: GameState,
    grid: HexGrid,
    *,
    from_position: str,
    from_zone: str,
    to_position: str,
    to_zone: str,
    faction_key: str,
    async_id: str,
    count: int,
) -> GameState:
    """Przenosi jednostki między strefami/systemami (bez reguł ruchu).

    Raises:
        ValueError: Gdy ``asyncId`` nieznany, ``count <= 0`` lub brak jednostek.
    """
    base_type = base_type_for_async(async_id)
    if count <= 0:
        raise ValueError("count musi być > 0")
    new_state = state.clone()
    player_id = resolve_player_id(faction_key, new_state)

    src = _get_or_make_system(new_state, from_position, grid)
    src_bucket = _zone_bucket(src, from_zone, player_id)
    available = src_bucket.get(base_type, 0)
    moved = min(available, count)
    if moved <= 0:
        raise ValueError("Brak jednostek do przesunięcia.")
    remaining = available - moved
    if remaining == 0:
        src_bucket.pop(base_type, None)
    else:
        src_bucket[base_type] = remaining
    _prune_zone(src, from_zone, player_id)
    new_state.systems[from_position] = src

    dst = _get_or_make_system(new_state, to_position, grid)
    dst_bucket = _zone_bucket(dst, to_zone, player_id)
    dst_bucket[base_type] = dst_bucket.get(base_type, 0) + moved
    new_state.systems[to_position] = dst
    return new_state


def sync_controlled_planets(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    target: list[str],
) -> None:
    """Synchronizuje kontrolę planet gracza do ``planet_owners`` (opcja A, Bug 3).

    MUTUJE przekazany ``state`` (zakłada się, że to już klon). Odbiera własność planet
    spoza listy docelowej, nadaje własność planet z listy w ich systemach.
    """
    target_set = set(target)
    for sys_state in state.systems.values():
        for planet_id, owner in list(sys_state.planet_owners.items()):
            if owner == player_id and planet_id not in target_set:
                del sys_state.planet_owners[planet_id]
    for planet_id in target_set:
        position = planet_position(planet_id, state, grid, registry)
        if position is None:
            continue  # planeta spoza mapy — nie da się umiejscowić
        system = _get_or_make_system(state, position, grid)
        system.planet_owners[planet_id] = player_id
        state.systems[position] = system


def edit_player(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    updates: dict[str, object],
) -> GameState:
    """Edytuje pola gracza (tworzy, gdy nie istnieje). ``updates`` = pola do nadpisania.

    ``leader_states`` jest SCALANE z istniejącym (edycja jednego lidera nie kasuje
    pozostałych). ``controlled_planets`` jest synchronizowane do ``planet_owners``
    systemów (opcja A — jedno źródło prawdy).
    """
    new_state = state.clone()
    player = new_state.players.get(player_id) or PlayerState(player_id=player_id)
    for field, value in updates.items():
        if field == "leader_states" and isinstance(value, dict):
            merged = dict(player.leader_states)
            merged.update(value)
            player.leader_states = merged
        else:
            setattr(player, field, value)
    new_state.players[player_id] = player
    controlled = updates.get("controlled_planets")
    if controlled is not None and isinstance(controlled, list):
        sync_controlled_planets(new_state, grid, registry, player_id, controlled)
    return new_state
