"""The Naalu Collective — scenariusze przez prawdziwe API (dostępność, RULES.md 62.16)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(flow: Flow) -> Json:
    return flow.state()


def _other_turn(flow: Flow) -> None:
    """Tura rywala (God-Mode): to on aktywuje systemy i rusza statki."""
    flow.edit(active=flow.other)


def _first_option(offer: Json, key: str) -> str:
    field = next(i for i in offer["inputs"] if i["key"] == key)
    return str(field["options"][0]["value"])


@covers("abilities:foresight")
def test_foresight_po_wlocie_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naalu")
    arena, source = flow.plain_pair()
    flow.space(arena, flow.me, {"cruiser": 1, "fighter": 2})
    flow.space(source, flow.other, {"destroyer": 1})
    _other_turn(flow)
    flow.activate(arena)
    flow.decline_all()  # Z'eu przy aktywacji - nie tym razem
    faction = _state(flow)["players"][flow.other]["faction"]
    flow.post("/tactical/move", {
        "faction": faction, "fromPosition": source,
        "ships": [{"baseType": "destroyer", "count": 1}], "cargo": [], "route": [source, arena],
    })
    offer = flow.offer("Foresight")
    destination = _first_option(offer, "destination")
    flow.accept("Foresight", {"destination": destination})
    systems = _state(flow)["systems"]
    assert systems[destination]["space_units"][flow.me] == {"cruiser": 1, "fighter": 2}
    assert flow.me in systems[destination]["command_tokens"]
    assert not any(systems[arena]["space_units"].get(flow.me, {}).values())


@covers("leaders:naaluagent-te")
def test_zeu_po_aktywacji_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naalu")
    arena, _ = flow.plain_pair()
    _other_turn(flow)
    reinf = _state(flow)["players"][flow.other]["cc_reinf"]
    flow.activate(arena)
    flow.accept("Z'eu")
    state = _state(flow)
    assert flow.other not in state["systems"][arena]["command_tokens"]
    assert state["players"][flow.other]["cc_reinf"] == reinf + 1
    assert state["players"][flow.me]["leader_states"]["naaluagent-te"] == "exhausted"


@covers("promissory_notes:gift")
def test_gift_of_prescience_na_koncu_fazy_strategii(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naalu")
    note = flow.give_note("gift", flow.other)
    last = max(_state(flow)["players"][flow.other]["strategy_cards"])

    def unpicked(s: Json) -> None:
        s["players"][flow.other]["strategy_cards"].remove(last)

    # Faza strategii bez ostatniej karty rywala; jego wybór domyka fazę (okno „koniec fazy”).
    flow.edit(unpicked, phase="STRATEGY", active=flow.other)
    flow.post("/strategy/pick", {"player_id": flow.other, "initiative": last})
    pause = _state(flow)["reaction_pause"]
    assert pause is not None and flow.other in pause["eligible"]  # „Next phase” czeka
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note)
    players = _state(flow)["players"]
    assert "gift" in players[flow.other]["promissory_notes_in_play"]


@covers("units:naalu_mech_te")
def test_iconoclast_gdy_rywal_kuje_relikt(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naalu")
    flow.player(lambda p: p.update(relic_fragments=["crf1", "crf2", "crf3"]), pid=flow.other)
    _other_turn(flow)
    flow.post("/relic/forge", {"player_id": flow.other, "fragments": ["crf1", "crf2", "crf3"]})
    offer = flow.offer("Iconoclast")
    assert offer["mandatory"]
    planet = _first_option(offer, "planet")
    flow.accept("Iconoclast", {"planet": planet})
    systems = _state(flow)["systems"]
    assert any(
        s["planet_units"].get(planet, {}).get(flow.me, {}).get("mech") == 1
        for s in systems.values()
    )


@covers("leaders:naaluhero")
def test_oracle_na_koncu_statusu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naalu")
    flow.player(lambda p: p["leader_states"].update(naaluhero="unlocked"))
    before = list(_state(flow)["players"][flow.other]["private"]["promissory_notes"])
    assert before
    flow.to_status()
    flow.finish_status()
    flow.accept("The Oracle")
    choice = flow.offer("give a promissory note", pid=flow.other)
    note = _first_option(choice, "note")
    flow.accept("give a promissory note", {"note": note}, pid=flow.other)
    players = _state(flow)["players"]
    assert players[flow.me]["leader_states"]["naaluhero"] == "purged"
    mine = players[flow.me]
    # Alliance i podobne notki „place immediately” lądują od razu w strefie (promissory_play).
    assert note in mine["private"]["promissory_notes"] + mine["promissory_notes_in_play"]
    assert len(players[flow.other]["private"]["promissory_notes"]) == len(before) - 1


@covers("breakthroughs:naalubt")
def test_mindsieve_w_oknie_secondary(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naalu")
    flow.player(lambda p: p.update(breakthrough_unlocked=True))
    flow.player(lambda p: p.update(strategy_cards=[5]), pid=flow.other)
    _other_turn(flow)
    flow.post("/strategy/play", {"player_id": flow.other, "initiative": 5})
    if _state(flow)["pending_strategy"] is not None:
        flow.post("/strategy/primary-step", {
            "player_id": flow.other, "payload": {"players": []},
        })
    assert f"{flow.me}:naalubt" in flow.available()
    note = _state(flow)["players"][flow.me]["private"]["promissory_notes"][0]
    flow.use("breakthrough", "naalubt", {"note": note})
    state = _state(flow)
    assert flow.me in state["pending_window"]["context"]["no_cost"].split(",")
    owner = state["players"][flow.other]
    assert note in owner["private"]["promissory_notes"] + owner["promissory_notes_in_play"]
