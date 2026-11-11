"""Router zegara szachowego (RULES.md 58): pauza i wznowienie.

Cienkie endpointy: odczyt stanu → ``core.game_clock`` → commit + broadcast. Pauza to
sprawa stołu, nie akcja gry — może ją włączyć każdy gracz, więc bez ``actor_id``.
Błędy domenowe (``ValueError``) → HTTP 422.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.schemas import ChessClockConfig, StateEnvelope
from src.core import actor as actor_rules
from src.core import game_clock

router = APIRouter(prefix="/clock", tags=["clock"])


@router.post("/configure", response_model=StateEnvelope)
async def post_configure(
    actor: ActorId,
    request: ChessClockConfig, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """(Re)startuje zegar w trwającej grze: każdy gracz dostaje pełną pulę od teraz."""
    actor_rules.require_seated(ctx.service.current_state(), actor)  # akcja stołu (44.1a)
    try:
        new_state = game_clock.configure(
            ctx.service.current_state(),
            initial_ms=request.total_minutes * 60_000,
            increment_ms=request.increment_seconds * 1000,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label="clock:configure")
    await ctx.service.broadcast()
    return ctx.service.envelope()


@router.post("/disable", response_model=StateEnvelope)
async def post_disable(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Wyłącza zegar w trwającej grze."""
    actor_rules.require_seated(ctx.service.current_state(), actor)  # akcja stołu (44.1a)
    new_state = game_clock.disable(ctx.service.current_state())
    ctx.service.replace_state(new_state, label="clock:disable")
    await ctx.service.broadcast()
    return ctx.service.envelope()


@router.post("/pause", response_model=StateEnvelope)
async def post_pause(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Zatrzymuje zegar szachowy wszystkich graczy."""
    actor_rules.require_seated(ctx.service.current_state(), actor)  # akcja stołu (44.1a)
    try:
        new_state = game_clock.pause(ctx.service.current_state(), ctx.service.now())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label="clock:pause")
    await ctx.service.broadcast()
    return ctx.service.envelope()


@router.post("/resume", response_model=StateEnvelope)
async def post_resume(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Wznawia zatrzymany zegar szachowy."""
    actor_rules.require_seated(ctx.service.current_state(), actor)  # akcja stołu (44.1a)
    try:
        new_state = game_clock.resume(ctx.service.current_state(), ctx.service.now())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label="clock:resume")
    await ctx.service.broadcast()
    return ctx.service.envelope()
