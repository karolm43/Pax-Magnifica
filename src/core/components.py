"""Katalog komponentów TI4: modele kart, celów, żetonów, talii itd.

Moduł nie zawiera ŻADNYCH danych ani reguł gry. Kształty plików JSON (klucz
identyfikatora, pola tekstowe, pole okna) opisuje wyłącznie tabela
``CATEGORY_SPECS``; zawartość pochodzi z assetów AsyncTI4 wczytywanych przez
loader. Surowy wpis JSON jest zawsze zachowany w polu ``raw`` (nic nie ginie).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src import config


class ComponentCategory(StrEnum):
    """Kategorie komponentów adresowalne w katalogu, API i audycie."""

    ACTION_CARD = "action_cards"
    AGENDA = "agendas"
    PUBLIC_OBJECTIVE = "public_objectives"
    SECRET_OBJECTIVE = "secret_objectives"
    ATTACHMENT = "attachments"
    EXPLORATION = "explores"
    RELIC = "relics"
    PROMISSORY_NOTE = "promissory_notes"
    TOKEN = "tokens"
    BORDER_ANOMALY = "border_anomalies"
    GALACTIC_EVENT = "galactic_events"
    GENERIC_CARD = "genericcards"
    DECK = "decks"
    # Kategorie już obecne w StaticDataRegistry (tylko do adresowania).
    FACTION = "factions"
    LEADER = "leaders"
    ABILITY = "abilities"
    TECHNOLOGY = "technologies"
    BREAKTHROUGH = "breakthroughs"
    STRATEGY_CARD = "strategy_cards"
    UNIT = "units"


class ComponentRef(NamedTuple):
    """Adres komponentu: kategoria + identyfikator."""

    category: ComponentCategory
    id: str


class ComponentBase(BaseModel):
    """Wspólna baza modeli komponentów (ignoruje nieznane pola, zachowuje ``raw``)."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    source: str
    name: str | None = None
    texts: dict[str, str] = Field(default_factory=dict)
    window: str | None = None
    notes: str | None = None
    flavor_text: str | None = None
    image_path: str | None = Field(default=None, alias="imagePath")
    raw: dict[str, Any] = Field(default_factory=dict)


class ActionCardDef(ComponentBase):
    """Karta akcji."""

    phase: str | None = None
    automation_id: str | None = Field(default=None, alias="automationID")
    play_timing: str | None = Field(default=None, alias="playTiming")


class AgendaDef(ComponentBase):
    """Karta agendy (prawo / dyrektywa)."""

    type: str | None = None
    target: str | None = None


class ObjectiveDef(ComponentBase):
    """Cel publiczny albo tajny."""

    phase: str | None = None
    points: int | None = None


class AttachmentDef(ComponentBase):
    """Attachment planety/systemu."""

    tech_speciality: list[str] = Field(default_factory=list, alias="techSpeciality")
    planet_types: list[str] = Field(default_factory=list, alias="planetTypes")
    is_legendary: bool = Field(default=False, alias="isLegendary")
    token: str | None = None


class ExplorationDef(ComponentBase):
    """Karta eksploracji."""

    type: str | None = None
    resolution: str | None = None
    attachment_id: str | None = Field(default=None, alias="attachmentId")


class RelicDef(ComponentBase):
    """Relikt."""

    short_name: str | None = Field(default=None, alias="shortName")


class PromissoryNoteDef(ComponentBase):
    """Promissory note (``id`` może zawierać placeholder ``<color>``)."""

    color: str | None = None
    play_area: bool = Field(default=False, alias="playArea")
    faction: str | None = None
    play_immediately: bool = Field(default=False, alias="playImmediately")


class TokenDef(ComponentBase):
    """Żeton mapy."""

    space_or_planet: str | None = Field(default=None, alias="spaceOrPlanet")
    attachment_id: str | None = Field(default=None, alias="attachmentID")
    alias_list: list[str] = Field(default_factory=list, alias="aliasList")


class BorderAnomalyDef(ComponentBase):
    """Anomalia graniczna."""

    alias_list: list[str] = Field(default_factory=list, alias="aliasList")
    automation: str | None = None
    automation_notes: str | None = Field(default=None, alias="automationNotes")


class GalacticEventDef(ComponentBase):
    """Wydarzenie galaktyczne."""

    complexity: int | None = None


class GenericCardDef(ComponentBase):
    """Karta generyczna."""

    card_type: str | None = Field(default=None, alias="cardType")


class DeckDef(ComponentBase):
    """Talia: lista identyfikatorów kart (``cardIDs``)."""

    deck_type: str | None = Field(default=None, alias="type")
    card_ids: list[str] = Field(default_factory=list, alias="cardIDs")

    @field_validator("card_ids", mode="before")
    @classmethod
    def _split_card_ids(cls, value: object) -> object:
        """Napis rozdzielany białymi znakami → lista; lista przechodzi bez zmian."""
        if isinstance(value, str):
            return value.split()
        return value


@dataclass(frozen=True)
class CategorySpec:
    """Kształt JSON jednej kategorii (jedyne miejsce takiej wiedzy)."""

    category: ComponentCategory
    directory: Path
    model: type[ComponentBase]
    id_field: str  # "alias" albo "id"
    text_fields: tuple[str, ...] = ()
    window_field: str | None = None


def _spec(
    category: ComponentCategory,
    directory: Path,
    model: type[ComponentBase],
    id_field: str,
    text_fields: tuple[str, ...] = (),
    window_field: str | None = None,
) -> tuple[ComponentCategory, CategorySpec]:
    return category, CategorySpec(
        category, directory, model, id_field, text_fields, window_field
    )


CATEGORY_SPECS: Mapping[ComponentCategory, CategorySpec] = dict(
    [
        _spec(ComponentCategory.ACTION_CARD, config.ACTION_CARDS_DATA_DIR,
              ActionCardDef, "alias", ("text",), "window"),
        _spec(ComponentCategory.AGENDA, config.AGENDAS_DATA_DIR,
              AgendaDef, "alias", ("text1", "text2", "mapText")),
        _spec(ComponentCategory.PUBLIC_OBJECTIVE, config.PUBLIC_OBJECTIVES_DATA_DIR,
              ObjectiveDef, "alias", ("text",)),
        _spec(ComponentCategory.SECRET_OBJECTIVE, config.SECRET_OBJECTIVES_DATA_DIR,
              ObjectiveDef, "alias", ("text",)),
        _spec(ComponentCategory.ATTACHMENT, config.ATTACHMENTS_DATA_DIR,
              AttachmentDef, "id"),
        _spec(ComponentCategory.EXPLORATION, config.EXPLORES_DATA_DIR,
              ExplorationDef, "id", ("text",)),
        _spec(ComponentCategory.RELIC, config.RELICS_DATA_DIR,
              RelicDef, "alias", ("text",)),
        _spec(ComponentCategory.PROMISSORY_NOTE, config.PROMISSORY_NOTES_DATA_DIR,
              PromissoryNoteDef, "alias", ("text",)),
        _spec(ComponentCategory.TOKEN, config.TOKENS_DATA_DIR, TokenDef, "id"),
        _spec(ComponentCategory.BORDER_ANOMALY, config.BORDER_ANOMALIES_DATA_DIR,
              BorderAnomalyDef, "id", ("automationNotes",)),
        _spec(ComponentCategory.GALACTIC_EVENT, config.GALACTIC_EVENTS_DATA_DIR,
              GalacticEventDef, "alias", ("text",)),
        _spec(ComponentCategory.GENERIC_CARD, config.GENERIC_CARDS_DATA_DIR,
              GenericCardDef, "alias", ("text",)),
        _spec(ComponentCategory.DECK, config.DECKS_DATA_DIR,
              DeckDef, "alias", ("description",)),
    ]
)


def build_component(entry: Mapping[str, Any], spec: CategorySpec) -> ComponentBase:
    """Buduje model komponentu z surowego wpisu JSON wg ``CategorySpec``.

    Raises:
        pydantic.ValidationError: Gdy wpis nie spełnia modelu kategorii
            (np. brak identyfikatora albo ``source``).
    """
    data: dict[str, Any] = dict(entry)
    data["id"] = entry.get(spec.id_field)
    data["texts"] = {
        field: entry[field] for field in spec.text_fields if isinstance(entry.get(field), str)
    }
    data["window"] = entry.get(spec.window_field) if spec.window_field else None
    # Brytyjska pisownia (relikty) i amerykańska (reszta) trafiają do jednego pola.
    flavor = entry.get("flavorText", entry.get("flavourText"))
    data["flavor_text"] = flavor
    data["raw"] = dict(entry)
    return spec.model.model_validate(data)


class ComponentCatalog:
    """Niemutowalny katalog komponentów pogrupowanych w kategorie."""

    def __init__(
        self, tables: Mapping[ComponentCategory, Mapping[str, ComponentBase]]
    ) -> None:
        self._tables: dict[ComponentCategory, dict[str, ComponentBase]] = {
            category: dict(table) for category, table in tables.items()
        }

    def get(self, category: ComponentCategory, component_id: str) -> ComponentBase | None:
        """Zwraca komponent albo ``None``, gdy brak kategorii lub identyfikatora."""
        return self._tables.get(category, {}).get(component_id)

    def all(self, category: ComponentCategory) -> Mapping[str, ComponentBase]:
        """Zwraca kopię słownika ``id -> komponent`` kategorii (pusty, gdy brak)."""
        return dict(self._tables.get(category, {}))

    def counts(self) -> dict[ComponentCategory, dict[str, int]]:
        """Liczby komponentów: kategoria -> źródło -> liczba."""
        result: dict[ComponentCategory, dict[str, int]] = {}
        for category, table in self._tables.items():
            per_source: dict[str, int] = {}
            for component in table.values():
                per_source[component.source] = per_source.get(component.source, 0) + 1
            result[category] = per_source
        return result
