"""Zegar szachowy graczy — czyste funkcje nad ``GameState.clock`` (RULES.md 58).

To funkcja PROJEKTOWA (jak limit rund), NIE reguła TI4. Każdy gracz ma pulę czasu; tyka
zegar tylko tego, kto TERAZ podejmuje decyzję (``clock_holder``). Czas rzeczywisty nie jest
tu odczytywany — wołający podaje ``now`` (sekundy UNIX), więc funkcje są deterministyczne
i testowalne bez zegara systemowego. W API ``now`` podaje ``StateService`` przy commicie.

Model rozliczania:
- ``settle(state, now)`` — wołane przy KAŻDYM commicie stanu: odejmuje holderowi czas od
  ``running_since``, nalicza dodatek za zakończoną turę i przełącza holdera.
- Między commitami nic się nie zapisuje; UI dolicza upływ sam (``snapshot``).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.game_state import GameState

# Granice konfiguracji (ochrona przed literówką typu 6000 minut).
MAX_INITIAL_MS = 24 * 60 * 60 * 1000
MAX_INCREMENT_MS = 60 * 60 * 1000


@dataclass(frozen=True)
class PlayerClock:
    """Odczyt zegara gracza na chwilę ``now`` (z doliczonym nierozliczonym odcinkiem)."""

    player_id: str
    remaining_ms: int
    turn_ms: int
    running: bool


def clock_holder(state: GameState) -> str | None:
    """Gracz, którego zegar powinien teraz tykać (⚠ ZAŁOŻENIE, RULES.md 58.2).

    - koniec gry albo trwający setup startowy (wybory równoległe) → nikt;
    - otwarte okno czasowe → jego bieżący respondent (to on decyduje);
    - w przeciwnym razie ``active_player_id`` (wybór karty strategii, tura w fazie akcji,
      punktowanie w statusie, głosowanie w agendzie — silnik prowadzi je tym polem).
    """
    if state.winner_id is not None or state.setup is not None:
        return None
    window = state.pending_window
    if window is not None:
        responder = window.current_responder
        if responder is not None and responder in state.players:
            return responder
    active = state.active_player_id
    return active if active in state.players else None


def configure(state: GameState, *, initial_ms: int, increment_ms: int = 0) -> GameState:
    """Włącza zegar z pulą ``initial_ms`` dla każdego gracza (nowa gra). Zwraca nowy stan.

    Zegar rusza przy najbliższym ``settle`` (commit). Raises: ``ValueError`` przy
    wartościach spoza zakresu.
    """
    if not 0 < initial_ms <= MAX_INITIAL_MS:
        raise ValueError(f"Clock time must be between 1 ms and 24 h (got {initial_ms} ms).")
    if not 0 <= increment_ms <= MAX_INCREMENT_MS:
        raise ValueError(f"Clock increment must be between 0 and 1 h (got {increment_ms} ms).")
    new_state = state.clone()
    clock = new_state.clock
    clock.enabled = True
    clock.initial_ms = initial_ms
    clock.increment_ms = increment_ms
    clock.remaining_ms = {pid: initial_ms for pid in new_state.players}
    clock.holder_id = None
    clock.holder_turn_ms = 0
    clock.running_since = None
    clock.paused = False
    clock.turn_owner_id = None
    return new_state


def _elapsed_ms(since: float | None, now: float) -> int:
    if since is None:
        return 0
    return max(0, round((now - since) * 1000))


def settle(state: GameState, now: float) -> GameState:
    """Rozlicza zegar na chwilę ``now`` (MUTUJE i zwraca ``state``, jak ``apply_victory``).

    Kolejno: (1) holder traci czas od ``running_since``, (2) gdy ``active_player_id`` się
    zmienił, poprzedni właściciel tury dostaje dodatek, (3) przełączenie holdera zeruje
    licznik tury, (4) zegar tyka dalej od ``now``, o ile nie ma pauzy i jest holder.
    """
    clock = state.clock
    if not clock.enabled:
        return state
    # Gracze dodani po starcie (God-Mode) dostają pełną pulę.
    for pid in state.players:
        clock.remaining_ms.setdefault(pid, clock.initial_ms)

    spent = _elapsed_ms(clock.running_since, now)
    if clock.holder_id in clock.remaining_ms and spent:
        clock.remaining_ms[clock.holder_id] -= spent
        clock.holder_turn_ms += spent

    # Dodatek tylko za turę rozegraną przy działającej grze: gdy holdera nie ma (setup
    # startowy, koniec gry), zmiany ``active_player_id`` nie są niczyją turą.
    holder = clock_holder(state)
    active = state.active_player_id
    previous_owner = clock.turn_owner_id
    if previous_owner is not None and previous_owner != active:
        if previous_owner in clock.remaining_ms:
            clock.remaining_ms[previous_owner] += clock.increment_ms
    clock.turn_owner_id = active if holder is not None else None

    if holder != clock.holder_id:
        clock.holder_id = holder
        clock.holder_turn_ms = 0
    clock.running_since = now if holder is not None and not clock.paused else None
    return state


def pause(state: GameState, now: float) -> GameState:
    """Zatrzymuje zegar (rozlicza do ``now``). Zwraca nowy stan. Raises: ``ValueError``."""
    if not state.clock.enabled:
        raise ValueError("The chess clock is not enabled in this game.")
    if state.clock.paused:
        raise ValueError("The chess clock is already paused.")
    new_state = settle(state.clone(), now)
    new_state.clock.paused = True
    new_state.clock.running_since = None
    return new_state


def resume(state: GameState, now: float) -> GameState:
    """Wznawia zatrzymany zegar od ``now``. Zwraca nowy stan. Raises: ``ValueError``."""
    if not state.clock.enabled:
        raise ValueError("The chess clock is not enabled in this game.")
    if not state.clock.paused:
        raise ValueError("The chess clock is not paused.")
    new_state = state.clone()
    new_state.clock.paused = False
    return settle(new_state, now)


def snapshot(state: GameState, now: float) -> list[PlayerClock]:
    """Odczyt zegarów wszystkich graczy na chwilę ``now`` (bez zmiany stanu).

    Kolejność: ``seating_order``, potem pozostali gracze. Pusta lista, gdy zegar wyłączony.
    """
    clock = state.clock
    if not clock.enabled:
        return []
    live = _elapsed_ms(clock.running_since, now)
    order = [pid for pid in state.seating_order if pid in state.players]
    order += [pid for pid in state.players if pid not in order]
    result: list[PlayerClock] = []
    for pid in order:
        is_holder = pid == clock.holder_id
        remaining = clock.remaining_ms.get(pid, clock.initial_ms)
        result.append(
            PlayerClock(
                player_id=pid,
                remaining_ms=remaining - (live if is_holder else 0),
                turn_ms=clock.holder_turn_ms + live if is_holder else 0,
                running=is_holder and clock.running_since is not None,
            )
        )
    return result
