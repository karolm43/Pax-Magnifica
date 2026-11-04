"""Testy modeli komponentów i ``ComponentCatalog`` na krótkich wpisach."""

from __future__ import annotations

from typing import Any

from src.core.components import (
    CATEGORY_SPECS,
    ActionCardDef,
    ComponentCatalog,
    ComponentCategory,
    DeckDef,
    ExplorationDef,
    build_component,
)

_ACTION: dict[str, Any] = {
    "alias": "amendment", "name": "Amendment", "phase": "Action",
    "window": "At the end of the status phase", "text": "Tekst.",
    "automationID": "amendment", "flavorText": "Flaw", "extra": 1, "source": "base",
}


def test_action_card_zachowuje_pola_i_raw() -> None:
    spec = CATEGORY_SPECS[ComponentCategory.ACTION_CARD]
    card = build_component(_ACTION, spec)
    assert isinstance(card, ActionCardDef)
    assert card.id == "amendment"
    assert card.window == "At the end of the status phase"
    assert card.texts == {"text": "Tekst."}
    assert card.flavor_text == "Flaw"
    assert card.automation_id == "amendment"
    assert card.raw == _ACTION


def test_relikt_flavour_text_brytyjska_pisownia() -> None:
    spec = CATEGORY_SPECS[ComponentCategory.RELIC]
    relic = build_component(
        {"alias": "r", "name": "R", "text": "t", "source": "pok", "flavourText": "f"}, spec
    )
    assert relic.flavor_text == "f"


def test_exploration_uzywa_id_i_attachment_id() -> None:
    spec = CATEGORY_SPECS[ComponentCategory.EXPLORATION]
    exp = build_component(
        {"id": "e1", "type": "Cultural", "attachmentId": "a1", "source": "pok"}, spec
    )
    assert isinstance(exp, ExplorationDef)
    assert exp.id == "e1" and exp.attachment_id == "a1"


def test_deck_card_ids_rozciete_po_bialych_znakach() -> None:
    spec = CATEGORY_SPECS[ComponentCategory.DECK]
    deck = build_component(
        {"alias": "d", "type": "agenda", "cardIDs": "a b\tc\nd", "source": "base"}, spec
    )
    assert isinstance(deck, DeckDef)
    assert deck.card_ids == ["a", "b", "c", "d"]
    as_list = build_component(
        {"alias": "d", "type": "agenda", "cardIDs": ["x", "y"], "source": "base"}, spec
    )
    assert isinstance(as_list, DeckDef) and as_list.card_ids == ["x", "y"]


def test_catalog_get_all_counts() -> None:
    spec = CATEGORY_SPECS[ComponentCategory.ACTION_CARD]
    a = build_component(_ACTION, spec)
    b = build_component({**_ACTION, "alias": "b", "source": "pok"}, spec)
    catalog = ComponentCatalog({ComponentCategory.ACTION_CARD: {a.id: a, b.id: b}})
    assert catalog.get(ComponentCategory.ACTION_CARD, "b") is b
    assert catalog.get(ComponentCategory.ACTION_CARD, "nope") is None
    assert catalog.get(ComponentCategory.AGENDA, "b") is None
    assert set(catalog.all(ComponentCategory.ACTION_CARD)) == {"amendment", "b"}
    assert catalog.all(ComponentCategory.AGENDA) == {}
    assert catalog.counts() == {ComponentCategory.ACTION_CARD: {"base": 1, "pok": 1}}
