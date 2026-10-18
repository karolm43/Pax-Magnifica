"""Testy serializacji ``web-data`` (kontrakt dla frontendu ti4_web).

Weryfikują, że endpoint ``GET /api/public/game/{id}/web-data`` zwraca dokument
``PlayerDataResponse`` o kształcie, którego oczekuje frontend: pozycje jako
``"<pozycja>:<systemId>"``, jednostki kluczowane ``asyncId`` per frakcja oraz
dane graczy z zasobami i VP. Treść pochodzi z realnego stanu (map string + setup),
nie z pamięci.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.registry import StaticDataRegistry

# Prawdziwy map string AsyncTI4 (6 graczy, pierścień 3): rogi domowe jako "0".
SAMPLE_MAP_STRING = (
    "72 66 77 65 69 50 61 44 64 76 60 73 46 42 71 79 70 59 "
    "48 45 68 51 67 47 49 62 43 58 63 78 41 40"
)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"))
    return TestClient(app)


def test_web_data_has_required_top_level_keys(client: TestClient) -> None:
    client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    data = client.get("/api/public/game/g/web-data").json()
    for key in (
        "gameName",
        "gameRound",
        "ringCount",
        "vpsToWin",
        "tilePositions",
        "tileUnitData",
        "playerData",
        "objectives",
        "cardPool",
        "expeditions",
    ):
        assert key in data, f"brak pola {key}"
    assert data["gameName"] == "g"
    assert data["ringCount"] >= 3
    # Wersja schematu musi spełniać próg frontendu, inaczej render blokuje
    # ekran "Update Needed" (REQUIRED_VERSION_SCHEMA w GameMapPage.tsx).
    assert data["versionSchema"] >= 5


def test_web_data_tile_positions_format(client: TestClient) -> None:
    client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    data = client.get("/api/public/game/g/web-data").json()
    # Centrum zawsze obecne jako "000:18" (Mecatol).
    assert "000:18" in data["tilePositions"]
    # Każdy wpis to "<pozycja>:<systemId>" i ma odpowiadający klucz w tileUnitData.
    for entry in data["tilePositions"]:
        position, system_id = entry.split(":")
        assert position and system_id
        assert position in data["tileUnitData"]
    # Sloty domowe (brak kafelka) nie trafiają do tilePositions.
    assert not any(entry.endswith(":__home__") for entry in data["tilePositions"])


def test_web_data_units_use_async_ids(client: TestClient) -> None:
    client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    client.post(
        "/setup/player",
        json={
            "player_id": "p1",
            "faction_id": "sol",
            "color": "red",
            "home_position": "301",
        },
    )
    data = client.get("/api/public/game/g/web-data").json()

    tile = data["tileUnitData"]["301"]
    # Statki w przestrzeni frakcji Sol — kluczowane asyncId, entityType "unit".
    space = tile["space"]["sol"]
    async_ids = {e["entityId"] for e in space}
    assert async_ids <= {"cv", "dd", "ff", "ca", "dn", "fs", "ws"}
    assert all(e["entityType"] == "unit" and e["count"] > 0 for e in space)

    # Planeta domowa Jord: jednostki naziemne/struktury (gf/sd), kontrolowana przez Sol.
    jord = tile["planets"]["jord"]
    assert jord["controlledBy"] == "sol"
    ground_ids = {e["entityId"] for e in jord["entities"]["sol"]}
    assert "gf" in ground_ids  # piechota


def test_web_data_player_data_carries_counters(client: TestClient) -> None:
    client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    client.post(
        "/setup/player",
        json={
            "player_id": "p1",
            "faction_id": "sol",
            "color": "red",
            "home_position": "301",
        },
    )
    data = client.get("/api/public/game/g/web-data").json()
    assert len(data["playerData"]) == 1
    player = data["playerData"][0]
    assert player["faction"] == "sol"
    assert player["color"] == "red"
    assert "totalVps" in player
    assert "tg" in player
