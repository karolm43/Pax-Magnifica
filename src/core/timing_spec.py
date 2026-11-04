"""Specyfikacja czasowa komponentów (okno użycia: when/after/before/...).

Moduł tłumaczy frazy okien z danych JSON (``window``, ``abilityWindow``) na
strukturę ``TimingSpec``. Klasyfikacja jest w pełni deterministyczna i opiera się
WYŁĄCZNIE na prefiksach frazy (design: ``core/timing_spec.py``, R8.2) — żadnej
wiedzy o kartach z pamięci. Tekst okna zostaje bez zmian w ``raw_text`` (R8.5).

Moduł tylko IMPORTUJE ``WindowType`` i ``Phase``; ``core/timing.py`` i ``WindowType``
nie są modyfikowane (R8.8).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from src.core.game_state import Phase, WindowType


class TriggerKind(StrEnum):
    """Rodzaj wyzwalacza okna (zbiór zamknięty, R8.1)."""

    WHEN = "when"
    AFTER = "after"
    BEFORE = "before"
    INSTEAD = "instead"
    AT_START = "at_start"
    AT_END = "at_end"
    DURING = "during"
    ACTION = "action"
    UNCLASSIFIED = "unclassified"


# Wartości pola ``playTiming`` w danych kart akcji — służą WYŁĄCZNIE do pola
# ``play_timing_agrees`` (porównanie z klasyfikacją), nie zmieniają klasyfikacji.
AGENDA_WHEN = "AGENDA_WHEN"
AGENDA_AFTER = "AGENDA_AFTER"

# Odwzorowanie rodzaju wyzwalacza na typ okna silnika (decyzja D10).
# ⚠️ ZAŁOŻENIE (RULES.md 34): when/after/before/instead → REACTION (uniwersalne
# okno „when/after"); pozostałe rodzaje → None („brak okna" — nie są reakcją).
TRIGGER_WINDOW_MAP: Mapping[TriggerKind, WindowType | None] = MappingProxyType(
    {
        TriggerKind.WHEN: WindowType.REACTION,
        TriggerKind.AFTER: WindowType.REACTION,
        TriggerKind.BEFORE: WindowType.REACTION,
        TriggerKind.INSTEAD: WindowType.REACTION,
        TriggerKind.AT_START: None,
        TriggerKind.AT_END: None,
        TriggerKind.DURING: None,
        TriggerKind.ACTION: None,
        TriggerKind.UNCLASSIFIED: None,
    }
)

# Kolejność ma znaczenie tylko dla czytelności: prefiksy są rozłączne.
_PREFIX_RULES: tuple[tuple[re.Pattern[str], TriggerKind], ...] = (
    (re.compile(r"when\s"), TriggerKind.WHEN),
    (re.compile(r"after\s"), TriggerKind.AFTER),
    (re.compile(r"before\s"), TriggerKind.BEFORE),
    (re.compile(r"instead of"), TriggerKind.INSTEAD),
    (re.compile(r"at the start"), TriggerKind.AT_START),
    (re.compile(r"at the end"), TriggerKind.AT_END),
    (re.compile(r"during\s"), TriggerKind.DURING),
    # „action" jako całe słowo (np. „ACTION:" albo samo „Action").
    (re.compile(r"action(?![^\W_])"), TriggerKind.ACTION),
)


@dataclass(frozen=True)
class TimingSpec:
    """Specyfikacja czasowa jednego komponentu."""

    raw_text: str  # dokładnie jak w JSON (R8.5), bez trim/normalizacji
    trigger: TriggerKind
    phase_raw: str | None  # pole ``phase`` z JSON bez zmian
    phase: Phase | None  # tylko gdy ``phase_raw`` pasuje do ``Phase`` (bez wielkości liter)
    play_timing: str | None  # pole ``playTiming`` bez zmian
    # None = brak playTiming (lub wartość nieznana); False = sprzeczność z oknem.
    play_timing_agrees: bool | None
    source_field: str  # z jakiego pola JSON pochodzi fraza (window / abilityWindow)
    effect_text: str | None  # ``windowEffect`` zachowany, nieparsowany
    window_type: WindowType | None  # wynik ``TRIGGER_WINDOW_MAP``


def classify_trigger(text: str) -> TriggerKind:
    """Klasyfikuje frazę okna po prefiksie (casefold, bez wiodących białych znaków)."""
    normalized = text.casefold().lstrip()
    for pattern, kind in _PREFIX_RULES:
        if pattern.match(normalized):
            return kind
    return TriggerKind.UNCLASSIFIED


def _parse_phase(phase_raw: str | None) -> Phase | None:
    if phase_raw is None:
        return None
    candidate = phase_raw.strip().upper()
    try:
        return Phase(candidate)
    except ValueError:
        return None


def _play_timing_agrees(play_timing: str | None, trigger: TriggerKind) -> bool | None:
    if play_timing == AGENDA_WHEN:
        return trigger is TriggerKind.WHEN
    if play_timing == AGENDA_AFTER:
        return trigger is TriggerKind.AFTER
    return None


def parse_timing(
    window: str | None,
    *,
    phase: str | None = None,
    play_timing: str | None = None,
    source_field: str = "window",
    effect_text: str | None = None,
) -> TimingSpec | None:
    """Buduje ``TimingSpec`` z frazy okna; ``None`` gdy fraza jest pusta lub brak."""
    if window is None or not window.strip():
        return None
    trigger = classify_trigger(window)
    return TimingSpec(
        raw_text=window,
        trigger=trigger,
        phase_raw=phase,
        phase=_parse_phase(phase),
        play_timing=play_timing,
        play_timing_agrees=_play_timing_agrees(play_timing, trigger),
        source_field=source_field,
        effect_text=effect_text,
        window_type=TRIGGER_WINDOW_MAP[trigger],
    )
