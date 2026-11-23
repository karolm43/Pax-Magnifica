"""The Titans of Ul — scenariusze przez prawdziwe API (dostępność, RULES.md 62.18)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers

VEFUTII = "vefutii"


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _me(flow: Flow) -> Json:
    return flow.state()["players"][flow.me]  # type: ignore[no-any-return]


def _planet_system(flow: Flow, pid: str | None = None) -> tuple[str, str]:
    """Sąsiad domu podmieniony na Vefutii (20) - rzadka mapa nie ma planet poza domami."""
    position = flow.neighbor_of(flow.home)
    flow.set_tile(position, "20")
    if pid is not None:
        flow.ground(position, VEFUTII, pid, {"infantry": 1})
        flow.player(lambda p: p.update(controlled_planets=[*p["controlled_planets"], VEFUTII]),
                    pid=pid)
    return position, VEFUTII


def _sleeper(flow: Flow, position: str, planet: str) -> None:
    def put(s: Json) -> None:
        s["systems"][position]["faction_tokens"] = {planet: {"sleeper": flow.me}}

    flow.edit(put)


def _web(flow: Flow) -> Json:
    return flow.client.get("/api/public/game/g/web-data").json()  # type: ignore[no-any-return]


def _web_player(flow: Flow) -> Json:
    faction = _me(flow)["faction"]
    return next(p for p in _web(flow)["playerData"] if p["faction"] == faction)


@covers("abilities:awaken")
def test_awaken_po_aktywacji_i_zeton_na_mapie(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "titans")
    position, planet = _planet_system(flow, flow.me)
    _sleeper(flow, position, planet)
    entities = _web(flow)["tileUnitData"][position]["planets"][planet]["entities"]
    assert {"entityId": "sleeper", "entityType": "token", "count": 1} in entities["neutral"]
    assert _web_player(flow)["sleeperTokensReinf"] == 4
    flow.activate(position)
    flow.accept("Awaken", {f"sleeper:{planet}": "pds"})
    system = flow.state()["systems"][position]
    assert system["planet_units"][planet][flow.me]["pds"] == 1
    assert system["faction_tokens"] == {}
    assert _web_player(flow)["sleeperTokensReinf"] == 5


@covers("units:titans_flagship")
def test_ouranos_zastepuje_pds(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "titans")
    position, planet = _planet_system(flow)
    flow.ground(position, planet, flow.me, {"pds": 1})
    flow.player(lambda p: p.update(controlled_planets=[*p["controlled_planets"], planet]))
    flow.activate(position)
    flow.accept("Ouranos", {"pds": planet})
    system = flow.state()["systems"][position]
    assert system["space_units"][flow.me] == {"flagship": 1}
    assert "pds" not in system["planet_units"].get(planet, {}).get(flow.me, {})


@covers("abilities:terragenesis")
def test_terragenesis_po_eksploracji(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "titans")
    position, planet = _planet_system(flow)
    flow.space(position, flow.me, {"carrier": 1, "infantry": 2})
    flow.activate(position)
    flow.decline_all()
    flow.to_step("INVASION")
    if flow.state()["invasion"] is None:
        flow.post("/tactical/invasion/begin")
    flow.post("/tactical/invasion/commit", {"commits": [
        {"planet": planet, "baseType": "infantry", "count": 2},
    ]})
    for _ in range(8):
        if flow.state()["exploration"] is not None:
            break
        flow.post("/tactical/invasion/next")
    view: Json = flow.client.get("/exploration").json()
    if view["current"] is None:
        flow.post("/exploration/draw", {"planet": planet})
        view = flow.client.get("/exploration").json()
    for _ in range(4):
        if flow.has_offer("Terragenesis"):
            break
        current = view["current"]
        if current is None:
            break
        option = next(o for o in current["options"] if o.get("enabled", True))
        params = option.get("params") or []
        body: Json = {"option": option["id"]}
        if params:
            body["param"] = params[0]["value"] if isinstance(params[0], dict) else params[0]
        flow.post("/exploration/resolve", body)
        view = flow.client.get("/exploration").json()
    flow.accept("Terragenesis", {"source": "supply"})
    tokens = flow.state()["systems"][position]["faction_tokens"]
    assert tokens == {planet: {"sleeper": flow.me}}


@covers("leaders:titansagent")
def test_tellurian_w_oknie_przypisania_trafien(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "titans")
    flow.space_combat({"dreadnought": 2, "cruiser": 1}, {"cruiser": 3})
    for _ in range(16):
        battle = flow.battle()
        pending = battle.get("required") or {}
        if battle.get("step") == "ASSIGN" and any(int(n) > 0 for n in pending.values()):
            break
        if battle.get("step") == "AFB":
            flow.post("/tactical/battle/afb")
        elif battle.get("step") == "ASSIGN":
            flow.assign_auto()
        else:
            flow.decline_all()
            flow.post("/tactical/battle/roll")
    assert f"{flow.me}:titansagent" in flow.available()
    combat = flow.state()["active_combat"]
    target = next(pid for pid, n in combat["pending_hits"].items() if n > 0)
    before = combat["pending_hits"][target]
    flow.use("leader", "titansagent", {"hit": f"combat:{target}"})
    assert flow.state()["active_combat"]["pending_hits"][target] == before - 1
    assert _me(flow)["leader_states"]["titansagent"] == "exhausted"


@covers("leaders:titanshero")
def test_geoform_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "titans")
    flow.player(lambda p: p["leader_states"].update(titanshero="unlocked"))
    row = flow.playable()["titanshero"]
    assert row["playable"], row["reason"]
    flow.use("leader", "titanshero")
    assert flow.state()["planet_attachments"]["elysium"] == ["titanshero"]
    entities = _web(flow)["tileUnitData"][flow.home]["planets"]["elysium"]["entities"]
    assert {"entityId": "titanshero", "entityType": "attachment", "count": 1} in entities[
        "neutral"
    ]
    assert not flow.playable()["titanshero"]["playable"]


@covers("promissory_notes:terraform")
def test_terraform_zagrany_przez_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "titans")
    position, planet = _planet_system(flow, flow.other)
    note = flow.give_note("terraform", flow.other)
    flow.edit(active=flow.other)
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note, {"planet": planet})
    state = flow.state()
    assert state["planet_attachments"][planet] == ["terraform"]
    assert note not in state["players"][flow.other]["promissory_notes_in_play"]
    assert note not in state["players"][flow.me]["private"]["promissory_notes"]
    del position


@covers("breakthroughs:titansbt")
def test_slumberstate_prosba_i_zgoda(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "titans")
    position, planet = _planet_system(flow, flow.other)
    flow.player(lambda p: p.update(breakthrough_unlocked=True))
    row = flow.playable()["titansbt"]
    assert row["playable"], row["reason"]
    flow.use("breakthrough", "titansbt", {"planet": planet, "source": "supply"})
    flow.accept("Slumberstate", {"answer": "allow"}, pid=flow.other)
    tokens = flow.state()["systems"][position]["faction_tokens"]
    assert tokens == {planet: {"sleeper": flow.me}}
