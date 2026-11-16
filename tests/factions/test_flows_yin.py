"""The Yin Brotherhood — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.10)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers

_TILE = "26"  # zwykły kafel z jedną planetą (rzadka mapa startowa nie ma planet poza domami)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _influence_planets(flow: Flow, pid: str, need: int) -> list[str]:
    """Gotowe planety gracza z łącznym wpływem >= ``need``."""
    chosen: list[str] = []
    total = 0
    for system in flow.state()["systems"].values():
        for planet, owner in system["planet_owners"].items():
            info = flow.registry.planets.get(planet)
            if owner != pid or info is None or not info.influence:
                continue
            chosen.append(planet)
            total += int(info.influence)
            if total >= need:
                return chosen
    raise AssertionError("Not enough influence.")


def _ground_combat(
    flow: Flow, attackers: int, defenders: int, defender: str = ""
) -> tuple[str, str]:
    """``me`` ląduje na planecie rywala w zwykłym systemie i zaczyna walkę naziemną."""
    position, _ = flow.plain_pair()
    flow.set_tile(position, _TILE)
    planet = flow.planets(position)[0]
    flow.ground(position, planet, defender or flow.other, {"infantry": defenders},
                owner=not defender)
    flow.space(position, flow.me, {"carrier": 1, "infantry": attackers})
    flow.activate(position)
    flow.to_step("INVASION")
    if flow.state()["invasion"] is None:
        flow.post("/tactical/invasion/begin")
    while flow.state()["invasion"]["phase"] != "COMMIT":
        flow.post("/tactical/invasion/next")
    flow.post("/tactical/invasion/commit", {"commits": [
        {"planet": planet, "baseType": "infantry", "count": attackers},
    ]})
    for _ in range(4):
        if flow.state()["invasion"]["phase"] == "GROUND_COMBAT":
            break
        flow.post("/tactical/invasion/next")
    flow.post("/tactical/battle/start", {"planet": planet})
    return position, planet


def _assign(flow: Flow, faction: str, key: str, base_type: str, ok: bool = True) -> Json:
    return flow.post("/tactical/battle/assign", {  # type: ignore[no-any-return]
        "faction": faction, "sustain": [], "destroy": [], "destroyDamaged": [],
        key: [{"baseType": base_type, "count": 1}],
    }, ok=ok)


@covers("abilities:indoctrination")
def test_indoctrination_zastepuje_piechote(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    position, target = _ground_combat(flow, attackers=2, defenders=2)
    offer = flow.offer("Indoctrination")
    units = [o["value"] for o in offer["inputs"][0]["options"]]
    assert units == ["infantry", "mech"]  # Moyin's Ashes: mech za +1 wpływu
    flow.accept("Indoctrination", {
        "unit": "mech", "planets": _influence_planets(flow, flow.me, 3), "trade_goods": 0,
    })
    here = flow.state()["systems"][position]["planet_units"][target]
    assert here[flow.other] == {"infantry": 1}
    assert here[flow.me].get("mech") == 1
    assert flow.state()["players"][flow.me]["leader_states"]["yincommander"] == "unlocked"
    flow.fight()


@covers("abilities:devotion")
def test_devotion_po_rundzie_cel_wybiera_yin(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    flow.space_combat({"cruiser": 2, "carrier": 1}, {"destroyer": 2, "dreadnought": 1})
    flow.fight(stop=lambda: flow.has_offer("Devotion"))
    offer = flow.offer("Devotion")
    targets = [o["value"] for o in offer["inputs"][1]["options"]]
    assert "dreadnought" in targets
    flow.accept("Devotion", {"ship": "cruiser", "target": "dreadnought"})
    flow.decline_all()  # Brother Milor po zniszczeniu własnego krążownika
    view = flow.battle()
    assert view["step"] == "ASSIGN" and view["assigning"] == "sol"
    destroyers = any(u["baseType"] == "destroyer" for u in view["defender"]["units"])
    if destroyers:
        _assign(flow, "sol", "destroy", "destroyer", ok=False)  # cel wybrał Yin
    dread = next(u for u in view["defender"]["units"] if u["baseType"] == "dreadnought")
    if int(dread.get("sustainable") or 0):
        _assign(flow, "sol", "sustain", "dreadnought")  # trafiony statek może użyć Sustain
    else:
        _assign(flow, "sol", "destroyDamaged", "dreadnought")
    flow.fight()


@covers("technologies:ic")
def test_impulse_core_trafienie_w_nie_mysliwca(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    flow.player(lambda p: p["technologies"].append("ic"))
    flow.space_combat({"cruiser": 2}, {"fighter": 2, "carrier": 1})
    flow.accept("Impulse Core", {"ship": "cruiser"})
    flow.decline_all()  # Brother Milor po zniszczeniu własnego krążownika
    view = flow.battle()
    assert view["step"] == "ASSIGN" and view["assigning"] == "sol"
    _assign(flow, "sol", "destroy", "fighter", ok=False)
    _assign(flow, "sol", "destroy", "carrier")
    assert flow.state()["systems"][view["position"]]["space_units"][flow.me]["cruiser"] == 1


@covers("technologies:yso")
def test_yin_spinner_po_produkcji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    flow.player(lambda p: p["technologies"].append("yso"))
    flow.activate(flow.home)
    flow.to_step("PRODUCTION")
    flow.post("/tactical/produce", {"faction": flow.me, "orders": [
        {"baseType": "fighter", "count": 1, "zone": "space"},
    ]})
    offer = flow.offer("Yin Spinner")
    where = next(o["value"] for o in offer["inputs"][0]["options"] if o["value"].endswith("space"))
    before = flow.state()["systems"][flow.home]["space_units"][flow.me].get("infantry", 0)
    flow.accept("Yin Spinner", {"where": where, "count": 2})
    position = where.partition("|")[0]
    after = flow.state()["systems"][position]["space_units"][flow.me].get("infantry", 0)
    assert after == before + 2


@covers("leaders:yinagent")
def test_brother_milor_po_zniszczeniu_w_walce(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    position = flow.space_combat({"dreadnought": 2}, {"destroyer": 3})
    flow.fight(stop=lambda: flow.has_offer("Brother Milor"))
    fighters = flow.state()["systems"][position]["space_units"]
    before = {pid: fighters.get(pid, {}).get("fighter", 0) for pid in (flow.me, flow.other)}
    flow.accept("Brother Milor")
    state = flow.state()
    assert state["players"][flow.me]["leader_states"]["yinagent"] == "exhausted"
    after = {
        pid: state["systems"][position]["space_units"].get(pid, {}).get("fighter", 0)
        for pid in (flow.me, flow.other)
    }
    assert sum(after.values()) == sum(before.values()) + 2


@covers("leaders:yinhero")
def test_quantum_dissemination_inwazja_bez_aktywacji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yin")
    position, _ = flow.plain_pair()
    flow.set_tile(position, _TILE)
    planet = flow.planets(position)[0]
    flow.ground(position, planet, flow.other, {"infantry": 1})
    flow.player(lambda p: p["leader_states"].update(yinhero="unlocked"))
    row = flow.playable()["yinhero"]
    assert row["playable"], row["reason"]
    choice = f"{position}|{planet}"
    flow.use("leader", "yinhero", {"planet1": choice, "planet2": choice, "planet3": "none"})
    state = flow.state()
    assert state["active_system"] is None
    assert state["invasion"]["source"] == "leaders:yinhero"
    assert state["invasion"]["phase"] == "COMMIT"
    assert state["players"][flow.me]["leader_states"]["yinhero"] == "purged"
    flow.post("/turn/end", {"player_id": flow.me}, ok=False)  # inwazja w toku
    flow.post("/tactical/invasion/next")
    assert flow.state()["invasion"]["phase"] == "GROUND_COMBAT"  # bez Space Cannon Defense
    flow.post("/tactical/battle/start", {"planet": planet})
    flow.fight()
    flow.post("/tactical/battle/close")
    for _ in range(3):
        if flow.state()["invasion"] is None:
            break
        flow.post("/tactical/invasion/next")
    assert flow.state()["invasion"] is None


@covers("promissory_notes:greyfire")
def test_greyfire_mutagen_u_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "sol", other="yin")

    def take(s: Json) -> None:
        s["players"][flow.other]["private"]["promissory_notes"].remove("greyfire")
        s["players"][flow.me]["private"]["promissory_notes"].append("greyfire")

    flow.edit(take)
    position, target = _ground_combat(flow, attackers=2, defenders=2, defender="neutral")
    row = flow.notes_playable(flow.me)["greyfire"]
    assert row["playable"], row["reason"]
    flow.play_note(flow.me, "greyfire")
    here = flow.state()["systems"][position]["planet_units"][target]
    assert here["neutral"] == {"infantry": 1}
    assert here[flow.me]["infantry"] == 3
    assert "greyfire" in flow.state()["players"][flow.other]["private"]["promissory_notes"]


def test_yin_ascendant_z_edytora_i_w_panelu_liderow(registry: StaticDataRegistry) -> None:
    """Przełom przyznany w edytorze gracza = „gain” (sojusz), commander widoczny w panelu."""
    flow = Flow(registry, "yin")
    flow.post(f"/player/{flow.me}/edit", {"breakthrough_unlocked": True})
    state = flow.state()
    assert state["players"][flow.me]["breakthrough_unlocked"] is True
    alliances = [e for e in state["active_effects"] if e["key"] == "breakthroughs:yinbt:alliances"]
    assert len(alliances) == 1 and len(alliances[0]["data"]["commanders"]) == 1
    commander = alliances[0]["data"]["commanders"][0]
    data = flow.client.get(
        "/api/public/game/g/web-data", params={"viewing_player": flow.me}
    ).json()
    me = next(p for p in data["playerData"] if p["faction"] == "yin")
    shown = {leader["id"]: leader for leader in me["leaders"]}
    assert shown[commander]["alliance"] is True and shown[commander]["locked"] is False
    # Ponowne zapisanie tego samego pola nie losuje kolejnego sojuszu.
    flow.post(f"/player/{flow.me}/edit", {"breakthrough_unlocked": True})
    again = [e for e in flow.state()["active_effects"] if e["key"] == alliances[0]["key"]]
    assert len(again[0]["data"]["commanders"]) == 1
