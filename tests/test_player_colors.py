"""Kolory graczy z assetów AsyncTI4 (core/player_colors + /game/new)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.player_colors import all_color_aliases, canonical_color


def test_all_color_aliases_include_special_colors() -> None:
    aliases = all_color_aliases()
    # Zwykłe, dwukolorowe (split) i gradientowe.
    for expected in ("red", "lgy", "splitred", "rbw", "nea", "blt"):
        assert expected in aliases
    assert len(aliases) == len(set(aliases))


def test_canonical_color_maps_names_to_alias() -> None:
    assert canonical_color("white") == "lgy"
    assert canonical_color("purple") == "ppl"
    assert canonical_color("lgy") == "lgy"
    assert canonical_color("nie-ma-takiego") == "nie-ma-takiego"


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app(store=EventStore(":memory:")))


def test_engine_config_lists_seats(client: TestClient) -> None:
    seats = client.get("/engine/config").json()["seats"]
    assert seats[0] == "301"
    assert len(seats) == 6


def test_new_game_accepts_special_color_and_seat(client: TestClient) -> None:
    response = client.post(
        "/game/new",
        json={
            "players": [
                {"faction_id": "sol", "color": "splitred", "home_position": "307"},
                {"faction_id": "hacan", "color": "white"},
            ]
        },
    )
    assert response.status_code == 200, response.text
    players = client.get("/state").json()["state"]["players"]
    by_faction = {p["faction"]: p for p in players.values()}
    assert by_faction["sol"]["color"] == "splitred"
    assert by_faction["sol"]["home_position"] == "307"
    # "white" jest normalizowane do aliasu kanonicznego.
    assert by_faction["hacan"]["color"] == "lgy"


def test_new_game_rejects_duplicate_color_across_alias_and_name(client: TestClient) -> None:
    response = client.post(
        "/game/new",
        json={
            "players": [
                {"faction_id": "sol", "color": "white"},
                {"faction_id": "hacan", "color": "lgy"},
            ]
        },
    )
    assert response.status_code == 422
