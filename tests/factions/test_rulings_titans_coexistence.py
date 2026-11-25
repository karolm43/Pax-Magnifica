"""The Titans of Ul — Slumberstate Computing coexistence (block I4, RULES.md 40.1 I7b / 62.18).

Board helpers come from ``test_titans.py`` (102 = Wellon arena, 103 = New Albion, 104 = Thibah).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.core import board_graph, coexistence, rules_hooks, status_phase, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, InvasionState
from src.core.hooks.factions import titans
from src.core.invasion import _contested
from src.core.registry import StaticDataRegistry
from tests.factions.test_titans import (
    ALBION,
    EAST,
    _activate,
    _offers,
    _own,
    _sleeper,
    _state,
    _units,
)
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(None)
    yield
    board_graph.bind_grid_provider(previous)


def _awaken_on_rival(
    registry: StaticDataRegistry, params: dict[str, str], *, breakthrough: bool = True
) -> tuple[GameState, dict[str, str]]:
    """p2 controls New Albion with infantry; the Titans (p1) awaken their sleeper there."""
    state = _state()
    state.players["p1"].breakthrough_unlocked = breakthrough
    _own(state, EAST, ALBION, pid="p2", units={"infantry": 1})
    _sleeper(state, EAST, ALBION)
    activated = _activate(state, registry, EAST)
    offer = _offers(activated, "p1", "Awaken")[0]
    fields = {
        i["key"]: i for i in titans.awaken_inputs(activated, registry, "p1", offer.ctx)
    }
    after = triggers.accept_offer(activated, "p1", offer.id, params)
    return after, {k: str(v.get("auto")) for k, v in fields.items()}


def _fights(state: GameState, registry: StaticDataRegistry,
            committed: dict[str, dict[str, int]] | None = None) -> list[str]:
    state.invasion = InvasionState(position=EAST, attacker="p1", committed=committed or {})
    return _contested(state, registry, EAST, "p1")


@ruling(
    "breakthroughs:titansbt#1", "R_coexistence/notes/1", "R_coexistence/notes/2",
    "R_coexistence/notes/2.1",
)
def test_slumberstate_coexist_instead_of_coalescence_combat(
    registry: StaticDataRegistry,
) -> None:
    coexist, autos = _awaken_on_rival(
        registry, {f"sleeper:{ALBION}": "pds", f"coexist:{ALBION}": "coexist"}
    )
    assert autos[f"coexist:{ALBION}"] == "coexist"  # choice + "Auto" (ASSUMPTION 62.18)
    assert _units(coexist, EAST, ALBION) == {"pds": 1}
    assert coexist.systems[EAST].planet_owners[ALBION] == "p2"  # controller keeps the planet
    assert coexistence.coexisting_players(coexist, EAST, ALBION) == ["p1"]
    assert coexistence.peaceful(coexist, EAST, ALBION) == {"p1"}
    assert _fights(coexist, registry) == []  # no ground combat in the Invasion step
    # Choosing the combat keeps Coalescence: the ground combat is fought.
    combat, _ = _awaken_on_rival(
        registry, {f"sleeper:{ALBION}": "pds", f"coexist:{ALBION}": "combat"}
    )
    assert coexistence.peaceful(combat, EAST, ALBION) == set()
    assert _fights(combat, registry) == [ALBION]


def test_slumberstate_coexist_needs_the_breakthrough(registry: StaticDataRegistry) -> None:
    after, autos = _awaken_on_rival(
        registry, {f"sleeper:{ALBION}": "pds", f"coexist:{ALBION}": "coexist"},
        breakthrough=False,
    )
    assert f"coexist:{ALBION}" not in autos
    assert _fights(after, registry) == [ALBION]


@ruling("breakthroughs:titansbt#1")
def test_slumberstate_committing_other_units_brings_the_combat_back(
    registry: StaticDataRegistry,
) -> None:
    """"If you commit no other units": a commit to that planet voids the coexistence choice."""
    after, _ = _awaken_on_rival(
        registry, {f"sleeper:{ALBION}": "pds", f"coexist:{ALBION}": "coexist"}
    )
    assert _fights(after, registry) == []
    assert _fights(after, registry, {ALBION: {"infantry": 1}}) == [ALBION]


@ruling("F_ul/hecatoncheires/5")
def test_hecatoncheires_deploy_into_coexistence(registry: StaticDataRegistry) -> None:
    after, _ = _awaken_on_rival(
        registry, {f"sleeper:{ALBION}": "mech", f"coexist:{ALBION}": "coexist"}
    )
    assert _units(after, EAST, ALBION) == {"mech": 1, "infantry": 1}
    assert after.systems[EAST].planet_owners[ALBION] == "p2"
    assert coexistence.peaceful(after, EAST, ALBION) == {"p1"}
    assert _fights(after, registry) == []


def _coexisting_state(breakthrough: bool = True) -> GameState:
    state = _state()
    state.players["p1"].breakthrough_unlocked = breakthrough
    _own(state, EAST, ALBION, pid="p2", units={"infantry": 1})
    state.systems[EAST].planet_units[ALBION]["p1"] = {"pds": 1}
    state.decks.action_card_deck = [f"ac{i}" for i in range(10)]
    return state


@ruling("breakthroughs:titansbt#2")
def test_slumberstate_extra_action_cards_for_both_players(registry: StaticDataRegistry) -> None:
    state = _coexisting_state()
    drawn = status_phase._draw_action_cards(state, ["p1", "p2"])
    assert drawn == {"p1": 2, "p2": 2}  # "you and that player each draw 1 additional"
    # No coexistence (or no breakthrough): the usual single card.
    plain = _coexisting_state(breakthrough=False)
    assert status_phase._draw_action_cards(plain, ["p1", "p2"]) == {"p1": 1, "p2": 1}
    alone = _coexisting_state()
    del alone.systems[EAST].planet_units[ALBION]["p1"]
    assert status_phase._draw_action_cards(alone, ["p1", "p2"]) == {"p1": 1, "p2": 1}


@ruling("F_ul/slumberstate-computing/5")
def test_slumberstate_cards_only_in_the_draw_action_cards_step(
    registry: StaticDataRegistry,
) -> None:
    state = _coexisting_state()
    state.decks.agenda_laws = {"minister_policy": "p1"}
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    assert len(state.players["p1"].private.action_cards) == 1  # Minister of Policy: just 1
    assert state.players["p2"].private.action_cards == []
