"""Testy skanerów lokalności ``audit/locality.py`` (przykłady na krótkich tekstach)."""

from __future__ import annotations

from pathlib import Path

from src import config
from src.audit.locality import (
    collect_sources,
    find_external_urls,
    find_outside_root_reads,
    find_reference_path_usage,
    load_allowlist,
    load_unused_asset_dirs,
    scan_external_urls,
)

_NAMES = ["refdir"]


def test_reference_usage_ignores_docstrings_and_comments() -> None:
    code = '"""Zob. refdir."""\n# refdir w komentarzu\nx = 1\n'
    assert find_reference_path_usage({"a.py": code}, _NAMES) == []


def test_reference_usage_flags_code_literal() -> None:
    code = 'p = "../refdir/data"\n'
    found = find_reference_path_usage({"a.py": code}, _NAMES)
    assert [(f.file, f.line, f.text) for f in found] == [("a.py", 1, "refdir")]


def test_reference_usage_scans_non_python_text() -> None:
    found = find_reference_path_usage({"v.ts": "a\nimport 'refdir/x'\n"}, _NAMES)
    assert [f.line for f in found] == [2]


def test_outside_root_reads() -> None:
    code = 'a = "C:\\\\dane\\\\x"\nb = "../x"\nc = "/static"\nd = "/home/u/x"\n'
    found = find_outside_root_reads({"a.py": code})
    assert [f.line for f in found] == [1, 2, 4]


def test_outside_root_allows_paths_under_root() -> None:
    code = 'a = "C:/proj/assets/x"\n'
    assert find_outside_root_reads({"a.py": code}, project_root="C:\\proj") == []


def test_external_urls_respect_allowlist_and_local_hosts() -> None:
    text = (
        "http://localhost:8000/a\n"
        "http://127.0.0.1/b\n"
        "https://www.tirules2.com/x\n"
        "https://www.tirules2.com.evil.io/x\n"
        "https://cdn.example.com/img.png\n"
    )
    found = find_external_urls(text, ["https://www.tirules2.com"], file="f.ts")
    assert [f.text for f in found] == [
        "https://www.tirules2.com.evil.io/x",
        "https://cdn.example.com/img.png",
    ]
    assert found[0].file == "f.ts"


def test_scan_external_urls_skips_test_files(tmp_path: Path) -> None:
    (tmp_path / "a.ts").write_text("https://x.io/a", encoding="utf-8")
    (tmp_path / "a.test.ts").write_text("https://y.io/a", encoding="utf-8")
    assert set(collect_sources(tmp_path, ["*.ts"])) == {"a.ts", "a.test.ts"}
    found = scan_external_urls(tmp_path, ["*.ts"], [])
    assert [f.file for f in found] == ["a.ts"]


def test_audit_config_files_load() -> None:
    assert (config.AUDIT_DIR / "expected_gaps.json").read_text(encoding="utf-8").strip() == "[]"
    assert "https://ti4battle.com" in load_allowlist()
    assert "hover_images" in load_unused_asset_dirs()
