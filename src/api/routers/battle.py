"""Router walki — okno pola bitwy (RULES.md 39): stan, start, AFB, rzuty, straty, zamknięcie.

Cienka warstwa nad ``core.battle``: odczyt stanu → core → commit → broadcast → mapowanie
``ValueError`` na HTTP 422. Okno pola bitwy w UI czyta ``GET /tactical/battle``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src import config
from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.routers.audio import audio_files as _audio_files
from src.api.schemas import (
    BattleAbilityToolView,
    BattleAnnounceRetreatRequest,
    BattleAssignRequest,
    BattleEffectView,
    BattleExtraDiceRequest,
    BattleHitTargetView,
    BattleLogView,
    BattleLossItem,
    BattleRelicAdjustRequest,
    BattleRelicRerollRequest,
    BattleRelicToolView,
    BattleResponse,
    BattleRetreatRequest,
    BattleRollView,
    BattleSideView,
    BattleStartRequest,
    BattleUnitView,
    ExtraDieView,
    RetreatOptionView,
    StateEnvelope,
)
from src.api.web_data import entity_key_map
from src.core import actor as actor_rules
from src.core import battle, battle_rerolls, board_edit, faction_components, ion_storm
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
    cancels = battle.sustain_cancels(state, player_id)
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
                sustain=u.sustain or u.granted > 0,
                sustainable=u.sustainable,
                afb_hits_on=u.afb_hits_on,
                afb_dice=u.afb_dice,
            )
            for u in units
        ],
        unit_count=sum(u.count for u in units),
        total_dice=sum(u.total_dice for u in units),
        expected_hits=round(sum(u.expected_hits for u in units), 2),
        hp=battle.absorbable_hits(units, cancels),
        sustain_cancels=cancels,
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
                    ion_storm_choice=ion_storm.choice_needed(
                        state, grid, ctx.registry, combat.position, pos
                    )
                    is not None,
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
            label=str(e.get("label", "")),
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
    afb_extra: dict[str, list[ExtraDieView]] = {}
    if combat.step is CombatStep.AFB:
        for pid in (combat.attacker, combat.defender):
            sources = battle.afb_extra_sources(state, pid)
            if sources:
                chosen = combat.afb_picks.get(pid, {})
                afb_extra[key(pid)] = [
                    ExtraDieView(key=e.key, name=e.name, dice=e.dice,
                                       pick=chosen.get(e.key, "auto"))
                    for e in sources
                ]
    return BattleResponse(
        afb_extra=afb_extra,
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
        sustain_hold=combat.sustain_hold,
        hit_targets={
            key(pid): BattleHitTargetView(
                types=[str(t) for t in target.get("types", [])],
                count=int(target.get("count", 0)),
                label=str(target.get("label", "")),
                damaged=target.get("damaged"),
                chooser=key(str(target["chooser"])) if target.get("chooser") else "",
            )
            for pid, target in combat.hit_targets.items()
            if combat.pending_hits.get(pid, 0) > 0
        },
        rolls=by_key(combat.rolls),
        afb=by_key(combat.afb),
        log=log,
        effects=[
            BattleEffectView(
                kind=str(e.get("kind", "")),
                player=key(str(e.get("player", ""))),
                victim=key(str(e.get("victim", ""))),
                unit=str(e.get("unit", "")),
            )
            for e in combat.effects
        ],
        winner=key(combat.winner) if combat.winner is not None else None,
        outcome=combat.outcome,
        announcing=announcing,
        retreating=[key(pid) for pid in combat.retreating],
        retreated={key(pid): pos for pid, pos in combat.retreated.items()},
        retreat_options=retreat_options,
        relic_tools=[
            BattleRelicToolView(faction=key(t["player"]), tool=t["tool"])
            for t in battle_rerolls.dice_relic_tools(state)
        ],
        ability_tools=[
            BattleAbilityToolView(
                faction=key(t["player"]), player_id=t["player"], kind=t["kind"],
                component_id=t["component"], name=t["name"], text=t["text"],
                min=t["min"], max=t["max"],
            )
            for t in faction_components.combat_dice_uses(state, ctx.registry)
        ],
    )


def _items(items: list[BattleLossItem]) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        if item.count > 0:
            result[item.base_type] = result.get(item.base_type, 0) + item.count
    return result


@router.get("/battle/sounds")
def get_battle_sounds() -> dict[str, list[str]]:
    """Próbki dźwięku walki: ``assets/extra/sfx/*`` (stary układ) i ``assets/extra/sfx/battle/*``.

    ``files`` = ścieżki względem ``assets/extra/sfx/`` (serwowane pod ``/static/extra/sfx/``);
    nazwa ``laser-2.ogg`` to 2. WARIANT zdarzenia ``laser`` (front losuje wariant). ``sounds`` =
    nazwy zdarzeń, które mają co najmniej jedną próbkę. Front pyta o listę RAZ, zamiast próbować
    każdy plik (każdy brak = czerwony 404 w konsoli); zdarzenia spoza listy grają syntezą.
    """
    folder = config.ASSETS_DIR / "extra" / "sfx"
    files = _audio_files(folder)
    files += [f"battle/{name}" for name in _audio_files(folder / "battle")]
    sounds = sorted({re.sub(r"-\d+$", "", Path(name).stem) for name in files})
    return {"sounds": sounds, "files": files}


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


@router.post("/tactical/battle/afb/extra-dice", response_model=StateEnvelope)
async def post_battle_afb_extra_dice(
    actor: ActorId, request: BattleExtraDiceRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Przypisanie dodatkowych kości AFB do jednostek przed rzutem (RULES.md 62.11)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.player_id, actor_rules.combat_sides,
        "Assign extra dice",
    )
    player_id = request.player_id
    try:
        new_state = battle.set_afb_picks(
            ctx.service.current_state(), ctx.current_grid, ctx.registry, player_id,
            dict(request.picks),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, "battle:afb-extra-dice")


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


@router.post("/tactical/battle/relic-reroll", response_model=StateEnvelope)
async def post_battle_relic_reroll(
    actor: ActorId,
    request: BattleRelicRerollRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Przerzut kości z +1 do wyniku (Crown of Thalnos) - po rzucie, przed przypisaniem strat."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Relic reroll"
    )
    state = ctx.service.current_state()
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = battle_rerolls.reroll_with_relic(
            state, ctx.current_grid, ctx.registry, player_id,
            {pick.entry: pick.dice for pick in request.picks},
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"battle:relic-reroll:{player_id}")


@router.post("/tactical/battle/relic-adjust", response_model=StateEnvelope)
async def post_battle_relic_adjust(
    actor: ActorId,
    request: BattleRelicAdjustRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Zmiana wyniku jednej kości o ±1 (Heart of Ixth) w rzucie dowolnej strony."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Relic die change"
    )
    state = ctx.service.current_state()
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        target_id = board_edit.resolve_player_id(request.target, state)
        new_state = battle_rerolls.adjust_die_with_relic(
            state, ctx.current_grid, ctx.registry, player_id,
            target=target_id, entry_index=request.entry, die_index=request.die,
            delta=request.delta,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"battle:relic-adjust:{player_id}")


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
            ion_storm_token=request.ion_storm_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"battle:retreat:{player_id}:{request.destination}")
