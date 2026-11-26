"""Sąsiedztwo graczy (Neighbors) — CZYSTA logika nad ``GameState`` + ``HexGrid``.

Reguła TI4 (źródło: tirules2.com → ``docs/rules_tirules/R_neighbors.md``,
RULES.md 2):

    Dwóch graczy jest sąsiadami (neighbors), jeśli OBAJ mają jednostkę lub
    kontrolują planetę w TYM SAMYM systemie. Są sąsiadami również wtedy, gdy obaj
    mają jednostkę lub kontrolują planetę w systemach SĄSIADUJĄCYCH ze sobą
    (sąsiedztwo przez wormhole wliczone — ``HexGrid.are_adjacent``).

To POJĘCIE GRACZA (kto z kim graniczy), odrębne od statycznego sąsiedztwa mapy
(``HexGrid``): sąsiedztwo systemów jest wejściem, sąsiedztwo graczy — wynikiem.

Funkcje są czyste (bez HTTP, bez mutacji stanu): liczą zbiór ``player_id``
sąsiadów dla danego gracza. Warstwa serializacji (``api/web_data.py``) mapuje
``player_id`` na kolory, których oczekuje viewer.

Ograniczenia (świadome, zgodne z RULES.md 2 — adjacency zweryfikowane częściowo):
* sąsiedztwo systemów bierzemy z ``HexGrid`` (geometria + wormhole) plus sąsiedztwo
  z bieżącej akcji taktycznej (``action_adjacency``: SCC, Lazax Gate Folding — F_winnu:
  „the Winnu player may become neighbors…”); hyperlanes nie są modelowane.
* player-dependent adjacency (RULES.md 61.7, ``board_graph.extra_adjacent_for_player``): A in X
  and B in Y are neighbors when X, Y are adjacent for A OR for B (F_creuss Quantum
  Entanglement: "the Creuss player and that player are neighbors") - the relation stays symmetric.
"""

from __future__ import annotations

from src.core import action_adjacency, board_graph
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid


def _players_present(state: GameState) -> dict[str, set[str]]:
    """Mapa ``pozycja systemu -> zbiór player_id obecnych w tym systemie``.

    „Obecny" = ma jednostkę w przestrzeni, jednostkę na planecie LUB kontroluje
    planetę (``planet_owners``) — dokładnie definicja z R_neighbors. Puste wpisy
    (0 jednostek) nie liczą się jako obecność.
    """
    presence: dict[str, set[str]] = {}
    for position, system in state.systems.items():
        here: set[str] = set()
        # Jednostki w przestrzeni.
        for owner, by_type in system.space_units.items():
            if any(count > 0 for count in by_type.values()):
                here.add(owner)
        # Jednostki na planetach.
        for by_player in system.planet_units.values():
            for owner, by_type in by_player.items():
                if any(count > 0 for count in by_type.values()):
                    here.add(owner)
        # Kontrola planet (bez względu na stojące jednostki).
        here.update(system.planet_owners.values())
        # R_neutral_units: „there is no neutral player” - jednostki neutralne (Pirate Contract,
        # Thunder's Edge) nie są niczyim sąsiadem; obecność liczą tylko gracze.
        here &= set(state.players)
        if here:
            presence[position] = here
    return presence


def _extra_map(state: GameState, presence: dict[str, set[str]]) -> dict[str, frozenset[str]]:
    """Dodatkowe sąsiedztwo z akcji taktycznej, liczone raz dla systemów z obecnością."""
    if state.tactical_step is None:
        return {}
    found = {pos: action_adjacency.extra_adjacent(state, pos) for pos in presence}
    return {pos: extra for pos, extra in found.items() if extra}


def _player_extra(
    state: GameState, grid: HexGrid, presence: dict[str, set[str]]
) -> dict[tuple[str, str], frozenset[str]]:
    """``{(player_id, position): systems adjacent only for that player}`` where it is present."""
    found: dict[tuple[str, str], frozenset[str]] = {}
    for position, here in presence.items():
        for owner in here:
            extra = board_graph.extra_adjacent_for_player(state, owner, position, grid)
            if extra:
                found[(owner, position)] = extra
    return found


def _player_cuts(
    state: GameState, grid: HexGrid, presence: dict[str, set[str]]
) -> dict[tuple[str, str], frozenset[str]]:
    """``{(player_id, position): systems NOT adjacent for that player}`` (layer 4, Void Tether)."""
    found: dict[tuple[str, str], frozenset[str]] = {}
    for position, here in presence.items():
        for owner in here:
            cut = board_graph.cut_adjacent_for_player(state, owner, position, grid)
            if cut:
                found[(owner, position)] = cut
    return found


def _adjacent(grid: HexGrid, extra: dict[str, frozenset[str]], a: str, b: str) -> bool:
    if grid.are_adjacent(a, b):
        return True
    return b in extra.get(a, frozenset()) or a in extra.get(b, frozenset())


def neighbors_of(player_id: str, state: GameState, grid: HexGrid) -> set[str]:
    """Zbiór ``player_id`` graczy będących sąsiadami ``player_id`` (bez niego).

    Sąsiedztwo: wspólna obecność w tym samym systemie lub w systemach wzajemnie
    sąsiednich (graf mapy + akcja taktyczna + sąsiedztwo zależne od gracza, RULES.md 61.7).
    Gracz nigdy nie jest własnym sąsiadem. Pusty stan / brak obecności → pusty zbiór.
    """
    return neighbors_by_player(state, grid).get(player_id, set())


def neighbors_by_player(
    state: GameState, grid: HexGrid
) -> dict[str, set[str]]:
    """Sąsiedzi dla KAŻDEGO gracza: ``{player_id: {sąsiad_id, ...}}``.

    Liczy obecność raz i składa symetryczne relacje w jednym przejściu (tańsze niż
    ``neighbors_of`` per gracz). Relacja jest symetryczna: jeśli A jest sąsiadem B,
    to B jest sąsiadem A.
    """
    presence = _players_present(state)
    extra = _extra_map(state, presence)
    own_extra = _player_extra(state, grid, presence)
    cuts = _player_cuts(state, grid, presence)
    result: dict[str, set[str]] = {pid: set() for pid in state.players}

    def cut(owner: str, pos: str, far: str) -> bool:
        return far in cuts.get((owner, pos), frozenset())

    positions = list(presence.items())
    for i, (pos_a, here_a) in enumerate(positions):
        # Ten sam system: wszyscy obecni są wzajemnie sąsiadami.
        for owner in here_a:
            if owner in result:
                result[owner].update(here_a)
        # Systemy sąsiednie: obecni po obu stronach krawędzi.
        for pos_b, here_b in positions[i + 1 :]:
            if _adjacent(grid, extra, pos_a, pos_b):
                # Layer 4 (Void Tether): the pair is not neighbours across the cut edge only when
                # BOTH treat it as cut - the tether's owner keeps the adjacency (void-tether 1.1).
                for owner in here_a:
                    for peer in here_b:
                        if owner in result and peer in result and not (
                            cut(owner, pos_a, pos_b) and cut(peer, pos_b, pos_a)
                        ):
                            result[owner].add(peer)
                            result[peer].add(owner)
                continue
            # Player-dependent adjacency: the owner of the effect and everybody on the other side.
            sides = ((here_a, here_b, pos_a, pos_b), (here_b, here_a, pos_b, pos_a))
            for side, other, pos, far in sides:
                for owner in side:
                    if far in own_extra.get((owner, pos), frozenset()):
                        result[owner].update(other)
                        for peer in other:
                            result[peer].add(owner)

    # Gracz nie jest własnym sąsiadem.
    for pid, neigh in result.items():
        neigh.discard(pid)
    return result
