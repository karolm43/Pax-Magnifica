"""Menadżer połączeń WebSocket — rozsyłanie stanu do podłączonych klientów.

Każde połączenie pamięta swoją tożsamość (``seats.Identity``), bo w grze sieciowej dostaje
WŁASNĄ projekcję stanu (RULES.md 44.3): ``broadcast_each`` buduje ładunek raz na klucz widoku
(gracz / operator), nigdy jeden pełny stan dla wszystkich. ``broadcast_json`` wolno używać
wyłącznie dla danych w pełni jawnych (np. mapa). Błędy wysyłki do pojedynczego klienta nie
przerywają rozsyłania — zrywa się tylko wadliwe połączenie.
"""

from __future__ import annotations

from collections.abc import Callable

from starlette.websockets import WebSocket

from src.api.seats import LOCAL, Identity


class ConnectionManager:
    """Rejestr aktywnych połączeń WebSocket z obsługą broadcastu."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, Identity] = {}

    async def connect(self, websocket: WebSocket, identity: Identity = LOCAL) -> None:
        """Akceptuje połączenie i dodaje je do rejestru z tożsamością klienta."""
        await websocket.accept()
        self._connections[websocket] = identity

    def disconnect(self, websocket: WebSocket) -> None:
        """Usuwa połączenie z rejestru (bez zamykania)."""
        self._connections.pop(websocket, None)

    async def _send(self, payloads: dict[WebSocket, object]) -> None:
        stale: list[WebSocket] = []
        for connection, payload in payloads.items():
            try:
                await connection.send_json(payload)
            except Exception:  # noqa: BLE001 — zrywamy tylko wadliwe połączenie
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)

    async def broadcast_json(self, payload: object) -> None:
        """Rozsyła TEN SAM ładunek wszystkim — tylko dane w pełni jawne (RULES.md 44.3)."""
        await self._send({c: payload for c in list(self._connections)})

    async def broadcast_each(self, build: Callable[[Identity], object]) -> None:
        """Rozsyła ładunek zbudowany osobno dla każdego klucza widoku (projekcja per gracz)."""
        cache: dict[str, object] = {}
        payloads: dict[WebSocket, object] = {}
        for connection, identity in list(self._connections.items()):
            key = identity.view_key
            if key not in cache:
                cache[key] = build(identity)
            payloads[connection] = cache[key]
        await self._send(payloads)

    @property
    def connection_count(self) -> int:
        """Liczba aktywnych połączeń."""
        return len(self._connections)
