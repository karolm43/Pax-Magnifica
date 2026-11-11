"""Stały nadzór limitów: pojemność (capacity) i pula floty (fleet pool) w KAŻDYM systemie.

RULES.md 42 / 39.6: nadwyżkę statków / ładunku trzeba usunąć „natychmiast", niezależnie od tego,
CO ją spowodowało (produkcja, karta akcji, relikt, agenda, zdolność frakcji, eksploracja...).
Kroki akcji taktycznej już sprawdzają limity w AKTYWNYM systemie (``tactical._check_can_leave``),
ale efekt poza aktywacją (np. karta stawiająca statki w innym systemie) omijał tę bramkę.
Ten moduł domyka lukę JEDNYM punktem: ``enforce_limits`` woła warstwa API po każdej zwykłej
akcji (``StateService.replace_state``), więc nowy efekt nie musi pamiętać o sprawdzeniu.

Funkcja CZYSTA (``state -> state``): otwiera okno ``CAPACITY`` albo ``FLEET_POOL`` dla pierwszego
systemu z nadwyżką. Kolejne systemy zostaną sprawdzone po zamknięciu okna (kolejny commit).
"""

from __future__ import annotations

from src.core import capacity, fleet_pool
from src.core.game_state import GameState, Phase
from src.core.registry import StaticDataRegistry

# Fazy, w których efekty realnie stawiają jednostki. Poza nimi (setup, strategia) nic nie
# sprawdzamy, żeby nie karać rozstawienia startowego.
_ENFORCED_PHASES = (Phase.ACTION, Phase.AGENDA)


def _skipped_positions(state: GameState) -> set[str]:
    """Systemy pomijane: aktywny system trwającej akcji taktycznej ma własną bramkę kroków."""
    if state.tactical_step is not None and state.active_system is not None:
        return {state.active_system}
    return set()


def systems_over_limit(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Pozycje systemów z nadwyżką capacity albo fleet pool (poza aktywnym systemem akcji)."""
    skip = _skipped_positions(state)
    result: list[str] = []
    for position in state.systems:
        if position in skip:
            continue
        over_capacity = capacity.players_with_excess(state, registry, position)
        if over_capacity or fleet_pool.players_with_excess(state, position):
            result.append(position)
    return result


def enforce_limits(state: GameState, registry: StaticDataRegistry | None) -> GameState:
    """Otwiera okno usunięcia nadwyżki dla pierwszego systemu ponad limit; inaczej bez zmian.

    Nic nie robi, gdy: brak rejestru, trwa inne okno, faza statusu (własny krok puli floty),
    nierozstrzygnięta eksploracja albo faza spoza ``_ENFORCED_PHASES``.
    """
    if registry is None or state.pending_window is not None or state.status is not None:
        return state
    if state.phase not in _ENFORCED_PHASES or state.exploration is not None:
        return state
    for position in systems_over_limit(state, registry):
        checked = capacity.open_capacity_check(state, registry, position)
        if checked.pending_window is None:
            checked = fleet_pool.open_fleet_pool_check(state, position)
        if checked.pending_window is not None:
            return checked
    return state
