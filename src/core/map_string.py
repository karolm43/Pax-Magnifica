"""Parser map stringa AsyncTI4 — ciąg ID kafelków → rozmieszczenie na pozycjach.

Format (patrz docs/RULES.md 2a): ciąg identyfikatorów kafelków oddzielonych
spacjami. Kafelki przypisywane są po kolei do pozycji ``101, 102, ..., 201, ...``
(pierścień po pierścieniu). ``0`` oznacza puste miejsce (pomijane, ale zajmuje
pozycję w sekwencji). Mecatol Rex jest domyślny w centrum ``000`` i zwykle nie
występuje w stringu.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from src.core.hex_grid import HexGrid
from src.core.home_slots import HOME_SLOT_COLORS_6P, home_slot_color
from src.core.positions import load_positions, ordered_positions
from src.core.registry import StaticDataRegistry

# Identyfikator systemu Mecatol Rex (centrum każdej mapy).
MECATOL_SYSTEM_ID = "18"

# Token pustego miejsca w map stringu.
_EMPTY_TOKEN = "0"

# Pseudo-identyfikator systemu dla slotu domowego (brak kafelka — wybór frakcji).
HOME_SLOT_SYSTEM_ID = "__home__"


@dataclass(frozen=True)
class PlacedTile:
    """Kafelek lub slot przypisany do pozycji na planszy."""

    position: str
    tile_id: str
    # Gdy pozycja to slot domowy gracza (pusty róg pierścienia): kolor gracza.
    home_color: str | None = None

    @property
    def is_home_slot(self) -> bool:
        """Czy to slot domowy (kolorowy róg bez kafelka systemu)."""
        return self.home_color is not None


def parse_map_string(
    map_string: str,
    *,
    include_center: bool = True,
    alias_path: str | Path | None = None,
) -> list[PlacedTile]:
    """Parsuje map string na listę kafelków przypisanych do pozycji.

    Args:
        map_string: Ciąg ID kafelków oddzielonych białymi znakami, np.
            ``"72 66 77 ... 41 40"``. ``0`` = puste miejsce (pomijane).
        include_center: Gdy ``True`` (domyślnie) i string nie zaczyna się od ID
            centrum, Mecatol Rex (``18``) jest automatycznie dodawany na pozycji
            ``000``. Ustaw ``False``, by nie dodawać centrum.
        alias_path: Opcjonalna ścieżka do pliku alias pozycji (dla testów).

    Returns:
        Lista ``PlacedTile`` w kolejności pozycji (bez pustych miejsc).

    Raises:
        ValueError: Gdy string jest pusty lub ma więcej kafelków niż dostępnych
            pozycji w aliasie.
    """
    tokens = map_string.split()
    if not tokens:
        raise ValueError("Empty map string.")

    positions = ordered_positions(alias_path)
    if len(tokens) > len(positions):
        raise ValueError(
            f"Map string has {len(tokens)} tiles, but only "
            f"{len(positions)} positions are available "
            f"(add support for further rings in the alias)."
        )

    placed: list[PlacedTile] = []
    if include_center:
        placed.append(PlacedTile(position="000", tile_id=MECATOL_SYSTEM_ID))

    for token, position in zip(tokens, positions, strict=False):
        if token == _EMPTY_TOKEN:
            # Puste "0" na rogu domowym = slot gracza (kolorowy heks bez kafelka).
            # Pozostałe puste pozycje po prostu pomijamy.
            color = home_slot_color(position)
            if color is not None:
                placed.append(
                    PlacedTile(
                        position=position,
                        tile_id=HOME_SLOT_SYSTEM_ID,
                        home_color=color,
                    )
                )
            continue
        placed.append(PlacedTile(position=position, tile_id=token))

    return placed


def build_grid_from_map_string(
    map_string: str,
    registry: StaticDataRegistry,
    *,
    include_center: bool = True,
    alias_path: str | Path | None = None,
) -> HexGrid:
    """Buduje ``HexGrid`` z map stringa, używając danych systemów z rejestru.

    Współrzędne pochodzą z tabeli pozycji AsyncTI4 (``core.positions``), a wormhole
    i anomalie z rejestru. Kafelki nieobecne w rejestrze (np. homebrew poza aktywnymi
    źródłami) są pomijane — graf zawiera tylko znane systemy.

    Args:
        map_string: Map string AsyncTI4.
        registry: Rejestr statycznych danych (wormhole, anomalie, metadane).
        include_center: Czy automatycznie dodać Mecatol Rex w centrum.
        alias_path: Opcjonalna ścieżka do pliku alias pozycji (dla testów).

    Returns:
        Zbudowany graf mapy z policzonymi krawędziami.
    """
    coords = load_positions(alias_path)
    grid = HexGrid()

    for tile in parse_map_string(
        map_string, include_center=include_center, alias_path=alias_path
    ):
        hex_coord = coords.get(tile.position)
        if hex_coord is None:
            continue  # Pozycja spoza aliasu — pomijamy (bezpieczeństwo).

        if tile.is_home_slot:
            # Slot domowy: węzeł bez systemu (kafelek zależy od wyboru frakcji).
            grid.place_system(
                position=tile.position,
                system_id=HOME_SLOT_SYSTEM_ID,
                hex_override=hex_coord,
            )
            continue

        system = registry.systems.get(tile.tile_id)
        if system is None:
            continue  # Kafelek spoza aktywnych źródeł — pomijamy.
        grid.place_system(
            position=tile.position,
            system_id=system.id,
            wormholes=list(system.wormholes),
            anomalies=set(system.anomalies),
            hex_override=hex_coord,
        )

    grid.build_edges()
    return grid


def random_map_string(registry: StaticDataRegistry, rng: random.Random) -> str:
    """Losowy map string 6-osobowy: 30 kafelków (blue+red) na pierścieniach 1–3.

    Home sloty (rogi pierścienia 3) zachowują ``"0"`` — frakcje wchodzą tam samy przy setupie.
    Kafelki Fracture i Mecatol Rex są wykluczone z puli losowania.
    """
    usable = sorted(
        sid
        for sid, s in registry.systems.items()
        if s.tile_back in ("blue", "red") and sid != MECATOL_SYSTEM_ID and not s.is_fracture
    )
    # Pierścienie 1–3 = pierwsze 36 pozycji; home sloty to rogi pierścienia 3.
    positions_6p = ordered_positions()[:36]
    non_home = [p for p in positions_6p if p not in HOME_SLOT_COLORS_6P]
    tiles = rng.sample(usable, min(len(non_home), len(usable)))
    rng.shuffle(tiles)
    tile_iter = iter(tiles)
    tokens = []
    for pos in positions_6p:
        if pos in HOME_SLOT_COLORS_6P:
            tokens.append(_EMPTY_TOKEN)
        else:
            tokens.append(next(tile_iter, _EMPTY_TOKEN))
    return " ".join(tokens)
