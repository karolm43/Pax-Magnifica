# ruff: noqa: E501  (generator raportu: długie teksty opisów są celowe)
"""Katalog okien czasowych WSZYSTKICH komponentów (RULES.md 54) -> ``docs/OKNA_CZASOWE.md``.

Przechodzi po każdej agendzie (standard + Absol), karcie akcji, relikcie, notce, karcie eksploracji,
wydarzeniu galaktycznym, zdolności frakcji, liderze, technologii i przełomie, i dla każdego ustala:
* okno czasowe z pola ``window`` / ``abilityWindow`` albo z pierwszej klauzuli czasowej w tekście
  (``core/game_events.classify_window`` -> zdarzenie + moment + filtry);
* rodzaj: akcja komponentu, reakcja w oknie, efekt przy zdobyciu, efekt trwały, efekt ciągły;
* czasy trwania („until the end of ...”, „while this law is in play”) i odroczone wyzwalacze;
* czy zdarzenie jest już EMITOWANE przez silnik (``EVENT_INFO.emitted_by``).

Klasyfikacja to HEURYSTYKA po słowach kluczowych — sekcja „Przypadki szczególne” pokazuje wszystko,
co nie zostało przypisane. Generowane: ``uv run python -m src.audit.timing_catalog --write``.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from src.core.components import ComponentCategory
from src.core.game_events import (
    EVENT_INFO,
    Clause,
    Duration,
    GameEvent,
    Moment,
    WindowRef,
    classify_window,
    deferred_phase,
    find_clauses,
    find_durations,
)
from src.core.models import FactionDef
from src.core.registry import StaticDataRegistry

DOC_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "OKNA_CZASOWE.md"
SNIPPET = 110
_ACTION_BODY = re.compile(r"(?:^|\n|[.!?]\s)ACTION:|^\s*ACTION\b")

_KIND_LABEL = {
    "action": "akcja komponentu",
    "timed": "reakcja w oknie",
    "gain": "przy zdobyciu",
    "persistent": "efekt trwały",
    "passive": "efekt ciągły",
    "agenda": "wynik agendy",
}


@dataclass(frozen=True)
class Entry:
    """Jeden komponent z ustalonym oknem czasowym."""

    category: str
    cid: str
    name: str
    source: str
    faction: str | None
    kind: str
    window: WindowRef | None
    window_text: str | None
    clauses: tuple[Clause, ...]
    durations: tuple[Duration, ...]
    deferred: str | None
    optional: bool
    body: str

    @property
    def key(self) -> str:
        return f"{self.category}:{self.cid}"


def _build(
    category: str,
    cid: str,
    name: str | None,
    source: str,
    faction: str | None,
    window_text: str | None,
    body: str,
    *,
    agenda: bool = False,
) -> Entry:
    body = " ".join(body.split())
    clauses = tuple(find_clauses(body))
    field_window = classify_window(window_text)
    first_clause = next((c.window for c in clauses if c.window is not None), None)
    gain = next(
        (c.window for c in clauses if c.window and c.window.event is GameEvent.COMPONENT_GAINED),
        None,
    )
    durations = tuple(find_durations(body))
    if agenda:
        kind, window = "agenda", WindowRef(GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER)
    elif field_window is not None and field_window.moment is Moment.ACTION:
        kind, window = "action", field_window
    elif _ACTION_BODY.search(body):
        kind, window = "action", WindowRef(GameEvent.COMPONENT_ACTION, Moment.ACTION)
    elif field_window is not None:
        kind, window = "timed", field_window
    elif gain is not None:
        kind, window = "gain", gain
    elif first_clause is not None:
        kind, window = "timed", first_clause
    elif Duration.WHILE_IN_PLAY in durations:
        kind, window = "persistent", None
    else:
        kind, window = "passive", None
    return Entry(
        category,
        cid,
        name or cid,
        source,
        faction,
        kind,
        window,
        window_text,
        clauses,
        durations,
        deferred_phase(body),
        bool(re.search(r"\bmay\b", body.lower())),
        body,
    )


def collect(registry: StaticDataRegistry) -> list[Entry]:
    """Zbiera wpisy dla wszystkich komponentów podlegających oknom czasowym."""
    entries: list[Entry] = []
    catalog = registry.catalog
    for category in (
        ComponentCategory.AGENDA,
        ComponentCategory.ACTION_CARD,
        ComponentCategory.RELIC,
        ComponentCategory.PROMISSORY_NOTE,
        ComponentCategory.EXPLORATION,
        ComponentCategory.GALACTIC_EVENT,
    ):
        for cid, comp in sorted(catalog.all(category).items()):
            body = " ".join(comp.texts.values())
            agenda = category is ComponentCategory.AGENDA
            if agenda:
                body = f"{getattr(comp, 'target', '') or ''}. {body}"
            entries.append(
                _build(
                    category.value,
                    cid,
                    comp.name,
                    comp.source,
                    getattr(comp, "faction", None),
                    comp.window,
                    body,
                    agenda=agenda,
                )
            )
    for cid, ability in sorted(registry.abilities.items()):
        body = f"{ability.permanent_effect or ''} {ability.window_effect or ''}"
        entries.append(
            _build(
                "abilities",
                cid,
                ability.name,
                ability.source,
                ability.faction,
                ability.window,
                body,
            )
        )
    for cid, leader in sorted(registry.leaders.items()):
        entries.append(
            _build(
                "leaders",
                cid,
                leader.name,
                leader.source,
                leader.faction,
                leader.ability_window,
                f"[{leader.type}] {leader.ability_text or ''}",
            )
        )
    for cid, tech in sorted(registry.technologies.items()):
        entries.append(
            _build("technologies", cid, tech.name, tech.source, tech.faction, None, tech.text or "")
        )
    for cid, bt in sorted(registry.breakthroughs.items()):
        entries.append(
            _build("breakthroughs", cid, bt.name, bt.source, bt.faction, None, bt.text or "")
        )
    return entries


def _cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ")


def _snip(text: str) -> str:
    text = " ".join(text.split())
    return _cell(text if len(text) <= SNIPPET else text[: SNIPPET - 1] + "…")


def _fmt(window: WindowRef | None) -> str:
    if window is None:
        return "—"
    ctx = ",".join(f"{k}={v}" for k, v in window.ctx)
    extra = ["would"] if window.would else []
    if window.once_per:
        extra.append(f"1/{window.once_per}")
    suffix = f" [{'; '.join([*(ctx.split(',') if ctx else []), *extra])}]" if (ctx or extra) else ""
    return f"`{window.event.value}` · {window.moment.value}{suffix}"


def _static_contract() -> list[str]:
    return [
        "# Okna czasowe komponentów (generowany — nie edytuj ręcznie)",
        "",
        "Wygenerowano: `uv run python -m src.audit.timing_catalog --write`. Opis kontraktu: `RULES.md` 54, "
        "kod: `core/game_events.py` (zdarzenia, klasyfikator), `core/triggers.py` (emisja), "
        "`core/active_effects.py` (efekty trwałe).",
        "Klasyfikacja to HEURYSTYKA po słowach kluczowych; wszystko, co nie dostało zdarzenia, jest w "
        "sekcji „Przypadki szczególne”.",
        "",
        "## 1. Kontrakt silnika (skrót)",
        "",
        "* **Okno = para (zdarzenie, moment)** + filtry kontekstu (np. `phase=strategy`). Momenty: "
        "`before`, `when`, `after`, `start`, `end`, `during`, `instead`, `any`, `action`.",
        "* **Kolejność** (R_abilities): wszystkie `when` przed `after`; wszystkie `after` przed następnym "
        "`before`. Ta sama chwila w fazie akcji: kolejność inicjatywy od gracza aktywnego; w fazie "
        "strategii i agendy: od mówcy zgodnie z zegarem.",
        "* **Obowiązkowe vs opcjonalne:** zdolność z komponentu w grze jest obowiązkowa, chyba że ma „may” "
        "(wtedy silnik tworzy ofertę i otwiera okno REACTION dla graczy z publicznym źródłem).",
        "* **Karty z ręki** (karty akcji, ukryte notki) NIE tworzą ofert — grane są przez STOP "
        "(RULES.md 43.4), żeby pytanie nie zdradzało ręki.",
        "* **Efekt trwały:** zakres `turn`, `tactical_action`, `combat`, `combat_round`, `phase`, `round`, "
        "`game` albo `while_in_play`; wygasa na zdarzeniach końca zakresu. Efekt z określonym czasem trwania "
        "zostaje, nawet gdy komponent zniknie (R_abilities).",
        "* **`would`** w oknie („when you would ...”) = przed skutkiem; to miejsce na zastąpienie (REPLACE).",
        "",
    ]


def _section_events(entries: list[Entry]) -> list[str]:
    usage: dict[GameEvent, Counter[str]] = defaultdict(Counter)
    moments: dict[GameEvent, Counter[str]] = defaultdict(Counter)
    for e in entries:
        if e.window is not None:
            usage[e.window.event][e.category] += 1
            moments[e.window.event][e.window.moment.value] += 1
    lines = [
        "## 2. Zdarzenia: kto ich potrzebuje i czy silnik je emituje",
        "",
        "`Emisja` = funkcja silnika, która woła `triggers.fire` (— = zdarzenie tylko zdefiniowane).",
        "",
        "| Zdarzenie | Znaczenie | Komponentów | Momenty | Kategorie | Emisja |",
        "|---|---|---:|---|---|---|",
    ]
    for event in GameEvent:
        info = EVENT_INFO.get(event)
        total = sum(usage[event].values())
        mom = ", ".join(f"{m}×{n}" for m, n in moments[event].most_common())
        cats = ", ".join(f"{c}×{n}" for c, n in usage[event].most_common())
        lines.append(
            f"| `{event.value}` | {_cell(info.summary) if info else '—'} | {total} | {mom or '—'} | "
            f"{cats or '—'} | {('`' + info.emitted_by + '`') if info and info.emitted_by else '—'} |"
        )
    wired = sum(1 for i in EVENT_INFO.values() if i.emitted_by)
    needed = {e.window.event for e in entries if e.window is not None}
    missing = sorted(
        (ev.value for ev in needed if not (EVENT_INFO.get(ev) and EVENT_INFO[ev].emitted_by)),
    )
    lines += [
        "",
        f"Zdarzeń zdefiniowanych: **{len(GameEvent)}**, emitowanych przez silnik: **{wired}**. "
        f"Potrzebne komponentom, a jeszcze nie emitowane: **{len(missing)}**.",
        "",
        "Nieemitowane, ale potrzebne: " + (", ".join(f"`{m}`" for m in missing) or "—"),
        "",
    ]
    return lines


def _section_kinds(entries: list[Entry]) -> list[str]:
    table: dict[str, Counter[str]] = defaultdict(Counter)
    for e in entries:
        table[e.category][e.kind] += 1
    kinds = list(_KIND_LABEL)
    lines = [
        "## 3. Rodzaje komponentów wg kategorii",
        "",
        "| Kategoria | " + " | ".join(_KIND_LABEL[k] for k in kinds) + " | razem |",
        "|---|" + "---:|" * (len(kinds) + 1),
    ]
    for category, counts in sorted(table.items()):
        lines.append(
            f"| {category} | "
            + " | ".join(str(counts[k]) for k in kinds)
            + f" | {sum(counts.values())} |"
        )
    return lines + [""]


def _section_durations(entries: list[Entry]) -> list[str]:
    persistent = [e for e in entries if e.durations or e.deferred]
    lines = [
        f"## 4. Efekty trwałe i czasy trwania ({len(persistent)})",
        "",
        "Zakres wygasania wykryty w tekście. `deferred` = „at the start of the next ... phase” "
        "(odroczony wyzwalacz; hook na `phase`/`start` sprawdza efekt w magazynie).",
        "",
        "| Komponent | Nazwa | Zakresy | deferred | Tekst |",
        "|---|---|---|---|---|",
    ]
    for e in persistent:
        durations = ", ".join(d.value for d in e.durations) or "—"
        lines.append(
            f"| `{e.key}` | {_cell(e.name)} | {durations} | {e.deferred or '—'} | {_snip(e.body)} |"
        )
    return lines + [""]


def _section_agendas(entries: list[Entry]) -> list[str]:
    agendas = [e for e in entries if e.category == "agendas"]
    by_source = Counter(e.source for e in agendas)
    lines = [
        f"## 5. Agendy ({len(agendas)}: "
        + ", ".join(f"{s}×{n}" for s, n in sorted(by_source.items()))
        + ")",
        "",
        "Każda agenda: efekt wyniku rozstrzyga się `agenda.outcome_resolved`/`after`; prawo zostaje w grze "
        "(`while_in_play`), a jego klauzule czasowe stają się hookami prawa (`SOURCE_AGENDA`). "
        "Kolumna „Klauzule” to okna WEWNĄTRZ tekstu agendy.",
        "",
        "| Id | Nazwa | Źródło | Typ | Klauzule czasowe w tekście | Trwanie | Tekst |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in agendas:
        clause_cells = (
            "; ".join(_fmt(c.window) if c.window else f"? {_snip(c.text)[:40]}" for c in e.clauses)
            or "—"
        )
        kind = (
            "law"
            if re.search(r"\blaw\b", e.body[:200].lower()) or "while" in e.body.lower()
            else "—"
        )
        lines.append(
            f"| `{e.cid}` | {_cell(e.name)} | {e.source} | {kind} | {_cell(clause_cells)} | "
            f"{', '.join(d.value for d in e.durations) or '—'} | {_snip(e.body)} |"
        )
    return lines + [""]


def _faction_groups(registry: StaticDataRegistry) -> dict[str, tuple[str, set[str]]]:
    families: dict[str, list[FactionDef]] = {}
    for faction in registry.factions.values():
        if faction.is_playable:
            families.setdefault(registry.faction_family(faction), []).append(faction)
    return {
        family: (variants[0].name, {f.id for f in variants} | {family})
        for family, variants in sorted(families.items())
    }


def _section_factions(registry: StaticDataRegistry, entries: list[Entry]) -> list[str]:
    lines = [
        "## 6. Frakcje: zdolności, liderzy, technologie, przełomy, notki",
        "",
        "Dla każdej frakcji komponenty z oknem (reakcja/akcja/przy zdobyciu) i efekty ciągłe.",
        "",
    ]
    for family, (name, ids) in _faction_groups(registry).items():
        mine = [e for e in entries if e.faction is not None and e.faction.lower() in ids]
        if not mine:
            continue
        lines += [
            f"### {_cell(name)} (`{family}`) — {len(mine)} komponentów",
            "",
            "| Komponent | Nazwa | Rodzaj | Okno | Opc. | Tekst |",
            "|---|---|---|---|:---:|---|",
        ]
        for e in mine:
            lines.append(
                f"| `{e.key}` | {_cell(e.name)} | {_KIND_LABEL[e.kind]} | {_fmt(e.window)} | "
                f"{'tak' if e.optional else '—'} | {_snip(e.body)} |"
            )
        lines.append("")
    return lines


def _section_by_event(entries: list[Entry], categories: set[str], title: str) -> list[str]:
    groups: dict[str, list[Entry]] = defaultdict(list)
    for e in entries:
        if e.category in categories:
            key = e.window.event.value if e.window else f"({_KIND_LABEL[e.kind]})"
            groups[key].append(e)
    lines = [title, ""]
    for key in sorted(groups):
        group = groups[key]
        lines += [
            f"### `{key}` ({len(group)})",
            "",
            "| Komponent | Nazwa | Okno | Źródło | Tekst |",
            "|---|---|---|---|---|",
        ]
        for e in group:
            lines.append(
                f"| `{e.key}` | {_cell(e.name)} | {_fmt(e.window)} | {e.source} | {_snip(e.body)} |"
            )
        lines.append("")
    return lines


def _section_special(entries: list[Entry]) -> list[str]:
    unmapped_field = [
        e for e in entries if e.window_text and classify_window(e.window_text) is None
    ]
    unmapped_clause = [(e, c) for e in entries for c in e.clauses if c.window is None]
    lines = [
        "## 9. Przypadki szczególne (bez przypisanego zdarzenia)",
        "",
        f"* pole okna bez dopasowania: **{len(unmapped_field)}**",
        f"* klauzule w tekście bez dopasowania: **{len(unmapped_clause)}**",
        "",
        "### Pola okna bez dopasowania",
        "",
        "| Komponent | Nazwa | Fraza okna |",
        "|---|---|---|",
    ]
    for e in unmapped_field:
        lines.append(f"| `{e.key}` | {_cell(e.name)} | {_snip(e.window_text or '')} |")
    lines += [
        "",
        "### Klauzule w tekście bez dopasowania",
        "",
        "| Komponent | Nazwa | Klauzula |",
        "|---|---|---|",
    ]
    for e, c in unmapped_clause:
        lines.append(f"| `{e.key}` | {_cell(e.name)} | {_snip(c.text)} |")
    return lines + [""]


def render_markdown(registry: StaticDataRegistry) -> str:
    """Składa raport (deterministyczny dla tych samych danych)."""
    entries = collect(registry)
    lines: list[str] = []
    lines += _static_contract()
    lines += _section_events(entries)
    lines += _section_kinds(entries)
    lines += _section_durations(entries)
    lines += _section_agendas(entries)
    lines += _section_factions(registry, entries)
    lines += _section_by_event(entries, {"action_cards"}, "## 7. Karty akcji wg zdarzenia")
    lines += _section_by_event(
        entries,
        {"relics", "promissory_notes", "explores", "galactic_events"},
        "## 8. Relikty, notki, eksploracja i wydarzenia wg zdarzenia",
    )
    lines += _section_special(entries)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI: wypisuje raport albo zapisuje ``docs/OKNA_CZASOWE.md`` (``--write``)."""
    parser = argparse.ArgumentParser(description="Katalog okien czasowych komponentów.")
    parser.add_argument("--write", action="store_true", help="zapisz do docs/OKNA_CZASOWE.md")
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
