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


# --- Faza strategii (Etap E2) -------------------------------------------------


def test_strategy_cards_pool_endpoint(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    cards = client.get("/strategy/cards").json()
    # Domyślny zestaw PoK: 8 kart, inicjatywy 1..8, nazwy z danych.
    assert [c["initiative"] for c in cards] == [1, 2, 3, 4, 5, 6, 7, 8]
    names = {c["name"] for c in cards}
    assert {"Leadership", "Trade", "Imperial"} <= names
    # Na starcie nic nie wybrane, brak TG na kartach.
    assert all(c["picked_by"] is None and c["trade_goods"] == 0 for c in cards)


def test_strategy_pick_assigns_and_appears_in_web_data(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post("/strategy/pick", json={"player_id": "p1", "initiative": 3})
    # Pula: karta 3 ma właściciela p1.
    cards = client.get("/strategy/cards").json()
    politics = next(c for c in cards if c["initiative"] == 3)
    assert politics["picked_by"] == "p1"
    # web-data: strategyCards + playerData.scs odzwierciedlają wybór.
    data = client.get("/api/public/game/g/web-data").json()
    sc3 = next(c for c in data["strategyCards"] if c["initiative"] == 3)
    assert sc3["picked"] is True
    assert sc3["pickedByFaction"] == "sol"  # klucz tożsamości = frakcja
    sol = next(p for p in data["playerData"] if p["faction"] == "sol")
    assert 3 in sol["scs"]


def test_strategy_pick_transfers_trade_goods(client: TestClient) -> None:
    # Dwaj gracze; p1 wybiera 1, nowa runda dokłada TG na niewybranych, p2 bierze TG.
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}, {"faction_id": "hacan"}]},
    )
    client.post("/strategy/pick", json={"player_id": "p1", "initiative": 1})
    # Nowa runda: akumulacja +1 TG na kartach 2..8 (p2 nic nie wybrał), reset puli.
    client.post("/round/next")
    cards = client.get("/strategy/cards").json()
    card5 = next(c for c in cards if c["initiative"] == 5)
    assert card5["trade_goods"] == 1  # +1 z akumulacji
    # p2 wybiera kartę 5 → dostaje 1 TG z karty, licznik karty zeruje się.
    data_before = client.get("/api/public/game/g/web-data").json()
    hacan_tg_before = next(
        p for p in data_before["playerData"] if p["faction"] == "hacan"
    )["tg"]
    client.post("/strategy/pick", json={"player_id": "p2", "initiative": 5})
    data_after = client.get("/api/public/game/g/web-data").json()
    hacan_tg_after = next(
        p for p in data_after["playerData"] if p["faction"] == "hacan"
    )["tg"]
    assert hacan_tg_after == hacan_tg_before + 1
    sc5 = next(c for c in data_after["strategyCards"] if c["initiative"] == 5)
    assert sc5["tradeGoods"] == 0


def test_strategy_play_marks_exhausted_in_web_data(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post("/strategy/pick", json={"player_id": "p1", "initiative": 6})
    client.post("/strategy/play", json={"player_id": "p1", "initiative": 6})
    data = client.get("/api/public/game/g/web-data").json()
    sc6 = next(c for c in data["strategyCards"] if c["initiative"] == 6)
    assert sc6["exhausted"] is True and sc6["played"] is True
    sol = next(p for p in data["playerData"] if p["faction"] == "sol")
    assert 6 in sol["exhaustedSCs"]


def test_strategy_pick_rejects_taken_card(client: TestClient) -> None:
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}, {"faction_id": "hacan"}]},
    )
    client.post("/strategy/pick", json={"player_id": "p1", "initiative": 2})
    resp = client.post("/strategy/pick", json={"player_id": "p2", "initiative": 2})
    assert resp.status_code == 422


def test_strategy_pick_sets_action_phase_initiative(client: TestClient) -> None:
    # Inicjatywa fazy akcji wynika z wybranych kart (RULES.md 9): niższy numer = pierwszy.
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}, {"faction_id": "hacan"}]},
    )
    client.post("/strategy/pick", json={"player_id": "p1", "initiative": 6})
    client.post("/strategy/pick", json={"player_id": "p2", "initiative": 2})
    # Przejdź do fazy akcji — aktywny powinien być p2 (karta 2 < 6).
    client.post("/phase/next")  # strategy -> action
    data = client.get("/api/public/game/g/web-data").json()
    hacan = next(p for p in data["playerData"] if p["faction"] == "hacan")
    assert hacan["active"] is True


# --- Setup: liderzy Keleres, wybór tech, home off-board (Ghost/Crimson) --------


def test_keleres_all_variants_own_shared_faction_units(client: TestClient) -> None:
    # Keleres dzieli keleres_flagship/keleres_mech między 3 warianty, ale pole faction
    # jednostki wskazuje tylko keleresm. Lista units frakcji jest autorytatywna —
    # wszystkie 3 warianty muszą mieć flagship i mech (inaczej panel ich nie pokazuje).
    for faction_id in ("keleresa", "keleresm", "keleresx"):
        client.post("/game/new", json={"players": [{"faction_id": faction_id}]})
        owned = client.get("/api/public/game/g/web-data").json()["playerData"][0][
            "unitsOwned"
        ]
        assert "keleres_flagship" in owned
        assert "keleres_mech" in owned


def test_faction_units_do_not_leak_across_factions(client: TestClient) -> None:
    # Regresja: Sol nie może dostać cudzych wariantów (np. keleres_*).
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    owned = client.get("/api/public/game/g/web-data").json()["playerData"][0][
        "unitsOwned"
    ]
    assert "sol_flagship" in owned
    assert not any("keleres" in u for u in owned)


def test_keleres_leaders_typed_from_data(client: TestClient) -> None:
    # Keleres hero (keleresherokuuasi) nie kończy się na "hero" — typ musi pochodzić
    # z danych lidera, nie z końcówki id. Każdy wariant: agent/commander/hero + hero locked.
    for faction_id, hero_id in (
        ("keleresa", "keleresherokuuasi"),
        ("keleresm", "keleresheroharka"),
        ("keleresx", "keleresheroodlynn"),
    ):
        client.post("/game/new", json={"players": [{"faction_id": faction_id}]})
        p = client.get("/api/public/game/g/web-data").json()["playerData"][0]
        types = {ldr["type"] for ldr in p["leaders"]}
        assert types == {"agent", "commander", "hero"}
        hero = next(ldr for ldr in p["leaders"] if ldr["type"] == "hero")
        assert hero["id"] == hero_id
        assert hero["locked"] is True


def test_factions_expose_starting_tech_choice(client: TestClient) -> None:
    factions = client.get("/factions").json()
    winnu = next(f for f in factions if f["id"] == "winnu")
    assert winnu["starting_tech_amount"] == 1
    assert len(winnu["starting_tech_options"]) == 8
    argent = next(f for f in factions if f["id"] == "argent")
    assert argent["starting_tech_amount"] == 2
    # Frakcja ze stałą tech nie ma wyboru.
    sol = next(f for f in factions if f["id"] == "sol")
    assert sol["starting_tech_amount"] == 0


def test_starting_tech_choice_applied(client: TestClient) -> None:
    # Argent wybiera 2 z [nm, st, ps].
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "argent", "starting_tech": ["nm", "ps"]}]},
    )
    p = client.get("/api/public/game/g/web-data").json()["playerData"][0]
    assert set(p["techs"]) == {"nm", "ps"}


def test_starting_tech_choice_validates_amount(client: TestClient) -> None:
    # Argent wymaga 2 — podanie 1 to błąd.
    resp = client.post(
        "/game/new",
        json={"players": [{"faction_id": "argent", "starting_tech": ["nm"]}]},
    )
    assert resp.status_code == 422


def test_starting_tech_choice_validates_option(client: TestClient) -> None:
    # 'amd' nie jest w opcjach Argenta.
    resp = client.post(
        "/game/new",
        json={"players": [{"faction_id": "argent", "starting_tech": ["nm", "amd"]}]},
    )
    assert resp.status_code == 422


def test_starting_tech_default_when_omitted(client: TestClient) -> None:
    # Quick-start bez wyboru: fallback na pierwsze N opcji (gra nie pada).
    client.post("/game/new", json={"players": [{"faction_id": "winnu"}]})
    p = client.get("/api/public/game/g/web-data").json()["playerData"][0]
    assert len(p["techs"]) == 1  # Winnu: 1 technologia


def test_ghost_home_system_off_board(client: TestClient) -> None:
    # Ghost: brama (sys 17) na slocie 301, prawdziwy dom (sys 51, planeta creuss) off-board.
    client.post("/game/new", json={"players": [{"faction_id": "ghost"}]})
    data = client.get("/api/public/game/g/web-data").json()
    tp = dict(entry.split(":") for entry in data["tilePositions"])
    assert tp.get("301") == "17"  # brama na slocie
    # Prawdziwy dom w rogu off-board (tr/br/bl) — kafelek 51.
    off = {pos: sid for pos, sid in tp.items() if pos in {"tr", "br", "bl", "tl"}}
    assert "51" in off.values()
    off_pos = next(pos for pos, sid in off.items() if sid == "51")
    # Flota + kontrola planety creuss są na kafelku off-board, nie na bramie.
    tile = data["tileUnitData"][off_pos]
    assert tile["space"].get("ghost")
    assert tile["planets"]["creuss"]["controlledBy"] == "ghost"


def test_crimson_home_system_off_board(client: TestClient) -> None:
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "crimson", "starting_tech": ["det"]}]},
    )
    data = client.get("/api/public/game/g/web-data").json()
    tp = dict(entry.split(":") for entry in data["tilePositions"])
    assert tp.get("301") == "94"  # brama The Sorrow
    off = {pos: sid for pos, sid in tp.items() if pos in {"tr", "br", "bl", "tl"}}
    assert "118" in off.values()


def test_ghost_and_crimson_corner_collision(client: TestClient) -> None:
    # Obaj startują na slotach mapujących się na 'tr' — drugi musi dostać inny róg.
    client.post(
        "/game/new",
        json={
            "players": [
                {"faction_id": "ghost"},
                {"faction_id": "crimson", "starting_tech": ["det"]},
            ]
        },
    )
    data = client.get("/api/public/game/g/web-data").json()
    tp = dict(entry.split(":") for entry in data["tilePositions"])
    off = {pos for pos in tp if pos in {"tr", "br", "bl", "tl"}}
    assert len(off) == 2  # dwa różne rogi, bez nakładania
