"""Czyste funkcje różnic i luk dla Audytora_Danych.

Wszystko tutaj jest CZYSTE (bez I/O poza ``load_expected_gaps``): różnice zbiorów
identyfikatorów, różnice tablic liczników (regresja względem baseline) oraz wykrywanie
luk źródeł kanonicznych z potwierdzonymi wyjątkami (``audit/expected_gaps.json``).
"""

from __future__ import annotations

import json
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from src import config

EXPECTED_GAPS_PATH: Path = config.AUDIT_DIR / "expected_gaps.json"
BASELINE_COUNTS_PATH: Path = config.AUDIT_DIR / "baseline_counts.json"


@dataclass(frozen=True)
class IdDiff:
    """Różnica dwóch zbiorów identyfikatorów (``extra`` tylko w lewym, ``missing`` w prawym)."""

    extra: frozenset[str]
    missing: frozenset[str]

    @property
    def is_empty(self) -> bool:
        return not self.extra and not self.missing


@dataclass(frozen=True)
class CountChange:
    """Zmiana licznika; ``None`` oznacza brak wpisu po danej stronie."""

    baseline: int | None
    current: int | None


@dataclass(frozen=True, order=True)
class CategorySourceGap:
    """Para (kategoria, źródło kanoniczne) bez ani jednego wpisu."""

    category: str
    source: str


def diff_sets(left: Iterable[str], right: Iterable[str]) -> IdDiff:
    """``extra = left \\ right``, ``missing = right \\ left``."""
    left_set = frozenset(left)
    right_set = frozenset(right)
    return IdDiff(extra=left_set - right_set, missing=right_set - left_set)


def diff_counts(
    baseline: Mapping[str, Mapping[str, int]],
    current: Mapping[str, Mapping[str, int]],
) -> dict[tuple[str, str], CountChange]:
    """Zwraca dokładnie pary (kategoria, źródło) o różnych licznikach (R6.5).

    Brak wpisu po jednej ze stron jest różnicą (``None``), więc wynik jest pusty
    wtedy i tylko wtedy, gdy obie tablice są równe.
    """
    keys: set[tuple[str, str]] = {
        (category, source)
        for table in (baseline, current)
        for category, row in table.items()
        for source in row
    }
    result: dict[tuple[str, str], CountChange] = {}
    for category, source in sorted(keys):
        old = baseline.get(category, {}).get(source)
        new = current.get(category, {}).get(source)
        if old != new:
            result[(category, source)] = CountChange(old, new)
    return result


def find_gaps(
    counts: Mapping[str, Mapping[str, int]],
    canonical_sources: Collection[str],
    expected: Collection[tuple[str, str]] = (),
) -> list[CategorySourceGap]:
    """Pary (kategoria, źródło kanoniczne) z licznikiem zero, minus potwierdzone wyjątki.

    Brak klucza źródła w wierszu kategorii liczy się jak zero (R6.2, R6.3).
    """
    allowed = set(expected)
    gaps = [
        CategorySourceGap(category, source)
        for category, row in counts.items()
        for source in canonical_sources
        if row.get(source, 0) == 0 and (category, source) not in allowed
    ]
    return sorted(gaps)


def load_expected_gaps(path: Path = EXPECTED_GAPS_PATH) -> frozenset[tuple[str, str]]:
    """Wczytuje potwierdzone wyjątki ``[{category, source, note}]`` (brak pliku = pusto)."""
    if not path.is_file():
        return frozenset()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path} must contain a list of {{category, source, note}} objects.")
    return frozenset(
        (str(item["category"]), str(item["source"]))
        for item in raw
        if isinstance(item, dict) and "category" in item and "source" in item
    )


def load_baseline_counts(path: Path = BASELINE_COUNTS_PATH) -> dict[str, dict[str, int]]:
    """Wczytuje ``baseline_counts.json`` (brak pliku = pusta tablica)."""
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain an object category -> source -> count.")
    return {str(c): {str(s): int(n) for s, n in row.items()} for c, row in raw.items()}
