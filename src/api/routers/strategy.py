"""Router fazy strategii (Etap E2): pula kart, wybór, zagranie."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    StateEnvelope,
    StrategyCardInfo,
    StrategyPickRequest,
    StrategyPlayRequest,
)
from src.core import strategy_phase

router = APIRouter()


@router.get("/strategy/cards", response_model=list[StrategyCardInfo])
def get_strategy_cards(ctx: AppContext = Depends(get_ctx)) -> list[StrategyCardInfo]:
    """Pula kart strategii aktywnego zestawu + ich stan w bieżącej grze."""
    state = ctx.service.current_state()
    owner_by_init: dict[int, str] = {}
    exhausted_by_init: dict[int, bool] = {}
    for pid, player in state.players.items():
        for init in player.strategy_cards:
            owner_by_init[init] = pid
            exhausted_by_init[init] = init in player.exhausted_strategy_cards
    cards: list[StrategyCardInfo] = []
    for card in ctx.registry.strategy_card_set():
        cards.append(
            StrategyCardInfo(
                initiative=card.initiative,
                id=card.id,
                name=card.name,
                primary_texts=list(card.primary_texts),
                secondary_texts=list(card.secondary_texts),
                colour_hex_code=card.colour_hex_code,
                trade_goods=state.strategy_card_tg.get(card.initiative, 0),
                picked_by=owner_by_init.get(card.initiative),
                exhausted=exhausted_by_init.get(card.initiative, False),
            )
        )
    return cards


async def _commit(ctx: AppContext, new_state, label: str) -> StateEnvelope:  # type: ignore[no-untyped-def]
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/strategy/pick", response_model=StateEnvelope)
async def post_strategy_pick(
    request: StrategyPickRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz wybiera kartę strategii (transfer TG z karty, ustala inicjatywę)."""
    try:
        new_state = strategy_phase.pick_strategy_card(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.initiative,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, f"strategy:pick:{request.player_id}:{request.initiative}"
    )


@router.post("/strategy/play", response_model=StateEnvelope)
async def post_strategy_play(
    request: StrategyPlayRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz zagrywa (wyczerpuje) swoją kartę strategii."""
    try:
        new_state = strategy_phase.play_strategy_card(
            ctx.service.current_state(), request.player_id, request.initiative
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, f"strategy:play:{request.player_id}:{request.initiative}"
    )
