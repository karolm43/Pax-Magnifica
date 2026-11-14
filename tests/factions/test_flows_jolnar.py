"""Universities of Jol-Nar — scenariusze przez prawdziwe API (dostępność, RULES.md 62.3)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers

TECHNOLOGY = 7


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _technology_primary(flow: Flow, tech: str) -> None:
    """Jol-Nar zagrywa kartę Technology i bada ``tech`` za darmo (krok 1 primary)."""
    def card(s: Json) -> None:
        s["players"][flow.me]["strategy_cards"] = [TECHNOLOGY]
        s["players"][flow.other]["strategy_cards"] = [1]

    flow.edit(card)
    flow.post("/strategy/play", {"player_id": flow.me, "initiative": TECHNOLOGY})
    flow.post("/strategy/primary-step", {"player_id": flow.me, "payload": {"tech": tech}})


@covers("promissory_notes:ra")
def test_research_agreement_po_badaniu_jolnar(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "jolnar")
    note = flow.give_note("ra", flow.other)
    _technology_primary(flow, "pa")
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note, {"technology": "pa"})
    assert "pa" in flow.state()["players"][flow.other]["technologies"]


@covers("leaders:jolnaragent")
def test_sucaban_sam_wyskakuje_przy_platnym_badaniu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "jolnar")
    _technology_primary(flow, "pa")
    assert flow.state()["pending_strategy"]["step"] == "research_paid"
    assert f"{flow.me}:jolnaragent" in flow.available()
    flow.use("leader", "jolnaragent")
    assert flow.has_offer("Sucaban")


@covers("leaders:jolnaragent")
def test_sucaban_obniza_koszt_focused_research(registry: StaticDataRegistry) -> None:
    """Focused Research z 2 TG: okno badania czeka, Sucaban zdejmuje piechotę przed zapłatą."""
    flow = Flow(registry, "jolnar")
    home = flow.planets(flow.home)[0]

    def hand(s: Json) -> None:
        s["players"][flow.me]["trade_goods"] = 2
        s["players"][flow.me]["private"]["action_cards"] = ["f_researched"]

    flow.edit(hand)
    flow.ground(flow.home, home, flow.me, {"infantry": 2})
    rows = flow.client.get("/action-card/playable", params={"player_id": flow.me}).json()
    row = next(r for r in rows["cards"] if r["card_id"] == "f_researched")
    assert row["playable"], row["reason"]
    flow.post("/action-card/play", {"player_id": flow.me, "card_id": "f_researched", "params": {}})
    research = flow.offer("Focused Research")
    assert research["inputs"][0]["kind"] == "research"
    assert f"{flow.me}:jolnaragent" in flow.available()
    flow.use("leader", "jolnaragent")
    removal = {i["key"]: 0 for i in flow.offer("Sucaban")["inputs"] if i["kind"] == "number"}
    removal[f"inf:{flow.home}:{home}"] = 2
    flow.accept("Sucaban", removal)
    assert flow.offer("Focused Research")["inputs"][0]["research"]["cost"] == 2
    tree = flow.offer("Focused Research")["inputs"][0]["research"]["tree"]
    tech = next(r["id"] for r in tree if r["status"] == "available")
    payload = {"tech": tech, "skips": [], "planets": [], "trade_goods": 2}
    flow.accept("Focused Research", {"research": payload})
    player = flow.state()["players"][flow.me]
    assert tech in player["technologies"] and player["trade_goods"] == 0


@covers("leaders:jolnarcommander")
def test_agnlan_oln_przerzut_afb(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "jolnar")
    flow.player(lambda p: p["leader_states"].update(jolnarcommander="unlocked"))
    flow.space_combat({"destroyer": 2}, {"carrier": 1, "fighter": 3})
    flow.fight(stop=lambda: flow.has_offer("Agnlan"))
    assert flow.has_offer("Agnlan")
    flow.accept("Agnlan", {"dice": ["0:0"]})
    assert flow.battle()["step"] != "TRIGGERS"  # walka poszła dalej po decyzji


@covers("leaders:jolnarhero")
def test_genetic_memory_jako_akcja(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "jolnar")
    flow.player(lambda p: p["leader_states"].update(jolnarhero="unlocked"))
    assert flow.playable()["jolnarhero"]["playable"], flow.playable()["jolnarhero"]["reason"]


@covers("technologies:scc")
def test_spatial_conduit_po_aktywacji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "jolnar")
    flow.player(lambda p: p["technologies"].append("scc"))
    target, _ = flow.plain_pair()
    flow.space(target, flow.me, {"cruiser": 1})
    flow.activate(target)
    assert flow.has_offer("Spatial Conduit")
