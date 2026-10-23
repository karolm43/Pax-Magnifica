"""Akcja taktyczna — maszyna kroków i aktywacja systemu (czyste funkcje nad ``GameState``).

Etap E3 planu pełnej rozgrywki (``docs/PLAN_PELNA_ROZGRYWKA.md``). Aplikacja PROWADZI
gracza przez kroki akcji taktycznej (aktywacja → ruch → space cannon → walka kosmiczna →
inwazja → produkcja), ale NIE waliduje reguł TI4: gracze grają fizycznie i wprowadzają
wynik do aplikacji (decyzja projektowa — asystent stołu, nie sędzia). Te funkcje realizują
mechaniczne operacje na stanie (połóż żeton dowodzenia, ustaw aktywny system, przejdź do
kolejnego kroku), nie egzekwując legalności.

Reguły (jako referencja TI4) spisane w ``docs/RULES.md`` 19 na podstawie AsyncTI4
(``CommandCounterHelper.addCC``, ``Tile.addCC``, ``Game.activeSystem``,
``service/tactical/``). Zero reguł z pamięci.

Funkcje są czyste: przyjmują ``GameState``, zwracają NOWY ``GameState`` (przez ``clone``),
nie mutując wejścia — spójne z Event Sourcingiem.
"""

from __future__ import annotations

from src.core.game_state import GameState, SystemState, TacticalStep
from src.core.hex_grid import HexGrid

# Kolejność kroków akcji taktycznej (okna czasowe fazy akcji — RULES.md 19).
_STEP_SEQUENCE: list[TacticalStep] = [
    TacticalStep.ACTIVATION,
    TacticalStep.MOVEMENT,
    TacticalStep.SPACE_CANNON,
    TacticalStep.SPACE_COMBAT,
    TacticalStep.INVASION,
    TacticalStep.PRODUCTION,
]


def _ensure_system(state: GameState, position: str, grid: HexGrid) -> SystemState:
    """Zwraca system ze stanu lub tworzy nowy (z ``system_id`` z grida).

    Mutuje przekazany ``state`` (zakłada się, że to już klon), zapisując system
    w ``state.systems`` gdy go nie było.
    """
    system = state.systems.get(position)
    if system is None:
        system_id = grid.system_id_at(position) if position in grid.positions else ""
        system = SystemState(position=position, system_id=system_id)
        state.systems[position] = system
    return system


def activate_system(state: GameState, grid: HexGrid, position: str) -> GameState:
    """Aktywuje system przez aktywnego gracza (fundament akcji taktycznej).

    Kładzie żeton dowodzenia aktywnego gracza w przestrzeni systemu, ustawia
    ``active_system`` i rozpoczyna maszynę kroków (``tactical_step = MOVEMENT`` —
    aktywacja sama jest krokiem zerowym, od razu przechodzimy do ruchu). Zużywa
    1 żeton z puli taktycznej gracza (``tactical_cc``), odkładając go na system
    (odpowiednik ``CommandCounterHelper.addCC`` z ``useTactic=true``).

    Aplikacja NIE waliduje reguł TI4 (np. „nie aktywuj systemu z własnym CC",
    „musisz mieć żeton w puli") — to operator pilnuje legalności. Jedyny twardy
    warunek to istnienie aktywnego gracza.

    Raises:
        ValueError: Gdy nie ustawiono aktywnego gracza (``active_player_id``).
    """
    active_id = state.active_player_id
    if active_id is None:
        raise ValueError("Brak aktywnego gracza — nie można aktywować systemu.")

    new_state = state.clone()
    system = _ensure_system(new_state, position, grid)

    # Żeton dowodzenia aktywnego gracza w przestrzeni (bez duplikatu).
    if active_id not in system.command_tokens:
        system.command_tokens.append(active_id)

    # Zużycie z puli taktycznej (nie schodzimy poniżej zera — to tylko licznik,
    # nie reguła; operator może i tak grać dalej).
    player = new_state.players.get(active_id)
    if player is not None and player.tactical_cc > 0:
        player.tactical_cc -= 1

    new_state.active_system = position
    new_state.tactical_step = TacticalStep.MOVEMENT
    return new_state


def next_step(state: GameState) -> GameState:
    """Przechodzi do następnego kroku akcji taktycznej.

    Po ostatnim kroku (``PRODUCTION``) kończy akcję taktyczną (czyści krok i aktywny
    system — patrz ``end_tactical_action``). Gdy akcja nie trwa (``tactical_step`` jest
    None) — bez zmian.
    """
    if state.tactical_step is None:
        return state.clone()
    idx = _STEP_SEQUENCE.index(state.tactical_step)
    if idx >= len(_STEP_SEQUENCE) - 1:
        return end_tactical_action(state)
    new_state = state.clone()
    new_state.tactical_step = _STEP_SEQUENCE[idx + 1]
    return new_state


def set_step(state: GameState, step: TacticalStep) -> GameState:
    """Ustawia konkretny krok akcji taktycznej (skok do kroku — np. z UI).

    Przydatne, gdy operator chce wrócić/przeskoczyć (np. pominąć walkę). Zero reguł.
    """
    new_state = state.clone()
    new_state.tactical_step = step
    return new_state


def end_tactical_action(state: GameState) -> GameState:
    """Kończy bieżącą akcję taktyczną: czyści ``active_system`` i ``tactical_step``.

    NIE zdejmuje żetonu dowodzenia z systemu (żeton zostaje — tak jak na stole).
    Tura gracza idzie dalej przez ``turn_flow.end_turn`` (osobna akcja).
    """
    new_state = state.clone()
    new_state.active_system = None
    new_state.tactical_step = None
    return new_state
