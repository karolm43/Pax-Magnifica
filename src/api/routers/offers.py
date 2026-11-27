"""Router ofert i decyzji graczy (RULES.md 56): lista, przyjęcie z wyborami, odmowa.

Cienka warstwa nad ``core.offers``. Odpowiada zawsze konkretny gracz (``actor_id``, RULES.md 44.1),
a silnik sprawdza, że oferta należy do niego i że wybory mieszczą się w legalnych opcjach.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.actor import ActorId, viewer_player
from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.core import actor as actor_rules
from src.core import offers
from src.core.game_state import GameState

router = APIRouter()


class OfferView(BaseModel):
    """Oferta/decyzja czekająca na gracza (formularz budowany z ``inputs``)."""

    id: str
    player_id: str
    owner_id: str
    name: str
    label: str
    text: str
    # Rodzaj komponentu do nagłówka (np. „Agent”, „Technology”); pusto, gdy nieznany.
    kind: str = ""
    # Komponent źródłowy „<kategoria>:<id>" (np. „technologies:asc") - kafelek w oknie decyzji.
    source: str = ""
    mandatory: bool
    inputs: list[dict[str, Any]]
    # Requested cooperative effect (RULES.md 54.15): requester, owner, payment, accepted.
    deal: dict[str, Any] | None = None


class OffersResponse(BaseModel):
    offers: list[OfferView]


class OfferAcceptRequest(BaseModel):
    actor_id: str
    offer_id: str
    params: dict[str, Any] = Field(default_factory=dict)


class OfferDeclineRequest(BaseModel):
    actor_id: str
    offer_id: str


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.get("/offers", response_model=OffersResponse)
async def get_offers(
    request: Request,
    player_id: str | None = None, ctx: AppContext = Depends(get_ctx)
) -> OffersResponse:
    """Decyzje czekające na gracza (bez ``player_id`` - wszystkie), z legalnymi opcjami."""
    player_id = viewer_player(request, player_id)  # RULES.md 44.3
    state = ctx.service.current_state()
    return OffersResponse(
        offers=[OfferView(**v) for v in offers.offers_view(state, ctx.registry, player_id)]
    )


@router.post("/offers/accept", response_model=StateEnvelope)
async def post_offer_accept(
    actor: ActorId,
    request: OfferAcceptRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz przyjmuje ofertę / podejmuje decyzję z wybranymi opcjami."""
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = offers.accept(
            ctx.service.current_state(), ctx.current_grid, ctx.registry,
            request.actor_id, request.offer_id, request.params,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"offer:accept:{request.offer_id}")


@router.post("/offers/decline", response_model=StateEnvelope)
async def post_offer_decline(
    actor: ActorId,
    request: OfferDeclineRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz odmawia („may”); decyzji obowiązkowej nie można odrzucić."""
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = offers.decline(
            ctx.service.current_state(), ctx.current_grid, ctx.registry,
            request.actor_id, request.offer_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"offer:decline:{request.offer_id}")
