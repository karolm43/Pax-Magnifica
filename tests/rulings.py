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

Kontrakt ogólny (decyzja użytkownika 2026-11-17): te same zasady dla rulingów kart i komponentów
ogólnych (``C_<typ>.md``) i zasad ogólnych (``R_<temat>.md``), ID ``C_agendas/<karta>/1``,
``R_movement/notes/2`` (sekcja „Related Topics” to linki - pomijana). W plikach kart
(``CARD_FILES``) wymagane są tylko sekcje kart z zarejestrowanym hookiem (karta
niezaimplementowana = wymaganie na przyszłość: strażnik zrobi się czerwony, gdy karta dostanie
hook) oraz sekcje, których nie da się dopasować do żadnej karty. Dług audytu:
``tests/rulings_debt.json`` (tylko maleje).

Podgląd listy: ``uv run python -m tests.rulings xxcha`` albo ``… tests.rulings C_relics``.
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
_RULINGS_FILE = {
    "jolnar": "F_jol_nar", "l1z1x": "F_lizix", "sardakk": "F_norr", "naaz": "F_naaz_rokha",
    "cabal": "F_vuilraith", "titans": "F_ul",
}

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


# ============================================================== kontrakt ogólny (C_ i R_)

SKIPPED_SECTIONS = frozenset({"related-topics"})

# Pliki kart: plik -> kategorie komponentów, do których należą sekcje (nagłówek = nazwa karty).
CARD_FILES: dict[str, tuple[str, ...]] = {
    "C_action_cards": ("action_cards",),
    "C_agendas": ("agendas",),
    "C_relics": ("relics",),
    "C_technology": ("technologies",),
    "C_promissory_notes": ("promissory_notes",),
    "C_events": ("galactic_events",),
}


def general_files() -> list[str]:
    """Pliki kontraktu ogólnego: wszystkie ``C_*`` i ``R_*`` z ``docs/rules_tirules``."""
    return sorted(p.stem for p in RULINGS_DIR.glob("[CR]_*.md"))


def general_rulings(stem: str) -> dict[str, str]:
    """Punkty pliku ``C_``/``R_`` bez sekcji z linkami."""
    return {
        key: text
        for key, text in parse_rulings(RULINGS_DIR / f"{stem}.md").items()
        if key.split("/")[1] not in SKIPPED_SECTIONS
    }


def name_key(name: str) -> str:
    """Klucz dopasowania nazwy karty do nagłówka sekcji (bez interpunkcji, ``Ω`` = omega)."""
    text = unicodedata.normalize("NFKD", name.replace("Ω", " omega ")).encode("ascii", "ignore")
    return re.sub(r"[^a-z0-9]", "", text.decode().lower())


def _category_names(registry: Any, category: str) -> dict[str, str]:
    from src.core.components import ComponentCategory

    if category == "technologies":
        return {t.id: t.name for t in registry.technologies.values()}
    return {k: v.name or "" for k, v in registry.catalog.all(ComponentCategory(category)).items()}


def section_components(registry: Any, stem: str) -> dict[str, list[str]]:
    """``{sekcja: [klucze komponentów]}`` pliku kart (pusta lista = nie pasuje do żadnej karty)."""
    by_key: dict[str, list[str]] = {}
    for category in CARD_FILES[stem]:
        for component_id, name in _category_names(registry, category).items():
            if name:
                by_key.setdefault(name_key(name), []).append(f"{category}:{component_id}")
    sections = dict.fromkeys(key.split("/")[1] for key in general_rulings(stem))

    def keys_of(section: str) -> list[str]:
        key = section.replace("-", "")
        # Karty Codexu (Ω) mają w assetach nazwę bez „Ω” - sekcja „hack-election-omega”.
        while key not in by_key and key.endswith("omega"):
            key = key[: -len("omega")]
        return sorted(by_key.get(key, []))

    return {s: keys_of(s) for s in sections}


def general_contract(registry: Any, stem: str, covered: frozenset[str]) -> dict[str, str]:
    """ID wymagane TERAZ w pliku ``C_``/``R_`` (karty z hookiem + sekcje bez dopasowania)."""
    rulings = general_rulings(stem)
    if stem not in CARD_FILES:
        return rulings
    sections = section_components(registry, stem)
    required = {s for s, keys in sections.items() if not keys or any(k in covered for k in keys)}
    return {key: text for key, text in rulings.items() if key.split("/")[1] in required}


if __name__ == "__main__":  # podgląd checklisty frakcji albo pliku C_/R_
    from src.core import rules_hooks
    from src.core.registry import StaticDataRegistry

    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    _registry = StaticDataRegistry()
    rules_hooks.bind_registry(_registry)
    _name = sys.argv[1]
    if _name[:2] in ("C_", "R_"):
        _items = general_contract(_registry, _name, rules_hooks.covered_components())
    else:
        _items = faction_contract(_registry, _name)
    for key, text in _items.items():
        print(f"{key}\t{text}")
