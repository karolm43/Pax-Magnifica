"""The Yin Brotherhood — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.10)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers
from tests.rulings import ruling

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


@ruling("units:yin_mech#1")
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


def _devotion_ready(flow: Flow, theirs: dict[str, int], damaged: dict[str, int]) -> str:
    """Walka kosmiczna do oferty Devotion; potem flota rywala ustawiona na ``theirs``/``damaged``.

    Ustawienie PO rundzie usuwa losowość kości: Yin wskazuje cel w znanym układzie.
    """
    # Rywal z dużym zapasem (War Sun nie ma, więc pancerniki z Sustain): przeżyje 1. rundę.
    position = flow.space_combat({"cruiser": 3}, {"dreadnought": 3})
    flow.fight(stop=lambda: flow.has_offer("Devotion"))
    assert flow.has_offer("Devotion"), "Yin stracił krążowniki przed końcem 1. rundy"

    def put(s: Json) -> None:
        system = s["systems"][position]
        system["space_units"][flow.me] = {"cruiser": 2}
        system["space_units"][flow.other] = dict(theirs)
        system["damaged_units"] = {"space": {flow.other: dict(damaged)}}

    flow.edit(put)
    return position


@ruling("F_yin/devotion/2", "abilities:devotion#1")
@covers("abilities:devotion")
def test_devotion_yin_wskazuje_uszkodzony_statek(registry: StaticDataRegistry) -> None:
    """F_yin: Yin wybiera KONKRETNY statek - uszkodzony pancernik ginie, Sustain nie ratuje."""
    flow = Flow(registry, "yin")
    position = _devotion_ready(flow, {"dreadnought": 2}, {"dreadnought": 1})
    offer = flow.offer("Devotion")
    targets = {o["value"]: o["meta"].get("damaged") for o in offer["inputs"][1]["options"]}
    assert targets == {"dreadnought": False, "dreadnought:damaged": True}
    flow.accept("Devotion", {"ship": "cruiser", "target": "dreadnought:damaged"})
    flow.decline_all()  # Brother Milor po zniszczeniu własnego krążownika
    view = flow.battle()
    assert view["step"] == "ASSIGN" and view["assigning"] == "sol"
    assert view["hitTargets"]["sol"] == {
        "types": ["dreadnought"], "count": 1, "label": "Devotion", "damaged": True,
        "chooser": "yin",
    }
    _assign(flow, "sol", "sustain", "dreadnought", ok=False)  # inny statek nie anuluje
    _assign(flow, "sol", "destroy", "dreadnought", ok=False)  # cel to uszkodzony egzemplarz
    _assign(flow, "sol", "destroyDamaged", "dreadnought")
    system = flow.state()["systems"][position]
    assert system["space_units"][flow.other]["dreadnought"] == 1
    assert not system["damaged_units"].get("space", {}).get(flow.other)
    assert system["space_units"][flow.me]["cruiser"] == 1


@ruling("F_yin/devotion/2.2")
@covers("abilities:devotion")
def test_devotion_nieuszkodzony_cel_moze_uzyc_sustain(registry: StaticDataRegistry) -> None:
    """Wskazany nieuszkodzony statek może anulować trafienie swoim Sustain Damage (F_yin)."""
    flow = Flow(registry, "yin")
    position = _devotion_ready(
        flow, {"dreadnought": 2, "destroyer": 1}, {"dreadnought": 1}
    )
    flow.accept("Devotion", {"ship": "cruiser", "target": "dreadnought"})
    flow.decline_all()
    assert flow.battle()["hitTargets"]["sol"]["damaged"] is False
    _assign(flow, "sol", "destroy", "destroyer", ok=False)  # cel wybrał Yin
    _assign(flow, "sol", "destroyDamaged", "dreadnought", ok=False)  # nie ten egzemplarz
    _assign(flow, "sol", "sustain", "dreadnought")
    damaged = flow.state()["systems"][position]["damaged_units"]["space"][flow.other]
    assert damaged["dreadnought"] == 2
    flow.fight()


@ruling("F_yin/devotion/5")
@covers("abilities:devotion")
def test_devotion_nie_po_odwrocie_przeciwnika(registry: StaticDataRegistry) -> None:
    """F_yin: po odwrocie przeciwnika Devotion nie ma celu - koniec rundy idzie PO kroku Retreat
    (R_space_combat), a zdarzenia końca rundy odpalają się raz."""
    flow = Flow(registry, "yin")
    position, refuge = flow.plain_pair()
    flow.space(refuge, flow.other, {"carrier": 1})  # dozwolony cel odwrotu rywala
    flow.space(position, flow.me, {"cruiser": 3})
    flow.space(position, flow.other, {"dreadnought": 2})
    flow.activate(position)
    flow.to_step("SPACE_COMBAT")
    flow.start_space_combat()
    assert flow.battle()["step"] == "ANNOUNCE"
    flow.post("/tactical/battle/announce-retreat", {"faction": "sol", "announce": True})
    flow.post("/tactical/battle/roll")
    for _ in range(6):
        view = flow.battle()
        if view["step"] == "ASSIGN":
            flow.assign_auto()
        elif view["step"] == "TRIGGERS":
            assert not flow.has_offer("Devotion")  # przed odwrotem - jeszcze nie koniec rundy
            flow.decline_all()
        else:
            break
    view = flow.battle()
    if view["step"] == "DONE":
        pytest.skip("Rzut zniszczył całą flotę rywala - odwrót nie następuje (O3).")
    assert view["step"] == "RETREAT"
    assert not flow.has_offer("Devotion")
    flow.post("/tactical/battle/retreat", {"faction": "sol", "destination": refuge})
    assert not flow.has_offer("Devotion")  # rywal uciekł - brak statków do trafienia
    assert flow.battle()["step"] == "DONE"


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
    flow.fight(stop=lambda: (
        flow.has_offer("Brother Milor") or flow.has_boost("Brother Milor", flow.other)
    ))
    fighters = flow.state()["systems"][position]["space_units"]
    before = {pid: fighters.get(pid, {}).get("fighter", 0) for pid in (flow.me, flow.other)}
    if not flow.has_offer("Brother Milor"):
        flow.request_boost("Brother Milor", flow.other)  # cooperative (RULES.md 54.15)
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


@ruling("promissory_notes:greyfire#1", "promissory_notes:greyfire#2")
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
