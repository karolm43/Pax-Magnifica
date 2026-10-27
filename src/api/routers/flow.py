"""Router przepływu faz i tur (Etap E1): koniec tury, pas, następna faza, nowa runda."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import SetSpeakerRequest, StateEnvelope
from src.core import strategy_phase, turn_flow
from src.core.game_state import GameState, Phase

router = APIRouter()


async def _commit_flow(
    ctx: AppContext, new_state: GameState, label: str
) -> StateEnvelope:
    """Commit wyniku funkcji przepływu + rozesłanie stanu i mapy."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/turn/end", response_model=StateEnvelope)
async def post_end_turn(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Kończy turę bieżącego gracza (przechodzi do następnego niespasowanego)."""
    return await _commit_flow(
        ctx, turn_flow.end_turn(ctx.service.current_state()), "turn:end"
    )


@router.post("/turn/pass", response_model=StateEnvelope)
async def post_pass_turn(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Bieżący gracz pasuje (pomijany do końca fazy akcji)."""
    return await _commit_flow(
        ctx, turn_flow.pass_turn(ctx.service.current_state()), "turn:pass"
    )


@router.post("/phase/next", response_model=StateEnvelope)
async def post_next_phase(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Przechodzi do następnej fazy rundy (Strategia→Akcja→Status→Agenda)."""
    return await _commit_flow(
        ctx, turn_flow.next_phase(ctx.service.current_state()), "phase:next"
    )


@router.post("/round/next", response_model=StateEnvelope)
async def post_next_round(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Rozpoczyna nową rundę: runda +1, faza = strategia, reset pasów.

    Na przełomie rundy karty strategii wracają do puli, a na każdej NIEWYBRANEJ
    karcie dokładany jest +1 trade good (RULES.md 13). Kolejność: accumulate → reset
    → next_round.
    """
    state = ctx.service.current_state()
    state = strategy_phase.accumulate_unpicked_tg(state, ctx.registry)
    state = strategy_phase.reset_strategy_cards(state)
    state = turn_flow.next_round(state)
    return await _commit_flow(ctx, state, "round:next")


@router.post("/speaker/set", response_model=StateEnvelope)
async def post_set_speaker(
    request: SetSpeakerRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Ustawia mówcę (speaker). W fazie strategii aktualizuje, kto wybiera.

    Mówca otwiera wybór kart w fazie strategii (speaker order, RULES.md 24). Gdy
    gracz nie jest w kolejności miejsc, dopisujemy go na koniec stołu (operator
    może ustawić mówcą dowolnego gracza — asystent, nie sędzia).
    """
    state = ctx.service.current_state()
    if request.player_id not in state.players:
        raise HTTPException(
            status_code=422, detail=f"Nieznany gracz: {request.player_id}"
        )
    new_state = state.clone()
    new_state.speaker_id = request.player_id
    if request.player_id not in new_state.seating_order:
        new_state.seating_order = [*new_state.seating_order, request.player_id]
    # W fazie strategii zmiana mówcy przestawia, kto teraz wybiera (od nowego
    # mówcy w górę), ale tylko dopóki trwa wybór (ktoś jeszcze nie ma karty).
    if new_state.phase is Phase.STRATEGY:
        new_state.active_player_id = strategy_phase.next_strategy_picker(new_state)
    return await _commit_flow(ctx, new_state, f"speaker:{request.player_id}")
