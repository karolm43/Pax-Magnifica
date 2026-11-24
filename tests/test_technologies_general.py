"""Testy technologii ogólnych jako hooków (RULES.md 55): efekty pasywne w regułach bazowych."""

from __future__ import annotations

import pytest

from src.core import (
    action_budget,
    component_action,
    dice,
    rules_hooks,
    space_cannon,
    turn_flow,
)
from src.core.game_state import GameState, Phase, PlayerState, StatusStep, SystemState
from src.core.hooks import technologies as tech_hooks
from src.core.production import order_cost
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_space_cannon import _grid as sc_grid
from tests.test_space_cannon import _state as sc_state
from tests.test_status_phase import _enter_status, _finish_all_scoring
from tests.test_status_phase import _state as status_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def test_aliasy_technologii_istnieja_w_danych(registry: StaticDataRegistry) -> None:
    for alias in (
        tech_hooks.ANTIMASS_ALIAS,
        tech_hooks.LIGHT_WAVE_ALIAS,
        tech_hooks.SARWEEN_ALIAS,
        tech_hooks.PLASMA_SCORING_ALIAS,
        tech_hooks.NEURAL_MOTIVATOR_ALIAS,
        tech_hooks.HYPER_METABOLISM_ALIAS,
        tech_hooks.FLEET_LOGISTICS_ALIAS,
        *tech_hooks.UNIT_UPGRADE_ALIASES,
    ):
        assert alias in registry.technologies, alias


def test_ulepszenia_jednostek_sa_pokryte_danymi() -> None:
    covered = rules_hooks.covered_components()
    for alias in tech_hooks.UNIT_UPGRADE_ALIASES:
        assert f"technologies:{alias}" in covered


# --- Light/Wave Deflector ----------------------------------------------------------------


def test_light_wave_pozwala_przechodzic_przez_cudze_statki() -> None:
    point = rules_hooks.POINT_MOVEMENT_PASS_FOREIGN_SHIPS
    player = PlayerState(player_id="p1", color="red", technologies=["lwd"])
    with_tech = GameState(players={"p1": player})
    without = GameState(players={"p1": PlayerState(player_id="p1", color="red")})
    assert rules_hooks.permits(point, with_tech, "p1", {"position": "101"})
    assert not rules_hooks.permits(point, without, "p1", {"position": "101"})


# --- Fleet Logistics ---------------------------------------------------------------------


def _action_state(techs: list[str]) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", technologies=techs),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
    )


def test_bez_fleet_logistics_jedna_akcja_na_ture() -> None:
    state = component_action.play_component_action(_action_state([]), "p1")
    assert action_budget.actions_left(state, "p1") == 0
    with pytest.raises(ValueError, match="already took an action"):
        component_action.play_component_action(state, "p1")


def test_fleet_logistics_daje_druga_akcje_ale_nie_trzecia() -> None:
    state = component_action.play_component_action(_action_state(["fl"]), "p1")
    assert action_budget.actions_left(state, "p1") == 1
    state = component_action.play_component_action(state, "p1")
    assert state.players["p1"].actions_this_turn == 2
    assert action_budget.actions_left(state, "p1") == 0
    with pytest.raises(ValueError, match="already took an action"):
        component_action.play_component_action(state, "p1")


@ruling("C_technology/fleet-logistics/4")
def test_fleet_logistics_pozwala_oddac_ture_po_jednej_akcji_i_zeruje_licznik() -> None:
    state = component_action.play_component_action(_action_state(["fl"]), "p1")
    state = turn_flow.end_turn(state, "p1")
    assert state.active_player_id == "p2"
    state = component_action.play_component_action(state, "p2")
    state = turn_flow.end_turn(state, "p2")
    assert state.active_player_id == "p1"
    assert state.players["p1"].actions_this_turn == 0
    assert not state.players["p1"].took_action_this_turn


def test_fleet_logistics_druga_akcja_wymaga_domkniecia_pierwszej() -> None:
    state = component_action.play_component_action(_action_state(["fl"]), "p1")
    state.active_system = "000"  # trwa akcja taktyczna
    with pytest.raises(ValueError, match="Finish your current action"):
        action_budget.require_free_action(state, "p1")


# --- Neural Motivator / Hyper Metabolism -------------------------------------------------


def test_neural_motivator_i_hyper_metabolism_zmieniaja_liczby_w_statusie(
    registry: StaticDataRegistry,
) -> None:
    state = _finish_all_scoring(_enter_status(status_state(registry)), registry)
    assert state.status is not None and state.status.step is StatusStep.REDISTRIBUTE
    # Gracze bez technologii: 2 żetony do rozdania.
    assert state.status.unassigned_cc["p1"] == 2

    base = _enter_status(status_state(registry))
    base.players["p1"].technologies = ["nm", "hm"]
    base.decks.action_card_deck = ["a1", "a2", "a3", "a4", "a5", "a6"]
    base.players["p1"].private.action_cards = []
    out = _finish_all_scoring(base, registry)
    assert out.status is not None
    assert out.status.unassigned_cc["p1"] == 3  # Hyper Metabolism
    assert out.status.unassigned_cc["p2"] == 2
    assert len(out.players["p1"].private.action_cards) == 2  # Neural Motivator
    assert len(out.players["p2"].private.action_cards) == 1


def test_hyper_metabolism_nie_przekracza_rezerwy(registry: StaticDataRegistry) -> None:
    base = _enter_status(status_state(registry))
    base.players["p1"].technologies = ["hm"]
    base.players["p1"].cc_reinf = 1
    for system in base.systems.values():  # krok 4 nie zwróci żetonów p1 do rezerwy
        system.command_tokens = [t for t in system.command_tokens if t != "p1"]
    out = _finish_all_scoring(base, registry)
    assert out.status is not None and out.status.unassigned_cc["p1"] == 1


# --- Space Cannon: Plasma Scoring / Antimass ---------------------------------------------


def _fire(
    state: GameState,
    registry: StaticDataRegistry,
    shooter: str = "p2",
    plasma: bool = False,
) -> GameState:
    opened = space_cannon.open_offense(state, sc_grid(), registry)
    plasma_unit = None
    if plasma:  # gracz wskazuje jednostkę z dodatkową kością (pierwsza grupa strzelców)
        plasma_unit = space_cannon.offense_shooters(opened, sc_grid(), registry, shooter)[0].key
    return space_cannon.fire_offense(
        opened, sc_grid(), registry, shooter, "p1", plasma_unit=plasma_unit
    )


@ruling("C_technology/plasma-scoring/1")
def test_plasma_scoring_dodaje_jedna_kosc_space_cannon_tylko_na_wybor(
    registry: StaticDataRegistry,
) -> None:
    ships = {"p1": {"destroyer": 1}}
    plain = _fire(sc_state(pds={"p2": 2}, ships=ships), registry)
    # Bez wskazania jednostki Plasma Scoring nie dodaje kości (decyzja gracza, "may").
    declined = _fire(sc_state(pds={"p2": 2}, ships=ships, techs={"p2": ["ps"]}), registry)
    boosted = _fire(
        sc_state(pds={"p2": 2}, ships=ships, techs={"p2": ["ps"]}), registry, plasma=True
    )
    plain_roll = space_cannon.read_log(plain)[0]["rolls"][0]
    boosted_roll = space_cannon.read_log(boosted)[0]["rolls"][0]
    assert len(plain_roll["dice"]) == 2
    assert len(space_cannon.read_log(declined)[0]["rolls"][0]["dice"]) == 2
    assert len(boosted_roll["dice"]) == 3  # +1 kość dla jednej jednostki
    assert boosted_roll["extraDice"] == 1


def test_plasma_scoring_bez_technologii_odrzuca_wybor(registry: StaticDataRegistry) -> None:
    ships = {"p1": {"destroyer": 1}}
    with pytest.raises(ValueError, match="Plasma Scoring"):
        _fire(sc_state(pds={"p2": 2}, ships=ships), registry, plasma=True)


@ruling("C_technology/antimass-deflectors/1")
def test_antimass_odejmuje_jeden_od_wyniku_kosci_space_cannon(
    registry: StaticDataRegistry,
) -> None:
    ships = {"p1": {"destroyer": 1}}
    fewer_hits_seen = False
    for seed in range(1, 40):
        plain = _fire(sc_state(pds={"p2": 12}, ships=ships, seed=seed), registry)
        shielded = _fire(
            sc_state(pds={"p2": 12}, ships=ships, techs={"p1": ["amd"]}, seed=seed), registry
        )
        plain_roll = space_cannon.read_log(plain)[0]["rolls"][0]
        shielded_roll = space_cannon.read_log(shielded)[0]["rolls"][0]
        assert plain_roll["dice"] == shielded_roll["dice"]  # to samo ziarno = te same kości
        # Modyfikator trafia do dziennika, żeby UI mogło go pokazać.
        assert plain_roll["modifier"] == 0 and shielded_roll["modifier"] == -1
        hits_on = plain_roll["hitsOn"]
        assert plain_roll["hits"] == dice.count_hits(plain_roll["dice"], hits_on)
        # -1 do wyniku kości = próg o 1 wyższy
        assert shielded_roll["hits"] == dice.count_hits(shielded_roll["dice"], hits_on + 1)
        fewer_hits_seen = fewer_hits_seen or shielded_roll["hits"] < plain_roll["hits"]
    assert fewer_hits_seen


# --- Sarween Tools -----------------------------------------------------------------------


def test_sarween_tools_obniza_koszt_pierwszego_zamowienia_o_1(
    registry: StaticDataRegistry,
) -> None:
    from src.core.production import ProductionOrder

    orders = [ProductionOrder("cruiser", 2)]
    state = GameState(
        active_system="000",
        players={"p1": PlayerState(player_id="p1", color="red", technologies=[])},
    )
    base = order_cost(state, registry, "p1", orders)
    state.players["p1"].technologies = ["st"]
    assert order_cost(state, registry, "p1", orders) == base - 1
    state.production_used = 1  # kolejne zamówienie w tym samym użyciu PRODUCTION
    assert order_cost(state, registry, "p1", orders) == base


def test_sarween_tools_nie_schodzi_ponizej_zera(registry: StaticDataRegistry) -> None:
    from src.core.production import ProductionOrder

    state = GameState(
        active_system="000",
        players={"p1": PlayerState(player_id="p1", color="red", technologies=["st"])},
    )
    assert order_cost(state, registry, "p1", [ProductionOrder("fighter", 1)]) >= 0
    assert order_cost(state, registry, "p1", []) == 0


# --- Plasma Scoring: Bombardment ---------------------------------------------------------


def test_plasma_scoring_punkt_bombardmentu_zwraca_jedna_kosc() -> None:
    state = GameState(
        players={"p1": PlayerState(player_id="p1", color="red", technologies=["ps"])},
        systems={"000": SystemState(position="000", system_id="18")},
    )
    assert rules_hooks.modify(rules_hooks.POINT_BOMBARDMENT_EXTRA_DICE, state, "p1", 0) == 1
    assert rules_hooks.modify(rules_hooks.POINT_BOMBARDMENT_EXTRA_DICE, state, "p2", 0) == 0
