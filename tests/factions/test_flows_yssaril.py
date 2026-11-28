"""The Yssaril Tribes — scenarios through the real API (availability, RULES.md 62.22)."""

from __future__ import annotations

import pytest

from src.core.components import ComponentCategory
from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _me(flow: Flow, pid: str | None = None) -> Json:
    return flow.state()["players"][pid or flow.me]  # type: ignore[no-any-return]


def _cards(registry: StaticDataRegistry, count: int, skip: int = 0) -> list[str]:
    return sorted(registry.catalog.all(ComponentCategory.ACTION_CARD))[skip:skip + count]


def _hand(flow: Flow, pid: str | None = None) -> list[str]:
    return list(_me(flow, pid)["private"]["action_cards"])


def _give(flow: Flow, pid: str, cards: list[str]) -> None:
    """Puts ``cards`` in the hand and takes them out of the action card deck (no re-draws)."""
    flow.player(lambda p: p["private"].__setitem__("action_cards", list(cards)), pid)
    service = flow.client.app.state.ctx.service  # type: ignore[attr-defined]
    state = service.current_state().clone()
    state.decks.action_card_deck = [c for c in state.decks.action_card_deck if c not in cards]
    service.replace_state(state, label="test")


def _facts(flow: Flow) -> list[Json]:
    entries = flow.client.get("/history/activity").json()["entries"]
    return [f for e in entries for f in e["activity"]["facts"]]


def _notes(flow: Flow) -> list[str]:
    return [str(f.get("detail") or "") for f in _facts(flow) if f["type"] == "ability_used"]


@covers("abilities:stall_tactics", "units:yssaril_mech")
def test_stall_tactics_i_blackshade_deploy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yssaril")
    cards = _cards(registry, 2)
    _give(flow, flow.me, cards)
    row = flow.playable()["stall_tactics"]
    assert row["playable"]
    flow.use("ability", "stall_tactics", {"card": cards[0]})
    assert _hand(flow) == [cards[1]]
    offer = flow.offer("Blackshade")
    planet = offer["inputs"][0]
    assert "auto" not in planet
    target = planet["options"][0]["value"]
    assert target in flow.planets(flow.home)
    flow.accept("Blackshade", {"planet": target})
    units = flow.state()["systems"][flow.home]["planet_units"][target][flow.me]
    assert units.get("mech") == 1


def test_scheming_w_fazie_statusu(registry: StaticDataRegistry) -> None:
    """Status-phase draw: 1 card + 1 (Scheming), then the mandatory discard of any card."""
    flow = Flow(registry, "yssaril")
    held = _cards(registry, 1, skip=30)
    _give(flow, flow.me, held)
    flow.to_status()
    for pid in flow.state()["seating_order"]:
        flow.post("/status/finish-scoring", {"player_id": pid}, ok=False)
    decision = flow.offer("Scheming")
    assert decision["mandatory"]
    hand = _hand(flow)
    assert len(hand) == 1 + 2 + 1  # held + 2 drawn (Neural Motivator start tech) + 1 additional
    assert {o["value"] for o in decision["inputs"][0]["options"]} == set(hand)
    flow.accept("Scheming", {"card": held[0]})
    assert len(_hand(flow)) == 3 and held[0] not in _hand(flow)


def test_mageon_implants_akcja_i_wybor(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yssaril")
    theirs = _cards(registry, 3)
    _give(flow, flow.other, theirs)
    flow.player(lambda p: p["technologies"].append("mi"))
    flow.post("/tactical/component-action", {
        "player_id": flow.me, "component_id": "mi", "params": {"player": flow.other},
    })
    decision = flow.offer("Mageon Implants")
    assert decision["mandatory"]
    assert {o["value"] for o in decision["inputs"][0]["options"]} == set(theirs)
    # The rival does not see the decision's content.
    rival_view = flow.client.get("/offers", params={"player_id": flow.other}).json()["offers"]
    assert not any("Mageon" in o["label"] for o in rival_view)
    flow.accept("Mageon Implants", {"card": theirs[1]})
    assert _hand(flow) == [theirs[1]]
    assert "mi" in _me(flow)["exhausted_technologies"]
    assert any("looks at" in n for n in _notes(flow))


def test_ssruu_uzywa_agenta_hacan(registry: StaticDataRegistry) -> None:
    """Ssruu has the text of the Hacan agent: the Yssaril uses Carth of Golden Sands."""
    flow = Flow(registry, "yssaril", "hacan")
    flow.player(lambda p: p["leader_states"].update(hacanagent="exhausted"), flow.other)
    assert flow.playable()["hacanagent"]["playable"]  # even if that agent is exhausted
    flow.use("leader", "hacanagent", {"target": "self"})
    me = _me(flow)
    assert me["commodities"] == 2
    assert me["leader_states"]["yssarilagent"] == "exhausted"
    assert not flow.playable()["hacanagent"]["playable"]  # Ssruu is spent


@covers("leaders:yssarilcommander")
def test_so_ata_po_aktywacji_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yssaril")
    away, _ = flow.plain_pair()
    flow.player(lambda p: p["leader_states"].update(yssarilcommander="unlocked"))
    theirs = _cards(registry, 2)
    _give(flow, flow.other, theirs)
    flow.space(away, flow.me, {"destroyer": 1})
    flow.other_turn()
    flow.activate(away)  # the rival (active) activates the system with the Yssaril's ship
    offer = flow.offer("So Ata")
    assert "auto" not in offer["inputs"][0]
    flow.accept("So Ata", {"hand": "action_cards"})
    look = flow.offer("So Ata")
    assert look["mandatory"]
    seen = look["inputs"][0]
    assert seen["kind"] == "info" and {o["value"] for o in seen["options"]} == set(theirs)
    flow.accept("So Ata", {"done": "done"})
    assert _hand(flow, flow.other) == theirs


@covers("leaders:yssarilhero")
def test_kyver_guild_of_spies(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yssaril")
    flow.player(lambda p: p["leader_states"].update(yssarilhero="unlocked"))
    theirs = _cards(registry, 4)
    _give(flow, flow.other, theirs)
    assert flow.playable()["yssarilhero"]["playable"]
    flow.use("leader", "yssarilhero")
    assert _me(flow)["leader_states"]["yssarilhero"] == "purged"
    show = flow.offer("show 1 action card", flow.other)
    assert show["mandatory"]
    flow.accept("show 1 action card", {"card": theirs[2]}, pid=flow.other)
    choose = flow.offer("take the card")
    assert "auto" not in choose["inputs"][1]
    flow.accept("take the card", {"choice": "take"})
    assert theirs[2] in _hand(flow)
    assert len(_hand(flow, flow.other)) == 3
    areas = [f for f in _facts(flow) if f["type"] == "area" and f.get("detail") == "kyver"]
    assert {f["value"] for f in areas} == {flow.other_home}


@covers("promissory_notes:spynet")
def test_spy_net_na_poczatku_tury_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yssaril")
    mine = _cards(registry, 3)
    _give(flow, flow.me, mine)
    note = flow.give_note("spynet", flow.other)
    flow.other_turn()  # the rival's turn starts: the "start of your turn" window
    assert flow.notes_playable(flow.other)[note]["playable"]
    flow.play_note(flow.other, note)
    pick = flow.offer("Spy Net", flow.other)
    assert pick["mandatory"]
    assert {o["value"] for o in pick["inputs"][0]["options"]} == set(mine)
    flow.accept("Spy Net", {"card": mine[0]}, pid=flow.other)
    assert _hand(flow, flow.other) == [mine[0]]
    assert note in _me(flow)["private"]["promissory_notes"]  # back with the Yssaril


@covers("breakthroughs:yssarilbt")
def test_deepgloom_pozycza_stall_tactics(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "yssaril")
    flow.player(lambda p: p.__setitem__("breakthrough_unlocked", True))
    assert f"{flow.me}:yssarilbt" in flow.available()
    flow.use("breakthrough", "yssarilbt", {"player": flow.other})
    card = _cards(registry, 1)
    _give(flow, flow.other, card)
    flow.other_turn()
    assert flow.playable(flow.other)["stall_tactics"]["playable"]
    flow.use("ability", "stall_tactics", {"card": card[0]}, pid=flow.other)
    assert _hand(flow, flow.other) == []
    assert not flow.has_offer("Blackshade")  # not the Yssaril's own use
    assert "stall_tactics" not in flow.playable(flow.other)


def test_ssruu_kopiuje_jr_xs455_o_przez_api(registry: StaticDataRegistry) -> None:
    """Another player's JR-XS455-O shows up in the Yssaril's Relics tab (Ssruu, C_relics jrxs455o
    1.2) and is played through the relic endpoint; Ssruu is exhausted, the relic stays."""
    flow = Flow(registry, "yssaril", "hacan")
    flow.player(lambda p: p["relics"].append("titanprototype"), flow.other)

    def rows() -> dict[str, Json]:
        found = flow.client.get("/relic/playable", params={"player_id": flow.me}).json()
        return {r["relic_id"]: r for r in found["relics"]}

    row = rows()["titanprototype"]
    assert row["playable"] and row["copied_by"] == "yssarilagent"
    form = flow.client.get("/relic/titanprototype/inputs", params={"player_id": flow.me})
    assert form.status_code == 200 and form.json()["copied_by"] == "yssarilagent"
    tg = _me(flow)["trade_goods"]
    flow.post("/relic/play", {"player_id": flow.me, "actor_id": flow.me,
                              "relic_id": "titanprototype",
                              "params": {"player": flow.me, "placement": "none"}})
    me = _me(flow)
    assert me["trade_goods"] == tg + 1
    assert me["leader_states"]["yssarilagent"] == "exhausted"
    assert "titanprototype" not in _me(flow, flow.other)["exhausted_relics"]
    assert rows()["titanprototype"]["exhausted"]


def test_ssruu_copy_of_tro_places_infantry_once(registry: StaticDataRegistry) -> None:
    """Ssruu copying T'ro, requested by the active player: the Yssaril and the Sardakk both hold
    T'ro's text, but one exhaust grants a single "place 2 infantry" decision (RULES.md 62.22)."""
    flow = Flow(registry, "sol", other="yssaril", third="sardakk")
    flow.activate(flow.home)
    flow.decline_all()
    flow.pass_reactions()
    flow.end_turn()
    owners = [b["owner"] for b in flow.boosts() if "T'ro" in b["name"]]
    assert owners[0] == flow.other  # the Yssaril's Ssruu copy is listed first
    flow.request_boost("T'ro")
    flow.accept("T'ro", pid=flow.other)
    assert _me(flow, flow.other)["leader_states"].get("yssarilagent") == "exhausted"
    assert _me(flow, flow.third)["leader_states"].get("sardakkagent") != "exhausted"
    decisions = [o for o in flow.offers() if "place 2 infantry" in o["label"]]
    assert len(decisions) == 1
    planet = flow.planets(flow.home)[0]
    before = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]["infantry"]
    flow.accept(decisions[0]["label"], {"planet": planet})
    after = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]["infantry"]
    assert after == before + 2
    assert not [o for o in flow.offers() if "place 2 infantry" in o["label"]]
