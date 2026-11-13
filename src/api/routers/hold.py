"""Router hold-rewind (RULES.md 53.7): zagranie karty reakcji w oknie, które już minęło.

Cienki: łańcuch migawek z ``StateService`` -> ``core/hold_rewind`` -> zapis jako rozgałęzienie
historii (``replace_state(branch_from=seq)``). Kontrakt dla frontu: ``tmp_scr/HOLD_BRIEF.md``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from src.api.actor import ActorId, require_view
from src.api.context import AppContext, get_ctx
from src.api.schemas import ActionCardInputsResponse, PlayActionCardResponse
from src.core import actor as actor_rules
from src.core import hold_rewind
from src.core.components import ComponentCategory

router = APIRouter()


class HoldPlayRequest(BaseModel):
    """Zagranie karty w przeszłej migawce; ``actor_id`` (RULES.md 44.1) = ``player_id``."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    player_id: str
    card_id: str
    seq: int
    params: dict[str, Any] = Field(default_factory=dict)


class HoldCard(BaseModel):
    card_id: str
    name: str
    window: str


class HoldStep(BaseModel):
    seq: int
    label: str
    nextLabel: str | None = None  # noqa: N815 (kontrakt JSON z frontem jest camelCase)
    nextSeq: int | None = None  # noqa: N815
    round: int
    phase: str
    stepsBack: int  # noqa: N815
    cards: list[HoldCard]


class HoldCandidatesResponse(BaseModel):
    steps: list[HoldStep]
    limitReason: str | None = None  # noqa: N815


def _chain(ctx: AppContext) -> list[hold_rewind.Snapshot]:
    return [
        hold_rewind.Snapshot(seq, label, state)
        for seq, label, state in ctx.service.recent_chain(hold_rewind.CHAIN_LIMIT)
    ]


@router.get("/hold/candidates", response_model=HoldCandidatesResponse)
async def get_hold_candidates(
    request: Request,
    player_id: str, ctx: AppContext = Depends(get_ctx)
) -> HoldCandidatesResponse:
    """Kroki, do których gracz może się cofnąć z kartą hold-rewind (od najnowszego)."""
    require_view(request, player_id)  # RULES.md 44.3
    try:
        steps, limit = hold_rewind.candidates(_chain(ctx), ctx.registry, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return HoldCandidatesResponse(steps=[HoldStep(**step) for step in steps], limitReason=limit)


@router.get("/hold/{card_id}/inputs", response_model=ActionCardInputsResponse)
async def get_hold_inputs(
    request: Request,
    card_id: str, player_id: str, seq: int, ctx: AppContext = Depends(get_ctx)
) -> ActionCardInputsResponse:
    """Formularz karty liczony na migawce ``seq`` (opcje ze stanu z tamtej chwili)."""
    require_view(request, player_id)  # RULES.md 44.3
    try:
        implemented, inputs = hold_rewind.inputs_at(
            _chain(ctx), ctx.registry, player_id, card_id, seq
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    card = ctx.registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
    assert card is not None  # zagwarantowane przez card_inputs
    return ActionCardInputsResponse(
        card_id=card_id,
        name=card.name or card_id,
        text=" ".join(card.texts.values()),
        implemented=implemented,
        inputs=inputs,
    )


@router.post("/hold/play", response_model=PlayActionCardResponse)
async def post_hold_play(
    actor: ActorId,
    request: HoldPlayRequest, ctx: AppContext = Depends(get_ctx)
) -> PlayActionCardResponse:
    """Cofa historię do migawki ``seq`` i zagrywa tam kartę (jeden commit rozgałęziający)."""
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    chain = _chain(ctx)
    try:
        new_state, implemented = hold_rewind.play_at(
            chain, ctx.registry, request.player_id, request.card_id, request.seq,
            request.params, actor_id=request.actor_id, now=ctx.service.now(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    rewinding = bool(chain) and request.seq != chain[-1].seq
    label = (
        f"{hold_rewind.REWIND_LABEL_PREFIX}:{request.card_id}:{request.seq}"
        if rewinding
        else f"action-card:{request.card_id}"
    )
    ctx.service.replace_state(new_state, label=label, branch_from=request.seq)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return PlayActionCardResponse(envelope=ctx.service.envelope(), implemented=implemented)
