"""Przepływ tur i faz (czyste funkcje nad ``GameState``).

Implementuje szkielet maszyny faz TI4 i kolejności tur fazy akcji — Etap E1 planu
pełnej rozgrywki (``docs/PLAN_PELNA_ROZGRYWKA.md``). Reguły spisane w ``docs/RULES.md`` 9
na podstawie AsyncTI4 (``EndTurnService.findNextUnpassedPlayer``). Zero reguł z pamięci.

Funkcje są czyste: przyjmują ``GameState``, zwracają NOWY ``GameState`` (przez ``clone``),
nie mutując wejścia — spójne z Event Sourcingiem (każdy wynik = nowa migawka).
"""

from __future__ import annotations

from src.core.game_state import GameState, Phase

# Kolejność faz rundy TI4.
_PHASE_SEQUENCE: list[Phase] = [
    Phase.STRATEGY,
    Phase.ACTION,
    Phase.STATUS,
    Phase.AGENDA,
]


def turn_order(state: GameState) -> list[str]:
    """Kolejność graczy wg inicjatywy (najniższy numer karty strategii pierwszy).

    Gracze bez karty strategii trafiają na koniec, w stabilnej kolejności po ``player_id``.
    """

    def key(player_id: str) -> tuple[int, str]:
        player = state.players[player_id]
        initiative = min(player.strategy_cards) if player.strategy_cards else 99
        return (initiative, player_id)

    return sorted(state.players, key=key)


def next_unpassed_player(state: GameState, current_id: str | None) -> str | None:
    """Następny gracz w kolejności, który nie spasował (ani nie jest wyeliminowany).

    Rotuje listę za bieżącego gracza i zwraca pierwszego aktywnego. Gdy wszyscy
    spasowali — zwraca None (koniec fazy akcji).
    """
    order = turn_order(state)
    if not order:
        return None
    # Ustaw punkt startowy tuż za bieżącym graczem.
    if current_id in order:
        idx = order.index(current_id)
        rotated = order[idx + 1 :] + order[: idx + 1]
    else:
        rotated = order
    for pid in rotated:
        if not state.players[pid].passed:
            return pid
    return None


def all_passed(state: GameState) -> bool:
    """Czy wszyscy gracze spasowali (koniec fazy akcji)."""
    if not state.players:
        return False
    return all(player.passed for player in state.players.values())


def end_turn(state: GameState) -> GameState:
    """Kończy turę bieżącego gracza i przekazuje ją następnemu niespasowanemu.

    Gdy nikt nie został (wszyscy spasowali) — przechodzi do fazy statusu.
    """
    new_state = state.clone()
    nxt = next_unpassed_player(new_state, new_state.active_player_id)
    if nxt is None:
        new_state.phase = Phase.STATUS
        new_state.active_player_id = None
    else:
        new_state.active_player_id = nxt
    return new_state


def pass_turn(state: GameState) -> GameState:
    """Bieżący gracz pasuje (pomijany do końca fazy akcji); tura idzie dalej."""
    new_state = state.clone()
    current = new_state.active_player_id
    if current is not None and current in new_state.players:
        new_state.players[current].passed = True
    nxt = next_unpassed_player(new_state, current)
    if nxt is None:
        new_state.phase = Phase.STATUS
        new_state.active_player_id = None
    else:
        new_state.active_player_id = nxt
    return new_state


def next_phase(state: GameState) -> GameState:
    """Przechodzi do następnej fazy w sekwencji (bez zmiany rundy).

    Wchodząc w fazę AKCJI, ustawia aktywnego gracza na pierwszego wg inicjatywy.
    """
    new_state = state.clone()
    idx = _PHASE_SEQUENCE.index(new_state.phase)
    new_state.phase = _PHASE_SEQUENCE[(idx + 1) % len(_PHASE_SEQUENCE)]
    if new_state.phase is Phase.ACTION:
        order = turn_order(new_state)
        new_state.active_player_id = order[0] if order else None
    return new_state


def next_round(state: GameState) -> GameState:
    """Rozpoczyna nową rundę: runda +1, faza = strategia, reset pasów i aktywnego."""
    new_state = state.clone()
    new_state.round_number += 1
    new_state.phase = Phase.STRATEGY
    new_state.active_player_id = None
    for player in new_state.players.values():
        player.passed = False
    return new_state
