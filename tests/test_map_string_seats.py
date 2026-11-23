"""Map string z gotowymi domami (np. z draftu Milty): kafelki, miejsca i setup gry.

docs/RULES.md 2a: tokeny tłumaczone przez aliasy (``8`` = ``08``, ``96`` = ``96a``),
nieznane kafelki = 422, kafelek domowy na miejscu = domyślna frakcja gracza (Auto),
kolejność przy stole wg miejsc zgodnie z ruchem zegara (docs/RULES.md 24).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.home_slots import seating_by_seats
from src.core.map_string import map_seats, resolve_tile_id, unknown_tiles
from src.core.registry import StaticDataRegistry

# String użytkownika (6 domów na rogach pierścienia 3).
MILTY = (
    "29 33 72 117 46 76 49 115 59 116 35 80 69 25 110 105 36 79 "
    "8 111 45 54 64 60 53 47 100 51 43 24 96 78 67 95 23 102"
)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    return TestClient(create_app(registry=registry, store=EventStore(":memory:")))


def test_resolve_tile_aliases(registry: StaticDataRegistry) -> None:
    assert resolve_tile_id("8", registry) == "08"
    assert resolve_tile_id("08", registry) == "08"
    assert resolve_tile_id("96", registry) == "96a"
    assert resolve_tile_id("nekro", registry) == "08"
    assert resolve_tile_id("999999", registry) is None


def test_user_string_has_no_unknown_tiles(registry: StaticDataRegistry) -> None:
    assert unknown_tiles(MILTY, registry) == []
    assert unknown_tiles("1 999999 0", registry) == ["999999"]


def test_map_seats_detect_home_factions(registry: StaticDataRegistry) -> None:
    seats = [(s.position, s.faction_id) for s in map_seats(MILTY, registry)]
    assert seats == [
        ("301", "nekro"),
        ("304", "cabal"),
        ("307", "nomad"),
        ("310", "ghost"),  # 51 = prawdziwy dom Creuss
        ("313", "firmament"),
        ("316", "deepwrought"),
    ]


def test_seating_by_seats_clockwise_from_player_one() -> None:
    homes = {"p1": "307", "p2": "301", "p3": "313", "p4": "304"}
    assert seating_by_seats(["p1", "p2", "p3", "p4"], homes) == ["p1", "p3", "p2", "p4"]


def test_map_seats_endpoint(client: TestClient) -> None:
    resp = client.get("/map/seats", params={"map_string": MILTY + " 999999"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["seats"][0] == {"position": "301", "faction_id": "nekro"}
    assert body["unknown_tiles"] == ["999999"]


def test_new_game_unknown_tile_is_422(client: TestClient) -> None:
    resp = client.post(
        "/game/new", json={"players": [{"faction_id": "sol"}], "map_string": "1 999999"}
    )
    assert resp.status_code == 422
    assert "999999" in resp.json()["detail"]


def test_new_game_takes_factions_from_home_tiles(client: TestClient) -> None:
    # Gracz 2 siedzi jawnie na 313 (Firmament), gracz 1 bez miejsca → auto 301 (Nekro),
    # gracz 3 wybrał jawnie inną frakcję — jej nie nadpisujemy.
    resp = client.post(
        "/game/new",
        json={
            "map_string": MILTY,
            "players": [
                {},
                {"home_position": "313"},
                {"faction_id": "sol", "home_position": "304"},
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    state = client.get("/state").json()["state"]
    players = state["players"]
    assert players["p1"]["faction"] == "nekro"
    assert players["p2"]["faction"] == "firmament"
    assert players["p3"]["faction"] == "sol"
    # Kolejność przy stole wg miejsc: 301 → 304 → 313.
    assert state["seating_order"] == ["p1", "p3", "p2"]
    # Nieobsadzone domy (Nomad 307, Creuss 310, Deepwrought 316) wracają do pustych slotów.
    systems = {t["position"]: t["system_id"] for t in resp.json()["tiles"]}
    assert systems["307"] == "__home__"
    assert systems["304"] != "54"
