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
