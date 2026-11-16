"""The Xxcha Kingdom — scenariusze przez prawdziwe API (dostępność dla gracza, RULES.md 62.9)."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json, covers

_CARD = "industrial_initiative"  # karta ACTION bez celów (gain TG za planety przemysłowe)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _with_planet_system(flow: Flow, registry: StaticDataRegistry) -> tuple[str, str]:
    """Sąsiad domu Xxcha dostaje kafel z 1 planetą (rzadka mapa startowa ma tylko domy)."""
    position = flow.neighbor_of(flow.home)
    tile = next(
        sid for sid, s in sorted(registry.systems.items())
        if len(s.planets) == 1 and sid.isdigit() and 19 <= int(sid) <= 30
    )
    flow.set_tile(position, tile)
    return position, registry.systems[tile].planets[0]


def _to_agenda(flow: Flow, deck: list[str]) -> str:
    """Status → agenda z ustaloną talią agend; zwraca mówcę."""
    flow.post("/god-mode/patch", {"custodians_removed": True})
    flow.to_status()
    flow.finish_status()
    service = flow.client.app.state.ctx.service  # type: ignore[attr-defined]
    state = service.current_state().clone()
    assert state.phase.value == "AGENDA"
    state.decks.agenda_deck = list(deck)
    state.decks.agenda_deck_seeded = True
    service.replace_state(state, label="test")
    return str(state.speaker_id)


def _form(flow: Flow, kind: str, component: str) -> Json:
    resp = flow.client.get(
        f"/faction-component/{kind}/{component}/form", params={"player_id": flow.me}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()  # type: ignore[no-any-return]


@covers("abilities:peace_accords")
def test_peace_accords_po_diplomacy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "xxcha")
    position, planet = _with_planet_system(flow, registry)

    def diplomacy(p: Json) -> None:
        p["strategy_cards"] = [2]

    flow.player(diplomacy)
    flow.post("/strategy/play", {"player_id": flow.me, "initiative": 2})
    flow.post("/strategy/primary-step", {"player_id": flow.me, "payload": {"system": flow.home}})
    flow.post("/strategy/primary-step", {"player_id": flow.me, "payload": {"planets": []}})
    offer = flow.offer("Peace Accords")
    values = [o["value"] for o in offer["inputs"][0]["options"]]
    assert f"{position}|{planet}" in values
    flow.accept("Peace Accords", {"planet": f"{position}|{planet}"})
    state = flow.state()
    assert state["systems"][position]["planet_owners"][planet] == flow.me
    assert planet in state["players"][flow.me]["exhausted_planets"]


@covers("abilities:quash")
def test_quash_podmienia_agende(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "xxcha")
    speaker = _to_agenda(flow, ["mutiny", "minister_peace", "minister_war"])
    flow.post("/agenda/reveal", {"player_id": speaker})
    tokens = flow.state()["players"][flow.me]["strategic_cc"]
    assert tokens >= 1
    assert f"{flow.me}:quash" in flow.available()
    flow.use("ability", "quash")
    state = flow.state()
    assert state["agenda"]["agenda_id"] == "minister_peace"
    assert state["players"][flow.me]["strategic_cc"] == tokens - 1


@covers("promissory_notes:favor")
def test_political_favor_u_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "xxcha")
    note = flow.give_note("favor", flow.other)
    speaker = _to_agenda(flow, ["mutiny", "minister_peace", "minister_war"])
    flow.post("/agenda/reveal", {"player_id": speaker})
    tokens = flow.state()["players"][flow.me]["strategic_cc"]
    row = flow.notes_playable(flow.other)[note]
    assert row["playable"], row["reason"]
    flow.play_note(flow.other, note)
    state = flow.state()
    assert state["agenda"]["agenda_id"] == "minister_peace"
    assert state["players"][flow.me]["strategic_cc"] == tokens - 1
    assert note in state["players"][flow.me]["private"]["promissory_notes"]  # wraca do Xxcha


def _instinct(p: Json) -> None:
    p["technologies"].append("it")
    p.update(strategic_cc=2)
    p["private"]["action_cards"] = []  # Xxcha bez kart - i tak może anulować (jawne)


@covers("technologies:it")
def test_instinct_training_anuluje_karte_rywala(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "xxcha")
    flow.player(_instinct)
    flow.other_turn()
    flow.player(lambda p: p["private"].update(action_cards=[_CARD]), flow.other)
    flow.post("/action-card/play", {"player_id": flow.other, "card_id": _CARD, "params": {}})
    held = flow.state()["held_play"]
    assert held is not None and held["card_id"] == _CARD
    assert f"{flow.me}:it" in flow.available()
    flow.use("technology", "it")
    state = flow.state()
    assert state["held_play"] is None
    assert _CARD in state["decks"]["action_card_discard"]
    me = state["players"][flow.me]
    assert "it" in me["exhausted_technologies"] and me["strategic_cc"] == 1
    # Anulowana karta ACTION oddaje akcję tury (F_xxcha) - rywal może zrobić inną akcję.
    assert not state["players"][flow.other]["took_action_this_turn"]


def test_instinct_training_anuluje_sabotage(registry: StaticDataRegistry) -> None:
    """F_xxcha: Instinct Training może anulować Sabotage - karta Xxcha działa mimo Sabotage."""
    flow = Flow(registry, "xxcha")
    flow.player(_instinct)
    flow.player(lambda p: p["private"].update(action_cards=[_CARD]))
    flow.player(lambda p: p["private"].update(action_cards=["sabo1"]), flow.other)
    flow.post("/action-card/play", {"player_id": flow.me, "card_id": _CARD, "params": {}})
    flow.post("/action-card/play", {"player_id": flow.other, "card_id": "sabo1", "params": {}})
    held = flow.state()["held_play"]
    assert held["counter"]["card_id"] == "sabo1"
    flow.use("technology", "it")
    state = flow.state()
    assert state["held_play"]["counter"] is None and state["held_play"]["card_id"] == _CARD
    assert "sabo1" in state["decks"]["action_card_discard"]
    flow.finish_hold()
    state = flow.state()
    assert state["held_play"] is None
    assert _CARD in state["decks"]["action_card_discard"]  # rozstrzygnięta zwykłą ścieżką


@covers("technologies:nf")
def test_nullification_field_konczy_ture(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "xxcha")
    def nullification(p: Json) -> None:
        p["technologies"].append("nf")
        p.update(strategic_cc=2)

    flow.player(nullification)
    flow.other_turn()
    _, target = flow.plain_pair()
    flow.space(target, flow.me, {"cruiser": 1})
    flow.post("/tactical/activate", {"position": target})
    flow.accept("Nullification Field")
    state = flow.state()
    assert state["tactical_step"] is None and state["active_system"] is None
    assert state["active_player_id"] == flow.me  # tura rywala skończona
    assert "nf" in state["players"][flow.me]["exhausted_technologies"]


@covers("leaders:xxchaagent")
def test_ggrocuto_rinn_odnawia_planete(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "xxcha")
    planet = flow.planets(flow.home)[0]
    flow.player(lambda p: p.update(exhausted_planets=[planet]))
    assert flow.playable()["xxchaagent"]["playable"], flow.playable()["xxchaagent"]["reason"]
    values = [o["value"] for o in _form(flow, "leader", "xxchaagent")["inputs"][0]["options"]]
    removal = next(v for v in values if v.startswith(f"{flow.home}|{planet}|") and
                   not v.endswith("|none"))
    infantry = flow.state()["systems"][flow.home]["planet_units"][planet][flow.me]["infantry"]
    flow.use("leader", "xxchaagent", {"planet": removal})
    state = flow.state()
    assert planet not in state["players"][flow.me]["exhausted_planets"]
    units = state["systems"][flow.home]["planet_units"][planet][flow.me]
    assert units.get("infantry", 0) == infantry - 1
    assert state["players"][flow.me]["leader_states"]["xxchaagent"] == "exhausted"


@covers("leaders:xxchahero-te")
def test_xxekir_grom_stawia_pds_i_mechy(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "xxcha")
    planets = flow.planets(flow.home)
    def hero(p: Json) -> None:
        p["leader_states"]["xxchahero-te"] = "unlocked"
        p["exhausted_planets"] = list(planets)

    flow.player(hero)
    assert flow.playable()["xxchahero-te"]["playable"]
    options = [o["value"] for o in _form(flow, "leader", "xxchahero-te")["inputs"][0]["options"]]
    mech = next(v for v in options if v.startswith(f"mech|{planets[0]}|"))
    pds = next(v for v in options if v.startswith(f"pds|{planets[0]}|"))
    before = flow.state()["systems"][flow.home]["planet_units"][planets[0]][flow.me]
    flow.use("leader", "xxchahero-te", {"units": [mech, pds]})
    state = flow.state()
    after = state["systems"][flow.home]["planet_units"][planets[0]][flow.me]
    assert after.get("mech", 0) == before.get("mech", 0) + 1
    assert after.get("pds", 0) == before.get("pds", 0) + 1
    exhausted = state["players"][flow.me]["exhausted_planets"]
    assert planets[0] not in exhausted and all(p in exhausted for p in planets[1:])
    assert state["players"][flow.me]["leader_states"]["xxchahero-te"] == "purged"
