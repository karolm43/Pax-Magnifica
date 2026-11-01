"""Testy StaticDataRegistry — ładowanie, filtrowanie źródeł, spójność."""

from __future__ import annotations

from src.core.registry import StaticDataRegistry


def test_registry_loads_core() -> None:
    """Oficjalny rdzeń ładuje niepuste zbiory jednostek, planet i systemów."""
    registry = StaticDataRegistry()
    assert len(registry.units) > 0
    assert len(registry.planets) > 0
    assert len(registry.systems) > 0


def test_registry_known_entities_present() -> None:
    """Rdzeń zawiera znane encje bazowe."""
    registry = StaticDataRegistry()
    assert "cruiser" in registry.units
    assert "mr" in registry.planets
    assert "18" in registry.systems
    assert registry.systems["18"].name == "Mecatol Rex"


def test_registry_filters_out_homebrew() -> None:
    """Encje z nieaktywnych źródeł nie są ładowane."""
    registry = StaticDataRegistry(enabled_sources=["base"])
    # Wszystkie załadowane jednostki mają source == 'base'
    assert all(u.source == "base" for u in registry.units.values())
    # Przy samym 'base' nic z pok/codex nie wejdzie
    report = registry.report()
    assert report.enabled_sources == ["base"]
    assert "pok" in report.skipped_sources


def test_registry_dense_indices() -> None:
    """Mapowania id -> indeks są gęste i zgodne z liczbą encji."""
    registry = StaticDataRegistry()
    assert sorted(registry.unit_index.values()) == list(range(len(registry.units)))
    assert sorted(registry.planet_index.values()) == list(range(len(registry.planets)))
    assert sorted(registry.system_index.values()) == list(range(len(registry.systems)))


def test_registry_reference_consistency() -> None:
    """Rdzeń oficjalny nie ma wiszących referencji system -> planeta."""
    registry = StaticDataRegistry()
    assert registry.missing_planet_references() == {}


# --- Wybór kanonicznego zestawu kart strategii (RULES.md 14) ---------------


def test_active_strategy_card_set_alias_prefers_thunders_edge() -> None:
    """Przy włączonym Thunder's Edge kanoniczny zestaw to ``te`` (najwyższy priorytet)."""
    registry = StaticDataRegistry(
        enabled_sources=["base", "pok", "codex1", "codex2", "codex3", "codex4", "thunders_edge"]
    )
    assert registry.active_strategy_card_set_alias() == "te"


def test_active_strategy_card_set_alias_pok_without_thunders_edge() -> None:
    """Bez Thunder's Edge, ale z PoK, kanoniczny zestaw to ``pok``."""
    registry = StaticDataRegistry(
        enabled_sources=["base", "pok", "codex1", "codex2", "codex3", "codex4"]
    )
    assert registry.active_strategy_card_set_alias() == "pok"


def test_active_strategy_card_set_alias_base_only() -> None:
    """Przy samym ``base`` kanoniczny zestaw to ``base_game``."""
    registry = StaticDataRegistry(enabled_sources=["base"])
    assert registry.active_strategy_card_set_alias() == "base_game"


def test_active_strategy_card_set_alias_homebrew_falls_back_to_pok() -> None:
    """Źródła homebrew spoza listy priorytetu są ignorowane → fallback ``pok``."""
    registry = StaticDataRegistry(enabled_sources=["anarchy", "luminous"])
    assert registry.active_strategy_card_set_alias() == "pok"


def test_canonical_set_has_te_cards_when_thunders_edge_enabled() -> None:
    """Kanoniczny zestaw z TE zawiera te4construction/te6warfare, resztę PoK."""
    registry = StaticDataRegistry(
        enabled_sources=["base", "pok", "codex1", "codex2", "codex3", "codex4", "thunders_edge"]
    )
    ids = [card.id for card in registry.strategy_card_set()]
    assert ids == [
        "pok1leadership",
        "pok2diplomacy",
        "pok3politics",
        "te4construction",
        "pok5trade",
        "te6warfare",
        "pok7technology",
        "pok8imperial",
    ]


def test_canonical_set_has_pok_cards_without_thunders_edge() -> None:
    """Bez TE kanoniczny zestaw to czyste karty PoK (pok4construction/pok6warfare)."""
    registry = StaticDataRegistry(
        enabled_sources=["base", "pok", "codex1", "codex2", "codex3", "codex4"]
    )
    ids = [card.id for card in registry.strategy_card_set()]
    assert "pok4construction" in ids
    assert "pok6warfare" in ids
    assert "te4construction" not in ids
    assert "te6warfare" not in ids


def test_explicit_alias_overrides_canonical_choice() -> None:
    """Jawny alias wymusza konkretny zestaw niezależnie od włączonych źródeł."""
    registry = StaticDataRegistry(
        enabled_sources=["base", "pok", "codex1", "codex2", "codex3", "codex4", "thunders_edge"]
    )
    ids = [card.id for card in registry.strategy_card_set("pok")]
    assert "pok4construction" in ids
    assert "te4construction" not in ids
