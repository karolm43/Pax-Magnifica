"""Źródła danych TI4: priorytet i walidacja manifestu aktywnych źródeł.

Priorytet ``thunders_edge > pok > codex4..1 > base`` pochodzi z RULES.md 14.
Moduł jest czysty poza ``known_source_ids`` (odczyt ``sources.json``).
"""

from __future__ import annotations

import json
from collections.abc import Collection, Iterable
from pathlib import Path

from src import config

# Od najwyższego do najniższego priorytetu (RULES.md 14).
SOURCE_PRIORITY: tuple[str, ...] = (
    "thunders_edge",
    "pok",
    "codex4",
    "codex3",
    "codex2",
    "codex1",
    "base",
)


# Fanowskie warianty TALII AGEND (wybierane w setupie gry, nie w manifeście źródeł).
# Wariant -> alias talii w katalogu. ``standard`` (None) = talia aktywnych źródeł (PoK/TE).
# Źródła fanowskie (``AGENDA_VARIANT_SOURCES``) ładują się WYŁĄCZNIE dla kart agend i talii
# agend - reszta ich danych (jednostki, technologie, karty akcji…) pozostaje nieaktywna.
AGENDA_STANDARD = "standard"
AGENDA_VARIANT_DECKS: dict[str, str | None] = {
    AGENDA_STANDARD: None,
    "absol": "agendas_absol",
}
AGENDA_VARIANT_SOURCES: frozenset[str] = frozenset({"absol"})


class UnknownSourcesError(ValueError):
    """Manifest aktywnych źródeł zawiera identyfikatory nieobecne w ``sources.json``."""

    def __init__(self, unknown: Iterable[str]) -> None:
        self.unknown: list[str] = sorted(set(unknown))
        super().__init__(
            "Unknown source identifiers in enabled sources: " + ", ".join(self.unknown)
        )


def source_rank(source: str) -> int:
    """Ranga źródła: mniejsza = wyższy priorytet; źródło spoza listy dostaje najniższą."""
    try:
        return SOURCE_PRIORITY.index(source)
    except ValueError:
        return len(SOURCE_PRIORITY)


def known_source_ids(path: Path = config.SOURCES_PATH) -> frozenset[str]:
    """Zwraca identyfikatory źródeł zdefiniowanych w ``sources.json``."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw if isinstance(raw, list) else [raw]
    return frozenset(
        entry["source"]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("source"), str)
    )


def validate_enabled_sources(enabled: Iterable[str], known: Collection[str]) -> None:
    """Sprawdza, że każde aktywne źródło jest znane.

    Raises:
        UnknownSourcesError: Z posortowaną listą nieznanych identyfikatorów.
    """
    unknown = [source for source in enabled if source not in known]
    if unknown:
        raise UnknownSourcesError(unknown)
