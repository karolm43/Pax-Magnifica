"""Testy fazy statusu (RULES.md 41): cele, punktowanie, kroki 1–8, setup celów."""

from __future__ import annotations

import random

import pytest

from src.core import objectives, status_phase, turn_flow
from src.core.components import ComponentCategory
from src.core.game_state import (
    GameState,
    Phase,
    PlayerState,
    StatusStep,
    SystemState,
)
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(registry: StaticDataRegistry) -> GameState:
    """3 graczy w fazie akcji (po 2 karty: inicjatywy 1/3/5), cele po setupie."""
    players = {
        pid: PlayerState(player_id=pid, color=pid, strategy_cards=cards)
        for pid, cards in (("p1", [1, 2]), ("p2", [3, 4]), ("p3", [5, 6]))
    }
    state = GameState(
        phase=Phase.ACTION,
        round_number=1,
        seating_order=["p1", "p2", "p3"],
        speaker_id="p2",
        active_player_id="p1",
        players=players,
        systems={
            "101": SystemState(position="101", system_id="1", command_tokens=["p1", "p2"]),
            "102": SystemState(position="102", system_id="2", command_tokens=["p1"]),
        },
    )
    return objectives.setup_objectives(state, registry, random.Random(7))


def _enter_status(state: GameState) -> GameState:
    out = turn_flow.next_phase(state)
    assert out.phase is Phase.STATUS and out.status is not None
    return out


# --------------------------------------------------------------------------- setup celów


def test_setup_draws_five_plus_five_and_reveals_two(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    o = state.objectives
    assert len(o.revealed) == 2
    assert len(o.stage1_deck) == 3  # 5 wylosowanych - 2 odkryte
    assert len(o.stage2_deck) == 5
    # Odkryte cele to cele I etapu; talia II etapu zawiera wyłącznie cele II etapu.
    assert all(objectives.objective_stage(registry, oid) == 1 for oid in o.revealed)
    assert all(objectives.objective_stage(registry, oid) == 2 for oid in o.stage2_deck)
    assert len(set(o.revealed + o.stage1_deck + o.stage2_deck)) == 10


def test_setup_deals_one_secret_each_and_shuffles_action_deck(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry)
    hands = [p.private.secret_objectives for p in state.players.values()]
    assert all(len(h) == 1 for h in hands)
    assert len({h[0] for h in hands}) == 3
    assert state.decks.action_card_deck
    assert not state.decks.action_card_discard


def test_setup_is_seedable(registry: StaticDataRegistry) -> None:
    a = _state(registry)
    b = _state(registry)
    assert a.objectives == b.objectives


# --------------------------------------------------------------------------- krok 1


def test_entering_status_initialises_steps_without_repair(registry: StaticDataRegistry) -> None:
    out = _enter_status(_state(registry))
    assert out.status is not None and out.status.step is StatusStep.SCORE_OBJECTIVES
    assert out.active_player_id == "p1"  # inicjatywa 1


def test_score_public_awards_points_and_limits_to_one(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    first, second = state.objectives.revealed
    state = status_phase.score_objective(state, registry, "p1", "public", first)
    assert state.players["p1"].victory_points == 1
    assert state.objectives.scored[first] == ["p1"]
    with pytest.raises(ValueError, match="already scored a public"):
        status_phase.score_objective(state, registry, "p1", "public", second)


def test_score_public_requires_players_turn(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    with pytest.raises(ValueError, match="not p2's turn"):
        status_phase.score_objective(
            state, registry, "p2", "public", state.objectives.revealed[0]
        )


def test_score_public_rejects_unrevealed_and_duplicate(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    with pytest.raises(ValueError, match="not revealed"):
        status_phase.score_objective(
            state, registry, "p1", "public", state.objectives.stage1_deck[0]
        )
    done = status_phase.score_objective(
        state, registry, "p1", "public", state.objectives.revealed[0]
    )
    with pytest.raises(ValueError, match="already scored"):
        objectives.score_public(done, registry, "p1", state.objectives.revealed[0])


def test_score_public_requires_home_planets(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    faction_id = next(
        fid for fid, f in registry.factions.items() if f.home_planets and f.leaders
    )
    state.players["p1"].faction = faction_id  # planety domowe nie należą do p1
    with pytest.raises(ValueError, match="home system"):
        status_phase.score_objective(
            state, registry, "p1", "public", state.objectives.revealed[0]
        )


def test_score_secret_reveals_card_and_limits_to_one(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    status_secrets = [
        sid
        for sid in registry.catalog.all(ComponentCategory.SECRET_OBJECTIVE)
        if (definition := objectives.objective_def(registry, sid)) is not None
        and definition.phase == "Status"
    ]
    state.players["p1"].private.secret_objectives = status_secrets[:2]
    state = status_phase.score_objective(state, registry, "p1", "secret", status_secrets[0])
    assert state.players["p1"].scored_secrets == [status_secrets[0]]
    assert state.players["p1"].private.secret_objectives == [status_secrets[1]]
    assert state.players["p1"].victory_points == 1
    with pytest.raises(ValueError, match="already scored a secret"):
        status_phase.score_objective(state, registry, "p1", "secret", status_secrets[1])


def test_score_secret_must_be_in_hand(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    with pytest.raises(ValueError, match="not in your hand"):
        status_phase.score_objective(state, registry, "p1", "secret", "nonexistent")


def test_reaching_vp_limit_ends_the_game(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    state.players["p1"].victory_points = 9
    state = status_phase.score_objective(
        state, registry, "p1", "public", state.objectives.revealed[0]
    )
    assert state.winner_id == "p1"
    with pytest.raises(ValueError, match="game has ended"):
        status_phase.finish_scoring(state, registry, "p1")


# --------------------------------------------------------------------------- kroki 2-8


def _finish_all_scoring(state: GameState, registry: StaticDataRegistry) -> GameState:
    for pid in ("p1", "p2", "p3"):
        state = status_phase.finish_scoring(state, registry, pid)
    return state


def test_finish_scoring_passes_turn_in_initiative_order(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    state = status_phase.finish_scoring(state, registry, "p1")
    assert state.active_player_id == "p2" and state.status is not None
    assert state.status.step is StatusStep.SCORE_OBJECTIVES
    with pytest.raises(ValueError, match="not p1's turn"):
        status_phase.finish_scoring(state, registry, "p1")


def test_steps_2_to_5_run_after_last_player(registry: StaticDataRegistry) -> None:
    before = _enter_status(_state(registry))
    stage1_before = len(before.objectives.stage1_deck)
    out = _finish_all_scoring(before, registry)
    assert out.status is not None and out.status.step is StatusStep.REDISTRIBUTE
    # Krok 2: odkryty kolejny cel I etapu.
    assert len(out.objectives.revealed) == 3
    assert len(out.objectives.stage1_deck) == stage1_before - 1
    # Krok 3: każdy dobrał jedną kartę akcji.
    assert all(len(p.private.action_cards) == 1 for p in out.players.values())
    # Krok 4: żetony zdjęte z planszy i zwrócone do rezerwy.
    assert all(not s.command_tokens for s in out.systems.values())
    assert out.players["p1"].cc_reinf == before.players["p1"].cc_reinf + 2 - 2
    # Krok 5: +2 żetony pobrane z rezerwy, czekają na przydział.
    assert out.status.unassigned_cc == {"p1": 2, "p2": 2, "p3": 2}


def test_stage2_revealed_only_after_all_stage1(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    for _ in range(3):
        state, revealed = objectives.reveal_next_public(state)
        assert revealed is not None
        assert objectives.objective_stage(registry, revealed) == 1
    state, revealed = objectives.reveal_next_public(state)
    assert revealed is not None and objectives.objective_stage(registry, revealed) == 2


def test_no_unrevealed_objective_ends_the_game(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    state.objectives.stage1_deck = []
    state.objectives.stage2_deck = []
    state.players["p3"].victory_points = 4
    state.players["p1"].victory_points = 4
    out = _finish_all_scoring(state, registry)
    assert out.winner_id == "p1"  # remis na 4 VP — wygrywa pierwszy wg inicjatywy
    assert out.status is not None and out.status.step is StatusStep.COMPLETE


def test_redistribute_validates_total_and_completes_phase(registry: StaticDataRegistry) -> None:
    state = _finish_all_scoring(_enter_status(_state(registry)), registry)
    with pytest.raises(ValueError, match="exactly 10"):
        status_phase.redistribute(state, registry, "p1", 1, 1, 1)
    with pytest.raises(ValueError, match="negative"):
        status_phase.redistribute(state, registry, "p1", -1, 6, 5)
    state = status_phase.redistribute(state, registry, "p1", 5, 3, 2)
    assert (state.players["p1"].tactical_cc, state.players["p1"].fleet_cc) == (5, 3)
    assert state.players["p1"].strategic_cc == 2
    with pytest.raises(ValueError, match="already confirmed"):
        status_phase.redistribute(state, registry, "p1", 5, 3, 2)
    state = status_phase.redistribute(state, registry, "p2", 3, 3, 4)
    assert state.status is not None and state.status.step is StatusStep.REDISTRIBUTE
    state = status_phase.redistribute(state, registry, "p3", 3, 3, 4)
    assert state.status is not None and state.status.step is StatusStep.COMPLETE
    assert turn_flow.can_advance_phase(state)
    assert state.active_player_id == "p2"  # mówca ogłasza krok 8


def test_ready_and_repair_run_at_the_end(registry: StaticDataRegistry) -> None:
    state = _finish_all_scoring(_enter_status(_state(registry)), registry)
    player = state.players["p1"]
    player.exhausted_planets = ["x"]
    player.exhausted_technologies = ["y"]
    player.exhausted_strategy_cards = [1]
    player.leader_states = {"agent": "exhausted", "hero": "locked"}
    state.systems["101"].space_units = {"p1": {"dreadnought": 1}}
    state.systems["101"].damaged_units = {"space": {"p1": {"dreadnought": 1}}}
    for pid in ("p1", "p2", "p3"):
        s = state.players[pid]
        state = status_phase.redistribute(
            state, registry, pid, s.tactical_cc + 2, s.fleet_cc, s.strategic_cc
        )
    done = state.players["p1"]
    assert done.exhausted_planets == [] and done.exhausted_technologies == []
    assert done.exhausted_strategy_cards == []
    assert done.leader_states == {"agent": "unlocked", "hero": "locked"}
    assert state.systems["101"].damaged_units == {}


def test_fleet_excess_reported_after_reducing_fleet_pool(registry: StaticDataRegistry) -> None:
    state = _finish_all_scoring(_enter_status(_state(registry)), registry)
    state.systems["101"].space_units = {"p1": {"cruiser": 3, "fighter": 4}}
    state = status_phase.redistribute(state, registry, "p1", 6, 2, 2)
    assert state.status is not None
    # 3 krążowniki (myśliwce się nie liczą) przy fleet pool 2 → nadwyżka 1.
    assert state.status.fleet_excess == {"p1": {"101": 1}}


def test_finish_status_without_custodians_starts_new_round(
    registry: StaticDataRegistry,
) -> None:
    state = _finish_all_scoring(_enter_status(_state(registry)), registry)
    for pid in ("p1", "p2", "p3"):
        s = state.players[pid]
        state = status_phase.redistribute(
            state, registry, pid, s.tactical_cc + 2, s.fleet_cc, s.strategic_cc
        )
    out = status_phase.finish_status(state, registry)
    assert out.phase is Phase.STRATEGY and out.round_number == 2
    assert out.status is None
    assert all(not p.strategy_cards for p in out.players.values())
    # TG doliczone na niewybranych kartach (zestaw ma 8 kart, wybrane 3).
    assert sum(out.strategy_card_tg.values()) > 0


def test_finish_status_with_custodians_goes_to_agenda(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.custodians_removed = True
    state = _finish_all_scoring(_enter_status(state), registry)
    for pid in ("p1", "p2", "p3"):
        s = state.players[pid]
        state = status_phase.redistribute(
            state, registry, pid, s.tactical_cc + 2, s.fleet_cc, s.strategic_cc
        )
    out = status_phase.finish_status(state, registry)
    assert out.phase is Phase.AGENDA and out.round_number == 1
    assert out.active_player_id == "p2"  # mówca
    assert all(not p.strategy_cards for p in out.players.values())


def test_finish_status_requires_completed_steps(registry: StaticDataRegistry) -> None:
    state = _enter_status(_state(registry))
    with pytest.raises(ValueError, match="Wrong status step"):
        status_phase.finish_status(state, registry)
    assert not turn_flow.can_advance_phase(state)


def test_phase_step_is_blocked_while_status_runs_in_steps(
    registry: StaticDataRegistry,
) -> None:
    state = _enter_status(_state(registry))
    with pytest.raises(ValueError, match="runs in steps"):
        turn_flow.advance_active_player(state, mark_passed=True)


# --------------------------------------------------------------------------- karty akcji


def test_action_cards_dealt_to_lowest_initiative_when_deck_is_short(
    registry: StaticDataRegistry,
) -> None:
    state = _enter_status(_state(registry))
    state.decks.action_card_deck = ["a1", "a2"]
    state.decks.action_card_discard = ["d1", "d2", "d3"]
    out = _finish_all_scoring(state, registry)
    # Talia (2 karty) trafia najpierw do najniższych w inicjatywie: p3, p2; p1 z przetasowanej.
    assert out.players["p3"].private.action_cards == ["a1"]
    assert out.players["p2"].private.action_cards == ["a2"]
    assert len(out.players["p1"].private.action_cards) == 1
    assert out.players["p1"].private.action_cards[0] in {"d1", "d2", "d3"}
    assert len(out.decks.action_card_deck) == 2 and not out.decks.action_card_discard


# --------------------------------------------------------------------------- tryb testowy


def test_complete_status_fast_forwards_default_decisions(registry: StaticDataRegistry) -> None:
    out = status_phase.complete_status(_enter_status(_state(registry)), registry)
    assert out.phase is Phase.STRATEGY and out.round_number == 2
    # Nowe żetony trafiły do puli taktycznej (3 + 2).
    assert out.players["p1"].tactical_cc == 5
