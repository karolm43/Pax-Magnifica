"""The Naaz-Rokha Alliance — komplet komponentów frakcji (RULES.md 62.15) i rulingi F_naaz_rokha.

Scenariusze przez prawdziwe API (ACTION, oferty, notka, okno eksploracji): ``test_flows_naaz.py``.
Statusy bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core import (
    battle,
    capacity,
    exploration,
    faction_components,
    fleet_pool,
    leaders,
    objective_events,
    production,
    rules_hooks,
    ship_roles,
    space_cannon,
    strategic_action,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    ExplorationState,
    ExploreCurrent,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hooks.factions import naaz
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.unit_ops import UnitCause
from tests.factions.completeness import missing_components
from tests.rulings import ruling

# 101 = dom Naaz (57: Naazir, Rokha), 102 = Vefutii (20, hazardous), 103 = Thibah (21, p2),
# 104 = Tarmann (22), 105 = Olergodt (TE 101: hazardous + cultural); 000 = Mecatol.
HOME, PLAIN, RIVAL, FAR, MULTI = "101", "102", "103", "104", "105"
NAAZIR, ROKHA, VEFUTII, THIBAH, TARMANN, OLERGODT = (
    "naazir", "rokha", "vefutii", "thibah", "tarmann", "olergodt",
)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _state(other: str = "sol") -> GameState:
    """p1 = Naaz-Rokha (aktywny), p2 = rywal z Thibah."""
    p1 = PlayerState(player_id="p1", color="green", faction="naaz", home_position=HOME)
    p2 = PlayerState(player_id="p2", color="blue", faction=other, home_position=FAR)
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2"],
        players={"p1": p1, "p2": p2},
        systems={
            "000": SystemState(position="000", system_id="18"),
            HOME: SystemState(position=HOME, system_id="57",
                              planet_owners={NAAZIR: "p1", ROKHA: "p1"},
                              space_units={"p1": {"carrier": 1}}),
            PLAIN: SystemState(position=PLAIN, system_id="20", planet_owners={VEFUTII: "p1"}),
            RIVAL: SystemState(position=RIVAL, system_id="21", planet_owners={THIBAH: "p2"}),
            FAR: SystemState(position=FAR, system_id="22"),
            MULTI: SystemState(position=MULTI, system_id="101", planet_owners={OLERGODT: "p1"}),
        },
    )
    state.players["p1"].controlled_planets = [NAAZIR, ROKHA, VEFUTII, OLERGODT]
    state.players["p2"].controlled_planets = [THIBAH]
    for p in state.players.values():
        p.cc_reinf = 8
        p.tactical_cc = 3
        p.fleet_cc = 3
        p.strategic_cc = 2
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


def _explore_window(state: GameState, planet: str, position: str, pid: str = "p1") -> GameState:
    after = state.clone()
    exploration.start_exploration(after, rules_hooks.bound_registry(), pid, position, [planet])
    return after


def test_naaz_komplet(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "naaz") == []


# ============================================================================ Distant Suns


@ruling("abilities:distant_suns#1", "abilities:distant_suns#2", "F_naaz_rokha/distant-suns/2")
def test_distant_suns_dwie_karty_wybor_jednej(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[PLAIN].planet_units = {VEFUTII: {"p1": {"mech": 1}}}
    state = _explore_window(state, VEFUTII, PLAIN)
    ex = state.exploration
    assert ex is not None and ex.current is None  # decyzja PRZED ujawnieniem (2)
    assert exploration.extra_draw_allowed(state, "p1", VEFUTII)
    state = exploration.draw(state, registry, VEFUTII, extra=True)
    cur = state.exploration.current  # type: ignore[union-attr]
    assert cur is not None and len(cur.candidates) == 2
    assert exploration.options_for(state, registry) == []
    with pytest.raises(ValueError, match="Choose which"):
        exploration.resolve(state, registry, "keep")
    keep, drop = cur.candidates
    state = exploration.choose(state, keep)
    cur = state.exploration.current  # type: ignore[union-attr]
    assert cur is not None and cur.card_id == keep and not cur.candidates
    assert drop in state.decks.exploration_discard["hazardous"]


@ruling("F_naaz_rokha/distant-suns/1")
def test_distant_suns_wiele_mechow_jedna_dodatkowa(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[PLAIN].planet_units = {VEFUTII: {"p1": {"mech": 3}}}
    state = exploration.draw(_explore_window(state, VEFUTII, PLAIN), registry, VEFUTII,
                             extra=True)
    assert len(state.exploration.current.candidates) == 2  # type: ignore[union-attr]


@ruling("F_naaz_rokha/distant-suns/3")
def test_distant_suns_ta_sama_talia_przy_kilku_cechach(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[MULTI].planet_units = {OLERGODT: {"p1": {"mech": 1}}}
    state = exploration.draw(_explore_window(state, OLERGODT, MULTI), registry, OLERGODT,
                             "cultural", extra=True)
    cur = state.exploration.current  # type: ignore[union-attr]
    assert cur is not None and cur.deck == "cultural"
    for card in cur.candidates:
        assert card in exploration.deck_card_ids(registry, "cultural")


def test_distant_suns_bez_mecha_nie(registry: StaticDataRegistry) -> None:
    state = _explore_window(_state(), VEFUTII, PLAIN)
    assert state.exploration is not None and state.exploration.current is not None  # auto
    state = _explore_window(_state(), OLERGODT, MULTI)
    with pytest.raises(ValueError, match="additional"):
        exploration.draw(state, registry, OLERGODT, "cultural", extra=True)


# ================================================================ Fabrication / Forgery


@ruling("abilities:fabrication#1", "F_naaz_rokha/fabrication/3")
def test_fabrication_relikt_z_dwoch_unknown(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].relic_fragments = ["urf1", "urf2"]
    after = _play(state, registry, "ability", "fabrication",
                  {"mode": "relic", "fragments": ["urf1", "urf2"]})
    assert after.players["p1"].relic_fragments == []
    assert len(after.players["p1"].relics) == 1
    assert {"urf1", "urf2"} <= set(after.decks.purged)


def test_fabrication_rozne_typy_odrzucone(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].relic_fragments = ["crf1", "hrf1"]
    with pytest.raises(ValueError, match="same type"):
        _play(state, registry, "ability", "fabrication",
              {"mode": "relic", "fragments": ["crf1", "hrf1"]})
    state.players["p1"].relic_fragments = ["crf1", "urf1"]
    after = _play(state, registry, "ability", "fabrication",
                  {"mode": "relic", "fragments": ["crf1", "urf1"]})
    assert len(after.players["p1"].relics) == 1


@ruling("F_naaz_rokha/fabrication/1")
def test_fabrication_pusta_talia_reliktow(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].relic_fragments = ["crf1", "crf2"]
    probe = state.clone()
    from src.core import relics

    relics.ensure_relic_deck(probe, registry)
    probe.decks.relic_deck = []
    after = _play(probe, registry, "ability", "fabrication",
                  {"mode": "relic", "fragments": ["crf1", "crf2"]})
    assert after.players["p1"].relic_fragments == []
    assert after.players["p1"].relics == []


@ruling("abilities:fabrication#2", "F_naaz_rokha/fabrication/2")
def test_fabrication_zeton_i_pusta_rezerwa(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].relic_fragments = ["irf1", "irf2"]
    after = _play(state, registry, "ability", "fabrication",
                  {"mode": "fleet", "fragments": ["irf1"]})
    assert after.players["p1"].fleet_cc == 4 and after.players["p1"].cc_reinf == 7
    assert after.players["p1"].relic_fragments == ["irf2"]
    state.players["p1"].cc_reinf = 0
    after = _play(state, registry, "ability", "fabrication",
                  {"mode": "tactical", "fragments": ["irf1"]})
    assert after.players["p1"].tactical_cc == 3  # bez żetonu, fragment i tak purge
    assert after.players["p1"].relic_fragments == ["irf2"]


@ruling("F_naaz_rokha/black-market-forgery/1", "F_naaz_rokha/black-market-forgery/2")
def test_black_market_forgery_warunki(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].relic_fragments = ["hrf1", "urf1"]
    assert naaz._forgery_blocker(state, registry, "p2") is None  # Unknown = dowolny typ (2)
    from src.core import relics

    relics.ensure_relic_deck(state, registry)
    state.decks.relic_deck = []
    state.decks.relic_discard = []
    assert "empty" in (naaz._forgery_blocker(state, registry, "p2") or "")  # (1)


# ==================================================================== Pre-Fab Arcologies


@ruling("technologies:pfa#1")
def test_prefab_odswieza_po_eksploracji(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["pfa"]
    state.players["p1"].exhausted_planets = [VEFUTII]
    triggers.fire(state, GameEvent.PLANET_EXPLORED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "planet": VEFUTII, "deck": "hazardous", "card": "x"})
    assert VEFUTII not in state.players["p1"].exhausted_planets


@ruling("F_naaz_rokha/prefab-arcologies/1", "F_naaz_rokha/prefab-arcologies/1.1",
        "F_naaz_rokha/prefab-arcologies/1.2")
def test_prefab_po_produkcji_freelancers(registry: StaticDataRegistry) -> None:
    """Planeta gotowa dopiero PO produkcji Freelancers: wyczerpana wcześniej nie płaci (1.1),
    gotowa płaci i potem zostaje odświeżona (1.2)."""
    state = _state()
    state.players["p1"].technologies = ["pfa"]
    state.active_system = PLAIN
    state.players["p1"].exhausted_planets = [VEFUTII]
    state.exploration = ExplorationState(player_id="p1", position=PLAIN, queue=[])
    freelancers = next(
        c for c in exploration.deck_card_ids(registry, "cultural")
        if (exploration.card_def(registry, c).name or "").lower() == "freelancers"
    )
    state.exploration.current = ExploreCurrent(
        planet=VEFUTII, deck="cultural", card_id=freelancers
    )
    after = exploration.resolve(state, registry, "produce")
    assert after.production_grant is not None
    assert VEFUTII in after.players["p1"].exhausted_planets  # jeszcze nie odświeżona (1.1)
    assert after.exploration is not None and after.exploration.deferred_explored
    done = production.skip_grant(after)
    assert VEFUTII not in done.players["p1"].exhausted_planets  # po produkcji (1, 1.2)


# =========================================================================== Supercharge


@ruling("technologies:sc#1", "F_naaz_rokha/supercharge/1")
def test_supercharge_plus_jeden_tylko_walka(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["sc"]
    ctx = {"kind": "space", "attacker": "p1", "defender": "p2", "position": PLAIN, "round": 1}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START, ctx=ctx)
    state = _accept(state, "p1", "Supercharge")
    assert "sc" in state.players["p1"].exhausted_technologies
    assert rules_hooks.modify(rules_hooks.POINT_COMBAT_ROLL_MODIFIER, state, "p1", 0, {}) == 1
    for point in (rules_hooks.POINT_SPACE_CANNON_ROLL_MODIFIER,
                  rules_hooks.POINT_BOMBARDMENT_ROLL_MODIFIER):
        assert rules_hooks.modify(point, state, "p1", 0, {}) == 0


# ============================================================================ Visz El Vir


@ruling("units:naaz_flagship#1", "F_naaz_rokha/visz-el-vir/1")
def test_visz_el_vir_dodatkowa_kosc_mechow_na_planecie(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems[PLAIN].space_units = {"p1": {"flagship": 1}}
    state.systems[PLAIN].planet_units = {VEFUTII: {"p1": {"mech": 2, "infantry": 1}}}
    units = {u.base_type: u for u in battle.combat_units(
        state, None, registry, kind="ground", position=PLAIN, planet=VEFUTII, player_id="p1")}
    assert units["mech"].dice_per_unit == 3  # każdy mech: 2 + 1
    assert units["infantry"].dice_per_unit == 1


def _space_fight(state: GameState, mechs: int = 1) -> GameState:
    state.active_system = PLAIN
    state.tactical_step = TacticalStep.SPACE_COMBAT
    state.systems[PLAIN].space_units = {
        "p1": {"carrier": 1, "mech": mechs, "flagship": 1}, "p2": {"destroyer": 2},
    }
    state.active_combat = ActiveCombat(kind="space", position=PLAIN, attacker="p1",
                                       defender="p2")
    return state


@ruling("F_naaz_rokha/visz-el-vir/2", "units:naaz_mech_space#1",
        "F_naaz_rokha/eidolon-zgrav-eidolon/1", "F_naaz_rokha/eidolon-zgrav-eidolon/4")
def test_zgrav_statek_tylko_w_walce_kosmicznej(registry: StaticDataRegistry) -> None:
    state = _space_fight(_state())
    units = {u.base_type: u for u in battle.combat_units(
        state, None, registry, kind="space", position=PLAIN, planet=None, player_id="p1")}
    zgrav = units["mech"]
    assert zgrav.unit_id == "naaz_mech_space" and zgrav.base_hits_on == 8
    assert not zgrav.sustain  # Z-Grav nie ma Sustain Damage
    assert zgrav.dice_per_unit == 3  # 2 + Visz El Vir (mech - 4)
    state.active_combat = None  # poza walką mech jest ładunkiem (1)
    assert ship_roles.space_ground_variants(state, registry, "p1", PLAIN) == {}
    state.active_combat = ActiveCombat(kind="space", position=PLAIN, attacker="p1",
                                       defender="p2")
    state.active_system = FAR  # nie w aktywnym systemie (1)
    assert ship_roles.space_ground_variants(state, registry, "p1", PLAIN) == {}


@ruling("units:naaz_mech#1", "F_naaz_rokha/eidolon-zgrav-eidolon/2")
def test_eidolon_flip_obowiazkowy_na_starcie(registry: StaticDataRegistry) -> None:
    state = _space_fight(_state())
    triggers.fire(state, GameEvent.COMBAT, Moment.START, subject="p1",
                  ctx={"kind": "space", "position": PLAIN, "attacker": "p1", "defender": "p2"})
    assert not _offers(state, "p1", "Eidolon")
    assert any(n["component"] == "units:naaz_mech" for n in state.ability_notes)


@ruling("F_naaz_rokha/eidolon-zgrav-eidolon/2.2", "F_naaz_rokha/eidolon-zgrav-eidolon/3")
def test_zgrav_assault_cannon(registry: StaticDataRegistry) -> None:
    from src.core.hooks import technologies_combat as tc

    state = _space_fight(_state())
    state.systems[PLAIN].space_units["p1"] = {"carrier": 1, "mech": 1, "dreadnought": 1}
    ctx = {"kind": "space", "position": PLAIN, "attacker": "p1", "defender": "p2"}
    assert tc._assault_cannon_ready(state, "p1", ctx)  # Z-Grav liczy się do 3 (2.2)
    options = tc.assault_cannon_inputs(state, registry, "p1", ctx)[0]["options"]
    assert any(o["value"] == "mech" for o in options)  # cel jak statek (3)


@ruling("F_naaz_rokha/eidolon-zgrav-eidolon/5")
def test_zgrav_liczy_sie_do_demonstrate_your_power(registry: StaticDataRegistry) -> None:
    state = _space_fight(_state())
    state.systems[PLAIN].space_units["p1"] = {"carrier": 1, "mech": 2}
    assert state.active_combat is not None
    state.active_combat.step = CombatStep.DONE
    assert objective_events._dyp_ships(state, PLAIN, "p1") == 3


@ruling("units:naaz_mech_space#2", "F_naaz_rokha/eidolon-zgrav-eidolon/6")
def test_zgrav_po_walce_wraca_do_pojemnosci(registry: StaticDataRegistry) -> None:
    state = _space_fight(_state(), mechs=5)
    state.systems[PLAIN].space_units["p1"] = {"destroyer": 1, "mech": 2}
    assert state.active_combat is not None
    state.active_combat.step = CombatStep.DONE
    triggers.fire(state, GameEvent.COMBAT, Moment.END, ctx={
        "kind": "space", "position": PLAIN, "attacker": "p1", "defender": "p2", "winner": "p1"})
    assert any(n["component"] == "units:naaz_mech_space" for n in state.ability_notes)
    report = capacity.capacity_report(state, registry, PLAIN, "p1")
    assert report.cargo.get("mech") == 2 and report.excess == 2  # mechy znów ładunkiem


# ====================================================================== Garv and Gunn


@ruling("leaders:naazagent#1")
def test_garv_and_gunn_inny_gracz_eksploruje(registry: StaticDataRegistry) -> None:
    state = _state()
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p2", ctx={"player": "p2"})
    state = _accept(state, "p1", "Garv and Gunn")
    assert state.players["p1"].leader_states.get("naazagent") == "exhausted"
    offer = _offers(state, "p2", "explore 1 of your planets")
    assert offer, "decyzja gracza, który kończył turę"
    state = triggers.accept_offer(state, "p2", offer[0].id, {"planet": THIBAH})
    assert state.exploration is not None and state.exploration.player_id == "p2"


# ===================================================================== Dart and Tai


@ruling("leaders:naazcommander#unlock")
def test_dart_and_tai_odblokowanie(registry: StaticDataRegistry) -> None:
    unlock = leaders.unlock_predicate(registry, "naazcommander")
    assert unlock is not None
    state = _state()
    state.systems[HOME].space_units["p1"]["mech"] = 1
    state.systems[PLAIN].planet_units = {VEFUTII: {"p1": {"mech": 1}}}
    assert not unlock(state, registry, "p1")
    state.systems[MULTI].planet_units = {OLERGODT: {"p1": {"mech": 1}}}
    assert unlock(state, registry, "p1")


@ruling("leaders:naazcommander#1")
def test_dart_and_tai_eksploracja_przejetej(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"naazcommander": "unlocked"}
    ctx = {"player": "p1", "planet": THIBAH, "position": RIVAL, "previous": "p2"}
    triggers.fire(state, GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, subject="p1", ctx=ctx)
    state = _accept(state, "p1", "Dart and Tai")
    assert state.exploration is not None
    explored = state.exploration.current or None
    assert (explored is not None and explored.planet == THIBAH) or THIBAH in state.exploration.queue
    fresh = _state()
    fresh.players["p1"].leader_states = {"naazcommander": "unlocked"}
    triggers.fire(fresh, GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, subject="p1",
                  ctx={**ctx, "previous": None})
    assert not _offers(fresh, "p1", "Dart and Tai")  # niczyja planeta - zwykła eksploracja


@ruling("F_saar/scavenge/2.2")
def test_saar_z_alliance_naaz_dowolna_kolejnosc(registry: StaticDataRegistry) -> None:
    """Saar z Alliance Naaz-Rokha: TG ze Scavenge od razu, eksploracja to osobna oferta."""
    state = _state(other="saar")
    state.players["p2"].leader_states = {}
    state.players["p2"].promissory_notes_in_play = ["green_an"]
    state.players["p1"].leader_states = {"naazcommander": "unlocked"}
    from src.core.hooks import promissory_generic

    if "naazcommander" not in promissory_generic.alliance_commanders(state, "p2"):
        pytest.skip("Alliance Naaz-Rokha nie rozpoznany w danych")
    ctx = {"player": "p2", "planet": VEFUTII, "position": PLAIN, "previous": "p1"}
    triggers.fire(state, GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, subject="p2", ctx=ctx)
    assert state.players["p2"].trade_goods == 1
    assert _offers(state, "p2", "Dart and Tai")


# ============================================================ Hesh and Prit (hero)


@ruling("leaders:naazhero#unlock")
def test_bohater_odblokowanie_3_cele(registry: StaticDataRegistry) -> None:
    unlock = leaders.unlock_predicate(registry, "naazhero")
    assert unlock is not None
    assert not unlock(_state(), registry, "p1")


def _hero_state() -> GameState:
    from src.core import relics

    state = _state()
    state.players["p1"].leader_states = {"naazhero": "unlocked"}
    state.players["p2"].strategy_cards = [5]
    # Relikt bez skutku przy zdobyciu (losowy mógłby otworzyć własne okno).
    relics.ensure_relic_deck(state, rules_hooks.bound_registry())
    state.decks.relic_deck = ["emelpar", *[r for r in state.decks.relic_deck if r != "emelpar"]]
    return state


@ruling("leaders:naazhero#1", "leaders:naazhero#3",
        "F_naaz_rokha/hesh-and-prit-perfect-synthesis/2",
        "F_naaz_rokha/hesh-and-prit-perfect-synthesis/3",
        "F_naaz_rokha/hesh-and-prit-perfect-synthesis/3.1")
def test_perfect_synthesis_relikt_i_lancuch(registry: StaticDataRegistry) -> None:
    state = _hero_state()
    after = _play(state, registry, "leader", "naazhero", {"first": 6, "second": 1})
    assert len(after.players["p1"].relics) == 1
    assert after.players["p1"].leader_states["naazhero"] == "purged"
    window = after.pending_window
    assert window is not None and window.window_type is WindowType.STRATEGY_SECONDARY
    assert window.context["initiative"] == 6 and window.context[strategic_action.CHAIN_KEY] == "1"
    grid = grid_from_state(after, registry)
    after = strategic_action.resolve_secondary(after, registry, "p1", execute=False, grid=grid)
    window = after.pending_window
    assert window is not None and window.context["initiative"] == 1  # druga karta, potem (3)
    after = strategic_action.resolve_secondary(after, registry, "p1", execute=False, grid=grid)
    assert after.pending_window is None


@ruling("F_naaz_rokha/hesh-and-prit-perfect-synthesis/1",
        "F_naaz_rokha/hesh-and-prit-perfect-synthesis/1.1")
def test_perfect_synthesis_zero_albo_rozne_karty(registry: StaticDataRegistry) -> None:
    state = _hero_state()
    after = _play(state, registry, "leader", "naazhero", {"first": 0, "second": 0})
    assert len(after.players["p1"].relics) == 1 and after.pending_window is None
    with pytest.raises(ValueError, match="same strategy card"):
        _play(_hero_state(), registry, "leader", "naazhero", {"first": 6, "second": 6})


@ruling("F_naaz_rokha/hesh-and-prit-perfect-synthesis/4")
def test_perfect_synthesis_karta_wyeliminowanego_niewybrana(registry: StaticDataRegistry) -> None:
    from src.core.hooks.action_cards_board import strategy_cards_in_reach

    state = _hero_state()
    state.players["p2"].exhausted_strategy_cards = [5]
    assert 5 not in strategy_cards_in_reach(state, registry)
    del state.players["p2"]  # wyeliminowany: jego karty są „unchosen”
    state.seating_order = ["p1"]
    assert 5 in strategy_cards_in_reach(state, registry)


@ruling("leaders:naazhero#2", "F_naaz_rokha/hesh-and-prit-perfect-synthesis/5",
        "F_naaz_rokha/hesh-and-prit-perfect-synthesis/6")
def test_perfect_synthesis_zeton_z_rezerwy(registry: StaticDataRegistry,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    state = _hero_state()
    after = _play(state, registry, "leader", "naazhero", {"first": 5, "second": 0})
    spent: list[Any] = []
    real_fire = triggers.fire

    def spy(st: GameState, event: GameEvent, moment: Moment, **kw: Any) -> Any:
        spent.append(event)
        return real_fire(st, event, moment, **kw)

    monkeypatch.setattr(triggers, "fire", spy)
    grid = grid_from_state(after, registry)
    done = strategic_action.resolve_secondary(after, registry, "p1", execute=True, grid=grid)
    p1 = done.players["p1"]
    assert p1.strategic_cc == 2 and p1.cc_reinf == 8  # żeton z rezerwy wraca do rezerwy (#2)
    assert GameEvent.STRATEGY_TOKEN_SPENT not in spent  # Alliance Muaat bez TG (6)
    after.players["p1"].cc_reinf = 0  # pusta rezerwa: żeton z arkusza, wybrana pula (5)
    with pytest.raises(ValueError, match="choose a pool"):
        strategic_action.resolve_secondary(after, registry, "p1", execute=True, grid=grid)
    done = strategic_action.resolve_secondary(
        after, registry, "p1", execute=True, payload={"token_pool": "tactical"}, grid=grid)
    assert done.players["p1"].tactical_cc == 2 and done.players["p1"].strategic_cc == 2


# ============================================================== Absolute Synergy


def _four_mechs(state: GameState) -> GameState:
    state.players["p1"].breakthrough_unlocked = True
    state.systems[PLAIN].space_units = {"p1": {"carrier": 1, "mech": 1}}
    state.systems[PLAIN].planet_units = {VEFUTII: {"p1": {"mech": 3}}}
    return state


@ruling("breakthroughs:naazbt#1", "F_naaz_rokha/absolute-synergy/1",
        "F_naaz_rokha/absolute-synergy/2")
def test_absolute_synergy_odwrocenie(registry: StaticDataRegistry) -> None:
    state = _four_mechs(_state())
    state.phase = Phase.STRATEGY  # w dowolnej chwili (2)
    assert naaz._synergy_window(state, registry, "p1") is None
    after, _ = faction_components.play(state, registry, "p1", "breakthrough", "naazbt",
                                       {"keep": f"{PLAIN}|space"})
    system = after.systems[PLAIN]
    assert system.space_units["p1"]["mech"] == 1
    assert not system.planet_units[VEFUTII].get("p1", {}).get("mech")
    assert after.players["p1"].breakthrough_flipped


@ruling("breakthroughs:naazbt#2", "F_naaz_rokha/eidolon-maximum/6")
def test_eidolon_maximum_statek_i_sila_naziemna(registry: StaticDataRegistry) -> None:
    state = _four_mechs(_state())
    state.players["p1"].breakthrough_flipped = True
    unit = resolve_unit_variant(registry, "naaz", [], "mech", True, True)
    assert unit is not None and unit.id == "naaz_voltron"
    space = {u.base_type: u for u in battle.combat_units(
        state, None, registry, kind="space", position=PLAIN, planet=None, player_id="p1")}
    assert space["mech"].base_hits_on == 4 and space["mech"].dice_per_unit == 4
    assert space["mech"].sustain
    ground = {u.base_type: u for u in battle.combat_units(
        state, None, registry, kind="ground", position=PLAIN, planet=VEFUTII, player_id="p1")}
    assert ground["mech"].unit_id == "naaz_voltron"
    assert ship_roles.space_ships(state, registry, "p1", PLAIN)["mech"] == 1


@ruling("F_naaz_rokha/eidolon-maximum/5")
def test_eidolon_maximum_to_mech_visz_el_vir(registry: StaticDataRegistry) -> None:
    state = _four_mechs(_state())
    state.players["p1"].breakthrough_flipped = True
    state.systems[PLAIN].space_units["p1"]["flagship"] = 1
    space = {u.base_type: u for u in battle.combat_units(
        state, None, registry, kind="space", position=PLAIN, planet=None, player_id="p1")}
    assert space["mech"].dice_per_unit == 5


def test_eidolon_maximum_rusza_sie_i_liczy_do_puli(registry: StaticDataRegistry) -> None:
    from src.core import floating_structures, movement

    state = _four_mechs(_state())
    state.players["p1"].breakthrough_flipped = True
    assert floating_structures.moves_as_ship(state, "p1", "mech")
    grid = grid_from_state(state, registry)
    assert movement._effective_move_value(
        state, grid, registry, PLAIN, "mech", "p1", boost=False, tempesta=False) == 3
    assert fleet_pool.fleet_report(state, PLAIN, "p1", registry).ships.get("mech") == 1
    assert "mech" not in capacity.capacity_report(state, registry, PLAIN, "p1").cargo


@ruling("breakthroughs:naazbt#3", "F_naaz_rokha/eidolon-maximum/2")
def test_eidolon_maximum_bez_trafien_ze_zdolnosci(registry: StaticDataRegistry) -> None:
    state = _four_mechs(_state())
    state.players["p1"].breakthrough_flipped = True
    state.active_system = PLAIN
    view = space_cannon.combat_view(state, "p1", registry)
    assert "mech" not in view and "carrier" in view  # trafienia na inne jednostki grupy


@ruling("breakthroughs:naazbt#4", "F_naaz_rokha/eidolon-maximum/3")
def test_eidolon_maximum_naprawa_tylko_w_swojej_walce(registry: StaticDataRegistry) -> None:
    from src.core.damage import damaged_count, set_damaged

    state = _four_mechs(_state())
    state.players["p1"].breakthrough_flipped = True
    system = state.systems[PLAIN]
    set_damaged(system, "space", "p1", "mech", 1)
    elsewhere = {"kind": "ground", "position": PLAIN, "planet": VEFUTII, "attacker": "p1",
                 "defender": "p2", "round": 2}
    system.planet_units[VEFUTII] = {"p2": {"infantry": 1}}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START, ctx=elsewhere)
    assert damaged_count(system, "space", "p1", "mech") == 1  # nie walczy na planecie (3)
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START, ctx={
        **elsewhere, "kind": "space", "planet": ""})
    assert damaged_count(system, "space", "p1", "mech") == 0


@ruling("breakthroughs:naazbt#5", "F_naaz_rokha/eidolon-maximum/4")
def test_eidolon_maximum_zakaz_stawiania_i_produkcji(registry: StaticDataRegistry) -> None:
    from src.core import board_reinforcements

    state = _four_mechs(_state())
    state.players["p1"].breakthrough_flipped = True
    assert not board_reinforcements.can_place(state, "p1", "mech")
    with pytest.raises(ValueError, match="cannot place"):
        unit_ops.place_units(state, state.systems[HOME], NAAZIR, "p1", "mech", 1)
    assert "mech" in production.forbidden_types(state, "p1", "spacedock")


@ruling("breakthroughs:naazbt#6")
def test_eidolon_maximum_zniszczony_albo_usuniety_odwraca_karte(
    registry: StaticDataRegistry,
) -> None:
    for cause in (UnitCause.DESTROYED, UnitCause.REMOVED):
        state = _four_mechs(_state())
        state.players["p1"].breakthrough_flipped = True
        state.systems[PLAIN].planet_units = {}
        unit_ops.remove_units(state, state.systems[PLAIN], "space", "p1", "mech", 1, cause)
        assert not state.players["p1"].breakthrough_flipped
        assert state.players["p1"].breakthrough_unlocked


# ================================================== Brother Milor Ω (Yin) vs Z-Grav Eidolon


@ruling("F_yin/brother-milor-omega/8", "F_yin/brother-milor-omega/8.1")
def test_milor_za_zgrav_wlasciciel_wybiera_typ(registry: StaticDataRegistry) -> None:
    """Zniszczony Z-Grav (mech + statek): właściciel stawia 2 myśliwce albo 2 piechotę; piechota
    w przestrzeni nie walczy w walce kosmicznej (8.1 - nie jest statkiem)."""
    state = _space_fight(_state(other="yin"))
    state.players["p2"].leader_states = {"yinagent": "unlocked"}
    system = state.systems[PLAIN]
    unit_ops.remove_units(state, system, "space", "p1", "mech", 1, UnitCause.DESTROYED)
    state = _accept(state, "p2", "Brother Milor")
    assert state.players["p2"].leader_states["yinagent"] == "exhausted"
    offer = _offers(state, "p1", "2 fighters or 2 infantry")
    assert offer, "wybór należy do właściciela zniszczonej jednostki"
    state = triggers.accept_offer(state, "p1", offer[0].id, {"unit": "infantry"})
    assert state.systems[PLAIN].space_units["p1"]["infantry"] == 2
    units = {u.base_type for u in battle.combat_units(
        state, None, registry, kind="space", position=PLAIN, planet=None, player_id="p1")}
    assert "infantry" not in units
