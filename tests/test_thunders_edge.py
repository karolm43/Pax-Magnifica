"""Testy modułu Thunder's Edge: The Fracture, ekspedycje, Thunder's Edge (RULES.md 50)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import battle, control, expeditions, relics
from src.core.dice import next_rng
from src.core.event_store import EventStore
from src.core.expedition_state import EXPEDITION_SLICES
from src.core.fracture import (
    FRACTURE_POSITIONS,
    NEUTRAL_SETUP,
    breakthrough_roll,
    choose_ingress,
    enter_play,
    ingress_candidates,
    sync_grid,
)
from src.core.game_state import (
    CombatStep,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid, position_to_hex
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.positions import ordered_positions
from src.core.registry import StaticDataRegistry
from src.core.system_planets import planets_of_system

COLORS = ("BIOTIC", "CYBERNETIC", "PROPULSION", "WARFARE")


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _specialty_systems(registry: StaticDataRegistry) -> list[str]:
    """Systemy (bez The Fracture) z planetą o specjalności technologicznej."""
    result: list[str] = []
    for sid, system in sorted(registry.systems.items()):
        if system.is_fracture:
            continue
        if any(
            (planet := registry.planets.get(p)) is not None and planet.tech_specialties
            for p in system.planets
        ):
            result.append(sid)
    return result


def _grid(registry: StaticDataRegistry, empty: int = 3) -> HexGrid:
    """Mecatol + systemy ze specjalnościami + kilka pustych systemów (kandydaci Thunder's Edge)."""
    grid = HexGrid()
    grid.place_system("000", "18", hex_override=position_to_hex("000"))
    empty_ids = [
        sid
        for sid, s in sorted(registry.systems.items())
        if sid.isdigit() and not s.planets and not s.wormholes and not s.anomalies
    ][:empty]
    ids = _specialty_systems(registry) + empty_ids
    positions = [p for p in ordered_positions() if p.isdigit()][: len(ids)]
    for position, sid in zip(positions, ids, strict=True):
        system = registry.systems[sid]
        grid.place_system(
            position,
            sid,
            wormholes=list(system.wormholes),
            anomalies=set(system.anomalies),
            hex_override=position_to_hex(position),
        )
    grid.build_edges()
    return grid


def _state(registry: StaticDataRegistry, grid: HexGrid, *, seed: int = 11) -> GameState:
    systems = {
        pos: SystemState(position=pos, system_id=grid.system_id_at(pos)) for pos in grid.positions
    }
    players = {
        "p1": PlayerState(player_id="p1", color="red", faction="arborec", trade_goods=10),
        "p2": PlayerState(player_id="p2", color="blue", faction="hacan"),
    }
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players=players,
        systems=systems,
        rng_seed=seed,
    )


def _after_action(state: GameState, player_id: str = "p1") -> GameState:
    new_state = state.clone()
    new_state.players[player_id].took_action_this_turn = True
    return new_state


# ------------------------------------------------------------------------- The Fracture


def test_enter_play_places_tiles_neutrals_and_mecatol_ingress(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid), registry, grid, "p1", breakthrough_id=None)

    assert state.fracture.in_play and state.fracture.entered_by == "p1"
    assert set(FRACTURE_POSITIONS) <= set(state.systems)
    # Neutralni wystawieni z odwrotu kafli.
    cocytus = state.systems["frac1"]
    assert cocytus.space_units[NEUTRAL_PLAYER_ID] == NEUTRAL_SETUP["fracture1"]["space"]
    assert cocytus.planet_units["cocytus"][NEUTRAL_PLAYER_ID] == {"infantry": 2}
    assert state.systems["frac7"].planet_units["lethe"][NEUTRAL_PLAYER_ID] == {"infantry": 1}
    # Planet neutralni nie kontrolują.
    assert not cocytus.planet_owners
    # Thunder's Edge nie ma w grze -> dodatkowy ingress na Mecatolu.
    assert state.systems["000"].ingress_token is True
    # Bez synergii: po jednym ingressie na każdy z 4 kolorów (każdy ma 6+ kandydatów -> wybór).
    assert sorted(c.color for c in state.fracture.pending) == sorted(COLORS)
    assert all(c.remaining == 1 for c in state.fracture.pending)


def test_synergy_asks_three_per_color(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid), registry, grid, "p1", "arborecbt")
    assert {c.color: c.remaining for c in state.fracture.pending} == {
        "BIOTIC": 3,
        "WARFARE": 3,
    }


def test_enter_twice_is_an_error(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid), registry, grid, "p1")
    with pytest.raises(ValueError, match="already in play"):
        enter_play(state, registry, grid, "p1")


def test_choose_ingress_flow_and_validation(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid), registry, grid, "p1", "arborecbt")
    candidates = ingress_candidates(state, registry, grid, "BIOTIC")
    assert len(candidates) > 3

    with pytest.raises(ValueError, match="Only p1"):
        choose_ingress(state, registry, grid, "p2", "BIOTIC", candidates[0])
    with pytest.raises(ValueError, match="No ingress token"):
        choose_ingress(state, registry, grid, "p1", "PROPULSION", candidates[0])
    with pytest.raises(ValueError, match="no planet"):
        choose_ingress(state, registry, grid, "p1", "BIOTIC", "000")

    for position in candidates[:3]:
        state = choose_ingress(state, registry, grid, "p1", "BIOTIC", position)
        assert state.systems[position].ingress_token
    assert [c.color for c in state.fracture.pending] == ["WARFARE"]
    # Pozycja z ingressem nie jest już kandydatem.
    with pytest.raises(ValueError):
        choose_ingress(state, registry, grid, "p1", "WARFARE", candidates[0])


def test_few_candidates_are_placed_automatically(registry: StaticDataRegistry) -> None:
    """Gdy kandydatów jest nie więcej niż trzeba, żetony kładą się same (R_fracture)."""
    grid = HexGrid()
    grid.place_system("000", "18", hex_override=position_to_hex("000"))
    # Tylko dwa systemy ze specjalnością BIOTIC i po jednym z pozostałych kolorów.
    chosen: dict[str, str] = {}
    for sid in _specialty_systems(registry):
        colors = {
            s.upper()
            for p in registry.systems[sid].planets
            if (planet := registry.planets.get(p)) is not None
            for s in (planet.tech_specialties or [])
        }
        for color in colors:
            chosen.setdefault(color, sid)
    ids = sorted(set(chosen.values()))
    for position, sid in zip(
        [p for p in ordered_positions() if p.isdigit()][: len(ids)], ids, strict=True
    ):
        grid.place_system(position, sid, hex_override=position_to_hex(position))
    grid.build_edges()
    state = enter_play(_state(registry, grid), registry, grid, "p1")
    assert state.fracture.pending == []
    assert sum(1 for s in state.systems.values() if s.ingress_token) >= 1


def test_roll_is_seeded_and_success_enters_play(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    base = _state(registry, grid)
    hit = miss = None
    for seed in range(1, 200):
        probe = base.clone()
        probe.rng_seed = seed
        result = next_rng(probe).randint(1, 10)
        if result in (1, 10) and hit is None:
            hit = seed
        if result not in (1, 10) and miss is None:
            miss = seed
        if hit and miss:
            break
    assert hit and miss
    for seed, success in ((hit, True), (miss, False)):
        start = base.clone()
        start.rng_seed = seed
        rolled = breakthrough_roll(start, registry, grid, "p1", "arborecbt")
        assert rolled.fracture.in_play is success
        assert rolled.fracture.last_roll is not None
        assert rolled.fracture.last_roll["success"] is success
    # Fracture już w grze -> brak rzutu.
    in_play = enter_play(base, registry, grid, "p1")
    again = breakthrough_roll(in_play, registry, grid, "p2", None)
    assert again.fracture.last_roll == in_play.fracture.last_roll


def test_sync_grid_adds_removes_and_links_ingress_to_egress(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid), registry, grid, "p1")
    sync_grid(grid, state, registry)
    assert set(FRACTURE_POSITIONS) <= grid.positions
    # Kafle łuku sąsiadują ze sobą, ale nie z planszą.
    assert grid.are_adjacent("frac1", "frac2") and grid.are_adjacent("frac6", "frac7")
    assert not any(n not in FRACTURE_POSITIONS for n in grid.neighbors("frac4"))
    # Ingress na Mecatolu <-> egress na frac2 i frac6; frac1 nie ma egressu.
    assert grid.are_adjacent("000", "frac2") and grid.are_adjacent("000", "frac6")
    assert not grid.are_adjacent("000", "frac1")
    # Egress nie sąsiaduje z egressem przez portal (frac2-frac6 nie są w łuku obok siebie).
    assert not grid.are_adjacent("frac2", "frac6")
    # Cofnięcie (stan bez Fracture) usuwa kafle i portale.
    sync_grid(grid, _state(registry, grid), registry)
    assert not (set(FRACTURE_POSITIONS) & grid.positions)
    assert not grid.are_adjacent("000", "frac2")


def test_relic_for_first_control_of_fracture_planet(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid), registry, grid, "p1")
    new_state = state.clone()
    control.set_planet_control(new_state, "frac1", "cocytus", "p1", registry)
    assert len(new_state.players["p1"].relics) == 1
    # Ta sama planeta zdobyta przez drugiego gracza (miała kontrolera) - bez reliktu.
    control.set_planet_control(new_state, "frac1", "cocytus", "p2", registry)
    assert new_state.players["p2"].relics == []
    # Zwykła planeta mapy nie daje reliktu.
    control.set_planet_control(new_state, "000", "mr", "p2", registry)
    assert new_state.players["p2"].relics == []


def test_relic_deck_draws_distinct_cards(registry: StaticDataRegistry) -> None:
    state = _state(registry, _grid(registry))
    first = relics.draw_relic(state, registry, "p1")
    second = relics.draw_relic(state, registry, "p1")
    assert first and second and first != second
    assert state.players["p1"].relics == [first, second]


def test_neutrals_never_control_planets(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid), registry, grid, "p1")
    control.recompute_from_units(state, "frac1", "cocytus")
    assert "cocytus" not in state.systems["frac1"].planet_owners


# ------------------------------------------------------------------ walka z neutralnymi


def _fight_to_the_end(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Prowadzi walkę p1 vs neutralni do końca (p1 sam wybiera straty, neutralni — automat)."""
    state = battle.start_combat(state, grid, registry)
    for _ in range(40):
        combat = state.active_combat
        assert combat is not None
        if combat.step is CombatStep.DONE:
            return state
        if combat.step is CombatStep.AFB:
            state = battle.resolve_afb(state, grid, registry)
        elif combat.step is CombatStep.ANNOUNCE:
            state = battle.announce_retreat(state, grid, "p1", announce=False)
        elif combat.step is CombatStep.ROLL:
            state = battle.roll_round(state, grid, registry)
        elif combat.step is CombatStep.ASSIGN:
            window = state.pending_window
            assert window is not None and window.current_responder == "p1"
            need = battle.required_hits(state, grid, registry, "p1")
            units = battle.side_units(state, grid, registry, "p1")
            destroy = {units[0].base_type: need}
            state = battle.assign_combat_hits(
                state, grid, registry, "p1", sustain={}, destroy=destroy, destroy_damaged={}
            )
    raise AssertionError("combat did not finish")


def test_space_combat_against_neutral_fleet(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid, seed=5), registry, grid, "p1")
    sync_grid(grid, state, registry)
    state.active_system = "frac1"
    state.tactical_step = TacticalStep.SPACE_COMBAT
    state.systems["frac1"].space_units["p1"] = {"cruiser": 8}
    assert battle.space_combat_required(state)

    done = _fight_to_the_end(state, grid, registry)
    combat = done.active_combat
    assert combat is not None and combat.defender == NEUTRAL_PLAYER_ID
    assert combat.outcome in ("winner", "draw")
    # Neutralni tracą statki automatycznie (nie ma okna przypisania dla "neutral").
    neutral_left = done.systems["frac1"].space_units.get(NEUTRAL_PLAYER_ID, {}).get("cruiser", 0)
    assert neutral_left < 2
    assert any(entry["losses"].get(NEUTRAL_PLAYER_ID) for entry in combat.log if "losses" in entry)


def test_neutral_hits_go_to_cheapest_unit_first(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid), registry, grid, "p1")
    units = battle.combat_units(
        state,
        grid,
        registry,
        kind="space",
        position="frac4",
        planet=None,
        player_id=NEUTRAL_PLAYER_ID,
    )
    costs = {u.base_type: registry.units[u.unit_id].cost or 0.0 for u in units}
    assert {u.base_type for u in units} == {"dreadnought", "destroyer"}
    sustain, destroy, destroy_damaged = battle.neutral_loss_choice(units, costs, 1)
    assert destroy == {"destroyer": 1} and not sustain and not destroy_damaged
    # Drugie trafienie: dreadnought używa Sustain Damage zamiast zginąć.
    sustain, destroy, _ = battle.neutral_loss_choice(units, costs, 2)
    assert destroy == {"destroyer": 1} and sustain == {"dreadnought": 1}


# ----------------------------------------------------------------------------- ekspedycje


def _pay(**kwargs: Any) -> expeditions.ExpeditionPayment:
    return expeditions.ExpeditionPayment(**kwargs)


def test_expedition_moment_and_one_per_turn(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = _state(registry, grid)
    with pytest.raises(ValueError, match="END of your turn"):
        expeditions.perform_expedition(state, registry, grid, "p1", "tradeGoods", _pay())
    state = _after_action(state)
    with pytest.raises(ValueError, match="not p2's turn"):
        expeditions.perform_expedition(
            _after_action(state, "p2"), registry, grid, "p2", "tradeGoods", _pay()
        )
    done = expeditions.perform_expedition(state, registry, grid, "p1", "tradeGoods", _pay())
    assert done.expeditions.claims == {"tradeGoods": "p1"}
    assert done.players["p1"].trade_goods == 7
    with pytest.raises(ValueError, match="already performed"):
        expeditions.perform_expedition(done, registry, grid, "p1", "fiveRes", _pay(trade_goods=5))
    with pytest.raises(ValueError, match="Unknown expedition slice"):
        expeditions.perform_expedition(state, registry, grid, "p1", "nope", _pay())


def test_expedition_unlocks_breakthrough_and_rolls(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = _after_action(_state(registry, grid))
    done = expeditions.perform_expedition(state, registry, grid, "p1", "tradeGoods", _pay())
    assert done.players["p1"].breakthrough_unlocked is True
    assert done.fracture.last_roll is not None  # rzut po zdobyciu przełomu
    # Gracz, który już ma przełom, nie rzuca ponownie.
    second = done.clone()
    second.expeditions.performed_by = None
    second.fracture.last_roll = None
    second.fracture.in_play = False  # gdyby rzut wystąpił, byłby zapisany
    again = expeditions.perform_expedition(
        second, registry, grid, "p1", "fiveRes", _pay(trade_goods=5)
    )
    assert again.fracture.last_roll is None


@pytest.mark.parametrize(
    ("slice_id", "pay_kwargs", "message"),
    [
        ("fiveRes", {"trade_goods": 4}, "at least 5"),
        ("fiveInf", {"trade_goods": 1}, "at least 5"),
        ("actionCards", {"action_cards": ["a"]}, "exactly 2"),
        ("secret", {}, "unscored secret"),
        ("techSkip", {"tech_planet": "mr"}, "technology specialty"),
        ("tradeGoods", {}, ""),
    ],
)
def test_slice_costs_are_enforced(
    registry: StaticDataRegistry, slice_id: str, pay_kwargs: dict[str, Any], message: str
) -> None:
    grid = _grid(registry)
    state = _after_action(_state(registry, grid))
    state.players["p1"].trade_goods = 2 if slice_id == "tradeGoods" else 10
    if message:
        with pytest.raises(ValueError, match=message):
            expeditions.perform_expedition(
                state, registry, grid, "p1", slice_id, _pay(**pay_kwargs)
            )
    else:
        with pytest.raises(ValueError, match="3 trade goods"):
            expeditions.perform_expedition(
                state, registry, grid, "p1", slice_id, _pay(**pay_kwargs)
            )


def test_card_slices_discard_the_chosen_cards(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = _after_action(_state(registry, grid))
    state.players["p1"].private.action_cards = ["a", "b", "c"]
    state.players["p1"].private.secret_objectives = ["s1", "s2"]
    state.decks.secret_objective_deck = ["s3"]
    done = expeditions.perform_expedition(
        state, registry, grid, "p1", "actionCards", _pay(action_cards=["a", "c"])
    )
    assert done.players["p1"].private.action_cards == ["b"]
    assert done.decks.action_card_discard == ["a", "c"]
    done.expeditions.performed_by = None
    after = expeditions.perform_expedition(done, registry, grid, "p1", "secret", _pay(secret="s2"))
    assert after.players["p1"].private.secret_objectives == ["s1"]
    assert sorted(after.decks.secret_objective_deck) == ["s2", "s3"]
    with pytest.raises(ValueError, match="UNSCORED"):
        expeditions.perform_expedition(done, registry, grid, "p1", "secret", _pay(secret="zzz"))


def test_resource_influence_and_specialty_slices(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = _after_action(_state(registry, grid))
    state.players["p1"].trade_goods = 0
    # Mecatol (wpływ 6) płaci piąty wpływ; planeta ze specjalnością jest wyczerpywana.
    state.systems["000"].planet_owners["mr"] = "p1"
    state.players["p1"].controlled_planets = ["mr"]
    paid = expeditions.perform_expedition(
        state, registry, grid, "p1", "fiveInf", _pay(planets=["mr"])
    )
    assert "mr" in paid.players["p1"].exhausted_planets

    pos = next(
        p for p in grid.positions if p != "000" and registry.systems[grid.system_id_at(p)].planets
    )
    planet = next(
        p
        for p in registry.systems[grid.system_id_at(pos)].planets
        if registry.planets[p].tech_specialties
    )
    state.systems[pos].planet_owners[planet] = "p1"
    state.players["p1"].controlled_planets = [planet]
    skipped = expeditions.perform_expedition(
        state, registry, grid, "p1", "techSkip", _pay(tech_planet=planet)
    )
    assert planet in skipped.players["p1"].exhausted_planets


def _claim_five(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Zajmuje pięć plastrów: p1 trzy, p2 dwa (przez bezpośredni zapis claims)."""
    new_state = state.clone()
    new_state.expeditions.claims = {
        "fiveRes": "p1",
        "actionCards": "p1",
        "fiveInf": "p2",
        "secret": "p2",
        "techSkip": "p1",
    }
    return new_state


def test_sixth_slice_opens_thunders_edge_placement(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = _claim_five(_after_action(_state(registry, grid)), grid, registry)
    state = expeditions.perform_expedition(state, registry, grid, "p1", "tradeGoods", _pay())
    placement = state.expeditions.pending_placement
    assert placement is not None
    assert placement.player_id == "p1" and placement.counts == {"p1": 4, "p2": 2}
    assert placement.leaders == ["p1"]
    assert expeditions.free_slices(state) == []
    assert "All expedition slices" in expeditions.expedition_block_reason(state, "p1")

    targets = expeditions.thunders_edge_targets(state, registry, grid)
    assert targets, "test grid should hold empty systems"
    for position in targets:
        assert not planets_of_system(state, registry, position, grid)
        assert not registry.systems[grid.system_id_at(position)].wormholes
    assert "000" not in targets

    with pytest.raises(ValueError, match="Only p1"):
        expeditions.place_thunders_edge(state, registry, grid, "p2", targets[0])
    with pytest.raises(ValueError, match="cannot hold"):
        expeditions.place_thunders_edge(state, registry, grid, "p1", "000")

    placed = expeditions.place_thunders_edge(state, registry, grid, "p1", targets[0])
    system = placed.systems[targets[0]]
    assert system.added_planets == ["thundersedge"]
    assert system.planet_units["thundersedge"]["p1"] == {"infantry": 4}
    assert system.planet_owners["thundersedge"] == "p1"
    assert placed.expeditions.thunders_edge_position == targets[0]
    assert placed.expeditions.pending_placement is None
    assert planets_of_system(placed, registry, targets[0], grid) == ["thundersedge"]
    # Kolejny Thunder's Edge nie jest możliwy.
    with pytest.raises(ValueError, match="not waiting"):
        expeditions.place_thunders_edge(placed, registry, grid, "p1", targets[1])


def test_tie_lets_placing_player_choose_infantry_owner(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = _after_action(_state(registry, grid))
    state.expeditions.claims = {
        "fiveRes": "p2",
        "actionCards": "p2",
        "fiveInf": "p2",
        "secret": "p1",
        "techSkip": "p1",
    }
    state = expeditions.perform_expedition(state, registry, grid, "p1", "tradeGoods", _pay())
    placement = state.expeditions.pending_placement
    assert placement is not None and placement.leaders == ["p1", "p2"]
    target = expeditions.thunders_edge_targets(state, registry, grid)[0]
    with pytest.raises(ValueError, match="Tie"):
        expeditions.place_thunders_edge(state, registry, grid, "p1", target)
    placed = expeditions.place_thunders_edge(state, registry, grid, "p1", target, "p2")
    assert placed.systems[target].planet_units["thundersedge"]["p2"] == {"infantry": 3}
    assert placed.systems[target].planet_owners["thundersedge"] == "p2"


def test_ingress_goes_to_thunders_edge_when_it_is_on_the_board(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid(registry)
    state = _state(registry, grid)
    target = expeditions.thunders_edge_targets(state, registry, grid)[0]
    state.expeditions.thunders_edge_position = target
    entered = enter_play(state, registry, grid, "p1")
    assert entered.systems[target].ingress_token is True
    # Mecatol dostaje ingress tylko wtedy, gdy Thunder's Edge nie ma na planszy.
    assert entered.systems["000"].ingress_token is False


def test_expedition_slice_order_is_clockwise_from_top() -> None:
    assert EXPEDITION_SLICES == (
        "fiveRes",
        "actionCards",
        "fiveInf",
        "secret",
        "techSkip",
        "tradeGoods",
    )


# --------------------------------------------------------------------------------- API


def _client(registry: StaticDataRegistry, state: GameState, grid: HexGrid) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    app.state.ctx.current_grid = grid
    return TestClient(app)


def test_api_expedition_flow_and_web_data(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = _after_action(_state(registry, grid))
    client = _client(registry, state, grid)

    view: dict[str, Any] = client.get("/thunders-edge").json()
    assert view["canPerform"] is True and view["fractureInPlay"] is False
    assert [s["id"] for s in view["slices"]] == list(EXPEDITION_SLICES)

    response = client.post("/expeditions/perform", json={"slice": "tradeGoods"})
    assert response.status_code == 200, response.text
    again = client.post(
        "/expeditions/perform", json={"slice": "fiveRes", "payment": {"trade_goods": 5}}
    )
    assert again.status_code == 422  # jedna ekspedycja na turę

    web = client.get("/api/public/game/g/web-data").json()
    assert web["expeditions"]["tradeGoods"]["completedBy"] is not None
    assert web["expeditions"]["fiveRes"]["completedBy"] is None
    assert "thundersEdge" in web["gameState"]


def test_api_god_mode_fracture_and_ingress(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    client = _client(registry, _state(registry, grid), grid)
    response = client.post("/god-mode/fracture", json={"breakthrough_id": "arborecbt"})
    assert response.status_code == 200, response.text

    view = client.get("/thunders-edge").json()
    assert view["fractureInPlay"] is True and view["pendingIngress"]
    choice = view["pendingIngress"][0]
    position = choice["candidates"][0]
    ok = client.post("/fracture/ingress", json={"color": choice["color"], "position": position})
    assert ok.status_code == 200, ok.text
    bad = client.post("/fracture/ingress", json={"color": choice["color"], "position": "000"})
    assert bad.status_code == 422

    web = client.get("/api/public/game/g/web-data").json()
    assert all(f"frac{i}" in {e.split(":")[0] for e in web["tilePositions"]} for i in range(1, 8))
    tokens = [
        e["entityId"]
        for e in web["tileUnitData"][position]["space"].get("neutral", [])
        if e["entityType"] == "token"
    ]
    assert "ingress" in tokens
    frac1 = web["tileUnitData"]["frac1"]
    assert "relictoken" in {
        e["entityId"] for e in frac1["planets"]["cocytus"]["entities"]["neutral"]
    }


def test_api_battle_view_with_neutral_defender(registry: StaticDataRegistry) -> None:
    grid = _grid(registry)
    state = enter_play(_state(registry, grid, seed=5), registry, grid, "p1")
    sync_grid(grid, state, registry)
    state.active_system = "frac1"
    state.tactical_step = TacticalStep.SPACE_COMBAT
    state.systems["frac1"].space_units["p1"] = {"cruiser": 8}
    client = _client(registry, state, grid)
    assert client.post("/tactical/battle/start", json={}).status_code == 200
    for step in ("roll",):
        response = client.post(f"/tactical/battle/{step}", json={})
        assert response.status_code in (200, 422), response.text
    view = client.get("/tactical/battle")
    assert view.status_code == 200, view.text
    assert view.json()["active"] is True


def test_neutral_fleets_never_trigger_fleet_pool_or_capacity(registry: StaticDataRegistry) -> None:
    from src.core import capacity, fleet_pool

    grid = _grid(registry)
    state = enter_play(_state(registry, grid), registry, grid, "p1")
    for position in ("frac1", "frac4", "frac7"):
        assert fleet_pool.players_with_excess(state, position) == []
        assert capacity.players_with_excess(state, registry, position) == []
        assert fleet_pool.open_fleet_pool_check(state, position).pending_window is None
