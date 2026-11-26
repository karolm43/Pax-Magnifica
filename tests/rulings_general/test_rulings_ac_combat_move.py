"""Action card rulings: combat and movement cards (``docs/rules_tirules/C_action_cards.md``).

Each test tags the points it checks with ``@ruling(...)`` (guard ``tests/test_ruling_coverage.py``).
Basic card behaviour is tested in ``tests/test_reactions_*.py`` and ``tests/test_action_cards*.py``;
this file reuses their fixtures. Rulings without a test have a status in
``tests/rulings_status.json``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    action_cards,
    active_effects,
    battle,
    board_graph,
    capacity,
    command_tokens,
    damage,
    invasion,
    movement,
    reaction_cards,
    rules_hooks,
    space_cannon,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    CombatStep,
    GameState,
    InvasionPhase,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.hooks.action_cards_board import ghost_ship_targets
from src.core.hooks.card_helpers import place_from_reinforcements
from src.core.invasion import BombardAssignment
from src.core.registry import StaticDataRegistry
from src.core.retreat import retreat_destinations
from tests.rulings import ruling
from tests.test_reactions_combat import (
    _afb_state,
    _assign_state,
    _can,
    _last_sustains,
    _start,
    _sustain_state,
)
from tests.test_reactions_combat import _bound_grid as _bound_grid  # noqa: F401 - autouse fixture
from tests.test_reactions_combat import _play as _play_combat
from tests.test_reactions_combat import _state as _combat_state
from tests.test_reactions_combat import grid as grid  # noqa: F401 - fixture
from tests.test_reactions_invasion import _PL1, _PL2, _seek
from tests.test_reactions_invasion import _grid as _inv_grid
from tests.test_reactions_invasion import _hand as _inv_hand
from tests.test_reactions_invasion import _play as _inv_play
from tests.test_reactions_invasion import _row as _inv_row
from tests.test_reactions_invasion import _state as _inv_state
from tests.test_reactions_tactical import ACTIVE as _TAC_ACTIVE
from tests.test_reactions_tactical import _capture_state
from tests.test_reactions_tactical import _grid as _tac_grid
from tests.test_reactions_tactical import _play as _tac_play
from tests.test_reactions_tactical import _playable as _tac_playable
from tests.test_reactions_tactical import _state as _tac_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _windows(state: GameState, event: GameEvent) -> list[reaction_cards.OpenWindow]:
    return [w for w in reaction_cards.open_windows(state) if w.event is event]


# ======================================================================================= Direct Hit


def _two_sustains(grid: HexGrid, registry: StaticDataRegistry, hand1: list[str]) -> GameState:
    """p2 cancels exactly 2 hits with SUSTAIN DAMAGE of two dreadnoughts; p1 still assigns."""
    for seed in range(1, 400):
        state = _start(
            _combat_state({"dreadnought": 5}, {"dreadnought": 5}, hand1=hand1, seed=seed),
            grid, registry,
        )
        state = battle.roll_round(state, grid, registry)
        combat = state.active_combat
        assert combat is not None
        if combat.pending_hits.get("p2") == 2 and combat.pending_hits.get("p1", 0) > 0:
            return battle.assign_combat_hits(
                state, grid, registry, "p2", sustain={"dreadnought": 2}, destroy={},
                destroy_damaged={},
            )
    raise AssertionError("no seed gave p2 exactly 2 hits")


@ruling("C_action_cards/direct-hit/1", "C_action_cards/direct-hit/2")
def test_direct_hit_once_per_sustained_ship(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _two_sustains(grid, registry, ["dh1", "dh2"])
    assert state.systems["000"].space_units["p2"]["dreadnought"] == 5
    assert _can(state, registry, "p1", "dh1") and _can(state, registry, "p1", "dh2")
    first = _play_combat(state, registry, "p1", "dh1", {"ship": "dreadnought"})
    assert _can(first, registry, "p1", "dh2")  # the second ship's SUSTAIN DAMAGE is still open
    second = _play_combat(first, registry, "p1", "dh2", {"ship": "dreadnought"})
    assert second.systems["000"].space_units["p2"]["dreadnought"] == 3
    assert damage.damaged_count(second.systems["000"], "space", "p2", "dreadnought") == 0


@ruling("C_action_cards/direct-hit/5")
def test_direct_hit_cannot_destroy_a_mech(grid: HexGrid, registry: StaticDataRegistry) -> None:
    """A mech's SUSTAIN DAMAGE in ground combat opens no Direct Hit (it is not a ship)."""
    for seed in range(1, 300):
        state = _start(
            _combat_state(
                {}, {}, hand1=["dh1"], ground=({"infantry": 4}, {"mech": 2}), seed=seed
            ),
            grid, registry, "pl",
        )
        state = battle.roll_round(state, grid, registry)
        combat = state.active_combat
        assert combat is not None
        if combat.step is CombatStep.ASSIGN and combat.pending_hits.get("p2", 0) >= 1:
            break
    else:
        raise AssertionError("no seed gave p2 a hit")
    sustained = battle.assign_combat_hits(
        state, grid, registry, "p2", sustain={"mech": 1},
        destroy={"mech": combat.pending_hits["p2"] - 1} if combat.pending_hits["p2"] > 1 else {},
        destroy_damaged={},
    )
    pl_units = sustained.systems["000"].planet_units["pl"]["p2"]
    assert pl_units.get("mech", 0) >= 1
    assert not _can(sustained, registry, "p1", "dh1")


# ========================================================================= Morale Boost / Fire Team


def _ground_with_morale(grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Ground combat: p1 played Morale Boost at the start of the round, then both rolled."""
    for seed in range(1, 300):
        state = _start(
            _combat_state(
                {}, {}, hand1=["mb1", "fire_team"], ground=({"infantry": 6}, {"infantry": 6}),
                seed=seed,
            ),
            grid, registry, "pl",
        )
        state = _play_combat(state, registry, "p1", "mb1")
        state = battle.roll_round(state, grid, registry)
        combat = state.active_combat
        assert combat is not None
        if combat.step is CombatStep.ASSIGN and all(
            combat.pending_hits.get(p, 0) > 0 for p in ("p1", "p2")
        ):
            return state
    raise AssertionError("no seed gave ground hits")


@ruling(
    "C_action_cards/morale-boost/1", "C_action_cards/fire-team/1",
)
def test_morale_boost_and_original_modifiers_apply_to_fire_team_reroll(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _ground_with_morale(grid, registry)
    combat = state.active_combat
    assert combat is not None
    assert all(int(entry["modifier"]) == 1 for entry in combat.rolls["p1"])
    dice = [f"{i}:{d}" for i, e in enumerate(combat.rolls["p1"]) for d in range(len(e["dice"]))]
    new = _play_combat(state, registry, "p1", "fire_team", {"dice": dice})
    after = new.active_combat
    assert after is not None
    for entry in after.rolls["p1"]:
        assert int(entry["modifier"]) == 1  # the +1 still applies to the rerolled dice
        expected = sum(1 for v in entry["dice"] if int(v) + 1 >= int(entry["hitsOn"]))
        assert int(entry["hits"]) == expected


@ruling("C_action_cards/morale-boost/2")
def test_second_morale_boost_cannot_be_played(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _start(
        _combat_state({"cruiser": 2}, {"cruiser": 2}, hand1=["mb1", "mb2"]), grid, registry
    )
    played = _play_combat(state, registry, "p1", "mb1")
    assert not _can(played, registry, "p1", "mb2")
    assert battle.side_units(played, grid, registry, "p1")[0].modifier == 1


@ruling("C_action_cards/morale-boost/3")
def test_morale_boost_does_not_change_afb_rolls(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _afb_state(grid, registry, [])
    plain = battle.resolve_afb(state, grid, registry)
    boosted = state.clone()
    active_effects.add_effect(boosted, "action_cards:mb1", Duration.COMBAT_ROUND, owner="p1")
    boosted = battle.resolve_afb(boosted, grid, registry)
    assert plain.active_combat is not None and boosted.active_combat is not None
    assert boosted.active_combat.log[0]["hits"] == plain.active_combat.log[0]["hits"]
    assert boosted.active_combat.log[0]["rolls"] == plain.active_combat.log[0]["rolls"]


# ============================================================================ Courageous to the End


def _courageous_state(
    grid: HexGrid, registry: StaticDataRegistry, p2: dict[str, int], seed: int = 1
) -> GameState:
    state = _start(
        _combat_state({"cruiser": 1}, p2, hand1=["courageous"], seed=seed), grid, registry
    )
    assert state.active_combat is not None
    state.active_combat.destroyed_ships = [{"player": "p1", "base_type": "cruiser", "hits_on": 7}]
    return state


@ruling("C_action_cards/courageous-to-the-end/1")
def test_courageous_ignores_combat_roll_modifiers(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    seen_unmodified_miss = False
    for seed in range(1, 60):
        state = _courageous_state(grid, registry, {"cruiser": 4}, seed)
        active_effects.add_effect(state, "action_cards:mb1", Duration.COMBAT_ROUND, owner="p1")
        new = _play_combat(state, registry, "p1", "courageous", {"ship": "cruiser"})
        assert new.table_roll is not None
        dice = [int(d) for d in new.table_roll["dice"]]
        hits = sum(1 for d in dice if d >= 7)  # no +1 from Morale Boost
        assert new.systems["000"].space_units["p2"].get("cruiser", 0) == 4 - hits
        seen_unmodified_miss |= 6 in dice  # a 6 would hit with +1 - it must not
        if seen_unmodified_miss:
            break
    assert seen_unmodified_miss


@ruling("C_action_cards/courageous-to-the-end/2")
def test_courageous_destroys_ships_sustain_damage_cannot_save(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _courageous_state(grid, registry, {"dreadnought": 3})
    assert state.active_combat is not None
    state.active_combat.destroyed_ships = [{"player": "p1", "base_type": "cruiser", "hits_on": 1}]
    new = _play_combat(state, registry, "p1", "courageous", {"ship": "cruiser"})
    assert new.systems["000"].space_units["p2"]["dreadnought"] == 1  # two destroyed outright
    assert damage.damaged_count(new.systems["000"], "space", "p2", "dreadnought") == 0


# ============================================================================= Reflective Shielding


@ruling("C_action_cards/reflective-shielding/1")
def test_reflective_hits_join_the_hits_of_the_roll(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _sustain_state(grid, registry, [], ["reflective"])
    combat = state.active_combat
    assert combat is not None
    from_roll = combat.pending_hits["p1"]
    new = _play_combat(state, registry, "p2", "reflective", {})
    assert new.active_combat is not None
    # One assignment covers the roll's hits plus the card's 2 hits.
    assert new.active_combat.pending_hits["p1"] == from_roll + 2
    assert battle.required_hits(new, grid, registry, "p1") == min(from_roll + 2, 5)


@ruling("C_action_cards/reflective-shielding/2")
def test_reflective_after_the_last_assignment_assigns_immediately(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _last_sustains(grid, registry, ["reflective"], [])
    played = _play_combat(state, registry, "p1", "reflective", {})
    window = played.pending_window
    assert window is not None and window.window_type is WindowType.COMBAT_ASSIGN_HITS
    assert window.queue == ["p2"]  # the opponent assigns the 2 hits right away
    assert played.active_combat is not None and played.active_combat.pending_hits["p2"] == 2


# ================================================================================ Emergency Repairs


@ruling("C_action_cards/emergency-repairs/1")
def test_emergency_repairs_at_start_of_first_round_repairs_earlier_damage(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _combat_state({"dreadnought": 2}, {"cruiser": 1}, hand1=["emergency"])
    damage.set_damaged(state.systems["000"], "space", "p1", "dreadnought", 2)  # earlier combat
    state = _start(state, grid, registry)
    assert state.active_combat is not None and state.active_combat.round == 1
    new = _play_combat(state, registry, "p1", "emergency")
    assert damage.damaged_count(new.systems["000"], "space", "p1", "dreadnought") == 0


@ruling("C_action_cards/emergency-repairs/2")
def test_emergency_repairs_at_end_of_last_round(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(
        _combat_state({"dreadnought": 2}, {"cruiser": 1}, hand1=["emergency"]), grid, registry
    )
    combat = state.active_combat
    assert combat is not None
    combat.step, combat.winner, combat.outcome = CombatStep.DONE, "p1", "winner"
    damage.set_damaged(state.systems["000"], "space", "p1", "dreadnought", 1)
    assert _windows(state, GameEvent.COMBAT_ROUND)[0].moment is Moment.END
    new = _play_combat(state, registry, "p1", "emergency")
    assert damage.damaged_count(new.systems["000"], "space", "p1", "dreadnought") == 0


@ruling("C_action_cards/emergency-repairs/3")
def test_emergency_repairs_cannot_answer_direct_hit(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _sustain_state(grid, registry, ["dh1"], ["emergency"])
    assert damage.damaged_count(state.systems["000"], "space", "p2", "dreadnought") > 0
    assert _can(state, registry, "p1", "dh1")
    assert not _can(state, registry, "p2", "emergency")  # not the start/end of a round


# ================================================================================= Intercept / Rout


@ruling("C_action_cards/intercept/1")
def test_intercepted_player_may_retreat_next_round(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _start(
        _combat_state(
            {"cruiser": 1}, {"cruiser": 1}, hand2=["intercept"],
            presence={"101": {"p1": {"destroyer": 1}}},
        ),
        grid, registry,
    )
    announced = battle.announce_retreat(state, grid, "p1", announce=True)
    blocked = _play_combat(announced, registry, "p2", "intercept")
    assert blocked.active_combat is not None and blocked.active_combat.retreating == []
    nxt = blocked.clone()
    assert nxt.active_combat is not None
    nxt.active_combat.round += 1
    nxt.active_combat.pending_hits = {}
    nxt.pending_window = None
    battle.begin_round_in_place(nxt, grid)
    assert nxt.active_combat is not None and nxt.active_combat.step is CombatStep.ANNOUNCE
    again = battle.announce_retreat(nxt, grid, "p1", announce=True)
    assert again.active_combat is not None and again.active_combat.retreating == ["p1"]


@ruling("C_action_cards/rout/1")
def test_rout_needs_an_eligible_retreat_system(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    trapped = _start(
        _combat_state({"cruiser": 1}, {"cruiser": 1}, hand2=["rout"]), grid, registry
    )
    assert not _can(trapped, registry, "p2", "rout")  # the attacker cannot announce a retreat
    with pytest.raises(ValueError):
        battle.announce_retreat(trapped, grid, "p1", announce=True)
    able = _start(
        _combat_state(
            {"cruiser": 1}, {"cruiser": 1}, hand2=["rout"],
            presence={"101": {"p1": {"destroyer": 1}}},
        ),
        grid, registry,
    )
    assert _can(able, registry, "p2", "rout")


# ================================================================================== Skilled Retreat


def _skilled(
    grid: HexGrid,
    registry: StaticDataRegistry,
    p1: dict[str, int],
    *,
    presence: dict[str, dict[str, dict[str, int]]] | None = None,
    hand1: list[str] | None = None,
    hand2: list[str] | None = None,
) -> GameState:
    return _start(
        _combat_state(
            p1, {"cruiser": 1}, hand1=hand1 or ["s_retreat1"], hand2=hand2, presence=presence
        ),
        grid, registry,
    )


@ruling("C_action_cards/skilled-retreat/1", "C_action_cards/skilled-retreat/2")
def test_skilled_retreat_is_no_retreat_and_ends_in_a_draw(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _skilled(grid, registry, {"cruiser": 2}, hand2=["intercept", "salvage"])
    new = _play_combat(state, registry, "p1", "s_retreat1", {"destination": "101"})
    combat = new.active_combat
    assert combat is not None and combat.outcome == "draw" and combat.winner is None
    assert combat.retreating == []
    assert not _windows(new, GameEvent.RETREAT_DECLARED)
    assert not _can(new, registry, "p2", "intercept")
    # No winner: no "after you win a combat" ability resolves (Salvage).
    assert not _windows(new, GameEvent.COMBAT_WON)
    new.players["p1"].commodities = 2
    assert not _can(new, registry, "p2", "salvage")


@ruling("C_action_cards/skilled-retreat/3", "C_action_cards/skilled-retreat/4")
def test_skilled_retreat_into_an_empty_system_with_ground_forces(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _skilled(grid, registry, {"carrier": 1, "infantry": 2})
    assert "p1" not in state.systems["101"].space_units
    new = _play_combat(state, registry, "p1", "s_retreat1", {"destination": "101"})
    assert new.systems["101"].space_units["p1"] == {"carrier": 1, "infantry": 2}


@ruling("C_action_cards/skilled-retreat/5", "C_action_cards/skilled-retreat/8")
def test_skilled_retreat_moves_every_ship_then_checks_capacity(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    # Carrier capacity 4; 4 fighters + 2 infantry = 6 - the player chooses what to remove.
    state = _skilled(grid, registry, {"carrier": 1, "fighter": 4, "infantry": 2})
    new = _play_combat(state, registry, "p1", "s_retreat1", {"destination": "101"})
    assert new.systems["000"].space_units.get("p1", {}) == {}
    assert new.systems["101"].space_units["p1"] == {"carrier": 1, "fighter": 4, "infantry": 2}
    window = new.pending_window
    assert window is not None and window.window_type is WindowType.CAPACITY
    assert window.queue == ["p1"] and window.context.get("position") == "101"
    assert capacity.players_with_excess(new, registry, "101") == ["p1"]
    # Fighters alone over capacity: no choice, the excess is removed at once in the destination.
    forced = _skilled(grid, registry, {"cruiser": 1, "fighter": 2})
    done = _play_combat(forced, registry, "p1", "s_retreat1", {"destination": "101"})
    assert done.systems["101"].space_units["p1"].get("fighter", 0) == 0
    assert done.systems["101"].space_units["p1"]["cruiser"] == 1


@ruling("C_action_cards/skilled-retreat/6")
def test_skilled_retreat_to_a_system_with_own_token_places_none(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _skilled(grid, registry, {"cruiser": 1})
    state.systems["101"].command_tokens = ["p1"]
    before = command_tokens.reinforcements(state, "p1")
    new = _play_combat(state, registry, "p1", "s_retreat1", {"destination": "101"})
    assert new.systems["101"].command_tokens == ["p1"]
    assert command_tokens.reinforcements(new, "p1") == before


@ruling("C_action_cards/skilled-retreat/7")
def test_skilled_retreat_takes_a_token_from_a_pool_when_reinforcements_are_empty(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _skilled(grid, registry, {"cruiser": 1})
    player = state.players["p1"]
    while command_tokens.reinforcements(state, "p1") > 0:
        command_tokens.take_from_reinforcements(state, "p1")
    pools = (player.tactical_cc, player.fleet_cc, player.strategic_cc)
    assert sum(pools) > 0
    assert _can(state, registry, "p1", "s_retreat1")
    new = _play_combat(state, registry, "p1", "s_retreat1", {"destination": "101"})
    assert "p1" in new.systems["101"].command_tokens
    after = new.players["p1"]
    assert sum((after.tactical_cc, after.fleet_cc, after.strategic_cc)) == sum(pools) - 1


# =========================================================================================== Waylay


@ruling("C_action_cards/waylay/1")
def test_waylay_hit_on_a_ship_can_be_cancelled_by_sustain_damage(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _afb_state(grid, registry, ["waylay"])
    played = _play_combat(state, registry, "p1", "waylay")
    resolved = battle.resolve_afb(played, grid, registry)
    combat = resolved.active_combat
    assert combat is not None and combat.afb_assign
    need = battle.required_hits(resolved, grid, registry, "p2")
    assert need >= 2
    sustain = min(need, 6)
    assigned = battle.assign_combat_hits(
        resolved, grid, registry, "p2", sustain={"dreadnought": sustain},
        destroy={"fighter": 1} if need > sustain else {}, destroy_damaged={},
    )
    assert assigned.systems["000"].space_units["p2"]["dreadnought"] == 6
    assert damage.damaged_count(assigned.systems["000"], "space", "p2", "dreadnought") == sustain


# ========================================================================== Space Cannon / invasion


@contextmanager
def _invasion_board() -> Iterator[HexGrid]:
    """Binds the two-planet invasion map (``tests/test_reactions_invasion``) for one test."""
    board = _inv_grid()
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: board)
    try:
        yield board
    finally:
        board_graph.bind_grid_provider(previous)


def _sc_hits(state: GameState) -> int:
    pending = space_cannon.pending_hits(state)
    return pending.hits if pending is not None else 0


def _sc_offense(seed: int, registry: StaticDataRegistry, p1_space: dict[str, int]) -> GameState:
    state = _inv_state(
        {"p1": p1_space}, {_PL1: {"p2": {"pds": 3}}}, {_PL1: "p2"},
        seed=seed, step=TacticalStep.SPACE_CANNON,
    )
    _inv_hand(state, "p1", "mjets1", "mjets2", "dh2")
    _inv_hand(state, "p2", "dh1")
    opened = space_cannon.open_offense(state, _inv_grid(), registry)
    return space_cannon.fire_offense(opened, _inv_grid(), registry, "p2", "p1")


@ruling("C_action_cards/direct-hit/4")
def test_direct_hit_outside_combat_removes_excess_cargo_at_once(
    registry: StaticDataRegistry,
) -> None:
    with _invasion_board():
        fired = _seek(
            lambda s: _sc_offense(s, registry, {"dreadnought": 1, "infantry": 1}),
            lambda st: _sc_hits(st) == 1,
        )
        sustained = space_cannon.assign_hits(
            fired, "p1", {}, sustain={"dreadnought": 1}, registry=registry
        )
        new = _inv_play(sustained, registry, "p2", "dh1", {"ship": "dreadnought"})
    # The dreadnought (capacity 1) is gone: its infantry cannot stay in space.
    assert new.systems["000"].space_units.get("p1", {}) == {}


@ruling("C_action_cards/maneuvering-jets/1", "C_action_cards/maneuvering-jets/3")
def test_maneuvering_jets_once_per_space_cannon_offense_roll(
    registry: StaticDataRegistry,
) -> None:
    with _invasion_board():
        fired = _seek(
            lambda s: _sc_offense(s, registry, {"destroyer": 4}), lambda st: _sc_hits(st) >= 2
        )
        hits = _sc_hits(fired)
        assert _inv_row(fired, registry, "p1", "mjets1")["playable"]
        once = _inv_play(fired, registry, "p1", "mjets1")
        assert _sc_hits(once) == hits - 1
        assert not _inv_row(once, registry, "p1", "mjets2")["playable"]  # same roll


def _three_player_offense(seed: int, registry: StaticDataRegistry) -> GameState:
    state = _inv_state(
        {"p1": {"destroyer": 6}},
        {_PL1: {"p2": {"pds": 3}}, _PL2: {"p3": {"pds": 3}}},
        {_PL1: "p2", _PL2: "p3"},
        seed=seed, step=TacticalStep.SPACE_CANNON,
    )
    state.players["p3"] = PlayerState(player_id="p3", color="p3")
    state.seating_order = ["p1", "p2", "p3"]
    _inv_hand(state, "p1", "mjets1", "mjets2")
    opened = space_cannon.open_offense(state, _inv_grid(), registry)
    return space_cannon.fire_offense(opened, _inv_grid(), registry, "p2", "p1")


@ruling("C_action_cards/maneuvering-jets/3.1")
def test_maneuvering_jets_once_after_each_players_offense_roll(
    registry: StaticDataRegistry,
) -> None:
    with _invasion_board():

        def p3_also_hits(st: GameState) -> bool:
            if _sc_hits(st) != 1:
                return False
            after = _inv_play(st, registry, "p1", "mjets1")
            nxt = space_cannon.fire_offense(after, _inv_grid(), registry, "p3", "p1")
            return _sc_hits(nxt) >= 1

        fired = _seek(lambda s: _three_player_offense(s, registry), p3_also_hits)
        after_p2 = _inv_play(fired, registry, "p1", "mjets1")
        assert _sc_hits(after_p2) == 0
        p3_fired = space_cannon.fire_offense(after_p2, _inv_grid(), registry, "p3", "p1")
        assert _sc_hits(p3_fired) >= 1
        assert _inv_row(p3_fired, registry, "p1", "mjets2")["playable"]  # a new roll
        p3_jets = _inv_play(p3_fired, registry, "p1", "mjets2")
        assert _sc_hits(p3_jets) == _sc_hits(p3_fired) - 1


def _defense(seed: int, registry: StaticDataRegistry, board: HexGrid) -> GameState:
    """SCD: p2 defends both planets with PDS; p1 committed infantry to both."""
    state = _inv_state(
        {"p1": {"infantry": 8}},
        {_PL1: {"p2": {"infantry": 1, "pds": 3}}, _PL2: {"p2": {"infantry": 1, "pds": 3}}},
        {_PL1: "p2", _PL2: "p2"},
        seed=seed,
    )
    _inv_hand(state, "p1", "mjets1", "mjets2", "mjets3")
    started = invasion.begin_invasion(state, board, registry)
    landed = invasion.commit_ground_forces(
        started, registry, {_PL1: {"infantry": 4}, _PL2: {"infantry": 4}}
    )
    entered = invasion.advance(landed, board, registry)
    assert entered.invasion is not None
    assert entered.invasion.phase is InvasionPhase.SPACE_CANNON_DEFENSE
    first = invasion.defense_fire(entered, board, registry, _PL1)
    return invasion.defense_fire(first, board, registry, _PL2)


def _def_hits(state: GameState, planet: str) -> int:
    return state.invasion.defense_pending.get(planet, 0) if state.invasion else 0


def _jets_planets(state: GameState, registry: StaticDataRegistry, card: str) -> list[str]:
    return sorted(
        str(w.ctx.get("planet"))
        for w in reaction_cards.matching_windows(state, registry, "p1", card)
    )


@ruling("C_action_cards/maneuvering-jets/1", "C_action_cards/maneuvering-jets/3.2")
def test_maneuvering_jets_once_per_planet_in_space_cannon_defense(
    registry: StaticDataRegistry,
) -> None:
    with _invasion_board() as board:
        fired = _seek(
            lambda s: _defense(s, registry, board),
            lambda st: _def_hits(st, _PL1) >= 2 and _def_hits(st, _PL2) >= 2,
        )
        assert _jets_planets(fired, registry, "mjets1") == sorted([_PL1, _PL2])
        before = {pl: _def_hits(fired, pl) for pl in (_PL1, _PL2)}
        one = _inv_play(fired, registry, "p1", "mjets1")
        first = next(pl for pl in before if _def_hits(one, pl) == before[pl] - 1)
        other = _PL2 if first == _PL1 else _PL1
        # Same planet's roll: no second card; the other planet's roll: one more.
        assert _jets_planets(one, registry, "mjets2") == [other]
        two = _inv_play(one, registry, "p1", "mjets2")
        assert _def_hits(two, other) == before[other] - 1
        assert _def_hits(two, first) == before[first] - 1
        assert _jets_planets(two, registry, "mjets3") == []


@ruling("C_action_cards/maneuvering-jets/2")
def test_maneuvering_jets_has_no_window_in_combat(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = _assign_state(grid, registry, ["mjets1"], [])
    assert state.active_combat is not None and state.active_combat.pending_hits["p1"] > 0
    assert not _can(state, registry, "p1", "mjets1")


@ruling("C_action_cards/emergency-repairs/1")
def test_emergency_repairs_in_the_space_cannon_offense_step(registry: StaticDataRegistry) -> None:
    state = _inv_state(
        {"p1": {"dreadnought": 1}}, {_PL1: {"p2": {"pds": 1}}}, {_PL1: "p2"},
        step=TacticalStep.SPACE_CANNON,
    )
    _inv_hand(state, "p1", "emergency")
    damage.set_damaged(state.systems["000"], "space", "p1", "dreadnought", 1)
    with _invasion_board() as board:
        opened = space_cannon.open_offense(state, board, registry)
        new = _inv_play(opened, registry, "p1", "emergency")
    assert damage.damaged_count(new.systems["000"], "space", "p1", "dreadnought") == 0


@ruling("C_action_cards/bunker/1")
def test_bunker_applies_to_bombardment_of_each_planet(registry: StaticDataRegistry) -> None:
    with _invasion_board() as board:
        state = _inv_state(
            {"p1": {"dreadnought": 4, "infantry": 1}},
            {_PL1: {"p2": {"infantry": 3}}, _PL2: {"p2": {"infantry": 3}}},
            {_PL1: "p2", _PL2: "p2"},
        )
        _inv_hand(state, "p2", "bunker")
        started = invasion.begin_invasion(state, board, registry)
        played = _inv_play(started, registry, "p2", "bunker")
        plan = [
            BombardAssignment("dreadnought", _PL1, 2), BombardAssignment("dreadnought", _PL2, 2),
        ]
        rolled = invasion.bombard(played, board, registry, plan)
    assert rolled.invasion is not None
    by_planet = {e["planet"]: e for e in rolled.invasion.log if "planet" in e}
    assert set(by_planet) == {_PL1, _PL2}
    for entry in by_planet.values():
        assert all(int(roll["modifier"]) == -4 for roll in entry["rolls"])


@ruling("C_action_cards/disable/3")
def test_disable_is_not_played_in_space_cannon_offense(registry: StaticDataRegistry) -> None:
    state = _inv_state(
        {"p1": {"dreadnought": 1, "infantry": 2}},
        {_PL1: {"p2": {"infantry": 1, "pds": 1}}}, {_PL1: "p2"},
        step=TacticalStep.SPACE_CANNON,
    )
    _inv_hand(state, "p1", "disable")
    with _invasion_board() as board:
        opened = space_cannon.open_offense(state, board, registry)
        assert not _inv_row(opened, registry, "p1", "disable")["playable"]
        assert space_cannon.offense_shooters(opened, board, registry, "p2")  # PDS still fires
        invading = state.clone()
        invading.tactical_step = TacticalStep.INVASION
        started = invasion.begin_invasion(invading, board, registry)
        assert _inv_row(started, registry, "p1", "disable")["playable"]  # start of invasion


@ruling("C_action_cards/disable/2")
def test_disable_leaves_magen_defense_grid_working(registry: StaticDataRegistry) -> None:
    from src.core.hooks import technologies_combat

    state = _inv_state(
        {"p1": {"dreadnought": 1, "infantry": 2}},
        {_PL1: {"p2": {"infantry": 1, "pds": 1}}}, {_PL1: "p2"},
    )
    state.players["p2"].technologies = [technologies_combat.MAGEN_ALIAS]
    _inv_hand(state, "p1", "disable")
    with _invasion_board() as board:
        started = invasion.begin_invasion(state, board, registry)
        played = _inv_play(started, registry, "p1", "disable")
    ctx = {
        "kind": "ground", "position": "000", "planet": _PL1, "attacker": "p1", "defender": "p2",
    }
    assert technologies_combat._magen_ground_ready(played, "p2", ctx)


@ruling("C_action_cards/solar-flare/1", "C_action_cards/solar-flare/2")
def test_solar_flare_leaves_active_player_and_defense_space_cannon(
    registry: StaticDataRegistry,
) -> None:
    state = _inv_state(
        {"p1": {"dreadnought": 1, "infantry": 2}, "p2": {"destroyer": 1}},
        {_PL1: {"p2": {"infantry": 1, "pds": 2}}, _PL2: {"p1": {"pds": 1}}},
        {_PL1: "p2", _PL2: "p1"},
        step=TacticalStep.MOVEMENT,
    )
    _inv_hand(state, "p1", "solar_flare")
    played = _inv_play(state, registry, "p1", "solar_flare")
    assert space_cannon.offense_targets(played, "p2") == []
    assert space_cannon.offense_targets(played, "p1") == ["p2"]  # the active player still fires
    # Space Cannon Defense of the same action is not affected.
    played.systems["000"].space_units["p2"] = {}
    played.tactical_step = TacticalStep.INVASION
    with _invasion_board() as board:
        started = invasion.begin_invasion(played, board, registry)
        landed = invasion.commit_ground_forces(started, registry, {_PL1: {"infantry": 2}})
        entered = invasion.advance(landed, board, registry)
        assert entered.invasion is not None
        assert invasion.defense_planets(entered, registry) == [_PL1]


# ======================================================================= Experimental Battlestation


def _eb_after_move(seed: int, registry: StaticDataRegistry, board: HexGrid) -> GameState:
    """p1 already has a cruiser in the active system and moves a destroyer in from 101."""
    state = _inv_state({"p1": {"cruiser": 1}}, step=TacticalStep.MOVEMENT, seed=seed)
    state.systems["000"].planet_units[_PL1] = {"p2": {"spacedock": 1}}
    state.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p1": {"destroyer": 1}}
    )
    _inv_hand(state, "p2", "experimental")
    moved = movement.move_fleet(state, board, registry, "101", {"destroyer": 1}, {}, "p1")
    assert moved.tactical_moved
    return moved


@ruling(
    "C_action_cards/experimental-battlestation/2",
    "C_action_cards/experimental-battlestation/3.1",
)
def test_experimental_hits_go_to_the_active_players_ships_incl_ones_already_there(
    registry: StaticDataRegistry,
) -> None:
    with _invasion_board() as board:
        hit = _seek(
            lambda s: _inv_play(
                _eb_after_move(s, registry, board), registry, "p2", "experimental",
                {"dock": {"position": "000", "zone": _PL1}},
            ),
            lambda st: _sc_hits(st) >= 1,
        )
    pending = space_cannon.pending_hits(hit)
    assert pending is not None and pending.target == "p1"  # only the active player
    with pytest.raises(ValueError):
        space_cannon.assign_hits(hit, "p2", {"cruiser": 1})
    done = space_cannon.assign_hits(hit, "p1", {"cruiser": 1} if pending.hits == 1 else {
        "cruiser": 1, "destroyer": 1,
    })
    assert done.systems["000"].space_units.get("p1", {}).get("cruiser", 0) == 0  # was there


@ruling("C_action_cards/experimental-battlestation/3")
def test_experimental_needs_ships_moved_in_not_only_present(registry: StaticDataRegistry) -> None:
    state = _inv_state({"p1": {"cruiser": 2}}, step=TacticalStep.MOVEMENT)
    state.systems["000"].planet_units[_PL1] = {"p2": {"spacedock": 1}}
    _inv_hand(state, "p2", "experimental")
    with _invasion_board() as board:
        assert not state.tactical_moved
        assert not _inv_row(state, registry, "p2", "experimental")["playable"]
        moved = _eb_after_move(1, registry, board)
        assert _inv_row(moved, registry, "p2", "experimental")["playable"]


@ruling("C_action_cards/experimental-battlestation/4")
def test_experimental_not_after_a_retreat(grid: HexGrid, registry: StaticDataRegistry) -> None:
    """Ships moved by a retreat are not moved in the Move Ships step: no window."""
    state = _start(
        _combat_state(
            {"cruiser": 1}, {"cruiser": 1}, hand2=["experimental"],
            presence={"101": {"p1": {"destroyer": 1}}},
        ),
        grid, registry,
    )
    state.systems["101"].planet_units = {"vefutii": {"p2": {"spacedock": 1}}}
    state.tactical_moved = True
    announced = battle.announce_retreat(state, grid, "p1", announce=True)
    assert announced.tactical_step is not TacticalStep.MOVEMENT
    assert not _can(announced, registry, "p2", "experimental")


# ====================================================================================== Ghost Squad


def _ghost_state(
    registry: StaticDataRegistry, board: HexGrid, *, titans: bool = False
) -> GameState:
    state = _inv_state(
        {"p1": {"infantry": 2}},
        {_PL1: {"p2": {"infantry": 1}}, _PL2: {"p2": {"infantry": 2, "pds": 1}}},
        {_PL1: "p2", _PL2: "p2"},
    )
    if titans:
        state.players["p2"].faction = "titans"
    _inv_hand(state, "p2", "ghost_squad")
    return invasion.begin_invasion(state, board, registry)


@ruling("C_action_cards/ghost-squad/1", "C_action_cards/ghost-squad/4")
def test_ghost_squad_after_commit_and_zero_forces(registry: StaticDataRegistry) -> None:
    with _invasion_board() as board:
        started = _ghost_state(registry, board)
        assert not _inv_row(started, registry, "p2", "ghost_squad")["playable"]  # nothing committed
        landed = invasion.commit_ground_forces(started, registry, {_PL1: {"infantry": 2}})
        assert _inv_row(landed, registry, "p2", "ghost_squad")["playable"]
        moved_none = _inv_play(landed, registry, "p2", "ghost_squad", {"units": []})
    assert moved_none.systems["000"].planet_units == landed.systems["000"].planet_units
    assert "ghost_squad" in moved_none.decks.action_card_discard


@ruling("C_action_cards/ghost-squad/2")
def test_ghost_squad_after_quantum_dissemination(registry: StaticDataRegistry) -> None:
    from src.core.hooks.factions import yin

    albion, starpoint = registry.systems["27"].planets[:2]
    board = HexGrid()
    board.place_system("102", "27", anomalies=set())
    board.build_edges()
    state = _inv_state(step=TacticalStep.MOVEMENT)
    state.systems = {
        "102": SystemState(
            position="102", system_id="27",
            planet_units={albion: {"p2": {"infantry": 1}}, starpoint: {"p2": {"infantry": 2}}},
            planet_owners={albion: "p2", starpoint: "p2"},
        )
    }
    state.players["p1"].faction = "yin"
    state.tactical_step = None
    state.active_system = None
    _inv_hand(state, "p2", "ghost_squad")
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: board)
    try:
        yin.quantum_dissemination(
            state, registry, "p1",
            {"planet1": f"102|{albion}", "planet2": "none", "planet3": "none"},
        )
        assert state.invasion is not None and state.invasion.last_commit
        assert _inv_row(state, registry, "p2", "ghost_squad")["playable"]
    finally:
        board_graph.bind_grid_provider(previous)


@ruling("C_action_cards/ghost-squad/2.1")
def test_ghost_squad_not_after_placing_without_commit(registry: StaticDataRegistry) -> None:
    state = _inv_state(
        {}, {_PL1: {"p2": {"infantry": 1}}, _PL2: {"p2": {"infantry": 2}}},
        {_PL1: "p2", _PL2: "p2"}, step=TacticalStep.MOVEMENT,
    )
    state.phase = Phase.AGENDA
    state.tactical_step = None
    _inv_hand(state, "p2", "ghost_squad")
    # Colonial Redistribution style: infantry placed on the planet, nothing committed.
    place_from_reinforcements(state, state.systems["000"], _PL1, "p1", "infantry", 1)
    assert not _windows(state, GameEvent.UNITS_COMMITTED)
    assert not _inv_row(state, registry, "p2", "ghost_squad")["playable"]


@ruling("C_action_cards/ghost-squad/3")
def test_ghost_squad_cannot_move_a_hel_titan(registry: StaticDataRegistry) -> None:
    with _invasion_board() as board:
        started = _ghost_state(registry, board, titans=True)
        landed = invasion.commit_ground_forces(started, registry, {_PL1: {"infantry": 2}})
        inputs = action_cards.card_inputs(landed, registry, "p2", "ghost_squad")[1]
        units = next(i for i in inputs if i["key"] == "units")
        assert {o["value"]["base_type"] for o in units["options"]} == {"infantry"}
        with pytest.raises(ValueError):
            _inv_play(
                landed, registry, "p2", "ghost_squad",
                {"to_planet": _PL1, "units": [{"planet": _PL2, "base_type": "pds"}]},
            )


# ========================================================================= Decoy Operation / Rescue


@ruling("C_action_cards/decoy-operation/1")
def test_decoy_keeps_a_damaged_mech_damaged(registry: StaticDataRegistry) -> None:
    state = _tac_state({"p2": ["decoy"]})
    system = state.systems[_TAC_ACTIVE]
    system.planet_owners = {"mr": "p2"}
    system.planet_units = {"mr": {"p2": {"pds": 1}}}
    state.systems["102"] = SystemState(
        position="102", system_id="19", planet_owners={"wellon": "p2"},
        planet_units={"wellon": {"p2": {"mech": 1}}},
    )
    damage.set_damaged(state.systems["102"], "wellon", "p2", "mech", 1)
    new = _tac_play(
        state, registry, "p2", "decoy",
        {"planet": "mr", "units": [{"planet": "wellon", "base_type": "mech"}]},
    )
    assert new.systems[_TAC_ACTIVE].planet_units["mr"]["p2"]["mech"] == 1
    assert damage.damaged_count(new.systems[_TAC_ACTIVE], "mr", "p2", "mech") == 1


def _rescue_state(registry: StaticDataRegistry, seed: int) -> tuple[GameState, HexGrid]:
    board = _tac_grid(
        ("000", "18", set(), []), ("101", "20", set(), []), ("104", "21", {"GRAVITY_RIFT"}, []),
    )
    state = _tac_state({"p2": ["rescue"]})
    state.rng_seed = seed
    state.active_system = "000"
    state.systems["000"] = SystemState(
        position="000", system_id="18", command_tokens=["p1"], space_units={"p2": {"cruiser": 1}}
    )
    state.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p1": {"destroyer": 1}}
    )
    state.systems["104"] = SystemState(
        position="104", system_id="21", space_units={"p2": {"destroyer": 1}}
    )
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: board)
    try:
        moved = movement.move_fleet(state, board, registry, "101", {"destroyer": 1}, {}, "p1")
        new = _tac_play(moved, registry, "p2", "rescue", {"from": "104", "base_type": "destroyer"})
    finally:
        board_graph.bind_grid_provider(previous)
    return new, board


@ruling("C_action_cards/rescue/1")
def test_rescue_out_of_a_gravity_rift_rolls_for_removal(registry: StaticDataRegistry) -> None:
    outcomes = [_rescue_state(registry, seed)[0] for seed in range(1, 30)]
    for new in outcomes:
        assert new.table_roll is not None and new.table_roll["kind"] == "gravity_rift"
    arrived = [n for n in outcomes if n.systems["000"].space_units["p2"].get("destroyer")]
    lost = [n for n in outcomes if not n.systems["000"].space_units["p2"].get("destroyer")]
    assert arrived and lost  # both results happen across seeds
    for new in lost:
        assert not new.systems["104"].space_units.get("p2")  # removed, not left behind
        assert new.table_roll is not None and int(new.table_roll["dice"][0]) <= 3


# ======================================================================================= Infiltrate


@ruling("C_action_cards/infiltrate/1")
def test_infiltrate_after_assimilate_replaces_nothing(registry: StaticDataRegistry) -> None:
    from tests.factions import test_l1z1x as lz

    state = lz._state()
    state.systems["102"].planet_units = {lz.THIBAH: {"p2": {"pds": 1, "spacedock": 1}}}
    state.players["p1"].private.action_cards = ["infiltrate"]
    lz._capture(state, registry)  # Assimilate already replaced the structures
    before = dict(state.systems["102"].planet_units[lz.THIBAH]["p1"])
    assert before == {"pds": 1, "spacedock": 1}
    from src.core.hooks import reactions_tactical

    assert reactions_tactical._infiltrate_targets(state, "p1", lz.THIBAH) == []
    assert reactions_tactical._destroyed_on_capture(state, "p1", lz.THIBAH) == []


@ruling("C_action_cards/infiltrate/2")
def test_infiltrate_takes_a_structure_from_the_board(registry: StaticDataRegistry) -> None:
    from src.core import control

    state = _capture_state()
    state.systems["102"].planet_units = {"wellon": {"p1": {"pds": 6}}}
    control.set_planet_control(state, _TAC_ACTIVE, "mr", "p1")
    inputs = action_cards.card_inputs(state, registry, "p1", "infiltrate")[1]
    assert any(i["key"] == "sources:pds" for i in inputs)  # the player picks the source
    new = _tac_play(state, registry, "p1", "infiltrate",
                    {"planet": "mr", "sources:pds": ["102|wellon"]})
    assert new.systems[_TAC_ACTIVE].planet_units["mr"]["p1"] == {"pds": 1, "spacedock": 1}
    assert new.systems["102"].planet_units["wellon"]["p1"] == {"pds": 5}


# ============================================================================= Tactical Bombardment


@ruling("C_action_cards/tactical-bombardment/1", "C_action_cards/tactical-bombardment/2")
def test_tactical_bombardment_needs_bombardment_any_planets(registry: StaticDataRegistry) -> None:
    from tests import test_action_cards_economy as te

    state = te._state(["tactical"], theirs=(te._HAZARDOUS,))
    state.systems["101"].space_units = {"p1": {"cruiser": 1}}
    assert not te._playable(state, registry, "tactical")["playable"]
    with pytest.raises(ValueError, match="Bombardment"):
        action_cards.play_action_card(state, registry, "p1", "tactical", {"position": "101"})
    state.systems["101"].space_units = {"p1": {"dreadnought": 1}}
    state.systems["101"].planet_owners = {}  # zero readied planets of other players
    assert te._playable(state, registry, "tactical")["playable"]
    done = te._play(state, registry, "tactical", {"position": "101"})
    assert done.players["p2"].exhausted_planets == []


# ====================================================================================== Flank Speed


@ruling("C_action_cards/flank-speed/1")
def test_second_flank_speed_cannot_be_played(registry: StaticDataRegistry) -> None:
    state = _tac_state({"p1": ["fs1", "fs2"]})
    played = _tac_play(state, registry, "p1", "fs1")
    assert not _tac_playable(played, registry, "p1", "fs2")
    assert rules_hooks.modify(rules_hooks.POINT_MOVEMENT_MOVE_VALUE, played, "p1", 2) == 3


@ruling("C_action_cards/flank-speed/2")
def test_cancelled_flank_speed_keeps_the_activation(registry: StaticDataRegistry) -> None:
    from tests import test_card_hold as hold

    state = hold._state(["fs1"], ["sabo2"], tactical=True)
    state.systems["101"].command_tokens = ["p1"]
    held = hold._play(state, registry, "fs1")
    done, _ = action_cards.play_action_card(held, registry, "p2", "sabo2", now=hold.NOW)
    assert done.held_play is None and not done.active_effects  # Flank Speed cancelled
    assert done.active_system == "101" and done.tactical_step is TacticalStep.MOVEMENT
    assert done.systems["101"].command_tokens == ["p1"]


# ========================================================================== In The Silence Of Space


@ruling("C_action_cards/in-the-silence-of-space/1")
def test_silence_of_space_only_for_ships_in_the_chosen_system(
    registry: StaticDataRegistry,
) -> None:
    board = _tac_grid(
        ("000", "18", set(), []), ("101", "20", set(), []),
        ("201", "21", set(), []), ("202", "22", set(), []), ("102", "23", set(), []),
    )
    state = _tac_state({"p1": ["silence_space"]})
    state.active_system = "000"
    state.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p2": {"cruiser": 1}}
    )
    state.systems["201"] = SystemState(
        position="201", system_id="21", space_units={"p1": {"destroyer": 1}}
    )
    state.systems["202"] = SystemState(
        position="202", system_id="22", space_units={"p1": {"destroyer": 1}}
    )
    new = _tac_play(state, registry, "p1", "silence_space", {"position": "201"})
    assert movement.can_move(new, board, registry, "201", "destroyer", "p1", route=[
        "201", "101", "000",
    ])[0]
    # Ships elsewhere: not through the other player's ships, but around them they may.
    assert not movement.can_move(
        new, board, registry, "202", "destroyer", "p1", route=["202", "101", "000"]
    )[0]
    ok, reason = movement.can_move(
        new, board, registry, "202", "destroyer", "p1", route=["202", "102", "000"]
    )
    assert ok, reason


# ================================================================================== Lost Star Chart


def _lost_star(registry: StaticDataRegistry, *, ban: bool) -> tuple[GameState, HexGrid]:
    board = _tac_grid(
        ("000", "18", set(), ["BETA"]), ("301", "20", set(), ["ALPHA"]),
        ("304", "21", set(), ["BETA"]),
    )
    state = _tac_state({"p1": ["lost_star"]})
    state.active_system = "000"
    for pos, sid in (("301", "20"), ("304", "21")):
        state.systems[pos] = SystemState(
            position=pos, system_id=sid, space_units={"p1": {"destroyer": 1}}
        )
    if ban:
        state.decks.agenda_laws = {"travel_ban": "for"}
    return state, board


@ruling("C_action_cards/lost-star-chart/1", "C_action_cards/lost-star-chart/1.1")
def test_lost_star_chart_moves_through_wormholes_under_travel_ban(
    registry: StaticDataRegistry,
) -> None:
    state, board = _lost_star(registry, ban=True)
    with _bound(board):
        # Travel Ban: the beta-beta link 304-000 has no effect.
        assert not movement.can_move(state, board, registry, "304", "destroyer", "p1")[0]
        new = _tac_play(state, registry, "p1", "lost_star")
        ok, reason = movement.can_move(new, board, registry, "301", "destroyer", "p1")
        assert ok, reason  # alpha -> beta
        ok, reason = movement.can_move(new, board, registry, "304", "destroyer", "p1")
        assert ok, reason  # beta -> beta, despite the law


@ruling("C_action_cards/lost-star-chart/2")
def test_lost_star_chart_lets_deep_space_cannon_reach_across(
    registry: StaticDataRegistry,
) -> None:
    board = _tac_grid(("000", "18", set(), ["BETA"]), ("301", "20", set(), ["ALPHA"]))
    state = _tac_state({"p1": ["lost_star"]})
    state.active_system = "000"
    state.tactical_step = TacticalStep.MOVEMENT
    state.systems["000"] = SystemState(
        position="000", system_id="18", command_tokens=["p1"], space_units={"p1": {"cruiser": 1}}
    )
    planet = registry.systems["20"].planets[0]
    state.systems["301"] = SystemState(
        position="301", system_id="20", planet_owners={planet: "p2"},
        planet_units={planet: {"p2": {"pds": 1}}},
    )
    state.players["p2"].technologies = ["pds2"]  # PDS II: DEEP SPACE CANNON
    with _bound(board):
        assert not space_cannon.offense_shooters(state, board, registry, "p2")
        new = _tac_play(state, registry, "p1", "lost_star")
        shooters = space_cannon.offense_shooters(new, board, registry, "p2")
    assert shooters and all(s.remote and s.position == "301" for s in shooters)


# ======================================================================================== Nav Suite


def _nav(_registry: StaticDataRegistry) -> GameState:
    state = _tac_state({"p1": ["nav_suite"], "p2": ["nav_suite"]})
    state.active_system = "000"
    return state


@ruling("C_action_cards/nav-suite/1")
def test_nav_suite_does_not_ignore_wormhole_effects(registry: StaticDataRegistry) -> None:
    board = _tac_grid(("000", "18", set(), ["ALPHA"]), ("301", "20", set(), ["ALPHA"]))
    state = _nav(registry)
    state.systems["301"] = SystemState(
        position="301", system_id="20", space_units={"p1": {"destroyer": 1}}
    )
    state.decks.agenda_laws = {"travel_ban": "for"}
    new = _tac_play(state, registry, "p1", "nav_suite")
    # A wormhole is not an anomaly: the law still stops the wormhole move.
    assert not movement.can_move(new, board, registry, "301", "destroyer", "p1")[0]


@ruling("C_action_cards/nav-suite/2")
def test_nav_suite_does_not_help_a_retreat(grid: HexGrid, registry: StaticDataRegistry) -> None:
    state = _start(
        _combat_state(
            {"cruiser": 1}, {"cruiser": 1},
            presence={"101": {"p1": {"destroyer": 1}}, "104": {"p1": {"destroyer": 1}}},
        ),
        grid, registry,
    )
    active_effects.add_effect(state, "action_cards:nav_suite", Duration.TACTICAL_ACTION, owner="p1")
    destinations = retreat_destinations(state, grid, "000", "p1")
    assert "101" in destinations and "104" not in destinations  # the supernova still blocks


@ruling("C_action_cards/nav-suite/3")
def test_nav_suite_through_and_into_an_asteroid_field(registry: StaticDataRegistry) -> None:
    board = _tac_grid(
        ("000", "18", set(), []), ("101", "20", {"ASTEROID_FIELD"}, []), ("201", "21", set(), []),
    )
    state = _nav(registry)
    state.systems["201"] = SystemState(
        position="201", system_id="21", space_units={"p1": {"destroyer": 1}}
    )
    assert not movement.can_move(state, board, registry, "201", "destroyer", "p1")[0]
    new = _tac_play(state, registry, "p1", "nav_suite")
    ok, reason = movement.can_move(new, board, registry, "201", "destroyer", "p1")
    assert ok, reason
    # Into: the asteroid field is the active system; out later: no harm, no technology needed.
    into = _nav(registry)
    into.active_system = "101"
    into.systems["000"] = SystemState(
        position="000", system_id="18", space_units={"p1": {"destroyer": 1}}
    )
    assert not movement.can_move(into, board, registry, "000", "destroyer", "p1")[0]
    entered = _tac_play(into, registry, "p1", "nav_suite")
    assert movement.can_move(entered, board, registry, "000", "destroyer", "p1")[0]
    later = _nav(registry)
    later.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p1": {"destroyer": 1}}
    )
    assert movement.can_move(later, board, registry, "101", "destroyer", "p1")[0]


@ruling("C_action_cards/nav-suite/4")
def test_nav_suite_gravity_rift_without_roll_and_without_bonus(
    registry: StaticDataRegistry,
) -> None:
    board = _tac_grid(
        ("000", "18", set(), []), ("101", "20", {"GRAVITY_RIFT"}, []), ("201", "21", set(), []),
    )
    state = _nav(registry)
    state.systems["201"] = SystemState(
        position="201", system_id="21", space_units={"p1": {"carrier": 1}}  # move 1
    )
    route = ["201", "101", "000"]
    ok, reason = movement.can_move(state, board, registry, "201", "carrier", "p1", route=route)
    assert ok, reason  # the rift gives +1 without Nav Suite
    new = _tac_play(state, registry, "p1", "nav_suite")
    assert not movement.can_move(new, board, registry, "201", "carrier", "p1", route=route)[0]
    out = _nav(registry)
    out.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p1": {"destroyer": 2}}
    )
    played = _tac_play(out, registry, "p1", "nav_suite")
    moved = movement.move_fleet(played, board, registry, "101", {"destroyer": 2}, {}, "p1")
    assert moved.systems["000"].space_units["p1"]["destroyer"] == 2
    assert moved.table_roll is None  # no removal roll


@ruling("C_action_cards/nav-suite/5")
def test_nav_suite_nebula_through_and_out(registry: StaticDataRegistry) -> None:
    board = _tac_grid(
        ("000", "18", set(), []), ("101", "20", {"NEBULA"}, []), ("201", "21", {"NEBULA"}, []),
    )
    through = _nav(registry)
    through.systems["201"] = SystemState(
        position="201", system_id="21", space_units={"p1": {"destroyer": 1}}
    )
    route = ["201", "101", "000"]
    assert not movement.can_move(through, board, registry, "201", "destroyer", "p1", route=route)[0]
    new = _tac_play(through, registry, "p1", "nav_suite")
    # Out of the 201 nebula with move 2 (not 1) and through the 101 nebula.
    ok, reason = movement.can_move(new, board, registry, "201", "destroyer", "p1", route=route)
    assert ok, reason


@ruling("C_action_cards/nav-suite/6")
def test_nav_suite_into_a_supernova_and_out_later(registry: StaticDataRegistry) -> None:
    board = _tac_grid(("000", "18", {"SUPERNOVA"}, []), ("101", "20", set(), []))
    state = _nav(registry)
    state.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p1": {"destroyer": 1}}
    )
    assert not movement.can_move(state, board, registry, "101", "destroyer", "p1")[0]
    new = _tac_play(state, registry, "p1", "nav_suite")
    moved = movement.move_fleet(new, board, registry, "101", {"destroyer": 1}, {}, "p1")
    assert moved.systems["000"].space_units["p1"]["destroyer"] == 1
    later = _nav(registry)
    later.active_system = "101"
    later.systems["000"] = SystemState(
        position="000", system_id="18", space_units={"p1": {"destroyer": 1}}
    )
    ok, reason = movement.can_move(later, board, registry, "000", "destroyer", "p1")
    assert ok, reason  # moving out of the supernova is unharmed


@ruling("C_action_cards/nav-suite/7")
def test_nav_suite_only_for_the_player_who_played_it(registry: StaticDataRegistry) -> None:
    state = _nav(registry)
    new = _tac_play(state, registry, "p1", "nav_suite")
    assert rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_ANOMALIES, new, "p1")
    assert not rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_ANOMALIES, new, "p2")


# ====================================================================================== War Machine


@ruling("C_action_cards/war-machine/1")
def test_war_machine_only_when_units_use_production(registry: StaticDataRegistry) -> None:
    from src.core.game_state import ProductionGrant

    state = _tac_state({"p1": ["war_machine1"]}, step=TacticalStep.PRODUCTION)
    state.active_system = "000"
    state.systems = {
        "000": SystemState(
            position="000", system_id="20", command_tokens=["p1"],
            planet_owners={"vefutii": "p1"}, planet_units={"vefutii": {"p1": {"spacedock": 1}}},
        )
    }
    assert _tac_playable(state, registry, "p1", "war_machine1")  # space dock PRODUCTION
    # Producing without PRODUCTION (Sling Relay-style free grant) opens no War Machine window.
    free = state.clone()
    free.tactical_step = None
    free.active_system = None
    free.production_grant = ProductionGrant(
        player_id="p1", position="000", free=True, units=1, ships_only=True
    )
    assert not _tac_playable(free, registry, "p1", "war_machine1")


# ===================================================================================== ACTION cards


@contextmanager
def _bound(board: HexGrid) -> Iterator[HexGrid]:
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: board)
    try:
        yield board
    finally:
        board_graph.bind_grid_provider(previous)


def _demo(registry: StaticDataRegistry) -> Any:
    return _bound(build_demo_grid(registry))


@ruling("C_action_cards/lucky-shot/1", "C_action_cards/lucky-shot/2")
def test_lucky_shot_only_other_players_and_no_sustain(registry: StaticDataRegistry) -> None:
    from tests import test_action_cards as ta

    planet = ta._planets_with(registry, "cultural", 1)
    state = ta._state(registry, ["lucky"], planet)
    state.systems["000"].space_units = {"p1": {"dreadnought": 1}, "p2": {"dreadnought": 1}}
    with _demo(registry):
        options = action_cards.card_inputs(state, registry, "p1", "lucky")[1][0]["options"]
        assert {o["value"]["owner"] for o in options} == {"p2"}
        with pytest.raises(ValueError):
            ta._play(state, registry, "lucky",
                     {"position": "000", "owner": "p1", "base_type": "dreadnought"})
        new = ta._play(state, registry, "lucky",
                       {"position": "000", "owner": "p2", "base_type": "dreadnought"})
    assert "dreadnought" not in new.systems["000"].space_units.get("p2", {})  # no SUSTAIN
    assert new.systems["000"].space_units["p1"]["dreadnought"] == 1


@ruling("C_action_cards/fighter-conscription/1")
def test_fighter_conscription_one_fighter_per_system(registry: StaticDataRegistry) -> None:
    from tests import test_action_cards_board as tb

    state = tb._state(["f_conscription"], [tb._system(
        "102", "115", space_units={"p1": {"carrier": 1}}, planet_owners={"industrex": "p1"},
        planet_units={"industrex": {"p1": {"spacedock": 1}}},
    )])
    with _demo(registry):
        new = tb._play(registry, state, "f_conscription")
    assert new.systems["102"].space_units["p1"] == {"carrier": 1, "fighter": 1}


def _no_reserve(state: GameState, base_type: str, where: SystemState) -> None:
    """Puts every unit of the type on the board (``where``), leaving the reinforcements empty."""
    from src.core.production import reinforcements_left

    left = reinforcements_left(state, "p1", base_type) or 0
    units = where.space_units.setdefault("p1", {})
    units[base_type] = units.get(base_type, 0) + left


@ruling("C_action_cards/war-effort/1")
def test_war_effort_takes_a_cruiser_from_the_board(registry: StaticDataRegistry) -> None:
    from tests import test_action_cards_board as tb

    state = tb._state(["war_effort"], [
        tb._system("101", "113", space_units={"p1": {"destroyer": 1}}),
        tb._system("104", "02"),
    ])
    _no_reserve(state, "cruiser", state.systems["104"])
    with _demo(registry):
        inputs = tb._inputs(registry, state, "war_effort")
        source = next(i for i in inputs if i["key"] == "source")
        assert [o["value"] for o in source["options"]] == ["auto", "104|space"]
        with pytest.raises(ValueError, match="reinforcements"):
            tb._play(registry, state, "war_effort", {"position": "101"})
        new = tb._play(registry, state, "war_effort", {"position": "101", "source": "104|space"})
    assert new.systems["101"].space_units["p1"] == {"destroyer": 1, "cruiser": 1}
    assert new.systems["104"].space_units["p1"]["cruiser"] == (
        state.systems["104"].space_units["p1"]["cruiser"] - 1
    )


@ruling("C_action_cards/ghost-ship/1", "C_action_cards/ghost-ship/4")
def test_ghost_ship_creuss_gate_nexus_tokens_and_asteroid_wormhole(
    registry: StaticDataRegistry,
) -> None:
    from tests import test_action_cards_board as tb

    board = HexGrid()
    for pos, sid in (("000", "18"), ("101", "17"), ("102", "82b"), ("103", "79"), ("104", "20")):
        board.place_system(pos, sid, anomalies=set())
    board.build_edges()
    state = tb._state(["ghost_ship"], [
        tb._system(pos, sid) for pos, sid in
        (("000", "18"), ("101", "17"), ("102", "82b"), ("103", "79"), ("104", "20"))
    ])
    state.players["p1"].home_position = None
    state.players["p2"].home_position = None
    state.systems["104"].wormhole_tokens = ["GAMMA"]
    with _bound(board):
        targets = ghost_ship_targets(state, registry, "p1")
        assert set(targets) == {"101", "102", "103", "104"}
        new = tb._play(registry, state, "ghost_ship", {"position": "103"})  # asteroid field
    assert new.systems["103"].space_units["p1"] == {"destroyer": 1}


@ruling("C_action_cards/ghost-ship/2", "C_action_cards/signal-jamming/2")
def test_no_ghost_ship_or_signal_jamming_in_an_eliminated_players_home(
    registry: StaticDataRegistry,
) -> None:
    from src.core.game_state import EliminatedPlayer
    from src.core.hooks.action_cards_board import jamming_targets
    from tests import test_action_cards_board as tb

    state = tb._state(["ghost_ship", "jamming"], [
        tb._system("000", "18", space_units={"p1": {"cruiser": 1}}),
    ])
    state.players["p3"] = PlayerState(player_id="p3", color="green")
    with _demo(registry):
        assert "101" in ghost_ship_targets(state, registry, "p1")  # beta wormhole, nobody's home
        assert "101" in {pos for pos, _ in jamming_targets(state, registry, "p1")}
        state.eliminated_players = [EliminatedPlayer(player_id="p4", home_position="101")]
        assert "101" not in ghost_ship_targets(state, registry, "p1")
        assert "101" not in {pos for pos, _ in jamming_targets(state, registry, "p1")}


@ruling("C_action_cards/ghost-ship/3")
def test_ghost_ship_takes_a_destroyer_from_the_board(registry: StaticDataRegistry) -> None:
    from tests import test_action_cards_board as tb

    state = tb._state(["ghost_ship"], [tb._system("104", "02")])
    _no_reserve(state, "destroyer", state.systems["104"])
    with _demo(registry):
        assert tb._playable(registry, state, "ghost_ship")
        inputs = tb._inputs(registry, state, "ghost_ship")
        assert [o["value"] for o in inputs[1]["options"]] == ["auto", "104|space"]
        new = tb._play(registry, state, "ghost_ship", {"position": "101", "source": "auto"})
        assert new.systems["101"].space_units["p1"] == {"destroyer": 1}
        state.systems["104"].command_tokens = ["p1"]  # the only destroyers sit under a token
        assert not tb._playable(registry, state, "ghost_ship")


@ruling("C_action_cards/signal-jamming/1", "C_action_cards/signal-jamming/3")
def test_signal_jamming_mecatol_and_a_player_with_tokens(registry: StaticDataRegistry) -> None:
    from tests import test_action_cards_board as tb

    state = tb._state(["jamming"], [tb._system("000", "18", space_units={"p1": {"cruiser": 1}})])
    state.players["p3"] = PlayerState(player_id="p3", color="green")
    state.players["p3"].cc_reinf = 0
    with _demo(registry):
        inputs = tb._inputs(registry, state, "jamming")
        values = [o["value"] for o in inputs[0]["options"]]
        assert {"position": "000", "player": "p2"} in values  # Mecatol Rex may be chosen
        assert all(v["player"] == "p2" for v in values)  # p3 has no token in reinforcements
        with pytest.raises(ValueError):
            tb._play(registry, state, "jamming", {"position": "000", "player": "p3"})
        new = tb._play(registry, state, "jamming", {"position": "000", "player": "p2"})
    assert new.systems["000"].command_tokens == ["p2"]


# ================================================================================ Ul (Hel-Titans)


@ruling("C_action_cards/disable/1")
def test_disabled_hel_titans_still_fight_in_ground_combat(registry: StaticDataRegistry) -> None:
    state = _inv_state(
        {"p1": {"dreadnought": 1, "infantry": 2}},
        {_PL1: {"p2": {"infantry": 1, "pds": 1}}}, {_PL1: "p2"},
    )
    state.players["p2"].faction = "titans"
    _inv_hand(state, "p1", "disable")
    with _invasion_board() as board:
        started = invasion.begin_invasion(state, board, registry)
        played = _inv_play(started, registry, "p1", "disable")
        assert not space_cannon.zone_shooters(played, registry, "p2", "000", _PL1)
        played.systems["000"].planet_units[_PL1]["p1"] = {"infantry": 2}
        fight = battle.start_combat(played, board, registry, _PL1)
        defenders = {u.base_type for u in battle.side_units(fight, board, registry, "p2")}
    assert "pds" in defenders  # the Hel-Titan still takes part in the ground combat


@ruling("C_action_cards/infiltrate/2.1")
def test_ul_infiltrate_places_hel_titans_undamaged(registry: StaticDataRegistry) -> None:
    from src.core import control

    state = _capture_state()
    state.players["p1"].faction = "titans"
    state.systems["102"].planet_units = {"wellon": {"p1": {"pds": 6}}}
    damage.set_damaged(state.systems["102"], "wellon", "p1", "pds", 6)  # every one damaged
    control.set_planet_control(state, _TAC_ACTIVE, "mr", "p1")
    new = _tac_play(state, registry, "p1", "infiltrate",
                    {"planet": "mr", "sources:pds": ["102|wellon"]})
    assert new.systems[_TAC_ACTIVE].planet_units["mr"]["p1"]["pds"] == 1
    assert damage.damaged_count(new.systems[_TAC_ACTIVE], "mr", "p1", "pds") == 0
