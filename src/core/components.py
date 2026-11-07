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
from typing import TYPE_CHECKING, Any, NamedTuple, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src import config
from src.core.game_state import Phase
from src.core.models import (
    AbilityDef,
    BreakthroughDef,
    FactionDef,
    LeaderDef,
    TechnologyDef,
    UnitDef,
)
from src.core.rules_links import RulesTopic, RulesTopicIndex
from src.core.timing_spec import TimingSpec, TriggerKind, parse_timing

if TYPE_CHECKING:
    from src.core.effects_registry import EffectStatus


class _EffectRegistryLike(Protocol):
    """Minimalny protokół rejestru efektów używany przez katalog.

    Pozwala wpiąć ``EffectRegistry`` bez importu z ``effects_registry`` (ten moduł
    sam importuje ``components``, więc import w drugą stronę dałby cykl).
    """

    def status_of(self, ref: ComponentRef) -> EffectStatus: ...


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
    # Modyfikatory wartości planety (Dyson Sphere +2/+1 itd.) — dane AsyncTI4.
    resources_modifier: int = Field(default=0, alias="resourcesModifier")
    influence_modifier: int = Field(default=0, alias="influenceModifier")


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


def build_timing_specs(
    tables: Mapping[ComponentCategory, Mapping[str, ComponentBase]],
    leaders: Mapping[str, LeaderDef] | None = None,
    abilities: Mapping[str, AbilityDef] | None = None,
) -> dict[ComponentRef, TimingSpec]:
    """Buduje specyfikacje czasowe wyłącznie z pól JSON (R8.2).

    Źródła fraz okna: karty akcji (``window`` + ``phase`` + ``playTiming``),
    zdolności frakcji (``window`` + ``windowEffect``), liderzy (``abilityWindow``).
    Komponenty bez frazy okna nie dostają specyfikacji.
    """
    specs: dict[ComponentRef, TimingSpec] = {}
    for comp_id, component in tables.get(ComponentCategory.ACTION_CARD, {}).items():
        if not isinstance(component, ActionCardDef):
            continue
        spec = parse_timing(
            component.window,
            phase=component.phase,
            play_timing=component.play_timing,
            source_field="window",
        )
        if spec is not None:
            specs[ComponentRef(ComponentCategory.ACTION_CARD, comp_id)] = spec
    for ability_id, ability in (abilities or {}).items():
        spec = parse_timing(
            ability.window,
            source_field="window",
            effect_text=ability.window_effect,
        )
        if spec is not None:
            specs[ComponentRef(ComponentCategory.ABILITY, ability_id)] = spec
    for leader_id, leader in (leaders or {}).items():
        spec = parse_timing(leader.ability_window, source_field="abilityWindow")
        if spec is not None:
            specs[ComponentRef(ComponentCategory.LEADER, leader_id)] = spec
    return specs


@dataclass(frozen=True)
class FactionBundle:
    """Komplet komponentów powiązanych z jedną frakcją (R5.6).

    Zbiera w jednym miejscu komponenty, których identyfikatory frakcja wymienia na
    swoich listach (``FactionDef``): liderów, zdolności, technologie frakcyjne,
    promissory notes, jednostki oraz przełom (breakthrough, Thunder's Edge).

    Każda lista zawiera modele rozwiązane z odpowiednich słowników — wyłącznie te
    identyfikatory, które udało się rozwiązać. Nierozwiązane identyfikatory NIE
    trafiają tu (spójność referencji sprawdza osobno ``core/references.py``);
    pozostają jednak dostępne na ``faction`` (surowe listy ``FactionDef``).

    ``faction_bundle`` NIE hardkoduje żadnych nazw ani list — czyta wyłącznie
    ``FactionDef`` i mapuje identyfikatory na modele.
    """

    faction: FactionDef
    leaders: list[LeaderDef]
    abilities: list[AbilityDef]
    faction_tech: list[TechnologyDef]
    promissory_notes: list[PromissoryNoteDef]
    units: list[UnitDef]
    breakthrough: BreakthroughDef | None


class ComponentCatalog:
    """Niemutowalny katalog komponentów pogrupowanych w kategorie."""

    def __init__(
        self,
        tables: Mapping[ComponentCategory, Mapping[str, ComponentBase]],
        timing_specs: Mapping[ComponentRef, TimingSpec] | None = None,
        *,
        factions: Mapping[str, FactionDef] | None = None,
        leaders: Mapping[str, LeaderDef] | None = None,
        abilities: Mapping[str, AbilityDef] | None = None,
        technologies: Mapping[str, TechnologyDef] | None = None,
        units: Mapping[str, UnitDef] | None = None,
        breakthroughs: Mapping[str, BreakthroughDef] | None = None,
        effect_registry: _EffectRegistryLike | None = None,
        rules_index: RulesTopicIndex | None = None,
    ) -> None:
        self._tables: dict[ComponentCategory, dict[str, ComponentBase]] = {
            category: dict(table) for category, table in tables.items()
        }
        self._timing_specs: dict[ComponentRef, TimingSpec] = dict(timing_specs or {})
        # Słowniki kategorii żyjących poza Katalogiem_Komponentów (w rejestrze):
        # potrzebne do złożenia paczki frakcji (R5.6). Puste, gdy katalog budowany
        # bez rejestru (np. w testach jednostkowych modeli).
        self._factions: dict[str, FactionDef] = dict(factions or {})
        self._leaders: dict[str, LeaderDef] = dict(leaders or {})
        self._abilities: dict[str, AbilityDef] = dict(abilities or {})
        self._technologies: dict[str, TechnologyDef] = dict(technologies or {})
        self._units: dict[str, UnitDef] = dict(units or {})
        self._breakthroughs: dict[str, BreakthroughDef] = dict(breakthroughs or {})
        # Rejestr efektów i indeks tematów reguł są opcjonalne i addytywne (R9.3, R10.1):
        # katalog budowany bez nich (np. w testach modeli) działa jak dotąd. Brak
        # rejestru → status zawsze NOT_IMPLEMENTED; brak indeksu → pusty indeks.
        self._effect_registry: _EffectRegistryLike | None = effect_registry
        self._rules_index: RulesTopicIndex = rules_index or RulesTopicIndex()

    def timing_spec(self, ref: ComponentRef) -> TimingSpec | None:
        """Zwraca specyfikację czasową komponentu albo ``None``."""
        return self._timing_specs.get(ref)

    def query_timing(
        self, trigger: TriggerKind, phase: Phase | None = None
    ) -> list[ComponentRef]:
        """Komponenty o danym wyzwalaczu (i fazie, jeśli podana), posortowane."""
        matches = [
            ref
            for ref, spec in self._timing_specs.items()
            if spec.trigger is trigger and (phase is None or spec.phase is phase)
        ]
        return sorted(matches, key=lambda ref: (ref.category.value, ref.id))

    def faction_bundle(self, faction_id: str) -> FactionBundle:
        """Zwraca komplet komponentów powiązanych z frakcją w jednym wywołaniu (R5.6).

        Identyfikatory czytane są WYŁĄCZNIE z list ``FactionDef`` (``leaders``,
        ``abilities``, ``faction_tech``, ``promissory_notes``, ``units``) i mapowane
        na modele z odpowiednich słowników. Nic nie jest hardkodowane. Identyfikatory
        nierozwiązane (brak w słowniku) są pomijane — ich wykryciem zajmuje się
        ``core/references.py``.

        Przełom (breakthrough, Thunder's Edge) nie figuruje na liście ``FactionDef``;
        dopasowywany jest po polu ``faction`` przełomu równym id frakcji LUB jej
        „rodzinie" (``short_name`` małymi literami) — tak samo jak w rejestrze, bez
        listy frakcji w kodzie.

        Args:
            faction_id: Identyfikator frakcji (klucz w słowniku frakcji).

        Raises:
            KeyError: Gdy frakcja o podanym identyfikatorze nie istnieje.
        """
        faction = self._factions[faction_id]
        leaders = [self._leaders[i] for i in faction.leaders if i in self._leaders]
        abilities = [
            self._abilities[i] for i in faction.abilities if i in self._abilities
        ]
        faction_tech = [
            self._technologies[i]
            for i in faction.faction_tech
            if i in self._technologies
        ]
        promissory = self._tables.get(ComponentCategory.PROMISSORY_NOTE, {})
        promissory_notes = [
            note
            for i in faction.promissory_notes
            if isinstance(note := promissory.get(i), PromissoryNoteDef)
        ]
        units = [self._units[i] for i in faction.units if i in self._units]
        breakthrough = self._breakthrough_for(faction)
        return FactionBundle(
            faction=faction,
            leaders=leaders,
            abilities=abilities,
            faction_tech=faction_tech,
            promissory_notes=promissory_notes,
            units=units,
            breakthrough=breakthrough,
        )

    def _breakthrough_for(self, faction: FactionDef) -> BreakthroughDef | None:
        """Przełom frakcji dopasowany po id wariantu lub rodzinie (bez listy nazw)."""
        keys = {faction.id, (faction.short_name or faction.id).lower()}
        return next(
            (bt for bt in self._breakthroughs.values() if bt.faction in keys), None
        )

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

    def effect_status(self, ref: ComponentRef) -> EffectStatus:
        """Status implementacji efektu komponentu (R9.3).

        Deleguje do wpiętego ``EffectRegistry``; gdy rejestru brak, zwraca domyślny
        ``NOT_IMPLEMENTED`` — tak samo jak pusty rejestr. Import lokalny, by uniknąć
        cyklu (``effects_registry`` importuje ``components``).
        """
        from src.core.effects_registry import EffectStatus

        if self._effect_registry is None:
            return EffectStatus.NOT_IMPLEMENTED
        return self._effect_registry.status_of(ref)

    def rules_topics(self, ref: ComponentRef) -> list[RulesTopic]:
        """Tematy zrzutu reguł powiązane z komponentem (R10.1).

        Dopasowanie deterministyczne (równość znormalizowanych nazw) po nazwie i
        identyfikatorze komponentu oraz temat kategorialny z ``CATEGORY_TOPIC_HINTS``.
        Nieznany komponent lub brak trafień → pusta lista; nic nie jest zgadywane.
        """
        component = self.get(ref.category, ref.id)
        names: list[str] = [ref.id]
        if component is not None and component.name:
            names.append(component.name)
        return self._rules_index.match(*names, category=ref.category.value)
