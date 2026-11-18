"""Testy technologii pasywnych/obowiązkowych (RULES.md 55.8)."""

from __future__ import annotations

import pytest

from src.core import retreat, technology, triggers, unit_ops
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.hooks import technologies_passive as passive
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause
from tests.rulings import ruling
from tests.test_technology import _first, _specialty_planet
from tests.test_technology import _state as research_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def test_aliasy_istnieja_w_danych(registry: StaticDataRegistry) -> None:
    for alias in (
        passive.DARK_ENERGY_TAP_ALIAS,
        passive.PSYCHOARCHAEOLOGY_ALIAS,
        passive.SELF_ASSEMBLY_ALIAS,
        passive.INFANTRY_II_ALIAS,
        "sd2",
        "dn2",
    ):
        assert alias in registry.technologies, alias


# --- Dark Energy Tap: odwrót -------------------------------------------------------------


def _retreat_grid() -> HexGrid:
    grid = HexGrid()
    for pos, sid in [("000", "18"), ("101", "20"), ("102", "22")]:
        grid.place_system(pos, sid, anomalies=set())
    grid.build_edges()
    return grid


def _retreat_state(techs: list[str]) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        players={
            "p1": PlayerState(player_id="p1", color="red", technologies=techs),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems={
            "000": SystemState(
                position="000", system_id="18",
                space_units={"p1": {"cruiser": 1}, "p2": {"cruiser": 1}},
            ),
            # 101: pusty system ze wpisem; 102: cudza struktura na planecie
            "101": SystemState(position="101", system_id="20"),
            "102": SystemState(
                position="102", system_id="22", planet_units={"pl": {"p2": {"pds": 1}}}
            ),
        },
    )


def test_bez_dark_energy_tap_odwrot_wymaga_obecnosci() -> None:
    state = _retreat_state([])
    assert retreat.retreat_destinations(state, _retreat_grid(), "000", "p1") == []


@ruling("C_technology/dark-energy-tap/6")
def test_dark_energy_tap_pozwala_wycofac_sie_do_systemu_bez_cudzych_jednostek() -> None:
    state = _retreat_state(["det"])
    # 101 jest pusty - tak; 102 ma strukturę innego gracza - nie.
    assert retreat.retreat_destinations(state, _retreat_grid(), "000", "p1") == ["101"]


def test_dark_energy_tap_odwrot_do_systemu_bez_wpisu_w_stanie(
    registry: StaticDataRegistry,
) -> None:
    state = _retreat_state(["det"])
    del state.systems["101"]
    grid = _retreat_grid()
    assert retreat.retreat_destinations(state, grid, "000", "p1") == ["101"]
    state.players["p1"].tactical_cc = 3
    moved, result = retreat.perform_retreat(state, grid, registry, "000", "p1", "101")
    assert moved.systems["101"].space_units["p1"] == {"cruiser": 1}
    assert result.moved == {"cruiser": 1}


# --- Psychoarchaeology ---------------------------------------------------------------------


def test_psychoarchaeology_specjalnosc_nie_wyczerpuje_planety(
    registry: StaticDataRegistry,
) -> None:
    tier1 = _first(registry, "WARFARE", 1)  # pa jest BIOTIC, więc nie pokrywa czerwonego
    green = _specialty_planet(registry, "WARFARE")
    state = research_state(registry, ["pa"], [green])
    done = technology.research(state, registry, "p1", tier1, [green])
    assert tier1 in done.players["p1"].technologies
    assert green not in done.players["p1"].exhausted_planets


def test_psychoarchaeology_dziala_na_juz_wyczerpanej_planecie(
    registry: StaticDataRegistry,
) -> None:
    tier1 = _first(registry, "WARFARE", 1)  # pa jest BIOTIC, więc nie pokrywa czerwonego
    green = _specialty_planet(registry, "WARFARE")
    state = research_state(registry, ["pa"], [green])
    state.players["p1"].exhausted_planets = [green]
    done = technology.research(state, registry, "p1", tier1, [green])
    assert tier1 in done.players["p1"].technologies
    assert done.players["p1"].exhausted_planets == [green]  # bez zmian

    plain = research_state(registry, [], [green])
    plain.players["p1"].exhausted_planets = [green]
    with pytest.raises(ValueError, match="not a ready planet"):
        technology.research(plain, registry, "p1", tier1, [green])


# --- Self-Assembly Routines ----------------------------------------------------------------


def _mech_state(techs: list[str]) -> GameState:
    return GameState(
        players={"p1": PlayerState(player_id="p1", color="red", technologies=techs)},
        systems={
            "101": SystemState(
                position="101", system_id="20", planet_units={"pl": {"p1": {"mech": 2}}}
            )
        },
    )


def test_self_assembly_daje_tg_za_kazdego_zniszczonego_mecha() -> None:
    state = _mech_state(["sar"])
    unit_ops.remove_units(
        state, state.systems["101"], "pl", "p1", "mech", 2, UnitCause.DESTROYED
    )
    assert state.players["p1"].trade_goods == 2


def test_self_assembly_nie_daje_tg_za_usuniecie_bez_zniszczenia_ani_bez_technologii() -> None:
    state = _mech_state(["sar"])
    unit_ops.remove_units(state, state.systems["101"], "pl", "p1", "mech", 1, UnitCause.REMOVED)
    assert state.players["p1"].trade_goods == 0
    plain = _mech_state([])
    unit_ops.remove_units(
        plain, plain.systems["101"], "pl", "p1", "mech", 1, UnitCause.DESTROYED
    )
    assert plain.players["p1"].trade_goods == 0


# --- Infantry II ----------------------------------------------------------------------------


def _infantry_state(techs: list[str], with_home_planet: bool = True) -> GameState:
    home = SystemState(
        position="000", system_id="18",
        planet_owners={"hp": "p1"} if with_home_planet else {},
    )
    field = SystemState(
        position="101", system_id="20", planet_units={"pl": {"p1": {"infantry": 12}}}
    )
    player = PlayerState(
        player_id="p1", color="red", technologies=techs, home_position="000"
    )
    return GameState(
        phase=Phase.ACTION, active_player_id="p2", rng_seed=5,
        players={"p1": player, "p2": PlayerState(player_id="p2", color="blue")},
        systems={"000": home, "101": field},
    )


def test_infantry_ii_rzuca_kosc_za_kazda_zniszczona_piechote() -> None:
    state = _infantry_state(["inf2"])
    unit_ops.remove_units(
        state, state.systems["101"], "pl", "p1", "infantry", 12, UnitCause.DESTROYED
    )
    roll = state.table_roll
    assert roll is not None and roll["kind"] == "infantry_ii" and len(roll["dice"]) == 12
    revived = sum(1 for d in roll["dice"] if d >= 6)
    assert state.players["p1"].infantry_ii_on_card == revived
    assert 0 < revived < 12  # ziarno 5: część odrodzona, część nie


def test_infantry_ii_nie_dziala_bez_technologii() -> None:
    state = _infantry_state([])
    unit_ops.remove_units(
        state, state.systems["101"], "pl", "p1", "infantry", 12, UnitCause.DESTROYED
    )
    assert state.table_roll is None
    assert state.players["p1"].infantry_ii_on_card == 0


def test_infantry_ii_wraca_na_planete_domowa_na_poczatku_tury() -> None:
    state = _infantry_state(["inf2"])
    state.players["p1"].infantry_ii_on_card = 3
    triggers.fire(
        state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"}
    )
    assert state.players["p1"].infantry_ii_on_card == 0
    assert state.systems["000"].planet_units["hp"]["p1"] == {"infantry": 3}


def test_infantry_ii_bez_planety_w_domu_wraca_do_rezerwy() -> None:
    state = _infantry_state(["inf2"], with_home_planet=False)
    state.players["p1"].infantry_ii_on_card = 2
    triggers.fire(
        state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"}
    )
    assert state.players["p1"].infantry_ii_on_card == 0
    assert state.systems["000"].planet_units == {}


def test_infantry_ii_wraca_tez_na_poczatku_pierwszej_tury_fazy_akcji() -> None:
    state = _infantry_state(["inf2"])
    state.active_player_id = "p1"
    state.players["p1"].infantry_ii_on_card = 1
    triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "action"})
    assert state.systems["000"].planet_units["hp"]["p1"] == {"infantry": 1}
