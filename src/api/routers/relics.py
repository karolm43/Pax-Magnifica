"""Router reliktów: zakładka Relics na ręce i zagranie „ACTION:” reliktu (RULES.md 59)."""

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
from src.api.schemas_relic_forge import (
    ForgeOption,
    ForgeOptionsResponse,
    ForgeRelicRequest,
    ForgeRelicResponse,
)
from src.core import actor as actor_rules
from src.core import relic_actions, relic_cards, relic_forge

router = APIRouter()


@router.get("/relic/playable", response_model=RelicPlayabilityResponse)
async def get_playable_relics(
    player_id: str, ctx: AppContext = Depends(get_ctx)
) -> RelicPlayabilityResponse:
    """Relikty gracza i które ACTION można zagrać teraz (UI pozwala podnieść tylko te)."""
    try:
        rows = relic_cards.playability(ctx.service.current_state(), ctx.registry, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RelicPlayabilityResponse(relics=[RelicPlayability(**row) for row in rows])


@router.get("/relic/{relic_id}/inputs", response_model=RelicInputsResponse)
async def get_relic_inputs(
    relic_id: str, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> RelicInputsResponse:
    """Formularz ACTION reliktu: tekst, rodzaj, czy silnik go automatyzuje i legalne wybory."""
    try:
        info = relic_actions.form(ctx.service.current_state(), ctx.registry, player_id, relic_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RelicInputsResponse(**info)


@router.post("/relic/play", response_model=PlayRelicResponse)
async def post_play_relic(
    actor: ActorId,
    request: PlayRelicRequest, ctx: AppContext = Depends(get_ctx)
) -> PlayRelicResponse:
    """Gracz zagrywa ACTION swojego reliktu - jego akcja w turze; efekt wg silnika.

    Relikt bez zakodowanego efektu jest zagrany jako akcja, a odpowiedź ma ``implemented=false`` -
    skutek rozstrzyga operator (God-Mode). ``ValueError`` -> HTTP 422.
    """
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state, implemented = relic_cards.play_relic(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.relic_id,
            request.params,
            actor_id=request.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label=f"relic:{request.relic_id}")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return PlayRelicResponse(envelope=ctx.service.envelope(), implemented=implemented)


@router.get("/relic/forge/options", response_model=ForgeOptionsResponse)
async def get_forge_options(
    player_id: str, ctx: AppContext = Depends(get_ctx)
) -> ForgeOptionsResponse:
    """Typy fragmentów gracza i czy da się TERAZ połączyć 3 w relikt (RULES.md 59.7)."""
    try:
        rows = relic_forge.options(ctx.service.current_state(), ctx.registry, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ForgeOptionsResponse(options=[ForgeOption(**row) for row in rows])


@router.post("/relic/forge", response_model=ForgeRelicResponse)
async def post_forge_relic(
    actor: ActorId,
    request: ForgeRelicRequest, ctx: AppContext = Depends(get_ctx)
) -> ForgeRelicResponse:
    """Gracz purge'uje fragmenty i dobiera relikt - jego akcja w turze. ``ValueError`` -> 422."""
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = relic_forge.forge(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.fragments,
            actor_id=request.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    reveal = new_state.relic_reveal or {}
    ctx.service.replace_state(new_state, label=f"relic:forge:{reveal.get('kind', '')}")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ForgeRelicResponse(envelope=ctx.service.envelope(), relic_id=reveal.get("relicId"))
