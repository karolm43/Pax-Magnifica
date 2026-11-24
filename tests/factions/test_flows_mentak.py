"""The Mentak Coalition — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.8)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _neighbors(flow: Flow) -> None:
    """Mentak i rywal są sąsiadami (statki w dwóch sąsiednich systemach)."""
    a, b = flow.plain_pair()
    flow.space(a, flow.me, {"cruiser": 1})
    flow.space(b, flow.other, {"cruiser": 1})


def _pillage_by_transaction(flow: Flow) -> None:
    """Mentak daje rywalowi 1 TG (rywal ma potem 4) - oferta Pillage przeciw partnerowi."""
    _neighbors(flow)
    flow.player(lambda p: p.update(trade_goods=3), flow.other)
    flow.player(lambda p: p.update(trade_goods=1))
    flow.transact(give={"trade_goods": 1})


@covers("abilities:ambush")
def test_ambush_na_starcie_walki(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mentak")
    flow.space_combat({"cruiser": 2}, {"destroyer": 2})
    offer = flow.offer("Ambush")
    ships = [o["value"] for o in offer["inputs"][0]["options"]]
    assert len(ships) == 2
    flow.accept("Ambush", {"ships": ships})
    view = flow.battle()
    assert view["log"][0]["phase"] == "AMBUSH"
    rolled = view["log"][0]["rolls"][view["attacker"]["faction"]]
    assert sum(len(r["dice"]) for r in rolled) == 2
    hits = view["log"][0]["hits"][view["attacker"]["faction"]]
    if hits:
        assert view["step"] == "ASSIGN" and view["assigning"] == view["defender"]["faction"]
    flow.fight()
    assert flow.battle().get("step") in (None, "DONE")


@covers("abilities:pillage", "leaders:mentakagent")
def test_pillage_po_transakcji_i_suffi_an(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mentak")
    _pillage_by_transaction(flow)
    assert flow.has_offer("Pillage")
    hands = {pid: len(flow.state()["players"][pid]["private"]["action_cards"])
             for pid in (flow.me, flow.other)}
    flow.accept("Pillage", {"take": "trade_good"})
    state = flow.state()
    assert state["players"][flow.other]["trade_goods"] == 3
    assert state["players"][flow.me]["trade_goods"] == 1
    assert flow.has_offer("Suffi An")
    flow.accept("Suffi An")
    state = flow.state()
    for pid in (flow.me, flow.other):
        assert len(state["players"][pid]["private"]["action_cards"]) == hands[pid] + 1
    assert state["players"][flow.me]["leader_states"]["mentakagent"] == "exhausted"


@covers("promissory_notes:pop")
def test_promise_of_protection_blokuje_pillage_i_wraca(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mentak")
    note = flow.give_note("pop", flow.other)
    flow.other_turn()
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note)
    assert note in flow.state()["players"][flow.other]["promissory_notes_in_play"]
    flow.end_turn(flow.other)
    flow.pass_and_end(flow.me)  # znów tura rywala
    flow.post("/tactical/activate", {"position": flow.home})  # system z jednostkami Mentaka
    state = flow.state()
    assert note not in state["players"][flow.other]["promissory_notes_in_play"]
    assert note in state["players"][flow.me]["private"]["promissory_notes"]


@covers("technologies:so")
def test_salvage_operations_po_wygranej(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mentak")

    def salvage(p: Json) -> None:
        p["technologies"].append("so")
        p.update(trade_goods=0)

    flow.player(salvage)
    flow.space_combat({"dreadnought": 3}, {"destroyer": 1})
    flow.fight()
    assert flow.battle()["step"] == "DONE"
    assert flow.state()["players"][flow.me]["trade_goods"] == 1  # +1 TG za walkę
    assert flow.has_offer("Salvage Operations")
    flow.accept("Salvage Operations")
    grant = flow.state()["production_grant"]
    assert grant["player_id"] == flow.me and "destroyer" in grant["allowed_types"]


@covers("leaders:mentakcommander")
def test_sula_mentarion_przeciwnik_oddaje_notke(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mentak")
    flow.player(lambda p: p["leader_states"].update(mentakcommander="unlocked"))
    hand = list(flow.state()["players"][flow.other]["private"]["promissory_notes"])
    assert len(hand) > 1
    flow.space_combat({"dreadnought": 3}, {"destroyer": 1})
    flow.fight()
    flow.accept("Mentarion")
    # Notkę wybiera przeciwnik (decyzja obowiązkowa).
    offer = flow.offer("give a promissory note", flow.other)
    assert offer["mandatory"]
    chosen = offer["inputs"][0]["options"][0]["value"]
    flow.accept("give a promissory note", {"note": chosen}, pid=flow.other)
    mine = flow.state()["players"][flow.me]
    # Alliance / SftT trafiają po otrzymaniu od razu do strefy gry (RULES.md 61.2).
    assert chosen in mine["private"]["promissory_notes"] + mine["promissory_notes_in_play"]
    assert chosen not in flow.state()["players"][flow.other]["private"]["promissory_notes"]


@covers("leaders:mentakhero")
def test_sleeper_cell_stawia_statki_za_zniszczone(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mentak")

    def hero(p: Json) -> None:
        p["leader_states"].update(mentakhero="unlocked")
        p.update(fleet_cc=8)  # pula mieści postawione statki

    flow.player(hero)
    position = flow.space_combat({"dreadnought": 3}, {"destroyer": 2})
    flow.accept("Sleeper Cell")
    assert flow.state()["players"][flow.me]["leader_states"]["mentakhero"] == "purged"
    flow.fight()
    state = flow.state()
    lost = state["active_combat"]["destroyed_all"]
    theirs = sum(1 for e in lost if e["player"] == flow.other and e["base_type"] == "destroyer")
    mine = sum(1 for e in lost if e["player"] == flow.me and e["base_type"] == "destroyer")
    assert theirs == 2
    placed = state["systems"][position]["space_units"][flow.me].get("destroyer", 0) + mine
    assert placed == theirs


def test_sleeper_cell_ponad_pule_floty_usuwa_od_razu(registry: StaticDataRegistry) -> None:
    """RULES.md 42.1 / F_mentak: nadwyżkę ponad pulę floty usuwa się NATYCHMIAST, w walce."""
    flow = Flow(registry, "mentak")
    flow.player(lambda p: p["leader_states"].update(mentakhero="unlocked"))
    flow.space_combat({"dreadnought": 3}, {"destroyer": 2})
    flow.accept("Sleeper Cell")

    def over_pool() -> bool:
        window = flow.state().get("pending_window") or {}
        return window.get("window_type") == "FLEET_POOL"

    flow.fight(stop=over_pool)
    assert over_pool()
    state = flow.state()
    assert state["active_combat"]["step"] != "DONE"  # okno w trakcie walki, nie po niej
    # Rzut kośćmi czeka, aż nadwyżka zniknie.
    if state["active_combat"]["step"] == "ROLL":
        resp = flow.post("/tactical/battle/roll", ok=False)
        assert resp.status_code == 422 and "fleet pool" in resp.text
    flow.fight()
    ships = flow.state()["systems"][state["active_combat"]["position"]]["space_units"][flow.me]
    assert sum(n for bt, n in ships.items() if bt != "fighter") <= 3
