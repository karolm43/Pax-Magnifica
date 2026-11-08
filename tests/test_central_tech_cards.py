"""Testy punktów centralnych: technologie, karty akcji (RULES.md 43.1a)."""

from __future__ import annotations

import pytest

from src.core import card_draw, technology
from src.core.game_state import GameState, PlayerState


def _state() -> GameState:
    player = PlayerState(player_id="p1", color="red", technologies=["amd"])
    player.private.action_cards = ["a1", "a2", "a3"]
    state = GameState(players={"p1": player})
    state.decks.action_card_deck = ["d1", "d2"]
    return state


def test_grant_technology_dodaje_i_nie_dubluje() -> None:
    state = _state()
    technology.grant_technology(state, "p1", "ws")
    technology.grant_technology(state, "p1", "ws")
    assert state.players["p1"].technologies == ["amd", "ws"]


def test_grant_technology_nieznany_gracz_jest_bledem() -> None:
    with pytest.raises(ValueError, match="Unknown player"):
        technology.grant_technology(_state(), "nikt", "ws")


def test_odrzucenie_kart_akcji_z_reki_trafia_na_stos_odrzuconych() -> None:
    state = _state()
    discarded = card_draw.discard_action_cards(state, "p1", 2)
    assert discarded == ["a1", "a2"]
    assert state.players["p1"].private.action_cards == ["a3"]
    assert state.decks.action_card_discard == ["a1", "a2"]


def test_dobor_tasuje_odrzucone_gdy_talia_pusta() -> None:
    state = _state()
    state.decks.action_card_deck = []
    state.decks.action_card_discard = ["x1", "x2"]
    assert card_draw.draw_action_card(state, "p1") is True
    assert len(state.players["p1"].private.action_cards) == 4
    assert len(state.decks.action_card_deck) == 1
    assert state.decks.action_card_discard == []
    state.decks.action_card_deck = []
    assert card_draw.draw_action_card(state, "p1") is False


def test_seed_action_deck_ustawia_talie_i_czysci_odrzucone() -> None:
    state = _state()
    state.decks.action_card_discard = ["old"]
    card_draw.seed_action_deck(state, ["n1", "n2"])
    assert state.decks.action_card_deck == ["n1", "n2"]
    assert state.decks.action_card_discard == []
