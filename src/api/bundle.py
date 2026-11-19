"""Paczka do rozesłania: JEDEN serwer podaje API i zbudowany frontend (``frontend/dist``).

W developmencie front serwuje Vite (:5173) i proxuje ``/bot/*`` → backend (:8000) z nagłówkiem
``X-Forwarded-For``. W paczce (``packaging/launcher.py``) nie ma Vite — tę rolę pełni ta warstwa:

- ``/bot/...``  → aplikacja API z obciętym prefiksem (także WebSocket ``/bot/ws``),
- ``/static/...`` → aplikacja API (assety),
- reszta → pliki ``dist``; nieznana ścieżka bez rozszerzenia → ``index.html`` (routing SPA),
- ``lifespan`` → aplikacja API (start/stop botów).

Bezpieczeństwo (RULES.md 44.6): host jest rozpoznawany po adresie połączenia. Bez proxy nagłówek
``X-Forwarded-For`` pochodzi od klienta, więc gość mógłby podać ``127.0.0.1`` i udawać hosta —
warstwa USUWA ten nagłówek z każdego żądania, zanim trafi do API.
"""

from __future__ import annotations

from pathlib import Path

from starlette.responses import FileResponse, PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

API_PREFIX = "/bot"
STATIC_PREFIX = "/static"


def _strip_forwarded(scope: Scope) -> Scope:
    headers = [(k, v) for k, v in scope.get("headers", []) if k.lower() != b"x-forwarded-for"]
    return {**scope, "headers": headers}


class BundleApp:
    """Dyspozytor ASGI: API pod ``/bot`` i ``/static``, frontend ``dist`` pod resztą."""

    def __init__(self, api: ASGIApp, dist_dir: Path) -> None:
        self.api = api
        self.dist_dir = dist_dir.resolve()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.api(scope, receive, send)
            return
        scope = _strip_forwarded(scope)
        path: str = scope.get("path", "/")
        if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
            inner = path[len(API_PREFIX) :] or "/"
            raw: bytes | None = scope.get("raw_path")
            scope = {**scope, "path": inner, "raw_path": raw[len(API_PREFIX) :] if raw else raw}
            await self.api(scope, receive, send)
            return
        if path.startswith(STATIC_PREFIX + "/") or scope["type"] != "http":
            await self.api(scope, receive, send)
            return
        await self._frontend(path)(scope, receive, send)

    def _frontend(self, path: str) -> ASGIApp:
        """Plik z ``dist`` albo ``index.html`` (ścieżki aplikacji, np. ``/game``)."""
        target = (self.dist_dir / path.lstrip("/")).resolve()
        if target.is_relative_to(self.dist_dir) and target.is_file():
            return FileResponse(target)
        if "." in Path(path).name:
            return PlainTextResponse("Not found", status_code=404)
        index = self.dist_dir / "index.html"
        if not index.is_file():
            return PlainTextResponse("Frontend build missing (frontend/dist)", status_code=500)
        # index.html bez cache: po aktualizacji paczki przeglądarka bierze nowe pliki z hashami.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
