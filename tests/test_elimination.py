"""Eliminacja gracza (R_elimination, ``core/elimination.py``) - warunki i skutki."""

from __future__ import annotations

import pytest

from src.core import elimination, rules_hooks, strategy_phase, turn_flow
from src.core.activity import derive_activity
from src.core.game_state import EliminatedPlayer, GameState, Phase, PlayerState, SystemState
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling


@pytest.fixture(scope="module", autouse=True)
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _state() -> GameState:
    """p1 (Arborec, czerwony): tylko flagowiec w systemie 000. p2, p3 z planetami."""
    players = {
        "p1": PlayerState(player_id="p1", color="red", faction="arborec", home_position="101"),
        "p2": PlayerState(
            player_id="p2", color="blue", faction="hacan", controlled_planets=["mollprimus"]
        ),
        "p3": PlayerState(
            player_id="p3", color="green", faction="sol", controlled_planets=["wellon"]
        ),
    }
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        speaker_id="p1",
        seating_order=["p1", "p2", "p3"],
        players=players,
        systems={
            "000": SystemState(
                position="000", system_id="18",
                space_units={"p1": {"flagship": 1}}, command_tokens=["p1", "p2"],
            ),
            "101": SystemState(position="101", system_id="5"),  # dom p1, bez jego planet
            "104": SystemState(
                position="104", system_id="19", planet_owners={"mollprimus": "p2"},
                planet_units={"mollprimus": {"p2": {"infantry": 1}}},
            ),
        },
    )


@ruling(
    "R_elimination/rules-reference/1", "R_elimination/rules-reference/1.1",
    "R_elimination/rules-reference/1.2", "R_elimination/rules-reference/1.3",
    "R_elimination/notes/1",
)
def test_eliminated_only_when_all_three_conditions_hold(registry: StaticDataRegistry) -> None:
    state = _state()
    # Flagowiec Arboreców produkuje, ale nie ma PRODUCTION - nie chroni przed eliminacją.
    assert elimination.meets_conditions(state, registry, "p1")
    state.systems["000"].space_units["p1"]["infantry"] = 1  # siła naziemna (także w kosmosie)
    assert not elimination.meets_conditions(state, registry, "p1")
    del state.systems["000"].space_units["p1"]["infantry"]
    state.systems["104"].planet_units["mollprimus"]["p1"] = {"spacedock": 1}  # PRODUCTION
    assert not elimination.meets_conditions(state, registry, "p1")
    del state.systems["104"].planet_units["mollprimus"]["p1"]
    state.players["p1"].controlled_planets = ["nestphar"]
    assert not elimination.meets_conditions(state, registry, "p1")


@ruling(
    "R_elimination/rules-reference/2", "R_elimination/rules-reference/3",
    "R_elimination/rules-reference/4", "R_elimination/rules-reference/4.1",
    "R_elimination/rules-reference/5", "R_elimination/rules-reference/6",
    "R_elimination/rules-reference/7", "R_elimination/rules-reference/8",
)
def test_elimination_removes_the_player_and_returns_components(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    p1 = state.players["p1"]
    p1.strategy_cards = [3]
    p1.private.action_cards = ["sabotage1"]
    p1.private.secret_objectives = ["btv"]
    p1.scored_secrets = ["dts"]
    p1.private.promissory_notes = ["blue_cf", "red_ta"]
    state.players["p2"].private.promissory_notes = ["red_cf"]
    state.players["p3"].promissory_notes_in_play = ["red_sftt"]
    state.decks.agenda_laws = {"censure": "p1", "minister_war": "p2"}

    assert elimination.check_all(state, registry) == ["p1"]
    assert "p1" not in state.players and state.seating_order == ["p2", "p3"]
    assert state.systems["000"].space_units.get("p1", {}) == {}
    assert state.systems["000"].command_tokens == ["p2"]
    assert state.players["p2"].private.promissory_notes == ["blue_cf"]  # wróciła, red_cf nie
    assert state.players["p3"].promissory_notes_in_play == []
    assert "censure" in state.decks.agenda_discard and "minister_war" in state.decks.agenda_laws
    assert "sabotage1" in state.decks.action_card_discard
    assert {"btv", "dts"} <= set(state.decks.secret_objective_deck)
    assert all(3 not in p.strategy_cards for p in state.players.values())
    assert state.speaker_id == "p2"  # mówca przechodzi na gracza po lewej
    assert [e.player_id for e in state.eliminated_players] == ["p1"]


@ruling(
    "R_elimination/notes/3", "R_relics/notes/2",
    "C_exploration_cards/cultural-relic-fragment/2",
    "C_exploration_cards/hazardous-relic-fragment/2",
    "C_exploration_cards/industrial-relic-fragment/2",
    "C_exploration_cards/unknown-relic-fragment/2",
)
def test_fragments_go_to_their_discard_piles_and_relics_are_purged(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.players["p1"].relic_fragments = ["crf1", "hrf1", "irf1", "urf1"]
    state.players["p1"].relics = ["emelpar"]
    elimination.check_all(state, registry)
    discard = state.decks.exploration_discard
    assert (discard["cultural"], discard["hazardous"]) == (["crf1"], ["hrf1"])
    assert (discard["industrial"], discard["frontier"]) == (["irf1"], ["urf1"])
    assert "emelpar" in state.decks.purged


@ruling("R_elimination/rules-reference/9")
def test_five_player_game_keeps_one_strategy_card_after_elimination() -> None:
    state = _state()
    for pid in ("p4", "p5"):
        state.players[pid] = PlayerState(player_id=pid)
    assert strategy_phase.pick_count(state) == 1
    del state.players["p5"]
    state.eliminated_players.append(EliminatedPlayer(player_id="p5"))
    assert len(state.players) == 4 and strategy_phase.pick_count(state) == 1


@ruling("R_elimination/notes/2", "R_elimination/notes/2.1")
def test_eliminated_home_system_stays_a_home_system(registry: StaticDataRegistry) -> None:
    from src.core import objective_events
    from src.core.game_state import ActiveCombat, CombatStep
    from src.core.hex_grid import HexGrid

    state = _state()
    elimination.check_all(state, registry)
    state.players["p2"].private.secret_objectives = ["dts"]
    combat = ActiveCombat(
        kind="space", position="101", attacker="p2", defender="p3", step=CombatStep.DONE
    )
    objective_events.on_combat_end(state, HexGrid(), combat, "p2")
    assert state.players["p2"].scored_secrets == ["dts"]  # Darken the Skies w domu p1


def test_end_turn_eliminates_and_passes_the_turn_on(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].took_action_this_turn = True
    after = turn_flow.end_turn(state, "p1", registry=registry)
    assert "p1" not in after.players
    assert after.active_player_id in {"p2", "p3"}
    entry = derive_activity("turn:end", state, after)
    assert entry is not None
    assert ("eliminated", "p1") in [(f.type, f.player_id) for f in entry.facts]


def test_last_player_is_never_eliminated(registry: StaticDataRegistry) -> None:
    state = _state()
    del state.players["p2"], state.players["p3"]
    state.seating_order = ["p1"]
    assert elimination.check_all(state, registry) == []
