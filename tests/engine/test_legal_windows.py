"""Bot w oknach czasowych: każde okno rozstrzyga własna decyzja ``core``, nie ogólne „OK”.

Regresja: generator zwracał ogólne ``window_respond`` dla okien bez własnej gałęzi — w oknie
``COMBAT_ASSIGN_HITS`` bot pomijał przypisanie strat, a dopełnione okno zostawało otwarte.
"""

from __future__ import annotations

import pytest

from src.core import timing
from src.core.game_state import WindowType
from src.core.registry import StaticDataRegistry
from src.engine import actions as act
from src.engine.legal import legal_actions
from src.engine.observation import observe
from tests.test_battle import _grid, _rolled_with_hits, _state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def test_assign_hits_window_yields_battle_assign(registry: StaticDataRegistry) -> None:
    rolled = _rolled_with_hits(registry, {"p1": {"cruiser": 6}, "p2": {"cruiser": 6}})
    window = rolled.pending_window
    assert window is not None and window.window_type is WindowType.COMBAT_ASSIGN_HITS
    pid = window.current_responder
    assert pid is not None
    ctx = act.EngineContext(registry=registry, grid=_grid())

    candidates = legal_actions(observe(rolled, ctx, pid), ctx)

    assert candidates and all(a.kind == "battle_assign" for a in candidates)
    after = act.apply_action(rolled, ctx, candidates[0])
    assert after.active_combat is not None
    assert after.active_combat.pending_hits[pid] == 0


@pytest.mark.parametrize(
    "window_type",
    [
        WindowType.SPACE_CANNON,
        WindowType.COMBAT_RETREAT,
        WindowType.CAPACITY,
        WindowType.FLEET_POOL,
    ],
)
def test_windows_without_bot_action_yet_offer_nothing(
    registry: StaticDataRegistry, window_type: WindowType
) -> None:
    state = timing.open_window(_state(), window_type, ["p1"])
    ctx = act.EngineContext(registry=registry, grid=_grid())

    assert legal_actions(observe(state, ctx, "p1"), ctx) == []

