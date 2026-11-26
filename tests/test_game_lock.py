"""Testy N4 — per-game lock w warstwie API (serializacja mutujących żądań HTTP)."""

from __future__ import annotations

import asyncio

import httpx

from src.api.app import create_app


def test_game_lock_serializes_mutating_requests() -> None:
    """Dwa równoległe POST-y nie nakładają się — drugi czeka na zwolnienie ``game_lock``."""

    async def _run() -> None:
        app = create_app(bots=False)
        ctx = app.state.ctx
        events: list[str] = []

        @app.post("/test/slow-post")
        async def _slow_post() -> dict[str, bool]:
            events.append("enter")
            await asyncio.sleep(0.05)
            events.append("exit")
            return {"ok": True}

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r1, r2 = await asyncio.gather(
                client.post("/test/slow-post"),
                client.post("/test/slow-post"),
            )

        assert r1.status_code == 200
        assert r2.status_code == 200
        # Gdyby nie lock, oba „enter” pojawiłyby się przed pierwszym „exit”.
        assert events == ["enter", "exit", "enter", "exit"]
        assert not ctx.game_lock.locked()

    asyncio.run(_run())


def test_game_lock_does_not_block_get_requests() -> None:
    """Żądania GET nie czekają na ``game_lock`` trzymany przez mutację."""

    async def _run() -> None:
        app = create_app(bots=False)
        ctx = app.state.ctx

        transport = httpx.ASGITransport(app=app)
        async with (
            ctx.game_lock,
            httpx.AsyncClient(transport=transport, base_url="http://test") as client,
        ):
            resp = await asyncio.wait_for(client.get("/state"), timeout=1.0)

        assert resp.status_code == 200

    asyncio.run(_run())
