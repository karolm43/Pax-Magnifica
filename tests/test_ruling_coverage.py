"""Strażnik: każdy ruling i każde zdanie karty audytowanej frakcji ma test (decyzja użytkownika
2026-11-16, ``tests/rulings.py``).

Dla każdej frakcji z modułem ``core/hooks/factions/<frakcja>.py`` spoza ``UNAUDITED``:

- każdy punkt ``docs/rules_tirules/F_<frakcja>.md`` i każde zdanie tekstu komponentu ma test
  oznaczony ``@ruling("<ID>")`` albo wpis w ``tests/rulings_status.json`` z powodem;
- wpis ``requires`` robi się czerwony, gdy wszystkie wymagane elementy są już w silniku;
- każde ID w ``@ruling`` i w statusach istnieje (literówka / nieaktualne ID = błąd).

``UNAUDITED`` to dług z chwili wprowadzenia strażnika: lista może TYLKO maleć. Nowa frakcja
nie trafia na nią - od pierwszego commita musi mieć komplet testów rulingów.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
from pathlib import Path

import pytest

from src.core import rules_hooks
from src.core.hooks import factions as faction_pkg
from src.core.registry import StaticDataRegistry
from tests.rulings import RULING_ATTR, faction_contract

TESTS_DIR = Path(__file__).resolve().parent
STATUS_FILE = TESTS_DIR / "rulings_status.json"

# Frakcje zaimplementowane przed strażnikiem, jeszcze nie przeaudytowane (tylko USUWAĆ).
UNAUDITED = frozenset({
    "sol", "winnu",
})


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    return reg


def implemented_factions() -> list[str]:
    return sorted(
        m.name for m in pkgutil.iter_modules(faction_pkg.__path__) if not m.name.startswith("_")
    )


def audited_factions() -> list[str]:
    return [f for f in implemented_factions() if f not in UNAUDITED]


def marked_ids() -> dict[str, list[str]]:
    """``{ID: [testy]}`` ze wszystkich modułów testów używających ``@ruling``."""
    found: dict[str, list[str]] = {}
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        if "@ruling(" not in path.read_text(encoding="utf-8"):
            continue
        module_name = ".".join(path.relative_to(TESTS_DIR.parent).with_suffix("").parts)
        module = importlib.import_module(module_name)
        for name, value in vars(module).items():
            for ruling_id in getattr(value, RULING_ATTR, ()):
                found.setdefault(ruling_id, []).append(f"{module_name}::{name}")
    return found


def statuses() -> dict[str, dict[str, object]]:
    raw = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def _status_for(ruling_id: str, table: dict[str, dict[str, object]]) -> str | None:
    """Klucz statusu pasujący do ID (dokładny albo sekcja ``…/*``)."""
    if ruling_id in table:
        return ruling_id
    section = ruling_id.rsplit("/", 1)[0] + "/*"
    return section if section in table else None


def _ready(requirement: str, covered: frozenset[str], factions: list[str]) -> bool:
    kind, _, name = requirement.partition(":")
    if kind == "faction":
        return name in factions
    return requirement in covered


def test_kazdy_ruling_i_zdanie_karty_ma_test(registry: StaticDataRegistry) -> None:
    marks = marked_ids()
    table = statuses()
    missing: list[str] = []
    for faction in audited_factions():
        for ruling_id, text in faction_contract(registry, faction).items():
            if ruling_id in marks or _status_for(ruling_id, table) is not None:
                continue
            missing.append(f"{ruling_id}  — {text[:90]}")
    assert not missing, (
        "Rulingi / zdania kart bez testu (dodaj test z @ruling albo status z powodem w "
        "tests/rulings_status.json):\n" + "\n".join(missing)
    )


def test_statusy_requires_nadal_niespelnione(registry: StaticDataRegistry) -> None:
    covered = rules_hooks.covered_components()
    factions = implemented_factions()
    ready: list[str] = []
    for key, entry in statuses().items():
        requires = entry.get("requires")
        if not requires and not entry.get("na"):
            raise AssertionError(f"{key}: status needs 'na' (reason) or 'requires'.")
        if isinstance(requires, list) and all(_ready(str(r), covered, factions) for r in requires):
            ready.append(f"{key} (requires {requires} - already implemented, write the test)")
    assert not ready, "\n".join(ready)


def test_id_w_testach_i_statusach_istnieja(registry: StaticDataRegistry) -> None:
    known: set[str] = set()
    for faction in implemented_factions():
        known |= set(faction_contract(registry, faction))
    unknown = [f"@ruling {i} ({', '.join(t)})" for i, t in marked_ids().items() if i not in known]
    for key in statuses():
        prefix = key[:-1] if key.endswith("/*") else None
        exists = any(i.startswith(prefix) for i in known) if prefix else key in known
        if not exists:
            unknown.append(f"status {key}")
    assert not unknown, "Nieznane ID rulingów:\n" + "\n".join(unknown)


def test_lista_unaudited_tylko_maleje() -> None:
    """Na liście wolno trzymać tylko frakcje, które istnieją (usunięta frakcja = usuń wpis)."""
    assert UNAUDITED <= set(implemented_factions())
    assert len(UNAUDITED) <= 9  # stan z 2026-11-16; zmniejszaj przy każdej przeaudytowanej
