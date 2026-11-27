"""The Mahact Gene-Sorcerers — scenarios through the real API (availability, RULES.md 62.23)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _me(flow: Flow, pid: str | None = None) -> Json:
    return flow.state()["players"][pid or flow.me]  # type: ignore[no-any-return]


def _to_vote(flow: Flow, deck: list[str]) -> None:
    """Status -> agenda with a fixed deck -> reveal -> the rival is about to vote."""
    flow.post("/god-mode/patch", {"custodians_removed": True})
    flow.to_status()
    flow.finish_status()
    service = flow.client.app.state.ctx.service  # type: ignore[attr-defined]
    state = service.current_state().clone()
    assert state.phase.value == "AGENDA"
    state.decks.agenda_deck = list(deck)
    state.decks.agenda_deck_seeded = True
    service.replace_state(state, label="test")
    flow.post("/agenda/reveal", {"player_id": state.speaker_id})
    if flow.state()["agenda"]["vote_order"][0] == flow.me:
        flow.post("/agenda/abstain", {"player_id": flow.me})


def test_edict_po_wygranej_walce(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mahact")
    reinf = _me(flow, flow.other)["cc_reinf"]
    flow.space_combat({"dreadnought": 3}, {"destroyer": 1})
    flow.fight()
    assert _me(flow)["foreign_fleet_tokens"] == [flow.other]
    assert _me(flow, flow.other)["cc_reinf"] == reinf - 1


@covers("technologies:gr")
def test_genetic_recombination_w_glosowaniu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mahact")
    flow.player(lambda p: p["technologies"].append("gr"))
    _to_vote(flow, ["regulations"])
    assert flow.state()["agenda"]["vote_order"][0] in (flow.other, flow.me)
    assert flow.playable()["gr"]["playable"]
    flow.use("technology", "gr", {"outcome": "against"})
    assert "gr" in _me(flow)["exhausted_technologies"]
    decision = flow.offer("Genetic Recombination", flow.other)
    assert decision["inputs"][0]["auto"] == "remove"
    flow.accept("Genetic Recombination", {"choice": "vote"}, pid=flow.other)
    planets = [p for p in _me(flow, flow.other)["controlled_planets"]]
    resp = flow.post("/agenda/vote", {"player_id": flow.other, "outcome": "for",
                                      "planets": planets}, ok=False)
    assert resp.status_code == 422 and "Genetic Recombination" in resp.text
    flow.post("/agenda/vote", {"player_id": flow.other, "outcome": "against", "planets": planets})
    assert flow.state()["agenda"]["votes"][flow.other]["outcome"] == "against"


@covers("leaders:mahacthero")
def test_benediction_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mahact")
    source, dest = flow.plain_pair()
    flow.clear_space(source)
    flow.clear_space(dest)
    flow.space(source, flow.me, {"cruiser": 2})
    flow.space(dest, flow.other, {"destroyer": 1})
    flow.player(lambda p: p["leader_states"].__setitem__("mahacthero", "unlocked"))
    assert flow.playable()["mahacthero"]["playable"]
    flow.use("leader", "mahacthero", {"source": source, "destination": dest})
    state = flow.state()
    combat = state["active_combat"]
    assert combat["position"] == dest and combat["no_retreat"]
    assert combat["attacker"] == flow.me
    assert state["players"][flow.me]["leader_states"]["mahacthero"] == "purged"
    flow.fight()
    assert flow.battle().get("step") in (None, "DONE")


@covers("promissory_notes:scepter")
def test_scepter_na_poczatku_fazy_strategii(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mahact")
    position, _ = flow.plain_pair()
    flow.space(position, flow.other, {"cruiser": 1})
    flow.give_note("scepter", flow.other)

    def to_strategy(s: Json) -> None:
        for p in s["players"].values():
            p["strategy_cards"] = []
            p["exhausted_strategy_cards"] = []

    flow.edit(to_strategy, phase="STRATEGY", active=flow.me)
    row = flow.notes_playable(flow.other)["scepter"]
    assert row["playable"], row
    flow.play_note(flow.other, "scepter", {"system": position})
    state = flow.state()
    assert flow.me in state["systems"][position]["command_tokens"]  # the Mahact places too
    assert "scepter" in state["players"][flow.me]["private"]["promissory_notes"]


@covers("units:mahact_mech")
def test_starlancer_konczy_ture_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mahact")
    position, _ = flow.plain_pair()
    flow.space(position, flow.me, {"mech": 1})
    flow.player(lambda p: p.__setitem__("foreign_fleet_tokens", [flow.other]))
    flow.edit(active=flow.other)
    flow.activate(position)
    flow.accept("Starlancer")
    state = flow.state()
    assert state["players"][flow.me]["foreign_fleet_tokens"] == []
    if flow.has_offer("Starlancer", flow.other):
        flow.accept("Starlancer", {"pool": "tactical"}, pid=flow.other)
    assert flow.state()["active_player_id"] == flow.me  # the rival's turn ended


@covers("breakthroughs:mahactbt")
def test_vaults_of_the_heir_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "mahact")
    flow.player(lambda p: p.__setitem__("breakthrough_unlocked", True))
    tech = sorted(_me(flow)["technologies"])[0]
    assert flow.playable()["mahactbt"]["playable"]
    flow.use("breakthrough", "mahactbt", {"technology": tech})
    me = _me(flow)
    assert tech not in me["technologies"] and tech in me["purged_technologies"]
    assert len(me["relics"]) == 1
