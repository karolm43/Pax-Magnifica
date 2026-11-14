"""Emirates of Hacan — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.6)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _to_vote(flow: Flow) -> None:
    """Status → agenda (żeton Custodians zdjęty) → ujawnienie → kolej Hacan na głos."""
    flow.post("/god-mode/patch", {"custodians_removed": True})
    flow.to_status()
    flow.finish_status()
    state = flow.state()
    assert state["phase"] == "AGENDA", state["phase"]
    flow.post("/agenda/reveal", {"player_id": state["speaker_id"]})
    for _ in range(6):
        agenda = flow.state()["agenda"]
        speaker = {"player_id": flow.state()["speaker_id"]}
        if agenda["step"] == "VOTE" and agenda["unresolvable"]:
            flow.post("/agenda/discard", speaker)  # brak kandydatów: mówca odrzuca agendę
            flow.post("/agenda/reveal", speaker)
            continue
        if agenda["step"] == "VOTE":
            break
        flow.post("/agenda/continue", speaker, ok=False)
    # Rywal głosuje pierwszy, jeśli to jego kolej (wstrzymuje się); potem Hacan.
    flow.post("/agenda/abstain", {"player_id": flow.other}, ok=False)


def test_transakcja_z_nie_sasiadem_i_karta_akcji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")

    def hands(s: Json) -> None:
        s["players"][flow.me]["private"]["action_cards"] = ["sabo1"]
        s["players"][flow.me]["trade_goods"] = 2

    flow.edit(hands)
    flow.post("/transactions/table/open", {"player_id": flow.me, "partner_id": flow.other})
    view = flow.client.get("/transactions/state", params={"player": flow.me}).json()
    assert view["tables"][0]["actionCards"]  # Arbiters
    flow.transact(give={"action_cards": ["sabo1"], "trade_goods": 1})
    assert "sabo1" in flow.state()["players"][flow.other]["private"]["action_cards"]


@covers("leaders:hacanagent")
def test_carth_of_golden_sands_w_fazie_akcji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")
    assert f"{flow.me}:hacanagent" in flow.available()
    # Okno trwa całą fazę akcji - UI pokazuje znacznik „gotowe”, nie wyskakującą kartę.
    rows = flow.client.get("/faction-component/available-now").json()["components"]
    carth = next(r for r in rows if r["component_id"] == "hacanagent")
    assert carth["standing"] is True
    flow.use("leader", "hacanagent", {"target": "self"})
    assert flow.state()["players"][flow.me]["commodities"] == 2


@covers("leaders:hacancommander")
def test_gila_przy_glosowaniu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")
    flow.player(lambda p: p.update(trade_goods=10))
    _to_vote(flow)
    assert f"{flow.me}:hacancommander" in flow.available()
    flow.use("leader", "hacancommander", {"trade_goods": 2})
    assert flow.state()["players"][flow.me]["trade_goods"] == 8
    # F_hacan: wstrzymanie się = brak dodatkowych głosów, wydane TG wracają.
    flow.post("/agenda/abstain", {"player_id": flow.me})
    state = flow.state()
    assert state["players"][flow.me]["trade_goods"] == 10
    assert not [e for e in state["active_effects"] if e["key"].startswith("leaders:hacan")]


@covers("leaders:hacanhero")
def test_harrugh_gefhara_przy_produkcji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")
    flow.player(lambda p: p["leader_states"].update(hacanhero="unlocked"))
    flow.activate(flow.home)
    flow.to_step("PRODUCTION")
    assert f"{flow.me}:hacanhero" in flow.available()
    flow.use("leader", "hacanhero")
    assert flow.state()["players"][flow.me]["leader_states"].get("hacanhero") == "purged"


@covers("promissory_notes:convoys")
def test_trade_convoys_akcja_i_zwrot(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")
    note = flow.give_note("convoys", flow.other)
    flow.other_turn()
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note)
    assert note in flow.state()["players"][flow.other]["promissory_notes_in_play"]
    flow.end_turn(flow.other)
    flow.pass_and_end(flow.me)  # znów tura rywala
    # Aktywacja systemu z jednostkami Hacan zwraca notkę.
    flow.post("/tactical/activate", {"position": flow.home})
    state = flow.state()
    assert note not in state["players"][flow.other]["promissory_notes_in_play"]


@covers("technologies:qdn")
def test_quantum_datahub_node_na_koniec_fazy_strategii(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")

    def ready(p: Json) -> None:
        p["technologies"].append("qdn")
        p.update(trade_goods=3, strategic_cc=2)

    flow.player(ready)
    flow.edit(lambda s: None, phase="STRATEGY")
    flow.post("/phase/next", {"player_id": flow.state()["speaker_id"]}, ok=False)
    assert flow.has_offer("Quantum Datahub")


@covers("units:hacan_flagship")
def test_wrath_of_kenara_po_rzucie(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")
    flow.player(lambda p: p.update(trade_goods=3))
    flow.space_combat({"flagship": 1}, {"destroyer": 2})
    flow.fight(stop=lambda: flow.has_offer("Wrath of Kenara"))
    assert flow.has_offer("Wrath of Kenara")
    offer = flow.offer("Wrath of Kenara")
    die = offer["inputs"][0]["options"][0]["value"]
    flow.accept("Wrath of Kenara", {"dice": [die]})
    assert flow.state()["players"][flow.me]["trade_goods"] == 2
