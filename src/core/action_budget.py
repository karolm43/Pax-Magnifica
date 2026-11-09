"""Budżet akcji gracza w turze fazy akcji (R_action_phase; RULES.md 31.7, 55.1).

Bazowo gracz wykonuje w turze JEDNĄ akcję (strategiczną, taktyczną albo komponentu). Wyjątki
zmieniają LIMIT przez punkt zaczepienia ``turn.actions`` (np. Fleet Logistics: 2 akcje), a nie
reguły bazowe. Wszystkie bramki „czy wolno wykonać akcję" i rejestracja wykonanej akcji idą
WYŁĄCZNIE tędy (punkt centralny, RULES.md 43.1a).

Moduł zależy tylko od ``game_state`` i ``rules_hooks`` (bez cykli z ``turn_flow``/``tactical``).
"""

from __future__ import annotations

from src.core import rules_hooks
from src.core.game_state import GameState

BASE_ACTIONS = 1


def actions_allowed(state: GameState, player_id: str) -> int:
    """Ile akcji wolno graczowi wykonać w jednej turze (bazowo 1, hooki mogą zwiększyć)."""
    return max(
        BASE_ACTIONS,
        rules_hooks.modify(rules_hooks.POINT_TURN_ACTIONS, state, player_id, BASE_ACTIONS),
    )


def actions_left(state: GameState, player_id: str) -> int:
    """Ile akcji zostało graczowi w bieżącej turze (0, gdy spasował)."""
    player = state.players.get(player_id)
    if player is None or player.passed:
        return 0
    # Flaga ``took_action_this_turn`` jest nadrzędna (God-Mode i stare zapisy ustawiają ją ręcznie):
    # False = żadna akcja, True bez licznika = jedna akcja.
    used = max(1, player.actions_this_turn) if player.took_action_this_turn else 0
    return max(0, actions_allowed(state, player_id) - used)


def require_free_action(state: GameState, player_id: str) -> None:
    """Rzuca ``ValueError``, gdy gracz wyczerpał limit akcji w tej turze.

    Przy dozwolonej drugiej akcji (Fleet Logistics) nie wolno zaczynać jej przed domknięciem
    pierwszej: trwająca akcja taktyczna / wieloetapowe primary blokują kolejną.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if actions_left(state, player_id) <= 0:
        raise ValueError(
            "You already took an action this turn - end your turn before acting again."
        )
    if player.took_action_this_turn and (
        state.active_system is not None or state.pending_strategy is not None
    ):
        raise ValueError("Finish your current action before starting another one.")


def register_action(state: GameState, player_id: str) -> None:
    """Zapisuje wykonaną akcję gracza (MUTUJE ``state`` - klon wołającego)."""
    player = state.players[player_id]
    previous = max(1, player.actions_this_turn) if player.took_action_this_turn else 0
    player.actions_this_turn = previous + 1
    player.took_action_this_turn = True


def reset_turn(state: GameState, player_id: str) -> None:
    """Nowa tura gracza: zeruje znacznik i licznik akcji (MUTUJE ``state``)."""
    player = state.players[player_id]
    player.took_action_this_turn = False
    player.actions_this_turn = 0
