"""Identyfikatory danych wbudowanych we frontend (``entities/data/*.ts``) vs katalog (R11.5).

Pliki ``*.ts`` są generowane i sformatowane (wpisy na 4 spacjach wcięcia), więc
identyfikator wpisu wydobywa wyłącznie regex po polach ``alias`` / ``id`` na tym
poziomie wcięcia. Zagnieżdżone obiekty (głębsze wcięcie) są pomijane.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from src import config
from src.audit.diffs import IdDiff, diff_sets

EMBEDDED_DATA_DIR: Path = config.FRONTEND_DIR / "src" / "entities" / "data"

_ID_RE = re.compile(r"^    (?:alias|id):\s*[\"']([^\"']+)[\"']", re.MULTILINE)


def extract_embedded_ids(text: str) -> set[str]:
    """Identyfikatory wpisów najwyższego poziomu z treści pliku TS."""
    return set(_ID_RE.findall(text))


def scan_embedded_ids(directory: Path = EMBEDDED_DATA_DIR) -> dict[str, set[str]]:
    """Mapa ``nazwa pliku (bez rozszerzenia) -> identyfikatory`` dla ``*.ts`` w katalogu."""
    result: dict[str, set[str]] = {}
    if not directory.is_dir():
        return result
    for path in sorted(directory.glob("*.ts")):
        ids = extract_embedded_ids(path.read_text(encoding="utf-8-sig", errors="replace"))
        if ids:
            result[path.stem] = ids
    return result


def diff_embedded_ids(embedded: Iterable[str], catalog_ids: Iterable[str]) -> IdDiff:
    """``extra = wbudowane \\ katalog``, ``missing = katalog \\ wbudowane``."""
    return diff_sets(embedded, catalog_ids)
