"""Router Katalogu_Komponentów: endpointy TYLKO-DO-ODCZYTU nad katalogiem danych.

Cienka warstwa HTTP (ARCHITEKTURA_KODU.md §4): czyta gotowy ``ComponentCatalog`` z
``ctx.registry.catalog`` i mapuje jego struktury na DTO z ``schemas_components``.
Żadnej logiki gry, żadnej mutacji ``GameState``, zero ``broadcast`` — wzorzec jak
``routers/rules.py``. Zależność ``get_ctx`` pozostaje w sygnaturze dla spójności.

Komponenty pochodzą wyłącznie ze źródeł kanonicznych — filtr jest już w katalogu
(R11.2), warstwa API niczego nie filtruje. Nieznana kategoria lub identyfikator →
``HTTPException(404, "Component not found: <category>/<id>")`` (R11.3). Nieprawidłowy
``trigger`` w zapytaniu czasowym → 422 (walidacja enum przez FastAPI).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas_components import (
    CategoriesResponse,
    CategoryComponentsResponse,
    ComponentDetailResponse,
    FactionBundleResponse,
    TimingSpecsResponse,
)
from src.core.components import ComponentCategory, ComponentRef
from src.core.game_state import Phase
from src.core.timing_spec import TriggerKind

router = APIRouter(tags=["components"])


def _parse_category(category: str) -> ComponentCategory:
    """Słownikuje nazwę kategorii; nieznana → 404 z kategorią i pustym id (R11.3)."""
    try:
        return ComponentCategory(category)
    except ValueError as exc:
        raise HTTPException(
            status_code=404, detail=f"Component not found: {category}/"
        ) from exc


@router.get("/components", response_model=CategoriesResponse)
async def get_categories(ctx: AppContext = Depends(get_ctx)) -> CategoriesResponse:
    """Lista kategorii katalogu z liczbą komponentów (z rozbiciem na źródła).

    Tylko do odczytu — nie commituje ani nie broadcastuje stanu.
    """
    return CategoriesResponse.from_counts(ctx.registry.catalog.counts())


@router.get("/components/{category}", response_model=CategoryComponentsResponse)
async def get_category_components(
    category: str, ctx: AppContext = Depends(get_ctx)
) -> CategoryComponentsResponse:
    """Słownik ``id -> komponent`` jednej kategorii (tylko źródła kanoniczne).

    Nieznana kategoria → 404 (R11.3).
    """
    parsed = _parse_category(category)
    table = dict(ctx.registry.catalog.all(parsed))
    return CategoryComponentsResponse.from_table(parsed, table)


@router.get(
    "/components/{category}/{component_id}",
    response_model=ComponentDetailResponse,
)
async def get_component(
    category: str, component_id: str, ctx: AppContext = Depends(get_ctx)
) -> ComponentDetailResponse:
    """Szczegół komponentu: dane + ``TimingSpec`` + status efektu + tematy reguł.

    Nieznana kategoria lub identyfikator → 404 z kategorią i id (R11.3).
    """
    parsed = _parse_category(category)
    catalog = ctx.registry.catalog
    component = catalog.get(parsed, component_id)
    if component is None:
        raise HTTPException(
            status_code=404,
            detail=f"Component not found: {parsed.value}/{component_id}",
        )
    ref = ComponentRef(parsed, component_id)
    return ComponentDetailResponse.from_core(
        ref,
        component,
        catalog.timing_spec(ref),
        catalog.effect_status(ref),
        catalog.rules_topics(ref),
    )


@router.get(
    "/components/factions/{faction_id}/bundle",
    response_model=FactionBundleResponse,
)
async def get_faction_bundle(
    faction_id: str, ctx: AppContext = Depends(get_ctx)
) -> FactionBundleResponse:
    """Paczka frakcji (R5.6): liderzy, zdolności, tech, promissory, jednostki, przełom.

    Nieznana frakcja → 404 z kategorią ``factions`` i identyfikatorem (R11.3).
    """
    try:
        bundle = ctx.registry.catalog.faction_bundle(faction_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Component not found: {ComponentCategory.FACTION.value}/{faction_id}",
        ) from exc
    return FactionBundleResponse.from_core(bundle)


@router.get("/timing-specs", response_model=TimingSpecsResponse)
async def get_timing_specs(
    trigger: TriggerKind,
    phase: Phase | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> TimingSpecsResponse:
    """Adresy komponentów o danym wyzwalaczu (i fazie, jeśli podana) — R8.6.

    ``trigger`` i ``phase`` są walidowane jako enum przez FastAPI: nieprawidłowa
    wartość → 422. Tylko do odczytu.
    """
    refs = ctx.registry.catalog.query_timing(trigger, phase)
    return TimingSpecsResponse.from_refs(
        trigger.value, phase.value if phase is not None else None, refs
    )
