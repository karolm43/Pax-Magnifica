"""Testy setupu startowego gry (RULES.md 45): tajne cele, notki, żeton Custodians, cele."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.event_store import EventStore
from src.core.registry import StaticDataRegistry

PLAYERS = {"players": [{"faction_id": "sol"}, {"faction_id": "arborec"}]}


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    return TestClient(create_app(registry=registry, store=EventStore(":memory:")))


def _state(client: TestClient) -> dict[str, Any]:
    return client.get("/state").json()["state"]  # type: ignore[no-any-return]


def _web(client: TestClient) -> dict[str, Any]:
    return client.get("/api/public/game/g/web-data").json()  # type: ignore[no-any-return]


def test_new_game_deals_promissory_hands(client: TestClient) -> None:
    client.post("/game/new", json=PLAYERS)
    for player in _state(client)["players"].values():
        hand = player["private"]["promissory_notes"]
        color = player["color"]
        # 5 wspólnych notek koloru gracza + 1 frakcyjna.
        assert len(hand) == 6
        assert len([n for n in hand if n.startswith(f"{color}_")]) == 5
    sol = _state(client)["players"]["p1"]["private"]["promissory_notes"]
    assert "ms" in sol  # frakcyjna notka Sol


def test_new_game_starts_in_secret_stage_with_two_candidates(client: TestClient) -> None:
    client.post("/game/new", json=PLAYERS)
    state = _state(client)
    assert state["setup"]["stage"] == "SECRETS"
    assert state["active_player_id"] == "p1"
    for player in state["players"].values():
        assert len(player["private"]["secret_candidates"]) == 2
        assert player["private"]["secret_objectives"] == []
    # Cele publiczne: 5+5 zakryte, żaden nie odkryty.
    assert state["objectives"]["revealed"] == []
    assert len(state["objectives"]["stage1_deck"]) == 5
    assert len(state["objectives"]["stage2_deck"]) == 5
    # Żeton Custodians jeszcze nie leży na planszy.
    assert state["setup"]["custodians_placed"] is False


def test_secret_choice_returns_other_to_deck_and_advances(client: TestClient) -> None:
    client.post("/game/new", json=PLAYERS)
    before = _state(client)
    deck_size = len(before["decks"]["secret_objective_deck"])
    first, second = before["players"]["p1"]["private"]["secret_candidates"]
    resp = client.post("/setup/secret", json={"player_id": "p1", "objective_id": first})
    assert resp.status_code == 200
    after = _state(client)
    assert after["players"]["p1"]["private"]["secret_objectives"] == [first]
    assert after["players"]["p1"]["private"]["secret_candidates"] == []
    assert len(after["decks"]["secret_objective_deck"]) == deck_size + 1
    assert second in after["decks"]["secret_objective_deck"]
    assert after["active_player_id"] == "p2"


def test_secret_choice_rejects_wrong_player_and_foreign_card(client: TestClient) -> None:
    client.post("/game/new", json=PLAYERS)
    state = _state(client)
    p2_card = state["players"]["p2"]["private"]["secret_candidates"][0]
    # Nie jego kolej.
    assert client.post(
        "/setup/secret", json={"player_id": "p2", "objective_id": p2_card}
    ).status_code == 422
    # Karta spoza jego dwóch kandydatów.
    assert client.post(
        "/setup/secret", json={"player_id": "p1", "objective_id": p2_card}
    ).status_code == 422


def test_bots_choose_secret_automatically(client: TestClient) -> None:
    client.post(
        "/game/new",
        json={
            "players": [
                {"faction_id": "sol"},
                {"faction_id": "arborec", "control_type": "BOT"},
            ]
        },
    )
    state = _state(client)
    assert len(state["players"]["p2"]["private"]["secret_objectives"]) == 1
    assert state["setup"]["secrets_chosen"] == ["p2"]
    assert state["active_player_id"] == "p1"


def test_full_setup_flow_ends_with_strategy_phase(client: TestClient) -> None:
    client.post("/game/new", json=PLAYERS)
    # Strategii nie da się wybrać przed końcem setupu.
    assert client.post(
        "/strategy/pick", json={"player_id": "p1", "initiative": 1}
    ).status_code == 422

    for pid in ("p1", "p2"):
        card = _state(client)["players"][pid]["private"]["secret_candidates"][0]
        assert client.post(
            "/setup/secret", json={"player_id": pid, "objective_id": card}
        ).status_code == 200
    state = _state(client)
    assert state["setup"]["stage"] == "CUSTODIANS"
    assert state["active_player_id"] == state["speaker_id"]

    # Tylko mówca kładzie żeton.
    assert client.post("/setup/custodians", json={"player_id": "p2"}).status_code == 422
    assert client.post("/setup/custodians", json={"player_id": "p1"}).status_code == 200
    assert _state(client)["setup"]["stage"] == "OBJECTIVES"

    # Cele odkrywa tylko mówca; po tym setup się kończy.
    assert client.post(
        "/setup/reveal-objectives", json={"player_id": "p2"}
    ).status_code == 422
    assert client.post(
        "/setup/reveal-objectives", json={"player_id": "p1"}
    ).status_code == 200
    state = _state(client)
    assert state["setup"] is None
    assert len(state["objectives"]["revealed"]) == 2
    assert len(state["objectives"]["stage1_deck"]) == 3
    assert state["phase"] == "STRATEGY"
    assert client.post(
        "/strategy/pick", json={"player_id": "p1", "initiative": 1}
    ).status_code == 200


def _mecatol_tokens(data: dict[str, Any]) -> list[dict[str, Any]]:
    planets = data["tileUnitData"]["000"]["planets"]
    return [
        e
        for planet in planets.values()
        for entities in planet["entities"].values()
        for e in entities
        if e["entityType"] == "token"
    ]


def test_custodian_token_appears_on_mecatol_after_placement(client: TestClient) -> None:
    client.post("/game/new", json=PLAYERS)
    assert _mecatol_tokens(_web(client)) == []
    assert _web(client)["gameState"]["setup"]["stage"] == "SECRETS"
    for pid in ("p1", "p2"):
        card = _state(client)["players"][pid]["private"]["secret_candidates"][0]
        client.post("/setup/secret", json={"player_id": pid, "objective_id": card})
    client.post("/setup/custodians", json={"player_id": "p1"})
    tokens = _mecatol_tokens(_web(client))
    assert [t["entityId"] for t in tokens] == ["custodian"]


def test_setup_payload_hides_other_players_candidates(client: TestClient) -> None:
    client.post("/game/new", json=PLAYERS)
    setup = _web(client)["gameState"]["setup"]
    state = _state(client)
    assert setup["chooserId"] == "p1"
    assert setup["candidates"] == state["players"]["p1"]["private"]["secret_candidates"]
    assert [p["id"] for p in setup["players"]] == ["p1", "p2"]


def test_skip_setup_randomizes_secrets_places_custodians_and_reveals(
    client: TestClient,
) -> None:
    client.post("/game/new", json=PLAYERS)
    assert client.post("/setup/skip").status_code == 200
    state = _state(client)
    assert state["setup"] is None
    for player in state["players"].values():
        assert len(player["private"]["secret_objectives"]) == 1
        assert player["private"]["secret_candidates"] == []
    assert len(state["objectives"]["revealed"]) == 2
    # Po domkniętym setupu skip nie ma już czego pomijać.
    assert client.post("/setup/skip").status_code == 422
