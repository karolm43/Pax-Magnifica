"""Karty akcji grane W REAKCJI na okno czasowe (when / after / before / at start / at end).

Karta reakcji NIE jest akcją tury (nie zużywa akcji) i nie ma kolejki pytań: gracz PRZECIĄGA ją
z ręki, gdy silnik pokazuje, że okno dla niej jest teraz otwarte (RULES.md 53.5, 43.4). Silnik
nigdy nie pyta graczy "czy masz kartę", więc zachowanie widoczne z zewnątrz nie zależy od ręki.

Trzy elementy:

* **Okna otwarte teraz** (:func:`open_windows`) - WYLICZANE ze stanu gry (krok walki, krok agendy,
  krok akcji taktycznej, faza...). Wylicza je zbiór *dostawców* (``@window_provider``), każdy
  temat (agenda, walka, ruch...) dokłada własnego w ``core/hooks/reactions_*.py``. Okno to para
  (zdarzenie, moment) z ``game_events`` + kontekst (``player`` = kto je wywołał, ``position``...).
* **Adres karty** - domyślnie z tekstu okna karty (``game_events.classify_window``), relacja
  gracza ("you" / "another player") z tego samego tekstu. :func:`declare_reaction` pozwala
  nadpisać punkty, relację i dodać warunek (np. "w systemie jest Twój żeton").
* **Zagrywalność** (:func:`available`) - karta jest do zagrania, gdy istnieje otwarte okno o tym
  adresie, relacja gracza się zgadza i warunek karty jest spełniony. Efekt jest zwykłym
  ``register_effect("action_cards:<id>")``; dostaje w ``params["__window"]`` okno, na które
  reaguje (słownik ``event/moment/ctx``).

Efekt z czasem trwania ("w tej akcji taktycznej", "w tej rundzie walki") = ``active_effects`` z
hookiem o źródle ``SOURCE_EFFECT`` (``card_effect_source``) - wygasa przez ``triggers.EXPIRY``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from src.core.components import ActionCardDef, ComponentCategory, ComponentRef
from src.core.game_events import GameEvent, Moment, classify_window
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import SOURCE_EFFECT, HookSource
from src.core.timing_spec import TriggerKind

SELF = "self"  # zdarzenie wywołał/dotyczy samego gracza ("you ...")
OTHER = "other"  # wywołał je inny gracz ("another player ...", "your opponent ...")
ANY = "any"  # obojętne ("an agenda is revealed")

WINDOW_KEY = "__window"  # klucz w ``params`` efektu: okno, na które karta reaguje


@dataclass
class OpenWindow:
    """Otwarte teraz okno czasowe: (zdarzenie, moment) + kontekst.

    ``ctx["player"]`` = gracz-podmiot zdarzenia (kto aktywował system, kto głosował...);
    pozostałe klucze zależą od okna (``position``, ``agenda_id``, ``planet``...). Wartości
    to napisy/liczby, żeby okno dało się przekazać do formularza i odpowiedzi API.
    """

    event: GameEvent
    moment: Moment
    ctx: dict[str, Any] = field(default_factory=dict)
    # Czy okno wolno pokazać wszystkim (pasek okien, ``core/timing_view``). False, gdy samo
    # istnienie okna zależy od informacji ukrytej (np. ktoś trzyma notkę - Acquiescence).
    public: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {"event": self.event.value, "moment": self.moment.value, "ctx": dict(self.ctx)}

    @property
    def subject(self) -> str | None:
        player = self.ctx.get("player")
        return str(player) if player is not None else None


WindowProvider = Callable[[GameState], list[OpenWindow]]
ReactionCondition = Callable[[GameState, StaticDataRegistry, str, OpenWindow], bool]
Point = tuple[GameEvent, Moment]


@dataclass(frozen=True)
class ReactionSpec:
    """Adres karty reakcji: punkty okien, relacja gracza do podmiotu i warunek dodatkowy."""

    points: tuple[Point, ...]
    subject: str = ANY
    condition: ReactionCondition | None = None


_PROVIDERS: list[WindowProvider] = []
_OVERRIDES: dict[str, ReactionSpec] = {}
_loaded = False


def window_provider(fn: WindowProvider) -> WindowProvider:
    """Dekorator: rejestruje dostawcę okien (funkcja ``state -> [OpenWindow]``, bez mutacji)."""
    _PROVIDERS.append(fn)
    return fn


def declare_reaction(
    *card_ids: str,
    points: Iterable[Point] | None = None,
    subject: str | None = None,
    condition: ReactionCondition | None = None,
) -> None:
    """Nadpisuje adres karty/kart reakcji (domyślnie liczony z tekstu okna karty).

    Args:
        card_ids: Identyfikatory kart akcji (np. ``"fs1", "fs2"``).
        points: Pary (zdarzenie, moment), w których karta jest zagrywalna.
        subject: ``SELF`` / ``OTHER`` / ``ANY`` - relacja gracza z ręki do ``ctx["player"]`` okna.
        condition: Dodatkowy warunek ``(state, registry, player_id, window) -> bool``.
    """
    for card_id in card_ids:
        previous = _OVERRIDES.get(card_id)
        base_points = tuple(points) if points is not None else (previous.points if previous else ())
        _OVERRIDES[card_id] = ReactionSpec(
            points=base_points,
            subject=subject or (previous.subject if previous else ""),
            condition=condition or (previous.condition if previous else None),
        )


HindsightFn = Callable[[GameState, GameState, OpenWindow], dict[str, Any]]
_HINDSIGHT: dict[str, HindsightFn] = {}
_FUTURE: ContextVar[GameState | None] = ContextVar("reaction_future_state", default=None)


def register_hindsight(card_id: str, fn: HindsightFn) -> None:
    """Rejestruje „wiedzę z przyszłości" karty zagrywanej przez hold-rewind (RULES.md 53.7).

    ``fn(state_at_window, future_state, window) -> dict`` zwraca dodatkowe klucze doklejane do
    ``window.ctx`` (np. którą kartę strategii gracz wybrał w cofniętym kroku). Działa TYLKO
    wewnątrz :func:`hindsight_scope` (cofnięcie do migawki); w zwykłej ścieżce okno otwarte
    TERAZ nie ma przyszłości i dane nie są doklejane (warunek karty to wie: :func:`in_hindsight`).
    """
    _HINDSIGHT[card_id] = fn


@contextmanager
def hindsight_scope(future_state: GameState) -> Iterator[None]:
    """Włącza doklejanie danych z przyszłości (stan PO cofanym kroku) do okien kart."""
    token = _FUTURE.set(future_state)
    try:
        yield
    finally:
        _FUTURE.reset(token)


def in_hindsight() -> bool:
    """Czy trwa ocena okien na migawce z przeszłości (hold-rewind)."""
    return _FUTURE.get() is not None


def _with_hindsight(state: GameState, card_id: str, window: OpenWindow) -> OpenWindow:
    future = _FUTURE.get()
    fn = _HINDSIGHT.get(card_id)
    if future is None or fn is None:
        return window
    return OpenWindow(
        window.event, window.moment, {**window.ctx, **fn(state, future, window)}, window.public
    )


_REWINDABLE: set[str] = set()
# Karty reakcji WYŁĄCZONE z hold-rewind. Sabotage odpowiada na ``held_play`` (okno, które czeka
# samo, a trwający ``held_play`` i tak blokuje cofanie) - cofanie nic jej nie daje.
_NOT_REWINDABLE: frozenset[str] = frozenset({"sabo1", "sabo2", "sabo3", "sabo4"})


def declare_rewindable(*card_ids: str) -> None:
    """Jawnie oznacza karty do hold-rewind (np. bez specyfikacji czasowej w katalogu)."""
    _REWINDABLE.update(card_ids)


def is_reaction_card(registry: StaticDataRegistry, card_id: str) -> bool:
    """Czy karta akcji jest kartą reakcji (okno inne niż ACTION, jak w ``playability``)."""
    spec = registry.catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, card_id))
    return spec is None or spec.trigger is not TriggerKind.ACTION


def is_rewindable(registry: StaticDataRegistry, card_id: str) -> bool:
    """Czy kartę wolno zagrać przez hold-rewind (``core/hold_rewind.py``, RULES.md 53.7).

    KAŻDA karta reakcji (okno when / after / at start...) poza Sabotage: gra nie czeka na reakcje,
    więc okno każdej z nich może minąć, zanim gracz zdąży ją przeciągnąć. Karty ACTION nie
    korzystają (grane we własnej turze jako akcja - cofanie byłoby zwykłym Undo). Zakaz oszustwa
    (kości, talie, faza, zagrania kart) pilnuje ``hold_rewind.is_irreversible_step`` niezależnie od
    karty, a okno i cel karty liczone są na stanie migawki.
    """
    _ensure_loaded()
    if card_id in _REWINDABLE:
        return True
    return card_id not in _NOT_REWINDABLE and is_reaction_card(registry, card_id)


def card_effect_source(card_id: str) -> HookSource:
    """Źródło hooków efektu trwałego karty (``active_effects.add_effect(key=...)``)."""
    return HookSource(SOURCE_EFFECT, f"action_cards:{card_id}")


def _ensure_loaded() -> None:
    """Leniwie importuje ``core.hooks`` (moduły ``reactions_*`` rejestrują dostawców i karty)."""
    global _loaded
    if _loaded:
        return
    _loaded = True
    import src.core.hooks  # noqa: F401  (efekt uboczny importu: rejestracje)


def open_windows(state: GameState) -> list[OpenWindow]:
    """Okna czasowe otwarte TERAZ (suma dostawców; kolejność = kolejność rejestracji)."""
    _ensure_loaded()
    windows: list[OpenWindow] = []
    for provider in _PROVIDERS:
        windows.extend(provider(state))
    return windows


def relation_from_text(window_text: str) -> str:
    """Relacja gracza do podmiotu okna wyczytana z tekstu okna karty (heurystyka domyślna)."""
    text = window_text.casefold()
    if "another player" in text or "your opponent" in text or "other player" in text:
        return OTHER
    if re.search(r"\b(you|your)\b", text):
        return SELF
    return ANY


def spec_for(registry: StaticDataRegistry, card_id: str) -> ReactionSpec | None:
    """Adres karty reakcji (nadpisanie albo z tekstu okna) albo ``None``, gdy to karta ACTION."""
    _ensure_loaded()
    card = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
    if not isinstance(card, ActionCardDef):
        return None
    timing = registry.catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, card_id))
    if timing is None or timing.trigger is TriggerKind.ACTION:
        return None
    override = _OVERRIDES.get(card_id)
    ref = classify_window(card.window or "")
    points = override.points if override and override.points else ()
    if not points and ref is not None:
        points = ((ref.event, ref.moment),)
    subject = override.subject if override and override.subject else relation_from_text(
        card.window or ""
    )
    return ReactionSpec(
        points=points, subject=subject, condition=override.condition if override else None
    )


def _subject_ok(spec: ReactionSpec, player_id: str, window: OpenWindow) -> bool:
    if spec.subject == ANY:
        return True
    actor = window.subject
    if spec.subject == SELF:
        return actor == player_id
    return actor is not None and actor != player_id


def matching_windows(
    state: GameState, registry: StaticDataRegistry, player_id: str, card_id: str
) -> list[OpenWindow]:
    """Otwarte okna, w których gracz może teraz zagrać daną kartę reakcji."""
    spec = spec_for(registry, card_id)
    if spec is None:
        return []
    found: list[OpenWindow] = []
    for window in open_windows(state):
        if (window.event, window.moment) not in spec.points:
            continue
        window = _with_hindsight(state, card_id, window)
        if not _subject_ok(spec, player_id, window):
            continue
        if spec.condition is not None and not spec.condition(state, registry, player_id, window):
            continue
        found.append(window)
    return found


def window_for(
    state: GameState, registry: StaticDataRegistry, player_id: str, card_id: str
) -> OpenWindow | None:
    """Pierwsze pasujące okno karty (do formularzy i efektów) albo ``None``."""
    found = matching_windows(state, registry, player_id, card_id)
    return found[0] if found else None


def available(
    state: GameState, registry: StaticDataRegistry, player_id: str, card_id: str
) -> tuple[bool, str | None, OpenWindow | None]:
    """Czy gracz może TERAZ zagrać kartę reakcji: ``(tak/nie, powód odmowy, okno)``."""
    window = window_for(state, registry, player_id, card_id)
    if window is None:
        return False, "There is no open window for this card right now.", None
    return True, None, window
