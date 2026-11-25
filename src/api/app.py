"""Fabryka aplikacji FastAPI Custodian Engine — montaż routerów + WebSocket + static.

Backend jest źródłem prawdy; frontend tylko odzwierciedla rozesłany stan. Logika edycji
planszy i reguł żyje w ``src/core`` (czyste funkcje), warstwa ``api`` jest cienka:
endpointy pogrupowane tematycznie w ``src/api/routers/*`` i montowane tutaj. Współdzielone
zależności przekazujemy przez ``AppContext`` na ``app.state.ctx`` (patrz ``api/context.py``).

Struktura warstw i konwencje: docs/ARCHITEKTURA_KODU.md.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.websockets import WebSocket, WebSocketDisconnect

from src import config
from src.api.actor import ACTOR_HEADER
from src.api.bot_runner import BotRunner
from src.api.connection_manager import ConnectionManager
from src.api.context import MAP_META_KEY, SEATS_META_KEY, AppContext
from src.api.demo_map import build_demo_grid
from src.api.routers import (
    action_cards,
    agenda,
    audio,
    battle,
    board,
    bug_report,
    capacity,
    capture,
    chat,
    clock,
    components,
    decks,
    epilogue,
    exploration,
    faction_components,
    fleet_pool,
    flow,
    frontier_cards,
    game,
    history,
    hold,
    invasion,
    offers,
    planet_ability,
    player_undo,
    players,
    production,
    promissory,
    reaction_pause,
    reaction_settings,
    relics,
    rules,
    setup,
    space_cannon,
    status,
    strategy,
    tactical,
    technology,
    thunders_edge,
    transactions,
    window,
)
from src.api.routers import network as network_routes
from src.api.saves import SaveManager
from src.api.seats import (
    SEAT_TOKEN_HEADER,
    TOKEN_QUERY,
    Identity,
    SeatRegistry,
    current_author,
    current_identity,
)
from src.api.state_service import StateService
from src.core import card_hold, error_text, reaction_prefs
from src.core import reaction_pause as reaction_pause_rules
from src.core.actor import ActorError
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1", "testclient"}


def _is_local(forwarded_for: str | None, client: object) -> bool:
    """Czy żądanie pochodzi z komputera hosta (RULES.md 44.6).

    Przez proxy Vite (``xfwd``) liczy się OSTATNI wpis ``X-Forwarded-For`` — dopisany przez
    proxy adres rzeczywistego klienta (wcześniejsze wpisy klient mógłby podrobić). Bez
    nagłówka: adres połączenia. ``testclient`` = klient testów FastAPI (zawsze lokalny).
    """
    if forwarded_for:
        peer = forwarded_for.split(",")[-1].strip()
    else:
        peer = str(getattr(client, "host", "") or "")
    return peer in _LOOPBACK or peer.startswith("127.")


def _restore_grid(store: EventStore) -> HexGrid | None:
    """Mapa zapisanej partii (``AppContext.set_map``); ``None`` = brak zapisu albo błędny zapis."""
    raw = store.get_meta(MAP_META_KEY)
    if not raw:
        return None
    try:
        grid = HexGrid.from_placements(json.loads(raw))
    except (ValueError, KeyError, TypeError):
        return None
    return grid if grid.positions else None


def create_app(
    *,
    registry: StaticDataRegistry | None = None,
    store: EventStore | None = None,
    initial_state: GameState | None = None,
    now: Callable[[], float] | None = None,
    network: bool = False,
    host_token: str | None = None,
    saves_dir: Path | None = None,
    bug_reports_dir: Path | None = None,
    bots: bool = False,
) -> FastAPI:
    """Fabryka aplikacji FastAPI (wstrzykiwalna dla testów).

    Args:
        registry: Rejestr statycznych danych (domyślnie ładowany z assetów).
        store: Magazyn historii (domyślnie SQLite w pamięci).
        initial_state: Stan początkowy (domyślnie pusty ``GameState``).
        now: Źródło czasu (s UNIX) dla zegara szachowego (domyślnie ``time.time``).
        network: Tryb gry sieciowej (RULES.md 44.2): każde żądanie wymaga tokenu miejsca.
        host_token: Stały token hosta (domyślnie losowy; ``seats.host_token`` po starcie).
        saves_dir: Katalog zapisów (nowa gra = nowy plik, „Load game"); ``None`` = wyłączone.
        bug_reports_dir: Katalog zgłoszeń „Report bug" (na dysku hosta); ``None`` = wyłączone.
        bots: Boty grają same (``api/bot_runner``, RULES.md 65.7); testy sterują botami ręcznie.
    """
    reg = registry if registry is not None else StaticDataRegistry()
    event_store = store if store is not None else EventStore()
    manager = ConnectionManager()
    service = StateService(
        event_store, manager, initial_state=initial_state, now=now or time.time
    )
    # Miejsca przy stole / lobby — wznowione z pliku partii (RULES.md 44.4). Zapis idzie przez
    # serwis, bo bieżący plik partii zmienia się w trakcie (nowa gra, „Load game").
    seats = SeatRegistry(
        network=network,
        host_token=host_token,
        saved=event_store.get_meta(SEATS_META_KEY),
        persist=lambda raw: service.set_meta(SEATS_META_KEY, raw),
    )
    demo_grid = _restore_grid(event_store) or build_demo_grid(reg)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        runner = app.state.bot_runner
        if runner is not None:
            await runner.start()
        try:
            yield
        finally:
            if runner is not None:
                await runner.stop()
            service.close()

    app = FastAPI(title="Custodian Engine API", version="0.1.0", lifespan=lifespan)

    # SĘDZIA (RULES.md 29): każda nielegalna akcja w ``core`` to ``ValueError``. Routery mapują
    # go na 422 lokalnie; ta siatka bezpieczeństwa robi to samo dla endpointów, które pominęły
    # własny ``try`` (np. God-Mode) — gracz dostaje czytelny powód zamiast HTTP 500.
    @app.exception_handler(ValueError)
    async def _value_error_as_422(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    # Autoryzacja aktora (RULES.md 44.1a): ``core/actor.ActorError`` to nie błąd reguł, tylko
    # „nie ty decydujesz" → 403. Jest ``PermissionError``, więc ``except ValueError`` go nie łapią.
    @app.exception_handler(ActorError)
    async def _actor_error_as_403(_request: Request, exc: ActorError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    # Błędy walidacji żądania (Pydantic) to lista obiektów - gracz dostaje jedno czytelne zdanie.
    @app.exception_handler(RequestValidationError)
    async def _validation_error_as_422(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": error_text.flatten_validation_errors(exc.errors())},
        )

    # Czytelne błędy: w każdej odpowiedzi 4xx z tekstowym ``detail`` id graczy (p1, p2) zamieniamy
    # na „Frakcja (kolor)". Jedno miejsce, kontrakt kontrakt ``detail: string`` bez zmian.
    @app.middleware("http")
    async def _humanize_error_detail(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if response.status_code not in (403, 422) or not response.headers.get(
            "content-type", ""
        ).startswith("application/json"):
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])  # type: ignore[attr-defined]
        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        try:
            payload = json.loads(body)
            detail = payload.get("detail") if isinstance(payload, dict) else None
            if isinstance(detail, str):
                ctx = request.app.state.ctx
                payload["detail"] = error_text.humanize(
                    detail, ctx.service.current_state(), ctx.registry
                )
                body = json.dumps(payload).encode()
        except (ValueError, AttributeError):
            pass  # nie-JSON albo brak kontekstu gry - oddajemy oryginał
        return Response(
            content=body, status_code=response.status_code, headers=headers,
            media_type="application/json",
        )

    # Bez tokenu w trybie sieciowym wolno pobrać tylko dane statyczne (assety, reguły, frakcje,
    # komponenty) i ``/network/me`` (front sprawdza, czy to gra sieciowa) — nic ze stanu gry.
    # Lobby otwarte: anonim może zobaczyć lobby i do niego dołączyć (dostaje token członka).
    _lobby_paths = re.compile(r"^/lobby(/join)?$")
    _public_paths = re.compile(
        r"^/(static|components|rules|factions|engine/config|timing-specs|network/me|audio/manifest"
        r"|docs|redoc|openapi\.json)(/|$)"
    )

    # Okno hold-play (RULES.md 53.6): gdy zagrana karta czeka na Sabotage, reszta gry stoi - akcje
    # graczy (POST) poza zagraniem karty / pasem / zwolnieniem, God-Mode i Undo/Redo dają 422.
    # ``faction-component/play``: komponent anulujący kartę (Instinct Training, RULES.md 62.9) -
    # resztę komponentów w trakcie okna odrzuca ``core`` (``faction_components``).
    _held_allowed = re.compile(
        r"(^|/)(action-card|reaction-settings|god-mode|undo|redo|history|game/new|map/load|state|pause"
        r"|resume|faction-component/play)(/|$)"
    )

    @app.middleware("http")
    async def _block_during_held_play(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == "POST" and not _held_allowed.search(request.url.path):
            ctx = request.app.state.ctx
            held = ctx.service.current_state().held_play
            # Stały czas okna minął (RULES.md 54.11): efekt karty wykonuje się przy dowolnym
            # kolejnym POST - gra nie zależy od odliczania w przeglądarce.
            if held is not None and card_hold.expired(held, ctx.service.now()):
                released = card_hold.resolve(ctx.service.current_state(), ctx.registry)
                ctx.service.replace_state(released, label="action-card:held-release")
                held = None
            if held is not None:
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": "A played card is waiting for a possible Sabotage - "
                        "wait until the window closes."
                    },
                )
        return await call_next(request)

    # Pauza ochronna w kluczowych oknach reakcji (RULES.md 54.10): gdy minął jej czas wg zegara
    # serwera, KAŻDY kolejny POST najpierw ją zwalnia - gra nie zależy od zegara klienta. Samo
    # blokowanie kroków robią bramki w ``core`` (``reaction_pause.require_clear``).
    @app.middleware("http")
    async def _expire_reaction_pause(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method == "POST" and not request.url.path.endswith("/reaction-pause/release"):
            service = request.app.state.ctx.service
            pause = service.current_state().reaction_pause
            if pause is not None and reaction_pause_rules.expired(pause, service.now()):
                released = reaction_pause_rules.release(service.current_state(), service.now())
                service.replace_state(released, label="reaction-pause:release")
        return await call_next(request)

    # Tożsamość (RULES.md 44.2): token miejsca → ``request.state.identity`` + ``current_identity``
    # (z niej ``StateService.envelope`` rzutuje stan). Middleware dodany PO hold-play, więc działa
    # PRZED nim (Starlette: ostatni dodany = zewnętrzny). Tryb lokalny: zawsze ``LOCAL``.
    @app.middleware("http")
    async def _seat_identity(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        token = request.headers.get(SEAT_TOKEN_HEADER) or request.query_params.get(TOKEN_QUERY)
        local = _is_local(request.headers.get("x-forwarded-for"), request.client)
        identity = seats.resolve(token, local=local)
        if identity is None:
            path = request.url.path
            lobby_public = seats.network and _lobby_paths.search(path)
            if request.method == "OPTIONS" or _public_paths.search(path) or lobby_public:
                identity = Identity(network=True)  # anonim: tylko dane jawne / dołączenie
            elif seats.network:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Join the game from the lobby first."},
                )
            else:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "This server is not hosting a network game right now."},
                )
        request.state.identity = identity
        reset = current_identity.set(identity)
        # Autor kroku historii (Undo gracza, RULES.md 44.7): jak ``actor.get_actor``.
        if identity.network and not identity.bot:
            author = identity.player_id
        else:
            author = (request.headers.get(ACTOR_HEADER) or "").strip() or None
        # „I'm back” (RULES.md 54.12 e): każda akcja gracza w UI zeruje jego strajki AFK. Zwolnienie
        # okna po czasie to zegar klienta, nie akcja gracza; zapis tylko, gdy coś się zmieniło.
        if (
            request.method == "POST"
            and author
            and not identity.bot
            and not request.url.path.endswith("/reaction-pause/release")
        ):
            current = service.current_state()
            active = reaction_prefs.with_presence(current, author)
            if active is not current:
                service.replace_state(active, label="reaction-settings:presence")
        reset_author = current_author.set(author)
        try:
            return await call_next(request)
        finally:
            current_author.reset(reset_author)
            current_identity.reset(reset)

    # CORS: dev-serwer Vite (5173) łączy się z backendem (8000).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Współdzielony kontekst dla routerów (current_grid podmieniany przy load/new game).
    ctx = AppContext(
        service=service,
        manager=manager,
        registry=reg,
        current_grid=demo_grid,
        seats=seats,
        saves=SaveManager(saves_dir) if saves_dir is not None else None,
        restore_grid=lambda s: _restore_grid(s) or build_demo_grid(reg),
        bug_reports_dir=bug_reports_dir,
    )
    app.state.ctx = ctx
    # Zgodność ze starszymi testami/diagnostyką odwołującymi się do app.state.*.
    app.state.service = service
    app.state.manager = manager
    app.state.registry = reg
    app.state.demo_grid = demo_grid
    app.state.bot_runner = None
    if bots:
        runner = BotRunner(app, ctx, reg.engine_config.bot)
        service.add_listener(runner.notify)
        app.state.bot_runner = runner

    # Routery tematyczne (ARCHITEKTURA_KODU.md §4).
    app.include_router(game.router)
    app.include_router(board.router)
    app.include_router(players.router)
    app.include_router(flow.router)
    app.include_router(setup.router)
    app.include_router(status.router)
    app.include_router(agenda.router)
    app.include_router(epilogue.router)
    app.include_router(clock.router)
    app.include_router(strategy.router)
    app.include_router(history.router)
    app.include_router(tactical.router)
    app.include_router(space_cannon.router)
    app.include_router(battle.router)
    app.include_router(capacity.router)
    app.include_router(capture.router)
    app.include_router(fleet_pool.router)
    app.include_router(invasion.router)
    app.include_router(exploration.router)
    app.include_router(thunders_edge.router)
    app.include_router(decks.router)
    app.include_router(production.router)
    app.include_router(transactions.router)
    app.include_router(chat.router)
    app.include_router(window.router)
    app.include_router(reaction_pause.router)
    app.include_router(reaction_settings.router)
    app.include_router(rules.router)
    app.include_router(components.router)
    app.include_router(action_cards.router)
    app.include_router(relics.router)
    app.include_router(planet_ability.router)
    app.include_router(faction_components.router)
    app.include_router(promissory.router)
    app.include_router(frontier_cards.router)
    app.include_router(hold.router)
    app.include_router(player_undo.router)
    app.include_router(offers.router)
    app.include_router(technology.router)
    app.include_router(network_routes.router)
    app.include_router(bug_report.router)
    app.include_router(audio.router)

    @app.websocket("/ws")
    async def ws_state(websocket: WebSocket) -> None:
        # Gra sieciowa: token w ``?token=`` (przeglądarka nie ustawi nagłówka WebSocketu).
        local = _is_local(websocket.headers.get("x-forwarded-for"), websocket.client)
        identity = seats.resolve(websocket.query_params.get(TOKEN_QUERY), local=local)
        if identity is None:
            await websocket.close(code=4401)
            return
        await manager.connect(websocket, identity)
        try:
            await websocket.send_json(service.envelope(identity).model_dump(mode="json"))
            while True:
                # Klient nie wysyła komend w tym bloku; utrzymujemy połączenie.
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    # Static (assety danych JSON).
    if config.ASSETS_DIR.is_dir():
        app.mount(
            "/static", StaticFiles(directory=str(config.ASSETS_DIR)), name="static"
        )

    return app
