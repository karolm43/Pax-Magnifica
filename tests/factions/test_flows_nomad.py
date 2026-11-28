"""The Nomad — scenarios through the real API (availability, RULES.md 62.21)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _me(flow: Flow) -> Json:
    return flow.state()["players"][flow.me]  # type: ignore[no-any-return]


def _web_player(flow: Flow, pid: str) -> Json:
    data = flow.client.get("/api/public/game/g/web-data").json()
    rows = data.get("playerData") or data.get("players") or []
    faction = flow.state()["players"][pid]["faction"]
    return next(r for r in rows if r.get("faction") == faction)


def _facts(flow: Flow) -> list[Json]:
    entries = flow.client.get("/history/activity").json()["entries"]
    return [f for e in entries for f in e["activity"]["facts"]]


def _dynamis_core(flow: Flow) -> None:
    """The Nomad gains trade goods from the supply: Dynamis Core's ACTION (commodity value)."""
    flow.player(lambda p: p["relics"].append("dynamiscore"))
    flow.post("/relic/play", {"player_id": flow.me, "relic_id": "dynamiscore"})


@covers("leaders:nomadagentartuno")
def test_artuno_odklada_trade_goods_z_puli(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nomad")
    before = _me(flow)["trade_goods"]
    _dynamis_core(flow)
    gained = _me(flow)["trade_goods"] - before
    assert gained > 0
    flow.accept("Artuno")
    me = _me(flow)
    assert me["trade_goods"] == before
    assert me["leader_trade_goods"] == {"nomadagentartuno": gained}
    assert me["leader_states"]["nomadagentartuno"] == "exhausted"
    leader = next(r for r in _web_player(flow, flow.me)["leaders"]
                  if r["id"] == "nomadagentartuno")
    assert leader["tgCount"] == gained
    assert any(f["type"] == "leader_tg" and f["delta"] == gained for f in _facts(flow))


@covers("breakthroughs:nomadbt")
def test_thunders_paradox_na_poczatku_tury_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nomad")

    def setup(p: Json) -> None:
        p["breakthrough_unlocked"] = True
        p["leader_states"]["nomadagentartuno"] = "exhausted"
        p["leader_trade_goods"] = {"nomadagentartuno": 3}

    flow.player(setup)
    before = _me(flow)["trade_goods"]
    flow.other_turn()  # the rival's turn starts
    offer = flow.offer("Thunder's Paradox")
    assert "auto" not in offer["inputs"][0]
    flow.accept("Thunder's Paradox", {"exhaust": f"{flow.me}|nomadagentthundarian",
                                      "ready": f"{flow.me}|nomadagentartuno"})
    me = _me(flow)
    assert me["leader_states"]["nomadagentthundarian"] == "exhausted"
    assert me["leader_states"]["nomadagentartuno"] == "unlocked"
    assert me["trade_goods"] == before + 3  # Artuno pays out when it readies
    assert me["leader_trade_goods"] == {}


@covers("leaders:nomadagentmercer")
def test_mercer_na_koncu_tury(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nomad")
    away, _ = flow.plain_pair()
    flow.space(away, flow.me, {"carrier": 1, "infantry": 2})
    flow.activate(flow.home)
    flow.decline_all()
    flow.end_turn()
    flow.accept("Field Marshal Mercer")
    decision = flow.offer("Field Marshal Mercer")
    assert decision["mandatory"]
    forces = next(i for i in decision["inputs"] if i["key"] == "forces")
    picks = [o["value"] for o in forces["options"] if o["value"].startswith(f"{away}|space")][:2]
    planet = flow.planets(flow.home)[0]
    flow.accept("Field Marshal Mercer", {"forces": picks, "planet_1": planet,
                                         "planet_2": planet})
    state = flow.state()
    assert state["systems"][away]["space_units"][flow.me].get("infantry", 0) == 0
    landed = state["systems"][flow.home]["planet_units"][planet][flow.me]
    assert landed.get("infantry", 0) >= 2


@covers("leaders:nomadagentthundarian", "technologies:tcs")
def test_thundarian_i_temporal_command_suite_w_walce(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nomad")
    def setup(p: Json) -> None:
        p["technologies"].append("tcs")
        p["fleet_cc"] = 6

    flow.player(setup)
    flow.player(lambda p: p.__setitem__("fleet_cc", 6), flow.other)
    flow.space_combat({"dreadnought": 3, "cruiser": 2}, {"dreadnought": 3, "cruiser": 2})
    flow.fight(stop=lambda: flow.battle().get("step") == "ASSIGN")
    view = flow.battle()
    assert view["step"] == "ASSIGN"
    assert f"{flow.me}:nomadagentthundarian" in flow.available()
    flow.use("leader", "nomadagentthundarian")
    assert flow.battle()["step"] == "ROLL"
    # The agent became exhausted: Temporal Command Suite readies it.
    flow.accept("Temporal Command Suite")
    me = _me(flow)
    assert me["leader_states"]["nomadagentthundarian"] == "unlocked"
    assert "tcs" in me["exhausted_technologies"]


@covers("leaders:nomadhero")
def test_time_warp_akcja_bohatera(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nomad")
    flow.player(lambda p: p["leader_states"].update(nomadhero="unlocked"))
    assert flow.playable()["nomadhero"]["playable"]
    flow.use("leader", "nomadhero")
    state = flow.state()
    assert state["players"][flow.me]["leader_states"]["nomadhero"] == "purged"
    effect = next(e for e in state["active_effects"] if e["key"] == "leaders:nomadhero:time_warp")
    assert effect["scope"] == "round" and effect["data"]["areas"][flow.home] == "time_warp"
    assert any(f["type"] == "area" and f["detail"] == "time_warp" and f["value"] == flow.home
               for f in _facts(flow))


@covers("promissory_notes:cavalry")
def test_cavalry_w_walce_dwoch_innych_graczy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "nomad", "sol", "letnev")
    note = flow.give_note("cavalry", flow.other)
    position, _ = flow.plain_pair()
    flow.space(position, flow.other, {"cruiser": 2})
    flow.space(position, flow.third, {"destroyer": 2})
    flow.edit(active=flow.other)
    flow.post("/tactical/activate", {"position": position})
    flow.to_step("SPACE_COMBAT")
    flow.start_space_combat()
    playable = flow.notes_playable(flow.other)
    assert playable[note]["playable"], playable[note]
    flow.play_note(flow.other, note, {"ship": "cruiser"})
    side = next(s for s in (flow.battle()["attacker"], flow.battle()["defender"])
                if s["playerId"] == flow.other)
    cruiser = next(u for u in side["units"] if u["baseType"] == "cruiser")
    assert cruiser["championHitsOn"] == 7 and cruiser["championDice"] == 2
    assert note in flow.state()["players"][flow.other]["promissory_notes_in_play"]
