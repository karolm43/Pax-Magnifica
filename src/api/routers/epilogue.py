"""Router epilogu: głosowanie nad zwycięstwem honorowym / niehonorowym.

Cienkie endpointy: odczyt stanu → ``core.epilogue`` → commit + broadcast. Błędy domenowe
(``ValueError``) mapujemy na HTTP 422.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.schemas import EpilogueVoteRequest, StateEnvelope
from src.core import actor as actor_rules
from src.core import epilogue
from src.core.game_state import GameState

router = APIRouter(prefix="/epilogue", tags=["epilogue"])


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    return ctx.service.envelope()


@router.post("/open", response_model=StateEnvelope)
async def post_open(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Otwiera głosowanie (idempotentnie) i oddaje głosy botów."""
    actor_rules.require_seated(ctx.service.current_state(), actor)  # akcja stołu (44.1a)
    try:
        new_state = epilogue.open_vote(ctx.service.current_state())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "epilogue:open")


@router.post("/vote", response_model=StateEnvelope)
async def post_vote(
    actor: ActorId,
    request: EpilogueVoteRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz (nie zwycięzca) głosuje: honorowe albo niehonorowe zwycięstwo."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.player_id, None, "Epilogue vote"
    )
    try:
        new_state = epilogue.cast_vote(
            ctx.service.current_state(), request.player_id, request.choice
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"epilogue:vote:{request.player_id}")
