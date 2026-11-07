"""Odwroty w walce kosmicznej: dozwolone systemy i wykonanie odwrotu (RULES.md 39.5).

Moduł nie zna przebiegu walki (kroki, okna) — to robi ``core/battle.py``. Tu są czyste reguły:

- ``retreat_destinations`` — systemy, do których gracz może się wycofać (O4);
- ``perform_retreat`` — przeniesienie statków z ruchem + ładunku, usunięcie tego, czego nie da
  się zabrać, i położenie żetonu dowodzenia w systemie docelowym (O5/O6).

Funkcje CZYSTE (``state -> state`` przez klon). Walidacja twarda: ``ValueError`` → HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count, move_damage, set_damaged
from src.core.game_state import GameState, SystemState
from src.core.hex_grid import HexGrid
from src.core.movement import (
    _CARGO_BASE_TYPES,
    CargoPickup,
    _capacity_provided,
    _capacity_used,
    _has_antimass,
)
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

# Anomalie blokujące odwrót (O4). Mgławica: cel nie jest systemem aktywnym (R_nebula);
# supernowa: nieprzejezdna; pole asteroid: tylko z Antimass Deflectors.
_SUPERNOVA = "SUPERNOVA"
_NEBULA = "NEBULA"
_ASTEROID = "ASTEROID_FIELD"

_GROUND_FORCES = frozenset({"infantry", "mech"})

# ⚠️ ZAŁOŻENIE (RULES.md 39.5): domyślna kolejność ładunku z przestrzeni, gdy gracz go nie
# wskaże — mechy, piechota, myśliwce.
_AUTO_CARGO_ORDER = ("mech", "infantry", "fighter")

# Pule żetonów na arkuszu dowodzenia (gdy rezerwa pusta — O6). Kolejność = domyślna
# (⚠️ ZAŁOŻENIE, RULES.md 39.5); gracz może wskazać pulę jawnie.
TOKEN_POOLS: dict[str, str] = {
    "tactic": "tactical_cc",
    "fleet": "fleet_cc",
    "strategy": "strategic_cc",
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
    """Systemy, do których gracz może się wycofać z walki w ``position`` (O4), posortowane."""
    has_antimass = _has_antimass(state, player_id)
    result: list[str] = []
    for neighbor in sorted(grid.neighbors(position)):
        if neighbor == position:
            continue
        anomalies = grid.anomalies_at(neighbor)
        if _SUPERNOVA in anomalies or _NEBULA in anomalies:
            continue
        if _ASTEROID in anomalies and not has_antimass:
            continue
        system = state.systems.get(neighbor)
        if system is None or _other_ships(system, player_id):
            continue
        if _has_presence(system, player_id):
            result.append(neighbor)
    return result


def _take(system: SystemState, zone: str, player_id: str, base_type: str, count: int) -> int:
    """Zdejmuje ``count`` jednostek ze strefy; zwraca liczbę PRZED zdjęciem (do uszkodzeń)."""
    if zone == "space":
        units = system.space_units.get(player_id, {})
    else:
        units = system.planet_units.get(zone, {}).get(player_id, {})
    before = units.get(base_type, 0)
    left = before - count
    if left > 0:
        units[base_type] = left
    else:
        units.pop(base_type, None)
    if not units:
        if zone == "space":
            system.space_units.pop(player_id, None)
        else:
            system.planet_units.get(zone, {}).pop(player_id, None)
    return before


def _put(system: SystemState, player_id: str, base_type: str, count: int) -> None:
    by_type = system.space_units.setdefault(player_id, {})
    by_type[base_type] = by_type.get(base_type, 0) + count


def _transfer(
    src: SystemState,
    zone: str,
    dest: SystemState,
    player_id: str,
    base_type: str,
    count: int,
) -> None:
    """Przenosi jednostki (z uszkodzeniami) do PRZESTRZENI systemu docelowego."""
    before = _take(src, zone, player_id, base_type, count)
    _put(dest, player_id, base_type, count)
    move_damage(src, zone, dest, "space", player_id, base_type, count, before)


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
) -> tuple[GameState, RetreatResult]:
    """Wycofuje jednostki gracza z ``position`` do ``destination`` (O5/O6).

    ``cargo`` = jawny ładunek (strefa ``"space"`` albo planeta kontrolowana w aktywnym
    systemie); ``None`` = ładunek domyślny (``_auto_cargo``). ``token_pool`` = pula na arkuszu,
    z której idzie żeton, gdy rezerwa jest pusta (``TOKEN_POOLS``; ``None`` = kolejność domyślna).

    Raises:
        ValueError: Niedozwolony cel, zły ładunek (przekroczona pojemność, porzucanie ładunku
            przy wolnej pojemności, planeta nie gracza), zła pula żetonów.
    """
    if destination not in retreat_destinations(state, grid, position, player_id):
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
        unit = resolve_unit_variant(registry, faction, techs, base_type)
        if is_space_unit(base_type) and unit is not None and (unit.move_value or 0) > 0:
            movers[base_type] = count
        elif base_type in _CARGO_BASE_TYPES:
            space_cargo[base_type] = count

    capacity = sum(
        _capacity_provided(registry, faction, techs, bt) * n for bt, n in movers.items()
    )
    cost = {bt: _capacity_used(registry, faction, techs, bt) for bt in _CARGO_BASE_TYPES}

    if cargo is None:
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
    if used > capacity:
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
    if any(cost.get(bt, 1) <= free for bt in left_behind):
        raise ValueError(
            "Fighters and ground forces in space cannot be left behind while the "
            "retreating ships still have free capacity."
        )

    new_state = state.clone()
    src = new_state.systems[position]
    dest = new_state.systems[destination]
    result = RetreatResult()
    for base_type, count in movers.items():
        _transfer(src, "space", dest, player_id, base_type, count)
        result.moved[base_type] = result.moved.get(base_type, 0) + count
    for item in chosen:
        _transfer(src, item.from_zone, dest, player_id, item.base_type, item.count)
        result.moved[item.base_type] = result.moved.get(item.base_type, 0) + item.count
    # O5: ładunek z przestrzeni, którego nie dało się zabrać, jest usuwany.
    for base_type, count in left_behind.items():
        _take(src, "space", player_id, base_type, count)
        set_damaged(
            src, "space", player_id, base_type, damaged_count(src, "space", player_id, base_type)
        )
        result.removed[base_type] = count

    # O6: żeton dowodzenia w systemie docelowym (tylko gdy coś się wycofało, bez duplikatu).
    if result.moved and player_id not in dest.command_tokens:
        owner = new_state.players.get(player_id)
        if owner is not None:
            if owner.cc_reinf > 0:
                owner.cc_reinf -= 1
                result.token_from = "reinforcements"
            else:
                pools = [token_pool] if token_pool is not None else list(TOKEN_POOLS)
                if token_pool is not None and getattr(owner, TOKEN_POOLS[token_pool]) <= 0:
                    raise ValueError(f"Your {token_pool} pool has no command token.")
                for pool in pools:
                    attr = TOKEN_POOLS[pool]
                    if getattr(owner, attr) > 0:
                        setattr(owner, attr, getattr(owner, attr) - 1)
                        result.token_from = pool
                        break
            if result.token_from is not None:
                dest.command_tokens.append(player_id)
                result.token_placed = True
    return new_state, result
