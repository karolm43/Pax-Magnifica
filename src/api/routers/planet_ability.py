"""Router kart zdolności legendarnych planet (RULES.md 60): formularz „ACTION:” (np. The Nucleus).

Cienka warstwa nad ``core.planet_abilities``. „ACTION:” zagrywa się jak każdą akcję komponentu
(``POST /tactical/component-action`` z ``component_id="planet:<id>"`` i ``params``); pozostałe
zdolności legendarne działają przez oferty (``GET /offers``). Tu jest tylko odczyt formularza.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from src.api.actor import require_view
from src.api.context import AppContext, get_ctx
from src.core import planet_abilities

router = APIRouter()


class PlanetAbilityFormResponse(BaseModel):
    planet_id: str
    name: str
    planet_name: str
    text: str
    kind: str  # "action" | "passive"
    implemented: bool
    exhausted: bool
    inputs: list[dict[str, Any]]


@router.get("/planet-ability/{planet_id}/form", response_model=PlanetAbilityFormResponse)
async def get_form(
    request: Request, planet_id: str, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> PlanetAbilityFormResponse:
    """Formularz karty zdolności legendarnej: tekst, rodzaj, czy silnik ją automatyzuje i wybory."""
    require_view(request, player_id)  # RULES.md 44.3
    try:
        state = ctx.service.current_state()
        data = planet_abilities.form(state, ctx.registry, player_id, planet_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PlanetAbilityFormResponse(**data)
