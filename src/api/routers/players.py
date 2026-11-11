"""Router edycji graczy (God-Mode): nadpisanie pól + synchronizacja kontroli planet."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import HostOnly
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    LeaderStateRequest,
    PlayerComponentToggleRequest,
    PlayerEditRequest,
    SetPlayerHandRequest,
    StateEnvelope,
)
from src.core import board_edit

router = APIRouter()


@router.post("/player/{player_id}/edit", dependencies=[HostOnly], response_model=StateEnvelope)
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


async def _commit(ctx: AppContext, new_state: object, label: str) -> StateEnvelope:
    """Commit stanu + broadcast (ten sam wzorzec co edycja gracza)."""
    ctx.service.replace_state(new_state, label=label)  # type: ignore[arg-type]
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/player/planet/toggle-exhaust", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_toggle_planet_exhaust(
    request: PlayerComponentToggleRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Przełącza wyczerpanie planety gracza (exhausted ↔ ready)."""
    new_state = board_edit.toggle_planet_exhaust(
        ctx.service.current_state(), request.player_id, request.component_id
    )
    return await _commit(ctx, new_state, f"planet-exhaust:{request.component_id}")


@router.post("/player/tech/toggle-exhaust", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_toggle_tech_exhaust(
    request: PlayerComponentToggleRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Przełącza wyczerpanie technologii gracza (exhausted ↔ ready)."""
    new_state = board_edit.toggle_tech_exhaust(
        ctx.service.current_state(), request.player_id, request.component_id
    )
    return await _commit(ctx, new_state, f"tech-exhaust:{request.component_id}")


@router.post("/player/leader/set-state", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_set_leader_state(
    request: LeaderStateRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Ustawia stan lidera gracza (locked/unlocked/exhausted)."""
    try:
        new_state = board_edit.set_leader_state(
            ctx.service.current_state(),
            request.player_id,
            request.leader_id,
            request.state,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"leader:{request.leader_id}:{request.state}")


@router.post("/player/hand/set", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_set_player_hand(
    request: SetPlayerHandRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """God-Mode: ustawia prywatną rękę gracza (karty akcji / sekrety / weksle).

    Podane listy nadpisują daną rękę, pominięte zostają bez zmian. Głównie do
    testów „paska ręki" na mapie. Commit → historia (Undo cofa).
    """
    new_state = board_edit.set_player_hand(
        ctx.service.current_state(),
        request.player_id,
        action_cards=request.action_cards,
        secret_objectives=request.secret_objectives,
        promissory_notes=request.promissory_notes,
    )
    return await _commit(ctx, new_state, f"hand:{request.player_id}")
