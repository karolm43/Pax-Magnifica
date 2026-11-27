"""The Clan of Saar — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.14)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _space(flow: Flow, position: str, pid: str | None = None) -> dict[str, int]:
    return dict(flow.state()["systems"][position]["space_units"].get(pid or flow.me, {}))


def test_setup_dok_w_przestrzeni_bez_scavenge(registry: StaticDataRegistry) -> None:
    """Nowa gra: Floating Factory stoi w przestrzeni domu, planety domowe nie dają TG ze
    Scavenge (rozstawienie to nie „zdobycie kontroli”), web-data rysuje dok w przestrzeni."""
    flow = Flow(registry, "saar")
    state = flow.state()
    assert _space(flow, flow.home).get("spacedock") == 1
    assert all(
        not by.get(flow.me, {}).get("spacedock")
        for by in state["systems"][flow.home]["planet_units"].values()
    )
    assert not flow.offers()
    assert state["players"][flow.me]["trade_goods"] == 0
    data: Json = flow.client.get("/api/public/game/g/web-data").json()
    space = data["tileUnitData"][flow.home]["space"]
    assert any(u["entityId"] == "sd" for units in space.values() for u in units)


def test_dok_leci_z_flota(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "saar")
    target = sorted(flow.grid().neighbors(flow.home))[0]
    flow.activate(target)
    flow.decline_all()
    flow.move(flow.home, target, {"spacedock": 1, "carrier": 1})
    assert _space(flow, target) == {"spacedock": 1, "carrier": 1}


@covers("technologies:cm")
def test_chaos_mapping_oferta_na_starcie_tury(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "saar")
    flow.player(lambda p: p.update(technologies=[*p["technologies"], "cm"], trade_goods=3))
    position, _ = flow.plain_pair()
    flow.activate(position)
    flow.decline_all()  # Captain Mendosa (agent Saar) odzywa się przy każdej aktywacji
    flow.end_turn()  # rywal spasuje -> znów tura me
    flow.pass_and_end(flow.other)
    # Planety wyczerpane - zapłata za jednostkę idzie z TG (widać, że jest płatna).
    flow.player(lambda p: p.update(exhausted_planets=list(p["controlled_planets"])))
    flow.accept("Chaos Mapping", {"position": flow.home})
    flow.post("/tactical/produce", {"faction": flow.me, "orders": [
        {"baseType": "cruiser", "count": 1, "zone": "space"},
    ]})
    assert _space(flow, flow.home)["cruiser"] == 2
    assert flow.state()["players"][flow.me]["trade_goods"] == 1  # jednostka płatna (cm 1)


@covers("leaders:saaragent")
def test_mendosa_przy_aktywacji_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "saar")
    flow.player(lambda p: p["leader_states"].update(saaragent="unlocked"))
    flow.player(lambda p: p.update(technologies=[*p["technologies"], "cr2"]))
    start, target = flow.plain_pair()
    flow.space(start, flow.other, {"dreadnought": 1})
    flow.edit(active=flow.other)
    flow.post("/tactical/activate", {"position": target})
    assert not flow.has_offer("Captain Mendosa")  # cooperative (RULES.md 54.15)
    flow.request_boost("Captain Mendosa", flow.other, trade_goods=0)
    offer = flow.offer("Captain Mendosa")
    assert offer["player_id"] == flow.me
    flow.accept("Captain Mendosa", {"ship": f"{start}|dreadnought"})
    state = flow.state()
    assert state["players"][flow.me]["leader_states"]["saaragent"] == "exhausted"
    assert any(e["key"] == "leaders:saaragent" and e["owner"] == flow.other
               for e in state["active_effects"])


@covers("leaders:saarcommander")
def test_rowl_sarrig_po_produkcji_mysliwcow(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "saar")
    flow.player(lambda p: p["leader_states"].update(saarcommander="unlocked"))
    flow.player(lambda p: p.update(trade_goods=5))
    start, _ = flow.plain_pair()
    flow.space(start, flow.me, {"spacedock": 1, "carrier": 1})
    flow.activate(flow.home)
    flow.decline_all()
    flow.to_step("PRODUCTION")
    flow.post("/tactical/produce", {"faction": flow.me, "orders": [
        {"baseType": "fighter", "count": 2, "zone": "space"},
    ]})
    flow.accept("Rowl Sarrig", {"moves": [f"space|fighter|0>{start}"]})
    assert _space(flow, start).get("fighter") == 1


@covers("leaders:saarhero")
def test_armageddon_relay_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "saar")
    flow.player(lambda p: p["leader_states"].update(saarhero="unlocked"))
    target = sorted(flow.grid().neighbors(flow.home))[0]
    flow.space(target, flow.other, {"fighter": 2, "destroyer": 1})
    row = flow.playable()["saarhero"]
    assert row["playable"], row["reason"]
    flow.use("leader", "saarhero", {"position": target})
    assert _space(flow, target, flow.other) == {"destroyer": 1}
    assert flow.state()["players"][flow.me]["leader_states"]["saarhero"] == "purged"


@covers("units:saar_mech")
def test_scavenger_zeta_po_inwazji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "saar")
    flow.player(lambda p: p.update(trade_goods=0))
    target = flow.invade_own_home(attackers=2, defenders=0)
    flow.post("/tactical/invasion/commit", {"commits": [
        {"planet": target, "baseType": "infantry", "count": 2},
    ]})
    for _ in range(6):
        if flow.has_offer("Scavenger Zeta"):
            break
        flow.post("/tactical/invasion/next")
    assert flow.state()["players"][flow.me]["trade_goods"] == 1  # Scavenge
    flow.accept("Scavenger Zeta")
    units = flow.state()["systems"][flow.home]["planet_units"][target][flow.me]
    assert units.get("mech") == 1


@covers("promissory_notes:ragh")
def test_raghs_call_przez_api(registry: StaticDataRegistry) -> None:
    """Rywal ląduje na planecie domu Saar: Ragh's Call zabiera siły Saar na inną planetę."""
    flow = Flow(registry, "saar")
    note = flow.give_note("ragh", flow.other)
    home_a, home_b = flow.planets(flow.home)

    def setup(s: Json) -> None:
        system = s["systems"][flow.home]
        system["planet_units"] = {home_a: {flow.me: {"infantry": 2}},
                                  home_b: {flow.me: {"infantry": 1}}}
        system["space_units"] = {flow.other: {"carrier": 1, "infantry": 2}}

    flow.edit(setup, active=flow.other)
    flow.post("/tactical/activate", {"position": flow.home})
    flow.decline_all()
    flow.to_step("INVASION")
    if flow.state()["invasion"] is None:
        flow.post("/tactical/invasion/begin")
    flow.post("/tactical/invasion/commit", {"commits": [
        {"planet": home_a, "baseType": "infantry", "count": 2},
    ]})
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row.get("reason")
    flow.play_note(flow.other, note, {"planet": home_a, "destination": home_b})
    planets = flow.state()["systems"][flow.home]["planet_units"]
    assert planets[home_a].get(flow.me, {}) == {}
    assert planets[home_b][flow.me] == {"infantry": 3}


@covers("breakthroughs:saarbt")
def test_deorbit_barrage_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "saar")
    flow.post(f"/player/{flow.me}/edit", {"breakthrough_unlocked": True})
    flow.player(lambda p: p.update(trade_goods=5))
    field = sorted(flow.grid().neighbors(flow.home))[0]
    flow.set_tile(field, "44")  # pole asteroid obok domu
    flow.space(field, flow.me, {"cruiser": 1})
    target = flow.planets(flow.home)[0]
    flow.ground(flow.home, target, flow.other, {"infantry": 3})
    row = flow.playable()["saarbt"]
    assert row["playable"], row["reason"]
    flow.use("breakthrough", "saarbt", {"planet": target, "planets": [], "trade_goods": 5})
    state = flow.state()
    assert state["players"][flow.me]["trade_goods"] == 0
    assert state["players"][flow.me]["breakthrough_exhausted"]
    if flow.has_offer("Deorbit Barrage: assign hits"):
        hits = sum(1 for k in flow.offer("Deorbit Barrage: assign hits")["inputs"]
                   if k["key"].startswith("hit"))
        flow.accept("Deorbit Barrage: assign hits",
                    {f"hit{i + 1}": f"{flow.other}|infantry" for i in range(hits)})
        left = flow.state()["systems"][flow.home]["planet_units"][target][flow.other]
        assert left.get("infantry", 0) == max(0, 3 - hits)
