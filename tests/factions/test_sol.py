"""Federation of Sol — komplet komponentów frakcji (RULES.md 62.4), konwencja par."""

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
    rules_hooks,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, SystemState, TurnEndWindow
from src.core.hooks import technologies_passive
from src.core.hooks.factions import sol
from src.core.production import ProductionOrder
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
    """p1 = Sol (aktywny), p2 = Jol-Nar; p1 kontroluje Industrex (system 102)."""
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="102",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="sol", trade_goods=4),
            "p2": PlayerState(player_id="p2", color="blue", faction="jolnar"),
        },
        systems={"102": SystemState(position="102", system_id="115")},
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


def _infantry(state: GameState, player: str, zone: str = "industrex") -> int:
    system = state.systems["102"]
    if zone == "space":
        return system.space_units.get(player, {}).get("infantry", 0)
    return system.planet_units.get(zone, {}).get(player, {}).get("infantry", 0)


# ------------------------------------------------------------------------------- kompletność


def test_frakcja_kompletna(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "sol") == []


# ----------------------------------------------------------------- Orbital Drop + mech


def test_orbital_drop_zeton_za_dwie_piechoty(registry: StaticDataRegistry) -> None:
    state = _state()
    before = state.players["p1"].strategic_cc
    after, implemented = faction_components.play(
        state, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
    )
    assert implemented is True
    assert _infantry(after, "p1") == 2
    assert after.players["p1"].strategic_cc == before - 1
    # DEPLOY mecha: 3 zasoby (TG) po Orbital Drop.
    assert any("Thunderbolt" in label for label in _labels(after, "p1"))
    deployed = _accept(after, "p1", "Thunderbolt", {"planets": [], "trade_goods": 3})
    assert deployed.systems["102"].planet_units["industrex"]["p1"]["mech"] == 1
    assert deployed.players["p1"].trade_goods == 1


def test_orbital_drop_bez_zetonu_strategii(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].strategic_cc = 0
    rows = {r["component_id"]: r for r in faction_components.playability(state, registry, "p1")}
    assert rows["orbital_drop"]["playable"] is False


def test_thunderbolt_bez_zasobow_brak_oferty(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].trade_goods = 0
    after, _ = faction_components.play(
        state, registry, "p1", "ability", "orbital_drop", {"planet": "102|industrex"}
    )
    assert not any("Thunderbolt" in label for label in _labels(after, "p1"))


# ---------------------------------------------------------------- Versatile, Spec Ops II


def test_versatile_jeden_zeton_wiecej() -> None:
    state = _state()
    point = rules_hooks.POINT_STATUS_COMMAND_TOKENS
    assert rules_hooks.modify(point, state, "p1", 2) == 3
    assert rules_hooks.modify(point, state, "p2", 2) == 2


def test_spec_ops_prog_z_tekstu_karty() -> None:
    assert technologies_passive.revive_threshold("so2") == 5
    assert technologies_passive.revive_threshold("inf2") == 6


def test_spec_ops_rzut_po_zniszczeniu_piechoty() -> None:
    state = _state()
    state.players["p1"].technologies = ["so2"]
    triggers.fire(state, GameEvent.UNIT_DESTROYED, Moment.AFTER, subject="p1",
                  ctx={"player": "p1", "base_type": "infantry", "count": 3})
    assert state.table_roll_seq == 1
    state.players["p2"].technologies = []
    triggers.fire(state, GameEvent.UNIT_DESTROYED, Moment.AFTER, subject="p2",
                  ctx={"player": "p2", "base_type": "infantry", "count": 3})
    assert state.table_roll_seq == 1  # bez Spec Ops / Infantry II - bez rzutu


# --------------------------------------------------------------------- Genesis (flagowiec)


def test_genesis_piechota_w_przestrzeni_na_koniec_statusu() -> None:
    state = _state()
    state.systems["102"].space_units = {"p1": {"flagship": 1}}
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    assert _infantry(state, "p1", "space") == 1
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "action"})
    assert _infantry(state, "p1", "space") == 1


def test_genesis_bez_flagowca() -> None:
    state = _state()
    state.systems["102"].space_units = {"p1": {"carrier": 1}}
    triggers.fire(state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    assert _infantry(state, "p1", "space") == 0


# ------------------------------------------------------------------------ Evelyn DeLouis


def _ground_round(state: GameState) -> None:
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START, ctx={
        "kind": "ground", "round": 1, "position": "102", "planet": "industrex",
        "attacker": "p2", "defender": "p1",
    })


def test_evelyn_dodatkowa_kosc_sily_naziemnej(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].planet_units = {
        "industrex": {"p1": {"infantry": 2}, "p2": {"infantry": 1}}
    }
    _ground_round(state)
    after = _accept(state, "p1", "Evelyn", {"unit": "p1|infantry"})
    assert leaders.state_of(after, registry, "p1", "solagent") == leaders.EXHAUSTED
    point = rules_hooks.POINT_COMBAT_BONUS_DICE
    ctx = {"kind": "ground", "base_type": "infantry"}
    assert rules_hooks.modify(point, after, "p1", 0, ctx) == 1
    assert rules_hooks.modify(point, after, "p1", 0, {**ctx, "kind": "space"}) == 0


def test_evelyn_nie_w_walce_kosmicznej() -> None:
    state = _state()
    state.systems["102"].space_units = {"p1": {"cruiser": 1}, "p2": {"cruiser": 1}}
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START, ctx={
        "kind": "space", "round": 1, "position": "102", "planet": "",
        "attacker": "p2", "defender": "p1",
    })
    assert not any("Evelyn" in label for label in _labels(state, "p1"))


# ------------------------------------------------------------------------- Claire Gibson


def test_claire_gibson_piechota_na_bronionej_planecie(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"solcommander": "unlocked"}
    state.systems["102"].planet_units = {"industrex": {"p1": {"infantry": 1}}}
    ctx = {"kind": "ground", "position": "102", "planet": "industrex",
           "attacker": "p2", "defender": "p1"}
    triggers.fire(state, GameEvent.COMBAT, Moment.START, subject="p2", ctx=ctx)
    after = _accept(state, "p1", "Claire Gibson")
    assert _infantry(after, "p1") == 2


def test_claire_gibson_nie_przy_ataku(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"solcommander": "unlocked"}
    ctx = {"kind": "ground", "position": "102", "planet": "industrex",
           "attacker": "p1", "defender": "p2"}
    triggers.fire(state, GameEvent.COMBAT, Moment.START, subject="p1", ctx=ctx)
    assert not any("Claire" in label for label in _labels(state, "p1"))


def test_claire_gibson_odblokowanie_12_zasobow(registry: StaticDataRegistry) -> None:
    state = _state()
    assert sol._commander_unlocked(state, registry, "p1") is False
    owners = {p: "p1" for p in ("industrex", "meharxull", "ang", "meer")}
    big = [p.id for p in registry.planets.values() if (p.resources or 0) >= 4][:3]
    owners.update({p: "p1" for p in big})
    state.systems["102"].planet_owners = owners
    assert sol._commander_unlocked(state, registry, "p1") is True


# ---------------------------------------------------------- Jace X — Helio Command Array


def test_helio_command_array_zdejmuje_wszystkie_zetony(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["105"] = SystemState(position="105", system_id="19", command_tokens=["p1"])
    state.systems["102"].command_tokens = ["p1", "p2"]
    state.players["p1"].leader_states = {"solhero": "unlocked"}
    reinforcements = state.players["p1"].cc_reinf
    after, _ = faction_components.play(state, registry, "p1", "leader", "solhero")
    assert after.systems["102"].command_tokens == ["p2"]
    assert after.systems["105"].command_tokens == []
    assert after.players["p1"].cc_reinf == reinforcements + 2
    assert leaders.state_of(after, registry, "p1", "solhero") == leaders.PURGED


# --------------------------------------------------------------------- Military Support


def test_military_support_na_poczatku_tury_sola(registry: StaticDataRegistry) -> None:
    state = _state()
    state.active_player_id = "p2"
    state.turn_end_window = TurnEndWindow(ended_player="p2", next_player="p1")
    state.systems["102"].planet_owners = {"industrex": "p2"}
    state.players["p2"].private.promissory_notes = ["ms"]
    strategic = state.players["p1"].strategic_cc
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows["ms"]["playable"] is True, rows["ms"]["reason"]
    after, implemented = promissory_play.play(
        state, registry, "p2", "ms", {"planet": "102|industrex"}
    )
    assert implemented is True
    assert after.players["p1"].strategic_cc == strategic - 1
    assert _infantry(after, "p2") == 2
    assert "ms" in after.players["p1"].private.promissory_notes


def test_military_support_poza_poczatkiem_tury(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].private.promissory_notes = ["ms"]
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows["ms"]["playable"] is False


# --------------------------------------------------------------- Bellum Gloriosum (BT)


def test_bellum_gloriosum_ladunek_poza_limitem(registry: StaticDataRegistry) -> None:
    state = _state()
    orders = [ProductionOrder("carrier", 1), ProductionOrder("infantry", 8)]
    assert production.free_cargo_units(state, registry, "p1", orders) == 0
    state.players["p1"].breakthrough_unlocked = True
    capacity = registry.units["sol_carrier"].capacity_value
    assert production.free_cargo_units(state, registry, "p1", orders) == min(capacity or 0, 8)
    assert production.free_cargo_units(
        state, registry, "p1", [ProductionOrder("infantry", 2)]
    ) == 0
