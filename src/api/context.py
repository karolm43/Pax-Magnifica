"""Wspólny kontekst aplikacji dla routerów (współdzielone zależności).

Routery (``api/routers/*``) nie mają dostępu do zmiennych domknięcia fabryki
``create_app``. Zamiast tego trzymamy współdzielone obiekty w jednym ``AppContext``
na ``app.state.ctx``; router pobiera go zależnością ``get_ctx``. ``current_grid`` to
bieżąca mapa (mutowalna — podmieniana przy ``/map/load`` i ``/game/new``), więc jest
własnością kontekstu, nie wartością kopiowaną.

Odczyt ``current_grid`` synchronizuje wormhole z ŻETONÓW położonych w grze (np. Gamma
Wormhole z eksploracji, ``SystemState.wormhole_tokens``) ze stanem — dzięki temu mapa
jest zawsze spójna ze stanem, także po Undo/Redo.
"""

from __future__ import annotations

from fastapi import Request

from src.api.connection_manager import ConnectionManager
from src.api.serializers import build_map_view
from src.api.state_service import StateService
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


class AppContext:
    """Współdzielone zależności warstwy API (jedna instancja na aplikację)."""

    def __init__(
        self,
        service: StateService,
        manager: ConnectionManager,
        registry: StaticDataRegistry,
        current_grid: HexGrid,
    ) -> None:
        self.service = service
        self.manager = manager
        self.registry = registry
        self._grid = current_grid

    @property
    def current_grid(self) -> HexGrid:
        """Bieżąca mapa, zsynchronizowana z żetonami wormhole ze stanu gry."""
        state = self.service.current_state()
        self._grid.sync_token_wormholes(
            {pos: s.wormhole_tokens for pos, s in state.systems.items() if s.wormhole_tokens}
        )
        return self._grid

    @current_grid.setter
    def current_grid(self, grid: HexGrid) -> None:
        self._grid = grid

    async def broadcast_map(self) -> None:
        """Rozsyła świeży widok mapy (z jednostkami) do klientów WebSocket."""
        view = build_map_view(self.current_grid, self.registry, self.service.current_state())
        await self.manager.broadcast_json(
            {"type": "map", **view.model_dump(mode="json")}
        )


def get_ctx(request: Request) -> AppContext:
    """Zależność FastAPI: zwraca ``AppContext`` z ``app.state.ctx``."""
    ctx: AppContext = request.app.state.ctx
    return ctx
