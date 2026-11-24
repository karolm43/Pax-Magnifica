"""Testy kart frontier: Enigmatic Device (ręka), Ion Storm (wormhole) i Mirage (planeta)."""

from __future__ import annotations

import pytest

from src.core import (
    exploration,
    frontier_cards,
    ion_storm,
    planet_stats,
    technology,
    triggers,
)
from src.core.components import ComponentCategory, ExplorationDef
from src.core.game_state import (
    ExplorationState,
    ExploreCurrent,
    GameState,
    Phase,
    PlayerState,
    SystemState,
)
from src.core.hex_grid import Hex, HexGrid
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    from src.core import rules_hooks

    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _card_id(registry: StaticDataRegistry, card_id: str) -> str:
    card = registry.catalog.get(ComponentCategory.EXPLORATION, card_id)
    assert isinstance(card, ExplorationDef)
    return card_id


def _state(registry: StaticDataRegistry, card_id: str) -> GameState:
    """p1 aktywny w fazie akcji, z ujawnioną kartą frontier ``card_id`` w systemie 000."""
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red"),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems={"000": SystemState(position="000", system_id="18")},
        rng_seed=3,
    )
    exploration.seed_deck(state, registry, "frontier")
    state.decks.exploration_deck["frontier"].remove(_card_id(registry, card_id))
    state.exploration = ExplorationState(
        player_id="p1",
        position="000",
        current=ExploreCurrent(planet="", deck="frontier", card_id=card_id),
    )
    return state


# ------------------------------------------------------------------ Enigmatic Device


def test_enigmatic_device_goes_to_hand_not_to_discard(registry: StaticDataRegistry) -> None:
    state = _state(registry, "ed1")
    options = exploration.options_for(state, registry)
    assert [o.id for o in options] == ["keep"]
    done = exploration.resolve(state, registry, "keep")
    assert done.players["p1"].frontier_cards == ["ed1"]
    assert "ed1" not in done.decks.exploration_discard.get("frontier", [])
    assert done.exploration is not None and done.exploration.log[-1]["fate"] == "kept"


def _with_device(registry: StaticDataRegistry, resources: int) -> GameState:
    state = _state(registry, "ed1")
    state = exploration.resolve(state, registry, "keep")
    state.exploration = None
    player = state.players["p1"]
    player.trade_goods = resources
    return state


def test_enigmatic_device_researches_a_technology_for_six_resources(
    registry: StaticDataRegistry,
) -> None:
    state = _with_device(registry, 6)
    rows = frontier_cards.playability(state, registry, "p1")
    assert rows[0]["relic_id"] == "ed1" and rows[0]["playable"] is True
    form = frontier_cards.form(state, registry, "p1", "ed1")
    tech_id = form["inputs"][0]["options"][0]["id"]
    assert form["inputs"][0]["kind"] == "info"
    played, implemented = frontier_cards.play_frontier_card(state, registry, "p1", "ed1", {})
    # Karta zużyta; technologię i zapłatę wybiera się w oknie badania (decyzja gracza).
    assert "ed1" in played.decks.purged
    offer = next(o for o in played.pending_offers if "research_cost" in o.ctx)
    payload = {"tech": tech_id, "skips": [], "planets": [], "trade_goods": 6}
    new_state = triggers.accept_offer(played, "p1", offer.id, {"research": payload})
    player = new_state.players["p1"]
    assert implemented and tech_id in player.technologies
    assert player.trade_goods == 0
    assert "ed1" not in player.frontier_cards and "ed1" in new_state.decks.purged
    assert player.took_action_this_turn
    assert technology  # moduł badań użyty przez efekt


@ruling("C_exploration_cards/enigmatic-device/1")
def test_enigmatic_device_needs_six_resources(registry: StaticDataRegistry) -> None:
    state = _with_device(registry, 5)
    row = frontier_cards.playability(state, registry, "p1")[0]
    assert row["playable"] is False and "needs 6 resources" in str(row["reason"])
    with pytest.raises(ValueError, match="needs 6 resources"):
        frontier_cards.play_frontier_card(
            state, registry, "p1", "ed1", {"technology": "ps", "trade_goods": 5}
        )
    assert state.players["p1"].frontier_cards == ["ed1"]  # nic się nie zużyło


def test_enigmatic_device_cannot_be_played_without_owning_it(
    registry: StaticDataRegistry,
) -> None:
    state = _with_device(registry, 6)
    with pytest.raises(ValueError, match="do not have"):
        frontier_cards.form(state, registry, "p2", "ed1")


# ------------------------------------------------------------------ Ion Storm


@ruling("C_exploration_cards/ion-storm/1", "R_exploration/notes/5")
def test_ion_storm_is_placed_with_chosen_side_and_stays_in_common_area(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, "ion")
    option = exploration.options_for(state, registry)[0]
    assert option.id == "place" and {p for p, _ in option.params} == {"ALPHA", "BETA"}
    with pytest.raises(ValueError, match="Choose a value"):
        exploration.resolve(state, registry, "place")
    done = exploration.resolve(state, registry, "place", "BETA")
    assert done.systems["000"].ion_storm == "BETA"
    assert done.systems["000"].token_wormholes() == ["BETA"]
    assert "ion" in done.decks.common_play_area and "ion" not in done.decks.purged


def _wormhole_systems(registry: StaticDataRegistry) -> tuple[str, str]:
    alpha = [s.id for s in registry.systems.values() if "ALPHA" in [w.upper() for w in s.wormholes]]
    assert len(alpha) >= 2
    return alpha[0], alpha[1]


@ruling("C_exploration_cards/ion-storm/2")
def test_ion_storm_flips_after_ships_use_its_wormhole(registry: StaticDataRegistry) -> None:
    sys_a, sys_b = _wormhole_systems(registry)
    grid = HexGrid()
    grid.place_system("a", sys_a, wormholes=["ALPHA"], hex_override=Hex(0, 0, 0))
    grid.place_system("b", sys_b, wormholes=["ALPHA"], hex_override=Hex(3, -3, 0))  # niesąsiadujące
    grid.build_edges()
    state = GameState(
        phase=Phase.ACTION,
        players={"p1": PlayerState(player_id="p1", color="red")},
        systems={
            # Kafelek "a" ma własny wormhole alpha: gracz wybiera żeton (C_exploration_cards).
            "a": SystemState(position="a", system_id=sys_a, ion_storm="ALPHA"),
            "b": SystemState(position="b", system_id=sys_b),
        },
    )
    # Z aktywną stroną ALPHA żeton łączy "a" z "b" przez wormhole (nie sąsiedztwem).
    assert grid.link_kind("a", "b") == "wormhole"
    ion_storm.note_move(state, grid, registry, "b", "a", use_token=True)
    assert state.ion_storm_used == ["a"]
    assert ion_storm.flip_used(state) == ["a"]
    assert state.systems["a"].ion_storm == "BETA" and state.ion_storm_used == []
    # Beta nie łączy już z systemem alpha: ruch nie użyje żetonu.
    assert ion_storm.uses_ion_storm(state, grid, registry, "b", "a") is None


def test_second_ion_storm_is_refused(registry: StaticDataRegistry) -> None:
    state = _state(registry, "ion")
    state.systems["other"] = SystemState(position="other", system_id="19", ion_storm="ALPHA")
    with pytest.raises(ValueError, match="already on the board"):
        exploration.resolve(state, registry, "place", "ALPHA")


# ------------------------------------------------------------------ Mirage


def test_mirage_is_placed_gained_and_ready(registry: StaticDataRegistry) -> None:
    state = _state(registry, "mirage")
    done = exploration.resolve(state, registry, "place")
    system = done.systems["000"]
    assert "mirage" in system.added_planets and system.planet_owners["mirage"] == "p1"
    assert "mirage" in done.players["p1"].controlled_planets
    assert "mirage" not in done.players["p1"].exhausted_planets
    assert "mirage" in done.decks.purged
    stats = planet_stats.planet_stats(done, registry, "mirage")
    assert stats is not None and stats.resources == 1 and stats.influence == 2
    # R_exploration: gracz, który przejmuje niczyją planetę, ją eksploruje (Mirage = cultural).
    assert done.exploration is not None
    current = done.exploration.current
    assert current is not None and current.planet == "mirage" and current.deck == "cultural"


def test_derelict_vessel_lists_secret_objectives_by_full_name(
    registry: StaticDataRegistry,
) -> None:
    """Wybór celu do oddania pokazuje pełne nazwy z danych, nie surowe id."""
    state = _state(registry, "dv1")
    state.decks.secret_objective_deck = ["a"]
    state.players["p1"].private.secret_objectives = ["btv", "dts", "sar"]
    option = exploration.options_for(state, registry)[0]
    labels = dict(option.params)
    assert labels["btv"] == "Brave the Void" and labels["dts"] == "Darken the Skies"
