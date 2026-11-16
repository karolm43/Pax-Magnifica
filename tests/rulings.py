"""Rulingi i zdania kart jako kontrakt testów (decyzja użytkownika 2026-11-16).

Każdy punkt rulingu z ``docs/rules_tirules/F_<frakcja>.md`` i każde zdanie (klauzula) tekstu
komponentu frakcji z assetów dostaje stałe ID. Test, który sprawdza dany ruling albo zdanie,
oznacza się ``@ruling("<ID>", ...)``. Strażnik ``tests/test_ruling_coverage.py`` wymaga, by
KAŻDE ID audytowanej frakcji miało test albo jawny status w ``tests/rulings_status.json``.

Format ID:

- ruling: ``F_xxcha/quash/1.1`` - plik, sekcja (slug nagłówka bez nawiasu typu, ``Ω`` = ``omega``),
  numer punktu (podpunkt po kropce);
- zdanie karty: ``abilities:quash#2``, ``leaders:xxchacommander#unlock`` - klucz komponentu jak
  w ``rules_hooks.covered_components``, numer zdania od 1 (zdania dzieli ``.``, ``;`` i nowa linia;
  okno zdolności to początek zdania 1).

Podgląd listy: ``uv run python -m tests.rulings xxcha``.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

RULINGS_DIR = Path(__file__).resolve().parent.parent / "docs" / "rules_tirules"
RULING_ATTR = "__rulings__"

# Moduł hooków frakcji -> plik rulingów, gdy nazwy się różnią.
_RULINGS_FILE = {"jolnar": "F_jol_nar", "sardakk": "F_norr", "naazrokha": "F_naaz_rokha"}

_BULLET = re.compile(r"^(?P<indent>\s*)- (?P<text>.+)$")
_SPLIT = re.compile(r"(?<=[.;!?])\s+|\n+")


def ruling(*ids: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Oznacza test: sprawdza te rulingi / zdania kart (ID jak w docstringu modułu)."""

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, RULING_ATTR, tuple(getattr(fn, RULING_ATTR, ())) + ids)
        return fn

    return decorate


def rulings_file(faction: str) -> Path:
    return RULINGS_DIR / f"{_RULINGS_FILE.get(faction, f'F_{faction}')}.md"


def _slug(heading: str) -> str:
    text = re.sub(r"\([^)]*\)\s*$", "", heading.replace("Ω", " omega "))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_rulings(path: Path) -> dict[str, str]:
    """``{ID: tekst}`` wszystkich punktów pliku rulingów (kolejność jak w pliku)."""
    found: dict[str, str] = {}
    prefix = path.stem
    section = ""
    seen_sections: dict[str, int] = {}
    counters: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = _slug(line[3:])
            seen_sections[section] = seen_sections.get(section, 0) + 1
            if seen_sections[section] > 1:
                section = f"{section}-{seen_sections[section]}"
            counters = []
            continue
        match = _BULLET.match(line)
        if match is None or not section:
            continue
        depth = len(match["indent"].expandtabs(4)) // 4
        counters = counters[: depth + 1]
        while len(counters) <= depth:
            counters.append(0)
        counters[depth] += 1
        number = ".".join(str(n) for n in counters)
        found[f"{prefix}/{section}/{number}"] = match["text"].strip()
    return found


def clauses(text: str) -> list[str]:
    return [part.strip() for part in _SPLIT.split(text) if part.strip()]


def component_texts(registry: Any, faction: str) -> dict[str, str]:
    """``{klucz komponentu: pełny tekst}`` komponentów frakcji (jak w ``completeness``)."""
    bundle = registry.catalog.faction_bundle(faction)
    texts: dict[str, str] = {}
    for ability in bundle.abilities:
        parts = [ability.window or "", ability.window_effect or "", ability.permanent_effect or ""]
        body = ""
        if parts[0]:
            body = f"{parts[0]}: {parts[1]}".strip()
        body = " ".join(p for p in (body, parts[2]) if p)
        texts[f"abilities:{ability.id}"] = body
    for tech in bundle.faction_tech:
        texts[f"technologies:{tech.id}"] = tech.text or ""
    for leader in bundle.leaders:
        window = leader.ability_window or ""
        texts[f"leaders:{leader.id}"] = f"{window} {leader.ability_text or ''}".strip()
    for note in bundle.promissory_notes:
        texts[f"promissory_notes:{note.id}"] = (note.texts or {}).get("text", "")
    for unit in bundle.units:
        if unit.faction and unit.ability:
            texts[f"units:{unit.id}"] = unit.ability
    if bundle.breakthrough is not None:
        texts[f"breakthroughs:{bundle.breakthrough.id}"] = bundle.breakthrough.text or ""
    return texts


def component_clauses(registry: Any, faction: str) -> dict[str, str]:
    """``{ID zdania: zdanie}``; liderzy z warunkiem odblokowania mają też ``#unlock``."""
    found: dict[str, str] = {}
    for key, text in component_texts(registry, faction).items():
        for index, part in enumerate(clauses(text), start=1):
            found[f"{key}#{index}"] = part
    for leader in registry.catalog.faction_bundle(faction).leaders:
        condition = leader.unlock_condition or ""
        if condition and condition != "Always Unlocked":
            found[f"leaders:{leader.id}#unlock"] = condition
    return found


def faction_contract(registry: Any, faction: str) -> dict[str, str]:
    """Pełna lista ID do pokrycia dla frakcji: rulingi + zdania kart."""
    contract = parse_rulings(rulings_file(faction)) if rulings_file(faction).exists() else {}
    contract.update(component_clauses(registry, faction))
    return contract


if __name__ == "__main__":  # podgląd checklisty frakcji
    from src.core.registry import StaticDataRegistry

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    for key, text in faction_contract(StaticDataRegistry(), sys.argv[1]).items():
        print(f"{key}\t{text}")
