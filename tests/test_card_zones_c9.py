"""Testy modułów centralnych C9: tajne cele, promissory notes, fragmenty reliktów."""

from __future__ import annotations

import random

import pytest

from src.core import promissory_notes, relic_fragments, secret_objectives
from src.core.game_state import GameState, PlayerState


def _state() -> GameState:
    players = {
        "p1": PlayerState(player_id="p1", color="red"),
        "p2": PlayerState(player_id="p2", color="blue"),
    }
    return GameState(players=players)


def test_promissory_note_transfer_moves_between_hands() -> None:
    state = _state()
    promissory_notes.set_hand(state, "p1", ["a", "b"])
    promissory_notes.transfer(state, "p1", "p2", "a")
    assert state.players["p1"].private.promissory_notes == ["b"]
    assert state.players["p2"].private.promissory_notes == ["a"]
    with pytest.raises(ValueError, match="does not hold"):
        promissory_notes.transfer(state, "p1", "p2", "a")


def test_relic_fragment_gain_and_transfer() -> None:
    state = _state()
    relic_fragments.gain(state, "p1", "crf1")
    relic_fragments.transfer(state, "p1", "p2", "crf1")
    assert state.players["p1"].relic_fragments == []
    assert state.players["p2"].relic_fragments == ["crf1"]
    with pytest.raises(ValueError, match="does not have"):
        relic_fragments.transfer(state, "p1", "p2", "crf1")


def test_secret_objective_setup_choice_and_score() -> None:
    state = _state()
    secret_objectives.seed_deck(state, ["s1", "s2", "s3", "s4"])
    secret_objectives.deal_candidates(state, "p1", 2)
    assert state.players["p1"].private.secret_candidates == ["s1", "s2"]
    secret_objectives.choose_candidate(state, "p1", "s1", random.Random(1))
    assert state.players["p1"].private.secret_objectives == ["s1"]
    assert state.players["p1"].private.secret_candidates == []
    assert sorted(state.decks.secret_objective_deck) == ["s2", "s3", "s4"]
    secret_objectives.score(state, "p1", "s1")
    assert state.players["p1"].private.secret_objectives == []
    assert state.players["p1"].scored_secrets == ["s1"]


def test_secret_objective_draw_over_limit_requires_return() -> None:
    state = _state()
    state.players["p1"].private.secret_objectives = ["h1", "h2"]
    state.players["p1"].scored_secrets = ["done"]
    secret_objectives.seed_deck(state, ["s1", "s2"])
    with pytest.raises(ValueError, match="more than 3"):
        secret_objectives.draw(state, "p1", None)
    secret_objectives.draw(state, "p1", secret_objectives.DRAWN)
    assert state.players["p1"].private.secret_objectives == ["h1", "h2"]
    assert sorted(state.decks.secret_objective_deck) == ["s1", "s2"]
