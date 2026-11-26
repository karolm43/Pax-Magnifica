"""Meta action cards (``C_action_cards``) and the general action card rules (``R_action_cards``).

Each test tags the points it checks with ``@ruling(...)`` (guard ``tests/test_ruling_coverage.py``).
Points the engine cannot honour yet are listed in ``tests/rulings_status.json``.
"""

from __future__ import annotations

import pytest

from src.api.web_objectives import card_pool_counts
from src.core import (
    action_budget,
    action_cards,
    card_draw,
    card_hold,
    component_action,
    hand_limit,
    hold_rewind,
    invasion,
    reaction_cards,
    rules_hooks,
    status_phase,
    strategic_action,
    strategy_phase,
    transaction,
    turn_flow,
    visibility,
)
from src.core.components import ComponentCategory, ComponentRef
from src.core.game_events import GameEvent
from src.core.game_state import GameState, Phase, SystemState, TacticalStep
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.timing_spec import TriggerKind
from tests import test_action_cards_board as board
from tests import test_action_cards_economy as eco
from tests import test_card_hold as hold
from tests import test_hold_rewind as rewind
from tests import test_reactions_agenda as agendas
from tests import test_reactions_invasion as landing
from tests import test_reactions_misc as misc
from tests.factions.flow_harness import Flow
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    found = StaticDataRegistry()
    rules_hooks.bind_registry(found)
    return found


@pytest.fixture
def grid() -> object:
    yield from landing.grid.__wrapped__()  # type: ignore[attr-defined]


def _row(state: GameState, registry: StaticDataRegistry, player: str, card: str) -> bool:
    return bool(misc._playable(state, registry, player, card)["playable"])


def _held(
    state: GameState, registry: StaticDataRegistry, who: str, card: str, **params: object
) -> GameState:
    new, _ = action_cards.play_action_card(state, registry, who, card, params, now=hold.NOW)
    assert new.held_play is not None
    return new


def _sabotage(state: GameState, registry: StaticDataRegistry, card: str = "sabo1") -> GameState:
    new, _ = action_cards.play_action_card(state, registry, "p2", card, now=hold.NOW)
    assert new.held_play is None
    return new


def _release(state: GameState, registry: StaticDataRegistry) -> GameState:
    assert state.held_play is not None
    return card_hold.release(
        state, registry, state.held_play.player_id, now=hold.NOW + state.held_play.seconds
    )


# ================================================================================== Sabotage


@ruling("C_action_cards/sabotage/1", "R_action_cards/notes/6", "R_action_cards/rules-reference/8")
def test_second_copy_may_be_played_after_sabotage(registry: StaticDataRegistry) -> None:
    card, planets = hold._industrial(registry)
    state = hold._state([card, card], ["sabo1"])
    hold._own(state, planets)
    done = _sabotage(_held(state, registry, "p1", card), registry)
    assert done.players["p1"].trade_goods == 1  # canceled card had no effect
    assert card in done.decks.action_card_discard
    again, _ = action_cards.play_action_card(done, registry, "p1", card)
    assert again.players["p1"].trade_goods == 3


@ruling("C_action_cards/sabotage/2")
def test_canceled_card_costs_nothing(registry: StaticDataRegistry) -> None:
    state = eco._state(["f_researched"], trade_goods=5)
    state.decks.action_card_deck = ["filler"]
    state.players["p2"].private.action_cards = ["sabo1"]
    done = _sabotage(_held(state, registry, "p1", "f_researched"), registry)
    assert done.players["p1"].trade_goods == 5
    assert not done.pending_offers


@ruling("C_action_cards/sabotage/4")
def test_cards_are_drawn_only_after_the_window(registry: StaticDataRegistry) -> None:
    state = hold._state(["spy"], ["sabo1", "fs1"])
    held = _held(state, registry, "p1", "spy", player="p2")
    assert held.players["p2"].private.action_cards == ["sabo1", "fs1"]
    assert held.rng_counter == state.rng_counter
    done = _release(held, registry)
    assert len(done.players["p2"].private.action_cards) == 1
    assert len(done.players["p1"].private.action_cards) == 1


@ruling("C_action_cards/sabotage/5")
def test_research_is_chosen_only_after_the_window(registry: StaticDataRegistry) -> None:
    state = eco._state(["f_researched"], trade_goods=5)
    state.decks.action_card_deck = ["filler"]
    state.players["p2"].private.action_cards = ["fs1"]
    held = _held(state, registry, "p1", "f_researched")
    assert held.held_play is not None and held.held_play.params == {}
    assert not held.pending_offers
    done = _release(held, registry)
    assert any("research_cost" in offer.ctx for offer in done.pending_offers)


@ruling("C_action_cards/sabotage/6")
def test_rider_can_only_be_canceled_when_played(registry: StaticDataRegistry) -> None:
    state = agendas._revealed(
        registry, [agendas.LAW], {"p1": ["imp_rider"], "p3": ["sabo1"]}
    )
    state.decks.action_card_deck = ["filler"]
    held = _held(state, registry, "p1", "imp_rider", outcome="for")
    assert _row(held, registry, "p3", "sabo1")
    done = _release(held, registry)
    assert not _row(done, registry, "p3", "sabo1")
    later = agendas._resolve_for(done, registry)
    assert not _row(later, registry, "p3", "sabo1")


@ruling("C_action_cards/sabotage/7")
def test_canceled_component_action_means_another_action_or_pass(
    registry: StaticDataRegistry,
) -> None:
    card, planets = hold._industrial(registry)
    state = hold._state([card], ["sabo1"])
    hold._own(state, planets)
    done = _sabotage(_held(state, registry, "p1", card), registry)
    assert not done.players["p1"].took_action_this_turn
    with pytest.raises(ValueError, match="must take an action"):
        turn_flow.end_turn(done, "p1")
    component_action.play_component_action(done, "p1")  # a different action
    assert turn_flow.pass_turn(done, "p1").players["p1"].passed  # or a pass


@ruling("C_action_cards/sabotage/7.1", "C_action_cards/master-plan/4")
@pytest.mark.parametrize("source", ["fleet_logistics", "master_plan"])
def test_canceled_second_action_lets_the_turn_end(
    registry: StaticDataRegistry, source: str
) -> None:
    card, planets = hold._industrial(registry)
    state = hold._state([card], ["sabo1"])
    hold._own(state, planets)
    if source == "fleet_logistics":
        state.players["p1"].technologies = ["fl"]
        state = component_action.play_component_action(state, "p1")
    else:
        state.players["p1"].private.action_cards.append("master_plan")
        state = component_action.play_component_action(state, "p1")
        state = _release(_held(state, registry, "p1", "master_plan"), registry)
    done = _sabotage(_held(state, registry, "p1", card), registry)
    ended = turn_flow.end_turn(done, "p1")
    assert ended.active_player_id != "p1"
    assert not ended.players["p1"].passed


# ======================================================================================= Spy


@ruling("C_action_cards/spy/1")
@pytest.mark.parametrize("taken", ["fs1", "reverse_engineer"])
def test_reverse_engineer_is_usable_only_if_spy_did_not_take_it(
    registry: StaticDataRegistry, taken: str
) -> None:
    for seed in range(1, 100):
        state = misc._state({"p1": ["spy"], "p2": ["reverse_engineer", "fs1"]})
        state.rng_seed = seed
        new = misc._play(state, registry, "p1", "spy", {"player": "p2"})
        if new.players["p1"].private.action_cards == [taken]:
            break
    else:
        pytest.fail("no seed takes that card")
    kept = new.players["p2"].private.action_cards
    if taken == "reverse_engineer":
        assert kept == ["fs1"]
        return
    after = misc._play(new, registry, "p2", "reverse_engineer")
    assert after.players["p2"].private.action_cards == ["spy"]


# ============================================================================== Coup D'etat


@ruling("C_action_cards/coup-detat/1")
def test_coup_still_opens_the_end_of_turn_window(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(rewind._action_state(["coup"]), registry, "p1", 1)
    new, _ = action_cards.play_action_card(state, registry, "p2", "coup")
    assert new.turn_end_window is not None and new.turn_end_window.ended_player == "p1"
    assert any(
        w.event is GameEvent.TURN and w.ctx.get("player") == "p1"
        for w in reaction_cards.open_windows(new)
    )


@ruling("C_action_cards/coup-detat/2")
def test_coup_not_playable_against_a_hero_primary(registry: StaticDataRegistry) -> None:
    state = rewind._action_state(["coup"])
    strategic_action.begin_hero_primary(state, registry, "p1", 3, ["p2"])
    assert state.pending_strategy is not None
    assert not reaction_cards.available(state, registry, "p2", "coup")[0]


# ==================================================================================== Crisis


@ruling("C_action_cards/crisis/1")
def test_crisis_skips_the_next_unpassed_player(registry: StaticDataRegistry) -> None:
    state = misc._state({"p1": ["crisis"]})
    state.players["p2"].passed = True
    state = misc._after_p1_turn(state)
    assert state.active_player_id == "p3"
    new = misc._play(state, registry, "p1", "crisis")
    assert new.active_player_id == "p1"  # p3's turn skipped, p2 had passed


@ruling("C_action_cards/crisis/2")
def test_crisis_may_skip_its_own_player(registry: StaticDataRegistry) -> None:
    state = misc._after_p1_turn(misc._state({"p2": ["crisis"]}))
    new = misc._play(state, registry, "p2", "crisis")
    assert new.active_player_id == "p3"


# ====================================================================== Diplomatic Pressure


def _pressed(registry: StaticDataRegistry, hand: list[str]) -> GameState:
    state = agendas._revealed(registry, [agendas.LAW, agendas.DIRECTIVE], {"p1": hand})
    state.players["p3"].private.promissory_notes = ["n1", "n2", "n3"]
    state.players["p2"].private.promissory_notes = ["m1"]
    return state


@ruling("C_action_cards/diplomatic-pressure/1", "C_action_cards/diplomatic-pressure/2")
def test_target_picks_the_note_and_it_is_not_a_transaction(
    registry: StaticDataRegistry,
) -> None:
    from src.core import triggers

    new = agendas._play(_pressed(registry, ["dp1"]), registry, "p1", "dp1", player="p3")
    offer = new.pending_offers[0]
    assert offer.player_id == "p3"
    done = triggers.accept_offer(new, "p3", offer.id, {"note": "n2"})
    assert done.players["p1"].private.promissory_notes == ["n2"]
    assert not done.players["p1"].transacted_with and not done.players["p3"].transacted_with
    assert done.last_transaction == []
    assert transaction.agenda_pair_free(done, "p1", "p3")


@ruling(
    "C_action_cards/diplomatic-pressure/3",
    "C_action_cards/diplomatic-pressure/3.1",
    "C_action_cards/diplomatic-pressure/3.2",
)
def test_one_diplomatic_pressure_per_target_and_agenda(registry: StaticDataRegistry) -> None:
    from src.core import active_effects
    from src.core.game_events import Duration

    state = _pressed(registry, ["dp1", "dp2", "dp3"])
    state = agendas._play(state, registry, "p1", "dp1", player="p2")
    state.players["p2"].private.promissory_notes = ["m2"]
    with pytest.raises(ValueError, match="not chosen yet"):
        action_cards.play_action_card(state, registry, "p1", "dp2", {"player": "p2"})
    other = agendas._play(state, registry, "p1", "dp2", player="p3")
    assert other.pending_offers  # a different target in the same agenda
    later = state.clone()
    active_effects.expire(later, Duration.AGENDA)  # that agenda is resolved
    again = agendas._play(later, registry, "p1", "dp3", player="p2")
    assert "m2" in again.players["p1"].private.promissory_notes


# ============================================================================ Extreme Duress


def _duressed(registry: StaticDataRegistry, hands: dict[str, list[str]] | None = None) -> GameState:
    state = misc._state({"p3": ["extremeduress"], "p2": ["fs1"], **(hands or {})})
    state = misc._after_p1_turn(state)
    return misc._play(state, registry, "p3", "extremeduress")


@ruling("C_action_cards/extreme-duress/1")
def test_first_of_several_actions_must_be_strategic(registry: StaticDataRegistry) -> None:
    state = _duressed(registry)
    state.players["p2"].technologies = ["fl"]
    acted = component_action.play_component_action(state, "p2")
    assert acted.players["p2"].private.action_cards == []
    assert action_budget.actions_left(acted, "p2") == 1


@ruling("C_action_cards/extreme-duress/2")
def test_duress_needs_one_readied_strategy_card(registry: StaticDataRegistry) -> None:
    for exhausted, legal in (([2], True), ([2, 5], False)):
        state = misc._state({"p3": ["extremeduress"]})
        state.players["p2"].strategy_cards = [2, 5]
        state.players["p2"].exhausted_strategy_cards = list(exhausted)
        assert _row(misc._after_p1_turn(state), registry, "p3", "extremeduress") is legal


@ruling("C_action_cards/extreme-duress/2.1")
@pytest.mark.parametrize("initiative", [2, 5])
def test_any_readied_strategy_card_avoids_the_penalty(
    registry: StaticDataRegistry, initiative: int
) -> None:
    state = misc._state({"p3": ["extremeduress"], "p2": ["fs1"]})
    state.players["p2"].strategy_cards = [2, 5]
    state = misc._play(misc._after_p1_turn(state), registry, "p3", "extremeduress")
    played = strategic_action.play_strategy_card(state, registry, "p2", initiative)
    assert played.players["p2"].private.action_cards == ["fs1"]


@ruling("C_action_cards/extreme-duress/3")
def test_duress_survives_a_coup(registry: StaticDataRegistry) -> None:
    state = _duressed(registry, {"p1": ["coup"]})
    state.players["p2"].trade_goods = 3
    declared = strategic_action.play_strategy_card(state, registry, "p2", 2)
    couped, _ = action_cards.play_action_card(declared, registry, "p1", "coup")
    assert couped.players["p2"].private.action_cards == ["fs1"]
    # Other players take turns; the effect waits for p2's next action.
    for pid in ("p3", "p1"):
        couped = turn_flow.end_turn(component_action.play_component_action(couped, pid), pid)
    assert couped.active_player_id == "p2"
    safe = strategic_action.play_strategy_card(couped, registry, "p2", 2)
    assert safe.players["p2"].private.action_cards == ["fs1"]
    punished = component_action.play_component_action(couped, "p2")
    assert punished.players["p2"].private.action_cards == []
    assert punished.players["p2"].trade_goods == 0


def test_duress_survives_a_turn_skipped_by_crisis(registry: StaticDataRegistry) -> None:
    state = misc._state({"p3": ["extremeduress"], "p2": ["fs1"], "p1": ["crisis"]})
    state = misc._play(misc._after_p1_turn(state), registry, "p3", "extremeduress")
    state = misc._play(state, registry, "p1", "crisis")
    for pid in ("p3", "p1"):
        state = turn_flow.end_turn(component_action.play_component_action(state, pid), pid)
    punished = component_action.play_component_action(state, "p2")
    assert punished.players["p2"].private.action_cards == []


# =============================================================================== Master Plan


@ruling("C_action_cards/master-plan/1")
def test_no_turn_boundary_between_master_plan_actions(registry: StaticDataRegistry) -> None:
    state = component_action.play_component_action(misc._state({"p1": ["master_plan"]}), "p1")
    state = misc._play(state, registry, "p1", "master_plan")
    second = component_action.play_component_action(state, "p1")
    for checked in (state, second):
        assert checked.turn_end_window is None
        assert not any(w.event is GameEvent.TURN for w in reaction_cards.open_windows(checked))


@ruling("C_action_cards/master-plan/2")
def test_forced_turn_end_leaves_no_master_plan(registry: StaticDataRegistry) -> None:
    state = component_action.play_component_action(misc._state({"p1": ["master_plan"]}), "p1")
    ended = turn_flow.end_turn(state, "p1", forced=True)
    assert not _row(ended, registry, "p1", "master_plan")
    with pytest.raises(ValueError, match="no open window"):
        action_cards.play_action_card(ended, registry, "p1", "master_plan")


@ruling("C_action_cards/master-plan/3")
def test_master_plan_does_not_allow_passing_after_an_action(
    registry: StaticDataRegistry,
) -> None:
    state = misc._state({"p1": ["master_plan"]})
    state.players["p1"].exhausted_strategy_cards = [1]
    state = component_action.play_component_action(state, "p1")
    state = misc._play(state, registry, "p1", "master_plan")
    with pytest.raises(ValueError, match="already took an action"):
        turn_flow.pass_turn(state, "p1")


# ==================================================================================== Parley


@ruling("C_action_cards/parley/1", "C_action_cards/parley/2")
def test_parley_covers_one_planet_and_locks_the_returned_units(
    grid: HexGrid, registry: StaticDataRegistry
) -> None:
    state = landing._commit_state(grid, registry)
    state = invasion.commit_ground_forces(
        state, registry, {landing._PL1: {"infantry": 1}, landing._PL2: {"infantry": 2}}
    )
    new = landing._play(state, registry, "p2", "parley", {"planet": landing._PL2})
    assert new.invasion is not None
    assert new.invasion.committed == {landing._PL1: {"infantry": 1}}
    assert new.invasion.parley_locked == {"infantry": 2}
    free = new.systems["000"].space_units["p1"]["infantry"] - 2
    with pytest.raises(ValueError, match=f"Only {free} infantry"):
        invasion.commit_ground_forces(new, registry, {landing._PL1: {"infantry": free + 1}})


# =========================================================================== Public Disgrace


@ruling("C_action_cards/public-disgrace/1")
def test_trade_goods_follow_the_player_who_ends_with_the_card(
    registry: StaticDataRegistry,
) -> None:
    before = rewind._strategy_state(["disgrace"])
    before.strategy_card_tg = {3: 2}
    after = strategy_phase.pick_strategy_card(before, registry, "p1", 3)
    assert after.players["p1"].trade_goods == 2
    undone, _ = hold_rewind.play_at(rewind._chain(before, after), registry, "p2", "disgrace", 1)
    picked = strategy_phase.pick_strategy_card(undone, registry, "p1", 4)
    assert picked.players["p1"].trade_goods == 0
    taken = strategy_phase.pick_strategy_card(picked, registry, "p2", 3)
    assert taken.players["p2"].trade_goods == 2


@ruling("C_action_cards/public-disgrace/2")
def test_disgrace_only_during_the_regular_pick(registry: StaticDataRegistry) -> None:
    done = rewind._strategy_state(["disgrace"])
    done.players["p1"].strategy_cards = [1, 3]
    done.players["p2"].strategy_cards = [2, 4]
    outside = rewind._action_state([])
    outside.players["p2"].private.action_cards = ["disgrace"]
    for state in (done, outside):
        assert strategy_phase.next_strategy_picker(state) is None or state.phase is Phase.ACTION
        assert not any(
            w.event is GameEvent.STRATEGY_CARD_CHOSEN for w in reaction_cards.open_windows(state)
        )


# ======================================================================= Puppets on a String


def _puppets(registry: StaticDataRegistry, *extra: str) -> GameState:
    state = misc._state({"p3": ["puppetsonastring", *extra]})
    state.players["p3"].passed = True
    state.players["p3"].exhausted_strategy_cards = [3]
    return misc._play(misc._after_p1_turn(state), registry, "p3", "puppetsonastring")


@ruling("C_action_cards/puppets-on-a-string/1")
def test_puppets_player_is_active(registry: StaticDataRegistry) -> None:
    state = _puppets(registry)
    assert state.active_player_id == "p3"
    component_action.play_component_action(state, "p3")


@ruling("C_action_cards/puppets-on-a-string/2", "C_action_cards/puppets-on-a-string/2.1")
def test_puppets_action_is_not_a_turn(registry: StaticDataRegistry) -> None:
    state = _puppets(registry)
    acted = component_action.play_component_action(state, "p3")
    for checked in (state, acted):
        assert not any(w.event is GameEvent.TURN for w in reaction_cards.open_windows(checked))


@ruling("C_action_cards/puppets-on-a-string/5", "C_action_cards/puppets-on-a-string/6.1")
def test_puppets_player_may_use_master_plan(registry: StaticDataRegistry) -> None:
    acted = component_action.play_component_action(_puppets(registry, "master_plan"), "p3")
    assert _row(acted, registry, "p3", "master_plan")
    more = misc._play(acted, registry, "p3", "master_plan")
    second = component_action.play_component_action(more, "p3")
    back = turn_flow.end_turn(second, "p3")
    assert back.active_player_id == "p2" and back.players["p3"].passed


@ruling("C_action_cards/puppets-on-a-string/6")
def test_puppets_player_gets_no_fleet_logistics_action(registry: StaticDataRegistry) -> None:
    state = _puppets(registry)
    state.players["p3"].technologies = ["fl"]
    assert action_budget.actions_left(state, "p3") == 1
    acted = component_action.play_component_action(state, "p3")
    with pytest.raises(ValueError, match="already took an action"):
        component_action.play_component_action(acted, "p3")


@ruling("C_action_cards/puppets-on-a-string/7.1")
def test_puppets_action_does_not_score_prove_endurance(registry: StaticDataRegistry) -> None:
    state = _puppets(registry)
    state.players["p1"].passed = True
    state.players["p2"].passed = True
    state.players["p3"].private.secret_objectives = ["pe"]
    back = turn_flow.end_turn(component_action.play_component_action(state, "p3"), "p3")
    assert back.players["p3"].passed
    assert back.players["p3"].private.secret_objectives == ["pe"]
    # Control: a real last pass of the round does score it.
    normal = misc._state()
    normal.players["p1"].passed = normal.players["p2"].passed = True
    normal.players["p3"].exhausted_strategy_cards = [3]
    normal.players["p3"].private.secret_objectives = ["pe"]
    normal.active_player_id = "p3"
    assert turn_flow.pass_turn(normal, "p3").players["p3"].private.secret_objectives == []


# ================================================================== Strategize / Brilliance


@ruling("C_action_cards/strategize/1")
@pytest.mark.parametrize(("initiative", "cost"), [(1, 0), (4, 1), (7, 1)])
def test_strategize_costs_a_token_except_leadership(
    registry: StaticDataRegistry, initiative: int, cost: int
) -> None:
    state = board._state(["strategize1"], strategic_cc=0)
    new = board._play(registry, state, "strategize1", {"initiative": initiative})
    assert new.pending_window is not None and new.pending_window.context["cost"] == cost
    if cost:
        with pytest.raises(ValueError, match="strategy pool"):
            strategic_action.resolve_secondary(new, registry, "p1", execute=True, payload={})


@ruling("C_action_cards/brilliance/1", "C_action_cards/brilliance/2")
@pytest.mark.parametrize("chosen", ["p1", "p2"])
def test_brilliance_gives_the_chosen_players_own_breakthrough(
    registry: StaticDataRegistry, chosen: str
) -> None:
    state = eco._state(["brilliance"])
    state.fracture.in_play = True
    new = eco._play(state, registry, "brilliance", {"player": chosen})
    unlocked = {pid for pid, p in new.players.items() if p.breakthrough_unlocked}
    assert unlocked == {chosen}
    found = registry.breakthrough_for_faction(new.players[chosen].faction)
    assert found is not None and found.faction == new.players[chosen].faction


# ============================================================== R_action_cards: drawing


def _deck_state(cards: list[str]) -> GameState:
    state = misc._state()
    state.decks.action_card_deck = list(cards)
    return state


@ruling("R_action_cards/rules-reference/1", "R_action_cards/notes/5")
def test_status_phase_draws_one_card_each_in_order(registry: StaticDataRegistry) -> None:
    state = _deck_state(["a", "b", "c", "d"])
    drawn = status_phase._draw_action_cards(state, ["p2", "p3", "p1"])
    assert drawn == {"p2": 1, "p3": 1, "p1": 1}
    assert [state.players[p].private.action_cards for p in ("p2", "p3", "p1")] == [
        ["a"], ["b"], ["c"]
    ]


@ruling("R_action_cards/notes/5.1")
def test_neural_motivator_draws_both_cards_before_the_next_player(
    registry: StaticDataRegistry,
) -> None:
    state = _deck_state(["a", "b", "c", "d", "e"])
    state.players["p1"].technologies = ["nm"]
    status_phase._draw_action_cards(state, ["p1", "p2", "p3"])
    assert state.players["p1"].private.action_cards == ["a", "b"]
    assert state.players["p2"].private.action_cards == ["c"]


@ruling("R_action_cards/rules-reference/2")
def test_politics_primary_and_secondary_draw_cards(registry: StaticDataRegistry) -> None:
    state = misc._state()
    state.players["p1"].strategy_cards = [3]
    state.players["p2"].strategy_cards = [2]
    state.players["p2"].strategic_cc = 1
    state.speaker_id = "p1"
    state.decks.action_card_deck = ["a", "b", "c", "d", "e"]
    played = strategic_action.play_strategy_card(state, registry, "p1", 3)
    chosen = strategic_action.submit_primary_step(played, registry, "p1", {"player": "p2"})
    assert chosen.players["p1"].private.action_cards == ["a", "b"]
    secondary = state.clone()
    strategic_action.begin_strategize_secondary(secondary, "p2", 3)
    done = strategic_action.resolve_secondary(secondary, registry, "p2", execute=True, payload={})
    assert done.players["p2"].private.action_cards == ["a", "b"]


@ruling("R_action_cards/rules-reference/3", "R_action_cards/notes/4")
def test_draw_takes_the_top_card_and_reshuffles_the_discard(
    registry: StaticDataRegistry,
) -> None:
    state = _deck_state(["top", "next"])
    state.decks.action_card_discard = ["old"]
    card_draw.draw_action_card(state, "p1")
    assert state.players["p1"].private.action_cards == ["top"]
    card_draw.draw_action_card(state, "p1")
    card_draw.draw_action_card(state, "p1")
    assert state.players["p1"].private.action_cards == ["top", "next", "old"]
    assert state.decks.action_card_discard == []


@ruling("R_action_cards/notes/1")
def test_players_start_without_action_cards(registry: StaticDataRegistry) -> None:
    state = Flow(registry, "hacan").state()
    assert all(not p["private"]["action_cards"] for p in state["players"].values())


# ======================================================== R_action_cards: hand and secrecy


@ruling("R_action_cards/rules-reference/4", "R_action_cards/rules-reference/4.1")
def test_hand_limit_is_seven_and_effects_change_it(registry: StaticDataRegistry) -> None:
    state = misc._state({"p1": [f"fs{i % 4 + 1}" for i in range(9)]})
    assert hand_limit.action_card_limit(state, "p1") == 7
    assert hand_limit.action_card_excess(state, "p1") == 2
    assert len(state.players["p1"].private.action_cards) == 9  # nothing discarded for them
    state.decks.agenda_laws = {"sanctions": "for"}
    assert hand_limit.action_card_limit(state, "p1") == 3


@ruling("R_action_cards/rules-reference/5", "R_action_cards/notes/2")
def test_hand_is_hidden_but_its_size_is_public(registry: StaticDataRegistry) -> None:
    state = misc._state({"p1": ["fs1", "fs2"]})
    seen = visibility.project_for_viewer(state, "p2")
    assert seen.players["p1"].private.action_cards == []
    assert seen.players["p1"].hidden_card_counts["action_cards"] == 2


@ruling("R_action_cards/notes/10")
def test_discard_pile_is_public(registry: StaticDataRegistry) -> None:
    state = misc._state({"p1": ["economic_initiative"]})
    new = misc._play(state, registry, "p1", "economic_initiative")
    assert card_pool_counts(new, registry)["actionCardDiscard"] == ["economic_initiative"]


# ================================================================= R_action_cards: playing


@ruling("R_action_cards/rules-reference/6")
def test_every_card_has_a_timing_from_its_first_paragraph(
    registry: StaticDataRegistry,
) -> None:
    cards = registry.catalog.all(ComponentCategory.ACTION_CARD)
    assert cards
    for card_id, card in cards.items():
        spec = registry.catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, card_id))
        assert spec is not None, card_id
        window = str(getattr(card, "window", "") or "")
        if window:
            assert (spec.trigger is TriggerKind.ACTION) == (window == "Action"), card_id


@ruling("R_action_cards/rules-reference/6.1", "R_action_cards/rules-reference/7")
def test_action_card_is_a_component_action_resolved_then_discarded(
    registry: StaticDataRegistry,
) -> None:
    state = misc._state({"p1": ["economic_initiative", "spy"]})
    assert not _row(state, registry, "p1", "spy")  # nobody to take a card from
    with pytest.raises(ValueError):
        action_cards.play_action_card(state, registry, "p1", "spy", {"player": "p2"})
    new = misc._play(state, registry, "p1", "economic_initiative")
    assert new.players["p1"].took_action_this_turn
    assert new.players["p1"].private.action_cards == ["spy"]
    assert new.decks.action_card_discard == ["economic_initiative"]
    status = state.clone()
    status.phase = Phase.STATUS
    assert not _row(status, registry, "p1", "economic_initiative")


@ruling("R_action_cards/rules-reference/6.2")
def test_a_second_flank_speed_waits_for_a_new_window(registry: StaticDataRegistry) -> None:
    state = misc._state({"p1": ["fs1", "fs2"]})
    state.active_system = "000"
    state.tactical_step = TacticalStep.MOVEMENT
    once = misc._play(state, registry, "p1", "fs1")
    assert not _row(once, registry, "p1", "fs2")
    assert rules_hooks.modify(rules_hooks.POINT_MOVEMENT_MOVE_VALUE, once, "p1", 2) == 3


@ruling("R_action_cards/rules-reference/6.2")
def test_a_canceled_copy_does_not_count_as_played(registry: StaticDataRegistry) -> None:
    state = hold._state(["fs1", "fs2"], ["sabo1"], tactical=True)
    done = _sabotage(_held(state, registry, "p1", "fs1"), registry)
    assert _row(done, registry, "p1", "fs2")


@ruling("R_action_cards/notes/7")
@pytest.mark.parametrize("card", ["lucky", "plague"])
def test_destroying_cards_never_target_own_units(
    registry: StaticDataRegistry, card: str
) -> None:
    state = board._state(
        [card],
        [
            SystemState(
                position="101", system_id="01", planet_owners={"jord": "p1"},
                planet_units={"jord": {"p1": {"infantry": 3}}},
                space_units={"p1": {"destroyer": 1}},
            )
        ],
    )
    assert not _row(state, registry, "p1", card)


@ruling("R_action_cards/notes/8")
def test_each_card_may_be_played_with_zero_targets(registry: StaticDataRegistry) -> None:
    state = board._state(["f_conscription"], [])
    assert board._playable(registry, state, "f_conscription")
    new = board._play(registry, state, "f_conscription")
    assert new.decks.action_card_discard == ["f_conscription"]


@ruling("R_action_cards/notes/9")
def test_repeal_law_needs_a_law(registry: StaticDataRegistry) -> None:
    state = misc._state({"p1": ["repeal"]})
    assert not state.decks.agenda_laws
    assert not _row(state, registry, "p1", "repeal")
    state.decks.agenda_laws = {agendas.LAW: "for"}
    assert _row(state, registry, "p1", "repeal")
    new = misc._play(state, registry, "p1", "repeal", {"law": agendas.LAW})
    assert agendas.LAW not in new.decks.agenda_laws
