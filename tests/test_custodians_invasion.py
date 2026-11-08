"""Testy żetonu Custodians w inwazji na Mecatol Rex (RULES.md 52, R_custodians_token)."""

from __future__ import annotations

import pytest

from src.core import custodians, invasion
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
    ObjectivesState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry

_MECATOL = "18"
_PLANET = "mr"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", _MECATOL, anomalies=set())
    grid.build_edges()
    return grid


def _state(*, trade_goods: int = 6, infantry: int = 2) -> GameState:
    system = SystemState(position="000", system_id=_MECATOL)
    system.space_units["p1"] = {"infantry": infantry} if infantry else {"cruiser": 1}
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=TacticalStep.INVASION,
        seating_order=["p1", "p2"],
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2")},
        systems={"000": system},
        objectives=ObjectivesState(custom_points={"custodians": 1}),
    )
    state.players["p1"].trade_goods = trade_goods
    return state


def _begin(state: GameState, registry: StaticDataRegistry) -> GameState:
    started = invasion.begin_invasion(state, _grid(), registry)
    assert started.invasion is not None
    assert started.invasion.phase is InvasionPhase.COMMIT
    return started


def test_cannot_land_on_mecatol_while_token_lies(registry: StaticDataRegistry) -> None:
    state = _begin(_state(), registry)
    with pytest.raises(ValueError, match="Custodians"):
        invasion.commit_ground_forces(state, registry, {_PLANET: {"infantry": 1}})


def test_claim_pays_six_influence_gives_vp_and_unlocks_landing(
    registry: StaticDataRegistry,
) -> None:
    state = _begin(_state(), registry)
    assert invasion.custodians_block_reason(state, registry) is None

    claimed = invasion.claim_custodians(state, registry, [], 6)
    assert claimed.custodians_removed is True
    assert claimed.players["p1"].victory_points == 1
    assert claimed.players["p1"].trade_goods == 0
    assert claimed.objectives.scored["custodians"] == ["p1"]
    assert custodians.on_board(claimed) is False
    assert claimed.invasion is not None and claimed.invasion.custodians_claimed

    landed = invasion.commit_ground_forces(claimed, registry, {_PLANET: {"infantry": 1}})
    assert landed.invasion is not None
    assert landed.invasion.committed == {_PLANET: {"infantry": 1}}


def test_claim_requires_six_influence(registry: StaticDataRegistry) -> None:
    state = _begin(_state(trade_goods=5), registry)
    with pytest.raises(ValueError, match="6 influence"):
        invasion.claim_custodians(state, registry, [], 5)


def test_claim_requires_ground_forces_in_orbit(registry: StaticDataRegistry) -> None:
    state = _state(infantry=0)
    # Bez sił naziemnych inwazja się nie otwiera, więc budujemy ją ręcznie.
    state.invasion = InvasionState(
        position="000", attacker="p1", phase=InvasionPhase.COMMIT
    )
    reason = invasion.custodians_block_reason(state, registry)
    assert reason is not None and "ground forces" in reason
    with pytest.raises(ValueError, match="ground forces"):
        invasion.claim_custodians(state, registry, [], 6)


def test_after_claim_must_commit_on_mecatol(registry: StaticDataRegistry) -> None:
    claimed = invasion.claim_custodians(_begin(_state(), registry), registry, [], 6)
    with pytest.raises(ValueError, match="Mecatol Rex"):
        invasion.advance(claimed, _grid(), registry)


def test_cannot_claim_after_landing_started_or_twice(registry: StaticDataRegistry) -> None:
    claimed = invasion.claim_custodians(_begin(_state(trade_goods=12), registry), registry, [], 6)
    with pytest.raises(ValueError, match="already been removed"):
        invasion.claim_custodians(claimed, registry, [], 6)
