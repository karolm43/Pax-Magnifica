"""Router kart akcji: zagranie karty z oknem ACTION jako akcji komponentu (RULES.md 53)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.actor import ActorId, require_view
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    ActionCardInputsResponse,
    ActionCardPlayability,
    ActionCardPlayabilityResponse,
    DiscardExcessRequest,
    HeldActionRequest,
    PlayActionCardRequest,
    PlayActionCardResponse,
    StateEnvelope,
)
from src.core import action_cards, card_hold, hand_limit, hold_rewind
from src.core import actor as actor_rules
from src.core.components import ComponentCategory
from src.core.game_state import GameState

router = APIRouter()


@router.get("/action-card/playable", response_model=ActionCardPlayabilityResponse)
async def get_playable_action_cards(
    request: Request,
    player_id: str, ctx: AppContext = Depends(get_ctx)
) -> ActionCardPlayabilityResponse:
    """Które karty z ręki gracza można zagrać teraz (UI pozwala podnieść tylko te)."""
    require_view(request, player_id)  # RULES.md 44.3
    state = ctx.service.current_state()
    try:
        rows = action_cards.playability(state, ctx.registry, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Karty reakcji, których okno minęło ostatnim krokiem: zagrywalne przez hold-rewind (53.7).
    chain = [
        hold_rewind.Snapshot(seq, label, snap)
        for seq, label, snap in ctx.service.recent_chain(2)
    ]
    passed = hold_rewind.just_passed(chain, ctx.registry, player_id)
    for row in rows:
        seq = passed.get(str(row["card_id"]))
        if seq is not None and not row["playable"]:
            row.update(playable=True, reason=None, reaction=True, hold_seq=seq)
    return ActionCardPlayabilityResponse(
        cards=[ActionCardPlayability(**row) for row in rows],
        discard=hand_limit.action_card_excess(state, player_id),
        handLimit=hand_limit.action_card_limit(state, player_id),
    )


@router.post("/action-card/discard-excess", response_model=StateEnvelope)
async def post_discard_excess(
    actor: ActorId,
    request: DiscardExcessRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz ponad limitem ręki odrzuca wybraną kartę akcji (R_action_cards, RULES.md 53.8)."""
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = hand_limit.discard_excess(
            ctx.service.current_state(), request.actor_id, request.card_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_held(ctx, new_state, f"action-card:discard-excess:{request.card_id}")


@router.get("/action-card/{card_id}/inputs", response_model=ActionCardInputsResponse)
async def get_action_card_inputs(
    request: Request,
    card_id: str, player_id: str, ctx: AppContext = Depends(get_ctx)
) -> ActionCardInputsResponse:
    """Formularz zagrania karty: tekst, czy silnik ją automatyzuje i legalne wybory gracza."""
    require_view(request, player_id)  # RULES.md 44.3
    try:
        implemented, inputs = action_cards.card_inputs(
            ctx.service.current_state(), ctx.registry, player_id, card_id
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
        summary=action_cards.card_summary(
            ctx.service.current_state(), ctx.registry, player_id, card_id
        ),
    )


@router.post("/action-card/play", response_model=PlayActionCardResponse)
async def post_play_action_card(
    actor: ActorId,
    request: PlayActionCardRequest, ctx: AppContext = Depends(get_ctx)
) -> PlayActionCardResponse:
    """Gracz zagrywa kartę akcji (okno ACTION) - jego akcja w turze; efekt wg silnika.

    Karta bez zaimplementowanego efektu jest zagrana i odrzucona, a odpowiedź ma
    ``implemented=false`` - skutek rozstrzyga operator (God-Mode). ``ValueError`` -> HTTP 422.
    """
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state, implemented = action_cards.play_action_card(
            ctx.service.current_state(),
            ctx.registry,
            request.player_id,
            request.card_id,
            request.params,
            actor_id=request.actor_id,
            now=ctx.service.now(),  # czas serwera włącza okno hold-play (RULES.md 53.6)
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    held = new_state.held_play is not None
    label = f"action-card:{request.card_id}" + (":held" if held else "")
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return PlayActionCardResponse(
        envelope=ctx.service.envelope(), implemented=implemented, held=held
    )


async def _commit_held(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


@router.post("/action-card/held/pass", response_model=StateEnvelope)
async def post_held_pass(
    actor: ActorId,
    request: HeldActionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Pas uprawnionego gracza w oknie hold-play (okno trwa stały czas, RULES.md 54.11)."""
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = card_hold.pass_hold(
            ctx.service.current_state(), ctx.registry, request.actor_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_held(ctx, new_state, "action-card:held-pass")


@router.post("/action-card/held/wait", response_model=StateEnvelope)
async def post_held_wait(
    actor: ActorId,
    request: HeldActionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """„More time” w oknie Sabotage: +10 s raz na gracza (anonimowo, RULES.md 54.11)."""
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = card_hold.ask_for_time(ctx.service.current_state(), request.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_held(ctx, new_state, "reaction-wait")


@router.post("/action-card/held/freeze", response_model=StateEnvelope)
async def post_held_freeze(
    actor: ActorId,
    request: HeldActionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Zatrzymuje zegar okna, gdy gracz zagrywa Sabotage (przeciąga kartę / wypełnia formularz)."""
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = card_hold.freeze(
            ctx.service.current_state(), request.actor_id, ctx.service.now()
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_held(ctx, new_state, "reaction-freeze")


@router.post("/action-card/held/unfreeze", response_model=StateEnvelope)
async def post_held_unfreeze(
    actor: ActorId,
    request: HeldActionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Wznawia zegar okna po zatrzymaniu (bez zatrzymania = bez zmian)."""
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    new_state = card_hold.unfreeze(
        ctx.service.current_state(), request.actor_id, ctx.service.now()
    )
    return await _commit_held(ctx, new_state, "reaction-unfreeze")


@router.post("/action-card/held/release", response_model=StateEnvelope)
async def post_held_release(
    actor: ActorId,
    request: HeldActionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Zwalnia okno hold-play, gdy minął jego stały czas wg zegara serwera."""
    # Aktor z nagłówka i pole actor_id w treści muszą się zgadzać (RULES.md 44.1a).
    request.actor_id = actor_rules.merge_claimed(actor, request.actor_id)
    try:
        new_state = card_hold.release(
            ctx.service.current_state(), ctx.registry, request.actor_id, now=ctx.service.now()
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_held(ctx, new_state, "action-card:held-release")
