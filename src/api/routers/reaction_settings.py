"""Router ustawień okien reakcji (RULES.md 54.11-54.12): długość i „Quick windows” (host),
„Skip all reactions”, deklaracje pasu i wyciszenia (gracz, prywatne).

Cienkie endpointy nad ``core.reaction_window``. Oba działają także w trakcie okna Sabotage
(middleware hold-play przepuszcza ``/reaction-settings/*``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId, HostOnly
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    AutoPassRequest,
    QuickWindowsRequest,
    ReactionJitterRequest,
    ReactionPrefsRequest,
    ReactionWindowRequest,
    StateEnvelope,
)
from src.core import actor as actor_rules
from src.core import reaction_prefs, reaction_window
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
    """Host ustawia stałą długość okien reakcji w trwającej grze (2–60 s)."""
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
        new_state = reaction_window.settle_quick(new_state, ctx.registry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Etykieta bez nazwy gracza i bez stanu: ustawienie jest prywatne (feed go nie pokazuje).
    return await _commit(ctx, new_state, "reaction-settings:auto-pass")


@router.post("/quick", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_quick(
    request: QuickWindowsRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Host włącza/wyłącza „Quick windows”: okno kończy się, gdy wszyscy spasowali (54.12)."""
    new_state = reaction_window.configure_quick(ctx.service.current_state(), request.enabled)
    new_state = reaction_window.settle_quick(new_state, ctx.registry)
    return await _commit(ctx, new_state, f"reaction-settings:quick:{int(request.enabled)}")


@router.post("/jitter", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_jitter(
    request: ReactionJitterRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Host ustawia „bluff jitter”: przy „Quick windows” okno bez reakcji zamyka się po 1-2 s."""
    try:
        new_state = reaction_window.configure_jitter(ctx.service.current_state(), request.seconds)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    new_state = reaction_window.settle_quick(new_state, ctx.registry)
    return await _commit(ctx, new_state, "reaction-settings:jitter")


@router.post("/prefs", response_model=StateEnvelope)
async def post_prefs(
    actor: ActorId, request: ReactionPrefsRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz zmienia deklaracje pasu / „only when involved” / wyciszenia (prywatne, 54.12)."""
    player = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = reaction_prefs.update(
            ctx.service.current_state(),
            player,
            declare=request.declare,
            only_involved=request.only_involved,
            mute_cards=request.mute_cards,
            mute_offers=request.mute_offers,
            mute_components=request.mute_components,
            unless_changes=request.unless_changes,
            auto_hits=request.auto_hits,
            clear_notices=request.clear_notices,
        )
        reaction_window.pass_open_windows(new_state, player, ctx.registry)
        new_state = reaction_window.settle_quick(new_state, ctx.registry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Etykieta bez nazwy gracza i bez treści: ustawienie jest prywatne (feed go nie pokazuje).
    return await _commit(ctx, new_state, "reaction-settings:prefs")

