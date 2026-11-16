"""Scenariusz przez prawdziwe API: efekty agend w oknie Rady (RULES.md 51.6).

Decyzja z efektu agendy sama wyskakuje graczowi (oferta obowiązkowa), mówca nie przejdzie dalej
bez niej, a rider jest jawny w web-data (na jaki wynik go zagrano).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _to_agenda(flow: Flow, deck: list[str], hand: dict[str, list[str]]) -> str:
    """Status → agenda z ustaloną talią agend i kartami w rękach; zwraca mówcę."""
    flow.post("/god-mode/patch", {"custodians_removed": True})
    flow.to_status()
    flow.finish_status()
    service = flow.client.app.state.ctx.service  # type: ignore[attr-defined]
    state = service.current_state().clone()
    assert state.phase.value == "AGENDA"
    state.decks.agenda_deck = list(deck)
    state.decks.agenda_deck_seeded = True
    for pid, cards in hand.items():
        state.players[pid].private.action_cards = list(cards)
    service.replace_state(state, label="test")
    return str(state.speaker_id)


def _agenda(flow: Flow) -> Any:
    data = flow.client.get("/api/public/game/test/web-data").json()
    return data["gameState"]["agendaPhase"]


def _abstain_all(flow: Flow) -> None:
    for _ in range(4):
        voter = flow.state()["agenda"]
        current = [p for p in voter["vote_order"]
                   if p not in voter["votes"] and p not in voter["abstained"]
                   and p not in voter["blocked"]]
        if not current or voter["step"] != "VOTE":
            return
        flow.post("/agenda/abstain", {"player_id": current[0]})


def test_decyzja_z_agendy_i_jawny_rider(registry: StaticDataRegistry) -> None:
    flow = Flow(registry, "hacan")
    speaker = _to_agenda(flow, ["grant_reallocation", "mutiny"], {flow.other: ["trade_rider"]})
    flow.post("/agenda/reveal", {"player_id": speaker})
    flow.post("/action-card/play", {
        "player_id": flow.other, "card_id": "trade_rider", "params": {"outcome": flow.me},
    })
    held = flow.state().get("held_play")
    if held:  # okno Sabotage: pozostali pasują
        flow.post("/action-card/held/pass", {"actor_id": flow.me})
    predictions = _agenda(flow)["predictions"]
    assert [(p["playerId"], p["card"], p["outcome"]) for p in predictions] == [
        (flow.other, "trade_rider", flow.me)
    ]
    _abstain_all(flow)
    flow.post("/agenda/decide", {"player_id": speaker, "outcome": flow.me})
    if flow.state()["agenda"]["step"] == "COUNTED":
        flow.post("/agenda/confirm", {"player_id": speaker})
    assert flow.state()["agenda"]["resolved_outcome"] == flow.me
    # Research Grant Reallocation: wybrany sam dostaje decyzję (którą technologię zdobyć).
    offer = flow.offer("Research Grant Reallocation")
    assert offer["mandatory"]
    flow.post("/agenda/continue", {"player_id": speaker}, ok=False)
    assert flow.state()["agenda"]["step"] == "RESOLVED"  # mówca czeka na decyzję
    field = offer["inputs"][0]
    assert field["kind"] == "research"  # pełne okno drzewa technologii, nie lista
    tech = next(r["id"] for r in field["research"]["tree"] if r["status"] == "available")
    flow.accept("Research Grant Reallocation", {"research": {"tech": tech}})
    state = flow.state()
    assert tech in state["players"][flow.me]["technologies"]
    assert state["players"][flow.other]["trade_goods"] >= 5  # trafiony Trade Rider
    flow.post("/agenda/continue", {"player_id": speaker})
    assert flow.state()["agenda"]["step"] == "REVEAL"


def test_web_data_limit_kart_akcji_dla_panelu_dowodcy(registry: StaticDataRegistry) -> None:
    """Panel dowódcy czyta limit kart akcji z silnika (nie zgaduje „7”)."""
    flow = Flow(registry, "hacan")
    data = flow.client.get("/api/public/game/test/web-data").json()
    limits = {p["discordId"]: p["actionCardLimit"] for p in data["playerData"] if p.get("faction")}
    expected = registry.hand_limits().action_cards
    assert limits and set(limits.values()) == {expected}
