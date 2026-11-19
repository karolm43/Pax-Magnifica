"""Pauza ochronna w kluczowych oknach reakcji (RULES.md 43.4 pkt 4, 54.10, 54.11) — stały czas.

Okna kart z ręki trwają „do następnej zatwierdzonej akcji” (53.5), więc szybki gracz zamykał je,
zanim inni zdążyli zareagować (Coup d'Etat, ridery, Salvage, Direct Hit). W kilku KLUCZOWYCH
oknach gra czeka: kolejny krok, który okno by zamknął, jest zablokowany, dopóki wszyscy uprawnieni
minie stały czas okna ustawiony przez hosta (``reaction_window``, 54.11; zegar serwera, ``now``
podaje warstwa API). Pasy nie skracają pauzy; silnik sam pasuje za graczy bez pasującej karty.

Kluczowe okna (decyzja użytkownika 2026-11-15):
* ogłoszona akcja strategiczna (Coup d'Etat) - blokuje pierwszy wybór primary;
* ujawniona agenda (Veto, Diplomatic Pressure, ridery...) - blokuje pierwszy głos / wstrzymanie;
* wygrana walka (Salvage) - blokuje zamknięcie bitwy;
* użycie Sustain Damage (Direct Hit, Reflective Shielding) - blokuje kolejny krok walki / Space
  Cannon.

**Filtr jawny (43.4 pkt 5).** Pauza otwiera się tylko, gdy na okno może zareagować karta spoza
stosu odrzuconych (``timing_view.live_relations``) i ktoś, kto mógłby być właściwą stroną okna
(„you” / „another player” z tekstu karty), ma w ręce choć jedną kartę akcji (liczba jest jawna).
Gracz bez pasującej karty dostaje pauzę tak samo jak z kartą - treść ręki nic nie zmienia.

Moduł jest czysty: funkcje mutują przekazany stan (klon wołającego) albo zwracają nowy.
"""

from __future__ import annotations

import json

from src.core import reaction_cards, reaction_prefs, reaction_window, timing, timing_view
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, ReactionPause
from src.core.reaction_cards import ANY, OTHER, SELF, OpenWindow
from src.core.registry import StaticDataRegistry

_SEEN_LIMIT = 32  # tyle ostatnich kluczy okien pamiętamy (to samo okno nie pauzuje dwa razy)

_E, _M = GameEvent, Moment
Point = tuple[GameEvent, Moment]

# Okno-klucz pauzy -> okna, których karty liczą się do uprawnionych (when i after tej chwili).
PAUSE_POINTS: dict[Point, tuple[Point, ...]] = {
    (_E.STRATEGIC_ACTION, _M.WHEN): ((_E.STRATEGIC_ACTION, _M.WHEN),),
    (_E.AGENDA_REVEALED, _M.AFTER): (
        (_E.AGENDA_REVEALED, _M.WHEN), (_E.AGENDA_REVEALED, _M.AFTER),
    ),
    (_E.COMBAT_WON, _M.AFTER): ((_E.COMBAT_WON, _M.AFTER),),
    (_E.UNIT_SUSTAIN_DAMAGE, _M.AFTER): (
        (_E.UNIT_SUSTAIN_DAMAGE, _M.WHEN), (_E.UNIT_SUSTAIN_DAMAGE, _M.AFTER),
    ),
}

# Klucze kontekstu, które NIE rozróżniają okna (kilka statków z Sustain Damage = jedna pauza).
_KEY_IGNORED = ("base_type", "count", "hits_on")


def window_key(state: GameState, window: OpenWindow) -> str:
    """Klucz okna pauzy: runda gry + zdarzenie + kontekst (bez szczegółów pojedynczego statku)."""
    ctx = {k: v for k, v in window.ctx.items() if k not in _KEY_IGNORED}
    data = json.dumps(ctx, sort_keys=True, default=str)
    return f"{state.round_number}|{window.event.value}|{window.moment.value}|{data}"


def _seating(state: GameState) -> list[str]:
    order = [pid for pid in state.seating_order if pid in state.players]
    return order + [pid for pid in sorted(state.players) if pid not in order]


def eligible_players(
    state: GameState, registry: StaticDataRegistry, window: OpenWindow
) -> list[str]:
    """Kto może odpowiedzieć w pauzie (z informacji jawnej; pusto = pauza niepotrzebna)."""
    live = timing_view.live_relations(state, registry)
    relations: set[str] = set()
    for point in PAUSE_POINTS.get((window.event, window.moment), ()):
        relations |= live.get(point, set())
    # Komponent frakcji z oknem użycia (Quash) - jawny, więc też otwiera pauzę (RULES.md 62.9).
    users = set(reaction_window.window_component_users(state, registry, _seating(state)))
    if not relations:
        return [pid for pid in _seating(state) if pid in users]
    subject = window.subject
    candidates = {
        pid
        for pid in state.players
        if ANY in relations
        or (SELF in relations and pid == subject)
        or (OTHER in relations and pid != subject)
    }
    return [
        pid for pid in _seating(state)
        if (pid in candidates and state.players[pid].private.action_cards) or pid in users
    ]


def _key_windows(state: GameState) -> list[OpenWindow]:
    return [
        w for w in reaction_cards.open_windows(state)
        if w.public and (w.event, w.moment) in PAUSE_POINTS
    ]


def sync(state: GameState, registry: StaticDataRegistry, now: float) -> None:
    """Po zatwierdzonym kroku: zamyka pauzę, której okno minęło, i otwiera nową (MUTUJE).

    Okno, które już miało pauzę (albo uznano, że nikt nie może zareagować), drugi raz jej nie
    dostaje (``reaction_pause_seen``).
    """
    windows = _key_windows(state)
    pause = state.reaction_pause
    if pause is not None:
        if any(window_key(state, w) == pause.key for w in windows):
            return
        state.reaction_pause = None  # okno minęło (np. Coup zakończył turę, Veto zmieniło agendę)
    for window in windows:
        key = window_key(state, window)
        if key in state.reaction_pause_seen:
            continue
        state.reaction_pause_seen = [*state.reaction_pause_seen, key][-_SEEN_LIMIT:]
        eligible = eligible_players(state, registry, window)
        if not eligible:
            continue
        category = reaction_prefs.category_of_event(window.event.value)
        involved = reaction_prefs.involved_players(
            state, eligible, subject=window.subject, ctx=window.ctx, category=category
        )
        state.reaction_pause = ReactionPause(
            key=key,
            event=window.event.value,
            moment=window.moment.value,
            label=timing_view.label(window.event, window.moment, window.ctx),
            subject=window.subject,
            opened_at=float(now),
            eligible=eligible,
            seconds=float(reaction_window.window_seconds(state)),
            involved=involved,
        )
        # Auto-pas (54.11-54.12): bez pasującej karty, deklaracje pasu, „only when involved” -
        # lista pasów jest prywatna.
        state.reaction_pause.passed = reaction_window.auto_passers(
            state, registry, eligible, category=category, involved=involved
        )
        if reaction_window.closes_early(state, state.reaction_pause):
            state.reaction_pause = None  # „Quick windows”: nikt nie reaguje - bez pauzy (54.12)
        return


def would_open(state: GameState, registry: StaticDataRegistry) -> bool:
    """Czy ``sync`` otworzyłby teraz pauzę (nowe kluczowe okno z uprawnionymi graczami)."""
    seen = set(state.reaction_pause_seen)
    return any(
        window_key(state, w) not in seen and eligible_players(state, registry, w)
        for w in _key_windows(state)
    )


def expired(pause: ReactionPause, now: float) -> bool:
    """Czy minął stały czas pauzy (z „More time”)."""
    return reaction_window.expired(pause, now)


def require_clear(state: GameState) -> None:
    """Brama kroku, który zamknąłby kluczowe okno (``timing.require_no_reaction_pause``)."""
    timing.require_no_reaction_pause(state)


def pass_pause(state: GameState, player_id: str) -> GameState:
    """Pas uprawnionego gracza (nowy stan). Pauza trwa dalej do końca czasu (54.11).

    Raises:
        ValueError: Brak pauzy, gracz nieuprawniony albo już spasował.
    """
    pause = state.reaction_pause
    if pause is None:
        raise ValueError("Nobody is waiting for reactions right now.")
    if player_id not in pause.eligible:
        raise ValueError(f"{player_id} is not asked to react in this window.")
    if player_id in pause.passed:
        raise ValueError(f"{player_id} has already passed.")
    new_state = state.clone()
    assert new_state.reaction_pause is not None
    new_state.reaction_pause.passed = [*pause.passed, player_id]
    if reaction_window.closes_early(new_state, new_state.reaction_pause):
        new_state.reaction_pause = None  # „Quick windows”: wszyscy spasowali (54.12)
    return new_state


def ask_for_time(state: GameState, player_id: str) -> GameState:
    """„More time” w pauzie (nowy stan; RULES.md 54.11).

    Raises:
        ValueError: Brak pauzy, gracz nieuprawniony albo już prosił.
    """
    if state.reaction_pause is None:
        raise ValueError("Nobody is waiting for reactions right now.")
    new_state = state.clone()
    assert new_state.reaction_pause is not None
    reaction_window.ask_for_time(new_state.reaction_pause, player_id)
    return new_state


def release(state: GameState, now: float) -> GameState:
    """Kończy pauzę po czasie (zegar serwera). Nowy stan.

    Raises:
        ValueError: Brak pauzy albo czas jeszcze nie minął.
    """
    pause = state.reaction_pause
    if pause is None:
        raise ValueError("Nobody is waiting for reactions right now.")
    if not expired(pause, now):
        raise ValueError("The reaction window is still open.")
    new_state = state.clone()
    new_state.reaction_pause = None
    return new_state
