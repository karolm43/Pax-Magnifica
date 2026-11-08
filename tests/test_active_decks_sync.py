"""Aktywne talie (agendy / karty akcji / relikwie): skład zgodny z rozszerzeniami i frontem.

Pilnuje, że (1) talie silnika nie zawierają kart USUNIĘTYCH przez rozszerzenia,
(2) plik ``frontend/src/entities/data/activeDecks.ts`` jest zsynchronizowany z silnikiem.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

from src.core.objectives import deck_card_ids
from src.core.registry import StaticDataRegistry

ROOT = Path(__file__).resolve().parent.parent

# Agendy usunięte w PoK (tirules2 / wiki: „13 of the Agendas ... are removed from play").
REMOVED_IN_POK = {
    "core_mining",
    "demilitarized_zone",
    "holy_planet_of_ixth",
    "representative_government",  # wersja base; PoK ma własną o tej samej nazwie
    "rt_biotic",
    "rt_cybernetic",
    "rt_propulsion",
    "rt_warfare",
    "senate_sanctuary",
    "shard_of_the_throne",
    "terraforming_initiative",
    "crown_of_emphidia",
    "crown_of_thalnos",
}


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _load_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gen_active_decks", ROOT / "scripts" / "gen_active_decks.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agenda_deck_is_pok_deck_without_removed_cards(registry: StaticDataRegistry) -> None:
    ids = deck_card_ids(registry, "agenda")
    assert len(ids) == 50 and len(set(ids)) == 50
    assert not REMOVED_IN_POK & set(ids)
    assert "rep_govt" in ids  # Representative Government (PoK)


def test_action_deck_is_te_pok_deck_of_140_cards(registry: StaticDataRegistry) -> None:
    ids = deck_card_ids(registry, "action_card")
    assert len(ids) == 140 and len(set(ids)) == 140  # 80 base + 20 codex I + 20 PoK + 20 TE


def test_frontend_active_decks_file_is_in_sync(registry: StaticDataRegistry) -> None:
    generated = _load_generator().render(registry)
    current = (ROOT / "frontend/src/entities/data/activeDecks.ts").read_text(encoding="utf-8")
    assert current == generated, "Uruchom: uv run python scripts/gen_active_decks.py"
