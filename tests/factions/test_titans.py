"""The Titans of Ul — komplet komponentów frakcji (RULES.md 62.18) i rulingi F_ul.

Scenariusze przez prawdziwe API (oferty, notka, akcje, przełom): ``test_flows_titans.py``.
Żetony sleeper (RULES.md 61.6): ``core/faction_tokens.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    active_effects,
    board_graph,
    capacity,
    exploration,
    faction_components,
    faction_tokens,
    invasion_bombard,
    invasion_common,
    invasion_defense,
    leaders,
    planet_stats,
    production,
    promissory_play,
    rules_hooks,
    space_cannon,
    tactical,
    triggers,
)
from src.core.battle import combat_units
from src.core.combat import resolve_unit_variant
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    InvasionState,
    Phase,
    PlayerState,
    ProductionGrant,
    SystemState,
)
from src.core.hooks import reactions_invasion
from src.core.hooks.factions import l1z1x, titans
from src.core.production import ProductionOrder, Spend, reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.strategy_cards import common as sc_common
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE, UNIT_CAP_BY_ASYNC_ID
from tests.factions.completeness import missing_components
from tests.rulings import ruling

# 101 = dom Titans (55: Elysium), 102 = Wellon (19), 103 = New Albion / Starpoint (27),
# 104 = Thibah (21, p2), 105 = Tar'mann (22), 106 = Quann (25); 000 = Mecatol.
HOME, ARENA, EAST, RIVAL, FAR, WEST = "101", "102", "103", "104", "105", "106"
ELYSIUM, WELLON, ALBION, STARPOINT = "elysium", "wellon", "newalbion", "starpoint"
THIBAH, TARMANN, QUANN = "thibah", "tarmann", "quann"
SLEEPER = faction_tokens.SLEEPER


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
    """p1 = Titans (aktywny, dom z dokiem na Elysium), p2 = rywal na Thibah."""
    p1 = PlayerState(player_id="p1", color="red", faction="titans", home_position=HOME,
                     strategy_cards=[4])
    p2 = PlayerState(player_id="p2", color="blue", faction=other, home_position=RIVAL,
                     strategy_cards=[2])
    state = GameState(
        phase=Phase.ACTION, active_player_id="p1", speaker_id="p1", seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            HOME: SystemState(position=HOME, system_id="55", planet_owners={ELYSIUM: "p1"},
                              planet_units={ELYSIUM: {"p1": {"spacedock": 1, "infantry": 2}}}),
            ARENA: SystemState(position=ARENA, system_id="19"),
            EAST: SystemState(position=EAST, system_id="27"),
            RIVAL: SystemState(position=RIVAL, system_id="21", planet_owners={THIBAH: "p2"},
                               planet_units={THIBAH: {"p2": {"infantry": 1}}}),
            FAR: SystemState(position=FAR, system_id="22"),
            WEST: SystemState(position=WEST, system_id="25"),
        },
    )
    p1.controlled_planets = [ELYSIUM]
    p2.controlled_planets = [THIBAH]
    for p in state.players.values():
        p.cc_reinf = 8
    return state


def _own(state: GameState, position: str, planet: str, pid: str = "p1",
         units: dict[str, int] | None = None) -> None:
    system = state.systems[position]
    system.planet_owners[planet] = pid
    if units is not None:
        system.planet_units.setdefault(planet, {})[pid] = dict(units)
    if planet not in state.players[pid].controlled_planets:
        state.players[pid].controlled_planets.append(planet)


def _sleeper(state: GameState, position: str, planet: str, pid: str = "p1") -> None:
    faction_tokens.place(state, pid, SLEEPER, position, planet)


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


def _activate(state: GameState, registry: StaticDataRegistry, position: str) -> GameState:
    return tactical.activate_system(state, _grid(state, registry), position)


def _explored(state: GameState, planet: str, pid: str = "p1") -> GameState:
    work = state.clone()
    triggers.fire(work, GameEvent.PLANET_EXPLORED, Moment.AFTER, subject=pid,
                  ctx={"player": pid, "planet": planet, "deck": "industrial"})
    return work


def _units(state: GameState, position: str, zone: str, pid: str = "p1") -> dict[str, int]:
    system = state.systems[position]
    if zone == "space":
        return dict(system.space_units.get(pid, {}))
    return dict(system.planet_units.get(zone, {}).get(pid, {}))


def test_kompletnosc_titans(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "titans") == []


# ------------------------------------------------------------------------------ Terragenesis


@ruling("abilities:terragenesis#1")
def test_terragenesis_kladzie_zeton_z_puli(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    after = _accept(_explored(state, WELLON), "p1", "Terragenesis", {"source": "supply"})
    assert faction_tokens.on_planet(after, WELLON, SLEEPER) == "p1"
    assert faction_tokens.supply_left(after, "p1", SLEEPER) == faction_tokens.SUPPLY[SLEEPER] - 1


@ruling("F_ul/terragenesis/2")
def test_terragenesis_przenosi_zeton_dopiero_przy_pustej_puli(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    _own(state, EAST, ALBION, units={"infantry": 1})
    _sleeper(state, EAST, ALBION)
    assert not _offers(_explored(state, ALBION), "p1", "Terragenesis")  # „does not have a sleeper”
    # Tokens left in the pool: moving a placed token is not allowed (F_ul terragenesis 2).
    explored = _explored(state, WELLON)
    offer = _offers(explored, "p1", "Terragenesis")[0]
    values = {o["value"] for o in titans.terragenesis_inputs(explored, registry, "p1",
                                                             offer.ctx)[0]["options"]}
    assert values == {"supply"}
    with pytest.raises(ValueError):
        triggers.accept_offer(explored, "p1", offer.id, {"source": ALBION})
    # All sleeper tokens on the board: only moving a placed token remains.
    for position, planet in ((FAR, TARMANN), (WEST, QUANN), (EAST, STARPOINT), ("000", "mr")):
        _sleeper(state, position, planet)
    assert faction_tokens.supply_left(state, "p1", SLEEPER) == 0
    explored = _explored(state, WELLON)
    offer = _offers(explored, "p1", "Terragenesis")[0]
    inputs = titans.terragenesis_inputs(explored, registry, "p1", offer.ctx)
    values = {o["value"] for o in inputs[0]["options"]}
    assert "supply" not in values and ALBION in values
    after = triggers.accept_offer(explored, "p1", offer.id, {"source": ALBION})
    assert faction_tokens.on_planet(after, WELLON, SLEEPER) == "p1"
    assert faction_tokens.on_planet(after, ALBION, SLEEPER) is None


# ---------------------------------------------------------------------------------- Awaken


@ruling("abilities:awaken#1", "units:titans_pds#1")
def test_awaken_zamienia_zeton_na_pds(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    _sleeper(state, ARENA, WELLON)
    after = _accept(_activate(state, registry, ARENA), "p1", "Awaken", {f"sleeper:{WELLON}": "pds"})
    assert _units(after, ARENA, WELLON)["pds"] == 1
    assert faction_tokens.on_planet(after, WELLON, SLEEPER) is None
    assert faction_tokens.supply_left(after, "p1", SLEEPER) == faction_tokens.SUPPLY[SLEEPER]


def test_awaken_kazdy_zeton_osobno(registry: StaticDataRegistry) -> None:
    """⚠️ ZAŁOŻENIE 62.18: gracz może zamienić tylko część żetonów."""
    state = _state()
    _own(state, EAST, ALBION, units={"infantry": 1})
    _own(state, EAST, STARPOINT, units={"infantry": 1})
    _sleeper(state, EAST, ALBION)
    _sleeper(state, EAST, STARPOINT)
    after = _accept(_activate(state, registry, EAST), "p1", "Awaken",
                    {f"sleeper:{ALBION}": "pds", f"sleeper:{STARPOINT}": "keep"})
    assert _units(after, EAST, ALBION)["pds"] == 1
    assert "pds" not in _units(after, EAST, STARPOINT)
    assert faction_tokens.on_planet(after, STARPOINT, SLEEPER) == "p1"


@ruling("F_ul/awaken/1", "F_ul/awaken/2")
def test_awaken_tylko_zetony_z_chwili_aktywacji(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    after = _activate(state, registry, ARENA)
    assert not _offers(after, "p1", "Awaken")
    # Żeton położony w kroku aktywacji (Scanlink + Terragenesis) nie budzi się w tej akcji.
    _sleeper(after, ARENA, WELLON)
    assert titans.awaken_sleepers(after, "p1", ARENA) == []


@ruling("F_ul/awaken/9")
def test_awaken_przy_pustej_rezerwie_pds_z_planszy(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    _own(state, FAR, TARMANN, units={"pds": 2})
    _own(state, WEST, QUANN, units={"pds": 2})
    _own(state, EAST, ALBION, units={"pds": 2})
    state.systems[EAST].command_tokens = ["p1"]  # z tego systemu nie wolno zdjąć
    state.systems[FAR].damaged_units = {TARMANN: {"p1": {"pds": 1}}}
    _sleeper(state, ARENA, WELLON)
    assert reinforcements_left(state, "p1", "pds") == 0
    activated = _activate(state, registry, ARENA)
    offer = _offers(activated, "p1", "Awaken")[0]
    inputs = titans.awaken_inputs(activated, registry, "p1", offer.ctx)
    sources = next(i for i in inputs if i["key"] == f"from:{WELLON}")
    values = {o["value"] for o in sources["options"]}
    assert f"{FAR}|{TARMANN}" in values and f"{EAST}|{ALBION}" not in values
    after = triggers.accept_offer(activated, "p1", offer.id, {
        f"sleeper:{WELLON}": "pds", f"from:{WELLON}": f"{FAR}|{TARMANN}",
    })
    assert _units(after, FAR, TARMANN)["pds"] == 1
    assert _units(after, ARENA, WELLON)["pds"] == 1
    assert not after.systems[ARENA].damaged_units  # postawiony nieuszkodzony


@ruling("F_ul/coalescence/2", "abilities:coalescence#1")
def test_awaken_na_cudzej_planecie(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, pid="p2", units={"spacedock": 1})
    _own(state, EAST, ALBION, pid="p2", units={"infantry": 1})
    _sleeper(state, ARENA, WELLON)
    _sleeper(state, EAST, ALBION)
    # Bez sił naziemnych przeciwnika: jego struktury giną, Titans przejmują planetę od razu.
    after = _accept(_activate(state, registry, ARENA), "p1", "Awaken",
                    {f"sleeper:{WELLON}": "pds"})
    assert after.systems[ARENA].planet_owners[WELLON] == "p1"
    assert "p2" not in after.systems[ARENA].planet_units[WELLON]
    # Z siłami naziemnymi: walka naziemna w kroku Invasion bez lądowania (Coalescence).
    after = _accept(_activate(state, registry, EAST), "p1", "Awaken",
                    {f"sleeper:{ALBION}": "pds"})
    assert after.systems[EAST].planet_owners[ALBION] == "p2"
    assert invasion_common_contested(after, registry, EAST) == [ALBION]


def invasion_common_contested(state: GameState, registry: StaticDataRegistry,
                              position: str) -> list[str]:
    from src.core.invasion import _contested

    state.invasion = InvasionState(position=position, attacker="p1")  # krok Invasion
    return _contested(state, registry, position, "p1")


@ruling("F_ul/coalescence/1")
def test_hel_titan_z_awaken_nie_dostaje_trafien_scd(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, pid="p2", units={"pds": 1})
    state.systems[ARENA].planet_units[WELLON]["p1"] = {"infantry": 1, "pds": 1}
    state.active_system = ARENA
    state.invasion = InvasionState(position=ARENA, attacker="p1",
                                   committed={WELLON: {"infantry": 1}})
    units = invasion_defense._landed_units(state, _grid(state, registry), registry, WELLON, "p1")
    assert set(units) == {"infantry"}


@ruling("F_ul/awaken/8")
def test_ceasefire_nie_blokuje_awaken(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    _sleeper(state, ARENA, WELLON)
    activated = _activate(state, registry, ARENA)
    active_effects.add_effect(activated, promissory_play.CEASEFIRE_EFFECT,
                              Duration.TACTICAL_ACTION, owner="p1", data={"position": ARENA})
    after = _accept(activated, "p1", "Awaken", {f"sleeper:{WELLON}": "pds"})
    assert _units(after, ARENA, WELLON)["pds"] == 1


@ruling("F_ul/coalescence/3", "F_ul/coalescence/3.1")
def test_w_turze_titans_harrow_nie_dziala(registry: StaticDataRegistry) -> None:
    state = _state(other="l1z1x")
    _own(state, ARENA, WELLON, pid="p2", units={"infantry": 1})
    state.systems[ARENA].planet_units[WELLON]["p1"] = {"pds": 1}
    state.systems[ARENA].space_units = {"p2": {"dreadnought": 2}}
    state.active_system = ARENA
    state.active_combat = ActiveCombat(kind="ground", position=ARENA, planet=WELLON,
                                       attacker="p1", defender="p2")
    assert not l1z1x._harrow_ready(state, "p2", {"kind": "ground", "phase": "combat"})


# --------------------------------------------------------------------------- Hel-Titan (PDS)


@ruling("technologies:ht2#3")
def test_hel_titan_broni_planety_i_walczy(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"pds": 1})
    assert invasion_common._defenders(state, WELLON, ARENA, "p2") == ["p1"]
    units = combat_units(state, _grid(state, registry), registry, kind="ground", position=ARENA,
                         planet=WELLON, player_id="p1")
    assert [(u.base_type, u.hits_on) for u in units] == [("pds", 7)]
    state.players["p1"].technologies = ["ht2"]
    assert invasion_common._defenders(state, WELLON, ARENA, "p2") == ["p1"]
    # Zwykły PDS innej frakcji nie broni planety.
    _own(state, EAST, ALBION, pid="p2", units={"pds": 1})
    assert invasion_common._defenders(state, ALBION, EAST, "p1") == []


@ruling("units:titans_pds#2", "technologies:ht2#4")
def test_hel_titan_nie_jest_ladunkiem() -> None:
    assert "pds" not in capacity.CARGO_TYPES


@ruling("technologies:ht2#1", "technologies:ht2#2")
def test_hel_titan_ii_statystyki(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "titans", ["ht2"], "pds")
    assert unit is not None and unit.id == "titans_pds2"
    assert (unit.combat_hits_on, unit.space_cannon_hits_on, unit.production_value) == (6, 5, 1)
    assert unit.planetary_shield and unit.sustain_damage


@ruling("technologies:ht2#5")
def test_hel_titan_ii_strzela_do_sasiedniego_systemu(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"pds": 1})
    state.active_system = HOME
    grid = _grid(state, registry)
    assert not space_cannon.offense_shooters(state, grid, registry, "p1") or all(
        s.position == HOME for s in space_cannon.offense_shooters(state, grid, registry, "p1")
    )
    state.players["p1"].technologies = ["ht2"]
    remote = [s for s in space_cannon.offense_shooters(state, grid, registry, "p1") if s.remote]
    assert [(s.position, s.hits_on) for s in remote] == [(ARENA, 5)]


def test_karty_strategii_produkuja_tylko_dokiem(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[HOME].planet_units[ELYSIUM]["p1"]["pds"] = 2
    types = {p.base_type for p in production.producers(state, registry, "p1", HOME)}
    assert types == {"spacedock", "pds"}
    sc_common.start_standalone_production(state, "p1", HOME, "Warfare")
    assert {p.base_type for p in production.producers(state, registry, "p1", HOME)} == {
        "spacedock"
    }


@ruling("F_ul/heltitan/1")
def test_produkcja_hel_titanow_sumuje_sie(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"pds": 2})
    found = production.producers(state, registry, "p1", ARENA)
    assert [(p.base_type, p.count, p.value) for p in found] == [("pds", 2, 2)]


@ruling("F_ul/heltitan/2")
def test_decoy_operation_i_transit_diodes_moga_uzyc_hel_titana(
    registry: StaticDataRegistry,
) -> None:
    from src.core.hooks import reactions_tactical, technologies_actions
    from src.core.reaction_cards import WINDOW_KEY

    # Decoy Operation: Hel-Titan (structure + ground force) is removed and placed again.
    state = _state()
    _own(state, ARENA, WELLON, units={"pds": 1})
    assert ("pds" in {bt for _p, _z, bt, _c in reactions_tactical._ground_force_options(
        state, "p1")})
    params = {
        WINDOW_KEY: {"ctx": {"position": HOME}},
        "planet": ELYSIUM,
        "units": [{"planet": WELLON, "base_type": "pds"}],
    }
    reactions_tactical.decoy_operation(state, registry, "p1", params)
    assert _units(state, ARENA, WELLON).get("pds", 0) == 0
    assert _units(state, HOME, ELYSIUM)["pds"] == 1

    # Transit Diodes: the same, from any system onto any planet the player controls.
    state = _state()
    state.players["p1"].technologies = ["td"]
    _own(state, ARENA, WELLON, units={"pds": 1})
    stacks = technologies_actions._td_stacks(state, registry, "p1")
    assert (ARENA, WELLON, "pds", 1) in stacks
    technologies_actions.transit_diodes(
        state, "p1", {"params": {"unit1": f"{ARENA}|{WELLON}|pds", "to1": f"{HOME}|{ELYSIUM}"}}
    )
    assert _units(state, ARENA, WELLON).get("pds", 0) == 0
    assert _units(state, HOME, ELYSIUM)["pds"] == 1


@ruling("F_ul/heltitan/3")
def test_ghost_squad_nie_przenosi_hel_titana(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"pds": 1, "infantry": 1})
    assert reactions_invasion._ground(state.systems[ARENA], WELLON, "p1") == {"infantry": 1}


@ruling("F_ul/heltitan/5")
def test_hel_titan_celem_bombardowania_tylko_bez_tarczy(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"pds": 1})
    state.active_player_id = "p2"
    state.active_system = ARENA
    state.systems[ARENA].space_units = {"p2": {"dreadnought": 1}}
    state.invasion = InvasionState(position=ARENA, attacker="p2")
    assert invasion_bombard.bombard_targets(state, registry) == []  # PLANETARY SHIELD
    state.players["p2"].technologies = ["ws"]
    state.systems[ARENA].space_units = {"p2": {"warsun": 1}}
    assert invasion_bombard.bombard_targets(state, registry) == [WELLON]


@ruling("technologies:se2#1", "technologies:se2#2")
def test_saturn_engine_ii_statystyki(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "titans", ["se2"], "cruiser")
    assert unit is not None and unit.id == "titans_cruiser2"
    assert (unit.cost, unit.combat_hits_on, unit.move_value, unit.capacity_value) == (2, 6, 3, 2)
    assert unit.sustain_damage


# ---------------------------------------------------------------------------------- Ouranos


@ruling("units:titans_flagship#1", "F_ul/ouranos/1", "F_ul/ouranos/2")
def test_ouranos_zastepuje_pds_z_chwili_aktywacji(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"pds": 1})
    after = _accept(_activate(state, registry, ARENA), "p1", "Ouranos", {"pds": WELLON})
    assert _units(after, ARENA, "space") == {"flagship": 1}
    assert "pds" not in _units(after, ARENA, WELLON)
    # PDS z Awaken w tej samej akcji nie może stać się Ouranosem.
    state = _state()
    _own(state, EAST, ALBION, units={"infantry": 1})
    _sleeper(state, EAST, ALBION)
    activated = _activate(state, registry, EAST)
    assert not _offers(activated, "p1", "Ouranos")
    after = _accept(activated, "p1", "Awaken", {f"sleeper:{ALBION}": "pds"})
    assert _units(after, EAST, ALBION)["pds"] == 1
    assert not _offers(after, "p1", "Ouranos")


# ------------------------------------------------------------------------- Hecatoncheires


@ruling("units:titans_mech#1", "F_ul/hecatoncheires/1")
def test_hecatoncheires_zamiast_pds(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, EAST, ALBION, units={"infantry": 1})
    _own(state, EAST, STARPOINT, units={"infantry": 1})
    _sleeper(state, EAST, ALBION)
    _sleeper(state, EAST, STARPOINT)
    # Kilka PDS w jednym kroku - decyzja osobno dla każdego.
    after = _accept(_activate(state, registry, EAST), "p1", "Awaken",
                    {f"sleeper:{ALBION}": "mech", f"sleeper:{STARPOINT}": "pds"})
    assert _units(after, EAST, ALBION) == {"infantry": 2, "mech": 1}
    assert _units(after, EAST, STARPOINT)["pds"] == 1
    # Construction: pseudo-struktura „mech” obok PDS.
    assert "mech" in sc_common.placeable_structures(state, "p1")[ELYSIUM]
    work = state.clone()
    sc_common.place_structure(work, "p1", ELYSIUM, "mech")
    assert _units(work, HOME, ELYSIUM) == {"spacedock": 1, "infantry": 3, "mech": 1}


@ruling("F_ul/hecatoncheires/4")
def test_hecatoncheires_tylko_z_rezerwy(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, FAR, TARMANN, units={"mech": _cap("mech")})
    assert sc_common.structure_problem(state, "p1", ELYSIUM, "mech") == (
        "No mech left in your reinforcements."
    )
    assert "mech" not in sc_common.placeable_structures(state, "p1")[ELYSIUM]


@ruling("F_ul/hecatoncheires/3")
def test_hecatoncheires_nie_na_planete_z_dwoma_pds(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[HOME].planet_units[ELYSIUM]["p1"]["pds"] = 2
    assert sc_common.structure_problem(state, "p1", ELYSIUM, "mech") is not None
    _own(state, ARENA, WELLON, units={"pds": 2})
    _sleeper(state, ARENA, WELLON)
    activated = _activate(state, registry, ARENA)
    offer = _offers(activated, "p1", "Awaken")[0]
    values = {o["value"] for o in titans.awaken_inputs(activated, registry, "p1", offer.ctx)[0][
        "options"]}
    assert values == {"keep"}


@ruling("F_ul/hecatoncheires/2")
def test_hecatoncheires_przy_pustej_rezerwie_pds(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, FAR, TARMANN, units={"pds": 2})
    _own(state, WEST, QUANN, units={"pds": 2})
    _own(state, ARENA, WELLON, units={"pds": 2})
    assert reinforcements_left(state, "p1", "pds") == 0
    assert sc_common.structure_problem(state, "p1", ELYSIUM, "mech") is not None
    assert "mech" in sc_common.placeable_structures(state, "p1", allow_board=True)[ELYSIUM]
    work = state.clone()
    sc_common.place_structure(work, "p1", ELYSIUM, "mech", source=TARMANN)
    assert _units(work, FAR, TARMANN)["pds"] == 1
    assert reinforcements_left(work, "p1", "pds") == 1  # PDS wrócił do rezerwy i tam leży
    assert _units(work, HOME, ELYSIUM)["mech"] == 1


# ---------------------------------------------------------------------------------- Tellurian


@ruling("leaders:titansagent#1")
def test_tellurian_anuluje_trafienie(registry: StaticDataRegistry) -> None:
    state = _state()
    state.active_combat = ActiveCombat(kind="space", position=ARENA, attacker="p1",
                                       defender="p2", step=CombatStep.ASSIGN,
                                       pending_hits={"p2": 2, "p1": 1})
    after, _ = faction_components.play(state, registry, "p1", "leader", titans.AGENT,
                                       {"hit": "combat:p2"})
    assert after.active_combat is not None
    assert after.active_combat.pending_hits == {"p2": 1, "p1": 1}
    assert after.players["p1"].leader_states[titans.AGENT] == "exhausted"


@ruling("F_ul/tellurian/1")
def test_tellurian_bez_trafien_do_przypisania(registry: StaticDataRegistry) -> None:
    state = _state()
    state.active_combat = ActiveCombat(kind="space", position=ARENA, attacker="p1",
                                       defender="p2", step=CombatStep.ROLL)
    with pytest.raises(ValueError, match="before hits are assigned"):
        faction_components.play(state, registry, "p1", "leader", titans.AGENT, {"hit": "x"})


def test_tellurian_space_cannon_i_bombardowanie(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, pid="p2", units={"infantry": 2})
    state.invasion = InvasionState(position=ARENA, attacker="p1", bombard_pending={WELLON: 2},
                                   log=[{"phase": "BOMBARDMENT", "planet": WELLON, "hits": 2,
                                         "rolls": []}])
    keys = [key for key, _target, _what in titans.pending_hit_targets(state)]
    assert keys == [f"bombard:{WELLON}"]
    titans.tellurian(state, registry, "p1", {"hit": f"bombard:{WELLON}"})
    assert state.invasion.bombard_pending == {WELLON: 1}


# -------------------------------------------------------------------------------- Tungstantus


@ruling("leaders:titanscommander#unlock")
def test_tungstantus_odblokowanie(registry: StaticDataRegistry) -> None:
    state = _state()
    unlocked = leaders.unlock_predicate(registry, titans.COMMANDER)
    assert unlocked is not None
    _own(state, ARENA, WELLON, units={"pds": 2})
    state.systems[EAST].space_units = {"p1": {"spacedock": 1}}  # dok w przestrzeni też
    assert not unlocked(state, registry, "p1")
    _own(state, FAR, TARMANN, units={"pds": 1})
    assert unlocked(state, registry, "p1")


def _producing(state: GameState) -> GameState:
    state.active_system = HOME
    state.players["p1"].trade_goods = 0
    state.players["p1"].exhausted_planets = [ELYSIUM]
    state.players["p1"].leader_states[titans.COMMANDER] = "unlocked"
    return state


@ruling("leaders:titanscommander#1", "F_ul/tungstantus/1", "F_ul/tungstantus/1.1")
def test_tungstantus_trade_good_przed_zaplata(registry: StaticDataRegistry) -> None:
    state = _producing(_state())
    grid = _grid(state, registry)
    orders = [ProductionOrder("fighter", 2)]
    with pytest.raises(ValueError, match="Not enough"):
        production.produce(state, grid, registry, "p1", orders, Spend(trade_goods=1))
    after = production.produce(state, grid, registry, "p1", orders, Spend(trade_goods=1),
                               commander_trade_good=True)
    assert after.players["p1"].trade_goods == 0  # zdobyty i od razu wydany
    assert _units(after, HOME, "space")["fighter"] == 2
    with pytest.raises(ValueError, match="already gained"):
        production.produce(after, grid, registry, "p1", orders, commander_trade_good=True)


@ruling("F_ul/tungstantus/1.2")
def test_tungstantus_bez_jednostek_bez_trade_good(registry: StaticDataRegistry) -> None:
    state = _producing(_state())
    after = production.produce(state, _grid(state, registry), registry, "p1", [],
                               commander_trade_good=True)
    assert after.players["p1"].trade_goods == 0


@ruling("F_ul/tungstantus/2")
def test_tungstantus_nie_przy_produkcji_bez_production(registry: StaticDataRegistry) -> None:
    state = _producing(_state())
    assert production.commander_trade_good_problem(state, "p1") is None
    state.production_grant = ProductionGrant(player_id="p1", position=HOME, free=True)
    assert production.commander_trade_good_problem(state, "p1") == (
        "This production does not use the PRODUCTION ability."
    )
    state.production_grant = None
    state.players["p1"].leader_states[titans.COMMANDER] = "locked"
    assert production.commander_trade_good_problem(state, "p1") is not None


# --------------------------------------------------------------------------------- Geoform


@ruling("leaders:titanshero#unlock")
def test_geoform_odblokowanie(registry: StaticDataRegistry) -> None:
    state = _state()
    unlocked = leaders.unlock_predicate(registry, titans.HERO)
    assert unlocked is not None
    state.players["p1"].scored_secrets = ["a", "b"]
    assert not unlocked(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert unlocked(state, registry, "p1")


@ruling("leaders:titanshero#1", "leaders:titanshero#2", "F_ul/ul-the-progenitor-geoform/1")
def test_geoform(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].exhausted_planets = [ELYSIUM]
    state.players["p1"].leader_states[titans.HERO] = "unlocked"
    work = state.clone()
    assert faction_components.run_action_effect(work, registry, "p1", f"leader:{titans.HERO}", {})
    # R_leaders: dołączona karta nie jest purge'owana (61.1), ale drugi raz jej nie użyjesz.
    assert faction_components.block_reason(work, registry, "p1", "leader", titans.HERO)
    assert ELYSIUM not in work.players["p1"].exhausted_planets
    stats = planet_stats.planet_stats(work, registry, ELYSIUM)
    base = registry.planets[ELYSIUM]
    assert stats is not None
    assert (stats.resources, stats.influence) == (base.resources + 3, base.influence + 3)
    shooters = space_cannon.zone_shooters(work, registry, "p1", HOME, ELYSIUM)
    assert [(s.base_type, s.hits_on, s.dice_per_unit) for s in shooters] == [("titanshero", 5, 3)]
    # SPACE CANNON należy do kontrolera Elysium.
    work.systems[HOME].planet_owners[ELYSIUM] = "p2"
    assert space_cannon.zone_shooters(work, registry, "p1", HOME, ELYSIUM) == []
    assert space_cannon.zone_shooters(work, registry, "p2", HOME, ELYSIUM)


# ------------------------------------------------------------------------------- Terraform


def _terraform(state: GameState, registry: StaticDataRegistry, planet: str) -> GameState:
    state.active_player_id = "p2"
    state.players["p2"].private.promissory_notes = [titans.TERRAFORM]
    after, implemented = promissory_play.play(state, registry, "p2", titans.TERRAFORM,
                                              {"planet": planet})
    assert implemented
    return after


@ruling("promissory_notes:terraform#1", "promissory_notes:terraform#2", "F_ul/terraform/1",
        "F_ul/terraform/2")
def test_terraform(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, "000", "mr", pid="p2")
    _own(state, HOME, ELYSIUM, pid="p2")
    assert titans.terraform_targets(state, "p2") == [THIBAH]  # bez domu i Mecatol Rex
    after = _terraform(state, registry, THIBAH)
    assert after.planet_attachments[THIBAH] == [titans.TERRAFORM]
    assert planet_stats.resources_of(after, registry, THIBAH) == 2
    assert planet_stats.influence_of(after, registry, THIBAH) == 2
    assert set(planet_stats.traits(after, registry, THIBAH)) >= {
        "cultural", "hazardous", "industrial"
    }
    # Nie wraca do Titans i nie leży w strefie zagrywającego - jest przy planecie.
    assert titans.TERRAFORM not in after.players["p1"].private.promissory_notes
    assert titans.TERRAFORM not in after.players["p2"].promissory_notes_in_play
    assert titans.TERRAFORM not in after.players["p2"].private.promissory_notes
    after.systems[RIVAL].planet_owners[THIBAH] = "p1"  # nowy kontroler ma premię
    assert planet_stats.resources_of(after, registry, THIBAH) == 2


@ruling("F_ul/terraform/3")
def test_terraform_eksplorujacy_wybiera_talie(registry: StaticDataRegistry) -> None:
    state = _terraform(_state(), registry, THIBAH)
    assert exploration.planet_traits(registry, THIBAH) == ["industrial"]
    assert set(exploration.planet_traits(registry, THIBAH, state)) == {
        "cultural", "hazardous", "industrial"
    }
    work = exploration.begin_exploration(state, registry, "p2", RIVAL, [THIBAH])
    with pytest.raises(ValueError, match="Choose which exploration deck"):
        exploration.draw(work, registry, THIBAH)


@ruling("F_ul/terraform/4")
def test_terraform_fracture_planet_with_only_lightning_is_explored(
    registry: StaticDataRegistry,
) -> None:
    """Fracture planets have only the LIGHTNING trait: Terraform makes them explorable."""
    state = _state()
    state.systems[RIVAL].planet_owners = {"cocytus": "p2"}
    assert not exploration.explorable(registry, "cocytus", state)
    state.planet_attachments["cocytus"] = [titans.TERRAFORM]
    assert not exploration.explorable(registry, "cocytus")  # without the board: no attachments
    assert exploration.explorable(registry, "cocytus", state)
    work = exploration.begin_exploration(state, registry, "p2", RIVAL, ["cocytus"])
    assert work.exploration is not None and work.exploration.queue == ["cocytus"]


# -------------------------------------------------------------------- Slumberstate Computing


@ruling(
    "breakthroughs:titansbt#3",
    "F_ul/slumberstate-computing/2",
    "F_ul/slumberstate-computing/3",
)
def test_slumberstate_zeton_na_cudzej_planecie_za_zgoda(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    # Thibah (104) nie sąsiaduje z domem Titans (101) - sąsiedztwo nie jest potrzebne.
    asked, _ = faction_components.play(state, registry, "p1", "breakthrough", titans.BREAKTHROUGH,
                                       {"planet": THIBAH, "source": "supply"})
    assert asked.transaction_tables == []  # zgoda to nie transakcja (stół nieotwarty)
    refused = _accept(asked, "p2", "Slumberstate", {"answer": "refuse"})
    assert faction_tokens.on_planet(refused, THIBAH, SLEEPER) is None
    allowed = _accept(asked, "p2", "Slumberstate", {"answer": "allow"})
    assert faction_tokens.on_planet(allowed, THIBAH, SLEEPER) == "p1"
    # Bez przełomu - brak tej możliwości.
    state.players["p1"].breakthrough_unlocked = False
    with pytest.raises(ValueError):
        faction_components.play(state, registry, "p1", "breakthrough", titans.BREAKTHROUGH,
                                {"planet": THIBAH, "source": "supply"})


# ----------------------------------------------------------- żetony na mapie (RULES.md 61.6)


def test_zetony_wracaja_przy_zniszczeniu_planety(registry: StaticDataRegistry) -> None:
    from src.core import tile_swap

    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    _sleeper(state, ARENA, WELLON)
    tile_swap.replace_tile(state, registry, ARENA, "81")
    assert faction_tokens.tokens_of(state, "p1", SLEEPER) == []
    assert faction_tokens.supply_left(state, "p1", SLEEPER) == faction_tokens.SUPPLY[SLEEPER]


def test_zeton_jeden_na_strefe() -> None:
    state = _state()
    _sleeper(state, ARENA, WELLON)
    with pytest.raises(ValueError, match="already"):
        faction_tokens.place(state, "p2", SLEEPER, ARENA, WELLON)


# ------------------------------------------------------------- krzyżowo: Letnev (Farran)


@ruling("F_letnev/rear-admiral-farran/2.1")
def test_farran_z_alliance_przy_sustain_hel_titana(registry: StaticDataRegistry) -> None:
    state = _state(other="letnev")
    state.players["p2"].leader_states["letnevcommander"] = "unlocked"
    state.players["p1"].promissory_notes_in_play = ["blue_an"]
    triggers.fire(state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "base_type": "pds", "count": 1})
    after = _accept(state, "p1", "Rear Admiral Farran")
    assert after.players["p1"].trade_goods == 1


def test_tellurian_anuluje_trafienie_afb(registry: StaticDataRegistry) -> None:
    """Trafienia AFB czekają na przypisanie w kroku ASSIGN (RULES.md 39 W4) - Tellurian działa."""
    state = _state()
    state.active_combat = ActiveCombat(kind="space", position=ARENA, attacker="p2",
                                       defender="p1", step=CombatStep.ASSIGN, afb_assign=True,
                                       pending_hits={"p1": 1})
    hits = titans.agent_inputs(state, registry, "p1")[0]
    assert hits["auto"] == "combat:p1"  # „Auto”: trafienie we własne jednostki
    after, _ = faction_components.play(state, registry, "p1", "leader", titans.AGENT, {})
    assert after.active_combat is not None and after.active_combat.pending_hits == {"p1": 0}


def test_wybor_z_auto_pominiete_pole_to_auto() -> None:
    """Decyzja użytkownika: każdy wybór ma „Auto”; pominięte pole = opcja Auto (bot, UI)."""
    from src.core import offer_inputs as oi

    inputs = [oi.choice("x", "X", [oi.option("a", "A"), oi.option("b", "B")], auto="b")]
    assert inputs[0]["auto"] == "b"
    assert oi.validate_params(inputs, {}) == {"x": "b"}
    assert oi.validate_params(inputs, {"x": "a"}) == {"x": "a"}
    # Auto spoza opcji jest ignorowane - pole zostaje wymagane.
    strict = [oi.choice("x", "X", [oi.option("a", "A")], auto="zzz")]
    assert "auto" not in strict[0]
    with pytest.raises(ValueError):
        oi.validate_params(strict, {})


def test_awaken_auto_bez_parametrow(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    _sleeper(state, ARENA, WELLON)
    after = _accept(_activate(state, registry, ARENA), "p1", "Awaken")  # „Auto” = PDS
    assert _units(after, ARENA, WELLON)["pds"] == 1

