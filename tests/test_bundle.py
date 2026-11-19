"""Paczka (``src/api/bundle.py``): API pod ``/bot``, frontend ``dist``, bez podróbki hosta."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket
from fastapi.testclient import TestClient

from src.api.bundle import BundleApp


def _api(events: list[str]) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        events.append("start")
        yield
        events.append("stop")

    api = FastAPI(lifespan=lifespan)

    @api.get("/api/echo")
    def echo(request: Request) -> dict[str, str | None]:
        return {"path": request.url.path, "xff": request.headers.get("x-forwarded-for")}

    @api.get("/static/a.txt")
    def static() -> str:
        return "asset"

    @api.websocket("/ws")
    async def ws(socket: WebSocket) -> None:
        await socket.accept()
        await socket.send_text("hello")
        await socket.close()

    return api


def _client(tmp_path: Path, events: list[str] | None = None) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (dist / "assets" / "main.js").write_text("js", encoding="utf-8")
    return TestClient(BundleApp(_api(events if events is not None else []), dist))


def test_api_under_bot_prefix_is_stripped(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        assert client.get("/bot/api/echo").json()["path"] == "/api/echo"


def test_forwarded_for_header_is_dropped(tmp_path: Path) -> None:
    """Gość nie może udawać hosta nagłówkiem ``X-Forwarded-For: 127.0.0.1`` (RULES.md 44.6)."""
    with _client(tmp_path) as client:
        res = client.get("/bot/api/echo", headers={"X-Forwarded-For": "127.0.0.1"})
        assert res.json()["xff"] is None


def test_static_goes_to_api(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        assert client.get("/static/a.txt").json() == "asset"


def test_frontend_files_and_spa_fallback(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        assert client.get("/assets/main.js").text == "js"
        assert "app" in client.get("/").text
        assert "app" in client.get("/game").text
        assert client.get("/missing.js").status_code == 404


def test_path_traversal_never_leaves_dist(tmp_path: Path) -> None:
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    with _client(tmp_path) as client:
        for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
            assert "secret" not in client.get(path).text


def test_websocket_and_lifespan_reach_api(tmp_path: Path) -> None:
    events: list[str] = []
    with _client(tmp_path, events) as client:
        assert events == ["start"]
        with client.websocket_connect("/bot/ws") as socket:
            assert socket.receive_text() == "hello"
    assert events == ["start", "stop"]
