"""Router okna produkcji (RULES.md 33.3): widok liczbowy kroku PRODUCTION.

Cienka warstwa nad ``core.production``: odczyt stanu → obliczenia → słownik dla okna.
Samo zamawianie idzie przez ``POST /tactical/produce`` (router taktyczny).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import StateEnvelope
from src.core import invasion, production, tactical
from src.core.planet_stats import influence_of, resources_of
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

router = APIRouter()


@router.get("/tactical/production/view")
async def get_production_view(ctx: AppContext = Depends(get_ctx)) -> dict[str, Any]:
    """Wszystko, czego okno produkcji potrzebuje: limit, producenci, planety, jednostki."""
    state = ctx.service.current_state()
    player_id = state.active_player_id
    position = state.active_system
    if player_id is None or position is None or player_id not in state.players:
        return {"active": False}
    registry = ctx.registry
    player = state.players[player_id]

    grant = production.active_grant(state, player_id)
    limit = (
        grant.units
        if grant is not None
        else production.production_limit(state, ctx.current_grid, registry, player_id)
    )
    remaining = production.remaining_production(state, ctx.current_grid, registry, player_id)
    producers = []
    for p in production.producers(state, registry, player_id, position):
        variant = invasion.unit_variant(state, registry, player_id, p.base_type)
        producers.append(
            {
                "zone": p.zone,
                "baseType": p.base_type,
                "asyncId": ASYNC_ID_BY_BASE_TYPE.get(p.base_type, p.base_type),
                "name": variant.name if variant is not None else p.base_type,
                "count": p.count,
                "value": p.value,
                "perUnit": p.per_unit,
                "forbids": list(p.forbids),
            }
        )

    exhausted = set(player.exhausted_planets)
    planets = []
    for pos, system in state.systems.items():
        for planet_id, owner in system.planet_owners.items():
            if owner != player_id:
                continue
            info = registry.planets.get(planet_id)
            res = resources_of(state, registry, planet_id)
            planets.append(
                {
                    "planet": planet_id,
                    "name": info.name if info is not None else planet_id,
                    "position": pos,
                    "resources": res,
                    "influence": influence_of(state, registry, planet_id),
                    # Ile planeta wnosi do płatności (Freelancers: wpływ liczy się jak zasoby).
                    "payValue": production.pay_value(state, registry, planet_id, player_id),
                    "planetType": info.planet_type if info is not None else None,
                    "exhausted": planet_id in exhausted,
                    "inActiveSystem": pos == position,
                }
            )

    units = []
    for u in tactical.production_help(state, registry, player_id).units:
        if u.base_type in production.STRUCTURES:
            continue
        units.append(
            {
                "baseType": u.base_type,
                "asyncId": u.async_id,
                "name": u.name,
                "cost": u.cost,
                "unitsPerCost": u.units_per_cost,
                "placement": u.placement,
                "reinforcements": production.reinforcements_left(
                    state, player_id, u.base_type
                ),
                "onBoard": production.deployed_count(state, player_id, u.base_type),
            }
        )

    return {
        "active": True,
        "grant": (
            {
                "source": grant.source,
                "units": grant.units,
                "influenceAsResources": grant.influence_as_resources,
            }
            if grant is not None
            else None
        ),
        "position": position,
        "playerId": player_id,
        "faction": player.faction,
        "limit": limit,
        "used": 0 if grant is not None else state.production_used,
        "usedByType": production.used_by_type(state),
        "remaining": remaining,
        "blockaded": production.is_blockaded(state, player_id, position),
        "producers": producers,
        "groundZones": production.allowed_ground_zones(
            state, registry, player_id, position
        ),
        "planets": planets,
        "tradeGoods": player.trade_goods,
        "units": units,
    }


@router.post("/tactical/production/skip-grant", response_model=StateEnvelope)
async def post_skip_grant(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Rezygnacja z jednorazowej produkcji z karty (np. Freelancers)."""
    try:
        new_state = production.skip_grant(ctx.service.current_state())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label="production:skip-grant")
    await ctx.service.broadcast()
    return ctx.service.envelope()
