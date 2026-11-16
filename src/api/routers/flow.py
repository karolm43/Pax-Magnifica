"""Router przepływu faz i tur (Etap E1): koniec tury, pas, następna faza, nowa runda."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId, HostOnly
from src.api.context import AppContext, get_ctx
from src.api.schemas import SetSpeakerRequest, StateEnvelope, TurnActionRequest
from src.core import actor as actor_rules
from src.core import phase_flow, skip_flow, strategy_phase, turn_flow
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
    actor: ActorId,
    request: TurnActionRequest | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> StateEnvelope:
    """Kończy turę aktywnego gracza (waliduje fazę/tura — RULES.md 31.2).

    Trwająca akcja taktyczna jest zamykana z walidacją (RULES.md 31.9); wykryta nadwyżka
    pojemności / puli floty otwiera okno i zostawia turę graczowi.
    """
    state = ctx.service.current_state()
    actor_rules.require(state, actor, actor_rules.turn_player(state), "Turn")
    player_id = actor_rules.subject(state, actor, request.player_id if request else None)
    try:
        new_state = turn_flow.end_turn(
            ctx.service.current_state(), player_id, registry=ctx.registry
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    label = "turn:end" if new_state.pending_window is None else "turn:end-blocked"
    return await _commit_flow(ctx, new_state, label)


@router.post("/turn/pass", response_model=StateEnvelope)
async def post_pass_turn(
    actor: ActorId,
    request: TurnActionRequest | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> StateEnvelope:
    """Aktywny gracz pasuje (waliduje fazę/tura + akcję strategiczną — RULES.md 31.2)."""
    state = ctx.service.current_state()
    actor_rules.require(state, actor, actor_rules.turn_player(state), "Turn")
    player_id = actor_rules.subject(state, actor, request.player_id if request else None)
    try:
        new_state = turn_flow.pass_turn(ctx.service.current_state(), player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "turn:pass")


@router.post("/turn/next-player", response_model=StateEnvelope)
async def post_next_player(
    actor: ActorId,
    request: TurnActionRequest | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> StateEnvelope:
    """Przekazuje aktywność następnemu graczowi (initiative order) w STATUS/AGENDA.

    Proste przesunięcie wskaźnika aktywnego gracza — BEZ oznaczania „skończył fazę".
    Służy do przeklikiwania kolejnych graczy w AGENDZIE (operator przewija graczy,
    nikogo nie kończąc). Faza spoza STATUS/AGENDA → 422.
    """
    state = ctx.service.current_state()
    actor_rules.require(state, actor, actor_rules.turn_player(state), "Turn")
    player_id = actor_rules.subject(state, actor, request.player_id if request else None)
    try:
        new_state = turn_flow.advance_active_player(
            ctx.service.current_state(), player_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "turn:next-player")


@router.post("/turn/phase-step", response_model=StateEnvelope)
async def post_phase_step(
    actor: ActorId,
    request: TurnActionRequest | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> StateEnvelope:
    """Bieżący gracz KOŃCZY swoją część fazy STATUS/AGENDA i przekazuje dalej.

    Oznacza aktywnego gracza jako „skończył" (``passed=True``) i przesuwa wskaźnik do
    następnego (initiative order). Służy jako: STATUS „Next player" (gracz zrobił swój
    krok R31.3) oraz AGENDA „Pass" (gracz zrezygnował z reakcji/głosu). Dzięki temu
    ``all_passed`` wykrywa komplet i mówca dostaje „Next phase". Faza spoza
    STATUS/AGENDA → 422.
    """
    state = ctx.service.current_state()
    actor_rules.require(state, actor, actor_rules.turn_player(state), "Turn")
    player_id = actor_rules.subject(state, actor, request.player_id if request else None)
    try:
        new_state = turn_flow.advance_active_player(
            ctx.service.current_state(), player_id, mark_passed=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "turn:phase-step")


@router.post("/phase/next", response_model=StateEnvelope)
async def post_next_phase(
    actor: ActorId,
    request: TurnActionRequest | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> StateEnvelope:
    """Przechodzi do następnej fazy rundy (Strategia→Akcja→Status→Agenda).

    Przejście fazy OGŁASZA MÓWCA (RULES.md 31.4): gdy podano ``player_id``, musi być
    równy ``speaker_id`` — inaczej 422. Pominięty ``player_id`` omija kontrolę
    tożsamości (zgodność wsteczna / wywołania wewnętrzne). God-Mode zmienia fazę
    własnym kanałem (``/god-mode/patch``) i tej walidacji nie przechodzi.
    """
    state = ctx.service.current_state()
    # Przejście fazy ogłasza mówca (RULES.md 31.4) — obcy aktor: 403, nie 422.
    actor_rules.require(state, actor, actor_rules.speaker(state), "Next phase")
    player_id = actor_rules.subject(state, actor, request.player_id if request else None)
    # Brama „wszyscy skończyli" i wybór domknięcia fazy: core/phase_flow (wspólne z botem).
    try:
        new_state = phase_flow.announce_next_phase(state, ctx.registry, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "phase:next")


@router.post("/phase/skip", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_skip_phase(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Tryb testowy (God-Mode): przeskakuje fazę z pominięciem bram i okien.

    Włączany w UI ustawieniem „Skip phases". Zwykłe ``/phase/next`` zostaje bez zmian.
    """
    try:
        new_state = skip_flow.skip_phase(ctx.service.current_state(), ctx.registry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "phase:skip")


@router.post("/turn/skip-player", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_skip_player(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Tryb testowy (God-Mode): oddaje turę następnemu graczowi bez akcji/pasa.

    Widoczny w UI razem z „Skip phase" (ustawienie „Skip phases").
    """
    try:
        new_state = skip_flow.skip_player(ctx.service.current_state())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "turn:skip-player")


@router.post("/round/next", response_model=StateEnvelope)
async def post_next_round(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Rozpoczyna nową rundę: runda +1, faza = strategia, reset pasów.

    Na przełomie rundy karty strategii wracają do puli, a na każdej NIEWYBRANEJ
    karcie dokładany jest +1 trade good (RULES.md 13). Kolejność: accumulate → reset
    → next_round.
    """
    state = ctx.service.current_state()
    # Nową rundę ogłasza mówca (RULES.md 31.4).
    actor_rules.require(state, actor, actor_rules.speaker(state), "New round")
    try:
        state = phase_flow.announce_next_round(state, ctx.registry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, state, "round:next")


@router.post("/speaker/set", dependencies=[HostOnly], response_model=StateEnvelope)
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
