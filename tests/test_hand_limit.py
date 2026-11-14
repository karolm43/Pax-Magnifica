"""Limit ręki kart akcji (R_action_cards, RULES.md 53.8) — przez prawdziwe API."""

from __future__ import annotations

import pytest

from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import Flow, Json


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _over_limit(registry: StaticDataRegistry) -> tuple[Flow, list[str]]:
    """Hacan ma 7 kart, partner oddaje mu 1 w transakcji (Arbiters) — 8 kart na ręce."""
    flow = Flow(registry, "hacan")
    deck = list(flow.state()["decks"]["action_card_deck"])
    mine, given = deck[:7], deck[7]

    def hands(s: Json) -> None:
        s["players"][flow.me]["private"]["action_cards"] = list(mine)
        s["players"][flow.other]["private"]["action_cards"] = [given]

    flow.edit(hands)
    flow.transact(receive={"action_cards": [given]})
    hand = flow.state()["players"][flow.me]["private"]["action_cards"]
    assert len(hand) == 8
    return flow, hand


def test_nadwyzka_blokuje_ture_i_zagrywanie(registry: StaticDataRegistry) -> None:
    flow, hand = _over_limit(registry)
    view = flow.client.get("/action-card/playable", params={"player_id": flow.me}).json()
    assert view["discard"] == 1 and view["handLimit"] == 7
    assert all(not row["playable"] and "discard" in row["reason"] for row in view["cards"])
    resp = flow.post("/turn/end", {"player_id": flow.me}, ok=False)
    assert resp.status_code == 422 and "discard" in resp.text
    # Nadwyżki nie wolno oddać w transakcji (R_action_cards: „cannot trade them”).
    resp = flow.transact(give={"action_cards": [hand[0]]}, ok=False)
    assert resp.status_code == 422


def test_odrzucenie_wybranej_karty_zdejmuje_blokade(registry: StaticDataRegistry) -> None:
    flow, hand = _over_limit(registry)
    chosen = hand[3]
    flow.post("/action-card/discard-excess", {"actor_id": flow.me, "card_id": chosen})
    state = flow.state()
    assert len(state["players"][flow.me]["private"]["action_cards"]) == 7
    assert chosen in state["decks"]["action_card_discard"]
    # Drugie odrzucenie — już w limicie.
    resp = flow.post(
        "/action-card/discard-excess", {"actor_id": flow.me, "card_id": hand[0]}, ok=False
    )
    assert resp.status_code == 422
    view = flow.client.get("/action-card/playable", params={"player_id": flow.me}).json()
    assert view["discard"] == 0
