"""Router historii i nadpisań: God-Mode patch, PUT state, lista historii, undo/redo."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    GodModePatch,
    HistoryEntry,
    HistoryList,
    StateEnvelope,
)
from src.core.game_state import GameState

router = APIRouter()


@router.put("/state", response_model=StateEnvelope)
async def put_state(
    state: GameState, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    envelope = ctx.service.replace_state(state)
    await ctx.service.broadcast()
    return envelope


@router.post("/god-mode/patch", response_model=StateEnvelope)
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


@router.post("/history/goto/{seq}", response_model=StateEnvelope)
async def post_history_goto(
    seq: int, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Przeskok do wskazanej migawki historii (undo/redo do punktu)."""
    envelope = ctx.service.goto(seq)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return envelope


@router.post("/undo", response_model=StateEnvelope)
async def post_undo(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    envelope = ctx.service.undo()
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return envelope


@router.post("/redo", response_model=StateEnvelope)
async def post_redo(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    envelope = ctx.service.redo()
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return envelope
