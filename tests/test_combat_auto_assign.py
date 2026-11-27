"""Optional auto-assignment of combat hits - RULES.md 54.14."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.core import battle, board_graph, combat_auto_assign, reaction_prefs, reaction_window
from src.core.battle_units import CombatUnit
from src.core.game_state import ControlType, GameState
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from tests.test_reactions_combat import _assign_state, _can


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(scope="module")
def grid() -> HexGrid:
    g = HexGrid()
    g.place_system("000", "18", anomalies=set())
    for pos, sid in (("101", "20"), ("102", "21"), ("103", "22"), ("104", "23")):
        g.place_system(pos, sid, anomalies=set())
    g.build_edges()
    return g


@pytest.fixture(autouse=True)
def _bound_grid(grid: HexGrid) -> Iterator[None]:
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield
    board_graph.bind_grid_provider(previous)


def _unit(base_type: str, count: int, *, sustain: bool = False, damaged: int = 0) -> CombatUnit:
    return CombatUnit(
        base_type=base_type, unit_id=base_type, name=base_type, count=count, damaged=damaged,
        hits_on=7, base_hits_on=7, modifier=0, dice_per_unit=1, sustain=sustain,
        afb_hits_on=None, afb_dice=0,
    )


COSTS: dict[str, float | None] = {
    "fighter": 0.5, "infantry": 0.5, "destroyer": 1.0, "dreadnought": 4.0, "warsun": 12.0,
}


# --- the plan -----------------------------------------------------------------------------------


def test_sustain_policy_covers_with_sustain_only() -> None:
    units = [_unit("dreadnought", 2, sustain=True), _unit("fighter", 3)]
    plan = combat_auto_assign.suggest(units, COSTS, 2, 1, reaction_prefs.AUTO_HITS_SUSTAIN)
    assert plan == ({"dreadnought": 2}, {}, {})
    # A third hit would destroy something: the player decides.
    assert combat_auto_assign.suggest(units, COSTS, 3, 1, reaction_prefs.AUTO_HITS_SUSTAIN) is None


def test_cheap_policy_destroys_fodder_after_sustain() -> None:
    units = [_unit("dreadnought", 1, sustain=True), _unit("fighter", 3), _unit("destroyer", 2)]
    plan = combat_auto_assign.suggest(units, COSTS, 3, 1, reaction_prefs.AUTO_HITS_CHEAP)
    assert plan == ({"dreadnought": 1}, {"fighter": 2}, {})


def test_cheap_policy_never_destroys_valuable_ships() -> None:
    units = [_unit("fighter", 1), _unit("destroyer", 2)]
    assert combat_auto_assign.suggest(units, COSTS, 2, 1, reaction_prefs.AUTO_HITS_CHEAP) is None


def test_sustain_goes_to_the_most_expensive_first() -> None:
    units = [_unit("dreadnought", 1, sustain=True), _unit("warsun", 1, sustain=True)]
    plan = combat_auto_assign.suggest(units, COSTS, 1, 1, reaction_prefs.AUTO_HITS_SUSTAIN)
    assert plan == ({"warsun": 1}, {}, {})


def test_off_policy_and_no_hits_mean_no_plan() -> None:
    units = [_unit("dreadnought", 2, sustain=True)]
    assert combat_auto_assign.suggest(units, COSTS, 1, 1, reaction_prefs.AUTO_HITS_OFF) is None
    assert combat_auto_assign.suggest(units, COSTS, 0, 1, reaction_prefs.AUTO_HITS_SUSTAIN) is None


# --- through the normal assignment path ----------------------------------------------------------


def _responder(state: GameState) -> str:
    window = state.pending_window
    assert window is not None and window.current_responder is not None
    return window.current_responder


def _policy(state: GameState, pid: str, policy: str) -> None:
    state.players[pid].private.reaction_prefs.auto_hits = policy


def test_auto_assignment_fires_the_normal_sustain_windows(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    """The responder's hits are covered by SUSTAIN DAMAGE automatically; the opponent's Direct
    Hit then becomes playable exactly as after a manual assignment."""
    options: tuple[tuple[list[str], list[str]], ...] = ((["dh1"], []), ([], ["dh1"]))
    for hands in options:
        state = _assign_state(grid, registry, *hands)
        who = _responder(state)
        other = "p2" if who == "p1" else "p1"
        if not state.players[other].private.action_cards:
            continue  # this seed asks the holder of Direct Hit first
        _policy(state, who, reaction_prefs.AUTO_HITS_SUSTAIN)
        required = battle.required_hits(state, grid, registry, who)
        after = combat_auto_assign.settle(state, registry)
        assert after is not state
        combat = after.active_combat
        assert combat is not None and combat.pending_hits.get(who, 0) == 0
        sustained = sum(int(e["count"]) for e in combat.sustained_ships if e["player"] == who)
        assert sustained == required
        assert _can(after, registry, other, "dh1")
        return
    raise AssertionError("no seed asked the player without Direct Hit first")


def test_no_auto_assignment_with_a_playable_reaction(
    grid: HexGrid, registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _assign_state(grid, registry, [], [])
    who = _responder(state)
    _policy(state, who, reaction_prefs.AUTO_HITS_CHEAP)
    monkeypatch.setattr(reaction_window, "has_playable_reaction", lambda *_a, **_k: True)
    assert combat_auto_assign.settle(state, registry) is state


def test_no_auto_assignment_for_bots_or_off(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _assign_state(grid, registry, [], [])
    who = _responder(state)
    assert combat_auto_assign.settle(state, registry) is state  # default: off
    _policy(state, who, reaction_prefs.AUTO_HITS_SUSTAIN)
    state.players[who].control_type = ControlType.BOT
    assert combat_auto_assign.settle(state, registry) is state
