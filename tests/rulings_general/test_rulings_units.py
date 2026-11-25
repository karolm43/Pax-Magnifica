"""Units - rulings of ``docs/rules_tirules/C_units.md`` point by point.

Every test marks the ``@ruling(...)`` points it checks (guard ``tests/test_ruling_coverage.py``);
statuses without a test live in ``tests/rulings_status.json``.
"""

from __future__ import annotations

import pytest

from src.core import (
    battle,
    capacity,
    movement_paths,
    production,
    rules_hooks,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import CombatStep, GameState, Phase, PlayerState, SystemState, TacticalStep
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause
from tests.rulings import ruling
from tests.test_battle import _state as battle_state
from tests.test_capacity import _grid as cap_grid
from tests.test_capacity import _state as cap_state
from tests.test_production import _grid as prod_grid
from tests.test_production import _state_with_dock_on_jord
from tests.test_technologies_combat import _start_magen, _victim_assigns, _with_tech


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


# ================================================================================== War Sun


@ruling("C_units/war-sun/1")
def test_war_sun_cannot_be_produced_without_the_war_sun_upgrade(
    registry: StaticDataRegistry,
) -> None:
    state = _state_with_dock_on_jord(trade_goods=20)
    orders = [production.ProductionOrder("warsun", 1)]
    with pytest.raises(ValueError, match="war sun unit upgrade"):
        production.validate_production(state, prod_grid(), registry, "p1", orders)
    state.players["p1"].technologies = ["ws"]  # War Sun unit upgrade
    production.validate_production(state, prod_grid(), registry, "p1", orders)


@ruling("C_units/war-sun/2.1")
def test_war_sun_does_not_stop_magen_defense_grid_omega_omega(
    registry: StaticDataRegistry,
) -> None:
    """A war sun strips Planetary Shield, yet Magen Defense Grid ΩΩ (structure-based, no
    Planetary Shield condition) still fires at the start of ground combat."""
    state = battle_state(
        space={"p1": {"warsun": 1}},
        planet={"p1": {"infantry": 2}, "p2": {"infantry": 2, "pds": 1}},
    )
    state.tactical_step = TacticalStep.INVASION
    state.players["p1"].faction = "muaat"
    state.players["p1"].technologies = ["pws2"]
    war_sun = resolve_unit_variant(registry, "muaat", ["pws2"], "warsun")
    assert war_sun is not None and war_sun.disables_planetary_shield
    _with_tech(state, "p2", "md")
    after = _victim_assigns(
        _start_magen(state, registry, "infantry"), registry, destroy={"infantry": 1}
    )
    assert after.systems["000"].planet_units["pl"]["p1"] == {"infantry": 1}


# ================================================================================== Flagship


@ruling("C_units/flagship/1")
def test_destroyed_flagship_returns_to_reinforcements(registry: StaticDataRegistry) -> None:
    state = battle_state(space={"p1": {"flagship": 1}})
    assert production.reinforcements_left(state, "p1", "flagship") == 0
    unit_ops.remove_units(
        state, state.systems["000"], "space", "p1", "flagship", 1, UnitCause.DESTROYED
    )
    assert production.reinforcements_left(state, "p1", "flagship") == 1  # may be produced again


# ================================================================================== Fighter


@ruling("C_units/fighter/1")
def test_fighters_and_ground_forces_do_not_count_toward_capacity_during_combat(
    registry: StaticDataRegistry,
) -> None:
    grid = cap_grid()
    state = cap_state(
        {"p1": {"carrier": 1, "fighter": 8, "infantry": 4}, "p2": {"cruiser": 1}},
        step=TacticalStep.SPACE_COMBAT,
    )
    assert capacity.capacity_report(state, registry, "000", "p1").excess > 0
    started = battle.start_combat(state, grid, registry)
    combat = started.active_combat
    assert combat is not None and combat.step is not CombatStep.DONE
    assert capacity.players_with_excess(started, registry, "000") == []  # during combat
    ended = started.clone()
    assert ended.active_combat is not None
    ended.active_combat.step = CombatStep.DONE
    assert capacity.players_with_excess(ended, registry, "000") == ["p1"]  # after combat


@ruling("C_units/fighter/2")
def test_ship_cannot_move_through_a_system_with_foreign_fighters(
    registry: StaticDataRegistry,
) -> None:
    state = cap_state({"p2": {"fighter": 1}}, step=TacticalStep.MOVEMENT)
    state.players["p1"].technologies = []
    grid = cap_grid()
    assert not movement_paths._node_passable_intermediate(  # noqa: SLF001
        grid, state, "000", "p1", can_enter_asteroids=True
    )
    # Own fighters do not block the owner.
    own = cap_state({"p1": {"fighter": 1}}, step=TacticalStep.MOVEMENT)
    assert movement_paths._node_passable_intermediate(  # noqa: SLF001
        grid, own, "000", "p1", can_enter_asteroids=True
    )


@ruling("C_units/fighter/2.1")
def test_light_wave_deflector_and_silence_of_space_pass_through_fighters(
    registry: StaticDataRegistry,
) -> None:
    """Examples from the ruling: Light/Wave Deflector and In The Silence Of Space (the third,
    Firmament's agent Myru Vos, has no implementation - Firmament is not a playable faction)."""
    grid = cap_grid()
    state = cap_state({"p2": {"fighter": 2}}, step=TacticalStep.MOVEMENT)
    state.players["p1"].technologies = ["lwd"]
    assert movement_paths._node_passable_intermediate(  # noqa: SLF001
        grid, state, "000", "p1", can_enter_asteroids=True
    )
    from src.core import active_effects  # local: only this example needs it

    silent = cap_state({"p2": {"fighter": 2}}, step=TacticalStep.MOVEMENT)
    active_effects.add_effect(
        silent, "action_cards:silence_space", Duration.TURN, owner="p1",
        data={"position": "101"},
    )
    assert movement_paths._node_passable_intermediate(  # noqa: SLF001
        grid, silent, "000", "p1", can_enter_asteroids=True, from_pos="101"
    )
    assert not movement_paths._node_passable_intermediate(  # noqa: SLF001
        grid, silent, "000", "p1", can_enter_asteroids=True, from_pos="202"
    )


# ================================================================================== Fighter II


@ruling("C_units/fighter-ii/1")
def test_fighter_ii_is_still_a_fighter(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, None, ["ff2"], "fighter")
    assert unit is not None and unit.base_type == "fighter"
    assert unit.id != resolve_unit_variant(registry, None, [], "fighter").id  # type: ignore[union-attr]
    state = cap_state({"p1": {"carrier": 1, "fighter": 2}, "p2": {"fighter": 1}})
    state.players["p1"].technologies = ["ff2"]
    report = capacity.capacity_report(state, registry, "000", "p1")
    assert report.cargo == {"fighter": 2}  # counted as a fighter for capacity
    assert report.names["fighter"] == unit.name
    # ... and for passage blocking when owned by another player.
    state.players["p2"].technologies = ["ff2"]
    assert not movement_paths._node_passable_intermediate(  # noqa: SLF001
        cap_grid(), state, "000", "p1", can_enter_asteroids=True
    )


# ================================================================================== Infantry II


def _inf_state(planets: list[str], on_card: int = 1) -> GameState:
    home = SystemState(position="000", system_id="18", planet_owners={p: "p1" for p in planets})
    player = PlayerState(
        player_id="p1", color="red", technologies=["inf2"], home_position="000",
        infantry_ii_on_card=on_card,
    )
    return GameState(
        phase=Phase.ACTION, active_player_id="p2", seating_order=["p1", "p2"],
        players={"p1": player, "p2": PlayerState(player_id="p2", color="blue")},
        systems={"000": home}, rng_seed=1,
    )


@ruling("C_units/infantry-ii/1")
def test_infantry_ii_on_card_returns_to_reserve_without_a_home_planet() -> None:
    state = _inf_state([], on_card=2)
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    assert state.players["p1"].infantry_ii_on_card == 0
    assert state.systems["000"].planet_units == {}  # nothing placed - back in reinforcements
    # With a home planet the unit is placed there instead.
    placed = _inf_state(["a"], on_card=2)
    triggers.fire(placed, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    assert placed.systems["000"].planet_units["a"]["p1"] == {"infantry": 2}


def _destroy_infantry(seed: int, cause: UnitCause) -> GameState:
    state = _inf_state(["a"], on_card=0)
    state.rng_seed = seed
    state.systems["000"].planet_units["a"] = {"p1": {"infantry": 1}}
    assert state.active_combat is None  # outside of combat (Plague-style destruction)
    unit_ops.remove_units(state, state.systems["000"], "a", "p1", "infantry", 1, cause)
    return state


@ruling("C_units/infantry-ii/2")
def test_infantry_ii_revive_roll_applies_outside_combat() -> None:
    revived = 0
    for seed in range(1, 80):
        state = _destroy_infantry(seed, UnitCause.DESTROYED)
        assert state.table_roll is not None and state.table_roll["kind"] == "infantry_ii"
        revived += state.players["p1"].infantry_ii_on_card
    assert 0 < revived < 79  # a 6+ revives, lower results do not


@ruling("C_units/infantry-ii/2.1")
def test_infantry_ii_revive_roll_does_not_apply_to_removed_infantry() -> None:
    for seed in range(1, 40):
        state = _destroy_infantry(seed, UnitCause.REMOVED)
        assert state.table_roll is None
        assert state.players["p1"].infantry_ii_on_card == 0


# ================================================================================== Space Dock


@ruling("C_units/space-dock/1")
def test_space_dock_has_no_capacity_but_holds_three_fighters(
    registry: StaticDataRegistry,
) -> None:
    dock = resolve_unit_variant(registry, None, [], "spacedock")
    assert dock is not None and dock.capacity_value == 3
    state = cap_state(
        {"p1": {"fighter": 3, "infantry": 1}}, planet={"p1": {"spacedock": 1}}
    )
    report = capacity.capacity_report(state, registry, "000", "p1")
    assert report.general == 0  # no capacity value for the space area
    assert report.fighter_only == 3
    assert report.excess == 1  # the infantry cannot be held by the dock
    no_ground = cap_state({"p1": {"fighter": 3}}, planet={"p1": {"spacedock": 1}})
    assert capacity.capacity_report(no_ground, registry, "000", "p1").excess == 0
    four = cap_state({"p1": {"fighter": 4}}, planet={"p1": {"spacedock": 1}})
    assert capacity.capacity_report(four, registry, "000", "p1").excess == 1


@ruling("C_units/space-dock/2")
def test_two_space_docks_hold_six_fighters(registry: StaticDataRegistry) -> None:
    state = cap_state({"p1": {"fighter": 6}})
    state.systems["000"].planet_units = {
        "pl": {"p1": {"spacedock": 1}}, "pl2": {"p1": {"spacedock": 1}},
    }
    report = capacity.capacity_report(state, registry, "000", "p1")
    assert report.fighter_only == 6 and report.excess == 0
    state.systems["000"].space_units["p1"]["fighter"] = 7
    assert capacity.capacity_report(state, registry, "000", "p1").excess == 1


@ruling("C_units/space-dock/3")
def test_space_dock_production_ignores_planet_exhaustion(registry: StaticDataRegistry) -> None:
    grid: HexGrid = prod_grid()
    ready = _state_with_dock_on_jord()
    spent = _state_with_dock_on_jord(exhausted=True)
    limit = production.production_limit(ready, grid, registry, "p1")
    assert limit > 0
    assert production.production_limit(spent, grid, registry, "p1") == limit
