"""Okna reakcji o stałej długości + auto-pas silnika (RULES.md 54.11).

Wspólna mechanika pauzy ochronnej (``core/reaction_pause.py``, 54.10) i okna Sabotage
(``core/card_hold.py``, 53.6):

* **Stała długość.** Okno trwa zawsze ``GameState.reaction_window_seconds`` (ustawia host) plus
  ewentualne „More time”. Pasy go NIE skracają - długość to jedyny sygnał widoczny dla innych,
  więc nie może zależeć od treści rąk (43.4).
* **Auto-pas.** Silnik zna ręce, więc przy otwarciu okna pasuje za uprawnionych, którzy nie mają
  karty reakcji zagrywalnej teraz, za botów i za graczy z „Skip all reactions”. Lista pasów jest
  prywatna (``visibility.redact_reaction_windows``).
* **„More time”.** Każdy uprawniony (także ten, za którego silnik spasował) może raz na okno
  przedłużyć je o ``WAIT_EXTENSION_SECONDS`` - prośba nic nie mówi o ręce.

Moduł jest czysty: czas (``now``) podaje wołający, funkcje zwracają nowy stan albo mutują
przekazany klon (opisane w docstringach).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from src.core.game_state import ControlType, GameState
from src.core.registry import StaticDataRegistry

DEFAULT_SECONDS = 4
MIN_SECONDS = 2
MAX_SECONDS = 30
WAIT_EXTENSION_SECONDS = 10


class TimedWindow(Protocol):
    """Wspólny kształt ``ReactionPause`` i ``HeldPlay`` (pola czasu i pasów)."""

    opened_at: float
    seconds: float
    eligible: list[str]
    passed: list[str]
    extended_by: list[str]


def window_seconds(state: GameState) -> int:
    """Długość nowego okna reakcji w s (ustawienie hosta, przycięte do zakresu)."""
    return max(MIN_SECONDS, min(MAX_SECONDS, int(state.reaction_window_seconds)))


def configure(state: GameState, seconds: int) -> GameState:
    """Host ustawia długość okien reakcji (nowy stan; trwające okno zachowuje swoją długość).

    Raises:
        ValueError: Wartość poza zakresem ``MIN_SECONDS``..``MAX_SECONDS``.
    """
    if not MIN_SECONDS <= seconds <= MAX_SECONDS:
        raise ValueError(
            f"Reaction window must be between {MIN_SECONDS} and {MAX_SECONDS} seconds."
        )
    new_state = state.clone()
    new_state.reaction_window_seconds = int(seconds)
    return new_state


def expired(window: TimedWindow, now: float) -> bool:
    """Czy minął stały czas okna (z przedłużeniami)."""
    return now - window.opened_at >= window.seconds


def has_playable_reaction(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    """Czy gracz może TERAZ zareagować (prywatne - tylko dla silnika): karta reakcji z ręki,
    notka-reakcja z ręki albo komponent frakcji z oknem użycia (Quash, Instinct Training -
    RULES.md 62.9)."""
    # lokalnie: moduły kart i komponentów importują moduły okien
    from src.core import action_cards, promissory_play

    if any(
        entry["reaction"] and entry["playable"]
        for entry in action_cards.playability(state, registry, player_id)
    ):
        return True
    if window_component_users(state, registry, [player_id]):
        return True
    return any(
        row["reaction"] and row["playable"]
        for row in promissory_play.playability(state, registry, player_id)
    )


def window_component_users(
    state: GameState, registry: StaticDataRegistry, player_ids: Iterable[str]
) -> list[str]:
    """Gracze z komponentem frakcji, którego mogą użyć TERAZ w chwilowym oknie (jawne: zdolność,
    technologia, żetony; bez okien trwających całą fazę - ``standing``)."""
    from src.core import faction_components  # lokalnie: importuje moduły okien

    ids = list(player_ids)
    users = {
        row["player_id"]
        for row in faction_components.available_now(state, registry, ids)
        if not row["standing"]
    }
    return [pid for pid in ids if pid in users]


def skips_automatically(state: GameState, player_id: str) -> bool:
    """Bot (brak jeszcze AI reakcji) albo gracz z włączonym „Skip all reactions”."""
    player = state.players.get(player_id)
    if player is None:
        return True
    return player.control_type is ControlType.BOT or player.private.auto_pass_reactions


def auto_passers(
    state: GameState, registry: StaticDataRegistry, eligible: Iterable[str]
) -> list[str]:
    """Uprawnieni, za których silnik pasuje od razu (stan z JUŻ otwartym oknem).

    Kolejność jak w ``eligible``. Wynik zależy od treści rąk, dlatego trafia wyłącznie do
    prywatnej listy pasów - na zewnątrz okno wygląda identycznie (stała długość).
    """
    return [
        pid
        for pid in eligible
        if skips_automatically(state, pid) or not has_playable_reaction(state, registry, pid)
    ]


def ask_for_time(window: TimedWindow, player_id: str) -> None:
    """„More time”: przedłuża okno o ``WAIT_EXTENSION_SECONDS`` (MUTUJE okno na klonie stanu).

    Raises:
        ValueError: Gracz nie jest uprawniony albo już prosił w tym oknie.
    """
    if player_id not in window.eligible:
        raise ValueError(f"{player_id} is not asked to react in this window.")
    if player_id in window.extended_by:
        raise ValueError("You already asked for more time in this window.")
    window.extended_by = [*window.extended_by, player_id]
    window.seconds = float(window.seconds) + WAIT_EXTENSION_SECONDS


def set_auto_pass(state: GameState, player_id: str, enabled: bool) -> GameState:
    """Gracz włącza/wyłącza „Skip all reactions” (nowy stan).

    Włączenie w trakcie okna pasuje od razu w trwających oknach; wyłączenie nie cofa pasu.

    Raises:
        ValueError: Nieznany gracz.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    new_state = state.clone()
    new_state.players[player_id].private.auto_pass_reactions = bool(enabled)
    if enabled:
        windows: list[TimedWindow | None] = [new_state.reaction_pause, new_state.held_play]
        for window in windows:
            if window is not None and player_id in window.eligible:
                if player_id not in window.passed:
                    window.passed = [*window.passed, player_id]
    return new_state

