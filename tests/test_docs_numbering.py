"""Test numeracji sekcji w ``docs/RULES.md`` (spec local-ti4-data-foundation, zadanie 13.1).

Pilnuje niezmiennika dokumentacji: każdy nagłówek sekcji ``## N.`` ma UNIKALNY numer.
W trakcie prac nad silnikiem pojawiły się duplikaty (dwie sekcje „3" i dwie „30");
ten test blokuje ich ponowne wprowadzenie. Lettered-subsekcje (``2a``, ``2b``, ``3a``)
są traktowane jako osobne, poprawne identyfikatory — liczy się brak KOLIZJI, nie ciągłość.
"""

from __future__ import annotations

import re

from src import config

# Dopasowuje nagłówki poziomu 2 z identyfikatorem liczbowym, np. „## 3.", „## 2a.",
# „## 30. Limity...". Grupa 1 = identyfikator sekcji (liczba + opcjonalna litera).
_SECTION_RE = re.compile(r"^##\s+(\d+[a-z]?)\.\s", re.MULTILINE)


def _section_ids() -> list[str]:
    text = (config.PROJECT_ROOT / "docs" / "RULES.md").read_text(encoding="utf-8")
    return _SECTION_RE.findall(text)


def test_identyfikatory_sekcji_sa_unikalne() -> None:
    """Żaden identyfikator sekcji ``## N.`` nie powtarza się w RULES.md."""
    ids = _section_ids()
    duplikaty = sorted({sid for sid in ids if ids.count(sid) > 1})
    assert not duplikaty, f"Zduplikowane numery sekcji w docs/RULES.md: {duplikaty}"


def test_sekcja_audytu_istnieje() -> None:
    """RULES.md zawiera sekcję z wynikami audytu danych (R6.6)."""
    ids = _section_ids()
    assert "37" in ids, "Brak sekcji 37 (wyniki audytu danych) w docs/RULES.md"


def test_wpisy_zalozen_obecne() -> None:
    """Sekcja audytu dokumentuje założenia D10 i placeholder <color> (R12.7)."""
    text = (config.PROJECT_ROOT / "docs" / "RULES.md").read_text(encoding="utf-8")
    assert "TRIGGER_WINDOW_MAP" in text
    assert "<color>" in text
    assert "explores_cpti" in text
