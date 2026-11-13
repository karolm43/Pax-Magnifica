"""Dźwięk (prezentacja): spis plików audio (``/audio/manifest``) i domy graczy (``/audio/homes``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import config
from src.api.app import create_app
from src.api.routers.audio import build_manifest
from src.core.board_graph import home_positions_by_player
from src.core.event_store import EventStore
from src.core.game_state import GameState, PlayerState, SystemState
from src.core.registry import StaticDataRegistry


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")


def test_manifest_lists_only_audio_files_by_folder(tmp_path: Path) -> None:
    _touch(tmp_path / "voices" / "sol" / "battle1.mp3")
    _touch(tmp_path / "voices" / "sol" / "homedefense.mp3")
    _touch(tmp_path / "voices" / "sol" / "readme.txt")
    _touch(tmp_path / "voices" / "transmissions" / "transmission1.mp3")
    _touch(tmp_path / "voices" / "empty" / "notes.txt")
    _touch(tmp_path / "music" / "loose.ogg")
    _touch(tmp_path / "music" / "bitwa" / "a.mp3")
    _touch(tmp_path / "extra" / "sfx" / "ui" / "click.ogg")
    _touch(tmp_path / "extra" / "sfx" / "ui" / "LICENSE.txt")

    manifest = build_manifest(tmp_path)

    assert manifest == {
        "voices": {"sol": ["battle1.mp3", "homedefense.mp3"]},
        "transmissions": ["transmission1.mp3"],
        "music": {"": ["loose.ogg"], "bitwa": ["a.mp3"]},
        "ui": ["click.ogg"],
    }


def test_manifest_without_folders_is_empty(tmp_path: Path) -> None:
    assert build_manifest(tmp_path) == {"voices": {}, "transmissions": [], "music": {}, "ui": []}


def test_manifest_endpoint_reads_assets_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _touch(tmp_path / "voices" / "hacan" / "joke1.mp3")
    monkeypatch.setattr(config, "ASSETS_DIR", tmp_path)

    client = TestClient(create_app(store=EventStore(":memory:")))
    resp = client.get("/audio/manifest")

    assert resp.status_code == 200
    assert resp.json()["voices"] == {"hacan": ["joke1.mp3"]}


def test_homes_endpoint_answers_for_current_game() -> None:
    client = TestClient(create_app(store=EventStore(":memory:")))
    resp = client.get("/audio/homes")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


def test_home_positions_by_player_splits_homes_per_owner() -> None:
    registry = StaticDataRegistry()
    state = GameState(
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="sol", home_position="103"),
            # Creuss: slot trzyma bramę (17), prawdziwy dom to kafelek 51 poza planszą.
            "p2": PlayerState(player_id="p2", color="blue", faction="ghost", home_position="106"),
        },
        systems={
            "103": SystemState(position="103", system_id="01"),
            "106": SystemState(position="106", system_id="17"),
            "tl": SystemState(position="tl", system_id="51"),
        },
    )

    homes = home_positions_by_player(state, registry)

    assert homes == {"p1": ["103"], "p2": ["tl"]}


def test_network_guest_reads_manifest_before_joining_but_not_homes() -> None:
    """Menu gościa (przed dołączeniem) gra motyw — spis plików jest jawny, domy graczy nie."""
    app = create_app(store=EventStore(":memory:"), network=True, host_token="host-token")
    remote = {"X-Forwarded-For": "10.147.17.5"}
    client = TestClient(app)
    assert client.get("/audio/manifest", headers=remote).status_code == 200
    assert client.get("/audio/homes", headers=remote).status_code == 401
