"""Agendy — rulingi ``docs/rules_tirules/C_agendas.md`` (wormhole, ministrowie, karty M–Z).

Wspólne helpery: ``test_rulings_agendas.py``. Statusy bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    board_graph,
    economy,
    movement,
    neighbors,
    objectives,
    retreat,
    rules_hooks,
    space_cannon,
    tactical,
    technology,
    triggers,
    turn_flow,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, SystemState, TacticalStep
from src.core.hex_grid import HexGrid
from src.core.hooks import agendas_directives, agendas_laws
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause
from tests.rulings import ruling
from tests.rulings_general.test_rulings_agendas import (
    _accept,
    _inputs,
    _offer,
    _resolve,
    _state,
)
from tests.test_agenda_effects import _planet
from tests.test_agenda_effects import registry as registry  # noqa: F401 - fixture modułu

ALPHA, BETA, DELTA = "39", "40", "17"  # puste systemy z wormholem alpha / beta; Creuss Gate (delta)


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    previous = board_graph._PROVIDER
    yield
    board_graph.bind_grid_provider(previous)


def _bind(grid: HexGrid) -> HexGrid:
    board_graph.bind_grid_provider(lambda: grid)
    return grid


def _line(registry: StaticDataRegistry, *systems: tuple[str, str]) -> HexGrid:
    """Siatka z systemów ``(pozycja, id)``; 101 i 104 leżą naprzeciw siebie (nie sąsiadują)."""
    grid = HexGrid()
    for position, system_id in systems:
        definition = registry.systems[system_id]
        grid.place_system(position, system_id, wormholes=list(definition.wormholes),
                          anomalies=set(definition.anomalies))
    grid.build_edges()
    return _bind(grid)


def _wormhole_pair(registry: StaticDataRegistry, law: str, *, faction: str = "") -> tuple[
    GameState, HexGrid
]:
    """p1 z krążownikiem w alpha (101), aktywny drugi alpha (104) - połączenie TYLKO wormholem."""
    grid = _line(registry, ("101", ALPHA), ("104", ALPHA))
    assert grid.are_adjacent("101", "104") and grid.link_kind("101", "104") == "wormhole"
    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.active_player_id, state.active_system = "p1", "104"
    state.tactical_step = TacticalStep.MOVEMENT
    state.players["p1"].faction = faction or None
    state.systems = {
        "101": SystemState(position="101", system_id=ALPHA, space_units={"p1": {"cruiser": 1}}),
        "104": SystemState(position="104", system_id=ALPHA),
    }
    state.decks.agenda_laws = {law: "for"}
    return state, grid


def _route_ok(state: GameState, grid: HexGrid) -> bool:
    return movement.route_error(state, grid, ["101", "104"], "p1", "cruiser") is None


# ======================================================================= Enforced Travel Ban


@ruling("C_agendas/enforced-travel-ban/1", "C_agendas/nexus-sovereignty/1")
def test_travel_ban_does_not_affect_creuss(registry: StaticDataRegistry) -> None:
    state, grid = _wormhole_pair(registry, "travel_ban")
    assert not _route_ok(state, grid)
    state.players["p1"].faction = "ghost"
    assert _route_ok(state, grid)
    assert not rules_hooks.forbidden(
        rules_hooks.POINT_MOVEMENT_WORMHOLES_BLOCKED, state, "p1", {"position": "101"}
    )
    state.decks.agenda_laws = {"nexus": "for"}  # Nexus Sovereignty - to samo wyłączenie
    assert not rules_hooks.forbidden(
        rules_hooks.POINT_MOVEMENT_WORMHOLES_BLOCKED, state, "p1", {"position": "101"}
    )


@ruling("C_agendas/enforced-travel-ban/2", "C_agendas/wormhole-reconstruction/1")
def test_travel_ban_other_adjacency_still_works(registry: StaticDataRegistry) -> None:
    state, grid = _wormhole_pair(registry, "travel_ban")
    assert not _route_ok(state, grid)
    state.decks.agenda_laws["wormhole_recon"] = "for"  # przy Reconstruction zakaz nie działa
    assert _route_ok(state, grid)
    state.decks.agenda_laws = {"travel_ban": "for"}
    grid = _line(registry, ("101", ALPHA), ("104", BETA))  # alpha-beta: tylko Lost Star Chart
    state.systems["104"].system_id = BETA
    assert not _route_ok(state, grid)
    state.active_effects = []
    import src.core.hooks.reactions_tactical  # noqa: F401 - rejestracja efektów kart
    from src.core import active_effects
    from src.core.game_events import Duration

    active_effects.add_effect(state, "action_cards:lost_star", Duration.TURN,
                              owner="p1")
    assert rules_hooks.permits(rules_hooks.POINT_MOVEMENT_ALPHA_BETA_ADJACENT, state, "p1")
    assert _route_ok(state, grid)


@ruling("C_agendas/enforced-travel-ban/3", "C_agendas/nexus-sovereignty/2")
def test_travel_ban_blocks_retreat_through_wormholes(registry: StaticDataRegistry) -> None:
    state, grid = _wormhole_pair(registry, "travel_ban")
    state.systems["101"].command_tokens = []
    assert "101" not in retreat.retreat_destinations(state, grid, "104", "p1")
    assert movement.wormhole_link_blocked(grid, state, "p1", "104", "101")
    state.decks.agenda_laws = {}
    assert not movement.wormhole_link_blocked(grid, state, "p1", "104", "101")
    assert "101" in retreat.retreat_destinations(state, grid, "104", "p1")


def _pds2(registry: StaticDataRegistry) -> str:
    return next(
        u.required_tech_id for u in registry.units.values()
        if u.base_type == "pds" and u.deep_space_cannon and u.required_tech_id and not u.faction
    )


@ruling("C_agendas/nexus-sovereignty/3", "C_agendas/enforced-travel-ban/4")
@pytest.mark.parametrize("law", ["travel_ban", "nexus"])
def test_travel_ban_deep_space_cannon_still_shoots(registry: StaticDataRegistry, law: str) -> None:
    state, grid = _wormhole_pair(registry, law)
    planet = next(p for p in registry.systems["26"].planets)
    grid = _line(registry, ("101", "26"), ("104", ALPHA))  # Lodor (alpha) z planetą
    state.systems["101"] = SystemState(
        position="101", system_id="26", planet_owners={planet: "p2"},
        planet_units={planet: {"p2": {"pds": 1}}},
    )
    state.systems["104"].space_units = {"p1": {"cruiser": 1}}
    state.players["p2"].technologies = [_pds2(registry)]
    shooters = space_cannon.offense_shooters(state, grid, registry, "p2")
    assert [s.position for s in shooters if s.remote] == ["101"]


@ruling("C_agendas/enforced-travel-ban/5", "C_agendas/nexus-sovereignty/4")
@pytest.mark.parametrize("law", ["travel_ban", "nexus"])
def test_travel_ban_players_stay_neighbors_through_wormholes(
    registry: StaticDataRegistry, law: str
) -> None:
    state, grid = _wormhole_pair(registry, law)
    state.systems["104"].space_units = {"p2": {"cruiser": 1}}
    assert neighbors.neighbors_of("p1", state, grid) == {"p2"}


@ruling("C_agendas/enforced-travel-ban/6")
def test_travel_ban_against_hits_pds_near_any_wormhole_type(registry: StaticDataRegistry) -> None:
    grid = _line(registry, ("101", DELTA), ("102", "19"), ("104", "20"))
    state = _state(registry, ["travel_ban"])
    planet = registry.systems["19"].planets[0]
    far = registry.systems["20"].planets[0]
    state.systems = {
        "101": SystemState(position="101", system_id=DELTA),
        "102": SystemState(position="102", system_id="19", planet_owners={planet: "p1"},
                           planet_units={planet: {"p1": {"pds": 2}}}),
        "104": SystemState(position="104", system_id="20", planet_owners={far: "p3"},
                           planet_units={far: {"p3": {"pds": 1}}}),
    }
    assert grid.are_adjacent("101", "102") and not grid.are_adjacent("101", "104")
    out = _resolve(registry, state, "against")
    assert out.systems["102"].planet_units[planet].get("p1", {}).get("pds", 0) == 0  # obok delta
    assert out.systems["104"].planet_units[far]["p3"] == {"pds": 1}


# =============================================================== Minister of Commerce / Exploration


def _commerce_state(registry: StaticDataRegistry) -> GameState:
    grid = _line(registry, ("101", "19"), ("102", "20"))
    del grid
    state = _state(registry, [])
    state.decks.agenda_laws = {"minister_commerce": "p1"}
    state.players["p1"].commodity_value = 3
    state.systems = {
        "101": SystemState(position="101", system_id="19", space_units={"p1": {"cruiser": 1}}),
        "102": SystemState(position="102", system_id="20",
                           space_units={"p2": {"cruiser": 1}, "p3": {"cruiser": 1}}),
    }
    return state


@ruling("C_agendas/minister-of-commerce/1", "C_agendas/minister-of-commerce/3")
def test_commerce_any_replenish_pays_all_neighbors_at_once(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _commerce_state(registry)
    gains: list[int] = []
    real = economy.gain_trade_goods

    def spy(st: GameState, pid: str, amount: int, *, cause: str = "") -> None:
        gains.append(amount)
        real(st, pid, amount, cause=cause)

    monkeypatch.setattr(economy, "gain_trade_goods", spy)
    economy.replenish_commodities(state, "p1")  # dowolny efekt uzupełnienia
    assert gains == [2] and state.players["p1"].trade_goods == 2


@ruling("C_agendas/minister-of-commerce/1.1")
def test_commerce_fixed_commodities_do_not_trigger(registry: StaticDataRegistry) -> None:
    state = _commerce_state(registry)
    economy.gain_commodities(state, "p1", 3)  # do pełna, ale „gain”, nie „replenish”
    assert state.players["p1"].commodities == 3 and state.players["p1"].trade_goods == 0


@ruling("C_agendas/minister-of-exploration/1")
def test_exploration_minister_trade_goods_one_at_a_time(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(registry, [])
    state.decks.agenda_laws = {"minister_exploration": "p1"}
    gains: list[int] = []
    monkeypatch.setattr(
        economy, "gain_trade_goods", lambda _s, _p, amount, *, cause="": gains.append(amount)
    )
    for planet in ("a", "b"):  # dwie planety z jednej inwazji
        triggers.fire(state, GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, subject="p1",
                      ctx={"player": "p1", "planet": planet})
    assert gains == [1, 1]


# ======================================================================= Minister of Industry


def _industry(registry: StaticDataRegistry) -> tuple[GameState, str]:
    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.active_player_id = "p1"
    state.decks.agenda_laws = {"minister_industry": "p1"}
    return state, _planet(state, "p1")


@ruling("C_agendas/minister-of-industry/1", "C_agendas/minister-of-industry/2")
def test_industry_whole_system_produces_and_pays(registry: StaticDataRegistry) -> None:
    from src.core.hooks.card_helpers import place_from_reinforcements

    state, planet = _industry(registry)
    state.systems["101"].space_units = {"p1": {"carrier": 1}}
    place_from_reinforcements(state, state.systems["101"], planet, "p1", "spacedock", 1)
    state = _accept(state, "p1")
    grant = state.production_grant
    assert grant is not None and grant.position == "101" and grant.player_id == "p1"
    assert not grant.free  # jednostki trzeba opłacić
    assert grant.standalone  # cały system, nie tylko nowy dok


@ruling("C_agendas/minister-of-industry/3")
def test_industry_no_second_dock_on_a_planet(registry: StaticDataRegistry) -> None:
    from src.core.strategy_cards.common import structure_problem

    state, planet = _industry(registry)
    state.systems["101"].planet_units = {planet: {"p1": {"spacedock": 1}}}
    assert structure_problem(state, "p1", planet, "spacedock") is not None


@ruling("C_agendas/minister-of-industry/3.1")
def test_industry_empty_reinforcements_remove_dock_from_system_without_command_token(
    registry: StaticDataRegistry,
) -> None:
    from src.core import board_reinforcements
    from src.core.strategy_cards.common import structure_problem

    state, planet = _industry(registry)
    extra = [p for p in sorted(registry.planets) if p != planet][:3]
    state.systems["101"].planet_units = {planet: {"p1": {"pds": 1}}}
    state.systems["102"] = SystemState(
        position="102", system_id="2", planet_owners={extra[0]: "p1"},
        planet_units={extra[0]: {"p1": {"spacedock": 1}}}, command_tokens=["p1"],  # token: locked
    )
    state.systems["103"] = SystemState(
        position="103", system_id="3", planet_owners={extra[1]: "p1"},
        planet_units={extra[1]: {"p1": {"spacedock": 2}}},
    )
    assert board_reinforcements.needs_board_source(state, "p1", "spacedock")  # all 3 on the board
    assert structure_problem(state, "p1", planet, "spacedock") is not None  # plain placement: no
    assert structure_problem(state, "p1", planet, "spacedock", allow_board=True) is None
    sources = board_reinforcements.board_sources(state, "p1", "spacedock")
    assert sources == [f"103|{extra[1]}"]  # not from the system holding p1's command token


@ruling("C_agendas/minister-of-industry/5")
def test_industry_saar_floating_factory_movement_is_not_placing(
    registry: StaticDataRegistry,
) -> None:
    from src.core import movement
    from src.core.state_grid import grid_from_state
    from tests.factions import test_saar as saar_tests

    state = saar_tests._state()
    state.decks.agenda_laws = {"minister_industry": "p1"}
    state = saar_tests._activate(state, registry, saar_tests.PLAIN)
    after = movement.move_fleet(
        state, grid_from_state(state, registry), registry, saar_tests.HOME,
        {"spacedock": 1}, {}, "p1", route=[saar_tests.HOME, saar_tests.PLAIN],
    )
    assert after.systems[saar_tests.PLAIN].space_units["p1"]["spacedock"] == 1  # it moved in
    assert after.production_grant is None
    assert not [o for o in after.pending_offers if o.label == "Minister of Industry"]


@ruling("C_agendas/minister-of-industry/4")
def test_industry_infiltrate_replacement_triggers(registry: StaticDataRegistry) -> None:
    state, planet = _industry(registry)
    triggers.fire(
        state, GameEvent.UNIT_PLACED, Moment.AFTER, subject="p1",
        ctx={"player": "p1", "base_type": "spacedock", "position": "101", "planet": planet,
             "cause": "replaced"},
    )
    assert _offer(state, "p1").label == "Minister of Industry"
    # Infiltrate stawia dok przez tę samą drogę co każde postawienie (place_from_reinforcements).
    import inspect

    from src.core.hooks import reactions_tactical

    assert "place_from_reinforcements" in inspect.getsource(reactions_tactical.infiltrate)


# ======================================================================= Minister of Peace


def _peace_state(registry: StaticDataRegistry) -> tuple[GameState, HexGrid]:
    grid = _line(registry, ("101", "19"), ("102", "20"))
    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.active_player_id = "p1"
    state.decks.agenda_laws = {"minister_peace": "p2"}
    state.systems = {
        "102": SystemState(position="102", system_id="20", space_units={"p3": {"cruiser": 1}}),
    }
    return state, grid


@ruling("C_agendas/minister-of-peace/3")
def test_peace_owner_needs_no_units_in_the_system(registry: StaticDataRegistry) -> None:
    state, grid = _peace_state(registry)
    out = tactical.activate_system(state, grid, "102")
    assert _offer(out, "p2").label == "Minister of Peace"  # p2 nie ma tam jednostek


@ruling(
    "C_agendas/minister-of-peace/1",
    "C_agendas/minister-of-peace/1.1",
    "C_agendas/minister-of-peace/2",
)
def test_peace_ends_the_action_but_not_the_turn(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, grid = _peace_state(registry)
    out = tactical.activate_system(state, grid, "102")
    out = _accept(out, "p2")
    assert "minister_peace" not in out.decks.agenda_laws
    # Akcja taktyczna skończona: nie ma już „aktywowanego systemu” dla zdolności „after…”.
    assert out.active_system is None and out.tactical_step is None
    assert not [o for o in out.pending_offers if o.event == GameEvent.SYSTEM_ACTIVATED.value]
    # Tura trwa: aktywny gracz kończy ją sam i „at the end of your turn” nadal działa.
    assert out.active_player_id == "p1"
    fired: list[tuple[str, str]] = []
    real = triggers.fire

    def spy(st: GameState, event: GameEvent, moment: Moment, **kw: Any) -> Any:
        fired.append((event.value, moment.value))
        return real(st, event, moment, **kw)

    monkeypatch.setattr(triggers, "fire", spy)
    turn_flow.end_turn(out, "p1")
    assert (GameEvent.TURN.value, Moment.END.value) in fired


# ======================================================================= Minister of Policy / War


@ruling("C_agendas/minister-of-policy/1", "C_agendas/minister-of-policy/2")
def test_policy_draws_one_more_card_at_the_end_of_status(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    state.decks.agenda_laws = {"minister_policy": "p1"}
    state.decks.action_card_deck = ["a1", "a2", "a3"]
    state.players["p1"].technologies = ["nm"]  # Neural Motivator nie dotyczy Ministra
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    assert state.players["p1"].private.action_cards == ["a1"]
    assert state.players["p2"].private.action_cards == []


@ruling("C_agendas/minister-of-war/1")
def test_minister_of_war_is_offered_after_a_strategic_action_primary(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.active_player_id = "p1"
    state.decks.agenda_laws = {"minister_war": "p1"}
    state.systems["101"].command_tokens = ["p1"]
    ctx = {"player": "p1", "initiative": 1, "ability": "primary"}
    triggers.fire(state, GameEvent.STRATEGIC_ACTION, Moment.AFTER, subject="p1", ctx=ctx)
    offers = [o for o in state.pending_offers if o.label == "Minister of War"]
    assert offers, "Minister of War must be offered after a strategic action"
    # A secondary ability is not the owner's action: no offer.
    state.pending_offers.clear()
    triggers.fire(state, GameEvent.STRATEGIC_ACTION, Moment.AFTER, subject="p1",
                  ctx={**ctx, "ability": "secondary"})
    assert not [o for o in state.pending_offers if o.label == "Minister of War"]


@ruling("C_agendas/minister-of-war/3")
def test_minister_of_war_extra_action_without_turn_events(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core import action_budget

    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.active_player_id = "p1"
    state.decks.agenda_laws = {"minister_war": "p1"}
    state.systems["101"].command_tokens = ["p1"]
    fired: list[str] = []
    real = triggers.fire

    def spy(st: GameState, event: GameEvent, moment: Moment, **kw: Any) -> Any:
        fired.append(event.value)
        return real(st, event, moment, **kw)

    monkeypatch.setattr(triggers, "fire", spy)
    agendas_laws._minister_war(state, "p1", {"params": {"position": "101"}})
    assert action_budget.actions_allowed(state, "p1") == 2  # druga akcja w tej samej turze
    assert GameEvent.TURN.value not in fired  # bez „start/end of turn” między akcjami


# ===================================================================== Mutiny / Seed / Constitution


def _vp_order(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    order: list[str] = []
    real = objectives.award_points

    def spy(st: GameState, pid: str, points: int, **kw: Any) -> None:
        order.append(pid)
        real(st, pid, points, **kw)

    monkeypatch.setattr(objectives, "award_points", spy)
    return order


@ruling("C_agendas/mutiny/1")
def test_mutiny_points_in_speaker_order(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _vp_order(monkeypatch)
    _resolve(registry, _state(registry, ["mutiny"]), "for",
             votes={"p3": "for", "p1": "for", "p2": "for"})
    assert order == ["p2", "p3", "p1"]  # mówca p2 pierwszy


@ruling("C_agendas/seed-of-an-empire/1")
def test_seed_ties_gain_in_speaker_order(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _vp_order(monkeypatch)
    _resolve(registry, _state(registry, ["seed_empire"]), "for")
    assert order == ["p2", "p3", "p1"]


@ruling("C_agendas/new-constitution/1")
def test_constitution_skips_planets_in_another_players_home(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["constitution"])
    state.players["p1"].faction, state.players["p2"].faction = "sol", "arborec"
    homes = {
        pid: (registry.factions[f].home_system, registry.factions[f].home_planets)
        for pid, f in (("p1", "sol"), ("p2", "arborec"))
    }
    state.systems["201"] = SystemState(position="201", system_id=homes["p1"][0] or "",
                                       planet_owners={p: "p1" for p in homes["p1"][1]})
    state.systems["202"] = SystemState(position="202", system_id=homes["p2"][0] or "",
                                       planet_owners={p: "p1" for p in homes["p2"][1]})
    state.players["p1"].home_position, state.players["p2"].home_position = "201", "202"
    state.decks.agenda_laws = {"conscription": "for"}
    out = _resolve(registry, state, "for")
    out.phase, out.agenda = Phase.STRATEGY, None
    agendas_directives._constitution_apply(out, "p1", {})
    assert sorted(out.players["p1"].exhausted_planets) == sorted(homes["p1"][1])


# ======================================================================= Prophecy / Schematics


@ruling("C_agendas/prophecy-of-ixth/1")
def test_prophecy_stays_after_fighters_from_other_effects(registry: StaticDataRegistry) -> None:
    from src.core.hooks.card_helpers import place_from_reinforcements

    state = _state(registry, [])
    state.decks.agenda_laws = {"prophecy": "p1"}
    state.systems["101"].space_units = {"p1": {"carrier": 1}}
    place_from_reinforcements(state, state.systems["101"], "space", "p1", "fighter", 1)
    assert "prophecy" in state.decks.agenda_laws
    triggers.fire(state, GameEvent.PRODUCTION_USED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "units": {"fighter": 1}})
    assert "prophecy" not in state.decks.agenda_laws  # PRODUCTION z <2 myśliwcami: odrzucona


@ruling("C_agendas/publicize-weapon-schematics/1")
def test_schematics_first_war_sun_owner_unlocks_free_prerequisites(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, [])
    state.decks.agenda_laws = {"schematics": "for"}
    ctx = {"technology": "ws"}
    point = rules_hooks.POINT_TECHNOLOGY_FREE_IGNORES
    assert rules_hooks.modify(point, state, "p2", 0, ctx) == 0
    state.players["p1"].technologies = ["ws"]
    assert rules_hooks.modify(point, state, "p2", 0, ctx) == sum(
        technology.prerequisites(registry.technologies["ws"]).values()
    )


@ruling(
    "C_agendas/publicize-weapon-schematics/2",
    "C_agendas/publicize-weapon-schematics/2.1",
    "C_agendas/publicize-weapon-schematics/2.2",
    "C_agendas/publicize-weapon-schematics/3",
)
def test_schematics_muaat_without_pws2_owns_no_war_sun_tech(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["schematics"])
    state.players["p1"].faction = "muaat"
    state.players["p1"].private.action_cards = ["a1", "a2"]
    assert not agendas_laws.owns_war_sun_tech(state, registry, "p1")  # Prototype War Sun I
    state.decks.agenda_laws = {"schematics": "for"}
    assert rules_hooks.modify(
        rules_hooks.POINT_TECHNOLOGY_FREE_IGNORES, state, "p2", 0, {"technology": "ws"}
    ) == 0
    # Prototype War Sun (bazowy typ warsun) traci SUSTAIN DAMAGE i bez PWS II.
    assert "warsun" in rules_hooks.forbidden(rules_hooks.POINT_UNIT_SUSTAIN_LOST, state, "p1")
    state.decks.agenda_laws = {}
    out = _resolve(registry, state, "against")
    assert out.players["p1"].private.action_cards == ["a1", "a2"]
    state.players["p1"].technologies = ["pws2"]
    assert agendas_laws.owns_war_sun_tech(state, registry, "p1")


# ======================================================================= Rearmament Agreement


def _rearm(registry: StaticDataRegistry) -> tuple[GameState, list[str]]:
    state = _state(registry, ["rearmament"])
    state.players["p1"].faction = "sol"
    home = registry.factions["sol"]
    state.systems["201"] = SystemState(position="201", system_id=home.home_system or "",
                                       planet_owners={p: "p1" for p in home.home_planets})
    state.players["p1"].home_position = "201"
    return state, list(home.home_planets)


@ruling("C_agendas/rearmament-agreement/1")
def test_rearmament_no_home_planet_no_mech(registry: StaticDataRegistry) -> None:
    state, homes = _rearm(registry)
    state.systems["201"].planet_owners = {p: "p3" for p in homes}  # dom zajęty przez p3
    out = _resolve(registry, state, "for")
    while any(o.player_id != "p1" for o in out.pending_offers):
        other = next(o.player_id for o in out.pending_offers)
        out = triggers.accept_offer(out, other, _offer(out, other).id, {})
    if any(o.player_id == "p1" for o in out.pending_offers):
        out = _accept(out, "p1", {})
    assert not any(
        u.get("p1", {}).get("mech") for s in out.systems.values() for u in s.planet_units.values()
    )


@ruling("C_agendas/rearmament-agreement/2")
def test_rearmament_mech_from_the_board_when_reinforcements_empty(
    registry: StaticDataRegistry,
) -> None:
    from src.core import board_reinforcements

    state, homes = _rearm(registry)
    state.systems["101"].planet_units = {_planet(state, "p1"): {"p1": {"mech": 4}}}
    assert board_reinforcements.needs_board_source(state, "p1", "mech")
    fields = agendas_directives._rearm_inputs(state, registry, "p1", {})
    assert [f["key"] for f in fields] == ["planet", "source"]
    assert fields[1]["auto"] == "none"  # Auto = do not place (nothing leaves the board)
    pick = next(o for o in fields[1]["options"] if o["value"] != "none")
    assert pick["meta"]["unit"] == "mech" and pick["meta"]["planet"]  # clicked on the map
    source = pick["value"]
    agendas_directives._rearm_for(state, "p1", {"params": {"planet": homes[0], "source": source}})
    assert state.systems["201"].planet_units[homes[0]]["p1"] == {"mech": 1}
    assert state.systems["101"].planet_units[_planet(state, "p1")]["p1"] == {"mech": 3}
    assert not state.damaged_units if hasattr(state, "damaged_units") else True


@ruling("C_agendas/rearmament-agreement/3")
def test_rearmament_against_ignores_players_without_mechs(registry: StaticDataRegistry) -> None:
    state, _homes = _rearm(registry)
    planet = _planet(state, "p3")
    state.systems["101"].planet_units = {planet: {"p3": {"mech": 1}}}
    out = _resolve(registry, state, "against")
    assert out.systems["101"].planet_units[planet]["p3"] == {"infantry": 1}
    assert not any(
        u.get("p1") for s in out.systems.values() for u in s.planet_units.values()
    )


# ====================================================================== Research Grant Reallocation


def _grant(registry: StaticDataRegistry, fleet: int) -> tuple[GameState, Any]:
    state = _state(registry, ["grant_reallocation"])
    state.players["p1"].fleet_cc = fleet
    out = _resolve(registry, state, "p1")
    hard = next(
        t for t in technology.tech_pool(out, registry, "p1").values()
        if sum(technology.prerequisites(t).values()) == 2 and not t.faction
    )
    return out, hard


@ruling(
    "C_agendas/research-grant-reallocation/1",
    "C_agendas/research-grant-reallocation/1.1",
)
def test_grant_any_tech_even_with_too_few_fleet_tokens(registry: StaticDataRegistry) -> None:
    out, hard = _grant(registry, 1)
    out = _accept(out, "p1", {"research": {"tech": hard.id}})
    assert hard.id in out.players["p1"].technologies
    assert out.players["p1"].fleet_cc == 0  # 2 prerekwizyty, 1 żeton: zdejmuje wszystkie


@ruling(
    "C_agendas/research-grant-reallocation/2",
    "C_agendas/research-grant-reallocation/2.1",
)
def test_grant_cost_ignores_owned_techs_and_specialties(registry: StaticDataRegistry) -> None:
    out, hard = _grant(registry, 3)
    color = next(iter(technology.prerequisites(hard)))
    out.players["p1"].technologies = [
        t.id for t in technology.tech_pool(out, registry, "p1").values()
        if color in t.types and not technology.prerequisites(t) and not t.faction
    ]
    planet, _colors = next(
        (p, d.tech_specialties) for p, d in sorted(registry.planets.items())
        if d.tech_specialties and d.tech_specialties[0].upper() == color
    )
    out.systems["102"] = SystemState(position="102", system_id="2", planet_owners={planet: "p1"})
    (field,) = _inputs(out, registry, "p1")
    assert field["kind"] == "research" and not field["research"].get("skips")
    out = _accept(out, "p1", {"research": {"tech": hard.id}})
    assert out.players["p1"].fleet_cc == 1  # 2 prerekwizyty = 2 żetony mimo posiadanych
    assert planet not in out.players["p1"].exhausted_planets


# ======================================================================= Shared Research


def _nebula(registry: StaticDataRegistry) -> str:
    return next(sid for sid, d in sorted(registry.systems.items())
                if "NEBULA" in {a.upper() for a in d.anomalies} and not d.planets)


@ruling("R_nebula/rules-reference/1")
def test_shared_research_cannot_end_in_a_non_active_nebula(registry: StaticDataRegistry) -> None:
    nebula = _nebula(registry)
    grid = _line(registry, ("101", "19"), ("102", nebula), ("103", "20"))
    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.active_player_id, state.active_system = "p1", "103"
    state.tactical_step = TacticalStep.MOVEMENT
    state.systems = {"101": SystemState(position="101", system_id="19",
                                        space_units={"p1": {"cruiser": 1}})}
    assert movement.route_error(state, grid, ["101", "102", "103"], "p1", "cruiser") is not None
    state.decks.agenda_laws = {"shared_research": "for"}
    assert movement.route_error(state, grid, ["101", "102", "103"], "p1", "cruiser") is None
    # Trasa zawsze kończy się w aktywnym systemie: wejść do mgławicy wolno tylko, gdy jest aktywna.
    state.active_system = "102"
    assert movement.route_error(state, grid, ["101", "102"], "p1", "cruiser") is None


@ruling("R_nebula/rules-reference/2")
def test_shared_research_ship_leaving_a_nebula_has_move_one(registry: StaticDataRegistry) -> None:
    nebula = _nebula(registry)
    grid = _line(registry, ("101", nebula), ("102", "19"), ("103", "20"))
    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.active_player_id, state.active_system = "p1", "103"
    state.tactical_step = TacticalStep.MOVEMENT
    state.systems = {"101": SystemState(position="101", system_id=nebula,
                                        space_units={"p1": {"cruiser": 1}})}
    state.decks.agenda_laws = {"shared_research": "for"}
    ok, _why = movement.can_move(state, grid, registry, "101", "cruiser", "p1",
                                 route=["101", "102", "103"])
    assert not ok  # start w mgławicy: ruch 1 przez cały krok, mimo Shared Research
    state.active_system = "102"
    assert movement.can_move(state, grid, registry, "101", "cruiser", "p1",
                             route=["101", "102"])[0]


# ======================================================================= Swords to Plowshares


@ruling("C_agendas/swords-to-plowshares/2")
def test_plowshares_for_ignores_mechs(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["plowshares"])
    planet = _planet(state, "p1")
    state.systems["101"].planet_units = {planet: {"p1": {"infantry": 3, "mech": 2}}}
    out = _resolve(registry, state, "for")
    assert out.systems["101"].planet_units[planet]["p1"] == {"infantry": 1, "mech": 2}
    assert out.players["p1"].trade_goods == 2


# ======================================================================= Wormhole Reconstruction


@ruling("C_agendas/wormhole-reconstruction/2")
def test_reconstruction_against_tokens_in_every_wormhole_type(registry: StaticDataRegistry) -> None:
    grid = _line(registry, ("101", DELTA), ("102", "19"))
    del grid
    state = _state(registry, ["wormhole_recon"])
    state.systems = {
        "101": SystemState(position="101", system_id=DELTA, space_units={"p1": {"cruiser": 1}}),
        "102": SystemState(position="102", system_id="19", space_units={"p1": {"cruiser": 1}},
                           wormhole_tokens=["GAMMA"]),
    }
    out = _resolve(registry, state, "against")
    assert out.systems["101"].command_tokens == ["p1"]
    assert out.systems["102"].command_tokens == ["p1"]


# ======================================================================= Wormhole Research


def _wr_state(registry: StaticDataRegistry) -> GameState:
    _line(registry, ("101", DELTA), ("102", ALPHA), ("103", "19"))
    state = _state(registry, ["wormhole_research"])
    state.systems = {
        "101": SystemState(position="101", system_id=DELTA, space_units={"p1": {"cruiser": 1}}),
        "102": SystemState(position="102", system_id=ALPHA,
                           space_units={"p3": {"carrier": 1, "fighter": 2, "infantry": 2,
                                               "spacedock": 1}}),
        "103": SystemState(position="103", system_id="19", space_units={"p2": {"cruiser": 1}}),
    }
    return state


def _wr_settle(state: GameState, registry: StaticDataRegistry, *, keep: str = "") -> GameState:
    """Declines the remaining (optional) offers of everyone but ``keep``, then the speaker
    continues: only then Wormhole Research destroys the ships (C_agendas)."""
    from src.core import agenda_phase

    while True:
        other = [o for o in state.pending_offers if o.player_id != keep]
        if not other:
            break
        state = triggers.decline_offer(state, other[0].player_id, other[0].id)
    return agenda_phase.continue_agenda(state, registry, "p2")


@ruling("C_agendas/wormhole-research/1", "C_agendas/wormhole-research/3")
def test_wormhole_research_delta_ships_research_and_survive(registry: StaticDataRegistry) -> None:
    out = _resolve(registry, _wr_state(registry), "for")
    assert {o.player_id for o in out.pending_offers} == {"p1", "p3"}  # p2 bez wormhole
    # Nothing is destroyed until the research choices are done (see wormhole-research/5).
    assert out.systems["102"].space_units["p3"]["carrier"] == 1
    out = _wr_settle(out, registry)
    assert out.systems["101"].space_units["p1"] == {"cruiser": 1}  # delta: statek zostaje
    assert out.systems["102"].space_units["p3"] == {"spacedock": 1}  # Floating Factory zostaje


@ruling("C_agendas/wormhole-research/1.1")
def test_wormhole_research_nexus_like_system_is_destroyed(registry: StaticDataRegistry) -> None:
    state = _wr_state(registry)
    state.systems["101"].wormhole_tokens = ["ALPHA"]  # delta + alpha w jednym systemie
    out = _wr_settle(_resolve(registry, state, "for"), registry)
    assert out.systems["101"].space_units.get("p1", {}) == {}


@ruling("C_agendas/wormhole-research/4")
def test_wormhole_research_needs_prerequisites(registry: StaticDataRegistry) -> None:
    from src.core import research_offer

    out = _resolve(registry, _wr_state(registry), "for")
    hard = next(t for t in technology.tech_pool(out, registry, "p1").values()
                if sum(technology.prerequisites(t).values()) >= 2 and not t.faction)
    with pytest.raises(ValueError):
        research_offer.resolve(out, registry, "p1", {"params": {"research": {"tech": hard.id}}})


@ruling("C_agendas/wormhole-research/2")
def test_wormhole_research_ground_forces_removed_fighters_destroyed(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.core import unit_ops

    causes: dict[str, UnitCause] = {}
    real = unit_ops.remove_units

    def spy(state: GameState, system: SystemState, zone: str, pid: str, base: str, n: int,
            cause: UnitCause = UnitCause.REMOVED) -> int:
        causes[base] = cause
        return real(state, system, zone, pid, base, n, cause)

    monkeypatch.setattr(unit_ops, "remove_units", spy)
    _wr_settle(_resolve(registry, _wr_state(registry), "for"), registry)
    assert causes["fighter"] is UnitCause.DESTROYED and causes["carrier"] is UnitCause.DESTROYED
    assert causes["infantry"] is UnitCause.REMOVED



def _wr_revolution(
    registry: StaticDataRegistry, p3_ships: dict[str, int], pick: str, *, faction: str = "sol"
) -> GameState:
    """Anti-Intellectual Revolution is a law; p3 (ships in alpha 102 + a cruiser in 103)
    researches and destroys ``pick`` ("<position>|space|<type>|0") for it; the others pass later.
    Returns the state before the speaker continues (the doomed ships are still on the board)."""
    state = _wr_state(registry)
    state.decks.agenda_laws = {"revolution": "for"}
    state.players["p3"].faction = faction
    state.players["p2"].faction = "sol"
    state.systems["102"].space_units = {
        "p3": dict(p3_ships), "p2": {"cruiser": 1},
    }
    state.systems["103"].space_units = {"p3": {"cruiser": 1}}
    out = _resolve(registry, state, "for")
    p2 = next(o for o in out.pending_offers if o.player_id == "p2")  # p2 is asked first
    out = triggers.decline_offer(out, "p2", p2.id)
    tech = next(
        t.id for t in sorted(technology.tech_pool(out, registry, "p3").values(), key=lambda t: t.id)
        if not technology.prerequisites(t) and not t.faction
    )
    out = _accept(out, "p3", {"research": {"tech": tech}})
    revolution = next(o for o in out.pending_offers if "Revolution" in o.label)
    return triggers.accept_offer(out, "p3", revolution.id, {"units": [pick]})


@ruling("C_agendas/wormhole-research/5")
def test_wormhole_research_doomed_ship_may_be_destroyed_for_the_revolution(
    registry: StaticDataRegistry,
) -> None:
    out = _wr_revolution(registry, {"carrier": 1}, "102|space|carrier|0")
    # The Revolution choice was real (the carrier in alpha OR the cruiser in 103) and p3 took the
    # doomed carrier, so the cruiser in 103 is spared - the engine used to force that cruiser.
    assert out.systems["103"].space_units["p3"] == {"cruiser": 1}
    assert "carrier" not in out.systems["102"].space_units.get("p3", {})
    out = _wr_settle(out, registry)
    assert out.systems["103"].space_units["p3"] == {"cruiser": 1}
    assert out.systems["102"].space_units.get("p2", {}) == {}  # still destroyed by the agenda


_TERROR = {"flagship": 1, "carrier": 1}


@ruling("C_agendas/wormhole-research/5.1")
def test_wormhole_research_vuilraith_flagship_destroyed_for_the_revolution_captures_nothing(
    registry: StaticDataRegistry,
) -> None:
    gone = _wr_settle(_wr_revolution(registry, _TERROR, "102|space|flagship|0", faction="cabal"),
                      registry)
    assert gone.players["p3"].captured_units == {} and gone.players["p3"].captured_tokens == {}
    assert gone.systems["102"].space_units.get("p2", {}) == {}
    # Control: the flagship survives (another ship is chosen) and captures the cruiser of p2.
    kept = _wr_settle(_wr_revolution(registry, _TERROR, "102|space|carrier|0", faction="cabal"),
                      registry)
    assert kept.players["p3"].captured_units.get("p2", {}) == {"cruiser": 1}


@ruling("C_agendas/wormhole-research/5.2")
def test_wormhole_research_capacity_is_resolved_before_the_ships_are_destroyed(
    registry: StaticDataRegistry,
) -> None:
    fleet = {"flagship": 1, "carrier": 1, "fighter": 7}  # capacity: flagship 3 + carrier 4 = 7
    out = _wr_revolution(registry, fleet, "102|space|carrier|0", faction="cabal")
    out = _wr_settle(out, registry)
    # Without the carrier the fleet is over capacity: the excess fighters are REMOVED first (not
    # captured); only the fighters that remain are destroyed by the agenda and captured.
    assert out.systems["102"].space_units.get("p3", {}).get("fighter", 0) == 0
    captured = out.players["p3"].captured_tokens.get("fighter", 0)
    assert captured == 3  # what the flagship alone can carry, not all 7


# ========================================================= Dodatkowe punkty M-Z (ministrowie)


@ruling("C_agendas/minister-of-commerce/2")
def test_commerce_pays_even_with_maximum_commodities(registry: StaticDataRegistry) -> None:
    state = _commerce_state(registry)
    state.players["p1"].commodities = 3  # już maksimum
    economy.replenish_commodities(state, "p1")
    assert state.players["p1"].commodities == 3
    assert state.players["p1"].trade_goods == 2  # 2 sąsiadów, nadal wypłata


@ruling("C_agendas/minister-of-war/2")
def test_minister_of_war_is_not_an_action_fleet_logistics_gives_three(
    registry: StaticDataRegistry,
) -> None:
    from src.core import action_budget

    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.active_player_id = "p1"
    state.players["p1"].technologies = ["fl"]  # Fleet Logistics: 2 akcje
    state.decks.agenda_laws = {"minister_war": "p1"}
    state.systems["101"].command_tokens = ["p1"]
    assert action_budget.actions_allowed(state, "p1") == 2
    agendas_laws._minister_war(state, "p1", {"params": {"position": "101"}})
    assert action_budget.actions_allowed(state, "p1") == 3
    assert action_budget.actions_left(state, "p1") == 3  # rozstrzygnięcie nie zużyło akcji


@ruling("C_agendas/public-execution/1")
def test_public_execution_crafty_does_not_save_the_hand(registry: StaticDataRegistry) -> None:
    """Limit ręki (Crafty) nie chroni przed odrzuceniem wszystkich kart przez Public Execution."""
    state = _state(registry, ["execution", "economic_equality"])
    state.players["p2"].faction = "yssaril"
    state.players["p2"].private.action_cards = ["sabo1", "sabo2", "sabo3", "sabo4"]
    out = _resolve(registry, state, "p2")
    assert out.players["p2"].private.action_cards == []


# ======================================================================= Shared Research


def _shared_research(registry: StaticDataRegistry) -> GameState:
    state = _state(registry, ["shared_research"])
    for pid, home in (("p1", "101"), ("p2", "102"), ("p3", "103")):
        state.players[pid].home_position = home
        state.systems.setdefault(home, SystemState(position=home, system_id="2"))
    return state


@ruling("C_agendas/shared-research/1")
def test_shared_research_against_without_reinforcements_places_nothing(
    registry: StaticDataRegistry,
) -> None:
    state = _shared_research(registry)
    state.players["p1"].cc_reinf = 0
    sheet = (state.players["p1"].tactical_cc, state.players["p1"].fleet_cc,
             state.players["p1"].strategic_cc)
    out = _resolve(registry, state, "against")
    assert "p1" not in out.systems["101"].command_tokens
    assert (out.players["p1"].tactical_cc, out.players["p1"].fleet_cc,
            out.players["p1"].strategic_cc) == sheet  # nic nie zabrane z arkusza
    assert "p2" in out.systems["102"].command_tokens  # reszta graczy kładzie żeton


@ruling("C_agendas/shared-research/2")
def test_shared_research_against_home_without_controlled_planets(
    registry: StaticDataRegistry,
) -> None:
    state = _shared_research(registry)
    assert not state.systems["102"].planet_owners  # p2 nie kontroluje tam planet
    out = _resolve(registry, state, "against")
    assert "p2" in out.systems["102"].command_tokens


# ======================================================================= Swords to Plowshares


@ruling("C_agendas/swords-to-plowshares/1")
def test_plowshares_for_all_trade_goods_gained_together(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(registry, ["plowshares"])
    first = _planet(state, "p1")
    taken = {p for s in state.systems.values() for p in s.planet_owners}
    second = next(p for p in sorted(registry.planets) if p not in taken)
    state.systems["102"] = SystemState(
        position="102", system_id="2", planet_owners={second: "p1"}
    )
    state.systems["101"].planet_units = {first: {"p1": {"infantry": 1}}}  # jedyna piechota ginie
    state.systems["102"].planet_units = {second: {"p1": {"infantry": 3}}}
    gains: list[tuple[str, int]] = []
    real = economy.gain_trade_goods

    def spy(st: GameState, pid: str, amount: int, *, cause: str = "") -> None:
        gains.append((pid, amount))
        real(st, pid, amount, cause=cause)

    monkeypatch.setattr(economy, "gain_trade_goods", spy)
    out = _resolve(registry, state, "for")
    assert out.systems["101"].planet_units[first].get("p1", {}).get("infantry", 0) == 0
    assert out.systems["102"].planet_units[second]["p1"]["infantry"] == 1
    assert gains == [("p1", 3)]  # jedna wypłata (Pillage Mentaka zadziała raz na sąsiada)


@ruling("C_agendas/swords-to-plowshares/3")
def test_plowshares_for_ignores_neutral_infantry(registry: StaticDataRegistry) -> None:
    from src.core.neutral import NEUTRAL_PLAYER_ID

    state = _state(registry, ["plowshares"])
    taken = {p for s in state.systems.values() for p in s.planet_owners}
    free = next(p for p in sorted(registry.planets) if p not in taken)
    state.systems["102"] = SystemState(
        position="102", system_id="2", planet_units={free: {NEUTRAL_PLAYER_ID: {"infantry": 2}}}
    )
    out = _resolve(registry, state, "for")
    assert out.systems["102"].planet_units[free][NEUTRAL_PLAYER_ID] == {"infantry": 2}
    assert all(p.trade_goods == 0 for p in out.players.values())


# ======================================================================= Wormhole Reconstruction


@ruling("C_agendas/wormhole-reconstruction/2.1")
def test_reconstruction_against_creuss_gate_gets_a_token_too(
    registry: StaticDataRegistry,
) -> None:
    _line(registry, ("101", DELTA))
    state = _state(registry, ["wormhole_recon"])
    state.players["p1"].faction = "ghost"
    state.systems = {
        "101": SystemState(position="101", system_id=DELTA, space_units={"p1": {"cruiser": 1}}),
    }
    out = _resolve(registry, state, "against")
    assert out.systems["101"].command_tokens == ["p1"]
