"""Raport pokrycia hooków (H3, RULES.md 43.2 pkt 2): co zrobiono, a co czeka i w jakiej kolejności.

Generuje ``docs/POKRYCIE_HOOKOW.md``
(uruchom: ``uv run python -m src.audit.hook_coverage --write``).
Raport jest GENEROWANY, nie ręczny — nie edytuj pliku wynikowego.

Dane:
* ``rules_hooks`` — zarejestrowane hooki i komponenty, które implementują (``covers``);
* katalog + rejestr — komponenty wymagające hooków (karty akcji, agendy, relikty, promissory
  notes, eksploracja, wydarzenia, technologie, zdolności frakcji, liderzy, przełomy);
* ``timing_spec`` — rodzaj wyzwalacza (when/after/instead/action…) komponentów z oknem.

UWAGA: przypisanie komponentu do OBSZARU reguł (ruch, walka, ekonomia…) to HEURYSTYKA po słowach
kluczowych w angielskim tekście komponentu. Służy do priorytetyzacji (który punkt zaczepienia
obsłuży najwięcej komponentów), nie do decyzji o implementacji — treść zawsze czytamy z assetów
i tirules2.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from src.core import rules_hooks
from src.core.components import ComponentCategory, ComponentRef
from src.core.registry import StaticDataRegistry
from src.core.timing_spec import TriggerKind, classify_trigger

DOC_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "POKRYCIE_HOOKOW.md"

# Obszar reguł -> wzorzec słów kluczowych (heurystyka, patrz docstring modułu).
AREAS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ruch (movement.*)", re.compile(r"\bmov(e|es|ed|ement)\b|gravity|wormhole|adjacent", re.I)),
    (
        "walka (combat.*, space_cannon, bombardment)",
        re.compile(
            r"combat|\broll|\bhits?\b|sustain damage|destroy|bombardment|space cannon|"
            r"anti-fighter|retreat",
            re.I,
        ),
    ),
    ("produkcja (production.*)", re.compile(r"produc|space dock|reinforcements", re.I)),
    (
        "ekonomia i płatności (economy, payment)",
        re.compile(r"trade goods?|commodit|\bspend|\bresources?\b|\binfluence\b", re.I),
    ),
    (
        "żetony dowodzenia (command_tokens)",
        re.compile(r"command tokens?|fleet pool|strategy pool|tactical pool", re.I),
    ),
    (
        "technologie (technology)",
        re.compile(r"technolog|research|prerequisite|unit upgrade", re.I),
    ),
    ("karty (card_draw, promissory)", re.compile(r"action cards?|\bdraw|discard|promissory", re.I)),
    (
        "planety i eksploracja (control, exploration)",
        re.compile(r"\bplanets?\b|explor|relic|frontier|attach|\bcontrol", re.I),
    ),
    (
        "agenda i głosowanie (agenda_phase)",
        re.compile(r"agenda|\bvot(e|es|ing)\b|\bspeaker", re.I),
    ),
    ("cele i punkty (objectives)", re.compile(r"victory points?|objective|\bscore", re.I)),
    (
        "status i odświeżanie (status_phase)",
        re.compile(r"status phase|\bready\b|refresh|exhaust", re.I),
    ),
    ("karty strategii i inicjatywa", re.compile(r"strategy card|initiative", re.I)),
)

_CATALOG_CATEGORIES = (
    ComponentCategory.ACTION_CARD,
    ComponentCategory.AGENDA,
    ComponentCategory.RELIC,
    ComponentCategory.PROMISSORY_NOTE,
    ComponentCategory.EXPLORATION,
    ComponentCategory.GALACTIC_EVENT,
)


@dataclass(frozen=True)
class Row:
    """Komponent wymagający (lub nie) hooka."""

    category: ComponentCategory
    component_id: str
    text: str
    trigger: TriggerKind | None
    covered: bool

    @property
    def key(self) -> str:
        return f"{self.category.value}:{self.component_id}"


def collect_rows(registry: StaticDataRegistry) -> list[Row]:
    """Zbiera komponenty wszystkich kategorii podlegających hookom."""
    covered = rules_hooks.covered_components()
    rows: list[Row] = []

    def add(category: ComponentCategory, cid: str, text: str, window: str | None) -> None:
        trigger = classify_trigger(window) if window else None
        key = f"{category.value}:{cid}"
        rows.append(Row(category, cid, text, trigger, key in covered))

    for category in _CATALOG_CATEGORIES:
        for cid, component in registry.catalog.all(category).items():
            text = " ".join([component.name or "", *component.texts.values()])
            spec = registry.catalog.timing_spec(ComponentRef(category, cid))
            trigger = spec.trigger if spec is not None else None
            rows.append(
                Row(category, cid, text, trigger, f"{category.value}:{cid}" in covered)
            )
    for tid, tech in registry.technologies.items():
        add(ComponentCategory.TECHNOLOGY, tid, f"{tech.name} {tech.text or ''}", None)
    for aid, ability in registry.abilities.items():
        text = f"{ability.name} {ability.permanent_effect or ''} {ability.window_effect or ''}"
        add(ComponentCategory.ABILITY, aid, text, ability.window)
    for lid, leader in registry.leaders.items():
        add(
            ComponentCategory.LEADER, lid,
            f"{leader.name} {leader.ability_text or ''}", leader.ability_window,
        )
    for bid, breakthrough in registry.breakthroughs.items():
        text = f"{breakthrough.name} {breakthrough.text or ''}"
        add(ComponentCategory.BREAKTHROUGH, bid, text, None)
    return rows


def areas_of(text: str) -> list[str]:
    """Obszary reguł wskazane przez słowa kluczowe tekstu (może być kilka lub żaden)."""
    return [name for name, pattern in AREAS if pattern.search(text)]


def render_markdown(registry: StaticDataRegistry) -> str:
    """Składa raport w Markdown (deterministyczny dla tych samych danych i hooków)."""
    rows = collect_rows(registry)
    hooks = rules_hooks.all_hooks()
    lines: list[str] = [
        "# Pokrycie hooków (generowany — nie edytuj ręcznie)",
        "",
        "Wygenerowano: `uv run python -m src.audit.hook_coverage --write`. Zasady: `RULES.md` 43.",
        "Przypisanie do obszarów to HEURYSTYKA po słowach kluczowych "
        "(priorytetyzacja, nie decyzja).",
        "",
        "## 1. Zarejestrowane hooki",
        "",
        f"Razem: **{len(hooks)}**.",
        "",
        "| Punkt zaczepienia | Rodzaj | Źródło | Komponent |",
        "|---|---|---|---|",
    ]
    for hook in sorted(hooks, key=lambda h: (h.point, h.kind.value, h.source.component_id)):
        lines.append(
            f"| `{hook.point}` | {hook.kind.name} | "
            f"{hook.source.kind}:{hook.source.component_id} | {hook.covers or '—'} |"
        )

    lines += ["", "## 2. Pokrycie per kategoria", "",
              "| Kategoria | Komponentów | Z hookiem | % |", "|---|---:|---:|---:|"]
    by_category: dict[ComponentCategory, list[Row]] = {}
    for row in rows:
        by_category.setdefault(row.category, []).append(row)
    for category in ComponentCategory:
        group = by_category.get(category)
        if not group:
            continue
        done = sum(1 for r in group if r.covered)
        percent = 100 * done / len(group)
        lines.append(f"| {category.value} | {len(group)} | {done} | {percent:.1f} |")

    lines += ["", "## 3. Rodzaj wyzwalacza (komponenty z oknem czasowym)", "",
              "| Wyzwalacz | Komponentów |", "|---|---:|"]
    triggers = Counter(r.trigger.value for r in rows if r.trigger is not None)
    for name, count in sorted(triggers.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {name} | {count} |")

    need: Counter[str] = Counter()
    need_open: Counter[str] = Counter()
    for row in rows:
        for area in areas_of(row.text):
            need[area] += 1
            if not row.covered:
                need_open[area] += 1
    lines += ["", "## 4. Zapotrzebowanie na obszary reguł (priorytety)", "",
              "Im więcej komponentów dotyka obszaru, tym bardziej opłaca się domknąć jego punkty "
              "zaczepienia.", "",
              "| Obszar | Komponentów | Bez hooka |", "|---|---:|---:|"]
    for area, count in sorted(need.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {area} | {count} | {need_open[area]} |")
    unassigned = sum(1 for r in rows if not areas_of(r.text))
    lines += [
        "",
        f"Bez dopasowania do obszaru: {unassigned} komponentów (do ręcznego przeglądu).",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI: wypisuje raport albo zapisuje go do ``docs/POKRYCIE_HOOKOW.md`` (``--write``)."""
    parser = argparse.ArgumentParser(description="Raport pokrycia hooków (H3).")
    parser.add_argument("--write", action="store_true", help="zapisz do docs/POKRYCIE_HOOKOW.md")
    args = parser.parse_args(argv)
    report = render_markdown(StaticDataRegistry())
    if args.write:
        DOC_PATH.write_text(report, encoding="utf-8", newline="\n")
        print(f"Zapisano {DOC_PATH}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
