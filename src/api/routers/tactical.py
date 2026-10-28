"""Router akcji taktycznej (Etap E3): aktywacja systemu + maszyna kroków.

Cienka warstwa HTTP: woła czyste funkcje z ``core.tactical`` (przepływ kroków) oraz
``core.board_edit`` (God-Mode żetony dowodzenia), commituje i rozsyła stan + mapę.
Aplikacja PROWADZI kroki akcji taktycznej, ale NIE waliduje reguł TI4 — gracze grają
fizycznie i wprowadzają wynik (decyzja projektowa; patrz docs/RULES.md 19).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    ActivateSystemRequest,
    CapturePlanetRequest,
    CombatHelpResponse,
    CombatSideHelp,
    CombatUnitHelp,
    CommandTokenRequest,
    MapView,
    ProducibleUnitHelp,
    ProductionHelpResponse,
    StateEnvelope,
    TacticalStepRequest,
)
from src.api.serializers import build_map_view
from src.api.web_data import entity_key_map
from src.core import board_edit, combat, tactical
from src.core.combat import PlayerCombat
from src.core.game_state import GameState, TacticalStep
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

router = APIRouter()


async def _commit_flow(
    ctx: AppContext, new_state: GameState, label: str
) -> StateEnvelope:
    """Commit wyniku funkcji taktycznej + rozesłanie stanu i mapy."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


async def _commit_map(ctx: AppContext, new_state: GameState, label: str) -> MapView:
    """Commit + rozesłanie, zwraca świeży widok mapy (dla edycji God-Mode CC)."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return build_map_view(ctx.current_grid, ctx.registry, ctx.service.current_state())


@router.post("/tactical/activate", response_model=StateEnvelope)
async def post_activate_system(
    request: ActivateSystemRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Aktywuje system przez aktywnego gracza (kładzie CC, ustawia aktywny system)."""
    try:
        new_state = tactical.activate_system(
            ctx.service.current_state(), ctx.current_grid, request.position
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, f"tactical:activate:{request.position}")


@router.post("/tactical/step/next", response_model=StateEnvelope)
async def post_next_step(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Przechodzi do następnego kroku akcji taktycznej (po produkcji — kończy akcję)."""
    return await _commit_flow(
        ctx, tactical.next_step(ctx.service.current_state()), "tactical:step"
    )


@router.post("/tactical/step/set", response_model=StateEnvelope)
async def post_set_step(
    request: TacticalStepRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Skok do wskazanego kroku akcji taktycznej (np. pominięcie walki)."""
    try:
        step = TacticalStep(request.step)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Nieznany krok: {request.step}") from exc
    return await _commit_flow(
        ctx, tactical.set_step(ctx.service.current_state(), step), "tactical:set-step"
    )


@router.post("/tactical/end", response_model=StateEnvelope)
async def post_end_tactical(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Kończy bieżącą akcję taktyczną (czyści aktywny system i krok)."""
    return await _commit_flow(
        ctx, tactical.end_tactical_action(ctx.service.current_state()), "tactical:end"
    )


@router.post("/system/{position}/command-token", response_model=MapView)
async def post_place_command_token(
    position: str, request: CommandTokenRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """God-Mode: kładzie żeton dowodzenia gracza w przestrzeni systemu."""
    new_state = board_edit.place_command_token(
        ctx.service.current_state(), ctx.current_grid, position, request.faction
    )
    return await _commit_map(ctx, new_state, f"cc:add:{position}")


@router.delete("/system/{position}/command-token", response_model=MapView)
async def delete_command_token(
    position: str, request: CommandTokenRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """God-Mode: zdejmuje żeton dowodzenia gracza z przestrzeni systemu."""
    new_state = board_edit.remove_command_token(
        ctx.service.current_state(), ctx.current_grid, position, request.faction
    )
    return await _commit_map(ctx, new_state, f"cc:remove:{position}")


def _to_side(side: PlayerCombat, keys: dict[str, str]) -> CombatSideHelp:
    """Mapuje ``PlayerCombat`` z core na DTO strony walki (klucz tożsamości + asyncId)."""
    return CombatSideHelp(
        faction=keys.get(side.player_id, side.player_id),
        player_id=side.player_id,
        units=[
            CombatUnitHelp(
                base_type=u.base_type,
                async_id=ASYNC_ID_BY_BASE_TYPE.get(u.base_type, u.base_type),
                unit_id=u.unit_id,
                name=u.name,
                count=u.count,
                combat_hits_on=u.combat_hits_on,
                combat_die_count=u.combat_die_count,
                expected_hits=u.expected_hits,
            )
            for u in side.units
        ],
        total_dice=side.total_dice,
        expected_hits=side.expected_hits,
    )


@router.get(
    "/tactical/combat/{position}",
    response_model=CombatHelpResponse,
    response_model_by_alias=True,
)
async def get_combat_help(
    position: str,
    planet: str | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> CombatHelpResponse:
    """Asystent walki: uczestnicy + pomoce liczbowe (ile kości, trafia na X+, expected).

    ``planet`` ustawione → walka NAZIEMNA na planecie; brak → walka KOSMICZNA w
    przestrzeni. Aplikacja NIE rozstrzyga walki (zero rzutów) — to tylko podpowiedź.
    Gdy walczących <2, ``sides`` jest puste (brak walki).
    """
    state = ctx.service.current_state()
    keys = entity_key_map(state)
    if planet is not None:
        sides = combat.ground_combat_participants(
            ctx.registry, state, position, planet
        )
        kind = "ground"
    else:
        sides = combat.space_combat_participants(ctx.registry, state, position)
        kind = "space"
    return CombatHelpResponse(
        position=position,
        planet=planet,
        kind=kind,
        sides=[_to_side(s, keys) for s in sides],
    )


@router.post("/tactical/system/{position}/capture", response_model=MapView)
async def post_capture_planet(
    position: str, request: CapturePlanetRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """Przejęcie kontroli planety po inwazji (nadpisuje poprzedniego właściciela)."""
    new_state = tactical.capture_planet(
        ctx.service.current_state(),
        ctx.current_grid,
        position,
        request.planet,
        request.faction,
    )
    return await _commit_map(ctx, new_state, f"capture:{position}:{request.planet}")


@router.get(
    "/tactical/production",
    response_model=ProductionHelpResponse,
    response_model_by_alias=True,
)
async def get_production_help(
    faction: str, ctx: AppContext = Depends(get_ctx)
) -> ProductionHelpResponse:
    """Pomoc liczbowa produkcji: dostępne zasoby gracza + koszt jego jednostek.

    ``faction`` to klucz z tileUnitData (frakcja lub player_id). Zero walidacji limitów —
    tylko podpowiedź (gracz stawia jednostki God-Mode).
    """
    state = ctx.service.current_state()
    player_id = board_edit.resolve_player_id(faction, state)
    help_ = tactical.production_help(state, ctx.registry, player_id)
    return ProductionHelpResponse(
        player_id=help_.player_id,
        available_resources=help_.available_resources,
        units=[
            ProducibleUnitHelp(
                base_type=u.base_type,
                async_id=u.async_id,
                unit_id=u.unit_id,
                name=u.name,
                cost=u.cost,
                units_per_cost=u.units_per_cost,
                placement=u.placement,
            )
            for u in help_.units
        ],
    )
