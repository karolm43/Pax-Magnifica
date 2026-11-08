"""Testy ``core/command_tokens`` i ``core/exhaust`` (RULES.md 43.1a)."""

from __future__ import annotations

import pytest

from src.core import command_tokens, exhaust
from src.core.game_state import GameState, PlayerState


def _state() -> GameState:
    p1 = PlayerState(
        player_id="p1", color="red",
        tactical_cc=3, fleet_cc=3, strategic_cc=2, cc_reinf=4,
        exhausted_planets=["a"], exhausted_technologies=["t1"],
    )
    return GameState(players={"p1": p1})


def _counts(state: GameState) -> tuple[int, int, int, int]:
    p = state.players["p1"]
    return p.tactical_cc, p.fleet_cc, p.strategic_cc, p.cc_reinf


# --- żetony dowodzenia -----------------------------------------------------------------------


def test_zdjecie_z_puli_i_odczyty() -> None:
    state = _state()
    command_tokens.spend_from_pool(state, "p1", "tactical")
    assert command_tokens.pool_count(state, "p1", "tactical") == 2
    assert command_tokens.sheet_total(state, "p1") == 7
    assert command_tokens.reinforcements(state, "p1") == 4


def test_wydanie_z_puli_do_rezerwy() -> None:
    state = _state()
    command_tokens.spend_to_reinforcements(state, "p1", "strategic", 2)
    assert _counts(state) == (3, 3, 0, 6)


def test_za_malo_zetonow_w_puli_to_blad_i_brak_zmiany() -> None:
    state = _state()
    with pytest.raises(ValueError, match="Not enough command tokens"):
        command_tokens.spend_from_pool(state, "p1", "strategic", 3)
    assert _counts(state) == (3, 3, 2, 4)


def test_zdobycie_z_rezerwy_do_pul_jest_atomowe() -> None:
    state = _state()
    command_tokens.gain_from_reinforcements(state, "p1", {"tactical": 1, "fleet": 2})
    assert _counts(state) == (4, 5, 2, 1)
    with pytest.raises(ValueError, match="reinforcements"):
        command_tokens.gain_from_reinforcements(state, "p1", {"tactical": 5})
    assert _counts(state) == (4, 5, 2, 1)


def test_nieznana_pula_i_ujemne_ilosci_sa_bledem() -> None:
    state = _state()
    with pytest.raises(ValueError, match="Unknown command token pool"):
        command_tokens.pool_count(state, "p1", "bogus")
    with pytest.raises(ValueError):
        command_tokens.return_to_reinforcements(state, "p1", -1)
    with pytest.raises(ValueError):
        command_tokens.gain_from_reinforcements(state, "p1", {"bogus": 1})
    assert _counts(state) == (3, 3, 2, 4)


def test_przerozdzielenie_pul() -> None:
    state = _state()
    command_tokens.set_pools(state, "p1", {"tactical": 8, "fleet": 0, "strategic": 0})
    assert _counts(state) == (8, 0, 0, 4)
    with pytest.raises(ValueError, match="all command token pools"):
        command_tokens.set_pools(state, "p1", {"tactical": 8})
    with pytest.raises(ValueError, match="negative"):
        command_tokens.set_pools(state, "p1", {"tactical": 9, "fleet": -1, "strategic": 0})


def test_zwrot_i_pobranie_z_rezerwy() -> None:
    state = _state()
    command_tokens.take_from_reinforcements(state, "p1", 4)
    assert command_tokens.reinforcements(state, "p1") == 0
    with pytest.raises(ValueError):
        command_tokens.take_from_reinforcements(state, "p1")
    command_tokens.return_to_reinforcements(state, "p1", 2)
    assert command_tokens.reinforcements(state, "p1") == 2


# --- wyczerpywanie --------------------------------------------------------------------------


def test_wyczerpanie_planet_zachowuje_kolejnosc_i_nie_dubluje() -> None:
    state = _state()
    exhaust.exhaust_planets(state, "p1", ["b", "a", "c"])
    assert state.players["p1"].exhausted_planets == ["a", "b", "c"]


def test_odswiezenie_planet() -> None:
    state = _state()
    exhaust.exhaust_planets(state, "p1", ["b", "c"])
    exhaust.ready_planets(state, "p1", ["a", "c"])
    assert state.players["p1"].exhausted_planets == ["b"]
    exhaust.ready_all_planets(state, "p1")
    assert state.players["p1"].exhausted_planets == []


def test_wyczerpanie_i_odswiezenie_technologii() -> None:
    state = _state()
    exhaust.exhaust_technology(state, "p1", "t1")
    exhaust.exhaust_technology(state, "p1", "t2")
    assert state.players["p1"].exhausted_technologies == ["t1", "t2"]
    exhaust.ready_all_technologies(state, "p1")
    assert state.players["p1"].exhausted_technologies == []


def test_nieznany_gracz_jest_bledem() -> None:
    state = _state()
    with pytest.raises(ValueError, match="Unknown player"):
        exhaust.exhaust_planets(state, "nikt", ["a"])
    with pytest.raises(ValueError, match="Unknown player"):
        command_tokens.reinforcements(state, "nikt")
