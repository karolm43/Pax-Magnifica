"""Testy warstwy API (FastAPI): REST, God-Mode, Undo/Redo, mapa, WebSocket."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.game_state import GameState, PlayerState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    """Rejestr ładowany raz na moduł (odczyt assetów jest kosztowny)."""
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    """Klient testowy z osobnym magazynem w pamięci na każdy test."""
    app = create_app(registry=registry, store=EventStore(":memory:"))
    return TestClient(app)


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


def test_setup_unknown_faction_404(client: TestClient) -> None:
    resp = client.post(
        "/setup/player",
        json={
            "player_id": "red",
            "faction_id": "NOPE",
            "color": "red",
            "home_position": "301",
        },
    )
    assert resp.status_code == 404


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
    data = client.get("/api/public/game/local/web-data").json()
    p = data["playerData"][0]
    assert p["totalVps"] == 5
    assert p["tg"] == 7
    assert p["tacticalCC"] == 1
    # Edycja jest w historii — Undo cofa.
    client.post("/undo")
    p = client.get("/api/public/game/local/web-data").json()["playerData"][0]
    assert p["totalVps"] == 0
    assert p["tacticalCC"] == 3


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
