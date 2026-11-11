"""Router walki — okno pola bitwy (RULES.md 39): stan, start, AFB, rzuty, straty, zamknięcie.

Cienka warstwa nad ``core.battle``: odczyt stanu → core → commit → broadcast → mapowanie
``ValueError`` na HTTP 422. Okno pola bitwy w UI czyta ``GET /tactical/battle``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    BattleAnnounceRetreatRequest,
    BattleAssignRequest,
    BattleLogView,
    BattleLossItem,
    BattleResponse,
    BattleRetreatRequest,
    BattleRollView,
    BattleSideView,
    BattleStartRequest,
    BattleUnitView,
    RetreatOptionView,
    StateEnvelope,
)
from src.api.web_data import entity_key_map
from src.core import actor as actor_rules
from src.core import battle, board_edit
from src.core.game_state import CombatStep, GameState, WindowType
from src.core.movement import CargoPickup
from src.core.retreat import retreat_destinations
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

router = APIRouter()

_NEBULA = "NEBULA"


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    """Commit wyniku funkcji walki + rozesłanie stanu i mapy."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


def _roll(raw: dict[str, Any]) -> BattleRollView:
    base_type = str(raw.get("baseType", ""))
    return BattleRollView(
        base_type=base_type,
        async_id=ASYNC_ID_BY_BASE_TYPE.get(base_type, base_type),
        name=str(raw.get("name", base_type)),
        hits_on=int(raw.get("hitsOn", 0)),
        modifier=int(raw.get("modifier", 0)),
        dice=[int(d) for d in raw.get("dice", [])],
        hits=int(raw.get("hits", 0)),
    )


def _side(
    ctx: AppContext, state: GameState, player_id: str, role: str, key: str
) -> BattleSideView:
    units = battle.side_units(state, ctx.current_grid, ctx.registry, player_id)
    return BattleSideView(
        faction=key,
        player_id=player_id,
        role=role,
        units=[
            BattleUnitView(
                base_type=u.base_type,
                async_id=ASYNC_ID_BY_BASE_TYPE.get(u.base_type, u.base_type),
                name=u.name,
                count=u.count,
                damaged=u.damaged,
                hits_on=u.hits_on,
                base_hits_on=u.base_hits_on,
                modifier=u.modifier,
                dice_per_unit=u.dice_per_unit,
                total_dice=u.total_dice,
                expected_hits=u.expected_hits,
                sustain=u.sustain,
                sustainable=u.sustainable,
                afb_hits_on=u.afb_hits_on,
                afb_dice=u.afb_dice,
            )
            for u in units
        ],
        unit_count=sum(u.count for u in units),
        total_dice=sum(u.total_dice for u in units),
        expected_hits=round(sum(u.expected_hits for u in units), 2),
        hp=sum(u.count + u.sustainable for u in units),
    )


def _build(ctx: AppContext, state: GameState) -> BattleResponse:
    combat = state.active_combat
    if combat is None:
        return BattleResponse(active=False)
    keys = entity_key_map(state)

    def key(player_id: str) -> str:
        return keys.get(player_id, player_id)

    def by_key(raw: dict[str, list[dict[str, Any]]]) -> dict[str, list[BattleRollView]]:
        return {key(pid): [_roll(r) for r in entries] for pid, entries in raw.items()}

    window = state.pending_window
    assigning = (
        key(window.current_responder)
        if window is not None
        and window.window_type is WindowType.COMBAT_ASSIGN_HITS
        and window.current_responder is not None
        else None
    )
    announcing = (
        key(window.current_responder)
        if window is not None
        and window.window_type is WindowType.COMBAT_RETREAT
        and window.current_responder is not None
        else None
    )
    grid = ctx.current_grid
    retreat_options = (
        {
            key(pid): [
                RetreatOptionView(
                    position=pos,
                    system_id=grid.system_id_at(pos) if pos in grid.positions else "",
                )
                for pos in retreat_destinations(state, grid, combat.position, pid)
            ]
            for pid in (combat.attacker, combat.defender)
        }
        if combat.kind == "space" and combat.step is not CombatStep.DONE
        else {}
    )
    required = {
        key(pid): battle.required_hits(state, ctx.current_grid, ctx.registry, pid)
        for pid in (combat.attacker, combat.defender)
        if combat.pending_hits.get(pid, 0) > 0
    }
    log = [
        BattleLogView(
            round=int(e.get("round", 0)),
            phase=str(e.get("phase", "")),
            rolls=by_key(dict(e.get("rolls", {}))),
            hits={key(pid): int(n) for pid, n in dict(e.get("hits", {})).items()},
            losses={key(pid): dict(v) for pid, v in dict(e.get("losses", {})).items()},
            sustained={
                key(pid): dict(v) for pid, v in dict(e.get("sustained", {})).items()
            },
            retreat=(
                {**dict(e["retreat"]), "player": key(str(e["retreat"].get("player", "")))}
                if e.get("retreat")
                else None
            ),
        )
        for e in combat.log
    ]
    return BattleResponse(
        active=True,
        kind=combat.kind,
        position=combat.position,
        planet=combat.planet,
        round=combat.round,
        step=combat.step.value,
        nebula=combat.kind == "space"
        and _NEBULA in ctx.current_grid.anomalies_at(combat.position),
        attacker=_side(ctx, state, combat.attacker, "attacker", key(combat.attacker)),
        defender=_side(ctx, state, combat.defender, "defender", key(combat.defender)),
        pending_hits={key(pid): n for pid, n in combat.pending_hits.items() if n > 0},
        required=required,
        assigning=assigning,
        rolls=by_key(combat.rolls),
        afb=by_key(combat.afb),
        log=log,
        winner=key(combat.winner) if combat.winner is not None else None,
        outcome=combat.outcome,
        announcing=announcing,
        retreating=[key(pid) for pid in combat.retreating],
        retreated={key(pid): pos for pid, pos in combat.retreated.items()},
        retreat_options=retreat_options,
    )


def _items(items: list[BattleLossItem]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        if item.count > 0:
            result[item.base_type] = result.get(item.base_type, 0) + item.count
    return result


@router.get("/tactical/battle", response_model=BattleResponse, response_model_by_alias=True)
async def get_battle(ctx: AppContext = Depends(get_ctx)) -> BattleResponse:
    """Stan okna pola bitwy (strony, jednostki, rzuty, straty do pokrycia, historia)."""
    return _build(ctx, ctx.service.current_state())


@router.post("/tactical/battle/start", response_model=StateEnvelope)
async def post_battle_start(
    actor: ActorId,
    request: BattleStartRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Rozpoczyna walkę w aktywnym systemie (kosmiczną albo naziemną na ``planet``)."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.turn_player, "Start combat"
    )
    try:
        new_state = battle.start_combat(
            ctx.service.current_state(), ctx.current_grid, ctx.registry, request.planet
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"battle:start:{request.planet or 'space'}")


@router.post("/tactical/battle/afb", response_model=StateEnvelope)
async def post_battle_afb(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Anti-Fighter Barrage obu stron (rzuty po stronie silnika)."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.combat_sides, "Anti-Fighter Barrage"
    )
    try:
        new_state = battle.resolve_afb(
            ctx.service.current_state(), ctx.current_grid, ctx.registry
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "battle:afb")


@router.post("/tactical/battle/roll", response_model=StateEnvelope)
async def post_battle_roll(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Rzuty combat obu stron w bieżącej rundzie."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.combat_sides, "Combat roll"
    )
    try:
        new_state = battle.roll_round(
            ctx.service.current_state(), ctx.current_grid, ctx.registry
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "battle:roll")


@router.post("/tactical/battle/assign", response_model=StateEnvelope)
async def post_battle_assign(
    actor: ActorId,
    request: BattleAssignRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz pokrywa trafienia (Sustain Damage + niszczone jednostki)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Assign hits"
    )
    state = ctx.service.current_state()
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = battle.assign_combat_hits(
            state,
            ctx.current_grid,
            ctx.registry,
            player_id,
            sustain=_items(request.sustain),
            destroy=_items(request.destroy),
            destroy_damaged=_items(request.destroy_damaged),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"battle:assign:{player_id}")


@router.post("/tactical/battle/close", response_model=StateEnvelope)
async def post_battle_close(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Zamyka zakończoną walkę (okno pola bitwy znika)."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.combat_sides, "Close combat"
    )
    try:
        new_state = battle.close_combat(ctx.service.current_state())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "battle:close")


@router.post("/tactical/battle/announce-retreat", response_model=StateEnvelope)
async def post_battle_announce_retreat(
    actor: ActorId,
    request: BattleAnnounceRetreatRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Ogłoszenie odwrotu albo walka dalej (okno COMBAT_RETREAT — RULES.md 39.5 O2)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Announce retreat"
    )
    state = ctx.service.current_state()
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = battle.announce_retreat(
            state, ctx.current_grid, player_id, announce=request.announce
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    verb = "announce" if request.announce else "stay"
    return await _commit(ctx, new_state, f"battle:retreat-{verb}:{player_id}")


@router.post("/tactical/battle/retreat", response_model=StateEnvelope)
async def post_battle_retreat(
    actor: ActorId,
    request: BattleRetreatRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Wykonanie ogłoszonego odwrotu do sąsiedniego systemu (RULES.md 39.5 O3–O6)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Retreat"
    )
    state = ctx.service.current_state()
    cargo = (
        [
            CargoPickup(base_type=c.base_type, count=c.count, from_zone=c.from_zone)
            for c in request.cargo
        ]
        if request.cargo is not None
        else None
    )
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = battle.retreat_from_combat(
            state,
            ctx.current_grid,
            ctx.registry,
            player_id,
            request.destination,
            cargo=cargo,
            token_pool=request.token_pool,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"battle:retreat:{player_id}:{request.destination}")
