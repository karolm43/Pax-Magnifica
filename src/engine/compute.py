"""Infrastruktura obliczeń bota (B2, RULES.md 65.4–65.6; plan ``docs/bot/PLAN.md`` §4).

Każdy algorytm to funkcja modułowa ``DecisionRequest -> DecisionResult`` zarejestrowana pod nazwą
(``register_algorithm``). Dane wejścia/wyjścia są picklable, więc ten sam algorytm działa w
procesie serwera (tryb ``inline`` — testy, arena) i w procesie roboczym (tryb ``process`` — gra
na żywo; serwer nie zamarza na czas liczenia).

Budżet: ``max_iterations`` (powtarzalny — testy, arena) i/lub ``deadline_s`` (gra na żywo).
Po przekroczeniu terminu ``Executor`` zwraca ruch domyślny (pierwszy kandydat z ``legal``).
Ziarno przychodzi z zewnątrz; ``random.Random(seed)`` jest jedynym źródłem losowości.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Callable
from concurrent.futures import Executor as _PoolExecutor
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Literal

from src.engine.actions import Action
from src.engine.observation import Observation


@dataclass(frozen=True)
class DecisionRequest:
    """Jedna decyzja jednego bota: obserwacja + kandydaci + algorytm i budżet."""

    observation: Observation
    legal: tuple[Action, ...]
    algorithm: str = "first"
    params: dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    state_seq: int | None = None
    max_iterations: int | None = None
    deadline_s: float | None = None


@dataclass(frozen=True)
class DecisionResult:
    """Wybrany ruch (indeks w ``request.legal``) + kolejność zapasowa i metryki."""

    order: tuple[int, ...]
    """Indeksy kandydatów od najlepszego; runner próbuje kolejnych, gdy Sędzia odrzuci ruch."""
    algorithm: str
    state_seq: int | None = None
    iterations: int = 0
    fallback: bool = False
    """``True`` = ruch domyślny (termin minął albo algorytm zawiódł)."""

    @property
    def index(self) -> int:
        return self.order[0]


Algorithm = Callable[[DecisionRequest], DecisionResult]

_ALGORITHMS: dict[str, Algorithm] = {}


def register_algorithm(name: str) -> Callable[[Algorithm], Algorithm]:
    """Dekorator: rejestruje funkcję modułową jako algorytm o nazwie ``name``."""

    def wrap(fn: Algorithm) -> Algorithm:
        if name in _ALGORITHMS:
            raise ValueError(f"Algorithm {name!r} is already registered.")
        _ALGORITHMS[name] = fn
        return fn

    return wrap


def algorithm_names() -> frozenset[str]:
    return frozenset(_ALGORITHMS)


def default_result(request: DecisionRequest) -> DecisionResult:
    """Ruch domyślny: kandydaci w kolejności generatora (pierwszy = bezpieczny, RULES.md 65.3)."""
    return DecisionResult(
        order=tuple(range(len(request.legal))),
        algorithm=request.algorithm,
        state_seq=request.state_seq,
        fallback=True,
    )


def decide(request: DecisionRequest) -> DecisionResult:
    """Uruchamia algorytm z żądania (funkcja modułowa - wysyłana do procesu roboczego)."""
    if not request.legal:
        raise ValueError("No legal actions to choose from.")
    fn = _ALGORITHMS.get(request.algorithm)
    if fn is None:
        raise ValueError(f"Unknown bot algorithm: {request.algorithm!r}.")
    return fn(request)


@register_algorithm("first")
def _first(request: DecisionRequest) -> DecisionResult:
    """Bot pasywny (B1): zawsze bezpieczny ruch domyślny generatora."""
    return DecisionResult(
        order=tuple(range(len(request.legal))),
        algorithm="first",
        state_seq=request.state_seq,
        iterations=1,
    )


@register_algorithm("random")
def _random(request: DecisionRequest) -> DecisionResult:
    """Losowy legalny kandydat (ziarno z żądania) - punkt odniesienia dla areny."""
    order = list(range(len(request.legal)))
    random.Random(request.seed).shuffle(order)
    return DecisionResult(
        order=tuple(order), algorithm="random", state_seq=request.state_seq, iterations=1
    )


class Executor:
    """Uruchamia decyzje: ``inline`` (w tym procesie) albo ``process`` (pula procesów roboczych).

    W trybie ``process`` wynik czeka najwyżej ``deadline_s`` z żądania; po terminie (albo przy
    wyjątku algorytmu) zwracany jest ruch domyślny - gra nigdy nie czeka na bota w nieskończoność.
    """

    def __init__(self, mode: Literal["inline", "process"] = "inline", workers: int = 1) -> None:
        self.mode = mode
        self._pool: _PoolExecutor | None = (
            ProcessPoolExecutor(max_workers=workers) if mode == "process" else None
        )

    def run(self, request: DecisionRequest) -> DecisionResult:
        """Decyzja synchroniczna (tryb inline: testy, arena)."""
        try:
            return decide(request)
        except Exception:  # algorytm zawiódł => ruch domyślny, gra toczy się dalej
            if not request.legal:
                raise
            return default_result(request)

    async def run_async(self, request: DecisionRequest) -> DecisionResult:
        """Decyzja bez blokowania pętli serwera (tryb process) z twardym terminem."""
        if self._pool is None:
            return self.run(request)
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(self._pool, decide, request)
        try:
            return await asyncio.wait_for(future, timeout=request.deadline_s)
        except Exception:  # termin minął albo proces roboczy zawiódł
            return default_result(request)

    def close(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None
