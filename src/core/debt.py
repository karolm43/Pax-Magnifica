"""Żetony długu (debt) (debt tokens) — nieformalna zasada stołu, NIE reguła TI4 (RULES.md 47.3).

Gracze zwyczajowo oddają sobie małe żetony kontroli (te od planet bez jednostek) jako
niewiążące obietnice/długi: obiecane 3 trade goods = 3 żetony wystawcy u wierzyciela. To
tylko PAMIĘĆ STOŁU — silnik niczego nie egzekwuje (żadnego wpływu na zasoby), więc:

* nie wymagają sąsiedztwa, tury ani fazy (można obiecywać każdemu, w każdej chwili);
* wystawca oddaje wierzycielowi N swoich żetonów (``give_debt_tokens``);
* wierzyciel zwraca żetony wystawcy, gdy dług spłacony/odpuszczony (``return_debt_tokens``).

Stan: ``GameState.debt_tokens`` = ``{holder_id: {issuer_id: liczba}}``. Funkcje CZYSTE
(``state -> state``, na klonie).
"""

from __future__ import annotations

from src.core.game_state import GameState


def _require_pair(state: GameState, issuer_id: str, holder_id: str, count: int) -> None:
    for pid in (issuer_id, holder_id):
        if pid not in state.players:
            raise ValueError(f"Unknown player: {pid}")
    if issuer_id == holder_id:
        raise ValueError("Debt tokens go between two different players.")
    if count < 1:
        raise ValueError("The number of debt tokens must be at least 1.")


def held_tokens(state: GameState, holder_id: str, issuer_id: str) -> int:
    """Ile żetonów ``issuer_id`` trzyma aktualnie ``holder_id``."""
    return state.debt_tokens.get(holder_id, {}).get(issuer_id, 0)


def give_debt_tokens(
    state: GameState, issuer_id: str, holder_id: str, count: int
) -> GameState:
    """Wystawca ``issuer_id`` oddaje ``holder_id`` ``count`` swoich żetonów długu."""
    _require_pair(state, issuer_id, holder_id, count)
    new_state = state.clone()
    by_issuer = new_state.debt_tokens.setdefault(holder_id, {})
    by_issuer[issuer_id] = by_issuer.get(issuer_id, 0) + count
    return new_state


def return_debt_tokens(
    state: GameState, holder_id: str, issuer_id: str, count: int
) -> GameState:
    """Posiadacz ``holder_id`` zwraca wystawcy ``issuer_id`` ``count`` jego żetonów.

    Raises:
        ValueError: Gdy posiadacz nie trzyma tylu żetonów tego wystawcy.
    """
    _require_pair(state, issuer_id, holder_id, count)
    have = held_tokens(state, holder_id, issuer_id)
    if count > have:
        raise ValueError(f"Cannot return {count} debt tokens - only {have} held.")
    new_state = state.clone()
    by_issuer = new_state.debt_tokens[holder_id]
    if have - count > 0:
        by_issuer[issuer_id] = have - count
    else:
        del by_issuer[issuer_id]
        if not by_issuer:
            del new_state.debt_tokens[holder_id]
    return new_state
