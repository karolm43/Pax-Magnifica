"""HexGrid — model topologiczny mapy na współrzędnych kubicznych.

Mapa Twilight Imperium to układ heksagonalnych pierścieni wokół systemu
centralnego (Mecatol Rex). AsyncTI4 koduje pozycje jako napisy ``RRP``:
``RR`` to numer pierścienia (``00`` = centrum, ``01`` = pierwszy pierścień, ...),
``P`` to indeks pozycji w pierścieniu (1..6*ring). Ten moduł przekłada ten
format na kanoniczne współrzędne kubiczne ``(q, r, s)`` spełniające ``q+r+s=0``,
i buduje graf sąsiedztwa z obsługą tuneli czasoprzestrzennych (wormhole)
oraz anomalii.

Odległość bazowa (spec):

    d(A, B) = (|qA-qB| + |rA-rB| + |sA-sB|) / 2
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

# Sześć kierunków sąsiedztwa w kostce (pointy-top), kolejność zgodna
# z kierunkiem "w prawo-górę" i dalej zgodnie z ruchem wskazówek zegara.
_CUBE_DIRECTIONS: tuple[tuple[int, int, int], ...] = (
    (+1, -1, 0),
    (+1, 0, -1),
    (0, +1, -1),
    (-1, +1, 0),
    (-1, 0, +1),
    (0, -1, +1),
)

# Anomalia bezwarunkowo nieprzejezdna dla ruchu (patrz docs/RULES.md 1.3).
# UWAGA: nieprzejezdność dotyczy LOGIKI RUCHU, nie sąsiedztwa. Sąsiedztwo
# geometryczne istnieje nawet dla supernowej (potrzebne dla efektów adjacency).
_IMPASSABLE_ANOMALY = "SUPERNOVA"


@dataclass(frozen=True)
class _PlacedSystem:
    """Metadane systemu umieszczonego na mapie."""

    system_id: str
    hex: Hex
    anomalies: frozenset[str]


@dataclass(frozen=True)
class Hex:
    """Współrzędna kubiczna pojedynczego heksa."""

    q: int
    r: int
    s: int

    def __post_init__(self) -> None:
        if self.q + self.r + self.s != 0:
            raise ValueError(
                f"Invalid cube coordinate: q+r+s != 0 ({self.q},{self.r},{self.s})"
            )

    def distance(self, other: Hex) -> int:
        """Odległość heksagonalna (kubiczna) do innego heksa."""
        return (
            abs(self.q - other.q)
            + abs(self.r - other.r)
            + abs(self.s - other.s)
        ) // 2

    def neighbors(self) -> list[Hex]:
        """Sześciu geometrycznych sąsiadów heksa."""
        return [
            Hex(self.q + dq, self.r + dr, self.s + ds)
            for dq, dr, ds in _CUBE_DIRECTIONS
        ]


def position_to_hex(position: str) -> Hex:
    """Przelicza pozycję AsyncTI4 (``RRP``) na współrzędną kubiczną.

    Centrum (``000``) to ``(0, 0, 0)``. Pozycje w pierścieniu ``n`` są
    rozmieszczone wokół centrum: zaczynając od wierzchołka i idąc wzdłuż
    sześciu krawędzi sześciokąta o promieniu ``n``.

    Args:
        position: Napis pozycji, np. ``"000"``, ``"101"``, ``"312"``.

    Returns:
        Współrzędna kubiczna heksa.

    Raises:
        ValueError: Gdy format pozycji jest niepoprawny.
    """
    if len(position) != 3 or not position.isdigit():
        raise ValueError(f"Invalid position format (expected 'RPP'): {position!r}")

    # Format AsyncTI4: pierwsza cyfra = pierścień, dwie ostatnie = indeks pozycji.
    ring = int(position[0])
    index = int(position[1:])

    if ring == 0:
        return Hex(0, 0, 0)

    # Pozycje w AsyncTI4 numerowane są od 1. Indeks 0-bazowy wokół pierścienia.
    idx = index - 1
    positions_in_ring = 6 * ring

    # Punkt startowy pierscienia: ruszamy "ring" krokow w kierunku 4,
    # potem obchodzimy sześć krawędzi po "ring" kroków każda.
    cube = _scale_direction(4, ring)
    hexes: list[Hex] = []
    for side in range(6):
        for _ in range(ring):
            hexes.append(Hex(*cube))
            dq, dr, ds = _CUBE_DIRECTIONS[side]
            cube = (cube[0] + dq, cube[1] + dr, cube[2] + ds)

    idx %= positions_in_ring
    return hexes[idx]


def _scale_direction(direction_index: int, factor: int) -> tuple[int, int, int]:
    """Mnoży kierunek kubiczny przez skalar."""
    dq, dr, ds = _CUBE_DIRECTIONS[direction_index]
    return (dq * factor, dr * factor, ds * factor)


class HexGrid:
    """Graf topologiczny mapy: heksy, sąsiedztwo, wormhole, anomalie."""

    def __init__(self) -> None:
        self._graph: nx.Graph[str] = nx.Graph()
        # Rejestr systemow umieszczonych na mapie: pozycja -> metadane.
        self._systems: dict[str, _PlacedSystem] = {}
        # Wormhole: typ -> zbior pozycji, ktore go zawieraja.
        self._wormholes: dict[str, set[str]] = {}
        # Wormhole z ŻETONÓW położonych w trakcie gry (np. Gamma Wormhole z eksploracji):
        # typ -> pozycje. Osobno od wbudowanych, żeby Undo/Redo dawało spójną mapę.
        self._token_wormholes: dict[str, set[str]] = {}
        # Portale The Fracture (RULES.md 50): pozycje z żetonem ingress i z egressem.
        # Każdy ingress sąsiaduje z każdym egressem (ingress–ingress i egress–egress NIE).
        self._ingress: set[str] = set()
        self._egress: set[str] = set()
        # Kafle wymienione w trakcie gry (Nova Seed, ``core/tile_swap``): pozycja -> kafel z
        # układu mapy sprzed wymiany - powrót przy Undo.
        self.tile_originals: dict[str, str] = {}

    # --- Umieszczanie systemów -----------------------------------------

    def remove_system(self, position: str) -> None:
        """Usuwa system z pozycji (np. gdy Undo cofnęło wejście The Fracture do gry)."""
        if position not in self._systems:
            return
        del self._systems[position]
        if position in self._graph:
            self._graph.remove_node(position)
        for positions in self._wormholes.values():
            positions.discard(position)
        self._ingress.discard(position)
        self._egress.discard(position)

    def place_system(
        self,
        position: str,
        system_id: str,
        wormholes: list[str] | None = None,
        anomalies: set[str] | None = None,
        hex_override: Hex | None = None,
    ) -> None:
        """Umieszcza system na danej pozycji i aktualizuje krawędzie grafu.

        Args:
            position: Pozycja w formacie ``RRP``.
            system_id: Identyfikator systemu (z rejestru).
            wormholes: Lista typów wormholi w systemie (np. ``["ALPHA"]``).
            anomalies: Zbiór anomalii systemu (np. ``{"NEBULA"}``).
            hex_override: Jawna współrzędna kubiczna. Gdy podana, ma pierwszeństwo
                przed geometrycznym ``position_to_hex`` — używane przy budowie mapy
                z tabeli pozycji AsyncTI4 (``core.positions``), która jest źródłem
                prawdy orientacji planszy (patrz docs/RULES.md 2a).
        """
        hexc = hex_override if hex_override is not None else position_to_hex(position)
        self._systems[position] = _PlacedSystem(
            system_id=system_id,
            hex=hexc,
            anomalies=frozenset(anomalies or set()),
        )
        self._graph.add_node(position, hex=hexc, system_id=system_id)

        for wh in wormholes or []:
            self._wormholes.setdefault(wh, set()).add(position)

    def swap_system_tile(
        self,
        position: str,
        system_id: str,
        wormholes: list[str],
        anomalies: set[str],
    ) -> None:
        """Podmienia kafelek na pozycji (np. flip Wormhole Nexus 82a ↔ 82b), zachowując heks.

        Czyści stare wormhole pozycji, wstawia nowe i przebudowuje krawędzie.
        """
        data = self._systems.get(position)
        if data is None:
            return
        for positions in self._wormholes.values():
            positions.discard(position)
        self.place_system(
            position, system_id, wormholes=wormholes, anomalies=anomalies, hex_override=data.hex
        )
        self.build_edges()

    def build_edges(self) -> None:
        """Buduje krawędzie grafu: geometryczne sąsiedztwo + wormhole.

        Krawędzie reprezentują CZYSTE SĄSIEDZTWO (adjacency), niezależne od
        gracza i anomalii. Przejezdność (czy statek może wykonać ruch) to osobna
        warstwa logiki ruchu — patrz docs/RULES.md sekcja 1 i 3. Dlatego nawet
        systemy nieprzejezdne (supernova) zachowują krawędzie sąsiedztwa, bo wiele
        efektów gry działa „w sąsiednim systemie" niezależnie od możliwości ruchu.
        """
        self._graph.remove_edges_from(list(self._graph.edges))
        hex_to_pos = {
            data.hex: pos for pos, data in self._systems.items()
        }

        # Krawędzie geometryczne (sąsiedztwo mapy)
        for pos, data in self._systems.items():
            for neighbor_hex in data.hex.neighbors():
                neighbor_pos = hex_to_pos.get(neighbor_hex)
                if neighbor_pos is None:
                    continue
                self._graph.add_edge(pos, neighbor_pos, kind="adjacent")

        # Krawędzie wormhole (ten sam typ łączy wszystkie zawierające go systemy —
        # wbudowane w kafelek ORAZ z żetonów położonych w grze).
        combined: dict[str, set[str]] = {}
        for source in (self._wormholes, self._token_wormholes):
            for wh_type, positions in source.items():
                combined.setdefault(wh_type, set()).update(
                    p for p in positions if p in self._systems
                )
        for positions in combined.values():
            pos_list = sorted(positions)
            for i, a in enumerate(pos_list):
                for b in pos_list[i + 1 :]:
                    self._graph.add_edge(a, b, kind="wormhole")

        # Portale The Fracture: każdy ingress <-> każdy egress (R_fracture). Istniejąca
        # krawędź (np. geometryczna) zachowuje swój rodzaj.
        for ingress in sorted(p for p in self._ingress if p in self._systems):
            for egress in sorted(p for p in self._egress if p in self._systems):
                if ingress != egress and not self._graph.has_edge(ingress, egress):
                    self._graph.add_edge(ingress, egress, kind="portal")

    def sync_portals(self, ingress: set[str], egress: set[str]) -> None:
        """Ustawia pozycje ingress/egress i przebudowuje krawędzie, gdy się zmieniły."""
        if ingress != self._ingress or egress != self._egress:
            self._ingress = set(ingress)
            self._egress = set(egress)
            self.build_edges()

    def sync_token_wormholes(self, tokens: dict[str, list[str]]) -> None:
        """Ustawia wormhole z żetonów (pozycja → typy) i przebudowuje krawędzie, gdy się zmieniły.

        Wołane przy każdym odczycie stanu przez warstwę API; tanie, gdy nic się nie zmieniło.
        """
        wanted: dict[str, set[str]] = {}
        for position, types in tokens.items():
            for wh_type in types:
                wanted.setdefault(wh_type.upper(), set()).add(position)
        if wanted != self._token_wormholes:
            self._token_wormholes = wanted
            self.build_edges()

    # --- Zapytania ------------------------------------------------------

    def are_adjacent(self, pos_a: str, pos_b: str) -> bool:
        """Czy dwa systemy sąsiadują (geometrycznie lub przez wormhole)."""
        return bool(self._graph.has_edge(pos_a, pos_b))

    def link_kind(self, pos_a: str, pos_b: str) -> str | None:
        """Rodzaj krawędzi między systemami: ``adjacent`` / ``wormhole`` / ``portal`` / ``None``."""
        if not self._graph.has_edge(pos_a, pos_b):
            return None
        kind = self._graph.edges[pos_a, pos_b].get("kind")
        return str(kind) if kind is not None else None

    def neighbors(self, position: str) -> set[str]:
        """Zwraca pozycje sąsiadujące z danym systemem."""
        if position not in self._graph:
            return set()
        return set(self._graph.neighbors(position))

    def is_edge(self, position: str) -> bool:
        """Czy system leży na KRAWĘDZI planszy: któraś z 6 stron nie dotyka innego kafelka.

        R_objectives (Control the Borderlands): „on the edge of the game board". Liczy się
        tylko styk geometryczny (nie wormhole). Nieznana pozycja → ``False``.
        """
        data = self._systems.get(position)
        if data is None:
            return False
        occupied = {s.hex for s in self._systems.values()}
        return any(neighbor not in occupied for neighbor in data.hex.neighbors())

    def distance(self, pos_a: str, pos_b: str) -> int:
        """Odległość geometryczna (kubiczna) między pozycjami."""
        return self._systems[pos_a].hex.distance(self._systems[pos_b].hex)

    def anomalies_at(self, position: str) -> set[str]:
        """Zbiór anomalii w danym systemie (pusty, gdy brak lub nieznany)."""
        data = self._systems.get(position)
        if data is None:
            return set()
        return set(data.anomalies)

    def is_impassable(self, position: str) -> bool:
        """Czy system jest BEZWARUNKOWO nieprzejezdny dla ruchu (supernova).

        UWAGA: dotyczy wyłącznie logiki ruchu, NIE sąsiedztwa. System
        nieprzejezdny nadal ma krawędzie sąsiedztwa w grafie (patrz docs/RULES.md).
        Nieprzejezdność warunkowa (asteroid field zależny od technologii, nebula
        zależna od systemu aktywnego) jest rozstrzygana w warstwie ruchu, nie tutaj.
        """
        return _IMPASSABLE_ANOMALY in self.anomalies_at(position)

    def wormhole_positions(self, wormhole_type: str) -> set[str]:
        """Pozycje systemów z wormholem danego typu (wbudowane i z żetonów), np. ``"ALPHA"``."""
        found = set(self._wormholes.get(wormhole_type, set()))
        found |= self._token_wormholes.get(wormhole_type, set())
        return {p for p in found if p in self._systems}

    # --- Zapis / odtworzenie (plik partii, RULES.md 44.4) ---------------------------------

    def to_placements(self) -> list[dict[str, object]]:
        """Rozstawione kafelki jako dane JSON: system, heks, anomalie, wormhole KAFELKA.

        Pomija warstwy synchronizowane ze stanu gry (żetony wormhole, ingress/egress) —
        odtworzy je ``AppContext.current_grid`` przy pierwszym odczycie.
        """
        return [
            {
                "position": position,
                "system_id": placed.system_id,
                "hex": [placed.hex.q, placed.hex.r, placed.hex.s],
                "anomalies": sorted(placed.anomalies),
                "wormholes": sorted(
                    wh for wh, where in self._wormholes.items() if position in where
                ),
            }
            for position, placed in sorted(self._systems.items())
        ]

    @classmethod
    def from_placements(cls, placements: list[dict[str, object]]) -> HexGrid:
        """Odbudowuje siatkę z ``to_placements`` (z krawędziami). Raises: ``ValueError``."""
        grid = cls()
        for item in placements:
            q, r, s = (int(v) for v in item["hex"])  # type: ignore[attr-defined]
            grid.place_system(
                position=str(item["position"]),
                system_id=str(item["system_id"]),
                wormholes=[str(w) for w in item["wormholes"]],  # type: ignore[attr-defined]
                anomalies={str(a) for a in item["anomalies"]},  # type: ignore[attr-defined]
                hex_override=Hex(q, r, s),
            )
        grid.build_edges()
        return grid

    @property
    def positions(self) -> set[str]:
        """Zbiór wszystkich zajętych pozycji."""
        return set(self._systems)

    def coordinates(self, position: str) -> tuple[int, int, int]:
        """Współrzędne kubiczne ``(q, r, s)`` systemu na danej pozycji.

        Raises:
            KeyError: Gdy na pozycji nie umieszczono systemu.
        """
        data = self._systems[position]
        return (data.hex.q, data.hex.r, data.hex.s)

    def system_id_at(self, position: str) -> str:
        """Identyfikator systemu umieszczonego na danej pozycji.

        Raises:
            KeyError: Gdy na pozycji nie umieszczono systemu.
        """
        return self._systems[position].system_id

    def edges(self) -> list[tuple[str, str, str]]:
        """Lista krawędzi grafu jako ``(pos_a, pos_b, kind)``.

        ``kind`` to ``"adjacent"`` (sąsiedztwo geometryczne) lub ``"wormhole"``.
        Krawędzie są zwracane w stabilnym, posortowanym porządku.
        """
        result: list[tuple[str, str, str]] = []
        for a, b, data in self._graph.edges(data=True):
            kind = str(data.get("kind", "adjacent"))
            lo, hi = sorted((a, b))
            result.append((lo, hi, kind))
        return sorted(result)
