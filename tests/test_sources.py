"""Testy modułu ``core/sources.py``: priorytet i walidacja źródeł."""

from __future__ import annotations

import pytest

from src import config
from src.core.registry import StaticDataRegistry
from src.core.sources import (
    SOURCE_PRIORITY,
    UnknownSourcesError,
    known_source_ids,
    source_rank,
    validate_enabled_sources,
)


def test_source_rank_follows_priority() -> None:
    ranks = [source_rank(s) for s in SOURCE_PRIORITY]
    assert ranks == sorted(ranks)
    assert source_rank("thunders_edge") < source_rank("base")


def test_source_rank_unknown_is_lowest() -> None:
    assert source_rank("nieznane") == len(SOURCE_PRIORITY)


def test_enabled_manifest_is_known() -> None:
    validate_enabled_sources(config.load_enabled_sources(), known_source_ids())


def test_validate_reports_sorted_unknown() -> None:
    with pytest.raises(UnknownSourcesError) as exc:
        validate_enabled_sources(["zzz", "base", "aaa"], {"base"})
    assert exc.value.unknown == ["aaa", "zzz"]


def test_registry_rejects_unknown_source() -> None:
    with pytest.raises(UnknownSourcesError):
        StaticDataRegistry(enabled_sources=["base", "nie_istnieje"])
