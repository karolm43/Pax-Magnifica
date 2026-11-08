"""Testy katalogu komponentów na REALNYCH danych assetów AsyncTI4.

Weryfikują, że po załadowaniu ``StaticDataRegistry`` z domyślnym
``enabled_sources.json`` katalog komponentów:

* ma niepustą każdą kategorię z ``CATEGORY_SPECS`` (poza potwierdzonymi lukami
  z ``audit/expected_gaps.json``),
* zawiera wyłącznie komponenty ze źródeł aktywnych (filtr po polu ``source``),
* ładuje wpis ``codex1`` ukryty w pliku homebrew ``theodisi.json`` (decyzja D6:
  filtr działa po polu ``source``, nie po nazwie pliku).

Wymagania: 4.5, 5.1, 5.4.
"""

from __future__ import annotations

import pytest

from src.audit.diffs import load_expected_gaps
from src.core.components import CATEGORY_SPECS, ComponentCategory
from src.core.registry import StaticDataRegistry
from src.core.sources import AGENDA_VARIANT_SOURCES


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    """Rejestr z domyślnym manifestem aktywnych źródeł (base, pok, codex1-4, TE)."""
    return StaticDataRegistry()


def test_kazda_kategoria_niepusta_poza_wyjatkami(registry: StaticDataRegistry) -> None:
    """Każda kategoria z ``CATEGORY_SPECS`` jest niepusta, poza ``expected_gaps``.

    _Requirements: 5.1, 5.4_
    """
    # Kategorie, dla których potwierdzono (w ``audit/expected_gaps.json``) brak
    # wpisów z aktywnego źródła — tylko one mogą być puste.
    gap_categories = {category for category, _source in load_expected_gaps()}
    empty = [
        category.value
        for category in CATEGORY_SPECS
        if not registry.catalog.all(category) and category.value not in gap_categories
    ]
    assert empty == [], f"Puste kategorie bez potwierdzonego wyjątku: {empty}"


def test_wszystkie_source_naleza_do_aktywnych(registry: StaticDataRegistry) -> None:
    """Żaden załadowany komponent nie ma źródła spoza aktywnego manifestu.

    _Requirements: 5.1_
    """
    enabled = set(registry.report().enabled_sources)
    # Wyjątek: fanowskie talie agend (wybierane w setupie) - tylko agendy i talie agend.
    variants = AGENDA_VARIANT_SOURCES
    offending: dict[str, set[str]] = {}
    for category in CATEGORY_SPECS:
        for component in registry.catalog.all(category).values():
            if component.source in enabled:
                continue
            if component.source in variants and category in (
                ComponentCategory.AGENDA,
                ComponentCategory.DECK,
                ComponentCategory.PROMISSORY_NOTE,
            ):
                continue
            offending.setdefault(category.value, set()).add(component.source)
    assert offending == {}, f"Komponenty ze źródeł nieaktywnych: {offending}"


def test_wpis_codex1_w_theodisi_jest_zaladowany(registry: StaticDataRegistry) -> None:
    """Wpis ``codex1`` w homebrew ``theodisi.json`` jest ładowany (D6, R4.5).

    Plik ``assets/data/action_cards/theodisi.json`` zawiera karty homebrew
    (``source == "theodisi"``), ale karta „War Machine" (alias ``war_machinell``)
    ma ``source == "codex1"``. Filtr źródeł działa po POLU ``source``, nie po nazwie
    pliku, więc ta karta MUSI się załadować, a reszta pliku — nie.

    _Requirements: 4.5, 5.1_
    """
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, "war_machinell")
    assert card is not None, "Wpis codex1 'war_machinell' z theodisi.json nie załadowany"
    assert card.source == "codex1"
    # Karty homebrew z tego samego pliku (source == 'theodisi') są odfiltrowane.
    assert registry.catalog.get(ComponentCategory.ACTION_CARD, "unchart_space") is None
