"""Undo gracza (RULES.md 44.7): cofnięcie własnego ostatniego kroku (nie tylko host)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.actor import ActorId, require_view
from src.api.context import AppContext, get_ctx
from src.api.schemas import PlayerUndoRequest, PlayerUndoStatus, StateEnvelope
from src.core import actor as actor_rules
from src.core import player_undo

router = APIRouter()


def _chain(ctx: AppContext) -> list[player_undo.Step]:
    return [
        player_undo.Step(seq, label, author, state)
        for seq, label, author, state in ctx.service.recent_steps(player_undo.CHAIN_LIMIT)
    ]


@router.get("/undo/mine", response_model=PlayerUndoStatus)
def get_player_undo(
    request: Request, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> PlayerUndoStatus:
    """Czy gracz może teraz cofnąć swój ostatni krok, a jeśli nie - dlaczego."""
    require_view(request, player_id)  # RULES.md 44.3
    target = player_undo.undo_target(_chain(ctx), player_id)
    return PlayerUndoStatus(
        available=target.seq is not None,
        reason=target.reason,
        label=target.label,
        undone_seq=target.undone_seq,
    )


@router.post("/undo/mine", response_model=StateEnvelope)
async def post_player_undo(
    actor: ActorId, request: PlayerUndoRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Cofa ostatni krok gracza (jeden commit rozgałęziający historię, zegar bez cofania)."""
    player_id = actor_rules.merge_claimed(actor, request.player_id)
    try:
        restored, branch_from, label = player_undo.undo(_chain(ctx), player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    envelope = ctx.service.replace_state(restored, label=label, branch_from=branch_from)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return envelope
