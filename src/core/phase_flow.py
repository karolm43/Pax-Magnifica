"""Ogłoszenia mówcy: następna faza i nowa runda (RULES.md 31.4). Funkcje CZYSTE.

Wcześniej ta logika (wybór funkcji domykającej fazę i komunikaty bramy) leżała w routerze
``/phase/next``. Przeniesiona tutaj, żeby każdy aktor (UI przez ``api/`` i bot przez
``src/engine/``) przechodził tę samą ścieżkę reguł (RULES.md 65.1).
"""

from __future__ import annotations

from src.core import agenda_phase, status_phase, strategy_phase, turn_flow
from src.core.game_state import GameState, Phase
from src.core.registry import StaticDataRegistry


def _blocked_reason(state: GameState) -> str:
    """Czytelny powód, dla którego mówca nie może jeszcze ogłosić następnej fazy."""
    open_reason = turn_flow.open_decisions_reason(state)
    if open_reason is not None:
        return open_reason
    if state.phase is Phase.ACTION:
        return "Every player must pass before the speaker can end the Action Phase."
    if state.phase in (Phase.STATUS, Phase.AGENDA) and state.winner_id is not None:
        return "The game has ended."
    if state.phase is Phase.STATUS and state.status is not None:
        return (
            "Finish the Status Phase steps (score objectives, then redistribute "
            "command tokens) before the speaker can return the Strategy Cards."
        )
    if state.phase is Phase.STATUS:
        return (
            "Every player must take their Status step before the speaker "
            "can end the Status Phase."
        )
    if state.phase is Phase.AGENDA:
        return (
            "Resolve both agendas (reveal, vote, outcome) before the speaker "
            "can end the Agenda Phase."
        )
    return "All players must pick their Strategy Cards before advancing."


def announce_next_phase(
    state: GameState, registry: StaticDataRegistry, player_id: str | None = None
) -> GameState:
    """Mówca ogłasza następną fazę rundy (Strategia → Akcja → Status → Agenda).

    ``player_id`` podany musi być mówcą (``None`` = wywołanie wewnętrzne, bez kontroli
    tożsamości). Status z trwającym stanem kroków kończy ``finish_status`` (krok 8), agenda —
    ``finish_agenda``; pozostałe fazy — ``turn_flow.next_phase``.

    Raises:
        ValueError: Nie mówca albo brama fazy zamknięta (powód po angielsku, jak w UI).
    """
    if player_id is not None and player_id != state.speaker_id:
        raise ValueError(
            f"Only the speaker announces a phase transition (speaker: {state.speaker_id})."
        )
    if not turn_flow.can_advance_phase(state):
        raise ValueError(_blocked_reason(state))
    if state.phase is Phase.STATUS and state.status is not None:
        return status_phase.finish_status(state, registry)
    if state.phase is Phase.AGENDA and state.agenda is not None:
        return agenda_phase.finish_agenda(state, registry)
    return turn_flow.next_phase(state)


def announce_next_round(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Mówca rozpoczyna nową rundę: +1 TG na niewybranych kartach, zwrot kart, runda +1.

    Kolejność jak dotąd w routerze ``/round/next``: accumulate/zwrot kart → ``next_round``.
    """
    state = strategy_phase.close_round_cards(state, registry)
    return turn_flow.next_round(state)
