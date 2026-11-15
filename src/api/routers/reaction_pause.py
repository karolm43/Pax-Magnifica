"""Router pauzy ochronnej w kluczowych oknach reakcji (RULES.md 54.10): pas i zwolnienie po czasie.

Cienkie endpointy nad ``core.reaction_pause``. Pauzę otwiera ``StateService`` po każdym kroku gry;
zwolnienie po czasie robi też middleware przy dowolnym kolejnym POST (zegar serwera), więc ten
endpoint jest dla klienta, który odlicza czas na ekranie.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.schemas import HeldActionRequest, StateEnvelope
from src.core import actor as actor_rules
from src.core import reaction_pause
from src.core.game_state import GameState

router = APIRouter()


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/reaction-pause/pass", response_model=StateEnvelope)
async def post_pause_pass(
    actor: ActorId, request: HeldActionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Uprawniony gracz nie reaguje w tym oknie; po ostatnim pasie gra rusza dalej."""
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    player = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = reaction_pause.pass_pause(ctx.service.current_state(), player)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"reaction-pause:pass:{player}")


@router.post("/reaction-pause/release", response_model=StateEnvelope)
async def post_pause_release(
    actor: ActorId, request: HeldActionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Koniec pauzy po czasie (sprawdza zegar serwera; nadmiarowe wywołania są niegroźne).

    Każdy gracz może poprosić o zwolnienie - decyduje zegar serwera, nie tożsamość.
    """
    actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = reaction_pause.release(ctx.service.current_state(), ctx.service.now())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "reaction-pause:release")
