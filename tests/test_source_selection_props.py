"""Testy właściwościowe wyboru i walidacji źródeł danych."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.sources import UnknownSourcesError, validate_enabled_sources

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
