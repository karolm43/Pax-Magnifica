"""The Embers of Muaat — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.13)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _space(flow: Flow, position: str, pid: str | None = None) -> dict[str, int]:
    return dict(flow.state()["systems"][position]["space_units"].get(pid or flow.me, {}))


@covers("abilities:star_forge", "units:muaat_mech")
def test_star_forge_i_ember_colossus(registry: StaticDataRegistry) -> None:
    """War sun startowy w domu: Star Forge stawia niszczyciel, mech w domu dokłada piechotę."""
    flow = Flow(registry, "muaat")
    planet = flow.planets(flow.home)[0]
    flow.ground(flow.home, planet, flow.me, {"mech": 1, "infantry": 1})
    flow.player(lambda p: p.update(strategic_cc=2))
    row = flow.playable()["star_forge"]
    assert row["playable"], row["reason"]
    before = _space(flow, flow.home).get("destroyer", 0)
    flow.use("ability", "star_forge", {"position": flow.home, "unit": "destroyer"})
    assert _space(flow, flow.home)["destroyer"] == before + 1
    assert flow.state()["players"][flow.me]["strategic_cc"] == 1
    offer = flow.offer("Ember Colossus")
    mech = offer["inputs"][0]["options"][0]["value"]
    flow.accept("Ember Colossus", {"mechs": [mech]})
    units = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]
    assert units == {"mech": 1, "infantry": 2}


def test_the_inferno_akcja_flagowca(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "muaat")
    position, _ = flow.plain_pair()
    flow.space(position, flow.me, {"flagship": 1})
    flow.player(lambda p: p.update(strategic_cc=1))
    row = flow.playable()["muaat_flagship"]
    assert row["playable"], row["reason"]
    flow.use("unit", "muaat_flagship")
    assert _space(flow, position) == {"flagship": 1, "cruiser": 1}


@covers("leaders:muaatcommander")
def test_magmus_po_wydaniu_zetonu(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "muaat")
    flow.player(lambda p: p.update(strategic_cc=1, trade_goods=0))
    flow.player(lambda p: p["leader_states"].update(muaatcommander="unlocked"))
    flow.use("ability", "star_forge", {"position": flow.home, "unit": "fighters"})
    flow.accept("Magmus")
    assert flow.state()["players"][flow.me]["trade_goods"] == 1


def test_magmus_odblokowanie_przez_produkcje_war_suna(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "muaat")
    flow.player(lambda p: p.update(trade_goods=20))
    flow.activate(flow.home)
    flow.to_step("PRODUCTION")
    flow.post("/tactical/produce", {"faction": flow.me, "orders": [
        {"baseType": "warsun", "count": 1, "zone": "space"},
    ]})
    assert flow.state()["players"][flow.me]["leader_states"]["muaatcommander"] == "unlocked"


@covers("leaders:muaatagent")
def test_umbat_rywal_produkuje(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "muaat")
    position, _ = flow.plain_pair()
    flow.space(position, flow.other, {"flagship": 1})
    flow.player(lambda p: p.update(trade_goods=6), flow.other)
    flow.use("leader", "muaatagent", {"player": flow.other})
    flow.accept("Umbat", {"position": position}, pid=flow.other)
    grant = flow.state()["production_grant"]
    assert grant["player_id"] == flow.other and grant["units"] == 2
    flow.post("/tactical/produce", {"faction": flow.other, "orders": [
        {"baseType": "cruiser", "count": 2, "zone": "space"},
    ]})
    assert _space(flow, position, flow.other)["cruiser"] == 2


@covers("leaders:muaathero")
def test_nova_seed_po_ruchu_war_suna(registry: StaticDataRegistry) -> None:
    """War sun wlatuje do systemu rywala: Nova Seed niszczy jego jednostki, kafel -> supernowa
    (mapa, web-data i feed Activity widzą nowy kafel)."""
    flow = Flow(registry, "muaat")
    flow.player(lambda p: p["leader_states"].update(muaathero="unlocked"))
    start, target = flow.plain_pair()
    flow.space(start, flow.me, {"warsun": 1})
    flow.space(target, flow.other, {"destroyer": 1})
    flow.activate(target)
    flow.decline_all()
    flow.to_step("MOVEMENT")
    flow.move(start, target, {"warsun": 1})
    flow.accept("Nova Seed")
    state = flow.state()
    system = state["systems"][target]
    assert system["system_id"] == "81" and state["replaced_tiles"] == {target: "81"}
    assert not system["space_units"].get(flow.other)
    assert state["players"][flow.me]["leader_states"]["muaathero"] == "purged"
    data: Json = flow.client.get("/api/public/game/g/web-data").json()
    assert f"{target}:81" in data["tilePositions"]
    feed = flow.client.get("/history/activity").json()["entries"]
    facts = [f for e in feed for f in e["activity"]["facts"] if f["type"] == "tile_replaced"]
    assert facts and facts[-1]["value"] == target


@covers("promissory_notes:fires")
def test_fires_of_the_gashlai_przez_api(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "muaat")
    note = flow.give_note("fires", flow.other)
    flow.player(lambda p: p.update(fleet_cc=3))
    flow.edit(active=flow.other)
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row.get("reason")
    flow.play_note(flow.other, note)
    state = flow.state()
    assert "ws" in state["players"][flow.other]["technologies"]
    assert state["players"][flow.me]["fleet_cc"] == 2
    assert "fires" in state["players"][flow.me]["private"]["promissory_notes"]


@covers("breakthroughs:muaatbt")
def test_stellar_genesis_z_edytora(registry: StaticDataRegistry) -> None:
    """Przełom z edytora = „gain”: Avernus kładzie się klikiem na mapie (kilka systemów obok
    planet gracza - druga planeta poza domem)."""
    flow = Flow(registry, "muaat")
    planet = next(p for pos in sorted(flow.state()["systems"]) if pos != flow.home
                  for p in flow.planets(pos))
    owned = [*flow.state()["players"][flow.me]["controlled_planets"], planet]
    flow.post(f"/player/{flow.me}/edit", {"controlled_planets": owned})
    flow.post(f"/player/{flow.me}/edit", {"breakthrough_unlocked": True})
    offer = flow.offer("Stellar Genesis")
    assert len(offer["inputs"][0]["options"]) > 1
    position = offer["inputs"][0]["options"][0]["value"]
    flow.accept("Stellar Genesis", {"position": position})
    state = flow.state()
    assert "avernus" in state["systems"][position]["added_planets"]
    assert "avernus" in state["players"][flow.me]["controlled_planets"]
    # Żeton planety widać na mapie (przestrzeń systemu, jak Mirage).
    data: Json = flow.client.get("/api/public/game/g/web-data").json()
    tokens = data["tileUnitData"][position]["space"].get("neutral", [])
    assert {"entityId": "avernus", "entityType": "token", "count": 1} in tokens


@covers("breakthroughs:muaatbt")
def test_stellar_genesis_system_z_planetami(registry: StaticDataRegistry) -> None:
    """Kandydaci z mapy gry: także system z planetami bez wpisu stanu (bez jednostek i żetonów)
    — wcześniej znikały i zostawały tylko puste systemy (z żetonem frontier)."""
    flow = Flow(registry, "muaat")
    flow.post(f"/player/{flow.me}/edit", {"breakthrough_unlocked": True})
    offer = flow.offer("Stellar Genesis")
    data: Json = flow.client.get("/api/public/game/g/web-data").json()
    with_planets = [
        o["value"] for o in offer["inputs"][0]["options"]
        if o["value"] not in flow.state()["systems"] and data["tileUnitData"].get(o["value"])
    ]
    assert with_planets, offer["inputs"][0]["options"]
    target = with_planets[0]
    assert "no planets" not in next(
        o["label"] for o in offer["inputs"][0]["options"] if o["value"] == target
    )
    flow.accept("Stellar Genesis", {"position": target})
    assert "avernus" in flow.state()["systems"][target]["added_planets"]
