"""Wykrywanie końca gry po progu punktów zwycięstwa (niezależnie od źródła punktów).

``objectives.award_points`` kończy grę przy punktowaniu celów, ale VP padają też z innych
miejsc (Imperial, karty, agendy, korekta God-Mode). Dlatego ``apply_victory`` jest wołane
przy KAŻDYM zatwierdzeniu stanu (``StateService.replace_state``): gdy ktokolwiek ma
``vps_to_win`` punktów, gra kończy się natychmiast (R_victory_points).
"""

from __future__ import annotations

from src.core import objectives, turn_flow
from src.core.game_state import GameState


def apply_victory(state: GameState) -> GameState:
    """Ustala zwycięzcę, gdy ktoś osiągnął próg VP (mutuje i zwraca ``state``).

    Przy kilku graczach nad progiem wygrywa najwyższy wynik, remis → pierwszy w kolejności
    inicjatywy (jak ``objectives.leaders_by_points``).
    """
    if state.winner_id is not None or state.vps_to_win <= 0:
        return state
    if not any(p.victory_points >= state.vps_to_win for p in state.players.values()):
        return state
    order = turn_flow.initiative_order(state)
    order += [p for p in state.players if p not in order]
    state.winner_id = objectives.leaders_by_points(state, order)
    state.end_reason = "victory_points"
    return state
