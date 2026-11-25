"""Legendary planets - rulings of ``docs/rules_tirules/C_legendary_planets.md`` point by point.

Every test marks the ``@ruling(...)`` points it checks (guard ``tests/test_ruling_coverage.py``).
Base tests live in ``tests/test_legendary_planets.py``; statuses without a test:
``tests/rulings_status.json``.
"""

from __future__ import annotations

import pytest

from src.core import (
    card_draw,
    control,
    exploration,
    hand_limit,
    legendary_planets,
    rules_hooks,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_legendary_planets import _end_turn_offer, _pass_offer, _state
from tests.test_legendary_planets import _grid as _grid  # noqa: F401 - autouse fixture
from tests.test_legendary_planets import registry as registry  # noqa: F401 - module fixture


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _offer_inputs(state: GameState, registry: StaticDataRegistry) -> list[dict[str, object]]:
    offer = state.pending_offers[0]
    hook = rules_hooks.hook_by_seq(offer.hook_seq)
    assert hook is not None and hook.inputs is not None
    return hook.inputs(state, registry, offer.player_id, offer.ctx)


# ============================================================================ The Acropolis


@ruling("C_legendary_planets/the-acropolis-emelpar/1")
def test_acropolis_readies_a_component_in_another_players_play_area(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("emelpar",))
    state.players["p2"].technologies = ["sc"]
    state.players["p2"].exhausted_technologies = ["sc"]
    offer_id = _end_turn_offer(state)
    done = triggers.accept_offer(state, "p1", offer_id, {"target": "tech|p2|sc"})
    assert done.players["p2"].exhausted_technologies == []


# ============================================================================ The Atrament


@ruling("C_legendary_planets/the-atrament-primor/1")
def test_atrament_places_both_infantry_on_one_planet(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("primor",))
    state.systems["101"].planet_owners["primor"] = "p1"
    state.systems["101"].planet_owners["other"] = "p1"
    state.players["p1"].controlled_planets.append("other")
    offer_id = _end_turn_offer(state)
    keys = [item["key"] for item in _offer_inputs(state, registry)]
    assert keys == ["planet", "count"]  # ONE planet for all the infantry, no per-unit split
    done = triggers.accept_offer(state, "p1", offer_id, {"planet": "primor", "count": 2})
    assert done.systems["101"].planet_units["primor"]["p1"] == {"infantry": 2}
    assert "other" not in done.systems["101"].planet_units


# ================================================================================ Garbozia


@ruling("C_legendary_planets/dok-n-pics-salvage-yard-garbozia/1")
def test_salvage_yard_player_chooses_the_discarded_card(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("garbozia",))
    state.decks.action_card_discard = ["sabotage", "lucky", "plague"]
    offer_id = _pass_offer(state)
    options = [o["value"] for o in _offer_inputs(state, registry)[0]["options"]]  # type: ignore[attr-defined]
    assert options == ["sabotage", "lucky", "plague"]  # whole discard pile on offer
    done = triggers.accept_offer(state, "p1", offer_id, {"card": "lucky"})
    assert done.legendary_cards["garbozia"] == ["lucky"]
    assert done.decks.action_card_discard == ["sabotage", "plague"]


@ruling("C_legendary_planets/dok-n-pics-salvage-yard-garbozia/3")
def test_salvage_yard_cards_do_not_count_toward_the_hand_limit(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("garbozia",))
    before = hand_limit.action_card_excess(state, "p1")
    state.decks.action_card_discard = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
    for card in list(state.decks.action_card_discard):
        card_draw.place_on_legendary_card(state, "garbozia", card)
    assert len(state.legendary_cards["garbozia"]) == 10
    assert not state.players["p1"].private.action_cards  # on the card, not in the hand
    assert hand_limit.action_card_excess(state, "p1") == before == 0


@ruling("C_legendary_planets/dok-n-pics-salvage-yard-garbozia/4")
def test_codex_cannot_take_cards_from_the_salvage_yard(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("garbozia",))
    state.decks.action_card_discard = ["sabotage"]
    card_draw.place_on_legendary_card(state, "garbozia", "sabotage")
    # The Codex takes from the discard pile (``take_from_discard``); the card is not there.
    assert "sabotage" not in state.decks.action_card_discard
    with pytest.raises(ValueError, match="not in the discard pile"):
        card_draw.take_from_discard(state, "p1", "sabotage")


@ruling("C_legendary_planets/dok-n-pics-salvage-yard-garbozia/5")
def test_salvage_yard_cards_stay_when_garbozia_changes_hands(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("garbozia",))
    state.decks.action_card_discard = ["sabotage"]
    card_draw.place_on_legendary_card(state, "garbozia", "sabotage")
    control.set_planet_control(state, "101", "garbozia", "p2", registry)
    assert "garbozia" in state.players["p2"].controlled_planets
    assert state.legendary_cards["garbozia"] == ["sabotage"]  # stays on the ability card


@ruling("C_legendary_planets/dok-n-pics-salvage-yard-garbozia/2")
def test_salvage_yard_cards_are_played_from_the_card_without_readying_it(
    registry: StaticDataRegistry,
) -> None:
    from src.core import action_cards

    state = _state(registry, owned=("garbozia",))
    state.players["p1"].exhausted_legendaries = ["garbozia"]  # exhausted: still playable
    state.decks.action_card_discard = ["industrial_initiative"]
    card_draw.place_on_legendary_card(state, "garbozia", "industrial_initiative")
    rows = {r["card_id"]: r for r in action_cards.playability(state, registry, "p1")}
    assert rows["industrial_initiative"]["playable"]
    assert rows["industrial_initiative"]["from_planet"] == "garbozia"
    assert not state.players["p1"].private.action_cards  # never really in the hand
    done, implemented = action_cards.play_action_card(
        state, registry, "p1", "industrial_initiative"
    )
    assert implemented and done.players["p1"].took_action_this_turn
    # Purged: it leaves the card and is NOT discarded; the exhausted card stays exhausted.
    assert "garbozia" not in done.legendary_cards
    assert done.decks.action_card_discard == [] and not done.salvage_yard_borrowed
    assert done.players["p1"].exhausted_legendaries == ["garbozia"]
    assert state.legendary_cards["garbozia"] == ["industrial_initiative"]  # pure function


@ruling("C_legendary_planets/dok-n-pics-salvage-yard-garbozia/5")
def test_new_controller_of_garbozia_plays_the_cards_that_stayed(
    registry: StaticDataRegistry,
) -> None:
    from src.core import action_cards

    state = _state(registry, owned=("garbozia",))
    state.decks.action_card_discard = ["industrial_initiative"]
    card_draw.place_on_legendary_card(state, "garbozia", "industrial_initiative")
    control.set_planet_control(state, "101", "garbozia", "p2", registry)
    with pytest.raises(ValueError, match="do not have"):
        action_cards.play_action_card(state, registry, "p1", "industrial_initiative")
    assert not any(r["from_planet"] for r in action_cards.playability(state, registry, "p1"))
    state.active_player_id = "p2"
    done, _ = action_cards.play_action_card(state, registry, "p2", "industrial_initiative")
    assert done.players["p2"].took_action_this_turn and "garbozia" not in done.legendary_cards


# ========================================================================= Galactic Council


@ruling("C_legendary_planets/the-galactic-council-mecatol-rex/1")
def test_galactic_council_discards_first_so_the_same_secret_may_return(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("mrte",))
    state.players["p1"].private.secret_objectives = ["sec_a"]
    state.decks.secret_objective_deck = []  # only the discarded card can be drawn
    offer_id = _end_turn_offer(state)
    done = triggers.accept_offer(state, "p1", offer_id, {"objective": "sec_a"})
    assert done.players["p1"].private.secret_objectives == ["sec_a"]
    assert done.decks.secret_objective_deck == []


@ruling("C_legendary_planets/the-galactic-council-mecatol-rex/2")
def test_galactic_council_needs_an_unscored_secret_in_hand(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("mrte",))
    state.players["p1"].private.secret_objectives = []
    state.players["p1"].scored_secrets = ["sec_scored"]
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    assert not state.pending_offers  # nothing to discard: the card cannot be exhausted
    assert "mrte" not in state.players["p1"].exhausted_legendaries


@ruling("C_legendary_planets/the-galactic-council-mecatol-rex/3")
def test_galactic_council_cannot_discard_a_scored_secret(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mrte",))
    state.players["p1"].private.secret_objectives = ["sec_a"]
    state.players["p1"].scored_secrets = ["sec_scored"]
    offer_id = _end_turn_offer(state)
    values = [o["value"] for o in _offer_inputs(state, registry)[0]["options"]]  # type: ignore[attr-defined]
    assert values == ["sec_a"]  # only the hand is offered
    with pytest.raises(ValueError, match="valid option"):
        triggers.accept_offer(state, "p1", offer_id, {"objective": "sec_scored"})
    assert state.players["p1"].scored_secrets == ["sec_scored"]


# ================================================================================ Hope's End


@ruling("C_legendary_planets/imperial-arms-vault-hopes-end/1")
def test_hopes_end_replacement_mech_is_placed_undamaged(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("hopesend",))
    state.systems["102"].planet_owners["x"] = "p1"
    # Damaged mech on a system without p1's command token; reinforcements are empty (4 on board).
    state.systems["102"].planet_units["x"] = {"p1": {"mech": 4}}
    state.systems["102"].damaged_units = {"x": {"p1": {"mech": 4}}}
    offer_id = _end_turn_offer(state)
    done = triggers.accept_offer(
        state, "p1", offer_id, {"choice": "mech:hopesend", "from": "102|x"}
    )
    assert done.systems["101"].planet_units["hopesend"]["p1"] == {"mech": 1}
    placed_damage = done.systems["101"].damaged_units.get("hopesend", {}).get("p1", {})
    assert placed_damage.get("mech", 0) == 0  # undamaged
    assert done.systems["102"].planet_units["x"]["p1"] == {"mech": 3}


# ============================================================================ Jupiter Brain


@ruling("C_legendary_planets/jupiter-brain-thunders-edge/1")
def test_jupiter_brain_is_ready_the_moment_it_is_gained(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    control.set_planet_control(state, "101", "thundersedge", "p1", registry)
    assert legendary_planets.is_ready(state, "p1", "thundersedge")  # gained readied
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    assert len(state.pending_offers) == 1  # usable at the end of the very same turn


# ================================================================================== Faunus


@ruling("C_legendary_planets/maxis-central-control-faunus/1")
def test_maxis_explores_only_a_planet_nobody_controlled(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The demo map has no free planet with a trait; give Moll Primus one so it can be explored.
    original = exploration.planet_traits

    def traits(
        reg: StaticDataRegistry, planet_id: str, state: GameState | None = None
    ) -> list[str]:
        return ["cultural"] if planet_id == "mollprimus" else original(reg, planet_id, state)

    monkeypatch.setattr(exploration, "planet_traits", traits)
    planet = "mollprimus"

    free = _state(registry, owned=("faunus",))
    offer_id = _pass_offer(free)
    assert planet in [o["value"] for o in _offer_inputs(free, registry)[0]["options"]]  # type: ignore[attr-defined]
    done = triggers.accept_offer(free, "p1", offer_id, {"planet": planet})
    assert planet in done.players["p1"].controlled_planets
    assert done.exploration is not None  # nobody controlled it: explored

    taken = _state(registry, owned=("faunus",))
    position = next(pos for pos in taken.systems if planet in _all_planets(taken, registry, pos))
    control.set_planet_control(taken, position, planet, "p2", registry)
    again = _pass_offer(taken)
    assert planet in [o["value"] for o in _offer_inputs(taken, registry)[0]["options"]]  # type: ignore[attr-defined]
    done = triggers.accept_offer(taken, "p1", again, {"planet": planet})
    assert planet in done.players["p1"].controlled_planets  # taken from another player ...
    assert done.exploration is None  # ... and NOT explored


def _all_planets(state: GameState, registry: StaticDataRegistry, position: str) -> list[str]:
    from src.core.state_grid import grid_from_state
    from src.core.system_planets import planets_of_system

    return list(planets_of_system(state, registry, position, grid_from_state(state, registry)))
