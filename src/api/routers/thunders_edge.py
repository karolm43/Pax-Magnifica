"""Router modułu Thunder's Edge — ekspedycje, The Fracture, Thunder's Edge (RULES.md 50).

Cienka warstwa nad ``core.expeditions`` i ``core.fracture``: odczyt stanu → core → commit →
broadcast → mapowanie ``ValueError`` na HTTP 422. Żadnej logiki gry w endpointach.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.api.schemas_thunders_edge import (
    ExpeditionRequest,
    FractureEnterRequest,
    IngressChoiceView,
    IngressRequest,
    PaymentOptions,
    SliceView,
    ThundersEdgeRequest,
    ThundersEdgeView,
)
from src.api.web_data import entity_key_map
from src.core import economy, expeditions, fracture, payment
from src.core import technology as tech
from src.core.expedition_state import EXPEDITION_SLICES
from src.core.game_state import GameState

router = APIRouter()


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


def _payment_options(ctx: AppContext, state: GameState) -> PaymentOptions:
    """Gotowe planety i TG aktywnego gracza (do płatności za plaster)."""
    active = state.active_player_id
    if active is None or active not in state.players:
        return PaymentOptions()
    registry = ctx.registry
    return PaymentOptions(
        resources=payment.ready_planet_values(state, registry, active, "resources"),
        influence=payment.ready_planet_values(state, registry, active, "influence"),
        trade_goods=economy.spendable_trade_goods(state, active),
        specialty_planets=sorted(tech.specialty_planets(state, registry, active)),
    )


def _build(ctx: AppContext, state: GameState) -> ThundersEdgeView:
    grid = ctx.current_grid
    registry = ctx.registry
    exp = state.expeditions
    active = state.active_player_id
    reason = expeditions.expedition_block_reason(state, active)
    placement = exp.pending_placement
    return ThundersEdgeView(
        slices=[SliceView(id=s, claimed_by=exp.claims.get(s)) for s in EXPEDITION_SLICES],
        free_slices=expeditions.free_slices(state),
        can_perform=reason == "",
        block_reason=reason,
        fracture_in_play=state.fracture.in_play,
        fracture_entered_by=state.fracture.entered_by,
        last_roll=state.fracture.last_roll,
        pending_ingress=[
            IngressChoiceView(
                color=c.color,
                remaining=c.remaining,
                candidates=fracture.ingress_candidates(state, registry, grid, c.color),
            )
            for c in state.fracture.pending
        ],
        placement_player=placement.player_id if placement else None,
        placement_targets=(
            expeditions.thunders_edge_targets(state, registry, grid) if placement else []
        ),
        placement_counts=dict(placement.counts) if placement else {},
        placement_leaders=list(placement.leaders) if placement else [],
        thunders_edge_position=exp.thunders_edge_position,
        payment=_payment_options(ctx, state),
        players=entity_key_map(state),
        log=list(state.fracture.log),
    )


def _actor(state: GameState, actor_id: str | None) -> str:
    resolved = actor_id or state.active_player_id
    if resolved is None:
        raise HTTPException(status_code=422, detail="There is no active player.")
    return resolved


@router.get("/thunders-edge", response_model=ThundersEdgeView, response_model_by_alias=True)
async def get_thunders_edge(ctx: AppContext = Depends(get_ctx)) -> ThundersEdgeView:
    """Stan ekspedycji, The Fracture (rzut, oczekujące ingress) i Thunder's Edge."""
    return _build(ctx, ctx.service.current_state())


@router.post("/expeditions/perform", response_model=StateEnvelope)
async def post_perform_expedition(
    request: ExpeditionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Aktywny gracz wykonuje ekspedycję (plaster + płatność) na koniec swojej tury."""
    state = ctx.service.current_state()
    actor = _actor(state, request.actor_id)
    pay = expeditions.ExpeditionPayment(
        planets=request.payment.planets,
        trade_goods=request.payment.trade_goods,
        action_cards=request.payment.action_cards,
        secret=request.payment.secret,
        tech_planet=request.payment.tech_planet,
    )
    try:
        new_state = expeditions.perform_expedition(
            state, ctx.registry, ctx.current_grid, actor, request.slice, pay
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"expedition:{actor}:{request.slice}")


@router.post("/fracture/ingress", response_model=StateEnvelope)
async def post_fracture_ingress(
    request: IngressRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz, który wprowadził The Fracture, kładzie żeton ingress w wybranym systemie."""
    state = ctx.service.current_state()
    actor = request.actor_id or state.fracture.entered_by
    if actor is None:
        raise HTTPException(status_code=422, detail="There is no ingress token to place.")
    try:
        new_state = fracture.choose_ingress(
            state, ctx.registry, ctx.current_grid, actor, request.color, request.position
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"fracture:ingress:{request.position}")


@router.post("/thunders-edge/place", response_model=StateEnvelope)
async def post_place_thunders_edge(
    request: ThundersEdgeRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz z 6. plastrem kładzie Thunder's Edge; piechotę stawia lider ekspedycji."""
    state = ctx.service.current_state()
    pending = state.expeditions.pending_placement
    actor = request.actor_id or (pending.player_id if pending else None)
    if actor is None:
        raise HTTPException(status_code=422, detail="Thunder's Edge is not waiting to be placed.")
    try:
        new_state = expeditions.place_thunders_edge(
            state,
            ctx.registry,
            ctx.current_grid,
            actor,
            request.position,
            request.infantry_player_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"thunders-edge:place:{request.position}")


@router.post("/god-mode/fracture", response_model=StateEnvelope)
async def post_god_mode_fracture(
    request: FractureEnterRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """God-Mode (wentyl): wprowadza The Fracture do gry bez rzutu i bez sprawdzania reguł."""
    state = ctx.service.current_state()
    actor = _actor(state, request.actor_id)
    try:
        new_state = fracture.enter_play(
            state, ctx.registry, ctx.current_grid, actor, request.breakthrough_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"god-mode-patch:fracture:{actor}")
