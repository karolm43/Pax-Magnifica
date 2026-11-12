"""Strażnik: każdy INTERAKTYWNY komponent zaimplementowanej frakcji ma scenariusz przez API.

Decyzja użytkownika (2026-11-12): efekt, który działa tylko w teście jednostkowym, a gracz nie
ma jak go użyć, to błąd. Interaktywny = gracz coś decyduje albo uruchamia:
oferta (hook ``optional``/``decide``), użycie w oknie (RULES.md 62.0), ACTION, promissory note.
Scenariusze: ``tests/factions/test_flows_<frakcja>.py`` z ``@covers(...)`` (``flow_harness``).
Nowa frakcja (moduł w ``core/hooks/factions``) bez scenariuszy = czerwony test (DoD bloku).
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

from src.core import faction_components, rules_hooks
from src.core.hooks import factions as faction_pkg
from src.core.registry import StaticDataRegistry
from tests.factions.flow_harness import COVERS_ATTR

_KIND = {"abilities": "ability", "leaders": "leader", "breakthroughs": "breakthrough"}


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def implemented_factions() -> list[str]:
    """Frakcje z własnym modułem hooków (``core/hooks/factions/<frakcja>.py``)."""
    return sorted(
        m.name for m in pkgutil.iter_modules(faction_pkg.__path__) if not m.name.startswith("_")
    )


def interactive_components(registry: StaticDataRegistry, faction: str) -> dict[str, list[str]]:
    """``klucz komponentu -> sposoby interakcji`` (offer / window / action / note)."""
    rules_hooks.bind_registry(registry)
    bundle = registry.catalog.faction_bundle(faction)
    keys: list[str] = []
    keys += [f"abilities:{a.id}" for a in bundle.abilities]
    keys += [f"technologies:{t.id}" for t in bundle.faction_tech]
    keys += [f"leaders:{leader.id}" for leader in bundle.leaders]
    keys += [f"promissory_notes:{n.id}" for n in bundle.promissory_notes]
    keys += [f"units:{u.id}" for u in bundle.units if u.faction and u.ability]
    if bundle.breakthrough is not None:
        keys.append(f"breakthroughs:{bundle.breakthrough.id}")
    hooks = rules_hooks.all_hooks()
    found: dict[str, list[str]] = {}
    for key in keys:
        how: set[str] = set()
        if any(h.covers == key and (h.optional or h.decide) for h in hooks):
            how.add("offer")
        if key in faction_components._WINDOW_USES:
            how.add("window")
        category, _, cid = key.partition(":")
        kind = _KIND.get(category)
        if kind is not None and faction_components.is_action(registry, kind, cid):
            how.add("action")
        if category == "promissory_notes":
            how.add("note")
        if how:
            found[key] = sorted(how)
    return found


def scenario_covers() -> set[str]:
    """Komponenty oznaczone ``@covers`` we wszystkich ``test_flows_*.py``."""
    covered: set[str] = set()
    for path in sorted(Path(__file__).parent.glob("test_flows_*.py")):
        module = importlib.import_module(f"tests.factions.{path.stem}")
        for value in vars(module).values():
            covered.update(getattr(value, COVERS_ATTR, ()))
    return covered


def test_kazdy_interaktywny_komponent_ma_scenariusz(registry: StaticDataRegistry) -> None:
    covered = scenario_covers()
    missing = {
        faction: sorted(set(interactive_components(registry, faction)) - covered)
        for faction in implemented_factions()
    }
    missing = {f: keys for f, keys in missing.items() if keys}
    assert not missing, (
        "Brak scenariusza przez API (tests/factions/test_flows_<frakcja>.py, @covers) dla: "
        f"{missing}"
    )


def test_straznik_widzi_frakcje(registry: StaticDataRegistry) -> None:
    """Strażnik nie może przejść „na pusto”: frakcje z modułami mają komponenty interaktywne."""
    factions = implemented_factions()
    assert {"sardakk", "letnev", "jolnar", "sol", "arborec"} <= set(factions)
    assert interactive_components(registry, "sardakk")


def test_covers_wskazuje_prawdziwe_komponenty(registry: StaticDataRegistry) -> None:
    """Literówka w ``@covers`` nie może udawać pokrycia."""
    known = {
        key for faction in implemented_factions()
        for key in interactive_components(registry, faction)
    }
    assert not scenario_covers() - known, sorted(scenario_covers() - known)
