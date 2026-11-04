"""Testy właściwościowe rejestru efektów (``src/core/effects_registry.py``).

Property 10 i 11 z designu local-ti4-data-foundation. Hypothesis, min. 100
iteracji. Czyste struktury: budujemy minimalny ``ComponentCatalog`` i
``EffectRegistry`` z wygenerowanych danych, bez ładowania realnych JSON.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.components import (
    ComponentBase,
    ComponentCatalog,
    ComponentCategory,
    ComponentRef,
)
from src.core.effects_registry import EffectRegistry, EffectStatus, coverage

# Mały alfabet identyfikatorów utrzymuje realistyczny i szeroki zbiór kolizji.
_ids = st.text(alphabet="abcdef0123", min_size=1, max_size=4)
_categories = st.sampled_from(list(ComponentCategory))
_statuses = st.sampled_from(list(EffectStatus))
_refs = st.builds(ComponentRef, _categories, _ids)


def _registry(status_map: dict[ComponentRef, EffectStatus]) -> EffectRegistry:
    return EffectRegistry(status_map)


# Feature: local-ti4-data-foundation, Property 10: Rejestr efektów — domyślny status i zapis statusu
@settings(max_examples=200)
@given(
    base=st.dictionaries(_refs, _statuses, max_size=12),
    missing=_refs,
    target=_refs,
    new_status=_statuses,
)
def test_status_domyslny_i_zapis_statusu(
    base: dict[ComponentRef, EffectStatus],
    missing: ComponentRef,
    target: ComponentRef,
    new_status: EffectStatus,
) -> None:
    """Referencja spoza kluczy → NOT_IMPLEMENTED; ``with_status`` trwały i niemutujący.

    **Validates: Requirements 9.1, 9.2**
    """
    registry = _registry(base)

    # Brak wpisu → domyślny status NOT_IMPLEMENTED (R9.2).
    if missing not in base:
        assert registry.status_of(missing) is EffectStatus.NOT_IMPLEMENTED

    # Migawka oryginału przed modyfikacją — ma pozostać nienaruszona.
    snapshot = {ref: registry.status_of(ref) for ref in base}

    updated = registry.with_status(target, new_status)

    # Zapis jest trwały po odczycie.
    assert updated.status_of(target) is new_status

    # Statusy innych referencji bez zmian w nowym rejestrze.
    for ref, status in snapshot.items():
        if ref != target:
            assert updated.status_of(ref) is status

    # Rejestr wejściowy nie został zmodyfikowany (niemutowalność).
    for ref, status in snapshot.items():
        assert registry.status_of(ref) is status
    if target not in base:
        assert registry.status_of(target) is EffectStatus.NOT_IMPLEMENTED


def _catalog(tables: dict[ComponentCategory, list[str]]) -> ComponentCatalog:
    """Minimalny katalog: tylko ``id`` i ``source`` są istotne dla pokrycia."""
    mapped = {
        category: {
            cid: ComponentBase(id=cid, source="base")
            for cid in ids
        }
        for category, ids in tables.items()
    }
    return ComponentCatalog(mapped)


# Feature: local-ti4-data-foundation, Property 11: Pokrycie efektów ma poprawne granice
@settings(max_examples=200)
@given(
    tables=st.dictionaries(_categories, st.lists(_ids, max_size=6, unique=True), max_size=5),
    status_map=st.dictionaries(_refs, _statuses, max_size=15),
)
def test_pokrycie_ma_poprawne_granice(
    tables: dict[ComponentCategory, list[str]],
    status_map: dict[ComponentRef, EffectStatus],
) -> None:
    """Granice wierszy pokrycia; liczone tylko komponenty obecne w katalogu.

    **Validates: Requirements 9.3**
    """
    catalog = _catalog(tables)
    registry = _registry(status_map)

    rows = coverage(catalog, registry)

    for category, row in rows.items():
        # Kategoria pusta nie trafia do wyniku (R9.3).
        catalog_ids = catalog.all(category)
        assert catalog_ids  # niepusta

        # Liczony jest dokładnie zbiór komponentów z katalogu, nie klucze osierocone.
        assert row.total == len(catalog_ids)

        # Granice liczb.
        assert 0 <= row.implemented <= row.total
        assert 0 <= row.manual <= row.total
        assert row.implemented + row.manual <= row.total

        # Procent w [0, 100].
        assert 0.0 <= row.percent_implemented <= 100.0

        # Zgodność procentu z licznikiem.
        assert row.percent_implemented == 100.0 * row.implemented / row.total

    # Kategorie bez wpisów w katalogu nie są obecne w wyniku.
    for category in ComponentCategory:
        if not catalog.all(category):
            assert category not in rows
