"""Zapis partii w pliku i wznowienie po restarcie (RULES.md 44.4, etap N3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import __main__ as server
from src.api.app import create_app
from src.api.seats import SEAT_TOKEN_HEADER
from src.core.event_store import EventStore
from src.core.registry import StaticDataRegistry

HOST = "host-token-for-tests"
MAP = "19 20 21 22 23 24"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _app(
    registry: StaticDataRegistry, path: Path, *, network: bool = True
) -> tuple[TestClient, EventStore]:
    store = EventStore(path)
    app = create_app(
        registry=registry, store=store, network=network, host_token=HOST if network else None
    )
    return TestClient(app), store


def _positions(client: TestClient, headers: dict[str, str]) -> list[str]:
    return sorted(t["position"] for t in client.get("/map", headers=headers).json()["tiles"])


def test_meta_roundtrip(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "g.db")
    assert store.get_meta("x") is None
    store.set_meta("x", "1")
    store.set_meta("x", "2")
    store.close()
    assert EventStore(tmp_path / "g.db").get_meta("x") == "2"


def test_restart_resumes_state_map_and_invites(
    registry: StaticDataRegistry, tmp_path: Path
) -> None:
    path = tmp_path / "game.db"
    first, store = _app(registry, path)
    host = {SEAT_TOKEN_HEADER: HOST}
    players = [{"faction_id": "sol"}, {"faction_id": "arborec"}]
    res = first.post("/game/new", json={"players": players}, headers={SEAT_TOKEN_HEADER: HOST})
    assert res.status_code == 200, res.text
    tokens = {
        s["player_id"]: s["token"]
        for s in first.get("/network/seats", headers={SEAT_TOKEN_HEADER: HOST}).json()["seats"]
    }
    before_state = first.get("/state", headers={SEAT_TOKEN_HEADER: HOST}).json()["state"]
    before_map = _positions(first, host)
    store.close()  # symulacja zamknięcia procesu

    second, _ = _app(registry, path)  # „restart": nowy proces, ten sam plik
    assert second.get("/state", headers={SEAT_TOKEN_HEADER: HOST}).json()["state"] == before_state
    assert _positions(second, host) == before_map
    for token in tokens.values():  # linki zaproszeń działają dalej
        assert second.get("/network/me", headers={SEAT_TOKEN_HEADER: token}).json()["authenticated"]
    assert second.post("/undo", headers={SEAT_TOKEN_HEADER: HOST}).status_code == 200


def test_loaded_map_is_remembered(registry: StaticDataRegistry, tmp_path: Path) -> None:
    path = tmp_path / "map.db"
    first, store = _app(registry, path, network=False)
    assert first.post("/map/load", json={"map_string": MAP}).status_code == 200
    positions = _positions(first, {})
    store.close()
    second, _ = _app(registry, path, network=False)
    assert _positions(second, {}) == positions


def test_fresh_and_broken_saves_are_set_aside(tmp_path: Path) -> None:
    path = tmp_path / "game.db"
    EventStore(path).close()
    server._open_store(path, fresh=True).close()  # noqa: SLF001
    assert any(p.name.startswith("game.old-") for p in tmp_path.iterdir())
    path.write_bytes(b"not a database")
    store = server._open_store(path, fresh=False)  # noqa: SLF001
    assert store.current() is None
    store.close()
    assert any(p.name.startswith("game.broken-") for p in tmp_path.iterdir())
