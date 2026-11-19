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

from src.core import reaction_prefs
from src.core.components import ComponentCategory
from src.core.game_state import ControlType, GameState
from src.core.registry import StaticDataRegistry

DEFAULT_SECONDS = 5
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
    involved: list[str]


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

    prefs = state.players[player_id].private.reaction_prefs
    # Wyciszone karty (54.12) nie liczą się jako „ma kartę” - auto-pas jak bez karty.
    if any(
        entry["reaction"] and entry["playable"]
        and not reaction_prefs.is_card_muted(
            prefs, card_name(registry, ComponentCategory.ACTION_CARD, entry["card_id"])
        )
        for entry in action_cards.playability(state, registry, player_id)
    ):
        return True
    if window_component_users(state, registry, [player_id]):
        return True
    return any(
        row["reaction"] and row["playable"]
        and not reaction_prefs.is_card_muted(
            prefs, card_name(registry, ComponentCategory.PROMISSORY_NOTE, row["template"])
        )
        for row in promissory_play.playability(state, registry, player_id)
    )


def card_name(registry: StaticDataRegistry, category: ComponentCategory, card_id: str) -> str:
    """Nazwa karty z assetów (klucz wyciszenia - wszystkie kopie, np. ``sabo1``..``sabo4``)."""
    card = registry.catalog.get(category, card_id)
    return (card.name if card is not None else None) or card_id


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


def skips_automatically(
    state: GameState,
    player_id: str,
    category: str | None = None,
    involved: Iterable[str] | None = None,
) -> bool:
    """Bot (brak jeszcze AI reakcji), „Skip all reactions”, deklaracja pasu w kategorii okna albo
    okno, które gracza nie dotyczy przy „only when it concerns me” (RULES.md 54.11-54.12)."""
    player = state.players.get(player_id)
    if player is None:
        return True
    if player.control_type is ControlType.BOT or player.private.auto_pass_reactions:
        return True
    if reaction_prefs.declares_pass(state, player_id, category):
        return True
    return involved is not None and reaction_prefs.skips_uninvolved(state, player_id, involved)


def auto_passers(
    state: GameState,
    registry: StaticDataRegistry,
    eligible: Iterable[str],
    *,
    category: str | None = None,
    involved: Iterable[str] | None = None,
) -> list[str]:
    """Uprawnieni, za których silnik pasuje od razu (stan z JUŻ otwartym oknem).

    Kolejność jak w ``eligible``. Wynik zależy od treści rąk, dlatego trafia wyłącznie do
    prywatnej listy pasów - na zewnątrz okno wygląda identycznie (stała długość).
    """
    concerned = list(involved) if involved is not None else None
    return [
        pid
        for pid in eligible
        if skips_automatically(state, pid, category, concerned)
        or not has_playable_reaction(state, registry, pid)
    ]


def all_passed(window: TimedWindow) -> bool:
    """Czy wszyscy uprawnieni spasowali (ręcznie albo auto-pasem)."""
    return set(window.eligible) <= set(window.passed)


def closes_early(state: GameState, window: TimedWindow) -> bool:
    """„Quick windows” hosta (54.12): okno kończy się, gdy wszyscy uprawnieni spasowali."""
    return state.quick_reaction_windows and all_passed(window)


def configure_quick(state: GameState, enabled: bool) -> GameState:
    """Host włącza/wyłącza „Quick windows” (nowy stan; trwające okna zamyka wołający)."""
    new_state = state.clone()
    new_state.quick_reaction_windows = bool(enabled)
    return new_state


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
    pass_open_windows(new_state, player_id)
    return new_state


def pass_open_windows(state: GameState, player_id: str) -> None:
    """Po zmianie preferencji: pasuje za gracza w trwających oknach, które teraz pomija (MUTUJE).

    Odwołanie nie cofa pasu (54.11). Zamknięcie okien w trybie „Quick windows” robi
    :func:`settle_quick` (potrzebuje rejestru do rozstrzygnięcia karty).
    """
    pause = state.reaction_pause
    if pause is not None and player_id in pause.eligible and player_id not in pause.passed:
        category = reaction_prefs.category_of_event(pause.event)
        if skips_automatically(state, player_id, category, pause.involved):
            pause.passed = [*pause.passed, player_id]
    held = state.held_play
    if held is not None and player_id in held.eligible and player_id not in held.passed:
        if skips_automatically(state, player_id, reaction_prefs.SABOTAGE, held.involved):
            held.passed = [*held.passed, player_id]


def settle_quick(state: GameState, registry: StaticDataRegistry) -> GameState:
    """„Quick windows”: zamyka trwające okna, w których wszyscy spasowali (nowy stan albo ten sam).

    Pauza po prostu znika; czekająca karta (okno Sabotage) rozstrzyga się od razu.
    """
    from src.core import card_hold  # lokalnie: card_hold importuje ten moduł

    result = state
    if result.reaction_pause is not None and closes_early(result, result.reaction_pause):
        result = result.clone()
        result.reaction_pause = None
    if result.held_play is not None and closes_early(result, result.held_play):
        result = card_hold.resolve(result, registry)
    return result

