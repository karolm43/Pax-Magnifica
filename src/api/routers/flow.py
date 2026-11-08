"""Router przepływu faz i tur (Etap E1): koniec tury, pas, następna faza, nowa runda."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import SetSpeakerRequest, StateEnvelope, TurnActionRequest
from src.core import agenda_phase, skip_flow, status_phase, strategy_phase, turn_flow
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
async def post_end_turn(
    request: TurnActionRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Kończy turę aktywnego gracza (waliduje fazę/tura — RULES.md 31.2)."""
    player_id = request.player_id if request is not None else None
    try:
        new_state = turn_flow.end_turn(ctx.service.current_state(), player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "turn:end")


@router.post("/turn/pass", response_model=StateEnvelope)
async def post_pass_turn(
    request: TurnActionRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Aktywny gracz pasuje (waliduje fazę/tura + akcję strategiczną — RULES.md 31.2)."""
    player_id = request.player_id if request is not None else None
    try:
        new_state = turn_flow.pass_turn(ctx.service.current_state(), player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "turn:pass")


@router.post("/turn/next-player", response_model=StateEnvelope)
async def post_next_player(
    request: TurnActionRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Przekazuje aktywność następnemu graczowi (initiative order) w STATUS/AGENDA.

    Proste przesunięcie wskaźnika aktywnego gracza — BEZ oznaczania „skończył fazę".
    Służy do przeklikiwania kolejnych graczy w AGENDZIE (operator przewija graczy,
    nikogo nie kończąc). Faza spoza STATUS/AGENDA → 422.
    """
    player_id = request.player_id if request is not None else None
    try:
        new_state = turn_flow.advance_active_player(
            ctx.service.current_state(), player_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "turn:next-player")


@router.post("/turn/phase-step", response_model=StateEnvelope)
async def post_phase_step(
    request: TurnActionRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Bieżący gracz KOŃCZY swoją część fazy STATUS/AGENDA i przekazuje dalej.

    Oznacza aktywnego gracza jako „skończył" (``passed=True``) i przesuwa wskaźnik do
    następnego (initiative order). Służy jako: STATUS „Next player" (gracz zrobił swój
    krok R31.3) oraz AGENDA „Pass" (gracz zrezygnował z reakcji/głosu). Dzięki temu
    ``all_passed`` wykrywa komplet i mówca dostaje „Next phase". Faza spoza
    STATUS/AGENDA → 422.
    """
    player_id = request.player_id if request is not None else None
    try:
        new_state = turn_flow.advance_active_player(
            ctx.service.current_state(), player_id, mark_passed=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "turn:phase-step")


@router.post("/phase/next", response_model=StateEnvelope)
async def post_next_phase(
    request: TurnActionRequest | None = None, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Przechodzi do następnej fazy rundy (Strategia→Akcja→Status→Agenda).

    Przejście fazy OGŁASZA MÓWCA (RULES.md 31.4): gdy podano ``player_id``, musi być
    równy ``speaker_id`` — inaczej 422. Pominięty ``player_id`` omija kontrolę
    tożsamości (zgodność wsteczna / wywołania wewnętrzne). God-Mode zmienia fazę
    własnym kanałem (``/god-mode/patch``) i tej walidacji nie przechodzi.
    """
    state = ctx.service.current_state()
    player_id = request.player_id if request is not None else None
    if player_id is not None and player_id != state.speaker_id:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Only the speaker announces a phase transition "
                f"(speaker: {state.speaker_id})."
            ),
        )
    # Brama „wszyscy skończyli" (akcja: pasy; status: kroki) — czytelny komunikat
    # zamiast surowego błędu z głębi silnika (DECYZJA PROJEKTOWA 2026-11).
    if not turn_flow.can_advance_phase(state):
        if state.phase is Phase.ACTION:
            detail = "Every player must pass before the speaker can end the Action Phase."
        elif state.phase is Phase.STATUS and state.winner_id is not None:
            detail = "The game has ended."
        elif state.phase is Phase.STATUS and state.status is not None:
            detail = (
                "Finish the Status Phase steps (score objectives, then redistribute "
                "command tokens) before the speaker can return the Strategy Cards."
            )
        elif state.phase is Phase.STATUS:
            detail = (
                "Every player must take their Status step before the speaker "
                "can end the Status Phase."
            )
        elif state.phase is Phase.AGENDA and state.winner_id is not None:
            detail = "The game has ended."
        elif state.phase is Phase.AGENDA:
            detail = (
                "Resolve both agendas (reveal, vote, outcome) before the speaker "
                "can end the Agenda Phase."
            )
        else:
            detail = "All players must pick their Strategy Cards before advancing."
        raise HTTPException(status_code=422, detail=detail)
    try:
        if state.phase is Phase.STATUS and state.status is not None:
            # Krok 8 fazy statusu: zwrot kart strategii, potem agenda albo nowa runda.
            new_state = status_phase.finish_status(state, ctx.registry)
        elif state.phase is Phase.AGENDA and state.agenda is not None:
            # Koniec fazy agendy (obie agendy + odświeżenie planet): nowa runda.
            new_state = agenda_phase.finish_agenda(state, ctx.registry)
        else:
            new_state = turn_flow.next_phase(state)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "phase:next")


@router.post("/phase/skip", response_model=StateEnvelope)
async def post_skip_phase(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Tryb testowy (God-Mode): przeskakuje fazę z pominięciem bram i okien.

    Włączany w UI ustawieniem „Skip phases". Zwykłe ``/phase/next`` zostaje bez zmian.
    """
    try:
        new_state = skip_flow.skip_phase(ctx.service.current_state(), ctx.registry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "phase:skip")


@router.post("/round/next", response_model=StateEnvelope)
async def post_next_round(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Rozpoczyna nową rundę: runda +1, faza = strategia, reset pasów.

    Na przełomie rundy karty strategii wracają do puli, a na każdej NIEWYBRANEJ
    karcie dokładany jest +1 trade good (RULES.md 13). Kolejność: accumulate → reset
    → next_round.
    """
    state = ctx.service.current_state()
    try:
        state = strategy_phase.close_round_cards(state, ctx.registry)
        state = turn_flow.next_round(state)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
            status_code=422, detail=f"Unknown player: {request.player_id}"
        )
    new_state = state.clone()
    strategy_phase.set_speaker(new_state, request.player_id)
    if request.player_id not in new_state.seating_order:
        new_state.seating_order = [*new_state.seating_order, request.player_id]
    # W fazie strategii zmiana mówcy przestawia, kto teraz wybiera (od nowego
    # mówcy w górę). Gdy wybór już skończony (picker = None), aktywny wskazuje
    # nowego mówcę — nie None (RULES.md 31.4, zasada "zawsze czyjaś tura").
    if new_state.phase is Phase.STRATEGY:
        new_state.active_player_id = (
            strategy_phase.next_strategy_picker(new_state) or new_state.speaker_id
        )
    return await _commit_flow(ctx, new_state, f"speaker:{request.player_id}")
