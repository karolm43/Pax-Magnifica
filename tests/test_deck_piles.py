"""Testy stosów kart (talia / odrzucone / purge) i debugowego przenoszenia kart."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import deck_piles, exploration
from src.core.event_store import EventStore
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from tests.test_exploration import _CULT, _card_id, _state, _with_card


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def test_unseeded_deck_is_full_and_drawn_card_leaves_it(registry: StaticDataRegistry) -> None:
    state = _state()
    full = deck_piles.explore_piles(state, registry, "cultural")
    assert len(full.deck) == 20 and full.discard == []
    drawn = exploration.begin_exploration(state, registry, "p1", "000", [_CULT])
    assert drawn.exploration is not None and drawn.exploration.current is not None
    card = drawn.exploration.current.card_id
    piles = deck_piles.explore_piles(drawn, registry, "cultural")
    assert len(piles.deck) == 19 and card not in piles.deck


def test_resolved_card_goes_to_discard_and_purged_to_purge_pile(
    registry: StaticDataRegistry,
) -> None:
    done = exploration.resolve(
        _with_card(_state(planets={_CULT: {"infantry": 1}}), registry, "Mercenary Outfit"),
        registry,
        "place_infantry",
    )
    assert deck_piles.explore_piles(done, registry, "cultural").discard == [
        _card_id(registry, "Mercenary Outfit")
    ]
    gamma = exploration.resolve(_with_card(_state(), registry, "Gamma Wormhole"), registry, "place")
    assert gamma.decks.purged == [_card_id(registry, "Gamma Wormhole")]
    assert deck_piles.explore_piles(gamma, registry, "cultural").discard == []


def test_move_card_sets_the_next_exploration(registry: StaticDataRegistry) -> None:
    wanted = _card_id(registry, "Core Mine")
    state = deck_piles.move_card(_state(), registry, wanted, "top")
    assert state.decks.exploration_deck["hazardous"][0] == wanted
    # Następna eksploracja hazardous dobiera dokładnie tę kartę.
    hazard = "cresius"  # planeta hazardous
    drawn = exploration.begin_exploration(state, registry, "p1", "000", [hazard])
    assert drawn.exploration is not None and drawn.exploration.current is not None
    assert drawn.exploration.current.card_id == wanted


def test_move_card_between_piles(registry: StaticDataRegistry) -> None:
    card = _card_id(registry, "Dyson Sphere")
    state = deck_piles.move_card(_state(), registry, card, "discard")
    assert card in state.decks.exploration_discard["cultural"]
    assert card not in state.decks.exploration_deck["cultural"]
    state = deck_piles.move_card(state, registry, card, "purged")
    assert state.decks.purged == [card]
    assert card not in state.decks.exploration_discard["cultural"]
    state = deck_piles.move_card(state, registry, card, "deck")
    assert card in state.decks.exploration_deck["cultural"] and state.decks.purged == []
    assert len(state.decks.exploration_deck["cultural"]) == 20


def test_move_card_validates(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError, match="Unknown target"):
        deck_piles.move_card(_state(), registry, "dmz", "nowhere")
    with pytest.raises(ValueError, match="Unknown card"):
        deck_piles.move_card(_state(), registry, "no_such_card", "top")
    # Karta przyczepiona do planety / u gracza nie leży w żadnym stosie.
    state = _state()
    state.players["p1"].relic_fragments = []
    drawn = exploration.resolve(_with_card(state, registry, "Dyson Sphere"), registry, "attach")
    with pytest.raises(ValueError, match="not in the deck"):
        deck_piles.move_card(drawn, registry, _card_id(registry, "Dyson Sphere"), "top")


def test_action_card_piles_can_be_moved(registry: StaticDataRegistry) -> None:
    state = _state()
    state.decks.action_card_deck = ["abs", "bunker"]
    state.decks.action_card_discard = ["blitz"]
    moved = deck_piles.move_card(state, registry, "bunker", "top")
    assert moved.decks.action_card_deck == ["bunker", "abs"]
    purged = deck_piles.move_card(moved, registry, "blitz", "purged")
    assert purged.decks.purged == ["blitz"] and purged.decks.action_card_discard == []


def test_card_pool_and_move_endpoint(registry: StaticDataRegistry) -> None:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=GameState())
    client = TestClient(app)

    def pool() -> dict[str, object]:
        data = client.get("/api/public/game/g/web-data").json()
        return dict(data["cardPool"])

    before = pool()
    assert len(before["culturalExploreDeck"]) == 20  # type: ignore[arg-type]
    assert before["culturalExploreDiscard"] == [] and before["purgedCards"] == []
    # Lista talii jest posortowana — nie zdradza kolejności.
    cultural = [str(c) for c in before["culturalExploreDeck"]]  # type: ignore[attr-defined]
    assert cultural == sorted(cultural)

    card = _card_id(registry, "Dyson Sphere")
    assert client.post("/decks/move", json={"cardId": card, "to": "purged"}).status_code == 200
    after = pool()
    assert after["purgedCards"] == [card] and card not in after["culturalExploreDeck"]  # type: ignore[operator]
    assert client.post("/decks/move", json={"cardId": card, "to": "top"}).status_code == 200
    assert pool()["exploreTop"]["cultural"] == card  # type: ignore[index]
    assert client.post("/decks/move", json={"cardId": card, "to": "x"}).status_code == 422
