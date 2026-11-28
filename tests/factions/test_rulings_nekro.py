"""The Nekro Virus — rulings of OTHER components that involve the Nekro (RULES.md 62.24).

Cross-file contract: ``F_<other faction>.md`` / ``C_<type>.md`` points that waited for the Nekro
(``requires: faction:nekro`` in ``tests/rulings_status.json``) plus the remaining F_nekro points
that need another faction or card. Board and helpers: ``test_nekro.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    agenda_phase,
    battle,
    battle_units,
    research_offer,
    rules_hooks,
    technology,
    triggers,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import GameEvent, Moment
from src.core.game_state import ActiveCombat, GameState
from src.core.hooks import agendas_directives, agendas_laws, relics_passive, technologies_combat
from src.core.hooks.action_cards_economy import divert_funding
from src.core.hooks.factions import cabal, jolnar, nekro, winnu
from src.core.hooks.reactions_combat import _prototype_options
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from tests.factions.test_nekro import (
    EMPTY,
    _agenda_state,
    _combat,
    _destroy,
    _offers,
    _state,
)
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    from src.core import board_graph

    rules_hooks.bind_registry(registry)
    yield
    board_graph.bind_grid_provider(None)


def _alastor(state: GameState, units: dict[str, int], rival: dict[str, int]) -> GameState:
    state.systems[EMPTY].space_units = {"p1": {"flagship": 1, **units}, "p2": dict(rival)}
    _combat(state)
    assert state.active_combat is not None
    state.active_combat.ground_as_ships = {
        "p1": {bt: n for bt, n in units.items() if bt in ("infantry", "mech")}
    }
    return state


# ================================================================================ Xxcha / agenda


@ruling("F_xxcha/elder-qanoj/4", "F_nekro/galactic-threat/2")
def test_nekro_z_sojuszem_xxcha_glosuje(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    xxcha = state.players["p2"]
    xxcha.faction = "xxcha"
    xxcha.leader_states = {"xxchacommander": "unlocked"}
    state.players["p1"].promissory_notes_in_play = [f"{xxcha.color}_an"]
    after = agenda_phase.reveal_agenda(state, registry, "p2")
    assert after.agenda is not None and "p1" not in after.agenda.blocked
    # Without the Alliance the Nekro cannot vote (pair test).
    state.players["p1"].promissory_notes_in_play = []
    blocked = agenda_phase.reveal_agenda(state, registry, "p2")
    assert blocked.agenda is not None and "p1" in blocked.agenda.blocked


@ruling("C_agendas/committee-formation/3")
def test_committee_formation_bez_glosowania(registry: StaticDataRegistry) -> None:
    state = _agenda_state(registry)
    state.decks.agenda_laws = {"committee": "p1"}
    after = agenda_phase.reveal_agenda(state, registry, "p2")
    assert _offers(after, "p1", "Committee Formation")


@ruling("C_agendas/antiintellectual-revolution/2")
def test_revolution_against_liczy_asymilatory(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    planets = ["mordaiii", "a", "b", "c", "d"]
    state.players["p1"].controlled_planets = planets
    assert technology.owned_cards(state, "p1") == ["dxa", "vax", "vay"]
    technology.assimilate(state, "p1", "vax", "ac2")
    # The copy is not an owned card: still 3 (the assimilator counts, copying or not).
    assert technology.owned_cards(state, "p1") == ["dxa", "vax", "vay"]
    ready, count = agendas_directives._revolution_targets(state, "p1")
    assert count == min(3, len(ready))


@ruling("C_agendas/publicize-weapon-schematics/4")
def test_schematics_kopia_war_sun(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    assert not agendas_laws.owns_war_sun_tech(state, registry, "p1")
    technology.assimilate(state, "p1", "vax", "pws2")
    assert agendas_laws.owns_war_sun_tech(state, registry, "p1")


@ruling("C_agendas/antiintellectual-revolution/1.1", "C_relics/the-prophets-tears/2")
def test_propagation_law_i_lzy(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.decks.agenda_laws = {"revolution": "for"}
    state.players["p1"].relics = ["prophetstears"]
    state.systems[EMPTY].space_units = {"p1": {"cruiser": 1}}
    tech = next(t for t in technology.tech_pool(state, registry, "p1").values()
                if not t.requirements and not t.faction and "UNITUPGRADE" not in t.types)
    after = technology.research(state, registry, "p1", tech.id)
    assert not _offers(after, "p1", "Anti-Intellectual Revolution")
    assert _offers(after, "p1", "Prophet's Tears")


# ======================================================================== Technology & research


@ruling("F_nekro/propagation/1", "F_nekro/propagation/1.1")
def test_propagation_sekundarna_technology_placi(registry: StaticDataRegistry) -> None:
    from src.core.strategy_cards.base import CardContext
    from src.core.strategy_cards.technology import _card_cost, _secondary

    state = _state(registry)
    state.players["p1"].trade_goods = 4
    tech = next(t for t in technology.tech_pool(state, registry, "p1").values()
                if not t.requirements and not t.faction and "UNITUPGRADE" not in t.types)
    _secondary(state, CardContext(registry=registry), "p1",
               {"tech": tech.id, "planets": [], "trade_goods": 4})
    assert state.players["p1"].trade_goods == 0  # still pays four resources (1)
    assert tech.id not in state.players["p1"].technologies
    assert _offers(state, "p1", "Propagation")
    # Minister of Sciences: free (1.1).
    state.decks.agenda_laws = {"minister_sciences": "p1"}
    assert _card_cost(state, "p1", 4) == 0


@ruling("F_nekro/propagation/4", "F_nekro/propagation/4.1")
def test_reveal_prototype_wymaga_ulepszenia(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[EMPTY].space_units = {"p1": {"dreadnought": 1, "fighter": 2},
                                        "p2": {"cruiser": 1}}
    _combat(state)
    # Every colour covered, so the upgrades are researchable (what the card "could research").
    state.players["p1"].technologies += [
        t.id for t in technology.generic_pool(registry).values()
        if "UNITUPGRADE" not in t.types and t.id != "asc"
    ]
    options = {t.id for t in _prototype_options(state, registry, "p1")}
    assert {"dn2", "ff2"} <= options
    state.players["p1"].technologies += ["dn2", "ff2"]
    assert _prototype_options(state, registry, "p1") == []  # nothing left to research (4.1)


@ruling("C_action_cards/divert-funding/6")
def test_divert_funding_daje_zetony(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].technologies.append("nm")
    work = state.clone()
    divert_funding(work, registry, "p1", {"return_technology": "nm"})
    assert "nm" not in work.players["p1"].technologies
    offer = next(o for o in triggers.offers_for(work, "p1") if "Divert Funding" in o.label)
    view = research_offer.research_input(work, registry, "p1", 0)["research"]
    tech = next(r["id"] for r in view["tree"] if r["status"] == "available")
    done = triggers.accept_offer(work, "p1", offer.id, {"research": {"tech": tech}})
    assert tech not in done.players["p1"].technologies
    assert _offers(done, "p1", "Propagation")


@ruling("C_relics/book-of-latvinia/3")
def test_book_of_latvinia_szesc_zetonow(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    no_prereq = [t.id for t in technology.tech_pool(state, registry, "p1").values()
                 if not technology.prerequisites(t)]
    state.players["p1"].technologies = sorted(set(state.players["p1"].technologies)
                                              | set(no_prereq))
    options = relics_passive._no_prerequisite_techs(state, registry, "p1")
    assert len(options) >= 2  # owned ones too: the Nekro "would research" them
    work = state.clone()
    chosen = [options[0].id, options[1].id]
    relics_passive.book_gained(work, "p1", {"params": {"technologies": chosen}})
    gained = 0
    for _ in range(2):
        offer = _offers(work, "p1", "Propagation")[0]
        work = triggers.accept_offer(work, "p1", offer.id,
                                     {f"token_{k}": "fleet" for k in (1, 2, 3)})
        gained += 3
    assert gained == 6 and work.players["p1"].fleet_cc == 3 + 6


# ================================================================================ Valefar copies


@ruling("F_mentak/corsair/3", "F_mentak/corsair/4")
def test_valefar_corsair_i_cruiser_ii(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="mentak")
    mentak = state.players["p2"]
    mentak.technologies = ["cr2"]
    mentak.breakthrough_unlocked = True
    assert "cr2" in nekro.gainable_techs(state, registry, "p1", ["p2"])  # Cruiser II under it
    targets = nekro.assimilable_techs(state, registry, "p1", ["p2"])
    assert all("corsair" not in t for t in targets)  # the Corsair card is not a technology


@ruling("F_jol_nar/rin-the-masters-legacy-genetic-memory/5", "F_nekro/valefar-assimilator/8")
def test_valefar_zostaje_po_wymianie_jol_nar(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="jolnar")
    state.players["p2"].technologies = ["scc"]
    technology.assimilate(state, "p1", "vax", "scc")
    technology.return_technology(state, "p2", "scc")  # Genetic Memory swap
    assert state.players["p1"].assimilated == {"vax": "scc"}


@ruling("F_jol_nar/rin-the-masters-legacy-genetic-memory/4")
def test_genetic_memory_bez_acidos(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="jolnar")
    jol = state.players["p2"]
    jol.leader_states = {jolnar.HERO: "unlocked"}
    jol.technologies = ["nm"]
    state.players["p1"].leader_states = {nekro.COMMANDER: "unlocked"}
    jol.promissory_notes_in_play = [f"{state.players['p1'].color}_an"]
    work = state.clone()
    jolnar.genetic_memory(work, registry, "p2", {"tech:nm": "sdn"})
    assert "sdn" in work.players["p2"].technologies
    assert not _offers(work, "p2", "Nekro Acidos")
    # An ordinary gain through the Alliance does offer it (pair test).
    other = state.clone()
    technology.grant_technology(other, "p2", "sdn")
    assert _offers(other, "p2", "Nekro Acidos")


@ruling("F_nekro/valefar-assimilator/7", "F_nekro/the-alastor/6.1",
        "F_nekro/valefar-assimilator-z/1")
def test_valefar_memoria_ii_zastepuje_alastor(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="nomad")
    technology.assimilate(state, "p1", "vax", "m2")
    p1 = state.players["p1"]
    flagship = resolve_unit_variant(registry, p1.faction, p1.technologies, "flagship")
    assert flagship is not None and flagship.id == "nomad_flagship2"
    sources = rules_hooks.owned_sources(state, "p1")
    assert rules_hooks.HookSource(rules_hooks.SOURCE_UNIT, nekro.FLAGSHIP) not in sources
    # Z tokens keep granting flagship texts on top of the copied Memoria II (z 1).
    p1.assimilated_flagships = ["mahact"]
    assert rules_hooks.HookSource(rules_hooks.SOURCE_UNIT, "mahact_flagship") in (
        rules_hooks.owned_sources(state, "p1")
    )


@ruling("F_vuilraith/it-feeds-on-carrion-dimensional-anchor/6")
def test_valefar_dimensional_tear_ii(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="cabal")
    state.systems[EMPTY].space_units = {"p1": {"spacedock": 1}}
    assert EMPTY not in cabal._tear_positions(state)
    technology.assimilate(state, "p1", "vax", "dt2")
    assert EMPTY in cabal._tear_positions(state)  # the Nekro docks are Dimensional Tears too


@ruling("F_nekro/valefar-assimilator-z/5", "R_capture/notes/3")
def test_valefar_z_terror_between(registry: StaticDataRegistry) -> None:
    state = _state(registry, other="cabal")
    state.players["p1"].assimilated_flagships = ["cabal"]
    state.systems[EMPTY].space_units = {"p1": {"flagship": 1, "cruiser": 1}, "p2": {"fighter": 1}}
    ctx: dict[str, Any] = {"position": EMPTY, "player": "p2", "base_type": "fighter"}
    assert rules_hooks.permits(rules_hooks.POINT_CAPTURE_DESTROYED, state, "p1", ctx)
    own = {**ctx, "player": "p1", "base_type": "cruiser"}
    assert rules_hooks.permits(rules_hooks.POINT_CAPTURE_DESTROYED, state, "p1", own)


# ==================================================================================== The Alastor


@ruling("C_technology/assault-cannon/3.2", "F_nekro/the-alastor/1.1", "F_nekro/the-alastor/9")
def test_alastor_assault_cannon(registry: StaticDataRegistry) -> None:
    state = _alastor(_state(registry), {"infantry": 2}, {"cruiser": 2})
    state.players["p1"].technologies.append("asc")
    ctx = {"kind": "space", "position": EMPTY, "attacker": "p1", "defender": "p2"}
    assert technologies_combat._assault_cannon_ready(state, "p1", ctx)
    assert state.active_combat is not None
    state.active_combat.ground_as_ships = {}
    assert not technologies_combat._assault_cannon_ready(state, "p1", ctx)


@ruling("F_winnu/salai-sai-corian/2", "F_nekro/the-alastor/1.2")
def test_alastor_salai_sai_corian(registry: StaticDataRegistry) -> None:
    state = _alastor(_state(registry, other="winnu"), {"infantry": 3}, {"flagship": 1})
    state.active_combat = ActiveCombat(kind="space", position=EMPTY, attacker="p2",
                                       defender="p1", ground_as_ships={"p1": {"infantry": 3}})
    extra = winnu.salai_sai_corian(state, "p2", {"base_type": "flagship", "kind": "space"})
    unit = registry.units[winnu.FLAGSHIP]
    assert extra == 4 - (unit.combat_die_count or 1)  # The Alastor + 3 infantry


@ruling("F_argent/raid-formation/6")
def test_alastor_raid_formation(registry: StaticDataRegistry) -> None:
    state = _alastor(_state(registry, other="argent"), {"mech": 1}, {"destroyer": 2})
    fresh, _hurt = battle.raid_targets(state, grid_from_state(state, registry), registry, "p1")
    assert fresh.get("mech") == 1 and fresh.get("flagship") == 1


@ruling("C_relics/metali-void-shielding/5")
def test_alastor_metali_void_shielding(registry: StaticDataRegistry) -> None:
    state = _alastor(_state(registry), {"infantry": 2}, {"cruiser": 2})
    state.players["p1"].relics = ["metalivoidshielding"]
    units = battle_units.combat_units(state, grid_from_state(state, registry), registry,
                                      kind="space", position=EMPTY, planet=None, player_id="p1")
    infantry = next(u for u in units if u.base_type == "infantry")
    assert infantry.granted == 1


@ruling("F_nekro/the-alastor/3")
def test_alastor_zniszczony_przed_uzyciem(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.systems[EMPTY].space_units = {"p1": {"flagship": 1, "infantry": 2}, "p2": {"cruiser": 1}}
    _combat(state)
    ctx = {"kind": "space", "position": EMPTY}
    assert nekro._alastor_ready(state, "p1", ctx)
    gone = _destroy(state, "p1", "flagship")
    assert not nekro._alastor_ready(gone, "p1", ctx)  # stale offer is dropped


@ruling("leaders:nekrohero#unlock")
def test_flayesh_odblokowanie(registry: StaticDataRegistry) -> None:
    from src.core import leaders

    state = _state(registry)
    fn = leaders.unlock_predicate(registry, nekro.HERO)
    assert fn is not None and not fn(state, registry, "p1")
    state.players["p1"].scored_secrets = ["a", "b", "c"]
    assert fn(state, registry, "p1")


def test_singularity_bez_gry_poza_walka_o_tym_systemie(registry: StaticDataRegistry) -> None:
    """Destruction in ANOTHER system during a combat (e.g. a Space Cannon elsewhere) is not
    "during this combat"."""
    state = _state(registry)
    state.players["p2"].technologies = ["nm"]
    state.systems[EMPTY].space_units = {"p1": {"cruiser": 1}, "p2": {"cruiser": 1}}
    _combat(state, position="103")
    work = state.clone()
    triggers.fire(work, GameEvent.UNIT_DESTROYED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "base_type": "cruiser", "zone": "space",
                       "position": EMPTY, "count": 1})
    assert not _offers(work, "p1", "Technological Singularity")


pytest_plugins: list[str] = []
