"""Testy akcji strategicznej (E8-T3): primary + okno secondary (RULES.md 30)."""

from __future__ import annotations

import pytest

from src.core import strategic_action, timing
from src.core.game_state import GameState, PlayerState, WindowType
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state_three() -> GameState:
    """Trzech graczy; p1 aktywny z kartą Leadership (inicjatywa 1)."""
    return GameState(
        active_player_id="p1",
        seating_order=["p1", "p2", "p3"],
        players={
            "p1": PlayerState(player_id="p1", color="red", strategy_cards=[1]),
            "p2": PlayerState(player_id="p2", color="green"),
            "p3": PlayerState(player_id="p3", color="blue"),
        },
    )


def test_leadership_initiative_matches_registry(registry: StaticDataRegistry) -> None:
    """Stała inicjatywy Leadership zgadza się z danymi (nie z pamięci)."""
    cards = {c.name: c.initiative for c in registry.strategy_card_set()}
    assert cards["Leadership"] == strategic_action._LEADERSHIP_INITIATIVE


def test_play_leadership_primary_grants_three_tokens(
    registry: StaticDataRegistry,
) -> None:
    state = _state_three()
    before = state.players["p1"].tactical_cc
    new = strategic_action.play_strategy_card(state, registry, "p1", 1)
    assert new.players["p1"].tactical_cc == before + 3
    # Karta oznaczona jako zagrana.
    assert 1 in new.players["p1"].exhausted_strategy_cards


def test_play_opens_secondary_window_for_others(
    registry: StaticDataRegistry,
) -> None:
    new = strategic_action.play_strategy_card(_state_three(), registry, "p1", 1)
    assert new.pending_window is not None
    assert new.pending_window.window_type is WindowType.STRATEGY_SECONDARY
    # Kolejka od gracza po aktywnym (p1), zegarowo: p2, p3. Inicjator pominięty.
    assert new.pending_window.queue == ["p2", "p3"]
    assert new.pending_window.context == {"initiative": 1}
    assert new.pending_window.current_responder == "p2"


def test_play_rejects_card_not_owned(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="does not hold"):
        strategic_action.play_strategy_card(_state_three(), registry, "p1", 5)


def test_play_solo_opens_no_window(registry: StaticDataRegistry) -> None:
    """Solo (brak innych graczy) — zagranie karty NIE otwiera okna secondary.

    Regresja: puste okno (kolejka []) zostawałoby ustawione jako ``pending_window``
    i BLOKOWAŁO End turn na stałe (nikt by go nie zamknął). Bez respondentów = bez okna,
    więc aktywny gracz może od razu zakończyć turę. Akcja i tak jest zaliczona.
    """
    state = GameState(
        active_player_id="p1",
        seating_order=["p1"],
        players={"p1": PlayerState(player_id="p1", color="red", strategy_cards=[1])},
    )
    new = strategic_action.play_strategy_card(state, registry, "p1", 1)
    assert new.pending_window is None
    assert new.players["p1"].took_action_this_turn is True
    assert 1 in new.players["p1"].exhausted_strategy_cards


def test_play_rejects_unknown_player(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="Unknown player"):
        strategic_action.play_strategy_card(_state_three(), registry, "x", 1)


def test_play_rejects_when_window_already_open(registry: StaticDataRegistry) -> None:
    state = _state_three()
    state = timing.open_window(state, WindowType.REACTION, ["p2"])
    with pytest.raises(ValueError, match="timing window is already open"):
        strategic_action.play_strategy_card(state, registry, "p1", 1)


def test_secondary_advances_and_closes(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state_three(), registry, "p1", 1)
    # p2 wykonuje secondary (szkielet — brak efektu liczbowego w T3).
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    assert state.pending_window is not None
    assert state.pending_window.current_responder == "p3"
    # p3 pasuje → okno dopełnione i zamknięte automatycznie.
    state = strategic_action.resolve_secondary(state, registry, "p3", execute=False)
    assert state.pending_window is None


def test_secondary_out_of_order_rejected(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state_three(), registry, "p1", 1)
    with pytest.raises(ValueError, match="out-of-order"):
        strategic_action.resolve_secondary(state, registry, "p3", execute=True)


def test_secondary_without_window_rejected(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="No open strategy card secondary window"):
        strategic_action.resolve_secondary(_state_three(), registry, "p2", execute=True)


def test_secondary_rejects_wrong_window_type(registry: StaticDataRegistry) -> None:
    state = _state_three()
    state = timing.open_window(state, WindowType.REACTION, ["p2"])
    with pytest.raises(ValueError, match="No open strategy card secondary window"):
        strategic_action.resolve_secondary(state, registry, "p2", execute=True)
