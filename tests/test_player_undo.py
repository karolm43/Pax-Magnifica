"""Undo gracza (RULES.md 44.7): cofnięcie własnego ostatniego kroku z zakazami."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.actor import ACTOR_HEADER
from src.api.app import create_app
from src.core import player_undo, reaction_prefs
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.player_undo import Step
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _base() -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", faction="sol", color="red"),
            "p2": PlayerState(player_id="p2", faction="arborec", color="blue"),
        },
        systems={"101": SystemState(position="101", system_id="20")},
    )


def _with_tg(state: GameState, pid: str, tg: int) -> GameState:
    new = state.clone()
    new.players[pid].trade_goods = tg
    return new


def test_wlasny_odwracalny_krok_mozna_cofnac() -> None:
    s0 = _base()
    s1 = _with_tg(s0, "p1", 3)
    chain = [Step(1, "initial", None, s0), Step(2, "tg:p1", "p1", s1)]
    target = player_undo.undo_target(chain, "p1")
    assert target.seq == 1 and target.undone_seq == 2
    restored, branch, label = player_undo.undo(chain, "p1")
    assert branch == 1 and restored.players["p1"].trade_goods == 0
    assert label.startswith("player-undo:p1:")


def test_cudzy_krok_kosci_tura_i_inny_gracz_blokuja() -> None:
    s0 = _base()
    s1 = _with_tg(s0, "p1", 3)
    assert player_undo.undo_target(
        [Step(1, "a", "p1", s0), Step(2, "b", "p2", s1)], "p1"
    ).reason == "Another player has acted since"
    rolled = s1.clone()
    rolled.rng_counter += 1
    assert player_undo.undo_target(
        [Step(1, "a", "p1", s0), Step(2, "b", "p1", rolled)], "p1"
    ).reason == "Dice were rolled"
    passed = s1.clone()
    passed.active_player_id = "p2"
    assert player_undo.undo_target(
        [Step(1, "a", "p1", s0), Step(2, "b", "p1", passed)], "p1"
    ).reason == "The turn has passed to another player"
    other = _with_tg(s1, "p2", 1)
    assert player_undo.undo_target(
        [Step(1, "a", "p1", s0), Step(2, "b", "p1", other)], "p1"
    ).reason == "It affected another player"
    assert player_undo.undo_target(
        [Step(1, "a", None, s0), Step(2, "god-mode-patch", "p1", s1)], "p1"
    ).seq is None


def test_kolejne_undo_przechodzi_przez_migawki_cofniec() -> None:
    s0 = _base()
    s1 = _with_tg(s0, "p1", 1)
    chain = [
        Step(1, "initial", None, s0),
        Step(2, "x", "p1", s1),
        Step(3, "player-undo:p1:y", "p1", s1),  # cofnięty krok s2
    ]
    assert player_undo.undo_target(chain, "p1").seq == 1
    # cudze Undo nie jest przezroczyste dla mnie
    chain[2] = Step(3, "player-undo:p2:y", "p2", s1)
    assert player_undo.undo_target(chain, "p1").seq is None


def test_migawka_obecnosci_innego_gracza_jest_przezroczysta() -> None:
    """Another player's "I'm back" (presence bookkeeping) is no game step: it neither blocks my
    undo nor is erased by it - presence is carried into the restored state like the clock."""
    s0 = _base()
    s1 = _with_tg(s0, "p1", 3)
    s2 = s1.clone()
    s2.players["p2"].private.reaction_prefs.responded = True
    s2.players["p2"].private.reaction_prefs.afk_strikes = 0
    s1.players["p2"].private.reaction_prefs.afk_strikes = 2
    s0.players["p2"].private.reaction_prefs.afk_strikes = 2
    chain = [
        Step(1, "initial", None, s0),
        Step(2, "tg:p1", "p1", s1),
        Step(3, reaction_prefs.PRESENCE_LABEL, "p2", s2),
    ]
    target = player_undo.undo_target(chain, "p1")
    assert target.seq == 1 and target.label == "tg:p1"
    restored, branch, _label = player_undo.undo(chain, "p1")
    assert branch == 1 and restored.players["p1"].trade_goods == 0
    prefs = restored.players["p2"].private.reaction_prefs
    assert prefs.responded and prefs.afk_strikes == 0


def _client(registry: StaticDataRegistry) -> TestClient:
    state = _base()
    state.players["p1"].tactical_cc = 3
    return TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    )


def _state(client: TestClient) -> dict[str, Any]:
    return dict(client.get("/state").json()["state"])


def test_endpoint_undo_mine_cofa_aktywacje_tylko_autorowi(registry: StaticDataRegistry) -> None:
    client = _client(registry)
    assert not client.get("/undo/mine", params={"player_id": "p1"}).json()["available"]
    res = client.post(
        "/tactical/activate", json={"position": "101"}, headers={ACTOR_HEADER: "p1"}
    )
    assert res.status_code == 200, res.text
    assert _state(client)["active_system"] == "101"
    assert not client.get("/undo/mine", params={"player_id": "p2"}).json()["available"]
    res = client.post("/undo/mine", json={"player_id": "p2"}, headers={ACTOR_HEADER: "p2"})
    assert res.status_code == 422
    mine = client.get("/undo/mine", params={"player_id": "p1"}).json()
    assert mine["available"], mine
    assert mine["label"] == "tactical:activate:101"
    # nagłówek i treść muszą się zgadzać
    res = client.post("/undo/mine", json={"player_id": "p1"}, headers={ACTOR_HEADER: "p2"})
    assert res.status_code == 403
    res = client.post("/undo/mine", json={"player_id": "p1"}, headers={ACTOR_HEADER: "p1"})
    assert res.status_code == 200, res.text
    state = _state(client)
    assert state["active_system"] is None
    assert state["players"]["p1"]["tactical_cc"] == 3
    feed = client.get("/history/activity").json()["entries"]
    assert feed[-1]["activity"]["action"] == "turn.undo"
    assert feed[-1]["activity"]["actor_id"] == "p1"
