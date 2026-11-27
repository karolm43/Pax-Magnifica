"""Abilities / coexistence — rulings ``R_abilities.md`` and ``R_coexistence.md`` point by point.

Timing rules live in ``src/core/triggers.py`` (``fire``, offers, ``resolution_order``; RULES.md
54) and ``src/core/timing.py``; coexistence is derived from the board in
``src/core/coexistence.py`` (RULES.md 40.1 I7b). Statuses without a test:
``tests/rulings_status.json``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    action_cards,
    active_effects,
    battle,
    board_graph,
    coexistence,
    component_action,
    control,
    exploration,
    invasion,
    invasion_common,
    objective_progress,
    objectives,
    production,
    promissory_notes,
    rules_hooks,
    timing,
    triggers,
    turn_flow,
    unit_ops,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    GameState,
    PendingOffer,
    Phase,
    PlayerState,
    SystemState,
    WindowType,
)
from src.core.hooks.factions import titans
from src.core.models import UnitDef
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import HookKind, HookSource
from src.core.strategy_cards.common import structure_problem
from src.core.unit_ops import UnitCause
from tests.factions.flow_harness import Flow
from tests.rulings import ruling
from tests.test_battle import _grid as battle_grid
from tests.test_battle import _state as battle_state
from tests.test_exploration import _CULT, _with_card
from tests.test_exploration import _grid as explore_grid
from tests.test_exploration import _state as explore_state
from tests.test_invasion import _PL1
from tests.test_invasion import _grid as inv_grid
from tests.test_invasion import _state as inv_state
from tests.test_promissory_play import _state as note_state
from tests.test_triggers import LAW, _log_all, _spy
from tests.test_triggers import _state as trig_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    yield


@pytest.fixture
def demo_grid(registry: StaticDataRegistry) -> Iterator[None]:
    grid = build_demo_grid(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield
    board_graph.bind_grid_provider(previous)


# ============================================================================ R_abilities


@ruling("R_abilities/rules-reference/2")
def test_card_overrides_the_rules_reference() -> None:
    """Homeland Defense Act ("any number of PDS") beats the 2-PDS structure limit."""
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={"p1": PlayerState(player_id="p1", color="red", controlled_planets=["jord"])},
        systems={
            "101": SystemState(
                position="101", system_id="01", planet_owners={"jord": "p1"},
                planet_units={"jord": {"p1": {"pds": 2}}},
            )
        },
    )
    assert "maximum number of pds" in str(structure_problem(state, "p1", "jord", "pds"))
    state.decks.agenda_laws["defense_act"] = "for"
    assert structure_problem(state, "p1", "jord", "pds") is None


@ruling("R_abilities/rules-reference/3.1")
def test_effect_with_a_duration_outlives_its_component() -> None:
    """An effect played from a card stays for its duration after the card is discarded."""
    state = trig_state()
    seen: list[str] = []
    source = HookSource(rules_hooks.SOURCE_EFFECT, "played_card")
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.COMBAT_ROUND, Moment.START, source)(
            lambda _s, pid, _c: seen.append(pid)
        )
        active_effects.add_effect(state, "played_card", Duration.COMBAT, owner="p1")
        state.players["p1"].private.action_cards = []  # the card itself is gone
        triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START)
        triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START)
        assert seen == ["p1", "p1"]  # through the whole combat
        triggers.fire(state, GameEvent.COMBAT, Moment.END)
        triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START)
    assert seen == ["p1", "p1"]  # the duration is over


@ruling("R_abilities/rules-reference/5")
def test_action_ability_needs_a_component_action_in_the_action_phase() -> None:
    state = trig_state(phase=Phase.ACTION, active_player_id="p1")
    done = component_action.play_component_action(state, "p1", None)
    assert done.players["p1"].took_action_this_turn  # it is the turn's action
    with pytest.raises(ValueError, match="already"):
        component_action.play_component_action(done, "p1", None)
    status = trig_state(phase=Phase.STATUS, active_player_id="p1")
    with pytest.raises(ValueError, match="only be performed during the action phase"):
        component_action.play_component_action(status, "p1", None)


@ruling("R_abilities/rules-reference/7", "R_abilities/rules-reference/8")
def test_may_creates_an_offer_and_mandatory_abilities_resolve_by_themselves() -> None:
    state = trig_state()
    ran: list[str] = []
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW)(
            lambda _s, pid, _c: ran.append(pid) if pid == "p1" else None
        )
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW, optional=True)(
            lambda _s, pid, _c: ran.append(f"may-{pid}")
        )
        triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1")
        assert ran == ["p1"]  # the mandatory one ran without asking anybody
        offers = triggers.offers_for(state, "p1")
        assert len(offers) == 1 and not offers[0].mandatory
        declined = triggers.decline_offer(state, "p1", offers[0].id)  # "may": optional part
        assert ran == ["p1"] and not triggers.offers_for(declined, "p1")
    # A mandatory decision cannot be skipped.
    forced = trig_state()
    forced.pending_offers = [
        PendingOffer(id="of1", player_id="p1", event="turn", moment="start", hook_seq=0,
                     label="x", ctx={}, mandatory=True)
    ]
    with pytest.raises(ValueError, match="mandatory"):
        triggers.decline_offer(forced, "p1", "of1")


@ruling("R_abilities/rules-reference/10", "R_abilities/rules-reference/11")
def test_cost_must_be_paid_to_resolve_the_effect(registry: StaticDataRegistry) -> None:
    """Volatile Fuel Source: "remove 1 infantry ... to gain 1 command token" - no infantry and
    no mech (cost) = no command token; spending command tokens from reinforcements is the gain."""
    state = _with_card(explore_state(planets={_CULT: {"pds": 1}}), registry, "Volatile Fuel Source")
    state.players["p1"].cc_reinf = 2
    options = {o.id: o for o in exploration.options_for(state, registry)}
    assert not options["infantry"].enabled and not options["mech"].enabled
    with pytest.raises(ValueError):
        exploration.resolve(state, registry, "infantry", "fleet")
    paid = _with_card(explore_state(planets={_CULT: {"infantry": 1}}), registry,
                      "Volatile Fuel Source")
    paid.players["p1"].cc_reinf = 2
    done = exploration.resolve(paid, registry, "infantry", "fleet")
    assert done.systems["000"].planet_units.get(_CULT, {}).get("p1", {}) == {}
    assert done.players["p1"].cc_reinf == 1


@ruling("R_abilities/rules-reference/12", "R_abilities/rules-reference/12.1")
def test_after_a_ship_is_destroyed_resolves_at_once() -> None:
    state = trig_state()
    state.systems["000"] = SystemState(
        position="000", system_id="18", space_units={"p2": {"cruiser": 2}}
    )
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _spy(log, GameEvent.UNIT_DESTROYED, Moment.AFTER)
        unit_ops.remove_units(
            state, state.systems["000"], "space", "p2", "cruiser", 1, UnitCause.DESTROYED
        )
        assert log == [("unit.destroyed", "after", "p2")]  # inside the destruction itself
        unit_ops.remove_units(
            state, state.systems["000"], "space", "p2", "cruiser", 1, UnitCause.DESTROYED
        )
    assert len(log) == 2


@ruling(
    "R_abilities/rules-reference/13", "R_abilities/rules-reference/13.1",
    "R_abilities/rules-reference/14", "R_abilities/notes/2",
)
def test_when_replaces_the_event_and_comes_before_after() -> None:
    state = trig_state()
    state.systems["000"] = SystemState(position="000", system_id="18", planet_owners={"jord": "p2"})
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _log_all(
            log,
            (GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER),
            (GameEvent.PLANET_CONTROL_GAINED, Moment.WHEN),
        )
        control.set_planet_control(state, "000", "jord", "p1")
    assert [m for _e, m, _s in log] == ["when", "after"]  # every "when" before any "after"
    # "When" modifies / replaces the event: a REPLACE hook cancels it, the "after" never comes.
    replaced = trig_state()
    after: list[str] = []
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW, kind=HookKind.REPLACE)(
            lambda *_a: True
        )
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW)(
            lambda _s, pid, _c: after.append(pid)
        )
        result = triggers.fire(replaced, GameEvent.TURN, Moment.START, subject="p1")
    assert result.replaced and after == []


@ruling("R_abilities/notes/3")
def test_after_abilities_of_an_event_come_before_the_next_event() -> None:
    state = trig_state(phase=Phase.ACTION, active_player_id="p3")
    for pid, card in (("p1", 1), ("p2", 2), ("p3", 3)):
        state.players[pid].strategy_cards = [card]
        state.players[pid].exhausted_strategy_cards = [card]
        state.players[pid].passed = pid != "p3"
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _log_all(
            log,
            (GameEvent.PLAYER_PASSED, Moment.WHEN),
            (GameEvent.PLAYER_PASSED, Moment.AFTER),
            (GameEvent.LAST_PLAYER_PASSED, Moment.AFTER),
        )
        turn_flow.pass_turn(state, "p3")
    assert [e[:2] for e in log] == [
        ("player.passed", "when"), ("player.passed", "after"), ("player.last_passed", "after"),
    ]


@ruling("R_abilities/rules-reference/16")
def test_ability_resolves_once_per_occurrence_of_its_timing_event() -> None:
    state = trig_state()
    seen: list[str] = []
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.COMBAT, Moment.START, LAW)(
            lambda _s, pid, _c: seen.append(pid) if pid == "p1" else None
        )
        for _ in range(3):  # three combats - "at the start of combat" every time
            triggers.fire(state, GameEvent.COMBAT, Moment.START)
    assert seen == ["p1", "p1", "p1"]


def _initiative(state: GameState, cards: Mapping[str, int]) -> None:
    for pid, card in cards.items():
        state.players[pid].strategy_cards = [card]


@ruling("R_abilities/rules-reference/17", "R_abilities/notes/8")
def test_action_phase_order_is_initiative_from_the_active_player() -> None:
    state = trig_state(phase=Phase.ACTION, active_player_id="p2")
    _initiative(state, {"p1": 7, "p2": 5, "p3": 6})  # Trade (5), Warfare (6), Technology (7)
    assert triggers.resolution_order(state) == ["p2", "p3", "p1"]
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW, optional=True)(lambda *_a: None)
        triggers.fire(state, GameEvent.TURN, Moment.START, subject="p2")
    window = state.pending_window
    assert window is not None and window.window_type is WindowType.REACTION
    assert window.queue == ["p2", "p3", "p1"]


@ruling("R_abilities/rules-reference/18")
def test_strategy_and_agenda_phase_order_is_clockwise_from_the_speaker() -> None:
    for phase in (Phase.STRATEGY, Phase.AGENDA):
        state = trig_state(phase=phase, speaker_id="p2")
        _initiative(state, {"p1": 1, "p2": 8, "p3": 2})  # initiative does not matter here
        assert triggers.resolution_order(state) == ["p2", "p3", "p1"]


@ruling("R_abilities/notes/9")
def test_status_phase_order_is_initiative_order() -> None:
    state = trig_state(phase=Phase.STATUS, speaker_id="p1")
    _initiative(state, {"p1": 8, "p2": 3, "p3": 1})
    assert triggers.resolution_order(state) == ["p3", "p2", "p1"]


@ruling("R_abilities/notes/8.3")
def test_window_closes_when_every_player_declined() -> None:
    state = trig_state(phase=Phase.ACTION, active_player_id="p1")
    _initiative(state, {"p1": 1, "p2": 2, "p3": 3})
    with rules_hooks.temporary_hooks():
        rules_hooks.on_event(GameEvent.TURN, Moment.START, LAW, optional=True)(lambda *_a: None)
        triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1")
        for pid in ("p1", "p2", "p3"):
            assert state.pending_window is not None
            assert state.pending_window.current_responder == pid
            offer = triggers.offers_for(state, pid)[0]
            state = triggers.decline_offer(state, pid, offer.id)
    assert state.pending_window is None and state.pending_offers == []


@ruling("R_abilities/notes/10")
def test_secondary_abilities_go_clockwise_after_the_primary() -> None:
    state = trig_state(phase=Phase.ACTION, active_player_id="p2")
    assert timing.build_response_queue(state, "p2") == ["p3", "p1"]


@ruling("R_abilities/notes/11")
def test_end_of_turn_abilities_resolve_on_the_turn_a_player_passes() -> None:
    state = trig_state(phase=Phase.ACTION, active_player_id="p1")
    for pid, card in (("p1", 1), ("p2", 2), ("p3", 3)):
        state.players[pid].strategy_cards = [card]
        state.players[pid].exhausted_strategy_cards = [card]
    log: list[tuple[str, str, str | None]] = []
    with rules_hooks.temporary_hooks():
        _log_all(log, (GameEvent.TURN, Moment.END))
        passed = turn_flow.pass_turn(state, "p1")
        assert passed.active_player_id == "p1"  # passing does not end the turn by itself
        turn_flow.end_turn(passed, "p1")
    assert log == [("turn", "end", "p1")]


@ruling("R_abilities/notes/1", "R_abilities/rules-reference/20")
def test_ability_usable_in_the_window_it_was_gained(registry: StaticDataRegistry) -> None:
    """Creuss IFF ("At the start of your turn") received before the start of the rival's turn
    is played at that start - not during another player's turn."""
    flow = Flow(registry, "ghost")
    note = flow.give_note("iff", flow.other)
    assert not flow.notes_playable(flow.other)[note]["playable"]  # Creuss's turn
    flow.other_turn()
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]


@ruling("R_abilities/notes/1.1", "R_abilities/notes/1.1.1")
def test_awaken_checks_its_condition_when_it_triggers(registry: StaticDataRegistry) -> None:
    from tests.factions.test_titans import ARENA, WELLON, _activate, _offers, _own, _sleeper
    from tests.factions.test_titans import _state as titans_state

    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(None)
    try:
        state = titans_state()
        _own(state, ARENA, WELLON, units={"infantry": 1})
        after = _activate(state, registry, ARENA)
        assert not _offers(after, "p1", "Awaken")
        _sleeper(after, ARENA, WELLON)  # added during the activation step: too late
        assert titans.awaken_sleepers(after, "p1", ARENA) == []
    finally:
        board_graph.bind_grid_provider(previous)


@ruling("R_abilities/notes/1.1", "R_abilities/notes/1.1.2")
def test_assault_cannon_checks_its_condition_when_it_resolves(
    registry: StaticDataRegistry,
) -> None:
    def start(ships: dict[str, int]) -> GameState:
        state = battle_state({"p1": ships, "p2": {"cruiser": 2, "fighter": 1}})
        state.players["p1"].technologies = ["asc"]
        return battle.start_combat(state, battle_grid(), registry)

    # Three non-fighter ships at the start of combat: the opponent loses one.
    assert start({"cruiser": 3}).systems["000"].space_units["p2"] == {"cruiser": 1, "fighter": 1}
    # Two non-fighter ships (plus fighters) at that moment: nothing happens.
    two = start({"cruiser": 2, "fighter": 3})
    assert two.systems["000"].space_units["p2"] == {"cruiser": 2, "fighter": 1}


@ruling("R_abilities/notes/6.1")
def test_each_unit_is_its_own_physical_object(
    registry: StaticDataRegistry, demo_grid: None
) -> None:
    """Two Exotrireme II in one system: each one may destroy itself (one offer per unit)."""
    from tests.factions.test_sardakk import _accept, _round_end_ctx
    from tests.factions.test_sardakk import _state as sardakk_state

    state = sardakk_state()
    state.players["p1"].technologies = ["exo2"]
    state.systems["102"].space_units["p1"] = {"dreadnought": 2}
    state.systems["102"].space_units["p2"] = {"cruiser": 4}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=_round_end_ctx())
    first = _accept(state, "p1", {"ships": ["cruiser#1", "cruiser#2"]})
    assert [o.label for o in first.pending_offers] == ["Exotrireme II"]  # the second unit
    second = _accept(first, "p1", {"ships": ["cruiser#1", "cruiser#2"]})
    assert second.systems["102"].space_units.get("p1", {}) == {}


@ruling("R_abilities/rules-reference/19")
def test_action_card_opening_paragraph_is_its_window(registry: StaticDataRegistry) -> None:
    from tests.test_action_cards import _rich_state

    state = _rich_state(registry)
    state.players["p1"].private.action_cards = ["messiah", "disgrace"]
    rows = {str(r["card_id"]): r for r in action_cards.playability(state, registry, "p1")}
    assert rows["messiah"]["playable"]  # "ACTION:" - now, as the turn's action
    assert not rows["disgrace"]["playable"]  # "When another player chooses a strategy card"
    assert "no open window" in str(rows["disgrace"]["reason"])


@ruling("R_abilities/rules-reference/20.1")
def test_promissory_note_that_triggers_on_receipt() -> None:
    """Support for the Throne: the receiver gains 1 victory point as soon as they get it."""
    state = note_state()
    state.players["p1"].private.promissory_notes.append("red_sftt")
    promissory_notes.transfer(state, "p1", "p2", "red_sftt")
    assert state.players["p2"].victory_points == 1
    assert "red_sftt" in state.players["p2"].promissory_notes_in_play


_UNIT_ABILITIES: dict[str, Callable[[UnitDef], bool]] = {
    "R_abilities/rules-reference/23.1": lambda u: (u.afb_die_count or 0) > 0,
    "R_abilities/rules-reference/23.2": lambda u: (u.bombard_die_count or 0) > 0,
    "R_abilities/rules-reference/23.3": lambda u: "DEPLOY" in (u.ability or "").upper(),
    "R_abilities/rules-reference/23.4": lambda u: bool(u.planetary_shield),
    "R_abilities/rules-reference/23.5": lambda u: bool(u.production_value),
    "R_abilities/rules-reference/23.6": lambda u: (u.space_cannon_die_count or 0) > 0,
    "R_abilities/rules-reference/23.7": lambda u: bool(u.sustain_damage),
}


@ruling("R_abilities/rules-reference/23", *_UNIT_ABILITIES)
def test_unit_abilities_are_named_unit_attributes(registry: StaticDataRegistry) -> None:
    for ruling_id, has in _UNIT_ABILITIES.items():
        assert any(has(unit) for unit in registry.units.values()), ruling_id
    pds = registry.units["pds"]
    assert pds.planetary_shield and (pds.space_cannon_die_count or 0) > 0


@ruling("R_abilities/rules-reference/24")
def test_this_planet_means_the_planet_with_the_unit(registry: StaticDataRegistry) -> None:
    """Planetary Shield of a PDS protects only the planet the PDS is on."""
    from tests.test_invasion import _PL2

    state = inv_state({"p1": {"dreadnought": 1}}, {_PL1: {"p2": {"pds": 1, "infantry": 1}},
                                                   _PL2: {"p2": {"infantry": 1}}},
                      {_PL1: "p2", _PL2: "p2"})
    assert invasion_common.planet_shield(state, registry, "000", _PL1) == (True, True)
    assert invasion_common.planet_shield(state, registry, "000", _PL2) == (False, False)


# ========================================================================== R_coexistence


def _coexisting(*, p3_units: dict[str, int] | None = None) -> GameState:
    """p1 invades system 000; p2 controls ``_PL1``; p3 coexists on it by choice."""
    state = inv_state(
        {"p1": {"carrier": 1, "infantry": 2}},
        {_PL1: {"p2": {"infantry": 1}, "p3": dict(p3_units or {"infantry": 1, "pds": 1})}},
        {_PL1: "p2"},
    )
    state.players["p3"] = PlayerState(player_id="p3", color="p3")
    state.seating_order = ["p1", "p2", "p3"]
    coexistence.choose(state, "000", _PL1, "p3")
    return state


@ruling("R_coexistence/notes/4")
def test_added_units_coexist_immediately() -> None:
    state = _coexisting()
    system = state.systems["000"]
    unit_ops.place_units(state, system, _PL1, "p3", "infantry", 2, UnitCause.PLACED)
    control.recompute_from_units(state, "000", _PL1)
    assert system.planet_owners[_PL1] == "p2"
    assert system.planet_units[_PL1]["p3"]["infantry"] == 3
    assert coexistence.peaceful(state, "000", _PL1) == {"p3"}


@ruling("R_coexistence/notes/5")
def test_structures_alone_coexist_and_keep_control() -> None:
    # The controller holds the planet with a PDS only, another player's infantry coexists.
    state = _coexisting(p3_units={"infantry": 2})
    system = state.systems["000"]
    system.planet_units[_PL1]["p2"] = {"pds": 1}
    control.recompute_from_units(state, "000", _PL1)
    assert system.planet_owners[_PL1] == "p2"
    assert coexistence.coexisting_players(state, "000", _PL1) == ["p3"]
    # A structure without ground forces coexists by itself.
    lone = _coexisting(p3_units={"pds": 1})
    assert coexistence.coexisting_players(lone, "000", _PL1) == ["p3"]


@ruling("R_coexistence/notes/6")
def test_structure_limits_apply_to_each_player_separately() -> None:
    state = _coexisting(p3_units={"pds": 2})
    state.players["p2"].controlled_planets = [_PL1]
    assert structure_problem(state, "p2", _PL1, "pds") is None  # p3's PDS do not count
    state.systems["000"].planet_units[_PL1]["p2"]["pds"] = 2
    assert "maximum" in str(structure_problem(state, "p2", _PL1, "pds"))


@ruling("R_coexistence/notes/7.2")
def test_control_stays_until_establish_control_during_an_invasion(
    registry: StaticDataRegistry,
) -> None:
    grid = inv_grid()
    state = invasion.begin_invasion(_coexisting(), grid, registry)
    system = state.systems["000"]
    # The controller's last unit is destroyed (e.g. Bombardment): no change of control yet.
    unit_ops.remove_units(state, system, _PL1, "p2", "infantry", 1, UnitCause.DESTROYED)
    assert system.planet_owners[_PL1] == "p2"
    state = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 2}})
    assert state.systems["000"].planet_owners[_PL1] == "p2"
    assert state.invasion is not None
    invasion._establish_control(state, registry)
    assert state.systems["000"].planet_owners[_PL1] == "p1"  # the invader gains it
    assert coexistence.peaceful(state, "000", _PL1) == {"p3"}  # p3 still coexists


@ruling("R_coexistence/notes/8", "R_coexistence/notes/9")
def test_coexisting_units_are_blockaded_and_produce_only_ground_forces(
    registry: StaticDataRegistry,
) -> None:
    state = _coexisting(p3_units={"spacedock": 1, "infantry": 1})
    producers = production.producers(state, registry, "p3", "000")
    dock = next(p for p in producers if p.base_type == "spacedock")
    assert set(production.SHIP_TYPES) <= set(dock.forbids)  # no ships, no enemy ships needed
    assert "infantry" not in dock.forbids and "mech" not in dock.forbids
    assert not production.fits_producers(producers, {"cruiser": 1})
    assert production.fits_producers(producers, {"infantry": 2})
    # The controller's own dock on the same planet is not blockaded by coexistence.
    state.systems["000"].planet_units[_PL1]["p2"] = {"spacedock": 1}
    own = production.producers(state, registry, "p2", "000")
    assert production.fits_producers(own, {"cruiser": 1})


@ruling("R_coexistence/notes/10")
def test_shield_and_space_cannon_defense_include_coexisting_pds(
    registry: StaticDataRegistry,
) -> None:
    state = _coexisting()  # only p3 (coexisting) has a PDS on the planet
    assert invasion_common.planet_shield(state, registry, "000", _PL1, exclude="p1") == (
        True, True,
    )
    state = invasion.begin_invasion(state, inv_grid(), registry)
    shooters = invasion.defense_shooters(state, registry, _PL1)
    assert {s.player_id for s in shooters} == {"p3"}


@ruling("R_coexistence/notes/16")
def test_starting_a_ground_combat_ends_coexistence_even_when_losing(
    registry: StaticDataRegistry,
) -> None:
    # p1 (active) coexists by choice on p2's planet with infantry and a PDS, then commits.
    state = inv_state(
        {"p1": {"carrier": 1, "infantry": 1}},
        {_PL1: {"p1": {"infantry": 1, "pds": 1}, "p2": {"infantry": 2}}},
        {_PL1: "p2"},
    )
    coexistence.choose(state, "000", _PL1, "p1")
    state = invasion.begin_invasion(state, inv_grid(), registry)
    state = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 1}})
    assert invasion.combat_planets(state, registry) == [_PL1]
    # p2 wins; p1's PDS stays on the planet but no longer coexists by choice.
    system = state.systems["000"]
    system.planet_units[_PL1]["p1"] = {"pds": 1}
    assert state.invasion is not None
    state.invasion.combat_results = {_PL1: {"attacker": "p1", "defender": "p2", "winner": "p2"}}
    invasion._establish_control(state, registry)
    assert system.planet_owners[_PL1] == "p2"
    assert coexistence.peaceful(state, "000", _PL1) == set()


def _scoring_state(registry: StaticDataRegistry) -> GameState:
    """p3 coexists on p2's Jord; p2 also controls Moll Primus."""
    state = _coexisting()
    state.systems["101"] = SystemState(
        position="101", system_id="01", planet_owners={"jord": "p2"},
        planet_units={"jord": {"p2": {"infantry": 1}, "p3": {"infantry": 1}}},
    )
    state.players["p2"].controlled_planets = [_PL1, "jord"]
    return state


@ruling("R_coexistence/notes/17")
def test_coexisting_player_counts_the_planet_when_scoring(registry: StaticDataRegistry) -> None:
    state = _scoring_state(registry)
    grid = inv_grid()
    p3 = objective_progress.View(state, registry, grid, "p3")
    assert set(p3.owned) == {_PL1, "jord"}  # both planets count for the coexisting player
    assert p3.controlled == [] and p3.ready_planets() == []  # but it cannot spend them
    p2 = objective_progress.View(state, registry, grid, "p2")
    assert set(p2.owned) == {_PL1, "jord"}  # the controller's own count is unchanged
    # Push Boundaries: p3's coexistence does not count as p3 controlling p2's planets.
    others = objective_progress.View(state, registry, grid, "p1")
    assert others.owned == []


@ruling("R_coexistence/notes/17.1")
def test_public_objectives_with_coexistence_in_the_home_system(
    registry: StaticDataRegistry,
) -> None:
    state = _scoring_state(registry)
    state.players["p3"].faction = "sol"
    home = registry.factions["sol"]
    assert home.home_system is not None
    state.systems["101"] = SystemState(
        position="101", system_id=home.home_system,
        planet_owners=dict.fromkeys(home.home_planets, "p2"),
        planet_units={p: {"p2": {"infantry": 1}} for p in home.home_planets},
    )
    assert not objectives.controls_home_planets(state, registry, "p3")
    for planet in home.home_planets:
        state.systems["101"].planet_units[planet]["p3"] = {"infantry": 1}
    assert objectives.controls_home_planets(state, registry, "p3")


@ruling("R_coexistence/notes/18")
def test_only_the_controller_explores(registry: StaticDataRegistry) -> None:
    """Gaining control explores; coexisting instead (Slumberstate) does not."""
    from tests.factions.test_rulings_titans_coexistence import _awaken_on_rival
    from tests.factions.test_titans import ALBION, EAST

    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(None)
    try:
        coexist, _ = _awaken_on_rival(
            registry, {f"sleeper:{ALBION}": "pds", f"coexist:{ALBION}": "coexist"}
        )
    finally:
        board_graph.bind_grid_provider(previous)
    assert coexist.systems[EAST].planet_owners[ALBION] == "p2"
    assert coexistence.peaceful(coexist, EAST, ALBION) == {"p1"}
    assert coexist.exploration is None  # coexisting on New Albion - no exploration
    # Gaining control of an uncontrolled planet with a trait: the new controller explores.
    landed = explore_state({"carrier": 1, "infantry": 1})
    landed = invasion.begin_invasion(landed, explore_grid(), registry)
    landed = invasion.commit_ground_forces(landed, registry, {_CULT: {"infantry": 1}})
    invasion._establish_control(landed, registry)
    assert landed.systems["000"].planet_owners[_CULT] == "p1"
    assert landed.exploration is not None and landed.exploration.player_id == "p1"


@ruling("R_coexistence/notes/19")
def test_another_players_coexisting_units_cannot_pay_exploration_costs(
    registry: StaticDataRegistry,
) -> None:
    state = _with_card(explore_state(planets={_CULT: {"pds": 1}}), registry,
                       "Volatile Fuel Source")
    state.systems["000"].planet_units[_CULT]["p2"] = {"infantry": 2, "mech": 1}  # p2 coexists
    state.players["p1"].cc_reinf = 2
    options = {o.id: o for o in exploration.options_for(state, registry)}
    assert not options["infantry"].enabled and not options["mech"].enabled
