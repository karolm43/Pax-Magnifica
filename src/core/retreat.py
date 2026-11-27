"""Odwroty w walce kosmicznej: dozwolone systemy i wykonanie odwrotu (RULES.md 39.5).

Moduł nie zna przebiegu walki (kroki, okna) — to robi ``core/battle.py``. Tu są czyste reguły:

- ``retreat_destinations`` — systemy, do których gracz może się wycofać (O4);
- ``perform_retreat`` — przeniesienie statków z ruchem + ładunku, usunięcie tego, czego nie da
  się zabrać, i położenie żetonu dowodzenia w systemie docelowym (O5/O6).

Funkcje CZYSTE (``state -> state`` przez klon). Walidacja twarda: ``ValueError`` → HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core import (
    board_graph,
    command_tokens,
    floating_structures,
    ion_storm,
    rules_hooks,
    unit_ops,
)
from src.core.combat import player_variant, resolve_unit_variant
from src.core.game_state import GameState, SystemState
from src.core.hex_grid import HexGrid
from src.core.movement import (
    _CARGO_BASE_TYPES,
    CargoPickup,
    _can_enter_asteroids,
    _capacity_provided,
    _capacity_used,
    can_enter_supernova,
    fire_ships_moved,
    wormhole_link_blocked,
)
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

# Anomalie blokujące odwrót (O4): supernowa nieprzejezdna; pole asteroid tylko z Antimass
# Deflectors. Mgławica NIE blokuje - R_nebula notes/2-3 (decyzja użytkownika 2026-11-24):
# do mgławicy wolno wejść, także odwrotem, choć nie jest systemem aktywnym.
_SUPERNOVA = "SUPERNOVA"
_ASTEROID = "ASTEROID_FIELD"

_GROUND_FORCES = frozenset({"infantry", "mech"})

# ⚠️ ZAŁOŻENIE (RULES.md 39.5): domyślna kolejność ładunku z przestrzeni, gdy gracz go nie
# wskaże — mechy, piechota, myśliwce.
_AUTO_CARGO_ORDER = ("mech", "infantry", "fighter")

# Pule żetonów na arkuszu dowodzenia (gdy rezerwa pusta — O6). Kolejność = domyślna
# (⚠️ ZAŁOŻENIE, RULES.md 39.5); gracz może wskazać pulę jawnie.
TOKEN_POOLS: dict[str, str] = {
    "tactic": "tactical",
    "fleet": "fleet",
    "strategy": "strategic",
}


@dataclass
class RetreatResult:
    """Co się stało przy odwrocie (do dziennika walki i animacji okna bitwy)."""

    moved: dict[str, int] = field(default_factory=dict)
    removed: dict[str, int] = field(default_factory=dict)
    token_placed: bool = False
    token_from: str | None = None  # "reinforcements" albo nazwa puli z ``TOKEN_POOLS``


def _other_ships(system: SystemState, player_id: str) -> bool:
    """Czy w przestrzeni systemu stoją statki innego gracza (blokada O4)."""
    return any(
        count > 0 and is_space_unit(base_type)
        for pid, by_type in system.space_units.items()
        if pid != player_id
        for base_type, count in by_type.items()
    )


def _foreign_units(system: SystemState, player_id: str) -> bool:
    """Czy w systemie stoją jakiekolwiek jednostki innego gracza (statki, naziemne, struktury)."""
    if any(
        count > 0
        for pid, by_type in system.space_units.items()
        if pid != player_id
        for count in by_type.values()
    ):
        return True
    return any(
        count > 0
        for by_player in system.planet_units.values()
        for pid, by_type in by_player.items()
        if pid != player_id
        for count in by_type.values()
    )


def _has_presence(system: SystemState, player_id: str) -> bool:
    """Jednostki gracza (przestrzeń lub planeta) albo kontrolowana planeta (O4)."""
    if any(c > 0 for c in system.space_units.get(player_id, {}).values()):
        return True
    if any(
        c > 0
        for by_player in system.planet_units.values()
        for c in by_player.get(player_id, {}).values()
    ):
        return True
    return player_id in system.planet_owners.values()


def retreat_destinations(
    state: GameState, grid: HexGrid, position: str, player_id: str
) -> list[str]:
    """Systemy, do których gracz może się wycofać z walki w ``position`` (O4), posortowane.

    Hook PERMIT ``retreat.anywhere`` (Dark Energy Tap) znosi wymóg własnej obecności: wolno
    wycofać się do sąsiedniego systemu, w którym nie ma jednostek żadnego innego gracza
    (statków, sił naziemnych ani struktur).
    """
    combat = state.active_combat
    if combat is not None and combat.no_retreat and combat.position == position:
        return []  # Benediction: "neither player can retreat" (RULES.md 62.23)
    can_enter_asteroids = _can_enter_asteroids(state, player_id)
    anywhere = rules_hooks.permits(rules_hooks.POINT_RETREAT_ANYWHERE, state, player_id)
    result: list[str] = []
    # Tactical-action adjacency (SCC, Lazax Gate Folding) and the retreating player's own
    # adjacency (RULES.md 61.7) also allow a retreat.
    own = board_graph.extra_adjacent_for_player(state, player_id, position, grid)
    for neighbor in sorted(board_graph.neighbors_for_player(state, grid, player_id, position)):
        if neighbor not in own and wormhole_link_blocked(
            grid, state, player_id, position, neighbor
        ):
            continue
        anomalies = grid.anomalies_at(neighbor)
        if _SUPERNOVA in anomalies and not can_enter_supernova(state, player_id):
            continue  # R_space_combat: odwrót do supernowej tylko z Magmus Reactor
        if _ASTEROID in anomalies and not can_enter_asteroids:
            continue
        system = state.systems.get(neighbor)
        if system is None:
            if anywhere:  # pusty system (Dark Energy Tap): brak cudzych jednostek
                result.append(neighbor)
            continue
        if _other_ships(system, player_id):
            continue
        if _has_presence(system, player_id) or (
            anywhere and not _foreign_units(system, player_id)
        ):
            result.append(neighbor)
    return result


def _auto_cargo(
    space_cargo: dict[str, int], free: int, cost: dict[str, int]
) -> list[CargoPickup]:
    """Domyślny ładunek: mechy → piechota → myśliwce z przestrzeni, do zapełnienia pojemności."""
    picked: list[CargoPickup] = []
    for base_type in _AUTO_CARGO_ORDER:
        have = space_cargo.get(base_type, 0)
        unit_cost = cost.get(base_type, 1)
        if have <= 0:
            continue
        take = have if unit_cost == 0 else min(have, free // unit_cost)
        if take > 0:
            picked.append(CargoPickup(base_type=base_type, count=take, from_zone="space"))
            free -= take * unit_cost
    return picked


def perform_retreat(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    position: str,
    player_id: str,
    destination: str,
    cargo: list[CargoPickup] | None = None,
    token_pool: str | None = None,
    ion_storm_token: bool | None = None,
) -> tuple[GameState, RetreatResult]:
    """Wycofuje jednostki gracza z ``position`` do ``destination`` (O5/O6) - na KLONIE stanu.

    Opakowanie ``retreat_in_place`` (zwraca nowy stan); parametry i błędy jak tam.
    ``ion_storm_token`` = wybór wormholu przy Ion Storm (``ion_storm.note_move``).
    """
    new_state = state.clone()
    result = retreat_in_place(
        new_state, grid, registry, position, player_id, destination, cargo, token_pool
    )
    ships = {bt: n for bt, n in result.moved.items() if is_space_unit(bt)}
    # Odwrót to ruch (F_muaat Nova Seed 1: „the Muaat player may trigger Nova Seed when they
    # retreat”) - ``kind = retreat`` odróżnia go od ruchu akcji taktycznej.
    fire_ships_moved(new_state, player_id, destination, position, ships, kind="retreat")
    # Koniec kroku Retreat: odwrót przez wormhole Ion Storm obraca żeton (Skilled Retreat: nie).
    ion_storm.note_move(new_state, grid, registry, position, destination, ion_storm_token)
    ion_storm.flip_used(new_state)
    return new_state, result


def ships_move_destinations(
    state: GameState, grid: HexGrid, position: str, player_id: str
) -> list[str]:
    """Sąsiednie systemy, do których wolno PRZENIEŚĆ statki kartą (Skilled Retreat), posortowane.

    To NIE odwrót (O4 bez wymogu własnej obecności): wystarczy, że w celu nie ma statków
    innego gracza; nadal odpadają supernowa i pole asteroid bez Antimass Deflectors (mgławica
    dozwolona - R_nebula notes/2).
    """
    can_enter_asteroids = _can_enter_asteroids(state, player_id)
    result: list[str] = []
    own = board_graph.extra_adjacent_for_player(state, player_id, position, grid)
    for neighbor in sorted(board_graph.neighbors_for_player(state, grid, player_id, position)):
        if neighbor not in own and wormhole_link_blocked(
            grid, state, player_id, position, neighbor
        ):
            continue
        anomalies = grid.anomalies_at(neighbor)
        if _SUPERNOVA in anomalies and not can_enter_supernova(state, player_id):
            continue  # R_space_combat: odwrót do supernowej tylko z Magmus Reactor
        if _ASTEROID in anomalies and not can_enter_asteroids:
            continue
        system = state.systems.get(neighbor)
        if system is not None and _other_ships(system, player_id):
            continue
        result.append(neighbor)
    return result


def retreat_in_place(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    position: str,
    player_id: str,
    destination: str,
    cargo: list[CargoPickup] | None = None,
    token_pool: str | None = None,
    *,
    destinations: list[str] | None = None,
    token_pools: bool = True,
    carry_all: bool = False,
) -> RetreatResult:
    """Wycofuje jednostki gracza z ``position`` do ``destination`` (O5/O6) - MUTUJE ``state``.

    ``cargo`` = jawny ładunek (strefa ``"space"`` albo planeta kontrolowana w aktywnym
    systemie); ``None`` = ładunek domyślny (``_auto_cargo``). ``token_pool`` = pula na arkuszu,
    z której idzie żeton, gdy rezerwa jest pusta (``TOKEN_POOLS``; ``None`` = kolejność domyślna).
    ``destinations`` nadpisuje listę dozwolonych celów (Skilled Retreat);
    ``token_pools=False`` = żeton tylko z rezerwy (bez sięgania do puli arkusza).
    ``carry_all=True`` = cały ładunek z przestrzeni jedzie razem ze statkami, także ponad
    pojemność (Skilled Retreat, C_action_cards skilled-retreat/8); nadwyżkę usuwa potem
    sprawdzenie pojemności w systemie docelowym (skilled-retreat/5).

    Raises:
        ValueError: Niedozwolony cel, zły ładunek (przekroczona pojemność, porzucanie ładunku
            przy wolnej pojemności, planeta nie gracza), zła pula żetonów.
    """
    allowed = (
        destinations
        if destinations is not None
        else retreat_destinations(state, grid, position, player_id)
    )
    if destination not in allowed:
        raise ValueError(f"Your ships cannot retreat to system {destination}.")
    if token_pool is not None and token_pool not in TOKEN_POOLS:
        raise ValueError(f"Unknown command token pool: {token_pool}.")

    player = state.players.get(player_id)
    faction = player.faction if player is not None else None
    techs = player.technologies if player is not None else []
    src0 = state.systems[position]

    # O5: statki z wartością ruchu wycofują się same; myśliwce bez ruchu i siły naziemne
    # w przestrzeni to ładunek; statki bez ruchu zostają w systemie.
    movers: dict[str, int] = {}
    space_cargo: dict[str, int] = {}
    for base_type, count in sorted(src0.space_units.get(player_id, {}).items()):
        if count <= 0:
            continue
        unit = (
            player_variant(registry, player, base_type) if player is not None
            else resolve_unit_variant(registry, faction, techs, base_type)
        )
        # Struktura pływająca wycofuje się jak statek (Floating Factory, RULES.md 62.14).
        mover = floating_structures.moves_as_ship(state, player_id, base_type)
        if mover and unit is not None and (unit.move_value or 0) > 0:
            movers[base_type] = count
        elif base_type in _CARGO_BASE_TYPES:
            space_cargo[base_type] = count

    capacity = sum(
        _capacity_provided(registry, faction, techs, bt) * n for bt, n in movers.items()
    )
    cost = {bt: _capacity_used(registry, faction, techs, bt) for bt in _CARGO_BASE_TYPES}

    if carry_all:
        chosen = [CargoPickup(bt, n) for bt, n in sorted(space_cargo.items())] if movers else []
    elif cargo is None:
        chosen = _auto_cargo(space_cargo, capacity, cost) if movers else []
    else:
        chosen = [c for c in cargo if c.count > 0]
        if chosen and not movers:
            raise ValueError("Cargo needs a retreating ship to carry it.")
        need: dict[tuple[str, str], int] = {}
        for item in chosen:
            if item.base_type not in _CARGO_BASE_TYPES:
                raise ValueError(f"{item.base_type} cannot be transported.")
            if item.from_zone != "space":
                if item.base_type not in _GROUND_FORCES:
                    raise ValueError("Only ground forces can be picked up from a planet.")
                if src0.planet_owners.get(item.from_zone) != player_id:
                    raise ValueError(
                        "You can only take ground forces from planets you control "
                        f"({item.from_zone})."
                    )
            key = (item.base_type, item.from_zone)
            need[key] = need.get(key, 0) + item.count
        for (base_type, zone), count in need.items():
            if zone == "space":
                have = space_cargo.get(base_type, 0)
            else:
                have = src0.planet_units.get(zone, {}).get(player_id, {}).get(base_type, 0)
            if count > have:
                raise ValueError(f"Not enough {base_type} in {zone} to transport.")

    used = sum(cost.get(c.base_type, 1) * c.count for c in chosen)
    if used > capacity and not carry_all:
        raise ValueError(
            f"The retreating ships can carry {capacity}, but the cargo needs {used}."
        )
    taken_space: dict[str, int] = {}
    for item in chosen:
        if item.from_zone == "space":
            taken_space[item.base_type] = taken_space.get(item.base_type, 0) + item.count
    left_behind = {
        bt: n - taken_space.get(bt, 0)
        for bt, n in space_cargo.items()
        if n - taken_space.get(bt, 0) > 0
    }
    free = capacity - used
    if not carry_all and any(cost.get(bt, 1) <= free for bt in left_behind):
        raise ValueError(
            "Fighters and ground forces in space cannot be left behind while the "
            "retreating ships still have free capacity."
        )

    new_state = state  # mutacja w miejscu: walidacja powyżej poprzedza każdą zmianę
    src = new_state.systems[position]
    dest = new_state.systems.get(destination)
    if dest is None:  # pusty system (Dark Energy Tap) - jeszcze bez wpisu w stanie
        system_id = grid.system_id_at(destination) if destination in grid.positions else ""
        dest = SystemState(position=destination, system_id=system_id)
        new_state.systems[destination] = dest
    result = RetreatResult()
    # Uszkodzenia jadą razem z jednostkami do PRZESTRZENI systemu docelowego.
    for base_type, count in movers.items():
        unit_ops.transfer_units(new_state, src, "space", dest, "space", player_id, base_type, count)
        result.moved[base_type] = result.moved.get(base_type, 0) + count
    for item in chosen:
        unit_ops.transfer_units(
            new_state, src, item.from_zone, dest, "space", player_id, item.base_type, item.count
        )
        result.moved[item.base_type] = result.moved.get(item.base_type, 0) + item.count
    # O5: ładunek z przestrzeni, którego nie dało się zabrać, jest usuwany.
    for base_type, count in left_behind.items():
        unit_ops.remove_units(
            new_state, src, "space", player_id, base_type, count, UnitCause.REMOVED
        )
        result.removed[base_type] = count

    # O6: żeton dowodzenia w systemie docelowym (tylko gdy coś się wycofało, bez duplikatu).
    if result.moved and player_id not in dest.command_tokens:
        owner = new_state.players.get(player_id)
        if owner is not None:
            if command_tokens.reinforcements(new_state, player_id) > 0:
                command_tokens.take_from_reinforcements(new_state, player_id)
                result.token_from = "reinforcements"
            elif token_pools:
                pools = [token_pool] if token_pool is not None else list(TOKEN_POOLS)
                if (
                    token_pool is not None
                    and command_tokens.pool_count(new_state, player_id, TOKEN_POOLS[token_pool])
                    <= 0
                ):
                    raise ValueError(f"Your {token_pool} pool has no command token.")
                for pool in pools:
                    sheet_pool = TOKEN_POOLS[pool]
                    if command_tokens.pool_count(new_state, player_id, sheet_pool) > 0:
                        command_tokens.spend_from_pool(new_state, player_id, sheet_pool)
                        result.token_from = pool
                        break
            if result.token_from is not None:
                command_tokens.place_token(new_state, dest, player_id)
                result.token_placed = True
    return result
