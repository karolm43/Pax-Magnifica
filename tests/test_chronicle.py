"""Testy kroniki partii: rejestr bitew/podbojów/transakcji i wnioski końcowe."""

from __future__ import annotations

import pytest

from src.core import chronicle
from src.core.game_state import ActiveCombat, GameState, PlayerState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    players = {
        pid: PlayerState(player_id=pid, color=pid, faction=fac, display_name=pid)
        for pid, fac in (("p1", "sol"), ("p2", "hacan"), ("p3", "xxcha"))
    }
    return GameState(players=players, winner_id="p1", round_number=4)


def _combat(
    attacker: str, defender: str, winner: str | None, losses: dict[str, int]
) -> ActiveCombat:
    return ActiveCombat(
        kind="space",
        position="101",
        attacker=attacker,
        defender=defender,
        round=3,
        winner=winner,
        log=[{"losses": {pid: {"fighter": n} for pid, n in losses.items()}}],
    )


def test_battle_losses_are_summed_and_recorded() -> None:
    state = _state()
    chronicle.record_battle(state, _combat("p2", "p3", "p2", {"p2": 1, "p3": 4}))
    battle = state.chronicle.battles[0]
    assert battle["losses"] == {"p2": 1, "p3": 4}
    assert battle["rounds"] == 3 and battle["betrayal"] is False


def test_attack_despite_pact_note_is_a_betrayal() -> None:
    state = _state()
    # p3 trzyma Alliance wystawiony przez p2 (kolor p2 = "p2").
    state.players["p3"].promissory_notes_in_play.append("p2_an")
    chronicle.record_battle(state, _combat("p3", "p2", "p3", {"p2": 2, "p3": 0}))
    chronicle.record_conquest(state, "p3", "p2", "mecatol_rex")
    assert state.chronicle.battles[0]["betrayal"] is True
    assert state.chronicle.conquests[0]["betrayal"] is True


def test_highlights_cover_biggest_battle_betrayal_and_quiet_winner(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.players["p2"].private.promissory_notes.append("p3_cf")
    chronicle.record_battle(state, _combat("p3", "p2", "p3", {"p2": 5, "p3": 0}))
    keys = {h["key"] for h in chronicle.highlights(state, registry)}
    assert {"greatest_battle", "crushing_victory", "betrayal", "quiet_victory"} <= keys


def test_no_highlights_for_an_empty_game(registry: StaticDataRegistry) -> None:
    assert chronicle.highlights(_state(), registry) == []


def test_trade_without_pact_is_not_a_betrayal() -> None:
    state = _state()
    chronicle.record_deal(state, "p2", "p3")
    chronicle.record_battle(state, _combat("p3", "p2", "p3", {"p2": 1, "p3": 0}))
    assert state.chronicle.battles[0]["betrayal"] is False
    assert chronicle.pact_between(state, "p2", "p3") is None


def test_extra_achievements(registry: StaticDataRegistry) -> None:
    state = _state()
    # Obrońca p2 trzyma pozycję bez strat (mur), p3 atakuje trzy razy z rzędu (rywalizacja).
    for _ in range(3):
        chronicle.record_battle(state, _combat("p3", "p2", "p2", {"p2": 0, "p3": 4}))
    # Pyrrusowe zwycięstwo p1 (więcej strat niż wróg).
    chronicle.record_battle(state, _combat("p1", "p3", "p1", {"p1": 5, "p3": 1}))
    chronicle.record_deal(state, "p1", "p2")
    chronicle.record_conquest(state, "p1", "p3", "mecatol_rex")
    chronicle.record_conquest(state, "p2", "p1", "mecatol_rex")
    keys = {h["key"] for h in chronicle.highlights(state, registry)}
    assert {
        "unbreakable_wall",
        "pyrrhic_victory",
        "rivalry",
        "undefeated",
        "torn_world",
        "hermit",
    } <= keys
