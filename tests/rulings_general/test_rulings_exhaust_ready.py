"""Exhausted / readied cards — rulings ``R_exhausted.md`` and ``R_readied.md`` point by point.

Central point: ``src/core/exhaust.py`` (RULES.md 27, 43.1a). "Facedown" = the component id is on
the player's ``exhausted_*`` list; "faceup" = it is not. Statuses without a test:
``tests/rulings_status.json``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.core import (
    agenda_phase,
    component_action,
    exhaust,
    payment,
    relic_planets,
    rules_hooks,
    status_phase,
    strategic_action,
    technology_abilities,
    triggers,
    unit_ops,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, StatusPhaseState, SystemState
from src.core.hooks import action_cards_economy
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause
from tests.rulings import ruling
from tests.rulings_general.test_rulings_technology import _sar_state
from tests.test_technology import _specialty_planet

PLANET = "jord"  # any real planet with resources and influence
STATION = "oluzstation"  # Thunder's Edge space station


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    yield


def _state(*planets: str, techs: tuple[str, ...] = ()) -> GameState:
    """p1 controls ``planets`` (map + player list); p2 controls Mecatol Rex."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(
                player_id="p1", color="red", technologies=list(techs),
                controlled_planets=list(planets),
            ),
            "p2": PlayerState(player_id="p2", color="blue", controlled_planets=["mr"]),
        },
        systems={
            "101": SystemState(
                position="101", system_id="20", planet_owners=dict.fromkeys(planets, "p1")
            ),
            "000": SystemState(position="000", system_id="18", planet_owners={"mr": "p2"}),
        },
    )


# ================================================================ facedown / faceup representation


@ruling("R_exhausted/rules-reference/1", "R_readied/rules-reference/1")
def test_exhausting_flips_facedown_and_readying_flips_faceup() -> None:
    state = _state(PLANET, techs=("sr",))
    exhaust.exhaust_planets(state, "p1", [PLANET])
    exhaust.exhaust_technology(state, "p1", "sr")
    exhaust.exhaust_strategy_card(state, "p1", 4)
    player = state.players["p1"]
    assert (player.exhausted_planets, player.exhausted_technologies) == ([PLANET], ["sr"])
    assert player.exhausted_strategy_cards == [4]
    exhaust.ready_planets(state, "p1", [PLANET])
    exhaust.ready_technology(state, "p1", "sr")
    exhaust.ready_strategy_card(state, "p1", 4)
    assert not (
        player.exhausted_planets or player.exhausted_technologies
        or player.exhausted_strategy_cards
    )
    assert PLANET in player.controlled_planets and "sr" in player.technologies  # still in play


# ======================================================================== spending planets


@ruling(
    "R_exhausted/rules-reference/3", "R_readied/rules-reference/2", "R_readied/rules-reference/4"
)
def test_spending_exhausts_a_ready_planet_and_an_exhausted_one_cannot_be_spent(
    registry: StaticDataRegistry,
) -> None:
    state = _state(PLANET)
    value = payment.validate_payment(state, registry, "p1", "resources", [PLANET], 0)
    assert value == registry.planets[PLANET].resources
    payment.apply_payment(state, "p1", [PLANET], 0)
    assert state.players["p1"].exhausted_planets == [PLANET]
    for kind in ("resources", "influence"):
        with pytest.raises(ValueError, match="already exhausted"):
            payment.validate_payment(state, registry, "p1", kind, [PLANET], 0)


# ===================================================== exhausting a card to resolve its ability


def _dock_state(*techs: str) -> GameState:
    state = _state("pl", techs=techs)
    state.systems["101"].planet_units = {"pl": {"p1": {"spacedock": 1}}}
    return state


@ruling(
    "R_exhausted/rules-reference/4", "R_readied/rules-reference/3", "R_readied/rules-reference/4"
)
def test_exhaust_cost_ability_exhausts_its_card_and_cannot_be_used_again() -> None:
    state = _dock_state("sr")  # Sling Relay: "ACTION: Exhaust this card to produce 1 ship..."
    done = component_action.play_component_action(state, "p1", "sr", params={"system": "101"})
    assert done.players["p1"].exhausted_technologies == ["sr"]
    again = _dock_state("sr")
    again.players["p1"].exhausted_technologies = ["sr"]
    with pytest.raises(ValueError, match="not ready"):
        component_action.play_component_action(again, "p1", "sr", params={"system": "101"})


@ruling("R_readied/rules-reference/3.1")
def test_only_a_card_that_says_so_is_exhausted_as_a_cost(registry: StaticDataRegistry) -> None:
    """Psychoarchaeology exhausts PLANETS, never itself; Bio-Stims ("exhaust this card") does."""
    planet = _specialty_planet(registry, "WARFARE")
    state = _state(planet, techs=("pa",))
    done = technology_abilities.use_free_ability(state, registry, "p1", "pa", {"planets": [planet]})
    assert done.players["p1"].exhausted_planets == [planet]
    assert done.players["p1"].exhausted_technologies == []
    bio = _state(techs=("bs", "pi"))
    bio.players["p1"].exhausted_technologies = ["pi"]
    triggers.fire(bio, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    (offer,) = bio.pending_offers
    out = triggers.accept_offer(bio, "p1", offer.id, {"target": "tech:pi"})
    assert out.players["p1"].exhausted_technologies == ["bs"]


@ruling("R_exhausted/rules-reference/4.1", "R_readied/notes/1")
def test_passive_ability_of_an_exhausted_card_still_works() -> None:
    """Self-Assembly Routines exhausted: "After 1 of your mechs is destroyed, gain 1 trade good"
    still resolves."""
    state = _sar_state(["sar"])
    state.players["p1"].exhausted_technologies = ["sar"]
    unit_ops.remove_units(state, state.systems["101"], "pl", "p1", "mech", 1, UnitCause.DESTROYED)
    assert state.players["p1"].trade_goods == 1


# ============================================================================ strategy cards


def _sc_state() -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", strategy_cards=[1]),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
    )


@ruling("R_exhausted/rules-reference/5", "R_readied/rules-reference/6")
def test_strategic_action_exhausts_the_strategy_card(registry: StaticDataRegistry) -> None:
    done = strategic_action.play_strategy_card(_sc_state(), registry, "p1", 1)
    assert done.players["p1"].exhausted_strategy_cards == [1]
    played = _sc_state()
    played.players["p1"].exhausted_strategy_cards = [1]
    with pytest.raises(ValueError, match="already played"):
        strategic_action.play_strategy_card(played, registry, "p1", 1)


# ============================================================== Ready Cards step (status phase)


@ruling(
    "R_exhausted/rules-reference/2",
    "R_readied/rules-reference/5",
    "R_readied/rules-reference/6.1",
)
def test_ready_cards_step_readies_every_exhausted_card(registry: StaticDataRegistry) -> None:
    state = _state(PLANET, techs=("sr",))
    state.phase, state.status = Phase.STATUS, StatusPhaseState()
    player = state.players["p1"]
    player.strategy_cards, player.relics = [1], ["thetriad"]
    exhaust.exhaust_planets(state, "p1", [PLANET])
    exhaust.exhaust_technology(state, "p1", "sr")
    exhaust.exhaust_strategy_card(state, "p1", 1)
    exhaust.exhaust_relic(state, "p1", "thetriad")
    exhaust.exhaust_legendary(state, "p1", "mallice")
    exhaust.exhaust_breakthrough(state, "p1")
    player.leader_states = {"agent": "exhausted", "hero": "locked"}
    done = status_phase.finalize_status(state, registry).players["p1"]
    assert not (
        done.exhausted_planets or done.exhausted_technologies or done.exhausted_strategy_cards
        or done.exhausted_relics or done.exhausted_legendaries or done.breakthrough_exhausted
    )
    assert done.leader_states == {"agent": "unlocked", "hero": "locked"}  # only exhausted ready


# ================================================================ end of the agenda phase


@ruling(
    "R_exhausted/notes/1", "R_exhausted/notes/1.1", "R_readied/notes/2", "R_readied/notes/2.1"
)
def test_planets_stations_and_the_triad_ready_at_the_end_of_the_agenda_phase(
    registry: StaticDataRegistry,
) -> None:
    """Deepwrought ocean cards: status ``requires faction:deepwrought``."""
    state = _state(PLANET, STATION)
    state.players["p1"].relics = ["thetriad"]
    triad = next(iter(relic_planets.values(state, registry, "p1")))
    exhaust.exhaust_planets(state, "p1", [PLANET, STATION, triad])
    exhaust.exhaust_technology(state, "p1", "sr")
    assert state.players["p1"].exhausted_relics == ["thetriad"]
    agenda_phase._ready_all_planets(state)
    player = state.players["p1"]
    assert player.exhausted_planets == [] and player.exhausted_relics == []
    assert player.exhausted_technologies == ["sr"]  # only planets (and planet-like cards)


# ====================================================== "exhaust / ready a planet" = your planet


@ruling("R_exhausted/notes/2")
def test_exhaust_a_planet_means_your_own_unless_the_effect_says_otherwise(
    registry: StaticDataRegistry,
) -> None:
    planet = _specialty_planet(registry, "WARFARE")
    state = _state(planet, techs=("pa",))
    with pytest.raises(ValueError, match="Invalid selection|Wrong number"):  # p2's Mecatol Rex
        technology_abilities.use_free_ability(state, registry, "p1", "pa", {"planets": ["mr"]})
    # Uprising: "Exhaust 1 non-home planet controlled by another player" - says otherwise.
    action_cards_economy.uprising(state, registry, "p1", {"planet": "mr"})
    assert state.players["p2"].exhausted_planets == ["mr"]
    assert state.players["p1"].exhausted_planets == []
    with pytest.raises(ValueError, match="another player"):
        action_cards_economy.uprising(state, registry, "p1", {"planet": planet})


@ruling("R_readied/notes/3")
def test_ready_a_planet_means_your_own(registry: StaticDataRegistry) -> None:
    planet = _specialty_planet(registry, "WARFARE")
    other = _specialty_planet(registry, "PROPULSION")
    state = _state(planet)
    state.systems["000"].planet_owners[other] = "p2"
    state.players["p2"].controlled_planets.append(other)
    state.players["p2"].exhausted_planets = [other]
    with pytest.raises(ValueError, match="your planets"):  # Brilliance: "Ready 1 of your planets"
        action_cards_economy.brilliance(state, registry, "p1", {"planet": other})
    exhaust.exhaust_planets(state, "p1", [planet])
    action_cards_economy.brilliance(state, registry, "p1", {"planet": planet})
    assert state.players["p1"].exhausted_planets == []
    assert state.players["p2"].exhausted_planets == [other]
