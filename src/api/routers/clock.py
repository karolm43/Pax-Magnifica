"""Router zegara szachowego (RULES.md 58): pauza i wznowienie.

Cienkie endpointy: odczyt stanu → ``core.game_clock`` → commit + broadcast. Pauza to
sprawa stołu, nie akcja gry — może ją włączyć każdy gracz, więc bez ``actor_id``.
Błędy domenowe (``ValueError``) → HTTP 422.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.core import game_clock

router = APIRouter(prefix="/clock", tags=["clock"])


@router.post("/pause", response_model=StateEnvelope)
async def post_pause(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Zatrzymuje zegar szachowy wszystkich graczy."""
    try:
        new_state = game_clock.pause(ctx.service.current_state(), ctx.service.now())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label="clock:pause")
    await ctx.service.broadcast()
    return ctx.service.envelope()


@router.post("/resume", response_model=StateEnvelope)
async def post_resume(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Wznawia zatrzymany zegar szachowy."""
    try:
        new_state = game_clock.resume(ctx.service.current_state(), ctx.service.now())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label="clock:resume")
    await ctx.service.broadcast()
    return ctx.service.envelope()
