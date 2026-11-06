"""Testy Space Cannon Offense (RULES.md 38): strzelcy, zasięg deep, kolejka, rzuty, straty."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import dice, space_cannon, tactical, timing
from src.core.event_store import EventStore
from src.core.game_state import (
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid() -> HexGrid:
    """Centrum 000 + pierścień 101..103 (każdy sąsiaduje z 000)."""
    grid = HexGrid()
    for pos, sid in [("000", "18"), ("101", "20"), ("102", "22"), ("103", "23")]:
        grid.place_system(pos, sid, anomalies=set())
    grid.build_edges()
    return grid


def _state(
    *,
    active: str = "p1",
    seating: tuple[str, ...] = ("p1", "p2", "p3"),
    pds: dict[str, int] | None = None,
    pds_adjacent: dict[str, int] | None = None,
    ships: dict[str, dict[str, int]] | None = None,
    techs: dict[str, list[str]] | None = None,
    seed: int = 1,
) -> GameState:
    """Aktywny system 000. ``pds`` = PDS na planecie 'pl' w 000; ``pds_adjacent`` = PDS w 101."""
    techs = techs or {}
    players = {
        pid: PlayerState(player_id=pid, color=pid, technologies=techs.get(pid, []))
        for pid in seating
    }
    center = SystemState(position="000", system_id="18")
    for pid, count in (pds or {}).items():
        center.planet_units.setdefault("pl", {})[pid] = {"pds": count}
    for pid, by_type in (ships or {}).items():
        center.space_units[pid] = dict(by_type)
    systems = {"000": center}
    if pds_adjacent:
        adjacent = SystemState(position="101", system_id="20")
        adjacent.planet_units["pa"] = {pid: {"pds": c} for pid, c in pds_adjacent.items()}
        systems["101"] = adjacent
    return GameState(
        phase=Phase.ACTION,
        active_player_id=active,
        active_system="000",
        tactical_step=TacticalStep.SPACE_CANNON,
        seating_order=list(seating),
        players=players,
        systems=systems,
        rng_seed=seed,
    )


# ------------------------------------------------------------------ kości (dice)


def test_dice_deterministic_for_same_seed() -> None:
    a_state, a = dice.roll_dice(GameState(rng_seed=42), 8)
    b_state, b = dice.roll_dice(GameState(rng_seed=42), 8)
    assert a == b
    assert all(1 <= v <= 10 for v in a)
    assert a_state.rng_counter == b_state.rng_counter == 1


def test_dice_counter_advances_and_seed_is_lazy() -> None:
    state, first = dice.roll_dice(GameState(), 5)
    assert state.rng_seed != 0  # ziarno wylosowane i zapisane w stanie
    assert state.rng_counter == 1
    replay_state, replay = dice.roll_dice(
        GameState(rng_seed=state.rng_seed, rng_counter=0), 5
    )
    assert replay == first  # ten sam (ziarno, licznik) = ten sam wynik
    assert replay_state.rng_counter == 1
    after_second, _ = dice.roll_dice(state, 5)
    assert after_second.rng_counter == 2  # kolejny rzut używa kolejnego strumienia


def test_count_hits_uses_threshold_inclusive() -> None:
    assert dice.count_hits([1, 5, 6, 10], 6) == 2
    assert dice.count_hits([1, 2], 3) == 0


# --------------------------------------------------------- strzelcy i zasięg (deep)


def test_pds_in_active_system_fires_directly(registry: StaticDataRegistry) -> None:
    state = _state(pds={"p2": 2}, ships={"p1": {"destroyer": 1}})
    shooters = space_cannon.offense_shooters(state, _grid(), registry, "p2")
    assert len(shooters) == 1
    s = shooters[0]
    assert (s.base_type, s.zone, s.count, s.remote) == ("pds", "pl", 2, False)
    assert s.hits_on == 6  # PDS I z danych (baseUnits.json)


def test_adjacent_pds_needs_pds2_technology(registry: StaticDataRegistry) -> None:
    """PDS I w sąsiednim systemie NIE strzela; po technologii PDS II (deep) — tak."""
    base = _state(pds_adjacent={"p2": 1}, ships={"p1": {"destroyer": 1}})
    assert space_cannon.offense_shooters(base, _grid(), registry, "p2") == []

    upgraded = _state(
        pds_adjacent={"p2": 1},
        ships={"p1": {"destroyer": 1}},
        techs={"p2": ["pds2"]},
    )
    shooters = space_cannon.offense_shooters(upgraded, _grid(), registry, "p2")
    assert len(shooters) == 1
    assert shooters[0].remote is True
    assert shooters[0].position == "101"
    assert shooters[0].hits_on == 5  # PDS II: trafia na 5+ (dane)


def test_pds2_tech_alias_exists_in_registry(registry: StaticDataRegistry) -> None:
    assert "pds2" in registry.technologies


def test_coverage_marks_tiles_under_fire(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = _state(pds_adjacent={"p2": 2}, techs={"p2": ["pds2"]})
    cover = space_cannon.coverage(state, grid, registry)
    # PDS II w 101: własny kafelek (2 kości po 5+) i sąsiednie (tu: centrum 000).
    assert cover["101"]["p2"] == (2, 1.2)
    assert cover["000"]["p2"] == (2, 1.2)
    # Bez technologii pokrycie dotyczy tylko własnego kafelka.
    plain = space_cannon.coverage(_state(pds_adjacent={"p2": 2}), grid, registry)
    assert "000" not in plain
    assert plain["101"]["p2"] == (2, 1.0)  # PDS I: 6+ na d10 = 5/10 na kość, 2 kości


# ------------------------------------------------------------------- kolejka i cele


def test_queue_starts_with_active_player_clockwise(registry: StaticDataRegistry) -> None:
    state = _state(
        active="p2",
        pds={"p1": 1, "p2": 1, "p3": 1},
        ships={"p1": {"destroyer": 1}, "p2": {"destroyer": 1}, "p3": {"destroyer": 1}},
    )
    assert space_cannon.offense_queue(state, _grid(), registry) == ["p2", "p3", "p1"]


def test_non_active_player_can_fire_and_must_target_active(
    registry: StaticDataRegistry,
) -> None:
    """Strzela też gracz NIEaktywny (p2) i musi celować w aktywnego (p1)."""
    state = _state(pds={"p2": 1}, ships={"p1": {"destroyer": 2}, "p3": {"cruiser": 1}})
    assert space_cannon.offense_targets(state, "p2") == ["p1"]
    # Aktywny wybiera spośród graczy ze statkami.
    assert space_cannon.offense_targets(state, "p1") == ["p3"]
    assert space_cannon.offense_queue(state, _grid(), registry) == ["p2"]


def test_player_without_target_is_skipped(registry: StaticDataRegistry) -> None:
    """Aktywny gracz bez statków w systemie: nieaktywni nie mają kogo trafić → brak okna."""
    state = _state(pds={"p2": 1}, ships={"p3": {"cruiser": 1}})
    assert space_cannon.offense_queue(state, _grid(), registry) == []
    opened = space_cannon.open_offense(state, _grid(), registry)
    assert opened.pending_window is None


# ---------------------------------------------------------- okno: strzał / straty


def _open(state: GameState, registry: StaticDataRegistry) -> GameState:
    return space_cannon.open_offense(state, _grid(), registry)


def test_open_creates_space_cannon_window(registry: StaticDataRegistry) -> None:
    state = _state(pds={"p2": 1}, ships={"p1": {"destroyer": 1}})
    opened = _open(state, registry)
    assert opened.pending_window is not None
    assert opened.pending_window.window_type is WindowType.SPACE_CANNON
    assert opened.pending_window.queue == ["p2"]


def test_fire_out_of_turn_rejected(registry: StaticDataRegistry) -> None:
    state = _state(
        pds={"p1": 1, "p2": 1}, ships={"p1": {"destroyer": 1}, "p2": {"destroyer": 1}}
    )
    opened = _open(state, registry)
    assert opened.pending_window is not None
    assert opened.pending_window.queue == ["p1", "p2"]
    with pytest.raises(ValueError, match="turn"):
        space_cannon.fire_offense(opened, _grid(), registry, "p2", "p1")


def _fire_until_hit(
    base: GameState, registry: StaticDataRegistry, player: str, target: str | None
) -> GameState:
    """Szuka ziarna, przy którym strzał trafia (wynik deterministyczny dla ziarna)."""
    for seed in range(1, 200):
        candidate = base.clone()
        candidate.rng_seed = seed
        fired = space_cannon.fire_offense(candidate, _grid(), registry, player, target)
        if space_cannon.pending_hits(fired) is not None:
            return fired
    raise AssertionError("no seed produced a hit")


def test_fire_assign_flow_destroys_ships_and_closes_window(
    registry: StaticDataRegistry,
) -> None:
    state = _state(
        pds={"p2": 12}, ships={"p1": {"destroyer": 2, "fighter": 1}}
    )  # 12 kości — trafienia pewne dla jakiegoś ziarna
    fired = _fire_until_hit(_open(state, registry), registry, "p2", None)
    pending = space_cannon.pending_hits(fired)
    assert pending is not None
    assert (pending.roller, pending.target) == ("p2", "p1")
    required = min(pending.hits, 3)

    # Nie można iść dalej, dopóki nie przypisano strat.
    with pytest.raises(ValueError, match="pending hits"):
        space_cannon.pass_offense(fired, "p2")
    # Zła liczba strat / zły gracz / za dużo danego typu.
    with pytest.raises(ValueError, match="exactly"):
        space_cannon.assign_hits(fired, "p1", {})
    with pytest.raises(ValueError, match="targeted player"):
        space_cannon.assign_hits(fired, "p3", {"destroyer": required})
    with pytest.raises(ValueError, match="only"):
        space_cannon.assign_hits(fired, "p1", {"cruiser": required})

    losses: dict[str, int] = {}
    left = required
    for base_type, have in (("fighter", 1), ("destroyer", 2)):
        take = min(have, left)
        if take:
            losses[base_type] = take
            left -= take
    after = space_cannon.assign_hits(fired, "p1", losses)

    remaining = sum(after.systems["000"].space_units.get("p1", {}).values())
    assert remaining == 3 - required
    assert space_cannon.pending_hits(after) is None
    assert after.pending_window is None  # jedyny strzelec skończył → okno zamknięte


def test_pass_advances_and_closes_window(registry: StaticDataRegistry) -> None:
    state = _state(pds={"p2": 1}, ships={"p1": {"destroyer": 1}})
    opened = _open(state, registry)
    passed = space_cannon.pass_offense(opened, "p2")
    assert passed.pending_window is None
    assert passed.systems["000"].space_units["p1"] == {"destroyer": 1}


def test_fire_with_explicit_illegal_target_rejected(registry: StaticDataRegistry) -> None:
    state = _state(pds={"p2": 1}, ships={"p1": {"destroyer": 1}, "p3": {"cruiser": 1}})
    opened = _open(state, registry)
    with pytest.raises(ValueError, match="Illegal"):
        space_cannon.fire_offense(opened, _grid(), registry, "p2", "p3")


def test_active_player_must_choose_target_when_ambiguous(
    registry: StaticDataRegistry,
) -> None:
    state = _state(
        pds={"p1": 1},
        ships={"p1": {"destroyer": 1}, "p2": {"cruiser": 1}, "p3": {"cruiser": 1}},
    )
    opened = _open(state, registry)
    with pytest.raises(ValueError, match="Choose"):
        space_cannon.fire_offense(opened, _grid(), registry, "p1", None)


# --------------------------------------------------------- integracja z krokami akcji


def test_next_step_blocked_while_window_open(registry: StaticDataRegistry) -> None:
    state = _state(pds={"p2": 1}, ships={"p1": {"destroyer": 1}})
    opened = _open(state, registry)
    with pytest.raises(ValueError, match="Space Cannon"):
        tactical.next_step(opened)


def test_ending_action_clears_space_cannon_window(registry: StaticDataRegistry) -> None:
    state = _state(pds={"p2": 1}, ships={"p1": {"destroyer": 1}})
    ended = tactical.end_tactical_action(_open(state, registry))
    assert ended.pending_window is None


def test_other_open_window_blocks_space_cannon(registry: StaticDataRegistry) -> None:
    state = _state(pds={"p2": 1}, ships={"p1": {"destroyer": 1}})
    busy = timing.open_window(state, WindowType.REACTION, ["p2"])
    with pytest.raises(ValueError, match="Another timing window"):
        space_cannon.open_offense(busy, _grid(), registry)


# --------------------------------------------------------------------------- API


def _client(registry: StaticDataRegistry, state: GameState) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    return TestClient(app)


def test_api_step_next_opens_window_and_panel_reports_it(
    registry: StaticDataRegistry,
) -> None:
    state = _state(pds={"p2": 2}, ships={"p1": {"destroyer": 2}})
    state.tactical_step = TacticalStep.MOVEMENT
    client = _client(registry, state)

    assert client.post("/tactical/step/next").status_code == 200
    panel: dict[str, Any] = client.get("/tactical/space-cannon").json()
    assert panel["isOpen"] is True
    assert panel["queue"] == ["p2"]  # klucz tożsamości (brak frakcji → player_id)
    assert panel["current"] == "p2"
    side = panel["sides"][0]
    assert side["targets"] == ["p1"]
    assert side["shooters"][0]["hitsOn"] == 6
    assert side["totalDice"] == 2

    # Nie wolno wyjść z kroku przy otwartym oknie.
    blocked = client.post("/tactical/step/next")
    assert blocked.status_code == 422
    assert "Space Cannon" in blocked.json()["detail"]


def test_api_fire_and_pass_resolve_window(registry: StaticDataRegistry) -> None:
    state = _state(pds={"p2": 1}, ships={"p1": {"destroyer": 2}})
    state.tactical_step = TacticalStep.MOVEMENT
    client = _client(registry, state)
    client.post("/tactical/step/next")

    out_of_turn = client.post("/tactical/space-cannon/fire", json={"faction": "p1"})
    assert out_of_turn.status_code == 422

    assert client.post("/tactical/space-cannon/pass", json={"faction": "p2"}).status_code == 200
    panel = client.get("/tactical/space-cannon").json()
    assert panel["isOpen"] is False


def test_web_data_exposes_space_cannon_range(registry: StaticDataRegistry) -> None:
    """Kontrakt web-data: ``tileUnitData[pos].pds`` = pokrycie ostrzałem (soczewka mapy)."""
    state = _state(
        pds_adjacent={"p2": 1},
        ships={"p1": {"destroyer": 1}},
        techs={"p2": ["pds2"]},
    )
    client = _client(registry, state)
    data = client.get(
        "/api/public/game/g/web-data", params={"viewing_player": "p1"}
    ).json()
    tiles = data["tileUnitData"]
    assert tiles["101"]["pds"]["p2"]["count"] == 1  # własny kafelek PDS
    assert tiles["000"]["pds"]["p2"]["count"] == 1  # deep: sięga sąsiedniego systemu
    assert tiles["000"]["pds"]["p2"]["expected"] == 0.6  # 5+ na d10 → 6/10
