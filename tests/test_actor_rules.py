"""Uprawnienia aktora (RULES.md 44.1a): ``core/actor`` + nagłówek ``X-Actor-Id`` w API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.actor import ACTOR_HEADER
from src.api.app import create_app
from src.core import actor as actor_rules
from src.core.actor import ActorError
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState
from src.core.registry import StaticDataRegistry


def _state() -> GameState:
    return GameState(
        round_number=2,
        phase=Phase.ACTION,
        active_player_id="p1",
        speaker_id="p2",
        players={
            "p1": PlayerState(player_id="p1", faction="arborec", color="green"),
            "p2": PlayerState(player_id="p2", faction="sol", color="blue"),
        },
    )


# --- core/actor -----------------------------------------------------------------------------


def test_trusted_mode_passes_everything() -> None:
    state = _state()
    actor_rules.require(state, None, [], "x")
    actor_rules.check(state, None, "p2", actor_rules.turn_player)
    assert actor_rules.subject(state, None, "p2") == "p2"


def test_subject_resolves_faction_and_defaults_to_actor() -> None:
    state = _state()
    assert actor_rules.subject(state, "p1", "arborec") == "arborec"
    assert actor_rules.subject(state, "p1", None) == "p1"
    with pytest.raises(ActorError):
        actor_rules.subject(state, "p1", "sol")


def test_require_rejects_outsider_and_empty_entitlement() -> None:
    state = _state()
    actor_rules.require(state, "p1", actor_rules.turn_player(state), "Turn")
    with pytest.raises(ActorError):
        actor_rules.require(state, "p2", actor_rules.turn_player(state), "Turn")
    with pytest.raises(ActorError):  # brak walki = nikt nie rzuca
        actor_rules.require(state, "p1", actor_rules.combat_sides(state), "Roll")
    with pytest.raises(ActorError):  # spoza stołu
        actor_rules.require_seated(state, "intruder")


def test_merge_claimed() -> None:
    assert actor_rules.merge_claimed(None, "p1") == "p1"
    assert actor_rules.merge_claimed("p1", None) == "p1"
    assert actor_rules.merge_claimed("p1", "p1") == "p1"
    with pytest.raises(ActorError):
        actor_rules.merge_claimed("p1", "p2")


def test_actor_error_is_not_a_rules_error() -> None:
    """``except ValueError`` w routerach nie może zamienić 403 na 422."""
    assert not issubclass(ActorError, ValueError)


# --- API: nagłówek X-Actor-Id ---------------------------------------------------------------


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=_state())
    return TestClient(app)


def test_no_header_keeps_local_behaviour(client: TestClient) -> None:
    assert client.post("/turn/pass").status_code == 200


def test_active_player_may_act(client: TestClient) -> None:
    assert client.post("/turn/pass", headers={ACTOR_HEADER: "p1"}).status_code == 200


def test_other_player_gets_403(client: TestClient) -> None:
    res = client.post("/turn/pass", headers={ACTOR_HEADER: "p2"})
    assert res.status_code == 403
    assert client.get("/state").json()["state"]["players"]["p1"]["passed"] is False


def test_body_cannot_impersonate_header(client: TestClient) -> None:
    res = client.post("/turn/pass", json={"player_id": "p1"}, headers={ACTOR_HEADER: "p2"})
    assert res.status_code == 403


def test_combat_endpoint_without_combat_is_403_for_any_actor(client: TestClient) -> None:
    assert client.post("/tactical/battle/roll", headers={ACTOR_HEADER: "p1"}).status_code == 403


def test_speaker_only_round(client: TestClient) -> None:
    assert client.post("/round/next", headers={ACTOR_HEADER: "p1"}).status_code == 403


def test_table_action_requires_seat(client: TestClient) -> None:
    assert client.post("/clock/pause", headers={ACTOR_HEADER: "intruder"}).status_code == 403


def test_body_actor_id_mismatch_is_403(client: TestClient) -> None:
    res = client.post(
        "/offers/decline", json={"actor_id": "p2", "offer_id": "x"}, headers={ACTOR_HEADER: "p1"}
    )
    assert res.status_code == 403


def test_host_endpoints_unaffected_by_header(client: TestClient) -> None:
    """God-Mode nie patrzy na aktora (tryb lokalny: operator = host; N1 — rola z tokenu)."""
    assert client.post("/undo", headers={ACTOR_HEADER: "p2"}).status_code == 200


# --- awaiting: na kogo czeka gra (RULES.md 44.5) --------------------------------------------


def test_awaiting_turn_player_by_default() -> None:
    assert actor_rules.awaiting(_state()) == [("p1", "turn")]


def test_awaiting_window_and_offer_come_first() -> None:
    from src.core.game_state import PendingOffer, TimingWindow, WindowType

    state = _state()
    state.pending_window = TimingWindow(window_type=next(iter(WindowType)), queue=["p2", "p1"])
    state.pending_offers = [
        PendingOffer(id="o1", player_id="p1", event="e", moment="m", hook_seq=0)
    ]
    assert actor_rules.awaiting(state) == [("p2", "secondary"), ("p1", "decide")]


def test_awaiting_speaker_when_nobody_has_turn() -> None:
    state = _state()
    state.active_player_id = None
    assert actor_rules.awaiting(state) == [("p2", "speaker")]


def test_awaiting_reason_follows_phase() -> None:
    """Faza statusu/agendy nie mówi „take a turn” (plan U5/Z13)."""
    from src.core.game_state import (
        AgendaPhaseState,
        AgendaStep,
        StatusPhaseState,
        StatusStep,
    )

    state = _state()
    state.phase = Phase.STATUS
    state.status = StatusPhaseState()
    assert actor_rules.awaiting(state) == [("p1", "score")]
    state.status = StatusPhaseState(step=StatusStep.REDISTRIBUTE, done=["p1"])
    assert actor_rules.awaiting(state) == [
        (pid, "redistribute") for pid in state.players if pid != "p1"
    ]
    state.phase = Phase.AGENDA
    state.status = None
    state.agenda = AgendaPhaseState(step=AgendaStep.VOTE, vote_order=["p2", "p1"])
    assert actor_rules.awaiting(state) == [("p2", "vote")]
    state.agenda = AgendaPhaseState(step=AgendaStep.REVEAL)
    assert actor_rules.awaiting(state) == [("p2", "speaker")]


def test_web_data_lists_awaiting(client: TestClient) -> None:
    doc = client.get("/api/public/game/local/web-data").json()
    assert doc["awaiting"][0]["playerId"] == "p1"
    assert doc["awaiting"][0]["reason"] == "turn"
