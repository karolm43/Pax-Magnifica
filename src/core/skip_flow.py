"""Przeskok fazy dla testów w God-Mode (``/phase/skip``) — NIE dla zwykłej rozgrywki.

Zwykły przepływ (``turn_flow``) zostaje nietknięty: tu tylko SPRZĄTAMY blokady
(otwarte okno, walka, inwazja, akcja taktyczna), dobieramy brakujące karty strategii
i wołamy TE SAME funkcje przejścia (``next_phase`` / ``next_round``), więc wszystkie
efekty wejścia w fazę (naprawa jednostek, reset pasów, aktywny gracz) działają jak
zawsze. Nowa funkcja nie zmienia semantyki żadnej istniejącej reguły ani testu.
"""

from __future__ import annotations

from src.core import strategy_phase, turn_flow
from src.core.game_state import GameState, Phase
from src.core.registry import StaticDataRegistry


def _clear_blockers(state: GameState) -> None:
    """Zamyka wszystko, co blokuje przejście fazy (mutuje przekazany klon)."""
    state.pending_window = None
    state.active_combat = None
    state.invasion = None
    state.active_system = None
    state.tactical_step = None


def _autofill_strategy(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Dobiera graczom brakujące karty strategii (najniższa wolna inicjatywa)."""
    # Górny bezpiecznik pętli: pick_count <= 2 kart * max 8 graczy.
    for _ in range(32):
        picker = strategy_phase.next_strategy_picker(state)
        if picker is None:
            break
        taken = strategy_phase.picked_initiatives(state)
        free = [
            n for n in strategy_phase.available_initiatives(registry) if n not in taken
        ]
        if not free:
            raise ValueError("No free strategy cards left to auto-pick.")
        state = strategy_phase.pick_strategy_card(state, registry, picker, min(free))
    return state


def skip_phase(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Przeskakuje do następnej fazy z pominięciem bram (tryb testowy God-Mode).

    - STRATEGY: autowybór brakujących kart → ACTION.
    - ACTION/STATUS: bez wymagania pasów → następna faza.
    - AGENDA: jak ``/round/next`` (TG na niewybranych kartach, reset kart, runda +1).

    Raises:
        ValueError: Gdy nie da się dobrać kart (np. nieobsługiwana liczba graczy).
    """
    work = state.clone()
    _clear_blockers(work)
    if work.phase is Phase.STRATEGY:
        work = _autofill_strategy(work, registry)
        return turn_flow.next_phase(work)
    if work.phase is Phase.AGENDA:
        work = strategy_phase.accumulate_unpicked_tg(work, registry)
        work = strategy_phase.reset_strategy_cards(work)
        return turn_flow.next_round(work)
    return turn_flow.next_phase(work)
