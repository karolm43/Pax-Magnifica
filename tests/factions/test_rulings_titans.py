"""The Titans of Ul — remaining F_ul rulings (``docs/rules_tirules/F_ul.md``).

Board helpers are shared with ``test_titans.py`` (same map: 101 = Titans home,
102 = Wellon, 103 = New Albion / Starpoint, 104 = Thibah (p2), 105 = Tar'mann, 106 = Quann).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.core import (
    board_graph,
    capture,
    control,
    faction_components,
    faction_tokens,
    objective_progress,
    planet_stats,
    retreat,
    rules_hooks,
    strategic_action,
    triggers,
)
from src.core.game_state import ActiveCombat
from src.core.hooks.factions import cabal, titans
from src.core.registry import StaticDataRegistry
from tests.factions.test_titans import (
    ALBION,
    ARENA,
    EAST,
    ELYSIUM,
    FAR,
    HOME,
    RIVAL,
    SLEEPER,
    TARMANN,
    THIBAH,
    WELLON,
    _accept,
    _activate,
    _explored,
    _grid,
    _offers,
    _own,
    _sleeper,
    _state,
    _terraform,
    _units,
)
from tests.rulings import ruling

THUNDERS_EDGE = "thundersedge"


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


# ------------------------------------------------------------------------------ Terragenesis


@ruling("F_ul/terragenesis/1")
def test_terragenesis_jeden_zeton_na_planete(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    _sleeper(state, ARENA, WELLON)
    assert not _offers(_explored(state, WELLON), "p1", "Terragenesis")
    with pytest.raises(ValueError, match="already"):
        faction_tokens.place(state, "p1", SLEEPER, ARENA, WELLON)
    assert len([z for _p, z in faction_tokens.tokens_of(state, "p1", SLEEPER) if z == WELLON]) == 1


# ---------------------------------------------------------------------------------- Awaken


@ruling("F_ul/awaken/3")
def test_awaken_obok_dwoch_cudzych_pds(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    state.systems[ARENA].planet_units[WELLON]["p2"] = {"pds": 2}
    _sleeper(state, ARENA, WELLON)
    activated = _activate(state, registry, ARENA)
    offer = _offers(activated, "p1", "Awaken")[0]
    values = {o["value"] for o in titans.awaken_inputs(activated, registry, "p1", offer.ctx)[0][
        "options"]}
    assert "pds" in values  # two PDS of ANOTHER player do not block
    after = triggers.accept_offer(activated, "p1", offer.id, {f"sleeper:{WELLON}": "pds"})
    assert _units(after, ARENA, WELLON)["pds"] == 1
    # Two of the Titans' own PDS do block placing a third.
    own = _state()
    _own(own, ARENA, WELLON, units={"pds": 2})
    _sleeper(own, ARENA, WELLON)
    activated = _activate(own, registry, ARENA)
    offer = _offers(activated, "p1", "Awaken")[0]
    values = {o["value"] for o in titans.awaken_inputs(activated, registry, "p1", offer.ctx)[0][
        "options"]}
    assert values == {"keep"}


@ruling("F_ul/awaken/4")
def test_awaken_walka_naziemna_w_kroku_invasion(registry: StaticDataRegistry) -> None:
    from tests.factions.test_titans import invasion_common_contested

    state = _state()
    _own(state, EAST, ALBION, pid="p2", units={"infantry": 1})
    _sleeper(state, EAST, ALBION)
    after = _accept(_activate(state, registry, EAST), "p1", "Awaken",
                    {f"sleeper:{ALBION}": "pds"})
    assert after.systems[EAST].planet_owners[ALBION] == "p2"  # nothing resolved yet
    assert _units(after, EAST, ALBION)["pds"] == 1
    assert invasion_common_contested(after, registry, EAST) == [ALBION]


@ruling("F_ul/awaken/6")
def test_zeton_zostaje_po_zmianie_kontroli(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    _sleeper(state, ARENA, WELLON)
    state.systems[ARENA].planet_units[WELLON] = {"p2": {"infantry": 1}}
    state.players["p1"].controlled_planets.remove(WELLON)
    control.set_planet_control(state, ARENA, WELLON, "p2", registry)
    assert state.systems[ARENA].planet_owners[WELLON] == "p2"
    assert faction_tokens.on_planet(state, WELLON, SLEEPER) == "p1"
    after = _accept(_activate(state, registry, ARENA), "p1", "Awaken",
                    {f"sleeper:{WELLON}": "pds"})
    assert _units(after, ARENA, WELLON)["pds"] == 1
    assert faction_tokens.on_planet(after, WELLON, SLEEPER) is None


@ruling("F_ul/awaken/7")
def test_odwrot_do_systemu_z_zetonem_bez_awaken(registry: StaticDataRegistry) -> None:
    state = _state()
    _own(state, ARENA, WELLON, units={"infantry": 1})
    _sleeper(state, ARENA, WELLON)
    state.active_system = EAST
    state.systems[EAST].space_units = {"p1": {"cruiser": 1}, "p2": {"destroyer": 1}}
    state.active_combat = ActiveCombat(kind="space", position=EAST, attacker="p1",
                                       defender="p2")
    assert ARENA in retreat.retreat_destinations(state, _grid(state, registry), EAST, "p1")
    after, _ = retreat.perform_retreat(state, _grid(state, registry), registry, EAST, "p1", ARENA)
    assert _units(after, ARENA, "space") == {"cruiser": 1}
    assert not _offers(after, "p1", "Awaken")  # the system was not activated
    assert titans.awaken_sleepers(after, "p1", ARENA) == []
    assert faction_tokens.on_planet(after, WELLON, SLEEPER) == "p1"


# --------------------------------------------------------------------------- Terraform


@ruling("F_ul/terraform/2.1")
def test_terraform_po_przejeciu_przez_titans(registry: StaticDataRegistry) -> None:
    after = _terraform(_state(), registry, THIBAH)
    after.systems[RIVAL].planet_units[THIBAH] = {"p1": {"infantry": 1}}
    after.players["p2"].controlled_planets.remove(THIBAH)
    control.set_planet_control(after, RIVAL, THIBAH, "p1", registry)
    assert THIBAH in after.players["p1"].controlled_planets
    # The card stays attached to the planet, now in the Titans' play area - not in their hand.
    assert after.planet_attachments[THIBAH] == [titans.TERRAFORM]
    assert titans.TERRAFORM not in after.players["p1"].private.promissory_notes
    assert planet_stats.resources_of(after, registry, THIBAH) == 2
    assert set(planet_stats.traits(after, registry, THIBAH)) >= {
        "cultural", "hazardous", "industrial"
    }


@ruling("F_ul/terraform/5")
def test_terraform_na_thunders_edge(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[FAR].added_planets = [THUNDERS_EDGE]
    _own(state, FAR, THUNDERS_EDGE, pid="p2", units={"infantry": 1})
    assert THUNDERS_EDGE in titans.terraform_targets(state, "p2")
    base = registry.planets[THUNDERS_EDGE]
    after = _terraform(state, registry, THUNDERS_EDGE)
    assert after.planet_attachments[THUNDERS_EDGE] == [titans.TERRAFORM]
    assert planet_stats.resources_of(after, registry, THUNDERS_EDGE) == (base.resources or 0) + 1
    assert planet_stats.influence_of(after, registry, THUNDERS_EDGE) == (base.influence or 0) + 1


# --------------------------------------------------------------------------- Hel-Titan


@ruling("F_ul/heltitan/4")
def test_vortex_nie_celuje_w_hel_titana(registry: StaticDataRegistry) -> None:
    state = _state(other="cabal")
    state.systems[RIVAL].planet_units[THIBAH]["p2"]["spacedock"] = 1
    _own(state, FAR, TARMANN, units={"pds": 1, "infantry": 1})
    assert not capture.capturable("pds")
    targets = cabal._vortex_targets(state, "p2")
    assert ("p1", "infantry", FAR, TARMANN) in targets
    assert not [t for t in targets if t[1] == "pds"]


# -------------------------------------------------------------------- Geoform (Elysium)


@ruling("F_ul/ul-the-progenitor-geoform/2")
def test_elysium_z_geoform_liczy_sie_jako_attachment(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states[titans.HERO] = "unlocked"
    grid = _grid(state, registry)
    before = objective_progress.progress(state, registry, grid, "p1", "ancient_monuments")
    work = state.clone()
    assert faction_components.run_action_effect(work, registry, "p1", f"leader:{titans.HERO}", {})
    assert titans.HERO in work.planet_attachments[ELYSIUM]
    after = objective_progress.progress(work, registry, grid, "p1", "ancient_monuments")
    assert before is not None and after == before + 1


# ------------------------------------------------------------------------- Hecatoncheires


@ruling("F_ul/hecatoncheires/6")
def test_hecatoncheires_przy_obu_strukturach_construction(registry: StaticDataRegistry) -> None:
    state = strategic_action.play_strategy_card(_state(), registry, "p1", 4)
    state = strategic_action.submit_primary_step(state, registry, "p1", {"option": "structure"})
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"planet": ELYSIUM, "structure": "mech"}
    )
    assert state.pending_strategy is not None
    assert state.pending_strategy.step == "place_structure_2"
    state = strategic_action.submit_primary_step(
        state, registry, "p1", {"planet": ELYSIUM, "structure": "mech"}
    )
    assert _units(state, HOME, ELYSIUM) == {"spacedock": 1, "infantry": 4, "mech": 2}


# ---------------------------------------------------------------- Slumberstate Computing


@ruling("F_ul/slumberstate-computing/1")
def test_slumberstate_najwyzej_jeden_zeton_na_cudzej_planecie(
    registry: StaticDataRegistry,
) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    assert (THIBAH, "p2") in titans.consent_targets(state, "p1")
    _own(state, FAR, TARMANN, pid="p2", units={"infantry": 1})  # another target stays open
    _sleeper(state, RIVAL, THIBAH)
    assert (THIBAH, "p2") not in titans.consent_targets(state, "p1")
    with pytest.raises(ValueError, match="valid option for: Planet for a sleeper token"):
        faction_components.play(state, registry, "p1", "breakthrough", titans.BREAKTHROUGH,
                                {"planet": THIBAH, "source": "supply"})


@ruling("F_ul/slumberstate-computing/4")
def test_slumberstate_zgoda_dotyczy_wskazanej_planety(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    _own(state, FAR, TARMANN, pid="p2", units={"infantry": 1})
    asked, _ = faction_components.play(state, registry, "p1", "breakthrough", titans.BREAKTHROUGH,
                                       {"planet": THIBAH, "source": "supply"})
    offer = _offers(asked, "p2", "Slumberstate")[0]
    assert offer.ctx["planet"] == THIBAH  # the request names the planet
    allowed = triggers.accept_offer(asked, "p2", offer.id, {"answer": "allow"})
    assert faction_tokens.on_planet(allowed, THIBAH, SLEEPER) == "p1"
    assert faction_tokens.on_planet(allowed, TARMANN, SLEEPER) is None
