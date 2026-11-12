"""Arborec — komplet komponentów frakcji (RULES.md 62.5), konwencja par."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    board_graph,
    faction_components,
    leaders,
    production,
    promissory_play,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
)
from src.core.hooks import technologies_passive
from src.core.hooks.factions import arborec
from src.core.registry import StaticDataRegistry
from tests.factions.completeness import missing_components


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


def _state() -> GameState:
    """p1 = Arborec (aktywny), p2 = Sol; p1 kontroluje Industrex (102) i Meer (103)."""
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="102",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="green", faction="arborec", trade_goods=4),
            "p2": PlayerState(player_id="p2", color="blue", faction="sol", trade_goods=2),
        },
        systems={
            "102": SystemState(position="102", system_id="115"),
            "103": SystemState(position="103", system_id="19"),
        },
        rng_seed=7,
    )
    state.systems["102"].planet_owners = {"industrex": "p1"}
    return state


def _accept(
    state: GameState, player: str, label_part: str, params: dict[str, Any] | None = None
) -> GameState:
    offer = next(
        o for o in state.pending_offers if o.player_id == player and label_part in o.label
    )
    return triggers.accept_offer(state, player, offer.id, params)


def _labels(state: GameState, player: str) -> list[str]:
    return [o.label for o in state.pending_offers if o.player_id == player]


def _ground(state: GameState, position: str, planet: str, player: str = "p1") -> dict[str, int]:
    return state.systems[position].planet_units.get(planet, {}).get(player, {})


# ------------------------------------------------------------------------------- kompletność


def test_frakcja_kompletna(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "arborec") == []


# ------------------------------------------------------------------ Mitosis + Letani Behemoth


def test_mitosis_piechota_na_start_statusu() -> None:
    state = _state()
    triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "status"})
    # Jedna legalna opcja: decyzja obowiązkowa wykonuje się od razu (RULES.md 56).
    assert _ground(state, "102", "industrex") == {"infantry": 1}
    state.systems["103"].planet_owners = {"meer": "p1"}
    triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "status"})
    offer = next(o for o in state.pending_offers if o.player_id == "p1")
    after = triggers.accept_offer(state, "p1", offer.id, {"mitosis": "inf|103|meer"})
    assert _ground(after, "103", "meer") == {"infantry": 1}


def test_mitosis_mech_zamiast_piechoty() -> None:
    state = _state()
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 2}}}
    triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "status"})
    offer = next(o for o in state.pending_offers if o.player_id == "p1")
    after = triggers.accept_offer(state, "p1", offer.id, {"mitosis": "mech|102|industrex"})
    assert _ground(after, "102", "industrex") == {"infantry": 1, "mech": 1}


def test_mitosis_bez_planet_nic() -> None:
    state = _state()
    state.systems["102"].planet_owners = {}
    triggers.fire(state, GameEvent.PHASE, Moment.START, ctx={"phase": "status"})
    assert not [o for o in state.pending_offers if o.player_id == "p1"]


def test_doki_nie_produkuja_piechoty_sol_tak(registry: StaticDataRegistry) -> None:
    from src.core import rules_hooks

    state = _state()
    point = rules_hooks.POINT_PRODUCTION_FORBIDS
    assert "infantry" in rules_hooks.forbidden(point, state, "p1", {"producer_type": "spacedock"})
    assert not rules_hooks.forbidden(point, state, "p2", {"producer_type": "spacedock"})


# ------------------------------------------------------------- Bioplasmosis, Letani Warrior II


def test_bioplasmosis_jednoczesny_ruch_do_sasiedniego() -> None:
    state = _state()
    state.players["p1"].technologies = ["bio"]
    state.systems["103"].planet_owners = {"meer": "p1"}
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 3}}}
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    after = _accept(state, "p1", "Bioplasmosis", {"bio:102:industrex:103:meer": 2})
    assert _ground(after, "102", "industrex") == {"infantry": 1}
    assert _ground(after, "103", "meer") == {"infantry": 2}


def test_bioplasmosis_nie_wiecej_niz_jest() -> None:
    state = _state()
    state.players["p1"].technologies = ["bio"]
    state.systems["103"].planet_owners = {"meer": "p1"}
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 1}}}
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    with pytest.raises(ValueError):
        _accept(state, "p1", "Bioplasmosis", {"bio:102:industrex:103:meer": 3})


def test_letani_warrior_ii_prog_z_karty() -> None:
    assert technologies_passive.revive_threshold("lw2") == 6


# --------------------------------------------------------------------------- Letani Ospha


def test_letani_ospha_wlasciciel_zamienia_statek(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units = {"p2": {"destroyer": 1}}
    used, _ = faction_components.play(
        state, registry, "p1", "leader", "arborecagent", {"ship": "p2|102|destroyer"}
    )
    assert leaders.state_of(used, registry, "p1", "arborecagent") == leaders.EXHAUSTED
    assert any("Letani Ospha" in label for label in _labels(used, "p2"))
    with pytest.raises(ValueError):  # dreadnought kosztuje o więcej niż 2
        _accept(used, "p2", "Letani Ospha", {"replacement": "dreadnought"})
    after = _accept(used, "p2", "Letani Ospha", {"replacement": "cruiser"})
    assert after.systems["102"].space_units["p2"] == {"cruiser": 1}


def test_letani_ospha_bez_mysliwcow_do_wyboru(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units = {"p2": {"fighter": 2}}
    inputs = arborec.agent_inputs(state, registry, "p1")
    assert inputs[0]["options"] == []


# ------------------------------------------------------------------------ Dirzuga Rophal


def test_dirzuga_rophal_produkcja_po_cudzej_aktywacji(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"arboreccommander": "unlocked"}
    state.systems["102"].planet_units = {"industrex": {"p1": {"spacedock": 1}}}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": "102"})
    after = _accept(state, "p1", "Dirzuga")
    grant = after.production_grant
    assert grant is not None and grant.player_id == "p1" and grant.units == 1 and grant.free


def test_dirzuga_rophal_nie_przy_wlasnej_aktywacji() -> None:
    state = _state()
    state.players["p1"].leader_states = {"arboreccommander": "unlocked"}
    state.systems["102"].planet_units = {"industrex": {"p1": {"spacedock": 1}}}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "102"})
    assert not any("Dirzuga" in label for label in _labels(state, "p1"))


def test_dirzuga_rophal_odblokowanie_12_sil(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 11}}}
    assert arborec._commander_unlocked(state, registry, "p1") is False
    state.systems["102"].planet_units["industrex"]["p1"]["mech"] = 1
    assert arborec._commander_unlocked(state, registry, "p1") is True


# -------------------------------------------------------------- Duha Menaimon (flagowiec)


def test_duha_menaimon_5_jednostek_po_aktywacji() -> None:
    state = _state()
    state.systems["102"].space_units = {"p1": {"flagship": 1}}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "102"})
    after = _accept(state, "p1", "Duha Menaimon")
    assert after.production_grant is not None and after.production_grant.units == 5


def test_duha_menaimon_bez_flagowca() -> None:
    state = _state()
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "102"})
    assert not any("Duha" in label for label in _labels(state, "p1"))


# ---------------------------------------------------------------- Letani Miasmiala (hero)


def test_ultrasonic_emitter_kolejka_systemow(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"arborechero": "unlocked"}
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 1}}}
    state.systems["103"].space_units = {"p1": {"infantry": 1}}
    after, _ = faction_components.play(
        state, registry, "p1", "leader", "arborechero", {"systems": ["102", "103"]}
    )
    grant = after.production_grant
    assert grant is not None and grant.position == "102" and grant.queue == ["103"]
    assert leaders.state_of(after, registry, "p1", "arborechero") == leaders.PURGED
    nxt = production.skip_grant(after).production_grant
    assert nxt is not None and nxt.position == "103" and nxt.queue == []
    assert production.skip_grant(production.skip_grant(after)).production_grant is None


def test_ultrasonic_emitter_bez_sil_naziemnych(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"arborechero": "unlocked"}
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p1")}
    assert rows["arborechero"]["playable"] is False


# ------------------------------------------------------------------------------ Stymie


def _moved_into(state: GameState) -> None:
    state.active_player_id = "p2"
    state.tactical_step = TacticalStep.MOVEMENT
    state.tactical_moved = True


def test_stymie_zeton_przeciwnika_w_systemie(registry: StaticDataRegistry) -> None:
    state = _state()
    _moved_into(state)
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 1}}}
    state.players["p2"].private.promissory_notes = ["stymie"]
    state.players["p1"].private.promissory_notes = []
    # Notkę gra posiadacz (tu: Arborec dostał ją od kogoś? nie - własnej nie wolno).
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows["stymie"]["playable"] is False  # p2 to ruszający się gracz
    state.players["p2"].private.promissory_notes = []
    state.players["p1"].faction = "letnev"  # posiadacz ≠ Arborec, właściciel = p3
    state.players["p3"] = PlayerState(player_id="p3", color="red", faction="arborec")
    state.players["p1"].private.promissory_notes = ["stymie"]
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p1")}
    assert rows["stymie"]["playable"] is True, rows["stymie"]["reason"]
    reinforcements = state.players["p2"].cc_reinf
    after, _ = promissory_play.play(state, registry, "p1", "stymie", {"system": "103"})
    assert "p2" in after.systems["103"].command_tokens
    assert after.players["p2"].cc_reinf == reinforcements - 1
    assert "stymie" in after.players["p3"].private.promissory_notes


# ----------------------------------------------------------------- Psychospore (BT)


def test_psychospore_zdejmuje_zeton_i_stawia_piechote(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.systems["102"].command_tokens = ["p1"]
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 1}}}
    reinforcements = state.players["p1"].cc_reinf
    after, _ = faction_components.play(
        state, registry, "p1", "breakthrough", "arborecbt", {"target": "102|industrex"}
    )
    assert after.systems["102"].command_tokens == []
    assert after.players["p1"].cc_reinf == reinforcements + 1
    assert _ground(after, "102", "industrex") == {"infantry": 2}
    assert after.players["p1"].breakthrough_exhausted is True


def test_psychospore_bez_zetonu(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 1}}}
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p1")}
    assert rows["arborecbt"]["playable"] is False


# ------------------------------------------------- rulingi: żeton z arkusza, statek z planszy


def test_stymie_pusta_rezerwa_zeton_z_arkusza(registry: StaticDataRegistry) -> None:
    state = _state()
    _moved_into(state)
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 1}}}
    state.players["p1"].faction = "letnev"
    state.players["p3"] = PlayerState(player_id="p3", color="red", faction="arborec")
    state.players["p1"].private.promissory_notes = ["stymie"]
    state.players["p2"].cc_reinf = 0
    fleet = state.players["p2"].fleet_cc
    after, _ = promissory_play.play(state, registry, "p1", "stymie", {"system": "103"})
    offer = next(o for o in after.pending_offers if o.player_id == "p2")
    placed = triggers.accept_offer(after, "p2", offer.id, {"pool": "fleet"})
    assert "p2" in placed.systems["103"].command_tokens
    assert placed.players["p2"].fleet_cc == fleet - 1


def test_letani_ospha_statek_z_planszy_gdy_rezerwa_pusta(registry: StaticDataRegistry) -> None:
    state = _state()
    cap = production.reinforcements_left(state, "p2", "cruiser")
    assert cap is not None and cap > 0
    state.systems["102"].space_units = {"p2": {"destroyer": 1}}
    state.systems["103"].space_units = {"p2": {"cruiser": cap}}  # cała rezerwa na planszy
    used, _ = faction_components.play(
        state, registry, "p1", "leader", "arborecagent", {"ship": "p2|102|destroyer"}
    )
    after = _accept(used, "p2", "Letani Ospha", {"replacement": "cruiser@103"})
    assert after.systems["102"].space_units["p2"] == {"cruiser": 1}
    assert after.systems["103"].space_units["p2"]["cruiser"] == cap - 1


def test_dirzuga_rophal_wstrzymuje_ruch_aktywnego(registry: StaticDataRegistry) -> None:
    from src.core import movement, tactical
    from src.core.game_state import ProductionGrant

    grid = build_demo_grid(registry)
    state = _state()
    state.active_player_id = "p2"
    state.tactical_step = TacticalStep.MOVEMENT
    state.systems["103"].space_units = {"p2": {"cruiser": 1}}
    state.production_grant = ProductionGrant(
        player_id="p1", position="102", units=1, free=True, source="Dirzuga Rophal"
    )
    ok, reason = movement.can_move(state, grid, registry, "103", "cruiser", "p2")
    assert ok is False and "Dirzuga Rophal" in reason
    with pytest.raises(ValueError, match="Dirzuga"):
        tactical.next_step(state, registry)
    state.production_grant = None
    assert "Dirzuga" not in movement.can_move(state, grid, registry, "103", "cruiser", "p2")[1]
