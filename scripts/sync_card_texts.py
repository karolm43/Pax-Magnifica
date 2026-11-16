"""Synchronizacja TEKSTÓW kart aktywnych talii: assety silnika -> dane frontu.

Dlaczego: dane frontu (``actionCards.ts``, ``agendas.ts``) pochodzą ze starszego eksportu
AsyncTI4 i bywają nieaktualne względem assetów, z których gra silnik (np. Hack Election Ω z
Thunder's Edge „you vote last” vs stare „voting begins with the player to the right…”,
Insider Information „top 3 cards” vs „top card”). Gracz czytał w ręce INNĄ kartę, niż ta,
którą rozgrywa silnik. Źródło prawdy = assety (``assets/data``, wersje TE / Codex).

Porównanie pomija dopiski AsyncTI4 ``[Note: …]`` (rulingi, nie tekst karty) — zostają, gdy
sam tekst się zgadza; przy różnicy pole dostaje dokładny tekst z assetu. Brakujące na froncie
karty talii są dopisywane na końcu tablicy.

Uruchomienie: ``uv run python scripts/sync_card_texts.py`` (po zmianie assetów);
``--check`` tylko raportuje (kod 1 przy różnicach). Strażnik: ``tests/test_card_texts_sync.py``.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.objectives import deck_card_ids  # noqa: E402
from src.core.registry import StaticDataRegistry  # noqa: E402

DATA = ROOT / "frontend" / "src" / "entities" / "data"

# typ talii -> (folder assetów, plik TS, pola tekstowe)
SETS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "action_card": ("action_cards", "actionCards.ts", ("name", "window", "text")),
    "agenda": ("agendas", "agendas.ts", ("name", "type", "target", "text1", "text2")),
}

_STR = r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`[^`]*`)'
_NOTE = re.compile(r"\s*\[Note[^\]]*\]\s*$", re.I)


def _assets(folder: str) -> dict[str, dict[str, Any]]:
    cards: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "assets" / "data" / folder).glob("*.json")):
        for card in json.loads(path.read_text(encoding="utf-8")):
            cards.setdefault(card["alias"], card)
    return cards


def _blocks(text: str) -> dict[str, tuple[int, int]]:
    """alias -> (początek, koniec) literału obiektu w pliku TS (pierwsze wystąpienie)."""
    found: dict[str, tuple[int, int]] = {}
    for match in re.finditer(r'\{[^{}]*?alias:\s*"([^"]+)"[^{}]*?\}', text, re.S):
        found.setdefault(match.group(1), (match.start(), match.end()))
    return found


def _field(body: str, key: str) -> re.Match[str] | None:
    return re.search(rf"\b{key}:\s*" + _STR, body)


def _value(raw: str) -> str:
    if raw[0] == '"':
        return str(json.loads(raw))
    return raw[1:-1].replace("\\'", "'")


def _norm(value: str | None) -> str:
    text = (value or "").replace("’", "'").replace("\\n", " ")
    return re.sub(r"\s+", " ", _NOTE.sub("", text)).strip()


def _literal(card: dict[str, Any], keys: tuple[str, ...]) -> str:
    lines = [f'    alias: {json.dumps(card["alias"])},']
    for key in (*keys, "source"):
        if key in card and card[key] is not None:
            lines.append(f"    {key}: {json.dumps(card[key], ensure_ascii=False)},")
    return "  {\n" + "\n".join(lines) + "\n  },\n"


def diffs(registry: StaticDataRegistry) -> list[str]:
    """Różnice tekstów (``alias.pole``) i brakujące karty talii na froncie."""
    out: list[str] = []
    for kind, (folder, ts_file, keys) in SETS.items():
        assets = _assets(folder)
        text = (DATA / ts_file).read_text(encoding="utf-8")
        blocks = _blocks(text)
        for alias in sorted(set(deck_card_ids(registry, kind))):
            if alias not in blocks:
                out.append(f"{ts_file}: missing {alias}")
                continue
            body = text[blocks[alias][0]:blocks[alias][1]]
            for key in keys:
                match = _field(body, key)
                front = _value(match.group(1)) if match else ""
                if _norm(front) != _norm(assets[alias].get(key)):
                    out.append(f"{ts_file}: {alias}.{key}")
    return out


def sync(registry: StaticDataRegistry) -> int:
    """Wpisuje teksty z assetów do plików TS; zwraca liczbę zmian."""
    changes = 0
    for kind, (folder, ts_file, keys) in SETS.items():
        assets = _assets(folder)
        path = DATA / ts_file
        text = path.read_text(encoding="utf-8")
        deck = sorted(set(deck_card_ids(registry, kind)))
        # Od końca pliku, żeby przesunięcia nie psuły kolejnych zakresów.
        blocks = _blocks(text)
        for alias in sorted((a for a in deck if a in blocks), key=lambda a: -blocks[a][0]):
            start, end = blocks[alias]
            body = text[start:end]
            new_body = body
            for key in keys:
                want = assets[alias].get(key)
                match = _field(new_body, key)
                front = _value(match.group(1)) if match else ""
                if want is None or _norm(front) == _norm(want):
                    continue
                literal = json.dumps(want, ensure_ascii=False)
                if match:
                    new_body = new_body[:match.start(1)] + literal + new_body[match.end(1):]
                else:
                    at = new_body.index("\n", new_body.index("alias:")) + 1
                    new_body = new_body[:at] + f"    {key}: {literal},\n" + new_body[at:]
                changes += 1
            text = text[:start] + new_body + text[end:]
        missing = [a for a in deck if a not in blocks]
        if missing:
            tail = text.rindex("];")
            text = text[:tail] + "".join(_literal(assets[a], keys) for a in missing) + text[tail:]
            changes += len(missing)
        path.write_text(text, encoding="utf-8")
    return changes


def main() -> int:
    registry = StaticDataRegistry()
    if "--check" in sys.argv:
        found = diffs(registry)
        print("\n".join(found) or "OK")
        return 1 if found else 0
    print(f"Updated {sync(registry)} field(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
