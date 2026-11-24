"""The L1Z1X Mindnet — komplet komponentów frakcji (RULES.md 62.12) i rulingi F_lizix.

Scenariusze przez prawdziwe API (oferty, notka, ACTION): ``test_flows_l1z1x.py``. Statusy bez
testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    battle,
    combat_bombardment,
    control,
    invasion,
    leaders,
    production,
    rules_hooks,
    technology,
    triggers,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    InvasionPhase,
    InvasionState,
    Phase,
    PlayerState,
    StatusPhaseState,
    StatusStep,
    SystemState,
)
from src.core.hooks import reactions_combat, reactions_tactical
from src.core.hooks.factions import l1z1x
from src.core.reaction_cards import open_windows
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from tests.factions.completeness import missing_components
from tests.rulings import ruling

# Pozycje: 101-103 kolejne systemy pierścienia 1, 000 = Mecatol. Planety z kafli 19-22.
WELLON, VEFUTII, THIBAH, TARMANN = "wellon", "vefutii", "thibah", "tarmann"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _state() -> GameState:
    """p1 = L1Z1X (aktywny), p2 = Sol. 101 = Vefutii (p1), 102 = Thibah (p2), 103 = Tarmann."""
    p1 = PlayerState(player_id="p1", color="black", faction="l1z1x")
    p2 = PlayerState(player_id="p2", color="blue", faction="sol")
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            "101": SystemState(position="101", system_id="20", planet_owners={VEFUTII: "p1"}),
            "102": SystemState(position="102", system_id="21", planet_owners={THIBAH: "p2"}),
            "103": SystemState(position="103", system_id="22"),
        },
    )
    state.players["p1"].controlled_planets = [VEFUTII]
    state.players["p2"].controlled_planets = [THIBAH]
    for p in state.players.values():
        p.cc_reinf = 8
    return state


def test_l1z1x_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "l1z1x") == []


# ============================================================================== Assimilate


def _capture(state: GameState, registry: StaticDataRegistry, planet: str = THIBAH) -> None:
    control.set_planet_control(state, "102", planet, "p1", registry)


@ruling("abilities:assimilate#1", "F_lizix/assimilate/3")
def test_assimilate_wymienia_pds_i_dok(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].planet_units = {THIBAH: {"p2": {"pds": 2, "spacedock": 1}}}
    _capture(state, registry)
    units = state.systems["102"].planet_units[THIBAH]
    assert units.get("p1") == {"pds": 2, "spacedock": 1}
    assert not any(units.get("p2", {}).values())


def test_inwazja_l1z1x_nie_niszczy_struktur_przed_wymiana(registry: StaticDataRegistry) -> None:
    """R_invasion niszczy cudze struktury przy przejęciu - przy L1Z1X wymienia je Assimilate."""
    state = _state()
    system = state.systems["102"]
    system.planet_units = {THIBAH: {"p1": {"infantry": 1}, "p2": {"pds": 1}}}
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.ESTABLISH,
                                   committed={THIBAH: {"infantry": 1}})
    invasion._establish_control(state, registry)
    assert system.planet_units[THIBAH]["p1"] == {"infantry": 1, "pds": 1}
    # Inny gracz przejmujący planetę: struktury giną jak dotąd.
    other = _state()
    other.active_player_id = "p2"
    other.systems["101"].planet_units = {VEFUTII: {"p2": {"infantry": 1}, "p1": {"pds": 1}}}
    other.invasion = InvasionState(position="101", attacker="p2", phase=InvasionPhase.ESTABLISH,
                                   committed={VEFUTII: {"infantry": 1}})
    invasion._establish_control(other, registry)
    assert not other.systems["101"].planet_units[VEFUTII].get("p1", {}).get("pds")


@ruling("F_lizix/assimilate/1")
def test_przejety_dok_produkuje_w_tej_akcji(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].planet_units = {THIBAH: {"p2": {"spacedock": 1}}}
    _capture(state, registry)
    found = production.producers(state, registry, "p1", "102")
    assert any(p.base_type == "spacedock" for p in found)


@ruling("F_lizix/assimilate/2")
def test_infiltrate_po_assimilate_nic_nie_wymienia(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].planet_units = {THIBAH: {"p2": {"pds": 1}}}
    _capture(state, registry)
    assert reactions_tactical._infiltrate_targets(state, "p1", THIBAH) == []


def _full_pds(state: GameState, *, token: bool) -> None:
    """Wszystkie 6 PDS L1Z1X na planszy: Vefutii (101) - z żetonem L1Z1X albo bez."""
    state.systems["101"].planet_units = {VEFUTII: {"p1": {"pds": 6}}}
    state.systems["101"].command_tokens = ["p1"] if token else []


@ruling("F_lizix/assimilate/3")
def test_pusta_rezerwa_struktura_z_planszy(registry: StaticDataRegistry) -> None:
    state = _state()
    _full_pds(state, token=False)
    state.systems["102"].planet_units = {THIBAH: {"p2": {"pds": 1}}}
    ctx: dict[str, Any] = {"player": "p1", "planet": THIBAH, "position": "102"}
    inputs = l1z1x.assimilate_inputs(state, registry, "p1", ctx)
    assert [i["key"] for i in inputs] == ["sources:pds"]
    assert [o["value"] for o in inputs[0]["options"]] == [f"101|{VEFUTII}"]
    l1z1x.assimilate(state, "p1", {**ctx, "params": {"sources:pds": [f"101|{VEFUTII}"]}})
    assert state.systems["101"].planet_units[VEFUTII]["p1"]["pds"] == 5
    assert state.systems["102"].planet_units[THIBAH]["p1"] == {"pds": 1}


@ruling("F_lizix/assimilate/3")
def test_pusta_rezerwa_bez_wymiany_struktura_ginie(registry: StaticDataRegistry) -> None:
    """Rezerwa pusta, a PDS na planszy tylko w systemie z żetonem L1Z1X - wymiana niewymuszona,
    cudzy PDS ginie (zwykła reguła przejęcia)."""
    state = _state()
    _full_pds(state, token=True)
    state.systems["102"].planet_units = {THIBAH: {"p2": {"pds": 1}}}
    _capture(state, registry)
    assert state.pending_offers == []
    units = state.systems["102"].planet_units[THIBAH]
    assert not units.get("p1", {}).get("pds") and not units.get("p2", {}).get("pds")


# ================================================================================== Harrow


def _harrow_state(*, defenders: int = 2) -> GameState:
    """Walka naziemna na Thibah (102): L1Z1X atakuje, pancernik L1Z1X w przestrzeni."""
    state = _state()
    system = state.systems["102"]
    system.space_units = {"p1": {"dreadnought": 1}}
    system.planet_units = {THIBAH: {"p1": {"infantry": 1}, "p2": {"infantry": defenders}}}
    state.active_system = "102"
    state.invasion = InvasionState(position="102", attacker="p1",
                                   phase=InvasionPhase.GROUND_COMBAT)
    state.active_combat = ActiveCombat(kind="ground", position="102", planet=THIBAH,
                                       attacker="p1", defender="p2", step=CombatStep.ASSIGN)
    state.rng_seed = 5
    return state


_END = {"kind": "ground", "phase": "combat", "player": "p1"}


@ruling("abilities:harrow#1", "F_lizix/harrow/4")
def test_harrow_bombarduje_po_rundzie(registry: StaticDataRegistry) -> None:
    state = _harrow_state()
    state.systems["102"].space_units["p1"]["warsun"] = 1
    state.players["p1"].technologies = ["ws"]
    assert l1z1x._harrow_ready(state, "p1", _END)
    groups = {g.base_type: g.total_dice for g in combat_bombardment.groups(state, registry, "p1")}
    assert groups == {"dreadnought": 1, "warsun": 3}  # każda jednostka z Bombardment w systemie
    l1z1x.harrow(state, "p1", {**_END, "params": {}})
    combat = state.active_combat
    assert combat is not None
    # Rzut w dzienniku walki (okno walki naziemnej animuje go jak salwę z orbity), bez stołu.
    entry = combat.log[-1]
    assert entry["phase"] == "BOMBARDMENT" and entry["label"] == "Harrow"
    assert sum(len(r["dice"]) for r in entry["rolls"]["p1"]) == 4
    assert state.table_roll is None
    assert combat.round_end_hits.get("p2", 0) == entry["hits"]["p1"]


@ruling("F_lizix/harrow/1", "leaders:l1z1xcommander#1", "F_lizix/2ram/1.1")
def test_harrow_tarcza_blokuje_chyba_ze_2ram(registry: StaticDataRegistry) -> None:
    state = _harrow_state()
    state.systems["102"].planet_units[THIBAH]["p2"]["pds"] = 1
    assert not l1z1x._harrow_ready(state, "p1", _END)
    state.players["p1"].leader_states["l1z1xcommander"] = "unlocked"
    assert l1z1x._harrow_ready(state, "p1", _END)
    # 2RAM nie odbiera tarczy - PDS nadal ją ma (Magen Defense Grid działa).
    present, active = invasion.planet_shield(state, registry, "102", THIBAH, exclude="p1")
    assert present and active


@ruling("F_lizix/harrow/2", "F_norr/ghom-sekkus/9.1")
def test_harrow_tylko_jako_aktywny_gracz(registry: StaticDataRegistry) -> None:
    state = _harrow_state()
    state.active_player_id = "p2"
    assert not l1z1x._harrow_ready(state, "p1", _END)


@ruling("F_lizix/harrow/3")
def test_harrow_po_rundzie_bez_wlasnych_sil(registry: StaticDataRegistry) -> None:
    state = _harrow_state()
    del state.systems["102"].planet_units[THIBAH]["p1"]
    assert l1z1x._harrow_ready(state, "p1", _END)


def test_harrow_nie_po_afb_i_bez_celu(registry: StaticDataRegistry) -> None:
    state = _harrow_state()
    assert not l1z1x._harrow_ready(state, "p1", {**_END, "phase": "afb"})
    state.systems["102"].planet_units[THIBAH]["p2"] = {}
    assert not l1z1x._harrow_ready(state, "p1", _END)


@ruling("F_lizix/harrow/4.1", "F_lizix/annihilator/1", "units:l1z1x_mech#1")
def test_annihilator_spoza_walki_bombarduje_w_harrow(registry: StaticDataRegistry) -> None:
    state = _harrow_state()
    state.systems["102"].planet_units[THIBAH]["p1"]["mech"] = 1  # walczy - nie strzela
    assert {g.base_type for g in combat_bombardment.groups(state, registry, "p1")} == {
        "dreadnought"
    }
    state.systems["102"].space_units["p1"]["mech"] = 1  # w przestrzeni - nie walczy
    groups = {g.base_type: g.count for g in combat_bombardment.groups(state, registry, "p1")}
    assert groups == {"dreadnought": 1, "mech": 1}


@ruling("F_lizix/harrow/5")
def test_harrow_x89_wyczerpuje_planete(registry: StaticDataRegistry) -> None:
    state = _harrow_state()
    state.players["p1"].technologies = ["x89c4"]
    l1z1x.harrow(state, "p1", {**_END, "params": {}})
    assert THIBAH in state.players["p2"].exhausted_planets


def test_harrow_okno_ambuscade_przed_rzutem(registry: StaticDataRegistry) -> None:
    """Oferta Harrow czeka = okno „when … units make a roll for a unit ability” dla L1Z1X."""
    from src.core.game_state import PendingOffer

    state = _harrow_state()

    def ability_windows() -> list[Any]:
        return [w for w in open_windows(state) if w.ctx.get("ability") == "bombardment"]

    assert ability_windows() == []
    state.pending_offers = [PendingOffer(id="o1", player_id="p1", event="combat.round",
                                         moment="end", hook_seq=0, label="Harrow")]
    assert [w.ctx["player"] for w in ability_windows()] == ["p1"]


@ruling("F_sol/evelyn-delouis/1.1")
def test_harrow_bez_kosci_evelyn(registry: StaticDataRegistry) -> None:
    """Agent Sol daje kość tylko w rzutach walki - Harrow (Bombardment) jej nie dostaje."""
    from src.core import active_effects
    from src.core.game_events import Duration

    state = _harrow_state()
    effect = active_effects.add_effect(state, "leaders:solagent:die", Duration.COMBAT, owner="p1")
    effect.data = {"unit": "p1|infantry"}
    assert combat_bombardment.extra_sources(state, "p1") == []


# ===================================================================== Inheritance Systems


def _tech_state(registry: StaticDataRegistry) -> tuple[GameState, str]:
    """p1 z Inheritance Systems; technologia z 2 prerekwizytami, których p1 nie ma."""
    state = _state()
    state.players["p1"].technologies = ["is"]
    state.players["p1"].trade_goods = 3
    tech = next(
        t for t in technology.tech_pool(state, registry, "p1").values()
        if sum(technology.prerequisites(t).values()) >= 2 and t.types
    )
    return state, tech.id


@ruling("technologies:is#1", "technologies:is#2", "F_lizix/inheritance-systems/1.1")
def test_inheritance_ignoruje_wszystkie_prerekwizyty_za_osobne_2(
    registry: StaticDataRegistry,
) -> None:
    state, tech = _tech_state(registry)
    with pytest.raises(ValueError, match="Prerequisites"):
        technology.plan_research(state, registry, "p1", tech, [])
    with pytest.raises(ValueError, match="Spend 2"):
        technology.plan_research(state, registry, "p1", tech, ["paid:is||1"])
    plan = technology.plan_research(state, registry, "p1", tech, ["paid:is|vefutii|0"])
    assert plan.paid_ignore == ("is", ("vefutii",), 0)
    # Planeta osobnej zapłaty nie płaci już kosztu badania (pula oddzielna - F_lizix).
    with pytest.raises(ValueError, match="cannot also pay"):
        technology.pay_research(state, registry, "p1", 4, ["vefutii"], 2,
                                skip_planets=plan.reserved_planets)
    technology.apply_research(state, "p1", plan)
    p1 = state.players["p1"]
    assert tech in p1.technologies
    assert "is" in p1.exhausted_technologies and "vefutii" in p1.exhausted_planets
    # Wyczerpana karta - przy kolejnym badaniu już nie działa.
    other = next(
        t.id for t in technology.tech_pool(state, registry, "p1").values()
        if t.id not in p1.technologies and sum(technology.prerequisites(t).values()) >= 2
    )
    with pytest.raises(ValueError, match="cannot ignore"):
        technology.plan_research(state, registry, "p1", other, ["paid:is||2"])


def test_inheritance_w_drzewie_i_widoku(registry: StaticDataRegistry) -> None:
    from src.core.strategy_cards.technology import research_view

    state, tech = _tech_state(registry)
    row = next(r for r in technology.tree_view(state, registry, "p1") if r["id"] == tech)
    assert row["status"] == "skippable"
    view = research_view(state, registry, "p1", 0)
    assert view["paid_skips"] == [{"card": "is", "name": "Inheritance Systems", "cost": 2}]


# ===================================================================== Super Dreadnought II


@ruling("technologies:sdn2#1", "technologies:sdn2#2", "technologies:sdn2#3")
def test_super_dreadnought_ii(registry: StaticDataRegistry) -> None:
    unit = resolve_unit_variant(registry, "l1z1x", ["sdn2"], "dreadnought")
    assert unit is not None and unit.id == "l1z1x_dreadnought2"
    assert (unit.cost, unit.combat_hits_on, unit.move_value, unit.capacity_value) == (4, 4, 2, 2)
    assert unit.sustain_damage and unit.bombard_hits_on == 4
    state = _state()
    state.players["p1"].technologies = ["sdn2"]
    assert reactions_combat._direct_hit_immune(state, "p1", "dreadnought")
    state.players["p1"].technologies = []
    assert not reactions_combat._direct_hit_immune(state, "p1", "dreadnought")


# ================================================================================ [0.0.1]


def _space_combat(registry: StaticDataRegistry, *, flagship: bool) -> GameState:
    state = _state()
    mine = {"dreadnought": 1, "carrier": 1}
    if flagship:
        mine["flagship"] = 1
    state.systems["103"].space_units = {"p1": mine, "p2": {"cruiser": 1, "fighter": 3}}
    state.active_system = "103"
    state.active_combat = ActiveCombat(kind="space", position="103", attacker="p1",
                                       defender="p2", step=CombatStep.ASSIGN)
    state.active_combat.rolls = {"p1": [
        {"baseType": "flagship", "name": "[0.0.1]", "hits": 1},
        {"baseType": "dreadnought", "name": "Super Dreadnought I", "hits": 1},
        {"baseType": "carrier", "name": "Carrier I", "hits": 1},
    ], "p2": []}
    state.active_combat.pending_hits = {"p2": 3}
    return state


@ruling("units:l1z1x_flagship#1")
def test_flagowiec_kieruje_trafienia_na_statki_niemysliwskie(
    registry: StaticDataRegistry,
) -> None:
    state = _space_combat(registry, flagship=True)
    grid = grid_from_state(state, registry)
    combat = state.active_combat
    assert combat is not None
    battle._direct_hits_to_non_fighters(state, grid, registry, combat)
    target = combat.hit_targets["p2"]
    assert target["types"] == ["cruiser"] and target["count"] == 2  # flagowiec + pancernik
    units = {u.base_type: u for u in battle.side_units(state, grid, registry, "p2")}
    with pytest.raises(ValueError, match="Assign 1 hit"):
        # „if able”: tylko 1 krążownik może przyjąć trafienie, więc wymagane jest 1.
        battle._check_hit_targets(combat, "p2", units, ({}, {"fighter": 3}, {}), 3)
    battle._check_hit_targets(combat, "p2", units, ({}, {"fighter": 2, "cruiser": 1}, {}), 3)


def test_bez_flagowca_trafienia_dowolnie(registry: StaticDataRegistry) -> None:
    state = _space_combat(registry, flagship=False)
    combat = state.active_combat
    assert combat is not None
    battle._direct_hits_to_non_fighters(state, grid_from_state(state, registry), registry, combat)
    assert combat.hit_targets == {}


# ============================================================================= Annihilator


def test_annihilator_w_kroku_bombardment(registry: StaticDataRegistry) -> None:
    state = _state()
    system = state.systems["102"]
    system.planet_units = {THIBAH: {"p2": {"infantry": 1}}}
    system.space_units = {"p1": {"mech": 1, "carrier": 1}}
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.BOMBARDMENT)
    groups = {g.base_type: g for g in invasion.bombard_groups(state, registry)}
    assert set(groups) == {"mech"} and groups["mech"].hits_on == 8
    # Każda jednostka - jedna planeta (reguła kroku Bombardment): przydział całego mecha.
    after = invasion.bombard(state, grid_from_state(state, registry), registry, [
        invasion.BombardAssignment(base_type="mech", planet=THIBAH, count=1),
    ])
    assert after.invasion is not None and after.invasion.bombarded
    # Mech innej frakcji nie bombarduje.
    state.players["p1"].faction = "sol"
    assert invasion.bombard_groups(state, registry) == []


# ==================================================================================== I48S


def _agent_state() -> GameState:
    state = _state()
    state.players["p1"].leader_states["l1z1xagent"] = "unlocked"
    state.active_player_id = "p2"
    state.systems["102"].planet_units = {THIBAH: {"p2": {"infantry": 2}}}
    return state


_ACT = {"player": "p2", "position": "102"}


@ruling("leaders:l1z1xagent#1", "F_lizix/i48s/1")
def test_i48s_aktywny_gracz_wymienia_piechote(registry: StaticDataRegistry) -> None:
    state = _agent_state()
    assert l1z1x._agent_ready(state, "p1", _ACT)
    l1z1x.i48s(state, "p1", _ACT)
    assert state.players["p1"].leader_states["l1z1xagent"] == "exhausted"
    # Piechota wyprodukowana/przywieziona później nie jest celem (F_lizix 1).
    state.systems["102"].space_units = {"p2": {"infantry": 1}}
    inputs = l1z1x.agent_inputs(state, registry, "p2", {})
    assert [o["value"] for o in inputs[0]["options"]] == [THIBAH, "none"]
    l1z1x.i48s_swap(state, "p1", {"player": "p1", "target": "p2",
                                  "params": {"infantry": THIBAH}})
    assert state.systems["102"].planet_units[THIBAH]["p2"] == {"infantry": 1, "mech": 1}


@ruling("F_lizix/i48s/2")
def test_i48s_mech_z_planszy(registry: StaticDataRegistry) -> None:
    state = _agent_state()
    state.systems["103"].planet_units = {TARMANN: {"p2": {"mech": 4}}}
    l1z1x.i48s(state, "p1", _ACT)
    inputs = l1z1x.agent_inputs(state, registry, "p2", {})
    assert inputs[1]["key"] == "source"
    assert [o["value"] for o in inputs[1]["options"]] == [f"103|{TARMANN}"]
    l1z1x.i48s_swap(state, "p1", {"player": "p1", "target": "p2", "params": {
        "infantry": THIBAH, "source": f"103|{TARMANN}",
    }})
    assert state.systems["103"].planet_units[TARMANN]["p2"]["mech"] == 3
    assert state.systems["102"].planet_units[THIBAH]["p2"]["mech"] == 1


def test_i48s_rezygnacja_i_brak_piechoty(registry: StaticDataRegistry) -> None:
    state = _agent_state()
    l1z1x.i48s(state, "p1", _ACT)
    l1z1x.i48s_swap(state, "p1", {"player": "p1", "target": "p2", "params": {"infantry": "none"}})
    assert state.systems["102"].planet_units[THIBAH]["p2"] == {"infantry": 2}
    fresh = _agent_state()
    fresh.systems["102"].planet_units = {}
    assert not l1z1x._agent_ready(fresh, "p1", _ACT)


# ==================================================================================== 2RAM


@ruling("leaders:l1z1xcommander#unlock")
def test_2ram_odblokowanie_4_pancerniki(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["101"].space_units = {"p1": {"dreadnought": 3}}
    state.systems["103"].space_units = {"p1": {"dreadnought": 0}}
    assert not l1z1x._commander_unlocked(state, registry, "p1")
    state.systems["103"].space_units = {"p1": {"dreadnought": 1}}
    assert l1z1x._commander_unlocked(state, registry, "p1")


def test_2ram_bombardowanie_przez_tarcze(registry: StaticDataRegistry) -> None:
    state = _state()
    system = state.systems["102"]
    system.planet_units = {THIBAH: {"p2": {"infantry": 1, "pds": 1}}}
    system.space_units = {"p1": {"dreadnought": 1}}
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.BOMBARDMENT)
    assert invasion.bombard_targets(state, registry) == []
    state.players["p1"].leader_states["l1z1xcommander"] = "unlocked"
    assert invasion.bombard_targets(state, registry) == [THIBAH]


# ===================================================================== Dark Space Navigation


def _hero_state() -> GameState:
    state = _state()
    state.players["p1"].leader_states["l1z1xhero"] = "unlocked"
    state.systems["101"].space_units = {"p1": {"dreadnought": 2, "infantry": 2, "fighter": 1,
                                               "carrier": 1}}
    state.systems["000"].space_units = {"p1": {"flagship": 1}}
    return state


def _mv(dest: str, units: list[str]) -> dict[str, list[str]]:
    return {"moves": [f"{u}>{dest}" for u in units]}


@ruling("leaders:l1z1xhero#1", "leaders:l1z1xhero#2",
        "F_lizix/the-helmsman-dark-space-navigation/1",
        "F_lizix/the-helmsman-dark-space-navigation/2",
        "F_lizix/the-helmsman-dark-space-navigation/3")
def test_dark_space_navigation_flagowiec_i_pancerniki_z_ladunkiem(
    registry: StaticDataRegistry,
) -> None:
    state = _hero_state()
    state.systems["101"].command_tokens = ["p1"]  # z żetonem: ruszają i zabierają ładunek
    assert "103" in l1z1x.hero_destinations(state, "p1")
    l1z1x.dark_space_navigation(state, registry, "p1", _mv("103", [
        "101|dreadnought|0", "101|dreadnought|1", "101|infantry|0", "101|fighter|0",
        "000|flagship|0",
    ]))
    assert state.systems["103"].space_units["p1"] == {"dreadnought": 2, "infantry": 1,
                                                      "fighter": 1, "flagship": 1}


def test_dark_space_navigation_tylko_jeden_cel_i_tylko_pancerniki(
    registry: StaticDataRegistry,
) -> None:
    state = _hero_state()
    with pytest.raises(ValueError, match="exactly 1 system"):
        l1z1x.dark_space_navigation(state, registry, "p1", {"moves": [
            "101|dreadnought|0>103", "000|flagship|0>102",
        ]})
    with pytest.raises(ValueError, match="Only your flagship"):
        l1z1x.dark_space_navigation(state, registry, "p1", _mv("103", ["101|carrier|0"]))
    with pytest.raises(ValueError, match="transported"):
        l1z1x.dark_space_navigation(state, registry, "p1", _mv("103", ["101|infantry|0"]))
    state.systems["103"].space_units = {"p2": {"destroyer": 1}}
    assert "103" not in l1z1x.hero_destinations(state, "p1")


@ruling("F_lizix/the-helmsman-dark-space-navigation/5",
        "F_lizix/the-helmsman-dark-space-navigation/5.2")
def test_dark_space_navigation_cele_bez_mglawicy_i_asteroid(
    registry: StaticDataRegistry,
) -> None:
    state = _hero_state()
    nebula = next(s for s, d in sorted(registry.systems.items()) if d.is_nebula)
    asteroid = next(
        s for s, d in sorted(registry.systems.items())
        if d.is_asteroid_field and not d.is_gravity_rift and not d.is_nebula
    )
    state.systems["102"].system_id = nebula
    state.systems["103"].system_id = asteroid
    found = l1z1x.hero_destinations(state, "p1")
    assert "102" not in found and "103" not in found
    state.players["p1"].technologies = ["amd"]
    assert "103" in l1z1x.hero_destinations(state, "p1")


@ruling("F_lizix/the-helmsman-dark-space-navigation/4")
def test_dark_space_navigation_szczelina(registry: StaticDataRegistry) -> None:
    state = _hero_state()
    rift = next(
        s for s, d in sorted(registry.systems.items())
        if d.is_gravity_rift and not d.planets and not d.is_asteroid_field and not d.is_nebula
    )
    state.systems["101"].system_id = rift
    state.systems["101"].planet_owners = {}
    state.systems["101"].space_units = {"p1": {"dreadnought": 6}}
    state.rng_seed = 3
    l1z1x.dark_space_navigation(state, registry, "p1",
                                _mv("103", [f"101|dreadnought|{i}" for i in range(6)]))
    assert state.systems["103"].space_units.get("p1", {}).get("dreadnought", 0) < 6
    assert state.table_roll is not None and state.table_roll["kind"] == "gravity_rift"


@ruling("F_lizix/the-helmsman-dark-space-navigation/6")
def test_dark_space_navigation_do_nexusa(registry: StaticDataRegistry) -> None:
    from src.core import nexus

    state = _hero_state()
    state.systems["103"].system_id = nexus.NEXUS_LOCKED_ID
    assert "103" in l1z1x.hero_destinations(state, "p1")
    l1z1x.dark_space_navigation(state, registry, "p1", _mv("103", ["000|flagship|0"]))
    assert state.systems["103"].space_units["p1"] == {"flagship": 1}


# ================================================================== Cybernetic Enhancements


def _redistribute() -> GameState:
    state = _state()
    state.phase = Phase.STATUS
    state.status = StatusPhaseState(step=StatusStep.REDISTRIBUTE, unassigned_cc={"p2": 2})
    return state


@ruling("promissory_notes:ce#1")
def test_cybernetic_enhancements_dodatkowy_zeton(registry: StaticDataRegistry) -> None:
    state = _redistribute()
    windows = [w for w in open_windows(state) if w.ctx.get("step")]
    assert {w.ctx["player"] for w in windows} == {"p1", "p2"}
    l1z1x.cybernetic_enhancements(state, registry, "p2", {})
    assert state.status is not None and state.status.unassigned_cc["p2"] == 3
    assert state.players["p2"].cc_reinf == 7
    state.status.done = ["p2"]
    with pytest.raises(ValueError, match="distribute"):
        l1z1x.cybernetic_enhancements(state, registry, "p2", {})


def test_cybernetic_enhancements_okno_tylko_w_rozdziale(registry: StaticDataRegistry) -> None:
    state = _redistribute()
    assert state.status is not None
    state.status.step = StatusStep.SCORE_OBJECTIVES
    assert not [w for w in open_windows(state) if w.ctx.get("step")]


# ============================================================================ Fealty Uplink


def _uplink_state() -> GameState:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    return state


@ruling("breakthroughs:l1z1xbt#1", "F_lizix/fealty-uplink/2")
def test_fealty_uplink_piechota_rowna_wplywowi(registry: StaticDataRegistry) -> None:
    state = _uplink_state()
    _capture(state, registry)  # Thibah: wpływ 1, poprzedni kontroler p2 - bez wyboru
    assert state.pending_offers == []
    assert state.systems["102"].planet_units[THIBAH]["p1"] == {"infantry": 1}


@ruling("F_lizix/fealty-uplink/1")
def test_fealty_uplink_przed_albo_po_eksploracji(registry: StaticDataRegistry) -> None:
    state = _uplink_state()
    state.invasion = InvasionState(position="103", attacker="p1", phase=InvasionPhase.ESTABLISH)
    ctx: dict[str, Any] = {"player": "p1", "planet": TARMANN, "position": "103", "previous": None}
    inputs = l1z1x.uplink_inputs(state, registry, "p1", ctx)
    assert [o["value"] for o in inputs[0]["options"]] == ["now", "after_explore"]
    l1z1x.fealty_uplink(state, "p1", {**ctx, "params": {"when": "after_explore"}})
    assert not state.systems["103"].planet_units.get(TARMANN)
    triggers.fire(state, GameEvent.PLANET_EXPLORED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "planet": TARMANN})
    assert state.systems["103"].planet_units[TARMANN]["p1"] == {"infantry": 1}
    assert not any(e.key == l1z1x.UPLINK_LATER for e in state.active_effects)


@ruling("leaders:l1z1xhero#unlock")
def test_bohater_odblokowanie_3_cele(registry: StaticDataRegistry) -> None:
    """Bohater: „Have 3 scored objectives.” (predykat ogólny z ``leaders``)."""
    unlock = leaders.unlock_predicate(registry, "l1z1xhero")
    assert unlock is not None
    state = _state()
    state.players["p1"].scored_secrets = ["a", "b"]
    assert not unlock(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert unlock(state, registry, "p1")
