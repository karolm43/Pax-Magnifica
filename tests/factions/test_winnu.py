"""The Winnu — komplet komponentów frakcji (RULES.md 62.7), konwencja par."""

from __future__ import annotations

from collections.abc import Iterator

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
