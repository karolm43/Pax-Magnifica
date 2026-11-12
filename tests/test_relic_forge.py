"""Fragmenty reliktów -> relikt (RULES.md 59.7) i jawne odsłonięcie reliktu (RULES.md 59.8)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import relic_forge, relics
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from tests.test_relics import _grid, _state

# Fixture autouse z test_relics (graf mapy demo) - import wystarcza, by pytest ją widział.
__all__ = ["_grid"]


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _with_fragments(registry: StaticDataRegistry, fragments: list[str]) -> GameState:
    state = _state(registry, [])
    state.players["p1"].relic_fragments = list(fragments)
    return state


def test_fragment_rules_come_from_card_text(registry: StaticDataRegistry) -> None:
    cultural = relic_forge.fragment_rule(registry, "crf1")
    assert (cultural.kind, cultural.needed, cultural.relics) == ("cultural", 3, 1)
    assert relic_forge.fragment_rule(registry, "hrf1").kind == "hazardous"
    assert relic_forge.fragment_rule(registry, "irf1").kind == "industrial"
    unknown = relic_forge.fragment_rule(registry, "urf1")
    assert unknown.wildcard and unknown.kind is None


def test_forge_purges_three_and_reveals_relic(registry: StaticDataRegistry) -> None:
    state = _with_fragments(registry, ["crf1", "crf2", "crf3", "hrf1"])
    new_state = relic_forge.forge(state, registry, "p1", ["crf1", "crf2", "crf3"])
    me = new_state.players["p1"]
    assert me.relic_fragments == ["hrf1"]
    assert len(me.relics) == 1
    assert me.took_action_this_turn
    assert {"crf1", "crf2", "crf3"} <= set(new_state.decks.purged)
    reveal = new_state.relic_reveal
    assert reveal is not None
    assert reveal["source"] == "fragments" and reveal["relicId"] == me.relics[0]
    assert reveal["fragments"] == ["crf1", "crf2", "crf3"] and reveal["kind"] == "cultural"
    assert reveal["seq"] == new_state.relic_reveal_seq == state.relic_reveal_seq + 1
    # Oryginał nietknięty (funkcja czysta).
    assert state.players["p1"].relic_fragments == ["crf1", "crf2", "crf3", "hrf1"]


def test_unknown_fragment_is_a_wildcard_but_not_alone(registry: StaticDataRegistry) -> None:
    state = _with_fragments(registry, ["crf1", "urf1", "urf2", "urf3"])
    new_state = relic_forge.forge(state, registry, "p1", ["crf1", "urf1", "urf2"])
    assert new_state.players["p1"].relic_fragments == ["urf3"]
    with pytest.raises(ValueError, match="At least one"):
        relic_forge.forge(state, registry, "p1", ["urf1", "urf2", "urf3"])


@pytest.mark.parametrize(
    ("chosen", "message"),
    [
        (["crf1", "crf2"], "exactly 3"),
        (["crf1", "crf2", "hrf1"], "same type"),
        (["crf1", "crf2", "crf9"], "do not have"),
    ],
)
def test_forge_rejects_bad_sets(
    registry: StaticDataRegistry, chosen: list[str], message: str
) -> None:
    state = _with_fragments(registry, ["crf1", "crf2", "hrf1"])
    with pytest.raises(ValueError, match=message):
        relic_forge.forge(state, registry, "p1", chosen)


def test_forge_is_an_action_on_own_turn(registry: StaticDataRegistry) -> None:
    state = _with_fragments(registry, ["crf1", "crf2", "crf3"])
    state.players["p2"].relic_fragments = ["hrf1", "hrf2", "hrf3"]
    with pytest.raises(ValueError, match="turn"):
        relic_forge.forge(state, registry, "p2", ["hrf1", "hrf2", "hrf3"])
    state.players["p1"].took_action_this_turn = True
    with pytest.raises(ValueError):
        relic_forge.forge(state, registry, "p1", ["crf1", "crf2", "crf3"])


def test_empty_relic_deck_still_purges(registry: StaticDataRegistry) -> None:
    state = _with_fragments(registry, ["irf1", "irf2", "irf3"])
    relics.ensure_relic_deck(state, registry)
    state.decks.relic_deck = []
    state.decks.relic_discard = []
    assert relic_forge.options(state, registry, "p1")[0]["deckEmpty"] is True
    new_state = relic_forge.forge(state, registry, "p1", ["irf1", "irf2", "irf3"])
    assert new_state.players["p1"].relics == []
    assert new_state.players["p1"].relic_fragments == []
    assert new_state.relic_reveal is not None and new_state.relic_reveal["relicId"] is None


def test_options_pick_own_type_first_and_explain_blockers(registry: StaticDataRegistry) -> None:
    state = _with_fragments(registry, ["urf1", "crf1", "crf2", "crf3", "hrf1"])
    rows = {row["kind"]: row for row in relic_forge.options(state, registry, "p1")}
    assert rows["cultural"]["fragments"] == ["crf1", "crf2", "crf3"]
    assert rows["cultural"]["reason"] is None
    assert rows["hazardous"]["fragments"] == []
    assert "3 hazardous" in rows["hazardous"]["reason"]
    state.active_player_id = "p2"
    rows = {row["kind"]: row for row in relic_forge.options(state, registry, "p1")}
    assert rows["cultural"]["reason"] is not None


def test_forge_endpoints(registry: StaticDataRegistry) -> None:
    state = _with_fragments(registry, ["hrf1", "hrf2", "urf1"])
    client = TestClient(
        create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    )
    options = client.get("/relic/forge/options", params={"player_id": "p1"}).json()["options"]
    assert options[0]["kind"] == "hazardous" and options[0]["deckEmpty"] is False
    chosen = options[0]["fragments"]
    assert sorted(chosen) == ["hrf1", "hrf2", "urf1"]
    denied = client.post(
        "/relic/forge", json={"player_id": "p1", "fragments": chosen},
        headers={"X-Actor-Id": "p2"},
    )
    assert denied.status_code in (403, 422)
    resp = client.post(
        "/relic/forge", json={"player_id": "p1", "fragments": chosen},
        headers={"X-Actor-Id": "p1"},
    )
    assert resp.status_code == 200, resp.text
    relic = resp.json()["relic_id"]
    assert relic
    me = client.get("/state").json()["state"]["players"]["p1"]
    assert me["relics"] == [relic] and me["relic_fragments"] == []
    web = client.get("/api/public/game/pax/web-data").json()
    assert web["gameState"]["relicReveal"]["relicId"] == relic
