"""Router eksploracji — okno po Establish Control (RULES.md 46): stan, wybór planety, karta.

Cienka warstwa nad ``core.exploration``: odczyt stanu → core → commit → broadcast →
mapowanie ``ValueError`` na HTTP 422.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.api.schemas_exploration import (
    ExplorationChooseRequest,
    ExplorationDrawRequest,
    ExplorationResolveRequest,
    ExplorationResponse,
    ExploreCardView,
    ExploreCurrentView,
    ExploreLogItem,
    ExploreOptionView,
    ExploreParamView,
    ExploreQueueItem,
)
from src.api.web_data import entity_key_map
from src.core import actor as actor_rules
from src.core import exploration
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

router = APIRouter()


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


def _card_view(
    registry: StaticDataRegistry, card_id: str, deck: str
) -> ExploreCardView:
    card = exploration.card_def(registry, card_id)
    return ExploreCardView(
        card_id=card_id,
        name=card.name or card_id,
        deck=deck,
        resolution=card.resolution or "",
        text=str(card.raw.get("text", "")),
        flavor_text=str(card.raw.get("flavorText", "")).strip("*"),
    )


def _build(ctx: AppContext, state: GameState) -> ExplorationResponse:
    ex = state.exploration
    if ex is None:
        return ExplorationResponse(active=False)
    registry = ctx.registry
    keys = entity_key_map(state)
    current: ExploreCurrentView | None = None
    if ex.current is not None:
        current = ExploreCurrentView(
            planet=ex.current.planet,
            card=_card_view(registry, ex.current.card_id, ex.current.deck),
            options=[
                ExploreOptionView(
                    id=o.id,
                    label=o.label,
                    enabled=o.enabled,
                    reason=o.reason,
                    params=[ExploreParamView(id=pid, label=lab) for pid, lab in o.params],
                )
                for o in exploration.options_for(state, registry)
            ],
            candidates=[
                _card_view(registry, card_id, ex.current.deck)
                for card_id in ex.current.candidates
            ],
        )
    return ExplorationResponse(
        active=True,
        player=keys.get(ex.player_id, ex.player_id),
        position=ex.position,
        queue=[
            ExploreQueueItem(
                planet=p,
                traits=exploration.planet_traits(registry, p, state),
                extra_draw=exploration.extra_draw_allowed(state, ex.player_id, p),
            )
            for p in ex.queue
        ],
        current=current,
        log=[
            ExploreLogItem(
                planet=str(e["planet"]),
                deck=str(e["deck"]),
                card=_card_view(registry, str(e["cardId"]), str(e["deck"])),
                summary=str(e["summary"]),
                fate=str(e["fate"]),
            )
            for e in ex.log
        ],
        done=ex.current is None and not ex.queue,
    )


@router.get("/exploration", response_model=ExplorationResponse, response_model_by_alias=True)
async def get_exploration(ctx: AppContext = Depends(get_ctx)) -> ExplorationResponse:
    """Stan okna eksploracji (kolejka planet, ujawniona karta, opcje, historia)."""
    return _build(ctx, ctx.service.current_state())


@router.post("/exploration/draw", response_model=StateEnvelope)
async def post_exploration_draw(
    actor: ActorId,
    request: ExplorationDrawRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Wybiera następną planetę (i talię) i ujawnia kartę eksploracji."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.exploring_player, "Explore"
    )
    try:
        new_state = exploration.draw(
            ctx.service.current_state(), ctx.registry, request.planet, request.deck,
            extra=request.extra,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"exploration:draw:{request.planet}")


@router.post("/exploration/choose", response_model=StateEnvelope)
async def post_exploration_choose(
    actor: ActorId,
    request: ExplorationChooseRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Distant Suns: wybiera 1 z dobranych kart do rozstrzygnięcia (reszta odrzucona)."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.exploring_player,
        "Choose exploration card",
    )
    try:
        new_state = exploration.choose(ctx.service.current_state(), request.card)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"exploration:choose:{request.card}")


@router.post("/exploration/resolve", response_model=StateEnvelope)
async def post_exploration_resolve(
    actor: ActorId,
    request: ExplorationResolveRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Rozstrzyga ujawnioną kartę wybraną opcją."""
    actor_rules.check(
        ctx.service.current_state(),
        actor,
        None,
        actor_rules.exploring_player,
        "Resolve exploration",
    )
    try:
        new_state = exploration.resolve(
            ctx.service.current_state(), ctx.registry, request.option, request.param
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"exploration:resolve:{request.option}")


@router.post("/exploration/finish", response_model=StateEnvelope)
async def post_exploration_finish(
    actor: ActorId, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Zamyka okno eksploracji po rozstrzygnięciu wszystkich planet."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.exploring_player, "Finish exploration"
    )
    try:
        new_state = exploration.finish(ctx.service.current_state())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "exploration:finish")
