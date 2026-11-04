"""Testy właściwościowe specyfikacji czasowej.

Obejmuje:
- Property 7: parse_timing zachowuje tekst okna i zwraca rodzaj z zamkniętego zbioru;
- Property 8: klasyfikacja wyzwalacza jest deterministyczna i oparta tylko na prefiksie;
- Property 9: query_timing zgadza się z modelem referencyjnym.

Hypothesis z min. 100 iteracjami. Żadnych reguł ani danych kart z pamięci —
testujemy wyłącznie czyste funkcje z ``core/timing_spec.py`` i ``core/components.py``.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.core.components import (
    ComponentCatalog,
    ComponentCategory,
    ComponentRef,
)
from src.core.game_state import Phase
from src.core.timing_spec import (
    TimingSpec,
    TriggerKind,
    classify_trigger,
    parse_timing,
)

# Nazwy faz w różnej wielkości liter — pole ``phase`` w JSON bywa „Agenda"/„agenda".
_PHASE_NAMES = [p.value for p in Phase]
_phase_text = st.sampled_from(
    [name for p in _PHASE_NAMES for name in (p, p.lower(), p.capitalize())]
)
# Dowolne pole fazy: None, nazwa fazy (różna wielkość liter) albo tekst losowy.
_phase_field = st.one_of(st.none(), _phase_text, st.text(max_size=12))

# Dowolny tekst okna (także z białymi znakami i znakami specjalnymi).
_window_text = st.text(max_size=60)

# Znane prefiksy wyzwalaczy i odpowiadający im rodzaj (z ``_PREFIX_RULES``).
_KNOWN_PREFIXES: list[tuple[str, TriggerKind]] = [
    ("when ", TriggerKind.WHEN),
    ("after ", TriggerKind.AFTER),
    ("before ", TriggerKind.BEFORE),
    ("instead of", TriggerKind.INSTEAD),
    ("at the start", TriggerKind.AT_START),
    ("at the end", TriggerKind.AT_END),
    ("during ", TriggerKind.DURING),
    ("action", TriggerKind.ACTION),
]


def _mixed_case(text: str, seed: int) -> str:
    """Zmienia wielkość liter deterministycznie na podstawie ``seed``."""
    out: list[str] = []
    for i, ch in enumerate(text):
        out.append(ch.upper() if (seed >> (i % 8)) & 1 else ch.lower())
    return "".join(out)


# Feature: local-ti4-data-foundation, Property 7: Specyfikacja czasowa zachowuje
# tekst okna i zamyka zbiór rodzajów
@settings(max_examples=200)
@given(window=_window_text, phase=_phase_field)
def test_parse_timing_zachowuje_tekst_i_zamyka_zbior_rodzajow(
    window: str, phase: str | None
) -> None:
    """**Validates: Requirements 8.1, 8.3, 8.5**"""
    spec = parse_timing(window, phase=phase)
    if not window.strip():
        # Tekst pusty lub same białe znaki → brak specyfikacji.
        assert spec is None
        return
    assert spec is not None
    # Tekst okna zachowany co do znaku (R8.5).
    assert spec.raw_text == window
    # Rodzaj wyzwalacza należy do zamkniętego zbioru (R8.1).
    assert spec.trigger in set(TriggerKind)
    # Pole fazy zachowane bez zmian.
    assert spec.phase_raw == phase
    # ``phase`` ustawione tylko gdy ``phase_raw`` pasuje do Phase (bez wielkości liter).
    if phase is not None and phase.strip().upper() in {p.value for p in Phase}:
        assert spec.phase is Phase(phase.strip().upper())
    else:
        assert spec.phase is None


# Feature: local-ti4-data-foundation, Property 8: Klasyfikacja wyzwalacza jest
# deterministyczna i oparta tylko na prefiksie
@settings(max_examples=200)
@given(
    prefix_idx=st.integers(min_value=0, max_value=len(_KNOWN_PREFIXES) - 1),
    case_seed=st.integers(min_value=0, max_value=255),
    leading=st.text(alphabet=" \t\n", max_size=5),
    rest=st.text(max_size=40),
)
def test_klasyfikacja_po_prefiksie_deterministyczna(
    prefix_idx: int, case_seed: int, leading: str, rest: str
) -> None:
    """**Validates: Requirements 8.2, 8.3**"""
    prefix, expected = _KNOWN_PREFIXES[prefix_idx]
    # „action" jest rozpoznawane jako całe słowo (design: ``action(?![^\\W_])``),
    # więc dalszy ciąg musi zaczynać się od znaku niebędącego częścią słowa.
    if expected is TriggerKind.ACTION and rest and (rest[0].isalnum() or rest[0] == "_"):
        rest = " " + rest
    text = leading + _mixed_case(prefix, case_seed) + rest
    # Znany prefiks (dowolna wielkość liter, dowolne wiodące białe znaki) → ten rodzaj.
    assert classify_trigger(text) is expected
    # Determinizm: dwa wywołania dają równy wynik.
    assert classify_trigger(text) == classify_trigger(text)
    spec = parse_timing(text)
    assert spec is not None
    assert spec.trigger is expected


# Feature: local-ti4-data-foundation, Property 8 (cd.): klasyfikacja zależy wyłącznie
# od treści (determinizm), a brak znanego prefiksu → UNCLASSIFIED z zachowanym tekstem
@settings(max_examples=200)
@given(window=_window_text)
def test_klasyfikacja_jest_funkcja_tylko_tekstu(window: str) -> None:
    """**Validates: Requirements 8.2, 8.3**"""
    # Determinizm: wynik zależy tylko od tekstu, dwa wywołania są równe.
    assert classify_trigger(window) == classify_trigger(window)
    kind = classify_trigger(window)
    assert kind in set(TriggerKind)
    # Gdy rodzaj to UNCLASSIFIED, tekst nadal jest zachowany (o ile niepusty).
    if kind is TriggerKind.UNCLASSIFIED and window.strip():
        spec = parse_timing(window)
        assert spec is not None
        assert spec.raw_text == window
        assert spec.trigger is TriggerKind.UNCLASSIFIED


# ---- Property 9: generator katalogu ze specyfikacjami czasowymi ----

_trigger = st.sampled_from(list(TriggerKind))
_opt_phase = st.one_of(st.none(), st.sampled_from(list(Phase)))


def _timing_spec(trigger: TriggerKind, phase: Phase | None) -> TimingSpec:
    """Buduje ``TimingSpec`` o zadanym rodzaju i fazie (reszta pól neutralna)."""
    return TimingSpec(
        raw_text="x",
        trigger=trigger,
        phase_raw=None if phase is None else phase.value,
        phase=phase,
        play_timing=None,
        play_timing_agrees=None,
        source_field="window",
        effect_text=None,
        window_type=None,
    )


# Każdy wpis: (indeks referencji, rodzaj, faza). Indeks zapewnia unikalny ComponentRef.
_spec_entry = st.tuples(_trigger, _opt_phase)


# Feature: local-ti4-data-foundation, Property 9: Zapytanie o specyfikacje czasowe
# zgadza się z modelem referencyjnym
@settings(max_examples=200)
@given(entries=st.lists(_spec_entry, max_size=30))
def test_query_timing_zgadza_sie_z_modelem_referencyjnym(
    entries: list[tuple[TriggerKind, Phase | None]]
) -> None:
    """**Validates: Requirements 8.4, 8.6**"""
    timing_specs: dict[ComponentRef, TimingSpec] = {}
    for idx, (trigger, phase) in enumerate(entries):
        ref = ComponentRef(ComponentCategory.ACTION_CARD, f"c{idx}")
        timing_specs[ref] = _timing_spec(trigger, phase)
    catalog = ComponentCatalog(tables={}, timing_specs=timing_specs)

    # Zapytanie bez fazy: dokładnie te komponenty o danym rodzaju.
    for kind in TriggerKind:
        expected = {
            ref for ref, spec in timing_specs.items() if spec.trigger is kind
        }
        assert set(catalog.query_timing(kind)) == expected
        # Zapytanie z fazą: dodatkowo filtr po fazie.
        for phase in Phase:
            expected_ph = {
                ref
                for ref, spec in timing_specs.items()
                if spec.trigger is kind and spec.phase is phase
            }
            assert set(catalog.query_timing(kind, phase)) == expected_ph

    # Suma wyników po wszystkich rodzajach = zbiór wszystkich komponentów ze specyfikacją.
    union: set[ComponentRef] = set()
    for kind in TriggerKind:
        union |= set(catalog.query_timing(kind))
    assert union == set(timing_specs)

    # Lista UNCLASSIFIED zgodna z filtrem (podstawa raportu audytu, R8.4).
    unclassified = {
        ref for ref, spec in timing_specs.items() if spec.trigger is TriggerKind.UNCLASSIFIED
    }
    assert set(catalog.query_timing(TriggerKind.UNCLASSIFIED)) == unclassified
