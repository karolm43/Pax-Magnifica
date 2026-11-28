"""Cooperative effects ("boosts") and binding deals - RULES.md 54.15.

Thin endpoints over ``core.cooperative``. The requester's list, the owner's terms and "Watch" are
read here (the owner's terms live in private state, so they are not in the web data). Accepting or
declining a deal goes through ``/offers/accept`` / ``/offers/decline`` like any other offer.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from src.api.actor import ActorId, require_view
from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.core import actor as actor_rules
from src.core import cooperative
from src.core.game_state import GameState

router = APIRouter(prefix="/boosts", tags=["boosts"])


class BoostRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str
    boost_id: str
    trade_goods: int = Field(default=0, ge=0, le=cooperative.MAX_PRICE)
    commodities: int = Field(default=0, ge=0, le=cooperative.MAX_PRICE)
    # The requester's debt tokens for the owner - always possible (RULES.md 47.3, 54.15 f).
    debt_tokens: int = Field(default=0, ge=0, le=cooperative.MAX_PRICE)


class BoostWithdrawBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str
    offer_id: str


class BoostSettingBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str
    source: str
    mode: str
    price: int = Field(default=0, ge=0, le=cooperative.MAX_PRICE)
    free_for: list[str] = Field(default_factory=list)


class WatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str
    # ``combat`` / ``turn``; ``None`` = stop watching.
    until: str | None = None


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    return ctx.service.envelope()


@router.get("")
def get_boosts(
    request: Request, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> dict[str, Any]:
    """What the player may request now, their open deals and their own effects' terms."""
    require_view(request, player_id)  # RULES.md 44.3
    state = ctx.service.current_state()
    if player_id not in state.players:
        raise HTTPException(status_code=404, detail=f"Unknown player: {player_id}")
    watch = state.players[player_id].private.reaction_prefs.watch
    return {
        "available": cooperative.available(state, ctx.registry, ctx.current_grid, player_id),
        "outgoing": [
            {"offerId": offer.id, **(cooperative.deal_view(offer) or {}), "name": offer.label}
            for offer, deal in cooperative.deals(state)
            if deal["requester"] == player_id and offer.player_id != player_id
        ],
        "owned": cooperative.owned(state, ctx.registry, player_id),
        "watch": (
            watch.until if watch is not None and cooperative.watching(state, player_id) else None
        ),
    }


@router.post("/request", response_model=StateEnvelope)
async def post_request(
    actor: ActorId, body: BoostRequestBody, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Asks for a boost with an optional payment (an offer to the owner, or to the requester when
    a standing offer accepts it)."""
    state = ctx.service.current_state()
    actor_rules.check(state, actor, body.player_id, None, "Boost request")
    try:
        new_state = cooperative.request(
            state, ctx.registry, ctx.current_grid, body.player_id, body.boost_id,
            trade_goods=body.trade_goods, commodities=body.commodities,
            debt_tokens=body.debt_tokens, now=ctx.service.now(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    paid = body.trade_goods + body.commodities + body.debt_tokens
    return await _commit(ctx, new_state, f"boost:request:{body.player_id}:{body.boost_id}:{paid}")


@router.post("/withdraw", response_model=StateEnvelope)
async def post_withdraw(
    actor: ActorId, body: BoostWithdrawBody, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """The requester withdraws a request (nothing is transferred)."""
    state = ctx.service.current_state()
    actor_rules.check(state, actor, body.player_id, None, "Boost request")
    try:
        new_state = cooperative.decline(state, body.player_id, body.offer_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"boost:withdraw:{body.player_id}")


@router.post("/settings", response_model=StateEnvelope)
async def post_settings(
    actor: ActorId, body: BoostSettingBody, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """The owner sets Ask me / Standing offer / Self-only for a cooperative effect (private)."""
    state = ctx.service.current_state()
    actor_rules.check(state, actor, body.player_id, None, "Reaction settings")
    try:
        new_state = cooperative.configure(
            state, body.player_id, body.source,
            mode=body.mode, price=body.price, free_for=body.free_for,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "reaction-settings:boosts")


@router.post("/watch", response_model=StateEnvelope)
async def post_watch(
    actor: ActorId, body: WatchBody, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """"Watch / Hold": be offered cooperative effects unprompted until this combat / turn ends."""
    state = ctx.service.current_state()
    actor_rules.check(state, actor, body.player_id, None, "Reaction settings")
    try:
        new_state = cooperative.set_watch(state, body.player_id, body.until)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "reaction-settings:watch")
