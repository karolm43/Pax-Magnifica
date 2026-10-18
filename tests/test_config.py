"""Testy konfiguracji ścieżek i manifestu aktywnych źródeł."""

from __future__ import annotations

import json

from src import config


def test_asset_paths_exist() -> None:
    """Wszystkie kluczowe ścieżki do assetów istnieją na dysku."""
    assert config.ASSETS_DIR.is_dir()
    assert config.DATA_DIR.is_dir()
    assert config.SYSTEMS_DIR.is_dir()
    assert config.PLANETS_DIR.is_dir()
    assert config.UNITS_DATA_DIR.is_dir()
    assert config.SOURCES_PATH.is_file()
    assert config.ENABLED_SOURCES_PATH.is_file()


def test_enabled_sources_loads() -> None:
    """Manifest ładuje się jako niepusta lista napisów."""
    sources = config.load_enabled_sources()
    assert isinstance(sources, list)
    assert len(sources) > 0
    assert all(isinstance(s, str) for s in sources)


def test_enabled_sources_are_official() -> None:
    """Każde aktywne źródło występuje w sources.json z canal == 'official'."""
    enabled = config.load_enabled_sources()
    raw_sources = json.loads(config.SOURCES_PATH.read_text(encoding="utf-8"))
    canal_by_source = {entry["source"]: entry.get("canal") for entry in raw_sources}

    for source_id in enabled:
        assert source_id in canal_by_source, f"Źródło '{source_id}' nieznane w sources.json"
        assert canal_by_source[source_id] == "official", (
            f"Źródło '{source_id}' nie jest oficjalne (canal={canal_by_source[source_id]})"
        )
