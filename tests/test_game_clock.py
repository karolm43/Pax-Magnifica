"""Zegar szachowy graczy (RULES.md 58): rozliczanie czasu, dodatek, pauza, API i web-data."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import game_clock
from src.core.event_store import EventStore
from src.core.game_state import GameState, PlayerState, TimingWindow, WindowType
from src.core.registry import StaticDataRegistry
from tests.setup_helpers import finish_setup

MIN = 60_000


def _state(active: str = "p1") -> GameState:
    state = GameState(
        players={pid: PlayerState(player_id=pid) for pid in ("p1", "p2", "p3")},
        seating_order=["p1", "p2", "p3"],
        active_player_id=active,
    )
    return game_clock.configure(state, initial_ms=10 * MIN, increment_ms=5_000)


def _remaining(state: GameState, now: float) -> dict[str, int]:
    return {c.player_id: c.remaining_ms for c in game_clock.snapshot(state, now)}


# --- core -------------------------------------------------------------------


def test_disabled_clock_is_noop() -> None:
    state = GameState(players={"p1": PlayerState(player_id="p1")}, active_player_id="p1")
    game_clock.settle(state, 100.0)
    assert state.clock.running_since is None
    assert game_clock.snapshot(state, 200.0) == []


@pytest.mark.parametrize(
    ("initial", "increment"), [(0, 0), (-1, 0), (MIN, -1), (25 * 60 * MIN, 0)]
)
def test_configure_rejects_out_of_range(initial: int, increment: int) -> None:
    with pytest.raises(ValueError):
        game_clock.configure(GameState(), initial_ms=initial, increment_ms=increment)


def test_only_holder_loses_time_and_turn_counter_runs() -> None:
    state = game_clock.settle(_state(), 1000.0)
    assert state.clock.holder_id == "p1"
    snap = {c.player_id: c for c in game_clock.snapshot(state, 1030.0)}
    assert snap["p1"].remaining_ms == 10 * MIN - 30_000
    assert snap["p1"].turn_ms == 30_000 and snap["p1"].running
    assert snap["p2"].remaining_ms == 10 * MIN and snap["p2"].turn_ms == 0


def test_end_of_turn_charges_time_and_grants_increment() -> None:
    state = game_clock.settle(_state(), 1000.0)
    game_clock.settle(state, 1010.0)  # commit w trakcie tury: ten sam holder, licznik rośnie
    assert state.clock.holder_turn_ms == 10_000
    state.active_player_id = "p2"
    game_clock.settle(state, 1040.0)
    assert state.clock.holder_id == "p2" and state.clock.holder_turn_ms == 0
    assert _remaining(state, 1040.0)["p1"] == 10 * MIN - 40_000 + 5_000


def test_window_responder_holds_the_clock_without_increment() -> None:
    state = game_clock.settle(_state(), 1000.0)
    state.pending_window = TimingWindow(
        window_type=WindowType.STRATEGY_SECONDARY, queue=["p2", "p3"]
    )
    game_clock.settle(state, 1010.0)
    assert state.clock.holder_id == "p2"
    state.pending_window = None
    game_clock.settle(state, 1025.0)
    remaining = _remaining(state, 1025.0)
    # p1 zapłacił 10 s, p2 15 s; aktywny gracz się nie zmienił, więc bez dodatku.
    assert remaining["p1"] == 10 * MIN - 10_000
    assert remaining["p2"] == 10 * MIN - 15_000
    assert state.clock.holder_id == "p1" and state.clock.holder_turn_ms == 0


def test_turn_changes_during_setup_grant_no_increment() -> None:
    from src.core.game_state import SetupState

    state = _state()
    state.setup = SetupState()
    game_clock.settle(state, 1000.0)
    state.active_player_id = "p2"
    game_clock.settle(state, 1010.0)
    state.setup = None
    game_clock.settle(state, 1020.0)
    assert _remaining(state, 1020.0) == {pid: 10 * MIN for pid in ("p1", "p2", "p3")}
    assert state.clock.holder_id == "p2"


def test_game_end_stops_the_clock() -> None:
    state = game_clock.settle(_state(), 1000.0)
    state.winner_id = "p2"
    game_clock.settle(state, 1010.0)
    assert state.clock.holder_id is None and state.clock.running_since is None
    assert _remaining(state, 5000.0)["p1"] == 10 * MIN - 10_000


def test_pause_and_resume() -> None:
    state = game_clock.settle(_state(), 1000.0)
    paused = game_clock.pause(state, 1020.0)
    assert paused.clock.paused and state.clock.running_since == 1000.0  # wejście nietknięte
    assert _remaining(paused, 9999.0)["p1"] == 10 * MIN - 20_000
    with pytest.raises(ValueError):
        game_clock.pause(paused, 1030.0)
    resumed = game_clock.resume(paused, 2000.0)
    assert _remaining(resumed, 2005.0)["p1"] == 10 * MIN - 25_000
    with pytest.raises(ValueError):
        game_clock.resume(resumed, 2010.0)


def test_time_may_run_below_zero() -> None:
    state = game_clock.settle(_state(), 1000.0)
    assert _remaining(state, 1000.0 + 11 * 60)["p1"] == -MIN


# --- API --------------------------------------------------------------------


class _FakeTime:
    def __init__(self) -> None:
        self.value = 1_000_000.0

    def __call__(self) -> float:
        return self.value


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _client(registry: StaticDataRegistry, fake: _FakeTime) -> TestClient:
    return TestClient(create_app(registry=registry, store=EventStore(":memory:"), now=fake))


def _new_game(client: TestClient, clock: dict[str, int] | None) -> None:
    body: dict[str, Any] = {
        "players": [{"faction_id": "sol"}, {"faction_id": "hacan"}, {"faction_id": "arborec"}]
    }
    if clock is not None:
        body["chess_clock"] = clock
    assert client.post("/game/new", json=body).status_code == 200


def _web_clock(client: TestClient) -> Any:
    return client.get("/api/public/game/x/web-data").json()["chessClock"]


def test_game_without_clock_has_no_web_section(registry: StaticDataRegistry) -> None:
    client = _client(registry, _FakeTime())
    _new_game(client, None)
    assert _web_clock(client) is None
    assert client.post("/clock/pause").status_code == 422


def test_clock_runs_through_api(registry: StaticDataRegistry) -> None:
    fake = _FakeTime()
    client = _client(registry, fake)
    _new_game(client, {"total_minutes": 30, "increment_seconds": 10})
    # Setup startowy (wybory równoległe) nie zużywa niczyjego czasu.
    fake.value += 100
    view = _web_clock(client)
    assert view["holderId"] is None
    assert all(p["remainingMs"] == 30 * MIN for p in view["players"])

    finish_setup(client)
    fake.value += 42
    view = _web_clock(client)
    holder = view["holderId"]
    assert holder is not None
    row = next(p for p in view["players"] if p["playerId"] == holder)
    assert row["running"] and row["remainingMs"] == 30 * MIN - 42_000
    assert row["turnMs"] == 42_000

    assert client.post("/clock/pause").status_code == 200
    fake.value += 500
    view = _web_clock(client)
    assert view["paused"]
    row = next(p for p in view["players"] if p["playerId"] == holder)
    assert not row["running"] and row["remainingMs"] == 30 * MIN - 42_000
    assert client.post("/clock/resume").status_code == 200
    assert client.post("/clock/resume").status_code == 422


def test_new_game_rejects_bad_clock_config(registry: StaticDataRegistry) -> None:
    client = _client(registry, _FakeTime())
    resp = client.post(
        "/game/new",
        json={
            "players": [{"faction_id": "sol"}, {"faction_id": "hacan"}],
            "chess_clock": {"total_minutes": 0},
        },
    )
    assert resp.status_code == 422
