"""Lista opcjonalnych próbek dźwięku walki (``GET /battle/sounds``).

Front pyta o nią raz zamiast próbować każdy plik - brakujące próbki nie sypią 404 w konsoli.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import config
from src.api.app import create_app
from src.core.event_store import EventStore


def _client() -> TestClient:
    return TestClient(create_app(store=EventStore(":memory:")))


def test_lists_only_existing_mp3_samples(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sfx = tmp_path / "extra" / "sfx"
    sfx.mkdir(parents=True)
    (sfx / "laser.mp3").write_bytes(b"x")
    (sfx / "explosion.mp3").write_bytes(b"x")
    (sfx / "notes.txt").write_text("x")
    monkeypatch.setattr(config, "ASSETS_DIR", tmp_path)

    resp = _client().get("/battle/sounds")

    assert resp.status_code == 200
    assert resp.json() == {"sounds": ["explosion", "laser"]}


def test_no_sfx_folder_means_empty_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "ASSETS_DIR", tmp_path)

    assert _client().get("/battle/sounds").json() == {"sounds": []}
