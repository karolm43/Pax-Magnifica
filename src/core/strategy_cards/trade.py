"""Trade (inicjatywa 5, base) — RULES.md 30.6, R_trade.

Primary: +3 trade goods → uzupełnij commodities → wskaż graczy z DARMOWYM, obowiązkowym
secondary. Secondary: uzupełnij commodities (koszt: 1 żeton ze strategy pool).
"""

from __future__ import annotations

from typing import Any

from src.core.game_state import GameState
from src.core.strategy_cards.base import CardContext, CardSpec, Draft

INITIATIVE = 5
PRIMARY_TRADE_GOODS = 3  # krok 1: „gains 3 trade goods"


def replenish_commodities(state: GameState, player_id: str) -> None:
    """Uzupełnia commodities gracza do wartości z jego arkusza frakcji (nie więcej)."""
    player = state.players[player_id]
    player.commodities = max(player.commodities, player.commodity_value)


def _on_step(
    state: GameState,
    _ctx: CardContext,
    owner_id: str,
    step: str,
    draft: Draft,
    payload: dict[str, Any],
) -> None:
    """Krok „choose_free_players": aktywny wskazuje graczy z darmowym secondary."""
    if step != "choose_free_players":
        raise ValueError(f"Unknown Trade step: {step}")
    raw = payload.get("players", [])
    if not isinstance(raw, list) or not all(isinstance(p, str) for p in raw):
        raise ValueError("'players' must be a list of player ids.")
    chosen: list[str] = []
    for pid in raw:
        if pid not in state.players:
            raise ValueError(f"Unknown player: {pid}")
        if pid == owner_id:
            raise ValueError("You cannot choose yourself - choose OTHER players.")
        if pid in chosen:
            raise ValueError(f"Player chosen twice: {pid}")
        chosen.append(pid)
    draft["free_players"] = chosen


def _primary(
    state: GameState, _ctx: CardContext, owner_id: str, _draft: Draft
) -> None:
    state.players[owner_id].trade_goods += PRIMARY_TRADE_GOODS
    replenish_commodities(state, owner_id)


def _secondary(
    state: GameState, _ctx: CardContext, player_id: str, _payload: dict[str, Any]
) -> None:
    replenish_commodities(state, player_id)


def _options(
    state: GameState,
    _ctx: CardContext,
    player_id: str,
    _step: str | None,
    _draft: Draft,
) -> dict[str, Any]:
    return {"players": [p for p in state.players if p != player_id], "needs_input": False}


SPEC = CardSpec(
    primary_steps=("choose_free_players",),
    on_step=_on_step,
    primary=_primary,
    secondary=_secondary,
    secondary_costs_token=True,
    options=_options,
)
