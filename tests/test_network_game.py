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
REMOTE = {"X-Forwarded-For": "10.147.17.5"}  # gracz z innego komputera (np. ZeroTier) przez proxy


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
    assert client.get("/state", headers=REMOTE).status_code == 401
    assert client.post("/turn/pass", headers=REMOTE).status_code == 401
    me = client.get("/network/me", headers=REMOTE).json()
    assert me["network"] is True and me["authenticated"] is False and me["host"] is False
    assert client.get("/state", headers={**_as("forged"), **REMOTE}).status_code == 401


def test_host_computer_needs_no_token(client: TestClient) -> None:
    me = client.get("/network/me").json()  # klient testów = ten komputer
    assert me["host"] is True and me["authenticated"] is True


def test_me_reports_seat(client: TestClient) -> None:
    token = _tokens(client)["p2"]
    me = client.get("/network/me", headers=_as(token)).json()
    assert (me["authenticated"], me["player_id"], me["host"]) == (True, "p2", False)


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
    assert client.get("/state", headers={**_as(old), **REMOTE}).status_code == 401
    assert client.get("/state", headers=_as(_tokens(client)["p2"])).status_code == 200


def test_websocket_requires_token_and_sends_own_projection(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws", headers=REMOTE) as ws:
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


# --- Lobby (RULES.md 44.6) ------------------------------------------------------------------


def test_closed_lobby_blocks_other_computers(registry: StaticDataRegistry) -> None:
    local = TestClient(create_app(registry=registry, store=EventStore(":memory:")))
    assert local.get("/state", headers=REMOTE).status_code == 403
    assert local.post("/lobby/join", json={"name": "Ania"}, headers=REMOTE).status_code == 403
    assert local.get("/factions", headers=REMOTE).status_code == 200  # dane statyczne jawne
    assert local.get("/state").status_code == 200  # ten komputer jak dotąd


def test_lobby_join_assign_and_play(registry: StaticDataRegistry) -> None:
    client = TestClient(create_app(registry=registry, store=EventStore(":memory:")))
    assert client.post("/lobby/open").json()["open"] is True
    joined = client.post("/lobby/join", json={"name": "  Ania  "}, headers=REMOTE).json()
    assert joined["name"] == "Ania"
    ania = {SEAT_TOKEN_HEADER: joined["token"], **REMOTE}
    lobby = client.get("/lobby", headers=ania).json()
    assert [m["name"] for m in lobby["members"]] == ["Ania"]
    assert lobby["addresses"] == []  # adresy hosta widzi tylko host
    assert client.get("/state", headers=ania).status_code == 200  # członek lobby, bez miejsca
    assert client.post("/turn/pass", headers=ania).status_code == 403  # nie siedzi przy stole

    players = [{"faction_id": "sol"}, {"faction_id": "arborec"}]
    assert client.post("/game/new", json={"players": players}).status_code == 200
    res = client.post(
        "/lobby/assign", json={"assignments": {"p1": "host", "p2": joined["member_id"]}}
    )
    assert res.status_code == 200, res.text
    assert res.json()["members"][0]["player_id"] == "p2"
    me = client.get("/network/me", headers=ania).json()
    assert me["player_id"] == "p2" and me["name"] == "Ania"
    host_me = client.get("/network/me").json()
    assert host_me["player_id"] == "p1" and host_me["host"] is True
    # Host siedzi jako p1 — widzi tylko swoją rękę; Ania nie może God-Mode.
    assert client.post("/undo", headers=ania).status_code == 403


def test_kicked_member_loses_access(registry: StaticDataRegistry) -> None:
    client = TestClient(create_app(registry=registry, store=EventStore(":memory:")))
    client.post("/lobby/open")
    joined = client.post("/lobby/join", json={"name": "Bartek"}, headers=REMOTE).json()
    client.post(f"/lobby/kick/{joined['member_id']}")
    res = client.get("/state", headers={SEAT_TOKEN_HEADER: joined["token"], **REMOTE})
    assert res.status_code == 401


def test_only_host_manages_lobby(registry: StaticDataRegistry) -> None:
    client = TestClient(create_app(registry=registry, store=EventStore(":memory:")))
    client.post("/lobby/open")
    joined = client.post("/lobby/join", json={"name": "Ola"}, headers=REMOTE).json()
    ola = {SEAT_TOKEN_HEADER: joined["token"], **REMOTE}
    assert client.post("/lobby/close", headers=ola).status_code == 403
    assert client.get("/saves", headers=ola).status_code == 403
    assert client.post("/lobby/join", json={"name": " "}, headers=REMOTE).status_code == 422


# --- Wspólny szkic kreatora (lobby na żywo, RULES.md 44.5a) -------------------------------


def _slot(name: str, control: str = "HUMAN", **extra: object) -> dict[str, object]:
    base: dict[str, object] = {"name": name, "controlType": control, "factionId": ""}
    return {**base, "color": "", "seat": None, **extra}


def test_live_draft_guests_edit_only_own_slot(registry: StaticDataRegistry) -> None:
    client = TestClient(create_app(registry=registry, store=EventStore(":memory:")))
    client.post("/lobby/open", json={"reset": True})
    draft = {"slots": [_slot("Host"), _slot(""), _slot("", "BOT")], "mapString": "", "step": 0}
    res = client.put("/lobby/draft", json={"draft": draft})
    assert res.status_code == 200, res.text
    assert res.json()["draft"]["owners"] == ["host", None, None]

    joined = client.post("/lobby/join", json={"name": "Ania"}, headers=REMOTE).json()
    ania = {SEAT_TOKEN_HEADER: joined["token"], **REMOTE}
    view = client.get("/lobby", headers=ania).json()
    assert view["you"] == joined["member_id"]
    assert view["draft"]["owners"][1] == joined["member_id"]  # wolny slot człowieka
    assert view["draft"]["slots"][1]["name"] == "Ania"
    assert view["draft"]["ownerNames"][1] == "Ania"

    ok = client.patch("/lobby/draft", json={"slots": {"1": {"factionId": "sol"}}}, headers=ania)
    assert ok.status_code == 200, ok.text
    hacan = {"slots": {"0": {"factionId": "hacan"}}}
    other = client.patch("/lobby/draft", json=hacan, headers=ania)
    assert other.status_code == 403
    step = client.patch("/lobby/draft", json={"step": 2}, headers=ania)
    assert step.status_code == 403
    taken = client.patch("/lobby/draft", json={"slots": {"0": {"factionId": "sol"}}})
    assert taken.status_code == 422  # frakcja zajęta przez Anię
    host = client.patch("/lobby/draft", json={"step": 1, "slots": {"0": {"factionId": "hacan"}}})
    assert host.status_code == 200 and host.json()["draft"]["step"] == 1

    players = [{"faction_id": "hacan"}, {"faction_id": "sol"}, {"faction_id": "arborec"}]
    assert client.post("/game/new", json={"players": players}).status_code == 200
    assert client.post("/lobby/seat").status_code == 200
    assert client.get("/network/me", headers=ania).json()["player_id"] == "p2"
    assert client.get("/network/me").json()["player_id"] == "p1"
    assert client.get("/network/seats").json()["host_home"] == "p1"


def test_new_lobby_forgets_old_guests(registry: StaticDataRegistry) -> None:
    client = TestClient(create_app(registry=registry, store=EventStore(":memory:")))
    client.post("/lobby/open")
    joined = client.post("/lobby/join", json={"name": "Ola"}, headers=REMOTE).json()
    client.post("/lobby/open", json={"reset": True})
    res = client.get("/lobby", headers={SEAT_TOKEN_HEADER: joined["token"], **REMOTE})
    assert res.status_code == 200  # /lobby jest publiczne przy otwartym lobby…
    assert res.json()["members"] == []  # …ale Oli już w nim nie ma
