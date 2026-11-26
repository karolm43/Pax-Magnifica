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


def in_bonus_action(state: GameState, player_id: str) -> bool:
    """Whether ``player_id`` is performing an extra action outside the turn order (Puppets on a
    String, Jupiter Brain - ``GameState.bonus_turn``)."""
    bonus = state.bonus_turn
    return bonus is not None and bonus.player == player_id


def outside_turn(state: GameState, player_id: str) -> bool:
    """Whether ``player_id`` acts although it is not their turn: the extra action of a passed
    player (Puppets on a String - ``BonusTurn.restore_passed``).

    C_action_cards/puppets-on-a-string/2: "It is not considered the turn of the player who played
    Puppets On A String for game effects" - no transactions (/3), nothing ends the turn (/4), no
    Fleet Logistics (/6).
    """
    bonus = state.bonus_turn
    return bonus is not None and bonus.player == player_id and bonus.restore_passed


def blocked_by_pass(state: GameState, player_id: str) -> bool:
    """Whether having passed stops ``player_id`` from performing actions.

    Puppets on a String: the player who played it "is still considered passed during their
    action" (C_action_cards/puppets-on-a-string/7) - ``passed`` stays True, yet they act.
    """
    player = state.players.get(player_id)
    return player is not None and player.passed and not in_bonus_action(state, player_id)


def actions_left(state: GameState, player_id: str) -> int:
    """Ile akcji zostało graczowi w bieżącej turze (0, gdy spasował)."""
    player = state.players.get(player_id)
    if player is None or blocked_by_pass(state, player_id):
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


def clear_reaction_traces(state: GameState) -> None:
    """Zeruje ślady okien kart reakcji: pauza końca tury, ostatnia transakcja, ostatnie odrzucenie.

    Wołane przy każdej nowej akcji (dowolnego gracza) i przy nowej turze - okno „po transakcji”,
    „po odrzuceniu karty” i „na końcu tury” trwa tylko do następnej akcji w grze.
    """
    state.turn_end_window = None
    state.last_transaction = []
    state.last_action_discard = None
    state.last_replenished = []
    state.last_research = []
    state.last_research_payment = None
    state.sustain_trace = []


def register_action(
    state: GameState, player_id: str, *, strategic: bool = False, component: str | None = None
) -> None:
    """Zapisuje wykonaną akcję gracza (MUTUJE ``state`` - klon wołającego).

    ``strategic`` = to akcja strategiczna (potrzebne efektom „jeśli kolejna akcja nie jest
    strategiczna”, np. Extreme Duress); ``component`` = id komponentu akcji komponentu (np. grana
    karta akcji, która nie może zniknąć z ręki, zanim zostanie zagrana). Efekty trwałe reagujące
    na początek akcji uruchamia punkt ``POINT_ACTION_STARTED``.
    """
    player = state.players[player_id]
    previous = max(1, player.actions_this_turn) if player.took_action_this_turn else 0
    player.actions_this_turn = previous + 1
    player.took_action_this_turn = True
    clear_reaction_traces(state)
    rules_hooks.run_persistent(
        rules_hooks.POINT_ACTION_STARTED,
        state,
        player_id,
        {"strategic": strategic, "component": component or ""},
    )


def unregister_action(state: GameState, player_id: str) -> None:
    """Oddaje ostatnią zarejestrowaną akcję tury (Coup d'Etat: akcja strategiczna się nie
    odbyła). Ślady okien wyczyszczone przy rejestracji zostają wyczyszczone (MUTUJE ``state``)."""
    player = state.players[player_id]
    player.actions_this_turn = max(0, player.actions_this_turn - 1)
    player.took_action_this_turn = player.actions_this_turn > 0


def reset_turn(state: GameState, player_id: str) -> None:
    """Nowa tura gracza: zeruje znacznik i licznik akcji (MUTUJE ``state``)."""
    player = state.players[player_id]
    player.took_action_this_turn = False
    player.actions_this_turn = 0
    clear_reaction_traces(state)
    # Stoły transakcji i umowy Trade żyją tylko w bieżącej turze (RULES.md 47.1b, 47.4).
    state.transaction_tables = []
    state.trade_deals = {}
