"""The Nomad — every faction component (RULES.md 62.21) and the F_nomad rulings.

Scenarios through the real API (offers, window uses, ACTIONs, notes): ``test_flows_nomad.py``.
Statuses without a test: ``tests/rulings_status.json``.

Board (ring 1 + part of ring 2): 000 Mecatol Rex, 101 Arcturus (53, Nomad home), 102 empty (46),
103 empty (47), 104 Jord (Sol home), 105 Lodor (26), 106 Tarmann (22), 201 empty (48).
Edges: 101-102-103-104-105-106 ring around 000; 201 touches 101 and 102.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from src.core import (
    battle,
    battle_units,
    board_graph,
    economy,
    exhaust,
    leaders,
    movement,
    offers,
    production,
    rules_hooks,
    transaction,
    triggers,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    AgendaPhaseState,
    AgendaStep,
    AgendaVote,
    CombatStep,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import nomad
from src.core.movement_paths import shortest_legal_path
from src.core.production import ProductionOrder
from src.core.registry import StaticDataRegistry
from src.core.retreat import retreat_destinations
from src.core.state_grid import grid_from_state
from src.core.transaction import TransactionSide
from tests import boosts
from tests.factions.completeness import missing_components
from tests.rulings import ruling

MECATOL, HOME, EMPTY, EMPTY_B, JORD, LODOR, TARMANN, FAR = (
    "000", "101", "102", "103", "104", "105", "106", "201",
)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    yield
    board_graph.bind_grid_provider(None)


def _bind(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    board_graph.bind_grid_provider(lambda: grid_from_state(state, registry))
    return grid_from_state(state, registry)


def _state(registry: StaticDataRegistry, other: str = "sol", seed: int = 1) -> GameState:
    """p1 = the Nomad (active, flagship + carrier at home), p2 = rival with Jord (104)."""
    p1 = PlayerState(player_id="p1", color="blue", faction="nomad", home_position=HOME,
                     controlled_planets=["arcturus"], technologies=["sr"])
    p2 = PlayerState(player_id="p2", color="red", faction=other, home_position=JORD,
                     controlled_planets=["jord"])
    systems = {
        MECATOL: SystemState(position=MECATOL, system_id="18"),
        HOME: SystemState(position=HOME, system_id="53", planet_owners={"arcturus": "p1"},
                          space_units={"p1": {"flagship": 1, "carrier": 1}}),
        EMPTY: SystemState(position=EMPTY, system_id="46"),
        EMPTY_B: SystemState(position=EMPTY_B, system_id="47"),
        JORD: SystemState(position=JORD, system_id="01", planet_owners={"jord": "p2"}),
        LODOR: SystemState(position=LODOR, system_id="26"),
        TARMANN: SystemState(position=TARMANN, system_id="22"),
        FAR: SystemState(position=FAR, system_id="48"),
    }
    state = GameState(phase=Phase.ACTION, active_player_id="p1", seating_order=["p1", "p2"],
                      players={"p1": p1, "p2": p2}, systems=systems, rng_seed=seed)
    for player in state.players.values():
        player.cc_reinf = 8
        player.tactical_cc = 3
        player.leader_states = {}
        player.commodity_value = registry.factions[player.faction or ""].commodities
    _bind(state, registry)
    return state


def _offers(state: GameState, pid: str, label: str) -> list[Any]:
    return [o for o in triggers.offers_for(state, pid) if label in o.label]


def _inputs(state: GameState, registry: StaticDataRegistry, offer: Any) -> list[dict[str, Any]]:
    return offers.offer_view(state, registry, offer)["inputs"]  # type: ignore[no-any-return]


def _accept(state: GameState, pid: str, label: str, params: dict[str, Any] | None = None
            ) -> GameState:
    offer = _offers(state, pid, label)[0]
    return triggers.accept_offer(state, pid, offer.id, params or {})


def _space_combat(
    registry: StaticDataRegistry, state: GameState, position: str
) -> tuple[GameState, HexGrid]:
    """Space combat in ``position`` (p1 attacks) - AFB resolved with Auto hits."""
    state.active_system = position
    state.tactical_step = TacticalStep.SPACE_COMBAT
    grid = _bind(state, registry)
    started = battle.start_combat(state, grid, registry)
    if started.active_combat is not None and started.active_combat.step is CombatStep.AFB:
        started = battle.resolve_afb(started, grid, registry)
    return started, grid


def _seek(state: GameState, action: Callable[[GameState], GameState],
          ok: Callable[[GameState], bool]) -> GameState:
    for seed in range(1, 400):
        candidate = state.clone()
        candidate.rng_seed = seed
        result = action(candidate)
        if ok(result):
            return result
    raise AssertionError("no seed produced the expected outcome")


def _to_roll(registry: StaticDataRegistry, state: GameState, grid: HexGrid) -> GameState:
    """Past the start-of-combat decisions (declined) and Announce Retreats (nobody retreats)."""
    for _ in range(20):
        combat = state.active_combat
        assert combat is not None
        if combat.step is CombatStep.TRIGGERS:
            for offer in list(state.pending_offers):
                if offer.mandatory:
                    state = triggers.accept_offer(state, offer.player_id, offer.id, {})
                else:
                    state = triggers.decline_offer(state, offer.player_id, offer.id)
            state = battle.resume_after_triggers(state, grid, registry)
        elif combat.step is CombatStep.ANNOUNCE and state.pending_window is not None:
            pid = state.pending_window.current_responder
            assert pid is not None
            state = battle.announce_retreat(state, grid, pid, announce=False)
        else:
            return state
    raise AssertionError("the combat did not reach the Roll Dice step")


def _rolled(registry: StaticDataRegistry, state: GameState, grid: HexGrid) -> GameState:
    """Combat dice of round 1 on the table with hits for both sides (assignment open)."""
    state = _to_roll(registry, state, grid)
    combat = state.active_combat
    assert combat is not None and combat.step is CombatStep.ROLL
    return _seek(
        state, lambda s: battle.roll_round(s, grid, registry),
        lambda s: s.active_combat is not None and s.active_combat.step is CombatStep.ASSIGN
        and all(n > 0 for n in s.active_combat.pending_hits.values()),
    )


def test_nomad_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "nomad") == []


# ==================================================================================== The Company


@ruling("abilities:the_company#1", "abilities:the_company#2")
def test_the_company_trzech_agentow(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    found = [lid for pid, lid, st in nomad.agents(state, registry) if pid == "p1"]
    assert found == [nomad.MERCER, nomad.THUNDARIAN, nomad.ARTUNO]
    assert all(leaders.is_ready(state, registry, "p1", lid) for lid in found)


# ================================================================================== Future Sight


def _agenda(state: GameState, votes: dict[str, AgendaVote]) -> None:
    state.phase = Phase.AGENDA
    state.agenda = AgendaPhaseState(agenda_id="minister_war", outcomes=["for", "against"],
                                    step=AgendaStep.RESOLVED, votes=votes)


def _resolved(state: GameState, outcome: str) -> None:
    triggers.fire(state, GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER,
                  ctx={"agenda": "minister_war", "outcome": outcome, "kind": "law"})


@ruling("abilities:future_sight#1", "F_nomad/future-sight/1")
def test_future_sight_glos_na_wynik(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _agenda(state, {"p1": AgendaVote(outcome="for", votes=3)})
    _resolved(state, "for")
    assert state.players["p1"].trade_goods == 1
    other = _state(registry)
    _agenda(other, {"p1": AgendaVote(outcome="against", votes=3)})
    _resolved(other, "for")  # neither voted for nor predicted (no game effect predicting)
    assert other.players["p1"].trade_goods == 0


@ruling("F_nomad/future-sight/2", "F_nomad/future-sight/2.1")
def test_future_sight_przewidywanie_raz(registry: StaticDataRegistry) -> None:
    from src.core import active_effects

    state = _state(registry)
    _agenda(state, {})
    for card in ("trade_rider", "war_rider"):
        active_effects.add_effect(state, f"action_cards:{card}", Duration.AGENDA, owner="p1",
                                  data={"outcome": "for"})
    _resolved(state, "for")
    gained = state.players["p1"].trade_goods
    assert gained >= 1  # Trade Rider pays too; Future Sight adds exactly one
    # Predicted "against", voted "for" (Xxcha Alliance) - either outcome pays.
    other = _state(registry)
    _agenda(other, {"p1": AgendaVote(outcome="for", votes=1)})
    active_effects.add_effect(other, "action_cards:politic_rider", Duration.AGENDA, owner="p1",
                              data={"outcome": "against"})
    _resolved(other, "for")
    assert other.players["p1"].trade_goods == 1


# ======================================================================== Memoria / Memoria II


@ruling("units:nomad_flagship#1", "F_nomad/memoria/1", "F_nomad/memoria/5")
def test_memoria_sasiaduje_z_mechami(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[EMPTY_B].space_units = {"p1": {"mech": 1}}
    grid = _bind(state, registry)
    path = shortest_legal_path(grid, state, HOME, EMPTY_B, "p1", can_enter_asteroids=False,
                               base_type="flagship")
    assert path == [HOME, EMPTY_B]
    # Only the Memoria: the carrier keeps map adjacency.
    carrier = shortest_legal_path(grid, state, HOME, EMPTY_B, "p1", can_enter_asteroids=False,
                                  base_type="carrier")
    assert carrier is not None and len(carrier) > 2
    # Moving a flagship of move 1 straight there (validated on the pre-move state).
    state.active_system = EMPTY_B
    state.tactical_step = TacticalStep.MOVEMENT
    ok, reason = movement.can_move(state, grid, registry, HOME, "flagship", "p1")
    assert ok, reason
    ok, _ = movement.can_move(state, grid, registry, HOME, "carrier", "p1")
    assert not ok


@ruling("F_nomad/memoria/2", "F_nomad/memoria/4", "F_nomad/memoria/3")
def test_memoria_to_nie_jest_sasiedztwo_planszy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[EMPTY_B].space_units = {"p1": {"mech": 1}}
    grid = _bind(state, registry)
    assert not board_graph.are_adjacent_for_player(state, grid, "p1", HOME, EMPTY_B)
    assert EMPTY_B not in board_graph.neighbors_for_player(state, grid, "p1", HOME)
    # Retreat keeps the board: no retreat into the mech's system.
    state.systems[HOME].space_units["p2"] = {"destroyer": 1}
    assert EMPTY_B not in retreat_destinations(state, grid, HOME, "p1")


@ruling("technologies:m2#1", "technologies:m2#2", "technologies:m2#3")
def test_memoria_ii_wartosci_z_danych(registry: StaticDataRegistry) -> None:
    from src.core.combat import resolve_unit_variant

    unit = resolve_unit_variant(registry, "nomad", ["m2"], "flagship")
    assert unit is not None and unit.id == "nomad_flagship2"
    assert (unit.cost, unit.combat_hits_on, unit.combat_die_count, unit.move_value,
            unit.capacity_value) == (8, 5, 2, 2, 6)
    assert unit.sustain_damage and (unit.afb_hits_on, unit.afb_die_count) == (5, 3)
    state = _state(registry)
    state.players["p1"].technologies = ["sr", "m2"]
    state.systems[FAR].space_units = {"p1": {"mech": 1}}
    grid = _bind(state, registry)
    assert shortest_legal_path(grid, state, JORD, FAR, "p1", can_enter_asteroids=False,
                               base_type="flagship") == [JORD, FAR]


# ===================================================================== Temporal Command Suite


def _exhausted_agent(state: GameState, registry: StaticDataRegistry, pid: str, leader: str
                     ) -> None:
    from src.core import faction_components

    faction_components.pay_cost(state, registry, pid, "leader", leader)


@ruling("technologies:tcs#1", "technologies:tcs#2", "F_nomad/temporal-command-suite/1",
        "F_nomad/temporal-command-suite/2")
def test_tcs_odswieza_cudzego_agenta_i_transakcja(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies = ["sr", "tcs"]
    state.active_player_id = "p2"  # the Nomad is not the active player
    _exhausted_agent(state, registry, "p2", "solagent")
    state = _accept(state, "p1", "Temporal Command Suite")
    assert leaders.is_ready(state, registry, "p2", "solagent")
    assert "tcs" in state.players["p1"].exhausted_technologies
    grid = _bind(state, registry)
    assert "p2" not in movement_neighbors(state, grid)  # not neighbours
    assert transaction.components_allowed(state, grid, "p1", "p2")
    state.players["p1"].trade_goods = 2
    done = transaction.resolve_transaction(
        state, grid, "p2", TransactionSide(trade_goods=2), TransactionSide(), "p1"
    )
    assert done.players["p2"].trade_goods == 2
    assert not transaction.granted_pair(done, "p1", "p2")  # one transaction


def movement_neighbors(state: GameState, grid: HexGrid) -> set[str]:
    from src.core.neighbors import neighbors_of

    return neighbors_of("p1", state, grid)


@ruling("F_nomad/temporal-command-suite/2.1", "F_nomad/temporal-command-suite/3")
def test_tcs_transakcja_w_fazie_strategii_i_druga(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.phase = Phase.STRATEGY
    transaction.grant_pair(state, "p1", "p2", "technologies:tcs")
    grid = _bind(state, registry)
    state.players["p1"].trade_goods = 1
    state.players["p1"].transacted_with = ["p2"]  # already transacted this turn
    done = transaction.resolve_transaction(
        state, grid, "p2", TransactionSide(trade_goods=1), TransactionSide(), "p1"
    )
    assert done.players["p2"].trade_goods == 1
    assert done.players["p1"].transacted_with == ["p2"]  # not counted again


def test_tcs_wlasny_agent_bez_transakcji(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies = ["sr", "tcs"]
    _exhausted_agent(state, registry, "p1", nomad.MERCER)
    state = _accept(state, "p1", "Temporal Command Suite")
    assert leaders.is_ready(state, registry, "p1", nomad.MERCER)
    assert not any(e.key == transaction.GRANT_KEY for e in state.active_effects)


# ======================================================================== Field Marshal Mercer


def _end_turn(state: GameState, pid: str, position: str) -> None:
    triggers.fire(state, GameEvent.TURN, Moment.END, subject=pid,
                  ctx={"player": pid, "position": position})


@ruling("leaders:nomadagentmercer#1", "F_nomad/field-marshal-mercer/1",
        "F_nomad/field-marshal-mercer/2", "F_nomad/field-marshal-mercer/3",
        "F_nomad/field-marshal-mercer/4")
def test_mercer_przenosi_sily_naziemne(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[JORD].planet_units = {"jord": {"p2": {"infantry": 1}}}
    state.systems[LODOR].planet_owners = {"lodor": "p2"}
    state.systems[LODOR].command_tokens = ["p2"]
    state.systems[LODOR].space_units = {"p2": {"carrier": 1, "infantry": 1}}
    state.systems[TARMANN].planet_units = {"tarmann": {"p2": {"mech": 1}}}
    _end_turn(state, "p2", LODOR)
    # Cooperative (RULES.md 54.15): the player whose turn ends requests Mercer.
    state = _accept(boosts.request(state, registry, "p2", "Field Marshal Mercer"), "p1",
                    "Field Marshal Mercer")
    assert state.players["p1"].leader_states.get(nomad.MERCER) == "exhausted"
    decision = _offers(state, "p2", "Field Marshal Mercer")[0]
    inputs = _inputs(state, registry, decision)
    forces = next(i for i in inputs if i["key"] == "forces")
    values = {o["value"] for o in forces["options"]}
    space_inf = f"{LODOR}|space|infantry|0"
    mech = f"{TARMANN}|tarmann|mech|0"
    assert space_inf in values and mech in values
    state = triggers.accept_offer(state, "p2", decision.id,
                                  {"forces": [space_inf, mech], "planet_1": "lodor",
                                   "planet_2": "lodor"})
    lodor = state.systems[LODOR].planet_units["lodor"]["p2"]
    assert lodor == {"infantry": 1, "mech": 1}
    assert state.systems[TARMANN].planet_units.get("tarmann", {}).get("p2", {}).get("mech", 0) == 0


@ruling("F_nomad/field-marshal-mercer/5")
def test_mercer_uszkodzony_mech_zostaje_uszkodzony(registry: StaticDataRegistry) -> None:
    from src.core.damage import damaged_count, set_damaged

    state = _state(registry)
    state.systems[LODOR].planet_owners = {"lodor": "p2"}
    state.systems[TARMANN].planet_units = {"tarmann": {"p2": {"mech": 1}}}
    set_damaged(state.systems[TARMANN], "tarmann", "p2", "mech", 1)
    _end_turn(state, "p2", LODOR)
    # Cooperative (RULES.md 54.15): the player whose turn ends requests Mercer.
    state = _accept(boosts.request(state, registry, "p2", "Field Marshal Mercer"), "p1",
                    "Field Marshal Mercer")
    decision = _offers(state, "p2", "Field Marshal Mercer")[0]
    state = triggers.accept_offer(state, "p2", decision.id,
                                  {"forces": [f"{TARMANN}|tarmann|mech|0"], "planet_1": "lodor"})
    assert damaged_count(state.systems[LODOR], "lodor", "p2", "mech") == 1


def test_mercer_bez_aktywnego_systemu_brak_oferty(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[JORD].planet_units = {"jord": {"p2": {"infantry": 1}}}
    _end_turn(state, "p2", "")  # a strategic action: nothing activated this turn
    assert not _offers(state, "p1", "Field Marshal Mercer")


# ================================================================================ The Thundarian


def _fight(registry: StaticDataRegistry, other: str = "sol") -> tuple[GameState, HexGrid]:
    state = _state(registry, other)
    state.systems[EMPTY].space_units = {"p2": {"cruiser": 2, "dreadnought": 1}}
    state.systems[EMPTY].space_units["p1"] = {"cruiser": 2, "dreadnought": 1}
    started, grid = _space_combat(registry, state, EMPTY)
    return _rolled(registry, started, grid), grid


@ruling("leaders:nomadagentthundarian#1", "leaders:nomadagentthundarian#2",
        "leaders:nomadagentthundarian#3", "F_nomad/the-thundarian/2",
        "F_nomad/the-thundarian/4.5")
def test_thundarian_powrot_do_rzutu(registry: StaticDataRegistry) -> None:
    from src.core import active_effects, faction_components

    state, grid = _fight(registry)
    combat = state.active_combat
    assert combat is not None and battle.roll_step_open(state)
    active_effects.add_effect(state, "action_cards:mb1", Duration.COMBAT_ROUND, owner="p2")
    combat.pending_hits = {pid: n + 1 for pid, n in combat.pending_hits.items()}  # VPW extra
    rnd = combat.round
    after, _ = faction_components.play(state, registry, "p1", "leader", nomad.THUNDARIAN)
    redo = after.active_combat
    assert redo is not None and redo.step is CombatStep.ROLL and redo.round == rnd
    assert redo.pending_hits == {} and redo.rolls == {}
    assert after.pending_window is None
    assert after.players["p1"].leader_states.get(nomad.THUNDARIAN) == "exhausted"
    # Effects of that round stay; nobody lost a unit.
    assert active_effects.has_effect(after, "p2", "action_cards:mb1")
    assert after.systems[EMPTY].space_units["p2"] == {"cruiser": 2, "dreadnought": 1}
    again = battle.roll_round(after, grid, registry)
    assert again.active_combat is not None and again.active_combat.round == rnd


@ruling("F_nomad/the-thundarian/1")
def test_thundarian_w_cudzej_walce(registry: StaticDataRegistry) -> None:
    from src.core import faction_components

    state = _state(registry, "sol")
    state.players["p3"] = PlayerState(player_id="p3", color="green", faction="letnev")
    state.seating_order = ["p1", "p2", "p3"]
    state.active_player_id = "p2"
    state.systems[TARMANN].space_units = {"p2": {"cruiser": 2}, "p3": {"cruiser": 2}}
    state.systems[TARMANN].command_tokens = ["p2"]
    started, grid = _space_combat(registry, state, TARMANN)
    rolled = _rolled(registry, started, grid)
    # Cooperative (RULES.md 54.15): not prompted in others' combat - the combatants request it.
    assert not faction_components.available_now(rolled, registry, ["p1"])
    assert "The Thundarian" in boosts.names(rolled, registry, "p2")
    after, _ = faction_components.play(rolled, registry, "p1", "leader", nomad.THUNDARIAN)
    assert after.active_combat is not None and after.active_combat.step is CombatStep.ROLL


@ruling("F_nomad/the-thundarian/3", "F_nomad/the-thundarian/4")
def test_thundarian_tylko_po_kroku_rzutu(registry: StaticDataRegistry) -> None:
    from src.core import faction_components

    state = _state(registry)
    state.systems[EMPTY].space_units = {"p2": {"cruiser": 2}, "p1": {"cruiser": 2}}
    started, grid = _space_combat(registry, state, EMPTY)
    assert not battle.roll_step_open(started)  # before the roll
    rolled = _rolled(registry, started, grid)
    pid = rolled.pending_window.current_responder if rolled.pending_window else None
    assert pid is not None
    assigned = battle.sustain_one(rolled, grid, registry, pid, "cruiser") if any(
        u.sustainable for u in battle.side_units(rolled, grid, registry, pid)
    ) else battle.assign_combat_hits(
        rolled, grid, registry, pid, sustain={},
        destroy={"cruiser": battle.required_hits(rolled, grid, registry, pid)}, destroy_damaged={}
    )
    assert not battle.roll_step_open(assigned)  # a hit is assigned already
    with pytest.raises(ValueError):
        faction_components.play(assigned, registry, "p1", "leader", nomad.THUNDARIAN)
    # The rewind does not start a new round (no start-of-round window replayed).
    after, _ = faction_components.play(rolled, registry, "p1", "leader", nomad.THUNDARIAN)
    assert after.active_combat is not None
    assert after.active_combat.round == rolled.active_combat.round  # type: ignore[union-attr]


@ruling("F_nomad/the-thundarian/5")
def test_thundarian_odswiezony_znowu(registry: StaticDataRegistry) -> None:
    from src.core import faction_components

    state, grid = _fight(registry)
    state.players["p1"].technologies = ["sr", "tcs"]
    after, _ = faction_components.play(state, registry, "p1", "leader", nomad.THUNDARIAN)
    after = _accept(after, "p1", "Temporal Command Suite")
    assert leaders.is_ready(after, registry, "p1", nomad.THUNDARIAN)
    again = _rolled(registry, after, grid)
    assert battle.roll_step_open(again)
    assert faction_components.available_now(again, registry, ["p1"])


# ============================================================================ Artuno the Betrayer


@ruling("leaders:nomadagentartuno#1", "leaders:nomadagentartuno#2",
        "F_nomad/artuno-the-betrayer/3")
def test_artuno_odklada_i_oddaje(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    economy.gain_trade_goods(state, "p1", 3)
    state = _accept(state, "p1", "Artuno")
    player = state.players["p1"]
    # "an equal number" comes from the supply: the gained 3 stay in the pool.
    assert player.trade_goods == 3 and player.leader_trade_goods == {nomad.ARTUNO: 3}
    assert player.leader_states.get(nomad.ARTUNO) == "exhausted"
    exhaust.ready_all_leaders(state, "p1")
    assert state.players["p1"].trade_goods == 6
    assert state.players["p1"].leader_trade_goods == {}
    # The payout is not from the supply: no new Artuno offer.
    assert not _offers(state, "p1", "Artuno")


@ruling("F_nomad/artuno-the-betrayer/1", "F_nomad/artuno-the-betrayer/1.1")
def test_artuno_tylko_jedno_zdobycie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    economy.gain_trade_goods(state, "p1", 2)
    economy.gain_trade_goods(state, "p1", 1)
    first = _offers(state, "p1", "Artuno")[0]
    state = triggers.accept_offer(state, "p1", first.id, {})
    assert state.players["p1"].leader_trade_goods == {nomad.ARTUNO: 2}
    # The second offer is gone or unusable: Artuno is exhausted now.
    rest = _offers(state, "p1", "Artuno")
    if rest:
        with pytest.raises(ValueError):
            triggers.accept_offer(state, "p1", rest[0].id, {})


@ruling("F_nomad/artuno-the-betrayer/2", "F_nomad/artuno-the-betrayer/4")
def test_artuno_nie_z_karty_strategii_ani_zamiany(registry: StaticDataRegistry) -> None:
    from src.core import strategy_phase

    state = _state(registry)
    state.players["p1"].commodities = 2
    economy.convert_commodities_to_trade_goods(state, "p1", 2)
    assert not _offers(state, "p1", "Artuno")
    economy.give_to_player(state, "p2", "p1", commodities=0, trade_goods=0)
    pick = _state(registry)
    pick.phase = Phase.STRATEGY
    pick.speaker_id = "p1"
    pick.active_player_id = "p1"
    pick.strategy_card_tg = {1: 2}
    picked = strategy_phase.pick_strategy_card(pick, registry, "p1", 1)
    assert picked.players["p1"].trade_goods == 2
    assert not _offers(picked, "p1", "Artuno")


# ============================================================================= Navarch Feng


@ruling("leaders:nomadcommander#unlock", "F_nomad/navarch-feng/2", "F_nomad/navarch-feng/2.2")
def test_feng_odblokowanie_tajny_cel(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    assert not nomad._feng_unlocked(state, registry, "p1")
    state.players["p1"].scored_secrets = ["become_martyr"]
    assert leaders.refresh_unlocks(state, registry) == [nomad.COMMANDER]
    state.players["p1"].scored_secrets = []  # made public later: commanders never lock again
    assert leaders.is_ready(state, registry, "p1", nomad.COMMANDER)


@ruling("leaders:nomadcommander#1", "F_nomad/navarch-feng/1")
def test_feng_darmowy_flagowiec(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    orders = [ProductionOrder(base_type="flagship", count=1),
              ProductionOrder(base_type="cruiser", count=1)]
    assert production.order_cost(state, registry, "p1", orders) == 10
    state.players["p1"].leader_states = {nomad.COMMANDER: "unlocked"}
    assert production.order_cost(state, registry, "p1", orders) == 2
    assert registry.units["nomad_flagship"].cost == 8  # the cost itself stays


# ================================================================ Ahk-Syl Siven — Time Warp


def _hero_used(state: GameState, registry: StaticDataRegistry) -> GameState:
    from src.core import faction_components

    state.players["p1"].leader_states = {nomad.HERO: "unlocked"}
    after, _ = faction_components.play(state, registry, "p1", "leader", nomad.HERO)
    return after


@ruling("leaders:nomadhero#1", "leaders:nomadhero#2", "leaders:nomadhero#3",
        "F_nomad/ahksyl-siven-probability-matrix/2")
def test_time_warp_flagowiec_wychodzi_z_zetonem(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[HOME].command_tokens = ["p1"]
    state.systems[HOME].planet_units = {"arcturus": {"p1": {"infantry": 2}}}
    state.active_system = EMPTY
    state.tactical_step = TacticalStep.MOVEMENT
    grid = _bind(state, registry)
    ok, _ = movement.can_move(state, grid, registry, HOME, "flagship", "p1")
    assert not ok
    after = _hero_used(state, registry)
    assert after.players["p1"].leader_states.get(nomad.HERO) == "purged"
    effect = next(e for e in after.active_effects if e.key == nomad.TIME_WARP)
    assert effect.scope == Duration.ROUND.value and effect.data["areas"][HOME] == "time_warp"
    after.active_system = EMPTY
    after.tactical_step = TacticalStep.MOVEMENT
    assert movement.can_move(after, grid, registry, HOME, "flagship", "p1")[0]
    assert not movement.can_move(after, grid, registry, HOME, "carrier", "p1")[0]
    cargo = [movement.CargoPickup(base_type="infantry", count=2, from_zone="arcturus")]
    moved = movement.move_fleet(after, grid, registry, HOME, {"flagship": 1}, cargo, "p1")
    assert moved.systems[EMPTY].space_units["p1"] == {"flagship": 1, "infantry": 2}
    with pytest.raises(ValueError):
        movement.move_fleet(after, grid, registry, HOME, {"carrier": 1}, cargo, "p1")


@ruling("leaders:nomadhero#unlock")
def test_time_warp_odblokowanie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].scored_secrets = ["become_martyr", "fight_with_precision", "mechanize"]
    unlocked = leaders.refresh_unlocks(state, registry)
    assert nomad.HERO in unlocked


# ================================================================================= The Cavalry


def _cavalry_combat(registry: StaticDataRegistry, techs: list[str] | None = None
                    ) -> tuple[GameState, HexGrid]:
    """p2 (Sol) holds The Cavalry and attacks p3 (Letnev) in Tarmann."""
    from src.core import promissory_play

    state = _state(registry)
    state.players["p1"].technologies = ["sr", *(techs or [])]
    state.players["p3"] = PlayerState(player_id="p3", color="green", faction="letnev")
    state.seating_order = ["p1", "p2", "p3"]
    state.active_player_id = "p2"
    state.players["p2"].private.promissory_notes = ["cavalry"]
    state.systems[TARMANN].space_units = {"p2": {"cruiser": 2}, "p3": {"fighter": 3,
                                                                       "destroyer": 1}}
    state.active_system = TARMANN
    state.tactical_step = TacticalStep.SPACE_COMBAT
    grid = _bind(state, registry)
    started = battle.start_combat(state, grid, registry)
    played, _ = promissory_play.play(started, registry, "p2", "cavalry", {"ship": "cruiser"})
    return played, grid


@ruling("promissory_notes:cavalry#1", "F_nomad/the-cavalry/1")
def test_cavalry_statek_z_wartosciami_flagowca(registry: StaticDataRegistry) -> None:
    state, grid = _cavalry_combat(registry)
    cruiser = next(u for u in battle.side_units(state, grid, registry, "p2")
                   if u.base_type == "cruiser")
    assert (cruiser.champion_hits_on, cruiser.champion_dice) == (7, 2)  # Memoria I
    assert (cruiser.champion_afb_hits_on, cruiser.champion_afb_dice) == (8, 3)
    assert cruiser.total_dice == 3 and cruiser.sustainable == 1
    assert "cavalry" in state.players["p2"].promissory_notes_in_play
    # AFB step: only the champion rolls AFB (3 dice at 8).
    afb = battle.resolve_afb(state, grid, registry)
    assert afb.active_combat is not None
    rolls = afb.active_combat.afb.get("p2", [])
    assert [len(r["dice"]) for r in rolls] == [3] and rolls[0]["hitsOn"] == 8
    upgraded, grid2 = _cavalry_combat(registry, ["m2"])
    cr2 = next(u for u in battle.side_units(upgraded, grid2, registry, "p2")
               if u.base_type == "cruiser")
    assert (cr2.champion_hits_on, cr2.champion_afb_hits_on) == (5, 5)  # Memoria II


@ruling("promissory_notes:cavalry#2")
def test_cavalry_wraca_po_walce(registry: StaticDataRegistry) -> None:
    state, _grid = _cavalry_combat(registry)
    triggers.fire(state, GameEvent.COMBAT, Moment.END,
                  ctx={"kind": "space", "position": TARMANN, "winner": "p2"})
    assert "cavalry" in state.players["p1"].private.promissory_notes
    assert "cavalry" not in state.players["p2"].promissory_notes_in_play
    assert not any(e.key == nomad.CAVALRY_KEY for e in state.active_effects)


@ruling("F_nomad/the-cavalry/2", "F_nomad/the-cavalry/2.1")
def test_cavalry_uszkodzony_zostaje(registry: StaticDataRegistry) -> None:
    from src.core.damage import damaged_count, set_damaged

    state, grid = _cavalry_combat(registry)
    set_damaged(state.systems[TARMANN], "space", "p2", "cruiser", 1)
    cruiser = next(u for u in battle.side_units(state, grid, registry, "p2")
                   if u.base_type == "cruiser")
    assert cruiser.sustainable == 0  # already damaged: no second Sustain Damage
    triggers.fire(state, GameEvent.COMBAT, Moment.END,
                  ctx={"kind": "space", "position": TARMANN, "winner": "p2"})
    assert damaged_count(state.systems[TARMANN], "space", "p2", "cruiser") == 1


@ruling("F_nomad/the-cavalry/2.4")
def test_cavalry_emergency_repairs_tylko_z_sustain_damage(registry: StaticDataRegistry) -> None:
    from src.core.damage import damaged_count, set_damaged
    from src.core.hooks import reactions_combat

    state, _grid = _cavalry_combat(registry)
    state.systems[TARMANN].space_units["p2"]["dreadnought"] = 1
    set_damaged(state.systems[TARMANN], "space", "p2", "cruiser", 2)  # the champion + another
    set_damaged(state.systems[TARMANN], "space", "p2", "dreadnought", 1)
    # During the combat the champion has SUSTAIN DAMAGE: it is repaired; the other damaged cruiser
    # does not have the ability, so it stays damaged; the dreadnought has its own.
    assert reactions_combat._damaged_units(state, registry, "p2", TARMANN) == [
        ("space", "cruiser", 1), ("space", "dreadnought", 1)]
    during = state.clone()
    reactions_combat.emergency_repairs(during, registry, "p2", {})
    assert damaged_count(during.systems[TARMANN], "space", "p2", "cruiser") == 1
    assert damaged_count(during.systems[TARMANN], "space", "p2", "dreadnought") == 0
    # After the combat the cruiser lost The Cavalry's SUSTAIN DAMAGE: not repaired by the card.
    triggers.fire(state, GameEvent.COMBAT, Moment.END,
                  ctx={"kind": "space", "position": TARMANN, "winner": "p2"})
    state.active_combat = None
    assert reactions_combat._damaged_units(state, registry, "p2", TARMANN) == [
        ("space", "dreadnought", 1)]


def test_cavalry_nie_przeciw_nomadowi(registry: StaticDataRegistry) -> None:
    from src.core import promissory_play

    state = _state(registry)
    state.active_player_id = "p2"
    state.players["p2"].private.promissory_notes = ["cavalry"]
    state.systems[EMPTY].space_units = {"p2": {"cruiser": 1}, "p1": {"cruiser": 1}}
    state.active_system = EMPTY
    state.tactical_step = TacticalStep.SPACE_COMBAT
    grid = _bind(state, registry)
    started = battle.start_combat(state, grid, registry)
    with pytest.raises(ValueError):
        promissory_play.play(started, registry, "p2", "cavalry", {"ship": "cruiser"})


# ========================================================================= Quantum Manipulator


def _shielded(registry: StaticDataRegistry) -> tuple[GameState, HexGrid]:
    state = _state(registry)
    state.systems[EMPTY].space_units = {"p1": {"cruiser": 1, "carrier": 1, "mech": 1},
                                        "p2": {"cruiser": 3}}
    started, grid = _space_combat(registry, state, EMPTY)
    return _rolled(registry, started, grid), grid


@ruling("units:nomad_mech#1", "F_nomad/quantum-manipulator/2")
def test_quantum_manipulator_anuluje_trafienie(registry: StaticDataRegistry) -> None:
    state, grid = _shielded(registry)
    shields = battle_units.hit_shields(state, registry, "p1")
    assert [(u.base_type, u.shield) for u in shields] == [("mech", True)]
    assert battle.required_hits(state, grid, registry, "p1") == min(
        state.active_combat.pending_hits["p1"], 3)  # type: ignore[union-attr]
    while state.pending_window is not None and state.pending_window.current_responder != "p1":
        pid = state.pending_window.current_responder
        assert pid is not None
        need = battle.required_hits(state, grid, registry, pid)
        state = battle.assign_combat_hits(state, grid, registry, pid, sustain={},
                                          destroy={"cruiser": need}, destroy_damaged={})
    need = battle.required_hits(state, grid, registry, "p1")
    rest = {"cruiser": 1, "carrier": need - 2} if need >= 2 else {}
    after = battle.assign_combat_hits(state, grid, registry, "p1", sustain={"mech": 1},
                                      destroy=rest, destroy_damaged={})
    from src.core.damage import damaged_count

    assert damaged_count(after.systems[EMPTY], "space", "p1", "mech") == 1
    combat = after.active_combat
    assert combat is not None
    assert not any(e["base_type"] == "mech" for e in combat.sustained_ships)  # not a ship
    with pytest.raises(ValueError):
        battle.assign_combat_hits(state, grid, registry, "p1", sustain={},
                                  destroy={"mech": 1, **({"cruiser": need - 1} if need > 1
                                                          else {})}, destroy_damaged={})


@ruling("F_nomad/quantum-manipulator/1", "F_nomad/quantum-manipulator/1.2")
def test_quantum_manipulator_afb_tak_poza_walka_nie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    assert battle_units.hit_shields(state, registry, "p1") == []  # no combat (Space Cannon)
    state.systems[EMPTY].space_units = {"p1": {"fighter": 2, "carrier": 1, "mech": 1},
                                        "p2": {"destroyer": 2}}
    started, grid = _space_combat(registry, state, EMPTY)
    combat = started.active_combat
    if combat is None or not combat.afb_assign or not combat.pending_hits.get("p1"):
        pytest.skip("seed without AFB hits")
    after = battle.assign_combat_hits(started, grid, registry, "p1", sustain={"mech": 1},
                                      destroy={"fighter": combat.pending_hits["p1"] - 1},
                                      destroy_damaged={})
    assert after.systems[EMPTY].space_units["p1"]["mech"] == 1


@ruling("F_nomad/quantum-manipulator/2.1")
def test_quantum_manipulator_mimo_fourth_moon(registry: StaticDataRegistry) -> None:
    state = _state(registry, "mentak")
    state.systems[EMPTY].space_units = {"p1": {"cruiser": 1, "mech": 1},
                                        "p2": {"flagship": 1}}
    started, grid = _space_combat(registry, state, EMPTY)
    cruiser = next(u for u in battle.side_units(started, grid, registry, "p1"))
    assert not cruiser.sustain  # the Fourth Moon: ships lose SUSTAIN DAMAGE
    assert [u.base_type for u in battle_units.hit_shields(started, registry, "p1")] == ["mech"]


# ============================================================================ Thunder's Paradox


@ruling("breakthroughs:nomadbt#1", "F_nomad/thunders-paradox/1")
def test_thunders_paradox_odswieza_cudzego_agenta(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    state.players["p2"].leader_states = {"solagent": "exhausted"}
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p2", ctx={"player": "p2"})
    offer = _offers(state, "p1", "Thunder's Paradox")[0]
    inputs = _inputs(state, registry, offer)
    assert "auto" not in inputs[0] and "auto" not in inputs[1]
    state = triggers.accept_offer(state, "p1", offer.id,
                                  {"exhaust": f"p1|{nomad.ARTUNO}", "ready": "p2|solagent"})
    assert leaders.is_ready(state, registry, "p2", "solagent")
    assert state.players["p1"].leader_states.get(nomad.ARTUNO) == "exhausted"


def test_thunders_paradox_wyczerpanie_to_zdarzenie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    state.players["p1"].technologies = ["sr", "tcs"]
    state.players["p1"].leader_states = {nomad.ARTUNO: "exhausted"}
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    state = _accept(state, "p1", "Thunder's Paradox",
                    {"exhaust": f"p1|{nomad.MERCER}", "ready": f"p1|{nomad.ARTUNO}"})
    # Mercer "became exhausted": Temporal Command Suite may answer it.
    assert _offers(state, "p1", "Temporal Command Suite")


@ruling("F_nomad/quantum-manipulator/3")
def test_quantum_manipulator_bez_duranium(registry: StaticDataRegistry) -> None:
    from src.core.damage import set_damaged
    from src.core.hooks import technologies_combat

    state = _state(registry)
    system = state.systems[EMPTY]
    system.space_units = {"p1": {"dreadnought": 1, "mech": 1}}
    set_damaged(system, "space", "p1", "mech", 1)
    set_damaged(system, "space", "p1", "dreadnought", 1)
    ctx: dict[str, Any] = {"position": EMPTY, "kind": "space", "planet": None, "sustained": {}}
    assert technologies_combat._repairable(state, "p1", ctx) == ["dreadnought"]


@ruling("F_letnev/gravleash-maneuvers/8")
def test_thundarian_gravleash_na_inny_statek(registry: StaticDataRegistry) -> None:
    from src.core import active_effects, faction_components

    state = _state(registry, "letnev")
    state.systems[EMPTY].space_units = {"p1": {"cruiser": 2, "dreadnought": 1},
                                        "p2": {"cruiser": 2, "dreadnought": 1}}
    started, grid = _space_combat(registry, state, EMPTY)
    rolled = _rolled(registry, started, grid)
    active_effects.add_effect(rolled, "breakthroughs:letnevbt:ship", Duration.COMBAT_ROUND,
                              owner="p2", data={"base_type": "cruiser", "position": EMPTY})
    after, _ = faction_components.play(rolled, registry, "p1", "leader", nomad.THUNDARIAN)
    combat = after.active_combat
    assert combat is not None and combat.step is CombatStep.TRIGGERS
    decision = _offers(after, "p2", "Gravleash")[0]
    after = triggers.accept_offer(after, "p2", decision.id, {"gravleash_ship": "dreadnought"})
    after = battle.resume_after_triggers(after, grid, registry)
    assert after.active_combat is not None and after.active_combat.step is CombatStep.ROLL
    effect = next(e for e in after.active_effects if e.key == "breakthroughs:letnevbt:ship")
    assert effect.data["base_type"] == "dreadnought"


@ruling("C_relics/jrxs455o/1.1")
def test_tcs_odswieza_jr_xs455_o(registry: StaticDataRegistry) -> None:
    from src.core.hooks import relics_actions

    state = _state(registry)
    state.players["p1"].technologies = ["sr", "tcs"]
    state.players["p2"].relics = ["titanprototype"]
    state.active_player_id = "p2"
    played = state.clone()
    relics_actions.jr_xs455_o(played, registry, "p2", {"player": "p2", "placement": "none"})
    assert "titanprototype" in played.players["p2"].exhausted_relics
    played = _accept(played, "p1", "Temporal Command Suite")
    assert "titanprototype" not in played.players["p2"].exhausted_relics
    assert transaction.granted_pair(played, "p1", "p2")
