"""Sterownik testowy: partia samych botów „pasywnych” przez PRAWDZIWE API (plan B1).

W każdym kroku: dla graczy po kolei obserwacja → ``legal_actions`` → pierwsza akcja, którą
Sędzia przyjmie. Przyjętą akcję stosujemy DWA razy: przez katalog (``apply_action`` na kopii
stanu serwera) i przez HTTP (to samo żądanie co UI, nagłówek ``X-Actor-Id``) — i porównujemy
stany. Zapisujemy też, ile razy pierwszy kandydat był odrzucony (jakość generatora).

To NIE jest jeszcze runner bota (B3) ani arena (B4): sterownik żyje w testach.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.bot_http import request_for
from src.core.actor import ActorError
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.engine.actions import Action, EngineContext, apply_and_settle
from src.engine.legal import legal_actions
from src.engine.observation import observe

# Pola zmieniane przez commit serwera (zegar szachowy itp.), a nie przez regułę akcji.
_COMMIT_ONLY_FIELDS: frozenset[str] = frozenset()
# Przeskok zegara, gdy wszyscy czekają na koniec okna o stałej długości (RULES.md 54.11).
# Musi przekroczyć reaction_window_seconds (domyślnie 5 s) - 10 s z marginesem wystarczy.
_WAIT_SECONDS = 10.0

Policy = Callable[[list[Action]], list[Action]]
"""Kolejność prób kandydatów (domyślnie bez zmian = bot pasywny; fuzzer: losowo)."""
SeatOrder = Callable[[list[str]], list[str]]
"""Kolejność pytanych graczy (domyślnie kolejność miejsc; fuzzer: losowo, jak w sieci)."""
AfterStep = Callable[[Action], None]
"""Wywoływane po każdej przyjętej akcji (fuzzer: niezmienniki, web-data)."""


@dataclass
class Report:
    """Wynik przebiegu: kroki, rodzaje akcji, odrzucenia pierwszego kandydata, rozjazdy."""

    steps: int = 0
    kinds: Counter[str] = field(default_factory=Counter)
    first_rejected: Counter[str] = field(default_factory=Counter)
    rejections: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)
    stalled: str | None = None
    waits: int = 0


class BotTable:
    """Gra przez ``TestClient`` z samymi botami i sterowanym zegarem serwera."""

    def __init__(
        self,
        registry: StaticDataRegistry,
        factions: list[str],
        seed: int = 7,
        patch: dict[str, Any] | None = None,
        control: str = "BOT",
        policy: Policy | None = None,
        seat_order: SeatOrder | None = None,
        after_step: AfterStep | None = None,
        map_string: str | None = None,
    ) -> None:
        self.registry = registry
        self.policy: Policy = policy or (lambda candidates: candidates)
        self.seat_order: SeatOrder = seat_order or (lambda seats: seats)
        self.after_step = after_step
        self.clock = [1_000_000.0]
        self.app = create_app(
            registry=registry, store=EventStore(":memory:"), now=lambda: self.clock[0]
        )
        self.client = TestClient(self.app)
        # ``control="HUMAN"``: miejsca ludzi, za których gra sterownik (silnik nie decyduje za nich,
        # np. tajne cele w setupie) - pokrywa akcje, które za boty dziś rozstrzyga core.
        players = [
            {"faction_id": f, "control_type": control}
            | ({"difficulty": "EASY"} if control == "BOT" else {})
            for f in factions
        ]
        body: dict[str, Any] = {"players": players}
        if map_string is not None:
            body["map_string"] = map_string
        resp = self.client.post("/game/new", json=body)
        assert resp.status_code == 200, resp.text
        # Sytuacja startowa z God-Mode (np. zdjęty żeton Custodians => faza agendy).
        resp = self.client.post("/god-mode/patch", json={"rng_seed": seed, **(patch or {})})
        assert resp.status_code == 200, resp.text

    @property
    def state(self) -> GameState:
        return self.app.state.ctx.service.current_state()  # type: ignore[no-any-return]

    def ctx(self) -> EngineContext:
        app_ctx = self.app.state.ctx
        return EngineContext(
            registry=app_ctx.registry, grid=app_ctx.current_grid, now=self.clock[0]
        )

    def _post(self, action: Action) -> Any:
        path, body = request_for(action)
        headers = {"X-Actor-Id": action.player_id}
        if body is None:
            return self.client.post(path, headers=headers)
        return self.client.post(path, json=body, headers=headers)

    def step(self, report: Report) -> bool:
        """Jeden ruch pierwszego gracza (kolejność miejsc), który ma coś do zrobienia."""
        state = self.state
        ctx = self.ctx()
        for pid in self.seat_order(list(state.seating_order)):
            candidates = legal_actions(observe(state, ctx, pid), ctx)
            if candidates:
                # Indeks 0 = ruch domyślny generatora (statystyka first_rejected).
                default = candidates[0]
                candidates = self.policy(candidates)
            for action in candidates:
                try:
                    expected = apply_and_settle(state, ctx, action)
                except (ValueError, ActorError) as exc:
                    if action is default:
                        report.first_rejected[action.kind] += 1
                    report.rejections.append(f"{action.kind}: {exc}")
                    continue
                resp = self._post(action)
                if resp.status_code != 200:
                    report.mismatches.append(
                        f"{action.kind}: core OK, HTTP {resp.status_code} {resp.text[:200]}"
                    )
                    return False
                self._compare(action, expected, report)
                report.steps += 1
                report.kinds[action.kind] += 1
                if self.after_step is not None:
                    self.after_step(action)
                return True
        return False

    def _compare(self, action: Action, expected: GameState, report: Report) -> None:
        actual = self.state.model_dump(mode="json")
        wanted = expected.model_dump(mode="json")
        diff = sorted(
            key for key in set(actual) | set(wanted)
            if key not in _COMMIT_ONLY_FIELDS and actual.get(key) != wanted.get(key)
        )
        if diff:
            report.mismatches.append(f"{action.kind}: fields differ {diff}")

    def inject(self, state: GameState) -> None:
        """Podmienia stan serwera (sytuacja testowa ułożona w ``core``, jak God-Mode)."""
        self.app.state.ctx.service.replace_state(state, label="replace")

    def check(self, action: Action) -> list[str]:
        """Jedna akcja: katalog vs HTTP na bieżącym stanie; zwraca rozjazdy (pusta = zgodnie)."""
        report = Report()
        expected = apply_and_settle(self.state, self.ctx(), action)
        resp = self._post(action)
        if resp.status_code != 200:
            return [f"{action.kind}: core OK, HTTP {resp.status_code} {resp.text[:200]}"]
        self._compare(action, expected, report)
        return report.mismatches

    def run(
        self,
        *,
        until_round: int,
        max_steps: int = 2000,
        stop: Callable[[GameState], bool] | None = None,
    ) -> Report:
        """Gra do początku rundy ``until_round`` / warunku ``stop`` (albo końca, zawieszenia)."""
        report = Report()
        for _ in range(max_steps):
            state = self.state
            if state.round_number >= until_round or state.winner_id is not None:
                return report
            if stop is not None and stop(state):
                return report
            if not self.step(report):
                if report.mismatches:
                    return report
                if state.reaction_pause is not None or state.held_play is not None:
                    # Okno o stałej długości: nikt nic nie robi - mija czas serwera.
                    self.clock[0] += _WAIT_SECONDS
                    report.waits += 1
                    continue
                report.stalled = (
                    f"round {state.round_number}, phase {state.phase}, "
                    f"active {state.active_player_id}, window {state.pending_window}, "
                    f"strategy {state.pending_strategy}, status {state.status}, "
                    f"agenda {state.agenda}, held {state.held_play}, "
                    f"last rejections {report.rejections[-5:]}"
                )
                return report
        report.stalled = f"max_steps {max_steps} reached"
        return report
