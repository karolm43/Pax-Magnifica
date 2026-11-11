"""Router edycji planszy (God-Mode): jednostki w przestrzeni/na planetach, ruch.

Cienka warstwa HTTP: waliduje wejście, woła czyste funkcje z ``core.board_edit``,
commituje i rozsyła. Logika edycji jest w ``core`` (testowalna bez HTTP, gotowa dla AI).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import HostOnly
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    MapView,
    PlanetUnitsRequest,
    SpaceUnitsRequest,
    UnitEditRequest,
    UnitMoveRequest,
)
from src.api.serializers import build_map_view
from src.core import board_edit

router = APIRouter()


async def _commit_map(ctx: AppContext, new_state, label: str) -> MapView:  # type: ignore[no-untyped-def]
    """Commit stanu + broadcast + zwrot świeżego widoku mapy (wspólny ogon endpointów)."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return build_map_view(ctx.current_grid, ctx.registry, ctx.service.current_state())


@router.post("/system/{position}/space", dependencies=[HostOnly], response_model=MapView)
async def post_space_units(
    position: str, request: SpaceUnitsRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    changes = [(c.player_id, c.base_type, c.count) for c in request.changes]
    try:
        new_state = board_edit.set_space_units(
            ctx.service.current_state(), ctx.current_grid, position, changes
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_map(ctx, new_state, f"space:{position}")


@router.post("/system/{position}/planet/{planet}", dependencies=[HostOnly], response_model=MapView)
async def post_planet_units(
    position: str,
    planet: str,
    request: PlanetUnitsRequest,
    ctx: AppContext = Depends(get_ctx),
) -> MapView:
    changes = [(c.player_id, c.base_type, c.count) for c in request.changes]
    try:
        new_state = board_edit.set_planet_units(
            ctx.service.current_state(),
            ctx.current_grid,
            position,
            planet,
            changes,
            owner_id=request.owner_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_map(ctx, new_state, f"planet:{position}:{planet}")


@router.post("/system/{position}/edit-units", dependencies=[HostOnly], response_model=MapView)
async def post_edit_units(
    position: str, request: UnitEditRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """God-Mode: dodaj/odejmij jednostki w strefie systemu (delta)."""
    try:
        new_state = board_edit.edit_units(
            ctx.service.current_state(),
            ctx.current_grid,
            position,
            request.zone,
            request.faction,
            request.async_id,
            request.delta,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_map(ctx, new_state, f"edit:{position}:{request.zone}")


@router.post("/units/move", dependencies=[HostOnly], response_model=MapView)
async def post_move_units(
    request: UnitMoveRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """God-Mode: przesuń jednostki między strefami/systemami (bez reguł)."""
    try:
        new_state = board_edit.move_units(
            ctx.service.current_state(),
            ctx.current_grid,
            from_position=request.from_position,
            from_zone=request.from_zone,
            to_position=request.to_position,
            to_zone=request.to_zone,
            faction_key=request.faction,
            async_id=request.async_id,
            count=request.count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_map(ctx, new_state, "move-units")
