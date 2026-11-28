"""Technologie ogólne — rulingi ``docs/rules_tirules/C_technology.md`` punkt po punkcie.

Każdy test oznacza ``@ruling(...)`` punkty, które sprawdza (strażnik
``tests/test_ruling_coverage.py``, kontrakt ogólny). Podstawowe testy technologii są w
``tests/test_technologies_*.py`` (tam też część oznaczeń); statusy bez testu:
``tests/rulings_status.json``.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from src.core import (
    action_budget,
    active_effects,
    battle,
    card_draw,
    component_action,
    damage,
    economy,
    invasion,
    limits,
    movement,
    production,
    rules_hooks,
    tactical,
    technology,
    triggers,
    turn_flow,
    unit_ops,
)
from src.core.game_events import Duration, GameEvent, Moment
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


@ruling("C_technology/antimass-deflectors/2")
def test_antimass_lost_units_may_leave_an_asteroid_field_but_not_enter(
    registry: StaticDataRegistry,
) -> None:
    from tests.test_movement import _line_grid, _state_with_destroyer_at

    # Statki stoją w polu asteroid (zyskały i utraciły Antimass): wylatują, ale nie wlatują.
    leave_grid = _line_grid([("000", "18", set()), ("101", "20", {"ASTEROID_FIELD"})])
    state = _state_with_destroyer_at("101", "000")
    state.players["p1"].technologies = []
    ok, reason = movement.can_move(state, leave_grid, registry, "101", "destroyer", "p1")
    assert ok, reason
    enter_grid = _line_grid([("000", "18", {"ASTEROID_FIELD"}), ("101", "20", set())])
    ok, _ = movement.can_move(state, enter_grid, registry, "101", "destroyer", "p1")
    assert not ok


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


# ============================================================================ Gravity Drive


@ruling("C_technology/gravity-drive/1")
def test_gravity_drive_stacks_with_flank_speed(registry: StaticDataRegistry) -> None:
    grid = battle_grid()
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={"p1": PlayerState(player_id="p1", color="red", technologies=["gd"])},
    )

    def move_value(boost: bool) -> int | None:
        return movement._effective_move_value(
            state, grid, registry, "000", "cruiser", "p1", boost=boost, tempesta=False
        )

    base = move_value(False)
    assert base is not None
    assert move_value(True) == base + 1  # sam Gravity Drive
    active_effects.add_effect(state, "action_cards:fs1", Duration.TACTICAL_ACTION, owner="p1")
    assert move_value(False) == base + 1  # sam Flank Speed
    assert move_value(True) == base + 2  # oba razem: +2


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


@ruling("C_technology/fleet-logistics/5")
def test_fleet_logistics_second_action_waits_for_the_strategic_secondary() -> None:
    from src.core.game_state import StrategyResolution

    state = component_action.play_component_action(_fl_state(["fl"]), "p1")
    assert action_budget.actions_left(state, "p1") == 1
    # Pierwsza akcja = strategiczna: dopóki trwają secondary, druga akcja nie może się zacząć.
    state.pending_strategy = StrategyResolution(initiative=1, owner_id="p1", step="x")
    with pytest.raises(ValueError, match="Finish your current action"):
        action_budget.require_free_action(state, "p1")
    state.pending_strategy = None
    action_budget.require_free_action(state, "p1")  # po secondary druga akcja jest wolna


# ============================================================================ Light/Wave Deflector


def _lwd_pickup_state() -> GameState:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={
            "p1": PlayerState(player_id="p1", color="red", technologies=["cv2", "lwd"]),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems={
            "201": SystemState(position="201", system_id="21", space_units={"p1": {"carrier": 1}}),
            "101": SystemState(
                position="101", system_id="20",
                space_units={"p2": {"destroyer": 1}},
                planet_units={"pl": {"p1": {"infantry": 2}}},
                planet_owners={"pl": "p1"},
            ),
        },
    )
    state.players["p1"].controlled_planets = ["pl"]
    return state


@ruling("C_technology/light-wave-deflector/1")
def test_light_wave_ship_may_pick_up_units_in_a_system_with_foreign_ships(
    registry: StaticDataRegistry,
) -> None:
    from tests.test_technologies_combat import _far_grid

    grid = _far_grid()
    route = ["201", "101", "000"]
    pickup = movement.CargoPickup("infantry", 2, "pl", "101")
    done = movement.move_fleet(
        _lwd_pickup_state(), grid, registry, "201", {"carrier": 1}, [pickup], "p1", route=route
    )
    assert done.systems["000"].space_units["p1"] == {"carrier": 1, "infantry": 2}
    assert done.systems["101"].space_units["p2"] == {"destroyer": 1}  # statek wroga stoi dalej
    # Bez Light/Wave Deflector ten sam przelot jest zablokowany.
    blocked = _lwd_pickup_state()
    blocked.players["p1"].technologies = ["cv2"]
    with pytest.raises(ValueError):
        movement.move_fleet(
            blocked, grid, registry, "201", {"carrier": 1}, [pickup], "p1", route=route
        )


@ruling("C_technology/light-wave-deflector/2")
def test_light_wave_does_not_allow_production_next_to_foreign_ships(
    registry: StaticDataRegistry,
) -> None:
    state, _planet = _ie_state(registry)
    state.players["p1"].technologies.append("lwd")
    state.systems["101"].space_units["p1"] = {"carrier": 1}
    state.systems["101"].space_units["p2"] = {"destroyer": 1}
    with pytest.raises(ValueError, match="enemy ships"):
        production.produce(
            state, HexGrid(), registry, "p1", [production.ProductionOrder("fighter", 2)]
        )


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


@ruling(
    "C_technology/neural-motivator/1.1",
    "C_technology/neural-motivator/1.2",
    "C_technology/neural-motivator/1.3",
    "C_technology/neural-motivator/1.4",
)
def test_neural_motivator_does_not_change_other_action_card_draws(
    registry: StaticDataRegistry,
) -> None:
    from src.core import exploration
    from src.core.hooks import relics_combat
    from src.core.strategy_cards import politics
    from tests.test_exploration import _IND, _with_card
    from tests.test_exploration import _state as exploration_state

    def hand(state: GameState) -> int:
        return len(state.players["p1"].private.action_cards)

    # 1.1 Politics: secondary dobiera stałą liczbę kart niezależnie od technologii.
    plain = GameState(players={"p1": PlayerState(player_id="p1", color="red")})
    plain.decks.action_card_deck = ["a1", "a2", "a3", "a4", "a5", "a6"]
    with_nm = plain.clone()
    with_nm.players["p1"].technologies = ["nm"]
    politics._secondary(plain, None, "p1", {})  # type: ignore[arg-type]
    politics._secondary(with_nm, None, "p1", {})  # type: ignore[arg-type]
    assert hand(plain) == hand(with_nm) == politics.ACTION_CARDS_DRAWN

    # 1.2 Minister of Policy.
    policy = GameState(
        players={"p1": PlayerState(player_id="p1", color="red", technologies=["nm"])}
    )
    policy.decks.action_card_deck = ["a1", "a2", "a3"]
    agendas_laws._policy(policy, "p1", {})
    assert hand(policy) == 1

    # 1.3 Functioning Base.
    base = _with_card(exploration_state(), registry, "Functioning Base", _IND)
    base.players["p1"].technologies = ["nm"]
    base.decks.action_card_deck = ["ac1", "ac2", "ac3"]
    base.players["p1"].trade_goods = 1
    assert hand(exploration.resolve(base, registry, "draw_tg")) == 1

    # 1.4 The Prophet's Tears.
    tears = GameState(
        players={
            "p1": PlayerState(
                player_id="p1", color="red", technologies=["nm"], relics=["prophetstears"]
            )
        }
    )
    tears.decks.action_card_deck = ["a1", "a2", "a3"]
    relics_combat.prophets_tears_draw(tears, "p1", {})
    assert hand(tears) == 1


# ============================================================================ Hyper Metabolism


@ruling("C_technology/hyper-metabolism/1")
def test_hyper_metabolism_gives_three_command_tokens_instead_of_two() -> None:
    state = GameState(
        players={
            "p1": PlayerState(player_id="p1", color="red", technologies=["hm"]),
            "p2": PlayerState(player_id="p2", color="blue"),
        }
    )
    point = rules_hooks.POINT_STATUS_COMMAND_TOKENS
    assert rules_hooks.modify(point, state, "p1", 2) == 3
    assert rules_hooks.modify(point, state, "p2", 2) == 2


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


@ruling("C_technology/x89-bacterial-weapon-omega-omega/5")
def test_x89_exhausts_the_bombarders_own_planet_with_coexisting_enemy_units() -> None:
    state = _techs(battle_state({"p1": {"dreadnought": 1}}), "p1", "x89c4")
    state.players["p1"].controlled_planets = ["pl"]  # planeta p1 z jednostkami p2 (coexist)
    triggers.fire(
        state, GameEvent.UNIT_ABILITY_USED, Moment.AFTER, subject="p1",
        ctx={"ability": "bombardment", "player": "p1", "position": "000", "planets": ["pl"]},
    )
    assert state.players["p1"].exhausted_planets == ["pl"]


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


@ruling(
    "C_technology/plasma-scoring/2", "R_coexistence/notes/11", "R_coexistence/notes/11.1",
    "R_coexistence/notes/11.2",
)
def test_plasma_scoring_one_die_against_coexisting_players(registry: StaticDataRegistry) -> None:
    grid = inv_grid()
    planets = {_PL1: {"p2": {"infantry": 1}, "p3": {"infantry": 2}}}
    base = _bombard_state({"dreadnought": 3}, planets, ["ps"])
    base.players["p3"] = PlayerState(player_id="p3", color="p3")
    base = invasion.begin_invasion(base, grid, registry)
    # Each unit picks whose units it bombards (11.1): two at p2, one at p3.
    vs_p2 = BombardAssignment("dreadnought", _PL1, 2, "p2")
    vs_p3 = BombardAssignment("dreadnought", _PL1, 1, "p3")

    def run(state: GameState) -> GameState:
        return invasion.bombard(state, grid, registry, [vs_p2, vs_p3], plasma_unit=vs_p3.key)

    done = _seek(base, run, lambda s: _bombard_log(s)[0]["hits"] == 2)
    entries = {e["defender"]: e for e in _bombard_log(done)}
    dice = {pid: sum(len(r["dice"]) for r in e["rolls"]) for pid, e in entries.items()}
    assert dice == {"p2": 2, "p3": 2}  # separate rolls; Plasma Scoring adds 1 die to ONE of them
    assert done.invasion is not None
    # 11.2: two hits on p2's single infantry - the surplus does not reach p3's units.
    assert invasion.required_bombard_hits(done, grid, registry, _PL1, "p2") == 1
    after = invasion.assign_bombard_hits(
        done, grid, registry, _PL1, "p2", sustain={}, destroy={"infantry": 1}, destroy_damaged={},
    )
    assert after.systems["000"].planet_units[_PL1]["p3"] == {"infantry": 2}
    # Without a choice, "Auto" bombards the planet's controller.
    auto = invasion.bombard(base, grid, registry, [BombardAssignment("dreadnought", _PL1, 3)])
    assert {e["defender"] for e in _bombard_log(auto)} == {"p2"}
    with pytest.raises(ValueError, match="no ground forces"):
        invasion.bombard(base, grid, registry, [BombardAssignment("dreadnought", _PL1, 3, "p1")])


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


@ruling("C_technology/assault-cannon/3.1")
def test_assault_cannon_after_other_players_start_of_combat_abilities(
    registry: StaticDataRegistry,
) -> None:
    """Assault Cannon waits for the other players' start-of-combat abilities (a window after the
    ship-adding abilities) and only then resolves."""
    from src.core.hooks.factions import mentak

    state = _techs(battle_state({"p1": {"cruiser": 3}, "p2": {"dreadnought": 2}}), "p1", "asc")
    state.players["p2"].faction = "mentak"
    state.players["p2"].leader_states[mentak.HERO] = "unlocked"
    started = battle.start_combat(state, battle_grid(), registry)
    sleeper = next(o for o in started.pending_offers if "Sleeper Cell" in o.label)
    # Assault Cannon has not resolved yet: p2 still has both dreadnoughts.
    assert started.systems["000"].space_units["p2"] == {"dreadnought": 2}
    assert started.active_combat is not None and started.active_combat.step.value == "TRIGGERS"
    declined = triggers.decline_offer(started, "p2", sleeper.id)
    declined = battle.resume_after_triggers(declined, battle_grid(), registry)
    if declined.pending_offers:  # the victim picks the ship (one type here)
        offer = declined.pending_offers[0]
        declined = triggers.accept_offer(declined, offer.player_id, offer.id,
                                         {"ship": "dreadnought"})
        declined = battle.resume_after_triggers(declined, battle_grid(), registry)
    assert declined.systems["000"].space_units["p2"] == {"dreadnought": 1}


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


@ruling("C_technology/sling-relay/2")
def test_sling_relay_cannot_be_used_without_producing_a_ship(
    registry: StaticDataRegistry,
) -> None:
    from tests.test_technologies_actions import _dock_state

    done = component_action.play_component_action(
        _dock_state(["sr"]), "p1", "sr", params={"system": "101"}
    )
    with pytest.raises(ValueError, match="cannot be used without producing"):
        production.skip_grant(done)
    assert done.production_grant is not None  # the grant stays open until a ship is produced


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


def _ie_state(
    registry: StaticDataRegistry, attachments: list[str] | None = None
) -> tuple[GameState, str]:
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
    if attachments:
        state.planet_attachments[planet] = list(attachments)
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


@ruling("C_technology/integrated-economy/3")
def test_integrated_economy_uses_resources_including_explored_attachments(
    registry: StaticDataRegistry,
) -> None:
    from tests.test_exploration import _card_id

    plain, planet = _ie_state(registry)
    assert plain.production_grant is not None
    base = plain.production_grant.max_cost
    assert base is not None
    attached, _ = _ie_state(registry, [_card_id(registry, "Mining World")])
    assert attached.production_grant is not None
    assert attached.production_grant.max_cost is not None
    assert attached.production_grant.max_cost > base  # attachment z eksploracji podnosi limit


@ruling("C_technology/integrated-economy/5")
def test_integrated_economy_is_not_a_production_ability_so_sarween_does_not_apply(
    registry: StaticDataRegistry,
) -> None:
    orders = [production.ProductionOrder("cruiser", 1)]
    state, _planet = _ie_state(registry)
    assert state.production_grant is not None and state.production_grant.source == (
        "Integrated Economy"
    )
    base = production.order_cost(state, registry, "p1", orders)
    state.players["p1"].technologies.append("st")
    assert production.order_cost(state, registry, "p1", orders) == base


@ruling("C_technology/integrated-economy/6")
def test_integrated_economy_limit_uses_printed_cost_with_navarch_feng(
    registry: StaticDataRegistry,
) -> None:
    """Navarch Feng makes the Nomad flagship free to produce, but its cost stays 8: it does not
    fit under Integrated Economy's limit of the planet's resource value."""
    state, planet = _ie_state(registry)
    p1 = state.players["p1"]
    p1.faction = "nomad"
    p1.leader_states = {**p1.leader_states, "nomadcommander": "unlocked"}
    cap = int(registry.planets[planet].resources or 0)
    flagship = [production.ProductionOrder("flagship", 1)]
    assert production.order_cost(state, registry, "p1", flagship) == 0  # nothing is spent
    assert production.printed_order_cost(state, registry, "p1", flagship) == 8 > cap
    with pytest.raises(ValueError, match="exceeds"):
        production.produce(state, HexGrid(), registry, "p1", flagship)
    # Units that fit at their printed cost are still produced (and paid for).
    infantry = [production.ProductionOrder("infantry", 2, planet)]
    done = production.produce(state, HexGrid(), registry, "p1", infantry)
    assert done.systems["101"].planet_units[planet]["p1"] == {"infantry": 2}


# ============================================================================ Graviton Laser System


def _gls_one_hit(
    registry: StaticDataRegistry, *, pds: dict[str, int], plasma: bool = False
) -> GameState:
    from src.core import space_cannon
    from tests.test_space_cannon import _grid as sc_grid
    from tests.test_space_cannon import _state as sc_state

    for seed in range(1, 300):
        state = sc_state(
            pds=pds, techs={"p2": ["gls", "ps"] if plasma else ["gls"]}, seed=seed,
            ships={"p1": {"dreadnought": 2, "fighter": 2}},
        )
        opened = space_cannon.open_offense(state, sc_grid(), registry)
        unit = space_cannon.offense_shooters(opened, sc_grid(), registry, "p2")[0].key
        fired = space_cannon.fire_offense(
            opened, sc_grid(), registry, "p2", "p1", exhaust_gls=True,
            plasma_unit=unit if plasma else None,
        )
        pending = space_cannon.pending_hits(fired)
        if pending is not None and pending.hits == 1:
            return fired
    raise AssertionError("no seed with exactly one Space Cannon hit")


@ruling("C_technology/graviton-laser-system/1")
def test_graviton_laser_has_no_effect_in_space_cannon_defense(
    registry: StaticDataRegistry,
) -> None:
    grid = inv_grid()
    state = inv_state({"p1": {"infantry": 2}}, {_PL1: {"p2": {"pds": 2}}}, {_PL1: "p2"})
    _techs(state, "p2", "gls")
    state = invasion.begin_invasion(state, grid, registry)
    state = invasion.commit_ground_forces(state, registry, {_PL1: {"infantry": 2}})
    state = invasion.advance(state, grid, registry)
    state = invasion.defense_fire(state, grid, registry, _PL1)
    assert "gls" not in state.players["p2"].exhausted_technologies  # nic nie wyczerpuje
    assert state.invasion is not None
    if state.invasion.defense_pending.get(_PL1, 0):  # trafienia idą tylko w siły naziemne
        need = invasion.required_defense_hits(state, grid, registry, _PL1)
        invasion.assign_defense_hits(
            state, grid, registry, _PL1, sustain={}, destroy={"infantry": need},
            destroy_damaged={},
        )


@ruling("C_technology/graviton-laser-system/2")
def test_graviton_laser_hits_may_still_be_cancelled_by_sustain_damage(
    registry: StaticDataRegistry,
) -> None:
    from src.core import space_cannon

    fired = _gls_one_hit(registry, pds={"p2": 3})
    assert "gls" in fired.players["p2"].exhausted_technologies
    with pytest.raises(ValueError, match="non-fighter"):
        space_cannon.assign_hits(fired, "p1", {"fighter": 1})
    done = space_cannon.assign_hits(fired, "p1", sustain={"dreadnought": 1}, registry=registry)
    system = done.systems["000"]
    assert system.space_units["p1"] == {"dreadnought": 2, "fighter": 2}  # nic nie zginęło
    assert damage.damaged_count(system, "space", "p1", "dreadnought") == 1


@ruling("C_technology/graviton-laser-system/3")
def test_graviton_laser_applies_to_all_dice_including_other_units_cannons(
    registry: StaticDataRegistry,
) -> None:
    from src.core import space_cannon

    # GLS obejmuje KAŻDĄ kość rzutu, także dodatkową kość Plasma Scoring (a nie tylko bazowe).
    fired = _gls_one_hit(registry, pds={"p2": 2}, plasma=True)
    roll = space_cannon.read_log(fired)[0]["rolls"][0]
    assert roll["extraDice"] == 1 and len(roll["dice"]) == 3
    with pytest.raises(ValueError, match="non-fighter"):
        space_cannon.assign_hits(fired, "p1", {"fighter": 1})


@ruling("C_technology/plasma-scoring/3")
def test_plasma_scoring_adds_a_die_to_experimental_battlestation(
    registry: StaticDataRegistry,
) -> None:
    from src.core import action_cards, space_cannon
    from src.core.hex_grid import HexGrid
    from tests.test_reactions_invasion import _at_space_cannon, _move_state

    grid = HexGrid()

    def shot(plasma: bool) -> dict[str, Any]:
        state = _move_state(seed=1)
        _techs(state, "p2", "ps")
        params: dict[str, Any] = {"dock": {"position": "000", "zone": _PL1}}
        played, _ = action_cards.play_action_card(state, registry, "p2", "experimental", params)
        opened = _at_space_cannon(played, grid, registry)
        (dock,) = space_cannon.offense_shooters(opened, grid, registry, "p2")
        assert space_cannon.plasma_extra_dice(opened, dock) == 1  # offered in the Offense panel
        done = space_cannon.fire_offense(
            opened, grid, registry, "p2", plasma_unit=dock.key if plasma else None
        )
        return cast("dict[str, Any]", space_cannon.read_log(done)[0]["rolls"][0])

    # The dock fires in the Space Cannon Offense step, where the player chooses Plasma Scoring.
    assert len(shot(True)["dice"]) == 4 and shot(True)["extraDice"] == 1  # SPACE CANNON 5(x3)+1
    assert len(shot(False)["dice"]) == 3


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
