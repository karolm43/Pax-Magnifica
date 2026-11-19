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
    ("window_type", "kind"),
    [
        (WindowType.SPACE_CANNON, "space_cannon_pass"),
        (WindowType.COMBAT_RETREAT, "battle_announce_retreat"),
        (WindowType.CAPACITY, "capacity_resolve"),
        # FLEET_POOL: test_actions_parity.test_fleet_pool_resolve_matches_http
    ],
)
def test_windows_offer_their_own_decision(
    registry: StaticDataRegistry, window_type: WindowType, kind: str
) -> None:
    """B5: okno ma własną decyzję core (pas Space Cannon / walka dalej / usunięcie nadwyżki)."""
    state = timing.open_window(_state(), window_type, ["p1"])
    ctx = act.EngineContext(registry=registry, grid=_grid())

    candidates = legal_actions(observe(state, ctx, "p1"), ctx)

    assert candidates and candidates[0].kind == kind


def test_research_offer_gain_mode_picks_available_tech() -> None:
    """Research Grant Reallocation (obowiązkowe „gain any 1 technology”): bot nie może odmówić."""
    from src.engine.legal import _minimal_params

    tree = [{"id": "neural", "status": "owned"}, {"id": "gravity", "status": "available"}]
    gain = [{"key": "research", "kind": "research", "research": {"gain": {}, "tree": tree}}]
    may = [{"key": "research", "kind": "research", "research": {"tree": tree}}]

    assert _minimal_params(gain) == {"research": {"tech": "gravity"}}
    assert _minimal_params(may) == {"research": {"tech": None}}


def test_research_payloads_pay_with_planets_then_trade_goods() -> None:
    """Bot bada technologię kartą Technology: zapłata planetami od najcenniejszej, reszta TG."""
    from src.engine.legal import research_payloads

    tree = [{"id": "nm", "status": "available"}, {"id": "gd", "status": "locked"}]
    options = {"tree": tree, "cost": 4, "planets": {"a": 1, "b": 2}, "trade_goods": 2,
               "trade_good_value": 1}
    assert research_payloads(options) == [{"tech": "nm", "planets": ["b", "a"], "trade_goods": 1}]
    assert research_payloads({**options, "trade_goods": 0}) == []  # nie stać
    assert research_payloads({**options, "cost": 0}) == [{"tech": "nm"}]  # primary za darmo


def test_technology_secondary_bot_researches(registry: StaticDataRegistry) -> None:
    """Okno secondary Technology: bot ma pas i warianty badania; wariant faktycznie bada."""
    from src.core.game_state import GameState, Phase, PlayerState, SystemState, TimingWindow
    from src.core.strategy_cards import technology as technology_card

    state = GameState(
        phase=Phase.ACTION, active_player_id="p1", seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="sol"),
            "p2": PlayerState(player_id="p2", color="blue", faction="sol", trade_goods=8),
        },
        systems={"102": SystemState(position="102", system_id="19")},
        rng_seed=7,
    )
    state.pending_window = TimingWindow(
        window_type=WindowType.STRATEGY_SECONDARY, queue=["p2"],
        context={"initiative": technology_card.INITIATIVE},
    )
    ctx = act.EngineContext(registry=registry, grid=_grid())

    candidates = legal_actions(observe(state, ctx, "p2"), ctx)

    assert candidates[0] == act.StrategySecondary(player_id="p2", execute=False)
    research = [a for a in candidates[1:] if isinstance(a, act.StrategySecondary)]
    assert research and all(a.execute and a.payload["trade_goods"] == 4 for a in research)
    choice = research[0]
    after = act.apply_action(state, ctx, choice)
    assert choice.payload["tech"] in after.players["p2"].technologies
    assert after.players["p2"].trade_goods == 4
