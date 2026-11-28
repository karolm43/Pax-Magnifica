"""Cooperative registration options (RULES.md 54.15 e): ``mutual``, ``target``, ``owner_picks``,
``ACTION:`` components and technologies on request, proxies (Ssruu) and shared keys (Deepgloom)."""

from __future__ import annotations

import pytest

from src.core import cooperative, rules_hooks
from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow

ALPHA = "creussalpha"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> None:
    rules_hooks.bind_registry(registry)


def _offer_inputs(flow: Flow, name: str) -> dict[str, list[str]]:
    offer = flow.offer(name)
    return {i["key"]: [o["value"] for o in i.get("options", [])] for i in offer["inputs"]}


# --- mutual + target: Carth of Golden Sands ------------------------------------------------------


def test_mutual_component_keeps_the_owner_prompt_and_is_requestable(
    registry: StaticDataRegistry,
) -> None:
    flow = Flow(registry, "hacan")
    assert f"{flow.me}:hacanagent" in flow.available()  # mutual: the Hacan is still prompted
    assert flow.has_boost("Carth of Golden Sands", flow.other)


def test_target_limits_the_deal_to_the_requester(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")
    flow.request_boost("Carth of Golden Sands", flow.other)
    assert _offer_inputs(flow, "Carth of Golden Sands")["target"] == [flow.other]
    offer = flow.offer("Carth of Golden Sands")
    resp = flow.post("/offers/accept", {
        "actor_id": flow.me, "offer_id": offer["id"], "params": {"target": "self"},
    }, ok=False)
    assert resp.status_code == 422  # the deal is for the requester, not the Hacan's own use
    flow.accept("Carth of Golden Sands", {"target": flow.other})
    state = flow.state()
    assert state["players"][flow.other]["commodities"] == state["players"][flow.other][
        "commodity_value"]
    assert state["players"][flow.me]["commodities"] == 0


# --- ACTION: technology on request: Wormhole Generator -------------------------------------------


def test_action_technology_deal_uses_the_owners_component_action(
    registry: StaticDataRegistry,
) -> None:
    flow = Flow(registry, "ghost")
    flow.player(lambda p: p["technologies"].append("wg"))
    target, _ = flow.plain_pair()
    assert flow.has_boost("Wormhole Generator", flow.other)
    flow.request_boost("Wormhole Generator", flow.other)
    offer = flow.offer("Wormhole Generator")
    assert offer["player_id"] == flow.me  # owner_picks: the Creuss decides the details
    flow.accept("Wormhole Generator", {"token": ALPHA, "position": target})
    state = flow.state()
    assert "wg" in state["players"][flow.me]["exhausted_technologies"]
    assert state["systems"][target]["faction_tokens"]["space"][ALPHA] == flow.me
    assert not flow.has_boost("Wormhole Generator", flow.other)  # exhausted / action used


def test_action_component_is_requestable_only_on_the_owners_turn(
    registry: StaticDataRegistry,
) -> None:
    flow = Flow(registry, "ghost")
    flow.player(lambda p: p["technologies"].append("wg"))
    flow.other_turn()
    assert not flow.has_boost("Wormhole Generator", flow.other)  # RULES.md 31.8


# --- Deepgloom Executable: one key, a hook AND a window use --------------------------------------


def test_shared_key_keeps_separate_specs(registry: StaticDataRegistry) -> None:
    key = "breakthroughs:yssarilbt"
    assert cooperative.is_pull(key)
    hook = cooperative.spec_for(key, component=False)
    lend = cooperative.spec_for(key, component=True)
    assert hook is not None and hook.mutual and hook.target is None
    assert lend is not None and lend.mutual and lend.target == "player"


def test_deepgloom_lend_on_request_goes_to_the_requester(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yssaril")
    flow.player(lambda p: p.update(breakthrough_unlocked=True))
    assert f"{flow.me}:yssarilbt" in flow.available()  # the Yssaril keeps its own window
    flow.request_boost("Deepgloom Executable", flow.other)
    assert _offer_inputs(flow, "Deepgloom Executable")["player"] == [flow.other]
    flow.accept("Deepgloom Executable", {"player": flow.other})
    effects = flow.state()["active_effects"]
    assert any(e["key"] == "breakthroughs:yssarilbt:stall_tactics" and e["owner"] == flow.other
               for e in effects)


# --- Ssruu: a copied pull agent is a boost of the Yssaril ----------------------------------------


def test_ssruu_copy_of_a_pull_agent_is_requestable(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yssaril", other="saar")
    target, _ = flow.plain_pair()
    flow.activate(target)
    flow.decline_all()
    flow.pass_reactions()
    flow.end_turn()
    flow.post("/tactical/activate", {"position": target})  # the Saar activates
    rows = [b for b in flow.boosts(flow.other) if b["name"] == "Captain Mendosa"]
    assert [r["owner"] for r in rows] == [flow.me]  # Ssruu's copy; the Saar's own is an offer
    assert flow.has_offer("Captain Mendosa", flow.other)


# --- Guard: every ticked component of an implemented faction is registered ----------------------

_TICKED = (  # docs/faction_components_checklist.md, [x] rows of implemented factions
    "leaders:arborecagent", "leaders:argentagent", "leaders:cabalagent",
    "abilities:aetherpassage", "leaders:empyreanagent", "breakthroughs:empyreanbt",
    "technologies:as", "units:empyrean_flagship", "units:empyrean_mech",
    "leaders:ghostagent", "technologies:wg", "units:ghost_mech",
    "leaders:hacanagent", "leaders:jolnaragent", "leaders:l1z1xagent", "leaders:letnevagent",
    "leaders:mentakagent", "leaders:muaatagent", "leaders:naaluagent-te", "breakthroughs:naalubt",
    "leaders:naazagent", "leaders:nekroagent", "leaders:nomadagentmercer",
    "leaders:nomadagentthundarian",
    "breakthroughs:nomadbt", "leaders:saaragent", "leaders:sardakkagent", "leaders:solagent",
    "leaders:titansagent", "breakthroughs:titansbt", "leaders:winnuagent", "leaders:winnuhero",
    "leaders:xxchaagent", "leaders:yinagent", "breakthroughs:yssarilbt",
)


@pytest.mark.parametrize("key", _TICKED)
def test_ticked_component_is_cooperative(key: str) -> None:
    assert cooperative.is_pull(key), key
