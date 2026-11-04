"""Rejestr efektów: status implementacji efektu per komponent.

Czysta struktura danych (bez FastAPI/HTTP). Moduł NIE zawiera logiki efektów
żadnej karty, technologii ani zdolności; asymetria frakcyjna ma być realizowana
hookami w oknach silnika (RULES.md 29), nie warunkami w regułach bazowych.

Plik ``assets/config/effects_status.json`` ma kształt
``{"<kategoria>:<id>": "<status>"}``; brak pliku = pusty rejestr.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import NamedTuple

from src import config
from src.core.components import ActionCardDef, ComponentCatalog, ComponentCategory, ComponentRef


class EffectStatus(StrEnum):
    """Status implementacji efektu komponentu."""

    NOT_IMPLEMENTED = "not_implemented"
    IMPLEMENTED = "implemented"
    MANUAL = "manual"  # rozstrzyga operator w God-Mode


class CoverageRow(NamedTuple):
    """Pokrycie efektów w jednej kategorii."""

    total: int
    implemented: int
    manual: int
    percent_implemented: float


def _key(ref: ComponentRef) -> str:
    return f"{ref.category.value}:{ref.id}"


def _parse_key(key: str) -> ComponentRef:
    category, sep, component_id = key.partition(":")
    if not sep or not component_id:
        raise ValueError(f"Nieprawidłowy klucz rejestru efektów: {key!r}")
    return ComponentRef(ComponentCategory(category), component_id)


@dataclass(frozen=True)
class EffectRegistry:
    """Niemutowalny rejestr ``ComponentRef -> EffectStatus``."""

    statuses: Mapping[ComponentRef, EffectStatus] = field(
        default_factory=lambda: MappingProxyType({})
    )

    def __post_init__(self) -> None:
        # Kopia obronna: późniejsza zmiana słownika wejściowego nie wpływa na rejestr.
        object.__setattr__(self, "statuses", MappingProxyType(dict(self.statuses)))

    def status_of(self, ref: ComponentRef) -> EffectStatus:
        """Status komponentu; brak wpisu → ``NOT_IMPLEMENTED`` (R9.2)."""
        return self.statuses.get(ref, EffectStatus.NOT_IMPLEMENTED)

    def with_status(self, ref: ComponentRef, status: EffectStatus) -> EffectRegistry:
        """Zwraca NOWY rejestr z ustawionym statusem; oryginał bez zmian."""
        updated = dict(self.statuses)
        updated[ref] = status
        return EffectRegistry(updated)

    def to_json_dict(self) -> dict[str, str]:
        """Kształt zapisu pliku ``effects_status.json``."""
        return {_key(ref): status.value for ref, status in self.statuses.items()}

    @classmethod
    def load(cls, path: Path = config.EFFECTS_STATUS_PATH) -> EffectRegistry:
        """Wczytuje rejestr z JSON; brak pliku → pusty rejestr.

        Raises:
            ValueError: Gdy klucz, kategoria albo status są nieprawidłowe.
        """
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: oczekiwano obiektu JSON")
        return cls({_parse_key(k): EffectStatus(v) for k, v in raw.items()})


def coverage(
    catalog: ComponentCatalog, registry: EffectRegistry
) -> dict[ComponentCategory, CoverageRow]:
    """Pokrycie efektów per kategoria niepusta w katalogu (R9.3).

    ``percent_implemented`` ∈ [0, 100]; status ``manual`` nie liczy się jako
    ``implemented``.
    """
    result: dict[ComponentCategory, CoverageRow] = {}
    for category in ComponentCategory:
        ids = catalog.all(category)
        if not ids:
            continue
        statuses = [registry.status_of(ComponentRef(category, i)) for i in ids]
        implemented = statuses.count(EffectStatus.IMPLEMENTED)
        manual = statuses.count(EffectStatus.MANUAL)
        total = len(statuses)
        result[category] = CoverageRow(total, implemented, manual, 100.0 * implemented / total)
    return result


def resolve_action_card_ref(
    catalog: ComponentCatalog, automation_or_alias: str
) -> ComponentRef | None:
    """Adres karty akcji po ``automationID`` albo (zapasowo) po ``alias`` (R9.5).

    ``automationID`` ma pierwszeństwo; przy kilku kartach o tym samym
    ``automationID`` wynik jest deterministyczny (najmniejszy ``id``).
    """
    cards = catalog.all(ComponentCategory.ACTION_CARD)
    for card_id in sorted(cards):
        card = cards[card_id]
        if isinstance(card, ActionCardDef) and card.automation_id == automation_or_alias:
            return ComponentRef(ComponentCategory.ACTION_CARD, card_id)
    if automation_or_alias in cards:
        return ComponentRef(ComponentCategory.ACTION_CARD, automation_or_alias)
    return None
