"""Testy Leadership (RULES.md 30.7): wydawanie wpĹ‚ywu na ĹĽetony, primary i secondary."""

from __future__ import annotations

import pytest

from src.core import strategic_action
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.planet_stats import influence_of
from src.core.registry import StaticDataRegistry

# Planety o znanym, niezerowym wpĹ‚ywie wyliczamy z rejestru (zero hardkodowania liczb).
_PLANETS = ["jord", "arinam", "meer"]


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(registry: StaticDataRegistry) -> GameState:
    owners = {pid: "p1" for pid in _PLANETS}
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        systems={"101": SystemState(position="101", system_id="1", planet_owners=owners)},
        players={
            "p1": PlayerState(player_id="p1", color="red", strategy_cards=[1]),
            "p2": PlayerState(player_id="p2", color="green"),
        },
    )
    state.players["p2"].trade_goods = 4
    state.systems["102"] = SystemState(position="102", system_id="2", planet_owners={"lodor": "p2"})
    return state


def _influence(registry: StaticDataRegistry, state: GameState, pid: str) -> int:
    return influence_of(state, registry, pid)


def test_primary_without_spending_gives_three(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(registry), registry, "p1", 1)
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    assert state.pending_strategy is not None and state.pending_strategy.step == "distribute"
    assert state.pending_strategy.draft["gain"] == 3
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"tactical": 1, "fleet": 1, "strategic": 1}
    )
    p1 = state.players["p1"]
    assert (p1.tactical_cc, p1.fleet_cc, p1.strategic_cc, p1.cc_reinf) == (4, 4, 3, 5)


def test_primary_spend_influence_buys_extra_tokens(registry: StaticDataRegistry) -> None:
    base = _state(registry)
    total = sum(_influence(registry, base, p) for p in _PLANETS)
    bought = total // 3
    state = strategic_action.play_strategy_card(base, registry, "p1", 1)
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"planets": list(_PLANETS)}
    )
    assert state.pending_strategy is not None
    assert state.pending_strategy.draft["gain"] == min(3 + bought, 8)
    gain = state.pending_strategy.draft["gain"]
    state = strategic_action.submit_primary_step(state, registry, "p1", {"strategic": gain})
    p1 = state.players["p1"]
    assert set(_PLANETS) <= set(p1.exhausted_planets)
    assert p1.strategic_cc == 2 + gain


def test_primary_distribution_must_match_gain(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(registry), registry, "p1", 1)
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    with pytest.raises(ValueError, match="exactly 3"):
        strategic_action.submit_primary_step(state, registry, "p1", {"tactical": 2})


def test_primary_rejects_foreign_or_exhausted_planet(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(registry), registry, "p1", 1)
    with pytest.raises(ValueError, match="not yours"):
        strategic_action.submit_primary_step(state, registry, "p1", {"planets": ["lodor"]})
    state.players["p1"].exhausted_planets = ["jord"]
    with pytest.raises(ValueError, match="not yours or is already exhausted"):
        strategic_action.submit_primary_step(state, registry, "p1", {"planets": ["jord"]})


def test_primary_gain_capped_by_reinforcements(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].cc_reinf = 2
    state = strategic_action.play_strategy_card(state, registry, "p1", 1)
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    assert state.pending_strategy is not None
    assert state.pending_strategy.draft["gain"] == 2


def _open_secondary(registry: StaticDataRegistry) -> GameState:
    state = strategic_action.play_strategy_card(_state(registry), registry, "p1", 1)
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    return strategic_action.submit_primary_step(state, registry, "p1", {"tactical": 3})


def test_secondary_trade_goods_buy_tokens_without_strategy_token(
    registry: StaticDataRegistry,
) -> None:
    state = _open_secondary(registry)
    before = state.players["p2"]
    pool = before.strategic_cc
    state = strategic_action.resolve_secondary(
        state, registry, "p2", execute=True, payload={"trade_goods": 4, "fleet": 1}
    )
    p2 = state.players["p2"]
    assert p2.trade_goods == 0  # 4 TG = 4 wpĹ‚ywu â†’ 1 ĹĽeton (3), 1 przepada
    assert p2.fleet_cc == before.fleet_cc + 1
    assert p2.strategic_cc == pool  # Leadership nie wymaga ĹĽetonu strategicznego


def test_secondary_wrong_distribution_rejected(registry: StaticDataRegistry) -> None:
    state = _open_secondary(registry)
    with pytest.raises(ValueError, match="exactly 1"):
        strategic_action.resolve_secondary(
            state, registry, "p2", execute=True, payload={"trade_goods": 4}
        )
    # Stan wejĹ›ciowy nietkniÄ™ty (okno wciÄ…ĹĽ czeka na p2).
    assert state.pending_window is not None and state.pending_window.cursor == 0


def test_options_for_owner_and_responder(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(registry), registry, "p1", 1)
    prompt = strategic_action.step_options(state, registry, "p1")
    assert prompt is not None and prompt["kind"] == "primary"
    assert prompt["step"] == "spend_influence"
    assert set(prompt["options"]["planets"]) == set(_PLANETS)
    assert strategic_action.step_options(state, registry, "p2") is None
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    state = strategic_action.submit_primary_step(state, registry, "p1", {"tactical": 3})
    sec = strategic_action.step_options(state, registry, "p2")
    assert sec is not None and sec["kind"] == "secondary"
    assert sec["options"]["trade_goods"] == 4
    assert strategic_action.step_options(state, registry, "p1") is None

