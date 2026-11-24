"""Przegląd technologii ogólnych vs C_technology: Fighter II, Predictive Intelligence, X-89 ΩΩ,
wskaźniki aktywnych technologii (UI)."""

from __future__ import annotations

import pytest

from src.core import agenda_phase, capacity, fleet_pool, invasion, tech_effects, technology
from src.core.game_state import (
    ActiveCombat,
    AgendaPhaseState,
    CombatStep,
    GameState,
    InvasionState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_agenda_phase import DIRECTIVE, LAW, _planet_of, _state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


# --- wskaźniki UI ------------------------------------------------------------------------


def test_every_generic_tech_has_ui_contexts(registry: StaticDataRegistry) -> None:
    """Nowa technologia ogólna bez wpisu w TECH_CONTEXTS = czerwony test (brak wskaźnika w UI)."""
    missing = set(technology.generic_pool(registry)) - set(tech_effects.TECH_CONTEXTS)
    assert not missing


def test_active_techs_reports_state(registry: StaticDataRegistry) -> None:
    state = GameState(
        players={
            "p1": PlayerState(
                player_id="p1",
                color="red",
                technologies=["st", "pi", "gd", "zzz"],
                exhausted_technologies=["pi"],
            )
        }
    )
    rows = {r["alias"]: r for r in tech_effects.active_techs(state, registry, "p1")}
    assert set(rows) == {"st", "pi", "gd"}  # nieznany alias pominięty
    assert rows["st"]["state"] == "active" and "production" in rows["st"]["contexts"]
    assert rows["pi"]["state"] == "exhausted" and "agenda" in rows["pi"]["contexts"]
    assert rows["gd"]["contexts"] == ["movement"]


# --- Fighter II ---------------------------------------------------------------------------


def _fleet_state(techs: list[str], units: dict[str, int], pool: int = 3) -> GameState:
    system = SystemState(position="000", system_id="18")
    system.space_units["p1"] = dict(units)
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=TacticalStep.MOVEMENT,
        seating_order=["p1"],
        players={
            "p1": PlayerState(player_id="p1", color="p1", fleet_cc=pool, technologies=techs)
        },
        systems={"000": system},
        rng_seed=1,
    )


def test_fighter_ii_overflow_counts_against_fleet_pool(registry: StaticDataRegistry) -> None:
    # 1 carrier (capacity 4) + 7 fighters => 3 myśliwce ponad capacity.
    units = {"carrier": 1, "fighter": 7}
    without = fleet_pool.fleet_report(_fleet_state([], units), "000", "p1", registry)
    assert without.ships == {"carrier": 1}
    state = _fleet_state(["ff2"], units)
    report = fleet_pool.fleet_report(state, "000", "p1", registry)
    cap = capacity.capacity_report(state, registry, "000", "p1")
    assert report.ships["fighter"] == cap.fleet_fighters > 0
    assert report.total == 1 + cap.fleet_fighters
    # Z Fighter II nadmiar myśliwców nie jest nadwyżką capacity (idzie do fleet pool).
    assert cap.excess == 0
    assert capacity.capacity_report(_fleet_state([], units), registry, "000", "p1").excess > 0


def test_fighter_ii_fleet_removal_accepts_fighters(registry: StaticDataRegistry) -> None:
    state = _fleet_state(["ff2"], {"carrier": 1, "fighter": 7}, pool=1)
    report = fleet_pool.fleet_report(state, "000", "p1", registry)
    assert report.excess == report.total - 1
    fleet_pool.check_removal(report, {"fighter": report.excess})


def test_fighter_ii_overflow_ignored_during_combat(registry: StaticDataRegistry) -> None:
    # R_fleet_pool, Notes: w trakcie walki dowolna liczba Fighter II, bez capacity i fleet pool;
    # statki nie-myśliwskie liczą się do puli zawsze (RULES.md 42.1).
    state = _fleet_state(["ff2"], {"carrier": 1, "fighter": 7}, pool=1)
    state.active_combat = ActiveCombat(kind="space", position="000", attacker="p1", defender="p2")
    report = fleet_pool.fleet_report(state, "000", "p1", registry)
    assert report.ships == {"carrier": 1} and report.excess == 0
    assert fleet_pool.players_with_excess(state, "000") == []
    no_ff2 = _fleet_state([], {"carrier": 1, "fighter": 7})
    no_ff2.active_combat = state.active_combat
    assert capacity.players_with_excess(no_ff2, registry, "000") == []
    # Po zakończeniu walki oba limity wracają.
    state.active_combat.step = CombatStep.DONE
    assert fleet_pool.fleet_report(state, "000", "p1", registry).excess > 0
    no_ff2.active_combat.step = CombatStep.DONE
    assert capacity.players_with_excess(no_ff2, registry, "000") == ["p1"]


# --- Predictive Intelligence --------------------------------------------------------------


def test_predictive_intelligence_adds_three_votes(registry: StaticDataRegistry) -> None:
    state = agenda_phase.reveal_agenda(_state(registry, [LAW, DIRECTIVE]), registry, "p2")
    planet = _planet_of(state, "p3")
    state.players["p3"].technologies = ["pi"]
    base = agenda_phase.cast_vote(state, registry, "p3", "for", [planet])
    boosted = agenda_phase.cast_vote(state, registry, "p3", "for", [planet], use_predictive=True)
    assert boosted.agenda is not None and base.agenda is not None
    assert boosted.agenda.votes["p3"].votes == base.agenda.votes["p3"].votes + 3
    assert boosted.agenda.votes["p3"].techs == ["pi"]


@ruling("C_technology/predictive-intelligence/1")
def test_predictive_intelligence_requires_ready_card(registry: StaticDataRegistry) -> None:
    state = agenda_phase.reveal_agenda(_state(registry, [LAW, DIRECTIVE]), registry, "p2")
    planet = _planet_of(state, "p3")
    with pytest.raises(ValueError, match="Predictive Intelligence"):
        agenda_phase.cast_vote(state, registry, "p3", "for", [planet], use_predictive=True)
    state.players["p3"].technologies = ["pi"]
    state.players["p3"].exhausted_technologies = ["pi"]
    with pytest.raises(ValueError, match="Predictive Intelligence"):
        agenda_phase.cast_vote(state, registry, "p3", "for", [planet], use_predictive=True)


def test_predictive_intelligence_exhausts_only_when_outcome_loses(
    registry: StaticDataRegistry,
) -> None:
    def resolved(winning: str) -> GameState:
        state = agenda_phase.reveal_agenda(_state(registry, [LAW, DIRECTIVE]), registry, "p2")
        state.players["p3"].technologies = ["pi"]
        state = agenda_phase.cast_vote(
            state, registry, "p3", "for", [_planet_of(state, "p3")], use_predictive=True
        )
        # Wynik rozstrzyga się inaczej niż głos p3 (np. remis rozstrzygnięty przez mówcę).
        work = state.clone()
        agenda_phase._resolve(work, registry, winning, by_speaker=True)
        return work

    won = resolved("for")  # głos p3 przeszedł - karta zostaje gotowa
    lost = resolved("against")  # głos p3 przegrał - karta się wyczerpuje
    assert isinstance(won.agenda, AgendaPhaseState)
    assert "pi" not in won.players["p3"].exhausted_technologies
    assert "pi" in lost.players["p3"].exhausted_technologies


# --- X-89 ΩΩ: bombardowanie planety bez sił naziemnych -------------------------------------


@ruling("C_technology/x89-bacterial-weapon-omega-omega/7")
def test_x89_allows_bombarding_empty_enemy_planet(registry: StaticDataRegistry) -> None:
    planets = sorted(p for p in registry.planets if registry.planets[p].resources >= 0)
    planet = next(
        p for p in planets if p in {pl for s in registry.systems.values() for pl in s.planets}
    )
    system_id = next(sid for sid, s in registry.systems.items() if planet in s.planets)

    def build(techs: list[str]) -> GameState:
        system = SystemState(position="101", system_id=system_id, planet_owners={planet: "p2"})
        return GameState(
            phase=Phase.ACTION,
            active_player_id="p1",
            active_system="101",
            tactical_step=TacticalStep.INVASION,
            seating_order=["p1", "p2"],
            players={
                "p1": PlayerState(player_id="p1", color="red", technologies=techs),
                "p2": PlayerState(player_id="p2", color="blue"),
            },
            systems={"101": system},
            invasion=InvasionState(position="101", attacker="p1"),
        )

    assert invasion.bombard_targets(build([]), registry) == []
    assert planet in invasion.bombard_targets(build(["x89c4"]), registry)
