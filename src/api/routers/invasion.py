"""Router inwazji — okno inwazji (RULES.md 40): stan, bombardowanie, lądowanie, obrona, dalej.

Cienka warstwa nad ``core.invasion``: odczyt stanu → core → commit → broadcast → mapowanie
``ValueError`` na HTTP 422. Walka naziemna idzie istniejącym routerem ``/tactical/battle/*``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.schemas import BattleLossItem, StateEnvelope
from src.api.schemas_invasion import (
    BombardGroupView,
    BombardPendingView,
    BombardView,
    CustodiansView,
    DefensePlanetView,
    DefenseShooterView,
    InvasionAssignRequest,
    InvasionBombardRequest,
    InvasionCommitRequest,
    InvasionCustodiansRequest,
    InvasionPlanetRequest,
    InvasionPlanetView,
    InvasionResponse,
    InvasionUnitView,
)
from src.api.web_data import entity_key_map
from src.core import actor as actor_rules
from src.core import battle, board_edit, custodians, economy, invasion, payment, space_cannon
from src.core.damage import damaged_count
from src.core.game_state import GameState, SystemState
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

router = APIRouter()


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    """Commit wyniku funkcji inwazji + rozesłanie stanu i mapy."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


def _items(items: list[BattleLossItem]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        if item.count > 0:
            result[item.base_type] = result.get(item.base_type, 0) + item.count
    return result


def _units_view(
    state: GameState,
    ctx: AppContext,
    system: SystemState,
    zone: str,
    player_id: str,
    units: dict[str, int],
    *,
    ground: bool,
) -> list[InvasionUnitView]:
    views: list[InvasionUnitView] = []
    for base_type, count in sorted(units.items()):
        if count <= 0 or (base_type in invasion.GROUND_FORCES) != ground:
            continue
        variant = invasion.unit_variant(state, ctx.registry, player_id, base_type)
        views.append(
            InvasionUnitView(
                base_type=base_type,
                async_id=ASYNC_ID_BY_BASE_TYPE.get(base_type, base_type),
                name=variant.name if variant is not None else base_type,
                count=count,
                damaged=damaged_count(system, zone, player_id, base_type),
                sustain=variant.sustain_damage if variant is not None else False,
                base_hits_on=(variant.combat_hits_on or 0) if variant is not None else 0,
            )
        )
    return views


def _log_entry(raw: dict[str, Any], key: Any) -> dict[str, Any]:
    entry = dict(raw)
    defender = entry.get("defender")
    entry["defender"] = key(defender) if defender else None
    entry["rolls"] = [
        {**r, "owner": key(r["owner"])} if r.get("owner") else r for r in entry.get("rolls", [])
    ]
    return entry


def _custodians_view(ctx: AppContext, state: GameState) -> CustodiansView | None:
    """Żeton Custodians — tylko w inwazji na system Mecatol Rex (inaczej ``None``)."""
    inv = state.invasion
    if inv is None:
        return None
    registry = ctx.registry
    if not custodians.mecatol_planets(state, registry, inv.position):
        return None
    reason = invasion.custodians_block_reason(state, registry)
    return CustodiansView(
        on_board=custodians.on_board(state),
        claimed=inv.custodians_claimed,
        can_claim=reason is None,
        reason=reason,
        cost=custodians.removal_cost(state, inv.attacker),
        influence=custodians.influence_options(state, registry, inv.attacker),
        trade_goods=economy.spendable_trade_goods(state, inv.attacker),
        trade_good_value=payment.trade_good_value(state, inv.attacker),
        blocked_planets=sorted(custodians.landing_blocked(state, registry, inv.position)),
    )


def _build(ctx: AppContext, state: GameState) -> InvasionResponse:
    inv = state.invasion
    if inv is None:
        return InvasionResponse(active=False)
    keys = entity_key_map(state)

    def key(player_id: str) -> str:
        return keys.get(player_id, player_id)

    grid = ctx.current_grid
    registry = ctx.registry
    system = state.systems[inv.position]
    infos = invasion.planet_infos(state, registry)
    combat_planets = invasion.combat_planets(state, registry)
    targets = set(invasion.bombard_targets(state, registry))

    planets: list[InvasionPlanetView] = []
    for info in infos:
        forces: dict[str, list[InvasionUnitView]] = {}
        structures: dict[str, list[InvasionUnitView]] = {}
        for pid, by_type in system.planet_units.get(info.planet, {}).items():
            ground = _units_view(state, ctx, system, info.planet, pid, by_type, ground=True)
            built = _units_view(state, ctx, system, info.planet, pid, by_type, ground=False)
            if ground:
                forces[key(pid)] = ground
            if built:
                structures[key(pid)] = built
        planets.append(
            InvasionPlanetView(
                planet=info.planet,
                owner=key(info.owner) if info.owner else None,
                shielded=info.shielded,
                has_shield=info.has_shield,
                has_space_cannon=info.has_space_cannon,
                forces=forces,
                structures=structures,
                committed=dict(inv.committed.get(info.planet, {})),
                contested=info.planet in combat_planets,
                bombardable=info.planet in targets,
            )
        )

    groups = invasion.bombard_groups(state, registry)
    bombard = BombardView(
        plasma_dice=invasion.plasma_bombard_dice(state),
        groups=[
            BombardGroupView(
                base_type=g.base_type,
                async_id=ASYNC_ID_BY_BASE_TYPE.get(g.base_type, g.base_type),
                name=g.name,
                count=g.count,
                hits_on=g.hits_on,
                dice_per_unit=g.dice_per_unit,
                expected_hits=g.expected_hits,
            )
            for g in groups
        ],
        targets=sorted(targets),
        done=inv.bombarded,
        pending=[
            BombardPendingView(
                planet=planet,
                defender=key(invasion.bombard_defender(inv, planet)),
                hits=hits,
                required=invasion.required_bombard_hits(state, grid, registry, planet),
                cancels=battle.sustain_cancels(state, invasion.bombard_defender(inv, planet)),
            )
            for planet, hits in sorted(inv.bombard_pending.items())
        ],
    )

    defense: list[DefensePlanetView] = []
    for planet in invasion.defense_planets(state, registry):
        if planet in inv.defense_pending:
            status = "pending"
        elif planet in inv.defense_resolved:
            status = "resolved"
        else:
            status = "open"
        defense.append(
            DefensePlanetView(
                planet=planet,
                shooters=[
                    DefenseShooterView(
                        base_type=s.base_type,
                        async_id=ASYNC_ID_BY_BASE_TYPE.get(s.base_type, s.base_type),
                        name=s.name,
                        owner=key(s.player_id),
                        count=s.count,
                        hits_on=s.hits_on,
                        dice_per_unit=s.dice_per_unit,
                        key=s.key,
                        plasma_dice=space_cannon.plasma_extra_dice(state, s),
                    )
                    for s in invasion.defense_shooters(state, registry, planet)
                ],
                status=status,
                hits=inv.defense_pending.get(planet, 0),
                required=invasion.required_defense_hits(state, grid, registry, planet),
                cancels=battle.sustain_cancels(state, inv.attacker),
            )
        )

    # Inwazja komponentu: angażuje tylko jednostki z efektu, nie siły z orbity (F_yin Ω 4.1).
    cargo = [] if inv.source else _units_view(
        state,
        ctx,
        system,
        "space",
        inv.attacker,
        system.space_units.get(inv.attacker, {}),
        ground=True,
    )
    # Inwazja komponentu nie ma kroku taktycznego INVASION (panel pomocy), więc zawsze idzie
    # pełnym oknem - inaczej nikt nie przejdzie do Establish Control.
    simple = (
        not inv.source
        and not groups
        and not inv.log
        and not inv.combat_results
        and not any(i.defenders for i in infos)
        and not invasion.defense_planets(state, registry)
    )
    return InvasionResponse(
        custodians=_custodians_view(ctx, state),
        active=True,
        simple=simple,
        source=inv.source,
        phase=inv.phase.value,
        position=inv.position,
        attacker=key(inv.attacker),
        cargo=cargo,
        planets=planets,
        bombard=bombard,
        defense=defense,
        combat_planets=combat_planets,
        in_combat=state.active_combat is not None,
        results=[
            {
                **r,
                "previousOwner": key(r["previousOwner"]) if r.get("previousOwner") else None,
                "destroyedStructures": {
                    key(pid): v for pid, v in dict(r.get("destroyedStructures", {})).items()
                },
            }
            for r in inv.results
        ],
        log=[_log_entry(e, key) for e in inv.log],
        combat_results={
            planet: {
                **res,
                "winner": key(res["winner"]) if res.get("winner") else None,
                "defender": key(res["defender"]),
                "attacker": key(res["attacker"]),
            }
            for planet, res in inv.combat_results.items()
        },
    )


@router.get("/tactical/invasion", response_model=InvasionResponse, response_model_by_alias=True)
async def get_invasion(ctx: AppContext = Depends(get_ctx)) -> InvasionResponse:
    """Stan okna inwazji (podkrok, planety, bombardowanie, obrona, wyniki)."""
    return _build(ctx, ctx.service.current_state())


@router.post("/tactical/invasion/begin", response_model=StateEnvelope)
async def post_invasion_begin(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Rozpoczyna inwazję (przycisk w panelu pomocy); 422, gdy nie ma co robić."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.invasion_attacker, "Begin invasion"
    )
    try:
        new_state = invasion.begin_invasion(
            ctx.service.current_state(), ctx.current_grid, ctx.registry
        )
        if new_state.invasion is None:
            raise ValueError("Nothing to bombard or land - no ground forces in orbit.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "invasion:begin")


@router.post("/tactical/invasion/bombard", response_model=StateEnvelope)
async def post_bombard(
    actor: ActorId,
    request: InvasionBombardRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Bombardowanie: każda jednostka z Bombardment dostaje planetę (wszystkie albo żadna)."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.invasion_attacker, "Bombardment"
    )
    try:
        new_state = invasion.bombard(
            ctx.service.current_state(),
            ctx.current_grid,
            ctx.registry,
            [
                invasion.BombardAssignment(a.base_type, a.planet, a.count)
                for a in request.assignments
            ],
            request.plasma_unit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "invasion:bombard")


@router.post("/tactical/invasion/bombard/assign", response_model=StateEnvelope)
async def post_bombard_assign(
    actor: ActorId,
    request: InvasionAssignRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Obrońca planety pokrywa trafienia bombardowania."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Assign bombardment hits"
    )
    state = ctx.service.current_state()
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = invasion.assign_bombard_hits(
            state,
            ctx.current_grid,
            ctx.registry,
            request.planet,
            player_id,
            sustain=_items(request.sustain),
            destroy=_items(request.destroy),
            destroy_damaged=_items(request.destroy_damaged),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"invasion:bombard-assign:{request.planet}")


@router.post("/tactical/invasion/commit", response_model=StateEnvelope)
async def post_commit(
    actor: ActorId,
    request: InvasionCommitRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Commit Ground Forces: ląduje siły naziemne z przestrzeni na planety."""
    actor_rules.check(
        ctx.service.current_state(),
        actor,
        None,
        actor_rules.invasion_attacker,
        "Commit ground forces",
    )
    commits: dict[str, dict[str, int]] = {}
    for item in request.commits:
        if item.count > 0:
            by_type = commits.setdefault(item.planet, {})
            by_type[item.base_type] = by_type.get(item.base_type, 0) + item.count
    try:
        new_state = invasion.commit_ground_forces(
            ctx.service.current_state(), ctx.registry, commits
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "invasion:commit")


@router.post("/tactical/invasion/custodians", response_model=StateEnvelope)
async def post_custodians(
    actor: ActorId,
    request: InvasionCustodiansRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Zdejmuje żeton Custodians z Mecatol Rex za 6 wpływu (+1 VP, faza agendy)."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.invasion_attacker, "Remove Custodians"
    )
    try:
        new_state = invasion.claim_custodians(
            ctx.service.current_state(), ctx.registry, request.planets, request.trade_goods
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "invasion:custodians")


@router.post("/tactical/invasion/defense/fire", response_model=StateEnvelope)
async def post_defense_fire(
    actor: ActorId,
    request: InvasionPlanetRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Space Cannon Defense: strzelcy na planecie rzucają w zlądowane siły."""
    actor_rules.check(
        ctx.service.current_state(),
        actor,
        None,
        actor_rules.invasion_parties,
        "Space Cannon Defense",
    )
    try:
        new_state = invasion.defense_fire(
            ctx.service.current_state(),
            ctx.current_grid,
            ctx.registry,
            request.planet,
            request.plasma_unit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"invasion:defense-fire:{request.planet}")


@router.post("/tactical/invasion/defense/pass", response_model=StateEnvelope)
async def post_defense_pass(
    actor: ActorId,
    request: InvasionPlanetRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Rezygnacja ze Space Cannon Defense na planecie."""
    actor_rules.check(
        ctx.service.current_state(),
        actor,
        None,
        actor_rules.invasion_parties,
        "Space Cannon Defense",
    )
    try:
        new_state = invasion.defense_pass(
            ctx.service.current_state(), ctx.registry, request.planet
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"invasion:defense-pass:{request.planet}")


@router.post("/tactical/invasion/defense/assign", response_model=StateEnvelope)
async def post_defense_assign(
    actor: ActorId,
    request: InvasionAssignRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Atakujący pokrywa trafienia Space Cannon Defense na zlądowanych siłach."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Assign defense hits"
    )
    try:
        new_state = invasion.assign_defense_hits(
            ctx.service.current_state(),
            ctx.current_grid,
            ctx.registry,
            request.planet,
            sustain=_items(request.sustain),
            destroy=_items(request.destroy),
            destroy_damaged=_items(request.destroy_damaged),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"invasion:defense-assign:{request.planet}")


@router.post("/tactical/invasion/next", response_model=StateEnvelope)
async def post_invasion_next(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Przechodzi do następnego podkroku inwazji (z Establish Control — zamyka inwazję)."""
    actor_rules.check(
        ctx.service.current_state(),
        actor,
        None,
        actor_rules.invasion_attacker,
        "Next invasion step",
    )
    try:
        new_state = invasion.advance(
            ctx.service.current_state(), ctx.current_grid, ctx.registry
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "invasion:next")
