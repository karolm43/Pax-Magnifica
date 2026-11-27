"""The Empyrean — scenarios through the real API (availability, RULES.md 62.20)."""

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


def _other_turn(flow: Flow) -> None:
    """Like ``Flow.other_turn``, declining the Empyrean's own offers of that activation."""
    position, _ = flow.plain_pair()
    flow.activate(position)
    flow.decline_all()
    flow.end_turn()


def _move_other(flow: Flow, source: str, target: str, ships: dict[str, int]) -> None:
    faction = flow.state()["players"][flow.other]["faction"]
    flow.post("/tactical/move", {
        "faction": faction, "fromPosition": source,
        "ships": [{"baseType": bt, "count": n} for bt, n in ships.items()],
        "cargo": [], "route": [source, target],
    })


def _web(flow: Flow) -> Json:
    return flow.client.get("/api/public/game/g/web-data").json()  # type: ignore[no-any-return]


def _facts(flow: Flow) -> list[Json]:
    entries = flow.client.get("/history/activity").json()["entries"]
    return [f for e in entries for f in e["activity"]["facts"]]


@ruling("abilities:dark_whispers#1")
def test_dark_whispers_w_setupie(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    hand = _me(flow)["private"]["promissory_notes"]
    assert "dark_pact" in hand and "blood_pact" in hand


@covers("abilities:aetherpassage")
def test_aetherpassage_po_aktywacji_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    _other_turn(flow)
    target, _ = flow.plain_pair()
    flow.activate(target)  # the rival activates
    flow.request_boost("Aetherpassage", flow.other)  # cooperative (RULES.md 54.15)
    flow.accept("Aetherpassage")
    effects = flow.state()["active_effects"]
    assert any(e["key"] == "abilities:aetherpassage:allowed" and e["owner"] == flow.other
               for e in effects)


@covers("technologies:vw")
def test_voidwatch_rywal_oddaje_notke(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    flow.player(lambda p: p["technologies"].append("vw"))
    _other_turn(flow)
    target, source = flow.plain_pair()
    flow.space(target, flow.me, {"destroyer": 1})
    flow.space(source, flow.other, {"cruiser": 1})
    flow.activate(target)
    flow.decline_all()
    _move_other(flow, source, target, {"cruiser": 1})
    hand = flow.state()["players"][flow.other]["private"]["promissory_notes"]
    offer = flow.offer("Voidwatch", flow.other)
    assert offer["mandatory"] and offer["inputs"][0]["auto"] == hand[0]
    flow.accept("Voidwatch", {"note": hand[-1]}, pid=flow.other)
    assert hand[-1] in _me(flow)["private"]["promissory_notes"]


@covers("technologies:as")
def test_aetherstream_przy_mglawicy_domowej(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    flow.player(lambda p: p["technologies"].append("as"))
    near = flow.neighbor_of(flow.home)  # The Dark is a nebula: its neighbours touch an anomaly
    flow.activate(near)
    flow.accept("Aetherstream")
    assert any(e["key"] == "technologies:as:boost" and e["owner"] == flow.me
               for e in flow.state()["active_effects"])


@covers("leaders:empyreanagent")
def test_acamar_po_ruchu_do_pustego_systemu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    target, source = flow.plain_pair()  # the sparse start map: no planets outside homes
    flow.space(source, flow.me, {"destroyer": 1})
    flow.activate(target)
    flow.decline_all()
    before = _me(flow)["fleet_cc"]
    flow.move(source, target, {"destroyer": 1})
    flow.accept("Acamar")
    decision = flow.offer("Acamar")  # the gaining player picks the pool
    assert decision["mandatory"] and decision["inputs"][0]["auto"] == "tactical"
    flow.accept("Acamar", {"pool": "fleet"})
    me = _me(flow)
    assert me["fleet_cc"] == before + 1
    assert me["leader_states"]["empyreanagent"] == "exhausted"


@covers("leaders:empyreancommander")
def test_xuange_zwraca_zeton_po_ruchu_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    flow.player(lambda p: p["leader_states"].update(empyreancommander="unlocked"))
    _other_turn(flow)
    target, source = flow.plain_pair()

    def token(s: Json) -> None:
        s["systems"][target]["command_tokens"] = [flow.me]

    flow.edit(token)
    flow.space(source, flow.other, {"cruiser": 1})
    flow.activate(target)
    flow.decline_all()
    _move_other(flow, source, target, {"cruiser": 1})
    flow.accept("Xuange")
    assert flow.me not in flow.state()["systems"][target]["command_tokens"]


@covers("leaders:empyreanhero")
def test_multiverse_shift_frontier_tokens(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    flow.player(lambda p: p["leader_states"].update(empyreanhero="unlocked"))
    target, _ = flow.plain_pair()

    def clear(s: Json) -> None:
        for system in s["systems"].values():
            system["frontier_token"] = False

    flow.edit(clear)
    flow.space(target, flow.me, {"destroyer": 1})
    row = flow.playable()["empyreanhero"]
    assert row["playable"], row["reason"]
    flow.use("leader", "empyreanhero")
    state = flow.state()
    assert state["players"][flow.me]["leader_states"]["empyreanhero"] == "purged"
    assert state["exploration"]["current"]["deck"] == "frontier"
    assert state["exploration"]["position"] == target
    tokens = [p for p, s in state["systems"].items() if s["frontier_token"]]
    assert tokens and target not in tokens  # explored at once
    areas = {(f["value"], f["detail"]) for f in _facts(flow) if f["type"] == "area"}
    assert (target, "explore") in areas
    assert any(d == "frontier" for _, d in areas)
    assert any(f["type"] == "frontier_tokens" and f["delta"] >= 1 for f in _facts(flow))


@covers("promissory_notes:dark_pact")
@ruling("promissory_notes:dark_pact#1")
def test_dark_pact_zagranie_i_pelne_commodities(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    note = flow.give_note("dark_pact", flow.other)
    _other_turn(flow)
    flow.play_note(flow.other, note)
    other = flow.state()["players"][flow.other]
    assert note in other["promissory_notes_in_play"]
    value = int(other["commodity_value"])
    flow.end_turn(flow.other)  # the Empyrean's turn: it is the active player of the transaction
    flow.player(lambda p: p.update(commodities=value, trade_goods=0), flow.other)
    flow.player(lambda p: p.update(trade_goods=0))
    flow.space(flow.neighbor_of(flow.other_home), flow.me, {"destroyer": 1})  # neighbours
    flow.transact(give={}, receive={"commodities": value})
    state = flow.state()
    assert state["players"][flow.other]["trade_goods"] == 1
    assert state["players"][flow.me]["trade_goods"] == value + 1


@covers("promissory_notes:blood_pact")
@ruling("promissory_notes:blood_pact#1")
def test_blood_pact_zagranie_i_zwrot(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    note = flow.give_note("blood_pact", flow.other)
    _other_turn(flow)
    flow.play_note(flow.other, note)
    state = flow.state()
    assert note in state["players"][flow.other]["promissory_notes_in_play"]
    assert note not in state["players"][flow.other]["private"]["promissory_notes"]


@covers("units:empyrean_flagship")
def test_dynamo_naprawia_po_sustain_damage(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    position, _ = flow.plain_pair()
    flow.player(lambda p: p.update(fleet_cc=6))
    flow.player(lambda p: p.update(fleet_cc=6), flow.other)
    flow.space(position, flow.me, {"flagship": 1, "dreadnought": 2})
    flow.space(position, flow.other, {"dreadnought": 1, "destroyer": 4})
    flow.activate(position)
    flow.decline_all()
    flow.to_step("SPACE_COMBAT")
    flow.start_space_combat()
    flow.fight(stop=lambda: flow.has_offer("Dynamo"))
    offer = flow.offer("Dynamo")
    assert offer["inputs"][0]["auto"] >= 1
    flow.accept("Dynamo")
    assert "thedark" in _me(flow)["exhausted_planets"]


@covers("units:empyrean_mech")
def test_watcher_anuluje_karte_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    _other_turn(flow)
    flow.ground(flow.home, "thedark", flow.me, {"mech": 1})
    flow.space(flow.neighbor_of(flow.home), flow.other, {"cruiser": 1})
    flow.player(lambda p: p["private"].update(action_cards=["industrial_initiative"]), flow.other)
    flow.post("/action-card/play", {"player_id": flow.other, "card_id": "industrial_initiative",
                                    "params": {}})
    assert flow.state()["held_play"] is not None
    assert f"{flow.me}:empyrean_mech" in flow.available()
    flow.use("unit", "empyrean_mech")
    state = flow.state()
    assert state["held_play"] is None
    assert "industrial_initiative" in state["decks"]["action_card_discard"]
    assert "mech" not in state["systems"][flow.home]["planet_units"]["thedark"].get(flow.me, {})


@covers("breakthroughs:empyreanbt")
def test_void_tether_na_granicy_i_w_web_data(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "empyrean")
    flow.player(lambda p: p.update(breakthrough_unlocked=True))
    near = flow.neighbor_of(flow.home)
    flow.activate(near)
    offer = flow.offer("Void Tether: place")
    border = offer["inputs"][1]["options"][0]["value"]
    flow.accept("Void Tether: place", {"token": "new", "border": border})
    low = min(near, border)
    zones = flow.state()["systems"][low]["faction_tokens"]
    assert zones[f"border:{max(near, border)}"] == {"voidtether": flow.me}
    web = _web(flow)
    assert [b for b in web["borderAnomalies"] if b["type"] == "void_tether"]
    grid = flow.client.app.state.ctx.current_grid  # type: ignore[attr-defined]
    assert grid.are_adjacent(near, border)  # map graph untouched (adjacency layer only)
