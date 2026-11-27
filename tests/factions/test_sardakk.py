"""Sardakk N'orr — komplet komponentów frakcji (RULES.md 62.1). Konwencja par: bez / z wyjątkiem."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    active_effects,
    battle,
    board_graph,
    faction_components,
    invasion,
    leaders,
    promissory_play,
    rules_hooks,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
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
from src.core.hex_grid import HexGrid
from src.core.hooks import reactions_combat
from src.core.hooks.factions import sardakk
from src.core.registry import StaticDataRegistry
from tests import boosts
from tests.factions.completeness import missing_components
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(autouse=True, scope="module")
def _grid(registry: StaticDataRegistry) -> Iterator[None]:
    grid = build_demo_grid(registry)
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield
    board_graph.bind_grid_provider(previous)


def _state(*, sardakk_active: bool = True) -> GameState:
    """p1 = Sardakk, p2 = Sol; aktywny system 102 (Industrex), sąsiedni 000 (Mecatol)."""
    systems = {
        "102": SystemState(position="102", system_id="115"),
        "000": SystemState(position="000", system_id="18"),
        "103": SystemState(position="103", system_id="01"),
    }
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1" if sardakk_active else "p2",
        active_system="102",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="sardakk"),
            "p2": PlayerState(player_id="p2", color="blue", faction="sol"),
        },
        systems=systems,
    )


def _combat(state: GameState, kind: str, step: CombatStep = CombatStep.ROLL) -> ActiveCombat:
    combat = ActiveCombat(
        kind=kind, position="102", planet="industrex" if kind == "ground" else None,
        attacker="p1", defender="p2", step=step,
    )
    state.active_combat = combat
    return combat


def _modifiers(state: GameState, registry: StaticDataRegistry, pid: str) -> dict[str, int]:
    units = battle.combat_units(
        state, build_demo_grid(registry), registry, kind="space", position="102", planet=None,
        player_id=pid,
    )
    return {u.base_type: u.modifier for u in units}


def _accept(state: GameState, player: str, params: dict[str, Any] | None = None) -> GameState:
    offer = next(o for o in state.pending_offers if o.player_id == player)
    return triggers.accept_offer(state, player, offer.id, params)


# ------------------------------------------------------------------------------- kompletność


def test_frakcja_kompletna(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "sardakk") == []


# ------------------------------------------------------------------- Unrelenting + flagowiec


@ruling("abilities:unrelenting#1", "units:sardakk_flagship#1")
def test_unrelenting_i_flagowiec(registry: StaticDataRegistry) -> None:
    state = _state()
    system = state.systems["102"]
    system.space_units["p1"] = {"cruiser": 1}
    system.space_units["p2"] = {"cruiser": 1}
    assert _modifiers(state, registry, "p1") == {"cruiser": 1}  # Unrelenting
    assert _modifiers(state, registry, "p2") == {"cruiser": 0}  # bez wyjątku
    system.space_units["p1"]["flagship"] = 1
    mods = _modifiers(state, registry, "p1")
    assert mods == {"cruiser": 2, "flagship": 1}  # flagowiec: tylko INNE statki


# ------------------------------------------------------------------------ Valkyrie (VPW, mech)


@ruling("technologies:vpw#1")
def test_valkyrie_particle_weave(registry: StaticDataRegistry) -> None:
    state = _state()
    ctx = {"kind": "ground", "opponent_hits": 1, "own_hits": 0}
    point = rules_hooks.POINT_COMBAT_EXTRA_HITS
    assert rules_hooks.modify(point, state, "p1", 0, ctx) == 0  # bez technologii
    state.players["p1"].technologies = ["vpw"]
    assert rules_hooks.modify(point, state, "p1", 0, ctx) == 1
    assert rules_hooks.modify(point, state, "p1", 0, {**ctx, "opponent_hits": 0}) == 0
    assert rules_hooks.modify(point, state, "p1", 0, {**ctx, "kind": "space"}) == 0


@ruling("units:sardakk_mech#1")
def test_mech_po_sustain_zadaje_trafienie_i_wraca_do_kolejki(registry: StaticDataRegistry) -> None:
    state = _state()
    _combat(state, "ground", CombatStep.ASSIGN)
    # Obrońca (p2) już przypisał, teraz Sardakk (p1) używa Sustain Damage mechem.
    state.pending_window = TimingWindow(
        window_type=WindowType.COMBAT_ASSIGN_HITS, queue=["p2", "p1"], cursor=1,
        responded=["p2"],
    )
    ctx = {"player": "p1", "base_type": "mech", "count": 1}
    triggers.fire(state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject="p1", ctx=ctx)
    assert state.active_combat is not None
    assert state.active_combat.pending_hits.get("p2") == 1
    assert state.pending_window.queue == ["p2", "p1", "p2"]
    # Para: piechota (bez zdolności) nic nie dodaje.
    state2 = _state()
    _combat(state2, "ground", CombatStep.ASSIGN)
    ctx2 = {"player": "p1", "base_type": "infantry", "count": 1}
    triggers.fire(state2, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject="p1", ctx=ctx2)
    assert state2.active_combat is not None and not state2.active_combat.pending_hits


# ------------------------------------------------------------------------------ Exotrireme II


def _round_end_ctx() -> dict[str, Any]:
    return {
        "kind": "space", "round": 1, "position": "102", "planet": "", "attacker": "p1",
        "defender": "p2", "phase": "combat", "sustained": {},
    }


@ruling("F_norr/exotrireme/1")
def test_exotrireme_niszczy_do_2_statkow(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["exo2"]
    state.systems["102"].space_units["p1"] = {"dreadnought": 1, "carrier": 1}
    state.systems["102"].space_units["p2"] = {"cruiser": 2, "destroyer": 1}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=_round_end_ctx())
    assert [o.player_id for o in state.pending_offers] == ["p1"]
    after = _accept(state, "p1", {"ships": ["cruiser#1", "destroyer#1"]})
    assert after.systems["102"].space_units["p1"] == {"carrier": 1}
    assert after.systems["102"].space_units["p2"] == {"cruiser": 1}


@ruling("F_norr/exotrireme/3")
def test_exotrireme_po_odwrocie_przeciwnika_brak_oferty(registry: StaticDataRegistry) -> None:
    """F_norr: gdy przeciwnik się wycofuje, Exotrireme II nie działa."""
    state = _state()
    state.players["p1"].technologies = ["exo2"]
    state.systems["102"].space_units["p1"] = {"dreadnought": 1}
    state.systems["102"].space_units["p2"] = {"cruiser": 1}
    state.systems["000"].space_units["p2"] = {"carrier": 1}  # cel odwrotu
    combat = _combat(state, "space")
    combat.retreating = ["p2"]
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=_round_end_ctx())
    assert state.pending_offers == []
    combat.retreating = []  # bez odwrotu oferta jest
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=_round_end_ctx())
    assert [o.player_id for o in state.pending_offers] == ["p1"]


def test_exotrireme_bez_technologii_brak_oferty(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units["p1"] = {"dreadnought": 1}
    state.systems["102"].space_units["p2"] = {"cruiser": 1}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.END, ctx=_round_end_ctx())
    assert state.pending_offers == []


@ruling("technologies:exo2#3")
def test_direct_hit_nie_celuje_w_exotrireme_ii(registry: StaticDataRegistry) -> None:
    state = _state()
    combat = _combat(state, "space", CombatStep.ASSIGN)
    state.systems["102"].space_units["p1"] = {"dreadnought": 1}
    combat.sustained_ships = [{"player": "p1", "base_type": "dreadnought", "count": 1}]
    from src.core import damage

    damage.set_damaged(state.systems["102"], "space", "p1", "dreadnought", 1)
    assert reactions_combat._sustained_of(combat, state, "p1") == ["dreadnought"]
    state.players["p1"].technologies = ["exo2"]
    assert reactions_combat._sustained_of(combat, state, "p1") == []


# ---------------------------------------------------------------------------- Tekklar Legion


@ruling("promissory_notes:tekklar#1", "promissory_notes:tekklar#2", "promissory_notes:tekklar#3")
def test_tekklar_legion_bonus_i_kara(registry: StaticDataRegistry) -> None:
    state = _state()
    _combat(state, "ground", CombatStep.ROLL)
    state.players["p2"].private.promissory_notes = ["tekklar"]
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows["tekklar"]["playable"] is True, rows["tekklar"]["reason"]
    after, implemented = promissory_play.play(state, registry, "p2", "tekklar")
    assert implemented is True
    point = rules_hooks.POINT_COMBAT_ROLL_MODIFIER
    ctx = {"kind": "ground"}
    assert rules_hooks.modify(point, after, "p2", 0, ctx) == 1
    assert rules_hooks.modify(point, after, "p1", 0, ctx) == 0  # Unrelenting +1, Tekklar -1
    assert "tekklar" in after.players["p1"].private.promissory_notes  # wraca do N'orr


def test_tekklar_poza_walka_naziemna(registry: StaticDataRegistry) -> None:
    state = _state()
    _combat(state, "space", CombatStep.ROLL)
    state.players["p2"].private.promissory_notes = ["tekklar"]
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows["tekklar"]["playable"] is False


# ------------------------------------------------------------------------------------- T'ro


@ruling("leaders:sardakkagent#1", "leaders:sardakkagent#2")
def test_agent_tro_daje_piechote_aktywnemu(registry: StaticDataRegistry) -> None:
    state = _state(sardakk_active=False)
    state.systems["102"].planet_owners["industrex"] = "p2"
    ctx = {"position": "102", "player": "p2"}
    triggers.fire(state, GameEvent.TACTICAL_ACTION, Moment.END, subject="p2", ctx=ctx)
    assert state.pending_offers == []  # cooperative: requested, not pushed (54.15)
    state = boosts.request(state, registry, "p2", "T'ro")
    assert [o.player_id for o in state.pending_offers] == ["p1"]
    after = _accept(state, "p1")
    assert leaders.state_of(after, registry, "p1", "sardakkagent") == leaders.EXHAUSTED
    assert [o.player_id for o in after.pending_offers] == ["p2"]  # decyduje aktywny
    done = _accept(after, "p2", {"planet": "industrex"})
    assert done.systems["102"].planet_units["industrex"]["p2"] == {"infantry": 2}


def test_agent_tro_bez_planety_aktywnego_brak_oferty(registry: StaticDataRegistry) -> None:
    state = _state(sardakk_active=False)
    ctx = {"position": "102", "player": "p2"}
    triggers.fire(state, GameEvent.TACTICAL_ACTION, Moment.END, subject="p2", ctx=ctx)
    assert state.pending_offers == []


# --------------------------------------------------------------------------- G'hom Sek'kus


@ruling("leaders:sardakkcommander#unlock")
def test_commander_odblokowanie_planety_poza_domami(registry: StaticDataRegistry) -> None:
    state = _state()
    for i in range(5):
        state.systems["103"].planet_owners[f"home{i}"] = "p1"  # system domowy (Jord)
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", "sardakkcommander") == leaders.LOCKED
    for i in range(5):
        state.systems["000"].planet_owners[f"x{i}"] = "p1"
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", "sardakkcommander") == leaders.UNLOCKED


@ruling("leaders:sardakkcommander#1")
def test_commander_laduje_z_sasiedniej_planety(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"sardakkcommander": "unlocked"}
    state.tactical_step = TacticalStep.INVASION
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.COMMIT)
    state.systems["000"].planet_units["mr"] = {"p1": {"infantry": 2}}
    state.players["p1"].technologies = ["amd"]  # 102 w siatce demo to pole asteroid
    form = faction_components.form(state, registry, "p1", "leader", "sardakkcommander")
    assert form["mode"] == "window"
    keys = [i["key"] for i in form["inputs"]]
    assert keys == ["src:000:mr"]
    after, _ = faction_components.play(
        state, registry, "p1", "leader", "sardakkcommander",
        {"src:000:mr": "infantry>industrex"},
    )
    assert after.systems["000"].planet_units["mr"]["p1"] == {"infantry": 1}  # najwyżej 1
    assert after.systems["102"].planet_units["industrex"]["p1"] == {"infantry": 1}
    assert after.players["p1"].took_action_this_turn is False  # nie zużywa akcji
    with pytest.raises(ValueError, match="already used"):
        faction_components.play(
            after, registry, "p1", "leader", "sardakkcommander",
            {"src:000:mr": "infantry>industrex"},
        )


def test_commander_nie_z_systemu_z_wlasnym_zetonem(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"sardakkcommander": "unlocked"}
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.COMMIT)
    state.systems["000"].planet_units["mr"] = {"p1": {"infantry": 2}}
    state.systems["000"].command_tokens = ["p1"]
    reason = sardakk._commander_window(state, registry, "p1")
    assert reason is not None and "no ground forces" in reason


def _ghom_grid(active: set[str], source: set[str]) -> HexGrid:
    """102 (aktywny, Industrex) i sąsiedni 000 (Mecatol) z wybranymi anomaliami."""
    grid = HexGrid()
    grid.place_system("102", "115", anomalies=active)
    grid.place_system("000", "18", anomalies=source)
    grid.build_edges()
    return grid


def _provider(grid: HexGrid) -> Callable[[], HexGrid]:
    return lambda: grid


def _ghom_state() -> GameState:
    state = _state()
    state.players["p1"].leader_states = {"sardakkcommander": "unlocked"}
    state.tactical_step = TacticalStep.INVASION
    state.invasion = InvasionState(position="102", attacker="p1", phase=InvasionPhase.COMMIT)
    state.systems["000"].planet_units["mr"] = {"p1": {"infantry": 2}}
    return state


@ruling("F_norr/ghom-sekkus/6", "F_norr/ghom-sekkus/6.2")
def test_commander_nie_do_asteroid_ani_supernowej(registry: StaticDataRegistry) -> None:
    """F_norr: siły muszą legalnie wejść do aktywnego systemu (Mirage w asteroidach/supernowej)."""
    previous = board_graph._PROVIDER
    try:
        for anomaly in ("SUPERNOVA", "ASTEROID_FIELD"):
            board_graph.bind_grid_provider(_provider(_ghom_grid({anomaly}, set())))
            sources = sardakk._commander_sources(_ghom_state(), registry, "p1")
            assert [pos for pos, _, _ in sources] == []
        state = _ghom_state()
        state.players["p1"].technologies = ["amd"]  # Antimass Deflectors: asteroidy wolno
        assert [pos for pos, _, _ in sardakk._commander_sources(state, registry, "p1")] == ["000"]
    finally:
        board_graph.bind_grid_provider(previous)


@ruling("F_norr/ghom-sekkus/6.3")
def test_commander_z_gravity_rift_rzuca(registry: StaticDataRegistry) -> None:
    """F_norr: siły wychodzące z systemu z gravity rift rzucają na usunięcie (1–3)."""
    previous = board_graph._PROVIDER
    grid = _ghom_grid(set(), {"GRAVITY_RIFT"})
    board_graph.bind_grid_provider(lambda: grid)
    try:
        after, _ = faction_components.play(
            _ghom_state(), registry, "p1", "leader", "sardakkcommander",
            {"src:000:mr": "infantry>industrex"},
        )
    finally:
        board_graph.bind_grid_provider(previous)
    roll = after.table_roll
    assert roll is not None and roll["kind"] == "gravity_rift" and len(roll["dice"]) == 1
    landed = after.systems["102"].planet_units.get("industrex", {}).get("p1", {})
    assert after.systems["000"].planet_units["mr"]["p1"] == {"infantry": 1}
    assert landed == ({} if roll["dice"][0] <= 3 else {"infantry": 1})


# ----------------------------------------------------------------- Sh'val (Tekklar Conditioning)


@ruling(
    "leaders:sardakkhero#1", "leaders:sardakkhero#2",
    "F_norr/shval-harbinger-tekklar-conditioning/1",
)
def test_hero_pomija_do_ladowania_i_zwraca_statki(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"sardakkhero": "unlocked"}
    state.tactical_step = TacticalStep.MOVEMENT
    state.tactical_moved = True
    state.systems["102"].space_units["p1"] = {"carrier": 1, "infantry": 2}
    state.systems["102"].space_units["p2"] = {"destroyer": 1}  # walka kosmiczna pominięta
    after, _ = faction_components.play(state, registry, "p1", "leader", "sardakkhero")
    assert after.tactical_step is TacticalStep.INVASION
    assert leaders.state_of(after, registry, "p1", "sardakkhero") == leaders.PURGED
    grid = build_demo_grid(registry)
    started = invasion.begin_invasion(after, grid, registry)
    assert started.invasion is not None and started.invasion.phase is InvasionPhase.COMMIT
    landed = invasion.commit_ground_forces(started, registry, {"industrex": {"infantry": 2}})
    assert "carrier" not in landed.systems["102"].space_units.get("p1", {})
    assert not active_effects.has_effect(landed, "p1", sardakk.HERO_EFFECT)


def test_hero_przed_ruchem_niedostepny(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"sardakkhero": "unlocked"}
    state.tactical_step = TacticalStep.MOVEMENT
    with pytest.raises(ValueError, match="after you move ships"):
        faction_components.play(state, registry, "p1", "leader", "sardakkhero")


# ------------------------------------------------------------------- N'orr Supremacy (BT)


@ruling("breakthroughs:sardakkbt#1")
def test_przelom_po_wygranej_walce_zeton(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    fleet = state.players["p1"].fleet_cc
    ctx = {"kind": "space", "position": "102", "winner": "p1", "planet": "",
           "attacker": "p1", "defender": "p2"}
    triggers.fire(state, GameEvent.COMBAT_WON, Moment.AFTER, subject="p1", ctx=ctx)
    assert [o.player_id for o in state.pending_offers] == ["p1"]
    after = _accept(state, "p1", {"reward": "cc:fleet"})
    assert after.players["p1"].fleet_cc == fleet + 1


@ruling("breakthroughs:sardakkbt#1", "R_technology/notes/1")
def test_przelom_badanie_ulepszenia(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    inputs = sardakk.supremacy_inputs(state, registry, "p1", {})
    assert not [o for o in inputs[0]["options"] if str(o["value"]).startswith("tech:")]
    # Gracz z kilkoma technologiami każdego koloru spełnia prerekwizyty części ulepszeń.
    by_color: dict[str, list[str]] = {}
    for tid, tech in registry.technologies.items():
        if tech.faction is None and len(tech.types) == 1 and tech.types[0] != "UNITUPGRADE":
            by_color.setdefault(tech.types[0], []).append(tid)
    state.players["p1"].technologies = [t for ids in by_color.values() for t in sorted(ids)[:3]]
    inputs = sardakk.supremacy_inputs(state, registry, "p1", {})
    techs = [o["value"] for o in inputs[0]["options"] if str(o["value"]).startswith("tech:")]
    assert techs
    for value in techs:
        tech = registry.technologies[value[5:]]
        assert "UNITUPGRADE" in tech.types


def test_przelom_badanie_ze_skipem(registry: StaticDataRegistry) -> None:
    """Decyzja użytkownika 2026-11-13: prerekwizyty wolno pominąć skipem (tu: AIDA)."""
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.players["p1"].technologies = ["aida"]  # 1x czerwony; Destroyer II wymaga RR
    inputs = sardakk.supremacy_inputs(state, registry, "p1", {})
    assert "tech:dd2" in [o["value"] for o in inputs[0]["options"]]
    assert "aida" in [o["value"] for o in inputs[1]["options"]]
    ctx = {"kind": "space", "position": "102", "winner": "p1", "planet": "",
           "attacker": "p1", "defender": "p2"}
    triggers.fire(state, GameEvent.COMBAT_WON, Moment.AFTER, subject="p1", ctx=ctx)
    with pytest.raises(ValueError):
        _accept(state, "p1", {"reward": "tech:dd2", "skips": []})
    after = _accept(state, "p1", {"reward": "tech:dd2", "skips": ["aida"]})
    assert "dd2" in after.players["p1"].technologies
    assert "aida" in after.players["p1"].exhausted_technologies


def test_przelom_bez_wygranej_nic(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    ctx = {"kind": "space", "position": "102", "winner": "p2", "planet": "",
           "attacker": "p1", "defender": "p2"}
    triggers.fire(state, GameEvent.COMBAT_WON, Moment.AFTER, subject="p2", ctx=ctx)
    assert state.pending_offers == []
