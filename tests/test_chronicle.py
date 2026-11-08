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


def test_attack_after_deal_is_a_betrayal() -> None:
    state = _state()
    chronicle.record_deal(state, "p2", "p3")
    chronicle.record_battle(state, _combat("p3", "p2", "p3", {"p2": 2, "p3": 0}))
    chronicle.record_conquest(state, "p3", "p2", "mecatol_rex")
    assert state.chronicle.battles[0]["betrayal"] is True
    assert state.chronicle.conquests[0]["betrayal"] is True


def test_highlights_cover_biggest_battle_betrayal_and_quiet_winner(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    chronicle.record_deal(state, "p2", "p3")
    chronicle.record_battle(state, _combat("p3", "p2", "p3", {"p2": 5, "p3": 0}))
    keys = {h["key"] for h in chronicle.highlights(state, registry)}
    assert {"greatest_battle", "crushing_victory", "betrayal", "quiet_victory"} <= keys


def test_no_highlights_for_an_empty_game(registry: StaticDataRegistry) -> None:
    assert chronicle.highlights(_state(), registry) == []
