"""The Empyrean — every faction component (RULES.md 62.20) and the F_empyrean rulings.

Scenarios through the real API (offers, ACTIONs, notes, setup): ``test_flows_empyrean.py``.
Statuses without a test: ``tests/rulings_status.json``.

Board (ring 1 + part of ring 2): 000 Mecatol Rex, 101 The Dark (56, Empyrean home - a nebula),
102 Nebula (42), 103 empty (46), 104 Jord (Sol home), 105 Gravity Rift (41), 106 Tarmann,
201 empty (47), 202 Lodor (alpha), 203 Alpha Wormhole (39). Edges: 101-102-103-104-105-106 ring
around 000; 101-201/202; 102-202/203; 202-203; 201-202.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    agenda_phase,
    board_graph,
    economy,
    faction_tokens,
    leaders,
    movement,
    neighbors,
    offers,
    rules_hooks,
    space_cannon,
    system_swap,
    triggers,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    AgendaPhaseState,
    AgendaStep,
    AgendaVote,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.hooks import promissory_generic
from src.core.hooks.factions import empyrean
from src.core.movement_paths import shortest_legal_path
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.strategy_cards import diplomacy
from tests import boosts
from tests.factions.completeness import missing_components
from tests.rulings import ruling

MECATOL, DARK, NEBULA, EMPTY, JORD, RIFT, TARMANN = "000", "101", "102", "103", "104", "105", "106"
EMPTY2, LODOR, ALPHA = "201", "202", "203"


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


def _state(registry: StaticDataRegistry, other: str = "sol") -> GameState:
    """p1 = Empyrean (active, carrier + destroyer at home), p2 = rival with Jord (104)."""
    p1 = PlayerState(player_id="p1", color="purple", faction="empyrean", home_position=DARK,
                     controlled_planets=["thedark"], technologies=["vw", "as"])
    p2 = PlayerState(player_id="p2", color="red", faction=other, home_position=JORD,
                     controlled_planets=["jord"])
    systems = {
        MECATOL: SystemState(position=MECATOL, system_id="18"),
        DARK: SystemState(position=DARK, system_id="56", planet_owners={"thedark": "p1"},
                          space_units={"p1": {"carrier": 1, "destroyer": 1}}),
        NEBULA: SystemState(position=NEBULA, system_id="42"),
        EMPTY: SystemState(position=EMPTY, system_id="46"),
        JORD: SystemState(position=JORD, system_id="01", planet_owners={"jord": "p2"}),
        RIFT: SystemState(position=RIFT, system_id="41"),
        TARMANN: SystemState(position=TARMANN, system_id="22"),
        EMPTY2: SystemState(position=EMPTY2, system_id="47"),
        LODOR: SystemState(position=LODOR, system_id="26"),
        ALPHA: SystemState(position=ALPHA, system_id="39"),
    }
    state = GameState(phase=Phase.ACTION, active_player_id="p1", seating_order=["p1", "p2"],
                      players={"p1": p1, "p2": p2}, systems=systems)
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


def _activate(state: GameState, pid: str, position: str) -> None:
    state.active_player_id = pid
    state.active_system = position
    state.tactical_step = TacticalStep.MOVEMENT
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject=pid,
                  ctx={"player": pid, "position": position})


def _moved(state: GameState, pid: str, source: str, target: str, ships: dict[str, int],
           kind: str = "tactical") -> None:
    movement.fire_ships_moved(state, pid, target, source, ships, route=[source, target], kind=kind)


def _tether(state: GameState, a: str, b: str, owner: str = "p1") -> None:
    board_graph.ensure_system(state, min(a, b))
    zone = faction_tokens.border_zone(a, b)
    faction_tokens.place(state, owner, faction_tokens.VOID_TETHER, *zone)


def test_empyrean_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "empyrean") == []


# ===================================================================================== Voidborn


@ruling("abilities:voidborn#1", "F_empyrean/voidborn/1", "R_nebula/notes/6.1")
def test_voidborn_mglawica_nie_wplywa_na_ruch(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    grid = _bind(state, registry)
    # The Dark is a nebula: Empyrean ships starting there keep their move value; a rival does not.
    assert movement._effective_move_value(state, grid, registry, DARK, "destroyer", "p1",
                                          boost=False, tempesta=False) == 2
    state.systems[DARK].space_units["p2"] = {"destroyer": 1}
    assert movement._effective_move_value(state, grid, registry, DARK, "destroyer", "p2",
                                          boost=False, tempesta=False) == 1
    # Through a nebula: only the Empyrean (outside the Movement step too - no tactical step here).
    assert shortest_legal_path(grid, state, DARK, EMPTY, "p1", can_enter_asteroids=False) in (
        [DARK, NEBULA, EMPTY], [DARK, MECATOL, EMPTY])
    path = shortest_legal_path(grid, state, LODOR, EMPTY, "p1", can_enter_asteroids=False)
    assert path is not None and len(path) == 3
    assert shortest_legal_path(grid, state, ALPHA, EMPTY, "p1", can_enter_asteroids=False) == [
        ALPHA, NEBULA, EMPTY]
    rival = shortest_legal_path(grid, state, ALPHA, EMPTY, "p2", can_enter_asteroids=False)
    assert rival is None or NEBULA not in rival[1:-1]


@ruling("F_empyrean/voidborn/2")
def test_voidborn_mglawica_dalej_anomalia_i_premia_obroncy(registry: StaticDataRegistry) -> None:
    from src.core import battle_units

    state = _state(registry)
    grid = _bind(state, registry)
    assert "NEBULA" in grid.anomalies_at(DARK)
    state.systems[DARK].space_units["p2"] = {"destroyer": 1}
    units = battle_units.combat_units(state, grid, registry, kind="space", position=DARK,
                                      planet=None, player_id="p1", defender=True)
    assert units and all(u.modifier >= 1 for u in units)


# ================================================================================== Aetherpassage


@ruling("abilities:aetherpassage#1", "F_empyrean/aetherpassage/1")
def test_aetherpassage_przelot_przez_statki_empyrean(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[MECATOL].space_units = {"p1": {"destroyer": 1}}
    state.systems[EMPTY].space_units = {"p2": {"destroyer": 1}}
    grid = _bind(state, registry)
    before = shortest_legal_path(grid, state, EMPTY, TARMANN, "p2", can_enter_asteroids=False)
    assert before is None or MECATOL not in before
    # The decision comes only AFTER the rival activated (an offer on SYSTEM_ACTIVATED/AFTER).
    assert not _offers(state, "p1", "Aetherpassage")
    _activate(state, "p2", TARMANN)
    state = _accept(state, "p1", "Aetherpassage")
    grid = _bind(state, registry)
    assert shortest_legal_path(grid, state, EMPTY, TARMANN, "p2", can_enter_asteroids=False) == [
        EMPTY, MECATOL, TARMANN]
    # Not for its own activation (it can already fly through its own ships).
    other = _state(registry)
    _activate(other, "p1", TARMANN)
    assert not _offers(other, "p1", "Aetherpassage")


def test_aetherpassage_inne_statki_dalej_blokuja(registry: StaticDataRegistry) -> None:
    from src.core import active_effects

    state = _state(registry)
    state.systems[MECATOL].space_units = {"p1": {"destroyer": 1}}
    active_effects.add_effect(state, empyrean.PASSAGE, Duration.TACTICAL_ACTION, owner="p2",
                              data={"by": "p1"})
    assert empyrean.passage_through_ships(state, "p2", {"position": MECATOL})
    state.systems[MECATOL].space_units["p3"] = {"destroyer": 1}
    assert not empyrean.passage_through_ships(state, "p2", {"position": MECATOL})


@ruling("abilities:dark_whispers#1", "abilities:dark_whispers#2")
def test_dark_whispers_dwie_notki_frakcji(registry: StaticDataRegistry) -> None:
    from src.core import game_setup

    state = _state(registry)
    dealt = game_setup.deal_promissory_notes(state, registry)
    hand = dealt.players["p1"].private.promissory_notes
    assert "dark_pact" in hand and "blood_pact" in hand


# ====================================================================================== Voidwatch


@ruling("technologies:vw#1", "F_empyrean/voidwatch/1", "F_empyrean/voidwatch/2")
def test_voidwatch_rywal_oddaje_notke(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p2"].private.promissory_notes = ["red_cf", "red_ta"]
    state.systems[TARMANN].planet_units = {"tarmann": {"p1": {"infantry": 1}}}
    _moved(state, "p2", JORD, TARMANN, {"destroyer": 1})
    found = _offers(state, "p2", "Voidwatch")
    assert found and found[0].mandatory
    inputs = _inputs(state, registry, found[0])
    assert [o["value"] for o in inputs[0]["options"]] == ["red_cf", "red_ta"]  # the mover chooses
    assert inputs[0]["auto"] == "red_cf"
    state = triggers.accept_offer(state, "p2", found[0].id, {"note": "red_ta"})
    assert state.players["p1"].private.promissory_notes == ["red_ta"]
    assert state.players["p2"].private.promissory_notes == ["red_cf"]
    assert state.players["p2"].transacted_with == []  # not a transaction (voidwatch 2)


def test_voidwatch_bez_notek_albo_bez_jednostek_nic(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[TARMANN].planet_units = {"tarmann": {"p1": {"infantry": 1}}}
    _moved(state, "p2", JORD, TARMANN, {"destroyer": 1})  # "if able": empty hand
    assert not _offers(state, "p2", "Voidwatch")
    state.players["p2"].private.promissory_notes = ["red_cf"]
    _moved(state, "p2", JORD, EMPTY, {"destroyer": 1})  # no Empyrean units there
    assert not _offers(state, "p2", "Voidwatch")
    _moved(state, "p1", DARK, TARMANN, {"destroyer": 1})  # the Empyrean itself
    assert not _offers(state, "p1", "Voidwatch")


# =================================================================================== Aetherstream


@ruling("technologies:as#1", "F_empyrean/aetherstream/1")
def test_aetherstream_sasiad_obok_anomalii(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[EMPTY].space_units = {"p1": {"destroyer": 1}}  # neighbours with Jord
    _activate(state, "p2", TARMANN)  # Tarmann is next to the Gravity Rift
    state = _accept(state, "p1", "Aetherstream")
    bonus = rules_hooks.modify(rules_hooks.POINT_MOVEMENT_MOVE_VALUE, state, "p2", 1,
                               {"from": JORD, "base_type": "destroyer"})
    assert bonus == 2
    assert rules_hooks.modify(rules_hooks.POINT_MOVEMENT_MOVE_VALUE, state, "p1", 1,
                              {"from": DARK, "base_type": "carrier"}) == 1


def test_aetherstream_nie_dla_niesasiada_i_bez_anomalii(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _activate(state, "p2", TARMANN)  # not neighbours (p1 only at home)
    assert not _offers(state, "p1", "Aetherstream")
    state = _state(registry)
    state.systems[EMPTY].space_units = {"p1": {"destroyer": 1}}
    _activate(state, "p2", EMPTY)  # Empty (103) touches the Nebula (102)
    assert _offers(state, "p1", "Aetherstream")
    state = _state(registry)
    _activate(state, "p1", TARMANN)  # "you": the Empyrean player itself
    assert _offers(state, "p1", "Aetherstream")


@ruling("F_empyrean/aetherstream/2")
def test_aetherstream_odciete_void_tetherem(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[JORD].space_units = {"p1": {"destroyer": 1}}  # neighbours
    _tether(state, JORD, RIFT)
    grid = _bind(state, registry)
    # Jord (104) touches Mecatol, Empty (103) and the Gravity Rift (105) - the tether cuts the rift.
    assert RIFT not in board_graph.neighbors_for_player(state, grid, "p2", JORD)
    assert not empyrean._stream_ready(state, "p1", {"player": "p2", "position": JORD})
    assert empyrean._stream_ready(state, "p1", {"player": "p1", "position": JORD})
    from src.core import active_effects

    active_effects.add_effect(state, empyrean.TETHER_ALLOWED, Duration.TACTICAL_ACTION,
                              owner="p2", data={"by": "p1"})
    assert empyrean._stream_ready(state, "p1", {"player": "p2", "position": JORD})


# ============================================================================== Acamar (agent)


@ruling("leaders:empyreanagent#1", "leaders:empyreanagent#2")
def test_acamar_rywal_zyskuje_zeton(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _moved(state, "p2", JORD, EMPTY, {"destroyer": 1})
    assert not _offers(state, "p1", "Acamar")  # cooperative: requested, not pushed (54.15)
    state = boosts.request(state, registry, "p2", "Acamar")
    state = _accept(state, "p1", "Acamar")
    assert state.players["p1"].leader_states.get("empyreanagent") == "exhausted"
    decision = _offers(state, "p2", "Acamar")[0]
    assert decision.mandatory and _inputs(state, registry, decision)[0]["auto"] == "tactical"
    before = state.players["p2"].fleet_cc
    state = triggers.accept_offer(state, "p2", decision.id, {"pool": "fleet"})
    assert state.players["p2"].fleet_cc == before + 1
    assert state.players["p2"].cc_reinf == 7


@ruling("F_empyrean/acamar/1", "F_muaat/adjudicator-baal-nova-seed/8")
def test_acamar_tylko_system_bez_planet(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _moved(state, "p2", JORD, TARMANN, {"destroyer": 1})
    assert not boosts.names(state, registry, "p2")  # Tarmann has a planet
    state.systems[TARMANN].destroyed_planets = ["tarmann"]  # Stellar Converter
    _moved(state, "p2", JORD, TARMANN, {"destroyer": 1})
    assert boosts.names(state, registry, "p2") == ["Acamar"]
    # Nova Seed: the CURRENT tile decides (the supernova has no planets).
    other = _state(registry)
    other.systems[TARMANN].system_id = "81"
    _bind(other, registry)
    _moved(other, "p2", JORD, TARMANN, {"destroyer": 1})
    assert boosts.names(other, registry, "p2") == ["Acamar"]


# =========================================================================== Xuange (commander)


@ruling("leaders:empyreancommander#unlock", "F_empyrean/xuange/1")
def test_xuange_odblokowanie_sasiedzi_wszystkich(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    assert not empyrean._xuange_unlocked(state, registry, "p1")
    state.players["p2"].transacted_with = ["p1"]  # transactions do not make neighbours
    state.phase = Phase.AGENDA
    assert not empyrean._xuange_unlocked(state, registry, "p1")
    state.systems[EMPTY].space_units = {"p1": {"destroyer": 1}}
    assert empyrean._xuange_unlocked(state, registry, "p1")


@ruling("leaders:empyreancommander#1", "F_empyrean/xuange/2", "F_empyrean/xuange/5")
def test_xuange_zwraca_zeton(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states["empyreancommander"] = leaders.UNLOCKED
    state.systems[TARMANN].command_tokens = ["p1"]
    state.systems[EMPTY].command_tokens = ["p1"]
    _moved(state, "p2", EMPTY, TARMANN, {"destroyer": 1}, kind="retreat")  # any movement
    state = _accept(state, "p1", "Xuange")
    assert state.systems[TARMANN].command_tokens == []
    assert state.systems[EMPTY].command_tokens == ["p1"]  # only the system moved into
    assert state.players["p1"].cc_reinf == 9
    _moved(state, "p1", DARK, EMPTY, {"destroyer": 1})  # "another player"
    assert not _offers(state, "p1", "Xuange")


@ruling("F_empyrean/xuange/3")
def test_xuange_odblokowany_tym_ruchem_nie_dziala(registry: StaticDataRegistry) -> None:
    """The offer is decided when the move fires; the unlock is refreshed only after it settles."""
    state = _state(registry)
    state.systems[EMPTY].command_tokens = ["p1"]
    state.systems[MECATOL].space_units = {"p1": {"destroyer": 1}}
    state.systems[EMPTY].space_units = {"p2": {"destroyer": 1}}  # the move makes them neighbours
    _moved(state, "p2", JORD, EMPTY, {"destroyer": 1})
    assert not _offers(state, "p1", "Xuange")
    assert empyrean._xuange_unlocked(state, registry, "p1")


# ========================================================= Conservator Procyon — Multiverse Shift


def _resolve_frontier(state: GameState, registry: StaticDataRegistry) -> GameState:
    from src.core import exploration

    option = next(o for o in exploration.options_for(state, registry) if o.enabled)
    param = option.params[0][0] if option.params else None
    return exploration.resolve(state, registry, option.id, param)


@ruling("leaders:empyreanhero#1", "leaders:empyreanhero#2", "leaders:empyreanhero#3",
        "F_empyrean/conservator-procyon-multiverse-shift/1")
def test_multiverse_shift_frontier_i_eksploracja(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[TARMANN].destroyed_planets = ["tarmann"]  # "contains no planets" (procyon 1)
    state.systems[NEBULA].space_units = {"p1": {"destroyer": 1}}
    state.systems[EMPTY2].space_units = {"p1": {"cruiser": 1}}
    state.systems[EMPTY2].frontier_token = True  # already has one: not doubled
    state.decks.exploration_deck["frontier"] = ["urf1", "urf2"]  # relic fragments (keep)
    empyrean.multiverse_shift(state, registry, "p1", {})
    with_token = {pos for pos, s in state.systems.items() if s.frontier_token}
    # Explored right away: the first queued token (Nebula 102) left its system.
    assert {EMPTY, RIFT, TARMANN, ALPHA, EMPTY2} <= with_token
    assert JORD not in with_token and DARK not in with_token and MECATOL not in with_token
    ex = state.exploration
    assert ex is not None and ex.current is not None and ex.current.deck == "frontier"
    assert ex.position == NEBULA and ex.frontier_queue == [EMPTY2]  # board order
    state = _resolve_frontier(state, registry)
    ex = state.exploration
    assert ex is not None and ex.position == EMPTY2 and ex.current is not None
    assert not state.systems[EMPTY2].frontier_token
    state = _resolve_frontier(state, registry)
    assert state.exploration is not None and state.exploration.frontier_queue == []


@ruling("leaders:empyreanhero#unlock")
def test_multiverse_shift_odblokowanie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    assert leaders.state_of(state, registry, "p1", "empyreanhero") == "locked"
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", "empyreanhero") == leaders.UNLOCKED


@ruling("F_empyrean/conservator-procyon-multiverse-shift/2", "R_fracture/notes/3",
        "R_frontier_tokens/notes/3")
def test_multiverse_shift_w_the_fracture(registry: StaticDataRegistry) -> None:
    from src.core import fracture

    state = _state(registry)
    state.fracture.in_play = True
    grid = grid_from_state(state, registry)
    fracture.sync_grid(grid, state, registry)
    board_graph.bind_grid_provider(lambda: grid)
    empyrean.multiverse_shift(state, registry, "p1", {})
    planetless = [pos for pos in fracture.FRACTURE_POSITIONS
                  if pos in grid.positions and empyrean._no_planets(state, registry, pos)]
    assert planetless
    assert all(state.systems[pos].frontier_token for pos in planetless)


# ====================================================================== Dark Pact / Blood Pact


def _pact(state: GameState, note: str, holder: str = "p2") -> None:
    state.players[holder].promissory_notes_in_play = [note]


@ruling("promissory_notes:dark_pact#2", "F_empyrean/dark-pact/1", "F_empyrean/dark-pact/3")
def test_dark_pact_pelne_commodities(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _pact(state, "dark_pact")
    value = economy.commodity_value(state, "p2")
    state.players["p2"].commodities = value
    economy.give_to_player(state, "p2", "p1", commodities=value - 1, cause="transaction")
    assert state.players["p2"].trade_goods == 0  # not the full value
    assert state.players["p1"].trade_goods == value - 1
    state.players["p2"].commodities = value
    state.players["p1"].trade_goods = 0
    economy.give_to_player(state, "p2", "p1", commodities=value, cause="transaction")
    assert state.players["p2"].trade_goods == 1
    assert state.players["p1"].trade_goods == value + 1  # with the commodities (simultaneous)
    # The value is the maximum: replenishing never goes above it (dark-pact 1).
    economy.replenish_commodities(state, "p2")
    assert state.players["p2"].commodities == value


@ruling("F_empyrean/dark-pact/2")
def test_dark_pact_przez_trade_agreement(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _pact(state, "dark_pact")
    state.players["p2"].commodities = economy.commodity_value(state, "p2")
    promissory_generic.trade_agreement(state, registry, "p1", {"__owner": "p2"})
    assert state.players["p2"].trade_goods == 1


@ruling("F_empyrean/dark-pact/4")
def test_dark_pact_jedno_pillage(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    p3 = PlayerState(player_id="p3", color="yellow", faction="mentak", home_position=EMPTY2)
    state.players["p3"] = p3
    state.seating_order.append("p3")
    state.systems[MECATOL].space_units = {"p3": {"cruiser": 1}}
    state.systems[TARMANN].space_units = {"p2": {"cruiser": 1}}
    _bind(state, registry)
    _pact(state, "dark_pact")
    state.players["p1"].trade_goods = 5
    state.players["p2"].trade_goods = 5
    state.players["p2"].commodities = economy.commodity_value(state, "p2")
    economy.give_to_player(state, "p2", "p1", commodities=state.players["p2"].commodities,
                           cause="transaction")
    assert not _offers(state, "p3", "Pillage")  # the bonus TG is part of the transaction
    economy.gain_trade_goods(state, "p2", 1)
    assert _offers(state, "p3", "Pillage")  # control: a plain gain is pillageable


@ruling("promissory_notes:dark_pact#3", "promissory_notes:blood_pact#3",
        "F_empyrean/dark-pact/5", "F_empyrean/dark-pact/6", "F_empyrean/blood-pact/2",
        "F_empyrean/blood-pact/3")
def test_pakty_wracaja_po_aktywacji(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p2"].promissory_notes_in_play = ["dark_pact", "blood_pact"]
    state.systems[TARMANN].planet_units = {"tarmann": {"p1": {"pds": 1}}}  # structures only
    _activate(state, "p2", EMPTY)
    assert state.players["p2"].promissory_notes_in_play == ["dark_pact", "blood_pact"]
    _activate(state, "p2", TARMANN)  # no hostile act needed
    assert state.players["p2"].promissory_notes_in_play == []
    assert {"dark_pact", "blood_pact"} <= set(state.players["p1"].private.promissory_notes)


@ruling("F_empyrean/dark-pact/7", "F_empyrean/blood-pact/4")
def test_pakty_nie_wracaja_po_diplomacy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p2"].promissory_notes_in_play = ["dark_pact", "blood_pact"]
    state.systems[DARK].planet_owners = {"thedark": "p1"}
    diplomacy._primary(state, None, "p1", {"system": DARK, "planets": []})  # type: ignore[arg-type]
    assert "p2" in state.systems[DARK].command_tokens
    assert state.players["p2"].promissory_notes_in_play == ["dark_pact", "blood_pact"]


def _agenda(state: GameState, votes: dict[str, tuple[str, int]]) -> None:
    state.phase = Phase.AGENDA
    state.agenda = AgendaPhaseState(step=AgendaStep.VOTE, agenda_id="x",
                                    outcomes=["for", "against"], kind="for_against")
    for pid, (outcome, n) in votes.items():
        state.agenda.votes[pid] = AgendaVote(outcome=outcome, votes=n)


def _voted(state: GameState, pid: str) -> None:
    triggers.fire(state, GameEvent.AGENDA_VOTES_CAST, Moment.AFTER, subject=pid,
                  ctx={"player": pid})


@ruling("promissory_notes:blood_pact#2", "F_empyrean/blood-pact/1")
def test_blood_pact_cztery_glosy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _pact(state, "blood_pact")
    _agenda(state, {"p2": ("for", 3)})
    _voted(state, "p2")
    assert state.agenda is not None and state.agenda.votes["p2"].votes == 3  # Empyrean not yet
    state.agenda.votes["p1"] = AgendaVote(outcome="for", votes=2)
    _voted(state, "p1")
    assert state.agenda.votes["p2"].votes == 7
    _voted(state, "p1")  # once per agenda
    assert state.agenda.votes["p2"].votes == 7


@ruling("F_empyrean/blood-pact/1.1")
def test_blood_pact_rozne_wyniki_albo_brak_glosu(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _pact(state, "blood_pact")
    _agenda(state, {"p2": ("for", 3), "p1": ("against", 2)})
    _voted(state, "p1")
    assert state.agenda is not None and state.agenda.votes["p2"].votes == 3
    state = _state(registry)
    _pact(state, "blood_pact")
    _agenda(state, {"p2": ("for", 3)})
    assert state.agenda is not None
    state.agenda.abstained = ["p1"]  # cannot / does not vote
    _voted(state, "p2")
    assert state.agenda.votes["p2"].votes == 3
    assert agenda_phase.totals(state.agenda)["for"] == 3


# ============================================================================ Dynamo (flagship)


def _sustained(state: GameState, pid: str, position: str, base_type: str = "dreadnought") -> None:
    from src.core.damage import set_damaged

    set_damaged(state.systems[position], "space", pid, base_type, 1)
    triggers.fire(state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject=pid,
                  ctx={"player": pid, "base_type": base_type, "count": 1,
                       "position": position, "zone": "space"})


@ruling("units:empyrean_flagship#1", "F_empyrean/dynamo/4", "F_empyrean/dynamo/4.1")
def test_dynamo_naprawa_za_2_wplywu(registry: StaticDataRegistry) -> None:
    from src.core.damage import damaged_count

    state = _state(registry)
    state.systems[DARK].space_units["p1"]["flagship"] = 1
    state.systems[TARMANN].space_units = {"p2": {"dreadnought": 2}}  # adjacent to The Dark
    _sustained(state, "p2", TARMANN)
    offer = _offers(state, "p1", "Dynamo")[0]
    fields = {i["key"]: i for i in _inputs(state, registry, offer)}
    assert fields["repairs"]["auto"] == 1 and fields["planets"]["payment"]["cost"] == 2
    state = triggers.accept_offer(state, "p1", offer.id, {})  # "Auto": pays with The Dark
    assert damaged_count(state.systems[TARMANN], "space", "p2", "dreadnought") == 0
    assert "thedark" in state.players["p1"].exhausted_planets
    # The Dark is spent on ONE repair - its excess influence does not repair a second ship.
    _sustained(state, "p2", TARMANN)
    assert not _offers(state, "p1", "Dynamo")  # no ready influence left (4.1)


def test_dynamo_zasieg_i_brak_wplywu(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[DARK].space_units["p1"]["flagship"] = 1
    state.systems[JORD].space_units = {"p2": {"dreadnought": 1}}  # not adjacent to The Dark
    _sustained(state, "p2", JORD)
    assert not _offers(state, "p1", "Dynamo")
    state.systems[DARK].space_units["p2"] = {"dreadnought": 1}  # the flagship's own system
    _sustained(state, "p2", DARK)
    assert _offers(state, "p1", "Dynamo")


@ruling("F_empyrean/dynamo/2", "F_argent/raid-formation/4.2")
def test_dynamo_bez_sustain_damage_brak_oferty(registry: StaticDataRegistry) -> None:
    from src.core.damage import set_damaged

    state = _state(registry)
    state.systems[DARK].space_units["p1"]["flagship"] = 1
    state.systems[TARMANN].space_units = {"p2": {"dreadnought": 1}}
    set_damaged(state.systems[TARMANN], "space", "p2", "dreadnought", 1)  # Raid Formation
    assert not _offers(state, "p1", "Dynamo")


@ruling("F_empyrean/dynamo/3")
def test_dynamo_direct_hit_nadal_niszczy(registry: StaticDataRegistry) -> None:
    from src.core.game_state import ActiveCombat
    from src.core.hooks import reactions_combat

    state = _state(registry)
    state.systems[DARK].space_units["p1"]["flagship"] = 1
    state.systems[TARMANN].space_units = {"p2": {"dreadnought": 1}, "p1": {"cruiser": 1}}
    state.active_system = TARMANN
    state.active_combat = ActiveCombat(kind="space", position=TARMANN, attacker="p1",
                                       defender="p2")
    state.active_combat.sustained_ships = [{"player": "p2", "base_type": "dreadnought",
                                            "count": 1}]
    _sustained(state, "p2", TARMANN)
    state = _accept(state, "p1", "Dynamo", {"repairs": 1, "planets": ["thedark"]})
    combat = state.active_combat
    assert combat is not None
    assert reactions_combat._sustained_of(combat, state, "p2") == ["dreadnought"]


# ============================================================================== Watcher (mech)


def _held(state: GameState, player: str = "p2", card: str = "sabo1") -> None:
    from src.core.game_state import HeldPlay

    state.held_play = HeldPlay(player_id=player, card_id=card, opened_at=0.0, eligible=["p1"],
                               is_action=True)


@ruling("units:empyrean_mech#1", "F_empyrean/watcher/1", "F_empyrean/watcher/3",
        "F_empyrean/watcher/8")
def test_watcher_anuluje_karte_akcji(registry: StaticDataRegistry) -> None:
    from src.core import card_hold, faction_components
    from src.core.game_state import HeldPlay

    state = _state(registry)
    state.systems[TARMANN].planet_units = {"tarmann": {"p1": {"mech": 1}}}
    state.systems[RIFT].space_units = {"p2": {"cruiser": 1}}  # adjacent to Tarmann
    assert card_hold.cancellers(state, "p2", "sabo1") == ["p1"]  # the window opens for Empyrean
    state.held_play = HeldPlay(player_id="p2", card_id="sabo1", opened_at=0.0, eligible=["p1"],
                               is_action=True)
    state.players["p2"].took_action_this_turn = True
    inputs = empyrean.watcher_inputs(state, registry, "p1")
    assert inputs[0]["auto"] == f"{TARMANN}|tarmann|0"
    after, _ = faction_components.play(state, registry, "p1", "unit", empyrean.MECH, {})
    assert after.held_play is None
    assert "mech" not in after.systems[TARMANN].planet_units["tarmann"].get("p1", {})
    assert "sabo1" in after.decks.action_card_discard  # discarded, its effect never resolves
    assert "sabo1" not in after.players["p2"].private.action_cards


@ruling("F_empyrean/watcher/2", "F_empyrean/watcher/2.1")
def test_watcher_musi_byc_przy_jednostkach_gracza(registry: StaticDataRegistry) -> None:
    from src.core import faction_components

    state = _state(registry)
    state.systems[EMPTY2].space_units = {"p1": {"mech": 1}}  # mech in space (2 away from Jord)
    _held(state)
    assert empyrean._watcher_window(state, registry, "p1") is not None
    state.systems[LODOR].space_units = {"p2": {"destroyer": 1}}  # adjacent to 201
    assert empyrean._watcher_window(state, registry, "p1") is None
    with pytest.raises(ValueError):
        faction_components.play(state, registry, "p2", "unit", empyrean.MECH, {})
    _held(state, player="p1")
    assert empyrean._watcher_window(state, registry, "p1") is not None  # own card


# ======================================================================= Void Tether (breakthrough)


@ruling("breakthroughs:empyreanbt#1")
def test_void_tether_polozenie_i_przesuniecie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    state.systems[TARMANN].space_units = {"p2": {"cruiser": 1}}
    _activate(state, "p1", DARK)
    offer = _offers(state, "p1", "Void Tether: place")[0]
    fields = {i["key"]: i for i in _inputs(state, registry, offer)}
    assert fields["token"]["auto"] == "new"
    assert {o["value"] for o in fields["border"]["options"]} == {MECATOL, NEBULA, TARMANN,
                                                                  EMPTY2, LODOR}
    assert fields["border"]["auto"] == TARMANN  # the neighbour with a rival
    state = triggers.accept_offer(state, "p1", offer.id, {"token": "new", "border": TARMANN})
    assert faction_tokens.borders(state, faction_tokens.VOID_TETHER) == [(DARK, TARMANN, "p1")]
    assert faction_tokens.supply_left(state, "p1", faction_tokens.VOID_TETHER) == 1
    _activate(state, "p1", DARK)
    state = _accept(state, "p1", "Void Tether: place",
                    {"token": f"{DARK}|{TARMANN}", "border": NEBULA})
    assert faction_tokens.borders(state, faction_tokens.VOID_TETHER) == [(DARK, NEBULA, "p1")]


def test_void_tether_warunek_aktywacji(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    _activate(state, "p1", JORD)  # neither contains nor is adjacent to Empyrean units / planets
    assert not _offers(state, "p1", "Void Tether: place")
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    _activate(state, "p1", MECATOL)  # adjacent to The Dark
    assert _offers(state, "p1", "Void Tether: place")


@ruling("breakthroughs:empyreanbt#2", "F_empyrean/void-tether/1", "F_empyrean/void-tether/1.1")
def test_void_tether_odcina_sasiedztwo_innym(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _tether(state, LODOR, ALPHA)  # 202-203: an edge AND matching alpha wormholes
    grid = _bind(state, registry)
    assert grid.are_adjacent(LODOR, ALPHA)
    assert ALPHA not in board_graph.neighbors_for_player(state, grid, "p2", LODOR)
    assert not board_graph.are_adjacent_for_player(state, grid, "p2", ALPHA, LODOR)
    assert board_graph.are_adjacent_for_player(state, grid, "p1", ALPHA, LODOR)
    path = shortest_legal_path(grid, state, LODOR, ALPHA, "p2", can_enter_asteroids=False)
    assert path is None or len(path) > 2
    assert shortest_legal_path(grid, state, LODOR, ALPHA, "p1", can_enter_asteroids=False) == [
        LODOR, ALPHA]
    # Neighbours: Empyrean across the tether still is (1.1); two other players are not.
    state.systems[LODOR].space_units = {"p2": {"cruiser": 1}}
    state.systems[ALPHA].space_units = {"p1": {"cruiser": 1}}
    found = neighbors.neighbors_by_player(state, grid)
    assert "p2" in found["p1"] and "p1" in found["p2"]
    p3 = PlayerState(player_id="p3", color="yellow", faction="xxcha")
    state.players["p3"] = p3
    state.systems[ALPHA].space_units = {"p3": {"cruiser": 1}}
    found = neighbors.neighbors_by_player(state, grid)
    assert "p3" not in found["p2"]


def test_void_tether_zgoda_i_deep_space_cannon(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    _tether(state, JORD, RIFT)
    _activate(state, "p2", RIFT)
    state = _accept(state, "p1", "Void Tether: allow")
    grid = _bind(state, registry)
    assert RIFT in board_graph.neighbors_for_player(state, grid, "p2", JORD)
    # Space Cannon range follows the same layers (the shooter's adjacency).
    state.active_effects = []
    state.players["p2"].technologies.append("pds2")
    state.systems[JORD].planet_units = {"jord": {"p2": {"pds": 1}}}
    state.systems[RIFT].space_units = {"p1": {"cruiser": 1}}
    state.active_system = RIFT
    state.tactical_step = TacticalStep.SPACE_CANNON
    assert not [s for s in space_cannon.offense_shooters(state, grid, registry, "p2") if s.remote]


@ruling("F_empyrean/void-tether/2")
def test_void_tether_zostaje_po_eliminacji(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _tether(state, LODOR, ALPHA)
    del state.players["p1"]
    state.seating_order = ["p2"]
    grid = _bind(state, registry)
    assert ALPHA not in board_graph.neighbors_for_player(state, grid, "p2", LODOR)


def test_void_tether_zostaje_przy_zamianie_systemow(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _tether(state, LODOR, ALPHA)
    system_swap.swap_systems(state, LODOR, TARMANN)
    assert faction_tokens.borders(state, faction_tokens.VOID_TETHER) == [(LODOR, ALPHA, "p1")]


def test_void_tether_w_web_data(registry: StaticDataRegistry) -> None:
    from src.api import web_data

    state = _state(registry)
    _tether(state, MECATOL, DARK)
    grid = _bind(state, registry)
    assert web_data.border_direction(grid, MECATOL, DARK) == 0  # 101 is north of 000
    assert web_data.border_direction(grid, DARK, MECATOL) == 3
    assert web_data.build_border_anomalies(state, grid) == [
        {"tile": MECATOL, "direction": 0, "type": "void_tether"}]


@ruling("F_empyrean/watcher/4", "F_empyrean/watcher/4.1", "F_empyrean/watcher/4.2",
        "F_empyrean/watcher/5")
def test_watcher_ogloszenie_przed_anulowaniem_i_brak_efektu(registry: StaticDataRegistry) -> None:
    """The card waits on the table with its announced choices (targets, variable cost) - the hold
    window is what the Watcher answers; its effect (dice, draws) runs only after the window."""
    from src.core import card_hold, faction_components
    from src.core.game_state import HeldPlay

    state = _state(registry)
    state.systems[TARMANN].space_units = {"p1": {"mech": 1}, "p2": {"cruiser": 1}}
    announced = {"position": TARMANN, "player": "p1", "trade_goods": 2}
    state.held_play = HeldPlay(player_id="p2", card_id="plag1", params=announced, opened_at=0.0,
                               eligible=["p1"], is_action=True)
    assert state.held_play.params == announced  # announced BEFORE the Watcher may trigger
    before_tg = state.players["p2"].trade_goods
    after, _ = faction_components.play(state, registry, "p1", "unit", empyrean.MECH, {})
    assert after.held_play is None
    assert after.players["p2"].trade_goods == before_tg  # no cost paid, no effect resolved
    with pytest.raises(ValueError):
        card_hold.resolve(after, registry)  # nothing left to resolve


@ruling("F_empyrean/xuange/4")
def test_xuange_floating_factory_saar_ginie_przed_odblokowaniem(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, other="saar")
    state.systems[JORD].planet_owners = {}
    state.players["p2"].controlled_planets = []
    state.systems[EMPTY].space_units = {"p2": {"spacedock": 1}}  # a Floating Factory, no ships
    state.systems[EMPTY].space_units["p1"] = {"destroyer": 1}
    _bind(state, registry)
    _moved(state, "p1", DARK, EMPTY, {"destroyer": 1})
    assert "p2" not in state.systems[EMPTY].space_units or not state.systems[EMPTY].space_units[
        "p2"].get("spacedock")
    assert not empyrean._xuange_unlocked(state, registry, "p1")
