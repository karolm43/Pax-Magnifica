"""Testy przykładowe specyfikacji czasowej (core/timing_spec.py)."""

from __future__ import annotations

import pytest

from src.core.game_state import Phase, WindowType
from src.core.models import LeaderDef
from src.core.timing_spec import TRIGGER_WINDOW_MAP, TriggerKind, parse_timing


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("When an agenda is revealed", TriggerKind.WHEN),
        ("  AFTER an agenda is revealed", TriggerKind.AFTER),
        ("Before you roll", TriggerKind.BEFORE),
        ("Instead of producing units", TriggerKind.INSTEAD),
        ("At the start of a space combat", TriggerKind.AT_START),
        ("At the end of a combat between any players:", TriggerKind.AT_END),
        ("During the Agenda phase, after an outcome", TriggerKind.DURING),
        ("ACTION:", TriggerKind.ACTION),
        ("Action", TriggerKind.ACTION),
        ("Actions are cool", TriggerKind.UNCLASSIFIED),
        ("At any time", TriggerKind.UNCLASSIFIED),
    ],
)
def test_klasyfikacja_po_prefiksie(text: str, kind: TriggerKind) -> None:
    spec = parse_timing(text)
    assert spec is not None
    assert spec.trigger is kind
    assert spec.raw_text == text


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_brak_frazy_to_brak_specyfikacji(empty: str | None) -> None:
    assert parse_timing(empty) is None


def test_phase_play_timing_i_effect() -> None:
    spec = parse_timing(
        "When an agenda is revealed",
        phase="Agenda",
        play_timing="AGENDA_WHEN",
        effect_text="efekt",
    )
    assert spec is not None
    assert spec.phase is Phase.AGENDA
    assert spec.phase_raw == "Agenda"
    assert spec.play_timing_agrees is True
    assert spec.effect_text == "efekt"
    assert spec.window_type is WindowType.REACTION


def test_play_timing_sprzeczny_i_brak() -> None:
    sprzeczny = parse_timing("After an agenda is revealed", play_timing="AGENDA_WHEN")
    assert sprzeczny is not None
    assert sprzeczny.play_timing_agrees is False
    brak = parse_timing("After an agenda is revealed")
    assert brak is not None
    assert brak.play_timing_agrees is None
    assert parse_timing("x", phase="Nieznana").phase is None  # type: ignore[union-attr]


def test_mapa_okien_calkowita() -> None:
    assert set(TRIGGER_WINDOW_MAP) == set(TriggerKind)
    assert TRIGGER_WINDOW_MAP[TriggerKind.DURING] is None


def test_leader_def_czyta_ability_window() -> None:
    leader = LeaderDef.model_validate(
        {
            "id": "x",
            "type": "agent",
            "name": "X",
            "source": "base",
            "abilityWindow": "ACTION:",
        }
    )
    assert leader.ability_window == "ACTION:"
