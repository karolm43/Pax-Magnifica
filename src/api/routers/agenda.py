"""Router fazy agendy (RULES.md 51): ujawnienie, głosowanie, wynik, kolejna agenda.

Cienkie endpointy: odczyt stanu → funkcja ``core.agenda_phase`` → commit + broadcast.
Błędy domenowe (``ValueError``) mapujemy na HTTP 422. Koniec fazy (po obu agendach i
odświeżeniu planet) ogłasza mówca przez ``/phase/next``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    AgendaOutcomeRequest,
    AgendaVoteRequest,
    StateEnvelope,
    TurnActionRequest,
)
from src.core import agenda_phase
from src.core.game_state import GameState

router = APIRouter(prefix="/agenda", tags=["agenda"])


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


def _speaker_of(request: TurnActionRequest | None, state: GameState) -> str:
    """Gracz wykonujący akcję mówcy (brak ``player_id`` = mówca, zgodność wsteczna)."""
    if request is not None and request.player_id is not None:
        return request.player_id
    return state.speaker_id or ""


@router.post("/reveal", response_model=StateEnvelope)
async def post_reveal(
    request: TurnActionRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Mówca ujawnia wierzchnią agendę i otwiera głosowanie."""
    state = ctx.service.current_state()
    try:
        new_state = agenda_phase.reveal_agenda(state, ctx.registry, _speaker_of(request, state))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "agenda:reveal")


@router.post("/vote", response_model=StateEnvelope)
async def post_vote(
    request: AgendaVoteRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz, którego kolej, wyczerpuje planety i oddaje głosy na jeden wynik."""
    try:
        new_state = agenda_phase.cast_vote(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.outcome,
            request.planets,
            use_predictive=request.use_predictive,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"agenda:vote:{request.player_id}")


@router.post("/abstain", response_model=StateEnvelope)
async def post_abstain(
    request: TurnActionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz, którego kolej, wstrzymuje się od głosu."""
    state = ctx.service.current_state()
    player_id = request.player_id or state.active_player_id or ""
    try:
        new_state = agenda_phase.abstain(state, ctx.registry, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"agenda:abstain:{player_id}")


@router.post("/decide", response_model=StateEnvelope)
async def post_decide(
    request: AgendaOutcomeRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Mówca wybiera wynik przy remisie / braku głosów (to nie jest głos)."""
    try:
        new_state = agenda_phase.decide_tie(
            ctx.service.current_state(), ctx.registry, request.player_id, request.outcome
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"agenda:decide:{request.player_id}")


@router.post("/discard", response_model=StateEnvelope)
async def post_discard(
    request: TurnActionRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Mówca odrzuca agendę bez możliwych wyników i ujawnia następną."""
    state = ctx.service.current_state()
    try:
        new_state = agenda_phase.discard_unresolvable(
            state, ctx.registry, _speaker_of(request, state)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "agenda:discard")


@router.post("/continue", response_model=StateEnvelope)
async def post_continue(
    request: TurnActionRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Po wyniku: druga agenda albo (po drugiej) odświeżenie planet i koniec głosowań."""
    state = ctx.service.current_state()
    try:
        new_state = agenda_phase.continue_agenda(
            state, ctx.registry, _speaker_of(request, state)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "agenda:continue")
