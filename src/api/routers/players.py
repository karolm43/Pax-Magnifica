"""Router edycji graczy (God-Mode): nadpisanie pól + synchronizacja kontroli planet."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.context import AppContext, get_ctx
from src.api.schemas import PlayerEditRequest, StateEnvelope
from src.core import board_edit

router = APIRouter()


@router.post("/player/{player_id}/edit", response_model=StateEnvelope)
async def post_edit_player(
    player_id: str, request: PlayerEditRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """God-Mode: edycja pól gracza (VP, zasoby, CC, frakcja, planety…).

    Tworzy gracza, gdy nie istnieje. ``controlled_planets`` synchronizowane do
    ``planet_owners`` systemów (opcja A — jedno źródło prawdy). Commit → historia.
    """
    updates = request.model_dump(exclude_none=True)
    new_state = board_edit.edit_player(
        ctx.service.current_state(),
        ctx.current_grid,
        ctx.registry,
        player_id,
        updates,
    )
    ctx.service.replace_state(new_state, label=f"player:{player_id}")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()
