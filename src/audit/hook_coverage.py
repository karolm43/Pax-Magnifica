"""Raport pokrycia hooków (H3, RULES.md 43.2 pkt 2): co zrobiono, a co czeka i w jakiej kolejności.

Generuje ``docs/POKRYCIE_HOOKOW.md`` (krótkie podsumowanie) oraz szczegóły w
``docs/pokrycie_hookow/*.md`` (uruchom: ``uv run python -m src.audit.hook_coverage --write``).
Raport jest GENEROWANY, nie ręczny — nie edytuj pliku wynikowego.

Dane:
* ``rules_hooks`` — zarejestrowane hooki i komponenty, które implementują (``covers``);
* katalog + rejestr — komponenty wymagające hooków (karty akcji, agendy, relikty, promissory
  notes, eksploracja, wydarzenia, technologie, zdolności frakcji, liderzy, przełomy);
* ``timing_spec`` — rodzaj wyzwalacza (when/after/instead/action…) komponentów z oknem.

UWAGA: przypisanie komponentu do OBSZARU reguł (ruch, walka, ekonomia…) i szacowany TYP hooka
(FORBID/PERMIT/MODIFY/REPLACE/TRIGGER) to HEURYSTYKI po słowach kluczowych w angielskim tekście
komponentu. Służą do priorytetyzacji (który punkt zaczepienia obsłuży najwięcej komponentów) i do
przeglądu, nie do decyzji o implementacji — treść zawsze czytamy z assetów i tirules2.
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
from src.core.models import FactionDef
from src.core.registry import StaticDataRegistry
from src.core.timing_spec import TriggerKind, classify_trigger

DOC_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "POKRYCIE_HOOKOW.md"
SNIPPET = 140  # długość fragmentu tekstu w tabelach szczegółowych

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

# Szacowany TYP hooka (RULES.md 43.1 pkt 4) wg słów kluczowych; pierwszy pasujący wygrywa.
KINDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("REPLACE (instead of)", re.compile(r"\binstead\b", re.I)),
    ("FORBID (zakaz)", re.compile(r"cannot|can't|may not|must not|is not able|unable", re.I)),
    (
        "MODIFY (liczba/rzut)",
        re.compile(r"[+-]\s?\d|\badditional\b|\bextra\b|\breroll|\bre-roll|\bmore\b|\bfewer", re.I),
    ),
    ("PERMIT (pozwolenie)", re.compile(r"\bmay\b|\bcan\b|\bable\b", re.I)),
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
    name: str
    source: str
    body: str
    faction: str | None
    trigger: TriggerKind | None
    covered: bool

    @property
    def text(self) -> str:
        return f"{self.name} {self.body}"

    @property
    def key(self) -> str:
        return f"{self.category.value}:{self.component_id}"


def collect_rows(registry: StaticDataRegistry) -> list[Row]:
    """Zbiera komponenty wszystkich kategorii podlegających hookom."""
    covered = rules_hooks.covered_components()
    rows: list[Row] = []

    def add(
        category: ComponentCategory,
        cid: str,
        name: str | None,
        source: str,
        body: str,
        faction: str | None,
        trigger: TriggerKind | None,
    ) -> None:
        key = f"{category.value}:{cid}"
        rows.append(
            Row(category, cid, name or cid, source, " ".join(body.split()), faction, trigger,
                key in covered)
        )

    for category in _CATALOG_CATEGORIES:
        for cid, component in registry.catalog.all(category).items():
            spec = registry.catalog.timing_spec(ComponentRef(category, cid))
            add(
                category, cid, component.name, component.source,
                " ".join(component.texts.values()),
                getattr(component, "faction", None),
                spec.trigger if spec is not None else None,
            )
    for tid, tech in registry.technologies.items():
        add(ComponentCategory.TECHNOLOGY, tid, tech.name, tech.source, tech.text or "",
            tech.faction, None)
    for aid, ability in registry.abilities.items():
        body = f"{ability.permanent_effect or ''} {ability.window_effect or ''}"
        window = ability.window
        add(ComponentCategory.ABILITY, aid, ability.name, ability.source, body, ability.faction,
            classify_trigger(window) if window else None)
    # Lider zastąpiony nowszą wersją (``homebrewReplacesID``, np. Codex ``xxchahero`` →
    # TE ``xxchahero-te``) nie występuje w grze - nie liczy się do pokrycia (RULES.md 62.9).
    replaced = {leader.replaces_id for leader in registry.leaders.values() if leader.replaces_id}
    for lid, leader in registry.leaders.items():
        if lid in replaced:
            continue
        window = leader.ability_window
        add(ComponentCategory.LEADER, lid, leader.name, leader.source,
            f"[{leader.type}] {leader.ability_text or ''}", leader.faction,
            classify_trigger(window) if window else None)
    for bid, breakthrough in registry.breakthroughs.items():
        add(ComponentCategory.BREAKTHROUGH, bid, breakthrough.name, breakthrough.source,
            breakthrough.text or "", breakthrough.faction, None)
    for uid, unit in registry.units.items():
        if unit.faction and unit.ability:
            add(ComponentCategory.UNIT, uid, unit.name, unit.source, unit.ability,
                unit.faction, None)
    for pid, planet in registry.planets.items():
        if planet.legendary_ability_name:
            add(ComponentCategory.PLANET, pid, planet.legendary_ability_name, planet.source,
                planet.legendary_ability_text or "", None, None)
    return rows


def areas_of(text: str) -> list[str]:
    """Obszary reguł wskazane przez słowa kluczowe tekstu (może być kilka lub żaden)."""
    return [name for name, pattern in AREAS if pattern.search(text)]


def kind_of(row: Row) -> str:
    """Szacowany typ hooka: wyzwalacz z okna (when/after/…) albo słowa kluczowe w tekście."""
    if row.trigger in (TriggerKind.WHEN, TriggerKind.AFTER, TriggerKind.BEFORE):
        return "TRIGGER (okno reakcji)"
    if row.trigger is TriggerKind.INSTEAD:
        return "REPLACE (instead of)"
    for name, pattern in KINDS:
        if pattern.search(row.body):
            return name
    return "—"


def _cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ")


def _snippet(text: str) -> str:
    text = " ".join(text.split())
    return _cell(text if len(text) <= SNIPPET else text[: SNIPPET - 1] + "…")


def _hook_description(fn_doc: str | None) -> str:
    if not fn_doc:
        return "—"
    return _cell(fn_doc.strip().splitlines()[0])


def _faction_families(registry: StaticDataRegistry) -> dict[str, list[FactionDef]]:
    families: dict[str, list[FactionDef]] = {}
    for faction in registry.factions.values():
        if faction.is_playable:
            families.setdefault(registry.faction_family(faction), []).append(faction)
    return families


def _section_hooks() -> list[str]:
    hooks = rules_hooks.all_hooks()
    lines = [
        "## 1. Zarejestrowane hooki", "",
        f"Razem: **{len(hooks)}**. Opis = pierwsza linia docstringu funkcji hooka.", "",
        "| Punkt zaczepienia | Rodzaj | Źródło | Komponent | Co robi |",
        "|---|---|---|---|---|",
    ]
    for hook in sorted(hooks, key=lambda h: (h.point, h.kind.value, h.source.component_id)):
        lines.append(
            f"| `{hook.point}` | {hook.kind.name} | {hook.source.kind}:{hook.source.component_id} "
            f"| {hook.covers or '—'} | {_hook_description(hook.fn.__doc__)} |"
        )
    lines += ["", "Dostępne punkty zaczepienia (stałe `POINT_*` w `core/rules_hooks.py`):", ""]
    for name, value in sorted(vars(rules_hooks).items()):
        if name.startswith("POINT_"):
            lines.append(f"- `{value}`")
    return lines + [""]


def _section_categories(rows: list[Row]) -> list[str]:
    lines = ["## 2. Pokrycie per kategoria", "",
             "| Kategoria | Komponentów | Z hookiem | % |", "|---|---:|---:|---:|"]
    by_category: dict[ComponentCategory, list[Row]] = {}
    for row in rows:
        by_category.setdefault(row.category, []).append(row)
    for category in ComponentCategory:
        group = by_category.get(category)
        if group:
            done = sum(1 for r in group if r.covered)
            lines.append(
                f"| {category.value} | {len(group)} | {done} | {100 * done / len(group):.1f} |"
            )
    return lines + [""]


def _section_triggers(rows: list[Row]) -> list[str]:
    lines = ["## 3. Rodzaj wyzwalacza (komponenty z oknem czasowym)", "",
             "| Wyzwalacz | Komponentów |", "|---|---:|"]
    triggers = Counter(r.trigger.value for r in rows if r.trigger is not None)
    for name, count in sorted(triggers.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {name} | {count} |")
    return lines + [""]


def _section_areas(rows: list[Row]) -> list[str]:
    need: Counter[str] = Counter()
    need_open: Counter[str] = Counter()
    for row in rows:
        for area in areas_of(row.text):
            need[area] += 1
            if not row.covered:
                need_open[area] += 1
    lines = ["## 4. Zapotrzebowanie na obszary reguł i typy hooków (priorytety)", "",
             "Im więcej komponentów dotyka obszaru, tym bardziej opłaca się domknąć jego punkty "
             "zaczepienia.", "",
             "| Obszar | Komponentów | Bez hooka |", "|---|---:|---:|"]
    for area, count in sorted(need.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {area} | {count} | {need_open[area]} |")
    kinds = Counter(kind_of(r) for r in rows)
    lines += ["", "Szacowany typ hooka (RULES.md 43.1 pkt 4):", "",
              "| Typ | Komponentów |", "|---|---:|"]
    for name, count in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {name} | {count} |")
    return lines + [""]


def _section_unmatched(rows: list[Row]) -> list[str]:
    unmatched = [r for r in rows if not areas_of(r.text)]
    lines = [f"## 5. Przypadki szczególne: bez dopasowania do obszaru ({len(unmatched)})", "",
             "Te komponenty nie trafiły w żadne słowo kluczowe — wymagają ręcznego przeglądu "
             "(często to unikalne mechaniki albo teksty zbyt ogólne).", "",
             "| Kategoria | Id | Nazwa | Źródło | Wyzwalacz | Tekst |", "|---|---|---|---|---|---|"]
    for r in sorted(unmatched, key=lambda x: (x.category.value, x.component_id)):
        trigger = r.trigger.value if r.trigger else "—"
        lines.append(
            f"| {r.category.value} | `{r.component_id}` | {_cell(r.name)} | {r.source} | "
            f"{trigger} | {_snippet(r.body)} |"
        )
    return lines + [""]


def _section_action_queue(rows: list[Row]) -> list[str]:
    """Kolejka: karty akcji z oknem ACTION, które nie mają jeszcze efektu (cel: komplet)."""
    queue = [
        r for r in rows
        if r.category is ComponentCategory.ACTION_CARD
        and r.trigger is TriggerKind.ACTION
        and not r.covered
    ]
    lines = [
        f"## 6. Kolejka kart ACTION do zrobienia ({len(queue)})", "",
        "Karty zagrywane jako akcja komponentu, które silnik zagrywa tylko ręcznie "
        "(odrzucenie bez efektu). "
        "Po dodaniu efektu karta znika z tej listy.", "",
        "| Id | Nazwa | Źródło | Typ (szac.) | Obszary | Tekst |", "|---|---|---|---|---|---|",
    ]
    for r in sorted(queue, key=lambda x: x.component_id):
        areas = ", ".join(a.split(" (")[0] for a in areas_of(r.text)) or "—"
        lines.append(
            f"| `{r.component_id}` | {_cell(r.name)} | {r.source} | {kind_of(r)} | {areas} | "
            f"{_snippet(r.body)} |"
        )
    return lines + [""]


def _section_factions(registry: StaticDataRegistry, rows: list[Row]) -> list[str]:
    lines = ["## 7. Frakcje (komponenty frakcyjne i pokrycie)", "",
             "Zdolności, technologie frakcyjne, liderzy, przełom i promissory notes przypisane "
             "do frakcji. Keleres (3 warianty) liczony jako jedna rodzina.", "",
             "| Frakcja | Zdolności | Tech. | Liderzy | Przełom | PN | Jedn. | Z hookiem / razem | "
             "Obszary reguł |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for family, variants in sorted(_faction_families(registry).items()):
        ids = {f.id for f in variants} | {family}
        mine = [r for r in rows if r.faction is not None and r.faction.lower() in ids]
        by = Counter(r.category for r in mine)
        areas = sorted({a.split(" (")[0] for r in mine for a in areas_of(r.text)})
        done = sum(1 for r in mine if r.covered)
        name = variants[0].name
        lines.append(
            f"| {_cell(name)} (`{family}`) | {by[ComponentCategory.ABILITY]} | "
            f"{by[ComponentCategory.TECHNOLOGY]} | {by[ComponentCategory.LEADER]} | "
            f"{by[ComponentCategory.BREAKTHROUGH]} | {by[ComponentCategory.PROMISSORY_NOTE]} | "
            f"{by[ComponentCategory.UNIT]} | {done} / {len(mine)} | {', '.join(areas) or '—'} |"
        )
    return lines + [""]


def _category_table(group: list[Row]) -> list[str]:
    """Tabela szczegółowa jednej kategorii komponentów."""
    lines = ["| Id | Nazwa | Frakcja | Wyzwalacz | Typ | Obszary | Hook | Tekst |",
             "|---|---|---|---|---|---|:---:|---|"]
    for r in sorted(group, key=lambda x: x.component_id):
        areas = ", ".join(a.split(" (")[0] for a in areas_of(r.text)) or "—"
        lines.append(
            f"| `{r.component_id}` | {_cell(r.name)} | {r.faction or '—'} | "
            f"{r.trigger.value if r.trigger else '—'} | {kind_of(r)} | {areas} | "
            f"{'✔' if r.covered else '—'} | {_snippet(r.body)} |"
        )
    return lines


def _rows_by_category(rows: list[Row]) -> dict[ComponentCategory, list[Row]]:
    by_category: dict[ComponentCategory, list[Row]] = {}
    for row in rows:
        by_category.setdefault(row.category, []).append(row)
    return by_category


def _section_details(rows: list[Row]) -> list[str]:
    lines = ["## 8. Lista szczegółowa komponentów", "",
             "Każda kategoria zwinięta; kolumna „Typ” to oszacowanie heurystyczne.", ""]
    by_category = _rows_by_category(rows)
    for category in ComponentCategory:
        group = by_category.get(category)
        if not group:
            continue
        lines += [f"<details><summary>{category.value} ({len(group)})</summary>", "",
                  *_category_table(group), "", "</details>", ""]
    return lines


_HEADER = [
    "# Pokrycie hooków (generowany — nie edytuj ręcznie)", "",
    "Wygenerowano: `uv run python -m src.audit.hook_coverage --write`. Zasady: `RULES.md` 43.",
    "Obszary reguł i typ hooka to HEURYSTYKA po słowach kluczowych "
    "(priorytetyzacja, nie decyzja).", "",
]


def render_markdown(registry: StaticDataRegistry) -> str:
    """Składa PEŁNY raport w jednym Markdownie (``--print``; deterministyczny)."""
    rows = collect_rows(registry)
    lines: list[str] = list(_HEADER)
    for section in (
        _section_hooks(),
        _section_categories(rows),
        _section_triggers(rows),
        _section_areas(rows),
        _section_unmatched(rows),
        _section_action_queue(rows),
        _section_factions(registry, rows),
        _section_details(rows),
    ):
        lines += section
    return "\n".join(lines)


def render_files(registry: StaticDataRegistry) -> dict[str, str]:
    """Raport podzielony na pliki (oszczędność kontekstu): nazwa względem ``docs/`` -> treść.

    ``POKRYCIE_HOOKOW.md`` to krótkie podsumowanie (sekcje 2, 3, 4, 6, 7 + spis);
    ciężkie sekcje (lista hooków, przypadki szczególne, tabele per kategoria) trafiają do
    ``docs/pokrycie_hookow/``.
    """
    rows = collect_rows(registry)
    by_category = _rows_by_category(rows)
    files: dict[str, str] = {}
    toc = [
        "## Spis plików szczegółowych (czytaj punktowo, tylko gdy potrzebne)", "",
        "- [`pokrycie_hookow/hooki.md`](pokrycie_hookow/hooki.md) — sekcja 1: zarejestrowane "
        "hooki i punkty zaczepienia.",
        "- [`pokrycie_hookow/przypadki_szczegolne.md`](pokrycie_hookow/przypadki_szczegolne.md)"
        " — sekcja 5: komponenty bez dopasowania do obszaru.",
    ]
    for category in ComponentCategory:
        group = by_category.get(category)
        if not group:
            continue
        name = f"pokrycie_hookow/szczegoly_{category.value}.md"
        done = sum(1 for r in group if r.covered)
        toc.append(
            f"- [`{name}`]({name}) — sekcja 8: {category.value} ({done} / {len(group)} z hookiem)."
        )
        files[name] = "\n".join([
            f"# Pokrycie hooków: {category.value} ({len(group)})", "",
            "Generowany — nie edytuj. Podsumowanie: [`../POKRYCIE_HOOKOW.md`]"
            "(../POKRYCIE_HOOKOW.md). Kolumna „Typ” to oszacowanie heurystyczne.", "",
            *_category_table(group), "",
        ])
    files["pokrycie_hookow/hooki.md"] = "\n".join([
        "# Pokrycie hooków: zarejestrowane hooki", "",
        "Generowany — nie edytuj. Podsumowanie: [`../POKRYCIE_HOOKOW.md`](../POKRYCIE_HOOKOW.md).",
        "", *_section_hooks(),
    ])
    files["pokrycie_hookow/przypadki_szczegolne.md"] = "\n".join([
        "# Pokrycie hooków: przypadki szczególne", "",
        "Generowany — nie edytuj. Podsumowanie: [`../POKRYCIE_HOOKOW.md`](../POKRYCIE_HOOKOW.md).",
        "", *_section_unmatched(rows),
    ])
    hooks_total = len(rules_hooks.all_hooks())
    summary = list(_HEADER)
    summary += [
        f"Zarejestrowanych hooków: **{hooks_total}** (lista: `pokrycie_hookow/hooki.md`).", "",
    ]
    for section in (
        _section_categories(rows),
        _section_triggers(rows),
        _section_areas(rows),
        _section_action_queue(rows),
        _section_factions(registry, rows),
        toc + [""],
    ):
        summary += section
    files["POKRYCIE_HOOKOW.md"] = "\n".join(summary)
    return files


def write_files(files: dict[str, str]) -> list[Path]:
    """Zapisuje pliki raportu w ``docs/``; usuwa nieaktualne ``pokrycie_hookow/*.md``."""
    docs = DOC_PATH.parent
    parts_dir = docs / "pokrycie_hookow"
    parts_dir.mkdir(parents=True, exist_ok=True)
    for old in parts_dir.glob("*.md"):
        if f"pokrycie_hookow/{old.name}" not in files:
            old.unlink()
    written: list[Path] = []
    for name, text in sorted(files.items()):
        path = docs / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    """CLI: wypisuje pełny raport albo zapisuje go podzielony na pliki (``--write``)."""
    parser = argparse.ArgumentParser(description="Raport pokrycia hooków (H3).")
    parser.add_argument(
        "--write", action="store_true",
        help="zapisz do docs/POKRYCIE_HOOKOW.md + docs/pokrycie_hookow/*.md",
    )
    args = parser.parse_args(argv)
    registry = StaticDataRegistry()
    if args.write:
        for path in write_files(render_files(registry)):
            print(f"Zapisano {path}")
    else:
        print(render_markdown(registry))
    return 0


if __name__ == "__main__":
    sys.exit(main())
