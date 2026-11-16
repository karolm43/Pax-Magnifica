"""Router ustawień okien reakcji (RULES.md 54.11): długość okna (host) i „Skip all reactions”.

Cienkie endpointy nad ``core.reaction_window``. Oba działają także w trakcie okna Sabotage
(middleware hold-play przepuszcza ``/reaction-settings/*``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId, HostOnly
from src.api.context import AppContext, get_ctx
from src.api.schemas import AutoPassRequest, ReactionWindowRequest, StateEnvelope
from src.core import actor as actor_rules
from src.core import reaction_window
from src.core.game_state import GameState

router = APIRouter(prefix="/reaction-settings", tags=["reactions"])


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    return ctx.service.envelope()


@router.post("/window", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_window(
    request: ReactionWindowRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Host ustawia stałą długość okien reakcji w trwającej grze (2–30 s)."""
    try:
        new_state = reaction_window.configure(ctx.service.current_state(), request.seconds)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"reaction-settings:window:{request.seconds}")


@router.post("/auto-pass", response_model=StateEnvelope)
async def post_auto_pass(
    actor: ActorId, request: AutoPassRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz włącza/wyłącza „Skip all reactions” (ustawienie prywatne)."""
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    player = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = reaction_window.set_auto_pass(
            ctx.service.current_state(), player, request.enabled
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Etykieta bez nazwy gracza i bez stanu: ustawienie jest prywatne (feed go nie pokazuje).
    return await _commit(ctx, new_state, "reaction-settings:auto-pass")
