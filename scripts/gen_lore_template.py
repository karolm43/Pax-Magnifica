"""Szablon pól lore kart: ``frontend/src/entities/lore/cardLore.ts``.

Użytkownik wpisuje tekst fabularny (flavour) do pustych pól; skrypt tylko DODAJE brakujące wpisy
(karty z aktywnych źródeł z ``assets/enabled_sources.json``) i NIGDY nie rusza już wpisanych tekstów.
Pomija typy kart, które mają flavour w assetach AsyncTI4 (akcje, relikty, eksploracja) —
tam pole ``flavorText`` jest już w danych.

Format wpisu (jedna linia, string JSON): ``"id": "tekst", // Nazwa karty``.
Uruchomienie: ``uv run python scripts/gen_lore_template.py``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "src" / "entities" / "lore" / "cardLore.ts"

# rodzaj -> (folder assetów, pole z id, opis do komentarza sekcji)
KINDS: dict[str, tuple[str, str, str]] = {
    "leader": ("leaders", "id", "Leaders (agent / commander / hero)"),
    "agenda": ("agendas", "alias", "Agendas"),
    "promissoryNote": ("promissory_notes", "alias", "Promissory notes"),
    "publicObjective": ("public_objectives", "alias", "Public objectives"),
    "secretObjective": ("secret_objectives", "alias", "Secret objectives"),
    "technology": ("technologies", "alias", "Technologies"),
    "breakthrough": ("breakthroughs", "alias", "Breakthroughs (Thunder's Edge)"),
    "ability": ("abilities", "id", "Faction abilities"),
}

_ENTRY = re.compile(r'^\s*"([^"]+)":\s*("(?:[^"\\]|\\.)*"),')


def _existing() -> dict[str, dict[str, str]]:
    """Wpisane już teksty: ``{rodzaj: {id: literał JSON}}`` (puste też, by nie dublować)."""
    found: dict[str, dict[str, str]] = {}
    if not OUT.exists():
        return found
    kind: str | None = None
    for line in OUT.read_text(encoding="utf-8").splitlines():
        head = re.match(r"^const (\w+): LoreMap = \{", line)
        if head:
            kind = head.group(1)
            found[kind] = {}
        elif kind and (m := _ENTRY.match(line)):
            found[kind][m.group(1)] = m.group(2)
    return found


def _cards(kind: str) -> list[tuple[str, str]]:
    """Karty rodzaju ``kind`` z aktywnych źródeł: ``(id, etykieta do komentarza)``."""
    folder, key, _ = KINDS[kind]
    enabled = set(json.loads((ROOT / "assets" / "enabled_sources.json").read_text("utf-8")))
    out: dict[str, str] = {}
    for path in sorted((ROOT / "assets" / "data" / folder).glob("*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if isinstance(item, dict) and item.get("source") in enabled and item.get(key):
                label = str(item.get("name", "")).replace("\n", " ")
                if kind == "leader":  # imię lidera nic nie mówi — dopisz frakcję i rolę
                    label += f" ({item.get('faction', '?')} {item.get('type', '')})".rstrip()
                out.setdefault(str(item[key]), label)
    return sorted(out.items(), key=lambda kv: kv[1].lower())


def main() -> None:
    existing = _existing()
    lines = [
        "// Pola na lore (flavour) kart — WPISUJE UŻYTKOWNIK. Pusty string = brak (nic się nie wyświetla).",
        "// Jeden wpis = jedna linia, tekst w cudzysłowie: \"id\": \"Twój tekst.\", // Nazwa karty",
        "// Skrypt scripts/gen_lore_template.py dopisuje brakujące karty i nie rusza wpisanych tekstów.",
        "// Akcje, relikty i eksploracja mają flavour w assetach AsyncTI4 (pole flavorText) — tu ich nie ma.",
        "",
        "export type LoreMap = Record<string, string>;",
        "",
    ]
    names: list[str] = []
    for kind, (_, _, title) in KINDS.items():
        entries = dict(existing.get(kind, {}))
        for card_id, name in _cards(kind):
            entries.setdefault(card_id, '""')
        label = {cid: n for cid, n in _cards(kind)}
        lines.append(f"/** {title}. */")
        lines.append(f"const {kind}: LoreMap = {{")
        for card_id in sorted(entries, key=lambda c: (label.get(c, c).lower(), c)):
            comment = f" // {label[card_id]}" if card_id in label else ""
            lines.append(f"  {json.dumps(card_id)}: {entries[card_id]},{comment}")
        lines += ["};", ""]
        names.append(kind)
    lines.append("export const CARD_LORE = {")
    lines += [f"  {n}," for n in names]
    lines += ["} as const satisfies Record<string, LoreMap>;", "", "export type LoreKind = keyof typeof CARD_LORE;", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"zapisano {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
