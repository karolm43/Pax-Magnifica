"""Fuzzer partii botów: setki losowych gier przez prawdziwe API, szukanie wysypek (plan B4/B5).

Każda partia: losowe frakcje (3-6 graczy z puli grywalnych), losowe ziarno, bot losowy (kandydaci
``legal_actions`` w losowej kolejności, losowa kolejność pytanych graczy - jak w sieci). Po KAŻDEJ
przyjętej akcji sprawdzamy:

- zgodność katalog vs HTTP (sterownik ``BotTable``),
- niezmienniki stanu (``check_invariants``),
- czy stan przechodzi przez JSON bez zmian (to samo, co zapis/odczyt i wysyłka do UI),
- czy dokument web-data, który czyta front, buduje się dla każdego gracza (HTTP 200).

Błąd = plik JSON w katalogu raportu: ziarno, frakcje, ostatnie akcje, traceback i migawka stanu
(do odtworzenia przez ``BotTable.inject`` albo God-Mode).

Uruchomienie ręczne (duża próba)::

    uv run python -m tests.engine.fuzz --games 300 --rounds 4
    uv run python -m tests.engine.fuzz --replay 1234   # jedna partia z ziarna

Mały zestaw w pytest: ``tests/engine/test_fuzz_games.py``.

Zakres: cały generator ruchów - szkielet rundy (strategia, karty strategii, pas, status, agenda,
okna) i B5: aktywacje, ruch z ładunkiem, produkcja, walka, Space Cannon, odwrót, inwazja,
eksploracja, karty akcji. Domyślnie frakcje zrobione (``--all-factions`` = wszystkie grywalne).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import traceback
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core import faction_support
from src.core.game_state import GameState, Phase
from src.core.registry import StaticDataRegistry
from src.engine.actions import Action
from tests.engine.driver import BotTable, Report

_HISTORY = 30


@dataclass
class GameResult:
    """Wynik jednej partii fuzzera."""

    seed: int
    factions: list[str]
    steps: int = 0
    rounds: int = 0
    kinds: Counter[str] = field(default_factory=Counter)
    failure: str | None = None
    failure_file: str | None = None
    seconds: float = 0.0


def playable_factions(registry: StaticDataRegistry) -> list[str]:
    """Frakcje z puli wyboru setupu (te same, co w kreatorze)."""
    return sorted(fid for fid, f in registry.factions.items() if f.is_playable)


def sample_factions(
    registry: StaticDataRegistry, rng: random.Random, count: int, *, implemented: bool = True
) -> list[str]:
    """``count`` frakcji, najwyżej jeden wariant z rodziny (Keleres) - jak wymaga setup.

    ``implemented=True`` = tylko frakcje zrobione (``core/faction_support``) - te testujemy.
    """
    families: dict[str, list[str]] = {}
    for fid in playable_factions(registry):
        if implemented and not faction_support.is_implemented(fid):
            continue
        family = registry.faction_family(registry.factions[fid])
        families.setdefault(family, []).append(fid)
    chosen = rng.sample(sorted(families), count)
    return [rng.choice(families[family]) for family in chosen]


def check_invariants(state: GameState) -> list[str]:
    """Własności, które muszą zachodzić w KAŻDYM stanie gry (naruszenie = błąd silnika)."""
    problems: list[str] = []
    for pid, p in state.players.items():
        for name in (
            "trade_goods",
            "commodities",
            "victory_points",
            "tactical_cc",
            "fleet_cc",
            "strategic_cc",
            "cc_reinf",
        ):
            value = getattr(p, name)
            if value < 0:
                problems.append(f"{pid}.{name} = {value} < 0")
        if p.commodity_value > 0 and p.commodities > p.commodity_value:
            problems.append(f"{pid}.commodities {p.commodities} > value {p.commodity_value}")
    if state.setup is None and state.phase == Phase.ACTION and state.active_player_id is None:
        problems.append("action phase without active player")
    if state.active_player_id is not None and state.active_player_id not in state.players:
        problems.append(f"active player {state.active_player_id!r} is not a player")
    dumped = state.model_dump(mode="json")
    again = GameState.model_validate(dumped).model_dump(mode="json")
    if again != dumped:
        diff = sorted(k for k in set(dumped) | set(again) if dumped.get(k) != again.get(k))
        problems.append(f"JSON round-trip changes fields {diff}")
    return problems


class _Probe:
    """Hook po kroku: niezmienniki + web-data dla każdego gracza; zapamiętuje historię akcji."""

    def __init__(self, table_ref: list[BotTable]) -> None:
        self.table_ref = table_ref
        self.history: deque[dict[str, Any]] = deque(maxlen=_HISTORY)

    def __call__(self, action: Action) -> None:
        table = self.table_ref[0]
        self.history.append(action.model_dump(mode="json"))
        state = table.state
        problems = check_invariants(state)
        for pid in state.players:
            resp = table.client.get(
                "/api/public/game/fuzz/web-data", params={"viewing_player": pid}
            )
            if resp.status_code != 200:
                problems.append(f"web-data[{pid}] HTTP {resp.status_code}: {resp.text[:300]}")
        if problems:
            raise AssertionError("; ".join(problems))


def run_game(
    registry: StaticDataRegistry,
    seed: int,
    *,
    rounds: int = 4,
    max_steps: int = 4000,
    out_dir: Path | None = None,
    factions: list[str] | None = None,
    all_factions: bool = False,
) -> GameResult:
    """Jedna losowa partia; każdy wyjątek/rozjazd/zawieszenie zapisuje się jako ``failure``."""
    rng = random.Random(seed)
    if factions is None:
        factions = sample_factions(
            registry, rng, rng.randint(3, 6), implemented=not all_factions
        )
    result = GameResult(seed=seed, factions=factions)
    started = time.perf_counter()
    table_ref: list[BotTable] = []
    probe = _Probe(table_ref)

    def policy(candidates: list[Action]) -> list[Action]:
        shuffled = list(candidates)
        rng.shuffle(shuffled)
        return shuffled

    def seats(order: list[str]) -> list[str]:
        rng.shuffle(order)
        return order

    report = Report()
    try:
        table = BotTable(
            registry,
            factions,
            seed=seed,
            patch={"custodians_removed": True} if rng.random() < 0.5 else None,
            policy=policy,
            seat_order=seats,
            after_step=probe,
        )
        table_ref.append(table)
        report = table.run(until_round=rounds, max_steps=max_steps)
        if report.mismatches:
            result.failure = "mismatch: " + " | ".join(report.mismatches[:3])
        elif report.stalled is not None:
            result.failure = "stalled: " + report.stalled
    except Exception as exc:  # noqa: BLE001 - fuzzer zbiera KAŻDĄ wysypkę
        result.failure = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
    result.steps = report.steps
    result.kinds = report.kinds
    if table_ref:
        result.rounds = table_ref[0].state.round_number
    result.seconds = time.perf_counter() - started
    if result.failure is not None and out_dir is not None:
        result.failure_file = str(_dump_failure(out_dir, result, probe, table_ref))
    return result


def _dump_failure(
    out_dir: Path, result: GameResult, probe: _Probe, table_ref: list[BotTable]
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"fuzz_seed{result.seed}.json"
    doc = {
        "seed": result.seed,
        "factions": result.factions,
        "steps": result.steps,
        "failure": result.failure,
        "last_actions": list(probe.history),
        "state": table_ref[0].state.model_dump(mode="json") if table_ref else None,
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def _signature(failure: str) -> str:
    """Grupowanie błędów: pierwsza linia bez liczb zmiennych (seed, id)."""
    first = failure.splitlines()[0]
    return first[:160]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fuzzer partii botów (losowe gry przez API).")
    parser.add_argument("--games", type=int, default=50)
    parser.add_argument("--seed", type=int, default=1, help="pierwsze ziarno (kolejne +1)")
    parser.add_argument("--rounds", type=int, default=4, help="gra do początku tej rundy")
    parser.add_argument("--replay", type=int, default=None, help="tylko partia z tym ziarnem")
    parser.add_argument("--out", type=Path, default=Path("fuzz_reports"))
    parser.add_argument(
        "--all-factions", action="store_true", help="wszystkie grywalne, nie tylko zrobione"
    )
    args = parser.parse_args(argv)

    registry = StaticDataRegistry()
    seeds = [args.replay] if args.replay is not None else range(args.seed, args.seed + args.games)
    failures: dict[str, list[GameResult]] = {}
    kinds: Counter[str] = Counter()
    total_steps = 0
    for seed in seeds:
        res = run_game(
            registry, seed, rounds=args.rounds, out_dir=args.out, all_factions=args.all_factions
        )
        kinds.update(res.kinds)
        total_steps += res.steps
        mark = "OK " if res.failure is None else "ERR"
        print(
            f"{mark} seed={seed:<6} players={len(res.factions)} round={res.rounds} "
            f"steps={res.steps:<5} {res.seconds:5.1f}s",
            flush=True,
        )
        if res.failure is not None:
            failures.setdefault(_signature(res.failure), []).append(res)
            if args.replay is not None:
                print(res.failure)

    failed = sum(map(len, failures.values()))
    print(f"\n{len(list(seeds))} games, {total_steps} steps, {failed} failed")
    print("action kinds:", dict(kinds.most_common()))
    for sig, items in sorted(failures.items(), key=lambda kv: -len(kv[1])):
        seeds_txt = ", ".join(str(r.seed) for r in items[:8])
        print(f"\n[{len(items)}x] {sig}\n   seeds: {seeds_txt}\n   file: {items[0].failure_file}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
