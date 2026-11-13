"""Leadership (inicjatywa 1, base) — RULES.md 30.2 / 30.7, R_leadership + R_influence.

Primary: zdobądź 3 żetony dowodzenia; potem MOŻESZ wydać dowolną ilość wpływu, by zdobyć
1 żeton za każde 3 wpływu. Secondary (BEZ żetonu ze strategy pool): wydaj wpływ, 1 żeton za
3 wpływu. Zdobyte żetony gracz kładzie w pulach wedle własnego wyboru. Nadwyżka wpływu
(do 2) przepada. Żetony pochodzą z rezerwy — nie można zdobyć więcej, niż w niej leży.
"""

from __future__ import annotations

from typing import Any

from src.core.game_state import GameState
from src.core.payment import (
    apply_payment,
    parse_payment,
    ready_planet_values,
    trade_good_value,
    validate_payment,
)
from src.core.strategy_cards.base import CardContext, CardSpec, Draft
from src.core.strategy_cards.common import (
    check_distribution,
    gain_tokens,
    gainable_tokens,
    parse_pools,
)

INITIATIVE = 1
BASE_TOKENS = 3  # primary: „gains three command tokens"
INFLUENCE_PER_TOKEN = 3  # „one command token for every three influence"


def _bought(state: GameState, ctx: CardContext, player_id: str,
            planets: list[str], tg: int) -> int:
    paid = validate_payment(state, ctx.registry, player_id, "influence", planets, tg)
    return paid // INFLUENCE_PER_TOKEN


def _on_step(
    state: GameState,
    ctx: CardContext,
    owner_id: str,
    step: str,
    draft: Draft,
    payload: dict[str, Any],
) -> None:
    if step == "spend_influence":
        planets, tg = parse_payment(payload)
        bought = _bought(state, ctx, owner_id, planets, tg)
        draft["planets"] = planets
        draft["trade_goods"] = tg
        draft["gain"] = gainable_tokens(state, owner_id, BASE_TOKENS + bought)
    elif step == "distribute":
        check_distribution(parse_pools(payload), int(draft.get("gain", 0)))
        draft["pools"] = parse_pools(payload)
    else:
        raise ValueError(f"Unknown Leadership step: {step}")


def _primary(
    state: GameState, _ctx: CardContext, owner_id: str, draft: Draft
) -> None:
    apply_payment(state, owner_id, draft.get("planets", []), int(draft.get("trade_goods", 0)))
    gain_tokens(state, owner_id, draft["pools"])


def _secondary(
    state: GameState, ctx: CardContext, player_id: str, payload: dict[str, Any]
) -> None:
    planets, tg = parse_payment(payload)
    bought = _bought(state, ctx, player_id, planets, tg)
    gain = gainable_tokens(state, player_id, bought)
    pools = parse_pools(payload)
    check_distribution(pools, gain)
    apply_payment(state, player_id, planets, tg)
    gain_tokens(state, player_id, pools)


def _options(
    state: GameState,
    ctx: CardContext,
    player_id: str,
    step: str | None,
    draft: Draft,
) -> dict[str, Any]:
    player = state.players[player_id]
    if step == "distribute":
        return {"gain": int(draft.get("gain", 0))}
    return {
        "planets": ready_planet_values(state, ctx.registry, player_id, "influence"),
        "trade_goods": player.trade_goods,
        "trade_good_value": trade_good_value(state, player_id),
        "reinforcements": player.cc_reinf,
        "base_gain": BASE_TOKENS if step == "spend_influence" else 0,
        "per_token": INFLUENCE_PER_TOKEN,
        "needs_input": True,  # „follow" wymaga wyboru planet i rozkładu żetonów
    }


SPEC = CardSpec(
    primary_steps=("spend_influence", "distribute"),
    on_step=_on_step,
    primary=_primary,
    secondary=_secondary,
    secondary_costs_token=False,
    options=_options,
)
