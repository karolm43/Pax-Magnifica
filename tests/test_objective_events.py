"""Testy automatycznego zdobywania tajnych celów zdarzeniami (core/objective_events)."""

from __future__ import annotations

import pytest

from src.core import control, objective_events, rules_hooks, turn_flow, unit_ops
from src.core.game_state import (
    ActiveCombat,
    AgendaPhaseState,
    CombatStep,
    GameState,
    InvasionPhase,
    InvasionState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    TimingWindow,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause
from tests.rulings import ruling


@pytest.fixture(scope="module", autouse=True)
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _state(secret: str, holder: str = "p1") -> GameState:
    """p1/p2 (domy 101/102) i system 000 z jednostkami obu stron; ``holder`` trzyma ``secret``."""
    players = {
        "p1": PlayerState(player_id="p1", color="red", home_position="101"),
        "p2": PlayerState(player_id="p2", color="blue", home_position="102"),
    }
    players[holder].private.secret_objectives = [secret]
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players=players,
        systems={
            "000": SystemState(position="000", system_id="18"),
            "101": SystemState(position="101", system_id="18"),
            "102": SystemState(position="102", system_id="18"),
        },
    )


def _combat(
    position: str = "000", kind: str = "space", step: CombatStep = CombatStep.ROLL
) -> ActiveCombat:
    return ActiveCombat(kind=kind, position=position, attacker="p1", defender="p2", step=step)


def _scored(state: GameState, player: str = "p1") -> list[str]:
    return state.players[player].scored_secrets


# --------------------------------------------------------------------- koniec walki


def test_brave_the_void_needs_an_anomaly() -> None:
    grid = HexGrid()
    grid.place_system("000", "18", anomalies={"NEBULA"})
    grid.place_system("101", "18", anomalies=set())
    state = _state("btv")
    objective_events.on_combat_end(state, grid, _combat("101"), "p1")
    assert _scored(state) == []
    objective_events.on_combat_end(state, grid, _combat("000"), "p1")
    assert _scored(state) == ["btv"] and state.players["p1"].victory_points == 1
    assert state.auto_scored[0]["objective"] == "btv"


def test_darken_the_skies_only_in_another_players_home() -> None:
    grid = HexGrid()
    state = _state("dts")
    objective_events.on_combat_end(state, grid, _combat("101"), "p1")  # własny dom
    assert _scored(state) == []
    objective_events.on_combat_end(state, grid, _combat("102"), "p1")
    assert _scored(state) == ["dts"]


def test_spark_a_rebellion_needs_opponent_with_most_points() -> None:
    state = _state("sar")
    state.players["p2"].victory_points = 3
    objective_events.on_combat_end(state, HexGrid(), _combat(), "p1")
    assert _scored(state) == ["sar"]
    low = _state("sar")
    low.players["p1"].victory_points = 5
    low.players["p2"].victory_points = 3
    objective_events.on_combat_end(low, HexGrid(), _combat(), "p1")
    assert _scored(low) == []


def test_betray_a_friend_only_attacker_with_note_owner_snapshot() -> None:
    state = _state("baf")
    state.tactical_pn_owners = ["p2"]
    objective_events.on_combat_end(state, HexGrid(), _combat(), "p1")
    assert _scored(state) == ["baf"]
    defender = _state("baf", holder="p2")
    defender.tactical_pn_owners = ["p1"]
    objective_events.on_combat_end(defender, HexGrid(), _combat(), "p2")  # obrońca wygrywa
    assert _scored(defender, "p2") == []


def test_demonstrate_your_power_needs_three_non_fighter_ships_not_a_win() -> None:
    state = _state("dyp", holder="p2")
    state.systems["000"].space_units["p2"] = {"cruiser": 2, "fighter": 5}
    objective_events.on_combat_end(state, HexGrid(), _combat(), "p1")
    assert _scored(state, "p2") == []
    state.systems["000"].space_units["p2"] = {"cruiser": 2, "dreadnought": 1}
    objective_events.on_combat_end(state, HexGrid(), _combat(), "p1")  # p2 przegrywa, ale ma 3
    assert _scored(state, "p2") == ["dyp"]


def test_unveil_flagship_needs_flagship_in_the_combat_system() -> None:
    state = _state("uf")
    objective_events.on_combat_end(state, HexGrid(), _combat(), "p1")
    assert _scored(state) == []
    state.systems["000"].space_units["p1"] = {"flagship": 1}
    objective_events.on_combat_end(state, HexGrid(), _combat(), "p1")
    assert _scored(state) == ["uf"]


# --------------------------------------------------------------------- zniszczenia


def test_destroy_their_greatest_ship_in_combat() -> None:
    state = _state("dtgs")
    state.active_combat = _combat()
    state.systems["000"].space_units["p2"] = {"warsun": 1}
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p2", "warsun", 1, UnitCause.DESTROYED)
    assert _scored(state) == ["dtgs"]


def test_own_flagship_loss_does_not_score_for_the_opponent() -> None:
    state = _state("dtgs", holder="p2")
    state.active_combat = _combat()
    state.systems["000"].space_units["p2"] = {"flagship": 1}
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p2", "flagship", 1, UnitCause.DESTROYED)
    assert _scored(state, "p2") == []


def test_fight_with_precision_last_fighters_in_afb() -> None:
    state = _state("fwp")
    state.active_combat = _combat(step=CombatStep.AFB)
    state.systems["000"].space_units["p2"] = {"fighter": 3}
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p2", "fighter", 2, UnitCause.DESTROYED)
    assert _scored(state) == []  # zostały jeszcze myśliwce
    unit_ops.remove_units(state, system, "space", "p2", "fighter", 1, UnitCause.DESTROYED)
    assert _scored(state) == ["fwp"]


def test_turn_their_fleets_to_dust_in_space_cannon_offense() -> None:
    state = _state("ttfd", holder="p2")
    state.tactical_step = TacticalStep.SPACE_CANNON
    state.active_system = "000"
    state.pending_window = TimingWindow(
        window_type=WindowType.SPACE_CANNON, queue=["p2"], context={"roller": "p2", "target": "p1"}
    )
    state.systems["000"].space_units["p1"] = {"cruiser": 2}
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p1", "cruiser", 1, UnitCause.DESTROYED)
    assert _scored(state, "p2") == []
    unit_ops.remove_units(state, system, "space", "p1", "cruiser", 1, UnitCause.DESTROYED)
    assert _scored(state, "p2") == ["ttfd"]


def test_make_an_example_of_their_world_in_bombardment() -> None:
    state = _state("mew")
    state.invasion = InvasionState(position="000", attacker="p1", phase=InvasionPhase.BOMBARDMENT)
    system = state.systems["000"]
    system.planet_units["pl"] = {"p2": {"infantry": 2}}
    unit_ops.remove_units(state, system, "pl", "p2", "infantry", 1, UnitCause.DESTROYED)
    assert _scored(state) == []
    unit_ops.remove_units(state, system, "pl", "p2", "infantry", 1, UnitCause.DESTROYED)
    assert _scored(state) == ["mew"]


# --------------------------------------------------------------------- pozostałe


def test_become_a_martyr_when_a_home_system_planet_is_lost() -> None:
    state = _state("bam")
    state.systems["101"].planet_owners["pl"] = "p1"
    control.set_planet_control(state, "101", "pl", "p2")
    assert _scored(state) == ["bam"]
    outside = _state("bam")
    outside.systems["000"].planet_owners["pl"] = "p1"
    control.set_planet_control(outside, "000", "pl", "p2")
    assert _scored(outside) == []


def test_prove_endurance_for_the_last_player_to_pass() -> None:
    state = _state("pe")
    state.players["p2"].passed = True
    state.players["p1"].strategy_cards = [1]
    state.players["p1"].exhausted_strategy_cards = [1]
    state = turn_flow.pass_turn(state, "p1")
    assert _scored(state) == ["pe"]


def test_drive_the_debate_scores_for_elected_player_and_planet_owner() -> None:
    state = _state("dtd", holder="p2")
    objective_events.on_agenda_resolving(state, "for_against", "p2")
    assert _scored(state, "p2") == []  # For/Against nie liczy się
    objective_events.on_agenda_resolving(state, "player", "p2")
    assert _scored(state, "p2") == ["dtd"]
    planet = _state("dtd")
    planet.systems["000"].planet_owners["pl"] = "p1"
    objective_events.on_agenda_resolving(planet, "planet", "pl")
    assert _scored(planet) == ["dtd"]


def test_dictate_policy_after_third_law() -> None:
    state = _state("dp")
    state.agenda = AgendaPhaseState()
    state.decks.agenda_laws = {"a": "for", "b": "for"}
    objective_events.on_laws_changed(state)
    assert _scored(state) == []
    state.decks.agenda_laws["c"] = "for"
    objective_events.on_laws_changed(state)
    assert _scored(state) == ["dp"]


def test_secret_not_in_hand_is_never_scored() -> None:
    state = _state("btv", holder="p2")
    grid = HexGrid()
    grid.place_system("000", "18", anomalies={"NEBULA"})
    objective_events.on_combat_end(state, grid, _combat("000"), "p1")
    assert _scored(state) == [] and state.players["p1"].victory_points == 0


def test_unveil_flagship_is_lost_when_flagship_dies_in_the_combat_even_if_replaced() -> None:
    state = _state("uf")
    state.active_combat = _combat()
    system = state.systems["000"]
    system.space_units["p1"] = {"flagship": 1}
    unit_ops.remove_units(state, system, "space", "p1", "flagship", 1, UnitCause.DESTROYED)
    assert state.active_combat.flagships_destroyed == ["p1"]
    system.space_units["p1"] = {"flagship": 1}  # późniejszy efekt stawia go z powrotem
    objective_events.on_combat_end(state, HexGrid(), state.active_combat, "p1")
    assert _scored(state) == []


def test_own_destruction_by_an_effect_does_not_credit_the_opponent() -> None:
    """Crown of Thalnos niszczy własne jednostki: przeciwnik nie zdobywa dtgs."""
    state = _state("dtgs", holder="p2")
    state.active_combat = _combat()
    system = state.systems["000"]
    system.space_units["p1"] = {"warsun": 1}
    state.destroyed_by = "p1"
    unit_ops.remove_units(state, system, "space", "p1", "warsun", 1, UnitCause.DESTROYED)
    state.destroyed_by = None
    assert _scored(state, "p2") == []


# --------------------------------------------------------------------- limit celów na walkę


@ruling("R_objective_cards/rules-reference/7", "R_objective_cards/notes/6.1")
def test_only_one_objective_during_and_after_one_combat() -> None:
    """Fight with Precision w kroku AFB zużywa limit tej walki: po walce Brave the Void nie."""
    grid = HexGrid()
    grid.place_system("000", "18", anomalies={"NEBULA"})
    state = _state("fwp")
    state.players["p1"].private.secret_objectives = ["fwp", "btv"]
    combat = _combat(step=CombatStep.AFB)
    state.active_combat = combat
    state.systems["000"].space_units["p2"] = {"fighter": 1}
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p2", "fighter", 1, UnitCause.DESTROYED)
    assert _scored(state) == ["fwp"]
    combat.step = CombatStep.DONE
    objective_events.on_combat_end(state, grid, combat, "p1")
    assert _scored(state) == ["fwp"] and state.players["p1"].victory_points == 1


@ruling("R_objective_cards/rules-reference/7.1", "R_objective_cards/notes/5")
def test_each_combat_has_its_own_objective_limit() -> None:
    grid = HexGrid()
    grid.place_system("000", "18", anomalies={"NEBULA"})
    state = _state("btv")
    state.players["p1"].private.secret_objectives = ["btv", "dts"]
    objective_events.on_combat_end(state, grid, _combat("000"), "p1")
    objective_events.on_combat_end(state, grid, _combat("102", kind="ground"), "p1")
    assert _scored(state) == ["btv", "dts"]


@ruling("R_objective_cards/notes/6")
def test_space_cannon_scoring_is_outside_combat_limit() -> None:
    state = _state("ttfd", holder="p2")
    state.tactical_step = TacticalStep.SPACE_CANNON
    state.active_system = "000"
    state.pending_window = TimingWindow(
        window_type=WindowType.SPACE_CANNON, context={"roller": "p2"}
    )
    state.systems["000"].space_units["p1"] = {"cruiser": 1}
    system = state.systems["000"]
    unit_ops.remove_units(state, system, "space", "p1", "cruiser", 1, UnitCause.DESTROYED)
    assert _scored(state, "p2") == ["ttfd"]
    assert state.active_combat is None  # poza walką: nic nie liczy się do limitu walki


@ruling("C_relics/neuraloop/10")
def test_neuraloop_public_secret_and_own_secret_share_the_combat_limit() -> None:
    """Cel tajny odkryty przez Neuraloop jest publiczny: zdobywa go każdy, ale w tej samej walce
    gracz nie zdobędzie już własnego tajnego celu."""
    grid = HexGrid()
    grid.place_system("000", "18", anomalies={"NEBULA"})
    state = _state("btv")
    state.objectives.revealed = ["dyp"]
    state.systems["000"].space_units["p1"] = {"cruiser": 3}
    combat = _combat(step=CombatStep.DONE)
    objective_events.on_combat_end(state, grid, combat, "p1")
    assert state.objectives.scored.get("dyp") == ["p1"]
    assert _scored(state) == []  # btv czeka: limit tej walki zużyty
