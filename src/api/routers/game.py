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
from src.core import strategy_phase
from src.core.faction_setup import (
    OFF_BOARD_HOME,
    apply_setup_to_state,
    off_board_corner,
)
from src.core.game_state import GameState, Phase
from src.core.hex_grid import Hex, HexGrid
from src.core.map_string import build_grid_from_map_string
from src.core.models import FactionDef
from src.core.registry import StaticDataRegistry

# Synenetyczne heksy dla rogów off-board (poza planszą) — daleko od pierścieni,
# by nie kolidowały geometrycznie z kafelkami planszy. Sąsiedztwo do bramy idzie
# przez wormhole (Delta/Epsilon), nie przez geometrię. Patrz RULES.md 17.
_OFF_BOARD_HEX: dict[str, Hex] = {
    "tr": Hex(40, -20, -20),
    "br": Hex(40, 0, -40),
    "bl": Hex(-40, 40, 0),
    "tl": Hex(-40, 20, 20),
}

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
            starting_tech_options=list(f.starting_tech_options),
            starting_tech_amount=f.starting_tech_amount,
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


def _place_tile_on_slot(
    grid: HexGrid, system_id: str, position: str, registry: StaticDataRegistry
) -> None:
    """Kładzie kafelek ``system_id`` na pozycji slotu (zachowuje współrzędne slotu)."""
    sys_def = registry.systems.get(system_id)
    grid.place_system(
        position=position,
        system_id=system_id,
        wormholes=list(sys_def.wormholes) if sys_def else None,
        anomalies=set(sys_def.anomalies) if sys_def else None,
        hex_override=Hex(*grid.coordinates(position)),
    )


def _place_off_board_home(
    grid: HexGrid, system_id: str, corner: str, registry: StaticDataRegistry
) -> None:
    """Kładzie prawdziwy dom off-board (róg ``tr``/``br``/``bl``) z syntetycznym heksem."""
    sys_def = registry.systems.get(system_id)
    grid.place_system(
        position=corner,
        system_id=system_id,
        wormholes=list(sys_def.wormholes) if sys_def else None,
        anomalies=set(sys_def.anomalies) if sys_def else None,
        hex_override=_OFF_BOARD_HEX.get(corner, Hex(40, -20, -20)),
    )


def _setup_home_tiles(
    grid: HexGrid,
    faction: FactionDef,
    home_position: str,
    registry: StaticDataRegistry,
    taken_corners: set[str],
) -> tuple[str, str]:
    """Kładzie kafelek(i) domowe frakcji w gridzie i zwraca (unit_position, unit_system_id).

    Frakcja normalna: prawdziwy kafelek domowy na slocie → jednostki tam.
    Ghost/Crimson (RULES.md 17): brama na slocie + prawdziwy dom off-board →
    jednostki na off-board.
    """
    if not faction.home_system or home_position not in grid.positions:
        return home_position, faction.home_system or ""

    real_home = OFF_BOARD_HOME.get(faction.id)
    if real_home is None:
        # Zwykła frakcja: prawdziwy kafelek domowy na slocie.
        _place_tile_on_slot(grid, faction.home_system, home_position, registry)
        return home_position, faction.home_system

    # Off-board: brama na slocie, dom w rogu.
    _place_tile_on_slot(grid, faction.home_system, home_position, registry)
    corner = off_board_corner(home_position, taken_corners)
    taken_corners.add(corner)
    _place_off_board_home(grid, real_home, corner, registry)
    return corner, real_home


@router.post("/setup/player", response_model=MapView)
async def post_setup_player(
    request: SetupPlayerRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    faction = ctx.registry.factions.get(request.faction_id)
    if faction is None:
        raise HTTPException(
            status_code=404, detail=f"Nieznana frakcja: {request.faction_id}"
        )
    grid = ctx.current_grid
    # Najpierw połóż kafelki domowe (ustala, gdzie trafią jednostki — off-board dla
    # Ghost/Crimson), zbierając zajęte rogi z już rozstawionych graczy.
    taken_corners = {p for p in grid.positions if p in {"tr", "br", "bl", "tl"}}
    unit_position, unit_system_id = _setup_home_tiles(
        grid, faction, request.home_position, ctx.registry, taken_corners
    )
    grid.build_edges()
    try:
        new_state = apply_setup_to_state(
            ctx.service.current_state(),
            player_id=request.player_id,
            color=request.color,
            faction=faction,
            home_position=request.home_position,
            chosen_tech=request.starting_tech,
            unit_position=unit_position,
            unit_system_id=unit_system_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Utrzymaj kolejność miejsc (RULES.md 24): dopisz nowego gracza na koniec
    # stołu. Pierwszy gracz zostaje mówcą. W fazie strategii zaktualizuj, kto
    # wybiera (mówca, gdy jeszcze nikt nie wybierał).
    if request.player_id not in new_state.seating_order:
        new_state.seating_order = [*new_state.seating_order, request.player_id]
    if new_state.speaker_id is None:
        new_state.speaker_id = new_state.seating_order[0]
    if new_state.phase is Phase.STRATEGY:
        new_state.active_player_id = strategy_phase.next_strategy_picker(new_state)
    ctx.service.replace_state(new_state, label=f"setup:{request.faction_id}")

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
    seating: list[str] = []  # kolejność graczy przy stole (RULES.md 24)
    taken_corners: set[str] = set()  # rogi off-board zajęte przez Ghost/Crimson
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
        seating.append(player_id)
        # Połóż kafelki domowe (off-board dla Ghost/Crimson) i ustal gdzie flota.
        unit_position, unit_system_id = _setup_home_tiles(
            grid, faction, home_position, ctx.registry, taken_corners
        )
        try:
            new_state = apply_setup_to_state(
                new_state,
                player_id=player_id,
                color=color,
                faction=faction,
                home_position=home_position,
                chosen_tech=player.starting_tech,
                unit_position=unit_position,
                unit_system_id=unit_system_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    grid.build_edges()

    # Kolejność miejsc + mówca (RULES.md 24): pierwszy gracz = mówca na start.
    # Nowa gra zaczyna fazą strategii, więc aktywny = pierwszy wybierający (mówca).
    new_state.seating_order = seating
    new_state.speaker_id = seating[0] if seating else None
    new_state.active_player_id = strategy_phase.next_strategy_picker(new_state)
    ctx.current_grid = grid
    ctx.service.replace_state(new_state, label="game:new")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return build_map_view(grid, ctx.registry, ctx.service.current_state())
