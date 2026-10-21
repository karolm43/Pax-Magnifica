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
    # Zasoby/wpływy muszą być z rejestru także dla planety ZAJĘTEJ (nie zera).
    assert jord["resources"] > 0
    assert jord["influence"] > 0


def test_web_data_player_economy_sums_controlled_planets(
    client: TestClient,
) -> None:
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}]},
    )
    data = client.get("/api/public/game/g/web-data").json()
    sol = next(p for p in data["playerData"] if p["faction"] == "sol")
    # Panel gracza pokazuje ekonomię z kontrolowanych planet (nie zera).
    assert sol["resources"] > 0
    assert sol["influence"] > 0
    assert sol["planets"]
    # Jord (4 res / 2 inf): optimal = zasoby (res > inf), reguła AsyncTI4.
    assert sol["optimalResources"] == 4
    assert sol["optimalInfluence"] == 0


def test_web_data_player_leaders(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    data = client.get("/api/public/game/g/web-data").json()
    sol = next(p for p in data["playerData"] if p["faction"] == "sol")
    leaders = sol["leaders"]
    types = {ldr["type"] for ldr in leaders}
    assert types == {"agent", "commander", "hero"}
    # Agent gotowy na starcie; commander/hero zablokowani.
    agent = next(ldr for ldr in leaders if ldr["type"] == "agent")
    assert agent["locked"] is False
    hero = next(ldr for ldr in leaders if ldr["type"] == "hero")
    assert hero["locked"] is True
    assert sol["leaderIDs"] == [ldr["id"] for ldr in leaders]


def test_web_data_leader_state_override(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # God-Mode: odblokuj commandera.
    client.post(
        "/player/p1/edit",
        json={"leader_states": {"solcommander": "unlocked"}},
    )
    data = client.get("/api/public/game/g/web-data").json()
    sol = next(p for p in data["playerData"] if p["faction"] == "sol")
    commander = next(ldr for ldr in sol["leaders"] if ldr["type"] == "commander")
    hero = next(ldr for ldr in sol["leaders"] if ldr["type"] == "hero")
    assert commander["locked"] is False  # odblokowany
    assert hero["locked"] is True  # nietknięty


def test_new_game_without_map_string_uses_default(client: TestClient) -> None:
    # Bez map stringa — backend używa mapy testowej; kolory/sloty auto.
    resp = client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}, {"faction_id": "hacan"}]},
    )
    assert resp.status_code == 200
    data = client.get("/api/public/game/g/web-data").json()
    # Mapa testowa się załadowała (Mecatol + pierścienie).
    assert "000:18" in data["tilePositions"]
    assert len(data["tilePositions"]) > 10
    # Gracze z auto-przydziałem kolorów wg kolejności (red, green).
    players = {p["faction"]: p["color"] for p in data["playerData"]}
    assert players == {"sol": "red", "hacan": "green"}
    # Sol na 301, Hacan na 304 — statki w przestrzeni.
    assert data["tileUnitData"]["301"]["space"].get("sol")
    assert data["tileUnitData"]["304"]["space"].get("hacan")


def test_new_game_too_many_players_422(client: TestClient) -> None:
    resp = client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}] * 7},
    )
    assert resp.status_code == 422


def test_web_data_units_owned_is_real_base_ids(client: TestClient) -> None:
    # KLUCZOWE: 'unitsOwned' NIE może być [] (frontend lookupUnit odrzuca wtedy
    # wszystkie jednostki — [].includes zawsze False). Wysyłamy realne ID jednostek
    # BAZOWYCH (bez ulepszeń), by panel nie pokazywał błędnie „Upgraded".
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    data = client.get("/api/public/game/g/web-data").json()
    owned = data["playerData"][0]["unitsOwned"]
    assert isinstance(owned, list) and len(owned) > 0
    # Dla każdego asyncId JEDNA jednostka: wariant frakcyjny Sola wygrywa z generycznym.
    assert "sol_flagship" in owned  # frakcyjny flagship
    assert "sol_mech" in owned and "mech" not in owned  # bez podwójnego mecha
    # Fighter: Sol nie ma własnego wariantu, więc generyczny.
    assert "fighter" in owned
    # War Sun wymaga technologii 'ws' — Sol jej nie ma na starcie, więc NIE jest
    # posiadany (nie może liczyć się jak zbadany).
    assert "warsun" not in owned


def test_web_data_muaat_owns_innate_warsun(client: TestClient) -> None:
    # Muaat ma wrodzony War Sun (muaat_warsun, bez wymaganej technologii).
    client.post("/game/new", json={"players": [{"faction_id": "muaat"}]})
    data = client.get("/api/public/game/g/web-data").json()
    owned = data["playerData"][0]["unitsOwned"]
    assert "muaat_warsun" in owned
    # Generyczny warsun (za techem) nadal nieposiadany.
    assert "warsun" not in owned


def test_web_data_unit_counts_cap_and_deployed(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    data = client.get("/api/public/game/g/web-data").json()
    counts = data["playerData"][0]["unitCounts"]
    # Limity supply z AsyncTI4 (reinforcements.properties).
    assert counts["cv"]["unitCap"] == 4
    assert counts["ff"]["unitCap"] == 10
    assert counts["gf"]["unitCap"] == 12
    # Sol startuje z 2 carrierami w przestrzeni domowej → deployedCount >= 2.
    assert counts["cv"]["deployedCount"] >= 2


def test_web_data_stat_tile_positions(client: TestClient) -> None:
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}, {"faction_id": "hacan"}]},
    )
    data = client.get("/api/public/game/g/web-data").json()
    stats = data["statTilePositions"]
    # Każda frakcja ma 3 pozycje pierścienia 4 (heksy player-stats).
    assert set(stats.keys()) == {"sol", "hacan"}
    # Sol na slocie 301 → kolejność wg odległości: pierwszy = heks frakcji (centrum).
    # Zgodne 1:1 z AsyncTI4 (hacan 401,402,424 → firstHex=401).
    assert stats["sol"] == ["401", "402", "424"]
    for positions in stats.values():
        assert len(positions) == 3
        assert all(p.startswith("4") for p in positions)


def test_web_data_has_game_state(client: TestClient) -> None:
    # Panel faz we froncie wymaga obiektu gameState z poprawnym (małe litery) phase.
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "mentak"}, {"faction_id": "sol"}]},
    )
    data = client.get("/api/public/game/g/web-data").json()
    gs = data["gameState"]
    assert gs["phase"] == "strategy"  # domyślna faza, format frontendu
    # Aktywny gracz podawany jako KOLOR (frontend dopasowuje po kolorze).
    assert gs["activePlayer"] == "red"  # pierwszy gracz = red
    assert gs["activeSystem"] is None


def test_web_data_command_counters(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    data = client.get("/api/public/game/g/web-data").json()
    p = data["playerData"][0]
    # Startowe żetony dowodzenia (RULES.md 5): 3 taktyczne, 3 floty, 2 strategiczne.
    assert p["tacticalCC"] == 3
    assert p["fleetCC"] == 3
    assert p["strategicCC"] == 2
    assert p["ccReinf"] == 8


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
