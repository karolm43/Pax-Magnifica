"""Testy ``core/rules_links.py`` (R10.1-10.4)."""

from __future__ import annotations

from pathlib import Path

from src.core.rules_links import CATEGORY_TOPIC_HINTS, RulesTopic, RulesTopicIndex, normalize


def _index() -> RulesTopicIndex:
    return RulesTopicIndex(
        [
            RulesTopic("C_action_cards", "component", "Action Cards"),
            RulesTopic("F_argent", "faction", "The Argent Flight"),
            RulesTopic("R_anomalies", "rule", "Anomalies"),
        ]
    )


def test_normalize_ignores_case_and_punctuation() -> None:
    assert normalize("The Argent-Flight!") == "theargentflight"


def test_match_equality_on_title_and_code() -> None:
    idx = _index()
    assert [t.code for t in idx.match("the ARGENT flight")] == ["F_argent"]
    assert [t.code for t in idx.match("anomalies")] == ["R_anomalies"]
    assert [t.code for t in idx.match("C_action_cards")] == ["C_action_cards"]


def test_stripped_code_matches_by_equality() -> None:
    # "argent" == znormalizowany kod F_argent po usunięciu prefiksu (równość, nie zgadywanie).
    assert [t.code for t in _index().match("Argent")] == ["F_argent"]


def test_no_fuzzy_matching() -> None:
    # Częściowe/zbliżone nazwy nie trafiają — tylko pełna równość znormalizowana.
    assert _index().match("Anomaly", "ActionCard", "Flight", "") == []


def test_category_hint_added_and_deduplicated() -> None:
    idx = _index()
    named = idx.match("Action Cards", category="action_cards")
    assert [t.code for t in named] == ["C_action_cards"]
    hinted = idx.match("Sabotage", category="action_cards")
    assert [t.code for t in hinted] == ["C_action_cards"]
    assert idx.match("Sabotage", category="agendas") == []  # temat spoza indeksu pomijany
    assert idx.match("Sabotage", category="nieznana") == []


def test_missing_or_broken_file_gives_empty_index(tmp_path: Path) -> None:
    assert len(RulesTopicIndex.from_json(tmp_path / "brak.json")) == 0
    bad = tmp_path / "bad.json"
    bad.write_text("{nie json", encoding="utf-8")
    assert len(RulesTopicIndex.from_json(bad)) == 0


def test_real_dump_hints_resolve() -> None:
    idx = RulesTopicIndex.from_json()
    assert len(idx) > 100
    for codes in CATEGORY_TOPIC_HINTS.values():
        for code in codes:
            assert idx.get(code) is not None
    assert idx.match("Anomalies")
