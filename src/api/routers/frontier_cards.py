"""Router kart frontier w ręce gracza (Enigmatic Device): zakładka Action cards, zagranie ACTION.

Kształt odpowiedzi jak w ``relics`` (pole ``relic_id`` niesie id karty frontier), żeby front
używał jednego formularza zagrania.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    PlayRelicRequest,
    PlayRelicResponse,
    RelicInputsResponse,
    RelicPlayability,
    RelicPlayabilityResponse,
)
from src.core import actor as actor_rules
from src.core import frontier_cards

router = APIRouter()


@router.get("/frontier-card/playable", response_model=RelicPlayabilityResponse)
async def get_playable_frontier_cards(
    player_id: str, ctx: AppContext = Depends(get_ctx)
) -> RelicPlayabilityResponse:
    """Karty frontier gracza i które ACTION można zagrać teraz."""
    try:
        rows = frontier_cards.playability(ctx.service.current_state(), ctx.registry, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RelicPlayabilityResponse(relics=[RelicPlayability(**row) for row in rows])


@router.get("/frontier-card/{card_id}/inputs", response_model=RelicInputsResponse)
async def get_frontier_card_inputs(
    card_id: str, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> RelicInputsResponse:
    """Formularz ACTION karty frontier: tekst karty i legalne wybory gracza."""
    try:
        info = frontier_cards.form(ctx.service.current_state(), ctx.registry, player_id, card_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RelicInputsResponse(**info)


@router.post("/frontier-card/play", response_model=PlayRelicResponse)
async def post_play_frontier_card(
    actor: ActorId,
    request: PlayRelicRequest, ctx: AppContext = Depends(get_ctx)
) -> PlayRelicResponse:
    """Gracz zagrywa ACTION karty frontier - jego akcja w turze; ``ValueError`` -> HTTP 422."""
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state, implemented = frontier_cards.play_frontier_card(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.relic_id,
            request.params,
            actor_id=request.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label=f"frontier-card:{request.relic_id}")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return PlayRelicResponse(envelope=ctx.service.envelope(), implemented=implemented)
