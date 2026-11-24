"""Technologie ogólne — rulingi ``docs/rules_tirules/C_technology.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty, które sprawdza (strażnik
``tests/test_ruling_coverage.py``, kontrakt ogólny). Podstawowe testy technologii są w
``tests/test_technologies_*.py`` (tam też część oznaczeń); statusy bez testu:
``tests/rulings_status.json``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    action_budget,
    battle,
    card_draw,
    component_action,
    damage,
    economy,
    invasion,
    limits,
    production,
    rules_hooks,
    tactical,
    technology,
    triggers,
    turn_flow,
    unit_ops,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, SystemState
from src.core.hex_grid import HexGrid
from src.core.hooks import agendas_laws
from src.core.hooks import technologies_combat as combat_hooks
from src.core.invasion import BombardAssignment
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause
from tests.rulings import ruling
from tests.test_battle import _grid as battle_grid
from tests.test_battle import _state as battle_state
from tests.test_invasion import _PL1, _PL2, _seek
from tests.test_invasion import _grid as inv_grid
from tests.test_invasion import _state as inv_state
from tests.test_technology import _first, _specialty_planet
from tests.test_technology import _state as research_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _techs(state: GameState, player_id: str, *techs: str) -> GameState:
    state.players[player_id].technologies = list(techs)
    return state


# ============================================================================ Antimass Deflectors


@ruling("C_technology/antimass-deflectors/1")
def test_antimass_minus_one_also_in_space_cannon_defense(registry: StaticDataRegistry) -> None:
    """-1 działa także w Space Cannon Defense (ofensywa: ``test_antimass_odejmuje…``)."""
    grid = inv_grid()

    def defense(techs: list[str]) -> GameState:
        state = inv_state({"p1": {"infantry": 2}}, {_PL1: {"p2": {"pds": 2}}}, {_PL1: "p2"})
        _techs(state, "p1", *techs)
        state = invasion.begin_invasion(state, grid, registry)
        state = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 2}})
        state = invasion.advance(state, grid, registry)
        return invasion.defense_fire(state, grid, registry, _PL1)

    plain = defense([])
    shielded = defense(["amd"])
    assert plain.invasion is not None and shielded.invasion is not None
    plain_roll = plain.invasion.log[-1]["rolls"][0]
    shielded_roll = shielded.invasion.log[-1]["rolls"][0]
    assert plain_roll["modifier"] == 0 and shielded_roll["modifier"] == -1


# ============================================================================ Dark Energy Tap


def _frontier(techs: list[str]) -> GameState:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", technologies=techs),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
    )
    state.systems["101"] = SystemState(position="101", system_id="20", frontier_token=True)
    state.systems["102"] = SystemState(position="102", system_id="22")
    return state


@ruling("C_technology/dark-energy-tap/4")
def test_gaining_dark_energy_tap_does_not_explore_frontier_tokens() -> None:
    state = _frontier([])
    state.systems["101"].space_units = {"p1": {"cruiser": 1}}
    technology.grant_technology(state, "p1", "det")
    assert state.exploration is None and state.systems["101"].frontier_token


@ruling("C_technology/dark-energy-tap/4.1")
def test_ship_placed_outside_the_tactical_action_does_not_explore() -> None:
    state = _frontier(["det"])
    # Statek postawiony efektem poza akcją taktyczną w systemie z żetonem frontier...
    unit_ops.place_units(state, state.systems["101"], "space", "p1", "cruiser", 1)
    assert state.exploration is None
    # ...a akcja taktyczna w INNYM systemie nie bada tego żetonu.
    state.active_system = "102"
    state.systems["102"].space_units = {"p1": {"destroyer": 1}}
    ended = tactical.end_tactical_action(state)
    assert ended.exploration is None and ended.systems["101"].frontier_token


# ============================================================================ Fleet Logistics


def _fl_state(techs: list[str]) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", technologies=techs),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
    )


@ruling("C_technology/fleet-logistics/6")
def test_fleet_logistics_no_turn_start_or_end_between_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fired: list[tuple[GameEvent, Moment]] = []
    real = triggers.fire

    def spy(state: GameState, event: GameEvent, moment: Moment, *a: Any, **k: Any) -> Any:
        fired.append((event, moment))
        return real(state, event, moment, *a, **k)

    monkeypatch.setattr(triggers, "fire", spy)
    state = component_action.play_component_action(_fl_state(["fl"]), "p1")
    state = component_action.play_component_action(state, "p1")
    assert (GameEvent.TURN, Moment.END) not in fired
    assert (GameEvent.TURN, Moment.START) not in fired
    turn_flow.end_turn(state, "p1")
    assert (GameEvent.TURN, Moment.END) in fired


@ruling("C_technology/fleet-logistics/1")
def test_fleet_logistics_works_on_the_turn_it_is_gained() -> None:
    state = component_action.play_component_action(_fl_state([]), "p1")
    assert action_budget.actions_left(state, "p1") == 0
    technology.grant_technology(state, "p1", "fl")
    assert action_budget.actions_left(state, "p1") == 1


@ruling("C_technology/fleet-logistics/2")
def test_turn_ended_by_an_effect_gives_no_second_action() -> None:
    state = component_action.play_component_action(_fl_state(["fl"]), "p1")
    ended = turn_flow.end_turn(state, "p1", forced=True)  # np. Coup d'Etat kończy turę
    assert ended.active_player_id == "p2"


@ruling("C_technology/fleet-logistics/3")
def test_fleet_logistics_cannot_pass_after_an_action() -> None:
    state = component_action.play_component_action(_fl_state(["fl"]), "p1")
    assert action_budget.actions_left(state, "p1") == 1
    with pytest.raises(ValueError, match="already took an action"):
        turn_flow.pass_turn(state, "p1")


# ============================================================================ Neural Motivator


@ruling("C_technology/neural-motivator/1")
def test_neural_motivator_only_in_the_status_phase_draw() -> None:
    state = GameState(
        phase=Phase.ACTION,
        players={"p1": PlayerState(player_id="p1", color="red", technologies=["nm"])},
    )
    state.decks.action_card_deck = ["a1", "a2", "a3", "a4"]
    card_draw.draw_action_card(state, "p1")  # Politics i inne efkety poza statusem
    assert len(state.players["p1"].private.action_cards) == 1
    agendas_laws._policy(state, "p1", {})  # Minister of Policy (koniec fazy statusu)
    assert len(state.players["p1"].private.action_cards) == 2  # nadal po 1 karcie


# ============================================================================ Psychoarchaeology


@ruling("R_technology/rules-reference/12")
def test_psychoarchaeology_planet_ignores_only_one_prerequisite(
    registry: StaticDataRegistry,
) -> None:
    tier2 = _first(registry, "WARFARE", 2)
    red = _specialty_planet(registry, "WARFARE")
    state = research_state(registry, ["pa"], [red])
    with pytest.raises(ValueError):
        technology.research(state, registry, "p1", tier2, [red])
    with pytest.raises(ValueError):
        technology.research(state, registry, "p1", tier2, [red, red])
    state.players["p1"].technologies.append(_first(registry, "WARFARE", 0))
    done = technology.research(state, registry, "p1", tier2, [red])
    assert tier2 in done.players["p1"].technologies


@ruling("C_technology/psychoarchaeology/2")
def test_psychoarchaeology_trade_goods_one_at_a_time(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core import technology_abilities

    planets = [
        p.id for p in registry.planets.values() if p.tech_specialties
    ][:2]
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(
                player_id="p1", color="red", technologies=["pa"], controlled_planets=planets
            )
        },
    )
    gains: list[int] = []
    real = economy.gain_trade_goods

    def spy(st: GameState, pid: str, amount: int, *a: Any, **k: Any) -> Any:
        gains.append(amount)
        return real(st, pid, amount, *a, **k)

    monkeypatch.setattr(economy, "gain_trade_goods", spy)
    done = technology_abilities.use_free_ability(state, registry, "p1", "pa", {"planets": planets})
    assert gains == [1, 1] and done.players["p1"].trade_goods == 2


# ============================================================================ X-89 ΩΩ


def _bombard_state(
    space: dict[str, int], planets: dict[str, dict[str, dict[str, int]]], techs: list[str]
) -> GameState:
    state = inv_state({"p1": space}, planets, {_PL1: "p2", _PL2: "p2"})
    state.players["p1"].technologies = techs
    state.players["p2"].controlled_planets = [_PL1, _PL2]
    return state


def _bombard_log(state: GameState) -> list[dict[str, Any]]:
    assert state.invasion is not None
    return [e for e in state.invasion.log if e["phase"] == "BOMBARDMENT"]


@ruling("C_technology/x89-bacterial-weapon-omega-omega/2")
def test_x89_hits_to_cancel_are_the_doubled_hits(registry: StaticDataRegistry) -> None:
    grid = inv_grid()
    planets = {_PL1: {"p2": {"infantry": 6}}}

    def run(state: GameState) -> GameState:
        state = invasion.begin_invasion(state, grid, registry)
        return invasion.bombard(state, grid, registry, [BombardAssignment("dreadnought", _PL1, 2)])

    hit = _seek(
        _bombard_state({"dreadnought": 2}, planets, ["x89c4"]),
        run,
        lambda s: s.invasion is not None and _bombard_log(s)[0]["hits"] > 0,
    )
    entry = _bombard_log(hit)[0]
    rolled = sum(1 for r in entry["rolls"] for d in r["dice"] if d >= r["hitsOn"])
    assert entry["hits"] == 2 * rolled
    assert hit.invasion is not None
    # Do przypisania (i ewentualnego anulowania) czeka liczba JUŻ podwojona.
    assert hit.invasion.bombard_pending.get(_PL1, 0) == 2 * rolled


@ruling("C_technology/x89-bacterial-weapon-omega-omega/3.1")
def test_x89_ships_fighting_as_ground_forces_double_their_hits() -> None:
    state = _techs(battle_state({"p1": {"cruiser": 1}}), "p1", "x89c4")
    point = rules_hooks.POINT_COMBAT_HIT_MULTIPLIER
    ctx = {"kind": "ground", "base_type": "cruiser"}
    assert rules_hooks.modify(point, state, "p1", 1, ctx) == 2
    assert rules_hooks.modify(point, state, "p1", 1, {"kind": "space", "base_type": "mech"}) == 1


@ruling(
    "C_technology/x89-bacterial-weapon-omega-omega/6",
    "C_technology/x89-bacterial-weapon-omega-omega/6.1",
)
def test_unit_bombardment_dice_and_plasma_die_target_one_planet(
    registry: StaticDataRegistry,
) -> None:
    grid = inv_grid()
    planets = {_PL1: {"p2": {"infantry": 1}}, _PL2: {"p2": {"infantry": 1}}}
    state = _bombard_state({"warsun": 1}, planets, ["x89c4", "ps", "ws"])
    state = invasion.begin_invasion(state, grid, registry)
    groups = invasion.bombard_groups(state, registry)
    assert [(g.base_type, g.dice_per_unit) for g in groups] == [("warsun", 3)]
    # Jedna jednostka = jeden przydział (jedna planeta): nie da się rozbić kości War Sun.
    with pytest.raises(ValueError):
        invasion.bombard(
            state, grid, registry,
            [BombardAssignment("warsun", _PL1, 1), BombardAssignment("warsun", _PL2, 1)],
        )
    item = BombardAssignment("warsun", _PL1, 1)
    done = invasion.bombard(state, grid, registry, [item], plasma_unit=item.key)
    entries = _bombard_log(done)
    assert [e["planet"] for e in entries] == [_PL1]
    assert sum(len(r["dice"]) for r in entries[0]["rolls"]) == 4  # 3 War Sun + 1 Plasma Scoring


# ============================================================================ Plasma Scoring


@ruling("C_technology/plasma-scoring/1.1")
def test_plasma_scoring_one_die_per_bombardment_on_many_planets(
    registry: StaticDataRegistry,
) -> None:
    grid = inv_grid()
    planets = {_PL1: {"p2": {"infantry": 1}}, _PL2: {"p2": {"infantry": 1}}}
    state = _bombard_state({"dreadnought": 2}, planets, ["ps"])
    state = invasion.begin_invasion(state, grid, registry)
    first = BombardAssignment("dreadnought", _PL1, 1)
    second = BombardAssignment("dreadnought", _PL2, 1)
    done = invasion.bombard(state, grid, registry, [first, second], plasma_unit=first.key)
    entries = _bombard_log(done)
    dice = {e["planet"]: sum(len(r["dice"]) for r in e["rolls"]) for e in entries}
    assert dice == {_PL1: 2, _PL2: 1}  # JEDNA kość Plasma Scoring na całe bombardowanie


@ruling("C_technology/plasma-scoring/1.2")
def test_plasma_scoring_adds_a_die_on_each_defending_planet(registry: StaticDataRegistry) -> None:
    grid = inv_grid()
    state = inv_state(
        {"p1": {"infantry": 2}},
        {_PL1: {"p2": {"pds": 1}}, _PL2: {"p2": {"pds": 1}}},
        {_PL1: "p2", _PL2: "p2"},
    )
    state.players["p2"].technologies = ["ps"]
    state = invasion.begin_invasion(state, grid, registry)
    state = invasion.commit_ground_forces(
        state, registry, {_PL1: {"infantry": 1}, _PL2: {"infantry": 1}}
    )
    state = invasion.advance(state, grid, registry)
    for planet in (_PL1, _PL2):
        shooter = invasion.defense_shooters(state, registry, planet)[0]
        state = invasion.defense_fire(state, grid, registry, planet, plasma_unit=shooter.key)
        assert state.invasion is not None
        roll = state.invasion.log[-1]["rolls"][0]
        assert roll["extraDice"] == 1 and len(roll["dice"]) == 2
        if state.invasion.defense_pending.get(planet, 0):
            need = invasion.required_defense_hits(state, grid, registry, planet)
            state = invasion.assign_defense_hits(
                state, grid, registry, planet, sustain={}, destroy={"infantry": need},
                destroy_damaged={},
            )


# ========================================================================= AI Development Algorithm


@ruling(
    "C_technology/ai-development-algorithm/1", "C_technology/ai-development-algorithm/1.1"
)
def test_aida_alone_researches_destroyer_ii(registry: StaticDataRegistry) -> None:
    state = research_state(registry, [technology.AIDA], [])
    assert technology.prerequisites(registry.technologies["dd2"]) == {"WARFARE": 2}
    done = technology.research(state, registry, "p1", "dd2", [technology.AIDA_SKIP])
    assert "dd2" in done.players["p1"].technologies
    assert technology.AIDA in done.players["p1"].exhausted_technologies


# =========================================================================== Self-Assembly Routines


def _sar_state(techs: list[str]) -> GameState:
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={"p1": PlayerState(player_id="p1", color="red", technologies=techs)},
        systems={
            "101": SystemState(
                position="101", system_id="20", planet_owners={"pl": "p1"},
                planet_units={"pl": {"p1": {"mech": 2, "spacedock": 1}}},
            ),
            "102": SystemState(position="102", system_id="22"),
        },
    )


def test_self_assembly_trade_goods_one_at_a_time_even_when_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _sar_state(["sar"])
    state.players["p1"].exhausted_technologies = ["sar"]
    gains: list[int] = []
    real = economy.gain_trade_goods

    def spy(st: GameState, pid: str, amount: int, *a: Any, **k: Any) -> Any:
        gains.append(amount)
        return real(st, pid, amount, *a, **k)

    monkeypatch.setattr(economy, "gain_trade_goods", spy)
    unit_ops.remove_units(state, state.systems["101"], "pl", "p1", "mech", 2, UnitCause.DESTROYED)
    assert gains == [1, 1] and state.players["p1"].trade_goods == 2


def _sar_offer(state: GameState) -> Any:
    triggers.fire(
        state, GameEvent.PRODUCTION_USED, Moment.AFTER, subject="p1",
        ctx={"player": "p1", "position": "101"},
    )
    assert len(state.pending_offers) == 1
    return state.pending_offers[0]


@ruling("C_technology/selfassembly-routines/1")
def test_self_assembly_mech_only_on_a_planet(registry: StaticDataRegistry) -> None:
    from src.core import offers

    state = _sar_state(["sar"])
    offer = _sar_offer(state)
    view = offers.offer_view(state, registry, offer)
    assert [o["value"] for o in view["inputs"][0]["options"]] == ["pl"]
    no_planet = _sar_state(["sar"])
    triggers.fire(
        no_planet, GameEvent.PRODUCTION_USED, Moment.AFTER, subject="p1",
        ctx={"player": "p1", "position": "102"},
    )
    assert no_planet.pending_offers == []


@ruling("C_technology/selfassembly-routines/2")
def test_self_assembly_takes_a_mech_from_a_system_without_own_token() -> None:
    state = _sar_state(["sar"])
    state.systems["101"].planet_units["pl"]["p1"]["mech"] = 1
    state.systems["102"].planet_units = {"x": {"p1": {"mech": 3}}}
    state.systems["103"] = SystemState(
        position="103", system_id="23", command_tokens=["p1"],
        planet_units={"y": {"p1": {"mech": 0}}},
    )
    damage.set_damaged(state.systems["102"], "x", "p1", "mech", 1)
    assert production.reinforcements_left(state, "p1", "mech") == 0
    offer = _sar_offer(state)
    done = triggers.accept_offer(state, "p1", offer.id, {"planet": "pl", "from": "102|x"})
    assert done.systems["101"].planet_units["pl"]["p1"]["mech"] == 2
    assert done.systems["102"].planet_units["x"]["p1"]["mech"] == 2
    assert damage.damaged_count(done.systems["101"], "pl", "p1", "mech") == 0  # nieuszkodzony
    blocked = _sar_state(["sar"])
    blocked.systems["101"].planet_units["pl"]["p1"]["mech"] = 1
    blocked.systems["102"].planet_units = {"x": {"p1": {"mech": 3}}}
    blocked.systems["102"].command_tokens = ["p1"]
    offer = _sar_offer(blocked)
    with pytest.raises(ValueError):
        triggers.accept_offer(blocked, "p1", offer.id, {"planet": "pl", "from": "102|x"})


# ============================================================================ Duranium Armor


def _round_end(state: GameState, kind: str = "space", planet: str = "") -> None:
    triggers.fire(
        state, GameEvent.COMBAT_ROUND, Moment.END,
        ctx={
            "kind": kind, "round": 1, "position": "000", "planet": planet,
            "attacker": "p1", "defender": "p2", "phase": "combat", "sustained": {},
        },
    )


def _accept_repair(state: GameState, unit: str) -> GameState:
    if not state.pending_offers:
        return state
    offer = state.pending_offers[0]
    return triggers.accept_offer(state, offer.player_id, offer.id, {"unit": unit})


@ruling("C_technology/duranium-armor/5")
def test_duranium_repairs_unit_damaged_without_sustain_this_round() -> None:
    state = _techs(battle_state({"p1": {"dreadnought": 2}, "p2": {"cruiser": 1}}), "p1", "da")
    system = state.systems["000"]
    damage.set_damaged(system, "space", "p1", "dreadnought", 2)
    triggers.fire(
        state, GameEvent.COMBAT_ROUND, Moment.END,
        ctx={"kind": "space", "round": 1, "position": "000", "planet": "", "attacker": "p1",
             "defender": "p2", "phase": "combat", "sustained": {"p1": {"dreadnought": 1}}},
    )
    state = _accept_repair(state, "dreadnought")
    assert damage.damaged_count(state.systems["000"], "space", "p1", "dreadnought") == 1


@ruling("C_technology/duranium-armor/6")
def test_duranium_repairs_only_units_in_the_combat() -> None:
    state = _techs(battle_state({"p1": {"dreadnought": 1}, "p2": {"cruiser": 1}}), "p1", "da")
    system = state.systems["000"]
    system.planet_units["pl"] = {"p1": {"mech": 1}}
    damage.set_damaged(system, "pl", "p1", "mech", 1)
    _round_end(state)  # walka kosmiczna: mech na planecie nie uczestniczy
    assert damage.damaged_count(state.systems["000"], "pl", "p1", "mech") == 1


@ruling("C_technology/duranium-armor/5")
def test_duranium_repairs_unit_without_sustain_damage() -> None:
    state = _techs(battle_state({"p1": {"carrier": 1}, "p2": {"cruiser": 1}}), "p1", "da")
    damage.set_damaged(state.systems["000"], "space", "p1", "carrier", 1)
    _round_end(state)
    state = _accept_repair(state, "carrier")
    assert damage.damaged_count(state.systems["000"], "space", "p1", "carrier") == 0


# ============================================================================ Assault Cannon


@ruling("C_technology/assault-cannon/3")
def test_assault_cannon_condition_checked_when_it_resolves() -> None:
    state = battle_state({"p1": {"cruiser": 2}, "p2": {"cruiser": 1}})
    _techs(state, "p1", "asc")
    ctx = {"kind": "space", "position": "000", "attacker": "p1", "defender": "p2"}
    assert not combat_hooks._assault_cannon_ready(state, "p1", ctx)
    state.systems["000"].space_units["p1"]["destroyer"] = 1  # efekt dokłada statek na starcie
    assert combat_hooks._assault_cannon_ready(state, "p1", ctx)


@ruling("C_technology/assault-cannon/4")
def test_assault_cannon_sustain_damage_does_not_save_the_ship(
    registry: StaticDataRegistry,
) -> None:
    state = _techs(battle_state({"p1": {"cruiser": 3}, "p2": {"dreadnought": 2}}), "p1", "asc")
    started = battle.start_combat(state, battle_grid(), registry)
    if started.pending_offers:  # ofiara wybiera statek (tu jeden typ)
        offer = started.pending_offers[0]
        started = triggers.accept_offer(started, offer.player_id, offer.id, {"ship": "dreadnought"})
    system = started.systems["000"]
    assert system.space_units["p2"] == {"dreadnought": 1}
    assert damage.damaged_count(system, "space", "p2", "dreadnought") == 0


# ============================================================================ Sarween Tools


@ruling("C_technology/sarween-tools/1")
def test_sarween_no_discount_without_production_ability(registry: StaticDataRegistry) -> None:
    from src.core.game_state import ProductionGrant
    from src.core.production import ProductionOrder, order_cost

    state = GameState(
        active_system="000",
        players={"p1": PlayerState(player_id="p1", color="red", technologies=[])},
    )
    state.production_grant = ProductionGrant(
        player_id="p1", position="000", units=1, free=True, ships_only=True, source="Sling Relay"
    )
    orders = [ProductionOrder("cruiser", 1)]
    base = order_cost(state, registry, "p1", orders)
    state.players["p1"].technologies = ["st"]
    assert order_cost(state, registry, "p1", orders) == base


# ========================================================================== Predictive Intelligence


@ruling("C_technology/predictive-intelligence/1")
def test_predictive_intelligence_redistribution_needs_a_ready_card() -> None:
    state = _fl_state(["pi"])
    state.players["p1"].exhausted_technologies = ["pi"]
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    assert state.pending_offers == []


@ruling("R_fleet_pool/rules-reference/3")
def test_predictive_intelligence_fleet_pool_limit_applies_at_once(
    registry: StaticDataRegistry,
) -> None:
    state = _fl_state(["pi"])
    state.systems["101"] = SystemState(
        position="101", system_id="20", space_units={"p1": {"cruiser": 3}}
    )
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    offer = state.pending_offers[0]
    player = state.players["p1"]
    total = player.tactical_cc + player.fleet_cc + player.strategic_cc
    done = triggers.accept_offer(
        state, "p1", offer.id, {"tactical": total - 1, "fleet": 1, "strategic": 0}
    )
    checked = limits.enforce_limits(done, registry)
    window = checked.pending_window
    assert window is not None and window.window_type.name == "FLEET_POOL"


# ============================================================================ Transit Diodes


@ruling(
    "C_technology/transit-diodes/1",
    "C_technology/transit-diodes/2",
    "C_technology/transit-diodes/3",
    "C_technology/transit-diodes/4",
    "C_technology/transit-diodes/5",
)
def test_transit_diodes_sources_and_destinations() -> None:
    from tests.test_technologies_actions import _td_offer, _td_state

    state = _td_state()
    state.systems["101"].command_tokens = ["p1"]  # system z własnym żetonem - wolno brać
    state.systems["103"] = SystemState(
        position="103", system_id="23", space_units={"p1": {"mech": 1}}
    )
    damage.set_damaged(state.systems["103"], "space", "p1", "mech", 1)
    state.systems["102"].planet_owners["c"] = "p1"
    offer = _td_offer(state)
    params = {
        "unit1": "101|a|infantry", "to1": "102|b",
        "unit2": "103|space|mech", "to2": "102|c",
        "unit3": "", "to3": "", "unit4": "", "to4": "",
    }
    done = triggers.accept_offer(state, "p1", offer.id, params)
    target = done.systems["102"]
    assert target.planet_units["b"]["p1"] == {"infantry": 1}
    assert target.planet_units["c"]["p1"] == {"mech": 1}
    assert damage.damaged_count(target, "c", "p1", "mech") == 1  # nadal uszkodzony


# ============================================================================ Integrated Economy


def _ie_state(registry: StaticDataRegistry) -> tuple[GameState, str]:
    system_id, planet = next(
        (s.id, p)
        for s in registry.systems.values()
        for p in s.planets
        if (registry.planets[p].resources or 0) >= 2
    )
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(
                player_id="p1", color="red", technologies=["ie"], trade_goods=6,
                controlled_planets=[planet],
            ),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems={
            "101": SystemState(position="101", system_id=system_id, planet_owners={planet: "p1"})
        },
    )
    ctx = {"player": "p1", "planet": planet, "position": "101", "previous": None}
    triggers.fire(state, GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, subject="p1", ctx=ctx)
    offer = state.pending_offers[0]
    return triggers.accept_offer(state, "p1", offer.id, {}), planet


@ruling(
    "C_technology/integrated-economy/1",
    "C_technology/integrated-economy/2",
    )
def test_integrated_economy_paid_any_number_fighters_in_pairs(
    registry: StaticDataRegistry,
) -> None:
    state, planet = _ie_state(registry)
    cap = int(registry.planets[planet].resources or 0)
    done = production.produce(
        state, HexGrid(), registry, "p1", [production.ProductionOrder("infantry", 2 * cap, planet)]
    )
    assert done.systems["101"].planet_units[planet]["p1"] == {"infantry": 2 * cap}
    paid = 6 - done.players["p1"].trade_goods
    if planet in done.players["p1"].exhausted_planets:
        paid += cap
    assert paid >= cap  # opłacone (2 piechoty = 1 zasób)
    with pytest.raises(ValueError, match="exceeds"):
        production.produce(
            state, HexGrid(), registry, "p1",
            [production.ProductionOrder("infantry", 2 * cap + 1, planet)],
        )


@ruling("C_technology/integrated-economy/4")
def test_integrated_economy_ships_blocked_by_enemy_ships(registry: StaticDataRegistry) -> None:
    state, _planet = _ie_state(registry)
    state.systems["101"].space_units["p1"] = {"carrier": 1}  # pojemność (inaczej 39.6 C5)
    ok = production.produce(
        state, HexGrid(), registry, "p1", [production.ProductionOrder("fighter", 2)]
    )
    assert ok.systems["101"].space_units["p1"] == {"carrier": 1, "fighter": 2}
    state.systems["101"].space_units["p2"] = {"destroyer": 1}
    with pytest.raises(ValueError, match="enemy ships"):
        production.produce(
            state, HexGrid(), registry, "p1", [production.ProductionOrder("fighter", 2)]
        )


# ============================================================================ Graviton Laser System


@ruling("R_space_cannon/notes/5")
def test_capacity_resolved_after_each_space_cannon_player(registry: StaticDataRegistry) -> None:
    """Po przypisaniu trafień jednego strzelca nadwyżkę ładunku usuwa się, zanim strzeli kolejny."""
    from src.core import space_cannon
    from tests.test_space_cannon import _grid as sc_grid
    from tests.test_space_cannon import _state as sc_state

    for seed in range(1, 200):
        state = sc_state(
            pds={"p2": 3}, pds_adjacent={"p3": 3},
            ships={"p1": {"carrier": 1, "fighter": 2}}, seed=seed,
        )
        opened = space_cannon.open_offense(state, sc_grid(), registry)
        fired = space_cannon.fire_offense(opened, sc_grid(), registry, "p2", "p1")
        if space_cannon.pending_hits(fired) is None:
            continue
        need = space_cannon.required_hits(fired, "p1", registry)
        if need != 1:
            continue
        done = space_cannon.assign_hits(fired, "p1", {"carrier": 1}, registry=registry)
        window = done.pending_window
        assert window is not None and window.window_type.name == "CAPACITY"
        return
    raise AssertionError("no seed with exactly one Space Cannon hit")
