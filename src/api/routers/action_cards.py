"""Router kart akcji: zagranie karty z oknem ACTION jako akcji komponentu (RULES.md 53)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import PlayActionCardRequest, PlayActionCardResponse
from src.core import action_cards

router = APIRouter()


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
