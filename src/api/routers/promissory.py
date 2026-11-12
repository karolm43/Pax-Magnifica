"""Router promissory notes: zagrywalność z ręki, formularz i zagranie (RULES.md 61.2).

Cienka warstwa nad ``core.promissory_play``. Ręka jest prywatna (RULES.md 44.3): lista i
formularz tylko dla właściciela ręki (host widzi wszystko).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.actor import ActorId, require_view
from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.core import actor as actor_rules
from src.core import promissory_play

router = APIRouter()


class PromissoryRow(BaseModel):
    note_id: str
    template: str
    owner_id: str | None = None
    playable: bool
    reason: str | None = None
    implemented: bool


class PromissoryPlayableResponse(BaseModel):
    notes: list[PromissoryRow]


class PromissoryForm(BaseModel):
    note_id: str
    template: str
    owner_id: str | None = None
    name: str
    text: str
    action: bool
    implemented: bool
    inputs: list[dict[str, Any]]


class PlayPromissoryRequest(BaseModel):
    player_id: str
    note_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    actor_id: str | None = None


class PlayPromissoryResponse(BaseModel):
    envelope: StateEnvelope
    implemented: bool


@router.get("/promissory/playable", response_model=PromissoryPlayableResponse)
async def get_playable(
    request: Request, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> PromissoryPlayableResponse:
    """Notki z ręki gracza i które można zagrać TERAZ (UI pozwala podnieść tylko te)."""
    require_view(request, player_id)  # RULES.md 44.3
    try:
        rows = promissory_play.playability(ctx.service.current_state(), ctx.registry, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PromissoryPlayableResponse(notes=[PromissoryRow(**row) for row in rows])


@router.get("/promissory/{note_id}/form", response_model=PromissoryForm)
async def get_form(
    request: Request, note_id: str, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> PromissoryForm:
    """Formularz notki: tekst z kolorem właściciela, czy silnik ją automatyzuje i wybory."""
    require_view(request, player_id)  # RULES.md 44.3
    try:
        data = promissory_play.form(ctx.service.current_state(), ctx.registry, player_id, note_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PromissoryForm(**data)


@router.post("/promissory/play", response_model=PlayPromissoryResponse)
async def post_play(
    actor: ActorId, request: PlayPromissoryRequest, ctx: AppContext = Depends(get_ctx)
) -> PlayPromissoryResponse:
    """Gracz zagrywa notkę z ręki (reakcja w otwartym oknie albo ACTION). ``ValueError`` -> 422."""
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state, implemented = promissory_play.play(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.note_id,
            request.params,
            actor_id=request.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    label = f"promissory:{request.player_id}:{request.note_id}"
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return PlayPromissoryResponse(envelope=ctx.service.envelope(), implemented=implemented)
