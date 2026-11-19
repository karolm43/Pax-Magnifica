"""The Naaz-Rokha Alliance — scenariusze przez prawdziwe API (dostępność, RULES.md 62.15)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _me(flow: Flow) -> Json:
    return flow.state()["players"][flow.me]  # type: ignore[no-any-return]


def _explorable(flow: Flow) -> tuple[str, str]:
    """Sąsiad domu podmieniony na Vefutii (20, hazardous) - rzadka mapa nie ma planet poza
    domami: (pozycja, planeta)."""
    position = flow.neighbor_of(flow.home)
    flow.set_tile(position, "20")
    return position, "vefutii"


@covers("abilities:fabrication")
def test_fabrication_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naaz")
    flow.player(lambda p: p.update(relic_fragments=["crf1", "urf1", "hrf1"]))
    row = flow.playable()["fabrication"]
    assert row["playable"], row["reason"]
    flow.use("ability", "fabrication", {"mode": "relic", "fragments": ["crf1", "urf1"]})
    me = _me(flow)
    assert me["relic_fragments"] == ["hrf1"] and len(me["relics"]) == 1


@covers("leaders:naazagent")
def test_garv_and_gunn_i_distant_suns_w_oknie_eksploracji(registry: StaticDataRegistry) -> None:
    """Koniec tury: agent pozwala eksplorować; planeta z mechem - Distant Suns (2 karty)."""
    flow = Flow(registry, "naaz")
    position, planet = _explorable(flow)
    flow.ground(position, planet, flow.me, {"mech": 1})
    flow.player(lambda p: p.update(controlled_planets=[*p["controlled_planets"], planet]))
    flow.activate(flow.home)
    flow.decline_all()
    flow.end_turn()
    flow.accept("Garv and Gunn")
    assert _me(flow)["leader_states"]["naazagent"] == "exhausted"
    flow.accept("explore 1 of your planets", {"planet": planet})
    view: Json = flow.client.get("/exploration").json()
    assert view["active"] and view["current"] is None  # decyzja przed ujawnieniem
    assert view["queue"][0]["extraDraw"]
    flow.post("/exploration/draw", {"planet": planet, "extra": True})
    view = flow.client.get("/exploration").json()
    candidates = view["current"]["candidates"]
    assert len(candidates) == 2 and view["current"]["options"] == []
    flow.post("/exploration/choose", {"card": candidates[1]["cardId"]})
    view = flow.client.get("/exploration").json()
    assert view["current"]["candidates"] == [] and view["current"]["options"]


@covers("technologies:sc")
def test_supercharge_na_starcie_rundy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naaz")
    flow.player(lambda p: p.update(technologies=[*p["technologies"], "sc"]))
    flow.space_combat({"dreadnought": 2}, {"destroyer": 1})
    for _ in range(4):
        if flow.has_offer("Supercharge"):
            break
        step = flow.battle().get("step")
        if step == "AFB":
            flow.post("/tactical/battle/afb")
        else:
            flow.decline_all()
    flow.accept("Supercharge")
    assert "sc" in _me(flow)["exhausted_technologies"]


@covers("leaders:naazcommander")
def test_dart_and_tai_po_przejeciu_planety_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naaz")
    flow.player(lambda p: p["leader_states"].update(naazcommander="unlocked"))
    position, planet = _explorable(flow)
    flow.ground(position, planet, flow.other, {"infantry": 1})
    flow.player(lambda p: p.update(controlled_planets=[planet]), pid=flow.other)
    flow.space(position, flow.me, {"carrier": 1, "infantry": 4})
    flow.activate(position)
    flow.decline_all()
    flow.to_step("INVASION")
    if flow.state()["invasion"] is None:
        flow.post("/tactical/invasion/begin")
    flow.post("/tactical/invasion/commit", {"commits": [
        {"planet": planet, "baseType": "infantry", "count": 4},
    ]})
    started = False
    for _ in range(12):
        if flow.has_offer("Dart and Tai"):
            break
        battle = flow.battle()
        if battle.get("active") and battle.get("step") not in (None, "DONE"):
            flow.fight()
            continue
        if battle.get("active"):
            flow.post("/tactical/battle/close")
            continue
        if flow.state()["invasion"]["phase"] == "GROUND_COMBAT" and not started:
            flow.post("/tactical/battle/start", {"planet": planet})
            started = True
            continue
        flow.post("/tactical/invasion/next")
    flow.accept("Dart and Tai")
    exploring = flow.state()["exploration"]
    assert exploring is not None and exploring["player_id"] == flow.me


@covers("leaders:naazhero")
def test_perfect_synthesis_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naaz")
    flow.player(lambda p: p["leader_states"].update(naazhero="unlocked"))
    before = _me(flow)
    row = flow.playable()["naazhero"]
    assert row["playable"], row["reason"]
    flow.use("leader", "naazhero", {"first": 5, "second": 1})
    me = _me(flow)
    assert len(me["relics"]) == len(before["relics"]) + 1
    assert me["leader_states"]["naazhero"] == "purged"
    window = flow.state()["pending_window"]
    assert window["context"]["initiative"] == 5
    flow.post("/strategy/secondary", {"player_id": flow.me, "execute": True})
    me = _me(flow)
    assert me["strategic_cc"] == before["strategic_cc"]  # żeton z rezerwy, nie z puli
    assert flow.state()["pending_window"]["context"]["initiative"] == 1
    flow.post("/strategy/secondary", {"player_id": flow.me, "execute": False})
    assert flow.state()["pending_window"] is None


@covers("promissory_notes:bmf")
@ruling("promissory_notes:bmf#1", "promissory_notes:bmf#2")
def test_black_market_forgery_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naaz")
    note = flow.give_note("bmf", flow.other)
    flow.player(lambda p: p.update(relic_fragments=["irf1", "irf2"]), pid=flow.other)
    flow.edit(active=flow.other)
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row
    flow.play_note(flow.other, note, {"fragments": ["irf1", "irf2"]})
    state = flow.state()
    assert len(state["players"][flow.other]["relics"]) == 1
    assert "bmf" in state["players"][flow.me]["private"]["promissory_notes"]  # wraca do Naaz


@covers("breakthroughs:naazbt")
def test_absolute_synergy_z_panelu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "naaz")
    flow.player(lambda p: p.update(breakthrough_unlocked=True))
    planet = flow.planets(flow.home)[0]

    def four(s: Json) -> None:
        system = s["systems"][flow.home]
        system["space_units"][flow.me] = {"carrier": 1, "mech": 2}
        for units in system["planet_units"].values():  # startowy mech z Rokha - limit 4 sztuk
            units.get(flow.me, {}).pop("mech", None)
        system["planet_units"].setdefault(planet, {})[flow.me] = {"mech": 2}

    flow.edit(four)
    assert f"{flow.me}:naazbt" in flow.available()
    flow.use("breakthrough", "naazbt", {"keep": f"{flow.home}|space"})
    state = flow.state()
    assert state["players"][flow.me]["breakthrough_flipped"]
    assert state["systems"][flow.home]["space_units"][flow.me]["mech"] == 1
    data: Json = flow.client.get("/api/public/game/g/web-data").json()
    owned = next(p for p in data["playerData"] if p["faction"] == "naaz")["unitsOwned"]
    assert "naaz_voltron" in owned and "naaz_mech" not in owned
