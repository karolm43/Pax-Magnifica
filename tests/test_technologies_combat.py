"""Testy technologii bojowych jako hooków (RULES.md 55.5-55.7)."""

from __future__ import annotations

import pytest

from src.core import battle, damage, movement, rules_hooks, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import CombatStep, GameState, Phase, PlayerState, SystemState, TacticalStep
from src.core.hex_grid import HexGrid
from src.core.hooks import technologies_combat as combat_hooks
from src.core.registry import StaticDataRegistry
from tests.test_battle import _grid as battle_grid
from tests.test_battle import _state as battle_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _with_tech(state: GameState, player_id: str, *techs: str) -> GameState:
    state.players[player_id].technologies = list(techs)
    return state


def test_aliasy_i_zastapione_wersje(registry: StaticDataRegistry) -> None:
    for alias in (
        combat_hooks.GRAVITY_DRIVE_ALIAS,
        combat_hooks.DURANIUM_ARMOR_ALIAS,
        combat_hooks.ASSAULT_CANNON_ALIAS,
        combat_hooks.MAGEN_ALIAS,
        combat_hooks.X89_ALIAS,
        "md_base",
        "md_c1",
        "x89_base",
        "x89",
    ):
        assert alias in registry.technologies, alias
    covered = rules_hooks.covered_components()
    for alias in ("gd", "da", "asc", "md", "x89c4", "md_base", "md_c1", "x89_base", "x89"):
        assert f"technologies:{alias}" in covered, alias


# --- Duranium Armor ----------------------------------------------------------------------


def _round_end(state: GameState, sustained: dict[str, dict[str, int]] | None = None) -> None:
    triggers.fire(
        state, GameEvent.COMBAT_ROUND, Moment.END,
        ctx={
            "kind": "space", "round": 1, "position": "000", "planet": "",
            "attacker": "p1", "defender": "p2", "phase": "combat",
            "sustained": sustained or {},
        },
    )


def test_duranium_armor_naprawia_jedna_uszkodzona_jednostke_po_rundzie() -> None:
    state = _with_tech(battle_state({"p1": {"dreadnought": 2}, "p2": {"cruiser": 1}}), "p1", "da")
    system = state.systems["000"]
    damage.set_damaged(system, "space", "p1", "dreadnought", 2)
    _round_end(state)
    assert damage.damaged_count(system, "space", "p1", "dreadnought") == 1  # tylko jedna


def test_duranium_armor_nie_naprawia_jednostki_ktora_uzyla_sustain_damage_w_tej_rundzie() -> None:
    state = _with_tech(battle_state({"p1": {"dreadnought": 1}, "p2": {"cruiser": 1}}), "p1", "da")
    system = state.systems["000"]
    damage.set_damaged(system, "space", "p1", "dreadnought", 1)
    _round_end(state, {"p1": {"dreadnought": 1}})
    assert damage.damaged_count(system, "space", "p1", "dreadnought") == 1


def test_duranium_armor_nie_dziala_poza_walka_i_bez_technologii() -> None:
    state = battle_state({"p1": {"dreadnought": 1}, "p2": {"cruiser": 1}})
    damage.set_damaged(state.systems["000"], "space", "p1", "dreadnought", 1)
    _round_end(state)  # bez technologii
    assert damage.damaged_count(state.systems["000"], "space", "p1", "dreadnought") == 1
    _with_tech(state, "p1", "da")
    triggers.fire(  # krok AFB to nie runda rzutów
        state, GameEvent.COMBAT_ROUND, Moment.END,
        ctx={"kind": "space", "position": "000", "planet": "", "attacker": "p1",
             "defender": "p2", "phase": "afb", "sustained": {}},
    )
    assert damage.damaged_count(state.systems["000"], "space", "p1", "dreadnought") == 1


# --- Assault Cannon ----------------------------------------------------------------------


def test_assault_cannon_wymaga_trzech_statkow_niemyslihwskich(
    registry: StaticDataRegistry,
) -> None:
    state = _with_tech(
        battle_state({"p1": {"cruiser": 2, "fighter": 5}, "p2": {"cruiser": 1, "destroyer": 1}}),
        "p1",
        "asc",
    )
    started = battle.start_combat(state, battle_grid(), registry)
    assert started.systems["000"].space_units["p2"] == {"cruiser": 1, "destroyer": 1}


def test_assault_cannon_moze_zakonczyc_walke_zanim_sie_zacznie(
    registry: StaticDataRegistry,
) -> None:
    state = _with_tech(
        battle_state({"p1": {"cruiser": 3}, "p2": {"cruiser": 1}}), "p1", "asc"
    )
    started = battle.start_combat(state, battle_grid(), registry)
    combat = started.active_combat
    assert combat is not None and combat.step is CombatStep.DONE
    assert combat.winner == "p1"
    assert "p2" not in started.systems["000"].space_units or not started.systems[
        "000"
    ].space_units["p2"]


def test_assault_cannon_obu_stron_pierwszy_w_inicjatywie_moze_odebrac_warunek(
    registry: StaticDataRegistry,
) -> None:
    # Atakujący (aktywny, p1) rozstrzyga pierwszy i zabija statek obrońcy z 3 do 2 -
    # obrońca traci prawo do własnego Assault Cannon.
    state = battle_state({"p1": {"cruiser": 3}, "p2": {"cruiser": 3}})
    _with_tech(state, "p1", "asc")
    _with_tech(state, "p2", "asc")
    started = battle.start_combat(state, battle_grid(), registry)
    assert started.systems["000"].space_units["p1"] == {"cruiser": 3}
    assert started.systems["000"].space_units["p2"] == {"cruiser": 2}


# --- Magen Defense Grid ΩΩ ----------------------------------------------------------------


def test_magen_stawia_piechote_przy_kazdej_strukturze_gdy_ktokolwiek_aktywuje_system() -> None:
    state = _with_tech(battle_state({"p1": {"cruiser": 1}}), "p2", "md")
    state.systems["000"].planet_units["pl"] = {"p2": {"pds": 1, "spacedock": 1, "infantry": 1}}
    triggers.fire(
        state, GameEvent.SYSTEM_ACTIVATED, Moment.WHEN,
        ctx={"player": "p1", "position": "000"},
    )
    assert state.systems["000"].planet_units["pl"]["p2"]["infantry"] == 3


def test_magen_trafia_siły_naziemne_przeciwnika_na_starcie_walki(
    registry: StaticDataRegistry,
) -> None:
    state = battle_state(
        planet={"p1": {"infantry": 2}, "p2": {"infantry": 2, "pds": 1}},
    )
    state.tactical_step = TacticalStep.INVASION
    _with_tech(state, "p2", "md")
    started = battle.start_combat(state, battle_grid(), registry, "pl")
    assert started.systems["000"].planet_units["pl"]["p1"] == {"infantry": 1}


def test_magen_moze_wygrac_walke_zabijajac_ostatnia_jednostke(
    registry: StaticDataRegistry,
) -> None:
    state = battle_state(planet={"p1": {"infantry": 1}, "p2": {"infantry": 1, "pds": 1}})
    state.tactical_step = TacticalStep.INVASION
    _with_tech(state, "p2", "md")
    started = battle.start_combat(state, battle_grid(), registry, "pl")
    combat = started.active_combat
    assert combat is not None and combat.step is CombatStep.DONE and combat.winner == "p2"


def test_magen_mech_z_sustain_damage_zostaje_uszkodzony_zamiast_zginac(
    registry: StaticDataRegistry,
) -> None:
    state = battle_state(planet={"p1": {"mech": 1}, "p2": {"infantry": 2, "pds": 1}})
    state.tactical_step = TacticalStep.INVASION
    _with_tech(state, "p2", "md")
    started = battle.start_combat(state, battle_grid(), registry, "pl")
    system = started.systems["000"]
    assert system.planet_units["pl"]["p1"] == {"mech": 1}
    assert damage.damaged_count(system, "pl", "p1", "mech") == 1


def test_magen_bez_struktury_nie_dziala(registry: StaticDataRegistry) -> None:
    state = battle_state(planet={"p1": {"infantry": 2}, "p2": {"infantry": 2}})
    state.tactical_step = TacticalStep.INVASION
    _with_tech(state, "p2", "md")
    started = battle.start_combat(state, battle_grid(), registry, "pl")
    assert started.systems["000"].planet_units["pl"]["p1"] == {"infantry": 2}


# --- X-89 ΩΩ -------------------------------------------------------------------------------


def test_x89_podwaja_trafienia_naziemne_i_bombardowania_ale_nie_kosmiczne() -> None:
    state = _with_tech(battle_state({"p1": {"cruiser": 1}}), "p1", "x89c4")
    point = rules_hooks.POINT_COMBAT_HIT_MULTIPLIER
    assert rules_hooks.modify(point, state, "p1", 1, {"kind": "ground"}) == 2
    assert rules_hooks.modify(point, state, "p1", 1, {"kind": "bombardment"}) == 2
    assert rules_hooks.modify(point, state, "p1", 1, {"kind": "space"}) == 1
    assert rules_hooks.modify(point, state, "p2", 1, {"kind": "ground"}) == 1


def test_x89_podwojone_trafienia_w_prawdziwym_rzucie_walki_naziemnej(
    registry: StaticDataRegistry,
) -> None:
    doubled_somewhere = False
    for seed in range(1, 40):
        plain = battle_state(
            planet={"p1": {"infantry": 4}, "p2": {"infantry": 4}}, seed=seed
        )
        plain.tactical_step = TacticalStep.INVASION
        boosted = plain.clone()
        _with_tech(boosted, "p1", "x89c4")
        results = []
        for state in (plain, boosted):
            started = battle.start_combat(state, battle_grid(), registry, "pl")
            rolled = battle.roll_round(started, battle_grid(), registry)
            assert rolled.active_combat is not None
            results.append(rolled.active_combat.log[-1]["hits"]["p1"])
        assert results[1] == 2 * results[0]
        doubled_somewhere = doubled_somewhere or results[0] > 0
    assert doubled_somewhere


def test_x89_wyczerpuje_bombardowane_planety() -> None:
    state = _with_tech(battle_state({"p1": {"dreadnought": 1}}), "p1", "x89c4")
    state.players["p2"].controlled_planets = ["pl", "other"]
    triggers.fire(
        state, GameEvent.UNIT_ABILITY_USED, Moment.AFTER, subject="p1",
        ctx={"ability": "bombardment", "player": "p1", "position": "000", "planets": ["pl"]},
    )
    assert state.players["p2"].exhausted_planets == ["pl"]


# --- Gravity Drive ------------------------------------------------------------------------


def _far_grid() -> HexGrid:
    grid = HexGrid()
    for pos, sid in [("000", "18"), ("101", "20"), ("102", "22"), ("103", "23"),
                     ("104", "24"), ("105", "25"), ("106", "26"), ("201", "21")]:
        grid.place_system(pos, sid, anomalies=set())
    grid.build_edges()
    return grid


def _far_state(count: int, techs: list[str]) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={"p1": PlayerState(player_id="p1", color="red", technologies=techs)},
        systems={
            "201": SystemState(
                position="201", system_id="21", space_units={"p1": {"carrier": count}}
            )
        },
    )


def test_gravity_drive_pozwala_jednemu_statkowi_przekroczyc_zasieg_o_jeden(
    registry: StaticDataRegistry,
) -> None:
    grid = _far_grid()
    assert not grid.are_adjacent("201", "000")
    plain = _far_state(2, [])
    with pytest.raises(ValueError, match="Range too short"):
        movement.move_fleet(plain, grid, registry, "201", {"carrier": 1}, {}, "p1")

    boosted = _far_state(2, ["gd"])
    moved = movement.move_fleet(boosted, grid, registry, "201", {"carrier": 1}, {}, "p1")
    assert moved.systems["000"].space_units["p1"] == {"carrier": 1}
    assert moved.gravity_drive_used
    # Premia jest jednorazowa w akcji: drugi statek z tego samego miejsca już nie dojedzie.
    with pytest.raises(ValueError, match="Range too short"):
        movement.move_fleet(moved, grid, registry, "201", {"carrier": 1}, {}, "p1")


def test_gravity_drive_nie_obejmuje_grupy_wiekszej_niz_jeden_statek(
    registry: StaticDataRegistry,
) -> None:
    with pytest.raises(ValueError, match="only 1 ship"):
        movement.move_fleet(
            _far_state(2, ["gd"]), _far_grid(), registry, "201", {"carrier": 2}, {}, "p1"
        )


def test_gravity_drive_nie_jest_zuzywany_gdy_ruch_i_tak_jest_legalny(
    registry: StaticDataRegistry,
) -> None:
    grid = _far_grid()
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={"p1": PlayerState(player_id="p1", color="red", technologies=["gd"])},
        systems={
            "101": SystemState(
                position="101", system_id="20", space_units={"p1": {"carrier": 2}}
            )
        },
    )
    moved = movement.move_fleet(state, grid, registry, "101", {"carrier": 2}, {}, "p1")
    assert not moved.gravity_drive_used


def test_gravity_drive_pokazuje_zrodlo_w_podgladzie_zasiegu(
    registry: StaticDataRegistry,
) -> None:
    grid = _far_grid()
    assert "201" not in movement.legal_move_sources(_far_state(1, []), grid, registry, "p1")
    assert "201" in movement.legal_move_sources(_far_state(1, ["gd"]), grid, registry, "p1")
