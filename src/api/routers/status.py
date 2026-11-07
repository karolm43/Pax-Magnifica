"""Router fazy statusu (RULES.md 41): punktowanie celów, rozdział żetonów dowodzenia.

Cienkie endpointy: odczyt stanu → funkcja ``core.status_phase`` → commit + broadcast.
Błędy domenowe (``ValueError``) mapujemy na HTTP 422. Kroki 2–4, 6–7 wykonują się same
w ``core`` po zakończeniu poprzedniego kroku interaktywnego; krok 8 to ``/phase/next``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    StateEnvelope,
    StatusRedistributeRequest,
    StatusScoreRequest,
    TurnActionRequest,
)
from src.core import status_phase
from src.core.game_state import GameState

router = APIRouter(prefix="/status", tags=["status"])


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/score", response_model=StateEnvelope)
async def post_score(
    request: StatusScoreRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Aktywny gracz zdobywa cel publiczny/tajny (krok 1). Limity i wymagania → 422."""
    try:
        new_state = status_phase.score_objective(
            ctx.service.current_state(),
            ctx.registry,
            ctx.current_grid,
            request.player_id,
            request.kind,
            request.objective_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"status:score:{request.objective_id}")


@router.post("/finish-scoring", response_model=StateEnvelope)
async def post_finish_scoring(
    request: TurnActionRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz kończy krok 1; ostatni uruchamia kroki 2–4 i przechodzi do kroku 5."""
    player_id = request.player_id if request is not None else None
    try:
        new_state = status_phase.finish_scoring(
            ctx.service.current_state(), ctx.registry, player_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "status:finish-scoring")


@router.post("/redistribute", response_model=StateEnvelope)
async def post_redistribute(
    request: StatusRedistributeRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz zatwierdza rozdział żetonów (krok 5); ostatni uruchamia kroki 6–7."""
    try:
        new_state = status_phase.redistribute(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.tactical,
            request.fleet,
            request.strategic,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"status:redistribute:{request.player_id}")
