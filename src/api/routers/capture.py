"""Router for captured units (RULES.md 61.5): player-initiated returns.

Thin layer over ``core.capture``. R_capture notes/5: a player who captured their own units may
return them to their reinforcements at any time.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.core import actor as actor_rules
from src.core import board_edit, capture

router = APIRouter()


class ReturnOwnRequest(BaseModel):
    """Own captured units going back to reinforcements."""

    model_config = ConfigDict(populate_by_name=True)

    faction: str
    base_type: str = Field(alias="baseType")
    count: int = Field(default=1, ge=1)


@router.post("/capture/return-own", response_model=StateEnvelope)
async def post_return_own(
    actor: ActorId, request: ReturnOwnRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Returns the player's own captured units to their reinforcements (R_capture notes/5)."""
    state = ctx.service.current_state()
    actor_rules.check(state, actor, request.faction, None, "Return captured units")
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = capture.return_own(state, player_id, request.base_type, request.count)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    label = capture.unit_label(state, player_id, request.base_type, request.count)
    ctx.service.replace_state(new_state, label=f"captured:return-own:{player_id}:{label}")
    await ctx.service.broadcast()
    return ctx.service.envelope()
