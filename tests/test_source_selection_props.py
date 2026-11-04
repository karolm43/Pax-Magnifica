"""Testy właściwościowe wyboru i walidacji źródeł danych."""

from __future__ import annotations

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.component_loader import EntryOrigin, select_entries
from src.core.sources import (
    SOURCE_PRIORITY,
    UnknownSourcesError,
    source_rank,
    validate_enabled_sources,
)

_ids = st.text(alphabet="abcdefgh01_", min_size=1, max_size=4)


# Feature: local-ti4-data-foundation, Property 3: Walidacja identyfikatorów aktywnych źródeł
@settings(max_examples=100)
@given(enabled=st.lists(_ids, max_size=10), known=st.sets(_ids, max_size=10))
def test_walidacja_zrodel_zglasza_dokladnie_nieznane(
    enabled: list[str], known: set[str]
) -> None:
    """**Validates: Requirements 4.2**"""
    expected = sorted({s for s in enabled if s not in known})
    if not expected:
        validate_enabled_sources(enabled, known)
        return
    try:
        validate_enabled_sources(enabled, known)
    except UnknownSourcesError as exc:
        assert exc.unknown == expected
        for source in expected:
            assert source in str(exc)
    else:
        raise AssertionError("oczekiwano UnknownSourcesError")


# Pula identyfikatorów komponentów (mała, by wymusić kolizje ``id``).
_entry_ids = st.sampled_from(["a", "b", "c", "d"])
# Pula aktywnych źródeł branych do filtra (podzbiór kanonicznych + jedno nieznane).
_enabled_pool = list(SOURCE_PRIORITY) + ["ds"]
# Generator pola ``source`` zgodny z zadaniem: None, liczby, listy tekstów, tekst.
_source = st.one_of(
    st.none(),
    st.integers(),
    st.lists(st.text(max_size=3), max_size=3),
    st.text(alphabet="abcdefgh_", min_size=1, max_size=12),
)


def _entry(source: object, entry_id: object) -> dict[str, object]:
    """Buduje surowy wpis z dowolnym ``source`` i ``id`` (pole id = ``alias``).

    ``source`` jest zawsze obecne jako klucz; gdy nie jest napisem (np. ``None``,
    liczba, lista), wpis trafi do ``sourceless`` w ``select_entries``.
    """
    return {"source": source, "alias": entry_id}


# Strategia wpisu wejściowego: pochodzenie (plik, indeks) + ``source`` + ``id``.
_raw_entry = st.tuples(
    st.sampled_from(["f1.json", "f2.json"]),
    st.integers(min_value=0, max_value=5),
    _source,
    _entry_ids,
)


def _materialize(
    rows: list[tuple[str, int, object, object]],
) -> list[tuple[EntryOrigin, dict[str, object]]]:
    """Zamienia wygenerowane krotki na wejście ``select_entries``."""
    return [
        (EntryOrigin(Path(file), index), _entry(source, entry_id))
        for file, index, source, entry_id in rows
    ]


# Feature: local-ti4-data-foundation, Property 1: Rachunek wpisów przy filtrowaniu po źródle
@settings(max_examples=200)
@given(rows=st.lists(_raw_entry, max_size=30), enabled=st.sets(st.sampled_from(_enabled_pool)))
def test_filtrowanie_zrodel_bilansuje_wszystkie_wpisy(
    rows: list[tuple[str, int, object, object]], enabled: set[str]
) -> None:
    """Każdy wpis wejściowy trafia dokładnie do jednej kategorii wyniku.

    Suma: pominięte (niekanoniczne) + bez źródła + aktywne wpisy = liczba wejść.
    Aktywne wpisy = unikalne wybrane ``id`` + przegrani w kolizjach.

    **Validates: Requirements 4.1, 4.3, 4.4, 4.7, 6.1**
    """
    entries = _materialize(rows)
    result = select_entries(entries, enabled, id_field="alias")

    # Liczby wejść w podziale na trzy rozłączne klasy, liczone niezależnie od loadera.
    sourceless_count = sum(1 for _, e in entries if not isinstance(e.get("source"), str))
    skipped_count = sum(
        1
        for _, e in entries
        if isinstance(e.get("source"), str) and e["source"] not in enabled
    )
    active_count = sum(
        1
        for _, e in entries
        if isinstance(e.get("source"), str) and e["source"] in enabled
    )

    # Wpisy bez poprawnego ``source`` lądują w ``sourceless``.
    assert len(result.sourceless) == sourceless_count
    # Licznik pominiętych sumuje się do liczby wpisów ze źródłem niekanonicznym.
    assert sum(result.skipped.values()) == skipped_count
    # Aktywne wpisy = wybrani (po jednym na ``id``) + przegrani w kolizjach.
    losers = sum(len(conflict.losers) for conflict in result.conflicts)
    assert len(result.selected) + losers == active_count
    # Pełny bilans: każdy wpis wejściowy policzony dokładnie raz.
    assert sourceless_count + skipped_count + active_count == len(entries)
    # Każdy wybrany wpis ma źródło z aktywnego zbioru.
    for candidate in result.selected.values():
        assert candidate.source in enabled


# Feature: local-ti4-data-foundation, Property 2: Deterministyczny wybór przy kolizji identyfikatora
@settings(max_examples=200)
@given(
    rows=st.lists(_raw_entry, min_size=1, max_size=30),
    enabled=st.sets(st.sampled_from(_enabled_pool)),
    data=st.data(),
)
def test_kolizja_id_wybiera_deterministycznie_niezaleznie_od_kolejnosci(
    rows: list[tuple[str, int, object, object]], enabled: set[str], data: st.DataObject
) -> None:
    """Zwycięzca kolizji nie zależy od kolejności wejścia i jest o najwyższym priorytecie.

    Wygrywa najniższy ``source_rank``; remis rangi rozstrzyga wcześniejszy
    ``(file, index)``. Przetasowanie wejścia daje identyczny wynik.

    **Validates: Requirements 4.1, 4.3, 4.4, 4.7, 6.1**
    """
    entries = _materialize(rows)
    result = select_entries(entries, enabled, id_field="alias")

    # Przetasowana kopia wejścia musi dać ten sam zbiór zwycięzców (niezależność od kolejności).
    shuffled = data.draw(st.permutations(entries))
    result_shuffled = select_entries(shuffled, enabled, id_field="alias")
    winners = {eid: c.source for eid, c in result.selected.items()}
    winners_shuffled = {eid: c.source for eid, c in result_shuffled.selected.items()}
    assert winners == winners_shuffled

    # Dla każdego wybranego ``id`` zwycięzca jest minimalny względem (rank, file, index).
    for entry_id, candidate in result.selected.items():
        active_same_id = [
            (origin, e["source"])
            for origin, e in entries
            if isinstance(e.get("source"), str)
            and e["source"] in enabled
            and e.get("alias") == entry_id
        ]
        best = min(
            active_same_id,
            key=lambda item: (source_rank(item[1]), str(item[0].file), item[0].index),
        )
        best_origin, best_source = best
        assert candidate.source == best_source
        assert candidate.origin == best_origin
        # Zwycięzca ma rangę nie gorszą niż każdy inny kandydat z tym ``id``.
        for _origin, src in active_same_id:
            assert source_rank(candidate.source) <= source_rank(src)
