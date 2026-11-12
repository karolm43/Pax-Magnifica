"""Scenariusze frakcji przez PRAWDZIWE API (nowa gra, setup, tura) - nie ręcznie zbudowany stan.

Sprawdzają to, co widzi gracz: czy decyzja/zdolność SAMA pojawia się we właściwej chwili
(oferta w ``/offers`` albo karta „Available now” z ``/faction-component/available-now``) i czy
gra na nią czeka. Testy jednostkowe frakcji (``test_<frakcja>.py``) sprawdzają efekty; tu -
dostępność w rzeczywistym przebiegu tury (RULES.md 62.0, 56).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from tests.setup_helpers import finish_setup


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(client: TestClient) -> dict[str, Any]:
    return client.get("/state").json()["state"]  # type: ignore[no-any-return]


def _start(registry: StaticDataRegistry, faction: str, **leaders: str) -> tuple[TestClient, str]:
    """Nowa gra 2-osobowa (``faction`` + Sol), faza akcji, tura gracza ``faction``."""
    client = TestClient(create_app(registry=registry, store=EventStore(":memory:")))
    other = "sol" if faction != "sol" else "letnev"
    assert client.post(
        "/game/new", json={"players": [{"faction_id": faction}, {"faction_id": other}]}
    ).status_code == 200
    finish_setup(client)
    state = _state(client)
    pid = next(p for p in state["seating_order"] if state["players"][p]["faction"] == faction)
    players = {
        p: {**state["players"][p], "strategy_cards": [i + 1]}
        for i, p in enumerate(state["seating_order"])
    }
    if leaders:
        players[pid]["leader_states"] = dict(leaders)
    assert client.post(
        "/god-mode/patch",
        json={"phase": "ACTION", "players": players, "active_player_id": pid},
    ).status_code == 200
    return client, pid


def _available(client: TestClient) -> set[str]:
    rows = client.get("/faction-component/available-now").json()["components"]
    return {f"{r['player_id']}:{r['component_id']}" for r in rows}


def test_tro_na_koniec_tury_gra_czeka_na_decyzje(registry: StaticDataRegistry) -> None:
    """Sardakk kończy turę przyciskiem End turn w trakcie akcji taktycznej we własnym domu:
    oferta T'ro wyskakuje, a tura NIE ucieka, dopóki gracz nie zdecyduje."""
    client, pid = _start(registry, "sardakk")
    home = _state(client)["players"][pid]["home_position"]
    assert client.post("/tactical/activate", json={"position": home}).status_code == 200
    assert client.post("/turn/end", json={"player_id": pid}).status_code == 200
    state = _state(client)
    assert state["active_player_id"] == pid  # tura czeka na decyzję
    offers = client.get("/offers", params={"player_id": pid}).json()["offers"]
    assert any(o["name"] == "T'ro" for o in offers), offers


def test_bohater_sardakk_sam_wyskakuje_po_ruchu(registry: StaticDataRegistry) -> None:
    """Tekklar Conditioning („After you move ships into the active system”) pojawia się jako
    „Available now” zaraz po ruchu - bez szukania w menu lidera."""
    client, pid = _start(registry, "sardakk", sardakkhero="unlocked")
    raw = _state(client)
    grid = grid_from_state(GameState.model_validate(raw), registry)
    homes = {p["home_position"] for p in raw["players"].values()}

    def plain(position: str) -> bool:
        return position not in homes and not grid.anomalies_at(position)

    # Mapa startowa bywa rzadka: bierzemy dwa sąsiednie zwykłe systemy i stawiamy tam krążownik.
    source, target = next(
        (a, b) for a in sorted(raw["systems"]) if plain(a)
        for b in sorted(grid.neighbors(a)) if plain(b) and b in raw["systems"]
    )
    placed = client.post(
        f"/system/{source}/space",
        json={"changes": [{"player_id": pid, "base_type": "cruiser", "count": 1}]},
    )
    assert placed.status_code == 200, placed.text
    assert client.post("/tactical/activate", json={"position": target}).status_code == 200
    assert f"{pid}:sardakkhero" not in _available(client)  # jeszcze nic nie ruszyło
    moved = client.post("/tactical/move", json={
        "faction": raw["players"][pid]["faction"], "fromPosition": source,
        "ships": [{"baseType": "cruiser", "count": 1}], "route": [source, target],
    })
    assert moved.status_code == 200, moved.text
    assert f"{pid}:sardakkhero" in _available(client)
    used = client.post("/faction-component/play", json={
        "player_id": pid, "kind": "leader", "component_id": "sardakkhero", "params": {},
    })
    assert used.status_code == 200, used.text
    assert _state(client)["tactical_step"] == "INVASION"
