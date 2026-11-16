"""Wyzwalacz bota (B3) i infrastruktura obliczeń (B2): boty grają same przez prawdziwe API.

Runner wysyła ruch bota tym samym żądaniem HTTP co klient człowieka (wewnętrzne ASGI), więc
test sprawdza całą ścieżkę: obserwacja → ``legal_actions`` → algorytm → trasa → commit.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.bot_runner import BotRunner, asgi_post
from src.api.seats import BOT, SeatRegistry
from src.core.actor import awaiting
from src.core.event_store import EventStore
from src.core.game_state import ControlType, GameState
from src.core.registry import StaticDataRegistry
from src.engine import actions as act
from src.engine import compute
from src.engine.observation import Observation
from tests.engine.test_passive_games import FOUR, SIX

_WAIT_SECONDS = 60.0


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


# --- engine/compute -------------------------------------------------------------------------


def _request(algorithm: str, seed: int = 0, **extra: Any) -> compute.DecisionRequest:
    legal = tuple(act.TurnPass(player_id="p1") for _ in range(5))
    obs = Observation(player_id="p1", view=GameState())
    return compute.DecisionRequest(
        observation=obs, legal=legal, algorithm=algorithm, seed=seed, **extra
    )


def test_first_keeps_generator_order() -> None:
    assert compute.decide(_request("first")).order == (0, 1, 2, 3, 4)


def test_random_is_seeded() -> None:
    a = compute.decide(_request("random", seed=3)).order
    assert a == compute.decide(_request("random", seed=3)).order
    assert sorted(a) == [0, 1, 2, 3, 4]


def test_unknown_algorithm_falls_back_to_default_move() -> None:
    result = compute.Executor("inline").run(_request("no-such-algorithm"))
    assert result.fallback and result.index == 0


def test_process_executor_matches_inline_and_respects_deadline() -> None:
    executor = compute.Executor("process", workers=1)
    try:
        request = _request("random", seed=11, deadline_s=60.0)
        remote = asyncio.run(executor.run_async(request))
        assert remote.order == compute.decide(request).order and not remote.fallback
        late = asyncio.run(executor.run_async(_request("random", seed=11, deadline_s=0.0)))
        assert late.fallback  # termin minął => ruch domyślny, gra nie czeka
    finally:
        executor.close()


# --- tożsamość runnera w grze sieciowej ------------------------------------------------------


def test_bot_token_resolves_to_bot_identity_only_in_memory() -> None:
    seats = SeatRegistry(network=True)
    assert seats.resolve(seats.bot_token) is BOT
    assert seats.bot_token not in seats.to_json()


# --- runner ---------------------------------------------------------------------------------


def _bot_app(registry: StaticDataRegistry, clock: list[float]) -> tuple[FastAPI, BotRunner]:
    app = create_app(
        registry=registry, store=EventStore(":memory:"), now=lambda: clock[0], bots=True
    )
    runner: BotRunner = app.state.bot_runner
    runner.config = runner.config.model_copy(update={"move_delay_s": 0.0})
    return app, runner


async def _new_game(app: FastAPI, factions: list[str], controls: list[str]) -> None:
    players = [
        {"faction_id": f, "control_type": c} | ({"difficulty": "EASY"} if c == "BOT" else {})
        for f, c in zip(factions, controls, strict=True)
    ]
    status, raw = await asgi_post(app, "/game/new", {"players": players}, {})
    assert status == 200, raw
    status, raw = await asgi_post(app, "/god-mode/patch", {"rng_seed": 7}, {})
    assert status == 200, raw


def _state(app: FastAPI) -> GameState:
    return app.state.ctx.service.current_state()  # type: ignore[no-any-return]


async def _play(app: FastAPI, runner: BotRunner, clock: list[float], until_round: int) -> str:
    """Kroki runnera do rundy ``until_round``; zwraca powód zatrzymania."""
    for _ in range(3000):
        state = _state(app)
        if state.round_number >= until_round or state.winner_id is not None:
            return "done"
        if not await runner.step():
            if state.reaction_pause is not None or state.held_play is not None:
                clock[0] += _WAIT_SECONDS  # okno o stałej długości: mija czas serwera
                continue
            return f"idle: awaiting {awaiting(state)}"
    return "max steps"


def test_bots_play_full_rounds_by_themselves(registry: StaticDataRegistry) -> None:
    clock = [1_000_000.0]
    app, runner = _bot_app(registry, clock)

    async def scenario() -> str:
        await _new_game(app, SIX, ["BOT"] * len(SIX))
        return await _play(app, runner, clock, until_round=3)

    assert asyncio.run(scenario()) == "done"
    assert runner.moves > 0
    labels = [label for _seq, label, _cur in app.state.ctx.service.history_entries()]
    # Ruch bota = ta sama trasa co człowieka: etykiety routerów, nie „bot:*”.
    assert not any(label.startswith("bot:") for label in labels)


def test_bots_wait_for_the_human(registry: StaticDataRegistry) -> None:
    clock = [1_000_000.0]
    app, runner = _bot_app(registry, clock)

    async def scenario() -> str:
        await _new_game(app, FOUR, ["HUMAN", "BOT", "BOT", "BOT"])
        return await _play(app, runner, clock, until_round=3)

    reason = asyncio.run(scenario())
    assert reason.startswith("idle"), reason
    state = _state(app)
    humans = {pid for pid, p in state.players.items() if p.control_type is ControlType.HUMAN}
    assert {pid for pid, _ in awaiting(state)} & humans, reason


def test_runner_wakes_on_commit_inside_server(registry: StaticDataRegistry) -> None:
    """Pętla w lifespan serwera: po utworzeniu gry boty same przechodzą setup i fazę strategii."""
    clock = [1_000_000.0]
    app, runner = _bot_app(registry, clock)
    runner.tick_s = 0.05
    players = [{"faction_id": f, "control_type": "BOT", "difficulty": "EASY"} for f in FOUR]
    with TestClient(app) as client:
        assert client.post("/game/new", json={"players": players}).status_code == 200
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and runner.moves < 10:
            time.sleep(0.05)
    assert runner.moves >= 10
