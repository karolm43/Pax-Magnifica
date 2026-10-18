"""Menadżer połączeń WebSocket — rozsyłanie stanu do podłączonych klientów.

Utrzymuje zbiór aktywnych połączeń i udostępnia asynchroniczny broadcast. Błędy
wysyłki do pojedynczego klienta nie przerywają rozsyłania do pozostałych — zrywa
się tylko wadliwe połączenie.
"""

from __future__ import annotations

from starlette.websockets import WebSocket


class ConnectionManager:
    """Rejestr aktywnych połączeń WebSocket z obsługą broadcastu."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Akceptuje połączenie i dodaje je do rejestru."""
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Usuwa połączenie z rejestru (bez zamykania)."""
        self._connections.discard(websocket)

    async def broadcast_json(self, payload: object) -> None:
        """Rozsyła ładunek JSON do wszystkich aktywnych połączeń.

        Połączenia, do których wysyłka się nie powiedzie, są usuwane z rejestru.
        """
        stale: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(payload)
            except Exception:  # noqa: BLE001 — zrywamy tylko wadliwe połączenie
                stale.append(connection)
        for connection in stale:
            self._connections.discard(connection)

    @property
    def connection_count(self) -> int:
        """Liczba aktywnych połączeń."""
        return len(self._connections)
