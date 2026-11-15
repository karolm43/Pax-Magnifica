"""Router okien czasowych (Etap E8-T2): odpowiedź respondenta, zamknięcie okna.

Cienki endpoint nad ``core.timing`` (wzorzec: odczyt stanu → core → commit →
broadcast → mapowanie błędów domenowych na HTTP). Otwieranie okien dla konkretnych
mechanik (secondary kart strategii, walka) robią ich własne routery od T3 —
tutaj jest endpoint ``/window/open`` jako NARZĘDZIE (ręczne/testowe otwarcie okna,
np. do weryfikacji panelu UI i testów integracyjnych), oraz uniwersalne
``/window/respond`` i ``/window/close``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId, HostOnly
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    OpenTimingWindow,
    OpenTimingWindowsResponse,
    StateEnvelope,
    WindowOpenRequest,
    WindowRespondRequest,
)
from src.core import actor as actor_rules
from src.core import timing, timing_view
from src.core.game_state import GameState, WindowType

router = APIRouter()


@router.get("/window/open-now", response_model=OpenTimingWindowsResponse)
async def get_open_windows(ctx: AppContext = Depends(get_ctx)) -> OpenTimingWindowsResponse:
    """Okna czasowe otwarte TERAZ — jawne dla wszystkich, bez informacji o rękach (43.4)."""
    rows = timing_view.describe_open_windows(ctx.service.current_state(), ctx.registry)
    return OpenTimingWindowsResponse(windows=[OpenTimingWindow(**row) for row in rows])


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    """Commit wyniku funkcji okna + rozesłanie stanu i mapy."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/window/open", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_window_open(
    request: WindowOpenRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Otwiera okno czasowe (narzędzie: ręczne/testowe otwarcie z gotową kolejką).

    Kolejkę można podać jawnie (``queue``) albo wyliczyć z inicjatora
    (``initiator_id`` → ``build_response_queue``, od gracza po inicjatorze zgodnie
    z zegarem). Mechaniki docelowe (secondary, walka) otwierają okna z własnych
    routerów od T3; ten endpoint zostaje jako wentyl operatora i punkt testowy.
    """
    try:
        window_type = WindowType(request.window_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"Unknown window type: {request.window_type}"
        ) from exc

    state = ctx.service.current_state()
    if request.queue is not None:
        queue = request.queue
    else:
        queue = timing.build_response_queue(
            state,
            request.initiator_id,
            include_initiator=request.include_initiator,
        )
    try:
        new_state = timing.open_window(
            state, window_type, queue, context=request.context or None
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"window:open:{window_type.value}")


@router.post("/window/respond", response_model=StateEnvelope)
async def post_window_respond(
    actor: ActorId,
    request: WindowRespondRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Rejestruje odpowiedź bieżącego respondenta i przesuwa kolejkę okna.

    W T2 to czysta mechanika kolejki (``timing.respond_current``) — efekty decyzji
    (secondary zużywa żeton, assign-hits usuwa jednostki) dojdą od T3. Odpowiedź
    poza kolejnością / brak okna → 422.
    """
    actor_rules.check(
        ctx.service.current_state(), actor, request.player_id, None, "Respond in window"
    )
    try:
        new_state = timing.respond_current(
            ctx.service.current_state(), request.player_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    decision = request.decision or "ok"
    return await _commit(
        ctx, new_state, f"window:respond:{request.player_id}:{decision}"
    )


@router.post("/window/close", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_window_close(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Zamyka bieżące okno czasowe (wentyl operatora / po zastosowaniu efektów)."""
    return await _commit(
        ctx, timing.close_window(ctx.service.current_state()), "window:close"
    )
