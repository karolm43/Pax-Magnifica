"""Testy raportu pokrycia hooków (H3) i spięcia hooków z rejestrem efektów."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from src.audit import hook_coverage
from src.core import rules_hooks
from src.core.components import ComponentCategory, ComponentRef
from src.core.effects_registry import EffectRegistry, EffectStatus
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import HookKind, HookSource


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _exists(registry: StaticDataRegistry, key: str) -> bool:
    category_value, _, component_id = key.partition(":")
    category = ComponentCategory(category_value)
    pools: dict[ComponentCategory, Mapping[str, object]] = {
        ComponentCategory.TECHNOLOGY: registry.technologies,
        ComponentCategory.ABILITY: registry.abilities,
        ComponentCategory.LEADER: registry.leaders,
        ComponentCategory.BREAKTHROUGH: registry.breakthroughs,
        ComponentCategory.FACTION: registry.factions,
        ComponentCategory.UNIT: registry.units,
    }
    pool = pools.get(category)
    if pool is not None:
        return component_id in pool
    return registry.catalog.get(category, component_id) is not None


def test_kazdy_covers_wskazuje_istniejacy_komponent(registry: StaticDataRegistry) -> None:
    """Literówka w ``covers`` nie może po cichu zawyżyć pokrycia."""
    for key in rules_hooks.covered_components():
        assert _exists(registry, key), f"hook wskazuje nieistniejący komponent: {key}"


def test_komponent_z_hookiem_ma_status_implemented(registry: StaticDataRegistry) -> None:
    ref = ComponentRef(ComponentCategory.TECHNOLOGY, "amd")
    assert registry.effect_registry.status_of(ref) is EffectStatus.IMPLEMENTED
    covered = rules_hooks.covered_components()
    uncovered = next(t for t in sorted(registry.technologies) if f"technologies:{t}" not in covered)
    other = ComponentRef(ComponentCategory.TECHNOLOGY, uncovered)
    assert registry.effect_registry.status_of(other) is EffectStatus.NOT_IMPLEMENTED


def test_jawny_wpis_pliku_ma_pierwszenstwo_przed_pokryciem() -> None:
    ref = ComponentRef(ComponentCategory.TECHNOLOGY, "amd")
    base = EffectRegistry({ref: EffectStatus.MANUAL})
    merged = base.with_hook_coverage(["technologies:amd", "technologies:ws"])
    assert merged.status_of(ref) is EffectStatus.MANUAL
    assert merged.status_of(ComponentRef(ComponentCategory.TECHNOLOGY, "ws")) is (
        EffectStatus.IMPLEMENTED
    )


def test_covers_tylko_z_rejestracji_w_bloku_nie_zostaje() -> None:
    before = rules_hooks.covered_components()
    with rules_hooks.temporary_hooks():
        rules_hooks.register(
            "test.point",
            HookSource(rules_hooks.SOURCE_FACTION, "x"),
            HookKind.PERMIT,
            covers="technologies:ws",
        )(lambda _s, _p, _c: True)
        assert "technologies:ws" in rules_hooks.covered_components()
    assert rules_hooks.covered_components() == before


def test_raport_zawiera_sekcje_i_policzone_hooki(registry: StaticDataRegistry) -> None:
    text = hook_coverage.render_markdown(registry)
    for header in ("## 1. Zarejestrowane hooki", "## 2. Pokrycie per kategoria",
                   "## 3. Rodzaj wyzwalacza", "## 4. Zapotrzebowanie"):
        assert header in text
    assert "`movement.enter_asteroids`" in text
    assert "| technologies |" in text


def test_raport_jest_deterministyczny(registry: StaticDataRegistry) -> None:
    assert hook_coverage.render_markdown(registry) == hook_coverage.render_markdown(registry)


def test_areas_of_dopasowuje_slowa_kluczowe() -> None:
    assert "produkcja (production.*)" in hook_coverage.areas_of("Produce 2 units")
    assert hook_coverage.areas_of("zzz") == []


def test_kolejka_kart_action_zawiera_tylko_karty_bez_efektu(registry: StaticDataRegistry) -> None:
    text = hook_coverage.render_markdown(registry)
    assert "## 6. Kolejka kart ACTION do zrobienia" in text
    queue = text.split("## 6. Kolejka kart ACTION do zrobienia", 1)[1].split("## 7.", 1)[0]
    assert "`meltdown`" not in queue  # Reactor Meltdown ma efekt (action_cards_economy)
    assert "`messiah`" not in queue  # ma efekt - zniknęła z kolejki
    assert "`disgrace`" not in queue  # karta reakcji, nie ACTION
