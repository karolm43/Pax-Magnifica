"""Okna czasowe (timing windows) — mechanika kolejki graczy reagujących po kolei.

Fundament interakcji między graczami (RULES.md 29.2). Jedno pojęcie obsługuje
secondary kart strategii, przypisanie strat w walce, space cannon offense oraz
reakcje „when/after" (karty akcji, technologie). Moduł jest CZYSTY: funkcje mają
sygnaturę ``state -> state`` (operują na klonie), nie importują FastAPI/HTTP ani
warstw wyższych (fazy/walka) — to one wołają ``timing``, nie odwrotnie.

Kolejność reagowania (POTWIERDZONA z użytkownikiem, RULES.md 29.2): od gracza PO
aktywnym (inicjatorze), zgodnie z ruchem wskazówek zegara (speaker order rotowany),
inicjator domyślnie pomijany. ``build_response_queue`` wylicza tę kolejność z
``seating_order``; ``open_window`` otwiera okno z gotową kolejką.
"""

from __future__ import annotations

from src.core.game_state import GameState, TimingWindow, WindowType


def build_response_queue(
    state: GameState,
    initiator_id: str | None,
    *,
    include_initiator: bool = False,
) -> list[str]:
    """Buduje kolejkę reagujących: od gracza PO inicjatorze, zgodnie z zegarem.

    Używa ``seating_order`` (kolejność przy stole). Zaczyna od gracza NASTĘPNEGO po
    ``initiator_id`` i obchodzi stół raz. Inicjator jest pomijany, chyba że
    ``include_initiator=True`` (wtedy trafia na KONIEC kolejki — reaguje ostatni).

    Gdy ``seating_order`` jest puste (gra złożona ręcznie), awaryjnie używa
    posortowanych ``player_id``. Zwraca tylko istniejących graczy.

    Args:
        state: Bieżący stan gry (źródło ``seating_order`` i ``players``).
        initiator_id: Gracz otwierający okno (aktywny). ``None`` = brak inicjatora
            do pominięcia (kolejka = pełny stół w kolejności zasiadania).
        include_initiator: Czy dołączyć inicjatora na końcu kolejki.

    Returns:
        Lista ``player_id`` w kolejności reagowania (może być pusta).
    """
    order = [pid for pid in state.seating_order if pid in state.players]
    if not order:
        order = sorted(state.players)
    if not order:
        return []

    if initiator_id is not None and initiator_id in order:
        start = order.index(initiator_id)
        # Obejście stołu zaczynające się OD inicjatora, potem rotacja o 1 w prawo
        # (gracz po inicjatorze pierwszy). Inicjator wraca na koniec rotacji.
        rotated = order[start + 1 :] + order[: start + 1]
        # ``rotated`` kończy się inicjatorem (order[start]); usuwamy go lub
        # zostawiamy na końcu zależnie od flagi.
        if include_initiator:
            return rotated
        return rotated[:-1]

    # Brak inicjatora w kolejności: cały stół (bez wyróżnionego startu).
    if initiator_id is not None and not include_initiator:
        return [pid for pid in order if pid != initiator_id]
    return list(order)


def open_window(
    state: GameState,
    window_type: WindowType,
    queue: list[str],
    *,
    context: dict[str, str | int] | None = None,
) -> GameState:
    """Otwiera okno czasowe z gotową kolejką reagujących.

    Ustawia ``state.pending_window`` na nowe ``TimingWindow`` (cursor=0). Warstwa
    wyżej (faza/walka) wylicza ``queue`` (np. ``build_response_queue``) i podaje
    ewentualny ``context`` (numer karty, pozycja systemu).

    Raises:
        ValueError: Gdy inne okno już trwa (``pending_window`` nie jest None) —
            okien nie zagnieżdżamy w tym modelu (jedno naraz).
    """
    if state.pending_window is not None:
        raise ValueError("Another timing window is already open - cannot open a new one.")
    new_state = state.clone()
    new_state.pending_window = TimingWindow(
        window_type=window_type,
        queue=list(queue),
        cursor=0,
        responded=[],
        context=dict(context) if context else {},
    )
    return new_state


# Okna limitów (RULES.md 42.1): mają pierwszeństwo przed każdym innym oknem i akcją.
LIMIT_WINDOWS = (WindowType.FLEET_POOL, WindowType.CAPACITY)


def interrupt(
    state: GameState,
    window_type: WindowType,
    queue: list[str],
    *,
    context: dict[str, str | int] | None = None,
) -> GameState:
    """Otwiera okno limitu NATYCHMIAST, zawieszając bieżące okno (RULES.md 42.1).

    Bieżące okno (np. przypisanie trafień, odwrót, decyzje graczy) czeka w
    ``suspended_window``; ``close_window`` przywraca je po zamknięciu okna limitu. Gdy okna
    nie ma — zwykłe ``open_window``. Zawieszone może być tylko jedno okno naraz.
    """
    if window_type not in LIMIT_WINDOWS:
        raise ValueError("Only fleet pool / capacity checks may interrupt another window.")
    current = state.pending_window
    if current is None:
        return open_window(state, window_type, queue, context=context)
    if current.window_type in LIMIT_WINDOWS or state.suspended_window is not None:
        return state  # okno limitu już trwa - kolejne sprawdzenie po jego zamknięciu
    held = state.clone()
    held.suspended_window = current
    held.pending_window = None
    return open_window(held, window_type, queue, context=context)


def require_no_limit_window(state: GameState) -> None:
    """Blokuje akcję, dopóki trwa okno usunięcia nadwyżki (RULES.md 42.1).

    Raises:
        ValueError: Otwarte okno FLEET_POOL / CAPACITY.
    """
    window = state.pending_window
    if window is not None and window.window_type is WindowType.FLEET_POOL:
        raise ValueError("Some ships exceed the fleet pool - remove the excess first.")
    if window is not None and window.window_type is WindowType.CAPACITY:
        raise ValueError("Some units exceed capacity - remove the excess first.")


def require_no_reaction_pause(state: GameState) -> None:
    """Brama kroku, który zamknąłby kluczowe okno reakcji, w trakcie pauzy (RULES.md 54.10).

    Raises:
        ValueError: Trwa pauza ochronna (gracze mogą jeszcze zagrać kartę).
    """
    pause = state.reaction_pause
    if pause is not None:
        raise ValueError(
            f"Players may react now ({pause.label}) - wait until the reaction window "
            f"closes ({pause.seconds:g} s)."
        )


def current_responder(state: GameState) -> str | None:
    """Gracz, którego teraz kolej odpowiadać (None, gdy brak okna lub zakończone)."""
    if state.pending_window is None:
        return None
    return state.pending_window.current_responder


def respond_current(state: GameState, player_id: str) -> GameState:
    """Rejestruje odpowiedź bieżącego respondenta i przesuwa kolejkę o jeden.

    NIE rozstrzyga efektu odpowiedzi (to robi warstwa wyżej PRZED/PO wywołaniu —
    np. secondary zużywa żeton, assign-hits usuwa jednostki). Tu tylko mechanika
    kolejki: potwierdzenie, że ``player_id`` to bieżący respondent, dopisanie do
    ``responded`` i inkrementacja ``cursor``.

    Gdy po przesunięciu okno się kończy (``is_complete``), NIE zamyka go sam —
    warstwa wyżej sprawdza ``is_window_complete`` i woła ``close_window`` po
    zastosowaniu efektów. To rozdziela „kto odpowiedział" od „co z tego wynika".

    Raises:
        ValueError: Gdy brak otwartego okna, okno już zakończone, albo
            ``player_id`` nie jest bieżącym respondentem (gra poza kolejnością).
    """
    if state.pending_window is None:
        raise ValueError("No open timing window.")
    window = state.pending_window
    if window.is_complete:
        raise ValueError("The timing window is already closed.")
    expected = window.queue[window.cursor]
    if player_id != expected:
        raise ValueError(
            f"It is now {expected}'s turn to respond, not {player_id} (out-of-order response)."
        )
    new_state = state.clone()
    assert new_state.pending_window is not None  # zachowane przez clone
    new_window = new_state.pending_window
    new_window.responded = [*new_window.responded, player_id]
    new_window.cursor += 1
    return new_state


def is_window_complete(state: GameState) -> bool:
    """Czy trwa okno i wszyscy z kolejki już odpowiedzieli (gotowe do zamknięcia)."""
    if state.pending_window is None:
        return False
    return state.pending_window.is_complete


def close_window(state: GameState) -> GameState:
    """Zamyka okno czasowe (czyści ``pending_window``).

    Wołane przez warstwę wyżej po zastosowaniu efektów — zwykle gdy okno jest
    zakończone (``is_window_complete``), ale dopuszczamy też zamknięcie wcześniejsze
    (np. efekt przerywający okno). Gdy brak okna — bez zmian (idempotentne).
    """
    new_state = state.clone()
    # Okno przerwane przez okno limitu wraca, gdy nadwyżka zniknęła (RULES.md 42.1).
    new_state.pending_window = new_state.suspended_window
    new_state.suspended_window = None
    return new_state
