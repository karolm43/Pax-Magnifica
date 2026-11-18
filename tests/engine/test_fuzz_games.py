"""Mały zestaw fuzzera (``tests/engine/fuzz.py``): losowe partie botów nie wysypują się.

Duża próba poza pytest: ``uv run python -m tests.engine.fuzz --games 300``. Tu kilka stałych
ziaren (powtarzalnie). Luki znalezione fuzzerem mają osobne testy celowane
(``test_actions_parity``: produkcja z Construction, okno FLEET_POOL).
"""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.engine.driver import BotTable
from tests.engine.fuzz import check_invariants, playable_factions, run_game


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.mark.parametrize("seed", [1, 2, 11, 125])
def test_random_bots_game_survives(registry: StaticDataRegistry, seed: int) -> None:
    result = run_game(registry, seed, rounds=3)

    assert result.failure is None, result.failure
    assert result.rounds == 3


def test_fuzz_pool_is_the_setup_pool(registry: StaticDataRegistry) -> None:
    pool = playable_factions(registry)

    assert "sol" in pool
    assert "neutral" not in pool


def test_invariants_catch_negative_trade_goods(registry: StaticDataRegistry) -> None:
    table = BotTable(registry, ["sol", "hacan", "xxcha"])
    state = table.state.clone()
    pid = next(iter(state.players))
    assert check_invariants(state) == []

    state.players[pid].trade_goods = -1

    assert check_invariants(state) == [f"{pid}.trade_goods = -1 < 0"]
