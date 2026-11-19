"""The Clan of Saar — komplet komponentów frakcji (RULES.md 62.14) i rulingi F_saar.

Scenariusze przez prawdziwe API (ACTION, oferty, notka, setup): ``test_flows_saar.py``. Statusy
bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    faction_components,
    floating_structures,
    movement,
    objectives,
    production,
    promissory_play,
    retreat,
    rules_hooks,
    tactical,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.fleet_pool import fleet_report
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    TimingWindow,
    WindowType,
)
from src.core.hooks.factions import saar
from src.core.objective_progress import progress
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.strategy_cards.common import place_structure
from src.core.unit_ops import UnitCause
from tests.factions.completeness import missing_components
from tests.rulings import ruling

# Pierścień 1: 101 = dom Saar (11: Ragh, Lisisii), 102 = Vefutii (20), 103 = Thibah (21, p2),
# 104 = pole asteroid (44), 105 = Tarmann (22), 106 = gravity rift (41); 000 = Mecatol.
HOME, PLAIN, RIVAL, ASTEROID, FAR, RIFT = "101", "102", "103", "104", "105", "106"
RAGH, LISISII, VEFUTII, THIBAH, TARMANN = "ragh", "lisisii", "vefutii", "thibah", "tarmann"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _state(other: str = "sol") -> GameState:
    """p1 = Saar (aktywny, dok pływający i transportowiec w domu), p2 = rywal z Thibah."""
    p1 = PlayerState(player_id="p1", color="red", faction="saar", home_position=HOME)
    p2 = PlayerState(player_id="p2", color="blue", faction=other, home_position=FAR)
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            HOME: SystemState(position=HOME, system_id="11",
                              planet_owners={RAGH: "p1", LISISII: "p1"},
                              space_units={"p1": {"carrier": 1, "spacedock": 1}}),
            PLAIN: SystemState(position=PLAIN, system_id="20"),
            RIVAL: SystemState(position=RIVAL, system_id="21", planet_owners={THIBAH: "p2"}),
            ASTEROID: SystemState(position=ASTEROID, system_id="44"),
            FAR: SystemState(position=FAR, system_id="22"),
            RIFT: SystemState(position=RIFT, system_id="41"),
        },
    )
    state.players["p1"].controlled_planets = [RAGH, LISISII]
    state.players["p2"].controlled_planets = [THIBAH]
    for p in state.players.values():
        p.cc_reinf = 8
        p.tactical_cc = 3
        p.fleet_cc = 3
    return state


def _offers(state: GameState, pid: str, label: str) -> list[Any]:
    return [o for o in triggers.offers_for(state, pid) if label in o.label]


def _accept(state: GameState, pid: str, label: str, params: dict[str, Any] | None = None
            ) -> GameState:
    offer = _offers(state, pid, label)[0]
    return triggers.accept_offer(state, pid, offer.id, params)


def _play(state: GameState, registry: StaticDataRegistry, kind: str, comp: str,
          params: dict[str, Any] | None = None, pid: str = "p1") -> GameState:
    after, _ = faction_components.play(state, registry, pid, kind, comp, params or {})
    return after


def _activate(state: GameState, registry: StaticDataRegistry, position: str,
              pid: str = "p1") -> GameState:
    state.active_player_id = pid
    return tactical.activate_system(state, grid_from_state(state, registry), position)


def test_saar_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "saar") == []


# ==================================================================== Floating Factory


@ruling("units:saar_spacedock#1")
def test_dok_stawiany_w_przestrzeni(registry: StaticDataRegistry) -> None:
    state = _state()
    system = state.systems[PLAIN]
    unit_ops.place_units(state, system, VEFUTII, "p1", "spacedock", 1)
    assert system.space_units["p1"] == {"spacedock": 1}
    assert not system.planet_units.get(VEFUTII, {}).get("p1")
    # Inni gracze stawiają dok na planecie jak zwykle.
    unit_ops.place_units(state, state.systems[RIVAL], THIBAH, "p2", "spacedock", 1)
    assert state.systems[RIVAL].planet_units[THIBAH]["p2"] == {"spacedock": 1}


@ruling("units:saar_spacedock#2", "F_saar/floating-factory/1")
def test_dok_rusza_sie_jak_statek_bez_puli_floty(registry: StaticDataRegistry) -> None:
    state = _activate(_state(), registry, PLAIN)
    grid = grid_from_state(state, registry)
    after = movement.move_fleet(state, grid, registry, HOME, {"spacedock": 1, "carrier": 1}, {},
                                "p1")
    assert after.systems[PLAIN].space_units["p1"] == {"spacedock": 1, "carrier": 1}
    assert fleet_report(after, PLAIN, "p1", registry).ships == {"carrier": 1}


@ruling("F_saar/floating-factory/4")
def test_dok_z_efektem_ruchu_statkow(registry: StaticDataRegistry) -> None:
    """Gravity Drive (+1 dla jednego statku) przenosi dok o 2 systemy."""
    state = _state()
    state.players["p1"].technologies = ["gd"]
    state.systems[HOME].space_units = {"p1": {"spacedock": 1}}
    state = _activate(state, registry, RIVAL)
    grid = grid_from_state(state, registry)
    with pytest.raises(ValueError):
        movement.move_fleet(state, grid, registry, HOME, {"spacedock": 1}, {}, "p1",
                            route=[HOME, PLAIN, RIVAL])
    after = movement.move_fleet(state, grid, registry, HOME, {"spacedock": 1}, {}, "p1",
                                gravity_drive=True, route=[HOME, PLAIN, RIVAL])
    assert after.systems[RIVAL].space_units["p1"] == {"spacedock": 1}


@ruling("F_saar/floating-factory/5")
def test_dok_rzuca_przy_wylocie_ze_szczeliny(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[RIFT].space_units = {"p1": {"spacedock": 1}}
    state.systems[HOME].space_units = {}
    state = _activate(state, registry, FAR)
    grid = grid_from_state(state, registry)
    before = state.table_roll_seq
    after = movement.move_fleet(state, grid, registry, RIFT, {"spacedock": 1}, {}, "p1")
    assert after.table_roll_seq == before + 1  # rzut gravity rift dla doku


@ruling("units:saar_spacedock#2")
def test_dok_wycofuje_sie_jak_statek(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[PLAIN].space_units = {"p1": {"carrier": 1, "spacedock": 1},
                                        "p2": {"destroyer": 1}}
    state.systems[HOME].space_units = {}
    state.active_player_id = "p2"
    state.active_system = PLAIN
    grid = grid_from_state(state, registry)
    after, result = retreat.perform_retreat(state, grid, registry, PLAIN, "p1", HOME)
    assert result.moved.get("spacedock") == 1
    assert after.systems[HOME].space_units["p1"]["spacedock"] == 1


@ruling("units:saar_spacedock#3", "F_saar/floating-factory/11", "F_saar/floating-factory/11.1",
        "technologies:ffac2#5")
def test_dok_bez_statkow_niszczony_po_wlocie_wroga(registry: StaticDataRegistry) -> None:
    """Wrogie statki wlatują do systemu z samym dokiem: dok ginie od razu (przed SCO)."""
    state = _state()
    state.systems[PLAIN].space_units = {"p1": {"spacedock": 1}}
    state.systems[FAR].space_units = {"p2": {"cruiser": 1}}
    state = _activate(state, registry, PLAIN, pid="p2")
    grid = grid_from_state(state, registry)
    after = movement.move_fleet(state, grid, registry, FAR, {"cruiser": 1}, {}, "p2",
                                route=[FAR, "000", PLAIN])
    assert not after.systems[PLAIN].space_units.get("p1")
    assert after.tactical_step is TacticalStep.MOVEMENT  # jeszcze przed Space Cannon Offense


@ruling("F_saar/floating-factory/11.2", "F_saar/floating-factory/10")
def test_dok_nie_ginie_bez_przylotu_ani_przy_przelocie(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[PLAIN].space_units = {"p1": {"spacedock": 1}}
    # Ruch zakończony, a w systemie doku nie ma statków wroga (zniszczone w szczelinie / przelot).
    triggers.fire(state, GameEvent.SHIPS_MOVED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": RIVAL, "from": FAR, "ships": {"cruiser": 1},
                       "route": [FAR, PLAIN, RIVAL]})
    triggers.fire(state, GameEvent.SHIPS_MOVED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": PLAIN, "from": FAR, "ships": {}})
    assert state.systems[PLAIN].space_units["p1"] == {"spacedock": 1}


@ruling("F_saar/floating-factory/6", "F_saar/floating-factory/8")
def test_dok_ginie_na_koniec_walki_bez_statkow(registry: StaticDataRegistry) -> None:
    """Saar bez statków po walce, przeciwnik ma same myśliwce: dok ginie przed usunięciem
    myśliwców za capacity (COMBAT/END idzie przed sprawdzeniem pojemności)."""
    state = _state()
    state.systems[PLAIN].space_units = {"p1": {"spacedock": 1}, "p2": {"fighter": 2}}
    triggers.fire(state, GameEvent.COMBAT, Moment.END,
                  ctx={"kind": "space", "position": PLAIN, "winner": "p2"})
    assert not state.systems[PLAIN].space_units.get("p1")


@ruling("F_saar/floating-factory/6.1")
def test_dok_zostaje_gdy_obie_strony_bez_statkow(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[PLAIN].space_units = {"p1": {"spacedock": 1}}
    triggers.fire(state, GameEvent.COMBAT, Moment.END,
                  ctx={"kind": "space", "position": PLAIN, "winner": ""})
    assert state.systems[PLAIN].space_units["p1"] == {"spacedock": 1}


@ruling("F_saar/floating-factory/7")
def test_direct_hit_na_ostatni_statek_niszczy_dok(registry: StaticDataRegistry) -> None:
    state = _state()
    system = state.systems[PLAIN]
    system.space_units = {"p1": {"spacedock": 1, "dreadnought": 1}, "p2": {"cruiser": 1}}
    unit_ops.remove_units(state, system, "space", "p1", "dreadnought", 1, UnitCause.DESTROYED)
    assert not system.space_units.get("p1")


@ruling("F_saar/floating-factory/7.1")
def test_straty_rundy_i_brak_wroga_nie_niszcza_doku(registry: StaticDataRegistry) -> None:
    """Straty przypisywane w rundzie są równoczesne (okno przypisywania - bez blokady), a
    zniszczenie ostatniego statku bez wrogich statków w systemie nie blokuje doku."""
    state = _state()
    system = state.systems[PLAIN]
    system.space_units = {"p1": {"spacedock": 1, "dreadnought": 1}, "p2": {"cruiser": 1}}
    state.pending_window = TimingWindow(window_type=WindowType.COMBAT_ASSIGN_HITS,
                                         queue=["p1", "p2"])
    unit_ops.remove_units(state, system, "space", "p1", "dreadnought", 1, UnitCause.DESTROYED)
    assert system.space_units["p1"] == {"spacedock": 1}
    lone = _state()
    lone.systems[PLAIN].space_units = {"p1": {"spacedock": 1, "dreadnought": 1}}
    unit_ops.remove_units(lone, lone.systems[PLAIN], "space", "p1", "dreadnought", 1,
                          UnitCause.DESTROYED)
    assert lone.systems[PLAIN].space_units["p1"] == {"spacedock": 1}


@ruling("F_saar/floating-factory/2")
def test_dok_produkuje_sily_naziemne_w_przestrzen_albo_na_planete(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    zones = production.allowed_ground_zones(state, registry, "p1", HOME)
    assert set(zones) == {RAGH, LISISII, "space"}
    assert production.producers(state, registry, "p1", HOME)[0].value == 5


@ruling("F_saar/floating-factory/3")
def test_dok_nie_jest_statkiem_w_walce(registry: StaticDataRegistry) -> None:
    """Dok nie jest celem trafień (Space Cannon, walka): nie jest statkiem."""
    from src.core.battle import combat_units

    state = _state()
    units = combat_units(state, grid_from_state(state, registry), registry, kind="space",
                         position=HOME, planet=None, player_id="p1")
    assert {u.base_type for u in units} == {"carrier"}


@ruling("F_saar/floating-factory/9", "F_saar/floating-factory/9.1")
def test_construction_dok_w_przestrzeni_systemu_planety(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[PLAIN].planet_owners = {VEFUTII: "p1"}
    state.players["p1"].controlled_planets.append(VEFUTII)
    place_structure(state, "p1", VEFUTII, "spacedock")
    assert state.systems[PLAIN].space_units["p1"] == {"spacedock": 1}
    state.planet_attachments[VEFUTII] = ["dmz"]
    with pytest.raises(ValueError):
        place_structure(state, "p1", VEFUTII, "spacedock")


@ruling("F_saar/floating-factory/12")
def test_dok_nie_liczy_sie_do_struktur_poza_domem(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[PLAIN].planet_owners = {VEFUTII: "p1"}
    state.systems[PLAIN].space_units = {"p1": {"spacedock": 1}}
    state.players["p1"].controlled_planets.append(VEFUTII)
    grid = grid_from_state(state, registry)
    assert progress(state, registry, grid, "p1", "infrastructure") == 0


@ruling("technologies:ffac2#1", "technologies:ffac2#2", "technologies:ffac2#3",
        "technologies:ffac2#4")
def test_floating_factory_2_dane_i_ruch(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "saar", ["ffac2"], "spacedock")
    assert unit is not None and unit.id == "saar_spacedock2"
    assert (unit.move_value, unit.capacity_value, unit.production_value) == (2, 5, 7)
    state = _state()
    state.players["p1"].technologies = ["ffac2"]
    assert floating_structures.floats(state, "p1", "spacedock")
    state = _activate(state, registry, RIVAL)
    after = movement.move_fleet(state, grid_from_state(state, registry), registry, HOME,
                                {"spacedock": 1}, {}, "p1", route=[HOME, PLAIN, RIVAL])
    assert after.systems[RIVAL].space_units["p1"]["spacedock"] == 1


# ============================================================================ Scavenge


def _invasion(state: GameState, position: str) -> None:
    state.invasion = InvasionState(position=position, attacker="p1",
                                   phase=InvasionPhase.ESTABLISH)


@ruling("abilities:scavenge#1", "F_saar/scavenge/1")
def test_scavenge_tg_za_kazda_planete(registry: StaticDataRegistry) -> None:
    from src.core import control

    state = _state()
    state.players["p1"].trade_goods = 0
    control.set_planet_control(state, RIVAL, THIBAH, "p1", registry)
    assert state.players["p1"].trade_goods == 1


@ruling("F_saar/scavenge/2", "F_saar/scavenge/2.1")
def test_scavenge_po_eksploracji_planety_niczyjej(registry: StaticDataRegistry) -> None:
    from src.core import control

    state = _state()
    state.players["p1"].trade_goods = 0
    _invasion(state, PLAIN)
    control.set_planet_control(state, PLAIN, VEFUTII, "p1", registry)
    assert state.players["p1"].trade_goods == 0  # najpierw eksploracja
    triggers.fire(state, GameEvent.PLANET_EXPLORED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "planet": VEFUTII})
    assert state.players["p1"].trade_goods == 1


# ============================================================================= Nomadic


@ruling("abilities:nomadic#1")
def test_nomadic_cele_bez_planet_domowych(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[HOME].planet_owners = {RAGH: "p2", LISISII: "p2"}
    assert objectives.controls_home_planets(state, registry, "p1")
    rival = _state()
    rival.systems[FAR].planet_owners = {}
    rival.players["p2"].faction = "sol"
    assert not objectives.controls_home_planets(rival, registry, "p2")


# ======================================================================= Chaos Mapping


@ruling("technologies:cm#1", "F_saar/chaos-mapping/5")
def test_chaos_mapping_blokuje_aktywacje_pola_asteroid(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["cm"]
    state.systems[ASTEROID].space_units = {"p1": {"cruiser": 1}}
    with pytest.raises(ValueError, match="prevents"):
        _activate(state, registry, ASTEROID, pid="p2")
    # Sam Saar może; same jednostki niebędące statkami nie blokują (dok pływający).
    _activate(_state(), registry, ASTEROID)
    docks = _state()
    docks.players["p1"].technologies = ["cm"]
    docks.systems[ASTEROID].space_units = {"p1": {"spacedock": 1}}
    after = _activate(docks, registry, ASTEROID, pid="p2")
    assert after.active_system == ASTEROID


@ruling("F_saar/chaos-mapping/4")
def test_chaos_mapping_nie_chroni_przed_kartami(registry: StaticDataRegistry) -> None:
    """Zdolność zabrania tylko AKTYWACJI - jednostki w polu asteroid pozostają celem efektów."""
    state = _state()
    state.players["p1"].technologies = ["cm"]
    state.systems[ASTEROID].space_units = {"p1": {"cruiser": 1}}
    assert not rules_hooks.permits(rules_hooks.POINT_TACTICAL_ACTIVATION_BLOCKED, state, "p1",
                                   {"activator": "p2", "position": PLAIN})


@ruling("technologies:cm#2", "F_saar/chaos-mapping/1", "F_saar/chaos-mapping/3")
def test_chaos_mapping_produkcja_na_starcie_tury(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["cm"]
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    after = _accept(state, "p1", "Chaos Mapping", {"position": HOME})
    grant = after.production_grant
    assert grant is not None and grant.units == 1 and grant.position == HOME
    assert "cm" not in after.players["p1"].exhausted_technologies  # bez wyczerpania


@ruling("F_saar/chaos-mapping/3.1", "F_saar/chaos-mapping/2")
def test_chaos_mapping_w_turze_pasu_i_ruch_po_produkcji(registry: StaticDataRegistry) -> None:
    """Oferta zależy tylko od startu tury (także tej, w której gracz spasuje); wyprodukowana
    jednostka stoi na planszy jak każda inna (może ruszyć w akcji taktycznej tej tury)."""
    state = _state()
    state.players["p1"].technologies = ["cm"]
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    assert _offers(state, "p1", "Chaos Mapping")
    state = _state()
    state.systems[HOME].space_units["p1"]["cruiser"] = 1  # jednostka z Chaos Mapping
    after = _activate(state, registry, PLAIN)
    moved = movement.move_fleet(after, grid_from_state(after, registry), registry, HOME,
                                {"cruiser": 1}, {}, "p1")
    assert moved.systems[PLAIN].space_units["p1"] == {"cruiser": 1}


# ===================================================================== Captain Mendosa


def _mendosa_state() -> GameState:
    """p2 aktywuje 102; jego niszczyciel (ruch 2) w 104, war sun Muaat... ruch 3 - krążownik
    Saar II? Najwyższy ruch na planszy daje statek p1 (Floating Factory się nie liczy)."""
    state = _state()
    state.players["p1"].leader_states = {"saaragent": "unlocked"}
    state.players["p1"].technologies = ["cr2"]  # Cruiser II: ruch 3
    state.systems[HOME].space_units = {"p1": {"cruiser": 1, "spacedock": 1}}
    state.systems[RIVAL].space_units = {"p2": {"dreadnought": 1}}
    return state


@ruling("leaders:saaragent#1", "F_saar/captain-mendosa/1", "F_saar/captain-mendosa/2")
def test_mendosa_podnosi_ruch_jednego_statku(registry: StaticDataRegistry) -> None:
    state = _activate(_mendosa_state(), registry, FAR, pid="p2")
    offer = _offers(state, "p1", "Captain Mendosa")[0]
    ship = saar.mendosa_inputs(state, registry, "p1", offer.ctx)[0]["options"][0]["value"]
    assert ship == f"{RIVAL}|dreadnought"
    state = _accept(state, "p1", "Captain Mendosa", {"ship": ship})
    assert state.players["p1"].leader_states["saaragent"] == "exhausted"
    grid = grid_from_state(state, registry)
    # Pancernik (ruch 1) leci o 3 systemy: 103 -> 102 -> 101 ... -> 105 przez Mecatol = 2.
    after = movement.move_fleet(state, grid, registry, RIVAL, {"dreadnought": 1}, {}, "p2",
                                route=[RIVAL, "000", FAR])
    assert after.systems[FAR].space_units["p2"] == {"dreadnought": 1}


@ruling("F_saar/captain-mendosa/2.1", "F_saar/captain-mendosa/2.2")
def test_mendosa_wartosc_bez_premii_po_aktywacji(registry: StaticDataRegistry) -> None:
    state = _mendosa_state()
    state.players["p1"].technologies = ["cr2", "gd"]  # Gravity Drive nie wchodzi do wartości
    assert saar.highest_move_value(state, registry) == 3


@ruling("F_saar/captain-mendosa/3")
def test_mendosa_nadpisuje_mglawice(registry: StaticDataRegistry) -> None:
    state = _mendosa_state()
    state.systems["106"] = SystemState(position="106", system_id="42")  # mgławica
    state.systems["106"].space_units = {"p2": {"carrier": 1}}
    state = _activate(state, registry, PLAIN, pid="p2")
    state = _accept(state, "p1", "Captain Mendosa", {"ship": "106|carrier"})
    grid = grid_from_state(state, registry)
    value = movement._effective_move_value(state, grid, registry, "106", "carrier", "p2",
                                           boost=False, tempesta=False)
    assert value == 3


def test_mendosa_tylko_jeden_statek(registry: StaticDataRegistry) -> None:
    state = _mendosa_state()
    state.systems[RIVAL].space_units = {"p2": {"dreadnought": 2}}
    state = _activate(state, registry, FAR, pid="p2")
    state = _accept(state, "p1", "Captain Mendosa", {"ship": f"{RIVAL}|dreadnought"})
    grid = grid_from_state(state, registry)
    with pytest.raises(ValueError, match="only 1 ship"):
        movement.move_fleet(state, grid, registry, RIVAL, {"dreadnought": 2}, {}, "p2",
                            route=[RIVAL, "000", FAR])
    after = movement.move_fleet(state, grid, registry, RIVAL, {"dreadnought": 1}, {}, "p2",
                                route=[RIVAL, "000", FAR])
    with pytest.raises(ValueError):  # premia zużyta - drugi pancernik już nie doleci
        movement.move_fleet(after, grid, registry, RIVAL, {"dreadnought": 1}, {}, "p2",
                            route=[RIVAL, "000", FAR])


# ===================================================================== Rowl Sarrig


@ruling("leaders:saarcommander#unlock")
def test_rowl_sarrig_odblokowanie_3_doki(registry: StaticDataRegistry) -> None:
    from src.core import leaders

    unlock = leaders.unlock_predicate(registry, "saarcommander")
    assert unlock is not None
    state = _state()
    state.systems[PLAIN].space_units = {"p1": {"spacedock": 1}}
    assert not unlock(state, registry, "p1")
    state.systems[FAR].space_units = {"p1": {"spacedock": 1}}
    assert unlock(state, registry, "p1")


@ruling("leaders:saarcommander#1")
def test_rowl_sarrig_mysliwce_do_innego_doku(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"saarcommander": "unlocked"}
    state.systems[HOME].space_units["p1"]["fighter"] = 2
    state.systems[PLAIN].space_units = {"p1": {"spacedock": 1, "carrier": 1}}
    state.systems[RIVAL].space_units = {"p1": {"spacedock": 1}, "p2": {"cruiser": 1}}
    triggers.fire(state, GameEvent.UNITS_PRODUCED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": HOME, "units": {"fighter": 2},
                       "zones": {"space": {"fighter": 2}}})
    offer = _offers(state, "p1", "Rowl Sarrig")[0]
    inputs = saar.rowl_inputs(state, registry, "p1", offer.ctx)
    dests = {o["meta"]["move"]["to"] for o in inputs[0]["options"]}
    assert dests == {PLAIN}  # dok w 103 jest zablokowany
    after = _accept(state, "p1", "Rowl Sarrig", {"moves": [f"space|fighter|0>{PLAIN}"]})
    assert after.systems[PLAIN].space_units["p1"]["fighter"] == 1
    assert after.systems[HOME].space_units["p1"]["fighter"] == 1


@ruling("F_saar/rowl-sarring/1")
def test_rowl_sarrig_nie_omija_blokady_produkcji(registry: StaticDataRegistry) -> None:
    """Commander przenosi tylko już wyprodukowane jednostki - produkcja w zablokowanym doku
    rządzi się zwykłymi regułami (statków nie wolno)."""
    state = _state()
    state.systems[HOME].space_units["p2"] = {"cruiser": 1}
    state.systems[HOME].space_units["p1"] = {"spacedock": 1}
    assert production.is_blockaded(state, "p1", HOME)


# =========================================================== Gurno Aggero (hero)


@ruling("leaders:saarhero#1", "leaders:saarhero#2", "leaders:saarhero#3",
        "F_saar/gurno-aggero-armageddon-relay/1")
def test_armageddon_relay(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"saarhero": "unlocked"}
    state.systems[PLAIN].space_units = {"p2": {"fighter": 2, "cruiser": 1, "infantry": 1}}
    state.systems[PLAIN].planet_units = {VEFUTII: {"p2": {"infantry": 2, "mech": 1}}}
    assert HOME not in saar.armageddon_systems(state, "p1")  # dok nie sąsiaduje ze swoim
    after = _play(state, registry, "leader", "saarhero", {"position": PLAIN})
    system = after.systems[PLAIN]
    assert system.space_units["p2"] == {"cruiser": 1}
    assert system.planet_units[VEFUTII]["p2"] == {"mech": 1}
    assert after.players["p1"].leader_states["saarhero"] == "purged"


@ruling("leaders:saarhero#unlock")
def test_bohater_odblokowanie_3_cele(registry: StaticDataRegistry) -> None:
    from src.core import leaders

    unlock = leaders.unlock_predicate(registry, "saarhero")
    assert unlock is not None
    state = _state()
    assert not unlock(state, registry, "p1")


# ======================================================== Scavenger Zeta (mech)


@ruling("units:saar_mech#1", "F_saar/scavenger-zeta/1", "F_saar/scavenger-zeta/3")
def test_scavenger_zeta_deploy_za_tg_ze_scavenge(registry: StaticDataRegistry) -> None:
    from src.core import control

    state = _state()
    state.players["p1"].trade_goods = 0
    state.systems[RIVAL].planet_units = {THIBAH: {"p1": {"infantry": 1}}}
    control.set_planet_control(state, RIVAL, THIBAH, "p1", registry)
    assert state.players["p1"].trade_goods == 1  # Scavenge opłaca DEPLOY
    after = _accept(state, "p1", "Scavenger Zeta")
    assert after.systems[RIVAL].planet_units[THIBAH]["p1"] == {"infantry": 1, "mech": 1}
    assert after.players["p1"].trade_goods == 0


@ruling("F_saar/scavenger-zeta/2")
def test_scavenger_zeta_po_eksploracji(registry: StaticDataRegistry) -> None:
    from src.core import control

    state = _state()
    state.players["p1"].trade_goods = 2
    _invasion(state, PLAIN)
    control.set_planet_control(state, PLAIN, VEFUTII, "p1", registry)
    assert not _offers(state, "p1", "Scavenger Zeta")
    triggers.fire(state, GameEvent.PLANET_EXPLORED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "planet": VEFUTII})
    assert _offers(state, "p1", "Scavenger Zeta")


# ======================================================================= Ragh's Call


def _ragh_state() -> GameState:
    """p2 ląduje na Thibah, którą trzyma Saar (piechota + uszkodzony mech)."""
    state = _state()
    state.systems[RIVAL].planet_owners = {THIBAH: "p1"}
    state.players["p1"].controlled_planets.append(THIBAH)
    state.players["p2"].controlled_planets = []
    state.systems[RIVAL].planet_units = {
        THIBAH: {"p1": {"infantry": 2, "mech": 1}, "p2": {"infantry": 3}},
    }
    state.systems[RIVAL].damaged_units = {THIBAH: {"p1": {"mech": 1}}}
    state.invasion = InvasionState(position=RIVAL, attacker="p2", phase=InvasionPhase.COMMIT,
                                   last_commit={THIBAH: {"infantry": 3}})
    state.active_player_id = "p2"
    state.active_system = RIVAL
    state.players["p2"].private.promissory_notes = ["ragh"]
    return state


@ruling("promissory_notes:ragh#1", "promissory_notes:ragh#2", "F_saar/raghs-call/1",
        "F_saar/raghs-call/3", "F_saar/raghs-call/4")
def test_raghs_call_zabiera_sily_saar(registry: StaticDataRegistry) -> None:
    state = _ragh_state()
    after, _ = promissory_play.play(state, registry, "p2", "ragh",
                                    {"planet": THIBAH, "destination": RAGH})
    assert after.systems[RIVAL].planet_units[THIBAH].get("p1", {}) == {}
    assert after.systems[HOME].planet_units[RAGH]["p1"] == {"infantry": 2, "mech": 1}
    assert after.systems[HOME].damaged_units[RAGH]["p1"] == {"mech": 1}
    assert "ragh" in after.players["p1"].private.promissory_notes  # wraca do Saar


@ruling("F_saar/raghs-call/2")
def test_raghs_call_pds_zostaje(registry: StaticDataRegistry) -> None:
    state = _ragh_state()
    state.systems[RIVAL].planet_units[THIBAH]["p1"]["pds"] = 1
    after, _ = promissory_play.play(state, registry, "p2", "ragh",
                                    {"planet": THIBAH, "destination": RAGH})
    assert after.systems[RIVAL].planet_units[THIBAH]["p1"] == {"pds": 1}


# ==================================================================== Deorbit Barrage


def _deorbit_state() -> GameState:
    """Statek Saar w polu asteroid 104; cel: Thibah (103, odległość 1) z siłami p2."""
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.players["p1"].trade_goods = 6
    state.systems[ASTEROID].space_units = {"p1": {"cruiser": 1}}
    state.systems[RIVAL].planet_units = {THIBAH: {"p2": {"infantry": 3, "mech": 1}}}
    state.rng_seed = 3
    return state


@ruling("breakthroughs:saarbt#1", "breakthroughs:saarbt#2", "F_saar/deorbit-barrage/1",
        "F_saar/deorbit-barrage/2", "F_saar/deorbit-barrage/3.1")
def test_deorbit_barrage_saar_przypisuje_trafienia(registry: StaticDataRegistry) -> None:
    state = _deorbit_state()
    assert THIBAH in saar.deorbit_planets(state, "p1")
    after = _play(state, registry, "breakthrough", "saarbt",
                  {"planet": THIBAH, "planets": [], "trade_goods": 6})
    assert after.players["p1"].trade_goods == 0
    assert after.players["p1"].breakthrough_exhausted
    offers = _offers(after, "p1", "Deorbit Barrage: assign hits")
    assert offers, "ziarno 3 daje trafienia"
    hits = len(saar.deorbit_assign_inputs(after, registry, "p1", offers[0].ctx))
    assert 0 < hits <= 6
    params = {f"hit{i + 1}": "p2|infantry" for i in range(hits)}
    done = _accept(after, "p1", "Deorbit Barrage: assign hits", params)
    left = done.systems[RIVAL].planet_units[THIBAH]["p2"].get("infantry", 0)
    assert left == max(0, 3 - hits)


@ruling("F_saar/deorbit-barrage/3")
def test_deorbit_barrage_sustain_damage_wlasciciela(registry: StaticDataRegistry) -> None:
    state = _deorbit_state()
    state.active_effects = []
    from src.core import active_effects
    from src.core.game_events import Duration

    active_effects.add_effect(state, saar.DEORBIT_KEY, Duration.TURN, owner="p1",
                              data={"planet": THIBAH, "hits": 2})
    faction_components.ability_used(state, "p1", saar.DEORBIT_ASSIGN, "p1")
    state = _accept(state, "p1", "Deorbit Barrage: assign hits",
                    {"hit1": "p2|mech", "hit2": "p2|mech"})
    offer = _offers(state, "p2", "SUSTAIN DAMAGE")[0]
    inputs = saar.deorbit_sustain_inputs(state, registry, "p2", offer.ctx)
    assert inputs[0]["max"] == 1  # 1 nieuszkodzony mech
    after = _accept(state, "p2", "SUSTAIN DAMAGE", {"mech": 1})
    # 1 trafienie anulowane Sustain Damage, drugie niszczy (już uszkodzonego) mecha.
    assert after.systems[RIVAL].planet_units[THIBAH]["p2"].get("mech", 0) == 0


def test_deorbit_barrage_poza_zasiegiem(registry: StaticDataRegistry) -> None:
    state = _deorbit_state()
    state.systems[ASTEROID].space_units = {}
    reason = faction_components.block_reason(state, registry, "p1", "breakthrough", "saarbt")
    assert reason is not None and "asteroid" in reason


# ============================================================ rulingi krzyżowe (C_technology)


@ruling("C_technology/dark-energy-tap/5")
def test_dok_nie_bada_zetonu_frontier(registry: StaticDataRegistry) -> None:
    from src.core.exploration_frontier import can_explore_frontier

    state = _state()
    state.systems[PLAIN].frontier_token = True
    state.systems[PLAIN].space_units = {"p1": {"spacedock": 1}}
    assert not can_explore_frontier(state, "p1", PLAIN)
    state.systems[PLAIN].space_units["p1"]["destroyer"] = 1  # statek z kroku Production
    assert can_explore_frontier(state, "p1", PLAIN)


@ruling("C_technology/magen-defense-grid-omega-omega/6.1")
def test_magen_piechota_przy_doku_w_przestrzeni(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["md"]  # Magen Defense Grid ΩΩ
    state.systems[HOME].planet_units = {RAGH: {"p1": {"pds": 1}}}
    after = _activate(state, registry, HOME, pid="p2")
    assert after.systems[HOME].space_units["p1"]["infantry"] == 1  # przy Floating Factory
    assert after.systems[HOME].planet_units[RAGH]["p1"]["infantry"] == 1  # przy PDS
