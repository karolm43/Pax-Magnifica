"""Wspólny kontekst aplikacji dla routerów (współdzielone zależności).

Routery (``api/routers/*``) nie mają dostępu do zmiennych domknięcia fabryki
``create_app``. Zamiast tego trzymamy współdzielone obiekty w jednym ``AppContext``
na ``app.state.ctx``; router pobiera go zależnością ``get_ctx``. ``current_grid`` to
bieżąca mapa (mutowalna — podmieniana przy ``/map/load`` i ``/game/new``), więc jest
polem kontekstu, nie wartością kopiowaną.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from src.api.connection_manager import ConnectionManager
from src.api.serializers import build_map_view
from src.api.state_service import StateService
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@dataclass
class AppContext:
    """Współdzielone zależności warstwy API (jedna instancja na aplikację)."""

    service: StateService
    manager: ConnectionManager
    registry: StaticDataRegistry
    current_grid: HexGrid

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
