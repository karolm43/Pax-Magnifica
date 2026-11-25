"""The Argent Flight — komplet komponentów frakcji (RULES.md 62.11) i rulingi F_argent.

Scenariusze przez prawdziwe API (oferty, notka, ACTION): ``test_flows_argent.py``. Statusy bez
testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    action_cards,
    active_effects,
    agenda_phase,
    battle,
    capacity,
    leaders,
    movement,
    production,
    rules_hooks,
    space_cannon,
    triggers,
)
from src.core.game_events import Duration
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    Phase,
    PlayerState,
    SystemState,
)
from src.core.hooks import technologies_combat
from src.core.hooks.factions import argent
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from tests.factions.completeness import missing_components
from tests.rulings import ruling
from tests.test_agenda_phase import LAW
from tests.test_agenda_phase import _state as _agenda_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _planet(registry: StaticDataRegistry, system_id: str) -> str:
    return registry.systems[system_id].planets[0]


def _state(registry: StaticDataRegistry) -> GameState:
    """p1 = Argent (aktywny), p2 = Sol; 101-103 kolejne systemy pierścienia 1, 000 = Mecatol."""
    p1 = PlayerState(player_id="p1", color="orange", faction="argent")
    p2 = PlayerState(player_id="p2", color="blue", faction="sol")
    mine = _planet(registry, "20")
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            "101": SystemState(position="101", system_id="20", planet_owners={mine: "p1"}),
            "102": SystemState(position="102", system_id="21"),
            "103": SystemState(position="103", system_id="22"),
        },
    )
    state.players["p1"].controlled_planets = [mine]
    for p in state.players.values():
        p.cc_reinf = 8
    return state


def _afb_combat(
    state: GameState, mine: dict[str, int], theirs: dict[str, int],
    rolls: list[dict[str, Any]], *, damaged: dict[str, int] | None = None,
) -> GameState:
    """Walka kosmiczna w 102 w kroku AFB z gotowym rzutem Argent (``rolls``)."""
    system = state.systems["102"]
    system.space_units = {"p1": dict(mine), "p2": dict(theirs)}
    if damaged:
        system.damaged_units = {"space": {"p2": dict(damaged)}}
    state.active_system = "102"
    state.active_combat = ActiveCombat(
        kind="space", position="102", attacker="p1", defender="p2", step=CombatStep.AFB,
        afb={"p1": rolls, "p2": []},
    )
    return state


def _afb_roll(dice: list[int], hits_on: int = 6) -> dict[str, Any]:
    return {"baseType": "destroyer", "name": "Strike Wing Alpha II", "hitsOn": hits_on,
            "modifier": 0, "dice": dice, "hits": sum(1 for d in dice if d >= hits_on)}


def _apply(state: GameState, registry: StaticDataRegistry) -> GameState:
    return battle._apply_afb(state, grid_from_state(state, registry), registry)


def test_kompletnosc_argent(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "argent") == []


# ===================================================================================== Zeal


@ruling("F_argent/zeal/3", "abilities:zeal#1")
def test_zeal_glosy_tylko_przy_wlasnych_glosach(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry, [LAW])
    state.players["p1"].faction = "argent"
    assert agenda_phase.extra_votes(state, registry, "p1", base_votes=2) == 3  # 3 graczy
    assert agenda_phase.extra_votes(state, registry, "p1", base_votes=0) == 0  # wstrzymanie
    assert agenda_phase.extra_votes(state, registry, "p3", base_votes=2) == 0


@ruling("F_argent/zeal/1", "F_argent/zeal/2", "abilities:zeal#2")
def test_zeal_argent_glosuje_pierwszy_takze_jako_mowca(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry, [LAW])  # mówca p2: zwykle p3, p1, p2
    assert agenda_phase.vote_order(state) == ["p3", "p1", "p2"]
    state.players["p1"].faction = "argent"
    assert agenda_phase.vote_order(state) == ["p1", "p3", "p2"]
    state.speaker_id = "p1"  # mówca Argent: nadal pierwszy, reszta od lewej mówcy
    assert agenda_phase.vote_order(state) == ["p1", "p2", "p3"]


@ruling("R_agenda_phase/rules-reference/6")
def test_zeal_dodatkowe_glosy_na_ten_sam_wynik(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry, [LAW])
    state.players["p1"].faction = "argent"
    state = agenda_phase.reveal_agenda(state, registry, "p2")
    planet = next(p for p, o in state.systems["101"].planet_owners.items() if o == "p1")
    influence = next(
        int(r["influence"]) for r in agenda_phase.voting_planets(state, registry, "p1")
        if r["planet"] == planet
    )
    assert agenda_phase.current_voter(state) == "p1"
    state = agenda_phase.cast_vote(state, registry, "p1", "for", [planet])
    assert state.agenda is not None
    vote = state.agenda.votes["p1"]
    assert vote.outcome == "for" and vote.votes == influence + 3


@ruling("C_action_cards/bribery/4.1", "F_argent/zeal/1.1")
def test_bribery_mowca_argent_tylko_od_razu_po_glosie(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry, [LAW])
    state.players["p1"].faction = "argent"
    state.speaker_id = "p1"
    for pid in state.players:
        state.players[pid].trade_goods = 3
        state.players[pid].private.action_cards = ["bribery"]
    state = agenda_phase.reveal_agenda(state, registry, "p1")

    def playable(pid: str) -> bool:
        rows = action_cards.playability(state, registry, pid)
        return any(r["card_id"] == "bribery" and r["playable"] for r in rows)

    planet = next(p for p, o in state.systems["101"].planet_owners.items() if o == "p1")
    state = agenda_phase.cast_vote(state, registry, "p1", "for", [planet])
    assert playable("p1") and not playable("p2")
    state = agenda_phase.abstain(state, registry, agenda_phase.current_voter(state) or "")
    assert not playable("p1")  # okno minęło razem z kolejnym głosem


# =========================================================================== Raid Formation


@ruling("F_argent/raid-formation/1", "abilities:raid_formation#1")
def test_raid_formation_bez_mysliwcow_uszkadza_statki(registry: StaticDataRegistry) -> None:
    state = _afb_combat(_state(registry), {"destroyer": 1}, {"dreadnought": 1, "cruiser": 1},
                        [_afb_roll([7, 8, 2])])
    out = _apply(state, registry)
    system = out.systems["102"]
    assert system.damaged_units["space"]["p2"] == {"dreadnought": 1}  # krążownik bez Sustain
    assert out.active_combat is not None
    assert out.active_combat.log[-1]["raidDamaged"] == {"p2": {"dreadnought": 1}}
    assert out.ability_notes[-1]["component"] == "abilities:raid_formation"  # feed Activity


@ruling("F_argent/raid-formation/2", "F_argent/raid-formation/4")
def test_raid_formation_przed_przypisaniem_i_bez_sustain(registry: StaticDataRegistry) -> None:
    """Uszkodzenie przy wyprodukowaniu trafień - nie jest użyciem Sustain Damage (bez okien Direct
    Hit / Reflective Shielding), a późniejsze anulowanie trafień nic nie zmienia."""
    state = _afb_combat(_state(registry), {"destroyer": 2}, {"fighter": 1, "dreadnought": 2},
                        [_afb_roll([9, 9, 1, 1, 1, 7])])
    out = _apply(state, registry)
    combat = out.active_combat
    assert combat is not None
    assert out.systems["102"].damaged_units["space"]["p2"]["dreadnought"] == 2
    assert combat.sustained_ships == []
    # Trafienie AFB w myśliwca przypisuje jego właściciel (krok ASSIGN, RULES.md 39 W4).
    assert combat.pending_hits == {"p2": 1} and combat.hit_targets["p2"]["types"] == ["fighter"]
    out = battle.assign_combat_hits(out, grid_from_state(out, registry), registry, "p2",
                                    sustain={}, destroy={"fighter": 1}, destroy_damaged={})
    assert out.systems["102"].space_units["p2"].get("fighter", 0) == 0


@ruling("F_argent/raid-formation/2")
def test_raid_formation_liczy_kosci_po_przerzucie(registry: StaticDataRegistry) -> None:
    state = _afb_combat(_state(registry), {"destroyer": 1}, {"dreadnought": 2},
                        [_afb_roll([7, 1, 1])])
    assert state.active_combat is not None
    state.active_combat.afb["p1"] = [_afb_roll([1, 1, 1])]  # przerzut przed skutkami
    out = _apply(state, registry)
    assert not out.systems["102"].damaged_units.get("space", {}).get("p2")


@ruling("F_argent/raid-formation/3")
def test_raid_formation_wybor_argent_takze_uszkodzonego(registry: StaticDataRegistry) -> None:
    state = _afb_combat(_state(registry), {"destroyer": 1},
                        {"dreadnought": 3, "carrier": 1}, [_afb_roll([7, 1, 1])],
                        damaged={"dreadnought": 1})  # 2 nieuszkodzone cele, nadwyżka 1
    out = _apply(state, registry)
    offer = next(o for o in out.pending_offers if o.player_id == "p1")
    assert out.active_combat is not None and out.active_combat.step is CombatStep.TRIGGERS
    inputs = argent.raid_inputs(out, registry, "p1", {})
    values = {o["value"] for o in inputs[0]["options"]}
    assert {"dreadnought#0", "dreadnought#1", "dreadnought:damaged#0"} == values
    out = triggers.accept_offer(out, "p1", offer.id, {"ships": ["dreadnought:damaged#0"]})
    out = battle.resume_after_triggers(out, grid_from_state(out, registry), registry)
    assert out.systems["102"].damaged_units["space"]["p2"] == {"dreadnought": 1}  # bez skutku
    assert out.active_combat is not None and out.active_combat.step is not CombatStep.TRIGGERS


@ruling("C_technology/duranium-armor/5")
def test_raid_formation_duranium_naprawia_pozniej(registry: StaticDataRegistry) -> None:
    state = _afb_combat(_state(registry), {"destroyer": 1}, {"dreadnought": 1},
                        [_afb_roll([7, 1, 1])])
    out = _apply(state, registry)
    ctx = {"position": "102", "kind": "space", "sustained": {}}
    assert technologies_combat._repairable(out, "p2", ctx) == ["dreadnought"]


@ruling("F_argent/raid-formation/4.1")
def test_raid_formation_non_euclidean_nie_zmniejsza(registry: StaticDataRegistry) -> None:
    state = _afb_combat(_state(registry), {"destroyer": 1}, {"dreadnought": 3},
                        [_afb_roll([7, 8, 1])])
    state.players["p2"].faction = "letnev"
    state.players["p2"].technologies = ["nes"]
    out = _apply(state, registry)
    offer = next(o for o in out.pending_offers if o.player_id == "p1")
    out = triggers.accept_offer(out, "p1", offer.id, {"ships": ["dreadnought#0",
                                                                 "dreadnought#1"]})
    assert out.systems["102"].damaged_units["space"]["p2"] == {"dreadnought": 2}


@ruling("F_argent/raid-formation/5", "F_argent/raid-formation/5.1")
def test_raid_formation_z_waylay(registry: StaticDataRegistry) -> None:
    """3 myśliwce i 3 pancerniki, Waylay, 5 trafień: 2 pancerniki uszkodzone, potem rywal
    przypisuje WSZYSTKIE 5 trafień (ostatni pancernik może użyć Sustain Damage)."""
    state = _afb_combat(_state(registry), {"destroyer": 2},
                        {"fighter": 3, "dreadnought": 3}, [_afb_roll([9, 9, 9, 9, 9, 1])])
    active_effects.add_effect(state, "action_cards:waylay", Duration.COMBAT_ROUND, owner="p1")
    out = _apply(state, registry)
    offer = next(o for o in out.pending_offers if o.player_id == "p1")
    out = triggers.accept_offer(out, "p1", offer.id,
                                {"ships": ["dreadnought#0", "dreadnought#1"]})
    out = battle.resume_after_triggers(out, grid_from_state(out, registry), registry)
    combat = out.active_combat
    assert combat is not None
    assert out.systems["102"].damaged_units["space"]["p2"] == {"dreadnought": 2}
    assert combat.step is CombatStep.ASSIGN and combat.pending_hits == {"p2": 5}


@ruling("C_relics/metali-void-shielding/4")
def test_raid_formation_pomija_sustain_z_metali(registry: StaticDataRegistry) -> None:
    state = _afb_combat(_state(registry), {"destroyer": 1}, {"cruiser": 2},
                        [_afb_roll([7, 8, 1])])
    state.players["p2"].relics = ["metali_void_shielding"]
    out = _apply(state, registry)
    assert not out.systems["102"].damaged_units.get("space", {}).get("p2")


# ======================================================================= Strike Wing Alpha II


@ruling("F_argent/strike-wing-alpha/1", "F_argent/strike-wing-alpha/2",
        "technologies:swa2#3")
def test_swa2_wyniki_9_10_niszcza_piechote_w_przestrzeni(registry: StaticDataRegistry) -> None:
    state = _afb_combat(_state(registry), {"destroyer": 1},
                        {"carrier": 1, "infantry": 3}, [_afb_roll([10, 9, 3])])
    state.players["p1"].technologies = ["swa2"]
    state.systems["102"].planet_units = {_planet(registry, "21"): {"p2": {"infantry": 2}}}
    out = _apply(state, registry)
    assert out.systems["102"].space_units["p2"].get("infantry", 0) == 1
    assert out.systems["102"].planet_units[_planet(registry, "21")]["p2"] == {"infantry": 2}
    assert out.active_combat is not None
    assert out.active_combat.log[-1]["losses"]["p2"]["infantry"] == 2
    # Bez technologii zwykły niszczyciel Argent nie zabija piechoty.
    plain = _afb_combat(_state(registry), {"destroyer": 1},
                        {"carrier": 1, "infantry": 3}, [_afb_roll([10, 9, 3])])
    assert _apply(plain, registry).systems["102"].space_units["p2"]["infantry"] == 3


@ruling("technologies:swa2#1", "technologies:swa2#2")
def test_swa2_statystyki_z_danych(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies = ["swa2"]
    state.systems["102"].space_units = {"p1": {"destroyer": 1}, "p2": {"fighter": 1}}
    state.active_system = "102"
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1",
                                       defender="p2")
    unit = next(u for u in battle.side_units(state, grid_from_state(state, registry), registry,
                                             "p1"))
    assert (unit.name, unit.base_hits_on, unit.afb_hits_on, unit.afb_dice) == (
        "Strike Wing Alpha II", 7, 6, 3)
    info = registry.units["argent_destroyer2"]
    assert (info.cost, info.move_value, info.capacity_value) == (1, 2, 1)


@ruling("F_argent/strike-wing-alpha/3")
def test_swa2_ostatnie_sily_naziemne_eliminacja(registry: StaticDataRegistry) -> None:
    state = _afb_combat(_state(registry), {"destroyer": 1}, {"carrier": 1, "infantry": 1},
                        [_afb_roll([10, 1, 1])])
    state.players["p1"].technologies = ["swa2"]
    state.players["p2"].home_position = "103"  # dom bez planet i jednostek p2
    out = _apply(state, registry)
    assert "p2" not in out.players
    assert out.active_combat is not None
    assert out.active_combat.winner == "p1"


# ======================================================================= Aerie Hololattice


def _route_state(registry: StaticDataRegistry) -> GameState:
    """p2 (Sol) leci krążownikiem 101 -> 102 -> 103; w 102 stoi PDS Argent na planecie."""
    state = _state(registry)
    state.active_player_id = "p2"
    state.active_system = "103"
    planet = _planet(registry, "21")
    state.systems["101"].space_units = {"p2": {"cruiser": 1}}
    state.systems["102"].planet_units = {planet: {"p1": {"pds": 1}}}
    state.systems["102"].planet_owners = {planet: "p1"}
    return state


@ruling("F_argent/aerie-hololattice/2", "technologies:ah#1")
def test_hololattice_blokuje_przelot_takze_z_light_wave(registry: StaticDataRegistry) -> None:
    state = _route_state(registry)
    grid = grid_from_state(state, registry)
    route = ["101", "102", "103"]
    assert movement.route_error(state, grid, route, "p2", "cruiser") is None
    state.players["p1"].technologies = ["ah"]
    assert movement.route_error(state, grid, route, "p2", "cruiser") is not None
    state.players["p2"].technologies = ["lwd"]
    assert movement.route_error(state, grid, route, "p2", "cruiser") is not None
    # Sam Argent przelatuje bez przeszkód; cel ze strukturami też jest dozwolony.
    state.active_player_id = "p1"
    state.systems["101"].space_units = {"p1": {"cruiser": 1}}
    assert movement.route_error(state, grid, route, "p1", "cruiser") is None


@ruling("F_argent/aerie-hololattice/1", "technologies:ah#2")
def test_hololattice_planeta_ze_struktura_ma_production_1(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    mine = _planet(registry, "20")
    state.systems["101"].planet_units = {mine: {"p1": {"pds": 1}}}
    assert production.producers(state, registry, "p1", "101") == []
    state.players["p1"].technologies = ["ah"]
    found = production.producers(state, registry, "p1", "101")
    assert [(p.zone, p.value) for p in found] == [(mine, 1)]
    assert production.allowed_ground_zones(state, registry, "p1", "101") == [mine]


# ============================================================================ Quetzecoatl


@ruling("F_argent/quetzecoatl/1", "units:argent_flagship#1")
def test_quetzecoatl_blokuje_space_cannon_offense(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.active_system = "102"
    state.systems["102"].space_units = {"p1": {"flagship": 1, "carrier": 1}}
    assert space_cannon.offense_targets(state, "p2") == []
    state.systems["102"].space_units = {"p1": {"carrier": 1}}
    state.systems["103"].space_units = {"p1": {"flagship": 1}}  # flagowiec w innym systemie
    assert space_cannon.offense_targets(state, "p2") == ["p1"]
    # Space Cannon Defense (inwazja) nie korzysta z tego punktu - hook dotyczy tylko Offense.
    assert not rules_hooks.permits(
        rules_hooks.POINT_SPACE_CANNON_DEFENSE_IMMUNE, state, "p1"
    )


# ========================================================================= Aerie Sentinel


@ruling("units:argent_mech#1")
def test_aerie_sentinel_poza_pojemnoscia_tylko_przy_statku_z_pojemnoscia(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry)
    state.systems["102"].space_units = {"p1": {"carrier": 1, "infantry": 4, "mech": 1}}
    assert capacity.capacity_report(state, registry, "102", "p1").excess == 0
    state.systems["102"].space_units = {"p1": {"cruiser": 1, "mech": 1}}  # Cruiser I bez pojemn.
    assert capacity.capacity_report(state, registry, "102", "p1").excess == 1
    # Transport: statek bez wartości pojemności nie zabierze mecha.
    state.systems["101"].space_units = {"p1": {"cruiser": 1, "mech": 1}}
    state.active_system = "102"
    grid = grid_from_state(state, registry)
    with pytest.raises(ValueError, match="capacity value"):
        movement.move_fleet(state, grid, registry, "101", {"cruiser": 1},
                            [movement.CargoPickup("mech", 1)], "p1", route=["101", "102"])


# ===================================================================== Trrakan Aun Zulok


@ruling("leaders:argentcommander#unlock", "F_argent/trrakan-aun-zulok/1.1")
def test_commander_odblokowanie_szesc_jednostek(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states = {"argentcommander": "locked"}
    state.systems["102"].space_units = {"p1": {"destroyer": 4, "carrier": 2}}
    planet = _planet(registry, "20")
    state.systems["101"].planet_units = {planet: {"p1": {"pds": 1}}}
    leaders.refresh_unlocks(state, registry)
    assert state.players["p1"].leader_states["argentcommander"] == "locked"  # 5 jednostek
    state.systems["102"].space_units["p1"]["dreadnought"] = 1  # Bombardment
    leaders.refresh_unlocks(state, registry)
    assert state.players["p1"].leader_states["argentcommander"] == "unlocked"


@ruling("F_argent/trrakan-aun-zulok/1")
def test_commander_blitz_liczy_statki(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.active_system = "102"
    state.systems["102"].space_units = {"p1": {"destroyer": 3, "carrier": 3}}
    assert argent._ability_units(state, registry, "p1") == 3
    active_effects.add_effect(state, "action_cards:blitz", Duration.TACTICAL_ACTION, owner="p1")
    assert argent._ability_units(state, registry, "p1") == 6


@ruling("F_argent/trrakan-aun-zulok/2", "leaders:argentcommander#1")
def test_commander_kosc_tylko_dla_zdolnosci_jednostek(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states = {"argentcommander": "unlocked"}
    for point in (rules_hooks.POINT_SPACE_CANNON_EXTRA_DICE,
                  rules_hooks.POINT_BOMBARDMENT_EXTRA_DICE,
                  rules_hooks.POINT_COMBAT_AFB_EXTRA_DICE):
        assert rules_hooks.modify(point, state, "p1", 0) == 1
    assert rules_hooks.modify(rules_hooks.POINT_COMBAT_EXTRA_DICE, state, "p1", 0,
                              {"kind": "space", "base_type": "destroyer"}) == 0
    # AFB: kość dostaje najcelniejsza grupa.
    state.systems["102"].space_units = {"p1": {"destroyer": 2}, "p2": {"fighter": 3}}
    state.active_system = "102"
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1",
                                       defender="p2", step=CombatStep.AFB)
    out = battle.resolve_afb(state, grid_from_state(state, registry), registry)
    combat = out.active_combat
    assert combat is not None
    entry = combat.log[-1]["rolls"]["p1"][0]
    assert entry["extraDice"] == 1 and len(entry["dice"]) == 2 * 2 + 1


# ============================================================ Mirik Aun Sissiri — Helix Protocol


def _mv(dest: str, units: list[str]) -> dict[str, list[str]]:
    """Parametry ruchu (``oi.unit_moves``): każda jednostka -> ``dest``."""
    return {"moves": [f"{u}>{dest}" for u in units]}


def _helix_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry)
    state.systems["103"].command_tokens = ["p1"]
    state.systems["101"].space_units = {"p1": {"carrier": 1, "infantry": 2, "fighter": 2}}
    return state


@ruling("F_argent/mirik-aun-sissiri-helix-protocol/1",
        "F_argent/mirik-aun-sissiri-helix-protocol/4", "leaders:argenthero#1")
def test_helix_ruch_prosto_do_systemu_z_zetonem(registry: StaticDataRegistry) -> None:
    state = _helix_state(registry)
    state.systems["000"].space_units = {"p1": {"fighter": 1}}
    assert argent.helix_destinations(state, "p1") == ["103"]
    argent.helix_protocol(state, registry, "p1", _mv("103", [
        "101|carrier|0", "101|infantry|0", "101|infantry|1", "101|fighter|0", "101|fighter|1",
    ]))
    assert state.systems["103"].space_units["p1"] == {"carrier": 1, "infantry": 2, "fighter": 2}
    # Myśliwce lecą bez transportu (Helix), ale pojemność celu obowiązuje.
    state.systems["103"].space_units["p1"]["fighter"] = 1
    argent.helix_protocol(state, registry, "p1", _mv("103", ["000|fighter|0"]))
    assert state.systems["103"].space_units["p1"]["fighter"] == 2


def test_helix_zostawione_mysliwce_gina_zamiast_bledu(registry: StaticDataRegistry) -> None:
    """Statek z pojemnością odlatuje, myśliwce zostają bez pojemności: ruch jest legalny
    (R_capacity: ruch może spowodować usunięcie), a nadwyżkę bez wyboru usuwa limit po akcji
    (RULES.md 39.6 C5) - zamiast błędu „Capacity exceeded"."""
    from src.core import limits

    state = _helix_state(registry)
    state.phase = Phase.ACTION
    argent.helix_protocol(state, registry, "p1", _mv("103", ["101|carrier|0"]))
    assert state.systems["101"].space_units["p1"] == {"infantry": 2, "fighter": 2}
    after = limits.enforce_limits(state, registry)
    assert after.pending_window is None
    assert not any(after.systems["101"].space_units.get("p1", {}).values())


@ruling("F_argent/mirik-aun-sissiri-helix-protocol/2",
        "F_argent/mirik-aun-sissiri-helix-protocol/3")
def test_helix_ze_zetonem_rusza_i_zabiera_ladunek(registry: StaticDataRegistry) -> None:
    """Statki z systemu z żetonem Argent ruszają i - wg rulingu FAQ (3.2, zastępuje zakaz z 3)
    - zabierają ze sobą piechotę i myśliwce z tego systemu."""
    state = _helix_state(registry)
    state.systems["101"].command_tokens = ["p1"]
    argent.helix_protocol(state, registry, "p1", _mv("103", [
        "101|carrier|0", "101|infantry|0", "101|infantry|1", "101|fighter|0",
    ]))
    assert state.systems["103"].space_units["p1"] == {"carrier": 1, "infantry": 2, "fighter": 1}


@ruling("F_argent/mirik-aun-sissiri-helix-protocol/4")
def test_helix_piechota_tylko_ze_statkiem_z_tego_samego_systemu(
    registry: StaticDataRegistry,
) -> None:
    state = _helix_state(registry)
    state.systems["102"].space_units = {"p1": {"infantry": 1}}
    with pytest.raises(ValueError, match="transported"):
        argent.helix_protocol(state, registry, "p1",
                              _mv("103", ["101|carrier|0", "102|infantry|0"]))


@ruling(
    "F_argent/mirik-aun-sissiri-helix-protocol/6",
    "R_nebula/notes/2",
    "R_supernova/rules-reference/1",
    "R_asteroid_field/notes/1",
)
def test_helix_cele_mglawica_tak_asteroidy_z_antimass(registry: StaticDataRegistry) -> None:
    state = _helix_state(registry)
    nebula = next(s for s, d in sorted(registry.systems.items()) if d.is_nebula)
    asteroid = next(
        s for s, d in sorted(registry.systems.items())
        if d.is_asteroid_field and not d.is_gravity_rift and not d.is_nebula
    )
    state.systems["102"].system_id = nebula
    state.systems["102"].command_tokens = ["p1"]
    state.systems["000"].system_id = asteroid
    state.systems["000"].command_tokens = ["p1"]
    assert argent.helix_destinations(state, "p1") == ["102", "103"]  # mgławica OK (notes/2)
    state.players["p1"].technologies = ["amd"]
    assert argent.helix_destinations(state, "p1") == ["000", "102", "103"]


@ruling("F_argent/mirik-aun-sissiri-helix-protocol/6", "R_gravity_rift/rules-reference/2")
def test_helix_szczelina_rzut_przy_wyjsciu(registry: StaticDataRegistry) -> None:
    state = _helix_state(registry)
    rift = next(
        s for s, d in sorted(registry.systems.items())
        if d.is_gravity_rift and not d.planets and not d.is_asteroid_field and not d.is_nebula
    )
    state.systems["101"].system_id = rift
    state.systems["101"].planet_owners = {}
    state.systems["101"].space_units = {"p1": {"carrier": 6}}
    state.rng_seed = 3
    argent.helix_protocol(state, registry, "p1", _mv("103", [f"101|carrier|{i}" for i in range(6)]))
    arrived = state.systems["103"].space_units.get("p1", {}).get("carrier", 0)
    assert arrived < 6
    assert state.table_roll is not None and state.table_roll["kind"] == "gravity_rift"


@ruling("F_argent/mirik-aun-sissiri-helix-protocol/5")
def test_helix_do_nexusa_odwraca_go(registry: StaticDataRegistry) -> None:
    from src.core import nexus

    state = _helix_state(registry)
    state.systems["103"].system_id = nexus.NEXUS_LOCKED_ID
    argent.helix_protocol(state, registry, "p1", _mv("103", ["101|carrier|0",
                                                                          "101|infantry|0",
                                                                          "101|infantry|1",
                                                                          "101|fighter|0",
                                                                          "101|fighter|1"]))
    assert nexus.activate_nexus(state).systems["103"].system_id == nexus.NEXUS_ACTIVE_ID


# ============================================================================ Wing Transfer


@ruling("F_argent/wing-transfer/1")
def test_wing_transfer_nie_do_systemu_z_cudzymi_statkami(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems["102"].space_units = {"p1": {"carrier": 1}}
    state.systems["103"].space_units = {"p2": {"cruiser": 1}}
    state.systems["103"].command_tokens = ["p1"]
    active_effects.add_effect(state, argent.WING_TRANSFER, Duration.TACTICAL_ACTION, owner="p1")
    ctx = {"player": "p1", "position": "102", "params": _mv("103", ["102|carrier|0"])}
    with pytest.raises(ValueError):
        argent.wing_transfer_move(state, "p1", ctx)
    assert state.systems["102"].space_units["p1"] == {"carrier": 1}


@ruling("F_argent/wing-transfer/2")
def test_wing_transfer_ruch_wymaga_pojemnosci(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems["102"].space_units = {"p1": {"carrier": 1, "fighter": 4}}
    state.systems["103"].space_units = {"p1": {"cruiser": 1}}
    state.systems["103"].command_tokens = ["p1"]
    active_effects.add_effect(state, argent.WING_TRANSFER, Duration.TACTICAL_ACTION, owner="p1")
    ctx = {"player": "p1", "position": "102",
           "params": _mv("103", ["102|fighter|0"])}
    with pytest.raises(ValueError):
        argent.wing_transfer_move(state, "p1", ctx)  # myśliwiec bez statku z pojemnością
    ctx["params"] = _mv("103", ["102|carrier|0", "102|fighter|0", "102|fighter|1",
                                             "102|fighter|2", "102|fighter|3"])
    argent.wing_transfer_move(state, "p1", ctx)
    assert state.systems["103"].space_units["p1"] == {"cruiser": 1, "carrier": 1, "fighter": 4}


def test_ruch_z_efektu_to_jedno_pole_przeciagania(registry: StaticDataRegistry) -> None:
    """Decyzja użytkownika: ruch z efektu = przeciąganie na mapie (``oi.unit_moves``), nie
    sloty „Destination N”; jednostka nie „rusza” do własnego systemu."""
    state = _state(registry)
    state.systems["102"].space_units = {"p1": {"carrier": 1}}
    state.systems["103"].space_units = {"p1": {"cruiser": 1}}
    state.systems["103"].command_tokens = ["p1"]
    inputs = argent.transfer_move_inputs(state, registry, "p1", {"position": "102"})
    assert [(i["key"], i["kind"]) for i in inputs] == [("moves", "multi")]
    moves = {o["value"]: o["meta"]["move"] for o in inputs[0]["options"]}
    assert moves == {
        "102|carrier|0>103": {"unit": "102|carrier|0", "from": "102", "to": "103"},
        "103|cruiser|0>102": {"unit": "103|cruiser|0", "from": "103", "to": "102"},
    }
    with pytest.raises(ValueError, match="two systems"):
        argent.wing_transfer_move(state, "p1", {
            "player": "p1", "position": "102",
            "params": {"moves": ["102|carrier|0>103", "102|carrier|0>102"]},
        })


# ================================================ Dodatkowe kości: każde źródło osobno (+ auto)


def test_dodatkowe_kosci_kazde_zrodlo_osobno() -> None:
    from src.core import extra_dice

    extra = [extra_dice.ExtraDie("technologies:ps", "Plasma Scoring", 1),
             extra_dice.ExtraDie("leaders:argentcommander", "Trrakan Aun Zulok", 1)]
    groups = {"pds": 6, "flagship": 5}
    assert extra_dice.assign(extra, groups, {}) == {}  # bez wyboru - nic („may”)
    assert extra_dice.assign(extra, groups, {"technologies:ps": "pds",
                                             "leaders:argentcommander": "auto"}) == {
        "pds": 1, "flagship": 1}
    assert extra_dice.assign(extra, groups, {"technologies:ps": "none",
                                             "leaders:argentcommander": "flagship"}) == {
        "flagship": 1}
    with pytest.raises(ValueError):
        extra_dice.assign(extra, groups, {"technologies:ps": "carrier"})


def test_afb_wybor_kosci_gracza_i_auto(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states = {"argentcommander": "unlocked"}
    state.systems["102"].space_units = {"p1": {"destroyer": 2}, "p2": {"fighter": 3}}
    state.active_system = "102"
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1",
                                       defender="p2", step=CombatStep.AFB)
    grid = grid_from_state(state, registry)
    picked = battle.set_afb_picks(state, grid, registry, "p1",
                                  {"leaders:argentcommander": "none"})
    out = battle.resolve_afb(picked, grid, registry)
    assert out.active_combat is not None
    entry = out.active_combat.log[-1]["rolls"]["p1"][0]
    assert "extraDice" not in entry and len(entry["dice"]) == 4  # gracz zrezygnował
    with pytest.raises(ValueError):
        battle.set_afb_picks(state, grid, registry, "p1", {"leaders:argentcommander": "carrier"})
