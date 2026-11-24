"""The Yin Brotherhood — komplet komponentów frakcji (RULES.md 62.10) i rulingi F_yin."""

from __future__ import annotations

import pytest

from src.core import battle, breakthrough, rules_hooks, technology, triggers, unit_ops
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    Phase,
    PlayerState,
    SystemState,
)
from src.core.hooks.factions import yin
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import SOURCE_LEADER, HookSource
from src.core.state_grid import grid_from_state
from src.core.unit_ops import UnitCause
from tests.factions.completeness import missing_components
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def _planet(registry: StaticDataRegistry, system_id: str) -> str:
    return registry.systems[system_id].planets[0]


def _state(registry: StaticDataRegistry) -> GameState:
    """p1 = Yin (aktywny, dom w 103), p2 = Sol; 101/102 zwykłe systemy, 000 = Mecatol Rex."""
    p1 = PlayerState(player_id="p1", color="black", faction="yin")
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
            "103": SystemState(position="103", system_id="03"),
        },
    )
    state.players["p1"].controlled_planets = [mine]
    return state


def test_kompletnosc_yin(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "yin") == []


# ------------------------------------------------------------------------------- Van Hauge


@ruling("F_yin/van-hauge/2", "units:yin_flagship#1")
def test_van_hauge_niszczy_wszystkie_statki_bez_sil_naziemnych(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry)
    system = state.systems["102"]
    planet = _planet(registry, "21")
    system.space_units = {
        "p1": {"flagship": 1, "cruiser": 1, "infantry": 2},
        "p2": {"destroyer": 2, "fighter": 1},
    }
    system.planet_units = {planet: {"p2": {"infantry": 1}}}
    unit_ops.remove_units(state, system, "space", "p1", "flagship", 1, UnitCause.DESTROYED)
    assert system.space_units.get("p2", {}).get("destroyer", 0) == 0
    assert system.space_units.get("p2", {}).get("fighter", 0) == 0
    assert system.space_units["p1"].get("cruiser", 0) == 0
    assert system.space_units["p1"]["infantry"] == 2  # siły naziemne zostają (F_yin)
    assert system.planet_units[planet]["p2"] == {"infantry": 1}


def test_cudzy_flagowiec_nie_dziala_jak_van_hauge(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    system = state.systems["102"]
    system.space_units = {"p1": {"cruiser": 1}, "p2": {"flagship": 1, "destroyer": 1}}
    unit_ops.remove_units(state, system, "space", "p2", "flagship", 1, UnitCause.DESTROYED)
    assert system.space_units["p1"]["cruiser"] == 1
    assert system.space_units["p2"]["destroyer"] == 1


# ------------------------------------------------------------------------ Yin Ascendant


@ruling("F_yin/yin-ascendant/1", "breakthroughs:yinbt#1")
def test_yin_ascendant_przy_zdobyciu_i_celu_publicznym(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    breakthrough.unlock_breakthrough(state, registry, "p1")
    gained = yin.alliance_factions(state, "p1")
    assert len(gained) == 1 and gained[0] not in ("yin", "sol")
    commander = next(
        lid for lid in registry.factions[gained[0]].leaders
        if registry.leaders[lid].type == "commander"
    )
    assert HookSource(SOURCE_LEADER, commander) in rules_hooks.owned_sources(state, "p1")
    triggers.fire(
        state, GameEvent.OBJECTIVE_SCORED, Moment.AFTER, subject="p1",
        ctx={"player": "p1", "objective": "x", "secret": "true"},
    )
    assert len(yin.alliance_factions(state, "p1")) == 1  # cel tajny - bez sojuszu
    triggers.fire(
        state, GameEvent.OBJECTIVE_SCORED, Moment.AFTER, subject="p1",
        ctx={"player": "p1", "objective": "x", "secret": "false"},
    )
    both = yin.alliance_factions(state, "p1")
    assert len(both) == 2 and len(set(both)) == 2  # bez powtórek („unused”)


def test_bez_przelomu_cel_nie_daje_sojuszu(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    triggers.fire(
        state, GameEvent.OBJECTIVE_SCORED, Moment.AFTER, subject="p1",
        ctx={"player": "p1", "objective": "x", "secret": "false"},
    )
    assert yin.alliance_factions(state, "p1") == []


# ------------------------------------------------------------------------- Brother Omar


def test_omar_spelnia_zielony_prerekwizyt(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    tech = registry.technologies["dxa"]  # wymaga 1 zielonego
    assert technology.missing_prerequisites(state, registry, "p1", tech)
    state.players["p1"].leader_states = {"yincommander": "unlocked"}
    assert not technology.missing_prerequisites(state, registry, "p1", tech)


@ruling("leaders:yincommander#2")
def test_omar_zwrot_piechoty_tylko_dla_technologii_innego_gracza(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry)
    planet = _planet(registry, "20")
    state.systems["101"].planet_units = {planet: {"p1": {"infantry": 2}}}
    state.players["p1"].leader_states = {"yincommander": "unlocked"}
    skip = f"{technology.INFANTRY_SKIP_PREFIX}101|{planet}"
    with pytest.raises(ValueError, match="another player owns"):
        technology.plan_research(state, registry, "p1", "fl", [skip])
    state.players["p2"].technologies = ["fl"]
    assert skip in [v for v, _ in technology.skip_choices(state, registry, "p1")]
    plan = technology.plan_research(state, registry, "p1", "fl", [skip])
    after = state.clone()
    technology.apply_research(after, "p1", plan)
    assert "fl" in after.players["p1"].technologies
    assert after.systems["101"].planet_units[planet]["p1"]["infantry"] == 1


def test_bez_omara_nie_ma_skipu_piechoty(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    planet = _planet(registry, "20")
    state.systems["101"].planet_units = {planet: {"p1": {"infantry": 2}}}
    state.players["p2"].technologies = ["fl"]
    skip = f"{technology.INFANTRY_SKIP_PREFIX}101|{planet}"
    assert skip not in [v for v, _ in technology.skip_choices(state, registry, "p1")]
    with pytest.raises(ValueError):
        technology.plan_research(state, registry, "p1", "fl", [skip])


# ----------------------------------------------------------------- walka: rulingi F_yin


def _ground(state: GameState, registry: StaticDataRegistry, p2_units: dict[str, int]) -> None:
    planet = _planet(registry, "21")
    state.systems["102"].planet_units = {planet: {"p1": {"infantry": 2}, "p2": p2_units}}
    state.active_combat = ActiveCombat(
        kind="ground", position="102", planet=planet, attacker="p1", defender="p2",
    )


def test_strona_bez_sil_przegrywa_bez_rzutu(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    _ground(state, registry, {})
    after = battle.roll_round(state, grid_from_state(state, registry), registry)
    assert after.active_combat is not None
    assert after.active_combat.step is CombatStep.DONE
    assert after.active_combat.winner == "p1"
    assert after.active_combat.log == []


def test_indoctrination_tylko_przeciw_piechocie(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    state.players["p1"].trade_goods = 3
    _ground(state, registry, {"mech": 1})
    assert not yin._indoctrination_ready(state, "p1", {"kind": "ground"})  # same mechy (F_yin)
    _ground(state, registry, {"mech": 1, "infantry": 1})
    assert yin._indoctrination_ready(state, "p1", {"kind": "ground"})


def test_greyfire_nie_przeciw_yin_i_od_dwoch_sil(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    window = OpenWindow(GameEvent.COMBAT, Moment.START, {})
    _ground(state, registry, {"infantry": 2})
    # Posiadacz p2 walczy z Yin - notka niezagrywalna.
    assert yin._greyfire_condition(state, registry, "p2", window) is not None
    state.players["p1"].faction = "letnev"
    assert yin._greyfire_condition(state, registry, "p2", window) is None
    _ground(state, registry, {"infantry": 1})
    state.systems["102"].planet_units[_planet(registry, "21")]["p1"] = {"infantry": 1}
    assert yin._greyfire_condition(state, registry, "p2", window) is not None


def test_hit_target_if_able(registry: StaticDataRegistry) -> None:
    """Impulse Core: bez nie-myśliwców przeciwnik przypisuje trafienie dowolnie („if able”)."""
    state = _state(registry)
    state.systems["102"].space_units = {"p1": {"cruiser": 1}, "p2": {"fighter": 2}}
    state.active_combat = ActiveCombat(
        kind="space", position="102", attacker="p1", defender="p2",
    )
    params = {"params": {"ship": "cruiser"}}
    yin.impulse_core(state, "p1", params)
    combat = state.active_combat
    assert combat.start_hits == {"p2": 1}
    assert "p2" not in combat.hit_targets  # brak nie-myśliwców - bez wymogu celu


# --------------------------------------------------------------------- Brother Milor Ω


@ruling("F_yin/brother-milor-omega-replaced-by-omega-omega/2")
def test_milor_tylko_w_fazie_akcji_i_w_walce(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    ctx = {"player": "p2", "base_type": "destroyer", "zone": "space", "position": "102"}
    assert not yin._milor_ready(state, "p1", ctx)  # brak walki
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1", defender="p2")
    assert yin._milor_ready(state, "p1", ctx)
    state.phase = Phase.STATUS
    assert not yin._milor_ready(state, "p1", ctx)  # F_yin Ω: tylko faza akcji


# --------------------------------------------------------------- Quantum Dissemination


def test_dissemination_bez_domow_i_mecatolu_z_custodians(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    targets = {planet for _, planet in yin.dissemination_targets(state, registry)}
    assert "darien" not in targets  # planeta domowa
    assert "mr" not in targets  # żeton Custodians (R_custodians_token)
    assert _planet(registry, "21") in targets and _planet(registry, "20") in targets
    state.custodians_removed = True
    assert "mr" in {p for _, p in yin.dissemination_targets(state, registry)}


def test_dissemination_kolejka_systemow(registry: StaticDataRegistry) -> None:
    state = _state(registry)
    a, b = _planet(registry, "20"), _planet(registry, "21")
    yin.quantum_dissemination(
        state, registry, "p1", {"planet1": f"101|{a}", "planet2": f"102|{b}", "planet3": "none"},
    )
    inv = state.invasion
    assert inv is not None and inv.source == "leaders:yinhero"
    assert inv.position == "101" and inv.queue[0]["position"] == "102"
    assert state.systems["102"].planet_units[b]["p1"]["infantry"] == 1


def test_dissemination_zamkniecie_otwiera_kolejny_system(registry: StaticDataRegistry) -> None:
    from src.core import invasion
    from src.core.game_state import InvasionPhase

    state = _state(registry)
    a, b = _planet(registry, "20"), _planet(registry, "21")
    yin.quantum_dissemination(
        state, registry, "p1", {"planet1": f"101|{a}", "planet2": f"102|{b}", "planet3": "none"},
    )
    grid = grid_from_state(state, registry)
    state = invasion.advance(state, grid, registry)  # COMMIT -> (brak walki) ESTABLISH
    assert state.invasion is not None and state.invasion.phase is InvasionPhase.ESTABLISH
    state.exploration = None  # wynik eksploracji nieistotny dla kolejki
    state = invasion.advance(state, grid, registry)
    assert state.invasion is not None and state.invasion.position == "102"
    assert state.invasion.phase is InvasionPhase.COMMIT and not state.invasion.queue


def test_okno_badania_pokazuje_skip_piechoty(registry: StaticDataRegistry) -> None:
    from src.core.strategy_cards.technology import research_view

    state = _state(registry)
    planet = _planet(registry, "20")
    state.systems["101"].planet_units = {planet: {"p1": {"infantry": 1}}}
    state.players["p1"].leader_states = {"yincommander": "unlocked"}
    state.players["p2"].technologies = ["fl"]
    view = research_view(state, registry, "p1", 6)
    assert [s["value"] for s in view["infantry_skips"]] == [f"infantry:101|{planet}"]
    row = next(r for r in view["tree"] if r["id"] == "fl")
    assert row["status"] == "skippable" and row["infantrySkip"] is True


def test_dissemination_cala_plansza_nie_tylko_systemy_z_jednostkami(
    registry: StaticDataRegistry,
) -> None:
    """Błąd zgłoszony przez użytkownika: cele były tylko w systemach z wpisem w stanie (tam, gdzie
    coś stało). „Any non-home planets” = każda planeta na planszy (siatka mapy)."""
    from src.api.demo_map import build_demo_grid
    from src.core import board_graph

    grid = build_demo_grid(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    try:
        state = _state(registry)
        # 102 bez wpisu w stanie (nic tam nie stoi) - kafel z siatki mapy (Industrex).
        empty = "102"
        del state.systems[empty]
        planet = registry.systems[grid.system_id_at(empty)].planets[0]
        assert (empty, planet) in yin.dissemination_targets(state, registry)
        yin.quantum_dissemination(
            state, registry, "p1",
            {"planet1": f"{empty}|{planet}", "planet2": "none", "planet3": "none"},
        )
        assert state.systems[empty].planet_units[planet]["p1"]["infantry"] == 1
    finally:
        board_graph.bind_grid_provider(previous)
