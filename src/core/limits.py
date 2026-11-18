"""Stały nadzór limitów: pojemność (capacity) i pula floty (fleet pool) w KAŻDYM systemie.

RULES.md 42 / 39.6: nadwyżkę statków / ładunku trzeba usunąć „natychmiast", niezależnie od tego,
CO ją spowodowało (produkcja, karta akcji, relikt, agenda, zdolność frakcji, eksploracja...).
Kroki akcji taktycznej już sprawdzają limity w AKTYWNYM systemie (``tactical._check_can_leave``),
ale efekt poza aktywacją (np. karta stawiająca statki w innym systemie) omijał tę bramkę.
Ten moduł domyka lukę JEDNYM punktem: ``enforce_limits`` woła warstwa API po każdej zwykłej
akcji (``StateService.replace_state``), więc nowy efekt nie musi pamiętać o sprawdzeniu.

Funkcja CZYSTA (``state -> state``): otwiera okno ``CAPACITY`` albo ``FLEET_POOL`` dla pierwszego
systemu z nadwyżką. Kolejne systemy zostaną sprawdzone po zamknięciu okna (kolejny commit).

Pula floty (RULES.md 42.1, decyzja użytkownika 2026-11-13): „if at any time … remove excess" -
sprawdzana NATYCHMIAST w KAŻDYM systemie, także w aktywnym systemie trwającej akcji taktycznej i
w trakcie innego okna (to okno czeka zawieszone - ``timing.interrupt``). Akcje bez własnego okna
blokuje ``timing.require_no_limit_window``.
"""

from __future__ import annotations

from src.core import capacity, fleet_pool, timing
from src.core.game_state import GameState, Phase, WindowType
from src.core.registry import StaticDataRegistry

# Fazy, w których efekty realnie stawiają jednostki. Faza strategii od 2. rundy też: koniec fazy
# statusu stawia jednostki (Genesis Sola, F_sol: „After, the Sol player might need to remove an
# infantry or fighter to meet capacity limits”), a następna jest faza strategii (bez agendy).
# Faza strategii 1. rundy = rozstawienie startowe - nie sprawdzamy (RULES.md 42.x).
_ENFORCED_PHASES = (Phase.ACTION, Phase.AGENDA)


def _enforced_phase(state: GameState) -> bool:
    if state.phase in _ENFORCED_PHASES:
        return True
    return state.phase is Phase.STRATEGY and state.round_number > 1 and state.setup is None


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


def fleet_pool_excess(state: GameState) -> tuple[str, list[str]] | None:
    """Pierwszy system z nadwyżką puli floty (każdy, także aktywny) i gracze do usunięcia."""
    for position in state.systems:
        queue = fleet_pool.players_with_excess(state, position)
        if queue:
            return position, queue
    return None


def enforce_limits(state: GameState, registry: StaticDataRegistry | None) -> GameState:
    """Otwiera okno usunięcia nadwyżki dla pierwszego systemu ponad limit; inaczej bez zmian.

    Pula floty: zawsze i natychmiast (przerywa inne okno). Capacity: gdy nie trwa inne okno ani
    eksploracja. Nic nie robi bez rejestru, w fazie statusu (własny krok puli floty) i w fazie
    strategii 1. rundy (``_enforced_phase``).
    """
    if registry is None or state.status is not None or not _enforced_phase(state):
        return state
    window = state.pending_window
    if window is None or window.window_type not in timing.LIMIT_WINDOWS:
        excess = fleet_pool_excess(state)
        if excess is not None:
            position, queue = excess
            return timing.interrupt(
                state, WindowType.FLEET_POOL, queue, context={"position": position}
            )
    if state.pending_window is not None or state.exploration is not None:
        return state
    for position in systems_over_limit(state, registry):
        # Nadwyżka bez wyboru znika od razu (RULES.md 39.6 C5) - stan idzie dalej.
        state = capacity.open_capacity_check(state, registry, position)
        if state.pending_window is not None:
            return state
    return state
