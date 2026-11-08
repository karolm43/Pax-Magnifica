"""Fanowskie warianty talii agend (Absol, Black Spectrum) wybierane w setupie gry."""

from __future__ import annotations

import pytest

from src.core.card_draw import ensure_agenda_deck
from src.core.components import ComponentCategory
from src.core.game_state import GameState
from src.core.objectives import agenda_deck_ids, deck_card_ids
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def test_standard_deck_unchanged_by_fan_decks(registry: StaticDataRegistry) -> None:
    assert len(agenda_deck_ids(registry, "standard")) == 50
    assert agenda_deck_ids(registry) == deck_card_ids(registry, "agenda")


@pytest.mark.parametrize(("variant", "size"), [("absol", 60), ("black_spectrum", 50)])
def test_fan_deck_cards_exist_in_catalog(
    registry: StaticDataRegistry, variant: str, size: int
) -> None:
    ids = agenda_deck_ids(registry, variant)
    assert len(ids) == size and len(set(ids)) == size
    for card_id in ids:
        assert registry.catalog.get(ComponentCategory.AGENDA, card_id) is not None


def test_fan_sources_load_only_agendas_and_agenda_decks(registry: StaticDataRegistry) -> None:
    action_cards = registry.catalog.all(ComponentCategory.ACTION_CARD)
    assert not [c for c in action_cards.values() if c.source in ("absol", "black_spectrum")]
    decks = registry.catalog.all(ComponentCategory.DECK)
    fan = [d for d in decks.values() if d.source in ("absol", "black_spectrum")]
    assert fan and all(d.id.startswith("agendas_") for d in fan)


def test_unknown_variant_rejected(registry: StaticDataRegistry) -> None:
    with pytest.raises(ValueError):
        agenda_deck_ids(registry, "nope")


@pytest.mark.parametrize("variant", ["standard", "absol", "black_spectrum"])
def test_ensure_agenda_deck_uses_selected_variant(
    registry: StaticDataRegistry, variant: str
) -> None:
    state = GameState()
    state.decks.agenda_variant = variant
    ensure_agenda_deck(state, registry)
    assert sorted(state.decks.agenda_deck) == sorted(agenda_deck_ids(registry, variant))
