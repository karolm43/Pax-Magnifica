"""Raport Audytora_Danych: zbiera wyniki ładowania, referencji, czasu, efektów i
różnic z dyskiem w jedną strukturę ``AuditReport``, renderuje ją do tekstu i wyznacza
kod wyjścia.

Podział odpowiedzialności (R12.1, R12.2):

- ``build_report(registry, scans)`` jest CZYSTE nad już zebranymi danymi: nie czyta
  dysku samodzielnie (I/O żyje w ``collect_scans`` i ``__main__``), więc daje się
  testować na mini-rejestrze i sztucznych skanach.
- ``render_text(report)`` buduje czytelny raport tekstowy ze wszystkimi sekcjami.
- ``exit_code(report)`` zwraca ≠ 0 wtedy i tylko wtedy, gdy raport zawiera BŁĄD
  KRYTYCZNY (nierozwiązana referencja, brakujący plik z manifestu, zewnętrzny URL
  spoza listy dozwolonej albo błąd walidacji wpisu kanonicznego). Ostrzeżenia
  (podejrzane wpisy, ``unclassified``, luki do potwierdzenia, „bez noty”, osierocone
  statusy, kolizje ``id``) nie zmieniają kodu 0 (Property 14, R3.4, R7.5, R12.2).

Wpis „podejrzany” (R4.5) jest wykrywany STRUKTURALNIE: wpis o źródle kanonicznym
leżący w pliku, którego nazwa (bez rozszerzenia) NIE jest identyfikatorem żadnego
źródła kanonicznego ani nazwą bazową kategorii. Reguła nie zawiera listy nazw
homebrew (przykład efektu: ``theodisi.json`` z wpisem ``codex1``).

Spójność referencji (R7.x) pochodzi z ``core/references.py``, który powstaje
równolegle (zadanie 4.1). Import jest OBRONNY: gdy modułu jeszcze nie ma, audyt
działa dalej i korzysta z ``registry.missing_planet_references`` jako substytutu,
oznaczając w raporcie, że pełna analiza referencji była niedostępna.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from src import config
from src.audit.assets_manifest import (
    ManifestDiff,
    build_manifest,
    diff_manifest,
    list_asset_files,
    load_manifest_paths,
    write_manifest,
)
from src.audit.diffs import (
    BASELINE_COUNTS_PATH,
    CategorySourceGap,
    find_gaps,
    load_expected_gaps,
)
from src.audit.frontend_data import diff_embedded_ids, scan_embedded_ids
from src.audit.locality import (
    LocalityFinding,
    load_allowlist,
    scan_external_urls,
)
from src.core.component_loader import IdConflict, SourcelessEntry, iter_entries_with_origin
from src.core.components import (
    CATEGORY_SPECS,
    CategorySpec,
    ComponentCatalog,
    ComponentCategory,
    ComponentRef,
)
from src.core.effects_registry import CoverageRow, EffectRegistry, coverage
from src.core.rules_links import CATEGORY_TOPIC_HINTS, RulesTopicIndex
from src.core.sources import SOURCE_PRIORITY, known_source_ids
from src.core.timing_spec import TriggerKind

if TYPE_CHECKING:
    from src.audit.diffs import IdDiff
    from src.core.registry import StaticDataRegistry

# Źródła kanoniczne = pełna lista priorytetu (base, pok, codex1-4, thunders_edge).
CANONICAL_SOURCES: frozenset[str] = frozenset(SOURCE_PRIORITY)

# Wzorce plików skanowanych pod kątem zewnętrznych URL (R2.5).
_FRONTEND_URL_PATTERNS: tuple[str, ...] = (
    "src/**/*.ts",
    "src/**/*.tsx",
    "index.html",
    "vite.config.ts",
)


@dataclass(frozen=True)
class SuspiciousEntry:
    """Wpis o źródle kanonicznym w pliku o nietypowej nazwie (strukturalnie, R4.5)."""

    category: ComponentCategory
    entry_id: str
    source: str
    file_stem: str


@dataclass(frozen=True)
class ExternalUrlHit:
    """Zewnętrzny adres URL spoza listy dozwolonej (R2.5)."""

    file: str
    line: int
    url: str


@dataclass
class AuditScans:
    """Dane zebrane z dysku i przekazane do czystego ``build_report``.

    Oddziela I/O (``collect_scans``) od logiki raportu, dzięki czemu ``build_report``
    pozostaje testowalne bez dysku.
    """

    manifest: ManifestDiff = field(default_factory=lambda: ManifestDiff(frozenset(), frozenset()))
    external_urls: list[ExternalUrlHit] = field(default_factory=list)
    frontend_diff: dict[str, IdDiff] = field(default_factory=dict)
    suspicious: list[SuspiciousEntry] = field(default_factory=list)
    # Nierozwiązane referencje jako czytelne napisy (źródło: core/references.py lub
    # substytut missing_planet_references). Pusta lista = brak nierozwiązanych.
    unresolved: list[str] = field(default_factory=list)
    # Czy pełna analiza referencji (core/references.py) była dostępna.
    references_module_available: bool = True


@dataclass
class AuditReport:
    """Zebrany wynik audytu danych (R12.1)."""

    counts: dict[ComponentCategory, dict[str, int]] = field(default_factory=dict)
    skipped: dict[ComponentCategory, dict[str, int]] = field(default_factory=dict)
    sourceless: dict[ComponentCategory, list[SourcelessEntry]] = field(default_factory=dict)
    conflicts: dict[ComponentCategory, list[IdConflict]] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    suspicious: list[SuspiciousEntry] = field(default_factory=list)
    gaps_to_confirm: list[CategorySourceGap] = field(default_factory=list)
    unclassified_timing: list[ComponentRef] = field(default_factory=list)
    effect_coverage: dict[ComponentCategory, CoverageRow] = field(default_factory=dict)
    manifest: ManifestDiff = field(default_factory=lambda: ManifestDiff(frozenset(), frozenset()))
    external_urls: list[ExternalUrlHit] = field(default_factory=list)
    frontend_diff: dict[str, IdDiff] = field(default_factory=dict)
    no_rules_note: list[ComponentRef] = field(default_factory=list)
    orphan_effect_statuses: list[ComponentRef] = field(default_factory=list)
    # Czy wystąpił błąd walidacji wpisu kanonicznego (DataValidationError przy starcie).
    validation_error: str | None = None
    references_module_available: bool = True

    @property
    def has_critical(self) -> bool:
        """Czy raport zawiera BŁĄD KRYTYCZNY (zmienia kod wyjścia)."""
        return bool(
            self.unresolved
            or self.manifest.missing
            or self.external_urls
            or self.validation_error
        )


# --- Wykrywanie wpisów podejrzanych (strukturalnie, R4.5) ----------------


def detect_suspicious(
    specs: Mapping[ComponentCategory, CategorySpec] | None = None,
    canonical: Collection[str] = CANONICAL_SOURCES,
    known: Collection[str] | None = None,
) -> list[SuspiciousEntry]:
    """Wpisy kanoniczne w plikach o nietypowej nazwie (czysto strukturalnie).

    Dla każdej kategorii z ``CATEGORY_SPECS`` skanuje pliki ``*.json`` i zgłasza wpis,
    którego ``source`` jest kanoniczne, a nazwa pliku (bez rozszerzenia) NIE jest
    identyfikatorem żadnego ZNANEGO źródła ani nazwą bazową kategorii. Lista nazw
    homebrew nie jest używana — reguła wynika wyłącznie ze struktury (R4.5).

    Args:
        specs: Tabela kategorii (domyślnie ``CATEGORY_SPECS``). Wstrzykiwana w testach.
        canonical: Zbiór źródeł kanonicznych.
        known: Zbiór znanych identyfikatorów źródeł (domyślnie z ``sources.json``);
            nazwa pliku równa któremukolwiek znanemu źródłu jest „normalna”.
    """
    active_specs = CATEGORY_SPECS if specs is None else specs
    known_ids = set(known) if known is not None else set(known_source_ids())
    found: list[SuspiciousEntry] = []
    for category, spec in active_specs.items():
        if not spec.directory.is_dir():
            continue
        base_name = category.value  # nazwa bazowa kategorii (np. "action_cards")
        for origin, entry in iter_entries_with_origin(spec.directory):
            source = entry.get("source")
            entry_id = entry.get(spec.id_field)
            if not isinstance(source, str) or source not in canonical:
                continue
            if not isinstance(entry_id, str) or not entry_id:
                continue
            stem = origin.file.stem
            # Nazwa pliku „normalna”: identyfikator znanego źródła albo nazwa kategorii.
            if stem in known_ids or stem == base_name:
                continue
            found.append(SuspiciousEntry(category, entry_id, source, stem))
    found.sort(key=lambda e: (e.category.value, e.entry_id, e.source))
    return found


# --- Budowa raportu (czysta nad registry + scans) ------------------------


def build_report(
    registry: StaticDataRegistry,
    scans: AuditScans | None = None,
) -> AuditReport:
    """Składa ``AuditReport`` z rejestru i zebranych skanów (czysta, bez I/O)."""
    scans = scans or AuditScans()
    load = registry.load_report
    catalog = registry.catalog

    counts = catalog.counts()

    # Luki źródeł kanonicznych (kategoria bez wpisów dla źródła), minus wyjątki.
    # ``counts`` używa kluczy ComponentCategory; find_gaps operuje na napisach.
    counts_by_name = {cat.value: row for cat, row in counts.items()}
    expected = {(c, s) for c, s in load_expected_gaps()}
    gaps = find_gaps(counts_by_name, CANONICAL_SOURCES, expected)
    gaps_to_confirm = [CategorySourceGap(g.category, g.source) for g in gaps]

    # Specyfikacje czasowe nieklasyfikowalne (trigger == UNCLASSIFIED).
    unclassified = catalog.query_timing(TriggerKind.UNCLASSIFIED)

    # Pokrycie efektów i statusy osierocone (status wskazuje nieistniejący komponent).
    effect_registry = EffectRegistry.load()
    effect_coverage = coverage(catalog, effect_registry)
    orphans = _orphan_statuses(catalog, effect_registry)

    # Komponenty „bez noty” reguł: kategorie z podpowiedzią tematu, dla których indeks
    # nie zwraca żadnego tematu (brak tirules.json ⇒ wszystkie „bez noty”, R10.3).
    no_rules_note = _components_without_rules_note(catalog)

    return AuditReport(
        counts=counts,
        skipped=dict(load.skipped),
        sourceless=dict(load.sourceless),
        conflicts=dict(load.conflicts),
        unresolved=list(scans.unresolved),
        suspicious=list(scans.suspicious),
        gaps_to_confirm=gaps_to_confirm,
        unclassified_timing=unclassified,
        effect_coverage=effect_coverage,
        manifest=scans.manifest,
        external_urls=list(scans.external_urls),
        frontend_diff=dict(scans.frontend_diff),
        no_rules_note=no_rules_note,
        orphan_effect_statuses=orphans,
        references_module_available=scans.references_module_available,
    )


def _orphan_statuses(
    catalog: ComponentCatalog, registry: EffectRegistry
) -> list[ComponentRef]:
    """Statusy efektów wskazujące komponent spoza katalogu (ostrzeżenie)."""
    orphans = [
        ref
        for ref in registry.statuses
        if catalog.get(ref.category, ref.id) is None
    ]
    return sorted(orphans, key=lambda ref: (ref.category.value, ref.id))


def _components_without_rules_note(catalog: ComponentCatalog) -> list[ComponentRef]:
    """Komponenty kategorii z podpowiedzią tematu, dla których indeks nie ma tematu.

    Brak ``tirules.json`` daje pusty indeks → wszystkie takie komponenty trafiają na
    listę „bez noty” (R10.3). Dopasowanie korzysta z ``RulesTopicIndex.match`` po
    nazwie/aliasie oraz podpowiedzi kategorialnej.
    """
    index = RulesTopicIndex.from_json()
    missing: list[ComponentRef] = []
    for category in ComponentCategory:
        if category.value not in CATEGORY_TOPIC_HINTS:
            continue
        for component_id, component in catalog.all(category).items():
            names = [n for n in (component.name, component.id) if n]
            if not index.match(*names, category=category.value):
                missing.append(ComponentRef(category, component_id))
    return sorted(missing, key=lambda ref: (ref.category.value, ref.id))


# --- Zbieranie skanów z dysku (cienka otoczka I/O) -----------------------


def _collect_unresolved(registry: StaticDataRegistry) -> tuple[list[str], bool]:
    """Nierozwiązane referencje z ``core/references.py`` (import obronny, zadanie 4.1).

    Gdy moduł jeszcze nie istnieje, używa ``registry.missing_planet_references`` jako
    substytutu i sygnalizuje, że pełna analiza była niedostępna.
    """
    def _fallback() -> tuple[list[str], bool]:
        missing = registry.missing_planet_references()
        lines = [
            f"system {system_id}: brak planet {planets}"
            for system_id, planets in sorted(missing.items())
        ]
        return lines, False

    # Import przez importlib, by mypy nie wymagał istnienia modułu tworzonego równolegle.
    try:
        references = importlib.import_module("src.core.references")
    except ImportError:
        return _fallback()

    find = getattr(references, "find_unresolved_references", None)
    if find is None:
        return _fallback()
    refs = find(registry)
    return [str(ref) for ref in refs], True


def _external_url_hits() -> list[ExternalUrlHit]:
    """Skanuje frontend pod kątem zewnętrznych URL spoza listy dozwolonej (R2.5)."""
    if not config.FRONTEND_DIR.is_dir():
        return []
    allowlist = load_allowlist()
    findings: list[LocalityFinding] = scan_external_urls(
        config.FRONTEND_DIR, _FRONTEND_URL_PATTERNS, allowlist
    )
    return [ExternalUrlHit(f.file, f.line, f.text) for f in findings]


def _frontend_diff(registry: StaticDataRegistry) -> dict[str, IdDiff]:
    """Różnice id wbudowanych we frontend vs katalog (R11.5), per plik danych."""
    embedded = scan_embedded_ids()
    if not embedded:
        return {}
    catalog = registry.catalog
    # Dla każdego pliku danych frontu porównaj z całą przestrzenią id katalogu.
    all_ids: set[str] = set()
    for category in ComponentCategory:
        all_ids.update(catalog.all(category).keys())
    return {stem: diff_embedded_ids(ids, all_ids) for stem, ids in embedded.items()}


def collect_scans(registry: StaticDataRegistry) -> AuditScans:
    """Zbiera wszystkie dane z dysku potrzebne audytowi (I/O w jednym miejscu)."""
    manifest_diff = diff_manifest(load_manifest_paths(), list_asset_files())
    unresolved, refs_available = _collect_unresolved(registry)
    return AuditScans(
        manifest=manifest_diff,
        external_urls=_external_url_hits(),
        frontend_diff=_frontend_diff(registry),
        suspicious=detect_suspicious(),
        unresolved=unresolved,
        references_module_available=refs_available,
    )


# --- Renderowanie i kod wyjścia ------------------------------------------


def exit_code(report: AuditReport) -> int:
    """Zwraca 1 przy błędzie krytycznym, 0 przy samych ostrzeżeniach (Property 14)."""
    return 1 if report.has_critical else 0


def _fmt_counts(counts: Mapping[ComponentCategory, Mapping[str, int]]) -> list[str]:
    lines: list[str] = []
    for category in sorted(counts, key=lambda c: c.value):
        row = counts[category]
        total = sum(row.values())
        by_source = ", ".join(f"{s}={n}" for s, n in sorted(row.items()))
        lines.append(f"  {category.value}: {total} ({by_source})" if by_source
                     else f"  {category.value}: 0")
    return lines


def render_text(report: AuditReport) -> str:
    """Buduje czytelny raport tekstowy ze wszystkimi sekcjami (R12.1)."""
    lines: list[str] = ["=== Audyt danych TI4 ===", "", "Liczby komponentów:"]
    lines.extend(_fmt_counts(report.counts) or ["  (brak)"])

    lines.append("")
    lines.append("Pominięte wpisy (nieaktywne źródła):")
    skipped_any = False
    for category in sorted(report.skipped, key=lambda c: c.value):
        row = report.skipped[category]
        if row:
            skipped_any = True
            by_source = ", ".join(f"{s}={n}" for s, n in sorted(row.items()))
            lines.append(f"  {category.value}: {by_source}")
    if not skipped_any:
        lines.append("  (brak)")

    lines.append("")
    lines.append(f"Wpisy bez źródła: {sum(len(v) for v in report.sourceless.values())}")
    lines.append(f"Kolizje id: {sum(len(v) for v in report.conflicts.values())}")

    lines.append("")
    lines.append("Wpisy podejrzane (źródło kanoniczne w pliku o nietypowej nazwie):")
    if report.suspicious:
        for entry in report.suspicious:
            lines.append(
                f"  {entry.category.value}/{entry.entry_id}: "
                f"source={entry.source} w pliku {entry.file_stem}.json"
            )
    else:
        lines.append("  (brak)")

    lines.append("")
    lines.append("Luki źródeł kanonicznych do potwierdzenia:")
    if report.gaps_to_confirm:
        lines.extend(f"  {g.category}: brak {g.source}" for g in report.gaps_to_confirm)
    else:
        lines.append("  (brak)")

    lines.append("")
    note = (
        ""
        if report.references_module_available
        else " (analiza częściowa: brak core/references.py)"
    )
    lines.append(f"Nierozwiązane referencje{note}:")
    if report.unresolved:
        lines.extend(f"  {line}" for line in report.unresolved)
    else:
        lines.append("  (brak)")

    lines.append("")
    lines.append(f"Specyfikacje czasowe 'unclassified': {len(report.unclassified_timing)}")
    for ref in report.unclassified_timing[:20]:
        lines.append(f"  {ref.category.value}/{ref.id}")

    lines.append("")
    lines.append("Pokrycie efektów:")
    if report.effect_coverage:
        for category in sorted(report.effect_coverage, key=lambda c: c.value):
            r = report.effect_coverage[category]
            lines.append(
                f"  {category.value}: {r.implemented}/{r.total} "
                f"({r.percent_implemented:.1f}%), manual={r.manual}"
            )
    else:
        lines.append("  (brak)")

    lines.append("")
    lines.append(f"Komponenty bez noty reguł: {len(report.no_rules_note)}")
    lines.append(f"Osierocone statusy efektów: {len(report.orphan_effect_statuses)}")
    for ref in report.orphan_effect_statuses[:20]:
        lines.append(f"  {ref.category.value}/{ref.id}")

    lines.append("")
    lines.append("Manifest grafik:")
    lines.append(f"  brakujące na dysku: {len(report.manifest.missing)}")
    lines.append(f"  nieużywane (na dysku, brak w manifeście): {len(report.manifest.unused)}")

    lines.append("")
    lines.append(f"Zewnętrzne URL spoza listy dozwolonej: {len(report.external_urls)}")
    for hit in report.external_urls[:20]:
        lines.append(f"  {hit.file}:{hit.line}: {hit.url}")

    lines.append("")
    lines.append("Różnice danych wbudowanych we frontend (plik: extra/missing):")
    nonempty = {k: d for k, d in report.frontend_diff.items() if not d.is_empty}
    if nonempty:
        for stem in sorted(nonempty):
            d = nonempty[stem]
            lines.append(f"  {stem}: extra={len(d.extra)}, missing={len(d.missing)}")
    else:
        lines.append("  (brak różnic)")

    if report.validation_error:
        lines.append("")
        lines.append(f"BŁĄD WALIDACJI: {report.validation_error}")

    lines.append("")
    lines.append(
        f"Wynik: {'BŁĘDY KRYTYCZNE' if report.has_critical else 'OK (same ostrzeżenia lub czysto)'}"
    )
    return "\n".join(lines)


# --- Zapis baseline/manifest ---------------------------------------------


def write_baseline(
    report: AuditReport, path: Path = BASELINE_COUNTS_PATH
) -> None:
    """Zapisuje liczby komponentów do ``baseline_counts.json`` (R6.4, R6.5).

    Kształt: ``{kategoria: {źródło: liczba}}`` — deterministycznie posortowany.
    Diff zatwierdza użytkownik przy commicie.
    """
    data = {
        category.value: {s: n for s, n in sorted(report.counts[category].items())}
        for category in sorted(report.counts, key=lambda c: c.value)
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --- CLI -----------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.audit",
        description="Audytor_Danych TI4: raport spójności lokalnej bazy danych.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="zapisz liczby komponentów do audit/baseline_counts.json",
    )
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        help="zapisz manifest grafik do audit/assets_manifest.json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="wypisz skrót raportu w formacie JSON zamiast tekstu",
    )
    return parser


def _report_json(report: AuditReport) -> str:
    """Zwięzły JSON z liczbami i licznikami ostrzeżeń/błędów (do CI)."""
    data = {
        "counts": {
            category.value: dict(sorted(report.counts[category].items()))
            for category in sorted(report.counts, key=lambda c: c.value)
        },
        "critical": report.has_critical,
        "unresolved": len(report.unresolved),
        "suspicious": len(report.suspicious),
        "gaps_to_confirm": len(report.gaps_to_confirm),
        "unclassified_timing": len(report.unclassified_timing),
        "no_rules_note": len(report.no_rules_note),
        "orphan_effect_statuses": len(report.orphan_effect_statuses),
        "manifest_missing": len(report.manifest.missing),
        "manifest_unused": len(report.manifest.unused),
        "external_urls": len(report.external_urls),
        "references_module_available": report.references_module_available,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    """Punkt wejścia CLI audytu (``python -m src.audit``)."""
    from src.core.component_loader import DataValidationError
    from src.core.registry import StaticDataRegistry

    args = _build_arg_parser().parse_args(argv)

    try:
        registry = StaticDataRegistry()
    except DataValidationError as exc:
        # Błąd modelu kanonicznego: rejestr nie wstał. Zgłaszamy jako krytyczny.
        report = AuditReport(validation_error=str(exc))
        print(render_text(report))
        return exit_code(report)

    report = build_report(registry, collect_scans(registry))

    if args.write_manifest:
        write_manifest(build_manifest())
    if args.write_baseline:
        write_baseline(report)

    print(_report_json(report) if args.json else render_text(report))
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
