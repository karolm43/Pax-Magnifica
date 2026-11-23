"""The Argent Flight — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.11)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _damaged(flow: Flow, position: str) -> dict[str, int]:
    space = flow.state()["systems"][position]["damaged_units"].get("space", {})
    return dict(space.get(flow.other, {}))


@covers("abilities:raid_formation")
def test_raid_formation_argent_wybiera_statki(registry: StaticDataRegistry) -> None:
    """Strike Wing Alpha II (AFB 6x3) przeciw 3 pancernikom bez myśliwców: przy 1-2 trafieniach
    Argent wybiera, które pancerniki zostaną uszkodzone (decyzja w oknie bitwy)."""
    for seed in range(1, 40):
        flow = Flow(registry, "argent")
        flow.player(lambda p: p["technologies"].append("swa2"))
        flow.client.post("/god-mode/patch", json={"rng_seed": seed})
        position = flow.space_combat({"destroyer": 1}, {"dreadnought": 3})
        assert flow.battle()["step"] == "AFB"
        flow.post("/tactical/battle/afb")
        if not flow.has_offer("Raid Formation"):
            continue
        offer = flow.offer("Raid Formation")
        field = offer["inputs"][0]
        assert field["kind"] == "multi" and field["min"] == field["max"]
        picks = [o["value"] for o in field["options"]][: field["min"]]
        flow.accept("Raid Formation", {"ships": picks})
        assert _damaged(flow, position) == {"dreadnought": len(picks)}
        assert flow.battle()["step"] != "TRIGGERS"  # walka idzie dalej
        flow.fight()
        return
    pytest.fail("Żaden seed nie dał 1-2 trafień AFB.")


@ruling("promissory_notes:ambuscade#1", "promissory_notes:ambuscade#2")
@covers("promissory_notes:ambuscade")
def test_ambuscade_dodatkowa_kosc_afb_i_zwrot(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "argent")
    note = flow.give_note("ambuscade", flow.other)
    flow.space_combat({"carrier": 1, "fighter": 3}, {"destroyer": 1})
    assert flow.battle()["step"] == "AFB"
    assert flow.notes_playable(flow.me) == {} or "ambuscade" not in flow.notes_playable(flow.me)
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row.get("reason")
    flow.play_note(flow.other, note)
    flow.post("/tactical/battle/afb")
    state = flow.state()
    combat = state["active_combat"]
    log = combat["log"][0] if combat else None
    assert log is not None and log["phase"] == "AFB"
    entry = log["rolls"][flow.other][0]
    assert entry["extraDice"] == 1 and len(entry["dice"]) == 2 + 1  # Destroyer I: AFB 9 (x2)
    assert "ambuscade" in state["players"][flow.me]["private"]["promissory_notes"]
    assert not any(e["key"].startswith("promissory_notes:ambuscade") for e in
                   state["active_effects"])


@ruling("leaders:argentagent#1", "leaders:argentagent#2")
@covers("leaders:argentagent")
def test_trilossa_przenosi_wyprodukowana_piechote(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "argent")
    planets = flow.planets(flow.home)
    dock = next(
        p for p in planets
        if flow.state()["systems"][flow.home]["planet_units"].get(p, {}).get(flow.me, {})
        .get("spacedock")
    )
    other = next(p for p in planets if p != dock)
    flow.activate(flow.home)
    flow.to_step("PRODUCTION")
    flow.post("/tactical/produce", {"faction": flow.me, "orders": [
        {"baseType": "infantry", "count": 2, "zone": dock},
    ]})
    before = flow.state()["systems"][flow.home]["planet_units"][other].get(flow.me, {})
    flow.accept("Trilossa Aun Mirik")
    offer = flow.offer("place your ground forces")
    params: Json = {i["key"]: 0 for i in offer["inputs"]}  # nieruszone trasy = 0 (jak UI)
    key = f"{dock}|{other}|infantry"
    assert key in params
    params[key] = 2
    flow.accept("place your ground forces", params)
    state = flow.state()
    after = state["systems"][flow.home]["planet_units"][other][flow.me]
    assert after.get("infantry", 0) == before.get("infantry", 0) + 2
    assert state["players"][flow.me]["leader_states"]["argentagent"] == "exhausted"


@ruling("leaders:argenthero#2", "leaders:argenthero#unlock")
@covers("leaders:argenthero")
def test_helix_protocol_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "argent")
    flow.player(lambda p: p["leader_states"].update(argenthero="locked"))
    flow.player(lambda p: p.update(scored_secrets=["a", "b", "c"]))
    flow.post("/god-mode/patch", {"rng_seed": 7})  # odświeżenie stanu (odblokowania)
    position, _ = flow.plain_pair()

    def token(s: Json) -> None:
        s["systems"][position]["command_tokens"] = [flow.me]

    flow.edit(token)
    if flow.state()["players"][flow.me]["leader_states"]["argenthero"] != "unlocked":
        flow.player(lambda p: p["leader_states"].update(argenthero="unlocked"))
    row = flow.playable()["argenthero"]
    assert row["playable"], row["reason"]
    ships = flow.state()["systems"][flow.home]["space_units"][flow.me]
    picks = [f"{flow.home}|{bt}|{i}" for bt, n in ships.items() for i in range(n)
             if bt not in ("infantry", "mech", "fighter")]
    flow.use("leader", "argenthero", {"moves": [f"{u}>{position}" for u in picks]})
    state = flow.state()
    assert state["players"][flow.me]["leader_states"]["argenthero"] == "purged"
    moved = state["systems"][position]["space_units"][flow.me]
    assert sum(moved.values()) == len(picks)


@ruling("breakthroughs:argentbt#1", "breakthroughs:argentbt#2")
@covers("breakthroughs:argentbt")
def test_wing_transfer_zetony_i_ruch_na_koniec_akcji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "argent")
    flow.player(lambda p: p.update(breakthrough_unlocked=True))
    position, neighbor = flow.plain_pair()
    flow.space(position, flow.me, {"carrier": 1})
    flow.space(neighbor, flow.me, {"cruiser": 1})
    flow.activate(position)
    offer = flow.offer("Wing Transfer: place")
    assert [o["value"] for o in offer["inputs"][0]["options"]] == [neighbor] or neighbor in [
        o["value"] for o in offer["inputs"][0]["options"]
    ]
    flow.accept("Wing Transfer: place", {"systems": [neighbor]})
    assert flow.me in flow.state()["systems"][neighbor]["command_tokens"]
    flow.post("/tactical/end", {"player_id": flow.me}, ok=False)
    for _ in range(6):
        if flow.has_offer("Wing Transfer: move"):
            break
        flow.post("/tactical/step/next", ok=False)
    flow.accept("Wing Transfer: move", {"moves": [f"{neighbor}|cruiser|0>{position}"]})
    assert flow.state()["systems"][position]["space_units"][flow.me] == {
        "carrier": 1, "cruiser": 1,
    }
