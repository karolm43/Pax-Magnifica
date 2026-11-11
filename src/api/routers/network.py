"""Gra sieciowa (RULES.md 44.2): kim jestem, zaproszenia (tokeny miejsc), miejsce hosta.

Tokeny żyją w ``AppContext.seats`` (pamięć procesu), nigdy w ``GameState``. Linki zaproszeń
buduje front z własnego adresu (``?token=``) — backend nie zna publicznego adresu serwera.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from src.api.actor import HostOnly, identity_of
from src.api.context import AppContext, get_ctx

router = APIRouter(prefix="/network", tags=["network"])


class NetworkMe(BaseModel):
    """Tożsamość klienta: tryb gry i rola."""

    network: bool
    authenticated: bool
    player_id: str | None = None
    host: bool = False


class SeatInvite(BaseModel):
    """Miejsce przy stole z tokenem zaproszenia (widzi tylko host)."""

    player_id: str
    name: str
    faction: str | None = None
    color: str | None = None
    token: str
    is_host_seat: bool = False


class SeatsResponse(BaseModel):
    network: bool
    host_seat: str | None = None
    seats: list[SeatInvite]


class HostSeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str | None = None


@router.get("/me", response_model=NetworkMe)
def get_me(request: Request, ctx: AppContext = Depends(get_ctx)) -> NetworkMe:
    """Kim jest ten klient (publiczne: bez tokenu w sieci → ``authenticated=False``)."""
    identity = identity_of(request)
    if not ctx.seats.network:
        return NetworkMe(network=False, authenticated=True, host=True)
    authenticated = identity.host or identity.player_id is not None
    return NetworkMe(
        network=True,
        authenticated=authenticated,
        player_id=identity.player_id,
        host=identity.host,
    )


def _seats(ctx: AppContext) -> SeatsResponse:
    state = ctx.service.current_state()
    tokens = ctx.seats.seat_tokens(list(state.players)) if ctx.seats.network else {}
    seats = [
        SeatInvite(
            player_id=pid,
            name=p.display_name or p.faction or pid,
            faction=p.faction,
            color=p.color,
            token=tokens.get(pid, ""),
            is_host_seat=pid == ctx.seats.host_seat,
        )
        for pid, p in state.players.items()
    ]
    return SeatsResponse(network=ctx.seats.network, host_seat=ctx.seats.host_seat, seats=seats)


@router.get("/seats", dependencies=[HostOnly], response_model=SeatsResponse)
def get_seats(ctx: AppContext = Depends(get_ctx)) -> SeatsResponse:
    """Zaproszenia: token każdego miejsca (brakujące tworzone przy pierwszym odczycie)."""
    return _seats(ctx)


@router.post("/seats/{player_id}/rotate", dependencies=[HostOnly], response_model=SeatsResponse)
def post_rotate(player_id: str, ctx: AppContext = Depends(get_ctx)) -> SeatsResponse:
    """Nowy token miejsca — stary link przestaje działać (np. trafił do złej osoby)."""
    if player_id not in ctx.service.current_state().players:
        raise HTTPException(status_code=422, detail=f"Unknown player: {player_id}")
    ctx.seats.rotate(player_id)
    return _seats(ctx)


@router.post("/host-seat", dependencies=[HostOnly], response_model=SeatsResponse)
def post_host_seat(request: HostSeatRequest, ctx: AppContext = Depends(get_ctx)) -> SeatsResponse:
    """Host siada jako gracz (widzi wtedy tylko swoje) albo wraca do roli operatora (``None``)."""
    players = ctx.service.current_state().players
    if request.player_id is not None and request.player_id not in players:
        raise HTTPException(status_code=422, detail=f"Unknown player: {request.player_id}")
    ctx.seats.set_host_seat(request.player_id)
    return _seats(ctx)
