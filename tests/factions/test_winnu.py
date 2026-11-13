"""The Winnu — komplet komponentów frakcji (RULES.md 62.7), konwencja par."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from src.core import board_graph, custodians, planet_stats, rules_hooks
from src.core.game_state import ActiveCombat, GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import winnu
from src.core.registry import StaticDataRegistry
from tests.factions.completeness import missing_components


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _grid() -> Iterator[HexGrid]:
    """000 = Mecatol, 301 = system z wormhole alfa (tile 26), daleko od 000."""
    grid = HexGrid()
    grid.place_system("000", "18")
    grid.place_system("301", "26", wormholes=["alpha"])
    grid.place_system("101", "20")
    grid.build_edges()
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield grid
    board_graph.bind_grid_provider(previous)


def _state(faction: str = "winnu") -> GameState:
    p1 = PlayerState(player_id="p1", color="green", faction=faction, home_position="101")
    p2 = PlayerState(player_id="p2", color="blue", faction="sol")
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            "301": SystemState(position="301", system_id="26"),
            "101": SystemState(position="101", system_id="20"),
        },
    )


def test_kompletnosc_winnu(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "winnu") == []


def test_blood_ties_custodians_bez_wplywu(registry: StaticDataRegistry) -> None:
    assert custodians.removal_cost(_state(), "p1") == 0
    assert custodians.removal_cost(_state("sol"), "p1") == custodians.INFLUENCE_COST


def test_lazax_gate_folding_mecatol_jak_wormhole(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["lgf"]
    assert "301" in winnu.lazax_gate_folding(state, "p1", {"position": "000"})
    assert winnu.lazax_gate_folding(state, "p1", {"position": "301"}) == {"000"}
    state.systems["000"].planet_owners = {"mr": "p1"}  # kontrola Mecatol wyłącza efekt
    assert winnu.lazax_gate_folding(state, "p1", {"position": "000"}) == set()


def test_lazax_gate_folding_dla_wszystkich_w_akcji_winnu(
    registry: StaticDataRegistry, _grid: HexGrid
) -> None:
    """F_winnu: w akcji taktycznej Winnu Mecatol sąsiaduje z 301 także dla innych graczy
    (sąsiedztwo graczy, odwrót); poza akcją — nie."""
    from src.core import neighbors, retreat
    from src.core.game_state import TacticalStep

    state = _state()
    state.players["p1"].technologies = ["lgf"]
    state.systems["000"].space_units = {"p1": {"carrier": 1}, "p2": {"cruiser": 1}}
    state.systems["301"].space_units = {"p2": {"destroyer": 1}}
    assert retreat.retreat_destinations(state, _grid, "000", "p2") == []
    state.systems["301"].space_units = {}
    state.systems["301"].planet_owners = {}
    state.systems["000"].space_units = {"p2": {"cruiser": 1}}
    state.systems["301"].space_units = {"p1": {"carrier": 1}}
    assert neighbors.neighbors_of("p1", state, _grid) == set()  # bez akcji taktycznej
    state.tactical_step = TacticalStep.MOVEMENT
    assert neighbors.neighbors_of("p1", state, _grid) == {"p2"}
    state.systems["000"].space_units = {"p1": {"carrier": 1}, "p2": {"cruiser": 1}}
    state.systems["301"].space_units = {"p2": {"destroyer": 1}}
    assert retreat.retreat_destinations(state, _grid, "000", "p2") == ["301"]


def _reclamation_values(
    state: GameState, registry: StaticDataRegistry, ctx: Mapping[str, Any]
) -> list[object]:
    return [o["value"] for o in winnu.reclamation_inputs(state, registry, "p1", ctx)[0]["options"]]


def test_reclamation_pusta_rezerwa_bierze_dok_z_planszy(registry: StaticDataRegistry) -> None:
    """F_winnu / R_component_limitations: bez doków w rezerwie dok zdejmuje się z systemu bez
    własnego żetonu dowodzenia i stawia na Mecatol Rex."""
    from src.core import production

    state = _state()
    home = registry.systems["20"].planets[0]
    state.systems["000"].planet_owners = {"mr": "p1"}
    state.systems["101"].planet_owners = {home: "p1"}
    cap = production.reinforcements_left(state, "p1", "spacedock")
    assert cap is not None
    state.systems["101"].planet_units = {home: {"p1": {"spacedock": cap}}}
    ctx = {"player": "p1", "gained": ["mr"]}
    values = _reclamation_values(state, registry, ctx)
    assert f"spacedock<{home}" in values and f"pds+spacedock<{home}" in values
    winnu.reclamation(state, "p1", {**ctx, "params": {"place": f"pds+spacedock<{home}"}})
    assert state.systems["000"].planet_units["mr"]["p1"] == {"pds": 1, "spacedock": 1}
    assert state.systems["101"].planet_units[home]["p1"]["spacedock"] == cap - 1
    state.systems["101"].command_tokens = ["p1"]  # system z własnym żetonem — nie wolno
    state.systems["000"].planet_units["mr"]["p1"] = {}
    state.systems["101"].planet_units[home]["p1"]["spacedock"] = cap
    values = _reclamation_values(state, registry, ctx)
    assert values == ["pds"]


def test_hegemonic_trade_policy_zamienia_wartosci(registry: StaticDataRegistry) -> None:
    state = _state()
    planet = registry.systems["20"].planets[0]
    state.systems["101"].planet_owners = {planet: "p1"}
    before = planet_stats.planet_stats(state, registry, planet)
    assert before is not None
    from src.core import active_effects
    from src.core.game_events import Duration

    active_effects.add_effect(
        state, winnu.HTP_SWAP, Duration.TURN, owner="p1", data={"planet": planet}
    )
    after = planet_stats.planet_stats(state, registry, planet)
    assert after is not None
    assert (after.resources, after.influence) == (before.influence, before.resources)


def _combat(state: GameState, position: str) -> None:
    state.active_combat = ActiveCombat(
        kind="space", position=position, planet=None, attacker="p1", defender="p2"
    )


def test_salai_sai_corian_kosci_wg_statkow_przeciwnika(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["101"].space_units = {"p1": {"flagship": 1}, "p2": {"cruiser": 3, "fighter": 4}}
    _combat(state, "101")
    base = registry.units[winnu.FLAGSHIP].combat_die_count or 1
    ctx = {"base_type": "flagship", "kind": "space"}
    assert winnu.salai_sai_corian(state, "p1", ctx) == 3 - base
    state.systems["101"].space_units["p2"] = {"fighter": 4}
    assert winnu.salai_sai_corian(state, "p1", ctx) == -base  # same myśliwce: 0 kości


def test_rickar_rickani_w_domu_i_na_mecatol(registry: StaticDataRegistry) -> None:
    state = _state()
    assert winnu.rickar_rickani(state, "p1", {"position": "000"}) == 2
    assert winnu.rickar_rickani(state, "p1", {"position": "101"}) == 2
    assert winnu.rickar_rickani(state, "p1", {"position": "301"}) == 0


def test_imperator_za_support_for_the_throne(registry: StaticDataRegistry) -> None:
    state = _state()
    _combat(state, "101")
    assert winnu.imperator_combat(state, "p1", {}) == 0
    state.players["p2"].promissory_notes_in_play = ["green_sftt"]
    assert winnu.imperator_combat(state, "p1", {}) == 1


def test_imperator_i_gravity_drive_na_rozne_statki(registry: StaticDataRegistry) -> None:
    """Decyzja użytkownika (RULES.md 62.7): premia Imperatora to osobny kanał — z Gravity Drive
    dwa różne statki dostają po +1 w tej samej akcji (albo jeden oba)."""
    from src.core import movement, movement_route

    grid = HexGrid()
    for pos, sid in [("000", "65"), ("101", "20"), ("102", "22"), ("103", "23"),
                     ("104", "24"), ("105", "25"), ("106", "26"), ("201", "21")]:
        grid.place_system(pos, sid, anomalies=set())
    grid.build_edges()
    assert not grid.are_adjacent("201", "000")
    player = PlayerState(
        player_id="p1", color="green", faction="winnu", technologies=["gd"],
        breakthrough_unlocked=True,
    )
    state = GameState(
        phase=Phase.ACTION, active_player_id="p1", active_system="000",
        players={"p1": player},
        systems={
            "000": SystemState(position="000", system_id="65"),  # Primor (legendarna)
            "201": SystemState(position="201", system_id="21", space_units={"p1": {"carrier": 2}}),
        },
    )
    bonuses = movement_route.available_bonuses(state, grid, registry, "201", "p1")
    assert bonuses == ["gravity_drive", "imperator"]
    moved = movement.move_fleet(
        state, grid, registry, "201", {"carrier": 1}, {}, "p1",
        gravity_drive=True, imperator=True,
    )
    assert moved.gravity_drive_used and not moved.imperator_used  # wystarczyła jedna premia
    again = movement.move_fleet(
        moved, grid, registry, "201", {"carrier": 1}, {}, "p1",
        gravity_drive=True, imperator=True,
    )
    assert again.imperator_used
    assert again.systems["000"].space_units["p1"] == {"carrier": 2}
