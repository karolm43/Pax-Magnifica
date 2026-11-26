"""Legendarne planety (RULES.md 60): karty zdolności, oferty, ACTION Avernus, dary Custodia Vigilia.

Plus przejęcie planety w The Fracture dające relikt (RULES.md 50) także bez jawnego rejestru.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    board_graph,
    command_tokens,
    control,
    exhaust,
    legendary_planets,
    planet_abilities,
    production,
    rules_hooks,
    space_cannon,
    status_phase,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(autouse=True, scope="module")
def _grid(registry: StaticDataRegistry) -> Iterator[None]:
    grid = build_demo_grid(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield
    board_graph.bind_grid_provider(previous)


def _state(registry: StaticDataRegistry, *, owned: tuple[str, ...] = ()) -> GameState:
    """p1 (aktywny, kontroluje planety ``owned`` w systemie 101) i p2; talie niepuste."""
    grid = build_demo_grid(registry)
    systems = {
        pos: SystemState(position=pos, system_id=grid.system_id_at(pos))
        for pos in sorted(grid.positions)
    }
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(
                player_id="p1", color="red", faction="sol", home_position="103",
                commodities=2, commodity_value=3, tactical_cc=3, fleet_cc=3, strategic_cc=2,
                cc_reinf=4,
            ),
            "p2": PlayerState(
                player_id="p2", color="blue", faction="arborec", home_position="105",
                commodity_value=2, cc_reinf=4,
            ),
        },
        systems=systems,
    )
    state.decks.action_card_deck = ["a1", "a2", "a3"]
    for planet in owned:
        systems["101"].planet_owners[planet] = "p1"
        state.players["p1"].controlled_planets.append(planet)
    return state


def _end_turn_offer(state: GameState, player: str = "p1") -> str:
    triggers.fire(state, GameEvent.TURN, Moment.END, subject=player, ctx={"player": player})
    assert len(state.pending_offers) == 1
    return state.pending_offers[0].id


def _pass_offer(state: GameState, player: str = "p1") -> str:
    ctx = {"player": player}
    triggers.fire(state, GameEvent.PLAYER_PASSED, Moment.WHEN, subject=player, ctx=ctx)
    assert len(state.pending_offers) == 1
    return state.pending_offers[0].id


# ------------------------------------------------------------------------------------ pokrycie


def test_every_legendary_planet_is_covered(registry: StaticDataRegistry) -> None:
    covered = rules_hooks.covered_components()
    ids = [p for p, d in registry.planets.items() if d.legendary_ability_name]
    assert ids
    missing = [p for p in ids if f"planets:{p}" not in covered]
    assert not missing, missing


def test_controller_owns_the_ability_card_as_hook_source(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mallice",))
    sources = rules_hooks.owned_sources(state, "p1")
    assert rules_hooks.HookSource(rules_hooks.SOURCE_PLANET, "mallice") in sources
    others = rules_hooks.owned_sources(state, "p2")
    assert not any(s.kind == rules_hooks.SOURCE_PLANET for s in others)


# ------------------------------------------------------------- kontrola, wyczerpanie, gotowość


def test_ability_card_travels_with_planet_and_keeps_exhaustion(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("mallice",))
    exhaust.exhaust_legendary(state, "p1", "mallice")
    control.set_planet_control(state, "101", "mallice", "p2", registry)
    assert "mallice" not in state.players["p1"].exhausted_legendaries
    assert "mallice" in state.players["p2"].exhausted_legendaries  # zostaje wyczerpana
    control.set_planet_control(state, "101", "mallice", None, registry)
    control.set_planet_control(state, "101", "mallice", "p1", registry)
    assert "mallice" not in state.players["p1"].exhausted_legendaries  # z talii: gotowa


def test_legendary_card_is_independent_of_planet_card(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mallice",))
    exhaust.exhaust_legendary(state, "p1", "mallice")
    exhaust.ready_planets(state, "p1", ["mallice"])
    assert "mallice" in state.players["p1"].exhausted_legendaries
    exhaust.ready_all_legendaries(state, "p1")
    assert not state.players["p1"].exhausted_legendaries


def test_status_phase_readies_ability_cards(registry: StaticDataRegistry) -> None:
    from src.core.game_state import StatusPhaseState

    state = _state(registry, owned=("mallice",))
    state.status = StatusPhaseState()
    exhaust.exhaust_legendary(state, "p1", "mallice")
    done = status_phase.finalize_status(state, registry)
    assert not done.players["p1"].exhausted_legendaries


# ------------------------------------------------------------------------- oferty na koniec tury


def test_mallice_offers_at_end_of_turn_and_exhausts_the_card(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mallice",))
    offer_id = _end_turn_offer(state)
    done = triggers.accept_offer(state, "p1", offer_id, {"mode": "trade_goods"})
    assert done.players["p1"].trade_goods == 2
    assert "mallice" in done.players["p1"].exhausted_legendaries
    # wyczerpana karta nie daje drugiej oferty
    triggers.fire(done, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    assert not done.pending_offers


def test_mallice_converts_all_commodities(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mallice",))
    offer_id = _end_turn_offer(state)
    done = triggers.accept_offer(state, "p1", offer_id, {"mode": "convert"})
    assert (done.players["p1"].commodities, done.players["p1"].trade_goods) == (0, 2)


def test_decline_keeps_the_card_ready(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mallice",))
    offer_id = _end_turn_offer(state)
    done = triggers.decline_offer(state, "p1", offer_id)
    assert not done.players["p1"].exhausted_legendaries


def test_other_players_turn_end_does_not_offer(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mallice",))
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p2", ctx={"player": "p2"})
    assert not state.pending_offers


def test_flight_academy_places_fighters_in_a_system_with_own_ships(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("mirage",))
    state.systems["102"].space_units["p1"] = {"carrier": 1}
    offer_id = _end_turn_offer(state)
    with pytest.raises(ValueError, match="valid option"):
        triggers.accept_offer(state, "p1", offer_id, {"position": "103", "count": 2})
    done = triggers.accept_offer(state, "p1", offer_id, {"position": "102", "count": 2})
    assert done.systems["102"].space_units["p1"] == {"carrier": 1, "fighter": 2}


def test_atrament_places_infantry_on_a_controlled_planet(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("primor",))
    state.systems["101"].planet_owners["primor"] = "p1"
    offer_id = _end_turn_offer(state)
    done = triggers.accept_offer(state, "p1", offer_id, {"planet": "primor", "count": 2})
    assert done.systems["101"].planet_units["primor"]["p1"] == {"infantry": 2}


def test_hopes_end_draws_a_card_or_places_a_mech(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("hopesend",))
    offer_id = _end_turn_offer(state)
    drawn = triggers.accept_offer(state, "p1", offer_id, {"choice": "card"})
    assert len(drawn.players["p1"].private.action_cards) == 1
    placed = triggers.accept_offer(state, "p1", offer_id, {"choice": "mech:hopesend"})
    assert placed.systems["101"].planet_units["hopesend"]["p1"] == {"mech": 1}


def test_hopes_end_with_empty_mech_reinforcements_moves_one_from_the_board(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("hopesend",))
    # 4 mechy to limit plastiku: wszystkie na planszy, więc rezerwa jest pusta.
    state.systems["102"].planet_owners["x"] = "p1"
    state.systems["102"].planet_units["x"] = {"p1": {"mech": 4}}
    offer_id = _end_turn_offer(state)
    with pytest.raises(ValueError, match="mech on the board"):
        triggers.accept_offer(state, "p1", offer_id, {"choice": "mech:hopesend", "from": ""})
    done = triggers.accept_offer(
        state, "p1", offer_id, {"choice": "mech:hopesend", "from": "102|x"}
    )
    assert done.systems["102"].planet_units["x"]["p1"] == {"mech": 3}
    assert done.systems["101"].planet_units["hopesend"]["p1"] == {"mech": 1}


def test_galactic_council_discards_then_draws_a_secret(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mrte",))
    state.players["p1"].private.secret_objectives = ["sec_a"]
    state.decks.secret_objective_deck = ["sec_b"]
    offer_id = _end_turn_offer(state)
    done = triggers.accept_offer(state, "p1", offer_id, {"objective": "sec_a"})
    hand = done.players["p1"].private.secret_objectives
    assert len(hand) == 1 and hand[0] in {"sec_a", "sec_b"}
    assert "mrte" in done.players["p1"].exhausted_legendaries


def test_galactic_council_needs_an_unscored_secret(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mrte",))
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    assert not state.pending_offers  # C_legendary_planets: bez tajnego celu nie wyczerpasz


def test_acropolis_readies_another_component_of_any_player(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("emelpar",))
    state.players["p2"].exhausted_technologies = ["sc"]
    state.players["p2"].technologies = ["sc"]
    offer_id = _end_turn_offer(state)
    done = triggers.accept_offer(state, "p1", offer_id, {"target": "tech|p2|sc"})
    assert done.players["p2"].exhausted_technologies == []
    assert "emelpar" in done.players["p1"].exhausted_legendaries


# ---------------------------------------------------------------------------- oferty przy pasie


def test_hyperion_draws_a_card_and_a_command_token_when_passing(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("ordinian",))
    offer_id = _pass_offer(state)
    done = triggers.accept_offer(state, "p1", offer_id, {"pool": "fleet"})
    player = done.players["p1"]
    assert len(player.private.action_cards) == 1
    assert (player.fleet_cc, player.cc_reinf) == (4, 3)


def test_pass_abilities_do_not_fire_at_end_of_turn(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("ordinian",))
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    assert not state.pending_offers


def test_salvage_yard_puts_a_discarded_card_on_the_planet_card(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("garbozia",))
    state.decks.action_card_discard = ["sabotage"]
    offer_id = _pass_offer(state)
    done = triggers.accept_offer(state, "p1", offer_id, {"card": "sabotage"})
    assert done.legendary_cards["garbozia"] == ["sabotage"]
    assert done.decks.action_card_discard == []


def test_maxis_control_takes_an_empty_planet_and_explores_it(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("faunus",))
    offer_id = _pass_offer(state)
    offer = state.pending_offers[0]
    assert offer.id == offer_id
    hook = rules_hooks.hook_by_seq(offer.hook_seq)
    assert hook is not None and hook.inputs is not None
    options = hook.inputs(state, registry, "p1", offer.ctx)[0]["options"]
    planet = options[0]["value"]
    done = triggers.accept_offer(state, "p1", offer_id, {"planet": planet})
    assert planet in done.players["p1"].controlled_planets
    assert "faunus" in done.players["p1"].exhausted_legendaries


# ------------------------------------------------------------------------------- punkty zwycięstwa


def test_styx_gives_and_takes_a_victory_point(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    control.set_planet_control(state, "101", "styx", "p1", registry)
    assert state.players["p1"].victory_points == 1
    control.set_planet_control(state, "101", "styx", "p2", registry)
    assert state.players["p1"].victory_points == 0
    assert state.players["p2"].victory_points == 1
    # Rejestr źródeł VP (panel „Other points"): punkt przeszedł z p1 do p2.
    assert state.objectives.point_sources["planets:styx"] == {"p2": 1}


# -------------------------------------------------------------------------------- Custodia Vigilia


def test_custodian_favour_gives_mecatol_space_cannon_and_production(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("custodiavigilia",))
    state.systems["101"].planet_owners["mr"] = "p1"
    state.players["p1"].controlled_planets.append("mr")
    shooters = space_cannon.zone_shooters(state, registry, "p1", "101", "mr")
    assert [(s.hits_on, s.total_dice) for s in shooters] == [(5, 1)]
    producers = production.producers(state, registry, "p1", "101")
    assert [(p.zone, p.value) for p in producers] == [("mr", 3)]
    # bez kontroli Mecatol Rex nie ma darów
    state.systems["101"].planet_owners.pop("mr")
    assert not space_cannon.zone_shooters(state, registry, "p1", "101", "mr")
    assert not production.producers(state, registry, "p1", "101")


def test_custodian_favour_gives_command_tokens_when_another_player_scores_imperial_vp(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("custodiavigilia",))
    triggers.fire(
        state, GameEvent.IMPERIAL_VICTORY_POINT, Moment.AFTER, subject="p2", ctx={"player": "p2"}
    )
    offer = state.pending_offers[0]
    assert offer.mandatory and offer.player_id == "p1"
    done = triggers.accept_offer(
        state, "p1", offer.id, {"pools": ["tactical", "strategic"]}
    )
    player = done.players["p1"]
    assert (player.tactical_cc, player.strategic_cc) == (4, 3)
    assert command_tokens.reinforcements(done, "p1") == 2


def test_custodian_favour_ignores_own_imperial_vp(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("custodiavigilia",))
    triggers.fire(
        state, GameEvent.IMPERIAL_VICTORY_POINT, Moment.AFTER, subject="p1", ctx={"player": "p1"}
    )
    assert not state.pending_offers


# ------------------------------------------------------------------- Avernus / Jupiter / Tempesta


def test_nucleus_is_an_action_that_places_units_in_a_war_sun_system(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("avernus",))
    assert planet_abilities.is_action_planet(registry, "avernus")
    rows = {r["planet_id"]: r for r in planet_abilities.playability(state, registry, "p1")}
    assert not rows["avernus"]["playable"]  # bez war suna
    state.systems["102"].space_units["p1"] = {"warsun": 1}
    rows = {r["planet_id"]: r for r in planet_abilities.playability(state, registry, "p1")}
    assert rows["avernus"]["playable"]
    done, implemented = planet_abilities.play_planet_ability(
        state, registry, "p1", "avernus", {"position": "102", "unit": "fighters"}
    )
    assert implemented
    assert done.systems["102"].space_units["p1"] == {"warsun": 1, "fighter": 2}
    assert "avernus" in done.players["p1"].exhausted_legendaries
    assert done.players["p1"].took_action_this_turn
    # nie zużywa żetonu dowodzenia
    assert (done.players["p1"].strategic_cc, done.players["p1"].cc_reinf) == (2, 4)
    with pytest.raises(ValueError, match="exhausted"):
        planet_abilities.play_planet_ability(
            done, registry, "p1", "avernus", {"position": "102", "unit": "fighters"}
        )


def test_jupiter_brain_gives_an_extra_action_after_the_turn(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("thundersedge",))
    state.players["p1"].took_action_this_turn = True
    state.speaker_id = "p1"
    # Odtwarzamy stan tuż po end_turn: pauza po turze p1, aktywny p2.
    from src.core.game_state import TurnEndWindow

    state.turn_end_window = TurnEndWindow(ended_player="p1", ended_passed=False, next_player="p2")
    state.active_player_id = "p2"
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    offer = state.pending_offers[0]
    done = triggers.accept_offer(state, "p1", offer.id, {})
    assert done.active_player_id == "p1"
    assert done.bonus_turn is not None and done.bonus_turn.not_a_turn is False
    assert "thundersedge" in done.players["p1"].exhausted_legendaries


def test_jupiter_brain_after_passing_is_still_the_players_turn(
    registry: StaticDataRegistry,
) -> None:
    """User decision 2026-11-26 (RULES.md 53.10): the "not considered your turn" rules of Puppets
    on a String (no transactions, Minister of Peace) do not apply to Jupiter Brain."""
    from src.core import action_budget
    from src.core.game_state import TurnEndWindow

    state = _state(registry, owned=("thundersedge",))
    state.players["p1"].took_action_this_turn = True
    state.players["p1"].passed = True
    state.speaker_id = "p1"
    state.turn_end_window = TurnEndWindow(ended_player="p1", ended_passed=True, next_player="p2")
    state.active_player_id = "p2"
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    done = triggers.accept_offer(state, "p1", state.pending_offers[0].id, {})
    assert done.bonus_turn is not None and done.bonus_turn.not_a_turn is False
    assert done.players["p1"].passed is True
    assert not action_budget.outside_turn(done, "p1")


# ------------------------------------------------------------------------------ Fracture -> relikt


def test_fracture_planet_gives_a_relic_without_explicit_registry(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry)
    state.systems["frac1"] = SystemState(position="frac1", system_id="fracture1")
    state.decks.relic_deck = ["codex", "shard"]
    control.set_planet_control(state, "frac1", "some_planet", "p1")  # bez registry
    assert len(state.players["p1"].relics) == 1
    # planeta już kontrolowana przez innego gracza => zmiana kontrolera nie daje reliktu
    control.set_planet_control(state, "frac1", "some_planet", "p2")
    assert state.players["p2"].relics == []


def test_legendary_helpers(registry: StaticDataRegistry) -> None:
    state = _state(registry, owned=("mallice",))
    assert legendary_planets.legendary_planets_of(state, registry, "p1") == ["mallice"]
    assert legendary_planets.is_ready(state, "p1", "mallice")
    assert not legendary_planets.is_ready(state, "p2", "mallice")


def test_ionian_fuel_refinery_adds_one_to_the_boosted_ship_for_the_action(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("tempesta",))
    triggers.fire(
        state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
        ctx={"player": "p1", "position": "102"},
    )
    offer = state.pending_offers[0]
    done = triggers.accept_offer(state, "p1", offer.id, {})
    args = (rules_hooks.POINT_MOVEMENT_MOVE_VALUE, done, "p1", 1)
    assert rules_hooks.modify(*args, {"tempesta": True}) == 2
    assert rules_hooks.modify(*args, {"tempesta": False, "boost": True}) == 1
    assert "tempesta" in done.players["p1"].exhausted_legendaries


def test_aeurex_mechanica_places_a_ship_matching_an_owned_upgrade(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, owned=("industrex",))
    state.players["p1"].technologies = ["cv2"]
    state.systems["102"].space_units["p1"] = {"carrier": 1}
    offer_id = _pass_offer(state)
    with pytest.raises(ValueError, match="valid option"):
        triggers.accept_offer(state, "p1", offer_id, {"ship": "cruiser", "position": "102"})
    done = triggers.accept_offer(state, "p1", offer_id, {"ship": "carrier", "position": "102"})
    assert done.systems["102"].space_units["p1"] == {"carrier": 2}
