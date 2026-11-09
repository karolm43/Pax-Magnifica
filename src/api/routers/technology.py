"""Router użycia technologii (RULES.md 57): formularz wyborów, zdolności poza akcją, użycie.

Cienka warstwa nad ``core.technology_abilities``. „ACTION:” technologii wykonuje się przez akcję
komponentu (``POST /tactical/component-action`` z ``params``); tu są formularze i zdolności, które
akcją NIE są (Psychoarchaeology). Odpowiada zawsze konkretny gracz (``actor_id``, RULES.md 44.1).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.core import technology_abilities

router = APIRouter()


class TechnologyFormResponse(BaseModel):
    tech_id: str
    name: str
    text: str
    kind: str  # "action" | "free"
    implemented: bool
    exhausted: bool
    inputs: list[dict[str, Any]]


class TechnologyAbility(TechnologyFormResponse):
    usable: bool
    reason: str


class TechnologyAbilitiesResponse(BaseModel):
    abilities: list[TechnologyAbility]


class TechnologyUseRequest(BaseModel):
    actor_id: str
    tech_id: str
    params: dict[str, Any] = Field(default_factory=dict)


@router.get("/technology/abilities", response_model=TechnologyAbilitiesResponse)
async def get_abilities(
    player_id: str, ctx: AppContext = Depends(get_ctx)
) -> TechnologyAbilitiesResponse:
    """Zdolności technologii gracza używane poza akcją (np. Psychoarchaeology)."""
    state = ctx.service.current_state()
    return TechnologyAbilitiesResponse(
        abilities=[
            TechnologyAbility(**a)
            for a in technology_abilities.free_abilities(state, ctx.registry, player_id)
        ]
    )


@router.get("/technology/{tech_id}/form", response_model=TechnologyFormResponse)
async def get_form(
    tech_id: str, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> TechnologyFormResponse:
    """Formularz użycia technologii: tekst, czy silnik ją automatyzuje i legalne wybory."""
    try:
        data = technology_abilities.form(
            ctx.service.current_state(), ctx.registry, player_id, tech_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TechnologyFormResponse(**data)


@router.post("/technology/ability", response_model=StateEnvelope)
async def post_use_ability(
    request: TechnologyUseRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz używa zdolności technologii poza akcją (nie zużywa akcji tury)."""
    try:
        new_state = technology_abilities.use_free_ability(
            ctx.service.current_state(), ctx.registry, request.actor_id, request.tech_id,
            request.params,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label=f"technology:ability:{request.tech_id}")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()
