"""Testy modułów różnic Audytora: manifest grafik, id wbudowane we froncie, liczniki, luki."""

from __future__ import annotations

from pathlib import Path

from src.audit.assets_manifest import (
    build_manifest,
    diff_manifest,
    list_asset_files,
    load_manifest_paths,
    write_manifest,
)
from src.audit.diffs import (
    CategorySourceGap,
    CountChange,
    diff_counts,
    find_gaps,
    load_expected_gaps,
)
from src.audit.frontend_data import diff_embedded_ids, extract_embedded_ids


def test_diff_manifest_missing_and_unused() -> None:
    diff = diff_manifest(["a.png", "b.png"], ["b.png", "c.png"])
    assert diff.missing == {"a.png"}
    assert diff.unused == {"c.png"}
    assert diff_manifest(["a.png"], ["a.png"]).is_empty


def test_build_manifest_roundtrip(tmp_path: Path) -> None:
    (tmp_path / "units").mkdir()
    (tmp_path / "units" / "x.png").write_bytes(b"abc")
    (tmp_path / "units" / "notes.txt").write_bytes(b"skip")
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "y.png").write_bytes(b"zzz")

    assert list_asset_files(tmp_path, ["units"]) == ["units/x.png"]
    manifest = build_manifest(tmp_path, ["units"])
    entry = manifest["files"][0]
    assert entry["path"] == "units/x.png"
    assert entry["size"] == 3
    assert len(str(entry["sha256"])) == 64

    target = tmp_path / "manifest.json"
    write_manifest(manifest, target)
    assert load_manifest_paths(target) == ["units/x.png"]
    assert load_manifest_paths(tmp_path / "brak.json") == []


def test_extract_embedded_ids_top_level_only() -> None:
    text = (
        "export const x = [\n"
        "  {\n"
        '    alias: "abolishment",\n'
        "    nested: {\n"
        '      id: "ignored",\n'
        "    },\n"
        "  },\n"
        "  {\n"
        "    id:\n"
        '      "arcane_citadel",\n'
        "  },\n"
        "];\n"
    )
    assert extract_embedded_ids(text) == {"abolishment", "arcane_citadel"}


def test_diff_embedded_ids() -> None:
    diff = diff_embedded_ids({"a", "b"}, {"b", "c"})
    assert diff.extra == {"a"}
    assert diff.missing == {"c"}
    assert diff_embedded_ids({"a"}, {"a"}).is_empty


def test_diff_counts_only_differences() -> None:
    baseline = {"agendas": {"base": 10, "pok": 5}}
    assert diff_counts(baseline, {"agendas": {"base": 10, "pok": 5}}) == {}
    changes = diff_counts(baseline, {"agendas": {"base": 11}, "relics": {"pok": 1}})
    assert changes == {
        ("agendas", "base"): CountChange(10, 11),
        ("agendas", "pok"): CountChange(5, None),
        ("relics", "pok"): CountChange(None, 1),
    }


def test_find_gaps_respects_expected() -> None:
    counts = {"agendas": {"base": 3}, "relics": {"base": 0, "pok": 2}}
    gaps = find_gaps(counts, ["base", "pok"], expected={("relics", "base")})
    assert gaps == [CategorySourceGap("agendas", "pok")]


def test_load_expected_gaps(tmp_path: Path) -> None:
    path = tmp_path / "gaps.json"
    path.write_text('[{"category": "agendas", "source": "codex1", "note": "x"}]', encoding="utf-8")
    assert load_expected_gaps(path) == {("agendas", "codex1")}
    assert load_expected_gaps(tmp_path / "brak.json") == frozenset()
