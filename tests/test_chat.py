"""Czat i szepty — RULES.md 47.6 (``core/chat.py``, ``api/routers/chat.py``).

Decyzja użytkownika 2026-11-17: czat przy stole z szeptem; treść szeptu widzą tylko nadawca
i adresat, pozostali widzą, ŻE ktoś do kogoś szepcze.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import chat
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState
from src.core.registry import StaticDataRegistry

PLAYERS = ["p1", "p2", "p3"]


def test_post_publiczna_i_szept() -> None:
    log = chat.post(chat.ChatLog(), PLAYERS, "p1", "  hello  ", now=10.0)
    log = chat.post(log, PLAYERS, "p1", "secret deal", now=11.0, to="p2")
    assert [m.seq for m in log.messages] == [1, 2]
    assert log.messages[0].text == "hello" and log.messages[0].to is None
    seen_by = {p: chat.visible(log, p, sees_everything=False) for p in PLAYERS}
    # Publiczna - wszyscy z treścią.
    assert all(v[0]["text"] == "hello" for v in seen_by.values())
    # Szept: treść u nadawcy i adresata, u trzeciego tylko fakt szeptu.
    assert seen_by["p1"][1]["text"] == seen_by["p2"][1]["text"] == "secret deal"
    third = seen_by["p3"][1]
    assert (third["whisper"], third["sender"], third["to"], third["text"]) == (
        True, "p1", "p2", None
    )
    assert chat.visible(log, None, sees_everything=True)[1]["text"] == "secret deal"


def test_post_walidacja() -> None:
    with pytest.raises(ValueError, match="empty"):
        chat.post(chat.ChatLog(), PLAYERS, "p1", "   ", now=0)
    with pytest.raises(ValueError, match="too long"):
        chat.post(chat.ChatLog(), PLAYERS, "p1", "x" * (chat.MAX_LENGTH + 1), now=0)
    with pytest.raises(ValueError, match="yourself"):
        chat.post(chat.ChatLog(), PLAYERS, "p1", "hi", now=0, to="p1")
    with pytest.raises(ValueError, match="Unknown"):
        chat.post(chat.ChatLog(), PLAYERS, "p9", "hi", now=0)


def test_dziennik_przycina_i_przezywa_json() -> None:
    log = chat.ChatLog()
    for i in range(chat.MAX_MESSAGES + 5):
        log = chat.post(log, PLAYERS, "p1", f"m{i}", now=float(i), to="p2" if i % 2 else None)
    assert len(log.messages) == chat.MAX_MESSAGES
    assert log.messages[-1].seq == chat.MAX_MESSAGES + 5
    assert chat.ChatLog.from_json(log.to_json()) == log
    assert chat.ChatLog.from_json("not json") == chat.ChatLog()


@pytest.fixture
def client() -> TestClient:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=PLAYERS,
        players={p: PlayerState(player_id=p, color=c) for p, c in zip(
            PLAYERS, ("red", "blue", "green"), strict=True
        )},
    )
    app = create_app(
        registry=StaticDataRegistry(), store=EventStore(":memory:"), initial_state=state,
        now=lambda: 123.0,
    )
    return TestClient(app)


def test_endpoint_szept_i_undo_nie_kasuje(client: TestClient) -> None:
    body = {"player_id": "p1", "text": "psst", "to": "p3"}
    assert client.post("/chat/send", json=body).status_code == 200
    assert client.post("/chat/send", json={"player_id": "p2", "text": "hi all"}).status_code == 200
    seen = client.get("/chat?player=p2").json()["messages"]
    assert [(m["sender"], m["to"], m["text"]) for m in seen] == [
        ("p1", "p3", None), ("p2", None, "hi all")
    ]
    assert client.get("/chat?player=p3").json()["messages"][0]["text"] == "psst"
    assert seen[0]["at"] == 123.0
    # Aktor musi być nadawcą; pusta wiadomość -> 422.
    spoof = client.post(
        "/chat/send", json={"player_id": "p1", "text": "x"}, headers={"X-Actor-Id": "p2"}
    )
    assert spoof.status_code in (403, 422)
    assert client.post("/chat/send", json={"player_id": "p1", "text": " "}).status_code == 422
    # Czat nie jest stanem gry: zmiana stanu i Undo nie ruszają dziennika.
    client.post("/turn/pass")
    client.post("/undo")
    assert len(client.get("/chat?player=p2").json()["messages"]) == 2
