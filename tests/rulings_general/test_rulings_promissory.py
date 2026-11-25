"""Notki ogólne — rulingi ``docs/rules_tirules/C_promissory_notes.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty, które sprawdza (strażnik
``tests/test_ruling_coverage.py``, kontrakt ogólny). Podstawowe testy notek:
``tests/test_promissory_play.py``; statusy bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

import pytest

from src.core import (
    active_effects,
    agenda_phase,
    economy,
    faction_components,
    production,
    promissory_notes,
    promissory_play,
    rules_hooks,
    space_cannon,
    strategic_action,
    transaction,
    triggers,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.hooks import promissory_generic
from src.core.registry import StaticDataRegistry
from src.core.transaction import TransactionSide
from tests.rulings import ruling
from tests.test_promissory_play import _activate, _rows
from tests.test_promissory_play import _state as pn_state


@pytest.fixture(scope="module", autouse=True)
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _received(state: GameState, note: str) -> PlayerState:
    """p1 (red) daje swoją notkę ``note`` graczowi p2; zwraca p2."""
    state.players["p1"].private.promissory_notes.append(note)
    promissory_notes.transfer(state, "p1", "p2", note)
    return state.players["p2"]


def _activate_by_p2(state: GameState, position: str) -> None:
    triggers.fire(
        state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
        ctx={"player": "p2", "position": position},
    )


# ============================================================ Alliance / Support for the Throne


@ruling(
    "C_promissory_notes/support-for-the-throne/1",
    "C_promissory_notes/alliance/1",
    "C_promissory_notes/support-for-the-throne/1",
    "C_promissory_notes/support-for-the-throne/1.1",
)
@pytest.mark.parametrize("note", ["red_an", "red_sftt"])
def test_received_note_goes_straight_to_play_area(note: str) -> None:
    state = pn_state()
    p2 = _received(state, note)
    assert note in p2.promissory_notes_in_play and note not in p2.private.promissory_notes
    with pytest.raises(ValueError):  # nie ma jej w ręce - nie da się jej dalej oddać
        promissory_notes.transfer(state, "p2", "p1", note)


@ruling(
    "C_promissory_notes/support-for-the-throne/2",
    "C_promissory_notes/alliance/3",
    "C_promissory_notes/support-for-the-throne/2",
    "C_promissory_notes/support-for-the-throne/3",
)
@pytest.mark.parametrize("note", ["red_an", "red_sftt"])
def test_activating_system_with_only_owner_structures_returns_note(note: str) -> None:
    state = pn_state()
    _received(state, note)
    state.systems["101"].planet_units["pl"] = {"p1": {"pds": 1}}  # tylko struktura, bez walki
    _activate_by_p2(state, "101")
    assert note not in state.players["p2"].promissory_notes_in_play
    assert note in state.players["p1"].private.promissory_notes
    assert state.players["p2"].victory_points == 0


@ruling("C_promissory_notes/alliance/2", "C_promissory_notes/support-for-the-throne/5")
@pytest.mark.parametrize("note", ["blue_an", "blue_sftt"])
def test_diplomacy_token_does_not_return_note(
    registry: StaticDataRegistry, note: str
) -> None:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        speaker_id="p2",
        seating_order=["p1", "p2"],
        systems={
            "101": SystemState(
                position="101", system_id="26", planet_owners={"lodor": "p1"},
                planet_units={"lodor": {"p1": {"infantry": 1}}},
            ),
        },
        players={
            "p1": PlayerState(player_id="p1", color="red", strategy_cards=[2]),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
    )
    state.players["p2"].private.promissory_notes = [note]
    promissory_notes.transfer(state, "p2", "p1", note)  # p1 trzyma notkę p2 (blue)
    state.systems["101"].space_units = {"p2": {"cruiser": 1}}
    state = strategic_action.play_strategy_card(state, registry, "p1", 2)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"system": "101"})
    state = strategic_action.submit_primary_step(state, registry, "p1", {"planets": []})
    assert "p2" in state.systems["101"].command_tokens
    assert note in state.players["p1"].promissory_notes_in_play


@ruling("C_promissory_notes/support-for-the-throne/4")
def test_activating_a_system_with_only_control_tokens_keeps_the_note() -> None:
    state = pn_state()
    _received(state, "red_sftt")
    held_vp = state.players["p2"].victory_points  # the note itself gave p2 a point
    state.systems["101"].planet_owners["pl"] = "p1"  # control token only, no units
    _activate_by_p2(state, "101")
    assert "red_sftt" in state.players["p2"].promissory_notes_in_play
    assert state.players["p2"].victory_points == held_vp
    state.systems["101"].planet_units["pl"] = {"p1": {"infantry": 1}}  # a unit changes it
    _activate_by_p2(state, "101")
    assert "red_sftt" in state.players["p1"].private.promissory_notes


@ruling("C_promissory_notes/support-for-the-throne/6")
def test_note_giver_activates_the_holders_systems_without_penalty() -> None:
    state = pn_state()
    holder = _received(state, "red_sftt")
    held_vp, giver_vp = holder.victory_points, state.players["p1"].victory_points
    state.systems["101"].space_units = {"p2": {"cruiser": 1}}
    triggers.fire(
        state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
        ctx={"player": "p1", "position": "101"},
    )
    assert "red_sftt" in holder.promissory_notes_in_play  # stays with the holder
    assert (holder.victory_points, state.players["p1"].victory_points) == (held_vp, giver_vp)


@ruling("C_promissory_notes/support-for-the-throne/8")
def test_support_may_be_given_to_the_player_it_makes_win() -> None:
    state = _sftt_trade_state(Phase.ACTION)
    state.players["p2"].private.promissory_notes = []
    done = transaction.resolve_transaction(
        state, HexGrid(), "p2",
        give=TransactionSide(promissory_note="red_sftt"),
        receive=TransactionSide(),
    )
    assert done.winner_id == "p2"  # the transfer is legal even though it ends the game


@ruling("C_promissory_notes/support-for-the-throne/7")
def test_simultaneous_support_trade_active_player_scores_first() -> None:
    state = _sftt_trade_state(Phase.ACTION)
    done = transaction.resolve_transaction(
        state, HexGrid(), "p2",
        give=TransactionSide(promissory_note="red_sftt"),
        receive=TransactionSide(promissory_note="blue_sftt"),
    )
    assert done.winner_id == "p1"  # aktywny dostaje punkt pierwszy


@ruling("C_promissory_notes/support-for-the-throne/7.1")
def test_simultaneous_support_trade_in_agenda_speaker_order_first() -> None:
    state = _sftt_trade_state(Phase.AGENDA)
    done = transaction.resolve_transaction(
        state, HexGrid(), "p2",
        give=TransactionSide(promissory_note="red_sftt"),
        receive=TransactionSide(promissory_note="blue_sftt"),
        player_id="p1",
    )
    assert done.winner_id == "p2"  # p2 jest mówcą - pierwszy w kolejności od mówcy


def _sftt_trade_state(phase: Phase) -> GameState:
    from src.core.game_state import AgendaPhaseState

    p1 = PlayerState(player_id="p1", color="red", victory_points=9)
    p2 = PlayerState(player_id="p2", color="blue", victory_points=9)
    p1.private.promissory_notes = ["red_sftt"]
    p2.private.promissory_notes = ["blue_sftt"]
    state = GameState(
        phase=phase,
        active_player_id="p1",
        speaker_id="p2",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(
                position="000", system_id="18",
                space_units={"p1": {"cruiser": 1}, "p2": {"cruiser": 1}},
            )
        },
    )
    if phase is Phase.AGENDA:
        state.agenda = AgendaPhaseState(agenda_id="revolution")
    return state


# ============================================================================ Ceasefire


def _ceasefire_played(registry: StaticDataRegistry) -> GameState:
    state = pn_state()
    state.systems["101"].space_units["p2"] = {"carrier": 1}
    state.systems["101"].space_units["p1"] = {"cruiser": 1}
    _activate(state, "101")
    played, _ = promissory_play.play(state, registry, "p2", "red_cf")
    return played


@ruling("C_promissory_notes/ceasefire/1")
def test_ceasefire_does_not_stop_space_cannon_offense(registry: StaticDataRegistry) -> None:
    from tests.test_space_cannon import _grid as sc_grid
    from tests.test_space_cannon import _state as sc_state

    state = sc_state(pds={"p1": 1}, ships={"p2": {"cruiser": 1}})
    active_effects.add_effect(
        state, promissory_play.CEASEFIRE_EFFECT, Duration.TACTICAL_ACTION, owner="p1"
    )
    opened = space_cannon.open_offense(state, sc_grid(), registry)
    assert opened.pending_window is not None
    fired = space_cannon.fire_offense(opened, sc_grid(), registry, "p1", "p2")
    assert space_cannon.read_log(fired)[0]["rolls"]


@ruling("C_promissory_notes/ceasefire/2")
def test_ceasefire_keeps_units_already_in_the_system(registry: StaticDataRegistry) -> None:
    played = _ceasefire_played(registry)
    assert promissory_play.ceasefire_blocks(played, "p1")
    assert played.systems["101"].space_units["p1"] == {"cruiser": 1}


@ruling("C_promissory_notes/ceasefire/3")
def test_ceasefire_ground_forces_board_ships_already_in_the_active_system(
    registry: StaticDataRegistry,
) -> None:
    from src.core import movement

    state = pn_state()
    state.systems["101"].space_units["p1"] = {"carrier": 1}
    state.systems["101"].space_units["p2"] = {"cruiser": 1}
    state.systems["101"].planet_owners["pl"] = "p1"
    state.systems["101"].planet_units["pl"] = {"p1": {"infantry": 7}}
    _activate(state, "101")
    # Without Ceasefire nothing moves, so there is no transport either.
    pickup = [movement.CargoPickup("infantry", 2, from_zone="pl")]
    with pytest.raises(ValueError, match="transporting ship"):
        movement.move_fleet(state, HexGrid(), registry, "101", {}, pickup, "p1")
    played, _ = promissory_play.play(state, registry, "p2", "red_cf")
    assert promissory_play.ceasefire_blocks(played, "p1")
    done = movement.move_fleet(played, HexGrid(), registry, "101", {}, pickup, "p1")
    assert done.systems["101"].space_units["p1"] == {"carrier": 1, "infantry": 2}
    assert done.systems["101"].planet_units["pl"]["p1"] == {"infantry": 5}
    # The carrier's capacity (6 for Sol) is the limit.
    with pytest.raises(ValueError, match="Capacity exceeded"):
        movement.move_fleet(
            played, HexGrid(), registry, "101", {},
            [movement.CargoPickup("infantry", 7, from_zone="pl")], "p1",
        )
    # Moving ships stays blocked.
    with pytest.raises(ValueError, match="Ceasefire"):
        movement.move_fleet(played, HexGrid(), registry, "102", {"cruiser": 1}, [], "p1")


@ruling("C_promissory_notes/ceasefire/4")
def test_ceasefire_playable_with_only_ground_forces_or_structures(
    registry: StaticDataRegistry,
) -> None:
    state = pn_state()
    state.systems["101"].planet_units["pl"] = {"p2": {"pds": 1}}
    _activate(state, "101")
    assert _rows(state, registry, "p2")["red_cf"]["playable"] is True


@ruling("C_promissory_notes/ceasefire/5")
def test_ceasefire_does_not_stop_production(registry: StaticDataRegistry) -> None:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="101",
        players={
            "p1": PlayerState(player_id="p1", color="red", trade_goods=5),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems={
            "101": SystemState(
                position="101", system_id="20", planet_owners={"pl": "p1"},
                planet_units={"pl": {"p1": {"spacedock": 1}}},
            )
        },
    )
    active_effects.add_effect(
        state, promissory_play.CEASEFIRE_EFFECT, Duration.TACTICAL_ACTION, owner="p1"
    )
    done = production.produce(
        state, HexGrid(), registry, "p1", [production.ProductionOrder("infantry", 1, "pl")]
    )
    assert done.systems["101"].planet_units["pl"]["p1"]["infantry"] == 1


# ============================================================================ Political Secret


def _silence(state: GameState) -> None:
    active_effects.add_effect(
        state, promissory_play.POLITICAL_SECRET_EFFECT, Duration.AGENDA, owner="p1"
    )


@ruling("C_promissory_notes/political-secret/2")
def test_political_secret_leaves_leaders_and_technology(registry: StaticDataRegistry) -> None:
    state = pn_state()
    _silence(state)
    for kind, component in (
        (faction_components.LEADER, "solagent"),
        (faction_components.TECHNOLOGY, "dt2"),
    ):
        reason = faction_components.block_reason(state, registry, "p1", kind, component)
        assert reason is None or "Political Secret" not in reason


@ruling("C_promissory_notes/political-secret/2.1")
def test_political_secret_other_notes_of_that_player_still_playable(
    registry: StaticDataRegistry,
) -> None:
    state = pn_state()
    _silence(state)
    economy.replenish_commodities(state, "p1")
    assert _rows(state, registry, "p2")["red_ta"]["playable"] is True


@ruling("C_promissory_notes/political-secret/3")
def test_political_secret_ends_when_the_agenda_is_discarded(registry: StaticDataRegistry) -> None:
    from tests.test_agenda_phase import DIRECTIVE, LAW
    from tests.test_agenda_phase import _state as agenda_state

    state = agenda_phase.reveal_agenda(agenda_state(registry, [LAW, DIRECTIVE]), registry, "p2")
    state.players["p1"].color = "red"
    promissory_generic.political_secret(state, registry, "p3", {"__owner": "p1"})
    assert promissory_play.silenced(state, "p1")
    assert state.agenda is not None and "p1" in state.agenda.blocked
    vetoed = agenda_phase.veto_agenda(state.clone(), registry)
    assert not promissory_play.silenced(vetoed, "p1")
    assert vetoed.agenda is not None and "p1" not in vetoed.agenda.blocked


@ruling("C_promissory_notes/political-secret/1")
def test_political_secret_keeps_passive_faction_abilities() -> None:
    state = pn_state()  # p1 = Sol (Versatile: +1 żeton w fazie statusu)
    _silence(state)
    point = rules_hooks.POINT_STATUS_COMMAND_TOKENS
    assert rules_hooks.modify(point, state, "p1", 2) == 3


# ============================================================================ Trade Agreement


@ruling("C_promissory_notes/trade-agreement/2")
def test_trade_agreement_playable_when_replenishing_at_maximum(
    registry: StaticDataRegistry,
) -> None:
    state = pn_state()
    state.players["p1"].commodities = 4  # już maksimum
    economy.replenish_commodities(state, "p1")
    assert state.players["p1"].commodities == 4
    assert _rows(state, registry, "p2")["red_ta"]["playable"] is True


@ruling("C_promissory_notes/trade-agreement/1")
def test_trade_agreement_not_playable_on_gaining_commodities(
    registry: StaticDataRegistry,
) -> None:
    state = pn_state()
    economy.gain_commodities(state, "p1", 2)
    assert state.players["p1"].commodities == 2
    assert _rows(state, registry, "p2")["red_ta"]["playable"] is False
