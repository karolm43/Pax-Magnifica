"""Testy silnika walki (RULES.md 39): strony, AFB, rzuty, Sustain Damage, straty, koniec, API."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import battle, damage, movement, status_phase, tactical, turn_flow
from src.core.combat import resolve_unit_variant
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
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _grid(nebula: bool = False) -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", "18", anomalies={"NEBULA"} if nebula else set())
    grid.place_system("101", "20", anomalies=set())
    grid.build_edges()
    return grid


def _state(
    space: dict[str, dict[str, int]] | None = None,
    planet: dict[str, dict[str, int]] | None = None,
    *,
    step: TacticalStep = TacticalStep.SPACE_COMBAT,
    players: tuple[str, ...] = ("p1", "p2"),
    seed: int = 1,
) -> GameState:
    """Aktywny p1, aktywny system 000; ``planet`` = jednostki na planecie 'pl' w 000."""
    center = SystemState(position="000", system_id="18")
    for pid, by_type in (space or {}).items():
        center.space_units[pid] = dict(by_type)
    for pid, by_type in (planet or {}).items():
        center.planet_units.setdefault("pl", {})[pid] = dict(by_type)
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=step,
        seating_order=list(players),
        players={pid: PlayerState(player_id=pid, color=pid) for pid in players},
        systems={"000": center},
        rng_seed=seed,
    )


def _seek(
    state: GameState, action: Callable[[GameState], GameState], ok: Callable[[GameState], bool]
) -> GameState:
    """Szuka ziarna, przy którym akcja daje oczekiwany wynik (rzuty są deterministyczne)."""
    for seed in range(1, 400):
        candidate = state.clone()
        candidate.rng_seed = seed
        result = action(candidate)
        if ok(result):
            return result
    raise AssertionError("no seed produced the expected outcome")


def _afb_assigned(state: GameState, registry: StaticDataRegistry) -> GameState:
    """AFB i przypisanie jego trafień przez właścicieli myśliwców (krok ASSIGN, RULES.md 39 W4)."""
    out = battle.resolve_afb(state, _grid(), registry)
    while (
        out.active_combat is not None
        and out.active_combat.step is CombatStep.ASSIGN
        and out.pending_window is not None
    ):
        pid = out.pending_window.current_responder
        assert pid is not None
        need = battle.required_hits(out, _grid(), registry, pid)
        out = battle.assign_combat_hits(
            out, _grid(), registry, pid, sustain={}, destroy={"fighter": need}, destroy_damaged={}
        )
    return out


def _units(state: GameState, pid: str) -> dict[str, int]:
    return state.systems["000"].space_units.get(pid, {})


# --------------------------------------------------------------------------- start


def test_start_space_combat_sets_sides_and_afb(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"destroyer": 1}, "p2": {"fighter": 2}})
    started = battle.start_combat(state, _grid(), registry)
    combat = started.active_combat
    assert combat is not None
    assert (combat.kind, combat.attacker, combat.defender) == ("space", "p1", "p2")
    assert combat.step is CombatStep.AFB  # destroyer ma Anti-Fighter Barrage (dane)


def test_start_without_afb_units_goes_to_roll(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"cruiser": 1}, "p2": {"carrier": 1}})
    started = battle.start_combat(state, _grid(), registry)
    assert started.active_combat is not None
    assert started.active_combat.step is CombatStep.ROLL


def test_start_requires_space_combat_step(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"cruiser": 1}, "p2": {"carrier": 1}}, step=TacticalStep.MOVEMENT)
    with pytest.raises(ValueError, match="SPACE_COMBAT"):
        battle.start_combat(state, _grid(), registry)


def test_start_without_opponent_rejected(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="no combat"):
        battle.start_combat(_state({"p1": {"cruiser": 1}}), _grid(), registry)


def test_three_sides_rejected(registry: StaticDataRegistry) -> None:
    state = _state(
        {"p1": {"cruiser": 1}, "p2": {"carrier": 1}, "p3": {"cruiser": 1}},
        players=("p1", "p2", "p3"),
    )
    with pytest.raises(ValueError, match="More than two"):
        battle.start_combat(state, _grid(), registry)


# ----------------------------------------------------------------------------- AFB


def test_afb_destroys_only_fighters_and_can_end_combat(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"destroyer": 2}, "p2": {"fighter": 1}})
    started = battle.start_combat(state, _grid(), registry)
    done = _seek(
        started,
        lambda s: _afb_assigned(s, registry),
        lambda s: s.active_combat is not None and s.active_combat.step is CombatStep.DONE,
    )
    combat = done.active_combat
    assert combat is not None
    assert combat.winner == "p1" and combat.outcome == "winner"
    assert _units(done, "p2") == {}
    assert _units(done, "p1") == {"destroyer": 2}  # AFB nie trafia w statki atakującego


def test_afb_excess_hits_wasted_and_next_step_roll(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"destroyer": 2, "cruiser": 1}, "p2": {"fighter": 1, "dreadnought": 1}})
    started = battle.start_combat(state, _grid(), registry)
    after = _seek(
        started,
        lambda s: _afb_assigned(s, registry),
        lambda s: _units(s, "p2").get("fighter", 0) == 0,
    )
    assert after.active_combat is not None
    assert after.active_combat.step is CombatStep.ROLL
    assert after.active_combat.round == 1  # AFB nie zmienia numeru rundy
    assert _units(after, "p2") == {"dreadnought": 1}  # dreadnought nieruszony przez AFB


# -------------------------------------------------------------------- rzuty i straty


def _rolled_with_hits(registry: StaticDataRegistry, space: dict[str, dict[str, int]]) -> GameState:
    started = battle.start_combat(_state(space), _grid(), registry)
    return _seek(
        started,
        lambda s: battle.roll_round(s, _grid(), registry),
        lambda s: s.pending_window is not None,
    )


def test_roll_opens_assign_window_defender_first(registry: StaticDataRegistry) -> None:
    rolled = _rolled_with_hits(registry, {"p1": {"cruiser": 6}, "p2": {"cruiser": 6}})
    window = rolled.pending_window
    assert window is not None and window.window_type is WindowType.COMBAT_ASSIGN_HITS
    combat = rolled.active_combat
    assert combat is not None and combat.step is CombatStep.ASSIGN
    needing = [p for p in ("p2", "p1") if combat.pending_hits.get(p, 0) > 0]
    assert window.queue == needing  # obrońca (p2) przed atakującym


def test_sides_roll_separately_and_round_closes_after_both(registry: StaticDataRegistry) -> None:
    """Każda strona rzuca sama (nie muszą jednocześnie); runda rusza dopiero po obu rzutach."""
    started = battle.start_combat(
        _state({"p1": {"cruiser": 6}, "p2": {"cruiser": 6}}), _grid(), registry
    )
    first = battle.roll_round(started, _grid(), registry, "p1")
    combat = first.active_combat
    assert combat is not None and combat.step is CombatStep.ROLL
    assert list(combat.side_rolls) == ["p1"] and combat.log == [] and first.pending_window is None
    with pytest.raises(ValueError, match="already rolled"):
        battle.roll_round(first, _grid(), registry, "p1")
    with pytest.raises(ValueError, match="not a side"):
        battle.roll_round(first, _grid(), registry, "p3")
    second = battle.roll_round(first, _grid(), registry, "p2")
    done = second.active_combat
    assert done is not None and done.side_rolls == {}
    assert set(done.log[-1]["rolls"]) == {"p1", "p2"}
    assert done.log[-1]["rolls"]["p1"] == combat.side_rolls["p1"]  # rzut pierwszej strony zachowany


def test_assign_validation(registry: StaticDataRegistry) -> None:
    rolled = _rolled_with_hits(registry, {"p1": {"cruiser": 6}, "p2": {"cruiser": 6}})
    window = rolled.pending_window
    assert window is not None
    first = window.current_responder
    assert first is not None
    other = "p1" if first == "p2" else "p2"
    need = battle.required_hits(rolled, _grid(), registry, first)
    with pytest.raises(ValueError, match="turn"):
        battle.assign_combat_hits(
            rolled, _grid(), registry, other, sustain={}, destroy={"cruiser": 1}, destroy_damaged={}
        )
    with pytest.raises(ValueError, match="exactly"):
        battle.assign_combat_hits(
            rolled, _grid(), registry, first, sustain={}, destroy={}, destroy_damaged={}
        )
    with pytest.raises(ValueError, match="Sustain"):
        battle.assign_combat_hits(
            rolled, _grid(), registry, first, sustain={"cruiser": 1}, destroy={}, destroy_damaged={}
        )
    after = battle.assign_combat_hits(
        rolled, _grid(), registry, first, sustain={}, destroy={"cruiser": need}, destroy_damaged={}
    )
    assert _units(after, first).get("cruiser", 0) == 6 - need


def test_sustain_damage_marks_unit_and_required_counts_it(
    registry: StaticDataRegistry,
) -> None:
    """Dreadnought z Sustain Damage: 2 trafienia = sustain + zniszczenie (W7/W8)."""
    dn = resolve_unit_variant(registry, None, [], "dreadnought")
    assert dn is not None and dn.sustain_damage  # dane: dreadnought ma Sustain Damage
    rolled = _seek(
        battle.start_combat(
            _state({"p1": {"cruiser": 8}, "p2": {"dreadnought": 1, "fighter": 1}}),
            _grid(),
            registry,
        ),
        lambda s: battle.roll_round(s, _grid(), registry),
        lambda s: s.active_combat is not None and s.active_combat.pending_hits.get("p2", 0) >= 3,
    )
    # p2: 1 DN + 1 FF = 2 jednostki + 1 Sustain = może przyjąć 3 trafienia.
    assert battle.required_hits(rolled, _grid(), registry, "p2") == 3
    after = battle.assign_combat_hits(
        rolled,
        _grid(),
        registry,
        "p2",
        sustain={"dreadnought": 1},
        destroy={"fighter": 1},
        destroy_damaged={"dreadnought": 1},
    )
    assert _units(after, "p2") == {}


def test_sustained_unit_stays_damaged_and_cannot_sustain_again(
    registry: StaticDataRegistry,
) -> None:
    rolled = _seek(
        battle.start_combat(
            _state({"p1": {"cruiser": 3}, "p2": {"dreadnought": 2}}), _grid(), registry
        ),
        lambda s: battle.roll_round(s, _grid(), registry),
        lambda s: s.active_combat is not None and s.active_combat.pending_hits.get("p2") == 1,
    )
    after = battle.assign_combat_hits(
        rolled, _grid(), registry, "p2", sustain={"dreadnought": 1}, destroy={}, destroy_damaged={}
    )
    assert _units(after, "p2") == {"dreadnought": 2}
    assert damage.damaged_count(after.systems["000"], "space", "p2", "dreadnought") == 1
    assert after.active_combat is not None  # walka trwa (p1 ma jeszcze cruisery)
    units = {u.base_type: u for u in battle.side_units(after, _grid(), registry, "p2")}
    assert units["dreadnought"].damaged == 1
    assert units["dreadnought"].sustainable == 1  # Sustain zostaje tylko drugiemu egzemplarzowi


def test_nebula_gives_defender_plus_one(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"cruiser": 1}, "p2": {"cruiser": 1}})
    started = battle.start_combat(state, _grid(nebula=True), registry)
    attacker = battle.side_units(started, _grid(nebula=True), registry, "p1")[0]
    defender = battle.side_units(started, _grid(nebula=True), registry, "p2")[0]
    assert attacker.modifier == 0
    assert defender.modifier == 1
    assert defender.hits_on == attacker.hits_on - 1


def test_combat_runs_to_done_and_close(registry: StaticDataRegistry) -> None:
    grid = _grid()
    state = battle.start_combat(
        _state({"p1": {"dreadnought": 3}, "p2": {"fighter": 1}}), grid, registry
    )
    for _ in range(60):
        combat = state.active_combat
        assert combat is not None
        if combat.step is CombatStep.DONE:
            break
        if combat.step is CombatStep.AFB:
            state = battle.resolve_afb(state, grid, registry)
        elif combat.step is CombatStep.ROLL:
            state = battle.roll_round(state, grid, registry)
        else:
            window = state.pending_window
            assert window is not None and window.current_responder is not None
            pid = window.current_responder
            need = battle.required_hits(state, grid, registry, pid)
            units = battle.side_units(state, grid, registry, pid)
            sustain: dict[str, int] = {}
            destroy: dict[str, int] = {}
            left = need
            for u in units:  # najpierw Sustain Damage, potem niszczenie
                take = min(u.sustainable, left)
                if take:
                    sustain[u.base_type] = take
                    left -= take
            damaged_now: dict[str, int] = {}
            for u in units:
                take = min(u.count - u.damaged - sustain.get(u.base_type, 0), left)
                if take > 0:
                    destroy[u.base_type] = take
                    left -= take
            for u in units:
                take = min(u.damaged + sustain.get(u.base_type, 0), left)
                if take > 0:
                    damaged_now[u.base_type] = take
                    left -= take
            state = battle.assign_combat_hits(
                state,
                grid,
                registry,
                pid,
                sustain=sustain,
                destroy=destroy,
                destroy_damaged=damaged_now,
            )
    combat = state.active_combat
    assert combat is not None and combat.step is CombatStep.DONE
    assert combat.winner == "p1"
    assert state.pending_window is None
    closed = battle.close_combat(state)
    assert closed.active_combat is None


def test_close_unfinished_combat_rejected(registry: StaticDataRegistry) -> None:
    started = battle.start_combat(
        _state({"p1": {"cruiser": 1}, "p2": {"carrier": 1}}), _grid(), registry
    )
    with pytest.raises(ValueError, match="not finished"):
        battle.close_combat(started)


# ------------------------------------------------------------- integracja z krokami


def test_space_combat_step_cannot_be_skipped(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"cruiser": 1}, "p2": {"carrier": 1}})
    with pytest.raises(ValueError, match="resolve the space combat"):
        tactical.next_step(state)
    started = battle.start_combat(state, _grid(), registry)
    with pytest.raises(ValueError, match="in progress"):
        tactical.next_step(started)


def test_end_action_is_validated_during_combat(registry: StaticDataRegistry) -> None:
    # „End action" nie może być furtką: ani przy obowiązkowej walce, ani w jej trakcie.
    state = _state({"p1": {"cruiser": 1}, "p2": {"carrier": 1}})
    with pytest.raises(ValueError, match="resolve the space combat"):
        tactical.end_action(state, registry)
    started = battle.start_combat(state, _grid(), registry)
    with pytest.raises(ValueError, match="in progress"):
        tactical.end_action(started, registry)


def test_end_action_allowed_without_pending_combat(registry: StaticDataRegistry) -> None:
    state = _state({"p1": {"cruiser": 1}})
    ended = tactical.end_action(state, registry)
    assert ended.active_system is None and ended.tactical_step is None


def test_end_action_clears_combat(registry: StaticDataRegistry) -> None:
    rolled = _rolled_with_hits(registry, {"p1": {"cruiser": 6}, "p2": {"cruiser": 6}})
    ended = tactical.end_tactical_action(rolled)
    assert ended.active_combat is None
    assert ended.pending_window is None


# --------------------------------------------------------------------- walka naziemna


def test_ground_combat_in_invasion_step(registry: StaticDataRegistry) -> None:
    state = _state(planet={"p1": {"infantry": 2}, "p2": {"mech": 1}}, step=TacticalStep.INVASION)
    started = battle.start_combat(state, _grid(), registry, planet="pl")
    combat = started.active_combat
    assert combat is not None and combat.kind == "ground" and combat.planet == "pl"
    assert combat.step is CombatStep.ROLL  # w walce naziemnej nie ma AFB
    mech = battle.side_units(started, _grid(), registry, "p2")[0]
    assert mech.sustain  # mech ma Sustain Damage (dane)
    with pytest.raises(ValueError, match="INVASION"):
        battle.start_combat(
            _state(planet={"p1": {"infantry": 1}, "p2": {"infantry": 1}}), _grid(), registry, "pl"
        )


# ------------------------------------------------------------- naprawa i ruch uszkodzeń


def test_status_phase_repairs_damaged_units(registry: StaticDataRegistry) -> None:
    """Naprawa to krok 7 fazy statusu (R_status_phase), nie samo wejście w fazę."""
    state = _state({"p1": {"dreadnought": 1}})
    damage.set_damaged(state.systems["000"], "space", "p1", "dreadnought", 1)
    status = turn_flow.next_phase(state)
    assert status.phase is Phase.STATUS
    # Samo wejście w STATUS niczego nie naprawia — jednostki wciąż uszkodzone.
    assert status.systems["000"].damaged_units != {}
    repaired = status_phase.finalize_status(status, registry)
    assert repaired.systems["000"].damaged_units == {}


def test_moving_damaged_ships_moves_damage_undamaged_first(
    registry: StaticDataRegistry,
) -> None:
    grid = _grid()
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        players={"p1": PlayerState(player_id="p1")},
        systems={
            "101": SystemState(
                position="101",
                system_id="20",
                space_units={"p1": {"dreadnought": 2}},
                damaged_units={"space": {"p1": {"dreadnought": 1}}},
            )
        },
    )
    one = movement.move_fleet(state, grid, registry, "101", {"dreadnought": 1}, {}, "p1")
    assert damage.damaged_count(one.systems["101"], "space", "p1", "dreadnought") == 1
    assert damage.damaged_count(one.systems["000"], "space", "p1", "dreadnought") == 0
    both = movement.move_fleet(state, grid, registry, "101", {"dreadnought": 2}, {}, "p1")
    assert damage.damaged_count(both.systems["000"], "space", "p1", "dreadnought") == 1


# --------------------------------------------------------------------------- API


def _client(registry: StaticDataRegistry, state: GameState) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    return TestClient(app)


def test_api_battle_flow(registry: StaticDataRegistry) -> None:
    client = _client(
        registry, _state({"p1": {"destroyer": 1, "cruiser": 2}, "p2": {"carrier": 1, "fighter": 2}})
    )
    assert client.get("/tactical/battle").json()["active"] is False

    assert client.post("/tactical/battle/start", json={}).status_code == 200
    view: dict[str, Any] = client.get("/tactical/battle").json()
    assert view["active"] is True
    assert view["step"] == "AFB"
    assert view["attacker"]["faction"] == "p1"
    assert view["defender"]["role"] == "defender"
    assert view["attacker"]["unitCount"] == 3
    assert view["defender"]["hp"] == 3  # carrier + 2 myśliwce, bez Sustain Damage

    assert client.post("/tactical/battle/roll").status_code == 422  # teraz AFB
    assert client.post("/tactical/battle/afb").status_code == 200
    after_afb = client.get("/tactical/battle").json()
    assert after_afb["afb"]["p1"][0]["baseType"] == "destroyer"
    assert after_afb["log"][0]["phase"] == "AFB"


def test_web_data_exposes_combat_and_damage(registry: StaticDataRegistry) -> None:
    state = battle.start_combat(
        _state({"p1": {"dreadnought": 2}, "p2": {"carrier": 1}}), _grid(), registry
    )
    damage.set_damaged(state.systems["000"], "space", "p1", "dreadnought", 1)
    client = _client(registry, state)
    data = client.get("/api/public/game/g/web-data", params={"viewing_player": "p1"}).json()
    combat = data["gameState"]["activeCombat"]
    assert combat["system"] == "000" and combat["unitHolder"] == "space"
    assert combat["participantColors"] == ["p1", "p2"]
    dn = next(e for e in data["tileUnitData"]["000"]["space"]["p1"] if e["entityId"] == "dn")
    assert dn["sustained"] == 1
