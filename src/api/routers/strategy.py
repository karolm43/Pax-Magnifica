"""Router fazy strategii (Etap E2): pula kart, wybór, zagranie."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.actor import ActorId, require_view
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    StateEnvelope,
    StrategyCardInfo,
    StrategyPickRequest,
    StrategyPlayRequest,
    StrategyPrimaryStepRequest,
    StrategySecondaryRequest,
)
from src.core import actor as actor_rules
from src.core import strategic_action, strategy_phase

router = APIRouter()


@router.get("/strategy/cards", response_model=list[StrategyCardInfo])
def get_strategy_cards(ctx: AppContext = Depends(get_ctx)) -> list[StrategyCardInfo]:
    """Pula kart strategii aktywnego zestawu + ich stan w bieżącej grze.

    Guard spójności danych rejestru: ``validate_strategy_card_set`` sprawdza komplet
    8 kart/unikalność inicjatyw ORAZ komplet pól każdej karty (R6.2, R6.4 — kontrola
    pól przeniesiona do ``core/`` w ramach znaleziska #4 przeglądu). Błąd domenowy
    (``ValueError``) mapujemy na HTTP 422.
    """
    try:
        card_set = strategy_phase.validate_strategy_card_set(ctx.registry)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    state = ctx.service.current_state()
    owner_by_init: dict[int, str] = {}
    exhausted_by_init: dict[int, bool] = {}
    for pid, player in state.players.items():
        for init in player.strategy_cards:
            owner_by_init[init] = pid
            exhausted_by_init[init] = init in player.exhausted_strategy_cards
    cards: list[StrategyCardInfo] = []
    for card in card_set:
        cards.append(
            StrategyCardInfo(
                initiative=card.initiative,
                id=card.id,
                name=card.name,
                primary_texts=list(card.primary_texts),
                secondary_texts=list(card.secondary_texts),
                colour_hex_code=card.colour_hex_code,
                trade_goods=state.strategy_card_tg.get(card.initiative, 0),
                picked_by=owner_by_init.get(card.initiative),
                exhausted=exhausted_by_init.get(card.initiative, False),
            )
        )
    return cards


@router.get("/strategy/options")
def get_strategy_options(
    request: Request,
    player_id: str, ctx: AppContext = Depends(get_ctx)
) -> dict[str, Any] | None:
    """Dozwolone wybory dla gracza, który teraz odpowiada na kartę strategii (lub null).

    Monit primary (właściciel karty) albo secondary (bieżący respondent okna), razem z
    opcjami z modułu karty (planety do wydania, cele, gracze...). Dane prywatne dostaje
    tylko ``player_id`` będący adresatem monitu (pod grę sieciową).
    """
    require_view(request, player_id)  # RULES.md 44.3
    state = ctx.service.current_state()
    if player_id not in state.players:
        raise HTTPException(status_code=404, detail=f"Unknown player: {player_id}")
    return strategic_action.step_options(state, ctx.registry, player_id, ctx.current_grid)


async def _commit(ctx: AppContext, new_state, label: str) -> StateEnvelope:  # type: ignore[no-untyped-def]
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/strategy/pick", response_model=StateEnvelope)
async def post_strategy_pick(
    actor: ActorId,
    request: StrategyPickRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz wybiera kartę strategii (transfer TG z karty, ustala inicjatywę)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.player_id, None, "Pick strategy card"
    )
    try:
        new_state = strategy_phase.pick_strategy_card(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.initiative,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, f"strategy:pick:{request.player_id}:{request.initiative}"
    )


@router.post("/strategy/play", response_model=StateEnvelope)
async def post_strategy_play(
    actor: ActorId,
    request: StrategyPlayRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Akcja strategiczna: rozstrzyga PRIMARY i otwiera okno SECONDARY (RULES.md 30).

    Zastępuje dawne „tylko oznacz zagraną": teraz zagranie karty wykonuje efekt primary
    (dispatch po karcie — w T3 realnie Leadership) i otwiera okno secondary dla
    pozostałych graczy (kolejka od gracza po aktywnym, zgodnie z zegarem).
    """
    actor_rules.check(
        ctx.service.current_state(), actor, request.player_id, None, "Play strategy card"
    )
    try:
        new_state = strategic_action.play_strategy_card(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.initiative,
            grid=ctx.current_grid,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, f"strategy:play:{request.player_id}:{request.initiative}"
    )


@router.post("/strategy/primary-step", response_model=StateEnvelope)
async def post_strategy_primary_step(
    actor: ActorId,
    request: StrategyPrimaryStepRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Wybór aktywnego gracza dla bieżącego kroku wieloetapowego primary (RULES.md 30.5).

    Tylko właściciel karty; po ostatnim kroku silnik stosuje primary i otwiera okno
    secondary. Zły payload / nie ten gracz → 422.
    """
    actor_rules.check(
        ctx.service.current_state(), actor, request.player_id, None, "Primary ability"
    )
    try:
        new_state = strategic_action.submit_primary_step(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.payload,
            grid=ctx.current_grid,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"strategy:primary-step:{request.player_id}")


@router.post("/strategy/secondary", response_model=StateEnvelope)
async def post_strategy_secondary(
    actor: ActorId,
    request: StrategySecondaryRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Odpowiedź bieżącego respondenta w oknie secondary (wykonaj/pas) — RULES.md 30.1.

    Przesuwa kolejkę okna; po dopełnieniu okno zamyka się samo. ``execute=True`` wykonuje
    efekt secondary (w T3 Leadership = szkielet bez kupna żetonów za wpływ).
    """
    actor_rules.check(
        ctx.service.current_state(), actor, request.player_id, None, "Secondary ability"
    )
    try:
        new_state = strategic_action.resolve_secondary(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            execute=request.execute,
            payload=request.payload,
            grid=ctx.current_grid,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    decision = "exec" if request.execute else "pass"
    return await _commit(
        ctx, new_state, f"strategy:secondary:{request.player_id}:{decision}"
    )
