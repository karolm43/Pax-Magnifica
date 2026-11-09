"""Kolory graczy z assetów AsyncTI4 (katalog ``config.PLAYER_COLORS_DIR``).

Źródłem jest zrzut danych AsyncTI4 (solid / split / gradient) — zero hardkodowania.
Moduł dostarcza:
- listę kanonicznych aliasów (np. ``"lgy"``, ``"splitred"``, ``"rbw"``),
- normalizację dowolnej nazwy/aliasu do aliasu kanonicznego (``"white"`` → ``"lgy"``),
  bo grafiki jednostek i żetonów nazywają się wg aliasu (``units/lgy_gf.png``).

Czysty moduł ``core`` (bez FastAPI); wynik jest cache'owany.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from src import config

# Kolejność plików = kolejność kategorii w palecie (zwykłe → dwukolorowe → gradienty).
_COLOR_FILES: tuple[str, ...] = ("solidColors.json", "splitColors.json", "gradientColors.json")


@dataclass(frozen=True)
class PlayerColorDef:
    """Definicja koloru gracza: alias kanoniczny, nazwa i wszystkie nazwy zastępcze."""

    alias: str
    name: str
    aliases: tuple[str, ...]


@lru_cache(maxsize=1)
def load_player_colors(colors_dir: Path | None = None) -> tuple[PlayerColorDef, ...]:
    """Wczytuje kolory z plików AsyncTI4 w stałej kolejności (brak pliku → pomijany)."""
    base = colors_dir or config.PLAYER_COLORS_DIR
    result: list[PlayerColorDef] = []
    for filename in _COLOR_FILES:
        path = base / filename
        if not path.is_file():
            continue
        entries = json.loads(path.read_text(encoding="utf-8"))
        for entry in entries:
            alias = str(entry["alias"])
            names = {alias, str(entry.get("name", alias)), *map(str, entry.get("aliases", []))}
            result.append(
                PlayerColorDef(
                    alias=alias,
                    name=str(entry.get("name", alias)),
                    aliases=tuple(sorted(names)),
                )
            )
    return tuple(result)


@lru_cache(maxsize=1)
def _lookup() -> dict[str, str]:
    """Mapa dowolna-nazwa → alias kanoniczny (pierwszy wpis wygrywa przy kolizji)."""
    lookup: dict[str, str] = {}
    for definition in load_player_colors():
        for key in definition.aliases:
            lookup.setdefault(key, definition.alias)
    return lookup


def canonical_color(color: str) -> str:
    """Zwraca alias kanoniczny koloru; nieznany kolor wraca bez zmian (walidacja go odrzuci)."""
    return _lookup().get(color, color)


def all_color_aliases() -> list[str]:
    """Wszystkie kanoniczne aliasy kolorów w kolejności palety."""
    return [definition.alias for definition in load_player_colors()]
