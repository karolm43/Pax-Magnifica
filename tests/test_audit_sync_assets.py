"""Testy przykładowe synchronizacji grafik (``src/audit/sync_assets.py``).

Pokrywają: kopiowanie brakujących plików z manifestu, pomijanie już obecnych,
listę „niezsynchronizowane" + niezerowy kod wyjścia, nienaruszalność katalogu
źródłowego (R12.8) oraz zachowanie przy braku ``--from`` (kod 2). Wymagania: 3.3, 12.8.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.audit.sync_assets import SyncResult, main, render_result, sync_assets


def _make_source(root: Path) -> None:
    """Przygotowuje katalog źródłowy z dwoma plikami w podkatalogu ``units``."""
    (root / "units").mkdir(parents=True)
    (root / "units" / "a.png").write_bytes(b"alpha")
    (root / "units" / "b.png").write_bytes(b"beta")


def test_sync_copies_missing_and_skips_present(tmp_path: Path) -> None:
    source = tmp_path / "ref"
    assets = tmp_path / "assets"
    _make_source(source)
    # Jeden plik jest już obecny w assets i musi zostać pominięty (nie nadpisany).
    (assets / "units").mkdir(parents=True)
    (assets / "units" / "a.png").write_bytes(b"EXISTING")

    result = sync_assets(
        source,
        manifest_paths=["units/a.png", "units/b.png"],
        assets_dir=assets,
    )

    assert result.copied == ("units/b.png",)
    assert result.already_present == ("units/a.png",)
    assert result.unsynced == ()
    assert not result.has_unsynced
    # Obecny plik nie został nadpisany zawartością ze źródła.
    assert (assets / "units" / "a.png").read_bytes() == b"EXISTING"
    # Skopiowany plik ma treść ze źródła.
    assert (assets / "units" / "b.png").read_bytes() == b"beta"


def test_sync_reports_unsynced_when_source_missing_file(tmp_path: Path) -> None:
    source = tmp_path / "ref"
    assets = tmp_path / "assets"
    _make_source(source)  # brak pliku units/c.png w źródle

    result = sync_assets(
        source,
        manifest_paths=["units/a.png", "units/c.png"],
        assets_dir=assets,
    )

    assert result.copied == ("units/a.png",)
    assert result.unsynced == ("units/c.png",)
    assert result.has_unsynced
    assert "units/c.png" in render_result(result)


def test_sync_never_modifies_source_dir(tmp_path: Path) -> None:
    """Katalog źródłowy pozostaje nietknięty po synchronizacji (R12.8)."""
    source = tmp_path / "ref"
    assets = tmp_path / "assets"
    _make_source(source)

    before = {
        p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in source.rglob("*")
        if p.is_file()
    }

    sync_assets(source, manifest_paths=["units/a.png", "units/b.png"], assets_dir=assets)

    after = {
        p.relative_to(source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in source.rglob("*")
        if p.is_file()
    }
    assert after == before


def test_sync_result_defaults_empty() -> None:
    assert SyncResult().unsynced == ()
    assert not SyncResult().has_unsynced


def test_main_exit_code_nonzero_on_unsynced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "ref"
    assets = tmp_path / "assets"
    _make_source(source)
    assets.mkdir()

    # Manifest wskazuje plik nieobecny w źródle → niezerowy kod wyjścia.
    monkeypatch.setattr(
        "src.audit.sync_assets.load_manifest_paths", lambda _path: ["units/a.png", "units/c.png"]
    )
    monkeypatch.setattr("src.audit.sync_assets.config.ASSETS_DIR", assets)

    code = main(["--from", str(source)])
    assert code == 1
    assert "units/c.png" in capsys.readouterr().out


def test_main_exit_code_zero_when_all_synced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "ref"
    assets = tmp_path / "assets"
    _make_source(source)
    assets.mkdir()

    monkeypatch.setattr(
        "src.audit.sync_assets.load_manifest_paths", lambda _path: ["units/a.png", "units/b.png"]
    )
    monkeypatch.setattr("src.audit.sync_assets.config.ASSETS_DIR", assets)

    assert main(["--from", str(source)]) == 0


def test_main_missing_from_exits_with_code_2() -> None:
    """Brak ``--from`` = argparse zgłasza SystemExit z kodem 2 (komunikat o użyciu)."""
    with pytest.raises(SystemExit) as excinfo:
        main([])
    assert excinfo.value.code == 2
