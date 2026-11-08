"""Loader komponentów TI4: iteracja wpisów, filtr źródeł, kolizje ``id``, walidacja modeli.

Moduł nie zawiera danych ani reguł gry. Logika wyboru wpisów (``select_entries``)
jest CZYSTA (bez plików i modeli), więc daje się testować samymi słownikami.
Plik wejściowy ma kształt listy obiektów albo pojedynczego obiektu.

Reguły wyboru (design D9, RULES.md 14):
- wpis bez ``source`` (albo ze ``source`` nie będącym napisem) → ``sourceless``;
- ``source`` spoza aktywnych → licznik ``skipped`` i indeks ``skipped_index``;
- aktywny wpis bez poprawnego ``id`` → ``invalid_id``;
- kolizja ``id`` → wygrywa niższy ``source_rank``; remis rangi rozstrzyga
  wcześniejszy ``(file, index)``, więc wynik nie zależy od kolejności wejścia.
"""

from __future__ import annotations

import json
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from src.core.components import (
    CATEGORY_SPECS,
    CategorySpec,
    ComponentBase,
    ComponentCategory,
    build_component,
)
from src.core.sources import source_rank

RawEntry = dict[str, object]


def _without_non_agenda_variant_decks(
    entries: Iterable[tuple[EntryOrigin, Mapping[str, object]]],
    enabled: Collection[str],
    variant_sources: Collection[str],
) -> Iterator[tuple[EntryOrigin, Mapping[str, object]]]:
    """Pomija talie źródeł fanowskich innego typu niż ``agenda`` (np. karty akcji Absol).

    Talie źródeł z manifestu przechodzą bez zmian; źródła wariantowe (``variant_sources``),
    których nie ma w manifeście, wnoszą WYŁĄCZNIE talie agend.
    """
    for origin, entry in entries:
        source = entry.get("source")
        if (
            isinstance(source, str)
            and source in variant_sources
            and source not in enabled
            and entry.get("type") != "agenda"
        ):
            continue
        yield origin, entry


def _only_replacement_variant_notes(
    entries: Iterable[tuple[EntryOrigin, Mapping[str, object]]],
    enabled: Collection[str],
    variant_sources: Collection[str],
) -> Iterator[tuple[EntryOrigin, Mapping[str, object]]]:
    """Z notek źródeł wariantowych przepuszcza tylko ZAMIENNIKI oficjalnych notek.

    FAN-AGENDAS: zamiennik ma ``homebrewReplacesID`` (np. ``absol_<color>_ps`` →
    ``<color>_ps``); podmiana przy rozdawaniu: ``game_setup.common_promissory_note_ids``.
    """
    for origin, entry in entries:
        source = entry.get("source")
        if (
            isinstance(source, str)
            and source in variant_sources
            and source not in enabled
            and not isinstance(entry.get("homebrewReplacesID"), str)
        ):
            continue
        yield origin, entry


@dataclass(frozen=True)
class EntryOrigin:
    """Skąd pochodzi wpis: plik i numer wpisu w pliku (od 0)."""

    file: Path
    index: int


@dataclass(frozen=True)
class SourcelessEntry:
    """Wpis bez poprawnego pola ``source`` (pominięty)."""

    origin: EntryOrigin
    entry_id: object


@dataclass(frozen=True)
class InvalidIdEntry:
    """Aktywny wpis bez poprawnego identyfikatora (pominięty)."""

    origin: EntryOrigin
    source: str


@dataclass(frozen=True)
class IdConflict:
    """Kolizja ``id`` między aktywnymi wpisami: zwycięzca i przegrani."""

    entry_id: str
    winner: tuple[str, EntryOrigin]  # (source, origin)
    losers: tuple[tuple[str, EntryOrigin], ...]


@dataclass(frozen=True)
class Candidate:
    """Wpis wybrany do załadowania wraz z pochodzeniem."""

    origin: EntryOrigin
    source: str
    entry: RawEntry


@dataclass
class SelectionResult:
    """Wynik czystego wyboru wpisów dla jednej kategorii."""

    selected: dict[str, Candidate] = field(default_factory=dict)
    skipped: dict[str, int] = field(default_factory=dict)  # źródło -> liczba
    skipped_index: dict[str, str] = field(default_factory=dict)  # id -> źródło
    sourceless: list[SourcelessEntry] = field(default_factory=list)
    invalid_id: list[InvalidIdEntry] = field(default_factory=list)
    conflicts: list[IdConflict] = field(default_factory=list)


@dataclass
class LoadReport:
    """Raport ładowania wszystkich kategorii (liczby po deduplikacji)."""

    loaded: dict[ComponentCategory, dict[str, int]] = field(default_factory=dict)
    skipped: dict[ComponentCategory, dict[str, int]] = field(default_factory=dict)
    # kategoria -> id pominiętego (niekanonicznego) wpisu -> jego źródło.
    skipped_index: dict[ComponentCategory, dict[str, str]] = field(default_factory=dict)
    sourceless: dict[ComponentCategory, list[SourcelessEntry]] = field(default_factory=dict)
    invalid_id: dict[ComponentCategory, list[InvalidIdEntry]] = field(default_factory=dict)
    conflicts: dict[ComponentCategory, list[IdConflict]] = field(default_factory=dict)


class DataValidationError(ValueError):
    """Wpis aktywnego źródła nie spełnia modelu kategorii."""

    def __init__(
        self, category: ComponentCategory, file: Path, entry_id: str, detail: str
    ) -> None:
        self.category = category
        self.file = file
        self.entry_id = entry_id
        super().__init__(
            f"Invalid component entry: category={category.value}, "
            f"file={file}, id={entry_id}: {detail}"
        )


def _read_entries(path: Path) -> list[RawEntry]:
    """Czyta plik JSON jako listę wpisów (lista obiektów albo pojedynczy obiekt)."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [entry for entry in raw if isinstance(entry, dict)]
    if isinstance(raw, dict):
        return [raw]
    return []


def iter_entries_with_origin(directory: Path) -> Iterator[tuple[EntryOrigin, RawEntry]]:
    """Iteruje wpisy wszystkich ``*.json`` katalogu (alfabetycznie) z ich pochodzeniem."""
    for path in sorted(directory.glob("*.json")):
        for index, entry in enumerate(_read_entries(path)):
            yield EntryOrigin(path, index), entry


def _sort_key(candidate: Candidate) -> tuple[int, str, int]:
    return (
        source_rank(candidate.source),
        str(candidate.origin.file),
        candidate.origin.index,
    )


def select_entries(
    entries: Iterable[tuple[EntryOrigin, Mapping[str, object]]],
    enabled: Collection[str],
    id_field: str,
) -> SelectionResult:
    """Czysty wybór wpisów: filtr po ``source`` i rozstrzyganie kolizji ``id``."""
    result = SelectionResult()
    groups: dict[str, list[Candidate]] = {}
    for origin, entry in entries:
        source = entry.get("source")
        entry_id = entry.get(id_field)
        if not isinstance(source, str):
            result.sourceless.append(SourcelessEntry(origin, entry_id))
            continue
        if source not in enabled:
            result.skipped[source] = result.skipped.get(source, 0) + 1
            if isinstance(entry_id, str) and entry_id:
                known = result.skipped_index.get(entry_id)
                if known is None or source_rank(source) < source_rank(known) or (
                    source_rank(source) == source_rank(known) and source < known
                ):
                    result.skipped_index[entry_id] = source
            continue
        if not isinstance(entry_id, str) or not entry_id:
            result.invalid_id.append(InvalidIdEntry(origin, source))
            continue
        groups.setdefault(entry_id, []).append(Candidate(origin, source, dict(entry)))

    for entry_id, candidates in groups.items():
        ordered = sorted(candidates, key=_sort_key)
        result.selected[entry_id] = ordered[0]
        if len(ordered) > 1:
            result.conflicts.append(
                IdConflict(
                    entry_id,
                    (ordered[0].source, ordered[0].origin),
                    tuple((c.source, c.origin) for c in ordered[1:]),
                )
            )
    result.conflicts.sort(key=lambda conflict: conflict.entry_id)
    return result


def load_components(
    enabled: Collection[str],
    specs: Mapping[ComponentCategory, CategorySpec] | None = None,
    *,
    agenda_variant_sources: Collection[str] = (),
) -> tuple[dict[ComponentCategory, dict[str, ComponentBase]], LoadReport]:
    """Wczytuje komponenty wszystkich kategorii z ``CATEGORY_SPECS``.

    Args:
        enabled: Aktywne źródła (pole ``source`` wpisów).
        specs: Opcjonalna tabela kategorii (domyślnie ``CATEGORY_SPECS``).
        agenda_variant_sources: Dodatkowe źródła (fanowskie talie agend), ładowane WYŁĄCZNIE
            dla agend, talii agend i notek zastępujących oficjalne; reszta ich danych
            pozostaje nieaktywna.

    Raises:
        DataValidationError: Gdy wybrany wpis nie przechodzi walidacji modelu.
    """
    active_specs = CATEGORY_SPECS if specs is None else specs
    tables: dict[ComponentCategory, dict[str, ComponentBase]] = {}
    report = LoadReport()
    for category, spec in active_specs.items():
        category_enabled: Collection[str] = enabled
        entries: Iterable[tuple[EntryOrigin, Mapping[str, object]]] = (
            iter_entries_with_origin(spec.directory) if spec.directory.is_dir() else ()
        )
        if agenda_variant_sources and category in (
            ComponentCategory.AGENDA,
            ComponentCategory.DECK,
            ComponentCategory.PROMISSORY_NOTE,
        ):
            # FAN-AGENDAS: wariant Absol - ładujemy tylko agendy, talie agend i notki
            # ZASTĘPUJĄCE oficjalne (``homebrewReplacesID``, np. Absol's Political Secret).
            category_enabled = {*enabled, *agenda_variant_sources}
            if category is ComponentCategory.DECK:
                entries = _without_non_agenda_variant_decks(
                    entries, enabled, agenda_variant_sources
                )
            elif category is ComponentCategory.PROMISSORY_NOTE:
                entries = _only_replacement_variant_notes(
                    entries, enabled, agenda_variant_sources
                )
        selection = select_entries(entries, category_enabled, spec.id_field)
        table: dict[str, ComponentBase] = {}
        per_source: dict[str, int] = {}
        for entry_id in sorted(selection.selected):
            candidate = selection.selected[entry_id]
            try:
                table[entry_id] = build_component(candidate.entry, spec)
            except ValidationError as exc:
                raise DataValidationError(
                    category, candidate.origin.file, entry_id, str(exc)
                ) from exc
            per_source[candidate.source] = per_source.get(candidate.source, 0) + 1
        tables[category] = table
        report.loaded[category] = per_source
        report.skipped[category] = selection.skipped
        report.skipped_index[category] = selection.skipped_index
        report.sourceless[category] = selection.sourceless
        report.invalid_id[category] = selection.invalid_id
        report.conflicts[category] = selection.conflicts
    return tables, report
