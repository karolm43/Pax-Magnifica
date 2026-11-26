"""Szablon pól lore kart: ``frontend/src/entities/lore/cardLore.ts``.

Użytkownik wpisuje tekst fabularny (flavour) do pustych pól; skrypt DODAJE brakujące wpisy
i NIGDY nie rusza już wpisanych tekstów. Karty akcji, relikty, eksploracja, systemy i planety dostają jako tekst startowy flavour z
assetów/danych gry (``flavorText``); odtąd edytujesz go tu (wpisany tekst nigdy nie jest nadpisywany).

Skład wpisów = karty, które SILNIK naprawdę używa (nie „wszystko z włączonych źródeł”):
- agendy/cele: aktywne talie (``core.objectives.deck_card_ids``) — bez 13 agend usuniętych w PoK;
- liderzy/zdolności/notki frakcyjne: listy frakcji z rejestru (z podmianami TE,
  np. ``xxchahero-te``);
- technologie: ``technology.generic_pool`` (najnowsza wersja Ω/ΩΩ) + technologie frakcji
  (bez tych zastąpionych przełomami TE, np. ``iihq``).
Pusty wpis karty, której silnik już nie używa, znika; wpis z tekstem zostaje (ostrzeżenie).

Talia agend Absol: karty o tej samej nazwie co oficjalne dostają ALIAS (``LORE_ALIASES``) i
czytają lore oficjalnej karty; tylko nowe karty Absol mają własne pola.

Format wpisu (jedna linia, string JSON): ``"id": "tekst", // Nazwa karty``.
Uruchomienie: ``uv run python scripts/gen_lore_template.py``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core import variants  # noqa: E402
from src.core.game_setup import common_promissory_note_ids  # noqa: E402
from src.core.objectives import deck_card_ids  # noqa: E402
from src.core.registry import StaticDataRegistry  # noqa: E402
from src.core.technology import generic_pool  # noqa: E402

OUT = ROOT / "frontend" / "src" / "entities" / "lore" / "cardLore.ts"

# rodzaj -> (folder assetów, pole z id, opis do komentarza sekcji)
KINDS: dict[str, tuple[str, str, str]] = {
    "leader": ("leaders", "id", "Leaders (agent / commander / hero)"),
    "agenda": ("agendas", "alias", "Agendas (official deck + new Absol cards)"),
    "promissoryNote": ("promissory_notes", "alias", "Promissory notes"),
    "publicObjective": ("public_objectives", "alias", "Public objectives"),
    "secretObjective": ("secret_objectives", "alias", "Secret objectives"),
    "technology": ("technologies", "alias", "Technologies"),
    "breakthrough": ("breakthroughs", "alias", "Breakthroughs (Thunder's Edge)"),
    "ability": ("abilities", "id", "Faction abilities"),
    "attachment": ("attachments", "id", "Attachments (planet tokens)"),
    "feature": ("tokens", "id", "Map features: anomalies, wormholes, borders and board tokens"),
    "unit": ("units", "id", "Faction units (flagships, mechs, unique ships/ground forces)"),
    "actionCard": ("action_cards", "alias", "Action cards"),
    "relic": ("relics", "alias", "Relics"),
    "exploration": ("explores", "id", "Exploration cards"),
    "plot": ("genericcards", "alias", "Plot cards (Firmament / Obsidian)"),
    "system": ("", "id", "Systems (map tiles)"),
    "planet": ("", "id", "Planets"),
}
# Rodzaje z flavourem już istniejącym w danych gry: tekst z assetów JSON (pole ``flavorText`` /
# ``flavourText``) albo z wygenerowanych plików TS (systemy, planety). Trafia do pola JAKO
# PODPOWIEDŹ startowa — dalej edytujesz go tylko w cardLore.ts (wpisany tekst wygrywa).
PREFILLED = {"actionCard", "relic", "exploration", "system", "planet"}
# Rodzaje z danych TS (nie ma ich w assets/data): plik, pole nazwy.
TS_KINDS = {
    "system": ROOT / "frontend" / "src" / "entities" / "data" / "systems.ts",
    "planet": ROOT / "frontend" / "src" / "entities" / "data" / "planets.ts",
}

# Źródła oficjalne (assets/enabled_sources.json) — tylko ich żetony i attachmenty dostają pola.
OFFICIAL_SOURCES = {"base", "pok", "codex1", "codex2", "codex3", "codex4", "thunders_edge"}
# Cechy mapy niebędące żetonem w assetach: id pola -> nazwa (klucze zgodne z featureRules.ts).
STATIC_FEATURES = {
    "wormhole_alpha": "Alpha Wormhole",
    "wormhole_beta": "Beta Wormhole",
    "wormhole_gamma": "Gamma Wormhole",
    "wormhole_delta": "Delta Wormhole",
    "wormhole_epsilon": "Epsilon Wormhole",
    "void_tether": "Void Tether (border)",
    "spatial_tear": "Spatial Tear (border)",
}
# Warianty/duplikaty żetonów (inne wersje tego samego, żetony wormhole mają własne pola).
SKIPPED_TOKENS = {
    "custodianvp", "custc1", "custvpc1", "gamma", "creussalpha", "creussbeta", "creussgamma",
    "anomaly", "big_obelisk",
}


def _clean_flavour(text: object) -> str:
    """Flavour z danych: bez kursywy ``*...*`` (komponenty i tak jej nie pokazują)."""
    return re.sub(r"^\*+|\*+$", "", str(text or "").strip()).strip()


_TS_BLOCK = re.compile(r"\n  \{\n")
_TS_STR = r'("(?:[^"\\]|\\.)*")'


def _ts_items(kind: str) -> list[dict[str, str]]:
    """Wpisy z wygenerowanego pliku TS (systemy/planety): id, name, source, flavourText."""
    out: list[dict[str, str]] = []
    for block in _TS_BLOCK.split(TS_KINDS[kind].read_text(encoding="utf-8"))[1:]:
        item: dict[str, str] = {}
        block = "\n" + block  # rozcięcie zjadło newline sprzed pierwszego pola
        for field in ("id", "name", "source", "flavourText"):
            m = re.search(rf'\n    "?{field}"?:\s*{_TS_STR}', block)
            if m:
                item[field] = json.loads(m.group(1))
        if item.get("id"):
            out.append(item)
    return out


def _prefill(kind: str) -> dict[str, str]:
    """Istniejący flavour oficjalnych kart ``id -> tekst`` (tylko niepuste)."""
    out: dict[str, str] = {}
    if kind in TS_KINDS:
        for item in _ts_items(kind):
            text = _clean_flavour(item.get("flavourText"))
            if item.get("source") in OFFICIAL_SOURCES and text:
                out.setdefault(item["id"], text)
        return out
    folder, key, _ = KINDS[kind]
    for path in sorted((ROOT / "assets" / "data" / folder).glob("*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if not isinstance(item, dict) or item.get("source") not in OFFICIAL_SOURCES:
                continue
            text = _clean_flavour(item.get("flavorText") or item.get("flavourText"))
            if item.get(key) and text:
                out.setdefault(str(item[key]), text)
    return out


def _official_plots() -> set[str]:
    """Karty Plot oficjalnych źródeł (genericcards z ``cardType == plot``)."""
    out: set[str] = set()
    for path in (ROOT / "assets" / "data" / "genericcards").glob("*.json"):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if (
                isinstance(item, dict)
                and item.get("cardType") == "plot"
                and item.get("source") in OFFICIAL_SOURCES
            ):
                out.add(str(item["alias"]))
    return out


def _official_ids(folder: str) -> set[str]:
    out: set[str] = set()
    for path in (ROOT / "assets" / "data" / folder).glob("*.json"):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if isinstance(item, dict) and item.get("source") in OFFICIAL_SOURCES and item.get("id"):
                out.add(str(item["id"]))
    return out


def _explored_attachments() -> set[str]:
    """Attachmenty z kart eksploracji oficjalnych źródeł (ich source bywa pusty = base/pok)."""
    out: set[str] = set()
    for path in (ROOT / "assets" / "data" / "explores").glob("*.json"):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if isinstance(item, dict) and item.get("source") in OFFICIAL_SOURCES:
                att = item.get("attachmentId")
                if att:
                    out.add(str(att))
    return out


# Jednostki ogólne: karta jednostki czyta pole po id bazowym (ulepszenia je dziedziczą).
GENERIC_UNITS = {
    "fighter", "infantry", "destroyer", "cruiser", "carrier",
    "dreadnought", "warsun", "pds", "spacedock",
}

# Karty spoza list frakcji, które mimo to mają własną kartę w grze (przełomy, The Cavalry, …).
EXTRA_CARDS = {
    "unit": {"mentak_cruiser3", "naaz_voltron", "cavalry1", "ghemina_carrier"},
    "promissoryNote": {"rider"},  # Keleres Rider
    "relic": {"enigmaticdevice"},
}
# Ta sama jednostka pod innym id: czyta pole wskazanej (jak agendy Absol).
UNIT_ALIASES = {
    "absol_naaz_mech_space": "naaz_mech_space",
    "cavalry2": "cavalry1",
    "naalu_mech": "naalu_mech_te",
    "naalu_mech_omega": "naalu_mech_te",
}

# Moduł talii agend Absol (assets/config/variants.json).
ABSOL_AGENDAS = "absol_agendas"
# Karty Absol przemianowane względem oficjalnych (ta sama karta, inna nazwa).
ABSOL_RENAMED = {
    "absol_leak": "classified",  # Classified Document Leak(s)
    "absol_grant": "grant_reallocation",  # Research Grant (Re)allocation
}

HEADER = (
    "// Pola na lore (flavour) kart — WPISUJE UŻYTKOWNIK. Pusty string = brak"
    " (nic się nie wyświetla).",
    "// Jeden wpis = jedna linia, tekst w cudzysłowie: \"id\": \"Twój tekst.\", // Nazwa karty",
    "// Skrypt scripts/gen_lore_template.py dopisuje brakujące karty i nie rusza wpisanych"
    " tekstów.",
    "// Lista = karty używane przez silnik (aktywne talie, frakcje, najnowsze wersje kart"
    " Codex/TE).",
    "// Karty akcji, relikty, eksploracja, systemy i planety: tekst startowy skopiowany z assetów"
    " AsyncTI4 — tu go edytujesz.",
    "// Pozostałe teksty w TYM folderze (entities/lore/): factionLore.ts (lore, cytaty, portrety frakcji),",
    "// factionVoiceLines.ts (kwestie frakcji w czacie), chronicleLore.ts (Kronika Imperium),",
    "// battleLore.ts (opisy bitew w oknie wyniku i w kronice).",
)

_ENTRY = re.compile(r'^\s*"([^"]+)":\s*("(?:[^"\\]|\\.)*"),(?:\s*//\s*(.*))?$')


def _existing() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    """Wpisane już teksty ``{rodzaj: {id: literał JSON}}`` (puste też) i komentarze wpisów
    (użytkownik może je doprecyzować, np. frakcją notki — skrypt ich nie nadpisuje)."""
    found: dict[str, dict[str, str]] = {}
    comments: dict[str, dict[str, str]] = {}
    if not OUT.exists():
        return found, comments
    kind: str | None = None
    for line in OUT.read_text(encoding="utf-8").splitlines():
        head = re.match(r"^const (\w+): LoreMap = \{", line)
        if head:
            kind = head.group(1)
            found[kind] = {}
            comments[kind] = {}
        elif line.startswith("};"):
            kind = None
        elif kind and (m := _ENTRY.match(line)):
            found[kind][m.group(1)] = m.group(2)
            if m.group(3):
                comments[kind][m.group(1)] = m.group(3).strip()
    return found, comments


def _labels(kind: str) -> dict[str, str]:
    """Etykiety do komentarzy: ``id -> nazwa`` ze WSZYSTKICH plików assetów rodzaju."""
    folder, key, _ = KINDS[kind]
    out: dict[str, str] = {}
    if kind in TS_KINDS:
        for item in _ts_items(kind):
            out.setdefault(item["id"], item.get("name", "").replace("\n", " "))
        return out
    for path in sorted((ROOT / "assets" / "data" / folder).glob("*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if isinstance(item, dict) and item.get(key):
                label = str(item.get("name", "")).replace("\n", " ")
                if kind == "unit":  # nazwa jednostki + frakcja i typ bazowy
                    owner = item.get("faction", "generic")
                    label += f" ({owner} {item.get('baseType', '')})".rstrip()
                if kind == "leader":  # imię lidera nic nie mówi — dopisz frakcję i rolę
                    label += f" ({item.get('faction', '?')} {item.get('type', '')})".rstrip()
                if item.get("source") == "absol":
                    label += " [Absol]"
                out.setdefault(str(item[key]), label)
    out.update(STATIC_FEATURES if kind == "feature" else {})
    return out


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _used(registry: StaticDataRegistry) -> dict[str, set[str]]:
    """Id kart, których silnik używa w grze (oficjalne talie, listy frakcji)."""
    factions = list(registry.factions.values())
    techs = set(generic_pool(registry))
    for f in factions:
        techs.update(f.faction_tech, f.starting_tech, f.starting_tech_options)
    return {
        "leader": {lid for f in factions for lid in f.leaders},
        "agenda": set(deck_card_ids(registry, "agenda")),
        "promissoryNote": {n for f in factions for n in f.promissory_notes}
        | set(common_promissory_note_ids(registry, "<color>")),
        "publicObjective": set(deck_card_ids(registry, "public_stage_1_objective"))
        | set(deck_card_ids(registry, "public_stage_2_objective")),
        "secretObjective": set(deck_card_ids(registry, "secret_objective")),
        "technology": {t for t in techs if t in registry.technologies},
        "breakthrough": set(registry.breakthroughs),
        "ability": {a for f in factions for a in f.abilities},
        # warianty „...stat” (bonus do cech) czytają pole karty bazowej
        "attachment": {
            a
            for a in _official_ids("attachments") | _explored_attachments()
            if not a.endswith("stat")
        },
        "feature": (_official_ids("tokens") - SKIPPED_TOKENS) | set(STATIC_FEATURES),
        "unit": {u for f in factions for u in f.units if registry.units[u].faction}
        | GENERIC_UNITS,
        # każda karta w grze dostaje pole, także bez flavouru w assetach (+ karty z flavourem)
        "actionCard": set(deck_card_ids(registry, "action_card")) | set(_prefill("actionCard")),
        "relic": set(deck_card_ids(registry, "relic")) | set(_prefill("relic")),
        "exploration": _official_ids("explores"),
        "plot": _official_plots(),
        "system": {
            i["id"]
            for i in _ts_items("system")
            if i.get("source") in OFFICIAL_SOURCES and i.get("name")
        },
        "planet": {
            i["id"] for i in _ts_items("planet") if i.get("source") in OFFICIAL_SOURCES
        },
    }


def _absol_agendas(official: set[str], labels: dict[str, str]) -> tuple[set[str], dict[str, str]]:
    """Talia Absol: ``(nowe karty z własnym polem, alias absol_id -> id oficjalnej karty)``."""
    registry = StaticDataRegistry(variant_ids=(ABSOL_AGENDAS,))
    module = next(m for m in registry.variant_modules if m.id == ABSOL_AGENDAS)
    by_name = {_norm(labels[a]): a for a in official if a in labels}
    own: set[str] = set()
    aliases: dict[str, str] = {}
    for card in sorted(variants.variant_deck_ids(registry, module, "agenda")):
        name = _norm(labels.get(card, card).removesuffix(" [Absol]"))
        target = ABSOL_RENAMED.get(card) or by_name.get(name)
        if target is None:  # nowa karta Absol; 4 kopie Emergency Session = 4 osobne pola
            own.add(card)
        else:
            aliases[card] = target
    return own, aliases


def main() -> None:
    existing, comments = _existing()
    used = _used(StaticDataRegistry())
    labels = {kind: _labels(kind) for kind in KINDS}
    absol_own, absol_aliases = _absol_agendas(used["agenda"], labels["agenda"])
    used["agenda"] |= absol_own
    for kind, extra in EXTRA_CARDS.items():
        used[kind] |= extra

    lines = [
        *HEADER,
        "",
        "export type LoreMap = Record<string, string>;",
        "",
    ]
    for kind, (_, _, title) in KINDS.items():
        prefill = _prefill(kind) if kind in PREFILLED else {}
        entries = {
            cid: json.dumps(prefill[cid], ensure_ascii=False) if cid in prefill else '""'
            for cid in used[kind]
        }
        for cid, literal in existing.get(kind, {}).items():
            if cid in entries or literal != '""':
                entries[cid] = literal
                if cid not in used[kind]:
                    print(f"UWAGA: {kind}:{cid} ma tekst, ale silnik już tej karty nie używa")
        label = labels[kind]
        lines.append(f"/** {title}. */")
        lines.append(f"const {kind}: LoreMap = {{")
        for cid in sorted(entries, key=lambda c: ((label.get(c) or c).lower(), c)):
            text = comments.get(kind, {}).get(cid) or label.get(cid)
            comment = f" // {text}" if text else ""
            lines.append(f"  {json.dumps(cid)}: {entries[cid]},{comment}")
        lines += ["};", ""]

    lines.append("export const CARD_LORE = {")
    lines += [f"  {kind}," for kind in KINDS]
    lines += [
        "} as const satisfies Record<string, LoreMap>;",
        "",
        "export type LoreKind = keyof typeof CARD_LORE;",
        "",
    ]

    lines.append("/** Ta sama karta pod innym id — czyta lore wskazanej karty. */")
    lines.append(
        "export const LORE_ALIASES: "
        "Partial<Record<LoreKind, Readonly<Record<string, string>>>> = {"
    )
    lines.append("  agenda: {")
    for cid, target in sorted(absol_aliases.items()):
        comment = labels["agenda"].get(cid, "")
        lines.append(f"    {json.dumps(cid)}: {json.dumps(target)}, // {comment}")
    lines += ["  },", "  unit: {"]
    for cid, target in sorted(UNIT_ALIASES.items()):
        comment = labels["unit"].get(cid, "")
        lines.append(f"    {json.dumps(cid)}: {json.dumps(target)}, // {comment}")
    lines += ["  },", "};", ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"zapisano {OUT.relative_to(ROOT)} (aliasy Absol: {len(absol_aliases)}, "
          f"nowe Absol: {len(absol_own)})")


if __name__ == "__main__":
    main()
