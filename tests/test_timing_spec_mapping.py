"""Testy przykładowe mapowania okien i braku regresji okien (zadanie 5.5).

Pokrywają dwie właściwości z wymagań:

- R8.7: ``TRIGGER_WINDOW_MAP`` jest CAŁKOWITE nad ``TriggerKind`` (każdy rodzaj
  wyzwalacza ma wpis), odwzorowuje na istniejące typy ``WindowType`` lub ``None``
  („brak okna"), a rodzaje bez odpowiednika są jawnie oznaczone jako ``None``.
- R8.8: specyfikacja czasowa NIE zmienia zachowania ``core/timing.py`` — tu jako
  test braku regresji potwierdzamy, że publiczny interfejs ``timing``/``WindowType``
  pozostaje nienaruszony, a pakiet testów ``tests/test_timing.py`` przechodzi bez
  modyfikacji (uruchamiany osobno przez bramkę QA).
"""

from __future__ import annotations

from src.core import timing
from src.core.game_state import WindowType
from src.core.timing_spec import (
    TRIGGER_WINDOW_MAP,
    TriggerKind,
    classify_trigger,
    parse_timing,
)

# Rodzaje wyzwalaczy, które mapują się na uniwersalne okno „when/after" (REACTION).
_REACTION_TRIGGERS: frozenset[TriggerKind] = frozenset(
    {
        TriggerKind.WHEN,
        TriggerKind.AFTER,
        TriggerKind.BEFORE,
        TriggerKind.INSTEAD,
    }
)

# Rodzaje bez odpowiednika w silniku okien — oznaczone jako „brak okna" (None).
_NO_WINDOW_TRIGGERS: frozenset[TriggerKind] = frozenset(
    {
        TriggerKind.AT_START,
        TriggerKind.AT_END,
        TriggerKind.DURING,
        TriggerKind.ACTION,
        TriggerKind.UNCLASSIFIED,
    }
)


# --- R8.7: mapowanie całkowite nad TriggerKind ---------------------------


def test_mapa_pokrywa_wszystkie_rodzaje_wyzwalaczy() -> None:
    """Każda wartość ``TriggerKind`` ma dokładnie jeden wpis w mapie (całkowitość)."""
    assert set(TRIGGER_WINDOW_MAP) == set(TriggerKind)
    # Żadnej nadmiarowej wartości spoza enuma.
    assert len(TRIGGER_WINDOW_MAP) == len(list(TriggerKind))


def test_mapa_zwraca_tylko_windowtype_lub_none() -> None:
    """Wartości mapy to istniejące typy ``WindowType`` albo ``None`` („brak okna")."""
    for kind in TriggerKind:
        value = TRIGGER_WINDOW_MAP[kind]
        assert value is None or isinstance(value, WindowType)


def test_rodzaje_reakcji_mapuja_na_reaction() -> None:
    """when/after/before/instead → uniwersalne okno REACTION (D10, RULES.md 34)."""
    for kind in _REACTION_TRIGGERS:
        assert TRIGGER_WINDOW_MAP[kind] is WindowType.REACTION


def test_rodzaje_bez_okna_sa_oznaczone_none() -> None:
    """Rodzaje bez odpowiednika w silniku są jawnie oznaczone jako „brak okna" (None)."""
    for kind in _NO_WINDOW_TRIGGERS:
        assert TRIGGER_WINDOW_MAP[kind] is None


def test_podzial_rodzajow_jest_rozlaczny_i_zupelny() -> None:
    """Zbiory „reakcja" i „brak okna" są rozłączne i razem dają pełny TriggerKind."""
    assert _REACTION_TRIGGERS.isdisjoint(_NO_WINDOW_TRIGGERS)
    assert _REACTION_TRIGGERS | _NO_WINDOW_TRIGGERS == set(TriggerKind)


def test_window_type_specyfikacji_zgadza_sie_z_mapa() -> None:
    """``TimingSpec.window_type`` pochodzi wprost z mapy dla każdego rodzaju."""
    probki: dict[TriggerKind, str] = {
        TriggerKind.WHEN: "When an agenda is revealed",
        TriggerKind.AFTER: "After you activate a system",
        TriggerKind.BEFORE: "Before you roll dice",
        TriggerKind.INSTEAD: "Instead of producing units",
        TriggerKind.AT_START: "At the start of the strategy phase",
        TriggerKind.AT_END: "At the end of your turn",
        TriggerKind.DURING: "During the action phase",
        TriggerKind.ACTION: "ACTION:",
        TriggerKind.UNCLASSIFIED: "At any time you wish",
    }
    # Upewnij się, że próbki pokrywają wszystkie rodzaje (spójność testu z enumem).
    assert set(probki) == set(TriggerKind)
    for kind, tekst in probki.items():
        assert classify_trigger(tekst) is kind
        spec = parse_timing(tekst)
        assert spec is not None
        assert spec.trigger is kind
        assert spec.window_type is TRIGGER_WINDOW_MAP[kind]


# --- R8.8: brak regresji okien (core/timing.py nienaruszone) -------------


def test_windowtype_zawiera_tylko_znane_typy_okien() -> None:
    """Zbiór typów okien silnika pozostaje nienaruszony przez specyfikację czasową."""
    assert {w.value for w in WindowType} == {
        "STRATEGY_SECONDARY",
        "COMBAT_ASSIGN_HITS",
        "SPACE_CANNON",
        "REACTION",
        "COMBAT_RETREAT",  # ogłoszenie odwrotów w walce kosmicznej (RULES.md 39.5)
    }


def test_interfejs_timing_pozostaje_dostepny() -> None:
    """Publiczne funkcje ``core/timing.py`` są nadal dostępne (brak regresji API)."""
    for nazwa in (
        "build_response_queue",
        "open_window",
        "current_responder",
        "respond_current",
        "is_window_complete",
        "close_window",
    ):
        assert callable(getattr(timing, nazwa))
