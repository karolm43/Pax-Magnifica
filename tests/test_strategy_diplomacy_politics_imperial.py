"""Testy Diplomacy, Politics i Imperial (RULES.md 30.8-30.10)."""

from __future__ import annotations

import pytest

from src.core import strategic_action
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(card: int) -> GameState:
    """p1 aktywny z kartą ``card``; p1 ma planety w systemach 101 (zwykły) i 18 (Mecatol)."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        speaker_id="p2",
        seating_order=["p1", "p2", "p3"],
        systems={
            "101": SystemState(
                position="101", system_id="26", planet_owners={"lodor": "p1"}
            ),
            "000": SystemState(
                position="000", system_id="18", planet_owners={"mecatolrex": "p1"}
            ),
        },
        players={
            "p1": PlayerState(player_id="p1", color="red", strategy_cards=[card]),
            "p2": PlayerState(player_id="p2", color="green"),
            "p3": PlayerState(player_id="p3", color="blue"),
        },
    )


# --- Diplomacy ------------------------------------------------------------------------------


def test_diplomacy_rejects_mecatol_and_foreign_systems(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(2), registry, "p1", 2)
    for bad in ("000", "999", None, 5):
        with pytest.raises(ValueError, match="not Mecatol Rex"):
            strategic_action.submit_primary_step(state, registry, "p1", {"system": bad})


def test_diplomacy_places_tokens_from_reinforcements_and_readies(
    registry: StaticDataRegistry,
) -> None:
    state = _state(2)
    state.players["p1"].exhausted_planets = ["lodor", "mecatolrex"]
    state.systems["101"].command_tokens = ["p3"]  # p3 już ma żeton - nie kładzie drugiego
    state = strategic_action.play_strategy_card(state, registry, "p1", 2)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"system": "101"})
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"planets": ["lodor", "mecatolrex"]}
    )
    assert sorted(state.systems["101"].command_tokens) == ["p2", "p3"]
    assert state.players["p2"].cc_reinf == 7  # zabrany z rezerwy
    assert state.players["p3"].cc_reinf == 8  # nie kładł
    assert state.players["p1"].exhausted_planets == []
    assert state.pending_window is not None  # secondary otwarte


def test_diplomacy_empty_reinforcements_takes_from_sheet(registry: StaticDataRegistry) -> None:
    state = _state(2)
    state.players["p2"].cc_reinf = 0
    state = strategic_action.play_strategy_card(state, registry, "p1", 2)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"system": "101"})
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    assert "p2" in state.systems["101"].command_tokens
    assert state.players["p2"].tactical_cc == 2  # ⚠️ założenie: najpierw pula taktyczna


def test_diplomacy_ready_limit_and_exhausted_only(registry: StaticDataRegistry) -> None:
    state = _state(2)
    state.systems["101"].planet_owners = {"lodor": "p1", "arinam": "p1", "meer": "p1"}
    state.players["p1"].exhausted_planets = ["lodor", "arinam", "meer"]
    state = strategic_action.play_strategy_card(state, registry, "p1", 2)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"system": "101"})
    with pytest.raises(ValueError, match="at most 2"):
        strategic_action.submit_primary_step(
            state, registry, "p1", {"planets": ["lodor", "arinam", "meer"]}
        )
    state.players["p1"].exhausted_planets = ["lodor"]
    with pytest.raises(ValueError, match="not exhausted"):
        strategic_action.submit_primary_step(state, registry, "p1", {"planets": ["arinam"]})


def test_diplomacy_without_planets_still_playable(registry: StaticDataRegistry) -> None:
    state = _state(2)
    state.systems["101"].planet_owners = {}
    state = strategic_action.play_strategy_card(state, registry, "p1", 2)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"system": None})
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    assert state.systems["101"].command_tokens == []
    assert state.pending_window is not None


def test_diplomacy_secondary_readies_and_costs_token(registry: StaticDataRegistry) -> None:
    state = _state(2)
    state.systems["102"] = SystemState(
        position="102", system_id="27", planet_owners={"arinam": "p2"}
    )
    state.players["p2"].exhausted_planets = ["arinam"]
    state = strategic_action.play_strategy_card(state, registry, "p1", 2)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"system": "101"})
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    prompt = strategic_action.step_options(state, registry, "p2")
    assert prompt is not None and prompt["options"]["exhausted"] == ["arinam"]
    state = strategic_action.resolve_secondary(
        state, registry, "p2", execute=True, payload={"planets": ["arinam"]}
    )
    assert state.players["p2"].exhausted_planets == []
    assert state.players["p2"].strategic_cc == 1  # żeton ze strategy pool wydany


# --- Politics -------------------------------------------------------------------------------


def _politics_ready(registry: StaticDataRegistry) -> GameState:
    state = _state(3)
    state.decks.action_card_deck = ["a1", "a2", "a3", "a4"]
    state = strategic_action.play_strategy_card(state, registry, "p1", 3)
    return strategic_action.submit_primary_step(state, registry, "p1", {"player": "p3"})


def test_politics_speaker_must_change(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(3), registry, "p1", 3)
    with pytest.raises(ValueError, match="already has the speaker"):
        strategic_action.submit_primary_step(state, registry, "p1", {"player": "p2"})
    with pytest.raises(ValueError, match="Choose a player"):
        strategic_action.submit_primary_step(state, registry, "p1", {"player": "zz"})


def test_politics_agenda_peek_is_private_and_reorders_deck(registry: StaticDataRegistry) -> None:
    state = _politics_ready(registry)
    assert state.pending_strategy is not None and state.pending_strategy.step == "agenda_order"
    assert "cards" not in state.pending_strategy.draft  # podgląd nie wycieka do szkicu
    own = strategic_action.step_options(state, registry, "p1")
    assert own is not None
    peek = own["options"]["cards"]
    assert len(peek) == 2
    assert strategic_action.step_options(state, registry, "p2") is None
    deck_before = list(state.decks.agenda_deck)
    assert deck_before[:2] == peek
    # jedna na górę, druga na spód
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"top": [peek[1]], "bottom": [peek[0]]}
    )
    deck = state.decks.agenda_deck
    assert deck[0] == peek[1] and deck[-1] == peek[0]
    assert deck[1:-1] == deck_before[2:]
    # Wiedza o talii (RULES.md 53.5.a1): właściciel pamięta wierzch i spód, inni nic.
    assert state.players["p1"].private.agenda_peek == [peek[1]]
    assert state.players["p1"].private.agenda_peek_bottom == [peek[0]]
    assert state.players["p2"].private.agenda_peek == []
    assert state.speaker_id == "p3"
    assert len(state.players["p1"].private.action_cards) == 2


def test_politics_agenda_order_must_use_exactly_the_peeked_cards(
    registry: StaticDataRegistry,
) -> None:
    state = _politics_ready(registry)
    peek = state.decks.agenda_deck[:2]
    bad_payloads: list[dict[str, list[str]]] = [
        {"top": [peek[0]], "bottom": []},
        {"top": [peek[0], peek[0]], "bottom": []},
        {"top": ["x", peek[1]], "bottom": []},
    ]
    for payload in bad_payloads:
        with pytest.raises(ValueError, match="top or the bottom"):
            strategic_action.submit_primary_step(state, registry, "p1", payload)


def test_politics_secondary_draws_two_for_a_token(registry: StaticDataRegistry) -> None:
    state = _politics_ready(registry)
    peek = state.decks.agenda_deck[:2]
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"top": peek, "bottom": []}
    )
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    assert len(state.players["p2"].private.action_cards) == 2
    assert state.players["p2"].strategic_cc == 1


# --- Imperial -------------------------------------------------------------------------------


def test_imperial_mecatol_gives_victory_point_not_secret(registry: StaticDataRegistry) -> None:
    state = _state(8)
    state.decks.secret_objective_deck = ["s1", "s2"]
    state = strategic_action.play_strategy_card(state, registry, "p1", 8)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"objective": None})
    assert state.players["p1"].victory_points == 1
    assert state.players["p1"].private.secret_objectives == []
    with pytest.raises(ValueError, match="needs the map grid"):
        strategic_action.submit_primary_step(
            strategic_action.play_strategy_card(_state(8), registry, "p1", 8),
            registry,
            "p1",
            {"objective": "anything"},
        )


def test_imperial_without_mecatol_draws_secret(registry: StaticDataRegistry) -> None:
    state = _state(8)
    state.systems["000"].planet_owners = {"mecatolrex": "p2"}
    state.decks.secret_objective_deck = ["s1", "s2"]
    state = strategic_action.play_strategy_card(state, registry, "p1", 8)
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    assert state.players["p1"].victory_points == 0
    assert state.players["p1"].private.secret_objectives == ["s1"]


def test_imperial_secret_limit_requires_return(registry: StaticDataRegistry) -> None:
    state = _state(8)
    state.systems["000"].planet_owners = {}
    p1 = state.players["p1"]
    p1.private.secret_objectives = ["h1", "h2"]
    p1.scored_secrets = ["done1"]
    state.decks.secret_objective_deck = ["s1", "s2"]
    state = strategic_action.play_strategy_card(state, registry, "p1", 8)
    with pytest.raises(ValueError, match="more than 3"):
        strategic_action.submit_primary_step(state, registry, "p1", {})
    with pytest.raises(ValueError, match="UNSCORED"):
        strategic_action.submit_primary_step(state, registry, "p1", {"return": "done1"})
    done = strategic_action.submit_primary_step(state, registry, "p1", {"return": "h1"})
    hand = done.players["p1"].private.secret_objectives
    assert sorted(hand) == ["h2", "s1"]
    assert sorted(done.decks.secret_objective_deck) == ["h1", "s2"]


def test_imperial_can_return_the_drawn_card(registry: StaticDataRegistry) -> None:
    state = _state(8)
    state.systems["000"].planet_owners = {}
    p1 = state.players["p1"]
    p1.private.secret_objectives = ["h1", "h2", "h3"]
    state.decks.secret_objective_deck = ["s1"]
    state = strategic_action.play_strategy_card(state, registry, "p1", 8)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"return": "drawn"})
    assert sorted(state.players["p1"].private.secret_objectives) == ["h1", "h2", "h3"]
    assert state.decks.secret_objective_deck == ["s1"]


def test_imperial_secondary_draws_with_token_and_limit(registry: StaticDataRegistry) -> None:
    state = _state(8)
    state.decks.secret_objective_deck = ["s1", "s2"]
    state = strategic_action.play_strategy_card(state, registry, "p1", 8)
    state = strategic_action.submit_primary_step(state, registry, "p1", {})
    state = strategic_action.resolve_secondary(state, registry, "p2", execute=True)
    assert state.players["p2"].private.secret_objectives == ["s1"]
    assert state.players["p2"].strategic_cc == 1


def test_politics_draws_at_speaker_step_and_hides_cards(registry: StaticDataRegistry) -> None:
    from src.api.web_game import _pending_strategy

    state = _politics_ready(registry)
    hand = state.players["p1"].private.action_cards
    assert hand == ["a1", "a2"]  # dobrane od razu po wyborze mówcy
    assert state.speaker_id == "p3"
    own = strategic_action.step_options(state, registry, "p1")
    assert own is not None and own["options"]["drawn"] == ["a1", "a2"]
    public = _pending_strategy(state)
    assert public is not None and "_drawn" not in public["draft"]


def test_imperial_options_carry_progress_rows(registry: StaticDataRegistry) -> None:
    from src.core.hex_grid import HexGrid

    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("101", "26")
    grid.build_edges()
    state = _state(8)
    state.objectives.revealed = ["corner"]
    state = strategic_action.play_strategy_card(state, registry, "p1", 8, grid=grid)
    prompt = strategic_action.step_options(state, registry, "p1", grid)
    assert prompt is not None
    rows = prompt["options"]["public_options"]
    assert [r["key"] for r in rows] == ["corner"]
    assert set(rows[0]) == {"key", "progress", "threshold", "ready", "manual", "spend"}
