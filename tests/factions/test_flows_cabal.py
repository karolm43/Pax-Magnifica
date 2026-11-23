"""The Vuil'raith Cabal — scenariusze przez prawdziwe API (dostępność, RULES.md 62.17)."""

from __future__ import annotations

from typing import Any

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(flow: Flow) -> Json:
    return flow.state()


def _home_neighbor(flow: Flow) -> str:
    """System obok domu Cabal (Dimensional Tear na Acheron) - poza domem rywala."""
    state = _state(flow)
    return next(
        n for n in sorted(flow.grid().neighbors(flow.home))
        if n in state["systems"] and n != flow.other_home
    )


def _web_player(flow: Flow, pid: str) -> Json:
    web = flow.client.get("/api/public/game/g/web-data").json()
    faction = _state(flow)["players"][pid]["faction"]
    return next(p for p in web["playerData"] if p["faction"] == faction)


def test_dom_cabal_to_szczelina_w_web_data(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "cabal")
    assert "GRAVITY_RIFT" in flow.grid().anomalies_at(flow.home)


@covers("leaders:cabalagent")
def test_stillness_of_stars_po_trade_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "cabal")
    flow.player(lambda p: p.update(strategy_cards=[5]), pid=flow.other)
    flow.edit(active=flow.other)
    flow.post("/strategy/play", {"player_id": flow.other, "initiative": 5})
    if _state(flow)["pending_strategy"] is not None:
        flow.post("/strategy/primary-step", {
            "player_id": flow.other, "payload": {"players": []},
        })
    offer = flow.offer("The Stillness of Stars")
    units = [o["value"] for o in next(i for i in offer["inputs"] if i["key"] == "unit")["options"]]
    assert "fighter" in units and "pds" not in units
    flow.accept("The Stillness of Stars", {"unit": "carrier"})
    state = _state(flow)
    assert state["players"][flow.me]["captured_units"] == {flow.other: {"carrier": 1}}
    assert state["players"][flow.other]["commodities"] == 0
    assert state["players"][flow.me]["leader_states"]["cabalagent"] == "exhausted"
    nombox = _web_player(flow, flow.me)["nombox"]
    assert list(nombox.values()) == [["carrier,1"]]


def test_vortex_akcja_komponentu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "cabal")
    target = _home_neighbor(flow)
    flow.player(lambda p: p["technologies"].append("vtx"))
    flow.space(target, flow.other, {"destroyer": 1})
    flow.post("/tactical/component-action", {
        "player_id": flow.me, "component_id": "vtx",
        "params": {"unit": f"{flow.other}|destroyer|{target}|space"},
    })
    state = _state(flow)
    assert state["players"][flow.me]["captured_units"] == {flow.other: {"destroyer": 1}}
    assert "vtx" in state["players"][flow.me]["exhausted_technologies"]


@covers("leaders:cabalhero")
def test_dimensional_anchor(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "cabal")
    target = _home_neighbor(flow)
    flow.player(lambda p: p["leader_states"].update(cabalhero="unlocked"))
    flow.space(target, flow.other, {"destroyer": 2, "fighter": 1})
    assert flow.playable()["cabalhero"]["playable"]
    flow.use("leader", "cabalhero")
    state = _state(flow)
    roll = state["table_roll"]
    assert roll["playerId"] == flow.other and len(roll["dice"]) == 2  # myśliwiec nie rzuca
    hit = sum(1 for d in roll["dice"] if d <= 3)
    captured = state["players"][flow.me]["captured_units"].get(flow.other, {})
    assert captured.get("destroyer", 0) == hit
    assert state["players"][flow.me]["leader_states"]["cabalhero"] == "purged"


@covers("promissory_notes:crucible")
@ruling("promissory_notes:crucible#2")
def test_crucible_po_aktywacji_wraca_do_cabal(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "cabal")
    note = flow.give_note("crucible", flow.other)
    flow.edit(active=flow.other)
    flow.post("/tactical/activate", {"position": _home_neighbor(flow)})
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note)
    state = _state(flow)
    effects = [e["key"] for e in state["active_effects"] if e.get("owner") == flow.other]
    assert "promissory_notes:crucible" in effects
    assert "crucible" in state["players"][flow.me]["private"]["promissory_notes"]
    assert "crucible" not in state["players"][flow.other]["private"]["promissory_notes"]


@covers("breakthroughs:cabalbt")
def test_przelom_ekspedycja_fracture_i_ingress(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "cabal")
    flow.player(lambda p: p.update(trade_goods=6, took_action_this_turn=True))
    flow.post("/expeditions/perform", {"slice": "tradeGoods", "payment": {"trade_goods": 3}})
    state = _state(flow)
    assert state["fracture"]["in_play"] and state["fracture"]["last_roll"] is None
    view: Any = flow.client.get("/thunders-edge").json()
    for _ in range(12):  # rozłóż ingressy (gracz wybiera, gdy kandydatów jest więcej)
        pending = view.get("pendingIngress") or []
        if not pending:
            break
        choice = pending[0]
        flow.post("/fracture/ingress", {
            "actor_id": flow.me, "color": choice["color"], "position": choice["candidates"][0],
        })
        view = flow.client.get("/thunders-edge").json()
    # Oferta przesunięcia wyskakuje SAMA zaraz po rozłożeniu ingressów - nie „Available now”.
    assert f"{flow.me}:cabalbt" not in flow.available()
    label = "Al'raith Ix Ianovar: move ingress tokens"
    source = next(p for p, s in sorted(_state(flow)["systems"].items()) if s["ingress_token"])
    flow.accept(label, {"from_1": source, "to_1": flow.home, "from_2": "none", "to_2": "none"})
    systems = _state(flow)["systems"]
    assert systems[flow.home]["ingress_token"] and not systems[source]["ingress_token"]
    assert not flow.has_offer(label)


def test_transakcja_zwraca_przechwycony_statek(registry: StaticDataRegistry) -> None:
    """R_capture: przechwycony statek wraca do właściciela w transakcji (stół 47.1b);
    myśliwców / piechoty zwrócić nie wolno (422)."""
    flow = Flow(registry, "cabal")
    a, b = flow.plain_pair()
    flow.space(a, flow.me, {"cruiser": 1})
    flow.space(b, flow.other, {"cruiser": 1})
    flow.player(lambda p: p.update(
        captured_units={flow.other: {"carrier": 1}}, captured_tokens={"fighter": 2},
    ))
    resp = flow.transact(give={"captured_units": ["fighter"]}, ok=False)
    assert resp.status_code == 422
    flow.transact(give={"captured_units": ["carrier"]})
    state = _state(flow)
    assert state["players"][flow.me]["captured_units"] == {}
    assert list(_web_player(flow, flow.me)["nombox"].values()) == [["fighter,2"]]
