"""The Ghosts of Creuss — every faction component (RULES.md 62.19) and the F_creuss rulings.

Scenarios through the real API (ACTIONs, offers, the note, setup): ``test_flows_ghost.py``.
Statuses without a test: ``tests/rulings_status.json``.

Board (ring 1 + ring 2, ``positions`` table): 000 Mecatol Rex, 101 Creuss Gate (17, delta) on the
Creuss home slot, 102 Lodor (alpha), 103 Vefut II, 104 Quann (beta), 105 Jord (Sol home), 106
Tarmann, 201 Alpha Wormhole (39), 209 Beta Wormhole (40), 207 asteroid field (44); Creuss home
(51, delta) off-board at ``tr``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    action_adjacency,
    board_graph,
    component_action,
    faction_components,
    faction_tokens,
    leaders,
    movement,
    neighbors,
    production,
    retreat,
    rules_hooks,
    space_cannon,
    system_swap,
    triggers,
)
from src.core.components import ComponentCategory
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    EliminatedPlayer,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import Hex, HexGrid
from src.core.hooks.factions import ghost, mentak
from src.core.movement_paths import shortest_legal_path, wormhole_link_blocked
from src.core.production import ProductionOrder
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from tests.factions.completeness import missing_components
from tests.rulings import ruling

MECATOL, GATE, LODOR, VEFUT, QUANN, JORD, TARMANN = "000", "101", "102", "103", "104", "105", "106"
ALPHA_EMPTY, BETA_EMPTY, ASTEROIDS = "201", "209", "207"
HOME = "tr"  # Creuss home (51) off-board
ALPHA, BETA, GAMMA = "creussalpha", "creussbeta", "creussgamma"


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


def _grid(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    grid = grid_from_state(state, registry)
    grid.place_system(HOME, "51", wormholes=["DELTA"], hex_override=Hex(9, -9, 0))
    grid.build_edges()
    grid.sync_token_wormholes({})
    grid.sync_token_wormholes(board_graph.placed_wormholes(state))
    return grid


def _bind(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    """Map of the CURRENT state (tokens and Hil Colish re-synced on every read, like the API)."""
    board_graph.bind_grid_provider(lambda: _grid(state, registry))
    return _grid(state, registry)


def _state(registry: StaticDataRegistry, other: str = "sol") -> GameState:
    """p1 = Creuss (active, carrier + 2 destroyers at home), p2 = rival with Jord (105)."""
    p1 = PlayerState(player_id="p1", color="blue", faction="ghost", home_position=HOME,
                     controlled_planets=["creuss"], technologies=["wg", "ds"])
    p2 = PlayerState(player_id="p2", color="red", faction=other, home_position=JORD,
                     controlled_planets=["jord"])
    systems = {
        MECATOL: SystemState(position=MECATOL, system_id="18"),
        GATE: SystemState(position=GATE, system_id="17", frontier_token=True),
        LODOR: SystemState(position=LODOR, system_id="26"),
        VEFUT: SystemState(position=VEFUT, system_id="20"),
        QUANN: SystemState(position=QUANN, system_id="25"),
        JORD: SystemState(position=JORD, system_id="01", planet_owners={"jord": "p2"}),
        TARMANN: SystemState(position=TARMANN, system_id="22"),
        ALPHA_EMPTY: SystemState(position=ALPHA_EMPTY, system_id="39"),
        BETA_EMPTY: SystemState(position=BETA_EMPTY, system_id="40"),
        ASTEROIDS: SystemState(position=ASTEROIDS, system_id="44"),
        HOME: SystemState(position=HOME, system_id="51", planet_owners={"creuss": "p1"},
                          space_units={"p1": {"carrier": 1, "destroyer": 2}}),
    }
    state = GameState(phase=Phase.ACTION, active_player_id="p1", seating_order=["p1", "p2"],
                      players={"p1": p1, "p2": p2}, systems=systems)
    for player in state.players.values():
        player.cc_reinf = 8
        player.tactical_cc = 3
    _bind(state, registry)
    return state


def _offers(state: GameState, pid: str, label: str) -> list[Any]:
    return [o for o in triggers.offers_for(state, pid) if label in o.label]


def _play(state: GameState, registry: StaticDataRegistry, kind: str, comp: str,
          params: dict[str, Any] | None = None, pid: str = "p1") -> GameState:
    after, _ = faction_components.play(state, registry, pid, kind, comp, params or {})
    _bind(after, registry)
    return after


def _generator(state: GameState, registry: StaticDataRegistry, params: dict[str, Any]
               ) -> GameState:
    """Wormhole Generator as a component action (technology ACTION) of the active player."""
    after = component_action.play_component_action(state, "p1", "wg", params=params)
    _bind(after, registry)
    return after


def _tokens(state: GameState) -> dict[str, str]:
    """``{kind: position}`` of the Creuss tokens on the board."""
    return {kind: pos for kind in faction_tokens.CREUSS_WORMHOLES
            for pos, _zone in faction_tokens.tokens_of(state, "p1", kind)}


def _put_token(state: GameState, registry: StaticDataRegistry, kind: str, position: str) -> None:
    ghost.place_or_move_token(state, registry, "p1", kind, position)
    _bind(state, registry)


def test_ghost_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "ghost") == []


def test_zetony_wormhole_zgodne_z_assetami(registry: StaticDataRegistry) -> None:
    """Token kinds and their wormhole types come from ``assets/data/tokens`` (one of each)."""
    tokens = registry.catalog.all(ComponentCategory.TOKEN)
    for kind, wormhole in faction_tokens.CREUSS_WORMHOLES.items():
        assert tokens[kind].wormholes == [wormhole]  # type: ignore[attr-defined]
        assert faction_tokens.SUPPLY[kind] == 1
    assert ghost.token_kinds(registry) == [ALPHA, BETA, GAMMA]


# ======================================================================== Quantum Entanglement


@ruling("abilities:quantum_entanglement#1")
def test_qe_alfa_i_beta_sasiaduja_tylko_dla_creuss(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    grid = _bind(state, registry)
    assert QUANN in board_graph.extra_adjacent_for_player(state, "p1", LODOR, grid)
    assert ALPHA_EMPTY not in board_graph.extra_adjacent_for_player(state, "p1", LODOR, grid) - {
        p for p in grid.wormhole_positions("BETA") | grid.wormhole_positions("ALPHA")
    }
    assert board_graph.extra_adjacent_for_player(state, "p2", LODOR, grid) == frozenset()
    assert shortest_legal_path(grid, state, LODOR, BETA_EMPTY, "p1",
                               can_enter_asteroids=False) == [LODOR, BETA_EMPTY]
    path = shortest_legal_path(grid, state, LODOR, BETA_EMPTY, "p2", can_enter_asteroids=False)
    assert path is None or len(path) > 2
    # The Creuss token creates the same adjacency (a real map wormhole for everybody).
    _put_token(state, registry, BETA, TARMANN)
    grid = _bind(state, registry)
    assert grid.are_adjacent(TARMANN, QUANN)
    assert TARMANN in board_graph.extra_adjacent_for_player(state, "p1", LODOR, grid)


@ruling("abilities:quantum_entanglement#2", "F_creuss/quantum-entanglement/1",
        "F_creuss/slipstream/1")
def test_prawa_wormhole_nie_dzialaja_na_creuss(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.decks.agenda_laws = {"travel_ban": "for"}
    grid = _bind(state, registry)
    assert grid.are_adjacent(LODOR, ALPHA_EMPTY) or LODOR in grid.wormhole_positions("ALPHA")
    assert not wormhole_link_blocked(grid, state, "p1", LODOR, ALPHA_EMPTY)
    assert wormhole_link_blocked(grid, state, "p2", LODOR, ALPHA_EMPTY)
    # Slipstream still applies under the ban (a move value bonus, not a wormhole link).
    state.active_system = ALPHA_EMPTY
    assert ghost.slipstream(state, "p1", {"from": LODOR}) == 1


@ruling("F_creuss/quantum-entanglement/2", "F_creuss/quantum-entanglement/2.1",
        "F_mentak/pillage/2")
def test_qe_sasiedzi_i_pillage(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="mentak")
    state.systems[LODOR].space_units = {"p1": {"destroyer": 1}}
    state.systems[BETA_EMPTY].space_units = {"p2": {"cruiser": 1}}
    grid = _bind(state, registry)
    found = neighbors.neighbors_by_player(state, grid)
    assert "p2" in found["p1"] and "p1" in found["p2"]
    reason = mentak.pillage_reason(state, "p2", "p1")
    assert reason is None or "neighbor" not in reason.lower()


@ruling("F_creuss/quantum-entanglement/3", "C_agendas/ixthian-artifact/4")
def test_ixthian_bez_sasiedztwa_qe(registry: StaticDataRegistry) -> None:
    """Ixthian Artifact uses pure map adjacency (``board_graph.adjacent_positions``)."""
    state = _state(registry)
    state.systems[MECATOL].wormhole_tokens = ["ALPHA"]
    state.systems[BETA_EMPTY].space_units = {"p1": {"destroyer": 1}}
    _bind(state, registry)
    near = board_graph.adjacent_positions(MECATOL)
    assert BETA_EMPTY not in near and ALPHA_EMPTY in near


@ruling("F_creuss/quantum-entanglement/4")
def test_deep_space_cannon_przez_qe_tylko_creuss(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies.append("pds2")
    state.players["p2"].technologies.append("pds2")
    state.systems[LODOR].space_units = {"p1": {"destroyer": 1}, "p2": {"destroyer": 1}}
    state.systems[BETA_EMPTY].planet_units = {}
    state.systems[QUANN].planet_units = {"quann": {"p2": {"pds": 1}}}
    state.systems[QUANN].planet_owners = {"quann": "p2"}
    state.active_system = LODOR
    state.tactical_step = TacticalStep.SPACE_CANNON
    grid = _bind(state, registry)
    assert not [s for s in space_cannon.offense_shooters(state, grid, registry, "p2") if s.remote]
    state.systems[QUANN].planet_units = {"quann": {"p1": {"pds": 1}}}
    state.systems[QUANN].planet_owners = {"quann": "p1"}
    assert [s for s in space_cannon.offense_shooters(state, grid, registry, "p1") if s.remote]


# ===================================================================================== Slipstream


@ruling("abilities:slipstream#1", "F_creuss/slipstream/2")
def test_slipstream_dom_i_alfa_beta(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.active_system = TARMANN
    assert ghost.slipstream(state, "p1", {"from": HOME}) == 1
    assert ghost.slipstream(state, "p1", {"from": LODOR}) == 1
    assert ghost.slipstream(state, "p1", {"from": QUANN}) == 1
    assert ghost.slipstream(state, "p1", {"from": GATE}) == 0  # Creuss Gate (delta) - not home
    assert ghost.slipstream(state, "p1", {"from": VEFUT}) == 0
    _put_token(state, registry, GAMMA, VEFUT)
    assert ghost.slipstream(state, "p1", {"from": VEFUT}) == 0  # gamma does not count
    state.systems[VEFUT].space_units = {"p1": {"flagship": 1}}
    assert ghost.slipstream(state, "p1", {"from": VEFUT}) == 0  # Hil Colish delta either
    _put_token(state, registry, ALPHA, VEFUT)
    assert ghost.slipstream(state, "p1", {"from": VEFUT}) == 1
    # The engine reads it as a move value bonus (Creuss carrier: move 1 -> 2).
    value = rules_hooks.modify(rules_hooks.POINT_MOVEMENT_MOVE_VALUE, state, "p1", 1,
                               {"from": HOME, "base_type": "carrier"})
    assert value == 2


@ruling("abilities:creuss_gate#2", "F_creuss/creuss-gate/1")
def test_brama_nie_jest_domem(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    assert not board_graph.is_home_system(state, registry, GATE)
    assert board_graph.is_home_system(state, registry, HOME)
    assert state.systems[GATE].frontier_token


# ============================================================================= Dimensional Splicer


def _combat(state: GameState, position: str, p2: dict[str, int]) -> None:
    state.systems[position].space_units = {"p1": {"cruiser": 1}, "p2": p2}
    state.active_system = position
    state.active_combat = ActiveCombat(kind="space", position=position, attacker="p1",
                                       defender="p2")


@ruling("technologies:ds#1", "F_creuss/dimensional-splicer/2", "F_creuss/dimensional-splicer/3",
        "F_creuss/dimensional-splicer/5")
def test_splicer_jedno_trafienie_w_wybrany_statek(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _put_token(state, registry, BETA, LODOR)  # Lodor: alpha (tile) + beta (token)
    _combat(state, LODOR, {"dreadnought": 1, "destroyer": 2})
    assert ghost._splicer_ready(state, "p1", {"kind": "space"})
    inputs = ghost.splicer_inputs(state, registry, "p1", {})
    assert {o["value"] for o in inputs[0]["options"]} == {"dreadnought", "destroyer"}
    assert inputs[0]["auto"] == "destroyer"  # cannot SUSTAIN DAMAGE
    ghost.dimensional_splicer(state, "p1", {"params": {"target": "dreadnought"}})
    combat = state.active_combat
    assert combat is not None and combat.start_hits == {"p2": 1}  # one hit, 2 wormholes
    target = combat.hit_targets["p2"]
    assert target["types"] == ["dreadnought"] and target["chooser"] == "p1"
    assert target["damaged"] is False


@ruling("F_creuss/dimensional-splicer/1")
def test_splicer_przez_delte_hil_colish(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _combat(state, VEFUT, {"destroyer": 1})
    assert not ghost._splicer_ready(state, "p1", {"kind": "space"})  # no wormhole
    state.systems[VEFUT].space_units["p1"]["flagship"] = 1
    assert ghost._splicer_ready(state, "p1", {"kind": "space"})
    assert not ghost._splicer_ready(state, "p1", {"kind": "ground"})


@ruling("F_winnu/lazax-gate-folding/2.4")
def test_splicer_w_mecatol_podczas_akcji_winnu(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="winnu")
    state.players["p2"].technologies = ["lgf"]
    state.active_player_id = "p2"
    state.tactical_step = TacticalStep.SPACE_COMBAT
    state.systems[MECATOL].space_units = {"p1": {"cruiser": 1}, "p2": {"destroyer": 1}}
    state.active_system = MECATOL
    state.active_combat = ActiveCombat(kind="space", position=MECATOL, attacker="p2",
                                       defender="p1")
    assert ghost._splicer_ready(state, "p1", {"kind": "space"})
    state.tactical_step = None
    assert not ghost._splicer_ready(state, "p1", {"kind": "space"})


# ============================================================================ Wormhole Generator


@ruling("technologies:wg#1", "F_creuss/wormhole-generator-omega/3",
        "F_creuss/wormhole-generator-replaced-by-omega/5")
def test_generator_legalne_systemy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[TARMANN].space_units = {"p2": {"destroyer": 1}}
    state.systems[VEFUT].space_units = {"neutral": {"destroyer": 1}}
    legal = ghost.token_systems(state, registry, "p1")
    assert HOME in legal  # home system with a planet Creuss controls
    assert JORD not in legal  # another player's home
    assert TARMANN not in legal and VEFUT not in legal  # another player's / neutral ships
    assert LODOR in legal and MECATOL in legal
    state.systems[TARMANN].planet_owners = {"tarmann": "p1"}
    assert TARMANN in ghost.token_systems(state, registry, "p1")  # a planet you control


@ruling("F_creuss/wormhole-generator-omega/1", "F_creuss/wormhole-generator-replaced-by-omega/3",
        "F_creuss/creuss-iff/4")
def test_generator_dom_wyeliminowanego(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.eliminated_players = [EliminatedPlayer(player_id="p3", faction="hacan",
                                                 home_position=ASTEROIDS)]
    assert ASTEROIDS not in ghost.token_systems(state, registry, "p1")
    state.systems[ASTEROIDS].planet_owners = {"x": "p1"}
    assert ASTEROIDS in ghost.token_systems(state, registry, "p1")


@ruling("F_creuss/wormhole-generator-omega/2", "F_creuss/wormhole-generator-replaced-by-omega/4",
        "F_creuss/creuss-iff/5")
def test_generator_w_fracture(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems["frac1"] = SystemState(position="frac1", system_id="fracture1")
    assert "frac1" in ghost.token_systems(state, registry, "p1")


@ruling("F_creuss/wormhole-generator-replaced-by-omega/2.1")
def test_generator_ten_sam_system(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _put_token(state, registry, ALPHA, VEFUT)
    note = ghost.place_or_move_token(state, registry, "p1", ALPHA, VEFUT)
    assert "stays" in note and _tokens(state) == {ALPHA: VEFUT}
    ghost.place_or_move_token(state, registry, "p1", ALPHA, TARMANN)
    assert _tokens(state) == {ALPHA: TARMANN}  # moved, not a second token


@ruling("F_creuss/wormhole-generator-omega/4", "F_creuss/wormhole-generator-replaced-by-omega/6",
        "R_entropic_scars/notes/4.2")
def test_generator_w_bliznie_entropicznej(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[VEFUT].system_id = "114"  # Entropic Scar
    _bind(state, registry)
    after = _generator(state, registry, {"token": ALPHA, "position": VEFUT})
    assert _tokens(after) == {}  # discarded - back in the Creuss reinforcements
    assert faction_tokens.supply_left(after, "p1", ALPHA) == 1
    assert "wg" in after.players["p1"].exhausted_technologies


def test_generator_akcja_wyczerpuje_i_tworzy_sasiedztwo(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    after = _generator(state, registry, {"token": ALPHA, "position": TARMANN})
    assert _tokens(after) == {ALPHA: TARMANN}
    assert "wg" in after.players["p1"].exhausted_technologies
    grid = _bind(after, registry)
    assert grid.are_adjacent(TARMANN, LODOR) and grid.are_adjacent(TARMANN, ALPHA_EMPTY)
    with pytest.raises(ValueError, match="exhausted"):
        ghost.wormhole_generator(after, registry, "p1", {"token": BETA, "position": VEFUT})


# ============================================================================ Creuss IFF (note)


def _window(pid: str) -> OpenWindow:
    return OpenWindow(GameEvent.TURN, Moment.START, {"player": pid})


@ruling("promissory_notes:iff#1", "F_creuss/creuss-iff/1.1", "F_creuss/creuss-iff/3")
def test_iff_raz_na_okno_i_bez_generatora(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies = []  # no Wormhole Generator - IFF still works
    assert ghost._iff_condition(state, registry, "p2", _window("p2")) is None
    assert ghost._iff_condition(state, registry, "p2", _window("p1")) is not None
    inputs = ghost.iff_inputs(state, registry, "p2")
    positions = {o["value"] for o in inputs[1]["options"]}
    assert JORD in positions and HOME not in positions  # "you" = the player resolving it
    ghost.creuss_iff(state, registry, "p2", {"token": BETA, "position": JORD})
    assert _tokens(state) == {BETA: JORD}
    assert ghost._iff_condition(state, registry, "p2", _window("p2")) is not None


# ============================================================================ Hil Colish (flagship)


@ruling("units:ghost_flagship#1", "F_creuss/hil-colish/2.1", "F_creuss/hil-colish/8",
        "R_entropic_scars/notes/4.3", "C_agendas/ixthian-artifact/5")
def test_hil_colish_niesie_delte(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[MECATOL].space_units = {"p1": {"flagship": 1}}
    grid = _bind(state, registry)
    assert board_graph.unit_wormholes(state) == {MECATOL: ["DELTA"]}
    assert grid.are_adjacent(MECATOL, HOME)  # (the gate also touches Mecatol on the map)
    assert {GATE, HOME} <= board_graph.adjacent_positions(MECATOL)  # Ixthian Artifact
    # The delta moves with the ship; an entropic scar does not cancel it.
    state.systems[MECATOL].space_units = {}
    state.systems[VEFUT].system_id = "114"
    state.systems[VEFUT].space_units = {"p1": {"flagship": 1}}
    grid = _bind(state, registry)
    assert not grid.are_adjacent(MECATOL, HOME)
    assert grid.are_adjacent(VEFUT, GATE) and "DELTA" in board_graph.wormholes_at(
        state, registry, VEFUT)


@ruling("F_creuss/hil-colish/7")
def test_bez_hil_colish_bez_delty(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[VEFUT].space_units = {"p1": {"flagship": 1}}
    state.systems[VEFUT].space_units = {"p1": {}}  # returned to reinforcements (gravity rift)
    grid = _bind(state, registry)
    assert board_graph.unit_wormholes(state) == {}
    assert not grid.are_adjacent(VEFUT, GATE)


def _move(state: GameState, registry: StaticDataRegistry, source: str,
          ships: dict[str, int]) -> GameState:
    grid = _bind(state, registry)
    after = movement.move_fleet(state, grid, registry, source, ships, [], "p1")
    _bind(after, registry)
    return after


@ruling("F_creuss/hil-colish/1", "units:ghost_flagship#2", "F_creuss/hil-colish/3")
def test_hil_colish_pierwszy_otwiera_delte_w_celu(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[GATE].space_units = {"p1": {"carrier": 1}}  # move 1, no Slipstream at the gate
    state.systems[VEFUT].space_units = {"p1": {"flagship": 1}}
    state.active_system = QUANN
    state.tactical_step = TacticalStep.MOVEMENT
    with pytest.raises(ValueError):
        _move(state, registry, GATE, {"carrier": 1})  # gate -> Quann: 2 hops, no link yet
    after = _move(state, registry, VEFUT, {"flagship": 1})  # Hil Colish moves first
    after = _move(after, registry, GATE, {"carrier": 1})  # delta -> delta
    assert after.systems[QUANN].space_units["p1"] == {"flagship": 1, "carrier": 1}
    # Both fleet moves happen inside ONE Movement step: one Space Cannon Offense step follows.
    assert after.tactical_step is TacticalStep.MOVEMENT


@ruling("F_creuss/hil-colish/2")
def test_hil_colish_ostatni_reszta_przez_delte_startu(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[VEFUT].space_units = {"p1": {"flagship": 1}}
    state.active_system = VEFUT
    state.tactical_step = TacticalStep.MOVEMENT
    after = _move(state, registry, HOME, {"destroyer": 2})  # through the delta in Vefut II
    assert after.systems[VEFUT].space_units["p1"]["destroyer"] == 2


@ruling("F_creuss/hil-colish/4")
def test_light_wave_deflector_przez_delte(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p2"].technologies = ["lwd"]
    state.systems["204"] = SystemState(position="204", system_id="19",
                                       space_units={"p1": {"flagship": 1}})
    state.systems["205"] = SystemState(position="205", system_id="20",
                                       space_units={"p2": {"cruiser": 1}})
    state.active_player_id = "p2"
    grid = _bind(state, registry)
    path = shortest_legal_path(grid, state, "205", GATE, "p2", can_enter_asteroids=False)
    assert path == ["205", "204", GATE]  # through the Creuss ships and their delta


@ruling("F_creuss/hil-colish/5")
def test_odwrot_do_innej_delty(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[VEFUT].space_units = {"p1": {"flagship": 1}, "p2": {"destroyer": 1}}
    grid = _bind(state, registry)
    assert HOME in retreat.retreat_destinations(state, grid, VEFUT, "p1")


@ruling("F_creuss/hil-colish/5.1")
def test_odwrot_po_zniszczeniu_hil_colish(registry: StaticDataRegistry) -> None:
    """Destinations are computed at the Retreat step: without the flagship its delta is gone."""
    state = _state(registry)
    state.systems[VEFUT].space_units = {"p1": {"flagship": 1, "destroyer": 1},
                                        "p2": {"destroyer": 1}}
    _bind(state, registry)
    state.systems[VEFUT].space_units["p1"] = {"destroyer": 1}  # destroyed before Retreat
    grid = _bind(state, registry)
    assert HOME not in retreat.retreat_destinations(state, grid, VEFUT, "p1")


@ruling("F_creuss/emissary-taivra/4")
def test_taivra_nie_obraca_ion_storm(registry: StaticDataRegistry) -> None:
    from src.core import ion_storm

    state = _state(registry)
    state.systems[VEFUT].ion_storm = "BETA"
    state.active_player_id, state.active_system = "p2", GATE
    state.tactical_step = TacticalStep.MOVEMENT
    grid = _bind(state, registry)
    ghost.emissary_taivra(state, "p1", {"position": GATE})
    assert VEFUT in action_adjacency.neighbors(state, grid, GATE)  # linked by Taivra
    assert ion_storm.uses_ion_storm(state, grid, registry, VEFUT, GATE) is None  # no flip


@ruling("F_creuss/hil-colish/9")
def test_delta_daje_zasieg_deep_space_cannon(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies.append("pds2")
    state.systems[HOME].planet_units = {"creuss": {"p1": {"pds": 1}}}
    state.systems[VEFUT].space_units = {"p1": {"flagship": 1}, "p2": {"destroyer": 1}}
    state.active_system = VEFUT
    state.tactical_step = TacticalStep.SPACE_CANNON
    grid = _bind(state, registry)
    assert [s for s in space_cannon.offense_shooters(state, grid, registry, "p1") if s.remote]


@ruling("C_exploration_cards/ion-storm/2.1")
def test_ion_storm_obraca_sie_po_ruchu_hil_colish(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[TARMANN].ion_storm = "ALPHA"
    state.systems[LODOR].space_units = {"p1": {"flagship": 1}}
    state.active_system = TARMANN
    state.tactical_step = TacticalStep.MOVEMENT
    after = _move(state, registry, LODOR, {"flagship": 1})  # through the alpha side
    assert after.systems[TARMANN].ion_storm == "BETA"  # flipped right after the flagship moves
    after.systems[QUANN].space_units = {"p1": {"destroyer": 1}}
    after = _move(after, registry, QUANN, {"destroyer": 1})  # now through the beta side
    assert after.systems[TARMANN].space_units["p1"]["destroyer"] == 1


# ============================================================================ Icarus Drive (mech)


@ruling("units:ghost_mech#1", "F_creuss/icarus-drive/1", "F_creuss/icarus-drive/2")
def test_icarus_drive_zeton_w_systemie_mecha(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[VEFUT].planet_units = {"vefutii": {"p1": {"mech": 1}}}
    assert ghost._icarus_ready(state, "p1", {"position": JORD, "player": "p2"})
    inputs = ghost.icarus_inputs(state, registry, "p1", {})
    mech = inputs[0]["options"][0]["value"]
    assert inputs[0]["options"][0]["meta"]["position"] == VEFUT
    ghost.icarus_drive(state, "p1", {"params": {"mech": mech, "token": GAMMA}})
    assert _tokens(state) == {GAMMA: VEFUT}  # the mech's system, not the active one
    assert "p1" not in state.systems[VEFUT].planet_units.get("vefutii", {})


@ruling("F_saar/chaos-mapping/7")
def test_zeton_w_polu_asteroid_saar_bez_aktywacji(registry: StaticDataRegistry) -> None:
    from src.core import tactical

    state = _state(registry, other="saar")
    state.players["p2"].technologies = ["cm"]
    state.systems[ASTEROIDS].space_units = {"p2": {"carrier": 1}, "p1": {"mech": 1}}
    mech = ghost.icarus_inputs(state, registry, "p1", {})[0]["options"][0]["value"]
    ghost.icarus_drive(state, "p1", {"params": {"mech": mech, "token": ALPHA}})
    assert _tokens(state) == {ALPHA: ASTEROIDS}
    grid = _bind(state, registry)
    with pytest.raises(ValueError):
        tactical.activate_system(state, grid, ASTEROIDS)


# ======================================================================== Emissary Taivra (agent)


@ruling("leaders:ghostagent#1", "F_creuss/emissary-taivra/2", "F_creuss/emissary-taivra/5",
        "F_creuss/emissary-taivra/5.1")
def test_taivra_tylko_przy_nie_delcie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    assert ghost._taivra_ready(state, "p1", {"position": LODOR})
    assert not ghost._taivra_ready(state, "p1", {"position": GATE})  # delta only
    assert not ghost._taivra_ready(state, "p1", {"position": TARMANN})
    _put_token(state, registry, BETA, TARMANN)  # e.g. Creuss IFF at the start of the turn
    assert ghost._taivra_ready(state, "p1", {"position": TARMANN})
    state.systems[GATE].wormhole_tokens = ["GAMMA"]
    assert ghost._taivra_ready(state, "p1", {"position": GATE})  # delta + non-delta


@ruling("leaders:ghostagent#2", "F_creuss/emissary-taivra/1", "F_creuss/emissary-taivra/3")
def test_taivra_laczy_wszystkie_wormhole(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems["301"] = SystemState(position="301", system_id="82a")  # inactive Nexus (gamma)
    state.active_player_id = "p2"
    state.active_system = VEFUT
    state.tactical_step = TacticalStep.MOVEMENT
    _put_token(state, registry, BETA, VEFUT)
    grid = _bind(state, registry)
    ghost.emissary_taivra(state, "p1", {"position": VEFUT})
    assert state.players["p1"].leader_states["ghostagent"] == "exhausted"
    near = action_adjacency.neighbors(state, grid, VEFUT)
    assert {GATE, HOME, ALPHA_EMPTY, "301"} <= near  # delta, alpha, the inactive Nexus
    assert VEFUT in action_adjacency.neighbors(state, grid, GATE)
    state.tactical_step = None
    assert GATE not in action_adjacency.neighbors(state, grid, VEFUT)


# ======================================================================= Sai Seravus (commander)


@ruling("leaders:ghostcommander#unlock", "F_creuss/sai-seravus/4")
def test_seravus_odblokowanie_z_zetonami(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[LODOR].space_units = {"p1": {"destroyer": 1}}
    state.systems[QUANN].space_units = {"p1": {"destroyer": 1}}
    state.systems[TARMANN].space_units = {"p1": {"destroyer": 1}}
    unlock = leaders.unlock_predicate(registry, "ghostcommander")
    assert unlock is not None and not unlock(state, registry, "p1")
    _put_token(state, registry, ALPHA, TARMANN)
    assert unlock(state, registry, "p1")


def _moved(route: list[str], ships: dict[str, int], kind: str = "tactical") -> dict[str, Any]:
    return {"player": "p1", "position": route[-1], "from": route[0], "ships": ships,
            "route": route, "kind": kind}


@ruling("leaders:ghostcommander#1", "F_creuss/sai-seravus/1", "F_creuss/sai-seravus/1.1",
        "F_creuss/sai-seravus/3")
def test_seravus_mysliwce_po_przejsciu_wormhole(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[QUANN].space_units = {"p1": {"carrier": 2, "destroyer": 1, "infantry": 5}}
    ctx = _moved([LODOR, QUANN], {"carrier": 2, "destroyer": 1})  # Quantum Entanglement hop
    # 2 carriers (capacity 4 each = 8) hold 5 infantry: room for 3, but only 2 ships qualify.
    assert ghost.seravus_limit(state, "p1", ctx) == 2
    state.systems[QUANN].space_units["p1"]["infantry"] = 7
    assert ghost.seravus_limit(state, "p1", ctx) == 1  # no ground force removed for room
    geometric = _moved([VEFUT, QUANN], {"carrier": 2})
    assert ghost.seravus_limit(state, "p1", geometric) == 0  # no wormhole used
    ghost.sai_seravus(state, "p1", {**ctx, "params": {"fighters": 1}})
    assert state.systems[QUANN].space_units["p1"]["fighter"] == 1
    assert ghost.seravus_inputs(state, registry, "p1", ctx)[0]["auto"] == 0


@ruling("F_creuss/sai-seravus/1.2", "F_creuss/sai-seravus/2", "F_creuss/sai-seravus/2.1")
def test_seravus_dok_i_kazdy_ruch(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[LODOR].space_units = {"p1": {"destroyer": 1}}
    ctx = _moved([QUANN, LODOR], {"destroyer": 1}, kind="retreat")
    assert ghost.seravus_limit(state, "p1", ctx) == 0  # no capacity after a retreat
    state.systems[LODOR].space_units = {"p1": {"carrier": 1, "infantry": 4}}
    carrier = _moved([QUANN, LODOR], {"carrier": 1}, kind="retreat")
    assert ghost.seravus_limit(state, "p1", carrier) == 0  # full
    state.systems[LODOR].planet_owners = {"lodor": "p1"}
    state.systems[LODOR].planet_units = {"lodor": {"p1": {"spacedock": 1}}}
    assert ghost.seravus_limit(state, "p1", carrier) == 1  # dock holds fighters


# ============================================= Riftwalker Meian — Singularity Reactor (hero)


@ruling("leaders:ghosthero#1", "F_creuss/riftwalker-meian-singularity-reactor/3")
def test_bohater_kandydaci(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems["301"] = SystemState(position="301", system_id="82b")
    state.systems["302"] = SystemState(position="302", system_id="118")
    state.systems["frac1"] = SystemState(position="frac1", system_id="fracture1",
                                         wormhole_tokens=["GAMMA"])
    found = ghost.swap_candidates(state, registry, "p1")
    assert LODOR in found and QUANN in found and GATE in found
    assert HOME not in found and "301" not in found and "302" not in found
    assert "frac1" not in found and VEFUT not in found  # no wormhole, no Creuss units


@ruling("leaders:ghosthero#2", "F_creuss/riftwalker-meian-singularity-reactor/1",
        "F_creuss/riftwalker-meian-singularity-reactor/2", "leaders:ghosthero#unlock")
def test_bohater_zamienia_systemy_z_jednostkami(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states["ghosthero"] = "unlocked"
    state.systems[LODOR].space_units = {"p1": {"destroyer": 1}}
    state.systems[LODOR].command_tokens = ["p2"]
    _put_token(state, registry, GAMMA, LODOR)
    state.systems[JORD].space_units = {"p2": {"carrier": 1}}
    state.systems[JORD].wormhole_tokens = ["GAMMA"]
    after = _play(state, registry, "leader", "ghosthero", {"first": LODOR, "second": JORD})
    assert after.systems[JORD].system_id == "26" and after.systems[LODOR].system_id == "01"
    assert after.systems[JORD].space_units == {"p1": {"destroyer": 1}}
    assert after.systems[JORD].command_tokens == ["p2"]
    assert _tokens(after) == {GAMMA: JORD}
    assert after.systems[LODOR].planet_owners == {"jord": "p2"}
    assert after.players["p2"].home_position == LODOR  # the home tile moved
    assert after.replaced_tiles == {LODOR: "01", JORD: "26"}
    assert after.players["p1"].leader_states["ghosthero"] == "purged"
    grid = _bind(after, registry)
    assert grid.system_id_at(LODOR) == "01" and grid.system_id_at(JORD) == "26"
    # The unlock condition is the generic "3 scored objectives" predicate.
    assert leaders.unlock_predicate(registry, "ghosthero") is not None


def test_swap_bledy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    with pytest.raises(ValueError):
        system_swap.swap_systems(state, LODOR, LODOR)


# ================================================================ Particle Synthesis (breakthrough)


@ruling("breakthroughs:ghostbt#1", "F_creuss/particle-synthesis/1",
        "F_creuss/particle-synthesis/2")
def test_particle_synthesis_produkcja(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    state.systems[LODOR].space_units = {"p1": {"destroyer": 1}}
    _put_token(state, registry, ALPHA, LODOR)  # alpha (tile) + alpha (token): 2 x PRODUCTION 1
    ctx = {"position": LODOR}
    assert ghost.particle_synthesis_production(state, "p1", ctx) == 2
    state.systems[LODOR].space_units["p1"]["flagship"] = 1
    assert ghost.particle_synthesis_production(state, "p1", ctx) == 3  # + Hil Colish delta
    assert ghost.particle_synthesis_production(state, "p1", {"position": VEFUT}) == 0
    state.systems[QUANN].planet_units = {"quann": {"p1": {"infantry": 1}}}
    assert ghost.particle_synthesis_production(state, "p1", {"position": QUANN}) == 0  # no ships


@ruling("breakthroughs:ghostbt#2", "F_creuss/particle-synthesis/3")
def test_particle_synthesis_znizka_i_sarween(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    state.players["p1"].technologies.append("st")
    state.systems[LODOR].space_units = {"p1": {"destroyer": 1}}
    _put_token(state, registry, BETA, LODOR)
    state.active_system = LODOR
    state.tactical_step = TacticalStep.PRODUCTION
    cost = production.order_cost(state, registry, "p1", [ProductionOrder("cruiser", 2)])
    assert cost == 4 - 2 - 1  # 2 wormholes + Sarween Tools
    state.active_system = VEFUT
    assert production.order_cost(state, registry, "p1", [ProductionOrder("cruiser", 2)]) == 3


@ruling("F_creuss/particle-synthesis/4")
def test_particle_synthesis_producent_w_przestrzeni(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].breakthrough_unlocked = True
    state.systems[LODOR].space_units = {"p1": {"destroyer": 1}}
    state.systems[LODOR].planet_owners = {"lodor": "p1"}
    state.active_system = LODOR
    found = production.producers(state, registry, "p1", LODOR)
    space = [p for p in found if p.zone == "space"]
    assert space and space[0].value == 1


def test_taivra_effect_wygasa_z_akcja(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    ghost.emissary_taivra(state, "p1", {"position": LODOR})
    effects = [e for e in state.active_effects if e.key == ghost.TAIVRA_LINK]
    assert effects and effects[0].scope == Duration.TACTICAL_ACTION.value
    assert effects[0].owner is None  # valid for every player in this action
