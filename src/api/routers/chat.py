"""Router czatu i szeptów (RULES.md 47.6) — cienka warstwa nad ``core.chat``.

Dziennik leży w metadanych pliku partii (``chat``), nie w ``GameState``: Undo go nie cofa, „Load
game” przełącza go razem z partią. Po nowej wiadomości serwer wysyła jawny sygnał ``{"type":
"chat"}`` (bez treści — treść szeptu każdy pobiera przez ``GET /chat`` ze swojej perspektywy).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.api.actor import ActorId, identity_of, viewer_player
from src.api.context import AppContext, get_ctx
from src.core import actor as actor_rules
from src.core import chat

router = APIRouter()

CHAT_META_KEY = "chat"


class ChatSendRequest(BaseModel):
    """Nowa wiadomość: nadawca, treść i adresat szeptu (``None`` = do wszystkich)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    text: str = Field(max_length=chat.MAX_LENGTH * 2)
    to: str | None = None
    voice: bool = False
    """Komunikat frakcji: gotowa kwestia z pola gracza (publiczna, z bąbelkiem w UI)."""


class ChatMessageView(BaseModel):
    """Wiadomość z perspektywy oglądającego (cudzy szept: ``text = None``)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    seq: int
    sender: str
    to: str | None
    whisper: bool
    text: str | None
    at: float
    voice: bool = False


class ChatResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    messages: list[ChatMessageView] = Field(default_factory=list)


def _log(ctx: AppContext) -> chat.ChatLog:
    return chat.ChatLog.from_json(ctx.service.get_meta(CHAT_META_KEY))


def _response(ctx: AppContext, request: Request, player: str | None) -> ChatResponse:
    identity = identity_of(request)
    viewer = viewer_player(request, player)
    return ChatResponse(
        messages=[
            ChatMessageView(**m)
            for m in chat.visible(
                _log(ctx), viewer, sees_everything=identity.sees_everything and player is None
            )
        ]
    )


@router.get("/chat", response_model=ChatResponse, response_model_by_alias=True)
async def get_chat(
    request: Request, player: str | None = None, ctx: AppContext = Depends(get_ctx)
) -> ChatResponse:
    """Dziennik czatu z perspektywy oglądającego (w sieci zawsze własnej, z tokenu)."""
    return _response(ctx, request, player)


@router.post("/chat/send", response_model=ChatResponse, response_model_by_alias=True)
async def post_chat(
    actor: ActorId,
    body: ChatSendRequest,
    request: Request,
    ctx: AppContext = Depends(get_ctx),
) -> ChatResponse:
    """Gracz pisze do wszystkich albo szepcze do jednego gracza."""
    state = ctx.service.current_state()
    actor_rules.check(state, actor, body.player_id, None, "Chat")
    try:
        log = chat.post(
            _log(ctx), list(state.players), body.player_id, body.text, ctx.service.now(),
            to=body.to, voice=body.voice,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.set_meta(CHAT_META_KEY, log.to_json())
    await ctx.manager.broadcast_json({"type": "chat", "seq": log.last_seq})
    return _response(ctx, request, body.player_id)
