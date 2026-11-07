"""Testy inwazji (RULES.md 40): Bombardment, Commit, Space Cannon Defense, walka, Establish."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from src.core import battle, invasion, tactical
from src.core.game_state import (
    GameState,
    InvasionPhase,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.invasion import BombardAssignment
from src.core.registry import StaticDataRegistry

# Kafelek 09 ma dwie planety: maaluuk i druaa.
_TILE = "09"
_PL1 = "maaluuk"
_PL2 = "druaa"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", _TILE, anomalies=set())
    grid.build_edges()
    return grid


def _state(
    space: dict[str, dict[str, int]] | None = None,
    planets: dict[str, dict[str, dict[str, int]]] | None = None,
    owners: dict[str, str] | None = None,
    *,
    seed: int = 1,
) -> GameState:
    """Aktywny p1 (atakujący) w INVASION; ``planets`` = ``{planeta: {gracz: {typ: n}}}``."""
    system = SystemState(position="000", system_id=_TILE)
    for pid, by_type in (space or {}).items():
        system.space_units[pid] = dict(by_type)
    for planet, by_player in (planets or {}).items():
        for pid, by_type in by_player.items():
            system.planet_units.setdefault(planet, {})[pid] = dict(by_type)
    system.planet_owners = dict(owners or {})
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=TacticalStep.INVASION,
        seating_order=["p1", "p2"],
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2")},
        systems={"000": system},
        rng_seed=seed,
    )


def _seek(
    state: GameState,
    run: Callable[[GameState], GameState],
    ok: Callable[[GameState], bool],
) -> GameState:
    """Szuka ziarna, przy którym przebieg daje oczekiwany wynik (rzuty są deterministyczne)."""
    for seed in range(1, 600):
        candidate = state.clone()
        candidate.rng_seed = seed
        try:
            result = run(candidate)
        except ValueError:
            continue
        if ok(result):
            return result
    raise AssertionError("no seed produced the expected outcome")


def _fight(state: GameState, grid: HexGrid, registry: StaticDataRegistry, planet: str) -> GameState:
    """Rozgrywa walkę naziemną do końca, strata = niszczenie pierwszych z brzegu jednostek."""
    state = battle.start_combat(state, grid, registry, planet)
    for _ in range(40):
        combat = state.active_combat
        assert combat is not None
        if combat.step.value == "DONE":
            break
        state = battle.roll_round(state, grid, registry)
        while state.pending_window is not None:
            pid = state.pending_window.current_responder
            assert pid is not None
            units = battle.side_units(state, grid, registry, pid)
            need = battle.required_hits(state, grid, registry, pid)
            destroy: dict[str, int] = {}
            for unit in units:
                take = min(unit.count, need)
                if take:
                    destroy[unit.base_type] = take
                    need -= take
            state = battle.assign_combat_hits(
                state, grid, registry, pid, sustain={}, destroy=destroy, destroy_damaged={}
            )
    return battle.close_combat(state)


# ------------------------------------------------------------------------------- start


def test_no_invasion_without_ground_forces_or_bombardment(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"cruiser": 1}})
    assert invasion.begin_invasion(state, _grid(), registry).invasion is None


def test_begin_goes_straight_to_commit_when_nothing_bombards(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"infantry": 2}})
    started = invasion.begin_invasion(state, _grid(), registry)
    assert started.invasion is not None
    assert started.invasion.phase is InvasionPhase.COMMIT


def test_begin_opens_bombardment_when_dreadnought_has_target(registry: StaticDataRegistry) -> None:
    state = _state(
        {"p1": {"dreadnought": 2, "infantry": 1}},
        {_PL1: {"p2": {"infantry": 2}}},
        {_PL1: "p2"},
    )
    started = invasion.begin_invasion(state, _grid(), registry)
    assert started.invasion is not None
    assert started.invasion.phase is InvasionPhase.BOMBARDMENT
    groups = invasion.bombard_groups(started, registry)
    assert [(g.base_type, g.count, g.hits_on) for g in groups] == [("dreadnought", 2, 5)]


def test_planetary_shield_blocks_bombardment_but_not_war_sun(
    registry: StaticDataRegistry,
) -> None:
    planets = {_PL1: {"p2": {"infantry": 2, "pds": 1}}}
    dread = invasion.begin_invasion(
        _state({"p1": {"dreadnought": 1}}, planets, {_PL1: "p2"}), _grid(), registry
    )
    assert dread.invasion is None  # tarcza: nie ma kogo bombardować, nic do lądowania
    war_state = _state({"p1": {"warsun": 1}}, planets, {_PL1: "p2"})
    war_state.players["p1"].technologies = ["ws"]  # bez technologii war sun to placeholder
    war = invasion.begin_invasion(war_state, _grid(), registry)
    assert war.invasion is not None
    assert invasion.bombard_targets(war, registry) == [_PL1]


def test_bombard_requires_all_units_and_assigns_hits(registry: StaticDataRegistry) -> None:
    grid = _grid()
    base = invasion.begin_invasion(
        _state(
            {"p1": {"dreadnought": 2}},
            {_PL1: {"p2": {"infantry": 3}}},
            {_PL1: "p2"},
        ),
        grid,
        registry,
    )
    with pytest.raises(ValueError, match="every unit"):
        invasion.bombard(base, grid, registry, [BombardAssignment("dreadnought", _PL1, 1)])
    with pytest.raises(ValueError, match="cannot be bombarded"):
        invasion.bombard(base, grid, registry, [BombardAssignment("dreadnought", _PL2, 2)])

    rolled = _seek(
        base,
        lambda s: invasion.bombard(s, grid, registry, [BombardAssignment("dreadnought", _PL1, 2)]),
        lambda s: s.invasion is not None and s.invasion.bombard_pending.get(_PL1, 0) > 0,
    )
    assert rolled.invasion is not None
    hits = rolled.invasion.bombard_pending[_PL1]
    with pytest.raises(ValueError, match="Assign the bombardment hits"):
        invasion.advance(rolled, grid, registry)
    required = invasion.required_bombard_hits(rolled, grid, registry, _PL1)
    assert required == min(hits, 3)
    after = invasion.assign_bombard_hits(
        rolled, grid, registry, _PL1, "p2",
        sustain={}, destroy={"infantry": required}, destroy_damaged={},
    )
    assert after.invasion is not None and not after.invasion.bombard_pending
    left = after.systems["000"].planet_units.get(_PL1, {}).get("p2", {}).get("infantry", 0)
    assert left == 3 - required
    with pytest.raises(ValueError, match="already been resolved"):
        invasion.bombard(after, grid, registry, [BombardAssignment("dreadnought", _PL1, 2)])


# -------------------------------------------------------------------------------- commit


def test_commit_moves_ground_forces_from_space_to_planet(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = invasion.begin_invasion(
        _state({"p1": {"carrier": 1, "infantry": 3, "mech": 1}}), grid, registry
    )
    committed = invasion.commit_ground_forces(
        state, registry, {_PL1: {"infantry": 2}, _PL2: {"infantry": 1, "mech": 1}}
    )
    system = committed.systems["000"]
    assert system.space_units["p1"] == {"carrier": 1}
    assert system.planet_units[_PL1]["p1"] == {"infantry": 2}
    assert system.planet_units[_PL2]["p1"] == {"infantry": 1, "mech": 1}
    assert committed.invasion is not None
    assert committed.invasion.committed[_PL1] == {"infantry": 2}
    with pytest.raises(ValueError, match="space area"):
        invasion.commit_ground_forces(committed, registry, {_PL1: {"infantry": 1}})
    with pytest.raises(ValueError, match="not a ground force"):
        invasion.commit_ground_forces(state, registry, {_PL1: {"carrier": 1}})
    with pytest.raises(ValueError, match="not a planet"):
        invasion.commit_ground_forces(state, registry, {"nowhere": {"infantry": 1}})


# --------------------------------------------------------------------- space cannon defense


def test_space_cannon_defense_fires_at_landed_forces(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = invasion.begin_invasion(
        _state(
            {"p1": {"infantry": 4}},
            {_PL1: {"p2": {"pds": 2}}},
            {_PL1: "p2"},
        ),
        grid,
        registry,
    )
    state = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 4}})
    state = invasion.advance(state, grid, registry)
    assert state.invasion is not None
    assert state.invasion.phase is InvasionPhase.SPACE_CANNON_DEFENSE
    with pytest.raises(ValueError, match="every planet"):
        invasion.advance(state, grid, registry)

    fired = _seek(
        state,
        lambda s: invasion.defense_fire(s, grid, registry, _PL1),
        lambda s: s.invasion is not None and s.invasion.defense_pending.get(_PL1, 0) > 0,
    )
    assert fired.invasion is not None
    required = invasion.required_defense_hits(fired, grid, registry, _PL1)
    assert required > 0
    done = invasion.assign_defense_hits(
        fired, grid, registry, _PL1,
        sustain={}, destroy={"infantry": required}, destroy_damaged={},
    )
    assert done.systems["000"].planet_units[_PL1]["p1"]["infantry"] == 4 - required
    nxt = invasion.advance(done, grid, registry)
    assert nxt.invasion is not None
    # Obrońca nie ma sił naziemnych → brak walki → od razu Establish Control.
    assert nxt.invasion.phase is InvasionPhase.ESTABLISH


def test_space_cannon_defense_can_be_declined(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = invasion.begin_invasion(
        _state({"p1": {"infantry": 1}}, {_PL1: {"p2": {"pds": 1}}}, {_PL1: "p2"}),
        grid,
        registry,
    )
    state = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 1}})
    state = invasion.advance(state, grid, registry)
    state = invasion.defense_pass(state, registry, _PL1)
    state = invasion.advance(state, grid, registry)
    assert state.invasion is not None
    assert state.invasion.phase is InvasionPhase.ESTABLISH


# --------------------------------------------------------------------- establish control


def test_uncontested_landing_captures_planet_destroys_structures(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = _state(
        {"p1": {"infantry": 2}},
        {_PL1: {"p2": {"spacedock": 1}}},
        {_PL1: "p2"},
    )
    state.players["p2"].controlled_planets = [_PL1]
    state.players["p2"].exhausted_planets = [_PL1]
    state = invasion.begin_invasion(state, grid, registry)
    state = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 2}})
    state = invasion.advance(state, grid, registry)
    assert state.invasion is not None
    assert state.invasion.phase is InvasionPhase.ESTABLISH
    system = state.systems["000"]
    assert system.planet_owners[_PL1] == "p1"
    assert "p2" not in system.planet_units[_PL1]  # dok zniszczony
    assert _PL1 in state.players["p1"].exhausted_planets
    assert _PL1 in state.players["p1"].controlled_planets
    assert _PL1 not in state.players["p2"].controlled_planets
    assert state.invasion.results[0]["outcome"] == "captured"
    assert state.invasion.results[0]["destroyedStructures"] == {"p2": {"spacedock": 1}}
    assert invasion.advance(state, grid, registry).invasion is None


def test_ground_combat_winner_takes_planet(registry: StaticDataRegistry) -> None:
    grid = _grid()
    base = invasion.begin_invasion(
        _state({"p1": {"infantry": 5}}, {_PL2: {"p2": {"infantry": 1}}}, {_PL2: "p2"}),
        grid,
        registry,
    )
    base = invasion.commit_ground_forces(base, registry, {_PL2: {"infantry": 5}})

    def run(s: GameState) -> GameState:
        s = invasion.advance(s, grid, registry)
        assert s.invasion is not None
        assert s.invasion.phase is InvasionPhase.GROUND_COMBAT
        with pytest.raises(ValueError, match="still to be fought"):
            invasion.advance(s, grid, registry)
        s = _fight(s, grid, registry, _PL2)
        return invasion.advance(s, grid, registry)

    result = _seek(
        base,
        run,
        lambda s: s.invasion is not None and s.invasion.results[0]["outcome"] == "captured",
    )
    assert result.systems["000"].planet_owners[_PL2] == "p1"
    assert result.invasion is not None
    assert result.invasion.combat_results[_PL2]["winner"] == "p1"


def test_draw_lets_defender_retain_control(registry: StaticDataRegistry) -> None:
    grid = _grid()
    base = invasion.begin_invasion(
        _state({"p1": {"infantry": 1}}, {_PL2: {"p2": {"infantry": 1}}}, {_PL2: "p2"}),
        grid,
        registry,
    )
    base = invasion.commit_ground_forces(base, registry, {_PL2: {"infantry": 1}})

    def run(s: GameState) -> GameState:
        s = invasion.advance(s, grid, registry)
        s = _fight(s, grid, registry, _PL2)
        return invasion.advance(s, grid, registry)

    result = _seek(
        base,
        run,
        lambda s: s.invasion is not None and s.invasion.results[0]["outcome"] == "retained",
    )
    assert result.systems["000"].planet_owners[_PL2] == "p2"


def test_committing_nothing_skips_to_establish(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = invasion.begin_invasion(_state({"p1": {"infantry": 1}}), grid, registry)
    state = invasion.advance(state, grid, registry)
    assert state.invasion is not None
    assert state.invasion.phase is InvasionPhase.ESTABLISH
    assert state.invasion.results == []


# ---------------------------------------------------------------------------- nawigacja


def test_next_step_blocked_until_invasion_reaches_establish(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = invasion.begin_invasion(_state({"p1": {"infantry": 1}}), grid, registry)
    with pytest.raises(ValueError, match="invasion is in progress"):
        tactical.next_step(state)
    state = invasion.advance(state, grid, registry)  # → ESTABLISH
    moved = tactical.next_step(state)
    assert moved.tactical_step is TacticalStep.PRODUCTION
    assert moved.invasion is None
