"""Router gry: stan, mapa, web-data, frakcje, nowa gra, wczytanie mapy, setup gracza."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.actor import HostOnly, identity_of, viewer_player
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    EngineConfigInfo,
    FactionInfo,
    MapStringRequest,
    MapView,
    NewGamePlayer,
    NewGameRequest,
    PlayerHandResponse,
    SetupPlayerRequest,
    StartingUnit,
    StateEnvelope,
)
from src.api.serializers import AUTO_SLOT_ORDER, DEFAULT_MAP_STRING, build_map_view
from src.api.web_data import build_web_data
from src.core import actor as actor_rules
from src.core import game_clock, strategy_phase
from src.core.faction_setup import (
    OFF_BOARD_HOME,
    apply_setup_to_state,
    off_board_corner,
    parse_starting_fleet,
)
from src.core.game_setup import begin_setup, place_frontier_tokens
from src.core.game_state import GameState, Phase
from src.core.hex_grid import Hex, HexGrid
from src.core.map_string import build_grid_from_map_string
from src.core.models import FactionDef
from src.core.objectives import agenda_deck_ids
from src.core.player_colors import all_color_aliases, canonical_color
from src.core.registry import StaticDataRegistry
from src.core.setup_service import (
    PlayerSetupInput,
    ResolvedPlayer,
    resolve_players,
)

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
    request: Request,
    game_id: str,
    viewing_player: str | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> dict[str, object]:
    """Dokument ``PlayerDataResponse`` dla frontendu ti4_web (viewer planszy).

    Opcjonalny query param ``viewing_player`` wyznacza perspektywę dokumentu (R6.6);
    brak → aktywny gracz. Nieudane ustalenie viewera lub nieznany viewer →
    ``ValueError`` z warstwy ``core``/serializacji, mapowany na HTTP 422.

    Gra sieciowa (RULES.md 44.2/44.3): parametr jest ignorowany — perspektywa to miejsce z tokenu,
    a dokument buduje się z projekcji ścisłej (``project_strict``).
    """
    strict = not identity_of(request).sees_everything
    viewing_player = viewer_player(request, viewing_player)
    state = ctx.service.current_state()
    try:
        doc = build_web_data(
            ctx.current_grid,
            ctx.registry,
            state,
            game_name=game_id,
            viewing_player=viewing_player,
            now=ctx.service.now(),
            strict=strict,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # Na kogo czeka gra (jawne; pasek „Your move / Waiting for X" w sieci, RULES.md 44.5).
    doc["awaiting"] = [
        {
            "playerId": pid,
            "name": state.players[pid].display_name or state.players[pid].faction or pid,
            "faction": state.players[pid].faction,
            "color": state.players[pid].color,
            "reason": reason,
        }
        for pid, reason in actor_rules.awaiting(state)
    ]
    return doc


@router.get("/api/game/{game_id}/hand", response_model=PlayerHandResponse)
def get_player_hand(
    request: Request,
    game_id: str,
    player: str | None = None,
    ctx: AppContext = Depends(get_ctx),
) -> PlayerHandResponse:
    """Prywatna ręka gracza (karty akcji / tajne cele / promissory notes) z ID.

    Tryb solo/lokalny: operator widzi wszystko (God-Mode), więc endpoint zwraca
    JAWNIE identyfikatory kart — w odróżnieniu od web-data, które cudze ręce
    redaguje do samych liczników (R6.1). Query param ``player`` wskazuje gracza
    (``player_id``); brak → AKTYWNY gracz. To zasila „pasek ręki" na mapie
    (styl stołu) oraz zakładkę gracza.

    Zwraca puste listy, gdy nie da się ustalić gracza (np. przed startem gry) —
    panel ręki pokazuje wtedy po prostu pustą rękę zamiast błędu.
    """
    player = viewer_player(request, player)  # RULES.md 44.3
    state = ctx.service.current_state()
    player_id = player or state.active_player_id
    target = state.players.get(player_id) if player_id else None
    if target is None:
        return PlayerHandResponse()
    return PlayerHandResponse(
        actionCards=list(target.private.action_cards),
        secretObjectives=list(target.private.secret_objectives),
        promissoryNotes=list(target.private.promissory_notes),
        agendaPeek=list(target.private.agenda_peek),
        revealedSecrets={k: list(v) for k, v in target.private.revealed_secrets.items()},
    )


def _faction_starting_units(faction: FactionDef) -> list[StartingUnit]:
    """Flota startowa frakcji jako lista pozycji (liczba + typ) z pełnymi nazwami w UI.

    Używa tego samego parsera co setup (``parse_starting_fleet``), więc kody floty
    (``cv``/``dd``/...) są rozwiązywane w jednym miejscu. Przy niepoprawnym stringu
    (teoretycznie — dane są spójne) zwraca pustą listę, by nie wywalić listy frakcji.
    """
    if not faction.starting_fleet:
        return []
    try:
        entries = parse_starting_fleet(faction.starting_fleet, faction.home_planets)
    except ValueError:
        return []
    return [
        StartingUnit(
            base_type=entry.base_type,
            count=entry.count,
            placement=str(entry.placement),
        )
        for entry in entries
    ]


def _faction_breakthrough_id(
    faction_id: str, registry: StaticDataRegistry
) -> str | None:
    """Identyfikator przełomu (breakthrough) frakcji lub None — dopasowanie po ``faction``."""
    breakthrough = registry.breakthrough_for_faction(faction_id)
    return breakthrough.id if breakthrough is not None else None


def _faction_info(f: FactionDef, registry: StaticDataRegistry) -> FactionInfo:
    """Buduje ``FactionInfo`` (pola bogate do faction summary) ze statycznego rejestru."""
    return FactionInfo(
        id=f.id,
        name=f.name,
        source=f.source,
        home_system=f.home_system,
        home_planets=list(f.home_planets),
        starting_fleet=f.starting_fleet,
        preferred_colours=list(f.preferred_colours),
        starting_tech_options=list(f.starting_tech_options),
        starting_tech_amount=f.starting_tech_amount,
        # Pola bogate do faction summary (identyfikatory ze statycznego rejestru).
        starting_tech=list(f.starting_tech),
        abilities=list(f.abilities),
        faction_tech=list(f.faction_tech),
        leaders=list(f.leaders),
        units=list(f.units),
        promissory_notes=list(f.promissory_notes),
        commodities=f.commodities,
        complexity=f.complexity,
        breakthrough=_faction_breakthrough_id(f.id, registry),
        starting_units=_faction_starting_units(f),
    )


@router.get("/factions", response_model=list[FactionInfo])
def get_factions(ctx: AppContext = Depends(get_ctx)) -> list[FactionInfo]:
    return [
        _faction_info(f, ctx.registry)
        for f in sorted(ctx.registry.factions.values(), key=lambda x: x.name)
        # Pomijamy placeholdery systemowe (Neutral/Lazax) — nie są grywalne.
        if f.is_playable
    ]


@router.get("/factions/{faction_id}", response_model=FactionInfo)
def get_faction(
    faction_id: str, ctx: AppContext = Depends(get_ctx)
) -> FactionInfo:
    """Pełne dane JEDNEJ frakcji po id — także NIEGRYWALNEJ (np. Obsidian).

    `/factions` zwraca tylko grywalne (pula wyboru). Ten endpoint dociąga detal
    dowolnej frakcji z rejestru na żądanie — używane dla edge-case'u Firmament →
    Obsidian: Obsidian nie jest wybieralny przy setupie, ale gracz może podejrzeć
    jego komponenty (wchodzi do gry przez akcję Firmamentu). Placeholdery systemowe
    (pusty home / brak liderów) odrzucamy — nie mają czego pokazać.
    """
    faction = ctx.registry.factions.get(faction_id)
    if faction is None or (not faction.home_system and not faction.leaders):
        raise HTTPException(status_code=404, detail=f"Unknown faction: {faction_id!r}")
    return _faction_info(faction, ctx.registry)


@router.get("/engine/config", response_model=EngineConfigInfo)
def get_engine_config(ctx: AppContext = Depends(get_ctx)) -> EngineConfigInfo:
    """Konfiguracja silnika dla setupu (dozwolony zbiór poziomów trudności bota).

    Front pobiera zbiór trudności STĄD zamiast trzymać własną kopię — wartości
    pochodzą z ``engine_config.json`` przez ``StaticDataRegistry`` (R10.2,
    docs/RULES.md 36). Lista jest posortowana dla deterministycznej prezentacji.
    """
    return EngineConfigInfo(
        valid_difficulties=sorted(ctx.registry.valid_difficulties()),
        valid_personalities=sorted(ctx.registry.valid_personalities()),
        seats=[position for position, _color in AUTO_SLOT_ORDER],
    )


@router.post("/map/load", dependencies=[HostOnly], response_model=MapView)
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
            detail="The map string produced no known system (check IDs and sources).",
        )
    ctx.set_map(grid)
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


def _place_locked_mallice(grid: HexGrid, registry: StaticDataRegistry) -> None:
    """Kładzie Wormhole Nexus stroną nieaktywną (82a, tylko gamma) z boku mapy.

    Kafelek leży poza pierścieniami, w rogu ``tl`` (jak w AsyncTI4). Pomijamy, gdy
    róg jest już zajęty albo kafelek nie jest załadowany (wyłączone źródło).
    """
    if "tl" in grid.positions or "82a" not in registry.systems:
        return
    _place_off_board_home(grid, "82a", "tl", registry)


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


def _available_colors() -> list[str]:
    """Zbiór dozwolonych kolorów graczy (R7.7) — wszystkie kolory AsyncTI4.

    Na początku stoją kolory rogów domowych (``AUTO_SLOT_ORDER``), żeby auto-przydział
    dawał te same kolory co dotąd; dalej reszta palety (solid / split / gradient)
    z ``assets/data/colors``. Wszystko w postaci aliasów kanonicznych, bo tak
    nazywają się grafiki jednostek (``units/lgy_gf.png``). Wstrzykiwane do
    ``resolve_players`` zamiast hardkodowania listy w ``core``.
    """
    ordered = [canonical_color(color) for _position, color in AUTO_SLOT_ORDER]
    ordered.extend(alias for alias in all_color_aliases() if alias not in ordered)
    return ordered


def _canonicalize_colors(players: Sequence[NewGamePlayer]) -> None:
    """Zamienia jawnie podane kolory na aliasy kanoniczne (``white`` → ``lgy``).

    Dzięki temu ``white`` i ``lgy`` to ten sam kolor w wykrywaniu duplikatów.
    Nieznany kolor zostaje bez zmian i zostanie odrzucony walidacją.
    """
    for player in players:
        if player.color is not None:
            player.color = canonical_color(player.color)


def _validate_home_position(
    grid: HexGrid, home_position: str, player_id: str, taken: set[str]
) -> None:
    """Waliduje przypisanie pozycji domowej względem mapy (R14.4).

    Pozycja musi ISTNIEĆ na mapie (inaczej flota się nie renderuje — Bug 8) oraz
    nie może być już PRZYPISANA innemu graczowi. Naruszenie → ``HTTPException(422)``
    z komunikatem wskazującym gracza; stan setupu pozostaje niezmieniony.
    """
    if home_position not in grid.positions:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Home position {home_position!r} of player {player_id!r} does not "
                f"exist on this map. Provide a home_position matching the map_string."
            ),
        )
    if home_position in taken:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Home position {home_position!r} of player {player_id!r} is already "
                f"przypisana innemu graczowi."
            ),
        )


def _apply_resolved_player(
    state: GameState,
    resolved: ResolvedPlayer,
    faction: FactionDef,
    *,
    home_position: str,
    unit_position: str,
    unit_system_id: str,
) -> GameState:
    """Nanosi jednego ``ResolvedPlayer`` na stan i ustawia nowe pola ``PlayerState``.

    Woła ``apply_setup_to_state`` (flota, kontrola planet, technologie), a następnie
    dopisuje pola setupu modelu gracza: ``display_name``, ``control_type``,
    ``difficulty`` (R11.1/R11.2). Walidacja odbyła się już w ``resolve_players``,
    więc tutaj nie powtarzamy sprawdzeń.
    """
    new_state = apply_setup_to_state(
        state,
        player_id=resolved.player_id,
        color=resolved.color,
        faction=faction,
        home_position=home_position,
        chosen_tech=resolved.starting_tech,
        unit_position=unit_position,
        unit_system_id=unit_system_id,
    )
    player = new_state.players[resolved.player_id]
    player.display_name = resolved.display_name
    player.control_type = resolved.control_type
    player.difficulty = resolved.difficulty
    player.personality = resolved.personality
    return new_state


@router.post("/setup/player", dependencies=[HostOnly], response_model=MapView)
async def post_setup_player(
    request: SetupPlayerRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """Setup pojedynczego gracza na wskazanym slocie domowym.

    Walidacja konfiguracji (nazwa, kolor, frakcja, trudność, technologie) jest
    delegowana do ``resolve_players`` z jednoelementową listą — ten sam kontrakt
    co ``/game/new`` (R8.5: ``faction_id=None`` → losowa frakcja). ``ValueError``
    z walidacji → ``HTTPException(422)``. ``home_position`` jest wymagany w tym
    kontrakcie i walidowany względem grida (R14.4).
    """
    current = ctx.service.current_state()
    # Kolory już zajęte przez rozstawionych graczy — wykluczamy je z puli, żeby
    # auto-dobór w ``resolve_players`` nie powielił koloru istniejącego gracza.
    used_colors = {
        canonical_color(p.color) for p in current.players.values() if p.color is not None
    }
    request.color = canonical_color(request.color)
    available = [c for c in _available_colors() if c not in used_colors]
    try:
        # SetupPlayerRequest spełnia PlayerSetupInput strukturalnie; jego pola
        # ``color``/``home_position`` są węższe (str zamiast str|None), co mypy
        # traktuje jak niezgodność atrybutu mutowalnego protokołu — rzutujemy
        # jawnie na protokół (duck typing jest poprawny w czasie działania).
        resolved_list = resolve_players(
            [cast("PlayerSetupInput", request)],
            ctx.registry,
            available_colors=available,
            max_players=len(AUTO_SLOT_ORDER),
            valid_difficulties=ctx.registry.valid_difficulties(),
            valid_personalities=ctx.registry.valid_personalities(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    resolved = resolved_list[0]
    faction = ctx.registry.factions[resolved.faction_id]

    grid = ctx.current_grid
    # R14.4: pozycja domowa musi istnieć na mapie i nie może być zajęta przez
    # innego już rozstawionego gracza (home_position z ich PlayerState).
    taken_homes = {
        p.home_position
        for pid, p in current.players.items()
        if pid != resolved.player_id and p.home_position is not None
    }
    _validate_home_position(grid, request.home_position, resolved.player_id, taken_homes)

    # Najpierw połóż kafelki domowe (ustala, gdzie trafią jednostki — off-board dla
    # Ghost/Crimson), zbierając zajęte rogi z już rozstawionych graczy.
    taken_corners = {p for p in grid.positions if p in {"tr", "br", "bl", "tl"}}
    unit_position, unit_system_id = _setup_home_tiles(
        grid, faction, request.home_position, ctx.registry, taken_corners
    )
    grid.build_edges()
    ctx.save_map()  # kafelek domowy zmienił siatkę w miejscu — zapis partii (RULES.md 44.4)
    new_state = _apply_resolved_player(
        current,
        resolved,
        faction,
        home_position=request.home_position,
        unit_position=unit_position,
        unit_system_id=unit_system_id,
    )

    # Utrzymaj kolejność miejsc (RULES.md 24): dopisz nowego gracza na koniec
    # stołu. Pierwszy gracz zostaje mówcą. W fazie strategii zaktualizuj, kto
    # wybiera (mówca, gdy jeszcze nikt nie wybierał).
    if resolved.player_id not in new_state.seating_order:
        new_state.seating_order = [*new_state.seating_order, resolved.player_id]
    if new_state.speaker_id is None:
        strategy_phase.set_speaker(new_state, new_state.seating_order[0])
    if new_state.phase is Phase.STRATEGY:
        new_state.active_player_id = strategy_phase.next_strategy_picker(new_state)
    ctx.service.replace_state(new_state, label=f"setup:{resolved.faction_id}")

    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return build_map_view(ctx.current_grid, ctx.registry, ctx.service.current_state())


@router.post("/game/new", dependencies=[HostOnly], response_model=MapView)
async def post_new_game(
    request: NewGameRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """Tworzy nową grę w jednym kroku: reset stanu + mapa + setup graczy.

    Walidacja konfiguracji graczy (liczba, nazwy, kolory, frakcje, typ sterowania,
    trudność, technologie) jest w całości delegowana do ``resolve_players``
    (warstwa ``core``). Endpoint pozostaje cienki: buduje mapę, rozwiązuje graczy,
    iteruje ``ResolvedPlayer`` i nanosi ich na stan. ``ValueError`` z walidacji →
    ``HTTPException(422)`` z komunikatem wskazującym pole i gracza (R11.4).
    """
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
            detail="The map string produced no known system (check IDs and sources).",
        )

    # Delegacja całej walidacji/normalizacji graczy do core (R11.1–R11.6, R8.5).
    # Zakres liczby graczy, losowy dobór frakcji i auto-kolory obsługuje resolve_players.
    _canonicalize_colors(request.players)
    try:
        resolved_players = resolve_players(
            request.players,
            ctx.registry,
            available_colors=_available_colors(),
            max_players=len(AUTO_SLOT_ORDER),
            valid_difficulties=ctx.registry.valid_difficulties(),
            valid_personalities=ctx.registry.valid_personalities(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        # FAN-AGENDAS: walidacja wariantu talii agend (standard / absol).
        agenda_deck_ids(ctx.registry, request.agenda_deck)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    _place_locked_mallice(grid, ctx.registry)

    new_state = GameState()
    new_state.decks.agenda_variant = request.agenda_deck
    seating: list[str] = []  # kolejność graczy przy stole (RULES.md 24)
    taken_corners: set[str] = set()  # rogi off-board zajęte przez Ghost/Crimson
    taken_homes: set[str] = set()  # zajęte pozycje domowe (R14.4)
    for index, resolved in enumerate(resolved_players):
        faction = ctx.registry.factions[resolved.faction_id]
        # home_position opcjonalny (R14.3): podany → walidacja względem mapy (R14.4),
        # pominięty → auto ze slotu wg kolejności gracza (AUTO_SLOT_ORDER).
        slot_position = AUTO_SLOT_ORDER[index][0]
        home_position = resolved.home_position or slot_position
        _validate_home_position(grid, home_position, resolved.player_id, taken_homes)
        taken_homes.add(home_position)
        seating.append(resolved.player_id)
        # Połóż kafelki domowe (off-board dla Ghost/Crimson) i ustal gdzie flota.
        unit_position, unit_system_id = _setup_home_tiles(
            grid, faction, home_position, ctx.registry, taken_corners
        )
        new_state = _apply_resolved_player(
            new_state,
            resolved,
            faction,
            home_position=home_position,
            unit_position=unit_position,
            unit_system_id=unit_system_id,
        )
    grid.build_edges()

    # Kolejność miejsc + mówca (RULES.md 24): pierwszy gracz = mówca na start.
    # Nowa gra zaczyna fazą strategii, więc aktywny = pierwszy wybierający (mówca).
    new_state.seating_order = seating
    strategy_phase.set_speaker(new_state, seating[0] if seating else None)
    new_state.active_player_id = strategy_phase.next_strategy_picker(new_state)
    # Cele i talie (RULES.md 41.1): 5+5 celów publicznych, dwa cele I etapu odkryte,
    # po jednym tajnym celu na gracza, potasowana talia kart akcji.
    # Gracze, mówca i żeton Custodians kończą setup w UI (``/setup/*``); do tego czasu
    # karty strategii są zablokowane (RULES.md 45).
    new_state = begin_setup(new_state, ctx.registry)
    # Żetony frontier na systemach bez planet (w tym bramy Creuss Gate / The Sorrow).
    new_state = place_frontier_tokens(new_state, grid, ctx.registry)
    if request.chess_clock is not None:
        # Zegar szachowy (RULES.md 58): rusza przy commicie, gdy pojawi się holder.
        new_state = game_clock.configure(
            new_state,
            initial_ms=request.chess_clock.total_minutes * 60_000,
            increment_ms=request.chess_clock.increment_seconds * 1000,
        )
    ctx.set_map(grid)
    ctx.service.replace_state(new_state, label="game:new")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return build_map_view(grid, ctx.registry, ctx.service.current_state())
