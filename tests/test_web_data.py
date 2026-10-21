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


def test_leader_states_merge_not_replace(client: TestClient) -> None:
    # REGRESJA: edycja jednego lidera NIE może kasować stanu pozostałych.
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post("/player/p1/edit", json={"leader_states": {"solcommander": "unlocked"}})
    client.post("/player/p1/edit", json={"leader_states": {"solhero": "unlocked"}})
    data = client.get("/api/public/game/g/web-data").json()
    sol = next(p for p in data["playerData"] if p["faction"] == "sol")
    states = {ldr["type"]: ldr["locked"] for ldr in sol["leaders"]}
    # Oba odblokowane równocześnie (commander nie wrócił do locked po edycji hero).
    assert states["commander"] is False
    assert states["hero"] is False


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


# --- Regresje audytu bugów game state (desync panel↔mapa + spójność) ---------


def test_unit_upgrade_tech_swaps_owned_variant(client: TestClient) -> None:
    # Bug 11: zbadanie technologii ulepszenia podmienia wpis w unitsOwned na wariant
    # ulepszony (frontend preferUpgradedUnit pokaże właściwe statystyki).
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    before = client.get("/api/public/game/g/web-data").json()["playerData"][0][
        "unitsOwned"
    ]
    # Sol ma wariant frakcyjny carriera (Advanced Carrier) → przed zbadaniem: bazowy
    # wariant frakcyjny, jego ulepszenie (Advanced Carrier II) wymaga techu 'ac2'.
    assert "sol_carrier" in before and "sol_carrier2" not in before
    # God-Mode: nadaj technologię Advanced Carrier II (alias 'ac2').
    client.post("/player/p1/edit", json={"technologies": ["ac2"]})
    after = client.get("/api/public/game/g/web-data").json()["playerData"][0][
        "unitsOwned"
    ]
    # Po zbadaniu: ulepszony wariant zastępuje bazowy (jeden wpis na asyncId cv).
    assert "sol_carrier2" in after and "sol_carrier" not in after


def test_warsun_tech_grants_generic_warsun(client: TestClient) -> None:
    # Bug 11 (pokrewny): War Sun jest posiadany dopiero po zbadaniu technologii 'ws'.
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post("/player/p1/edit", json={"technologies": ["ws"]})
    owned = client.get("/api/public/game/g/web-data").json()["playerData"][0][
        "unitsOwned"
    ]
    assert "warsun" in owned


def test_duplicate_faction_keeps_both_players_units(client: TestClient) -> None:
    # Bug 1: dwaj gracze z TĄ SAMĄ frakcją nie mogą scalać się w jeden wpis.
    # Każdy dostaje własny, niekolidujący klucz tożsamości (player_id).
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Ręcznie dołóż drugiego gracza z tą samą frakcją, z jednostkami w przestrzeni.
    client.post("/player/p2/edit", json={"faction": "sol", "color": "blue"})
    client.post(
        "/system/301/edit-units",
        json={"zone": "space", "faction": "p2", "asyncId": "dd", "delta": 2},
    )
    data = client.get("/api/public/game/g/web-data").json()
    # Obaj gracze obecni w playerData.
    keys = {p["faction"] for p in data["playerData"]}
    assert "p2" in keys  # drugi gracz pod kluczem player_id (kolizja frakcji)
    # Jednostki p2 widoczne pod jego kluczem (nie scalone z p1).
    space = data["tileUnitData"]["301"]["space"]
    assert "p2" in space
    assert any(e["entityId"] == "dd" and e["count"] == 2 for e in space["p2"])


def test_resolve_player_prefers_exact_player_id(client: TestClient) -> None:
    # Bug 2: edycja po kluczu player_id trafia dokładnie w tego gracza, nie w innego
    # o tej samej frakcji.
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post("/player/p2/edit", json={"faction": "sol", "color": "blue"})
    client.post(
        "/system/305/edit-units",
        json={"zone": "space", "faction": "p2", "asyncId": "ca", "delta": 1},
    )
    data = client.get("/api/public/game/g/web-data").json()
    space = data["tileUnitData"]["305"]["space"]
    # Dokładnie p2 dostał cruisera (nie p1/sol).
    assert "p2" in space and "sol" not in space


def test_planet_control_single_source_player_edit(client: TestClient) -> None:
    # Bug 3: edycja controlled_planets gracza aktualizuje planet_owners systemu,
    # więc mapa (controlledBy) i panel (planets) zgadzają się.
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Znajdź planetę z mapy, którą nadamy Solowi (Mecatol Rex = 'mr' w systemie 18).
    client.post("/player/p1/edit", json={"controlled_planets": ["mr"]})
    data = client.get("/api/public/game/g/web-data").json()
    sol = next(p for p in data["playerData"] if p["faction"] == "sol")
    # Panel: Mecatol na liście planet gracza.
    assert "mr" in sol["planets"]
    # Mapa: Mecatol w systemie 000 kontrolowany przez Sol.
    assert data["tileUnitData"]["000"]["planets"]["mr"]["controlledBy"] == "sol"


def test_planet_control_single_source_system_edit(client: TestClient) -> None:
    # Bug 3 (odwrotny kierunek): nadanie właściciela w systemie od razu widać w panelu.
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post(
        "/system/000/planet/mr",
        json={"changes": [], "owner_id": "p1"},
    )
    data = client.get("/api/public/game/g/web-data").json()
    sol = next(p for p in data["playerData"] if p["faction"] == "sol")
    assert "mr" in sol["planets"]


def test_unit_counts_has_no_monument_row(client: TestClient) -> None:
    # Bug 6: 'monument' nie jest asyncId standardowej jednostki — nie może pojawić
    # się jako widmowy wiersz w panelu rezerwy.
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    data = client.get("/api/public/game/g/web-data").json()
    counts = data["playerData"][0]["unitCounts"]
    assert "monument" not in counts


def test_active_and_passed_is_not_contradictory(client: TestClient) -> None:
    # Bug 7: gracz nie może być jednocześnie aktywny i spasowany — serializer nie
    # wskazuje wtedy aktywnego (null) zamiast wysyłać sprzeczne sygnały.
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # God-Mode: pierwszy (aktywny) gracz pasuje bezpośrednio.
    client.post("/player/p1/edit", json={"passed": True})
    data = client.get("/api/public/game/g/web-data").json()
    assert data["gameState"]["activePlayer"] is None
    sol = next(p for p in data["playerData"] if p["faction"] == "sol")
    assert sol["active"] is False and sol["passed"] is True


def test_active_color_ambiguous_when_duplicate_color(client: TestClient) -> None:
    # Bug 7: gdy dwóch graczy ma ten sam kolor, dopasowanie po kolorze jest
    # niejednoznaczne — nie wskazujemy aktywnego po kolorze.
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post("/player/p2/edit", json={"faction": "hacan", "color": "red"})
    data = client.get("/api/public/game/g/web-data").json()
    # p1 jest aktywny i ma kolor red; p2 też red → activePlayer null.
    assert data["gameState"]["activePlayer"] is None


def test_new_game_rejects_home_position_off_map(client: TestClient) -> None:
    # Bug 8: pozycja domowa spoza mapy jest odrzucana (inaczej flota nie renderuje się).
    resp = client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol", "home_position": "999"}]},
    )
    assert resp.status_code == 422


def test_edit_units_rejects_unknown_base_type_via_space(client: TestClient) -> None:
    # Bug 5: nieznany baseType nie może wejść do stanu (ginąłby w web-data).
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    resp = client.post(
        "/system/301/space",
        json={"changes": [{"player_id": "p1", "base_type": "cavalry", "count": 1}]},
    )
    assert resp.status_code == 422


def test_stat_tile_anchored_to_home_not_conquest(client: TestClient) -> None:
    # Bug 9: heks stat-area kotwiczy się do slotu domowego gracza (home_position),
    # niezależnie od tego, które inne planety gracz kontroluje.
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Sol zdobywa Mecatol (system 000, pierścień 0) — nie może przeciągnąć heksa tam.
    client.post("/system/000/planet/mr", json={"changes": [], "owner_id": "p1"})
    data = client.get("/api/public/game/g/web-data").json()
    positions = data["statTilePositions"]["sol"]
    # Heksy nadal przy domu (pierścień 4), nie przy zdobytym Mecatolu (pierścień 0).
    assert all(p.startswith("4") for p in positions)
