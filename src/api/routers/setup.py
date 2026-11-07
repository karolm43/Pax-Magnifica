"""Router setupu startowego gry (RULES.md 45): tajne cele, żeton Custodians, odkrycie celów.

Cienkie endpointy: odczyt stanu → funkcja ``core.game_setup`` → commit + broadcast. Błędy
domenowe (``ValueError``) mapujemy na HTTP 422. Stan setupu czyta front z web-data
(``gameState.setup``), więc tu są tylko akcje.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import SetupActorRequest, SetupSecretRequest, StateEnvelope
from src.core import game_setup
from src.core.game_state import GameState

router = APIRouter(prefix="/setup", tags=["setup"])


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/secret", response_model=StateEnvelope)
async def post_secret(
    request: SetupSecretRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz zatrzymuje jeden z dwóch dobranych tajnych celów (drugi wraca do talii)."""
    try:
        new_state = game_setup.choose_secret(
            ctx.service.current_state(), request.player_id, request.objective_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"setup:secret:{request.player_id}")


@router.post("/custodians", response_model=StateEnvelope)
async def post_custodians(
    request: SetupActorRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Mówca kładzie żeton Custodians na Mecatol Rex."""
    try:
        new_state = game_setup.place_custodians(
            ctx.service.current_state(), request.player_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "setup:custodians")


@router.post("/skip", response_model=StateEnvelope)
async def post_skip(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Pomija setup: losowe tajne cele, żeton Custodians, odkrycie celów publicznych."""
    try:
        new_state = game_setup.skip_setup(ctx.service.current_state())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "setup:skip")


@router.post("/reveal-objectives", response_model=StateEnvelope)
async def post_reveal_objectives(
    request: SetupActorRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Mówca odkrywa dwa cele publiczne I etapu — kończy setup, zaczyna się faza strategii."""
    try:
        new_state = game_setup.reveal_objectives(
            ctx.service.current_state(), request.player_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "setup:reveal-objectives")
