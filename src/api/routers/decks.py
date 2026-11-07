"""Router stosów kart — narzędzie DEBUG (RULES.md 46.4): przenoszenie kart między stosami.

Cienka warstwa nad ``core.deck_piles``: odczyt stanu → core → commit → broadcast →
mapowanie ``ValueError`` na HTTP 422. Pozwala m.in. ustawić „następną" kartę eksploracji
(``to = "top"``) albo przerzucić kartę do odrzuconych / purge.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.core import deck_piles

router = APIRouter()


class MoveCardRequest(BaseModel):
    """Karta i stos docelowy: ``top`` (wierzch talii), ``deck``, ``discard``, ``purged``."""

    model_config = ConfigDict(populate_by_name=True)

    card_id: str = Field(alias="cardId")
    to: str


@router.post("/decks/move", response_model=StateEnvelope)
async def post_move_card(
    request: MoveCardRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Debug: przenosi kartę między talią / odrzuconymi / purge (omija reguły)."""
    try:
        new_state = deck_piles.move_card(
            ctx.service.current_state(), ctx.registry, request.card_id, request.to
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label=f"decks:move:{request.card_id}:{request.to}")
    await ctx.service.broadcast()
    return ctx.service.envelope()
