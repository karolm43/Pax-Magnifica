"""Test regresji liczb wpisów Katalogu_Komponentów względem wzorca w repo.

Porównuje liczby komponentów per kategoria i źródło (``catalog.counts()``
z ``StaticDataRegistry``) z wartościami referencyjnymi zapisanymi w
``audit/baseline_counts.json``. Każda rozbieżność (dodany/usunięty wpis,
nowe lub znikające źródło w kategorii) zawodzi test z czytelnym wypisaniem
różnic, co chroni przed niezamierzoną zmianą zawartości danych.

Różnice liczymy czystą funkcją ``diff_counts`` z ``src/audit/diffs.py``,
a wzorzec wczytujemy przez ``load_baseline_counts`` z tego samego modułu —
unikamy duplikowania logiki po stronie testu.

Wymagania: 6.4, 6.5.
"""

from __future__ import annotations

import pytest

from src.audit.diffs import CountChange, diff_counts, load_baseline_counts
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    """Rejestr z domyślnym manifestem aktywnych źródeł (base, pok, codex1-4, TE)."""
    return StaticDataRegistry()


def _catalog_counts_as_str(registry: StaticDataRegistry) -> dict[str, dict[str, int]]:
    """Liczby z katalogu z kluczami kategorii jako ``str`` (``ComponentCategory`` → wartość).

    ``catalog.counts()`` zwraca klucze typu ``ComponentCategory`` (StrEnum); wzorzec
    w JSON ma klucze tekstowe. Normalizujemy po stronie katalogu, by porównanie i
    wypisane różnice operowały na zwykłych napisach.
    """
    return {
        category.value: dict(per_source)
        for category, per_source in registry.catalog.counts().items()
    }


def _format_changes(changes: dict[tuple[str, str], CountChange]) -> str:
    """Czytelne, deterministyczne wypisanie różnic (R6.5).

    Dla każdej pary (kategoria, źródło) pokazuje ``baseline → current``; ``None``
    oznacza brak wpisu po danej stronie (nowe lub usunięte źródło w kategorii).
    """
    lines = ["Liczby wpisów różnią się od audit/baseline_counts.json:"]
    for (category, source), change in sorted(changes.items()):
        old = "—" if change.baseline is None else str(change.baseline)
        new = "—" if change.current is None else str(change.current)
        lines.append(f"  {category}/{source}: {old} → {new}")
    lines.append(
        "Jeśli zmiana jest zamierzona, zaktualizuj wzorzec: "
        "uv run python -m src.audit --write-baseline"
    )
    return "\n".join(lines)


def test_liczby_wpisow_zgadzaja_sie_z_baseline(registry: StaticDataRegistry) -> None:
    """Liczby wpisów per kategoria i źródło są równe wzorcowi z repo.

    Przy rozbieżności test zawodzi z listą dokładnych różnic (R6.4, R6.5).

    _Requirements: 6.4, 6.5_
    """
    baseline = load_baseline_counts()
    assert baseline, (
        "Brak wzorca audit/baseline_counts.json — wygeneruj go przez "
        "uv run python -m src.audit --write-baseline"
    )

    current = _catalog_counts_as_str(registry)
    changes = diff_counts(baseline, current)

    assert not changes, _format_changes(changes)
