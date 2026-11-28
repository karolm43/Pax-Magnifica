"""Wyzwalacz bota (B3, RULES.md 65.7): boty grają same w procesie serwera.

Runner budzi się po każdym rozesłaniu stanu (``StateService.add_listener``) i co ``tick_s``
(okna o stałej długości kończą się z upływem czasu, nie z commitem). W kroku: dla botów w
kolejności miejsc obserwacja → ``legal_actions`` → decyzja algorytmu (``engine/compute``) →
ruch wysłany TYM SAMYM żądaniem HTTP co klient człowieka (``bot_http``), wewnętrznie przez ASGI.
Dzięki temu etykiety historii, Activity, middleware (hold-play, pauza reakcji) i broadcast są
identyczne jak dla człowieka.

Spójność (RULES.md 65.7): stan czytany i ruch wysyłany bez ``await`` po sprawdzeniu ``state_seq``.
Gdy w trakcie liczenia albo pauzy „dla oka” stan się zmienił (ruch człowieka, Undo), wynik
jest odrzucany i bot liczy od nowa. Odrzucony ruch (403/422) → kolejny kandydat z decyzji.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import time
import zlib
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from fastapi import FastAPI

from src.api.actor import ACTOR_HEADER
from src.api.bot_http import request_for
from src.api.context import AppContext
from src.api.seats import SEAT_TOKEN_HEADER
from src.core.actor import describe_wait_reasons, format_wait_reasons
from src.core.game_state import ControlType, GameState
from src.core.models import BotConfig
from src.engine.actions import Action, EngineContext
from src.engine.compute import DecisionRequest, Executor
from src.engine.legal import legal_actions
from src.engine.observation import observe

log = logging.getLogger(__name__)

Sleep = Callable[[float], Awaitable[None]]

# Bot actions that throw combat dice: paced per round (``BotConfig.combat_round_gap_s``).
_COMBAT_ROLL_KINDS = frozenset({"battle_roll", "battle_afb"})


def combat_roll_mark(state: GameState) -> tuple[str, str, int, bool] | None:
    """Which combat round a roll now belongs to: (kind, position, round, AFB) or ``None``."""
    combat = state.active_combat
    if combat is None:
        return None
    return (combat.kind, combat.position, combat.round, not combat.log)


async def asgi_post(
    app: FastAPI, path: str, body: Any, headers: dict[str, str]
) -> tuple[int, bytes]:
    """POST do własnej aplikacji w procesie (bez sieci i bez zależności klienta HTTP)."""
    payload = b"" if body is None else json.dumps(body).encode()
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    raw_headers.append((b"content-type", b"application/json"))
    raw_headers.append((b"content-length", str(len(payload)).encode()))
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
        "scheme": "http", "path": path, "raw_path": path.encode(), "query_string": b"",
        "root_path": "", "headers": raw_headers, "client": ("127.0.0.1", 0),
        "server": ("127.0.0.1", 0),
    }
    sent = False

    async def receive() -> dict[str, Any]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": payload, "more_body": False}

    status = 500
    chunks: list[bytes] = []

    async def send(message: MutableMapping[str, Any]) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = int(message["status"])
        elif message["type"] == "http.response.body":
            chunks.append(message.get("body", b""))

    await app(scope, receive, send)
    return status, b"".join(chunks)


def bot_ids(state: GameState) -> list[str]:
    """Miejsca botów w kolejności przy stole."""
    order = [pid for pid in state.seating_order if pid in state.players] or sorted(state.players)
    return [pid for pid in order if state.players[pid].control_type is ControlType.BOT]


class BotRunner:
    """Pętla botów jednej aplikacji (jedna gra na serwer)."""

    def __init__(
        self,
        app: FastAPI,
        ctx: AppContext,
        config: BotConfig,
        *,
        tick_s: float = 1.0,
        sleep: Sleep = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.app = app
        self.ctx = ctx
        self.config = config
        self.tick_s = tick_s
        self._sleep = sleep
        self._clock = clock
        # The combat round of the last bot combat roll and when it was posted (pacing).
        self._last_roll: tuple[tuple[str, str, int, bool], float] | None = None
        workers = config.workers or max(1, (os.cpu_count() or 2) - 1)
        self.executor = Executor(config.executor, workers=workers)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._wake: asyncio.Event | None = None
        self._task: asyncio.Task[None] | None = None
        # (state_seq, bot) z odrzuconymi wszystkimi kandydatami - nie próbujemy w kółko.
        self._stuck: set[tuple[int | None, str]] = set()
        # state_seq of the last reported stall (one warning per stuck state, not one per tick).
        self._stalled_seq: int | None = None
        self.moves = 0

    # --- Cykl życia -----------------------------------------------------------------------

    def notify(self) -> None:
        """Budzi pętlę (słuchacz ``StateService``; bezpieczne z dowolnego wątku)."""
        if self._loop is not None and self._wake is not None:
            self._loop.call_soon_threadsafe(self._wake.set)

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._wake = asyncio.Event()
        self._wake.set()  # partia wznowiona z zapisu może czekać na bota
        self._task = asyncio.create_task(self._run(), name="bot-runner")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self.executor.close()

    async def _run(self) -> None:
        assert self._wake is not None
        while True:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._wake.wait(), timeout=self.tick_s)
            self._wake.clear()
            try:
                while await self.step():
                    pass
            except Exception:  # błąd bota nie może zabić serwera; gra czeka na człowieka
                log.exception("Bot runner step failed; %s", self._waits())

    # --- Jeden ruch -----------------------------------------------------------------------

    async def step(self) -> bool:
        """Jeden ruch pierwszego bota, który ma coś do zrobienia; ``True`` = coś się zmieniło."""
        service = self.ctx.service
        state = service.current_state()
        seq = service.current_seq()
        bots = bot_ids(state)
        if not bots:
            return False
        ectx = EngineContext(
            registry=self.ctx.registry, grid=self.ctx.current_grid, now=service.now()
        )
        for pid in bots:
            if (seq, pid) in self._stuck:
                continue
            obs = observe(state, ectx, pid)
            legal = legal_actions(obs, ectx)
            if not legal:
                continue
            request = self._request(state, obs, legal, pid, seq)
            result = await self.executor.run_async(request)
            if result.fallback:
                log.warning(
                    "Bot %s: decision timed out or failed, using the default move; %s",
                    pid, self._waits(),
                )
            if self.config.move_delay_s > 0:
                await self._sleep(self.config.move_delay_s)
            await self._pace_combat_roll(state, legal[result.order[0]] if result.order else None)
            if service.current_seq() != seq:
                return True  # stan zmienił się w trakcie (człowiek, Undo) - liczymy od nowa
            for index in result.order:
                if await self._post(legal[index]):
                    self.moves += 1
                    return True
                if service.current_seq() != seq:
                    return True
            log.warning("Bot %s: every candidate rejected at seq %s; %s", pid, seq, self._waits())
            self._stuck.add((seq, pid))
        self._report_stall(state, seq, bots)
        return False

    async def _pace_combat_roll(self, state: GameState, action: Action | None) -> None:
        """Holds a bot's combat roll of a NEW round until the previous round had time on screen.

        Both sides of one round roll without waiting (each side rolls on its own); only the
        first roll of the next round waits ``combat_round_gap_s`` after the previous round's.
        """
        gap = self.config.combat_round_gap_s
        if action is None or action.kind not in _COMBAT_ROLL_KINDS:
            return
        mark = combat_roll_mark(state)
        if mark is None:
            return
        if self._last_roll is not None and self._last_roll[0] == mark:
            return  # the other side of the same round
        if gap > 0 and self._last_roll is not None and self._last_roll[0][:2] == mark[:2]:
            wait = gap - (self._clock() - self._last_roll[1])
            if wait > 0:
                await self._sleep(wait)
        self._last_roll = (mark, self._clock())

    def _waits(self) -> str:
        """Wait reasons for a log line; diagnostics must never break the runner."""
        try:
            return format_wait_reasons(self.ctx.service.current_state(), self.ctx.registry)
        except Exception as exc:  # noqa: BLE001
            return f"wait reasons unavailable ({exc!r})"

    def _report_stall(self, state: GameState, seq: int | None, bots: list[str]) -> None:
        """No bot moved although the game waits for bots only (no human, no timed window)."""
        if seq == self._stalled_seq or state.winner_id is not None:
            return
        if state.reaction_pause is not None or state.held_play is not None:
            return  # ends by itself when its time passes
        try:
            reasons = describe_wait_reasons(state, self.ctx.registry)
        except Exception:  # noqa: BLE001
            log.exception("Wait reasons failed at seq %s", seq)
            return
        if all(r.player_id in bots for r in reasons if r.blocking):
            self._stalled_seq = seq
            log.warning("Bot game stalled at seq %s; %s", seq, self._waits())

    def _request(
        self,
        state: GameState,
        obs: Any,
        legal: list[Action],
        pid: str,
        seq: int | None,
    ) -> DecisionRequest:
        player = state.players[pid]
        key = any(a.kind in self.config.key_decision_kinds for a in legal)
        return DecisionRequest(
            observation=obs,
            legal=tuple(legal),
            algorithm=self.config.algorithm_for(player.difficulty),
            seed=zlib.crc32(f"{seq}:{pid}".encode()),
            state_seq=seq,
            deadline_s=(
                self.config.key_decision_deadline_s if key else self.config.decision_deadline_s
            ),
        )

    async def _post(self, action: Action) -> bool:
        path, body = request_for(action)
        headers = {ACTOR_HEADER: action.player_id, SEAT_TOKEN_HEADER: self.ctx.seats.bot_token}
        status, raw = await asgi_post(self.app, path, body, headers)
        if status == 200:
            return True
        log.info("Bot %s: %s rejected (%s) %s", action.player_id, action.kind, status, raw[:200])
        return False
