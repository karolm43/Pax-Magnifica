"""Testy właściwościowe Audytora_Danych i Strażnika_Lokalności.

Property 15 (skaner zewnętrznych URL — ``src/audit/locality.py``) oraz
Property 12 i 13 (luki źródeł kanonicznych i różnice względem wzorca —
``src/audit/diffs.py``, ``assets_manifest.py``, ``frontend_data.py``).

Hypothesis, min. 100 iteracji. Funkcje pod testem są czyste nad tekstem lub
kolekcjami, więc testujemy je bez dysku, odtwarzając wynik oczekiwany modelem
referencyjnym niezależnym od implementacji.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from hypothesis import given, settings
from hypothesis import strategies as st

from src.audit.assets_manifest import ManifestDiff, diff_manifest
from src.audit.diffs import (
    CategorySourceGap,
    CountChange,
    IdDiff,
    diff_counts,
    diff_sets,
    find_gaps,
)
from src.audit.frontend_data import diff_embedded_ids
from src.audit.locality import LOCAL_HOSTS, LocalityFinding, find_external_urls
from src.audit.report import (
    AuditReport,
    ExternalUrlHit,
    SuspiciousEntry,
    exit_code,
)
from src.core.components import ComponentCategory, ComponentRef

# ---------------------------------------------------------------------------
# Property 15: Skaner zewnętrznych URL
# ---------------------------------------------------------------------------

# Hosty użyte w generatorze: lokalne (zawsze dozwolone) i zewnętrzne (kandydaci).
_LOCAL_HOST_POOL = sorted(LOCAL_HOSTS)
_EXTERNAL_HOST_POOL = [
    "images.asyncti4.com",
    "fonts.googleapis.com",
    "www.tirules2.com",
    "github.com",
    "example.org",
    "cdn.statically.io",
]
_HOST_POOL = _LOCAL_HOST_POOL + _EXTERNAL_HOST_POOL

# Segment ścieżki (bez białych znaków i znaków, które regex traktuje jak koniec URL).
_segment = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=0, max_size=6)


def _make_url(scheme: str, host: str, segments: list[str]) -> str:
    """Składa adres ``scheme://host[/seg...]`` z czystych segmentów."""
    path = "".join("/" + seg for seg in segments if seg)
    return f"{scheme}://{host}{path}"


# Krotka opisująca URL do wstawienia w tekst: (scheme, host, segmenty).
_url_spec = st.tuples(
    st.sampled_from(["http", "https"]),
    st.sampled_from(_HOST_POOL),
    st.lists(_segment, max_size=3),
)

# Prefiksy listy dozwolonej: pełny adres hosta zewnętrznego (opcjonalnie ze ścieżką).
_allowlist_prefix = st.builds(
    lambda scheme, host, segs: _make_url(scheme, host, segs),
    st.sampled_from(["http", "https"]),
    st.sampled_from(_EXTERNAL_HOST_POOL),
    st.lists(_segment, max_size=2),
)


def _host_of(url: str) -> str:
    """Host URL w małych literach (model referencyjny, jak w implementacji)."""
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _allowed_by_prefix_model(url: str, allowlist: list[str]) -> bool:
    """Niezależny model dopasowania prefiksu po granicy segmentu."""
    lowered = url.lower()
    for prefix in allowlist:
        base = prefix.lower().rstrip("/")
        if lowered == base:
            return True
        if lowered.startswith(base) and lowered[len(base)] in "/?#:":
            return True
    return False


# Feature: local-ti4-data-foundation, Property 15: Skaner zewnętrznych URL
@settings(max_examples=200)
@given(
    specs=st.lists(_url_spec, max_size=10),
    allowlist=st.lists(_allowlist_prefix, max_size=5),
    file=st.sampled_from(["", "a.ts", "index.html"]),
)
def test_skaner_url_zglasza_dokladnie_zewnetrzne_niedozwolone(
    specs: list[tuple[str, str, list[str]]], allowlist: list[str], file: str
) -> None:
    """Skaner zwraca dokładnie adresy zewnętrzne spoza hostów lokalnych i listy dozwolonej.

    Każdy URL budujemy w osobnej linii, więc numer linii jest przewidywalny.
    Oczekiwany zbiór wyznaczamy modelem referencyjnym: host spoza
    ``LOCAL_HOSTS`` i URL niepasujący do żadnego prefiksu listy dozwolonej.

    **Validates: Requirements 2.5**
    """
    urls = [_make_url(scheme, host, segs) for scheme, host, segs in specs]
    text = "\n".join(urls)

    findings = find_external_urls(text, allowlist, file=file)

    # Model referencyjny: (numer linii, url) dla każdego zgłoszonego adresu.
    expected: list[tuple[int, str]] = []
    for number, url in enumerate(urls, start=1):
        host = _host_of(url)
        if host in LOCAL_HOSTS or _allowed_by_prefix_model(url, allowlist):
            continue
        expected.append((number, url))

    assert [(f.line, f.text) for f in findings] == expected

    # Każde znalezisko niesie przekazaną nazwę pliku i jest typu LocalityFinding.
    for finding in findings:
        assert isinstance(finding, LocalityFinding)
        assert finding.file == file
        # Zgłoszony host nigdy nie jest lokalny.
        assert _host_of(finding.text) not in LOCAL_HOSTS


# Feature: local-ti4-data-foundation, Property 15: Skaner URL — hosty lokalne nigdy nie wpadają
@settings(max_examples=100)
@given(
    scheme=st.sampled_from(["http", "https"]),
    host=st.sampled_from(_LOCAL_HOST_POOL),
    segs=st.lists(_segment, max_size=3),
    allowlist=st.lists(_allowlist_prefix, max_size=3),
)
def test_skaner_url_pomija_hosty_lokalne(
    scheme: str, host: str, segs: list[str], allowlist: list[str]
) -> None:
    """Adres na hoście lokalnym nigdy nie jest zgłaszany, niezależnie od listy dozwolonej.

    **Validates: Requirements 2.5**
    """
    url = _make_url(scheme, host, segs)
    assert find_external_urls(url, allowlist) == []


# ---------------------------------------------------------------------------
# Property 12: Wykrywanie luk źródeł kanonicznych z wyjątkami
# ---------------------------------------------------------------------------

_categories = st.sampled_from(["action_card", "agenda", "objective_public", "objective_secret"])
_canonical = st.sampled_from(["base", "pok", "codex1", "thunders_edge"])
# Liczniki: zero bywa osobno (luka) lub dodatnie (brak luki); bywa też brak klucza.
_count = st.integers(min_value=0, max_value=5)


@st.composite
def _counts_table(
    draw: st.DrawFn,
) -> dict[str, dict[str, int]]:
    """Tablica ``kategoria -> źródło -> licznik`` z celowo rzadkimi kluczami."""
    categories = draw(st.lists(_categories, max_size=4, unique=True))
    table: dict[str, dict[str, int]] = {}
    for category in categories:
        row = draw(st.dictionaries(st.sampled_from(["base", "pok", "codex1"]), _count, max_size=3))
        table[category] = row
    return table


# Feature: local-ti4-data-foundation, Property 12: Wykrywanie luk źródeł kanonicznych z wyjątkami
@settings(max_examples=200)
@given(
    counts=_counts_table(),
    canonical=st.lists(_canonical, max_size=4, unique=True),
    expected=st.lists(st.tuples(_categories, _canonical), max_size=6),
)
def test_find_gaps_to_pary_z_zerem_minus_wyjatki(
    counts: dict[str, dict[str, int]],
    canonical: list[str],
    expected: list[tuple[str, str]],
) -> None:
    """Luka = (kategoria, źródło kanoniczne) z licznikiem zero, minus potwierdzone wyjątki.

    Brak klucza źródła w wierszu kategorii liczy się jak zero (R6.2, R6.3).
    Wynik jest posortowany i nie zawiera żadnej pary z listy wyjątków.

    **Validates: Requirements 3.2, 6.2, 6.3, 6.5, 11.5**
    """
    allowed = set(expected)
    gaps = find_gaps(counts, canonical, expected)

    # Model referencyjny wyznaczony niezależnie od implementacji.
    expected_gaps = sorted(
        CategorySourceGap(category, source)
        for category, row in counts.items()
        for source in canonical
        if row.get(source, 0) == 0 and (category, source) not in allowed
    )
    assert gaps == expected_gaps

    # Wynik jest posortowany rosnąco (deterministyczny).
    assert gaps == sorted(gaps)

    # Żadna luka nie jest na liście wyjątków i każda ma licznik zero.
    for gap in gaps:
        assert (gap.category, gap.source) not in allowed
        assert counts.get(gap.category, {}).get(gap.source, 0) == 0
        assert gap.source in canonical


# Feature: local-ti4-data-foundation, Property 12: Wyjątki całkowicie tłumią luki
@settings(max_examples=100)
@given(counts=_counts_table(), canonical=st.lists(_canonical, max_size=4, unique=True))
def test_find_gaps_z_wyjatkami_pokrywajacymi_wszystko_jest_pusty(
    counts: dict[str, dict[str, int]], canonical: list[str]
) -> None:
    """Gdy wyjątki pokrywają każdą możliwą parę, wynik jest pusty (R6.3).

    **Validates: Requirements 6.2, 6.3**
    """
    all_pairs = [
        (category, source) for category in counts for source in canonical
    ]
    # Dołóż pary dla kategorii spoza ``counts`` nie jest potrzebne: find_gaps iteruje po counts.
    assert find_gaps(counts, canonical, all_pairs) == []


# ---------------------------------------------------------------------------
# Property 13: Różnice względem wzorca są dokładnymi różnicami zbiorów lub słowników
# ---------------------------------------------------------------------------

_id = st.text(alphabet="abcdef0123", min_size=1, max_size=4)
_id_set = st.lists(_id, max_size=12)


# Feature: local-ti4-data-foundation, Property 13: diff_sets to dokładna różnica zbiorów
@settings(max_examples=200)
@given(left=_id_set, right=_id_set)
def test_diff_sets_jest_dokladna_roznica_zbiorow(left: list[str], right: list[str]) -> None:
    """``extra = left \\ right``, ``missing = right \\ left``; pusty ⇔ zbiory równe.

    **Validates: Requirements 3.2, 6.5, 11.5**
    """
    result = diff_sets(left, right)
    left_set = set(left)
    right_set = set(right)

    assert result.extra == left_set - right_set
    assert result.missing == right_set - left_set
    assert result.is_empty == (left_set == right_set)

    # Rozłączność klas i pełne pokrycie symetrycznej różnicy.
    assert result.extra.isdisjoint(result.missing)
    assert (result.extra | result.missing) == (left_set ^ right_set)


# Feature: local-ti4-data-foundation, Property 13: diff_embedded_ids pokrywa się z diff_sets
@settings(max_examples=100)
@given(embedded=_id_set, catalog=_id_set)
def test_diff_embedded_ids_to_roznica_zbiorow(
    embedded: list[str], catalog: list[str]
) -> None:
    """Różnica identyfikatorów wbudowanych vs katalog = ``diff_sets`` (R11.5).

    **Validates: Requirements 11.5**
    """
    result = diff_embedded_ids(embedded, catalog)
    reference = diff_sets(embedded, catalog)
    assert isinstance(result, IdDiff)
    assert result == reference
    # ``extra`` = wbudowane nadmiarowe (potencjalnie niekanoniczne), ``missing`` = brakujące.
    assert result.extra == set(embedded) - set(catalog)
    assert result.missing == set(catalog) - set(embedded)


# Feature: local-ti4-data-foundation, Property 13: diff_manifest to dokładna różnica ścieżek
@settings(max_examples=200)
@given(manifest=_id_set, disk=_id_set)
def test_diff_manifest_jest_dokladna_roznica(manifest: list[str], disk: list[str]) -> None:
    """``missing = manifest \\ dysk``, ``unused = dysk \\ manifest``; pusty ⇔ równe zbiory.

    **Validates: Requirements 3.2, 6.5**
    """
    result = diff_manifest(manifest, disk)
    manifest_set = set(manifest)
    disk_set = set(disk)

    assert isinstance(result, ManifestDiff)
    assert result.missing == manifest_set - disk_set
    assert result.unused == disk_set - manifest_set
    assert result.is_empty == (manifest_set == disk_set)
    assert result.missing.isdisjoint(result.unused)


# Generator tablic liczników do diff_counts (rzadkie klucze po obu stronach).
_counts_category = st.sampled_from(["action_card", "agenda", "objective"])
_counts_source = st.sampled_from(["base", "pok", "codex1"])


@st.composite
def _count_table(draw: st.DrawFn) -> dict[str, dict[str, int]]:
    """Tablica ``kategoria -> źródło -> licznik`` z celowo niepełnymi wierszami."""
    categories = draw(st.lists(_counts_category, max_size=3, unique=True))
    return {
        category: draw(st.dictionaries(_counts_source, st.integers(0, 9), max_size=3))
        for category in categories
    }


# Feature: local-ti4-data-foundation, Property 13: diff_counts to dokładna różnica słowników
@settings(max_examples=200)
@given(baseline=_count_table(), current=_count_table())
def test_diff_counts_jest_dokladna_roznica_slownikow(
    baseline: dict[str, dict[str, int]], current: dict[str, dict[str, int]]
) -> None:
    """Zwraca dokładnie pary o różnych licznikach; pusty ⇔ obie tablice równe (R6.5).

    Brak wpisu po jednej ze stron (``None``) jest różnicą.

    **Validates: Requirements 6.5**
    """
    result = diff_counts(baseline, current)

    # Model referencyjny: wszystkie klucze obecne po którejkolwiek stronie.
    keys = {
        (category, source)
        for table in (baseline, current)
        for category, row in table.items()
        for source in row
    }
    expected: dict[tuple[str, str], CountChange] = {}
    for category, source in keys:
        old = baseline.get(category, {}).get(source)
        new = current.get(category, {}).get(source)
        if old != new:
            expected[(category, source)] = CountChange(old, new)

    assert result == expected

    # Pusty wynik wtedy i tylko wtedy, gdy znormalizowane tablice są równe.
    tables_equal = all(
        baseline.get(c, {}).get(s) == current.get(c, {}).get(s) for c, s in keys
    )
    assert (not result) == tables_equal

    # Każda zwrócona para faktycznie różni się licznikiem.
    for (category, source), change in result.items():
        assert change.baseline != change.current
        assert change.baseline == baseline.get(category, {}).get(source)
        assert change.current == current.get(category, {}).get(source)


# ---------------------------------------------------------------------------
# Property 14: Kod wyjścia audytu odzwierciedla błędy krytyczne
# ---------------------------------------------------------------------------
#
# ``exit_code(report)`` zwraca ≠ 0 wtedy i tylko wtedy, gdy raport zawiera BŁĄD
# KRYTYCZNY: nierozwiązana referencja, brakujący plik z manifestu, zewnętrzny URL
# spoza listy dozwolonej albo błąd walidacji wpisu kanonicznego (R3.4, R7.5, R12.2).
# Ostrzeżenia (wpisy podejrzane, luki do potwierdzenia, 'unclassified', 'bez noty',
# osierocone statusy, pliki nieużywane z manifestu) NIE zmieniają kodu 0.
#
# Budujemy ``AuditReport`` bezpośrednio z losowych kombinacji pól krytycznych i
# ostrzegawczych (bez dysku i bez rejestru), a oczekiwanie wyznaczamy modelem
# referencyjnym niezależnym od ``has_critical``.

_category = st.sampled_from(list(ComponentCategory))
_short_id = st.text(alphabet="abcdef0123", min_size=1, max_size=5)

# --- Generatory pól KRYTYCZNYCH (każdy niepusty => błąd krytyczny) ---------

_unresolved = st.lists(st.text(max_size=10), max_size=4)
_manifest_missing = st.lists(_short_id, max_size=4)
_external_urls = st.lists(
    st.builds(
        ExternalUrlHit,
        st.sampled_from(["index.html", "a.ts", "b.tsx"]),
        st.integers(min_value=1, max_value=50),
        st.sampled_from(["https://x.example/a", "https://images.asyncti4.com/u.png"]),
    ),
    max_size=3,
)
_validation_error = st.one_of(st.none(), st.text(min_size=1, max_size=10))

# --- Generatory pól OSTRZEGAWCZYCH (nigdy nie zmieniają kodu) ---------------

_suspicious = st.lists(
    st.builds(SuspiciousEntry, _category, _short_id, st.just("codex1"), _short_id),
    max_size=3,
)
_gap_category = st.sampled_from(["agenda", "objective"])
_gaps = st.lists(
    st.builds(CategorySourceGap, _gap_category, st.just("thunders_edge")),
    max_size=3,
)
_refs = st.lists(st.builds(ComponentRef, _category, _short_id), max_size=3)
_manifest_unused = st.lists(_short_id, max_size=4)


# Feature: local-ti4-data-foundation, Property 14: Kod wyjścia audytu odzwierciedla błędy krytyczne
@settings(max_examples=200)
@given(
    unresolved=_unresolved,
    manifest_missing=_manifest_missing,
    external_urls=_external_urls,
    validation_error=_validation_error,
    suspicious=_suspicious,
    gaps=_gaps,
    unclassified=_refs,
    no_rules_note=_refs,
    orphans=_refs,
    manifest_unused=_manifest_unused,
)
def test_exit_code_jest_niezerowy_dokladnie_przy_bledzie_krytycznym(
    unresolved: list[str],
    manifest_missing: list[str],
    external_urls: list[ExternalUrlHit],
    validation_error: str | None,
    suspicious: list[SuspiciousEntry],
    gaps: list[CategorySourceGap],
    unclassified: list[ComponentRef],
    no_rules_note: list[ComponentRef],
    orphans: list[ComponentRef],
    manifest_unused: list[str],
) -> None:
    """``exit_code`` ≠ 0 ⇔ istnieje błąd krytyczny; ostrzeżenia nie zmieniają kodu 0.

    Model referencyjny: kod jest niezerowy dokładnie wtedy, gdy którekolwiek z pól
    krytycznych (nierozwiązane referencje, brakujące pliki manifestu, zewnętrzne URL,
    błąd walidacji) jest niepuste — niezależnie od obecności ostrzeżeń.

    **Validates: Requirements 3.4, 7.5, 12.1, 12.2**
    """
    report = AuditReport(
        unresolved=unresolved,
        manifest=ManifestDiff(
            missing=frozenset(manifest_missing), unused=frozenset(manifest_unused)
        ),
        external_urls=external_urls,
        validation_error=validation_error,
        suspicious=suspicious,
        gaps_to_confirm=gaps,
        unclassified_timing=unclassified,
        no_rules_note=no_rules_note,
        orphan_effect_statuses=orphans,
    )

    has_critical_ref = bool(
        unresolved or manifest_missing or external_urls or validation_error
    )

    assert report.has_critical is has_critical_ref
    assert exit_code(report) == (1 if has_critical_ref else 0)
    # Kod wyjścia jest zawsze 0 albo 1 (zgodne z semantyką procesu).
    assert exit_code(report) in (0, 1)


# Feature: local-ti4-data-foundation, Property 14: same ostrzeżenia nigdy nie dają błędu
@settings(max_examples=100)
@given(
    suspicious=_suspicious,
    gaps=_gaps,
    unclassified=_refs,
    no_rules_note=_refs,
    orphans=_refs,
    manifest_unused=_manifest_unused,
)
def test_exit_code_zero_gdy_tylko_ostrzezenia(
    suspicious: list[SuspiciousEntry],
    gaps: list[CategorySourceGap],
    unclassified: list[ComponentRef],
    no_rules_note: list[ComponentRef],
    orphans: list[ComponentRef],
    manifest_unused: list[str],
) -> None:
    """Dowolny zestaw samych ostrzeżeń (bez pól krytycznych) daje kod wyjścia 0.

    Pliki 'unused' z manifestu, wpisy podejrzane, luki, 'unclassified', 'bez noty'
    i osierocone statusy są ostrzeżeniami (R3.4, R12.2).

    **Validates: Requirements 3.4, 7.5, 12.2**
    """
    report = AuditReport(
        suspicious=suspicious,
        gaps_to_confirm=gaps,
        unclassified_timing=unclassified,
        no_rules_note=no_rules_note,
        orphan_effect_statuses=orphans,
        manifest=ManifestDiff(missing=frozenset(), unused=frozenset(manifest_unused)),
    )
    assert report.has_critical is False
    assert exit_code(report) == 0
