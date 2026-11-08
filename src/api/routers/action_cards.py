"""Router kart akcji: zagranie karty z oknem ACTION jako akcji komponentu (RULES.md 53)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    ActionCardInputsResponse,
    ActionCardPlayability,
    ActionCardPlayabilityResponse,
    PlayActionCardRequest,
    PlayActionCardResponse,
)
from src.core import action_cards
from src.core.components import ComponentCategory

router = APIRouter()


@router.get("/action-card/playable", response_model=ActionCardPlayabilityResponse)
async def get_playable_action_cards(
    player_id: str, ctx: AppContext = Depends(get_ctx)
) -> ActionCardPlayabilityResponse:
    """Które karty z ręki gracza można zagrać teraz (UI pozwala podnieść tylko te)."""
    try:
        rows = action_cards.playability(ctx.service.current_state(), ctx.registry, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ActionCardPlayabilityResponse(cards=[ActionCardPlayability(**row) for row in rows])


@router.get("/action-card/{card_id}/inputs", response_model=ActionCardInputsResponse)
async def get_action_card_inputs(
    card_id: str, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> ActionCardInputsResponse:
    """Formularz zagrania karty: tekst, czy silnik ją automatyzuje i legalne wybory gracza."""
    try:
        implemented, inputs = action_cards.card_inputs(
            ctx.service.current_state(), ctx.registry, player_id, card_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    card = ctx.registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
    assert card is not None  # zagwarantowane przez card_inputs
    return ActionCardInputsResponse(
        card_id=card_id,
        name=card.name or card_id,
        text=" ".join(card.texts.values()),
        implemented=implemented,
        inputs=inputs,
    )


@router.post("/action-card/play", response_model=PlayActionCardResponse)
async def post_play_action_card(
    request: PlayActionCardRequest, ctx: AppContext = Depends(get_ctx)
) -> PlayActionCardResponse:
    """Gracz zagrywa kartę akcji (okno ACTION) - jego akcja w turze; efekt wg silnika.

    Karta bez zaimplementowanego efektu jest zagrana i odrzucona, a odpowiedź ma
    ``implemented=false`` - skutek rozstrzyga operator (God-Mode). ``ValueError`` -> HTTP 422.
    """
    try:
        new_state, implemented = action_cards.play_action_card(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.card_id,
            request.params,
            actor_id=request.actor_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label=f"action-card:{request.card_id}")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return PlayActionCardResponse(envelope=ctx.service.envelope(), implemented=implemented)
