"""Test numeracji sekcji w ``docs/RULES.md`` (spec local-ti4-data-foundation, zadanie 13.1).

Pilnuje niezmiennika dokumentacji: każdy identyfikator sekcji ``N`` ma UNIKALNY numer.
Od podziału dokumentacji (2026-11) ``docs/RULES.md`` jest INDEKSEM
(tabela ``| N | [tytuł](rules/RNN.md) |``), a treść sekcji leży w ``docs/rules/R<NN>.md``.
Test sprawdza unikalność numerów w indeksie, istnienie plików sekcji oraz obecność
wpisów audytu danych w ``rules/R37.md``.
"""

from __future__ import annotations

import re

from src import config

_DOCS = config.PROJECT_ROOT / "docs"

# Wiersz tabeli indeksu: „| 37 | [Wyniki audytu…](rules/R37.md) | 92 |".
# Grupa 1 = identyfikator sekcji (liczba + opcjonalna litera), grupa 2 = plik sekcji.
_INDEX_ROW_RE = re.compile(
    r"^\|\s*(\d+[a-z]?)\s*\|\s*\[[^\]]*\]\((rules/R[^)]+\.md)\)", re.MULTILINE
)


def _index_rows() -> list[tuple[str, str]]:
    text = (_DOCS / "RULES.md").read_text(encoding="utf-8")
    return _INDEX_ROW_RE.findall(text)


def _section_ids() -> list[str]:
    return [sid for sid, _ in _index_rows()]


def test_identyfikatory_sekcji_sa_unikalne() -> None:
    """Żaden identyfikator sekcji nie powtarza się w indeksie RULES.md."""
    ids = _section_ids()
    assert ids, "Indeks docs/RULES.md nie zawiera wierszy sekcji"
    duplikaty = sorted({sid for sid in ids if ids.count(sid) > 1})
    assert not duplikaty, f"Zduplikowane numery sekcji w docs/RULES.md: {duplikaty}"


def test_pliki_sekcji_istnieja() -> None:
    """Każdy wiersz indeksu wskazuje istniejący plik ``docs/rules/R<NN>.md``."""
    brakujace = [path for _, path in _index_rows() if not (_DOCS / path).is_file()]
    assert not brakujace, f"Indeks RULES.md wskazuje brakujące pliki: {brakujace}"


def test_sekcja_audytu_istnieje() -> None:
    """RULES.md zawiera sekcję z wynikami audytu danych (R6.6)."""
    ids = _section_ids()
    assert "37" in ids, "Brak sekcji 37 (wyniki audytu danych) w docs/RULES.md"


def test_wpisy_zalozen_obecne() -> None:
    """Sekcja audytu dokumentuje założenia D10 i placeholder <color> (R12.7)."""
    text = (_DOCS / "rules" / "R37.md").read_text(encoding="utf-8")
    assert "TRIGGER_WINDOW_MAP" in text
    assert "<color>" in text
    assert "explores_cpti" in text
