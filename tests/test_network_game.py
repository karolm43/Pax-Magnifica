"""Gra sieciowa N1+N2 (RULES.md 44.2, 44.3): tokeny, role, projekcja per klient, brak wycieków."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.api.actor import ACTOR_HEADER
from src.api.app import create_app
from src.api.seats import SEAT_TOKEN_HEADER
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState
from src.core.registry import StaticDataRegistry
from src.core.visibility import HIDDEN_CARD, project_strict

P2_SECRET = "zz_p2_private_card"
DECK_CARD = "zz_top_of_deck"
HOST = "host-token-for-tests"


def _state() -> GameState:
    state = GameState(
        round_number=2,
        phase=Phase.ACTION,
        active_player_id="p1",
        speaker_id="p1",
        rng_seed=12345,
        players={
            "p1": PlayerState(player_id="p1", faction="arborec", color="green"),
            "p2": PlayerState(player_id="p2", faction="sol", color="blue"),
        },
    )
    state.players["p1"].private.action_cards = ["zz_p1_card"]
    state.players["p2"].private.action_cards = [P2_SECRET]
    state.decks.action_card_deck = [DECK_CARD, "zz_second"]
    state.objectives.stage1_deck = ["zz_stage1"]
    return state


# --- core: projekcja ścisła -----------------------------------------------------------------


def test_project_strict_hides_hands_decks_and_seed() -> None:
    view = project_strict(_state(), "p1")
    assert view.players["p1"].private.action_cards == ["zz_p1_card"]
    assert view.players["p2"].private.action_cards == []
    assert view.players["p2"].hidden_card_counts["action_cards"] == 1
    assert view.decks.action_card_deck == [HIDDEN_CARD, HIDDEN_CARD]
    assert view.objectives.stage1_deck == [HIDDEN_CARD]
    assert view.rng_seed == 0


def test_project_strict_observer_sees_no_hand() -> None:
    view = project_strict(_state(), None)
    assert all(not p.private.action_cards for p in view.players.values())


# --- API ------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    app = create_app(
        registry=registry,
        store=EventStore(":memory:"),
        initial_state=_state(),
        network=True,
        host_token=HOST,
    )
    return TestClient(app)


def _tokens(client: TestClient) -> dict[str, str]:
    res = client.get("/network/seats", headers={SEAT_TOKEN_HEADER: HOST})
    assert res.status_code == 200
    return {s["player_id"]: s["token"] for s in res.json()["seats"]}


def _as(token: str) -> dict[str, str]:
    return {SEAT_TOKEN_HEADER: token}


def test_local_mode_is_unchanged(registry: StaticDataRegistry) -> None:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=_state())
    local = TestClient(app)
    assert local.get("/network/me").json()["network"] is False
    assert P2_SECRET in local.get("/state").text  # operator widzi wszystko, jak dotąd


def test_no_token_is_401_but_public_data_works(client: TestClient) -> None:
    assert client.get("/state").status_code == 401
    assert client.post("/turn/pass").status_code == 401
    assert client.get("/network/me").json() == {
        "network": True, "authenticated": False, "player_id": None, "host": False,
    }
    assert client.get("/state", headers=_as("forged")).status_code == 401


def test_me_reports_seat(client: TestClient) -> None:
    token = _tokens(client)["p2"]
    me = client.get("/network/me", headers=_as(token)).json()
    assert me == {"network": True, "authenticated": True, "player_id": "p2", "host": False}


@pytest.mark.parametrize(
    "path",
    [
        "/state",
        "/api/public/game/local/web-data",
        "/api/public/game/local/web-data?viewing_player=p2",
        "/api/game/local/hand?player=p2",
        "/offers",
        "/history",
        "/history/activity",
        "/api/public/game/local/events",
        "/exploration",
        "/strategy/cards",
        "/tactical/battle",
        "/thunders-edge",
    ],
)
def test_nothing_leaks_to_other_player(client: TestClient, path: str) -> None:
    token = _tokens(client)["p1"]
    res = client.get(path, headers=_as(token))
    assert res.status_code == 200, res.text
    assert P2_SECRET not in res.text
    assert DECK_CARD not in res.text
    assert "12345" not in res.text or path.startswith("/history")


def test_own_hand_is_visible(client: TestClient) -> None:
    token = _tokens(client)["p1"]
    assert "zz_p1_card" in client.get("/api/game/local/hand", headers=_as(token)).text


def test_private_get_for_other_player_is_403(client: TestClient) -> None:
    token = _tokens(client)["p1"]
    res = client.get("/action-card/playable?player_id=p2", headers=_as(token))
    assert res.status_code == 403


def test_action_response_is_projected(client: TestClient) -> None:
    token = _tokens(client)["p1"]
    res = client.post("/turn/pass", headers=_as(token))
    assert res.status_code == 200, res.text
    assert P2_SECRET not in res.text and DECK_CARD not in res.text


def test_actor_comes_from_token_not_header(client: TestClient) -> None:
    token = _tokens(client)["p2"]
    # p2 podaje się za aktywnego p1 nagłówkiem X-Actor-Id — w sieci nagłówek jest ignorowany.
    res = client.post("/turn/pass", headers={**_as(token), ACTOR_HEADER: "p1"})
    assert res.status_code == 403


def test_player_cannot_use_god_mode(client: TestClient) -> None:
    token = _tokens(client)["p1"]
    assert client.post("/undo", headers=_as(token)).status_code == 403
    assert client.get("/network/seats", headers=_as(token)).status_code == 403
    assert client.post("/undo", headers=_as(HOST)).status_code == 200


def test_host_operator_sees_all_until_seated(client: TestClient) -> None:
    assert P2_SECRET in client.get("/state", headers=_as(HOST)).text
    res = client.post("/network/host-seat", json={"player_id": "p1"}, headers=_as(HOST))
    assert res.status_code == 200
    assert P2_SECRET not in client.get("/state", headers=_as(HOST)).text
    me = client.get("/network/me", headers=_as(HOST)).json()
    assert me["player_id"] == "p1" and me["host"] is True


def test_rotate_invalidates_old_link(client: TestClient) -> None:
    old = _tokens(client)["p2"]
    client.post("/network/seats/p2/rotate", headers=_as(HOST))
    assert client.get("/state", headers=_as(old)).status_code == 401
    assert client.get("/state", headers=_as(_tokens(client)["p2"])).status_code == 200


def test_websocket_requires_token_and_sends_own_projection(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws") as ws:
        ws.receive_json()
    token = _tokens(client)["p1"]
    with client.websocket_connect(f"/ws?token={token}") as ws:
        first = ws.receive_json()
        players = first["state"]["players"]
        assert players["p1"]["private"]["action_cards"] == ["zz_p1_card"]
        assert players["p2"]["private"]["action_cards"] == []
        # Broadcast po akcji też idzie w projekcji tego połączenia.
        client.post("/turn/pass", headers=_as(token))
        pushed = ws.receive_json()
        assert P2_SECRET not in str(pushed)


def test_full_game_web_data_builds_for_every_seat(registry: StaticDataRegistry) -> None:
    """Prawdziwa gra (nowa gra przez API): web-data w projekcji ścisłej buduje się dla każdego
    miejsca i nie zawiera cudzych kart ani składu talii (zaślepki ``hidden``)."""
    client = TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), network=True, host_token=HOST)
    )
    players = [{"faction_id": "sol"}, {"faction_id": "arborec"}, {"faction_id": "hacan"}]
    assert client.post("/game/new", json={"players": players}, headers=_as(HOST)).status_code == 200
    full = client.get("/state", headers=_as(HOST)).json()["state"]
    tokens = _tokens(client)
    for pid, token in tokens.items():
        res = client.get("/api/public/game/local/web-data", headers=_as(token))
        assert res.status_code == 200, res.text
        state = client.get("/state", headers=_as(token)).json()["state"]
        for other, player in full["players"].items():
            if other == pid:
                continue
            for card in player["private"]["action_cards"] + player["private"]["secret_candidates"]:
                quoted = f"\"{card}\""
                assert quoted not in res.text, (pid, card)
                assert quoted not in client.get("/state", headers=_as(token)).text, (pid, card)
        deck = state["decks"]["action_card_deck"]
        assert deck and set(deck) == {HIDDEN_CARD}
        assert len(deck) == len(full["decks"]["action_card_deck"])
