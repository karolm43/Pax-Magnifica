"""Schematy DTO warstwy API dla Katalogu_Komponentów (Pydantic v2).

Osobny plik od ``schemas.py``, by nie puchł kontrakt podstawowy (design R: tabela
plików, ``api/schemas_components.py``). DTO oddzielają kontrakt sieciowy od modeli
domenowych z ``core/components.py``, ``core/timing_spec.py``, ``core/effects_registry.py``
i ``core/rules_links.py``.

Zasada cienkiej warstwy (ARCHITEKTURA_KODU.md §4): logika pozostaje w ``core``; te
klasy jedynie mapują gotowe struktury rdzenia na odpowiedzi HTTP (klasmetody
``from_core``). Nic nie jest tu obliczane ani ładowane.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from src.core.components import (
    ComponentBase,
    ComponentCategory,
    ComponentRef,
    FactionBundle,
)
from src.core.effects_registry import EffectStatus
from src.core.rules_links import RulesTopic
from src.core.timing_spec import TimingSpec


class CategoryCount(BaseModel):
    """Liczba komponentów jednej kategorii (z rozbiciem na źródła)."""

    model_config = ConfigDict(extra="forbid")

    category: str
    total: int
    by_source: dict[str, int]


class CategoriesResponse(BaseModel):
    """Lista kategorii katalogu z licznikami (``GET /components``)."""

    model_config = ConfigDict(extra="forbid")

    categories: list[CategoryCount]

    @classmethod
    def from_counts(
        cls, counts: dict[ComponentCategory, dict[str, int]]
    ) -> CategoriesResponse:
        """Buduje odpowiedź z wyniku ``ComponentCatalog.counts``."""
        rows = [
            CategoryCount(
                category=category.value,
                total=sum(per_source.values()),
                by_source=dict(per_source),
            )
            for category, per_source in sorted(
                counts.items(), key=lambda item: item[0].value
            )
        ]
        return cls(categories=rows)


class ComponentRefDTO(BaseModel):
    """Adres komponentu: kategoria + identyfikator."""

    model_config = ConfigDict(extra="forbid")

    category: str
    id: str

    @classmethod
    def from_ref(cls, ref: ComponentRef) -> ComponentRefDTO:
        """Mapuje ``ComponentRef`` na DTO."""
        return cls(category=ref.category.value, id=ref.id)


class TimingSpecDTO(BaseModel):
    """Specyfikacja czasowa komponentu (okno użycia)."""

    model_config = ConfigDict(extra="forbid")

    raw_text: str
    trigger: str
    phase_raw: str | None
    phase: str | None
    play_timing: str | None
    play_timing_agrees: bool | None
    source_field: str
    effect_text: str | None
    window_type: str | None

    @classmethod
    def from_core(cls, spec: TimingSpec) -> TimingSpecDTO:
        """Mapuje ``TimingSpec`` z rdzenia na DTO (wartości enum jako napisy)."""
        return cls(
            raw_text=spec.raw_text,
            trigger=spec.trigger.value,
            phase_raw=spec.phase_raw,
            phase=spec.phase.value if spec.phase is not None else None,
            play_timing=spec.play_timing,
            play_timing_agrees=spec.play_timing_agrees,
            source_field=spec.source_field,
            effect_text=spec.effect_text,
            window_type=spec.window_type.value if spec.window_type is not None else None,
        )


class RulesTopicDTO(BaseModel):
    """Metadane tematu zrzutu reguł powiązanego z komponentem."""

    model_config = ConfigDict(extra="forbid")

    code: str
    category: str
    title: str

    @classmethod
    def from_core(cls, topic: RulesTopic) -> RulesTopicDTO:
        """Mapuje ``RulesTopic`` na DTO."""
        return cls(code=topic.code, category=topic.category, title=topic.title)


class ComponentDetailResponse(BaseModel):
    """Szczegół komponentu: dane + specyfikacja czasowa + status efektu + tematy reguł.

    Odpowiedź ``GET /components/{category}/{component_id}``. Pole ``component`` to
    surowa reprezentacja modelu komponentu (serializacja po aliasach, zachowuje
    ``raw``). ``timing_spec`` jest obecne tylko, gdy komponent ma specyfikację.
    """

    model_config = ConfigDict(extra="forbid")

    category: str
    id: str
    component: dict[str, Any]
    timing_spec: TimingSpecDTO | None
    effect_status: str
    rules_topics: list[RulesTopicDTO]

    @classmethod
    def from_core(
        cls,
        ref: ComponentRef,
        component: ComponentBase,
        timing_spec: TimingSpec | None,
        effect_status: EffectStatus,
        rules_topics: list[RulesTopic],
    ) -> ComponentDetailResponse:
        """Składa szczegół komponentu z gotowych struktur rdzenia."""
        return cls(
            category=ref.category.value,
            id=ref.id,
            component=component.model_dump(mode="json", by_alias=True),
            timing_spec=(
                TimingSpecDTO.from_core(timing_spec) if timing_spec is not None else None
            ),
            effect_status=effect_status.value,
            rules_topics=[RulesTopicDTO.from_core(t) for t in rules_topics],
        )


class CategoryComponentsResponse(BaseModel):
    """Komponenty jednej kategorii (``GET /components/{category}``).

    ``components`` to słownik ``id -> surowy model`` (serializacja po aliasach).
    Zwracane są wyłącznie komponenty ze źródeł kanonicznych (filtr jest już w
    katalogu, R11.2).
    """

    model_config = ConfigDict(extra="forbid")

    category: str
    count: int
    components: dict[str, dict[str, Any]]

    @classmethod
    def from_table(
        cls,
        category: ComponentCategory,
        table: dict[str, ComponentBase],
    ) -> CategoryComponentsResponse:
        """Buduje odpowiedź ze słownika ``id -> komponent`` kategorii."""
        serialized = {
            component_id: component.model_dump(mode="json", by_alias=True)
            for component_id, component in table.items()
        }
        return cls(category=category.value, count=len(serialized), components=serialized)


class FactionBundleResponse(BaseModel):
    """Paczka frakcji (R5.6): komplet komponentów powiązanych z jedną frakcją.

    Każda lista to surowe modele serializowane po aliasach. ``breakthrough`` jest
    obecne tylko, gdy frakcja ma przełom (Thunder's Edge).
    """

    model_config = ConfigDict(extra="forbid")

    faction: dict[str, Any]
    leaders: list[dict[str, Any]]
    abilities: list[dict[str, Any]]
    faction_tech: list[dict[str, Any]]
    promissory_notes: list[dict[str, Any]]
    units: list[dict[str, Any]]
    breakthrough: dict[str, Any] | None

    @classmethod
    def from_core(cls, bundle: FactionBundle) -> FactionBundleResponse:
        """Mapuje ``FactionBundle`` z rdzenia na DTO (serializacja po aliasach)."""

        def dump(model: BaseModel) -> dict[str, Any]:
            return model.model_dump(mode="json", by_alias=True)

        return cls(
            faction=dump(bundle.faction),
            leaders=[dump(m) for m in bundle.leaders],
            abilities=[dump(m) for m in bundle.abilities],
            faction_tech=[dump(m) for m in bundle.faction_tech],
            promissory_notes=[dump(m) for m in bundle.promissory_notes],
            units=[dump(m) for m in bundle.units],
            breakthrough=dump(bundle.breakthrough) if bundle.breakthrough is not None else None,
        )


class TimingSpecsResponse(BaseModel):
    """Wynik zapytania czasowego (``GET /timing-specs``): pasujące adresy komponentów."""

    model_config = ConfigDict(extra="forbid")

    trigger: str
    phase: str | None
    refs: list[ComponentRefDTO]

    @classmethod
    def from_refs(
        cls, trigger: str, phase: str | None, refs: list[ComponentRef]
    ) -> TimingSpecsResponse:
        """Buduje odpowiedź z listy ``ComponentRef`` zwróconej przez ``query_timing``."""
        return cls(
            trigger=trigger,
            phase=phase,
            refs=[ComponentRefDTO.from_ref(r) for r in refs],
        )
