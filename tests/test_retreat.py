"""Testy odwrotów w walce kosmicznej (RULES.md 39.5): ogłoszenie, cele, wykonanie, żeton, API."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import battle, damage, retreat
from src.core.event_store import EventStore
from src.core.game_state import (
    CombatStep,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.movement import CargoPickup
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    """000 = aktywny; sąsiedzi: 101 (zwykły), 102 (mgławica), 103 (asteroidy), 104 (supernowa)."""
    grid = HexGrid()
    grid.place_system("000", "18", anomalies=set())
    grid.place_system("101", "20", anomalies=set())
    grid.place_system("102", "21", anomalies={"NEBULA"})
    grid.place_system("103", "22", anomalies={"ASTEROID_FIELD"})
    grid.place_system("104", "23", anomalies={"SUPERNOVA"})
    grid.build_edges()
    return grid


def _state(
    space: dict[str, dict[str, int]],
    *,
    presence: dict[str, dict[str, dict[str, int]]] | None = None,
    planet: dict[str, dict[str, int]] | None = None,
    owners: dict[str, str] | None = None,
) -> GameState:
    """Walka w 000 (p1 atakuje). ``presence`` = przestrzeń sąsiednich systemów {pos: {pid: ..}}."""
    center = SystemState(position="000", system_id="18")
    for pid, by_type in space.items():
        center.space_units[pid] = dict(by_type)
    for pid, by_type in (planet or {}).items():
        center.planet_units.setdefault("pl", {})[pid] = dict(by_type)
    center.planet_owners = dict(owners or {})
    systems = {"000": center}
    for pos, sid in (("101", "20"), ("102", "21"), ("103", "22"), ("104", "23")):
        system = SystemState(position=pos, system_id=sid)
        for pid, by_type in (presence or {}).get(pos, {}).items():
            system.space_units[pid] = dict(by_type)
        systems[pos] = system
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=TacticalStep.SPACE_COMBAT,
        seating_order=["p1", "p2"],
        players={pid: PlayerState(player_id=pid, color=pid) for pid in ("p1", "p2")},
        systems=systems,
        rng_seed=1,
    )


def _everywhere(pid: str, unit: str = "destroyer") -> dict[str, dict[str, dict[str, int]]]:
    """Jednostka gracza w KAŻDYM sąsiednim systemie (żeby sprawdzić filtr anomalii)."""
    return {pos: {pid: {unit: 1}} for pos in ("101", "102", "103", "104")}


# --------------------------------------------------------------------- cele odwrotu


@ruling("R_nebula/notes/3", "R_supernova/rules-reference/1", "R_asteroid_field/rules-reference/1")
def test_destinations_need_presence_and_skip_anomalies() -> None:
    grid = _grid()
    state = _state({"p1": {"cruiser": 1}, "p2": {"cruiser": 1}}, presence=_everywhere("p2"))
    # Supernowa i asteroidy (bez Antimass) odpadają; do mgławicy wolno się wycofać (R_nebula
    # notes/3, decyzja użytkownika 2026-11-24).
    assert retreat.retreat_destinations(state, grid, "000", "p2") == ["101", "102"]
    assert retreat.retreat_destinations(state, grid, "000", "p1") == []  # brak obecności
    state.players["p2"].technologies = ["amd"]  # Antimass Deflectors (alias z danych)
    assert retreat.retreat_destinations(state, grid, "000", "p2") == ["101", "102", "103"]


def test_destination_with_enemy_ships_or_controlled_planet() -> None:
    grid = _grid()
    state = _state(
        {"p1": {"cruiser": 1}, "p2": {"cruiser": 1}},
        presence={"101": {"p2": {"destroyer": 1}, "p1": {"fighter": 1}}},
    )
    assert retreat.retreat_destinations(state, grid, "000", "p2") == []  # obcy statek w 101
    state.systems["101"].space_units.pop("p1")
    assert retreat.retreat_destinations(state, grid, "000", "p2") == ["101"]
    # Sama kontrolowana planeta też wystarcza.
    state2 = _state({"p1": {"cruiser": 1}, "p2": {"cruiser": 1}})
    state2.systems["101"].planet_owners = {"x": "p1"}
    assert retreat.retreat_destinations(state2, grid, "000", "p1") == ["101"]


# ------------------------------------------------------------------- przebieg walki


def test_no_destinations_skips_announce(registry: StaticDataRegistry) -> None:
    started = battle.start_combat(
        _state({"p1": {"cruiser": 1}, "p2": {"carrier": 1}}), _grid(), registry
    )
    assert started.active_combat is not None
    assert started.active_combat.step is CombatStep.ROLL
    assert started.pending_window is None


def test_announce_window_defender_first(registry: StaticDataRegistry) -> None:
    state = _state(
        {"p1": {"cruiser": 1}, "p2": {"carrier": 1}},
        presence={"101": {"p1": {"fighter": 1}}, "103": {"p2": {"fighter": 1}}},
    )
    state.players["p2"].technologies = ["amd"]
    started = battle.start_combat(state, _grid(), registry)
    combat = started.active_combat
    window = started.pending_window
    assert combat is not None and combat.step is CombatStep.ANNOUNCE
    assert window is not None and window.window_type is WindowType.COMBAT_RETREAT
    assert window.queue == ["p2", "p1"]
    with pytest.raises(ValueError, match="turn"):
        battle.announce_retreat(started, _grid(), "p1", announce=True)
    # Obrońca ogłasza odwrót → atakujący nie może już ogłosić (okno zamknięte), dalej rzuty.
    announced = battle.announce_retreat(started, _grid(), "p2", announce=True)
    assert announced.pending_window is None
    assert announced.active_combat is not None
    assert announced.active_combat.step is CombatStep.ROLL
    assert announced.active_combat.retreating == ["p2"]


def test_attacker_may_announce_when_defender_stays(registry: StaticDataRegistry) -> None:
    state = _state(
        {"p1": {"cruiser": 1}, "p2": {"carrier": 1}},
        presence={"101": {"p1": {"fighter": 1}}, "103": {"p2": {"fighter": 1}}},
    )
    state.players["p2"].technologies = ["amd"]
    grid = _grid()
    started = battle.start_combat(state, grid, registry)
    stayed = battle.announce_retreat(started, grid, "p2", announce=False)
    assert stayed.pending_window is not None  # teraz kolej atakującego
    attacked = battle.announce_retreat(stayed, grid, "p1", announce=True)
    assert attacked.pending_window is None
    assert attacked.active_combat is not None
    assert attacked.active_combat.retreating == ["p1"]


def _announced_and_rolled(
    registry: StaticDataRegistry, state: GameState, grid: HexGrid, pid: str
) -> GameState:
    """Ogłasza odwrót ``pid`` i rzuca tak, by NIKT nie miał trafień (prosto do kroku Retreat)."""
    started = battle.start_combat(state, grid, registry)
    window = started.pending_window
    assert window is not None
    current = started
    while current.pending_window is not None:
        responder = current.pending_window.current_responder
        assert responder is not None
        current = battle.announce_retreat(current, grid, responder, announce=responder == pid)
    for seed in range(1, 600):
        candidate = current.clone()
        candidate.rng_seed = seed
        rolled = battle.roll_round(candidate, grid, registry)
        if rolled.pending_window is None:
            return rolled
    raise AssertionError("no seed without hits")


def test_retreat_moves_ships_cargo_and_places_token(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state(
        {"p1": {"cruiser": 2}, "p2": {"carrier": 1, "fighter": 2, "infantry": 1, "cruiser": 1}},
        presence={"101": {"p2": {"fighter": 1}}},
    )
    rolled = _announced_and_rolled(registry, state, grid, "p2")
    combat = rolled.active_combat
    assert combat is not None and combat.step is CombatStep.RETREAT
    reinf = rolled.players["p2"].cc_reinf
    with pytest.raises(ValueError, match="cannot retreat"):
        battle.retreat_from_combat(rolled, grid, registry, "p2", "102")
    done = battle.retreat_from_combat(rolled, grid, registry, "p2", "101")
    # Carrier (capacity z danych) zabiera ładunek; w 000 nie zostaje nic z p2.
    assert done.systems["000"].space_units.get("p2") is None
    moved = done.systems["101"].space_units["p2"]
    assert moved["carrier"] == 1 and moved["cruiser"] == 1
    assert "p2" in done.systems["101"].command_tokens
    assert done.players["p2"].cc_reinf == reinf - 1
    final = done.active_combat
    assert final is not None and final.step is CombatStep.DONE
    assert final.winner == "p1"
    assert final.retreated == {"p2": "101"}
    assert final.log[-1]["phase"] == "RETREAT"


def test_cargo_without_capacity_is_removed(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state(
        {"p1": {"cruiser": 2}, "p2": {"cruiser": 1, "fighter": 2}},
        presence={"101": {"p2": {"destroyer": 1}}},
    )
    rolled = _announced_and_rolled(registry, state, grid, "p2")
    done = battle.retreat_from_combat(rolled, grid, registry, "p2", "101")
    assert done.systems["101"].space_units["p2"] == {"destroyer": 1, "cruiser": 1}
    entry = done.active_combat.log[-1] if done.active_combat else {}
    assert entry["losses"]["p2"] == {"fighter": 2}


def test_retreat_carries_damage(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state(
        {"p1": {"cruiser": 2}, "p2": {"dreadnought": 1}},
        presence={"101": {"p2": {"destroyer": 1}}},
    )
    damage.set_damaged(state.systems["000"], "space", "p2", "dreadnought", 1)
    rolled = _announced_and_rolled(registry, state, grid, "p2")
    done = battle.retreat_from_combat(rolled, grid, registry, "p2", "101")
    assert damage.damaged_count(done.systems["101"], "space", "p2", "dreadnought") == 1


def test_explicit_cargo_cannot_leave_units_with_free_capacity(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = _state(
        {"p1": {"cruiser": 2}, "p2": {"carrier": 1, "fighter": 1}},
        presence={"101": {"p2": {"destroyer": 1}}},
    )
    rolled = _announced_and_rolled(registry, state, grid, "p2")
    with pytest.raises(ValueError, match="free capacity"):
        battle.retreat_from_combat(rolled, grid, registry, "p2", "101", cargo=[])
    with pytest.raises(ValueError, match="Not enough"):
        battle.retreat_from_combat(
            rolled, grid, registry, "p2", "101", cargo=[CargoPickup("fighter", 3)]
        )


def test_token_not_duplicated_and_pool_used_when_reinforcements_empty(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = _state(
        {"p1": {"cruiser": 2}, "p2": {"cruiser": 1}},
        presence={"101": {"p2": {"destroyer": 1}}},
    )
    state.players["p2"].cc_reinf = 0
    rolled = _announced_and_rolled(registry, state, grid, "p2")
    tactic = rolled.players["p2"].tactical_cc
    done = battle.retreat_from_combat(rolled, grid, registry, "p2", "101", token_pool="tactic")
    assert done.players["p2"].tactical_cc == tactic - 1
    # Żeton już leży w 101 — drugi odwrót tam nie kładzie kolejnego.
    state2 = _state(
        {"p1": {"cruiser": 2}, "p2": {"cruiser": 1}},
        presence={"101": {"p2": {"destroyer": 1}}},
    )
    state2.systems["101"].command_tokens = ["p2"]
    rolled2 = _announced_and_rolled(registry, state2, grid, "p2")
    reinf = rolled2.players["p2"].cc_reinf
    done2 = battle.retreat_from_combat(rolled2, grid, registry, "p2", "101")
    assert done2.systems["101"].command_tokens == ["p2"]
    assert done2.players["p2"].cc_reinf == reinf


def test_retreat_does_not_happen_when_opponent_destroyed(
    registry: StaticDataRegistry,
) -> None:
    """O3: ogłoszony odwrót, ale przeciwnik stracił statki → walka kończy się bez odwrotu."""
    grid = _grid()
    state = _state(
        {"p1": {"fighter": 1}, "p2": {"dreadnought": 3}},
        presence={"101": {"p2": {"destroyer": 1}}},
    )
    started = battle.start_combat(state, grid, registry)
    announced = battle.announce_retreat(started, grid, "p2", announce=True)
    for seed in range(1, 600):
        candidate = announced.clone()
        candidate.rng_seed = seed
        rolled = battle.roll_round(candidate, grid, registry)
        combat = rolled.active_combat
        assert combat is not None
        if combat.pending_hits.get("p1", 0) >= 1 and combat.pending_hits.get("p2", 0) == 0:
            break
    else:
        raise AssertionError("no seed")
    after = battle.assign_combat_hits(
        rolled, grid, registry, "p1", sustain={}, destroy={"fighter": 1}, destroy_damaged={}
    )
    combat = after.active_combat
    assert combat is not None and combat.step is CombatStep.DONE
    assert combat.winner == "p2" and combat.retreated == {}
    assert after.systems["000"].space_units["p2"] == {"dreadnought": 3}


def test_ground_combat_has_no_announce(registry: StaticDataRegistry) -> None:
    state = _state(
        {},
        planet={"p1": {"infantry": 1}, "p2": {"infantry": 1}},
        presence={"101": {"p2": {"destroyer": 1}}},
    )
    state.tactical_step = TacticalStep.INVASION
    started = battle.start_combat(state, _grid(), registry, planet="pl")
    assert started.active_combat is not None
    assert started.active_combat.step is CombatStep.ROLL


# --------------------------------------------------------------------------- API


def test_api_retreat_flow(registry: StaticDataRegistry) -> None:
    state = _state(
        {"p1": {"cruiser": 1}, "p2": {"carrier": 1}},
        presence={"101": {"p2": {"destroyer": 1}}},
    )
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    client = TestClient(app)
    assert client.post("/tactical/battle/start", json={}).status_code == 200
    view: dict[str, Any] = client.get("/tactical/battle").json()
    assert view["step"] == "ANNOUNCE"
    assert view["announcing"] == "p2"
    assert [o["position"] for o in view["retreatOptions"]["p2"]] == ["101"]
    assert view["retreatOptions"]["p1"] == []
    bad = client.post("/tactical/battle/announce-retreat", json={"faction": "p1"})
    assert bad.status_code == 422
    ok = client.post("/tactical/battle/announce-retreat", json={"faction": "p2"})
    assert ok.status_code == 200
    after: dict[str, Any] = client.get("/tactical/battle").json()
    assert after["step"] == "ROLL" and after["retreating"] == ["p2"]
    assert client.post(
        "/tactical/battle/retreat", json={"faction": "p2", "destination": "101"}
    ).status_code == 422  # jeszcze nie krok Retreat
