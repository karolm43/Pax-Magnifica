"""The Ghosts of Creuss — scenarios through the real API (availability, RULES.md 62.19)."""

from __future__ import annotations

import pytest

from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers
from tests.rulings import ruling

ALPHA, BETA = "creussalpha", "creussbeta"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _me(flow: Flow) -> Json:
    return flow.state()["players"][flow.me]  # type: ignore[no-any-return]


def _gate(flow: Flow) -> str:
    """Creuss Gate (17) - on the Creuss home slot (``home_position``)."""
    return str(next(pos for pos, s in flow.state()["systems"].items() if s["system_id"] == "17"))


def _real_home(flow: Flow) -> str:
    """The Creuss home system (51) - off-board, in a corner of the map."""
    return str(next(pos for pos, s in flow.state()["systems"].items() if s["system_id"] == "51"))


def _api_grid(flow: Flow) -> HexGrid:
    """The server's map (off-board tiles, tokens and Hil Colish synced from the state)."""
    return flow.client.app.state.ctx.current_grid  # type: ignore[attr-defined,no-any-return]


def _token(flow: Flow, position: str, kind: str = ALPHA) -> None:
    def put(s: Json) -> None:
        s["systems"][position]["faction_tokens"] = {"space": {kind: flow.me}}

    flow.edit(put)


def _tokens(flow: Flow) -> dict[str, str]:
    return {
        kind: pos for pos, s in flow.state()["systems"].items()
        for kind, owner in s.get("faction_tokens", {}).get("space", {}).items()
        if owner == flow.me
    }


def _web(flow: Flow) -> Json:
    return flow.client.get("/api/public/game/g/web-data").json()  # type: ignore[no-any-return]


@ruling("abilities:creuss_gate#1", "abilities:creuss_gate#3", "F_creuss/creuss-gate/2")
def test_creuss_gate_w_setupie(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "ghost")
    state = flow.state()
    gate, home = _gate(flow), _real_home(flow)
    assert flow.home == gate  # the gate is where the home system would normally be placed
    assert state["systems"][home]["space_units"][flow.me]  # units in the off-board home (51)
    assert state["systems"][gate]["frontier_token"]  # R_frontier_tokens
    grid = _api_grid(flow)
    assert gate in grid.positions and home in grid.positions
    assert grid.are_adjacent(gate, home)  # delta <-> delta
    assert grid.is_edge(home)


def test_wormhole_generator_przez_api_i_zeton_na_mapie(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "ghost")
    flow.player(lambda p: p["technologies"].append("wg"))
    target, _ = flow.plain_pair()
    flow.post("/tactical/component-action", {
        "player_id": flow.me, "component_id": "wg", "params": {"token": ALPHA, "position": target},
    })
    assert _tokens(flow) == {ALPHA: target}
    assert "wg" in _me(flow)["exhausted_technologies"]
    space = _web(flow)["tileUnitData"][target]["space"]
    assert {"entityId": ALPHA, "entityType": "token", "count": 1} in space["neutral"]


@covers("technologies:ds")
@ruling("F_creuss/dimensional-splicer/4")
def test_dimensional_splicer_na_starcie_walki(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "ghost")
    flow.player(lambda p: p["technologies"].append("ds"))
    flow.player(lambda p: p["private"].update(action_cards=["sh1"]), flow.other)
    position, _ = flow.plain_pair()
    _token(flow, position)
    flow.space(position, flow.me, {"cruiser": 1, "destroyer": 1})
    flow.space(position, flow.other, {"dreadnought": 2})
    flow.activate(position)
    flow.decline_all()  # Emissary Taivra (alpha token in the active system)
    flow.to_step("SPACE_COMBAT")
    flow.start_space_combat()
    offer = flow.offer("Dimensional Splicer")
    assert {o["value"] for o in offer["inputs"][0]["options"]} == {"dreadnought"}
    flow.accept("Dimensional Splicer", {"target": "dreadnought"})
    flow.decline_all()
    rows = flow.client.get("/action-card/playable", params={"player_id": flow.other}).json()
    row = next(r for r in rows["cards"] if r["card_id"] == "sh1")
    assert row["playable"], row["reason"]  # Shields Holding cancels the Splicer hit
    hit = flow.state()["active_combat"]["hit_targets"][flow.other]
    assert hit["types"] == ["dreadnought"] and hit["chooser"] == flow.me


@ruling("F_creuss/dimensional-splicer/6")
def test_dimensional_splicer_sustain_i_direct_hit(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "ghost")
    flow.player(lambda p: p["technologies"].append("ds"))
    flow.player(lambda p: p["private"].update(action_cards=["dh1"]))
    position, _ = flow.plain_pair()
    _token(flow, position)
    flow.space(position, flow.me, {"cruiser": 1})
    flow.space(position, flow.other, {"dreadnought": 1})
    flow.activate(position)
    flow.decline_all()
    flow.to_step("SPACE_COMBAT")
    flow.start_space_combat()
    flow.accept("Dimensional Splicer", {"target": "dreadnought"})
    flow.decline_all()
    flow.assign_auto()  # the chosen dreadnought uses SUSTAIN DAMAGE
    damaged = flow.state()["systems"][position]["damaged_units"]
    assert damaged.get("space", {}).get(flow.other, {}).get("dreadnought") == 1
    rows = flow.client.get("/action-card/playable", params={"player_id": flow.me}).json()
    row = next(r for r in rows["cards"] if r["card_id"] == "dh1")
    assert row["playable"], row["reason"]  # Direct Hit after that Sustain Damage


@covers("leaders:ghostagent")
def test_emissary_taivra_po_aktywacji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "ghost")
    position, _ = flow.plain_pair()
    _token(flow, position, BETA)
    flow.activate(position)
    flow.accept("Emissary Taivra")
    state = flow.state()
    assert state["players"][flow.me]["leader_states"]["ghostagent"] == "exhausted"
    assert any(e["key"] == "leaders:ghostagent:link" for e in state["active_effects"])


@covers("units:ghost_mech")
def test_icarus_drive_po_aktywacji_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "ghost")
    home = _real_home(flow)
    flow.ground(home, "creuss", flow.me, {"mech": 1, "infantry": 1})
    position, _ = flow.plain_pair()
    flow.activate(position)  # "After any player activates a system"
    flow.accept("Icarus Drive", {"mech": f"{home}|creuss|0", "token": BETA})
    assert _tokens(flow) == {BETA: home}  # the mech's system, not the active one
    assert "mech" not in flow.state()["systems"][home]["planet_units"]["creuss"][flow.me]


@covers("leaders:ghostcommander")
def test_sai_seravus_po_ruchu_przez_wormhole(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "ghost")
    flow.player(lambda p: p["leader_states"].update(ghostcommander="unlocked"))
    home, gate = _real_home(flow), _gate(flow)
    flow.space(home, flow.me, {"carrier": 1})
    flow.activate(gate)
    flow.move(home, gate, {"carrier": 1})  # through the delta wormholes
    offer = flow.offer("Sai Seravus")
    assert offer["inputs"][0]["max"] == 1 and offer["inputs"][0]["auto"] == 1
    flow.accept("Sai Seravus", {"fighters": 1})
    assert flow.state()["systems"][gate]["space_units"][flow.me] == {"carrier": 1, "fighter": 1}


@covers("leaders:ghosthero")
def test_singularity_reactor_zamienia_systemy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "ghost")
    flow.player(lambda p: p["leader_states"].update(ghosthero="unlocked"))
    gate = _gate(flow)
    target, _ = flow.plain_pair()
    flow.space(target, flow.me, {"destroyer": 1})
    before = flow.state()["systems"]
    gate_tile, target_tile = before[gate]["system_id"], before[target]["system_id"]
    row = flow.playable()["ghosthero"]
    assert row["playable"], row["reason"]
    flow.use("leader", "ghosthero", {"first": gate, "second": target})
    state = flow.state()
    assert state["systems"][gate]["system_id"] == target_tile
    assert state["systems"][target]["system_id"] == gate_tile
    assert state["systems"][gate]["space_units"][flow.me] == {"destroyer": 1}
    assert state["players"][flow.me]["leader_states"]["ghosthero"] == "purged"
    grid = _api_grid(flow)
    assert grid.are_adjacent(target, _real_home(flow))  # the gate's delta moved with its tile
    entries = flow.client.get("/history/activity").json()["entries"]
    facts = [f for e in entries for f in e["activity"]["facts"]]
    assert {f["value"] for f in facts if f["type"] == "tile_replaced"} >= {gate, target}


@covers("promissory_notes:iff")
@ruling("promissory_notes:iff#2", "F_creuss/creuss-iff/1")
def test_creuss_iff_na_poczatku_tury_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "ghost")
    note = flow.give_note("iff", flow.other)
    flow.other_turn()  # Creuss ends the turn - the rival's turn starts
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note, {"token": ALPHA, "position": flow.other_home})
    state = flow.state()
    assert _tokens(flow) == {ALPHA: flow.other_home}
    assert note in state["players"][flow.me]["private"]["promissory_notes"]  # back to Creuss
    assert note not in state["players"][flow.other]["private"]["promissory_notes"]


def _batch(flow: Flow, legs: list[tuple[str, list[str], dict[str, int]]]) -> None:
    """One ``/tactical/move-batch`` flight (what the flight plan's "Fly" sends)."""
    flow.post("/tactical/move-batch", {"faction": "ghost", "legs": [
        {"faction": "ghost", "fromPosition": route[0], "route": route, "cargo": [],
         "ships": [{"baseType": bt, "count": n} for bt, n in ships.items()]}
        for _src, route, ships in legs
    ]})


@ruling("F_creuss/hil-colish/1")
def test_hil_colish_przed_innymi_dwa_loty_w_jednym_kroku(registry: StaticDataRegistry) -> None:
    """Flight plan "Hil Colish before the others": the flagship flies first, then the rest - in
    the SAME Movement step - with a route through its delta in the active system."""
    flow = Flow(registry, "ghost")
    home, gate = _real_home(flow), _gate(flow)
    grid = _api_grid(flow)
    # Active system 2+ hops from the gate (no other way in from the Creuss home).
    target, side = next(
        (a, b) for a, b in [flow.plain_pair()]
        if gate not in grid.neighbors(a) and a != gate
    )
    flow.clear_space(home)
    flow.space(side, flow.me, {"flagship": 1})
    flow.space(home, flow.me, {"destroyer": 1})
    flow.activate(target)
    early = flow.post("/tactical/move-batch", {"faction": "ghost", "legs": [
        {"faction": "ghost", "fromPosition": home, "route": [home, target], "cargo": [],
         "ships": [{"baseType": "destroyer", "count": 1}]}]}, ok=False)
    assert early.status_code == 422  # no delta in the active system yet
    _batch(flow, [(side, [side, target], {"flagship": 1})])
    assert flow.state()["tactical_step"] == "MOVEMENT"
    _batch(flow, [(home, [home, target], {"destroyer": 1})])  # delta -> delta
    arrived = flow.state()["systems"][target]["space_units"][flow.me]
    assert arrived == {"flagship": 1, "destroyer": 1}
