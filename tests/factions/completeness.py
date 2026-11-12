"""Test kompletności frakcji (DoD bloku frakcji, ``docs/PLAN_FRAKCJE.md`` §2).

Każdy komponent frakcji — zdolność, technologia frakcyjna, lider (efekt i warunek odblokowania),
przełom, promissory note i jednostka frakcyjna ze zdolnością — musi być zrealizowany w silniku
(klucz w ``rules_hooks.covered_components``) albo jawnie oznaczony jako MANUAL w
``effects_status.json``. Brak = lista braków w komunikacie asercji.
"""

from __future__ import annotations

from src.core import leaders, rules_hooks
from src.core.components import ComponentCategory, ComponentRef
from src.core.effects_registry import EffectStatus
from src.core.registry import StaticDataRegistry


def missing_components(registry: StaticDataRegistry, faction_id: str) -> list[str]:
    """Klucze komponentów frakcji bez realizacji (pusta lista = frakcja kompletna)."""
    bundle = registry.catalog.faction_bundle(faction_id)
    covered = rules_hooks.covered_components()
    keys: list[tuple[ComponentCategory, str]] = []
    keys += [(ComponentCategory.ABILITY, a.id) for a in bundle.abilities]
    keys += [(ComponentCategory.TECHNOLOGY, t.id) for t in bundle.faction_tech]
    keys += [(ComponentCategory.LEADER, leader.id) for leader in bundle.leaders]
    keys += [(ComponentCategory.PROMISSORY_NOTE, n.id) for n in bundle.promissory_notes]
    keys += [(ComponentCategory.UNIT, u.id) for u in bundle.units if u.faction and u.ability]
    if bundle.breakthrough is not None:
        keys.append((ComponentCategory.BREAKTHROUGH, bundle.breakthrough.id))
    missing: list[str] = []
    for category, cid in keys:
        key = f"{category.value}:{cid}"
        if key in covered:
            continue
        status = registry.catalog.effect_status(ComponentRef(category, cid))
        if status is EffectStatus.MANUAL:
            continue
        missing.append(key)
    # Warunek odblokowania commandera/bohatera: predykat stanu albo hook zdarzenia.
    for leader in bundle.leaders:
        if leader.type == "agent":
            continue
        if leaders.unlock_predicate(registry, leader.id) is None and not leaders.has_event_unlock(
            leader.id
        ):
            missing.append(f"unlocks:{leader.id}")
    return missing
