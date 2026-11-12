"""Universities of Jol-Nar — komplet komponentów frakcji (RULES.md 62.3), konwencja par."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    active_effects,
    battle,
    board_graph,
    faction_components,
    leaders,
    movement,
    promissory_play,
    space_cannon,
    technology,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    Phase,
    PlayerState,
    SystemState,
    TimingWindow,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.hooks.factions import jolnar
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards import technology as technology_card
from src.core.strategy_cards.base import CardContext
from tests.factions.completeness import missing_components


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture(scope="module")
def grid(registry: StaticDataRegistry) -> HexGrid:
    return build_demo_grid(registry)


@pytest.fixture(autouse=True, scope="module")
def _grid(grid: HexGrid) -> Iterator[None]:
    previous = board_graph._PROVIDER
    board_graph.bind_grid_provider(lambda: grid)
    yield
    board_graph.bind_grid_provider(previous)


def _state() -> GameState:
    """p1 = Jol-Nar (aktywny), p2 = Sol; system 102 z planetą Industrex (specjalność WARFARE)."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="102",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="jolnar", trade_goods=3),
            "p2": PlayerState(player_id="p2", color="blue", faction="sol", trade_goods=8),
        },
        systems={
            "102": SystemState(position="102", system_id="115"),
            "105": SystemState(position="105", system_id="19"),
        },
        rng_seed=7,
    )


def _accept(
    state: GameState, player: str, label_part: str, params: dict[str, Any] | None = None
) -> GameState:
    offer = next(
        o for o in state.pending_offers if o.player_id == player and label_part in o.label
    )
    return triggers.accept_offer(state, player, offer.id, params)


def _labels(state: GameState, player: str) -> list[str]:
    return [o.label for o in state.pending_offers if o.player_id == player]


# ------------------------------------------------------------------------------- kompletność


def test_frakcja_kompletna(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "jolnar") == []


# ------------------------------------------------------------------- Fragile, mech, flagowiec


def _modifiers(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player: str, kind: str
) -> dict[str, int]:
    units = battle.combat_units(
        state, grid, registry, kind=kind, position="102",
        planet="industrex" if kind == "ground" else None, player_id=player,
    )
    return {u.base_type: u.modifier for u in units}


def test_fragile_minus_jeden_tylko_jolnar(registry: StaticDataRegistry, grid: HexGrid) -> None:
    state = _state()
    state.systems["102"].space_units = {"p1": {"cruiser": 1}, "p2": {"cruiser": 1}}
    assert _modifiers(state, grid, registry, "p1", "space") == {"cruiser": -1}
    assert _modifiers(state, grid, registry, "p2", "space") == {"cruiser": 0}


def test_shield_paling_znosi_fragile_piechocie(
    registry: StaticDataRegistry, grid: HexGrid
) -> None:
    state = _state()
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 2, "mech": 1}}}
    assert _modifiers(state, grid, registry, "p1", "ground") == {"infantry": 0, "mech": -1}
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 2}}}
    assert _modifiers(state, grid, registry, "p1", "ground") == {"infantry": -1}


def test_hylarim_dodatkowe_trafienia_z_naturalnego_wyniku() -> None:
    state = _state()
    assert battle.natural_extra_hits(state, "p1", "space", "flagship", [9, 10, 8]) == 4
    assert battle.natural_extra_hits(state, "p1", "space", "cruiser", [9, 10]) == 0
    assert battle.natural_extra_hits(state, "p2", "space", "flagship", [10]) == 0


# ------------------------------------------------------------------- Analytical, Brilliant


def test_analytical_ignoruje_jeden_prerekwizyt(registry: StaticDataRegistry) -> None:
    state = _state()
    plan = technology.plan_research(state, registry, "p1", "gls", [])  # wymaga 1× żółty
    assert plan.tech_id == "gls"
    rows = {r["id"]: r for r in technology.tree_view(state, registry, "p1")}
    assert rows["gls"]["status"] == "available" and rows["gls"]["missing"] == {}
    with pytest.raises(ValueError):  # 2 brakujące symbole - ignoruje tylko 1
        technology.plan_research(state, registry, "p1", "td", [])
    with pytest.raises(ValueError):  # bez Analytical
        technology.plan_research(state, registry, "p2", "gls", [])


def test_analytical_nie_dla_ulepszen_jednostek(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["amd"]  # 1× niebieski; Carrier II wymaga BB
    with pytest.raises(ValueError):
        technology.plan_research(state, registry, "p1", "cv2", [])


def test_brilliant_secondary_jak_primary(registry: StaticDataRegistry) -> None:
    state = _state()
    ctx = CardContext(registry, None)
    options = technology_card._options(state, ctx, "p1", None, {})
    assert options["cost"] == 0 and options["as_primary"] is True
    technology_card._secondary(state, ctx, "p1", {"tech": "nm", "second": {"tech": None}})
    assert "nm" in state.players["p1"].technologies
    # Sol (bez Brilliant) płaci 4 zasoby: bez płatności - błąd.
    with pytest.raises(ValueError):
        technology_card._secondary(state, ctx, "p2", {"tech": "nm"})


# ----------------------------------------------------------------- E-Res Siphons, SCC


def test_ers_cudza_aktywacja_daje_4_tg() -> None:
    state = _state()
    state.systems["102"].space_units = {"p1": {"cruiser": 1}}
    state.players["p1"].technologies = ["ers"]
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "position": "102"})
    assert state.players["p1"].trade_goods == 7
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "102"})
    assert state.players["p1"].trade_goods == 7  # własna aktywacja - nic


def test_scc_laczy_aktywny_system_z_twoimi(grid: HexGrid) -> None:
    state = _state()
    state.players["p1"].technologies = ["scc"]
    state.systems["102"].space_units = {"p1": {"cruiser": 1}}
    state.systems["105"].space_units = {"p1": {"carrier": 1}}
    assert "102" not in movement._neighbors_for_move(grid, state, "105", "p1")
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "102"})
    after = _accept(state, "p1", "Spatial Conduit")
    assert "scc" in after.players["p1"].exhausted_technologies
    assert "102" in movement._neighbors_for_move(grid, after, "105", "p1")
    assert "105" in movement._neighbors_for_move(grid, after, "102", "p1")
    assert "102" not in movement._neighbors_for_move(grid, after, "105", "p2")


def test_scc_brak_oferty_bez_innych_jednostek() -> None:
    state = _state()
    state.players["p1"].technologies = ["scc"]
    state.systems["102"].space_units = {"p1": {"cruiser": 1}}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "position": "102"})
    assert not any("Spatial" in label for label in _labels(state, "p1"))


# -------------------------------------------------------------------- Research Agreement


def test_research_agreement_daje_zbadana_technologie(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["nm"]
    state.last_research = [{"player": "p1", "technology": "nm"}]
    state.players["p2"].private.promissory_notes = ["ra"]
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows["ra"]["playable"] is True, rows["ra"]["reason"]
    after, implemented = promissory_play.play(state, registry, "p2", "ra", {"technology": "nm"})
    assert implemented is True
    assert "nm" in after.players["p2"].technologies
    assert "ra" in after.players["p1"].private.promissory_notes


def test_research_agreement_nie_dla_technologii_frakcyjnej(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["ers"]
    state.last_research = [{"player": "p1", "technology": "ers"}]
    state.players["p2"].private.promissory_notes = ["ra"]
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows["ra"]["playable"] is False


def test_apply_research_zostawia_slad(registry: StaticDataRegistry) -> None:
    state = _state()
    plan = technology.plan_research(state, registry, "p1", "nm", [])
    technology.apply_research(state, "p1", plan)
    assert state.last_research == [{"player": "p1", "technology": "nm"}]


# ------------------------------------------------------------------------ Doctor Sucaban


def _secondary_window(state: GameState, responder: str) -> None:
    state.pending_window = TimingWindow(
        window_type=WindowType.STRATEGY_SECONDARY, queue=[responder],
        context={"initiative": technology_card.INITIATIVE},
    )


def test_sucaban_zdjeta_piechota_obniza_koszt(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].planet_units = {"industrex": {"p2": {"infantry": 3}}}
    _secondary_window(state, "p2")
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p1")}
    assert rows["jolnaragent"]["playable"] is True, rows["jolnaragent"]["reason"]
    used, _ = faction_components.play(state, registry, "p1", "leader", "jolnaragent")
    assert leaders.state_of(used, registry, "p1", "jolnaragent") == leaders.EXHAUSTED
    after = _accept(used, "p2", "Sucaban", {"inf:102:industrex": 2})
    assert after.systems["102"].planet_units["industrex"]["p2"]["infantry"] == 1
    options = technology_card._options(after, CardContext(registry, None), "p2", None, {})
    assert options["cost"] == technology_card.SECONDARY_COST - 2


def test_sucaban_poza_badaniem(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].planet_units = {"industrex": {"p2": {"infantry": 3}}}
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p1")}
    assert rows["jolnaragent"]["playable"] is False


# ----------------------------------------------------------------------------- Agnlan Oln


def test_agnlan_oln_odblokowanie_8_technologii(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["nm", "pa", "bs", "dxa", "hm", "sdn", "st"]
    assert leaders.unlock_predicate(registry, "jolnarcommander") is not None
    assert jolnar._commander_unlocked(state, registry, "p1") is False
    state.players["p1"].technologies.append("gls")
    assert jolnar._commander_unlocked(state, registry, "p1") is True


def test_agnlan_oln_bez_rzutu_zdolnosci(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"jolnarcommander": "unlocked"}
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p1")}
    assert rows["jolnarcommander"]["playable"] is False


def test_przerzut_tylko_wybranych_kosci() -> None:
    state = _state()
    entries = [{"baseType": "pds", "dice": [1, 1, 1], "hitsOn": 6, "modifier": 0}]
    fresh, _ = space_cannon.reroll_entries(
        state, entries, roller="p1", picks={(0, 1)}, source=("agnlan_oln", "Agnlan Oln")
    )
    assert fresh[0]["dice"][0] == 1 and fresh[0]["dice"][2] == 1


# ------------------------------------------------------------------ Rin — Genetic Memory


def test_genetic_memory_zamienia_technologie_tego_koloru(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["nm", "amd"]
    state.players["p1"].leader_states = {"jolnarhero": "unlocked"}
    after, implemented = faction_components.play(
        state, registry, "p1", "leader", "jolnarhero",
        {"tech:nm": "hm", "tech:amd": "keep"},
    )
    assert implemented is True
    assert set(after.players["p1"].technologies) == {"hm", "amd"}
    assert leaders.state_of(after, registry, "p1", "jolnarhero") == leaders.PURGED


def test_genetic_memory_zly_kolor_odrzucony(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].technologies = ["nm"]
    state.players["p1"].leader_states = {"jolnarhero": "unlocked"}
    with pytest.raises(ValueError):
        faction_components.play(state, registry, "p1", "leader", "jolnarhero", {"tech:nm": "gd"})


# ------------------------------------------------------------ Specialist Compounds (BT)


def _paid_research(state: GameState, registry: StaticDataRegistry, payload: dict[str, Any]) -> str:
    return technology_card._research_with_cost(
        state, CardContext(registry, None), "p1", payload, technology_card.SECOND_RESEARCH_COST
    )


def test_specialist_compounds_planeta_zamiast_zasobow(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.systems["102"].planet_owners = {"industrex": "p1"}  # specjalność WARFARE
    _paid_research(state, registry, {"tech": "ps", "compound_planet": "industrex"})
    assert "ps" in state.players["p1"].technologies
    assert "industrex" in state.players["p1"].exhausted_planets
    assert state.players["p1"].trade_goods == 3  # nic nie zapłacone


def test_specialist_compounds_kolor_musi_pasowac(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.systems["102"].planet_owners = {"industrex": "p1"}
    with pytest.raises(ValueError):
        _paid_research(state, registry, {"tech": "nm", "compound_planet": "industrex"})
    state.players["p1"].breakthrough_unlocked = False
    with pytest.raises(ValueError):  # bez przełomu
        _paid_research(state, registry, {"tech": "ps", "compound_planet": "industrex"})


def test_research_discount_zuzywany_przy_zaplacie(registry: StaticDataRegistry) -> None:
    from src.core.game_events import Duration

    state = _state()
    active_effects.add_effect(
        state, technology.RESEARCH_DISCOUNT, Duration.TURN, owner="p1", data={"amount": 6}
    )
    _paid_research(state, registry, {"tech": "nm"})
    assert technology.research_discount(state, "p1") == 0
