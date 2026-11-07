"""Router limitu pojemności (RULES.md 39.6): stan okna CAPACITY i usunięcie nadwyżki.

Cienka warstwa nad ``core.capacity``: odczyt stanu → core → commit → broadcast → ``ValueError``
na HTTP 422. Modal „Capacity exceeded" w UI czyta ``GET /tactical/capacity``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.api.context import AppContext, get_ctx
from src.api.schemas import BattleLossItem, StateEnvelope
from src.api.web_data import entity_key_map
from src.core import board_edit, capacity
from src.core.game_state import WindowType
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

router = APIRouter()


class CapacityCargoView(BaseModel):
    """Jednostka ładunku w przestrzeni: typ, liczba, zajmowana pojemność, uszkodzone."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    count: int
    cost: int  # capacityUsed na sztukę


class CapacityView(BaseModel):
    """Okno CAPACITY: kto usuwa, ile pojemności jest/zajęte, ładunek i podpowiedź „Auto"."""

    model_config = ConfigDict(populate_by_name=True)

    active: bool
    position: str | None = None
    player: str | None = None  # klucz encji (kolor/frakcja) bieżącego respondenta
    player_id: str | None = Field(default=None, serialization_alias="playerId")
    general: int = 0
    fighter_only: int = Field(default=0, serialization_alias="fighterOnly")
    used: int = 0
    excess: int = 0
    cargo: list[CapacityCargoView] = Field(default_factory=list)
    suggestion: dict[str, int] = Field(default_factory=dict)
    remaining: int = 0  # ilu graczy jeszcze czeka w kolejce (łącznie z bieżącym)


class CapacityResolveRequest(BaseModel):
    """Usunięcie wybranych jednostek z przestrzeni (myśliwce / piechota / mechy)."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    remove: list[BattleLossItem] = Field(default_factory=list)


@router.get("/tactical/capacity", response_model=CapacityView, response_model_by_alias=True)
async def get_capacity(ctx: AppContext = Depends(get_ctx)) -> CapacityView:
    """Stan okna limitu pojemności (pusty, gdy okno nie trwa)."""
    state = ctx.service.current_state()
    window = state.pending_window
    if (
        window is None
        or window.window_type is not WindowType.CAPACITY
        or window.current_responder is None
    ):
        return CapacityView(active=False)
    pid = window.current_responder
    position = str(window.context.get("position", ""))
    report = capacity.capacity_report(state, ctx.registry, position, pid)
    return CapacityView(
        active=True,
        position=position,
        player=entity_key_map(state).get(pid, pid),
        player_id=pid,
        general=report.general,
        fighter_only=report.fighter_only,
        used=report.used,
        excess=report.excess,
        cargo=[
            CapacityCargoView(
                base_type=bt,
                async_id=ASYNC_ID_BY_BASE_TYPE.get(bt, bt),
                name=report.names.get(bt, bt),
                count=report.cargo[bt],
                cost=report.cost.get(bt, 1),
            )
            for bt in capacity.CARGO_TYPES
            if report.cargo.get(bt, 0) > 0
        ],
        suggestion=capacity.auto_removal(report),
        remaining=len(window.queue) - window.cursor,
    )


@router.post("/tactical/capacity/resolve", response_model=StateEnvelope)
async def post_capacity_resolve(
    request: CapacityResolveRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz usuwa nadwyżkę ponad pojemność (dokładnie tyle, ile trzeba — RULES.md 39.6 C2)."""
    state = ctx.service.current_state()
    remove: dict[str, int] = {}
    for item in request.remove:
        if item.count > 0:
            remove[item.base_type] = remove.get(item.base_type, 0) + item.count
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = capacity.resolve_capacity(state, ctx.registry, player_id, remove)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label=f"capacity:{player_id}")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()
