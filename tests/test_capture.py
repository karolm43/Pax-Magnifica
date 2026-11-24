"""Przechwytywanie jednostek — wspólna mechanika (RULES.md 61.5) i rulingi R_capture / R_blockaded.

Komponenty, które przechwytują (Devour, The Terror Between, Reanimator, Vortex…): testy frakcji
(``tests/factions/test_cabal.py``). Tu: stan arkusza, rezerwa, zwrot, blokada, transakcja,
eliminacja.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.core import (
    board_graph,
    board_reinforcements,
    capture,
    rules_hooks,
    step_settle,
    transaction,
)
from src.core.game_state import ActiveCombat, GameState, Phase, PlayerState, SystemState
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import UNIT_CAP_BY_ASYNC_ID
from src.core.unit_ops import UnitCause, remove_units
from tests.rulings import ruling

HOME, ARENA, RIVAL = "101", "102", "104"
ACHERON, WELLON, THIBAH = "acheron", "wellon", "thibah"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(None)
    yield
    board_graph.bind_grid_provider(previous)


def _state() -> GameState:
    """p1 = Cabal (dok na Acheron), p2 = Sol."""
    p1 = PlayerState(player_id="p1", color="red", faction="cabal", home_position=HOME)
    p2 = PlayerState(player_id="p2", color="blue", faction="sol", home_position=RIVAL)
    state = GameState(
        phase=Phase.ACTION, active_player_id="p2", speaker_id="p1", seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            HOME: SystemState(position=HOME, system_id="54", planet_owners={ACHERON: "p1"},
                              planet_units={ACHERON: {"p1": {"spacedock": 1, "infantry": 1}}}),
            ARENA: SystemState(position=ARENA, system_id="19"),
            RIVAL: SystemState(position=RIVAL, system_id="21", planet_owners={THIBAH: "p2"}),
        },
    )
    p1.controlled_planets = [ACHERON]
    p2.controlled_planets = [THIBAH]
    return state


def _combat(state: GameState, position: str = ARENA) -> None:
    state.active_combat = ActiveCombat(kind="space", position=position, attacker="p2",
                                       defender="p1")


def _cap(base_type: str) -> int:
    from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

    return UNIT_CAP_BY_ASYNC_ID[ASYNC_ID_BY_BASE_TYPE[base_type]]


@ruling("R_capture/rules-reference/1", "R_capture/rules-reference/5")
def test_statek_na_arkuszu_i_poza_rezerwa_wlasciciela() -> None:
    state = _state()
    state.systems[ARENA].space_units = {"p1": {"cruiser": 1}, "p2": {"destroyer": 2}}
    _combat(state)
    remove_units(state, state.systems[ARENA], "space", "p2", "destroyer", 1, UnitCause.DESTROYED)
    assert state.players["p1"].captured_units == {"p2": {"destroyer": 1}}
    # Na planszy 1 + 1 przechwycony: właściciel nie ma go w rezerwie i nie wyprodukuje.
    assert reinforcements_left(state, "p2", "destroyer") == _cap("destroyer") - 2
    capture.return_unit(state, "p1", "p2", "destroyer")
    assert reinforcements_left(state, "p2", "destroyer") == _cap("destroyer") - 1
    assert state.players["p1"].captured_units == {}


@ruling("R_capture/rules-reference/3", "R_capture/rules-reference/4",
        "R_capture/rules-reference/4.3")
def test_mysliwiec_i_piechota_to_zeton_z_puli() -> None:
    state = _state()
    state.systems[ARENA].space_units = {"p1": {"cruiser": 1}, "p2": {"fighter": 2}}
    _combat(state)
    remove_units(state, state.systems[ARENA], "space", "p2", "fighter", 2, UnitCause.DESTROYED)
    assert state.players["p1"].captured_tokens == {"fighter": 2}
    assert state.players["p1"].captured_units == {}  # żeton nie należy do nikogo
    assert reinforcements_left(state, "p2", "fighter") is None  # wraca do rezerwy właściciela
    capture.return_unit(state, "p1", capture.TOKEN, "fighter", 2)  # do puli
    assert state.players["p1"].captured_tokens == {}


@ruling("R_capture/rules-reference/2", "R_capture/rules-reference/2.2")
def test_zwrot_jako_koszt_zdolnosci() -> None:
    state = _state()
    state.players["p1"].captured_units = {"p2": {"carrier": 1}}
    capture.spend_captured(state, "p1", "carrier", "p2")
    assert state.players["p1"].captured_units == {}
    with pytest.raises(ValueError):
        capture.spend_captured(state, "p1", "carrier", "p2")


@ruling("R_capture/rules-reference/2.3", "R_capture/rules-reference/4.2",
        "R_blockaded/rules-reference/2", "R_capture/notes/1")
def test_blokada_doku_oddaje_statki_ale_nie_zetony(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].captured_units = {"p2": {"cruiser": 1}}
    state.players["p1"].captured_tokens = {"infantry": 2}
    state.systems[HOME].space_units = {"p2": {"destroyer": 1}}  # Sol blokuje dok Cabal
    after = step_settle.settle_step(state, registry, 0.0, "tactical:test")
    assert after.players["p1"].captured_units == {}
    assert after.players["p1"].captured_tokens == {"infantry": 2}
    assert reinforcements_left(after, "p2", "cruiser") == _cap("cruiser")
    assert state.players["p1"].captured_units  # wejście bez zmian (czysta funkcja)


@ruling("R_blockaded/notes/1")
def test_walka_w_systemie_doku_to_nie_blokada() -> None:
    state = _state()
    state.systems[HOME].space_units = {"p1": {"cruiser": 1}, "p2": {"destroyer": 2}}
    state.players["p1"].captured_units = {"p2": {"carrier": 1}}
    assert capture.blockaders(state, "p1") == set()
    assert capture.release_blockaded(state) is state
    _combat(state, HOME)
    remove_units(state, state.systems[HOME], "space", "p2", "destroyer", 1, UnitCause.DESTROYED)
    assert state.players["p1"].captured_units["p2"]["destroyer"] == 1


@ruling("R_capture/rules-reference/6", "R_capture/notes/7", "R_blockaded/rules-reference/2.1")
def test_blokowany_nie_przechwytuje_od_blokujacego() -> None:
    state = _state()
    state.systems[HOME].space_units = {"p2": {"destroyer": 1}}  # blokada doku w domu Cabal
    state.systems[ARENA].space_units = {"p1": {"cruiser": 1}, "p2": {"destroyer": 1, "fighter": 1}}
    _combat(state)  # walka gdzie indziej - Cabal nadal blokowany w domu
    remove_units(state, state.systems[ARENA], "space", "p2", "destroyer", 1, UnitCause.DESTROYED)
    remove_units(state, state.systems[ARENA], "space", "p2", "fighter", 1, UnitCause.DESTROYED)
    assert state.players["p1"].captured_units == {}
    assert state.players["p1"].captured_tokens == {}
    assert not capture.can_capture_from_reinforcements(state, "p1", "p2", "dreadnought")


@ruling("R_capture/rules-reference/2.1", "R_capture/rules-reference/4.1", "R_capture/notes/2")
def test_transakcja_zwraca_tylko_wlascicielowi() -> None:
    state = _state()
    state.players["p1"].captured_units = {"p2": {"cruiser": 1}}
    state.players["p1"].captured_tokens = {"fighter": 1}
    side = transaction.TransactionSide(captured_units=("cruiser",))
    assert side.has_components()
    transaction.validate_side(state, "p1", "p2", side, "You")
    transaction._apply_side(state, "p1", "p2", side)
    assert state.players["p1"].captured_units == {}
    with pytest.raises(ValueError, match="fighters and infantry"):
        transaction.validate_side(
            state, "p1", "p2", transaction.TransactionSide(captured_units=("fighter",)), "You"
        )
    # Statek gracza p2 nie trafi do trzeciego gracza: p1 trzyma tylko jednostki p2.
    state.players["p1"].captured_units = {"p2": {"carrier": 1}}
    p3 = PlayerState(player_id="p3", color="green", faction="hacan")
    state.players["p3"] = p3
    with pytest.raises(ValueError, match="captured"):
        transaction.validate_side(
            state, "p1", "p3", transaction.TransactionSide(captured_units=("carrier",)), "You"
        )


@ruling("R_capture/notes/4")
def test_wyeliminowany_wlasciciel_jednostka_do_pudelka() -> None:
    state = _state()
    state.players["p1"].captured_units = {"p2": {"cruiser": 1}}
    del state.players["p2"]  # eliminacja (core/elimination usuwa gracza ze stanu)
    capture.return_unit(state, "p1", "p2", "cruiser")  # zwrot = pudełko, bez rezerwy
    assert state.players["p1"].captured_units == {}


def test_wyeliminowany_przechwytujacy_oddaje_jednostki() -> None:
    """R_elimination: „any units they have captured are returned to the reinforcements”."""
    state = _state()
    state.players["p1"].captured_units = {"p2": {"cruiser": 1}}
    assert reinforcements_left(state, "p2", "cruiser") == _cap("cruiser") - 1
    del state.players["p1"]
    assert reinforcements_left(state, "p2", "cruiser") == _cap("cruiser")


@ruling("R_capture/notes/5", "R_capture/rules-reference/5")
def test_wlasne_przechwycone_wraca_gracz_kiedy_chce() -> None:
    """Own captured units stay on the sheet (no automatic return, cannot be placed) until the
    player chooses to return them to reinforcements - which they may do at any time."""
    state = _state()
    state.players["p1"].captured_units = {"p1": {"cruiser": 2}, "p2": {"carrier": 1}}
    assert reinforcements_left(state, "p1", "cruiser") == _cap("cruiser") - 2
    state = capture.release_blockaded(state)
    assert state.players["p1"].captured_units["p1"] == {"cruiser": 2}
    after = capture.return_own(state, "p1", "cruiser")
    assert after.players["p1"].captured_units == {"p1": {"cruiser": 1}, "p2": {"carrier": 1}}
    assert reinforcements_left(after, "p1", "cruiser") == _cap("cruiser") - 1
    assert state.players["p1"].captured_units["p1"] == {"cruiser": 2}  # pure
    with pytest.raises(ValueError, match="own units"):
        capture.return_own(after, "p1", "cruiser", 2)
    with pytest.raises(ValueError, match="own units"):
        capture.return_own(after, "p1", "carrier")  # Sol carrier: not own
    with pytest.raises(ValueError, match="tokens"):
        capture.return_own(after, "p1", "fighter")


@ruling("R_capture/notes/6")
def test_cala_pula_na_planszy_albo_na_arkuszu_zdjecie_z_planszy() -> None:
    state = _state()
    cap = _cap("cruiser")
    state.systems[ARENA].space_units = {"p2": {"cruiser": cap - 1}}
    state.players["p1"].captured_units = {"p2": {"cruiser": 1}}
    assert board_reinforcements.needs_board_source(state, "p2", "cruiser")
    assert board_reinforcements.board_sources(state, "p2", "cruiser") == [f"{ARENA}|space"]


def test_struktury_nie_sa_przechwytywane() -> None:
    state = _state()
    state.systems[ARENA].planet_units = {WELLON: {"p2": {"pds": 1}}}
    state.active_combat = ActiveCombat(kind="ground", position=ARENA, planet=WELLON,
                                       attacker="p1", defender="p2")
    remove_units(state, state.systems[ARENA], WELLON, "p2", "pds", 1, UnitCause.DESTROYED)
    assert capture.total_held(state, "p1") == 0


def test_nombox_web_data() -> None:
    state = _state()
    state.players["p1"].captured_units = {"p2": {"cruiser": 2}, "p1": {"carrier": 1}}
    state.players["p1"].captured_tokens = {"infantry": 3}
    assert capture.nombox(state, "p1") == {
        "sol": ["cruiser,2"], "cabal": ["carrier,1", "infantry,3"],
    }
