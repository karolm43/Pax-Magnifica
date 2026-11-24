"""Entropic Scar (RULES.md 1.5) - rulingi ``R_entropic_scars.md``.

Kafle z danych: ``114`` (pusta blizna) i ``116`` (Lemox - blizna z planetą). Zdolności jednostek
nie działają w bliźnie ani przeciw jednostkom w niej; technologia frakcyjna na starcie statusu.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.core import (
    battle,
    entropic_scar,
    exploration,
    invasion,
    production,
    rules_hooks,
    space_cannon,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    CombatStep,
    GameState,
    InvasionPhase,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.hooks import entropic_scar as scar_hooks
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_exploration import _with_card

SCAR = "114"  # Entropic Scar (bez planet)
LEMOX_TILE = "116"  # Lemox - blizna z planetą
LEMOX = "lemox"
PLAIN = "18"  # zwykły kafel (Mecatol Rex) - porównanie


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    yield


def _grid(center: str, neighbor: str = "20") -> HexGrid:
    grid = HexGrid()
    grid.place_system("000", center, anomalies=set())
    grid.place_system("101", neighbor, anomalies=set())
    grid.build_edges()
    return grid


def _state(
    tile: str,
    space: dict[str, dict[str, int]] | None = None,
    planet: dict[str, dict[str, int]] | None = None,
    *,
    planet_id: str = LEMOX,
    step: TacticalStep = TacticalStep.SPACE_COMBAT,
    factions: dict[str, str] | None = None,
) -> GameState:
    """Aktywny p1, aktywny system 000 = kafel ``tile``."""
    center = SystemState(position="000", system_id=tile)
    for pid, by_type in (space or {}).items():
        center.space_units[pid] = dict(by_type)
    for pid, by_type in (planet or {}).items():
        center.planet_units.setdefault(planet_id, {})[pid] = dict(by_type)
    factions = factions or {}
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        tactical_step=step,
        seating_order=["p1", "p2"],
        players={
            pid: PlayerState(player_id=pid, color=pid, faction=factions.get(pid))
            for pid in ("p1", "p2")
        },
        systems={"000": center},
        rng_seed=1,
    )


# ============================================================================= anomalia


@ruling("R_entropic_scars/notes/1")
def test_scar_tiles_are_anomalies_without_movement_effects(registry: StaticDataRegistry) -> None:
    """Flaga ``isScar`` z danych = anomalia ENTROPIC_SCAR; nie blokuje ruchu (inne anomalie tak)."""
    for tile in (SCAR, LEMOX_TILE):
        assert entropic_scar.SCAR in registry.systems[tile].anomalies
    assert entropic_scar.SCAR not in registry.systems[PLAIN].anomalies
    state = _state(SCAR, {"p1": {"cruiser": 1}})
    assert entropic_scar.is_scar(state, "000")
    grid = HexGrid()
    grid.place_system("000", SCAR, anomalies=set(registry.systems[SCAR].anomalies))
    grid.build_edges()
    assert not grid.is_impassable("000")


# ========================================================= zdolności jednostek (by / against)


@ruling("R_entropic_scars/notes/2", "R_entropic_scars/notes/3")
def test_no_anti_fighter_barrage_or_sustain_in_scar(registry: StaticDataRegistry) -> None:
    """AFB i SUSTAIN DAMAGE to zdolności jednostek: w bliźnie nie działają."""
    fleets = {"p1": {"destroyer": 1, "dreadnought": 1}, "p2": {"fighter": 2}}
    normal = battle.start_combat(_state(PLAIN, fleets), _grid(PLAIN), registry)
    assert normal.active_combat is not None and normal.active_combat.step is CombatStep.AFB
    started = battle.start_combat(_state(SCAR, fleets), _grid(SCAR), registry)
    assert started.active_combat is not None
    assert started.active_combat.step is CombatStep.ROLL  # bez AFB
    units = {u.base_type: u for u in battle.side_units(started, _grid(SCAR), registry, "p1")}
    assert units["destroyer"].afb_hits_on is None
    assert units["dreadnought"].sustain is False


@ruling("R_entropic_scars/notes/2", "R_entropic_scars/notes/3")
def test_space_cannon_neither_from_nor_into_scar(registry: StaticDataRegistry) -> None:
    """PDS w bliźnie nie strzela; PDS II z sąsiedztwa nie strzela w statki w bliźnie."""
    inside = _state(LEMOX_TILE, {"p1": {"cruiser": 1}}, {"p2": {"pds": 1}},
                    step=TacticalStep.SPACE_CANNON)
    assert space_cannon.offense_shooters(inside, _grid(LEMOX_TILE), registry, "p2") == []
    outside = _state(SCAR, {"p1": {"cruiser": 1}}, step=TacticalStep.SPACE_CANNON)
    near = SystemState(position="101", system_id="20")
    near.planet_units["vefutii"] = {"p2": {"pds": 1}}
    outside.systems["101"] = near
    outside.players["p2"].technologies = ["pds2"]
    assert space_cannon.offense_shooters(outside, _grid(SCAR), registry, "p2") == []
    # Ten sam układ na zwykłym kaflu: PDS II strzela z sąsiedztwa (kontrola testu).
    plain = outside.clone()
    plain.systems["000"].system_id = PLAIN
    assert space_cannon.offense_shooters(plain, _grid(PLAIN), registry, "p2")


@ruling("R_entropic_scars/notes/2")
def test_no_production_from_units_in_scar(registry: StaticDataRegistry) -> None:
    """Dok na Lemox nie produkuje - także tekst doku definiujący X nie działa (2.2)."""
    state = _state(LEMOX_TILE, planet={"p1": {"spacedock": 1}})
    state.systems["000"].planet_owners[LEMOX] = "p1"
    assert production.producers(state, registry, "p1", "000") == []


@ruling("R_entropic_scars/notes/2")
def test_planetary_shield_and_bombardment_do_not_work_in_scar(
    registry: StaticDataRegistry,
) -> None:
    state = _state(
        LEMOX_TILE, {"p1": {"dreadnought": 2, "infantry": 1}}, {"p2": {"pds": 1, "infantry": 1}},
        step=TacticalStep.INVASION,
    )
    state.systems["000"].planet_owners[LEMOX] = "p2"
    assert invasion.planet_shield(state, registry, "000", LEMOX) == (True, False)
    started = invasion.begin_invasion(state, _grid(LEMOX_TILE), registry)
    assert started.invasion is not None
    assert started.invasion.phase is InvasionPhase.COMMIT  # bez kroku Bombardment


@ruling("R_entropic_scars/notes/2.1")
def test_text_abilities_still_work_in_scar(registry: StaticDataRegistry) -> None:
    """Zdolność tekstowa (Fragile Jol-Nar: -1 do rzutów) działa w bliźnie."""
    state = _state(SCAR, {"p1": {"cruiser": 1}, "p2": {"carrier": 1}},
                   factions={"p1": "jolnar"})
    started = battle.start_combat(state, _grid(SCAR), registry)
    cruiser = battle.side_units(started, _grid(SCAR), registry, "p1")[0]
    assert cruiser.modifier == -1


@ruling("R_entropic_scars/notes/2.3")
def test_deploy_cannot_place_in_scar(registry: StaticDataRegistry) -> None:
    """Letani Behemoth (Arborec) - DEPLOY: zamiana piechoty na mecha nie w bliźnie."""
    from src.core.hooks.factions import arborec

    state = _state(SCAR, {"p1": {"infantry": 1}}, factions={"p1": "arborec"})
    plain = SystemState(position="101", system_id="20")
    plain.space_units["p1"] = {"infantry": 1}
    state.systems["101"] = plain
    choice = arborec.mitosis_inputs(state, registry, "p1", {})[0]
    keys = {o["value"] for o in choice["options"]}
    assert "mech|101|space" in keys
    assert not any(k.startswith("mech|000|") for k in keys)
    with pytest.raises(ValueError, match="entropic scar"):
        arborec.mitosis(state, "p1", {"params": {"mitosis": "mech|000|space"}})


# ============================================================================ żetony wormhole


@ruling("R_entropic_scars/notes/4")
def test_gamma_wormhole_token_returns_from_scar(registry: StaticDataRegistry) -> None:
    from tests.test_exploration import _state as explore_state

    base = explore_state()
    base.systems["000"].system_id = LEMOX_TILE
    state = _with_card(base, registry, "Gamma Wormhole", planet=LEMOX)
    done = exploration.resolve(state, registry, "place")
    assert done.systems["000"].wormhole_tokens == []
    assert done.exploration is not None and done.exploration.log[-1]["fate"] == "purged"


# ===================================================================== start fazy statusu


def _status_state(
    registry: StaticDataRegistry, *, scars: int = 1, ground_only: bool = False, tokens: int = 2,
) -> GameState:
    state = GameState(
        phase=Phase.STATUS,
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="p1", faction="hacan", strategic_cc=tokens),
            "p2": PlayerState(player_id="p2", color="p2", faction="sol"),
        },
    )
    for index in range(scars):
        position = f"10{index + 1}"
        system = SystemState(position=position, system_id=SCAR if index == 0 else LEMOX_TILE)
        system.space_units["p1"] = {"infantry": 1} if ground_only else {"cruiser": 1}
        state.systems[position] = system
    return state


def _start_status(state: GameState) -> GameState:
    triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "status"})
    return state


def _scar_offers(state: GameState) -> list[str]:
    return [o.id for o in state.pending_offers if o.label == "Entropic Scar"]


@ruling("R_entropic_scars/notes/5", "R_entropic_scars/notes/5.1")
def test_status_start_offers_faction_tech_for_strategy_token(
    registry: StaticDataRegistry,
) -> None:
    state = _start_status(_status_state(registry))
    offers = _scar_offers(state)
    assert len(offers) == 1 and state.pending_offers[0].player_id == "p1"
    techs = scar_hooks.missing_faction_techs(state, "p1")
    assert techs
    # Technologia frakcyjna z prerekwizytami, których gracz nie ma (5.1: nie są potrzebne).
    done = triggers.accept_offer(state, "p1", offers[0], {"research": {"tech": techs[-1]}})
    assert techs[-1] in done.players["p1"].technologies
    assert done.players["p1"].strategic_cc == 1
    assert _scar_offers(done) == []  # jedna blizna = jedna technologia


@ruling("R_entropic_scars/notes/5")
def test_status_offer_may_be_declined_and_rejects_other_techs(
    registry: StaticDataRegistry,
) -> None:
    state = _start_status(_status_state(registry))
    offer = _scar_offers(state)[0]
    with pytest.raises(ValueError, match="faction technologies"):
        triggers.accept_offer(state.clone(), "p1", offer, {"research": {"tech": "gd"}})
    declined = triggers.accept_offer(state, "p1", offer, {"research": {"tech": None}})
    assert declined.players["p1"].strategic_cc == 2
    assert not set(scar_hooks.missing_faction_techs(declined, "p1")) & set(
        declined.players["p1"].technologies
    )


@ruling("R_entropic_scars/notes/5")
def test_no_offer_without_strategy_token(registry: StaticDataRegistry) -> None:
    assert _scar_offers(_start_status(_status_state(registry, tokens=0))) == []


def test_ground_forces_in_scar_do_not_count(registry: StaticDataRegistry) -> None:
    assert _scar_offers(_start_status(_status_state(registry, ground_only=True))) == []


@ruling("R_entropic_scars/notes/5.2")
def test_ships_in_two_scars_gain_both_faction_techs(registry: StaticDataRegistry) -> None:
    state = _start_status(_status_state(registry, scars=2))
    techs = scar_hooks.missing_faction_techs(state, "p1")
    assert len(techs) == 2
    first = triggers.accept_offer(state, "p1", _scar_offers(state)[0],
                                  {"research": {"tech": techs[0]}})
    second_offers = _scar_offers(first)
    assert len(second_offers) == 1
    done = triggers.accept_offer(first, "p1", second_offers[0], {"research": {"tech": techs[1]}})
    assert set(techs) <= set(done.players["p1"].technologies)
    assert done.players["p1"].strategic_cc == 0
