"""Nowa gra z ``random_map`` buduje losową mapę 6-osobową (zamiast domyślnej)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import create_app


def test_random_map_new_game_ok() -> None:
    client = TestClient(create_app())
    players = [{"control_type": "HUMAN"}, {"control_type": "HUMAN"}]
    res = client.post("/game/new", json={"players": players, "random_map": True})
    assert res.status_code == 200
    ids = [t["system_id"] for t in res.json()["tiles"]]
    assert "18" in ids and len(ids) > 20
