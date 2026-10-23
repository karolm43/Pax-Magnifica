"""Router gry: stan, mapa, web-data, frakcje, nowa gra, wczytanie mapy, setup gracza."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    FactionInfo,
    MapStringRequest,
    MapView,
    NewGameRequest,
    SetupPlayerRequest,
    StateEnvelope,
)
from src.api.serializers import AUTO_SLOT_ORDER, DEFAULT_MAP_STRING, build_map_view
from src.api.web_data import build_web_data
from src.core.faction_setup import apply_setup_to_state
from src.core.game_state import GameState
from src.core.hex_grid import Hex, HexGrid
from src.core.map_string import build_grid_from_map_string

router = APIRouter()


@router.get("/state", response_model=StateEnvelope)
def get_state(ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    return ctx.service.envelope()


@router.get("/map", response_model=MapView)
def get_map(ctx: AppContext = Depends(get_ctx)) -> MapView:
    return build_map_view(ctx.current_grid, ctx.registry, ctx.service.current_state())


@router.get("/api/public/game/{game_id}/events")
def get_game_events(game_id: str) -> list[dict[str, object]]:
    """Log zdarzeń AsyncTI4 — nie produkujemy go (mamy własną historię)."""
    return []


@router.get("/api/public/game/{game_id}/web-data")
def get_web_data(
    game_id: str, ctx: AppContext = Depends(get_ctx)
) -> dict[str, object]:
    """Dokument ``PlayerDataResponse`` dla frontendu ti4_web (viewer planszy)."""
    return build_web_data(
        ctx.current_grid, ctx.registry, ctx.service.current_state(), game_name=game_id
    )


@router.get("/factions", response_model=list[FactionInfo])
def get_factions(ctx: AppContext = Depends(get_ctx)) -> list[FactionInfo]:
    return [
        FactionInfo(
            id=f.id,
            name=f.name,
            home_system=f.home_system,
            home_planets=list(f.home_planets),
            starting_fleet=f.starting_fleet,
            preferred_colours=list(f.preferred_colours),
        )
        for f in sorted(ctx.registry.factions.values(), key=lambda x: x.name)
    ]


@router.post("/map/load", response_model=MapView)
async def post_load_map(
    request: MapStringRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    try:
        grid = build_grid_from_map_string(
            request.map_string, ctx.registry, include_center=request.include_center
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not grid.positions:
        raise HTTPException(
            status_code=422,
            detail="Map string nie dał żadnego znanego systemu (sprawdź ID i źródła).",
        )
    ctx.current_grid = grid
    await ctx.broadcast_map()
    return build_map_view(grid, ctx.registry, ctx.service.current_state())


def _place_home_tile(grid: HexGrid, faction, home_position: str, registry) -> None:  # type: ignore[no-untyped-def]
    """Podmienia slot domowy w gridzie na prawdziwy kafelek domowy frakcji."""
    if faction.home_system and home_position in grid.positions:
        home_sys = registry.systems.get(faction.home_system)
        grid.place_system(
            position=home_position,
            system_id=faction.home_system,
            wormholes=list(home_sys.wormholes) if home_sys else None,
            anomalies=set(home_sys.anomalies) if home_sys else None,
            hex_override=Hex(*grid.coordinates(home_position)),
        )


@router.post("/setup/player", response_model=MapView)
async def post_setup_player(
    request: SetupPlayerRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    faction = ctx.registry.factions.get(request.faction_id)
    if faction is None:
        raise HTTPException(
            status_code=404, detail=f"Nieznana frakcja: {request.faction_id}"
        )
    new_state = apply_setup_to_state(
        ctx.service.current_state(),
        player_id=request.player_id,
        color=request.color,
        faction=faction,
        home_position=request.home_position,
    )
    ctx.service.replace_state(new_state, label=f"setup:{request.faction_id}")

    grid = ctx.current_grid
    if faction.home_system and request.home_position in grid.positions:
        _place_home_tile(grid, faction, request.home_position, ctx.registry)
        grid.build_edges()

    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return build_map_view(ctx.current_grid, ctx.registry, ctx.service.current_state())


@router.post("/game/new", response_model=MapView)
async def post_new_game(
    request: NewGameRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """Tworzy nową grę w jednym kroku: reset stanu + mapa + setup graczy."""
    if len(request.players) > len(AUTO_SLOT_ORDER):
        raise HTTPException(
            status_code=422,
            detail=f"Za dużo graczy: max {len(AUTO_SLOT_ORDER)} (układ 6-osobowy).",
        )

    map_string = request.map_string or DEFAULT_MAP_STRING
    try:
        grid = build_grid_from_map_string(
            map_string, ctx.registry, include_center=request.include_center
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not grid.positions:
        raise HTTPException(
            status_code=422,
            detail="Map string nie dał żadnego znanego systemu (sprawdź ID i źródła).",
        )

    new_state = GameState()
    first_player_id: str | None = None
    for index, player in enumerate(request.players):
        faction = ctx.registry.factions.get(player.faction_id)
        if faction is None:
            raise HTTPException(
                status_code=404, detail=f"Nieznana frakcja: {player.faction_id}"
            )
        slot_position, slot_color = AUTO_SLOT_ORDER[index]
        home_position = player.home_position or slot_position
        color = player.color or slot_color
        player_id = player.player_id or f"p{index + 1}"
        # Bug 8: pozycja domowa MUSI istnieć na mapie — inaczej flota nie renderuje się.
        if home_position not in grid.positions:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Pozycja domowa {home_position!r} gracza {player_id!r} nie "
                    f"istnieje na tej mapie. Podaj home_position pasującą do map_string."
                ),
            )
        if first_player_id is None:
            first_player_id = player_id
        new_state = apply_setup_to_state(
            new_state,
            player_id=player_id,
            color=color,
            faction=faction,
            home_position=home_position,
        )
        _place_home_tile(grid, faction, home_position, ctx.registry)
    grid.build_edges()

    new_state.active_player_id = first_player_id
    ctx.current_grid = grid
    ctx.service.replace_state(new_state, label="game:new")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return build_map_view(grid, ctx.registry, ctx.service.current_state())
