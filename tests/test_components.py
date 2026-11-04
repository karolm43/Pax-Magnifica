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


def test_build_timing_specs_i_query_timing() -> None:
    from src.core.components import ComponentRef, build_timing_specs
    from src.core.game_state import Phase
    from src.core.models import AbilityDef, LeaderDef
    from src.core.timing_spec import TriggerKind

    spec = CATEGORY_SPECS[ComponentCategory.ACTION_CARD]
    card = build_component({**_ACTION, "alias": "c1", "phase": "Agenda",
                            "window": "When an agenda is revealed",
                            "playTiming": "AGENDA_WHEN"}, spec)
    no_window = build_component({"alias": "c2", "source": "base"}, spec)
    leaders = {"l1": LeaderDef.model_validate(
        {"id": "l1", "type": "agent", "name": "L", "source": "base",
         "abilityWindow": "ACTION:"})}
    abilities = {"a1": AbilityDef.model_validate(
        {"id": "a1", "name": "A", "source": "base",
         "window": "After a unit is destroyed", "windowEffect": "efekt"})}
    tables = {ComponentCategory.ACTION_CARD: {"c1": card, "c2": no_window}}

    specs = build_timing_specs(tables, leaders, abilities)
    assert set(specs) == {
        ComponentRef(ComponentCategory.ACTION_CARD, "c1"),
        ComponentRef(ComponentCategory.LEADER, "l1"),
        ComponentRef(ComponentCategory.ABILITY, "a1"),
    }
    ability_spec = specs[ComponentRef(ComponentCategory.ABILITY, "a1")]
    assert ability_spec.effect_text == "efekt"

    catalog = ComponentCatalog(tables, specs)
    assert catalog.timing_spec(ComponentRef(ComponentCategory.LEADER, "l1")) is not None
    assert catalog.timing_spec(ComponentRef(ComponentCategory.ACTION_CARD, "c2")) is None
    assert catalog.query_timing(TriggerKind.WHEN) == [
        ComponentRef(ComponentCategory.ACTION_CARD, "c1")
    ]
    assert catalog.query_timing(TriggerKind.WHEN, Phase.AGENDA) == [
        ComponentRef(ComponentCategory.ACTION_CARD, "c1")
    ]
    assert catalog.query_timing(TriggerKind.WHEN, Phase.STATUS) == []
    # konstruktor bez timing_specs (zgodność wsteczna)
    assert ComponentCatalog({}).query_timing(TriggerKind.WHEN) == []
