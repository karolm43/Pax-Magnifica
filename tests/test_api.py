"""Testy warstwy API (FastAPI): REST, God-Mode, Undo/Redo, mapa, WebSocket."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.game_state import GameState, PlayerState
from src.core.registry import StaticDataRegistry
from tests.setup_helpers import finish_setup


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    """Rejestr ładowany raz na moduł (odczyt assetów jest kosztowny)."""
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    """Klient testowy z osobnym magazynem w pamięci na każdy test."""
    app = create_app(registry=registry, store=EventStore(":memory:"))
    return TestClient(app)


def _web_data(
    client: TestClient, game_id: str, viewer: str = "p1"
) -> dict[str, Any]:
    """Pobiera web-data z perspektywy ``viewer`` (domyślnie ``p1``).

    Po integracji projekcji widoczności (R6) endpoint wymaga gracza perspektywy —
    bez aktywnego gracza i bez ``viewing_player`` zwraca 422 (R6.7). Te testy
    budują stany God-Mode / single-player bez aktywnego gracza, więc wskazują
    viewera jawnie (tak jak frontend).
    """
    data: dict[str, Any] = client.get(
        f"/api/public/game/{game_id}/web-data",
        params={"viewing_player": viewer},
    ).json()
    return data


# --- GET /state ----------------------------------------------------------


def test_get_state_returns_initial(client: TestClient) -> None:
    resp = client.get("/state")
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "state"
    assert body["state"]["round_number"] == 1
    assert body["history"]["history_size"] >= 1
    assert body["history"]["can_undo"] is False


# --- GET /map ------------------------------------------------------------


def test_get_map_has_center_and_ring(client: TestClient) -> None:
    resp = client.get("/map")
    assert resp.status_code == 200
    view = resp.json()
    positions = {t["position"] for t in view["tiles"]}
    assert "000" in positions  # centrum (Mecatol)
    assert len(view["tiles"]) >= 2
    # Centrum ma współrzędne (0,0,0)
    center = next(t for t in view["tiles"] if t["position"] == "000")
    assert (center["q"], center["r"], center["s"]) == (0, 0, 0)
    # Są krawędzie sąsiedztwa między centrum a pierścieniem
    assert any(e["a"] == "000" or e["b"] == "000" for e in view["edges"])


def test_map_tiles_have_valid_cube_coords(client: TestClient) -> None:
    view = client.get("/map").json()
    for tile in view["tiles"]:
        assert tile["q"] + tile["r"] + tile["s"] == 0


SAMPLE_MAP_STRING = (
    "72 66 77 26 27 34 50 69 76 31 35 37 78 62 75 67 38 65 "
    "0 28 79 0 48 64 0 44 29 0 25 47 0 39 49 0 41 40"
)


def test_load_map_string_replaces_map(client: TestClient) -> None:
    resp = client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    assert resp.status_code == 200
    view = resp.json()
    positions = {t["position"] for t in view["tiles"]}
    assert "000" in positions
    # 30 systemów + 6 slotów domowych + Mecatol = 37.
    assert len(view["tiles"]) == 37
    # Sloty domowe na rogach z kolorami.
    home = next(t for t in view["tiles"] if t["position"] == "301")
    assert home["is_home_slot"] is True
    assert home["home_color"] == "red"
    assert home["image_url"] is None
    # Po załadowaniu GET /map zwraca nową mapę.
    assert len(client.get("/map").json()["tiles"]) == 37


def test_load_map_string_invalid_returns_422(client: TestClient) -> None:
    resp = client.post("/map/load", json={"map_string": "   "})
    assert resp.status_code == 422


# --- Frakcje i setup -----------------------------------------------------


def test_get_factions(client: TestClient) -> None:
    resp = client.get("/factions")
    assert resp.status_code == 200
    factions = resp.json()
    assert len(factions) > 0
    arborec = next((f for f in factions if f["id"] == "arborec"), None)
    assert arborec is not None
    assert arborec["home_system"] == "05"
    # Placeholdery systemowe (Neutral/Lazax) NIE są grywalne → brak na liście.
    ids = {f["id"] for f in factions}
    assert "neutral" not in ids
    assert "lazax" not in ids
    # Firmament jest wybieralny; Obsidian NIE (zdolność nocturne „cannot be chosen
    # during setup" — wchodzi do gry tylko przez akcję Firmamentu).
    assert "firmament" in ids
    assert "obsidian" not in ids


def test_setup_rejects_non_playable_faction(client: TestClient) -> None:
    client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    resp = client.post(
        "/setup/player",
        json={
            "player_id": "red",
            "faction_id": "neutral",
            "color": "red",
            "home_position": "301",
        },
    )
    assert resp.status_code == 422
    assert "not playable" in resp.json()["detail"]


def test_setup_player_places_units(client: TestClient) -> None:
    client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    resp = client.post(
        "/setup/player",
        json={
            "player_id": "red",
            "faction_id": "arborec",
            "color": "red",
            "home_position": "301",
        },
    )
    assert resp.status_code == 200
    view = resp.json()
    home = next(t for t in view["tiles"] if t["position"] == "301")
    # Statki w przestrzeni z grafiką jednostki.
    space_types = {s["base_type"] for s in home["space_units"]}
    assert "carrier" in space_types
    carrier = next(s for s in home["space_units"] if s["base_type"] == "carrier")
    assert carrier["image_url"] == "/static/units/red_cv.png"
    # Naziemne na planecie.
    nestphar = next(p for p in home["planet_units"] if p["planet_id"] == "nestphar")
    assert nestphar["owner_id"] == "red"
    assert any(s["base_type"] == "infantry" for s in nestphar["stacks"])


def test_setup_unknown_faction_422(client: TestClient) -> None:
    # Nowy kontrakt (zad. 9.1): walidacja setupu jest delegowana do
    # ``resolve_players`` w core, które dla nieznanej frakcji rzuca ``ValueError``
    # → HTTP 422 (spójnie z resztą błędów walidacji setupu, design §Error Handling).
    # Wcześniej tymczasowy strażnik routera zwracał 404 — usunięty.
    resp = client.post(
        "/setup/player",
        json={
            "player_id": "red",
            "faction_id": "NOPE",
            "color": "red",
            "home_position": "301",
        },
    )
    assert resp.status_code == 422
    assert "NOPE" in resp.json()["detail"]


# --- Zmiana położenia jednostek ------------------------------------------


def test_set_space_units(client: TestClient) -> None:
    client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    resp = client.post(
        "/system/101/space",
        json={"changes": [{"player_id": "blu", "base_type": "destroyer", "count": 3}]},
    )
    assert resp.status_code == 200
    view = resp.json()
    tile = next(t for t in view["tiles"] if t["position"] == "101")
    dd = next(s for s in tile["space_units"] if s["base_type"] == "destroyer")
    assert dd["count"] == 3
    assert dd["player_id"] == "blu"


def test_set_space_units_zero_removes(client: TestClient) -> None:
    client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    client.post(
        "/system/101/space",
        json={"changes": [{"player_id": "blu", "base_type": "cruiser", "count": 2}]},
    )
    view = client.post(
        "/system/101/space",
        json={"changes": [{"player_id": "blu", "base_type": "cruiser", "count": 0}]},
    ).json()
    tile = next(t for t in view["tiles"] if t["position"] == "101")
    assert all(s["base_type"] != "cruiser" for s in tile["space_units"])


def test_set_planet_units_and_owner(client: TestClient) -> None:
    client.post("/map/load", json={"map_string": SAMPLE_MAP_STRING})
    resp = client.post(
        "/system/102/planet/hopesend",
        json={
            "owner_id": "grn",
            "changes": [{"player_id": "grn", "base_type": "infantry", "count": 2}],
        },
    )
    assert resp.status_code == 200
    view = resp.json()
    tile = next(t for t in view["tiles"] if t["position"] == "102")
    planet = next(p for p in tile["planet_units"] if p["planet_id"] == "hopesend")
    assert planet["owner_id"] == "grn"
    assert any(s["base_type"] == "infantry" and s["count"] == 2 for s in planet["stacks"])


def test_map_tiles_expose_image_url(client: TestClient) -> None:
    """Kafelki niosą URL grafiki wskazujący na /static/tiles/<plik>."""
    view = client.get("/map").json()
    center = next(t for t in view["tiles"] if t["position"] == "000")
    # Mecatol ma zdefiniowany imagePath w danych -> image_url ustawione.
    assert center["image_url"] is not None
    assert center["image_url"].startswith("/static/tiles/")
    assert center["image_url"].endswith(".png")


# --- PUT /state (God-Mode: pełne nadpisanie) -----------------------------


def test_put_state_replaces_and_records_history(client: TestClient) -> None:
    new_state = GameState(
        round_number=3,
        players={"p1": PlayerState(player_id="p1", victory_points=5)},
    )
    resp = client.put("/state", json=new_state.model_dump(mode="json"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"]["round_number"] == 3
    assert body["state"]["players"]["p1"]["victory_points"] == 5
    assert body["history"]["can_undo"] is True


# --- POST /god-mode/patch -----------------------------------------------


def test_patch_updates_only_given_fields(client: TestClient) -> None:
    client.put(
        "/state",
        json=GameState(
            round_number=2,
            players={"p1": PlayerState(player_id="p1", victory_points=1)},
        ).model_dump(mode="json"),
    )
    resp = client.post("/god-mode/patch", json={"round_number": 7})
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"]["round_number"] == 7
    # players nie podane w patchu -> pozostaje bez zmian
    assert body["state"]["players"]["p1"]["victory_points"] == 1


def test_patch_invalid_data_returns_422(client: TestClient) -> None:
    # Niepoprawna faza -> walidacja GameState powinna odrzucić patch.
    resp = client.post("/god-mode/patch", json={"phase": "NOT_A_PHASE"})
    assert resp.status_code == 422


# --- Undo / Redo ---------------------------------------------------------


def test_undo_redo_round_trip(client: TestClient) -> None:
    client.put("/state", json=GameState(round_number=2).model_dump(mode="json"))
    client.put("/state", json=GameState(round_number=3).model_dump(mode="json"))

    undo1 = client.post("/undo").json()
    assert undo1["state"]["round_number"] == 2

    undo2 = client.post("/undo").json()
    assert undo2["state"]["round_number"] == 1
    assert undo2["history"]["can_undo"] is False

    redo1 = client.post("/redo").json()
    assert redo1["state"]["round_number"] == 2
    assert redo1["history"]["can_redo"] is True


def test_commit_after_undo_truncates_redo(client: TestClient) -> None:
    """God-Mode: nowa zmiana po undo obcina gałąź redo (semantyka EventStore)."""
    client.put("/state", json=GameState(round_number=2).model_dump(mode="json"))
    client.put("/state", json=GameState(round_number=3).model_dump(mode="json"))
    client.post("/undo")  # wracamy do round=2
    # Nowa zmiana po undo
    client.put("/state", json=GameState(round_number=99).model_dump(mode="json"))
    body = client.get("/state").json()
    assert body["state"]["round_number"] == 99
    assert body["history"]["can_redo"] is False


# --- WebSocket -----------------------------------------------------------


def test_ws_sends_state_on_connect(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "state"
        assert msg["state"]["round_number"] == 1


def test_ws_receives_broadcast_on_mutation(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        _ = ws.receive_json()  # początkowy stan
        client.put("/state", json=GameState(round_number=42).model_dump(mode="json"))
        pushed = ws.receive_json()
        assert pushed["type"] == "state"
        assert pushed["state"]["round_number"] == 42


# --- Edytor God-Mode (edit-units / move) --------------------------------


def _space_count(view: Any, position: str, base_type: str) -> int:
    """Pomocniczo: liczba jednostek danego typu w przestrzeni pozycji."""
    tile = next(t for t in view["tiles"] if t["position"] == position)
    stacks = [s for s in tile["space_units"] if s["base_type"] == base_type]
    return sum(s["count"] for s in stacks)


def test_edit_units_add_and_remove(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Dodaj 3 krążowniki (ca) Sola w przestrzeni 101.
    resp = client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "sol", "asyncId": "ca", "delta": 3},
    )
    assert resp.status_code == 200
    assert _space_count(resp.json(), "101", "cruiser") == 3
    # Odejmij 2 — zostaje 1.
    resp = client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "sol", "asyncId": "ca", "delta": -2},
    )
    assert _space_count(resp.json(), "101", "cruiser") == 1
    # Delta poniżej zera obcina do 0 (usuwa).
    resp = client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "sol", "asyncId": "ca", "delta": -5},
    )
    assert _space_count(resp.json(), "101", "cruiser") == 0


def test_edit_player_fields(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    resp = client.post(
        "/player/p1/edit",
        json={"victory_points": 5, "trade_goods": 7, "tactical_cc": 1},
    )
    assert resp.status_code == 200
    data = _web_data(client, "local")
    p = data["playerData"][0]
    assert p["totalVps"] == 5
    assert p["tg"] == 7
    assert p["tacticalCC"] == 1
    # Edycja jest w historii — Undo cofa.
    client.post("/undo")
    p = _web_data(client, "local")["playerData"][0]
    assert p["totalVps"] == 0
    assert p["tacticalCC"] == 3


def test_toggle_planet_exhaust(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Sol kontroluje Jord (dom). Przełącz wyczerpanie → pojawia się w exhaustedPlanets.
    resp = client.post(
        "/player/planet/toggle-exhaust",
        json={"player_id": "p1", "component_id": "jord"},
    )
    assert resp.status_code == 200
    p = _web_data(client, "local")["playerData"][0]
    assert "jord" in p["exhaustedPlanets"]
    # Ponowny toggle = ready (znika).
    client.post(
        "/player/planet/toggle-exhaust",
        json={"player_id": "p1", "component_id": "jord"},
    )
    p = _web_data(client, "local")["playerData"][0]
    assert "jord" not in p["exhaustedPlanets"]


def test_toggle_tech_exhaust(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Nadaj graczowi technologię, potem wyczerp ją.
    client.post("/player/p1/edit", json={"technologies": ["gf"]})
    client.post(
        "/player/tech/toggle-exhaust",
        json={"player_id": "p1", "component_id": "gf"},
    )
    p = _web_data(client, "local")["playerData"][0]
    assert "gf" in p["exhaustedTechs"]


def test_set_leader_state(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Wyczerp dowolnego lidera Sol przez endpoint stanu lidera.
    leaders = _web_data(client, "local")["playerData"][0][
        "leaders"
    ]
    leader_id = leaders[0]["id"]
    resp = client.post(
        "/player/leader/set-state",
        json={"player_id": "p1", "leader_id": leader_id, "state": "exhausted"},
    )
    assert resp.status_code == 200
    p = _web_data(client, "local")["playerData"][0]
    target = next(leader for leader in p["leaders"] if leader["id"] == leader_id)
    assert target["exhausted"] is True
    # Nieznany stan → 422.
    bad = client.post(
        "/player/leader/set-state",
        json={"player_id": "p1", "leader_id": leader_id, "state": "nope"},
    )
    assert bad.status_code == 422


def test_history_list_and_goto(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "sol", "asyncId": "ca", "delta": 2},
    )
    hist = client.get("/history").json()["entries"]
    # Co najmniej: initial, game:new, edit:101:space — ostatni bieżący.
    assert len(hist) >= 3
    assert hist[-1]["is_current"] is True
    labels = [e["label"] for e in hist]
    assert any(label.startswith("edit:101") for label in labels)
    # Skok do wcześniejszej migawki (przed edycją) cofa jednostki.
    before_edit = next(e for e in hist if e["label"] == "game:new")
    client.post(f"/history/goto/{before_edit['seq']}")
    view = client.get("/map").json()
    tile = next(t for t in view["tiles"] if t["position"] == "101")
    assert all(s["base_type"] != "cruiser" for s in tile["space_units"])


def test_game_events_stub_empty(client: TestClient) -> None:
    resp = client.get("/api/public/game/local/events")
    assert resp.status_code == 200
    assert resp.json() == []


def test_edit_units_unknown_async_422(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    resp = client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "sol", "asyncId": "zz", "delta": 1},
    )
    assert resp.status_code == 422


def test_move_units_between_systems(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "sol", "asyncId": "dd", "delta": 2},
    )
    resp = client.post(
        "/units/move",
        json={
            "fromPosition": "101",
            "fromZone": "space",
            "toPosition": "102",
            "toZone": "space",
            "faction": "sol",
            "asyncId": "dd",
            "count": 1,
        },
    )
    assert resp.status_code == 200
    view = resp.json()
    assert _space_count(view, "101", "destroyer") == 1
    assert _space_count(view, "102", "destroyer") == 1


def test_move_units_none_available_422(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    resp = client.post(
        "/units/move",
        json={
            "fromPosition": "101",
            "fromZone": "space",
            "toPosition": "102",
            "toZone": "space",
            "faction": "sol",
            "asyncId": "ws",
            "count": 1,
        },
    )
    assert resp.status_code == 422


def test_move_ship_onto_planet_rejected_422(client: TestClient) -> None:
    """Statek nie może trafić na planetę (reguła umiejscowienia, RULES.md 26)."""
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "sol", "asyncId": "dd", "delta": 1},
    )
    resp = client.post(
        "/units/move",
        json={
            "fromPosition": "101",
            "fromZone": "space",
            "toPosition": "101",
            "toZone": "mr",  # planeta Mecatol — statek tam nie może stać
            "faction": "sol",
            "asyncId": "dd",
            "count": 1,
        },
    )
    assert resp.status_code == 422


def test_move_infantry_into_space_rejected_422(client: TestClient) -> None:
    """Piechota nie może trafić do przestrzeni (reguła umiejscowienia, RULES.md 26)."""
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post(
        "/system/101/edit-units",
        json={"zone": "mr", "faction": "sol", "asyncId": "gf", "delta": 1},
    )
    resp = client.post(
        "/units/move",
        json={
            "fromPosition": "101",
            "fromZone": "mr",
            "toPosition": "102",
            "toZone": "space",  # piechota w przestrzeni — niedozwolone
            "faction": "sol",
            "asyncId": "gf",
            "count": 1,
        },
    )
    assert resp.status_code == 422


# --- Akcja taktyczna (E3) ------------------------------------------------


def test_tactical_activate_sets_active_system_and_token(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Faza strategii przy 1 graczu nie wskazuje pickera (Pick_Count nieobsługiwane
    # dla <3 graczy → active_player_id = None). Akcja taktyczna wymaga aktywnego
    # gracza, więc ustawiamy go God-Mode (wentyl) — test dotyczy aktywacji systemu,
    # nie wyboru kart strategii.
    client.post("/god-mode/patch", json={"phase": "ACTION", "active_player_id": "p1"})
    resp = client.post("/tactical/activate", json={"position": "101"})
    assert resp.status_code == 200
    state = resp.json()["state"]
    assert state["active_system"] == "101"
    assert state["tactical_step"] == "MOVEMENT"
    assert state["systems"]["101"]["command_tokens"] == ["p1"]

    # web-data: aktywny system + żeton w ccs (jako klucz tożsamości = frakcja).
    data = _web_data(client, "g")
    assert data["gameState"]["activeSystem"] == "101"
    assert data["gameState"]["tacticalStep"] == "MOVEMENT"
    assert data["tileUnitData"]["101"]["ccs"] == ["sol"]


def test_tactical_step_next_and_end(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Aktywny gracz przez God-Mode (patrz test aktywacji) — przy 1 graczu faza
    # strategii nie wskazuje pickera; test dotyczy maszyny kroków, nie wyboru kart.
    client.post("/god-mode/patch", json={"phase": "ACTION", "active_player_id": "p1"})
    client.post("/tactical/activate", json={"position": "101"})
    # MOVEMENT -> SPACE_CANNON
    state = client.post("/tactical/step/next").json()["state"]
    assert state["tactical_step"] == "SPACE_CANNON"
    # Zakończenie czyści aktywny system/krok, żeton zostaje.
    state = client.post("/tactical/end").json()["state"]
    assert state["active_system"] is None
    assert state["tactical_step"] is None
    assert state["systems"]["101"]["command_tokens"] == ["p1"]


def test_tactical_set_step_unknown_422(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    resp = client.post("/tactical/step/set", json={"step": "BOGUS"})
    assert resp.status_code == 422


def test_god_mode_command_token_add_remove(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    # Dodanie żetonu God-Mode (bez zużycia puli).
    client.post("/system/102/command-token", json={"faction": "sol"})
    data = _web_data(client, "g")
    assert data["tileUnitData"]["102"]["ccs"] == ["sol"]
    # Zdjęcie żetonu.
    client.request("DELETE", "/system/102/command-token", json={"faction": "sol"})
    data = _web_data(client, "g")
    assert data["tileUnitData"]["102"]["ccs"] == []


def test_combat_help_two_sides(client: TestClient) -> None:
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}, {"faction_id": "hacan"}]},
    )
    # Postaw statki obu graczy w tym samym systemie 101 (God-Mode).
    client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "sol", "asyncId": "ca", "delta": 2},
    )
    client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "hacan", "asyncId": "dn", "delta": 1},
    )
    resp = client.get("/tactical/combat/101")
    assert resp.status_code == 200
    body = resp.json()
    assert body["kind"] == "space"
    assert body["planet"] is None
    factions = {side["faction"] for side in body["sides"]}
    assert factions == {"sol", "hacan"}
    # Pomoc liczbowa obecna (asyncId, hits-on, expected).
    sol = next(s for s in body["sides"] if s["faction"] == "sol")
    cruiser = next(u for u in sol["units"] if u["asyncId"] == "ca")
    assert cruiser["combatHitsOn"] == 7
    assert cruiser["expectedHits"] == 0.8


def test_combat_help_single_side_empty(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    client.post(
        "/system/101/edit-units",
        json={"zone": "space", "faction": "sol", "asyncId": "ca", "delta": 2},
    )
    body = client.get("/tactical/combat/101").json()
    # Jeden gracz → brak walki (puste sides).
    assert body["sides"] == []


def test_capture_planet_endpoint(client: TestClient) -> None:
    client.post(
        "/game/new",
        json={"players": [{"faction_id": "sol"}, {"faction_id": "hacan"}]},
    )
    # hacan kontroluje planetę; sol ją przejmuje po inwazji.
    client.post(
        "/system/101/planet/somePlanet",
        json={"changes": [], "owner_id": "p2"},
    )
    resp = client.post(
        "/tactical/system/101/capture",
        json={"planet": "somePlanet", "faction": "sol"},
    )
    assert resp.status_code == 200
    # web-data: planeta kontrolowana teraz przez sol.
    data = _web_data(client, "g")
    planet = data["tileUnitData"]["101"]["planets"]["somePlanet"]
    assert planet["controlledBy"] == "sol"


def test_production_help_endpoint(client: TestClient) -> None:
    client.post("/game/new", json={"players": [{"faction_id": "sol"}]})
    resp = client.get("/tactical/production?faction=sol")
    assert resp.status_code == 200
    body = resp.json()
    # Sol kontroluje planety domowe → zasoby > 0; koszty jednostek obecne.
    assert body["availableResources"] > 0
    cruiser = next(u for u in body["units"] if u["baseType"] == "cruiser")
    assert cruiser["cost"] == 2.0
    fighter = next(u for u in body["units"] if u["baseType"] == "fighter")
    assert fighter["unitsPerCost"] == 2
    assert fighter["placement"] == "space"
    infantry = next(u for u in body["units"] if u["baseType"] == "infantry")
    assert infantry["placement"] == "planet"


def _complete_strategy_three_players(client: TestClient) -> None:
    """Tworzy grę 3-osobową i kompletuje wybór kart (gotowe do /phase/next)."""
    client.post(
        "/game/new",
        json={
            "players": [
                {"faction_id": "sol"},
                {"faction_id": "hacan"},
                {"faction_id": "mentak"},
            ]
        },
    )
    finish_setup(client)
    # Speaker = p1; wybór rundowy. p1:1,2 · p2:3,4 · p3:5,6.
    for player_id, initiative in (
        ("p1", 1), ("p2", 3), ("p3", 5),
        ("p1", 2), ("p2", 4), ("p3", 6),
    ):
        client.post(
            "/strategy/pick",
            json={"player_id": player_id, "initiative": initiative},
        )


def test_phase_next_rejects_non_speaker(client: TestClient) -> None:
    """RULES.md 31.4: przejście fazy ogłasza MÓWCA. /phase/next z player_id != speaker
    jest odrzucane (422), a faza zostaje bez zmian — kolejne wywołanie przez mówcę
    nadal przechodzi STRATEGY→ACTION (dowód, że stan nie został zmieniony)."""
    _complete_strategy_three_players(client)  # speaker = p1
    resp = client.post("/phase/next", json={"player_id": "p2"})
    assert resp.status_code == 422
    assert "speaker" in resp.json()["detail"].lower()
    # Faza nie zmieniona: prawidłowe wywołanie mówcy wciąż przechodzi do akcji.
    ok = client.post("/phase/next", json={"player_id": "p1"})
    assert ok.status_code == 200
    assert ok.json()["state"]["phase"] == "ACTION"


def test_phase_next_accepts_speaker(client: TestClient) -> None:
    """RULES.md 31.4: /phase/next z player_id == speaker przechodzi STRATEGY→ACTION."""
    _complete_strategy_three_players(client)  # speaker = p1
    resp = client.post("/phase/next", json={"player_id": "p1"})
    assert resp.status_code == 200
    assert resp.json()["state"]["phase"] == "ACTION"


def test_phase_next_without_player_id_backward_compatible(client: TestClient) -> None:
    """Bez player_id (legacy) /phase/next nie waliduje mówcy — działa jak dotąd."""
    _complete_strategy_three_players(client)
    resp = client.post("/phase/next")
    assert resp.status_code == 200
    assert resp.json()["state"]["phase"] == "ACTION"


def test_phase_step_marks_player_and_advances_in_status(client: TestClient) -> None:
    """/turn/phase-step (STATUS „Next player") oznacza gracza passed i przesuwa
    aktywnego dalej (DECYZJA 2026-11). Po komplecie kroków mówca może iść dalej."""
    _complete_strategy_three_players(client)  # speaker = p1
    client.post("/phase/next", json={"player_id": "p1"})  # STRATEGY → ACTION
    # Zakończ akcję szybko przez God-Mode: ustaw fazę STATUS bez pasów.
    client.post("/god-mode/patch", json={"phase": "STATUS", "active_player_id": "p1"})
    # p1 robi krok → passed, aktywny = p2.
    resp = client.post("/turn/phase-step", json={"player_id": "p1"})
    assert resp.status_code == 200
    state = resp.json()["state"]
    assert state["players"]["p1"]["passed"] is True
    assert state["active_player_id"] == "p2"


def test_phase_next_blocks_status_until_all_steps(client: TestClient) -> None:
    """Brama „wszyscy skończyli": w STATUSIE /phase/next (mówca) jest odrzucane (422),
    dopóki każdy gracz nie zrobi swojego kroku (DECYZJA 2026-11)."""
    _complete_strategy_three_players(client)  # speaker = p1
    client.post("/god-mode/patch", json={"phase": "STATUS", "active_player_id": "p1"})
    # Nikt jeszcze nie zrobił kroku → mówca nie może przejść dalej.
    blocked = client.post("/phase/next", json={"player_id": "p1"})
    assert blocked.status_code == 422
    assert "status" in blocked.json()["detail"].lower()
    # Każdy gracz robi swój krok.
    for player_id in ("p1", "p2", "p3"):
        client.post("/turn/phase-step", json={"player_id": player_id})
    ok = client.post("/phase/next", json={"player_id": "p1"})
    assert ok.status_code == 200
    assert ok.json()["state"]["phase"] == "AGENDA"


def test_phase_step_without_player_id_uses_active(client: TestClient) -> None:
    """Frontend woła /turn/phase-step BEZ player_id (backend adresuje swojego
    aktywnego gracza — fix rozjazdu „gracza pulpitu", 2026-11). Kolejne kliknięcia
    bez id przeklikują wszystkich graczy w kolejności inicjatywy."""
    _complete_strategy_three_players(client)  # speaker = p1
    client.post("/god-mode/patch", json={"phase": "STATUS", "active_player_id": "p1"})
    seen = []
    for _ in range(3):
        resp = client.post("/turn/phase-step", json={})
        assert resp.status_code == 200
        seen.append(resp.json()["state"]["active_player_id"])
    # p1 (zrobił) → p2 → p3 → z powrotem p1; wszyscy oznaczeni passed.
    assert seen == ["p2", "p3", "p1"]
    state = client.get("/state").json()["state"]
    assert all(p["passed"] for p in state["players"].values())
