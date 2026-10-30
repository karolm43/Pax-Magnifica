"""Przepływ tur i faz (czyste funkcje nad ``GameState``).

Implementuje szkielet maszyny faz TI4 i kolejności tur fazy akcji — Etap E1 planu
pełnej rozgrywki (``docs/PLAN_PELNA_ROZGRYWKA.md``). Reguły spisane w ``docs/RULES.md`` 9
na podstawie AsyncTI4 (``EndTurnService.findNextUnpassedPlayer``). Zero reguł z pamięci.

Funkcje są czyste: przyjmują ``GameState``, zwracają NOWY ``GameState`` (przez ``clone``),
nie mutując wejścia — spójne z Event Sourcingiem (każdy wynik = nowa migawka).
"""

from __future__ import annotations

from src.core.game_state import GameState, Phase
from src.core.strategy_phase import next_strategy_picker

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


# Alias czytelnościowy: kolejność inicjatywy = kolejność tur fazy akcji ORAZ kroków
# fazy statusu (RULES.md 31.3). Ta sama funkcja, inna nazwa w kontekście statusu.
initiative_order = turn_order


def _require_action_turn(state: GameState, player_id: str | None) -> None:
    """Twarda walidacja: jesteśmy w fazie akcji i to tura ``player_id`` (RULES.md 31.2).

    ``player_id=None`` pomija kontrolę tożsamości (zgodność wsteczna / wywołania
    wewnętrzne) — ale faza nadal musi być ACTION. God-Mode nie przechodzi tędy.

    Raises:
        ValueError: Gdy faza != ACTION, brak aktywnego gracza, lub ``player_id`` nie
            jest aktywnym graczem.
    """
    if state.phase is not Phase.ACTION:
        raise ValueError("Zakończyć/spasować turę można tylko w fazie akcji.")
    if state.active_player_id is None:
        raise ValueError("Brak aktywnego gracza w fazie akcji.")
    if player_id is not None and player_id != state.active_player_id:
        raise ValueError(
            f"To nie tura gracza {player_id} (aktywny: {state.active_player_id})."
        )


def end_turn(state: GameState, player_id: str | None = None) -> GameState:
    """Kończy turę aktywnego gracza i przekazuje ją następnemu niespasowanemu.

    Twardo waliduje fazę akcji i (gdy podano) tożsamość aktywnego gracza — RULES.md 31.2.
    Gdy nikt nie został (wszyscy spasowali) — przechodzi do fazy statusu.

    Raises:
        ValueError: Gdy nie wolno zakończyć tury (patrz ``_require_action_turn``).
    """
    _require_action_turn(state, player_id)
    new_state = state.clone()
    nxt = next_unpassed_player(new_state, new_state.active_player_id)
    if nxt is None:
        new_state.phase = Phase.STATUS
        new_state.active_player_id = None
    else:
        new_state.active_player_id = nxt
    return new_state


def pass_turn(state: GameState, player_id: str | None = None) -> GameState:
    """Aktywny gracz pasuje (pomijany do końca fazy akcji); tura idzie dalej.

    Twardo waliduje fazę akcji i tożsamość (RULES.md 31.2). Dodatkowo: gracz NIE MOŻE
    spasować, dopóki nie wykona akcji strategicznej swojej karty (zagranie karty =
    wpis w ``exhausted_strategy_cards``) — reguła R_action_phase.

    Raises:
        ValueError: Gdy nie wolno spasować (zła faza/tura albo brak akcji strategicznej).
    """
    _require_action_turn(state, player_id)
    current = state.active_player_id
    assert current is not None  # zagwarantowane przez _require_action_turn
    player = state.players.get(current)
    # Pas dopiero po akcji strategicznej: gracz z kartą strategii musi ją zagrać.
    if (
        player is not None
        and player.strategy_cards
        and not player.exhausted_strategy_cards
    ):
        raise ValueError(
            "Nie można spasować przed wykonaniem akcji strategicznej (zagraj kartę)."
        )
    new_state = state.clone()
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
        # Faza akcji: kolejność tur wg INICJATYWY kart (RULES.md 9).
        order = turn_order(new_state)
        new_state.active_player_id = order[0] if order else None
    elif new_state.phase is Phase.STRATEGY:
        # Faza strategii: wybór zaczyna MÓWCA, dalej speaker order (RULES.md 24).
        new_state.active_player_id = next_strategy_picker(new_state)
    else:
        # Status/Agenda nie mają pojęcia "aktywnej tury" w tym szkielecie.
        new_state.active_player_id = None
    return new_state


def next_round(state: GameState) -> GameState:
    """Rozpoczyna nową rundę: runda +1, faza = strategia, reset pasów i aktywnego."""
    new_state = state.clone()
    new_state.round_number += 1
    new_state.phase = Phase.STRATEGY
    for player in new_state.players.values():
        player.passed = False
    # Nowa runda zaczyna się fazą strategii: wybiera mówca (RULES.md 24).
    # Wołane po reset_strategy_cards (flow.py), więc karty są już wyczyszczone.
    new_state.active_player_id = next_strategy_picker(new_state)
    return new_state
