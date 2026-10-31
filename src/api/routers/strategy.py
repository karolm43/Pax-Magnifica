"""Router fazy strategii (Etap E2): pula kart, wybór, zagranie."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    StateEnvelope,
    StrategyCardInfo,
    StrategyPickRequest,
    StrategyPlayRequest,
    StrategySecondaryRequest,
)
from src.core import strategic_action, strategy_phase
from src.core.models import StrategyCardDef

router = APIRouter()


def _ensure_card_fields_complete(cards: list[StrategyCardDef]) -> None:
    """Sprawdza komplet pól per-karta wymaganych do opisu puli (R6.4).

    Dla każdej karty wymagamy: nazwy, tekstu primary, tekstu secondary oraz
    koloru (``initiative`` jest już zwalidowana przez
    ``validate_strategy_card_set``). Gdy któregokolwiek pola brakuje w danych
    rejestru → ``ValueError("Karta {id}: brak pola {pole}.")`` (mapowane na 422).
    Zero wartości kodowanych w module — wyłącznie odczyt z rejestru.
    """
    for card in cards:
        if not card.name:
            raise ValueError(f"Karta {card.id}: brak pola nazwa.")
        if not card.primary_texts:
            raise ValueError(f"Karta {card.id}: brak pola tekst primary.")
        if not card.secondary_texts:
            raise ValueError(f"Karta {card.id}: brak pola tekst secondary.")
        if not card.colour_hex_code:
            raise ValueError(f"Karta {card.id}: brak pola kolor.")


@router.get("/strategy/cards", response_model=list[StrategyCardInfo])
def get_strategy_cards(ctx: AppContext = Depends(get_ctx)) -> list[StrategyCardInfo]:
    """Pula kart strategii aktywnego zestawu + ich stan w bieżącej grze.

    Guard spójności danych rejestru: najpierw ``validate_strategy_card_set``
    (komplet/unikalność — R6.2), potem kontrola kompletu pól każdej karty
    (R6.4); oba błędy domenowe (``ValueError``) mapujemy na HTTP 422.
    """
    try:
        card_set = strategy_phase.validate_strategy_card_set(ctx.registry)
        _ensure_card_fields_complete(card_set)
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


async def _commit(ctx: AppContext, new_state, label: str) -> StateEnvelope:  # type: ignore[no-untyped-def]
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/strategy/pick", response_model=StateEnvelope)
async def post_strategy_pick(
    request: StrategyPickRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz wybiera kartę strategii (transfer TG z karty, ustala inicjatywę)."""
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
    request: StrategyPlayRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Akcja strategiczna: rozstrzyga PRIMARY i otwiera okno SECONDARY (RULES.md 30).

    Zastępuje dawne „tylko oznacz zagraną": teraz zagranie karty wykonuje efekt primary
    (dispatch po karcie — w T3 realnie Leadership) i otwiera okno secondary dla
    pozostałych graczy (kolejka od gracza po aktywnym, zgodnie z zegarem).
    """
    try:
        new_state = strategic_action.play_strategy_card(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.initiative,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, f"strategy:play:{request.player_id}:{request.initiative}"
    )


@router.post("/strategy/secondary", response_model=StateEnvelope)
async def post_strategy_secondary(
    request: StrategySecondaryRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Odpowiedź bieżącego respondenta w oknie secondary (wykonaj/pas) — RULES.md 30.1.

    Przesuwa kolejkę okna; po dopełnieniu okno zamyka się samo. ``execute=True`` wykonuje
    efekt secondary (w T3 Leadership = szkielet bez kupna żetonów za wpływ).
    """
    try:
        new_state = strategic_action.resolve_secondary(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            execute=request.execute,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    decision = "exec" if request.execute else "pass"
    return await _commit(
        ctx, new_state, f"strategy:secondary:{request.player_id}:{decision}"
    )
