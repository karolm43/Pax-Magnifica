"""Aplikacja FastAPI Custodian Engine — REST + WebSocket.

Endpointy (Blok 3, minimalne API):
- ``GET  /state``            — bieżący stan gry + metadane historii.
- ``GET  /map``              — geometria mapy demonstracyjnej (kafelki + krawędzie).
- ``PUT  /state``            — God-Mode: nadpisanie całego ``GameState``.
- ``POST /god-mode/patch``   — God-Mode: częściowa modyfikacja stanu.
- ``POST /undo`` / ``/redo`` — nawigacja po historii (``EventStore``).
- ``GET  /static/*``         — statyczne assety danych (JSON) z katalogu assetów.
- ``WS   /ws``               — strumień stanu: po połączeniu wysyła bieżącą kopertę,
                               a każda mutacja rozsyła nową kopertę do klientów.

Backend jest źródłem prawdy; frontend tylko odzwierciedla rozesłany stan.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.websockets import WebSocket, WebSocketDisconnect

from src import config
from src.api.connection_manager import ConnectionManager
from src.api.demo_map import build_demo_grid
from src.api.schemas import (
    FactionInfo,
    GodModePatch,
    HistoryEntry,
    HistoryList,
    MapEdge,
    MapStringRequest,
    MapTile,
    MapView,
    NewGameRequest,
    PlanetUnits,
    PlanetUnitsRequest,
    PlayerEditRequest,
    SetupPlayerRequest,
    SpaceUnitsRequest,
    StateEnvelope,
    StrategyCardInfo,
    StrategyPickRequest,
    StrategyPlayRequest,
    UnitEditRequest,
    UnitMoveRequest,
    UnitStack,
)
from src.api.state_service import StateService
from src.api.web_data import build_web_data
from src.core import strategy_phase, turn_flow
from src.core.event_store import EventStore
from src.core.faction_setup import apply_setup_to_state
from src.core.game_state import GameState, PlayerState, SystemState
from src.core.hex_grid import Hex, HexGrid
from src.core.home_slots import HOME_SLOT_COLORS_6P, home_slot_color
from src.core.map_string import HOME_SLOT_SYSTEM_ID, build_grid_from_map_string
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE, BASE_TYPE_BY_ASYNC_ID

# Testowy map string (6-osobowa plansza) używany, gdy frontend nie poda własnego.
# To realny string AsyncTI4 (rogi domowe jako "0").
_DEFAULT_MAP_STRING = (
    "23 49 77 66 71 39 64 31 35 76 50 37 73 46 34 75 47 65 "
    "0 59 79 0 25 28 0 26 42 0 40 41 0 45 69 0 62 44"
)

# Kolejność automatycznego przydziału kolorów/slotów domowych wg kolejności graczy
# (gracz 1 → red/301, 2 → green/304, ...). Źródło: HOME_SLOT_COLORS_6P (home_slots.py).
_AUTO_SLOT_ORDER: list[tuple[str, str]] = [
    (position, color) for position, color in sorted(HOME_SLOT_COLORS_6P.items())
]


def _unit_image_url(color: str | None, base_type: str) -> str | None:
    """URL grafiki jednostki: ``/static/units/<kolor>_<asyncId>.png``.

    Zwraca None, gdy kolor nieznany lub ``baseType`` spoza katalogu.
    """
    if not color:
        return None
    async_id = ASYNC_ID_BY_BASE_TYPE.get(base_type)
    if async_id is None:
        return None
    return f"{config.STATIC_URL_PREFIX}/units/{color}_{async_id}.png"


def _stacks_from_units(
    units_by_player: dict[str, dict[str, int]], state: GameState
) -> list[UnitStack]:
    """Buduje listę stosów jednostek (z kolorem i grafiką) z surowych liczników."""
    stacks: list[UnitStack] = []
    for player_id, counts in sorted(units_by_player.items()):
        player = state.players.get(player_id)
        color = player.color if player else None
        for base_type, count in sorted(counts.items()):
            if count <= 0:
                continue
            stacks.append(
                UnitStack(
                    player_id=player_id,
                    base_type=base_type,
                    count=count,
                    color=color,
                    image_url=_unit_image_url(color, base_type),
                )
            )
    return stacks


def build_map_view(
    grid: HexGrid, registry: StaticDataRegistry, state: GameState
) -> MapView:
    """Serializuje ``HexGrid`` + stan gry do reprezentacji mapy dla frontendu.

    Dane kafelka (nazwa, planety, anomalie, wormhole, grafika) pochodzą z rejestru
    i grafu; jednostki (przestrzeń + planety) z ``GameState`` — bez reguł z pamięci.
    """
    tiles: list[MapTile] = []
    for position in sorted(grid.positions):
        q, r, s = grid.coordinates(position)
        system_id = grid.system_id_at(position)

        # Slot domowy gracza (kolorowy róg bez kafelka systemu).
        if system_id == HOME_SLOT_SYSTEM_ID:
            tiles.append(
                MapTile(
                    position=position,
                    system_id=system_id,
                    q=q,
                    r=r,
                    s=s,
                    is_home_slot=True,
                    home_color=home_slot_color(position),
                )
            )
            continue

        system = registry.systems.get(system_id)
        image_url: str | None = None
        if system is not None and system.image_path:
            image_url = f"{config.STATIC_URL_PREFIX}/tiles/{system.image_path}"

        # Jednostki z bieżącego stanu gry (jeśli system istnieje w stanie).
        sys_state = state.systems.get(position)
        space_stacks: list[UnitStack] = []
        planet_units: list[PlanetUnits] = []
        if sys_state is not None:
            space_stacks = _stacks_from_units(sys_state.space_units, state)
            for planet_id, by_player in sorted(sys_state.planet_units.items()):
                planet_units.append(
                    PlanetUnits(
                        planet_id=planet_id,
                        owner_id=sys_state.planet_owners.get(planet_id),
                        stacks=_stacks_from_units(by_player, state),
                    )
                )

        tiles.append(
            MapTile(
                position=position,
                system_id=system_id,
                q=q,
                r=r,
                s=s,
                wormholes=list(system.wormholes) if system else [],
                anomalies=sorted(grid.anomalies_at(position)),
                planets=list(system.planets) if system else [],
                name=system.name if system else None,
                image_url=image_url,
                space_units=space_stacks,
                planet_units=planet_units,
            )
        )
    edges = [
        MapEdge(a=a, b=b, kind=kind)  # type: ignore[arg-type]
        for a, b, kind in grid.edges()
    ]
    return MapView(tiles=tiles, edges=edges)


def create_app(
    *,
    registry: StaticDataRegistry | None = None,
    store: EventStore | None = None,
    initial_state: GameState | None = None,
) -> FastAPI:
    """Fabryka aplikacji FastAPI (wstrzykiwalna dla testów).

    Args:
        registry: Rejestr statycznych danych (domyślnie ładowany z assetów).
        store: Magazyn historii (domyślnie SQLite w pamięci).
        initial_state: Stan początkowy (domyślnie pusty ``GameState``).
    """
    reg = registry if registry is not None else StaticDataRegistry()
    event_store = store if store is not None else EventStore()
    manager = ConnectionManager()
    service = StateService(event_store, manager, initial_state=initial_state)
    demo_grid = build_demo_grid(reg)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        event_store.close()

    app = FastAPI(title="Custodian Engine API", version="0.1.0", lifespan=lifespan)

    # CORS: dev-serwer Vite (5173) łączy się z backendem (8000).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Udostępnij współdzielone obiekty przez stan aplikacji (dla testów/diagnostyki).
    # current_grid to bieżąca mapa: start = demo, po /map/load = mapa z map stringa.
    app.state.service = service
    app.state.manager = manager
    app.state.registry = reg
    app.state.demo_grid = demo_grid
    app.state.current_grid = demo_grid

    # --- REST ---------------------------------------------------------------

    @app.get("/state", response_model=StateEnvelope)
    def get_state() -> StateEnvelope:
        return service.envelope()

    async def broadcast_map() -> None:
        """Rozsyła świeży widok mapy (z jednostkami) do klientów WebSocket."""
        view = build_map_view(app.state.current_grid, reg, service.current_state())
        await manager.broadcast_json({"type": "map", **view.model_dump(mode="json")})

    @app.get("/map", response_model=MapView)
    def get_map() -> MapView:
        return build_map_view(app.state.current_grid, reg, service.current_state())

    @app.get("/api/public/game/{game_id}/events")
    def get_game_events(game_id: str) -> list[dict[str, object]]:
        """Log zdarzeń AsyncTI4 — nie produkujemy go (mamy własną historię).

        Zwracamy pustą listę, by panel zdarzeń frontendu nie zgłaszał 404.
        Historię stanu pokazuje nasz ``HistoryPanel`` (endpoint ``/history``).
        """
        return []

    @app.get("/api/public/game/{game_id}/web-data")
    def get_web_data(game_id: str) -> dict[str, object]:
        """Dokument ``PlayerDataResponse`` dla frontendu ti4_web (viewer planszy).

        Jeden dokument HTTP, z którego frontend renderuje całą planszę: pozycje,
        jednostki w przestrzeni i na planetach, gracze. Statyczne katalogi
        (definicje jednostek/planet/systemów) frontend ma wbudowane i rozwiązuje
        po ID — tu wysyłamy wyłącznie stan.
        """
        return build_web_data(
            app.state.current_grid,
            reg,
            service.current_state(),
            game_name=game_id,
        )

    @app.get("/factions", response_model=list[FactionInfo])
    def get_factions() -> list[FactionInfo]:
        return [
            FactionInfo(
                id=f.id,
                name=f.name,
                home_system=f.home_system,
                home_planets=list(f.home_planets),
                starting_fleet=f.starting_fleet,
                preferred_colours=list(f.preferred_colours),
            )
            for f in sorted(reg.factions.values(), key=lambda x: x.name)
        ]

    @app.post("/map/load", response_model=MapView)
    async def post_load_map(request: MapStringRequest) -> MapView:
        try:
            grid = build_grid_from_map_string(
                request.map_string, reg, include_center=request.include_center
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not grid.positions:
            raise HTTPException(
                status_code=422,
                detail="Map string nie dał żadnego znanego systemu (sprawdź ID i źródła).",
            )
        app.state.current_grid = grid
        await broadcast_map()
        return build_map_view(grid, reg, service.current_state())

    @app.post("/setup/player", response_model=MapView)
    async def post_setup_player(request: SetupPlayerRequest) -> MapView:
        faction = reg.factions.get(request.faction_id)
        if faction is None:
            raise HTTPException(
                status_code=404, detail=f"Nieznana frakcja: {request.faction_id}"
            )
        new_state = apply_setup_to_state(
            service.current_state(),
            player_id=request.player_id,
            color=request.color,
            faction=faction,
            home_position=request.home_position,
        )
        service.replace_state(new_state, label=f"setup:{request.faction_id}")

        # Podmień slot domowy w gridzie na prawdziwy kafelek domowy frakcji,
        # żeby render pokazał grafikę systemu + jednostki (zamiast pustego slotu).
        grid: HexGrid = app.state.current_grid
        if faction.home_system and request.home_position in grid.positions:
            home_sys = reg.systems.get(faction.home_system)
            grid.place_system(
                position=request.home_position,
                system_id=faction.home_system,
                wormholes=list(home_sys.wormholes) if home_sys else None,
                anomalies=set(home_sys.anomalies) if home_sys else None,
                hex_override=Hex(*grid.coordinates(request.home_position)),
            )
            grid.build_edges()

        await service.broadcast()
        await broadcast_map()
        return build_map_view(app.state.current_grid, reg, service.current_state())

    @app.post("/game/new", response_model=MapView)
    async def post_new_game(request: NewGameRequest) -> MapView:
        """Tworzy nową grę w jednym kroku: reset stanu + mapa + setup graczy.

        ``map_string`` opcjonalny (gdy brak — mapa testowa). Kolory i sloty domowe
        przydzielane automatycznie wg kolejności graczy, chyba że jawnie podane.
        """
        if len(request.players) > len(_AUTO_SLOT_ORDER):
            raise HTTPException(
                status_code=422,
                detail=f"Za dużo graczy: max {len(_AUTO_SLOT_ORDER)} (układ 6-osobowy).",
            )

        # 1) Zbuduj mapę (podany string lub testowy).
        map_string = request.map_string or _DEFAULT_MAP_STRING
        try:
            grid = build_grid_from_map_string(
                map_string, reg, include_center=request.include_center
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not grid.positions:
            raise HTTPException(
                status_code=422,
                detail="Map string nie dał żadnego znanego systemu (sprawdź ID i źródła).",
            )

        # 2) Reset stanu i rozstawienie graczy (walidacja frakcji przed mutacją).
        new_state = GameState()
        first_player_id: str | None = None
        for index, player in enumerate(request.players):
            faction = reg.factions.get(player.faction_id)
            if faction is None:
                raise HTTPException(
                    status_code=404, detail=f"Nieznana frakcja: {player.faction_id}"
                )
            slot_position, slot_color = _AUTO_SLOT_ORDER[index]
            home_position = player.home_position or slot_position
            color = player.color or slot_color
            player_id = player.player_id or f"p{index + 1}"
            # Bug 8: pozycja domowa MUSI istnieć na mapie — inaczej kafelek domowy
            # nie zostanie położony, a flota wyląduje w systemie bez kafelka (nie
            # renderuje się). Przy custom map_string slot może nie pasować do układu.
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
            # Podmień slot domowy w gridzie na prawdziwy kafelek domowy frakcji.
            if faction.home_system and home_position in grid.positions:
                home_sys = reg.systems.get(faction.home_system)
                grid.place_system(
                    position=home_position,
                    system_id=faction.home_system,
                    wormholes=list(home_sys.wormholes) if home_sys else None,
                    anomalies=set(home_sys.anomalies) if home_sys else None,
                    hex_override=Hex(*grid.coordinates(home_position)),
                )
        grid.build_edges()

        # Domyślnie: pierwszy gracz jest aktywny (panel faz podświetla kolejkę tur).
        new_state.active_player_id = first_player_id

        app.state.current_grid = grid
        service.replace_state(new_state, label="game:new")
        await service.broadcast()
        await broadcast_map()
        return build_map_view(grid, reg, service.current_state())

    def _validate_base_type(base_type: str) -> None:
        """Odrzuca ``baseType`` spoza katalogu (Bug 5: cicho ginął w web-data).

        ``/map`` emituje każdą jednostkę, ale ``web-data`` pomija typy bez asyncId
        w ``ASYNC_ID_BY_BASE_TYPE`` — jednostka istniałaby w stanie, lecz nie na
        planszy frontendu (desync). Blokujemy wejście nieznanego typu do stanu.
        """
        if base_type not in ASYNC_ID_BY_BASE_TYPE:
            raise HTTPException(
                status_code=422, detail=f"Nieznany baseType: {base_type}"
            )

    @app.post("/system/{position}/space", response_model=MapView)
    async def post_space_units(
        position: str, request: SpaceUnitsRequest
    ) -> MapView:
        for change in request.changes:
            _validate_base_type(change.base_type)
        state = service.current_state().clone()
        system = state.systems.get(position) or SystemState(
            position=position,
            system_id=_system_id_for(position),
        )
        for change in request.changes:
            bucket = system.space_units.setdefault(change.player_id, {})
            if change.count <= 0:
                bucket.pop(change.base_type, None)
            else:
                bucket[change.base_type] = change.count
            if not bucket:
                system.space_units.pop(change.player_id, None)
        state.systems[position] = system
        service.replace_state(state, label=f"space:{position}")
        await service.broadcast()
        await broadcast_map()
        return build_map_view(app.state.current_grid, reg, service.current_state())

    @app.post("/system/{position}/planet/{planet}", response_model=MapView)
    async def post_planet_units(
        position: str, planet: str, request: PlanetUnitsRequest
    ) -> MapView:
        for change in request.changes:
            _validate_base_type(change.base_type)
        state = service.current_state().clone()
        system = state.systems.get(position) or SystemState(
            position=position,
            system_id=_system_id_for(position),
        )
        by_player = system.planet_units.setdefault(planet, {})
        for change in request.changes:
            bucket = by_player.setdefault(change.player_id, {})
            if change.count <= 0:
                bucket.pop(change.base_type, None)
            else:
                bucket[change.base_type] = change.count
            if not bucket:
                by_player.pop(change.player_id, None)
        if request.owner_id is not None:
            system.planet_owners[planet] = request.owner_id
        state.systems[position] = system
        service.replace_state(state, label=f"planet:{position}:{planet}")
        await service.broadcast()
        await broadcast_map()
        return build_map_view(app.state.current_grid, reg, service.current_state())

    def _system_id_for(position: str) -> str:
        """System ID z bieżącego gridu dla pozycji (lub pusty, gdy brak)."""
        grid = app.state.current_grid
        if position in grid.positions:
            return str(grid.system_id_at(position))
        return ""

    def _resolve_player_id(faction_key: str, state: GameState) -> str:
        """Mapuje klucz z ``tileUnitData`` na ``player_id``.

        W web-data jednostki są kluczowane stabilnym ``player_id`` (patrz
        ``web_data._entity_key``), więc edytor zwykle przysyła wprost ``player_id``.
        Priorytet dopasowania (kolejność ważna przy kolizji frakcji/id):
        1. DOKŁADNE ``player_id`` — najpewniejsze, nigdy nie trafia w złego gracza.
        2. Frakcja — tylko gdy JEDNOZNACZNA (dokładnie jeden gracz ma tę frakcję);
           przy kolizji frakcji nie zgadujemy (Bug 2: `faction OR pid` trafiał w złego).
        Gdy brak dopasowania, zwracamy klucz bez zmian (traktujemy jak id gracza).
        """
        if faction_key in state.players:
            return faction_key
        matches = [
            pid
            for pid, player in state.players.items()
            if player.faction == faction_key
        ]
        if len(matches) == 1:
            return matches[0]
        return faction_key

    def _zone_bucket(
        system: SystemState, zone: str, player_id: str
    ) -> dict[str, int]:
        """Zwraca modyfikowalny słownik jednostek gracza w strefie (space/planeta)."""
        if zone == "space":
            return system.space_units.setdefault(player_id, {})
        by_player = system.planet_units.setdefault(zone, {})
        return by_player.setdefault(player_id, {})

    def _prune_zone(system: SystemState, zone: str, player_id: str) -> None:
        """Usuwa puste słowniki jednostek (porządek po edycji)."""
        if zone == "space":
            if not system.space_units.get(player_id):
                system.space_units.pop(player_id, None)
            return
        by_player = system.planet_units.get(zone)
        if by_player is not None:
            if not by_player.get(player_id):
                by_player.pop(player_id, None)
            if not by_player:
                system.planet_units.pop(zone, None)

    @app.post("/system/{position}/edit-units", response_model=MapView)
    async def post_edit_units(position: str, request: UnitEditRequest) -> MapView:
        """God-Mode: dodaj/odejmij jednostki w strefie systemu (delta, bez reguł)."""
        base_type = BASE_TYPE_BY_ASYNC_ID.get(request.async_id)
        if base_type is None:
            raise HTTPException(
                status_code=422, detail=f"Nieznany asyncId: {request.async_id}"
            )
        state = service.current_state().clone()
        player_id = _resolve_player_id(request.faction, state)
        system = state.systems.get(position) or SystemState(
            position=position, system_id=_system_id_for(position)
        )
        bucket = _zone_bucket(system, request.zone, player_id)
        new_count = max(0, bucket.get(base_type, 0) + request.delta)
        if new_count == 0:
            bucket.pop(base_type, None)
        else:
            bucket[base_type] = new_count
        _prune_zone(system, request.zone, player_id)
        state.systems[position] = system
        service.replace_state(state, label=f"edit:{position}:{request.zone}")
        await service.broadcast()
        await broadcast_map()
        return build_map_view(app.state.current_grid, reg, service.current_state())

    @app.post("/units/move", response_model=MapView)
    async def post_move_units(request: UnitMoveRequest) -> MapView:
        """God-Mode: przesuń jednostki między strefami/systemami (bez reguł)."""
        base_type = BASE_TYPE_BY_ASYNC_ID.get(request.async_id)
        if base_type is None:
            raise HTTPException(
                status_code=422, detail=f"Nieznany asyncId: {request.async_id}"
            )
        if request.count <= 0:
            raise HTTPException(status_code=422, detail="count musi być > 0")
        state = service.current_state().clone()
        player_id = _resolve_player_id(request.faction, state)

        src = state.systems.get(request.from_position) or SystemState(
            position=request.from_position,
            system_id=_system_id_for(request.from_position),
        )
        src_bucket = _zone_bucket(src, request.from_zone, player_id)
        available = src_bucket.get(base_type, 0)
        moved = min(available, request.count)
        if moved <= 0:
            raise HTTPException(status_code=422, detail="Brak jednostek do przesunięcia.")
        remaining = available - moved
        if remaining == 0:
            src_bucket.pop(base_type, None)
        else:
            src_bucket[base_type] = remaining
        _prune_zone(src, request.from_zone, player_id)
        state.systems[request.from_position] = src

        dst = state.systems.get(request.to_position) or SystemState(
            position=request.to_position,
            system_id=_system_id_for(request.to_position),
        )
        dst_bucket = _zone_bucket(dst, request.to_zone, player_id)
        dst_bucket[base_type] = dst_bucket.get(base_type, 0) + moved
        state.systems[request.to_position] = dst

        service.replace_state(state, label="move-units")
        await service.broadcast()
        await broadcast_map()
        return build_map_view(app.state.current_grid, reg, service.current_state())

    def _planet_position(planet_id: str, state: GameState) -> str | None:
        """Pozycja ``RPP`` systemu zawierającego daną planetę (z gridu+rejestru).

        Najpierw szuka w systemach aktywnej mapy (grid → system → planety z rejestru);
        gdy nie znajdzie, sprawdza systemy już obecne w stanie (np. slot domowy).
        Zwraca None, gdy planety nie da się umiejscowić (nie powinno się zdarzyć dla
        planet z map stringa).
        """
        grid = app.state.current_grid
        for position in grid.positions:
            system_id = grid.system_id_at(position)
            system = reg.systems.get(system_id)
            if system is not None and planet_id in system.planets:
                return str(position)
        for position, sys_state in state.systems.items():
            system = reg.systems.get(sys_state.system_id)
            if system is not None and planet_id in system.planets:
                return str(position)
        return None

    def _sync_controlled_planets(
        player_id: str, target: list[str], state: GameState
    ) -> None:
        """Synchronizuje kontrolę planet gracza do ``planet_owners`` (opcja A).

        ``planet_owners`` w systemach jest jedynym źródłem prawdy (Bug 3). Ta funkcja
        przenosi listę docelową z edycji God-Mode do systemów:
        1. Odbiera graczowi własność planet spoza listy docelowej (we wszystkich systemach).
        2. Nadaje własność każdej planecie z listy w jej systemie (tworząc ``SystemState``
           w razie potrzeby) — nadpisując poprzedniego właściciela.
        """
        target_set = set(target)
        # 1) Odbierz własność planet, których już nie ma na liście docelowej.
        for sys_state in state.systems.values():
            for planet_id, owner in list(sys_state.planet_owners.items()):
                if owner == player_id and planet_id not in target_set:
                    del sys_state.planet_owners[planet_id]
        # 2) Nadaj własność planet z listy docelowej w ich systemach.
        for planet_id in target_set:
            position = _planet_position(planet_id, state)
            if position is None:
                continue  # planeta spoza mapy — pomijamy (nie da się umiejscowić)
            system = state.systems.get(position) or SystemState(
                position=position, system_id=_system_id_for(position)
            )
            system.planet_owners[planet_id] = player_id
            state.systems[position] = system

    @app.post("/player/{player_id}/edit", response_model=StateEnvelope)
    async def post_edit_player(
        player_id: str, request: PlayerEditRequest
    ) -> StateEnvelope:
        """God-Mode: edycja pól gracza (VP, zasoby, CC, frakcja, planety…).

        Tworzy gracza, gdy nie istnieje. Każde podane pole nadpisuje stan; pominięte
        pozostają bez zmian. Bez sprawdzania zasad. Commit → historia (Undo działa).

        Kontrola planet (``controlled_planets``) jest synchronizowana do
        ``planet_owners`` systemów (opcja A — jedno źródło prawdy, Bug 3): panel i
        mapa zawsze pokazują tę samą kontrolę.
        """
        state = service.current_state().clone()
        player = state.players.get(player_id) or PlayerState(player_id=player_id)
        updates = request.model_dump(exclude_none=True)
        for field, value in updates.items():
            # leader_states SCALAMY z istniejącym (edycja jednego lidera nie
            # kasuje stanu pozostałych). Reszta pól = pełne nadpisanie.
            if field == "leader_states" and isinstance(value, dict):
                merged = dict(player.leader_states)
                merged.update(value)
                player.leader_states = merged
            else:
                setattr(player, field, value)
        state.players[player_id] = player
        # Synchronizacja kontroli planet do systemów (planet_owners = źródło prawdy).
        if request.controlled_planets is not None:
            _sync_controlled_planets(player_id, request.controlled_planets, state)
        service.replace_state(state, label=f"player:{player_id}")
        await service.broadcast()
        await broadcast_map()
        return service.envelope()

    # --- Przepływ faz i tur (Etap E1) ---------------------------------------

    async def _commit_flow(new_state: GameState, label: str) -> StateEnvelope:
        """Wspólne commitowanie wyniku funkcji przepływu + rozesłanie stanu."""
        service.replace_state(new_state, label=label)
        await service.broadcast()
        await broadcast_map()
        return service.envelope()

    @app.post("/turn/end", response_model=StateEnvelope)
    async def post_end_turn() -> StateEnvelope:
        """Kończy turę bieżącego gracza (tura przechodzi do następnego niespasowanego)."""
        return await _commit_flow(turn_flow.end_turn(service.current_state()), "turn:end")

    @app.post("/turn/pass", response_model=StateEnvelope)
    async def post_pass_turn() -> StateEnvelope:
        """Bieżący gracz pasuje (pomijany do końca fazy akcji)."""
        return await _commit_flow(turn_flow.pass_turn(service.current_state()), "turn:pass")

    @app.post("/phase/next", response_model=StateEnvelope)
    async def post_next_phase() -> StateEnvelope:
        """Przechodzi do następnej fazy rundy (Strategia→Akcja→Status→Agenda)."""
        return await _commit_flow(
            turn_flow.next_phase(service.current_state()), "phase:next"
        )

    @app.post("/round/next", response_model=StateEnvelope)
    async def post_next_round() -> StateEnvelope:
        """Rozpoczyna nową rundę: runda +1, faza = strategia, reset pasów.

        Na przełomie rundy karty strategii wracają do puli, a na każdej NIEWYBRANEJ
        karcie dokładany jest +1 trade good (RULES.md 13 — reguła akumulacji z bota).
        Kolejność: accumulate (na poprzednich wyborach) → reset → next_round.
        """
        state = service.current_state()
        state = strategy_phase.accumulate_unpicked_tg(state, reg)
        state = strategy_phase.reset_strategy_cards(state)
        state = turn_flow.next_round(state)
        return await _commit_flow(state, "round:next")

    # --- Faza strategii (Etap E2) -------------------------------------------

    @app.get("/strategy/cards", response_model=list[StrategyCardInfo])
    def get_strategy_cards() -> list[StrategyCardInfo]:
        """Pula kart strategii aktywnego zestawu + ich stan w bieżącej grze."""
        state = service.current_state()
        # Mapa: numer inicjatywy -> player_id, który ją wybrał.
        owner_by_init: dict[int, str] = {}
        exhausted_by_init: dict[int, bool] = {}
        for pid, player in state.players.items():
            for init in player.strategy_cards:
                owner_by_init[init] = pid
                exhausted_by_init[init] = init in player.exhausted_strategy_cards
        cards: list[StrategyCardInfo] = []
        for card in reg.strategy_card_set():
            cards.append(
                StrategyCardInfo(
                    initiative=card.initiative,
                    id=card.id,
                    name=card.name,
                    primary_texts=list(card.primary_texts),
                    secondary_texts=list(card.secondary_texts),
                    colour_hex_code=card.colour_hex_code,
                    trade_goods=state.strategy_card_tg.get(card.initiative, 0),
                    picked_by=owner_by_init.get(card.initiative),
                    exhausted=exhausted_by_init.get(card.initiative, False),
                )
            )
        return cards

    @app.post("/strategy/pick", response_model=StateEnvelope)
    async def post_strategy_pick(request: StrategyPickRequest) -> StateEnvelope:
        """Gracz wybiera kartę strategii (transfer TG z karty, ustala inicjatywę)."""
        try:
            new_state = strategy_phase.pick_strategy_card(
                service.current_state(), reg, request.player_id, request.initiative
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return await _commit_flow(
            new_state, f"strategy:pick:{request.player_id}:{request.initiative}"
        )

    @app.post("/strategy/play", response_model=StateEnvelope)
    async def post_strategy_play(request: StrategyPlayRequest) -> StateEnvelope:
        """Gracz zagrywa (wyczerpuje) swoją kartę strategii."""
        try:
            new_state = strategy_phase.play_strategy_card(
                service.current_state(), request.player_id, request.initiative
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return await _commit_flow(
            new_state, f"strategy:play:{request.player_id}:{request.initiative}"
        )

    @app.put("/state", response_model=StateEnvelope)
    async def put_state(state: GameState) -> StateEnvelope:
        envelope = service.replace_state(state)
        await service.broadcast()
        return envelope

    @app.post("/god-mode/patch", response_model=StateEnvelope)
    async def post_patch(patch: GodModePatch) -> StateEnvelope:
        try:
            envelope = service.apply_patch(patch)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        await service.broadcast()
        return envelope

    @app.get("/history", response_model=HistoryList)
    def get_history() -> HistoryList:
        """Lista migawek historii (etykieta + która bieżąca) dla panelu historii."""
        return HistoryList(
            entries=[
                HistoryEntry(seq=seq, label=label, is_current=is_current)
                for seq, label, is_current in service.history_entries()
            ]
        )

    @app.post("/history/goto/{seq}", response_model=StateEnvelope)
    async def post_history_goto(seq: int) -> StateEnvelope:
        """Przeskok do wskazanej migawki historii (undo/redo do punktu)."""
        envelope = service.goto(seq)
        await service.broadcast()
        await broadcast_map()
        return envelope

    @app.post("/undo", response_model=StateEnvelope)
    async def post_undo() -> StateEnvelope:
        envelope = service.undo()
        await service.broadcast()
        await broadcast_map()
        return envelope

    @app.post("/redo", response_model=StateEnvelope)
    async def post_redo() -> StateEnvelope:
        envelope = service.redo()
        await service.broadcast()
        await broadcast_map()
        return envelope

    # --- WebSocket ----------------------------------------------------------

    @app.websocket("/ws")
    async def ws_state(websocket: WebSocket) -> None:
        await manager.connect(websocket)
        try:
            # Po połączeniu wyślij natychmiast bieżący stan.
            await websocket.send_json(service.envelope().model_dump(mode="json"))
            while True:
                # Klient nie wysyła komend w tym bloku; utrzymujemy połączenie.
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    # --- Static (assety danych JSON) ---------------------------------------
    if config.ASSETS_DIR.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=str(config.ASSETS_DIR)),
            name="static",
        )

    return app
