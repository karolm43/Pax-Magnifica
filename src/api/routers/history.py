"""Router historii i nadpisań: God-Mode patch, PUT state, lista historii, undo/redo."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from src.api.actor import HostOnly
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    ActivityEntry,
    ActivityFeed,
    ActivityPlayer,
    GodModePatch,
    HistoryEntry,
    HistoryList,
    StateEnvelope,
)
from src.core.game_state import ControlType, GameState

router = APIRouter()


@router.put("/state", dependencies=[HostOnly], response_model=StateEnvelope)
async def put_state(
    state: GameState, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    envelope = ctx.service.replace_state(state)
    await ctx.service.broadcast()
    return envelope


@router.post("/god-mode/patch", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_patch(
    patch: GodModePatch, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    try:
        envelope = ctx.service.apply_patch(patch)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    await ctx.service.broadcast()
    return envelope


@router.get("/history", response_model=HistoryList)
def get_history(ctx: AppContext = Depends(get_ctx)) -> HistoryList:
    """Lista migawek historii (etykieta + która bieżąca) dla panelu historii."""
    return HistoryList(
        entries=[
            HistoryEntry(seq=seq, label=label, is_current=is_current)
            for seq, label, is_current in ctx.service.history_entries()
        ]
    )


@router.get("/history/activity", response_model=ActivityFeed)
def get_activity(ctx: AppContext = Depends(get_ctx)) -> ActivityFeed:
    """Feed „kto co zrobił" — wpisy z opisem akcji + dane graczy do wyświetlenia."""
    state = ctx.service.current_state()
    return ActivityFeed(
        current_seq=ctx.service.current_seq(),
        entries=[
            ActivityEntry(
                seq=seq, is_current=is_current, created_at=created_at, activity=entry
            )
            for seq, _label, is_current, created_at, entry in ctx.service.activity_feed()
            if entry is not None
        ],
        players={
            pid: ActivityPlayer(
                faction=player.faction,
                color=player.color,
                display_name=player.display_name,
                is_bot=player.control_type is ControlType.BOT,
            )
            for pid, player in state.players.items()
        },
    )


@router.post("/history/goto/{seq}", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_history_goto(
    seq: int, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Przeskok do wskazanej migawki historii (undo/redo do punktu)."""
    envelope = ctx.service.goto(seq)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return envelope


@router.post("/undo", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_undo(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    envelope = ctx.service.undo()
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return envelope


@router.post("/redo", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_redo(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    envelope = ctx.service.redo()
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return envelope
