"""Przeskok fazy / gracza dla testów w God-Mode (``/phase/skip``, ``/turn/skip-player``).

NIE dla zwykłej rozgrywki.

Zwykły przepływ (``turn_flow``) zostaje nietknięty: tu tylko SPRZĄTAMY blokady
(otwarte okno, walka, inwazja, akcja taktyczna), dobieramy brakujące karty strategii
i wołamy TE SAME funkcje przejścia (``next_phase`` / ``next_round``), więc wszystkie
efekty wejścia w fazę (naprawa jednostek, reset pasów, aktywny gracz) działają jak
zawsze. Nowa funkcja nie zmienia semantyki żadnej istniejącej reguły ani testu.
"""

from __future__ import annotations

from src.core import action_budget, agenda_phase, status_phase, strategy_phase, triggers, turn_flow
from src.core.game_state import GameState, Phase
from src.core.registry import StaticDataRegistry


def _clear_blockers(state: GameState) -> None:
    """Zamyka wszystko, co blokuje przejście fazy (mutuje przekazany klon)."""
    state.pending_window = None
    state.suspended_window = None
    triggers.drop_all_offers(state)  # decyzje graczy też blokują przejście fazy (RULES.md 54.8)
    state.pending_strategy = None
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
    if work.phase is Phase.STATUS:
        # Status z domyślnymi decyzjami (RULES.md 41): bez punktowania, nowe żetony do puli
        # taktycznej; po kroku 8 agenda (gdy zdjęto Custodians) albo nowa runda.
        return status_phase.complete_status(work, registry)
    if work.phase is Phase.AGENDA and work.agenda is not None:
        # Faza agendy z kolejnymi krokami (RULES.md 51): bez głosowań, planety gotowe, runda +1.
        return agenda_phase.skip_agenda(work, registry)
    if work.phase is Phase.AGENDA:
        work = strategy_phase.close_round_cards(work, registry)
        return turn_flow.next_round(work)
    return turn_flow.next_phase(work)


def skip_player(state: GameState) -> GameState:
    """Oddaje turę w fazie akcji następnemu graczowi BEZ akcji i pasa (God-Mode).

    Do testowania tur wszystkich graczy: sprzątamy blokady jak przy ``skip_phase``
    (okno, walka, akcja taktyczna), a następny gracz dostaje świeżą turę — tak jak
    po ``end_turn``, ale bez wymogu akcji i bez wyzwalaczy końca/początku tury.
    Kolejność: następny niespasowany; gdy wszyscy spasowali — po prostu następny
    w kolejności inicjatywy (by dało się przełączać między graczami dalej).

    Raises:
        ValueError: Poza fazą akcji (w pozostałych fazach aktywnego gracza wyznacza
            ich własny przebieg kroków).
    """
    if state.phase is not Phase.ACTION:
        raise ValueError("Skip player works only in the action phase.")
    work = state.clone()
    _clear_blockers(work)
    work.held_play = None
    work.exploration = None
    work.bonus_turn = None
    current = work.active_player_id
    nxt = turn_flow.next_unpassed_player(work, current)
    if nxt is None or nxt == current:
        order = turn_flow.turn_order(work)
        if not order:
            return work
        idx = order.index(current) if current in order else -1
        nxt = order[(idx + 1) % len(order)]
    work.active_player_id = nxt
    work.expeditions.performed_by = None
    action_budget.reset_turn(work, nxt)
    work.players[nxt].transacted_with = []
    return work
