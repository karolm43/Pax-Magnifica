"""Router transakcji między graczami + żetonów długu (RULES.md 47).

Cienka warstwa HTTP: walidacja i zmiana stanu siedzą w ``core.transaction`` oraz
``core.debt``; tu tylko wywołanie, commit + broadcast i mapowanie ``ValueError`` → 422.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    DebtTokensRequest,
    StateEnvelope,
    TransactionRequest,
    TransactionSideRequest,
)
from src.core import debt, transaction
from src.core.game_state import GameState

router = APIRouter()


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    """Commit stanu + rozesłanie (ten sam wzorzec co pozostałe routery)."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


def _side(req: TransactionSideRequest) -> transaction.TransactionSide:
    return transaction.TransactionSide(
        trade_goods=req.trade_goods,
        commodities=req.commodities,
        promissory_note=req.promissory_note,
        relic_fragments=tuple(req.relic_fragments),
    )


@router.post("/transactions/resolve", response_model=StateEnvelope)
async def post_resolve_transaction(
    request: TransactionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Rozstrzyga transakcję aktywnego gracza z sąsiadem (RULES.md 47). Błąd reguły → 422."""
    try:
        new_state = transaction.resolve_transaction(
            ctx.service.current_state(),
            ctx.current_grid,
            request.partner_id,
            _side(request.give),
            _side(request.receive),
            request.player_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"transaction:{request.partner_id}")


@router.post("/debt/give", response_model=StateEnvelope)
async def post_give_debt_tokens(
    request: DebtTokensRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Wystawca oddaje posiadaczowi żetony długu (zasada stołu, RULES.md 47.3)."""
    try:
        new_state = debt.give_debt_tokens(
            ctx.service.current_state(), request.issuer_id, request.holder_id, request.count
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, f"debt:give:{request.issuer_id}->{request.holder_id}"
    )


@router.post("/debt/return", response_model=StateEnvelope)
async def post_return_debt_tokens(
    request: DebtTokensRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Posiadacz zwraca wystawcy jego żetony długu (debt) (dług spłacony/odpuszczony)."""
    try:
        new_state = debt.return_debt_tokens(
            ctx.service.current_state(), request.holder_id, request.issuer_id, request.count
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, f"debt:return:{request.holder_id}->{request.issuer_id}"
    )
