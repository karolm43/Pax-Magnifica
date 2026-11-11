"""Gra sieciowa: kim jestem, lobby, zaproszenia, zapisy partii (RULES.md 44.2, 44.4, 44.6).

- Host (komputer z serwerem) otwiera lobby (``/lobby/open``) — od tej chwili inni mogą wejść
  na adres hosta (np. ZeroTier) i dołączyć imieniem (``/lobby/join`` → token członka).
- Przy starcie gry host przypisuje członków do miejsc (``/lobby/assign``).
- Zapisy: lista plików (``/saves``) i wczytanie (``/saves/load``) — tylko host.

Tokeny żyją w ``AppContext.seats`` i w metadanych pliku partii, nigdy w ``GameState``.
"""

from __future__ import annotations

import socket
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from src.api.actor import HostOnly, LobbyParty, PublicJoin, identity_of
from src.api.context import AppContext, get_ctx
from src.api.lobby_draft import DraftPermissionError
from src.core.actor import ActorError

router = APIRouter(tags=["network"])


# --- Kim jestem ---------------------------------------------------------------------------


class NetworkMe(BaseModel):
    """Tożsamość klienta: tryb gry i rola."""

    network: bool
    authenticated: bool
    player_id: str | None = None
    host: bool = False
    member_id: str | None = None
    name: str | None = None


@router.get("/network/me", response_model=NetworkMe)
def get_me(request: Request, ctx: AppContext = Depends(get_ctx)) -> NetworkMe:
    """Kim jest ten klient (publiczne: anonim w sieci → ``authenticated=False``)."""
    identity = identity_of(request)
    if not identity.network:
        return NetworkMe(network=False, authenticated=True, host=True)
    member = next(
        (m for m in ctx.seats.members() if m.member_id == identity.member_id), None
    )
    authenticated = identity.host or identity.player_id is not None or member is not None
    return NetworkMe(
        network=ctx.seats.network,
        authenticated=authenticated,
        player_id=identity.player_id,
        host=identity.host,
        member_id=identity.member_id,
        name=member.name if member else None,
    )


# --- Lobby --------------------------------------------------------------------------------


class LobbyMember(BaseModel):
    member_id: str
    name: str
    player_id: str | None = None


class LobbyView(BaseModel):
    """Stan lobby: czy otwarte, kto dołączył, czy gra już ma graczy (adresy — tylko host)."""

    open: bool
    members: list[LobbyMember]
    game_started: bool
    addresses: list[str] = Field(default_factory=list)
    save_name: str | None = None
    draft: dict[str, Any] | None = None
    """Wspólny szkic kreatora (``lobby_draft``) — sloty, właściciele, mapa, krok."""
    you: str | None = None
    """Kim jest pytający w szkicu: ``"host"`` albo ``member_id`` (gość)."""


def _local_addresses() -> list[str]:
    """Adresy IPv4 tego komputera (LAN, ZeroTier, Tailscale…) do linku „dołącz"."""
    found: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(str(info[4][0]))
    except OSError:
        pass
    return sorted(a for a in found if not a.startswith("127."))


def _lobby(request: Request, ctx: AppContext) -> LobbyView:
    identity = identity_of(request)
    seats = ctx.seats
    return LobbyView(
        open=seats.network,
        members=[
            LobbyMember(
                member_id=m.member_id, name=m.name, player_id=seats.member_seat(m.member_id)
            )
            for m in seats.members()
        ],
        game_started=bool(ctx.service.current_state().players),
        addresses=_local_addresses() if identity.host or not identity.network else [],
        save_name=ctx.save_name,
        draft=seats.draft_view(),
        you="host" if identity.host or not identity.network else identity.member_id,
    )


@router.get("/lobby", response_model=LobbyView)
def get_lobby(request: Request, ctx: AppContext = Depends(get_ctx)) -> LobbyView:
    """Lobby (publiczne, gdy otwarte: dołączający widzi, kto już jest)."""
    return _lobby(request, ctx)


class OpenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reset: bool = False
    """``True`` = nowe lobby („Play"): bez starych gości, miejsc i szkicu."""


@router.post("/lobby/open", dependencies=[HostOnly], response_model=LobbyView)
async def post_lobby_open(
    request: Request, body: OpenRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> LobbyView:
    """Host otwiera grę sieciową: inni mogą dołączyć z adresu tego komputera."""
    if body is not None and body.reset:
        ctx.seats.reset_lobby()
    ctx.seats.set_network(True)
    return _lobby(request, ctx)


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft: dict[str, Any]


@router.put("/lobby/draft", dependencies=[HostOnly], response_model=LobbyView)
async def put_lobby_draft(
    body: DraftRequest, request: Request, ctx: AppContext = Depends(get_ctx)
) -> LobbyView:
    """Host wysyła pełny szkic kreatora (start lobby, zmiana liczby graczy)."""
    try:
        ctx.seats.set_draft(body.draft)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _lobby(request, ctx)


@router.patch("/lobby/draft", dependencies=[LobbyParty], response_model=LobbyView)
async def patch_lobby_draft(
    patch: dict[str, Any], request: Request, ctx: AppContext = Depends(get_ctx)
) -> LobbyView:
    """Zmiana szkicu na żywo: host — wszystko, gość — swoja frakcja, kolor, miejsce."""
    try:
        ctx.seats.patch_draft(identity_of(request), patch)
    except DraftPermissionError as exc:
        raise ActorError(str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _lobby(request, ctx)


@router.post("/lobby/seat", dependencies=[HostOnly], response_model=LobbyView)
async def post_lobby_seat(request: Request, ctx: AppContext = Depends(get_ctx)) -> LobbyView:
    """Po utworzeniu gry: właściciele slotów szkicu siadają na swoich miejscach (``p{i+1}``)."""
    ctx.seats.bind_from_draft()
    await ctx.service.broadcast()
    return _lobby(request, ctx)


@router.post("/lobby/close", dependencies=[HostOnly], response_model=LobbyView)
async def post_lobby_close(request: Request, ctx: AppContext = Depends(get_ctx)) -> LobbyView:
    """Host zamyka grę sieciową: znów tylko ten komputer (dołączeni zachowują tokeny)."""
    ctx.seats.set_network(False)
    return _lobby(request, ctx)


class JoinRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


class JoinResponse(BaseModel):
    member_id: str
    name: str
    token: str


@router.post("/lobby/join", dependencies=[PublicJoin], response_model=JoinResponse)
async def post_lobby_join(request: JoinRequest, ctx: AppContext = Depends(get_ctx)) -> JoinResponse:
    """Dołączenie do lobby imieniem → token członka (front zapamiętuje go w karcie)."""
    try:
        member = ctx.seats.join(request.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JoinResponse(member_id=member.member_id, name=member.name, token=member.token)


@router.post("/lobby/kick/{member_id}", dependencies=[HostOnly], response_model=LobbyView)
async def post_lobby_kick(
    member_id: str, request: Request, ctx: AppContext = Depends(get_ctx)
) -> LobbyView:
    """Usuwa gracza z lobby (jego link/token przestaje działać)."""
    ctx.seats.kick(member_id)
    return _lobby(request, ctx)


class AssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignments: dict[str, str]
    """``{player_id: member_id | "host"}`` — kto siedzi na którym miejscu nowej gry."""


@router.post("/lobby/assign", dependencies=[HostOnly], response_model=LobbyView)
async def post_lobby_assign(
    body: AssignRequest, request: Request, ctx: AppContext = Depends(get_ctx)
) -> LobbyView:
    """Start gry z lobby: przypisuje członków do miejsc (każdy gra pod swoim tokenem)."""
    players = ctx.service.current_state().players
    unknown = [pid for pid in body.assignments if pid not in players]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown players: {', '.join(unknown)}")
    try:
        ctx.seats.bind(body.assignments)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await ctx.service.broadcast()
    return _lobby(request, ctx)


# --- Zaproszenia (linki miejsc) -----------------------------------------------------------


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
    host_home: str | None = None
    """Miejsce hosta z lobby — powrót z trybu testowego „gram za wszystkich"."""
    seats: list[SeatInvite]


class HostSeatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: str | None = None


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
    return SeatsResponse(
        network=ctx.seats.network,
        host_seat=ctx.seats.host_seat,
        host_home=ctx.seats.host_home,
        seats=seats,
    )


@router.get("/network/seats", dependencies=[HostOnly], response_model=SeatsResponse)
def get_seats(ctx: AppContext = Depends(get_ctx)) -> SeatsResponse:
    """Zaproszenia: token każdego miejsca (brakujące tworzone przy pierwszym odczycie)."""
    return _seats(ctx)


@router.post(
    "/network/seats/{player_id}/rotate", dependencies=[HostOnly], response_model=SeatsResponse
)
def post_rotate(player_id: str, ctx: AppContext = Depends(get_ctx)) -> SeatsResponse:
    """Nowy token miejsca — stary link przestaje działać (np. trafił do złej osoby)."""
    if player_id not in ctx.service.current_state().players:
        raise HTTPException(status_code=422, detail=f"Unknown player: {player_id}")
    ctx.seats.rotate(player_id)
    return _seats(ctx)


@router.post("/network/host-seat", dependencies=[HostOnly], response_model=SeatsResponse)
def post_host_seat(request: HostSeatRequest, ctx: AppContext = Depends(get_ctx)) -> SeatsResponse:
    """Host siada jako gracz (widzi wtedy tylko swoje) albo wraca do roli operatora (``None``)."""
    players = ctx.service.current_state().players
    if request.player_id is not None and request.player_id not in players:
        raise HTTPException(status_code=422, detail=f"Unknown player: {request.player_id}")
    ctx.seats.set_host_seat(request.player_id)
    return _seats(ctx)


# --- Zapisy partii ------------------------------------------------------------------------


class SaveEntry(BaseModel):
    name: str
    modified: float
    round_number: int | None = None
    phase: str | None = None
    players: list[str] = Field(default_factory=list)
    broken: bool = False
    current: bool = False


class SavesResponse(BaseModel):
    enabled: bool
    saves: list[SaveEntry]


class LoadSaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


@router.get("/saves", dependencies=[HostOnly], response_model=SavesResponse)
def get_saves(ctx: AppContext = Depends(get_ctx)) -> SavesResponse:
    """Zapisane partie (od najnowszej) do menu „Load game"."""
    if ctx.saves is None:
        return SavesResponse(enabled=False, saves=[])
    return SavesResponse(
        enabled=True,
        saves=[
            SaveEntry(**vars(info), current=info.name == ctx.save_name)
            for info in ctx.saves.list()
        ],
    )


@router.post("/saves/load", dependencies=[HostOnly], response_model=SavesResponse)
async def post_load_save(
    body: LoadSaveRequest, ctx: AppContext = Depends(get_ctx)
) -> SavesResponse:
    """Wczytuje partię z pliku: stan, historia Undo, mapa i miejsca graczy (ich linki działają)."""
    try:
        ctx.load_save(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return get_saves(ctx)
