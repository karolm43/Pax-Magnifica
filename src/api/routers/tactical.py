"""Router akcji taktycznej (Etap E3): aktywacja systemu + maszyna kroków.

Cienka warstwa HTTP: woła czyste funkcje z ``core.tactical`` (przepływ kroków) oraz
``core.board_edit`` (God-Mode żetony dowodzenia), commituje i rozsyła stan + mapę.
Aplikacja PROWADZI kroki akcji taktycznej, ale NIE waliduje reguł TI4 — gracze grają
fizycznie i wprowadzają wynik (decyzja projektowa; patrz docs/RULES.md 19).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    ActivateSystemRequest,
    CommandTokenRequest,
    MapView,
    StateEnvelope,
    TacticalStepRequest,
)
from src.api.serializers import build_map_view
from src.core import board_edit, tactical
from src.core.game_state import GameState, TacticalStep

router = APIRouter()


async def _commit_flow(
    ctx: AppContext, new_state: GameState, label: str
) -> StateEnvelope:
    """Commit wyniku funkcji taktycznej + rozesłanie stanu i mapy."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


async def _commit_map(ctx: AppContext, new_state: GameState, label: str) -> MapView:
    """Commit + rozesłanie, zwraca świeży widok mapy (dla edycji God-Mode CC)."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return build_map_view(ctx.current_grid, ctx.registry, ctx.service.current_state())


@router.post("/tactical/activate", response_model=StateEnvelope)
async def post_activate_system(
    request: ActivateSystemRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Aktywuje system przez aktywnego gracza (kładzie CC, ustawia aktywny system)."""
    try:
        new_state = tactical.activate_system(
            ctx.service.current_state(), ctx.current_grid, request.position
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, f"tactical:activate:{request.position}")


@router.post("/tactical/step/next", response_model=StateEnvelope)
async def post_next_step(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Przechodzi do następnego kroku akcji taktycznej (po produkcji — kończy akcję)."""
    return await _commit_flow(
        ctx, tactical.next_step(ctx.service.current_state()), "tactical:step"
    )


@router.post("/tactical/step/set", response_model=StateEnvelope)
async def post_set_step(
    request: TacticalStepRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Skok do wskazanego kroku akcji taktycznej (np. pominięcie walki)."""
    try:
        step = TacticalStep(request.step)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Nieznany krok: {request.step}") from exc
    return await _commit_flow(
        ctx, tactical.set_step(ctx.service.current_state(), step), "tactical:set-step"
    )


@router.post("/tactical/end", response_model=StateEnvelope)
async def post_end_tactical(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Kończy bieżącą akcję taktyczną (czyści aktywny system i krok)."""
    return await _commit_flow(
        ctx, tactical.end_tactical_action(ctx.service.current_state()), "tactical:end"
    )


@router.post("/system/{position}/command-token", response_model=MapView)
async def post_place_command_token(
    position: str, request: CommandTokenRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """God-Mode: kładzie żeton dowodzenia gracza w przestrzeni systemu."""
    new_state = board_edit.place_command_token(
        ctx.service.current_state(), ctx.current_grid, position, request.faction
    )
    return await _commit_map(ctx, new_state, f"cc:add:{position}")


@router.delete("/system/{position}/command-token", response_model=MapView)
async def delete_command_token(
    position: str, request: CommandTokenRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """God-Mode: zdejmuje żeton dowodzenia gracza z przestrzeni systemu."""
    new_state = board_edit.remove_command_token(
        ctx.service.current_state(), ctx.current_grid, position, request.faction
    )
    return await _commit_map(ctx, new_state, f"cc:remove:{position}")
