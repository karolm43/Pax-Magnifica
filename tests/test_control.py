"""Testy ``core/control`` — kontrola planet (RULES.md 12, 43.1a; R_control)."""

from __future__ import annotations

import pytest

from src.core import control
from src.core.game_state import GameState, PlayerState, SystemState


def _state() -> GameState:
    p1 = PlayerState(player_id="p1", color="red", controlled_planets=["alfa"])
    p2 = PlayerState(player_id="p2", color="blue", exhausted_planets=["alfa"])
    system = SystemState(position="101", system_id="20", planet_owners={"alfa": "p1"})
    # p2 ma znacznik wyczerpania planety, którą p1 kontroluje - sprawdzamy utratę kontroli.
    p1.exhausted_planets = ["alfa"]
    return GameState(players={"p1": p1, "p2": p2}, systems={"101": system})


def test_zmiana_kontrolera_aktualizuje_wlasciciela_i_lustro() -> None:
    state = _state()
    control.set_planet_control(state, "101", "alfa", "p2")
    assert state.systems["101"].planet_owners["alfa"] == "p2"
    assert state.players["p1"].controlled_planets == []
    assert state.players["p2"].controlled_planets == ["alfa"]


def test_poprzedni_kontroler_traci_znacznik_wyczerpania() -> None:
    state = _state()
    control.set_planet_control(state, "101", "alfa", "p2")
    assert state.players["p1"].exhausted_planets == []


def test_ten_sam_kontroler_nic_nie_zmienia() -> None:
    state = _state()
    control.set_planet_control(state, "101", "alfa", "p1")
    assert state.players["p1"].exhausted_planets == ["alfa"]
    assert state.players["p1"].controlled_planets == ["alfa"]


def test_brak_kontrolera_usuwa_wlasciciela() -> None:
    state = _state()
    control.set_planet_control(state, "101", "alfa", None)
    assert "alfa" not in state.systems["101"].planet_owners
    assert state.players["p1"].controlled_planets == []


def test_planeta_bez_wlasciciela_przechodzi_na_gracza_bez_duplikatow() -> None:
    state = _state()
    control.set_planet_control(state, "101", "beta", "p2")
    control.set_planet_control(state, "101", "beta", "p2")
    assert state.players["p2"].controlled_planets == ["beta"]


def test_nieznany_system_jest_bledem() -> None:
    state = _state()
    with pytest.raises(ValueError, match="Unknown system"):
        control.set_planet_control(state, "999", "alfa", "p2")
