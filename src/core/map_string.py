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

from src.core.faction_setup import OFF_BOARD_HOME
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

        tile_id = resolve_tile_id(tile.tile_id, registry)
        system = registry.systems.get(tile_id) if tile_id is not None else None
        if system is None:
            continue  # Kafelek spoza aktywnych źródeł — pomijamy (endpointy zgłaszają 422).
        grid.place_system(
            position=tile.position,
            system_id=system.id,
            wormholes=list(system.wormholes),
            anomalies=set(system.anomalies),
            hex_override=hex_coord,
        )

    grid.build_edges()
    return grid


def resolve_tile_id(token: str, registry: StaticDataRegistry) -> str | None:
    """Tłumaczy token map stringa na id systemu z rejestru (``None`` = nieznany kafelek).

    Map stringi z AsyncTI4 / generatorów (Milty) piszą kafelki różnie: ``8`` zamiast
    ``08``, ``96`` dla dwustronnego kafelka ``96a``/``96b``, aliasy tekstowe (``nekro``).
    Kolejność prób: dokładne id → bez/z wiodącym zerem → alias (bez wielkości liter) →
    strona ``a`` kafelka dwustronnego (strona startowa, np. Firmament przed Obsidian).
    """
    systems = registry.systems
    if token in systems:
        return token
    stripped = token.lstrip("0") or "0"
    for candidate in (stripped, stripped.zfill(2)):
        if candidate in systems:
            return candidate
    lowered = token.lower()
    for sid, system in systems.items():
        if lowered in (alias.lower() for alias in system.aliases):
            return sid
    if f"{stripped}a" in systems:
        return f"{stripped}a"
    return None


def unknown_tiles(map_string: str, registry: StaticDataRegistry) -> list[str]:
    """Tokeny map stringa, których nie ma w rejestrze (pomijając puste ``0``)."""
    return [
        token
        for token in map_string.split()
        if token != _EMPTY_TOKEN and resolve_tile_id(token, registry) is None
    ]


def home_faction_by_tile(registry: StaticDataRegistry) -> dict[str, str]:
    """Kafelek domowy → frakcja: dom z danych frakcji oraz prawdziwy dom off-board.

    Creuss/Crimson mają w danych bramę (17 / 94); map string z AsyncTI4 może zawierać
    zarówno bramę, jak i prawdziwy dom (51 / 118) — oba wskazują tę samą frakcję.
    """
    result: dict[str, str] = {}
    for faction in registry.factions.values():
        # Niegrywalne (Obsidian — druga strona kafelka Firmamentu) nie siadają przy stole.
        if faction.home_system and faction.is_playable:
            result.setdefault(faction.home_system, faction.id)
    for faction_id, real_home in OFF_BOARD_HOME.items():
        if faction_id in registry.factions:
            result.setdefault(real_home, faction_id)
    return result


@dataclass(frozen=True)
class MapSeat:
    """Miejsce gracza wykryte w map stringu: pusty róg domowy albo kafelek domowy frakcji."""

    position: str
    faction_id: str | None


def map_seats(map_string: str, registry: StaticDataRegistry) -> list[MapSeat]:
    """Miejsca graczy z map stringa, w kolejności pozycji (zgodnie z ruchem zegara).

    Miejsce = pusty róg domowy (``0`` na rogu pierścienia 3) albo pozycja, na której
    string kładzie kafelek domowy frakcji (gotowa mapa z draftu, np. Milty). Wtedy
    ``faction_id`` mówi, kto tam siedzi (docs/RULES.md 2a).
    """
    homes = home_faction_by_tile(registry)
    seats: list[MapSeat] = []
    for tile in parse_map_string(map_string, include_center=False):
        if tile.is_home_slot:
            seats.append(MapSeat(position=tile.position, faction_id=None))
            continue
        tile_id = resolve_tile_id(tile.tile_id, registry)
        if tile_id is not None and tile_id in homes:
            seats.append(MapSeat(position=tile.position, faction_id=homes[tile_id]))
    return seats


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
