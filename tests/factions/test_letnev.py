"""Barony of Letnev — komplet komponentów frakcji (RULES.md 62.2), konwencja par."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.api.demo_map import build_demo_grid
from src.core import (
    battle,
    board_graph,
    damage,
    faction_components,
    fleet_pool,
    leaders,
    promissory_play,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    InvasionState,
    Phase,
    PlayerState,
    SystemState,
    TimingWindow,
    WindowType,
)
from src.core.hooks.factions import letnev
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
    """p1 = Letnev (aktywny), p2 = Sol; walki w systemie 102 (Industrex)."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="102",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="letnev", trade_goods=3),
            "p2": PlayerState(player_id="p2", color="blue", faction="sol"),
        },
        systems={"102": SystemState(position="102", system_id="115")},
        rng_seed=7,
    )


def _round_start(state: GameState, kind: str = "space") -> None:
    ctx = {
        "kind": kind, "round": 1, "position": "102",
        "planet": "industrex" if kind == "ground" else "", "attacker": "p1", "defender": "p2",
    }
    triggers.fire(state, GameEvent.COMBAT_ROUND, Moment.START, ctx=ctx)


def _offers(state: GameState, player: str) -> list[str]:
    return [o.label for o in state.pending_offers if o.player_id == player]


def _accept(
    state: GameState, player: str, label_part: str, params: dict[str, Any] | None = None
) -> GameState:
    offer = next(
        o for o in state.pending_offers if o.player_id == player and label_part in o.label
    )
    return triggers.accept_offer(state, player, offer.id, params)


def _rolled(state: GameState) -> ActiveCombat:
    """Walka kosmiczna po rzucie: obie strony mają wpisy rzutów, okno przypisania otwarte."""
    combat = ActiveCombat(
        kind="space", position="102", attacker="p1", defender="p2", step=CombatStep.ASSIGN,
    )
    combat.rolls = {
        "p1": [{"baseType": "cruiser", "name": "Cruiser", "dice": [1, 2], "hitsOn": 7,
                "modifier": 0, "hits": 0}],
        "p2": [{"baseType": "cruiser", "name": "Cruiser", "dice": [9], "hitsOn": 7,
                "modifier": 0, "hits": 1}],
    }
    combat.pending_hits = {"p1": 1, "p2": 0}
    combat.log = [{"round": 1, "phase": "COMBAT", "rolls": combat.rolls,
                   "hits": {"p1": 0, "p2": 1}, "losses": {}, "sustained": {}}]
    state.active_combat = combat
    state.pending_window = TimingWindow(
        window_type=WindowType.COMBAT_ASSIGN_HITS, queue=["p1"]
    )
    return combat


# ------------------------------------------------------------------------------- kompletność


def test_frakcja_kompletna(registry: StaticDataRegistry) -> None:
    assert missing_components(registry, "letnev") == []


# ------------------------------------------------------------------------------------- Armada


def test_armada_dwa_statki_wiecej(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units["p1"] = {"cruiser": 5}
    state.systems["102"].space_units["p2"] = {"cruiser": 5}
    assert fleet_pool.fleet_report(state, "102", "p1", registry).pool == 5  # 3 + 2
    assert fleet_pool.fleet_report(state, "102", "p2", registry).pool == 3


def test_hero_bez_limitu_floty_do_konca_rundy(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].leader_states = {"letnevhero": "unlocked"}
    after, implemented = faction_components.play(state, registry, "p1", "leader", "letnevhero")
    assert implemented is True
    assert leaders.state_of(after, registry, "p1", "letnevhero") == leaders.PURGED
    after.systems["102"].space_units["p1"] = {"dreadnought": 12}
    assert fleet_pool.fleet_report(after, "102", "p1", registry).excess == 0


# ----------------------------------------------------------------- Munitions + War Funding


def test_munitions_placi_na_poczatku_rundy_i_przerzuca(registry: StaticDataRegistry) -> None:
    state = _state()
    _round_start(state)
    assert any("Munitions" in label for label in _offers(state, "p1"))
    paid = _accept(state, "p1", "Munitions")
    assert paid.players["p1"].trade_goods == 1
    paid.pending_offers = []
    paid.pending_window = None
    _rolled(paid)
    rows = {r["component_id"]: r for r in faction_components.playability(paid, registry, "p1")}
    assert rows["munitions"]["playable"] is True, rows["munitions"]["reason"]
    after, _ = faction_components.play(
        paid, registry, "p1", "ability", "munitions", {"dice": ["0:0", "0:1"]}
    )
    assert after.active_combat is not None
    assert len(after.active_combat.rolls["p1"][0]["dice"]) == 2
    with pytest.raises(ValueError):  # raz na rundę
        faction_components.play(after, registry, "p1", "ability", "munitions", {"dice": ["0:0"]})


def test_munitions_bez_tg_brak_oferty(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].trade_goods = 1
    _round_start(state)
    assert not any("Munitions" in label for label in _offers(state, "p1"))


def test_war_funding_przerzuca_kosci_przeciwnika(registry: StaticDataRegistry) -> None:
    state = _state()
    _rolled(state)
    state.players["p2"].private.promissory_notes = ["war_funding"]
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows["war_funding"]["playable"] is True, rows["war_funding"]["reason"]
    after, implemented = promissory_play.play(
        state, registry, "p2", "war_funding", {"opponent": "yes", "dice": []}
    )
    assert implemented is True
    assert "war_funding" in after.players["p1"].private.promissory_notes


def test_war_funding_poza_oknem_rzutow(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].private.promissory_notes = ["war_funding"]
    rows = {r["note_id"]: r for r in promissory_play.playability(state, registry, "p2")}
    assert rows["war_funding"]["playable"] is False


def test_przerzut_centralny_dolacza_przeciwnika_do_kolejki(registry: StaticDataRegistry) -> None:
    state = _state()
    combat = _rolled(state)
    combat.rolls["p1"][0]["dice"] = [1]
    combat.rolls["p1"][0]["hitsOn"] = 1  # każdy wynik trafia
    battle.reroll_combat_dice(state, "p1", {(0, 0)}, "test", "Test")
    assert combat.pending_hits["p2"] == 1
    assert state.pending_window is not None and "p2" in state.pending_window.queue


# ------------------------------------------------------------------------------ L4 i NES


def test_l4_pomija_space_cannon_defense(registry: StaticDataRegistry) -> None:
    from src.core import invasion

    state = _state()
    state.invasion = InvasionState(position="102", attacker="p1")
    state.invasion.committed = {"industrex": {"infantry": 1}}
    state.systems["102"].planet_units["industrex"] = {
        "p1": {"infantry": 1}, "p2": {"pds": 1},
    }
    assert invasion.defense_planets(state, registry) == ["industrex"]
    state.players["p1"].technologies = ["l4"]
    assert invasion.defense_planets(state, registry) == []


def test_non_euclidean_shielding_anuluje_dwa(registry: StaticDataRegistry) -> None:
    state = _state()
    combat = _rolled(state)
    combat.pending_hits = {"p1": 3, "p2": 0}
    state.systems["102"].space_units["p1"] = {"dreadnought": 1, "cruiser": 1}
    grid = build_demo_grid(registry)
    assert battle.required_hits(state, grid, registry, "p1") == 3  # 2 statki + 1 Sustain
    state.players["p1"].technologies = ["nes"]
    assert battle.sustain_cancels(state, "p1") == 2
    assert battle.required_hits(state, grid, registry, "p1") == 3
    after = battle.assign_combat_hits(
        state, grid, registry, "p1", sustain={"dreadnought": 1}, destroy={"cruiser": 1},
        destroy_damaged={},
    )
    assert after.systems["102"].space_units["p1"] == {"dreadnought": 1}
    with pytest.raises(ValueError):
        battle.assign_combat_hits(
            state, grid, registry, "p1", sustain={"dreadnought": 1}, destroy={},
            destroy_damaged={},
        )


# ---------------------------------------------------------------- flagowiec Arc Secundus


def test_arc_secundus_naprawa_na_starcie_rundy(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units["p1"] = {"flagship": 1}
    damage.set_damaged(state.systems["102"], "space", "p1", "flagship", 1)
    _round_start(state)
    assert damage.damaged_count(state.systems["102"], "space", "p1", "flagship") == 0


def test_arc_secundus_zdejmuje_tarcze(registry: StaticDataRegistry) -> None:
    from src.core import invasion

    state = _state()
    state.invasion = InvasionState(position="102", attacker="p1")
    state.systems["102"].planet_units["industrex"] = {"p2": {"pds": 1}}
    assert invasion._planet_shielded(state, registry, "industrex") is True
    state.systems["102"].space_units["p1"] = {"flagship": 1}
    assert invasion._planet_shielded(state, registry, "industrex") is False


# --------------------------------------------------------------------- mech Dunlain Reaper


def test_dunlain_reaper_zamienia_piechote(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].planet_units["industrex"] = {"p1": {"infantry": 2}, "p2": {"mech": 1}}
    _round_start(state, "ground")
    assert any("Dunlain" in label for label in _offers(state, "p1"))
    after = _accept(state, "p1", "Dunlain", {"trade_goods": 2})
    assert after.systems["102"].planet_units["industrex"]["p1"] == {"infantry": 1, "mech": 1}
    assert after.players["p1"].trade_goods == 1


def test_dunlain_reaper_bez_srodkow_brak_oferty(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].trade_goods = 1
    state.systems["102"].planet_units["industrex"] = {"p1": {"infantry": 2}, "p2": {"mech": 1}}
    _round_start(state, "ground")
    assert not any("Dunlain" in label for label in _offers(state, "p1"))


# --------------------------------------------------------------------------- agent Unlenn


def test_agent_dodatkowa_kosc_dla_wybranego_statku(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units["p1"] = {"cruiser": 2}
    state.systems["102"].space_units["p2"] = {"destroyer": 1}
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1", defender="p2")
    _round_start(state)
    after = _accept(state, "p1", "Unlenn", {"ship": "p1|cruiser"})
    assert leaders.state_of(after, registry, "p1", "letnevagent") == leaders.EXHAUSTED
    grid = build_demo_grid(registry)
    units = {u.base_type: u for u in battle.side_units(after, grid, registry, "p1")}
    assert units["cruiser"].total_dice == 3  # 2 krążowniki + 1 kość agenta
    plain = {u.base_type: u for u in battle.side_units(state, grid, registry, "p1")}
    assert plain["cruiser"].total_dice == 2


# ---------------------------------------------------------------- commander Rear Admiral Farran


def test_commander_odblokowanie_5_statkow(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["102"].space_units["p1"] = {"cruiser": 4, "fighter": 3}
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", "letnevcommander") == leaders.LOCKED
    state.systems["102"].space_units["p1"]["destroyer"] = 1
    leaders.refresh_unlocks(state, registry)
    assert leaders.state_of(state, registry, "p1", "letnevcommander") == leaders.UNLOCKED


def test_commander_tg_po_sustain(registry: StaticDataRegistry) -> None:
    state = _state()
    ctx = {"player": "p1", "base_type": "dreadnought", "count": 2}
    triggers.fire(state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject="p1", ctx=ctx)
    assert not _offers(state, "p1")  # zablokowany commander
    state.players["p1"].leader_states = {"letnevcommander": "unlocked"}
    triggers.fire(state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject="p1", ctx=ctx)
    after = _accept(state, "p1", "Farran")
    assert after.players["p1"].trade_goods == 5


# ------------------------------------------------------------------ Gravleash Maneuvers


def test_gravleash_premia_dla_jednego_statku(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].breakthrough_unlocked = True
    state.systems["102"].space_units["p1"] = {"cruiser": 2, "destroyer": 1}
    state.systems["102"].space_units["p2"] = {"destroyer": 1}
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1", defender="p2")
    _round_start(state)
    after = _accept(state, "p1", "Gravleash", {"ship": "cruiser"})
    grid = build_demo_grid(registry)
    units = {u.base_type: u for u in battle.side_units(after, grid, registry, "p1")}
    assert units["cruiser"].single_bonus == 2  # 2 typy statków w walce
    assert units["destroyer"].single_bonus == 0
    assert letnev.GRAVLEASH  # klucz efektu udokumentowany w module


def test_gravleash_wyrownuje_ruch_do_najszybszego(registry: StaticDataRegistry) -> None:
    from src.core import movement

    grid = build_demo_grid(registry)
    state = _state()
    together = ["dreadnought", "cruiser"]

    def value(s: GameState, companions: list[str] | None) -> int | None:
        return movement._effective_move_value(
            s, grid, registry, "000", "dreadnought", "p1",
            boost=False, tempesta=False, companions=companions,
        )

    assert value(state, together) == 1  # bez przełomu: dreadnought ma ruch 1
    state.players["p1"].breakthrough_unlocked = True
    assert value(state, together) == 2  # = krążownik ruszający z tego samego systemu
    assert value(state, None) == 1  # sam: bez zmian
    fighter = movement._effective_move_value(
        state, grid, registry, "000", "fighter", "p1",
        boost=False, tempesta=False, companions=together,
    )
    assert fighter is None  # myśliwce nie dostają wyrównania


def test_gravleash_przenosi_premie_gravity_drive(registry: StaticDataRegistry) -> None:
    from src.core import movement

    grid = build_demo_grid(registry)
    state = _state()
    state.players["p1"].technologies = ["gd"]
    state.players["p1"].breakthrough_unlocked = True
    together = ["dreadnought", "cruiser"]
    plain = movement._effective_move_value(
        state, grid, registry, "000", "dreadnought", "p1",
        boost=False, tempesta=False, companions=together,
    )
    boosted = movement._effective_move_value(
        state, grid, registry, "000", "dreadnought", "p1",
        boost=True, tempesta=False, companions=together,
    )
    assert plain == 2 and boosted == 3  # wyrównanie do krążownika z premią Gravity Drive


# ------------------------------------------------------------------ okna decyzji (UI ofert)


def test_oferta_agenta_ma_tekst_rodzaj_i_kafelki_jednostek(registry: StaticDataRegistry) -> None:
    from src.core import offers

    state = _state()
    state.systems["102"].space_units["p1"] = {"cruiser": 2}
    state.systems["102"].space_units["p2"] = {"destroyer": 1}
    state.active_combat = ActiveCombat(kind="space", position="102", attacker="p1", defender="p2")
    _round_start(state)
    view = next(v for v in offers.offers_view(state, registry, "p1") if "Unlenn" in v["label"])
    assert view["kind"] == "Agent"
    assert "additional die" in view["text"]
    options = view["inputs"][0]["options"]
    assert options[0]["meta"]["player"] == "p1"  # własne statki pierwsze
    assert {o["meta"]["unit"] for o in options} == {"cruiser", "destroyer"}
    assert all("(p1)" not in o["label"] for o in options)  # bez surowych id graczy


def test_dunlain_reaper_platnosc_jednym_widzetem(registry: StaticDataRegistry) -> None:
    from src.core import offers

    state = _state()
    state.systems["102"].planet_units["industrex"] = {"p1": {"infantry": 2}, "p2": {"mech": 1}}
    _round_start(state, "ground")
    view = next(v for v in offers.offers_view(state, registry, "p1") if "Dunlain" in v["label"])
    planets = next(i for i in view["inputs"] if i["key"] == "planets")
    assert planets["payment"] == {"cost": 2, "valueKind": "resources", "tradeGoods": "trade_goods"}
    assert view["kind"] == "Unit ability"


def test_munitions_widoczne_w_oknie_walki_po_rzucie(registry: StaticDataRegistry) -> None:
    state = _state()
    assert faction_components.combat_dice_uses(state, registry) == []
    _round_start(state)
    paid = _accept(state, "p1", "Munitions")
    paid.pending_offers = []
    paid.pending_window = None
    _rolled(paid)
    uses = faction_components.combat_dice_uses(paid, registry)
    assert [(u["player"], u["component"]) for u in uses] == [("p1", "munitions")]
    assert uses[0]["min"] == 1 and uses[0]["max"] == 2
