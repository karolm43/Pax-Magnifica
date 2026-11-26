"""Dostęp efektów kart do mapy: siatka, systemy bez wpisu w stanie, systemy domowe (RULES.md 53).

Efekt karty ma sygnaturę ``(state, registry, player_id, params)`` i nie dostaje siatki mapy
(``HexGrid``), a wiele kart akcji patrzy na całą planszę: „system bez statków innych graczy”,
„system sąsiadujący z Twoim statkiem”, „system z wormholem”. Warstwa API podpina więc
dostawcę siatki (``bind_grid_provider``, jak ``rules_hooks.bind_registry`` dla danych
statycznych); bez niego funkcje widzą tylko systemy, które mają wpis w ``state.systems``,
a sąsiedztwo jest puste (bezpieczny, węższy zakres).

Adjacency ≠ traversability: tu liczy się wyłącznie czyste sąsiedztwo grafu mapy.

Player-dependent adjacency (RULES.md 61.7, block I3) also lives here, as the ONE central point:
``extra_adjacent_for_player`` reads hook ``adjacency.extra_for_player`` (e.g. Creuss Quantum
Entanglement) and ``neighbors_for_player`` / ``are_adjacent_for_player`` combine the three layers
(map graph + tactical-action adjacency + the player's own). The map graph is never mutated.
"""

from __future__ import annotations

from collections.abc import Callable

from src.core import action_adjacency, rules_hooks
from src.core.faction_setup import OFF_BOARD_HOME
from src.core.game_state import GameState, SystemState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

GridProvider = Callable[[], HexGrid]

_PROVIDER: GridProvider | None = None


def bind_grid_provider(provider: GridProvider | None) -> None:
    """Podpina (albo odpina, ``None``) dostawcę bieżącej siatki mapy dla efektów kart."""
    global _PROVIDER
    _PROVIDER = provider


def bound_grid() -> HexGrid | None:
    """Bieżąca siatka mapy albo ``None``, gdy nikt jej nie podpiął."""
    return _PROVIDER() if _PROVIDER is not None else None


def board_positions(state: GameState) -> list[str]:
    """Pozycje wszystkich systemów na planszy: z siatki i ze stanu (posortowane)."""
    grid = bound_grid()
    positions = set(state.systems)
    if grid is not None:
        positions |= grid.positions
    return sorted(positions)


def system_id_at(state: GameState, position: str) -> str:
    """Id kafelka na pozycji (ze stanu, a gdy brak wpisu - z siatki); pusty napis, gdy nieznany."""
    system = state.systems.get(position)
    if system is not None:
        return system.system_id
    grid = bound_grid()
    if grid is not None and position in grid.positions:
        return grid.system_id_at(position)
    return ""


def ensure_system(state: GameState, position: str) -> SystemState:
    """System ze stanu albo nowy wpis (``system_id`` z siatki) - mutuje ``state`` (klon roboczy)."""
    system = state.systems.get(position)
    if system is None:
        system = SystemState(position=position, system_id=system_id_at(state, position))
        state.systems[position] = system
    return system


def adjacent_positions(position: str) -> set[str]:
    """Pozycje sąsiadujące (geometria + wormhole + portale) - pusty zbiór bez siatki."""
    grid = bound_grid()
    return grid.neighbors(position) if grid is not None else set()


def extra_adjacent_for_player(
    state: GameState, player_id: str, position: str, grid: HexGrid | None = None
) -> frozenset[str]:
    """Systems adjacent to ``position`` ONLY for ``player_id`` (layer 3, RULES.md 61.7).

    Union of hook FORBID ``adjacency.extra_for_player`` (ctx: ``position``, ``grid`` - the given
    grid or the bound one). A system is never adjacent to itself (R_adjacency rules-reference/2.1),
    so ``position`` is dropped. Hooks must return a symmetric relation.
    """
    if player_id not in state.players:
        return frozenset()
    found = rules_hooks.forbidden(
        rules_hooks.POINT_ADJACENCY_EXTRA_FOR_PLAYER, state, player_id,
        {"position": position, "grid": grid if grid is not None else bound_grid()},
    )
    return frozenset(found - {position})


def neighbors_for_player(
    state: GameState, grid: HexGrid, player_id: str, position: str
) -> set[str]:
    """Systems adjacent to ``position`` from ``player_id``'s point of view (RULES.md 61.7).

    Map graph (geometry + wormholes + portals) + tactical-action adjacency (``action_adjacency``,
    valid for everybody) + the player's own adjacency (``extra_adjacent_for_player``). Pure
    adjacency: traversability (anomalies, blockades, laws) is the caller's separate layer.
    """
    result = action_adjacency.neighbors(state, grid, position)
    result |= extra_adjacent_for_player(state, player_id, position, grid)
    result.discard(position)
    return result


def are_adjacent_for_player(
    state: GameState, grid: HexGrid, player_id: str, a: str, b: str
) -> bool:
    """Whether systems ``a`` and ``b`` are adjacent for ``player_id`` (all three layers)."""
    if a == b:
        return False
    if action_adjacency.are_adjacent(state, grid, a, b):
        return True
    return b in extra_adjacent_for_player(
        state, player_id, a, grid
    ) or a in extra_adjacent_for_player(state, player_id, b, grid)


def home_system_ids(state: GameState, registry: StaticDataRegistry) -> set[str]:
    """Id kafelków będących systemami domowymi graczy (także wyeliminowanych).

    Creuss i Crimson mają dom POZA planszą (RULES.md 17): bramę (``home_system`` frakcji)
    NIE liczymy jako domu - prawdziwy dom to wpis z ``OFF_BOARD_HOME``.
    R_elimination: dom wyeliminowanego gracza nadal jest domem dla efektów gry - tak samo jak
    ``card_targets_economy.home_planet_ids`` (Reactor Meltdown, Uprising), także gdy rekord
    eliminacji nie ma ``home_position`` (Mercenary Contract, Ghost Ship, Signal Jamming).
    """
    ids: set[str] = set()
    factions = [p.faction for p in state.players.values()]
    factions += [e.faction for e in state.eliminated_players]
    for faction_id in factions:
        faction = registry.factions.get(faction_id or "")
        if faction is None:
            continue
        if faction.id in OFF_BOARD_HOME:
            ids.add(OFF_BOARD_HOME[faction.id])
        elif faction.home_system:
            ids.add(faction.home_system)
    return ids


def home_positions(state: GameState, registry: StaticDataRegistry) -> set[str]:
    """Pozycje systemów domowych graczy przy stole (slot domowy lub kafelek domowy frakcji)."""
    positions: set[str] = set()
    for player in state.players.values():
        faction = registry.factions.get(player.faction or "")
        if faction is not None and faction.id in OFF_BOARD_HOME:
            continue  # slot trzyma bramę, nie dom
        if player.home_position:
            positions.add(player.home_position)
    # R_elimination: an eliminated player's home system remains a home system for game effects
    # (C_action_cards ghost-ship/2, signal-jamming/2).
    positions |= {e.home_position for e in state.eliminated_players if e.home_position}
    ids = home_system_ids(state, registry)
    positions |= {pos for pos, system in state.systems.items() if system.system_id in ids}
    return positions


def home_positions_by_player(
    state: GameState, registry: StaticDataRegistry
) -> dict[str, list[str]]:
    """Pozycje systemu domowego KAŻDEGO gracza osobno (``{player_id: [pozycje]}``).

    Ta sama logika co :func:`home_positions` (slot domowy albo kafelek domowy frakcji; dla
    Ghost/Crimson prawdziwy dom z ``OFF_BOARD_HOME``, nie brama), ale z podziałem na właściciela —
    np. żeby wiedzieć, czy walka toczy się w domu obrońcy.
    """
    result: dict[str, list[str]] = {}
    for pid, player in state.players.items():
        faction = registry.factions.get(player.faction or "")
        positions: set[str] = set()
        home_id = ""
        if faction is not None:
            home_id = OFF_BOARD_HOME.get(faction.id, faction.home_system or "")
        if player.home_position and (faction is None or faction.id not in OFF_BOARD_HOME):
            positions.add(player.home_position)
        if home_id:
            positions |= {
                pos for pos, system in state.systems.items() if system.system_id == home_id
            }
        result[pid] = sorted(positions)
    return result


def is_home_system(state: GameState, registry: StaticDataRegistry, position: str) -> bool:
    """Czy system na pozycji jest systemem domowym któregoś gracza przy stole."""
    return position in home_positions(state, registry) or (
        system_id_at(state, position) in home_system_ids(state, registry)
    )


def non_home_systems(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Pozycje prawdziwych systemów (znanych w rejestrze, bez hyperlane) poza domami graczy."""
    homes = home_positions(state, registry)
    ids = home_system_ids(state, registry)
    result: list[str] = []
    for position in board_positions(state):
        system_id = system_id_at(state, position)
        definition = registry.systems.get(system_id)
        if definition is None or (definition.name or "").strip().lower() == "hyperlane":
            continue
        if position in homes or system_id in ids:
            continue
        result.append(position)
    return result


def wormholes_at(state: GameState, registry: StaticDataRegistry, position: str) -> set[str]:
    """Typy wormholi w systemie: wydrukowane na kafelku + żetony położone w grze + wormhole
    jednostek (Hil Colish - ``unit_wormholes``)."""
    return set(wormhole_list(state, registry, position))


def wormhole_list(state: GameState, registry: StaticDataRegistry, position: str) -> list[str]:
    """Every wormhole in the system, one entry each (also two of the same type): printed on the
    tile, tokens in play, carried by units. Particle Synthesis counts "each wormhole" (62.19)."""
    definition = registry.systems.get(system_id_at(state, position))
    found = [wh.upper() for wh in (definition.wormholes if definition else [])]
    system = state.systems.get(position)
    if system is not None:
        found += [wh.upper() for wh in system.token_wormholes()]
    found += unit_wormholes(state).get(position, [])
    found += sorted(action_wormholes(state, position))
    return found


def action_wormholes(state: GameState, position: str) -> frozenset[str]:
    """Wormholes the ACTIVE player treats the system as having during their tactical action
    (hook FORBID ``system.action_wormholes`` - Lazax Gate Folding at Mecatol Rex)."""
    active = state.active_player_id
    if state.tactical_step is None or active is None or active not in state.players:
        return frozenset()
    return frozenset(t.upper() for t in rules_hooks.forbidden(
        rules_hooks.POINT_SYSTEM_ACTION_WORMHOLES, state, active, {"position": position}
    ))


def unit_wormholes_by_owner(state: GameState) -> list[tuple[str, str, str]]:
    """``(position, TYPE, owner)`` of every wormhole carried by units (hook FORBID
    ``board.unit_wormholes``, entries ``"<position>|<TYPE>"``) - Hil Colish's delta wormhole
    (RULES.md 62.19). Sorted by owner, then entry."""
    found: list[tuple[str, str, str]] = []
    for player_id in sorted(state.players):
        for entry in sorted(rules_hooks.forbidden(
            rules_hooks.POINT_BOARD_UNIT_WORMHOLES, state, player_id
        )):
            position, _, kind = str(entry).partition("|")
            if position and kind:
                found.append((position, kind.upper(), player_id))
    return found


def unit_wormholes(state: GameState) -> dict[str, list[str]]:
    """``{position: [TYPE]}`` wormholes carried by units (``unit_wormholes_by_owner``)."""
    found: dict[str, list[str]] = {}
    for position, kind, _owner in unit_wormholes_by_owner(state):
        found.setdefault(position, []).append(kind)
    return found


def placed_wormholes(state: GameState) -> dict[str, list[str]]:
    """``{position: [TYPE]}`` of every wormhole put into play on top of the tiles: tokens, the
    Ion Storm side and unit wormholes - the ONE input of ``HexGrid.sync_token_wormholes``."""
    result = {pos: s.token_wormholes() for pos, s in state.systems.items() if s.token_wormholes()}
    for position, types in unit_wormholes(state).items():
        result[position] = [*result.get(position, []), *types]
    return result
