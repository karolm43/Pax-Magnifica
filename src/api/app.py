"""Fabryka aplikacji FastAPI Custodian Engine — montaż routerów + WebSocket + static.

Backend jest źródłem prawdy; frontend tylko odzwierciedla rozesłany stan. Logika edycji
planszy i reguł żyje w ``src/core`` (czyste funkcje), warstwa ``api`` jest cienka:
endpointy pogrupowane tematycznie w ``src/api/routers/*`` i montowane tutaj. Współdzielone
zależności przekazujemy przez ``AppContext`` na ``app.state.ctx`` (patrz ``api/context.py``).

Struktura warstw i konwencje: docs/ARCHITEKTURA_KODU.md.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from src import config
from src.api.connection_manager import ConnectionManager
from src.api.context import AppContext
from src.api.demo_map import build_demo_grid
from src.api.routers import (
    battle,
    board,
    capacity,
    components,
    flow,
    game,
    history,
    invasion,
    players,
    production,
    rules,
    space_cannon,
    strategy,
    tactical,
    window,
)
from src.api.state_service import StateService
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry


def create_app(
    *,
    registry: StaticDataRegistry | None = None,
    store: EventStore | None = None,
    initial_state: GameState | None = None,
) -> FastAPI:
    """Fabryka aplikacji FastAPI (wstrzykiwalna dla testów).

    Args:
        registry: Rejestr statycznych danych (domyślnie ładowany z assetów).
        store: Magazyn historii (domyślnie SQLite w pamięci).
        initial_state: Stan początkowy (domyślnie pusty ``GameState``).
    """
    reg = registry if registry is not None else StaticDataRegistry()
    event_store = store if store is not None else EventStore()
    manager = ConnectionManager()
    service = StateService(event_store, manager, initial_state=initial_state)
    demo_grid = build_demo_grid(reg)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        event_store.close()

    app = FastAPI(title="Custodian Engine API", version="0.1.0", lifespan=lifespan)

    # CORS: dev-serwer Vite (5173) łączy się z backendem (8000).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Współdzielony kontekst dla routerów (current_grid podmieniany przy load/new game).
    ctx = AppContext(
        service=service, manager=manager, registry=reg, current_grid=demo_grid
    )
    app.state.ctx = ctx
    # Zgodność ze starszymi testami/diagnostyką odwołującymi się do app.state.*.
    app.state.service = service
    app.state.manager = manager
    app.state.registry = reg
    app.state.demo_grid = demo_grid

    # Routery tematyczne (ARCHITEKTURA_KODU.md §4).
    app.include_router(game.router)
    app.include_router(board.router)
    app.include_router(players.router)
    app.include_router(flow.router)
    app.include_router(strategy.router)
    app.include_router(history.router)
    app.include_router(tactical.router)
    app.include_router(space_cannon.router)
    app.include_router(battle.router)
    app.include_router(capacity.router)
    app.include_router(invasion.router)
    app.include_router(production.router)
    app.include_router(window.router)
    app.include_router(rules.router)
    app.include_router(components.router)

    @app.websocket("/ws")
    async def ws_state(websocket: WebSocket) -> None:
        await manager.connect(websocket)
        try:
            await websocket.send_json(service.envelope().model_dump(mode="json"))
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
