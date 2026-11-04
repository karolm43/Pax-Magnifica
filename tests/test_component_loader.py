"""Testy loadera komponentów na tmp_path (bez realnych assetów)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.component_loader import (
    DataValidationError,
    EntryOrigin,
    iter_entries_with_origin,
    load_components,
    select_entries,
)
from src.core.components import CATEGORY_SPECS, CategorySpec, ComponentCategory


def _write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _specs(directory: Path) -> dict[ComponentCategory, CategorySpec]:
    base = CATEGORY_SPECS[ComponentCategory.AGENDA]
    return {
        ComponentCategory.AGENDA: CategorySpec(
            base.category, directory, base.model, base.id_field, base.text_fields
        )
    }


def test_iter_entries_zachowuje_plik_i_indeks(tmp_path: Path) -> None:
    _write(tmp_path / "b.json", [{"alias": "x"}, {"alias": "y"}])
    _write(tmp_path / "a.json", {"alias": "z"})
    got = [(o.file.name, o.index, e["alias"]) for o, e in iter_entries_with_origin(tmp_path)]
    assert got == [("a.json", 0, "z"), ("b.json", 0, "x"), ("b.json", 1, "y")]


def test_select_entries_filtr_brak_zrodla_i_kolizja() -> None:
    f = Path("f.json")
    entries: list[tuple[EntryOrigin, dict[str, object]]] = [
        (EntryOrigin(f, 0), {"alias": "a", "source": "base"}),
        (EntryOrigin(f, 1), {"alias": "a", "source": "pok"}),  # wygrywa (wyższy priorytet)
        (EntryOrigin(f, 2), {"alias": "b"}),  # bez źródła
        (EntryOrigin(f, 3), {"alias": "c", "source": "absol"}),  # nieaktywne
        (EntryOrigin(f, 4), {"source": "base"}),  # bez id
        (EntryOrigin(f, 5), {"alias": "d", "source": 5}),  # źródło nie-napis
    ]
    result = select_entries(entries, {"base", "pok"}, "alias")
    assert result.selected["a"].source == "pok"
    assert [c.entry_id for c in result.conflicts] == ["a"]
    assert len(result.sourceless) == 2
    assert result.skipped == {"absol": 1}
    assert result.skipped_index == {"c": "absol"}
    assert len(result.invalid_id) == 1


def test_select_entries_remis_rangi_nie_zalezy_od_kolejnosci() -> None:
    e1 = (EntryOrigin(Path("a.json"), 3), {"alias": "a", "source": "base", "n": 1})
    e2 = (EntryOrigin(Path("b.json"), 0), {"alias": "a", "source": "base", "n": 2})
    for order in ([e1, e2], [e2, e1]):
        assert select_entries(order, {"base"}, "alias").selected["a"].entry["n"] == 1


def test_load_components_ladowanie_i_raport(tmp_path: Path) -> None:
    _write(tmp_path / "a.json", [
        {"alias": "law", "name": "Law", "source": "base"},
        {"alias": "hb", "name": "Hb", "source": "absol"},
    ])
    tables, report = load_components({"base"}, _specs(tmp_path))
    assert list(tables[ComponentCategory.AGENDA]) == ["law"]
    assert report.loaded[ComponentCategory.AGENDA] == {"base": 1}
    assert report.skipped_index[ComponentCategory.AGENDA] == {"hb": "absol"}


def test_load_components_blad_modelu_niesie_kontekst(tmp_path: Path) -> None:
    _write(tmp_path / "bad.json", [{"alias": "x", "source": "base", "type": 5}])
    with pytest.raises(DataValidationError) as info:
        load_components({"base"}, _specs(tmp_path))
    assert info.value.category is ComponentCategory.AGENDA
    assert info.value.file.name == "bad.json"
    assert info.value.entry_id == "x"
