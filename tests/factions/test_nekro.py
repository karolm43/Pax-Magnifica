"""The Nekro Virus — every faction component (RULES.md 62.24) and the F_nekro rulings.

Scenarios through the real API (offers, window uses, ACTIONs, notes): ``test_flows_nekro.py``.
Statuses without a test: ``tests/rulings_status.json``.

Board: 000 Mecatol Rex, 101 Nekro home (08: Mordai II), 102 empty (46), 103 empty (47), 104 the
rival's home (Sol: Jord), 105 Tarmann (22, BIOTIC), 106 Wellon (19, CYBERNETIC).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    agenda_phase,
    battle_units,
    board_graph,
    exhaust,
    faction_components,
    fleet_pool,
    leaders,
    offers,
    promissory_notes,
    promissory_play,
    rules_hooks,
    ship_roles,
    technology,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    AgendaPhaseState,
    AgendaStep,
    AgendaVote,
    GameState,
    Phase,
    PlayerState,
    SystemState,
)
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import mahact, nekro
from src.core.objective_progress import _p_faction_techs, _p_unit_upgrades
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.unit_ops import UnitCause
from tests.factions.completeness import missing_components
from tests.rulings import ruling

MECATOL, HOME, EMPTY, EMPTY_B, RIVAL, TARMANN, WELLON = (
    "000", "101", "102", "103", "104", "105", "106",
)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    yield
    board_graph.bind_grid_provider(None)


def _bind(state: GameState, registry: StaticDataRegistry) -> HexGrid:
    board_graph.bind_grid_provider(lambda: grid_from_state(state, registry))
    return grid_from_state(state, registry)


def _state(registry: StaticDataRegistry, other: str = "sol", third: str | None = None
           ) -> GameState:
    """p1 = the Nekro (active, owns both Valefar Assimilators), p2 = ``other`` at 104."""
    rival = registry.factions[other]
    p1 = PlayerState(player_id="p1", color="red", faction="nekro", home_position=HOME,
                     controlled_planets=["mordaiii"], technologies=["dxa", "vax", "vay"])
    p2 = PlayerState(player_id="p2", color="blue", faction=other, home_position=RIVAL,
                     controlled_planets=list(rival.home_planets))
    players = {"p1": p1, "p2": p2}
    if third is not None:
        players["p3"] = PlayerState(player_id="p3", color="green", faction=third)
    systems = {
        MECATOL: SystemState(position=MECATOL, system_id="18"),
        HOME: SystemState(position=HOME, system_id="08", planet_owners={"mordaiii": "p1"},
                          space_units={"p1": {"flagship": 1, "carrier": 1}}),
        EMPTY: SystemState(position=EMPTY, system_id="46"),
        EMPTY_B: SystemState(position=EMPTY_B, system_id="47"),
        RIVAL: SystemState(position=RIVAL, system_id=str(rival.home_system),
                           planet_owners={p: "p2" for p in rival.home_planets}),
        TARMANN: SystemState(position=TARMANN, system_id="22"),
        WELLON: SystemState(position=WELLON, system_id="19"),
    }
    state = GameState(phase=Phase.ACTION, active_player_id="p1",
                      seating_order=list(players), players=players, systems=systems, rng_seed=3)
    for player in state.players.values():
        player.cc_reinf = 8
        player.tactical_cc = 3
        player.leader_states = {}
        player.commodity_value = registry.factions[player.faction or ""].commodities
    _bind(state, registry)
    return state


def _offers(state: GameState, pid: str, label: str) -> list[Any]:
    return [o for o in triggers.offers_for(state, pid) if label in o.label]


def _inputs(state: GameState, registry: StaticDataRegistry, offer: Any) -> list[dict[str, Any]]:
    return offers.offer_view(state, registry, offer)["inputs"]  # type: ignore[no-any-return]


def _accept(state: GameState, pid: str, label: str, params: dict[str, Any] | None = None
            ) -> GameState:
    offer = _offers(state, pid, label)[0]
    return triggers.accept_offer(state, pid, offer.id, params or {})


def _use(state: GameState, registry: StaticDataRegistry, pid: str, kind: str, comp: str,
         params: dict[str, Any] | None = None) -> GameState:
    new_state, _implemented = faction_components.play(state, registry, pid, kind, comp, params)
    return new_state


def _combat(state: GameState, kind: str = "space", position: str = EMPTY,
            planet: str | None = None) -> GameState:
    state.active_combat = ActiveCombat(kind=kind, position=position, planet=planet,
                                       attacker="p1", defender="p2")
    return state


def _destroy(state: GameState, pid: str, base_type: str, position: str = EMPTY,
             zone: str = "space", cause: UnitCause = UnitCause.DESTROYED) -> GameState:
    work = state.clone()
    system = work.systems[position]
    unit_ops.remove_units(work, system, zone, pid, base_type, 1, cause)
    return work


def _fight_setup(registry: StaticDataRegistry, techs: list[str]) -> GameState:
    state = _state(registry)
    state.players["p2"].technologies = list(techs)
    state.systems[EMPTY].space_units = {"p1": {"cruiser": 2}, "p2": {"fighter": 3, "carrier": 1}}
    return _combat(state)


def _free_tech(state: GameState, registry: StaticDataRegistry, pid: str) -> str:
    """A technology without prerequisites the player may research now."""
    for tech in technology.tech_pool(state, registry, pid).values():
        if not tech.requirements and tech.id not in state.players[pid].technologies and (
            "UNITUPGRADE" not in tech.types and not tech.faction
        ):
            return tech.id
    raise AssertionError("no free technology")


def test_nekro_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "nekro") == []


# ===================================================================== Starting assimilators


def test_start_z_obydwoma_asymilatorami(registry: StaticDataRegistry) -> None:
    """⚠️ ASSUMPTION RULES.md 62.24: the Nekro starts owning Valefar Assimilator X and Y."""
    state = _state(registry)
    state.players["p1"].technologies = ["dxa"]
    work = state.clone()
    triggers.fire(work, GameEvent.SETUP, Moment.DURING, subject="p1", ctx={"player": "p1"})
    assert {"dxa", "vax", "vay"} <= set(work.players["p1"].technologies)
    assert "vax" not in work.players["p2"].technologies


# =================================================================================== Propagation


@ruling("abilities:propagation#1", "abilities:propagation#2", "F_nekro/propagation/2",
        "F_nekro/propagation/3")
def test_propagation_3_zetony_zamiast_technologii(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    tech = _free_tech(state, registry, "p1")
    seen: list[str] = []
    after = technology.research(state, registry, "p1", tech)
    assert tech not in after.players["p1"].technologies  # "You cannot research technology"
    assert after.last_research == []  # no "after research" trace (propagation 3)
    seen = [o.label for o in triggers.offers_for(after, "p1")]
    assert any("Propagation" in label for label in seen)
    offer = _offers(after, "p1", "Propagation")[0]
    assert all("auto" not in field for field in _inputs(after, registry, offer))
    with pytest.raises(ValueError):
        _accept(after, "p1", "Propagation", {"token_1": "tactical"})
    done = _accept(after, "p1", "Propagation",
                   {"token_1": "tactical", "token_2": "fleet", "token_3": "strategic"})
    p1 = done.players["p1"]
    assert (p1.tactical_cc, p1.fleet_cc, p1.strategic_cc, p1.cc_reinf) == (4, 4, 3, 5)


@ruling("F_nekro/propagation/2.1")
def test_propagation_prophets_tears_reaguje_na_when(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].relics = ["prophetstears"]
    after = technology.research(state, registry, "p1", _free_tech(state, registry, "p1"))
    assert _offers(after, "p1", "Prophet's Tears")


@ruling("F_nekro/propagation/3.1")
def test_propagation_bez_anti_intellectual_revolution(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.decks.agenda_laws = {"revolution": "for"}
    after = technology.research(state, registry, "p1", _free_tech(state, registry, "p1"))
    assert not _offers(after, "p1", "Anti-Intellectual Revolution")
    # A normal player researching under the law still gets it (pair test).
    rival = technology.research(state, registry, "p2", _free_tech(state, registry, "p2"))
    rival.systems[RIVAL].space_units = {"p2": {"cruiser": 1}}
    assert _free_tech(state, registry, "p2") in rival.players["p2"].technologies


def test_propagation_mniej_zetonow_w_rezerwie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].cc_reinf = 2
    after = technology.research(state, registry, "p1", _free_tech(state, registry, "p1"))
    done = _accept(after, "p1", "Propagation", {"token_1": "fleet", "token_2": "fleet"})
    assert done.players["p1"].fleet_cc == 5 and done.players["p1"].cc_reinf == 0


def test_propagation_widok_badania_ma_baner(registry: StaticDataRegistry) -> None:
    from src.core.strategy_cards.technology import research_view

    state = _state(registry)
    assert research_view(state, registry, "p1", 0)["propagation"] is True
    assert research_view(state, registry, "p2", 0)["propagation"] is False


# ====================================================================== Technological Singularity


@ruling("abilities:technological_singularity#1", "F_nekro/technological-singularity/3")
def test_singularity_po_zniszczeniu_w_walce(registry: StaticDataRegistry) -> None:
    state = _fight_setup(registry, ["nm", "ac2"])
    after = _destroy(state, "p2", "fighter")
    offer = _offers(after, "p1", "Technological Singularity")[0]
    fields = _inputs(after, registry, offer)
    techs = {o["value"] for o in fields[0]["options"]}
    assert {"nm", "ac2"} <= techs  # gain nm, copy ac2 (Valefar)
    assert all("auto" not in f for f in fields)
    done = _accept(after, "p1", "Technological Singularity", {"technology": "nm"})
    assert "nm" in done.players["p1"].technologies
    # Once per combat: a second destroyed unit offers nothing.
    again = _destroy(done, "p2", "fighter")
    assert not _offers(again, "p1", "Technological Singularity")


@ruling("F_nekro/technological-singularity/1", "F_nekro/technological-singularity/2")
def test_singularity_raz_na_walke_kazda_walka_osobno(registry: StaticDataRegistry) -> None:
    state = _fight_setup(registry, ["nm", "gd"])
    done = _accept(_destroy(state, "p2", "fighter"), "p1", "Technological Singularity",
                   {"technology": "nm"})
    # The space combat ends; a ground combat of the same action is a new combat.
    triggers.fire(done, GameEvent.COMBAT, Moment.END, ctx={"kind": "space", "position": EMPTY})
    done.active_combat = None
    done.systems[TARMANN].planet_units = {"tarmann": {"p2": {"infantry": 2}, "p1": {"mech": 1}}}
    ground = _combat(done, "ground", TARMANN, "tarmann")
    after = _destroy(ground, "p2", "infantry", TARMANN, "tarmann")
    assert _offers(after, "p1", "Technological Singularity")


@ruling("F_nekro/technological-singularity/3.1")
def test_singularity_wlasny_koszt_przeciwnika(registry: StaticDataRegistry) -> None:
    """Any destruction in the combat counts - also the opponent destroying its own unit."""
    state = _fight_setup(registry, ["nm"])
    work = state.clone()
    unit_ops.remove_units(work, work.systems[EMPTY], "space", "p2", "carrier", 1,
                          UnitCause.DESTROYED)
    assert _offers(work, "p1", "Technological Singularity")


@ruling("F_nekro/technological-singularity/3.2", "F_nekro/technological-singularity/3.3")
def test_singularity_nie_usuniecie_i_nie_poza_walka(registry: StaticDataRegistry) -> None:
    state = _fight_setup(registry, ["nm"])
    removed = _destroy(state, "p2", "fighter", cause=UnitCause.REMOVED)
    assert not _offers(removed, "p1", "Technological Singularity")
    outside = state.clone()
    outside.active_combat = None  # Space Cannon Offense / bombardment: no combat yet
    assert not _offers(_destroy(outside, "p2", "fighter"), "p1", "Technological Singularity")
    # Own units destroyed never trigger it.
    assert not _offers(_destroy(state, "p1", "cruiser"), "p1", "Technological Singularity")


@ruling("F_nekro/technological-singularity/4")
def test_singularity_ulepszenie_dziala_od_razu(registry: StaticDataRegistry) -> None:
    state = _fight_setup(registry, ["cr2"])
    done = _accept(_destroy(state, "p2", "fighter"), "p1", "Technological Singularity",
                   {"technology": "cr2"})
    grid = grid_from_state(done, registry)
    units = battle_units.combat_units(done, grid, registry, kind="space", position=EMPTY,
                                      planet=None, player_id="p1")
    cruiser = next(u for u in units if u.base_type == "cruiser")
    assert cruiser.unit_id == "cruiser2"


@ruling("F_nekro/technological-singularity/7")
def test_singularity_bez_prophets_tears(registry: StaticDataRegistry) -> None:
    state = _fight_setup(registry, ["nm"])
    state.players["p1"].relics = ["prophetstears"]
    done = _accept(_destroy(state, "p2", "fighter"), "p1", "Technological Singularity",
                   {"technology": "nm"})
    assert not _offers(done, "p1", "Prophet's Tears")  # gaining is not researching


# ===================================================================== Valefar Assimilator X / Y


@ruling("technologies:vax#1", "technologies:vax#2", "technologies:vay#1", "technologies:vay#2",
        "F_nekro/the-alastor/6")
def test_valefar_kopiuje_frakcyjne_ulepszenie(registry: StaticDataRegistry) -> None:
    state = _fight_setup(registry, ["ac2"])
    with pytest.raises(ValueError, match="X or Y"):
        _accept(_destroy(state, "p2", "fighter"), "p1", "Technological Singularity",
                {"technology": "ac2"})
    done = _accept(_destroy(state, "p2", "fighter"), "p1", "Technological Singularity",
                   {"technology": "ac2", "token": "vax"})
    p1 = done.players["p1"]
    assert p1.assimilated == {"vax": "ac2"} and "ac2" in p1.technologies
    carrier = resolve_unit_variant(registry, p1.faction, p1.technologies, "carrier")
    assert carrier is not None and carrier.id == "sol_carrier2"
    # The Sol player keeps its own technology.
    assert "ac2" in done.players["p2"].technologies


@ruling("F_nekro/valefar-assimilator/6", "F_nekro/valefar-assimilator/6.1")
def test_valefar_frakcyjne_przed_generycznym(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    p1 = state.players["p1"]
    p1.technologies = [*p1.technologies, "cv2"]
    technology.assimilate(state, "p1", "vax", "ac2")
    carrier = resolve_unit_variant(registry, p1.faction, p1.technologies, "carrier")
    assert carrier is not None and carrier.id == "sol_carrier2"
    from src.core.objective_progress import View

    view = View(state, registry, grid_from_state(state, registry), "p1")
    assert _p_unit_upgrades(view) == 1  # two carrier upgrades count once
    technology.release_assimilated(state, "p1", "vax")
    carrier = resolve_unit_variant(registry, p1.faction, p1.technologies, "carrier")
    assert carrier is not None and carrier.id == "carrier2"  # back to the generic one


@ruling("technologies:vax#3", "technologies:vay#3", "F_nekro/valefar-assimilator/1",
        "F_nekro/valefar-assimilator/3", "F_nekro/valefar-assimilator/11")
def test_valefar_ten_sam_typ_ten_sam_zeton(registry: StaticDataRegistry) -> None:
    state = _state(registry, third="mahact")
    state.players["p2"].technologies = ["so2"]
    state.players["p3"].technologies = ["cl2"]
    technology.assimilate(state, "p1", "vax", "so2")
    owners = ["p2", "p3"]
    # No second token on a card that already has one.
    assert "so2" not in nekro.assimilable_techs(state, registry, "p1", owners)
    with pytest.raises(ValueError, match="Valefar Assimilator X"):
        nekro.apply_gain(state, registry, "p1", owners, {"technology": "cl2", "token": "vay"},
                         "abilities:technological_singularity")
    nekro.apply_gain(state, registry, "p1", owners, {"technology": "cl2", "token": "vax"},
                     "abilities:technological_singularity")
    p1 = state.players["p1"]
    assert p1.assimilated == {"vax": "cl2"}
    assert "so2" not in p1.technologies  # the previous copy is lost (11)


@ruling("F_nekro/valefar-assimilator/2", "F_nekro/valefar-assimilator/2.1",
        "F_nekro/valefar-assimilator/2.2")
def test_valefar_stan_wyczerpania_asymilatora(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    technology.assimilate(state, "p1", "vax", "ac2")
    exhaust.exhaust_technology(state, "p1", "ac2")
    assert {"vax", "ac2"} <= set(state.players["p1"].exhausted_technologies)
    # A new copy keeps the assimilator's exhausted state.
    technology.assimilate(state, "p1", "vax", "so2")
    assert {"vax", "so2"} <= set(state.players["p1"].exhausted_technologies)
    assert "ac2" not in state.players["p1"].exhausted_technologies
    # Passive text still works while exhausted: the unit variant is the copied one.
    p1 = state.players["p1"]
    inf = resolve_unit_variant(registry, p1.faction, p1.technologies, "infantry")
    assert inf is not None and inf.id == "sol_infantry2"
    exhaust.ready_all_technologies(state, "p1")  # status phase readies both
    assert state.players["p1"].exhausted_technologies == []


@ruling("F_nekro/valefar-assimilator/4", "F_nekro/valefar-assimilator/5")
def test_valefar_tylko_technologie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p2"].technologies = ["ac2", "nm"]
    targets = nekro.assimilable_techs(state, registry, "p1", ["p2"])
    assert set(targets) == {"ac2"}  # never the base unit, the mech or a generic technology
    state.players["p1"].technologies = ["dxa"]  # without an assimilator: no copy at all
    assert nekro.assimilable_techs(state, registry, "p1", ["p2"]) == {}


@ruling("F_nekro/valefar-assimilator/9")
def test_valefar_cel_adapt_new_strategies(registry: StaticDataRegistry) -> None:
    from src.core.objective_progress import View

    state = _state(registry)
    grid = grid_from_state(state, registry)
    assert _p_faction_techs(View(state, registry, grid, "p1")) == 0  # bare assimilators: never
    technology.assimilate(state, "p1", "vax", "ac2")
    assert _p_faction_techs(View(state, registry, grid, "p1")) == 1


@ruling("F_nekro/valefar-assimilator/11.2")
def test_valefar_utrata_prototype_war_sun(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    technology.assimilate(state, "p1", "vax", "pws2")
    state.systems[EMPTY].space_units = {"p1": {"warsun": 1}}
    technology.release_assimilated(state, "p1", "vax")
    assert state.systems[EMPTY].space_units.get("p1", {}).get("warsun", 0) == 0
    # With the generic War Sun the war suns stay (pair test).
    state.players["p1"].technologies.append("ws")
    technology.assimilate(state, "p1", "vax", "pws2")
    state.systems[EMPTY].space_units = {"p1": {"warsun": 1}}
    technology.release_assimilated(state, "p1", "vax")
    assert state.systems[EMPTY].space_units["p1"]["warsun"] == 1


@ruling("F_nekro/nekro-acidos/2", "F_nekro/valefar-assimilator-z/3")
def test_zeton_to_nie_zdobycie_technologii(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states = {nekro.COMMANDER: "unlocked"}
    work = state.clone()
    technology.assimilate(work, "p1", "vax", "ac2")
    assert not _offers(work, "p1", "Nekro Acidos")


# ============================================================================ Valefar Z


@ruling("breakthroughs:nekrobt#1", "breakthroughs:nekrobt#2", "F_nekro/valefar-assimilator-z/2",
        "F_nekro/valefar-assimilator-z/4")
def test_valefar_z_tekst_cudzego_flagowca(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="mahact")
    state.players["p1"].breakthrough_unlocked = True
    state.players["p2"].technologies = ["nm"]
    state = _combat(state)
    state.systems[EMPTY].space_units = {"p1": {"flagship": 1}, "p2": {"fighter": 2}}
    source = rules_hooks.HookSource(rules_hooks.SOURCE_UNIT, "mahact_flagship")
    assert source not in rules_hooks.owned_sources(state, "p1")
    done = _accept(_destroy(state, "p2", "fighter"), "p1", "Technological Singularity",
                   {"token": "z|p2"})
    assert done.players["p1"].assimilated_flagships == ["mahact"]
    assert source in rules_hooks.owned_sources(done, "p1")
    assert "nm" not in done.players["p1"].technologies  # instead of gaining
    # Arvicon Rex text on The Alastor: +2 (no foreign token in a Nekro fleet pool - z 4).
    assert mahact.arvicon_rex(done, "p1", {"base_type": "flagship"}) == 2
    # One Z token per faction sheet.
    assert nekro.z_targets(done, "p1", ["p2"]) == []


@ruling("F_nekro/valefar-assimilator-z/8")
def test_valefar_z_bez_atrybutow_jednostki(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="mahact")
    state.players["p1"].assimilated_flagships = ["mahact"]
    p1 = state.players["p1"]
    flagship = resolve_unit_variant(registry, p1.faction, p1.technologies, "flagship")
    assert flagship is not None and flagship.id == nekro.FLAGSHIP  # The Alastor's own stats


@ruling("F_nekro/valefar-assimilator-z/9")
def test_valefar_z_po_eliminacji(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="mahact")
    state.players["p1"].assimilated_flagships = ["mahact"]
    del state.players["p2"]
    state.seating_order = ["p1"]
    source = rules_hooks.HookSource(rules_hooks.SOURCE_UNIT, "mahact_flagship")
    assert source in rules_hooks.owned_sources(state, "p1")


# ================================================================================ Galactic Threat


AGENDA, OUTCOME = "regulations", "p2"  # an "elect a player" agenda: outcomes p1 / p2


def _agenda_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry)
    state.phase = Phase.AGENDA
    state.speaker_id = "p2"
    state.agenda = AgendaPhaseState(step=AgendaStep.REVEAL)
    state.decks.agenda_deck = [AGENDA]
    return state


@ruling("abilities:galactic_threat#3")
def test_galactic_threat_nie_glosuje(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    after = agenda_phase.reveal_agenda(state, registry, "p2")
    assert after.agenda is not None and "p1" in after.agenda.blocked
    assert "p2" not in after.agenda.blocked


@ruling("F_nekro/galactic-threat/2")
def test_galactic_threat_glos_z_elder_qanoj(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    with rules_hooks.temporary_hooks():
        rules_hooks.register(
            rules_hooks.POINT_AGENDA_VOTE_UNBLOCKABLE,
            rules_hooks.HookSource(rules_hooks.SOURCE_FACTION, "nekro"),
            rules_hooks.HookKind.PERMIT,
        )(lambda _s, _p, _c: True)
        after = agenda_phase.reveal_agenda(state, registry, "p2")
        assert after.agenda is not None and "p1" not in after.agenda.blocked


@ruling("abilities:galactic_threat#1", "F_nekro/galactic-threat/1", "F_nekro/galactic-threat/1.1")
def test_galactic_threat_przepowiednia(registry: StaticDataRegistry) -> None:
    after = agenda_phase.reveal_agenda(_agenda_state(registry), registry, "p2")
    offer = _offers(after, "p1", "Galactic Threat")[0]
    outcomes = {o["value"] for o in _inputs(after, registry, offer)[0]["options"]}
    assert after.agenda is not None and outcomes == set(after.agenda.outcomes)  # no abstain
    assert "abstain" not in outcomes
    with pytest.raises(ValueError):
        _accept(after, "p1", "Galactic Threat", {"outcome": "abstain"})
    done = _accept(after, "p1", "Galactic Threat", {"outcome": OUTCOME})
    assert nekro._prediction(done, "p1") is not None
    # Once per agenda phase.
    assert not nekro._can_predict(done, "p1", {})


def _resolved(state: GameState, outcome: str) -> GameState:
    work = state.clone()
    triggers.fire(work, GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER,
                  ctx={"agenda": AGENDA, "outcome": outcome})
    return work


@ruling("abilities:galactic_threat#2", "F_nekro/antivirus/1")
def test_galactic_threat_trafna_daje_technologie(registry: StaticDataRegistry) -> None:
    after = agenda_phase.reveal_agenda(_agenda_state(registry), registry, "p2")
    done = _accept(after, "p1", "Galactic Threat", {"outcome": OUTCOME})
    done.players["p2"].technologies = ["nm"]
    done.players["p2"].promissory_notes_in_play = []  # Antivirus does not matter here
    assert done.agenda is not None
    done.agenda.votes = {"p2": AgendaVote(outcome=OUTCOME, votes=3)}
    wrong = _resolved(done, "p1")
    assert not _offers(wrong, "p1", "Galactic Threat: gain")
    right = _resolved(done, OUTCOME)
    decision = _offers(right, "p1", "Galactic Threat: gain")[0]
    assert decision.mandatory
    gained = _accept(right, "p1", "Galactic Threat: gain", {"technology": "nm"})
    assert "nm" in gained.players["p1"].technologies


@ruling("F_nekro/galactic-threat/3", "F_nekro/galactic-threat/3.1")
def test_galactic_threat_remis_mowcy_to_nie_glos(registry: StaticDataRegistry) -> None:
    after = agenda_phase.reveal_agenda(_agenda_state(registry), registry, "p2")
    done = _accept(after, "p1", "Galactic Threat", {"outcome": OUTCOME})
    done.players["p2"].technologies = ["nm"]
    assert done.agenda is not None
    done.agenda.votes = {}  # nobody voted, the speaker decided
    right = _resolved(done, OUTCOME)
    assert not _offers(right, "p1", "Galactic Threat: gain")


# ========================================================================== Nekro Malleon (agent)


@ruling("leaders:nekroagent#1", "leaders:nekroagent#2")
def test_malleon_odrzuc_karte_za_2_tg(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p2"].private.action_cards = ["sabotage1"]
    after = _use(state, registry, "p1", "leader", nekro.AGENT, {"target": "p2"})
    assert leaders.state_of(after, registry, "p1", nekro.AGENT) == "exhausted"
    decision = _offers(after, "p2", "Nekro Malleon")[0]
    values = {o["value"] for o in _inputs(after, registry, decision)[0]["options"]}
    assert {"card|sabotage1", "pool|tactical", "decline"} <= values
    done = _accept(after, "p2", "Nekro Malleon", {"choice": "card|sabotage1"})
    assert done.players["p2"].trade_goods == 2
    assert done.players["p2"].private.action_cards == []


@ruling("F_nekro/nekro-malleon/1", "F_nekro/nekro-malleon/1.1")
def test_malleon_zeton_ze_strategii(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p2"].strategic_cc = 2
    after = _use(state, registry, "p1", "leader", nekro.AGENT, {"target": "p2"})
    done = _accept(after, "p2", "Nekro Malleon", {"choice": "pool|strategic"})
    assert done.players["p2"].strategic_cc == 1 and done.players["p2"].trade_goods == 2
    declined = _accept(after, "p2", "Nekro Malleon", {"choice": "decline"})
    assert declined.players["p2"].trade_goods == 0


@ruling("F_nekro/nekro-malleon/2")
def test_malleon_nie_w_trakcie_innej_zdolnosci(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.phase = Phase.STATUS
    assert nekro._agent_window(state, registry, "p1") is not None
    state.phase = Phase.ACTION
    assert nekro._agent_window(state, registry, "p1") is None


# ======================================================================== Nekro Acidos (commander)


@ruling("leaders:nekrocommander#unlock")
def test_acidos_odblokowanie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    fn = leaders.unlock_predicate(registry, nekro.COMMANDER)
    assert fn is not None and not fn(state, registry, "p1")  # dxa + bare vax/vay = 1
    technology.assimilate(state, "p1", "vax", "ac2")
    state.players["p1"].technologies.append("nm")
    assert fn(state, registry, "p1")  # dxa, nm, ac2 (vax copying)


@ruling("leaders:nekrocommander#1", "F_nekro/nekro-acidos/1")
def test_acidos_po_zdobyciu_technologii(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.decks.action_card_deck = ["sabotage1", "sabotage2"]
    locked = state.clone()
    technology.grant_technology(locked, "p1", "nm")
    assert not _offers(locked, "p1", "Nekro Acidos")  # still locked at the unlocking gain
    state.players["p1"].leader_states = {nekro.COMMANDER: "unlocked"}
    work = state.clone()
    technology.grant_technology(work, "p1", "nm")
    done = _accept(work, "p1", "Nekro Acidos")
    assert done.players["p1"].private.action_cards == ["sabotage1"]


# ================================================================= UNIT.DSGN.FLAYESH (hero)


@ruling("leaders:nekrohero#1", "leaders:nekrohero#2", "leaders:nekrohero#3",
        "leaders:nekrohero#4", "F_nekro/unit-dsgn-flayesh-polymorphic-algorithm/1",
        "F_nekro/unit-dsgn-flayesh-polymorphic-algorithm/2")
def test_flayesh_pozera_planete(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].leader_states = {nekro.HERO: "unlocked"}
    state.systems[WELLON].space_units = {"p1": {"cruiser": 1}}
    state.systems[WELLON].planet_units = {"wellon": {"p2": {"infantry": 2, "pds": 1}}}
    state.systems[WELLON].planet_owners = {"wellon": "p2"}
    fields = faction_components.form(state, registry, "p1", "leader", nekro.HERO)["inputs"]
    planets = {o["value"] for o in fields[0]["options"]}
    assert planets == {"mordaiii", "wellon"} or planets == {"wellon"}
    techs = {o["value"] for o in fields[1]["options"]}
    assert techs and all(
        technology.tech_color(registry.technologies[t]) in ("CYBERNETIC", "BIOTIC", "WARFARE",
                                                             "PROPULSION")
        for t in techs
    )  # unit upgrades have no colour
    tech = next(t for t in sorted(techs)
                if technology.tech_color(registry.technologies[t]) == "CYBERNETIC")
    with pytest.raises(ValueError, match="specialty"):
        _use(state, registry, "p1", "leader", nekro.HERO, {"planet": "tarmann"})
    after = _use(state, registry, "p1", "leader", nekro.HERO,
                 {"planet": "wellon", "technology": tech})
    assert after.systems[WELLON].planet_units["wellon"].get("p2", {}) == {}
    assert after.players["p1"].trade_goods == 3  # Wellon 1 + 2
    assert tech in after.players["p1"].technologies
    assert leaders.state_of(after, registry, "p1", nekro.HERO) == "purged"
    assert not _offers(after, "p1", "Technological Singularity")  # outside a combat (1)


# ===================================================================================== Antivirus


def _note_in_hand(state: GameState, registry: StaticDataRegistry) -> str:
    note = next(n for n in state.players["p1"].private.promissory_notes if "antivirus" in n) \
        if state.players["p1"].private.promissory_notes else "antivirus"
    state.players["p1"].private.promissory_notes = []
    state.players["p2"].private.promissory_notes = [note]
    return note


@ruling("promissory_notes:antivirus#1", "promissory_notes:antivirus#2", "F_nekro/antivirus/2",
        "F_nekro/antivirus/2.1", "F_nekro/antivirus/3")
def test_antivirus_chroni_przed_osobliwoscia(registry: StaticDataRegistry) -> None:
    state = _fight_setup(registry, ["nm"])
    note = _note_in_hand(state, registry)
    # In the hand it does nothing (3).
    assert _offers(_destroy(state, "p2", "fighter"), "p1", "Technological Singularity")
    promissory_notes.place_in_play(state, "p2", note)
    assert nekro.antivirus_protects(state, "p2")
    assert not _offers(_destroy(state, "p2", "fighter"), "p1", "Technological Singularity")
    # Only a combat participant may play it (2); the Nekro need not fight (2.1).
    assert nekro._antivirus_condition(state, registry, "p2", None) is None  # type: ignore[arg-type]
    third = _state(registry, third="mahact")
    third.active_combat = ActiveCombat(kind="space", position=EMPTY, attacker="p2",
                                       defender="p3")
    assert nekro._antivirus_condition(third, registry, "p3", None) is None  # type: ignore[arg-type]
    assert nekro._antivirus_condition(third, registry, "p1", None) is not None  # type: ignore[arg-type]


@ruling("promissory_notes:antivirus#3", "F_nekro/antivirus/4", "F_nekro/antivirus/5",
        "F_nekro/antivirus/6")
def test_antivirus_wraca_po_aktywacji(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    note = _note_in_hand(state, registry)
    promissory_notes.place_in_play(state, "p2", note)
    state.systems[TARMANN].planet_units = {"tarmann": {"p1": {"pds": 1}}}  # structures only
    work = state.clone()
    triggers.fire(work, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": TARMANN})
    assert note not in work.players["p2"].promissory_notes_in_play
    assert note in work.players["p1"].private.promissory_notes
    # Another system without Nekro units: stays.
    other = state.clone()
    triggers.fire(other, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": EMPTY_B})
    assert note in other.players["p2"].promissory_notes_in_play
    assert promissory_play.notes_in_play(other, registry, "p2", nekro.ANTIVIRUS)


# ==================================================================================== The Alastor


def _alastor_state(registry: StaticDataRegistry) -> GameState:
    state = _state(registry)
    state.systems[EMPTY].space_units = {"p1": {"flagship": 1, "infantry": 3, "mech": 1},
                                        "p2": {"cruiser": 2}}
    return _combat(state)


@ruling("units:nekro_flagship#1", "F_nekro/the-alastor/1", "F_nekro/the-alastor/7")
def test_alastor_sily_naziemne_jak_statki(registry: StaticDataRegistry) -> None:
    state = _alastor_state(registry)
    work = state.clone()
    triggers.fire(work, GameEvent.COMBAT, Moment.START, subject="p1",
                  ctx={"kind": "space", "position": EMPTY, "attacker": "p1", "defender": "p2"})
    offer = _offers(work, "p1", "The Alastor")[0]
    fields = _inputs(work, registry, offer)
    assert {f["key"] for f in fields} == {"infantry", "mech"}
    assert all("auto" not in f for f in fields)
    done = _accept(work, "p1", "The Alastor", {"infantry": 2, "mech": 1})
    grid = grid_from_state(done, registry)
    units = {u.base_type: u for u in battle_units.combat_units(
        done, grid, registry, kind="space", position=EMPTY, planet=None, player_id="p1")}
    assert units["infantry"].count == 2 and "mech" in units
    ships = ship_roles.space_ships(done, registry, "p1", EMPTY)
    assert ships["infantry"] == 2  # ships for Assault Cannon / objectives (1.1)
    # The fleet pool ignores them (7).
    assert fleet_pool.fleet_report(done, EMPTY, "p1").ships == {"flagship": 1}


@ruling("F_nekro/the-alastor/5")
def test_alastor_zniszczony_sily_zostaja(registry: StaticDataRegistry) -> None:
    state = _alastor_state(registry)
    assert state.active_combat is not None
    state.active_combat.ground_as_ships = {"p1": {"infantry": 3}}
    after = _destroy(state, "p1", "flagship")
    grid = grid_from_state(after, registry)
    units = battle_units.combat_units(after, grid, registry, kind="space", position=EMPTY,
                                      planet=None, player_id="p1")
    assert [u.base_type for u in units] == ["infantry"]


def test_alastor_bez_wyboru_nie_walcza(registry: StaticDataRegistry) -> None:
    state = _alastor_state(registry)
    grid = grid_from_state(state, registry)
    units = battle_units.combat_units(state, grid, registry, kind="space", position=EMPTY,
                                      planet=None, player_id="p1")
    assert {u.base_type for u in units} == {"flagship"}


# ======================================================================================== Mordred


@ruling("units:nekro_mech#1", "F_nekro/mordred/1")
def test_mordred_plus_2_przeciw_asymilowanemu(registry: StaticDataRegistry) -> None:
    state = _combat(_state(registry), "ground", TARMANN, "tarmann")
    ctx = {"base_type": "mech"}
    assert nekro.mordred(state, "p1", ctx) == 0
    state.players["p2"].technologies = ["ac2", "so2"]
    technology.assimilate(state, "p1", "vax", "ac2")
    technology.assimilate(state, "p1", "vay", "so2")
    assert nekro.mordred(state, "p1", ctx) == 2  # +2 once, not +4
    assert nekro.mordred(state, "p1", {"base_type": "infantry"}) == 0
