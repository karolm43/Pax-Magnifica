# ruff: noqa: E501
"""Testy katalogu zdarzeń i klasyfikatora okien czasowych (RULES.md 54)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.audit import timing_catalog
from src.core.components import ComponentCategory
from src.core.game_events import (
    EVENT_INFO,
    Duration,
    GameEvent,
    Moment,
    classify_window,
    deferred_phase,
    event_point,
    find_clauses,
    find_durations,
)
from src.core.registry import StaticDataRegistry

SRC = Path(__file__).resolve().parent.parent / "src"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.mark.parametrize(
    ("phrase", "event", "moment", "ctx"),
    [
        ("After you activate a system", GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, {}),
        ("When a player activates a system:", GameEvent.SYSTEM_ACTIVATED, Moment.WHEN, {}),
        ("At the start of the strategy phase", GameEvent.PHASE, Moment.START, {"phase": "strategy"}),
        ("At the end of the status phase", GameEvent.PHASE, Moment.END, {"phase": "status"}),
        ("At the start of the agenda phase", GameEvent.PHASE, Moment.START, {"phase": "agenda"}),
        ("When an agenda is revealed", GameEvent.AGENDA_REVEALED, Moment.WHEN, {}),
        ("After an agenda is revealed:", GameEvent.AGENDA_REVEALED, Moment.AFTER, {}),
        ("When you cast votes:", GameEvent.AGENDA_VOTES_CAST, Moment.WHEN, {}),
        ("When you gain control of a planet", GameEvent.PLANET_CONTROL_GAINED, Moment.WHEN, {}),
        ("At the start of a space combat", GameEvent.COMBAT, Moment.START, {}),
        ("At the start of a combat round", GameEvent.COMBAT_ROUND, Moment.START, {}),
        ("After you win a space combat", GameEvent.COMBAT_WON, Moment.AFTER, {}),
        ("Before you assign hits to your ships during a space combat", GameEvent.HITS_ASSIGNED, Moment.BEFORE, {}),
        ("When one of your ships uses sustain damage during combat", GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.WHEN, {}),
        ("After a player's unit is destroyed during combat:", GameEvent.UNIT_DESTROYED, Moment.AFTER, {}),
        ("When 1 or more of your units use production", GameEvent.PRODUCTION_USED, Moment.WHEN, {}),
        ("At the start of your turn", GameEvent.TURN, Moment.START, {}),
        ("At the end of a player's turn:", GameEvent.TURN, Moment.END, {}),
        ("After the last player passes", GameEvent.LAST_PLAYER_PASSED, Moment.AFTER, {}),
        ("When another player chooses a strategy card during the strategy phase", GameEvent.STRATEGY_CARD_CHOSEN, Moment.WHEN, {}),
        ("When you research a unit upgrade technology", GameEvent.TECHNOLOGY_RESEARCH, Moment.WHEN, {"unit_upgrade": "true"}),
        ("After you replenish commodities", GameEvent.COMMODITIES_REPLENISHED, Moment.AFTER, {}),
        ("When you are negotiating a transaction", GameEvent.TRANSACTION, Moment.WHEN, {}),
        ("ACTION:", GameEvent.COMPONENT_ACTION, Moment.ACTION, {}),
        ("At any time", GameEvent.ANY_TIME, Moment.ANY, {}),
    ],
)
def test_classify_window_przyklady(
    phrase: str, event: GameEvent, moment: Moment, ctx: dict[str, str]
) -> None:
    ref = classify_window(phrase)
    assert ref is not None, phrase
    assert (ref.event, ref.moment) == (event, moment)
    assert ref.ctx_dict() == ctx


def test_would_once_per_i_faza_nadrzedna() -> None:
    would = classify_window("When you would research a technology")
    assert would is not None and would.would
    once = classify_window("Once per agenda phase, after an agenda is revealed")
    assert once is not None and once.once_per == "agenda phase"
    assert (once.event, once.moment) == (GameEvent.AGENDA_REVEALED, Moment.AFTER)
    nested = classify_window("During the agenda phase, after an outcome that you voted for is resolved")
    assert nested is not None and nested.scope_hint == "agenda"
    assert (nested.event, nested.moment) == (GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER)


def test_each_time_i_whenever_to_moment_when() -> None:
    each = classify_window("Each time hits are produced against 1 or more of your ships")
    assert each is not None and each.moment is Moment.WHEN
    assert each.event is GameEvent.COMBAT_HITS_PRODUCED
    whenever = classify_window("Whenever the owner of this card replenishes their commodities")
    assert whenever is not None and whenever.event is GameEvent.COMMODITIES_REPLENISHED


def test_brak_okna_zwraca_none() -> None:
    assert classify_window(None) is None
    assert classify_window("   ") is None
    assert classify_window("You may exhaust this card") is None


def test_klauzule_tekstowe_tna_czesc_okna() -> None:
    clauses = find_clauses(
        "At the start of the strategy phase, players who voted Against must exhaust planets. "
        "After you activate a system, gain 1 trade good."
    )
    refs = [(c.window.event, c.window.moment) for c in clauses if c.window]
    assert refs == [
        (GameEvent.PHASE, Moment.START),
        (GameEvent.SYSTEM_ACTIVATED, Moment.AFTER),
    ]


def test_czasy_trwania_i_odroczone_wyzwalacze() -> None:
    assert Duration.COMBAT in find_durations("Apply +1 to the results of your rolls this combat")
    assert Duration.WHILE_IN_PLAY in find_durations("While this card is in your play area, you may")
    assert Duration.TACTICAL_ACTION in find_durations("Until the end of the tactical action")
    assert Duration.INVASION in find_durations("Until the end of the invasion, units gain")
    assert deferred_phase("At the start of the next strategy phase, each player exhausts") == "strategy"
    assert deferred_phase("At the start of your next turn, place a unit") == "next"
    assert deferred_phase("No timing here") is None


def test_event_point_i_info_dla_kazdego_zdarzenia() -> None:
    assert event_point(GameEvent.PHASE, Moment.START) == "event:phase:start"
    for event in GameEvent:
        assert event in EVENT_INFO, f"brak opisu zdarzenia {event}"


def test_wszystkie_pola_okien_w_danych_maja_zdarzenie(registry: StaticDataRegistry) -> None:
    """Każde pole ``window``/``abilityWindow`` aktywnych komponentów mapuje się na zdarzenie."""
    missing: list[str] = []
    for category in (
        ComponentCategory.ACTION_CARD,
        ComponentCategory.RELIC,
        ComponentCategory.PROMISSORY_NOTE,
        ComponentCategory.EXPLORATION,
        ComponentCategory.GALACTIC_EVENT,
        ComponentCategory.AGENDA,
    ):
        for cid, comp in registry.catalog.all(category).items():
            if comp.window and classify_window(comp.window) is None:
                missing.append(f"{category.value}:{cid}: {comp.window}")
    for cid, ability in registry.abilities.items():
        if ability.window and classify_window(ability.window) is None:
            missing.append(f"abilities:{cid}: {ability.window}")
    for cid, leader in registry.leaders.items():
        if leader.ability_window and classify_window(leader.ability_window) is None:
            missing.append(f"leaders:{cid}: {leader.ability_window}")
    assert not missing, "Okna bez zdarzenia:\n" + "\n".join(missing)


def _emitted_events() -> set[str]:
    """Zdarzenia faktycznie emitowane w ``src/core`` (pliki wołające ``triggers.fire``)."""
    emitted: set[str] = set()
    skip = {"game_events.py", "triggers.py", "rules_hooks.py"}
    for path in (SRC / "core").rglob("*.py"):
        if path.name in skip or "hooks" in path.parts:
            continue
        text = path.read_text(encoding="utf-8-sig")
        if "triggers.fire(" not in text:
            continue
        for block in re.finditer(r"triggers\.fire\(([^)]*(?:\([^)]*\)[^)]*)*)\)", text, re.S):
            emitted.update(re.findall(r"GameEvent\.(\w+)", block.group(1)))
    return emitted


def test_emitted_by_zgadza_sie_z_kodem() -> None:
    """Dokumentacja ``emitted_by`` nie może kłamać: deklarowane = faktycznie emitowane."""
    emitted = _emitted_events()
    declared = {event.name for event, info in EVENT_INFO.items() if info.emitted_by}
    assert declared - emitted == set(), f"deklarowane, ale nie emitowane: {sorted(declared - emitted)}"
    assert emitted - declared == set(), f"emitowane bez emitted_by: {sorted(emitted - declared)}"


def test_katalog_okien_jest_deterministyczny_i_pelny(registry: StaticDataRegistry) -> None:
    text = timing_catalog.render_markdown(registry)
    assert text == timing_catalog.render_markdown(registry)
    for header in (
        "## 1. Kontrakt silnika",
        "## 2. Zdarzenia",
        "## 4. Efekty trwałe",
        "## 5. Agendy (123: absol×60, base×50, pok×13)",
        "## 6. Frakcje",
        "## 9. Przypadki szczególne",
    ):
        assert header in text
    assert "| `absol_conscription` |" in text  # agendy Absol są w katalogu
    assert "* pole okna bez dopasowania: **0**" in text


def test_katalog_obejmuje_wszystkie_agendy(registry: StaticDataRegistry) -> None:
    entries = [e for e in timing_catalog.collect(registry) if e.category == "agendas"]
    assert len(entries) == len(registry.catalog.all(ComponentCategory.AGENDA))
    assert all(e.kind == "agenda" for e in entries)
    absol = [e for e in entries if e.source == "absol"]
    assert len(absol) == 60
    laws_with_phase = [e for e in absol if any(c.window for c in e.clauses)]
    assert laws_with_phase, "Agendy Absol mają klauzule czasowe w tekście"
