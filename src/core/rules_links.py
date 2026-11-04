"""Powiązania komponentów z tematami zrzutu reguł (``docs/rules_tirules``).

Indeks czyta wyłącznie METADANE tematów z ``tirules.json`` (kod, kategoria,
tytuł). Treść tematów to nadal ``core/rules_content.py``; opisy kart pochodzą
z JSON assetów, nie ze zrzutu reguł (R10.4).

Dopasowanie jest deterministyczne i bez zgadywania: znormalizowana nazwa musi
RÓWNAĆ SIĘ znormalizowanemu tytułowi albo kodowi tematu. Poza tym działa tabela
``CATEGORY_TOPIC_HINTS`` (kategoria komponentu -> temat kategorialny). Rozmytego
dopasowania nie ma; brak trafienia daje pustą listę.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from src import config

# Kategoria komponentu (wartość ``ComponentCategory``) -> kody tematów kategorialnych.
# Klucze to napisy, by moduł nie zależał od ``components.py``. Kody są sprawdzane
# względem indeksu: nieistniejący temat jest pomijany.
CATEGORY_TOPIC_HINTS: Mapping[str, tuple[str, ...]] = {
    "action_cards": ("C_action_cards",),
    "agendas": ("C_agendas",),
    "public_objectives": ("C_objectives",),
    "secret_objectives": ("C_objectives",),
    "explores": ("C_exploration_cards",),
    "relics": ("C_relics",),
    "promissory_notes": ("C_promissory_notes",),
    "technologies": ("C_technology",),
    "units": ("C_units",),
    "galactic_events": ("C_events",),
}

_NON_ALNUM = re.compile(r"[\W_]+", re.UNICODE)
_CODE_PREFIX = re.compile(r"^[A-Z]_")


def normalize(text: str) -> str:
    """Normalizacja: ``casefold`` i usunięcie wszystkich znaków niealfanumerycznych."""
    return _NON_ALNUM.sub("", text.casefold())


@dataclass(frozen=True)
class RulesTopic:
    """Metadane tematu zrzutu reguł."""

    code: str  # np. "C_action_cards"
    category: str  # rule | faction | component
    title: str


class RulesTopicIndex:
    """Indeks tematów reguł z dopasowaniem przez równość znormalizowanych nazw."""

    def __init__(self, topics: list[RulesTopic] | None = None) -> None:
        self._topics: tuple[RulesTopic, ...] = tuple(topics or ())
        self._by_code: dict[str, RulesTopic] = {t.code: t for t in self._topics}
        self._by_key: dict[str, list[RulesTopic]] = {}
        for topic in self._topics:
            keys = {
                normalize(topic.title),
                normalize(topic.code),
                normalize(_CODE_PREFIX.sub("", topic.code)),
            }
            for key in keys:
                if key:
                    self._by_key.setdefault(key, []).append(topic)

    @classmethod
    def from_json(cls, path: Path = config.RULES_DIR / "tirules.json") -> RulesTopicIndex:
        """Wczytuje indeks; brak lub uszkodzony plik daje pusty indeks."""
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        entries = raw.get("topics") if isinstance(raw, dict) else None
        if not isinstance(entries, list):
            return cls()
        topics: list[RulesTopic] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            code, category, title = entry.get("code"), entry.get("category"), entry.get("title")
            if isinstance(code, str) and isinstance(category, str) and isinstance(title, str):
                topics.append(RulesTopic(code=code, category=category, title=title))
        return cls(topics)

    def __len__(self) -> int:
        return len(self._topics)

    def get(self, code: str) -> RulesTopic | None:
        """Zwraca temat o danym kodzie albo ``None``."""
        return self._by_code.get(code)

    def match(self, *names: str, category: str | None = None) -> list[RulesTopic]:
        """Zwraca tematy pasujące do nazw/aliasów (równość po normalizacji).

        Args:
            names: Nazwa i/lub alias komponentu.
            category: Opcjonalnie wartość kategorii komponentu; dodaje temat
                kategorialny z ``CATEGORY_TOPIC_HINTS``.

        Returns:
            Tematy bez duplikatów, w kolejności: trafienia po nazwie (kolejność
            argumentów), potem temat kategorialny. Brak trafień = pusta lista.
        """
        result: list[RulesTopic] = []
        seen: set[str] = set()

        def add(topic: RulesTopic) -> None:
            if topic.code not in seen:
                seen.add(topic.code)
                result.append(topic)

        for name in names:
            key = normalize(name)
            if key:
                for topic in self._by_key.get(key, ()):
                    add(topic)
        if category is not None:
            for code in CATEGORY_TOPIC_HINTS.get(category, ()):
                hinted = self._by_code.get(code)
                if hinted is not None:
                    add(hinted)
        return result
