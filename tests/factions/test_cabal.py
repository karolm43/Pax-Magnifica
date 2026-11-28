"""The Vuil'raith Cabal — komplet komponentów frakcji (RULES.md 62.17) i rulingi F_vuilraith.

Scenariusze przez prawdziwe API (oferty, notka, akcje, przełom): ``test_flows_cabal.py``.
Wspólna mechanika capture: ``tests/test_capture.py``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from src.core import (
    board_graph,
    capacity,
    capture,
    economy,
    expeditions,
    faction_components,
    fracture,
    leaders,
    movement,
    production,
    rules_hooks,
    technology,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.expedition_state import IngressChoice
from src.core.game_state import (
    ActiveCombat,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hooks.factions import cabal
from src.core.offer_inputs import has_legal_answer
from src.core.production import ProductionOrder, reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE, UNIT_CAP_BY_ASYNC_ID
from src.core.unit_ops import UnitCause
from tests.factions.completeness import missing_components
from tests.rulings import ruling

# 101 = dom Cabal (54: Acheron), 102 = Wellon (19), 103 = Vefutii (20), 104 = Thibah (21, p2),
# 105 = Tarmann (22), 106 = Quann (25); 000 = Mecatol. Pierścień 1: sąsiedzi kolejno.
HOME, ARENA, EAST, RIVAL, FAR, WEST = "101", "102", "103", "104", "105", "106"
ACHERON, WELLON, VEFUTII, THIBAH = "acheron", "wellon", "vefutii", "thibah"
RIFT_TILE, CORMUND_TILE, EVERRA_TILE = "41", "67", "68"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(None)
    yield
    board_graph.bind_grid_provider(previous)


def _state(other: str = "sol") -> GameState:
    """p1 = Cabal (Dimensional Tear na Acheron), p2 = rywal (aktywny)."""
    p1 = PlayerState(player_id="p1", color="red", faction="cabal", home_position=HOME,
                     strategy_cards=[4])
    p2 = PlayerState(player_id="p2", color="blue", faction=other, home_position=RIVAL,
                     strategy_cards=[2], commodity_value=4)
    state = GameState(
        phase=Phase.ACTION, active_player_id="p2", speaker_id="p1", seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            HOME: SystemState(position=HOME, system_id="54", planet_owners={ACHERON: "p1"},
                              planet_units={ACHERON: {"p1": {"spacedock": 1, "infantry": 1}}}),
            ARENA: SystemState(position=ARENA, system_id="19"),
            EAST: SystemState(position=EAST, system_id="20"),
            RIVAL: SystemState(position=RIVAL, system_id="21", planet_owners={THIBAH: "p2"}),
            FAR: SystemState(position=FAR, system_id="22"),
            WEST: SystemState(position=WEST, system_id="25"),
        },
    )
    p1.controlled_planets = [ACHERON]
    p2.controlled_planets = [THIBAH]
    for p in state.players.values():
        p.cc_reinf = 8
    return state


def _grid(state: GameState, registry: StaticDataRegistry) -> Any:
    return grid_from_state(state, registry)


def _cap(base_type: str) -> int:
    return UNIT_CAP_BY_ASYNC_ID[ASYNC_ID_BY_BASE_TYPE[base_type]]


def _offers(state: GameState, pid: str, label: str) -> list[Any]:
    return [o for o in triggers.offers_for(state, pid) if label in o.label]


def _accept(state: GameState, pid: str, label: str, params: dict[str, Any] | None = None
            ) -> GameState:
    offer = _offers(state, pid, label)[0]
    return triggers.accept_offer(state, pid, offer.id, params)


def _destroy(state: GameState, position: str, zone: str, pid: str, base_type: str,
             count: int = 1) -> None:
    unit_ops.remove_units(state, state.systems[position], zone, pid, base_type, count,
                          UnitCause.DESTROYED)


def _combat(state: GameState, position: str = ARENA, kind: str = "space",
            planet: str | None = None) -> None:
    state.active_combat = ActiveCombat(kind=kind, position=position, planet=planet,
                                       attacker="p2", defender="p1")


def test_kompletnosc_cabal(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "cabal") == []


# ------------------------------------------------------------------ Dimensional Tear


@ruling("units:cabal_spacedock#1", "units:cabal_spacedock#3", "F_vuilraith/dimensional-tear/1",
        "F_vuilraith/dimensional-tear/1.1", "F_vuilraith/dimensional-tear/7")
def test_dimensional_tear_to_gravity_rift(registry: StaticDataRegistry) -> None:
    state = _state()
    grid = _grid(state, registry)
    # Anomalia jak każda inna: cele „systemy z anomalią” (Make History) czytają anomalies_at.
    assert grid.anomalies_at(HOME) == {"GRAVITY_RIFT"}
    assert movement.is_gravity_rift(grid, HOME)
    _destroy(state, HOME, ACHERON, "p1", "spacedock")  # zniszczony dok = koniec szczeliny
    assert not _grid(state, registry).anomalies_at(HOME)


@ruling("units:cabal_spacedock#2", "F_vuilraith/dimensional-tear/4",
        "F_vuilraith/dimensional-tear/3")
def test_cabal_nie_rzuca_za_wlasna_szczeline(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[EAST].system_id = CORMUND_TILE  # naturalna szczelina z planetą
    state.systems[EAST].planet_units = {"cormund": {"p1": {"spacedock": 2}}}  # dwa doki
    grid = _grid(state, registry)
    for position in (HOME, EAST):
        route = [position, FAR]
        assert movement.rift_roll_nodes(state, grid, route, "p1") == []
        assert movement.rift_roll_nodes(state, grid, route, "p2") == [position]
        assert movement.rift_bonus(state, grid, route, "p1") == 1  # bez dodatkowego efektu


@ruling("F_vuilraith/dimensional-tear/2", "R_gravity_rift/notes/2")
def test_ta_sama_szczelina_plus_jeden_raz_rzut_za_kazde_wyjscie(
    registry: StaticDataRegistry,
) -> None:
    """Trasa wychodzi dwa razy z HOME i dwa razy z ARENA (obie to szczeliny): +1 za każdą RÓŻNĄ
    szczelinę (= 2), ale rzut za każde wyjście (gracz bez Dimensional Tear - p2)."""
    state = _state()
    state.systems[ARENA].planet_units = {WELLON: {"p1": {"spacedock": 1}}}
    grid = _grid(state, registry)
    route = [HOME, ARENA, HOME, ARENA, EAST]
    assert movement.rift_bonus(state, grid, route, "p1") == 2
    assert movement.rift_roll_nodes(state, grid, route, "p2") == [HOME, ARENA, HOME, ARENA]


@ruling("F_vuilraith/dimensional-tear/6")
def test_tear_w_mglawicy_plus_jeden_po_ustawieniu_jedynki(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[FAR].system_id = EVERRA_TILE
    state.systems[FAR].planet_units = {"everra": {"p1": {"spacedock": 1}}}
    grid = _grid(state, registry)
    assert grid.anomalies_at(FAR) == {"NEBULA", "GRAVITY_RIFT"}
    base = movement._effective_move_value(
        state, grid, registry, FAR, "cruiser", "p1", boost=False, tempesta=False
    )
    assert base == 1  # mgławica ustawia 1 …
    assert movement.rift_bonus(state, grid, [FAR, WEST], "p1") == 1  # … potem +1 ze szczeliny


@ruling("units:cabal_spacedock#4", "technologies:dt2#5")
def test_pojemnosc_doku_dla_mysliwcow(registry: StaticDataRegistry) -> None:
    state = _state()
    assert capacity.capacity_report(state, registry, HOME, "p1").fighter_only == 6
    state.players["p1"].technologies = ["dt2"]
    assert capacity.capacity_report(state, registry, HOME, "p1").fighter_only == 12


@ruling("technologies:dt2#1", "technologies:dt2#2", "technologies:dt2#3", "technologies:dt2#4")
def test_dimensional_tear_ii(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "cabal", ["dt2"], "spacedock")
    assert unit is not None and unit.id == "cabal_spacedock2" and unit.production_value == 7
    state = _state()
    state.players["p1"].technologies = ["dt2"]
    grid = _grid(state, registry)
    assert movement.is_gravity_rift(grid, HOME)
    assert movement.rift_roll_nodes(state, grid, [HOME, ARENA], "p1") == []


# ------------------------------------------------------------------------- Devour


@ruling("abilities:devour#1")
def test_devour_przechwytuje_przeciwnika_w_walce() -> None:
    state = _state()
    state.systems[ARENA].space_units = {"p1": {"cruiser": 2}, "p2": {"destroyer": 2}}
    _combat(state)
    _destroy(state, ARENA, "space", "p2", "destroyer")
    _destroy(state, ARENA, "space", "p1", "cruiser")  # własny - nie (bez flagowca)
    assert state.players["p1"].captured_units == {"p2": {"destroyer": 1}}
    assert state.ability_notes[-1]["component"] == "abilities:devour"
    state.active_combat = None
    _destroy(state, ARENA, "space", "p2", "destroyer")  # poza walką - nie
    assert state.players["p1"].captured_units == {"p2": {"destroyer": 1}}


@ruling("F_vuilraith/devour/1")
def test_devour_infantry_ii_zeton_i_odrodzenie() -> None:
    state = _state()
    state.players["p2"].technologies = ["inf2"]
    state.systems[ARENA].planet_units = {WELLON: {"p1": {"infantry": 1}, "p2": {"infantry": 2}}}
    _combat(state, kind="ground", planet=WELLON)
    _destroy(state, ARENA, WELLON, "p2", "infantry", 2)
    assert state.players["p1"].captured_tokens == {"infantry": 2}
    assert state.table_roll is not None and state.table_roll["playerId"] == "p2"  # rzut odrodzenia


def _seek(
    state: GameState,
    act: Callable[[GameState], GameState],
    ok: Callable[[GameState], bool],
) -> GameState:
    for seed in range(1, 300):
        candidate = state.clone()
        candidate.rng_seed = seed
        result = act(candidate)
        if ok(result):
            return result
    raise AssertionError("no seed produced the expected outcome")


@ruling("F_vuilraith/devour/3")
def test_devour_bombardowanie_nie_ale_afb_tak(registry: StaticDataRegistry) -> None:
    """Bombardment (poza walką) nie przechwytuje; Anti-Fighter Barrage (w walce) tak."""
    from src.core import battle, invasion
    from src.core.invasion import BombardAssignment

    state = _state()
    state.active_player_id = "p1"
    state.active_system = ARENA
    state.tactical_step = TacticalStep.INVASION
    state.systems[ARENA].planet_owners = {WELLON: "p2"}
    state.systems[ARENA].space_units = {"p1": {"dreadnought": 3}}
    state.systems[ARENA].planet_units = {WELLON: {"p2": {"infantry": 4}}}
    grid = _grid(state, registry)
    opened = invasion.begin_invasion(state, grid, registry)
    rolled = _seek(
        opened,
        lambda s: invasion.bombard(
            s, grid, registry, [BombardAssignment("dreadnought", WELLON, 3)]
        ),
        lambda s: s.invasion is not None and s.invasion.bombard_pending.get(WELLON, 0) > 0,
    )
    need = invasion.required_bombard_hits(rolled, grid, registry, WELLON)
    after = invasion.assign_bombard_hits(
        rolled, grid, registry, WELLON, "p2", sustain={}, destroy={"infantry": need},
        destroy_damaged={},
    )
    assert after.systems[ARENA].planet_units[WELLON]["p2"]["infantry"] == 4 - need
    assert capture.total_held(after, "p1") == 0  # Bombardment nie jest walką

    afb = _state()
    afb.active_player_id = "p1"
    afb.active_system = ARENA
    afb.tactical_step = TacticalStep.SPACE_COMBAT
    afb.systems[ARENA].space_units = {"p1": {"destroyer": 4}, "p2": {"fighter": 8}}
    agrid = _grid(afb, registry)

    def run(s: GameState) -> GameState:
        out = battle.resolve_afb(battle.start_combat(s, agrid, registry), agrid, registry)
        while (out.active_combat is not None and out.active_combat.step.name == "ASSIGN"
               and out.pending_window is not None):
            pid = out.pending_window.current_responder
            assert pid is not None
            hits = battle.required_hits(out, agrid, registry, pid)
            out = battle.assign_combat_hits(out, agrid, registry, pid, sustain={},
                                            destroy={"fighter": hits}, destroy_damaged={})
        return out

    done = _seek(afb, run, lambda s: s.systems[ARENA].space_units["p2"].get("fighter", 8) < 8)
    assert done.players["p1"].captured_tokens.get("fighter", 0) > 0


@ruling("F_vuilraith/devour/2")
def test_devour_nie_bierze_struktur() -> None:
    state = _state()
    state.systems[ARENA].planet_units = {WELLON: {"p1": {"infantry": 1}, "p2": {"pds": 1}}}
    _combat(state, kind="ground", planet=WELLON)
    _destroy(state, ARENA, WELLON, "p2", "pds")  # Hel Titan to PDS - struktura
    assert capture.total_held(state, "p1") == 0


# ------------------------------------------------------------------ The Terror Between


def _flagship(state: GameState, position: str = ARENA) -> None:
    state.systems[position].space_units.setdefault("p1", {})["flagship"] = 1


@ruling("units:cabal_flagship#1", "F_vuilraith/the-terror-between/2")
def test_flagowiec_przechwytuje_wszystko_takze_poza_walka() -> None:
    state = _state()
    state.systems[ARENA].space_units = {"p1": {"flagship": 1, "cruiser": 1},
                                        "p2": {"destroyer": 1}}
    _destroy(state, ARENA, "space", "p2", "destroyer")
    _destroy(state, ARENA, "space", "p1", "cruiser")  # „including your own”
    assert state.players["p1"].captured_units == {"p2": {"destroyer": 1}, "p1": {"cruiser": 1}}
    _destroy(state, ARENA, "space", "p1", "flagship")  # „all OTHER units”
    assert "flagship" not in state.players["p1"].captured_units.get("p1", {})
    assert reinforcements_left(state, "p1", "cruiser") == _cap("cruiser") - 1  # nie wraca sam


@ruling("F_vuilraith/the-terror-between/1")
def test_flagowiec_zniszczony_w_tej_rundzie_nadal_przechwytuje() -> None:
    state = _state()
    state.systems[ARENA].space_units = {"p2": {"destroyer": 1}}
    _combat(state)
    assert state.active_combat is not None
    state.active_combat.destroyed_ships = [{"player": "p1", "base_type": "flagship",
                                            "hits_on": 5}]
    state.active_combat.defender = "p1"
    _destroy(state, ARENA, "space", "p2", "destroyer")
    assert state.players["p1"].captured_units == {"p2": {"destroyer": 1}}


# ------------------------------------------------------------------------ Reanimator


@ruling("units:cabal_mech#1", "units:cabal_mech#2", "F_vuilraith/reanimator/2")
def test_reanimator_wlasna_piechota_na_arkusz_takze_poza_walka() -> None:
    state = _state()
    state.systems[HOME].planet_units[ACHERON]["p1"].update(mech=1, infantry=3)
    _destroy(state, HOME, ACHERON, "p1", "infantry", 2)  # np. Plague - poza walką
    assert state.players["p1"].captured_tokens == {"infantry": 2}
    state.systems[HOME].planet_units[ACHERON]["p1"].pop("mech")
    _destroy(state, HOME, ACHERON, "p1", "infantry")
    assert state.players["p1"].captured_tokens == {"infantry": 2}


@ruling("F_vuilraith/reanimator/1")
def test_reanimator_z_infantry_ii_zeton_i_rzut() -> None:
    state = _state()
    state.players["p1"].technologies = ["inf2"]
    state.systems[HOME].planet_units[ACHERON]["p1"].update(mech=1, infantry=2)
    _combat(state, HOME, kind="ground", planet=ACHERON)
    _destroy(state, HOME, ACHERON, "p1", "infantry")
    assert state.players["p1"].captured_tokens == {"infantry": 1}
    assert state.table_roll is not None and state.table_roll["playerId"] == "p1"


# ------------------------------------------------------------- Amalgamation (produkcja)


def _producing(state: GameState) -> GameState:
    state.active_player_id = "p1"
    state.active_system = HOME
    state.players["p1"].trade_goods = 0
    return state


@ruling("abilities:amalgamation#1", "F_vuilraith/amalgamation/1",
        "F_vuilraith/amalgamation/4")
def test_amalgamation_produkcja_za_przechwycone(registry: StaticDataRegistry) -> None:
    state = _producing(_state())
    state.players["p1"].captured_units = {"p2": {"cruiser": 2}}
    state.players["p1"].captured_tokens = {"fighter": 2}
    orders = [ProductionOrder("cruiser", 2), ProductionOrder("fighter", 2)]
    captured = {"cruiser": {"p2": 2}, "fighter": {capture.TOKEN: 2}}
    with pytest.raises(ValueError, match="Not enough resources"):
        production.validate_production(state, _grid(state, registry), registry, "p1", orders)
    after = production.produce(state, _grid(state, registry), registry, "p1", orders,
                               captured=captured)
    assert after.systems[HOME].space_units["p1"] == {"cruiser": 2, "fighter": 2}
    assert after.players["p1"].captured_units == {}
    assert after.players["p1"].captured_tokens == {}
    assert after.players["p1"].exhausted_planets == []  # bez wydawania zasobów
    assert reinforcements_left(after, "p2", "cruiser") == _cap("cruiser")  # wróciły do rezerwy


@ruling("F_vuilraith/amalgamation/2")
def test_amalgamation_wlasna_jednostka_przy_pustej_rezerwie(registry: StaticDataRegistry) -> None:
    state = _producing(_state())
    state.systems[ARENA].space_units = {"p1": {"cruiser": _cap("cruiser") - 1}}
    state.players["p1"].captured_units = {"p1": {"cruiser": 1}}
    assert reinforcements_left(state, "p1", "cruiser") == 0
    after = production.produce(state, _grid(state, registry), registry, "p1",
                               [ProductionOrder("cruiser", 1)], captured={"cruiser": {"p1": 1}})
    assert after.systems[HOME].space_units["p1"]["cruiser"] == 1


@ruling("F_vuilraith/amalgamation/3", "F_vuilraith/amalgamation/3.1")
def test_amalgamation_nie_zmienia_kosztu_jednostek(registry: StaticDataRegistry) -> None:
    """Koszt zamówienia (limit grantów typu Integrated Economy) liczy pełny koszt; zmienia się
    tylko wydatek (``paid_orders``)."""
    state = _producing(_state())
    state.players["p1"].captured_units = {"p2": {"carrier": 1}}
    orders = [ProductionOrder("carrier", 1)]
    captured = {"carrier": {"p2": 1}}
    assert production.order_cost(state, registry, "p1", orders) == 3
    assert production.paid_orders(orders, captured) == []


@ruling("F_vuilraith/amalgamation/6")
def test_amalgamation_przechwycony_war_sun_liczy_sie_jako_war_sun(
    registry: StaticDataRegistry,
) -> None:
    """Przechwycony Prototype War Sun (Muaat) to zwykły war sun (typ bazowy)."""
    state = _producing(_state("muaat"))
    state.players["p1"].technologies = ["ws"]
    state.systems[ARENA].space_units = {"p2": {"warsun": 1}}
    _combat(state)
    _destroy(state, ARENA, "space", "p2", "warsun")
    assert state.players["p1"].captured_units == {"p2": {"warsun": 1}}  # typ bazowy
    after = production.produce(state, _grid(state, registry), registry, "p1",
                               [ProductionOrder("warsun", 1)], captured={"warsun": {"p2": 1}})
    assert after.systems[HOME].space_units["p1"]["warsun"] == 1
    assert after.players["p1"].captured_units == {}


@ruling("F_vuilraith/amalgamation/7")
def test_amalgamation_war_sun_wymaga_wlasnej_technologii(registry: StaticDataRegistry) -> None:
    state = _producing(_state())
    state.players["p1"].captured_units = {"p2": {"warsun": 1}}
    with pytest.raises(ValueError, match="war sun"):
        production.produce(state, _grid(state, registry), registry, "p1",
                           [ProductionOrder("warsun", 1)], captured={"warsun": {"p2": 1}})
    assert state.players["p1"].captured_units == {"p2": {"warsun": 1}}


_PRODUCTION_POINTS = sorted(
    getattr(rules_hooks, name) for name in dir(rules_hooks) if name.startswith("POINT_PRODUCTION")
)


def _production_hooks(state: GameState) -> set[str]:
    return {
        hook.covers or "" for point in _PRODUCTION_POINTS
        for hook in rules_hooks.hooks_at(point, state, "p1")
    }


@pytest.mark.parametrize("other", ["naalu", "yin"])
@ruling("F_vuilraith/amalgamation/5")
def test_amalgamation_z_alliance_naalu_yin(registry: StaticDataRegistry, other: str) -> None:
    """The ruling describes the PoK commanders (1 extra fighter / infantry for no cost). The active
    variants (M'aban, Brother Omar) have no production text, so the Alliance adds no extra unit:
    Amalgamation works exactly as without it."""
    state = _producing(_state(other))
    state.players["p1"].captured_tokens = {"infantry": 1}
    orders = [ProductionOrder("infantry", 2, ACHERON)]
    captured = {"infantry": {capture.TOKEN: 1}}
    plain = production.produce(state, _grid(state, registry), registry, "p1", orders,
                               captured=captured)
    commander = f"{other}commander"
    state.players["p2"].leader_states = {commander: "unlocked"}
    state.players["p1"].promissory_notes_in_play = ["blue_an"]  # p2's Alliance
    assert faction_components.borrowed_commanders(state, "p1") == [commander]
    assert f"leaders:{commander}" not in _production_hooks(state)
    assert production.free_small_units(state, "p1", orders) == 0
    allied = production.produce(state, _grid(state, registry), registry, "p1", orders,
                                captured=captured)
    assert allied.systems[HOME].planet_units == plain.systems[HOME].planet_units
    assert allied.players["p1"].trade_goods == plain.players["p1"].trade_goods
    assert allied.players["p1"].exhausted_planets == plain.players["p1"].exhausted_planets


def test_amalgamation_walidacja(registry: StaticDataRegistry) -> None:
    state = _producing(_state())
    state.players["p1"].captured_units = {"p2": {"cruiser": 1}}
    grid = _grid(state, registry)
    with pytest.raises(ValueError, match="at most 1 captured unit"):
        production.produce(state, grid, registry, "p1", [ProductionOrder("cruiser", 1)],
                           captured={"cruiser": {"p2": 2}})
    with pytest.raises(ValueError, match="captured that many"):
        production.produce(state, grid, registry, "p1", [ProductionOrder("carrier", 1)],
                           captured={"carrier": {"p2": 1}})
    other = _state("cabal")  # bez Amalgamation (rywal = Sol jako p1 nie istnieje) - zakaz hooka
    other.players["p2"].captured_units = {"p1": {"cruiser": 1}}
    assert not production.captured_free_allowed(_state(), "p2")


# -------------------------------------------------------------------------- Riftmeld


@ruling("abilities:riftmeld#1", "F_vuilraith/riftmeld/1")
def test_riftmeld_zwrot_przechwyconej_ignoruje_prerekwizyty(registry: StaticDataRegistry) -> None:
    state = _state()
    tech = registry.technologies["cr2"]
    assert technology.upgraded_base_type(tech) == "cruiser"
    with pytest.raises(ValueError):
        technology.research(state, registry, "p1", "cr2")
    state.players["p1"].captured_units = {"p2": {"destroyer": 1}}
    row = next(r for r in technology.tree_view(state, registry, "p1") if r["id"] == "cr2")
    assert row["status"] == "locked"  # zły typ - Riftmeld nie pomaga
    state.players["p1"].captured_units = {"p2": {"cruiser": 1}}
    row = next(r for r in technology.tree_view(state, registry, "p1") if r["id"] == "cr2")
    assert row["status"] == "skippable"
    assert [o["value"] for o in row["capturedSkips"]] == ["captured:p2"]
    after = technology.research(state, registry, "p1", "cr2", ["captured:p2"])
    assert "cr2" in after.players["p1"].technologies
    assert after.players["p1"].captured_units == {}


# ---------------------------------------------------------------------------- Vortex


def _vortex_values(state: GameState, registry: StaticDataRegistry) -> list[str]:
    inputs = cabal.vortex_inputs(state, registry, "p1")
    return [o["value"] for o in inputs[0]["options"]]


@ruling("technologies:vtx#1", "technologies:vtx#2")
def test_vortex_przechwytuje_z_rezerwy(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["vtx"]
    state.systems[ARENA].space_units = {"p2": {"destroyer": 1}}
    state.systems[HOME].space_units = {"p1": {"cruiser": 1}, "p2": {"carrier": 1}}  # ten sam
    values = _vortex_values(state, registry)
    assert values == [f"p2|destroyer|{ARENA}|space"]  # carrier w systemie doku - nie sąsiedni
    cabal.vortex(state, registry, "p1", {"unit": values[0]})
    assert state.players["p1"].captured_units == {"p2": {"destroyer": 1}}
    assert state.systems[ARENA].space_units["p2"] == {"destroyer": 1}  # z rezerwy, nie z planszy
    assert "vtx" in state.players["p1"].exhausted_technologies
    with pytest.raises(ValueError, match="exhausted"):
        cabal.vortex(state, registry, "p1", {"unit": values[0]})


@ruling("F_vuilraith/vortex/1", "F_vuilraith/vortex/2")
def test_vortex_bez_celu_niedostepny(registry: StaticDataRegistry) -> None:
    state = _state()
    assert not has_legal_answer(cabal.vortex_inputs(state, registry, "p1"))
    state.systems[ARENA].space_units = {"p2": {"destroyer": _cap("destroyer"), "fighter": 9}}
    # Wszystkie niszczyciele na planszy - typ nie jest celem; myśliwce (żetony) zawsze.
    assert _vortex_values(state, registry) == [f"p2|fighter|{ARENA}|space"]


@ruling("F_vuilraith/vortex/4")
def test_vortex_nie_na_hel_titana(registry: StaticDataRegistry) -> None:
    """Hel-Titan to struktura (PDS) - nie jest celem Vortexa."""
    state = _state("titans")
    state.systems[ARENA].planet_units = {WELLON: {"p2": {"pds": 1}}}
    assert _vortex_values(state, registry) == []
    state.systems[ARENA].planet_units[WELLON]["p2"]["infantry"] = 1
    assert _vortex_values(state, registry) == [f"p2|infantry|{ARENA}|{WELLON}"]


@ruling("F_vuilraith/vortex/3")
def test_vortex_nie_na_blokujacego_tear(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[ARENA].space_units = {"p2": {"destroyer": 1}}
    state.systems[HOME].space_units = {"p2": {"cruiser": 1}}  # blokada Dimensional Tear
    assert _vortex_values(state, registry) == []


# -------------------------------------------------------------- The Stillness of Stars


@ruling("leaders:cabalagent#1", "F_vuilraith/the-stillness-of-stars/3",
        "F_vuilraith/the-stillness-of-stars/6", "F_vuilraith/the-stillness-of-stars/5")
def test_agent_po_uzupelnieniu_commodities(registry: StaticDataRegistry) -> None:
    state = _state("mentak")  # Pillage nie reaguje na zamianę (ruling 6)
    economy.replenish_commodities(state, "p2")  # np. secondary Trade - oferta od razu (5)
    value = state.players["p2"].commodity_value
    offer = _offers(state, "p1", "The Stillness of Stars")[0]
    units = [o["value"] for o in cabal.agent_inputs(state, registry, "p1", offer.ctx)[0]["options"]]
    assert "fighter" in units and "pds" not in units and "spacedock" not in units
    assert "warsun" not in units  # bez ulepszenia War Sun nie ma kosztu (ruling 2)
    after = _accept(state, "p1", "The Stillness of Stars", {"unit": "fighter"})
    p2 = after.players["p2"]
    assert p2.commodities == 0 and p2.trade_goods == value
    assert after.players["p1"].captured_tokens == {"fighter": 1}  # jeden, nie dwa (3)
    assert after.players["p1"].leader_states["cabalagent"] == "exhausted"
    assert not _offers(after, "p1", "Pillage")


@ruling("F_vuilraith/the-stillness-of-stars/1", "F_vuilraith/the-stillness-of-stars/2")
def test_agent_pelna_commodity_value_i_koszt(registry: StaticDataRegistry) -> None:
    state = _state()
    economy.replenish_commodities(state, "p2")
    state.players["p2"].commodities = 0  # np. Trade Agreement zabrał je od razu
    value = economy.commodity_value(state, "p2")
    offer = _offers(state, "p1", "The Stillness of Stars")[0]
    units = {o["value"] for o in cabal.agent_inputs(state, registry, "p1", offer.ctx)[0]["options"]}
    for base_type in units:
        unit = resolve_unit_variant(registry, "sol", [], base_type)
        assert unit is not None and unit.cost is not None and unit.cost <= value
    assert "dreadnought" in units  # koszt 4 ≤ 4
    after = _accept(state, "p1", "The Stillness of Stars", {"unit": "dreadnought"})
    assert after.players["p1"].captured_units == {"p2": {"dreadnought": 1}}
    assert after.players["p2"].trade_goods == 0


@ruling("F_vuilraith/the-stillness-of-stars/4")
def test_agent_trade_primary_przed_wyborem_graczy(registry: StaticDataRegistry) -> None:
    """Trade primary: TG + uzupełnienie od razu, oferta agenta PRZED wyborem graczy z darmowym
    secondary (kroku nie da się zatwierdzić, dopóki okno reakcji jest otwarte)."""
    from src.core import strategic_action

    state = _state()
    state.players["p2"].strategy_cards = [5]
    state.players["p2"].commodities = 0
    state = strategic_action.play_strategy_card(state, registry, "p2", 5)
    assert state.pending_strategy is not None
    assert state.pending_strategy.step == "choose_free_players"  # not chosen yet
    assert state.players["p2"].trade_goods == 3  # primary effect already applied
    assert state.players["p2"].commodities == state.players["p2"].commodity_value  # replenished
    assert _offers(state, "p1", "The Stillness of Stars")  # after the replenish
    with pytest.raises(ValueError, match="Resolve the open abilities"):
        strategic_action.submit_primary_step(state, registry, "p2", {"players": []})
    after = _accept(state, "p1", "The Stillness of Stars", {"unit": "fighter"})
    assert after.players["p2"].commodities == 0  # converted before players are chosen
    done = strategic_action.submit_primary_step(after, registry, "p2", {"players": []})
    assert done.pending_strategy is None  # primary done, secondary window follows


def test_agent_nie_dla_siebie(registry: StaticDataRegistry) -> None:
    state = _state()
    economy.replenish_commodities(state, "p1")
    assert not _offers(state, "p1", "The Stillness of Stars")


# ------------------------------------------------------------- That Which Molds Flesh


@ruling("leaders:cabalcommander#unlock")
def test_commander_odblokowanie_trzy_szczeliny(registry: StaticDataRegistry) -> None:
    state = _state()
    predicate = leaders.unlock_predicate(registry, "cabalcommander")
    assert predicate is not None
    state.systems[HOME].space_units = {"p1": {"cruiser": 1}}  # Dimensional Tear
    state.systems[EAST].system_id = RIFT_TILE
    state.systems[EAST].space_units = {"p1": {"cruiser": 1}}
    assert not predicate(state, registry, "p1")
    state.systems[WEST].system_id = CORMUND_TILE
    state.systems[WEST].planet_units = {"cormund": {"p1": {"infantry": 1}}}
    assert predicate(state, registry, "p1")


@ruling("leaders:cabalcommander#1")
def test_commander_dwie_sztuki_poza_limitem(registry: StaticDataRegistry) -> None:
    state = _producing(_state())
    state.players["p1"].trade_goods = 10
    orders = [ProductionOrder("fighter", 4), ProductionOrder("infantry", 3, zone=ACHERON)]
    grid = _grid(state, registry)
    with pytest.raises(ValueError, match="Production limit"):
        production.validate_production(state, grid, registry, "p1", orders)
    state.players["p1"].leader_states["cabalcommander"] = "unlocked"
    after = production.produce(state, grid, registry, "p1", orders)
    assert after.production_used == 5  # 7 sztuk, 2 poza limitem PRODUCTION 5
    assert production.free_small_units(after, "p1", [ProductionOrder("fighter", 1)]) == 0


# ------------------------------------------------- It Feeds on Carrion — Dimensional Anchor


class _Dice:
    """Kości o zadanych wynikach (po kolei, ostatni się powtarza)."""

    def __init__(self, *values: int) -> None:
        self.values = list(values)

    def randint(self, _a: int, _b: int) -> int:
        return self.values.pop(0) if len(self.values) > 1 else self.values[0]


def _hero(state: GameState, registry: StaticDataRegistry) -> GameState:
    work = state.clone()
    work.active_player_id = "p1"
    work.players["p1"].leader_states["cabalhero"] = "unlocked"
    assert faction_components.run_action_effect(work, registry, "p1", "leader:cabalhero", {})
    return work


@ruling("leaders:cabalhero#1", "leaders:cabalhero#2", "leaders:cabalhero#4",
        "F_vuilraith/it-feeds-on-carrion-dimensional-anchor/1",
        "F_vuilraith/it-feeds-on-carrion-dimensional-anchor/3")
def test_bohater_rzut_raz_na_statek_i_przechwycenie(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state()
    state.systems[EAST].planet_units = {VEFUTII: {"p1": {"spacedock": 1}}}  # druga szczelina
    state.systems[ARENA].space_units = {"p2": {"destroyer": 2, "fighter": 2}}  # obok obu
    state.systems[FAR].space_units = {"p2": {"cruiser": 1}}  # poza zasięgiem
    destroyed: list[str] = []
    real = capture.on_destroyed

    def spy(s: GameState, *args: Any) -> None:
        destroyed.append(str(args[2]))
        real(s, *args)

    monkeypatch.setattr(capture, "on_destroyed", spy)
    monkeypatch.setattr(cabal, "next_rng", lambda _s: _Dice(2))
    after = _hero(state, registry)
    assert after.table_roll is not None and after.table_roll["dice"] == [2, 2]  # raz na statek
    assert after.players["p1"].captured_units == {"p2": {"destroyer": 2}}
    assert after.systems[ARENA].space_units["p2"] == {"fighter": 2}  # myśliwce nie rzucają
    assert after.systems[FAR].space_units["p2"] == {"cruiser": 1}
    assert destroyed == []  # przechwycone, nie zniszczone
    assert after.players["p1"].leader_states["cabalhero"] == "purged"


@ruling("leaders:cabalhero#1")
def test_bohater_rzuty_kazdego_przeciwnika_widoczne(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    """„Each other player rolls” - rzut KAŻDEGO przeciwnika trafia na stół (UI), nie tylko
    ostatniego (wcześniej ``table_roll`` nadpisywał się i widać było kości jednego gracza)."""
    state = _state()
    state.players["p3"] = PlayerState(player_id="p3", color="green", faction="hacan",
                                      home_position=WEST)
    state.seating_order = ["p1", "p2", "p3"]
    state.systems[ARENA].space_units = {"p2": {"destroyer": 2}, "p3": {"cruiser": 3}}
    monkeypatch.setattr(cabal, "next_rng", lambda _s: _Dice(9))
    after = _hero(state, registry)
    rolls = [(r["playerId"], len(r["dice"])) for r in after.table_rolls]
    assert rolls == [("p2", 2), ("p3", 3)]  # 1 kość na każdy statek każdego gracza
    assert [r["seq"] for r in after.table_rolls] == sorted(r["seq"] for r in after.table_rolls)


@ruling("leaders:cabalhero#3", "F_vuilraith/it-feeds-on-carrion-dimensional-anchor/4",
        "F_vuilraith/it-feeds-on-carrion-dimensional-anchor/5")
def test_bohater_nadwyzka_ladunku_tez_przechwycona(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state()
    state.systems[ARENA].space_units = {
        "p2": {"carrier": 1, "dreadnought": 1, "infantry": 2, "fighter": 1},
    }
    monkeypatch.setattr(cabal, "next_rng", lambda _s: _Dice(1, 9))  # carrier 1, dreadnought 9
    after = capacity.open_capacity_check(_hero(state, registry), registry, ARENA)
    assert after.players["p1"].captured_units == {"p2": {"carrier": 1}}
    window = after.pending_window
    assert window is not None and window.queue[0] == "p2"  # właściciel wybiera, co usuwa (4)
    after = capacity.resolve_capacity(after, registry, "p2", {"infantry": 1, "fighter": 1})
    assert after.players["p1"].captured_tokens == {"infantry": 1, "fighter": 1}
    assert after.systems[ARENA].space_units["p2"] == {"dreadnought": 1, "infantry": 1}


@ruling("F_vuilraith/it-feeds-on-carrion-dimensional-anchor/2")
def test_bohater_blokujacy_tear_nie_rzuca(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state()
    state.systems[HOME].space_units = {"p2": {"destroyer": 1}}  # blokada Dimensional Tear
    state.systems[ARENA].space_units = {"p2": {"destroyer": 1}}
    monkeypatch.setattr(cabal, "next_rng", lambda _s: _Dice(1))
    after = _hero(state, registry)
    assert after.players["p1"].captured_units == {}


@ruling("leaders:cabalhero#unlock")
def test_bohater_odblokowanie(registry: StaticDataRegistry) -> None:
    state = _state()
    predicate = leaders.unlock_predicate(registry, "cabalhero")
    assert predicate is not None and not predicate(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert predicate(state, registry, "p1")


# --------------------------------------------------------------------------- Crucible


def _crucible(state: GameState, registry: StaticDataRegistry) -> None:
    cabal.crucible(state, registry, "p2", {})


@ruling("promissory_notes:crucible#1", "F_vuilraith/crucible/1", "F_vuilraith/crucible/2",
        "F_vuilraith/crucible/2.1", "F_vuilraith/crucible/2.1", "F_vuilraith/crucible/2.2",
        "F_vuilraith/crucible/2.3", "F_vuilraith/crucible/2.4")
def test_crucible_bez_rzutow_i_jedno_dodatkowe_plus_jeden(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[ARENA].planet_units = {WELLON: {"p1": {"spacedock": 1}}}
    state.systems[EAST].system_id = RIFT_TILE
    grid = _grid(state, registry)
    assert movement.rift_roll_nodes(state, grid, [HOME, FAR], "p2") == [HOME]
    _crucible(state, registry)
    assert movement.rift_roll_nodes(state, grid, [HOME, FAR], "p2") == []
    assert movement.rift_bonus(state, grid, [FAR, WEST], "p2") == 0
    assert movement.rift_bonus(state, grid, [HOME, FAR], "p2") == 2
    assert movement.rift_bonus(state, grid, [HOME, ARENA, FAR], "p2") == 3
    assert movement.rift_bonus(state, grid, [HOME, ARENA, EAST, FAR], "p2") == 4


@ruling("F_vuilraith/crucible/3", "F_vuilraith/crucible/3.1")
def test_crucible_trasa_liczona_z_premia(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[WEST].system_id = RIFT_TILE  # X=104 – S=105 – G=106 – Y=101
    state.active_system = HOME
    state.systems[HOME].command_tokens = ["p2"]
    state.systems[RIVAL].space_units = {"p2": {"carrier": 1}}  # Carrier I: ruch 1
    grid = _grid(state, registry)
    route = [RIVAL, FAR, WEST, HOME]
    assert not movement.can_move(state, grid, registry, RIVAL, "carrier", "p2", route=route)[0]
    _crucible(state, registry)
    ok, reason = movement.can_move(state, grid, registry, RIVAL, "carrier", "p2", route=route)
    assert ok, reason


@ruling("R_abilities/notes/6")
def test_crucible_nie_dwa_razy_w_jednym_oknie(registry: StaticDataRegistry) -> None:
    state = _state()
    assert cabal._crucible_condition(state, registry, "p2", None) is None  # type: ignore[arg-type]
    _crucible(state, registry)
    assert cabal._crucible_condition(state, registry, "p2", None)  # type: ignore[arg-type]


@ruling("F_vuilraith/crucible/4", "F_vuilraith/crucible/4.1")
def test_crucible_z_nav_suite_plus_jeden(registry: StaticDataRegistry) -> None:
    from src.core import active_effects
    from src.core.game_events import Duration

    state = _state()
    state.systems[EAST].system_id = RIFT_TILE
    _crucible(state, registry)
    grid = _grid(state, registry)
    assert movement.rift_bonus(state, grid, [EAST, FAR], "p2") == 2
    active_effects.add_effect(state, "action_cards:nav_suite", Duration.TACTICAL_ACTION,
                              owner="p2")
    state.tactical_step = TacticalStep.MOVEMENT  # Nav Suite działa w kroku ruchu
    assert rules_hooks.permits(rules_hooks.POINT_MOVEMENT_IGNORE_ANOMALIES, state, "p2")
    assert movement.rift_bonus(state, grid, [EAST, FAR], "p2") == 1  # tylko +1 z Crucible


# ----------------------------------------------------------- Al'raith Ix Ianovar (przełom)


@ruling("breakthroughs:cabalbt#1", "F_vuilraith/alraith-ix-ianovar/1",
        "F_vuilraith/alraith-ix-ianovar/2",
        "F_vuilraith/alraith-ix-ianovar/2.1", "F_vuilraith/alraith-ix-ianovar/2.2")
def test_przelom_fracture_bez_rzutu_z_synergia(registry: StaticDataRegistry) -> None:
    state = _state()
    grid = _grid(state, registry)
    expeditions.gain_breakthrough(state, registry, grid, "p1")
    assert state.fracture.in_play and state.fracture.last_roll is None  # bez rzutu
    assert state.fracture.breakthrough_id == "cabalbt"
    synergy = [c for c in registry.breakthroughs["cabalbt"].synergy]
    assert sorted(c.color for c in state.fracture.pending) == sorted(
        c for c in synergy if c in {c.color for c in state.fracture.pending}
    )
    assert all(c.remaining <= fracture.INGRESS_PER_SYNERGY_COLOR for c in state.fracture.pending)
    state.systems[EAST].system_id = RIFT_TILE  # jest dokąd przesunąć
    if state.fracture.pending:  # najpierw wszystkie ingressy (1.2) - oferty jeszcze nie ma
        assert not _offers(state, "p1", "Al'raith Ix Ianovar: move ingress tokens")
        while state.fracture.pending:
            choice = state.fracture.pending[0]
            spot = fracture.ingress_candidates(state, registry, grid, choice.color)[0]
            state = fracture.choose_ingress(state, registry, grid, "p1", choice.color, spot)
    # Zaraz po rozłożeniu ostatniego ingressu oferta wyskakuje sama (decyzja 2026-11-23).
    assert _offers(state, "p1", "Al'raith Ix Ianovar: move ingress tokens")


@ruling("breakthroughs:cabalbt#2", "F_vuilraith/alraith-ix-ianovar/3")
def test_przelom_przesuwa_ingress_do_szczeliny(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.fracture.in_play = True
    state.fracture.pending = []
    state.systems[FAR].ingress_token = True
    state.systems[WEST].ingress_token = True
    state.systems[EAST].system_id = RIFT_TILE
    assert not cabal._ingress_ready(state, "p1", {})  # tylko zaraz po wejściu przełomu
    cabal._open_ingress_window(state, "p1", {})
    assert cabal._ingress_ready(state, "p1", {})
    inputs = cabal.ingress_inputs(state, registry, "p1")
    targets = {o["value"] for o in inputs[1]["options"]}
    assert {HOME, EAST} <= targets  # Dimensional Tear też jest szczeliną
    cabal.move_ingress(state, registry, "p1",
                       {"from_1": FAR, "to_1": HOME, "from_2": WEST, "to_2": EAST})
    assert state.systems[HOME].ingress_token and state.systems[EAST].ingress_token
    assert not state.systems[FAR].ingress_token
    assert not cabal._ingress_ready(state, "p1", {})  # zużyte


@ruling("F_vuilraith/alraith-ix-ianovar/3.1", "F_vuilraith/alraith-ix-ianovar/4")
def test_przelom_ingress_nie_do_zajetej_szczeliny_ani_do_fracture(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.fracture.in_play = True
    state.fracture.pending = []
    state.systems[FAR].ingress_token = True
    state.systems[EAST].system_id = RIFT_TILE
    state.systems[EAST].ingress_token = True  # szczelina już z ingressem
    state.systems[WEST].system_id = CORMUND_TILE
    fracture_pos = fracture.FRACTURE_POSITIONS[0]
    board_graph.ensure_system(state, fracture_pos).system_id = RIFT_TILE  # szczelina w Fracture
    board_graph.ensure_system(state, fracture_pos).planet_units = {
        "x": {"p1": {"spacedock": 1}}}  # nawet z własnym dokiem
    cabal._open_ingress_window(state, "p1", {})
    targets = {o["value"] for o in cabal.ingress_inputs(state, registry, "p1")[1]["options"]}
    assert fracture_pos in cabal._grid(state).positions  # vacuity guard
    assert EAST not in targets and fracture_pos not in targets  # 3.1, 4
    assert {HOME, WEST} <= targets
    for bad in (EAST, fracture_pos):
        with pytest.raises(ValueError, match="gravity rift without one"):
            cabal.move_ingress(state, registry, "p1", {"from_1": FAR, "to_1": bad})
    cabal.move_ingress(state, registry, "p1", {"from_1": FAR, "to_1": HOME})
    assert state.systems[HOME].ingress_token


@ruling("breakthroughs:cabalbt#3")
def test_przelom_plus_jeden_z_fracture(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    start = fracture.FRACTURE_POSITIONS[0]
    point = rules_hooks.POINT_MOVEMENT_MOVE_VALUE
    assert rules_hooks.modify(point, state, "p1", 2, {"from": start, "base_type": "cruiser"}) == 3
    assert rules_hooks.modify(point, state, "p1", 2, {"from": HOME, "base_type": "cruiser"}) == 2


def test_ingress_choice_model() -> None:
    """Pomocniczo: model wyboru ingressu (używany przez przełom) się nie zmienił."""
    assert IngressChoice(color="BIOTIC", remaining=1).remaining == 1


@ruling("F_vuilraith/the-terror-between/1.1")
def test_flagowiec_po_direct_hit_nie_przechwytuje_reszty_rundy() -> None:
    """Direct Hit niszczy flagowiec PO Sustain Damage, przed przypisaniem pozostałych trafień -
    nie trafia do śladu ``destroyed_ships`` rundy, więc reszta strat nie jest „w tym samym
    czasie”."""
    state = _state()
    state.systems[ARENA].space_units = {"p1": {"flagship": 1, "cruiser": 1}, "p2": {"cruiser": 1}}
    _combat(state)
    _destroy(state, ARENA, "space", "p1", "flagship")  # Direct Hit (bez note_destroyed)
    _destroy(state, ARENA, "space", "p1", "cruiser")  # pozostałe trafienia
    assert state.players["p1"].captured_units == {}


@ruling("F_vuilraith/dimensional-tear/5")
def test_nekro_kopiuje_dimensional_tear_ii(registry: StaticDataRegistry) -> None:
    """Nekro copying Dimensional Tear II (Valefar Assimilator): systems with the Nekro's space
    docks are gravity rifts, and the Vuil'raith must roll for removal there (only the Nekro's own
    ships skip that roll)."""
    from src.core import map_anomalies, movement_paths

    state = _state("nekro")
    state.players["p2"].technologies = ["vax"]
    state.systems[EAST].space_units = {"p2": {"spacedock": 1}}
    assert EAST not in map_anomalies.extra_anomalies(state)
    technology.assimilate(state, "p2", "vax", cabal.DT2)
    assert map_anomalies.GRAVITY_RIFT in map_anomalies.extra_anomalies(state)[EAST]
    assert movement_paths.rolls_at(state, "p1", EAST)  # the Vuil'raith rolls
    assert not movement_paths.rolls_at(state, "p2", EAST)  # "your ships do not roll"
    assert not movement_paths.rolls_at(state, "p1", HOME)  # its own tear: still no roll
