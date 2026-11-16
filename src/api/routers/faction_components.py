"""Router komponentów frakcji: liderzy, zdolności frakcji, przełom (RULES.md 61.1, 61.3).

Cienka warstwa nad ``core.faction_components`` i ``core.leaders``: lista z zagrywalnością,
formularz ACTION, zagranie (akcja komponentu tury) i ręczne odblokowanie lidera, którego warunku
silnik jeszcze nie sprawdza.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.actor import ActorId, require_view
from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.core import actor as actor_rules
from src.core import faction_components, leaders
from src.core.game_state import ControlType

router = APIRouter()


class FactionComponentRow(BaseModel):
    kind: str  # leader | ability | breakthrough
    component_id: str
    name: str
    mode: str  # action | passive
    status: str
    implemented: bool
    playable: bool
    reason: str | None = None


class FactionComponentsResponse(BaseModel):
    components: list[FactionComponentRow]


class FactionComponentForm(BaseModel):
    kind: str
    component_id: str
    name: str
    text: str
    mode: str
    implemented: bool
    inputs: list[dict[str, Any]]
    status: str
    leader_type: str | None = None
    unlock_condition: str | None = None
    can_claim_unlock: bool = False


class PlayFactionComponentRequest(BaseModel):
    player_id: str
    kind: str
    component_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    actor_id: str | None = None


class PlayFactionComponentResponse(BaseModel):
    envelope: StateEnvelope
    implemented: bool


class ClaimUnlockRequest(BaseModel):
    player_id: str
    leader_id: str
    actor_id: str | None = None


@router.get("/faction-component/playable", response_model=FactionComponentsResponse)
async def get_playable(
    request: Request, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> FactionComponentsResponse:
    """Liderzy, zdolności i przełom gracza oraz które ACTION można zagrać teraz."""
    require_view(request, player_id)  # RULES.md 44.3
    try:
        rows = faction_components.playability(
            ctx.service.current_state(), ctx.registry, player_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FactionComponentsResponse(components=[FactionComponentRow(**row) for row in rows])


class AvailableNowRow(BaseModel):
    player_id: str
    kind: str
    component_id: str
    name: str
    text: str
    # Okno trwa całą fazę (Carth of Golden Sands) - UI: mały znacznik zamiast karty.
    standing: bool = False


class AvailableNowResponse(BaseModel):
    components: list[AvailableNowRow]


@router.get("/faction-component/available-now", response_model=AvailableNowResponse)
async def get_available_now(
    actor: ActorId, ctx: AppContext = Depends(get_ctx)
) -> AvailableNowResponse:
    """Zdolności „During X: you may…”, których można użyć TERAZ (RULES.md 62.0).

    W grze sieciowej tylko własne (z tokenu); lokalnie - wszystkich graczy-ludzi.
    """
    state = ctx.service.current_state()
    if actor is not None:
        players = [actor]
    else:
        players = [
            pid for pid, player in state.players.items()
            if player.control_type is not ControlType.BOT
        ]
    rows = faction_components.available_now(state, ctx.registry, players)
    return AvailableNowResponse(components=[AvailableNowRow(**row) for row in rows])


@router.get(
    "/faction-component/{kind}/{component_id}/form", response_model=FactionComponentForm
)
async def get_form(
    request: Request,
    kind: str,
    component_id: str,
    player_id: str,
    ctx: AppContext = Depends(get_ctx),
) -> FactionComponentForm:
    """Formularz komponentu frakcji: tekst, stan, czy silnik go automatyzuje i wybory."""
    require_view(request, player_id)  # RULES.md 44.3
    try:
        data = faction_components.form(
            ctx.service.current_state(), ctx.registry, player_id, kind, component_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return FactionComponentForm(**data)


@router.post("/faction-component/play", response_model=PlayFactionComponentResponse)
async def post_play(
    actor: ActorId,
    request: PlayFactionComponentRequest,
    ctx: AppContext = Depends(get_ctx),
) -> PlayFactionComponentResponse:
    """Gracz zagrywa ACTION lidera / zdolności / przełomu — akcja w turze. ``ValueError`` -> 422."""
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state, implemented = faction_components.play(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.kind,
            request.component_id,
            request.params,
            actor_id=request.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Gracz w etykiecie: komponenty z oknem użycia (Quash, Instinct Training) używa też gracz
    # nieaktywny (feed Activity, RULES.md 62.9).
    label = f"component-use:{request.kind}:{request.component_id}:{request.player_id}"
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return PlayFactionComponentResponse(envelope=ctx.service.envelope(), implemented=implemented)


@router.post("/leader/claim-unlock", response_model=StateEnvelope)
async def post_claim_unlock(
    actor: ActorId,
    request: ClaimUnlockRequest,
    ctx: AppContext = Depends(get_ctx),
) -> StateEnvelope:
    """Gracz odblokowuje lidera, którego warunku silnik jeszcze nie sprawdza (RULES.md 61.1)."""
    state = ctx.service.current_state()
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    actor_rules.check(state, request.actor_id, request.player_id, what="Unlock leader")
    try:
        new_state = leaders.claim_unlock(state, ctx.registry, request.player_id, request.leader_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label=f"leader:{request.leader_id}:unlocked")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()
