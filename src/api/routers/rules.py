"""Router przeglądarki Zasad (Rules_Browser): offline'owy zrzut reguł TI4.

Cienka warstwa HTTP zgodna ze złotą zasadą architektury (ARCHITEKTURA_KODU.md §1):
całe parsowanie, grupowanie i mapowanie treści żyje w czystych funkcjach
``core.rules_content``; router jedynie je woła, buduje DTO i mapuje wyjątki
domenowe na kody HTTP.

Treść reguł jest TYLKO DO ODCZYTU i nie dotyka ``GameState`` — w odróżnieniu od
routerów mutujących (np. ``tactical``) ten router NIE wywołuje
``ctx.service.replace_state`` / ``broadcast`` / commitu. Zależność ``get_ctx``
pozostaje w sygnaturze wyłącznie dla spójności wzorca (i ewentualnego cache'u w
przyszłości). Decyzja projektowa: patrz nota w design.md (sekcja Overview).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src import config
from src.api.context import AppContext, get_ctx
from src.api.schemas import RulesIndexResponse, TopicContentDTO
from src.core import rules_content

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=RulesIndexResponse)
async def get_rules_index(ctx: AppContext = Depends(get_ctx)) -> RulesIndexResponse:
    """Zwraca pełny indeks tematów pogrupowany (Reguły → Frakcje → Komponenty).

    Woła czystą funkcję ``load_index`` nad ``config.RULES_DIR`` i opakowuje wynik
    w DTO. Endpoint tylko do odczytu — nie commituje ani nie broadcastuje stanu.
    """
    groups = rules_content.load_index(config.RULES_DIR)
    return RulesIndexResponse.from_core(groups)


@router.get("/{slug}", response_model=TopicContentDTO)
async def get_topic(slug: str, ctx: AppContext = Depends(get_ctx)) -> TopicContentDTO:
    """Zwraca treść pojedynczego tematu o danym slug.

    Słownikuje slug przez ``load_topic`` (walidacja względem realnych plików —
    ochrona przed path-traversal). Wyjątki domenowe rdzenia mapuje na HTTP:
    ``FileNotFoundError`` → 404 (nieznany temat, Req 6.3), ``ValueError`` → 422
    (slug spoza zrzutu reguł). Endpoint tylko do odczytu.
    """
    try:
        topic = rules_content.load_topic(config.RULES_DIR, slug)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Brak tematu: {slug}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TopicContentDTO.from_core(topic)
