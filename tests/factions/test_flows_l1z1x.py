"""The L1Z1X Mindnet — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.12)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers
from tests.rulings import ruling


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _planet_units(flow: Flow, position: str, planet: str, pid: str) -> dict[str, int]:
    units = flow.state()["systems"][position]["planet_units"].get(planet, {})
    return dict(units.get(pid, {}))


def _ground_combat(flow: Flow, attackers: int, defenders: int, extra: Json | None = None) -> tuple[
    str, str
]:
    """Inwazja na kafel z dwiema planetami (dom L1Z1X ma jedną): rywal trzyma ``target``
    (``defenders`` piechoty + ``extra``), L1Z1X ląduje ``attackers`` piechoty. Zwraca (pozycja,
    planeta) po starcie walki naziemnej."""
    position, _ = flow.plain_pair()
    flow.set_tile(position, "27")  # New Albion + Starpoint
    target, source = "starpoint", "newalbion"

    def setup(s: Json) -> None:
        system = s["systems"][position]
        system["planet_units"] = {
            source: {flow.me: {"infantry": 1}},
            target: {flow.other: {"infantry": defenders, **(extra or {})}},
        }
        system["planet_owners"] = {source: flow.me, target: flow.other}
        system["space_units"] = {flow.me: {"carrier": 1, "infantry": attackers}}

    flow.edit(setup)
    flow.activate(position)
    assert flow.has_offer("I48S")  # własny agent też działa przy własnej aktywacji
    flow.decline_all()
    flow.to_step("INVASION")
    if flow.state()["invasion"] is None:
        flow.post("/tactical/invasion/begin")
    flow.post("/tactical/invasion/commit", {"commits": [
        {"planet": target, "baseType": "infantry", "count": attackers},
    ]})
    for _ in range(4):
        if flow.state()["invasion"]["phase"] == "GROUND_COMBAT":
            break
        flow.post("/tactical/invasion/next")
    flow.post("/tactical/battle/start", {"planet": target})
    return position, target


def _win_ground_combat(flow: Flow) -> None:
    """Walka naziemna do końca, potem kolejne podkroki inwazji aż do Establish Control."""
    flow.fight()
    flow.post("/tactical/battle/close")
    for _ in range(4):
        invasion = flow.state()["invasion"]
        if invasion is None or invasion["phase"] == "ESTABLISH":
            return
        flow.post("/tactical/invasion/next", ok=False)


@covers("abilities:harrow")
def test_harrow_po_rundzie_walki_naziemnej(registry: StaticDataRegistry) -> None:
    """Pancernik L1Z1X w aktywnym systemie: po rundzie walki naziemnej oferta Harrow, rzut na
    stół i trafienia przypisuje obrońca."""
    flow = Flow(registry, "l1z1x")
    position, _ = _ground_combat(flow, attackers=1, defenders=3)

    def dreadnought(s: Json) -> None:
        s["systems"][position]["space_units"][flow.me]["dreadnought"] = 1

    flow.edit(dreadnought)
    for _ in range(12):
        view = flow.battle()
        if flow.has_offer("Harrow"):
            break
        step = view.get("step")
        if not view.get("active") or step in (None, "DONE"):
            pytest.fail("Ground combat ended without a Harrow offer.")
        if step == "ROLL":
            flow.post("/tactical/battle/roll")
        elif step == "ASSIGN":
            flow.assign_auto()
        elif step == "TRIGGERS":
            flow.decline_all()  # decyzje startu walki rywala (np. agent Sol)
    offer = flow.offer("Harrow")
    # Plasma Scoring (technologia startowa L1Z1X): dodatkowa kość - wybór gracza, tu „Auto”.
    extra = {i["key"]: "auto" for i in offer["inputs"] if i["key"].startswith("extra:")}
    assert extra
    flow.accept("Harrow", extra)
    view = flow.battle()
    assert view.get("active")  # okno walki naziemnej zostaje otwarte
    entry = view["log"][-1]
    assert entry["phase"] == "BOMBARDMENT" and entry["label"] == "Harrow"
    assert not flow.has_offer("Harrow")
    flow.fight()


def _to_harrow_offer(flow: Flow, position: str) -> None:
    for _ in range(12):
        if flow.has_offer("Harrow"):
            return
        view = flow.battle()
        step = view.get("step")
        if not view.get("active") or step in (None, "DONE"):
            pytest.fail("Ground combat ended without a Harrow offer.")
        if step == "ROLL":
            flow.post("/tactical/battle/roll")
        elif step == "ASSIGN":
            flow.assign_auto()
        elif step == "TRIGGERS":
            flow.decline_all()
    pytest.fail("No Harrow offer.")


@ruling("promissory_notes:ambuscade#1")
def test_harrow_ambuscade_dodatkowa_kosc(registry: StaticDataRegistry) -> None:
    """Strike Wing Ambuscade zagrana w oknie przed rzutem Harrow: +1 kość tego rzutu."""
    flow = Flow(registry, "l1z1x", other="argent")

    def note(s: Json) -> None:
        s["players"][flow.other]["private"]["promissory_notes"].remove("ambuscade")
        s["players"][flow.me]["private"]["promissory_notes"].append("ambuscade")

    flow.edit(note)
    position, _ = _ground_combat(flow, attackers=1, defenders=3)

    def dreadnought(s: Json) -> None:
        s["systems"][position]["space_units"][flow.me]["dreadnought"] = 1

    flow.edit(dreadnought)
    _to_harrow_offer(flow, position)
    row = flow.notes_playable(flow.me)["ambuscade"]
    assert row["playable"], row.get("reason")
    flow.play_note(flow.me, "ambuscade")
    offer = flow.offer("Harrow")
    keys = [i["key"] for i in offer["inputs"] if i["key"].startswith("extra:")]
    assert any("ambuscade" in k for k in keys)  # zagrana notka = osobne źródło kości w oknie
    extra = {k: ("auto" if "ambuscade" in k else "none") for k in keys}
    flow.accept("Harrow", extra)  # Plasma Scoring bez kości - zostaje tylko Ambuscade
    entry = flow.battle()["log"][-1]
    roll = entry["rolls"][next(iter(k for k, v in entry["rolls"].items() if v))][0]
    assert len(roll["dice"]) == 2  # pancernik: 1 kość + 1 z Ambuscade
    state = flow.state()
    assert "ambuscade" in state["players"][flow.other]["private"]["promissory_notes"]


@covers("abilities:assimilate", "breakthroughs:l1z1xbt")
def test_assimilate_i_fealty_uplink_po_inwazji(registry: StaticDataRegistry) -> None:
    """Zdobyta planeta z PDS rywala: PDS zostaje wymieniony na PDS L1Z1X, a Fealty Uplink stawia
    piechotę równą wpływowi planety."""
    flow = Flow(registry, "l1z1x")
    flow.player(lambda p: p.update(breakthrough_unlocked=True))
    position, target = _ground_combat(flow, attackers=3, defenders=1)

    def pds(s: Json) -> None:  # PDS dopiero w walce (bez Space Cannon wcześniej w akcji)
        s["systems"][position]["planet_units"][target][flow.other]["pds"] = 1

    flow.edit(pds)
    flow.fight()
    survivors = _planet_units(flow, position, target, flow.me).get("infantry", 0)
    assert survivors > 0, "L1Z1X should win the ground combat with seed 7"
    _win_ground_combat(flow)
    state = flow.state()
    assert state["systems"][position]["planet_owners"][target] == flow.me
    mine = _planet_units(flow, position, target, flow.me)
    assert mine.get("pds") == 1
    assert not _planet_units(flow, position, target, flow.other).get("pds")
    influence = int(registry.planets[target].influence or 0)
    assert mine.get("infantry", 0) == survivors + influence  # ocalała piechota + Fealty Uplink


@covers("leaders:l1z1xagent")
def test_i48s_przy_aktywacji_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "l1z1x")
    position, _ = flow.plain_pair()
    flow.space(position, flow.other, {"carrier": 1, "infantry": 2})
    flow.edit(active=flow.other)
    flow.activate(position)
    flow.accept("I48S")
    offer = flow.offer("replace your infantry", flow.other)
    values = [o["value"] for o in offer["inputs"][0]["options"]]
    assert values == ["space", "none"]
    flow.accept("replace your infantry", {"infantry": "space"}, pid=flow.other)
    state = flow.state()
    assert state["systems"][position]["space_units"][flow.other] == {
        "carrier": 1, "infantry": 1, "mech": 1,
    }
    assert state["players"][flow.me]["leader_states"]["l1z1xagent"] == "exhausted"


@ruling("leaders:l1z1xhero#3")
@covers("leaders:l1z1xhero")
def test_dark_space_navigation_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "l1z1x")
    flow.player(lambda p: p["leader_states"].update(l1z1xhero="unlocked"))
    position, _ = flow.plain_pair()
    flow.space(flow.home, flow.me, {"dreadnought": 2, "infantry": 1, "carrier": 1})
    row = flow.playable()["l1z1xhero"]
    assert row["playable"], row["reason"]
    flow.use("leader", "l1z1xhero", {"moves": [
        f"{flow.home}|dreadnought|0>{position}", f"{flow.home}|dreadnought|1>{position}",
        f"{flow.home}|infantry|0>{position}",
    ]})
    state = flow.state()
    assert state["players"][flow.me]["leader_states"]["l1z1xhero"] == "purged"
    assert state["systems"][position]["space_units"][flow.me] == {"dreadnought": 2, "infantry": 1}


@ruling("promissory_notes:ce#2")
@covers("promissory_notes:ce")
def test_cybernetic_enhancements_w_fazie_statusu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "l1z1x")
    note = flow.give_note("ce", flow.other)
    flow.to_status()
    for pid in flow.state()["seating_order"]:
        flow.post("/status/finish-scoring", {"player_id": pid}, ok=False)
    state = flow.state()
    assert state["status"]["step"] == "REDISTRIBUTE"
    before = int(state["status"]["unassigned_cc"].get(flow.other, 0))
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row.get("reason")
    flow.play_note(flow.other, note)
    state = flow.state()
    assert int(state["status"]["unassigned_cc"][flow.other]) == before + 1
    assert "ce" in state["players"][flow.me]["private"]["promissory_notes"]
