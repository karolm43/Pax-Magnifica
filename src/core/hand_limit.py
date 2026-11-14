"""Limit ręki kart akcji (R_action_cards; RULES.md 53.8).

„Each player's hand can have a maximum of seven action cards. If a player ever has more than
seven action cards, that player must choose seven cards to keep and discard the rest.”
„If a player has more than seven action cards, they must discard the excess immediately. They
cannot play them to get down to seven, and the Hacan player cannot trade them.”

Limit z assetów (``engine_config.json`` → ``hand_limits.action_cards``). Nadwyżka nie jest
odrzucana automatycznie — gracz SAM wybiera karty (R56), przeciągając je na stos odrzuconych.
Dopóki ma nadwyżkę: nie zagra karty akcji, nie odda jej w transakcji, nie skończy tury ani
nie przejdzie fazy (``turn_flow``). Odrzucenie emituje zwykłe „po odrzuceniu karty akcji”.
"""

from __future__ import annotations

from src.core import card_draw, rules_hooks
from src.core.game_state import GameState


def action_card_limit(state: GameState, player_id: str) -> int | None:
    """Limit kart akcji gracza (``None`` = bez limitu albo brak rejestru w kontekście)."""
    if state.action_card_limit_disabled:
        return None  # God-Mode: limit wyłączony przez hosta.
    registry = rules_hooks.bound_registry()
    if registry is None:
        return None
    limit = registry.hand_limits().action_cards
    if limit is None:
        return None
    # Hook MODIFY (Executive Sanctions: maks. 3 karty - RULES.md 51.6).
    delta = rules_hooks.modify(
        rules_hooks.POINT_HAND_LIMIT, state, player_id, 0, {"base": int(limit)}
    )
    return max(0, int(limit) + int(delta))


def action_card_excess(state: GameState, player_id: str) -> int:
    """Ile kart akcji gracz ma ponad limit (0 = w limicie)."""
    player = state.players.get(player_id)
    limit = action_card_limit(state, player_id)
    if player is None or limit is None:
        return 0
    return max(0, len(player.private.action_cards) - limit)


def players_over_limit(state: GameState) -> dict[str, int]:
    """Gracze z nadwyżką kart akcji: ``{player_id: ile odrzucić}``."""
    found = {pid: action_card_excess(state, pid) for pid in state.players}
    return {pid: n for pid, n in found.items() if n > 0}


def over_limit_reason(state: GameState, player_id: str | None = None) -> str | None:
    """Powód blokady: gracz (albo ktokolwiek, gdy ``player_id=None``) musi najpierw odrzucić."""
    over = players_over_limit(state)
    if player_id is not None:
        excess = over.get(player_id, 0)
        if excess <= 0:
            return None
        return (
            f"You have more than {action_card_limit(state, player_id)} action cards - "
            f"discard {excess} first."
        )
    if not over:
        return None
    return "A player has more action cards than the hand limit - they must discard first."


def discard_excess(state: GameState, player_id: str, card_id: str) -> GameState:
    """Gracz z nadwyżką odrzuca WYBRANĄ kartę akcji (jedna na raz, przeciągnięcie w UI).

    Raises:
        ValueError: Gracz nie ma nadwyżki albo karty w ręce.
    """
    if action_card_excess(state, player_id) <= 0:
        raise ValueError("You are within the action card hand limit - nothing to discard.")
    new_state = state.clone()
    card_draw.discard_chosen_action_cards(new_state, player_id, [card_id])
    return new_state
