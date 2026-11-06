"""Router Space Cannon Offense (RULES.md 38): panel, strzał, pas, przypisanie strat.

Cienka warstwa nad ``core.space_cannon``: odczyt stanu → core → commit → broadcast →
mapowanie błędów domenowych (``ValueError``) na HTTP 422. Okno otwiera wejście w krok
SPACE_CANNON (``POST /tactical/step/next``) — tu tylko obsługa samego okna.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    SpaceCannonAssignRequest,
    SpaceCannonFireRequest,
    SpaceCannonLogEntry,
    SpaceCannonPanelResponse,
    SpaceCannonPassRequest,
    SpaceCannonPendingHelp,
    SpaceCannonRollHelp,
    SpaceCannonShipHelp,
    SpaceCannonShooterHelp,
    SpaceCannonSideHelp,
    StateEnvelope,
)
from src.api.web_data import entity_key_map
from src.core import board_edit, space_cannon
from src.core.combat import resolve_unit_variant
from src.core.game_state import GameState
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

router = APIRouter()


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    """Commit wyniku funkcji Space Cannon + rozesłanie stanu i mapy."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


def _roll_help(raw: dict[str, Any]) -> SpaceCannonRollHelp:
    base_type = str(raw.get("baseType", ""))
    return SpaceCannonRollHelp(
        base_type=base_type,
        async_id=ASYNC_ID_BY_BASE_TYPE.get(base_type, base_type),
        name=str(raw.get("name", base_type)),
        hits_on=int(raw.get("hitsOn", 0)),
        position=str(raw.get("position", "")),
        zone=str(raw.get("zone", "space")),
        dice=[int(d) for d in raw.get("dice", [])],
        hits=int(raw.get("hits", 0)),
    )


def _ship_names(
    ctx: AppContext, state: GameState, player_id: str, ships: dict[str, int]
) -> list[SpaceCannonShipHelp]:
    """Statki gracza z nazwą WARIANTU (np. „Carrier II") — do listy przypisania strat."""
    player = state.players.get(player_id)
    result: list[SpaceCannonShipHelp] = []
    for base_type, count in ships.items():
        unit = resolve_unit_variant(
            ctx.registry,
            player.faction if player is not None else None,
            player.technologies if player is not None else [],
            base_type,
        )
        result.append(
            SpaceCannonShipHelp(
                base_type=base_type,
                async_id=ASYNC_ID_BY_BASE_TYPE.get(base_type, base_type),
                name=unit.name if unit is not None else base_type,
                count=count,
            )
        )
    return result


def _build_panel(ctx: AppContext, state: GameState) -> SpaceCannonPanelResponse:
    keys = entity_key_map(state)

    def key(player_id: str) -> str:
        return keys.get(player_id, player_id)

    is_open = space_cannon.is_open(state)
    window = state.pending_window if is_open else None
    # Kolejka tylko z TRWAJĄCEGO okna — po zamknięciu panel pokazuje wynik z dziennika.
    queue = list(window.queue) if window is not None else []

    sides: list[SpaceCannonSideHelp] = []
    for player_id in queue:
        shooters = space_cannon.offense_shooters(
            state, ctx.current_grid, ctx.registry, player_id
        )
        sides.append(
            SpaceCannonSideHelp(
                faction=key(player_id),
                player_id=player_id,
                shooters=[
                    SpaceCannonShooterHelp(
                        base_type=s.base_type,
                        async_id=ASYNC_ID_BY_BASE_TYPE.get(s.base_type, s.base_type),
                        name=s.name,
                        count=s.count,
                        hits_on=s.hits_on,
                        dice_per_unit=s.dice_per_unit,
                        total_dice=s.total_dice,
                        expected_hits=s.expected_hits,
                        position=s.position,
                        zone=s.zone,
                        deep=s.deep,
                        remote=s.remote,
                    )
                    for s in shooters
                ],
                total_dice=sum(s.total_dice for s in shooters),
                expected_hits=round(sum(s.expected_hits for s in shooters), 2),
                targets=[
                    key(t) for t in space_cannon.offense_targets(state, player_id)
                ],
            )
        )

    pending_core = space_cannon.pending_hits(state)
    pending: SpaceCannonPendingHelp | None = None
    ships: list[SpaceCannonShipHelp] = []
    if pending_core is not None:
        target_ships = space_cannon.target_ships(state, pending_core.target)
        pending = SpaceCannonPendingHelp(
            roller=key(pending_core.roller),
            target=key(pending_core.target),
            hits=pending_core.hits,
            required=min(pending_core.hits, sum(target_ships.values())),
            rolls=[_roll_help(r) for r in pending_core.rolls],
        )
        ships = _ship_names(ctx, state, pending_core.target, target_ships)

    log = [
        SpaceCannonLogEntry(
            roller=key(str(e["roller"])),
            target=key(str(e["target"])) if e.get("target") else "",
            hits=int(e.get("hits", 0)),
            passed=bool(e.get("passed", False)),
            rolls=[_roll_help(r) for r in e.get("rolls", [])],
            destroyed={str(k): int(v) for k, v in dict(e.get("destroyed", {})).items()},
        )
        for e in space_cannon.read_log(state)
    ]

    return SpaceCannonPanelResponse(
        position=state.active_system,
        is_open=is_open,
        resolved=(not is_open and len(log) > 0),
        queue=[key(p) for p in queue],
        responded=[key(p) for p in window.responded] if window is not None else [],
        current=(
            key(window.current_responder)
            if window is not None and window.current_responder is not None
            else None
        ),
        sides=sides,
        pending=pending,
        target_ships=ships,
        log=log,
    )


@router.get(
    "/tactical/space-cannon",
    response_model=SpaceCannonPanelResponse,
    response_model_by_alias=True,
)
async def get_space_cannon(ctx: AppContext = Depends(get_ctx)) -> SpaceCannonPanelResponse:
    """Stan panelu Space Cannon Offense: kolejka, strzelcy, trafienia do przypisania, dziennik."""
    return _build_panel(ctx, ctx.service.current_state())


@router.post("/tactical/space-cannon/fire", response_model=StateEnvelope)
async def post_space_cannon_fire(
    request: SpaceCannonFireRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Bieżący gracz strzela Space Cannon (rzut kośćmi po stronie silnika)."""
    state = ctx.service.current_state()
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        target_id = (
            board_edit.resolve_player_id(request.target, state)
            if request.target is not None
            else None
        )
        new_state = space_cannon.fire_offense(
            state, ctx.current_grid, ctx.registry, player_id, target_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"space-cannon:fire:{player_id}")


@router.post("/tactical/space-cannon/pass", response_model=StateEnvelope)
async def post_space_cannon_pass(
    request: SpaceCannonPassRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Bieżący gracz rezygnuje ze strzału."""
    state = ctx.service.current_state()
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = space_cannon.pass_offense(state, player_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"space-cannon:pass:{player_id}")


@router.post("/tactical/space-cannon/assign", response_model=StateEnvelope)
async def post_space_cannon_assign(
    request: SpaceCannonAssignRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz-cel niszczy własne statki za trafienia Space Cannon."""
    state = ctx.service.current_state()
    losses: dict[str, int] = {}
    for item in request.losses:
        losses[item.base_type] = losses.get(item.base_type, 0) + item.count
    try:
        target_id = board_edit.resolve_player_id(request.faction, state)
        new_state = space_cannon.assign_hits(state, target_id, losses)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"space-cannon:assign:{target_id}")
