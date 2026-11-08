"""Testy ``core/unit_ops`` — jedyne miejsce zmiany liczby jednostek (RULES.md 43.1a)."""

from __future__ import annotations

import pytest

from src.core import control, unit_ops
from src.core.game_state import GameState, PlayerState, SystemState
from src.core.unit_ops import UnitCause


def _state() -> tuple[GameState, SystemState, SystemState]:
    a = SystemState(
        position="101",
        system_id="20",
        space_units={"p1": {"cruiser": 3, "fighter": 2}},
        planet_units={"pl": {"p1": {"infantry": 4, "mech": 1}}},
        damaged_units={"space": {"p1": {"cruiser": 2}}, "pl": {"p1": {"mech": 1}}},
    )
    b = SystemState(position="102", system_id="21")
    state = GameState(
        players={"p1": PlayerState(player_id="p1", color="red"),
                 "p2": PlayerState(player_id="p2", color="blue")},
        systems={"101": a, "102": b},
    )
    return state, a, b


def test_place_i_count() -> None:
    state, a, _ = _state()
    unit_ops.place_units(state, a, "space", "p1", "cruiser", 2, UnitCause.PLACED)
    unit_ops.place_units(state, a, "pl2", "p1", "pds", 1, UnitCause.PLACED)
    assert unit_ops.count_in_zone(a, "space", "p1", "cruiser") == 5
    assert unit_ops.count_in_zone(a, "pl2", "p1", "pds") == 1
    assert unit_ops.count_in_zone(None, "space", "p1", "cruiser") == 0
    with pytest.raises(ValueError):
        unit_ops.place_units(state, a, "space", "p1", "cruiser", -1)


def test_take_nie_dotyka_uszkodzen_i_zwraca_liczbe_przed() -> None:
    state, a, _ = _state()
    before = unit_ops.take_units(state, a, "space", "p1", "cruiser", 2)
    assert before == 3
    assert a.space_units["p1"]["cruiser"] == 1
    assert a.damaged_units["space"]["p1"]["cruiser"] == 2  # surowy zapis niezmieniony


def test_remove_przycina_uszkodzenia_i_czysci_puste_wpisy() -> None:
    state, a, _ = _state()
    unit_ops.remove_units(state, a, "space", "p1", "cruiser", 2, UnitCause.DESTROYED)
    assert a.space_units["p1"] == {"cruiser": 1, "fighter": 2}
    assert a.damaged_units["space"]["p1"]["cruiser"] == 1
    unit_ops.remove_units(state, a, "space", "p1", "cruiser", 5, UnitCause.DESTROYED)
    unit_ops.remove_units(state, a, "space", "p1", "fighter", 2, UnitCause.DESTROYED)
    assert "p1" not in a.space_units
    assert "space" not in a.damaged_units


def test_usuniecie_wiecej_niz_jest_nie_schodzi_ponizej_zera() -> None:
    state, a, _ = _state()
    before = unit_ops.remove_units(state, a, "pl", "p1", "mech", 9, UnitCause.REMOVED)
    assert before == 1
    assert a.planet_units["pl"]["p1"] == {"infantry": 4}


def test_transfer_przenosi_uszkodzenia_najpierw_nieuszkodzone() -> None:
    state, a, b = _state()
    # 3 krążowniki, 2 uszkodzone: ruszają 2 -> zostają 1 nieuszkodzony... uszkodzone jadą dopiero
    # gdy nieuszkodzonych zabraknie (1 nieuszkodzony + 1 uszkodzony).
    unit_ops.transfer_units(state, a, "space", b, "space", "p1", "cruiser", 2)
    assert a.space_units["p1"]["cruiser"] == 1
    assert b.space_units["p1"]["cruiser"] == 2
    assert b.damaged_units["space"]["p1"]["cruiser"] == 1
    assert a.damaged_units["space"]["p1"]["cruiser"] == 1


def test_transfer_w_obrebie_jednego_systemu_ladowanie() -> None:
    state, a, _ = _state()
    unit_ops.transfer_units(state, a, "space", a, "pl", "p1", "fighter", 2)
    assert "fighter" not in a.space_units["p1"]
    assert a.planet_units["pl"]["p1"]["fighter"] == 2


def test_replace_zone_units_zastepuje_zestaw() -> None:
    state, a, _ = _state()
    unit_ops.replace_zone_units(state, a, "space", "p1", {"dreadnought": 1})
    assert a.space_units["p1"] == {"dreadnought": 1}
    unit_ops.replace_zone_units(state, a, "pl", "p1", {"spacedock": 1})
    assert a.planet_units["pl"]["p1"] == {"spacedock": 1}


def test_kontrola_planety_po_postawieniu_jednostek() -> None:
    state, a, _ = _state()
    a.planet_units["nowa"] = {}
    unit_ops.place_units(state, a, "nowa", "p2", "infantry", 1)
    control.recompute_from_units(state, "101", "nowa")
    assert a.planet_owners["nowa"] == "p2"
    assert state.players["p2"].controlled_planets == ["nowa"]
    # koegzystencja (2 graczy) nie zmienia właściciela, statki nie dają kontroli
    unit_ops.place_units(state, a, "nowa", "p1", "infantry", 1)
    control.recompute_from_units(state, "101", "nowa")
    assert a.planet_owners["nowa"] == "p2"
    unit_ops.place_units(state, a, "pusta", "p1", "fighter", 3)
    control.recompute_from_units(state, "101", "pusta")
    assert "pusta" not in a.planet_owners
