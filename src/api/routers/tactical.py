"""Router akcji taktycznej (Etap E3): aktywacja systemu + maszyna kroków.

Cienka warstwa HTTP: woła czyste funkcje z ``core.tactical`` (przepływ kroków) oraz
``core.board_edit`` (God-Mode żetony dowodzenia), commituje i rozsyła stan + mapę.
Aplikacja PROWADZI kroki akcji taktycznej, ale NIE waliduje reguł TI4 — gracze grają
fizycznie i wprowadzają wynik (decyzja projektowa; patrz docs/RULES.md 19).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from src.api.actor import ActorId, HostOnly
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    ActivateSystemRequest,
    CapturePlanetRequest,
    CombatHelpResponse,
    CombatSideHelp,
    CombatUnitHelp,
    CommandTokenRequest,
    ComponentActionRequest,
    MapView,
    MoveRangeResponse,
    MoveRouteCargo,
    MoveRouteResponse,
    MoveRouteShip,
    MoveShipsRequest,
    ProduceRequest,
    ProducibleUnitHelp,
    ProductionHelpResponse,
    StateEnvelope,
    TacticalStepRequest,
)
from src.api.serializers import build_map_view
from src.api.web_data import entity_key_map
from src.core import actor as actor_rules
from src.core import (
    board_edit,
    combat,
    component_action,
    movement,
    movement_route,
    production,
    tactical,
)
from src.core.combat import PlayerCombat
from src.core.game_state import GameState, TacticalStep
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

router = APIRouter()

# Etykieta migawki ruchu statków — po niej „Undo last move” rozpoznaje, co wolno cofnąć.
MOVE_LABEL_PREFIX = "tactical:move:"


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


@router.post("/tactical/move", response_model=StateEnvelope)
async def post_tactical_move(
    actor: ActorId,
    request: MoveShipsRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Ruch statków do aktywnego systemu z WALIDACJĄ reguł (RULES.md 32).

    W odróżnieniu od God-Mode ``/units/move`` (bez reguł) — tu egzekwujemy R1–R6
    (zasięg z UnitDef, przejezdność anomalii, brak przejścia przez obce statki,
    start nie z własnym CC). Nielegalny ruch → 422.
    """
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Move ships"
    )
    player_id = board_edit.resolve_player_id(request.faction, ctx.service.current_state())
    # Statki (pojedynczy stos ``base_type``/``count`` dla zgodności wstecznej ORAZ
    # lista ``ships`` dla pełnej floty z UI) + ładunek → słowniki {base_type: count}.
    ships: dict[str, int] = {}
    if request.base_type is not None and request.count > 0:
        ships[request.base_type] = request.count
    for item in request.ships:
        if item.count > 0:
            ships[item.base_type] = ships.get(item.base_type, 0) + item.count
    cargo = [
        movement.CargoPickup(
            base_type=item.base_type,
            count=item.count,
            from_zone=item.from_zone,
            from_position=item.from_position,
        )
        for item in request.cargo
        if item.count > 0
    ]
    try:
        new_state = movement.move_fleet(
            ctx.service.current_state(),
            ctx.current_grid,
            ctx.registry,
            request.from_position,
            ships,
            cargo,
            player_id,
            gravity_drive=request.gravity_drive,
            tempesta=request.tempesta,
            imperator=request.imperator,
            route=request.route,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(
        ctx, new_state, f"{MOVE_LABEL_PREFIX}{request.from_position}"
    )


@router.post("/tactical/undo-move", response_model=StateEnvelope)
async def post_tactical_undo_move(
    actor: ActorId, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """„Undo last move” w kroku ruchu — dla AKTYWNEGO gracza, nie tylko hosta.

    W odróżnieniu od ogólnego ``/undo`` (God-Mode, host) cofa WYŁĄCZNIE ostatnią migawkę,
    jeśli jest to ruch statków (``tactical:move:*``) — gracz nie cofnie cudzej akcji ani
    innego kroku. Inna ostatnia zmiana → 422.
    """
    state = ctx.service.current_state()
    actor_rules.require(state, actor, [state.active_player_id], "Undo move")
    label = ctx.service.current_label() or ""
    if not label.startswith(MOVE_LABEL_PREFIX):
        raise HTTPException(
            status_code=422,
            detail="Nothing to undo - the last change was not a ship move.",
        )
    envelope = ctx.service.undo()
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return envelope


@router.post("/tactical/produce", response_model=StateEnvelope)
async def post_tactical_produce(
    actor: ActorId,
    request: ProduceRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Produkcja w aktywnym systemie (RULES.md 33.2-33.3): walidacja + płatność + postawienie.

    Limit PRODUCTION (wspólny dla całej akcji), blokada statków, strefy umieszczenia, rezerwa
    i koszt. Płatność: ``spend`` (planety do wyczerpania + TG) albo, gdy pominięte,
    automatyczna. W odróżnieniu od God-Mode edit-units egzekwuje reguły.
    """
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Produce"
    )
    state = ctx.service.current_state()
    player_id = board_edit.resolve_player_id(request.faction, state)
    orders = [
        production.ProductionOrder(
            base_type=o.base_type, count=o.count, zone=o.zone, sources=tuple(o.sources)
        )
        for o in request.orders
    ]
    spend = (
        production.Spend(
            planets=tuple(request.spend.planets),
            trade_goods=request.spend.trade_goods,
        )
        if request.spend is not None
        else None
    )
    try:
        new_state = production.produce(
            state, ctx.current_grid, ctx.registry, player_id, orders, spend,
            exhaust_aida=request.exhaust_aida,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(
        ctx, new_state, f"tactical:produce:{state.active_system}"
    )


@router.post("/tactical/activate", response_model=StateEnvelope)
async def post_activate_system(
    actor: ActorId,
    request: ActivateSystemRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Aktywuje system przez aktywnego gracza (kładzie CC, ustawia aktywny system)."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.turn_player, "Activate system"
    )
    try:
        new_state = tactical.activate_system(
            ctx.service.current_state(), ctx.current_grid, request.position
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, f"tactical:activate:{request.position}")


@router.post("/tactical/component-action", response_model=StateEnvelope)
async def post_component_action(
    actor: ActorId,
    request: ComponentActionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Akcja komponentu — trzeci typ akcji fazy akcji (RULES.md 31.8).

    Rejestruje, że aktywny gracz wykonał akcję komponentu w tej turze
    (``took_action_this_turn``), tak jak akcja strategiczna/taktyczna — dzięki temu
    ``End turn`` się odblokowuje. NIE wykonuje efektu konkretnego komponentu (szkielet);
    ``component_id`` jest tylko adnotacją „co zagrano". Walidacja (faza/tura/okno/jedna
    akcja) siedzi w ``core.component_action`` — ``ValueError`` → HTTP 422.
    """
    actor_rules.check(
        ctx.service.current_state(),
        actor,
        request.player_id,
        actor_rules.turn_player,
        "Component action",
    )
    try:
        new_state = component_action.play_component_action(
            ctx.service.current_state(), request.player_id, request.component_id,
            params=request.params,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    label = f"component-action:{request.component_id or 'other'}"
    return await _commit_flow(ctx, new_state, label)


@router.post("/tactical/step/next", response_model=StateEnvelope)
async def post_next_step(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Przechodzi do następnego kroku akcji taktycznej (po produkcji — kończy akcję).

    Wejście w krok SPACE_CANNON otwiera okno Space Cannon Offense (RULES.md 38) dla graczy
    mających strzelców i cel; opuszczenie kroku przy otwartym oknie → 422.
    """
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.turn_player, "Next tactical step"
    )
    try:
        state = ctx.service.current_state()
        # registry → silnik sprawdza limit pojemności przed przejściem (RULES.md 39.6); gdy
        # jest nadwyżka, krok ZOSTAJE i otwiera się okno CAPACITY (wtedy bez Space Cannon).
        # Puste kroki (brak strzelców, walki, lądowania, producentów) są pomijane od razu.
        new_state = tactical.advance_skipping_empty(
            state, ctx.current_grid, ctx.registry
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit_flow(ctx, new_state, "tactical:step")


@router.post("/tactical/step/set", dependencies=[HostOnly], response_model=StateEnvelope)
async def post_set_step(
    request: TacticalStepRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Skok do wskazanego kroku akcji taktycznej (np. pominięcie walki)."""
    try:
        step = TacticalStep(request.step)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Unknown step: {request.step}") from exc
    return await _commit_flow(
        ctx, tactical.set_step(ctx.service.current_state(), step), "tactical:set-step"
    )


@router.post("/tactical/end", response_model=StateEnvelope)
async def post_end_tactical(actor: ActorId, ctx: AppContext = Depends(get_ctx)) -> StateEnvelope:
    """Kończy bieżącą akcję taktyczną (walidowane: nie podczas walki / okien / inwazji)."""
    actor_rules.check(
        ctx.service.current_state(), actor, None, actor_rules.turn_player, "End tactical action"
    )
    return await _commit_flow(
        ctx,
        tactical.end_action(ctx.service.current_state(), ctx.registry),
        "tactical:end",
    )


@router.post("/system/{position}/command-token", dependencies=[HostOnly], response_model=MapView)
async def post_place_command_token(
    position: str, request: CommandTokenRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """God-Mode: kładzie żeton dowodzenia gracza w przestrzeni systemu."""
    new_state = board_edit.place_command_token(
        ctx.service.current_state(), ctx.current_grid, position, request.faction
    )
    return await _commit_map(ctx, new_state, f"cc:add:{position}")


@router.delete("/system/{position}/command-token", dependencies=[HostOnly], response_model=MapView)
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
    actor: ActorId,
    position: str, request: CapturePlanetRequest, ctx: AppContext = Depends(get_ctx)
) -> MapView:
    """Przejęcie kontroli planety po inwazji (nadpisuje poprzedniego właściciela)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Capture planet"
    )
    new_state = tactical.capture_planet(
        ctx.service.current_state(),
        ctx.current_grid,
        position,
        request.planet,
        request.faction,
    )
    return await _commit_map(ctx, new_state, f"capture:{position}:{request.planet}")


@router.get(
    "/tactical/move-range",
    response_model=MoveRangeResponse,
    response_model_by_alias=True,
)
async def get_move_range(
    faction: str,
    gravity_drive: bool = False,
    tempesta: bool = False,
    imperator: bool = False,
    ctx: AppContext = Depends(get_ctx),
) -> MoveRangeResponse:
    """Podgląd zasięgu ruchu: legalne systemy źródłowe do aktywnego (RULES.md 32).

    ``faction`` to klucz tożsamości gracza (jak w tileUnitData). Zwraca mapę
    {pozycja -> ruszalne base_type} przez ``movement.legal_move_sources`` (cienki
    wrapper, zero mutacji). Służy podświetleniu zasięgu/ścieżki na mapie.
    """
    state = ctx.service.current_state()
    player_id = board_edit.resolve_player_id(faction, state)
    sources = movement.legal_move_sources(
        state, ctx.current_grid, ctx.registry, player_id,
        gravity_drive=gravity_drive, tempesta=tempesta, imperator=imperator,
    )
    return MoveRangeResponse(active=state.active_system, sources=sources)


@router.get(
    "/tactical/move-route",
    response_model=MoveRouteResponse,
    response_model_by_alias=True,
)
async def get_move_route(
    faction: str,
    from_position: str,
    via: str = "",
    ctx: AppContext = Depends(get_ctx),
) -> MoveRouteResponse:
    """Podgląd trasy ruchu ze ``from_position`` do aktywnego systemu (RULES.md 32.1, 32.3).

    ``via`` = waypointy rozdzielone przecinkami (trasa przechodzi przez nie po kolei, jak w
    nawigacji). Zwraca trasę, alternatywy, możliwe waypointy, statki ze źródła (czy dolecą i
    ile uniosą) oraz ładunek leżący po drodze. Zero mutacji stanu.
    """
    state = ctx.service.current_state()
    player_id = board_edit.resolve_player_id(faction, state)
    waypoints = [v for v in via.split(",") if v]
    report = movement_route.route_report(
        state,
        ctx.current_grid,
        ctx.registry,
        from_position,
        waypoints,
        player_id,
    )
    return MoveRouteResponse(
        active=report.active,
        route=report.route,
        reason=report.reason,
        alternatives=report.alternatives,
        waypoints=report.waypoints,
        ships=[
            MoveRouteShip(
                baseType=s.base_type,
                count=s.count,
                capacity=s.capacity,
                reachable=s.reachable,
                alone=s.alone,
                withShips=s.with_ships,
                bonusOptions=s.bonus_options,
                bonusMax=s.bonus_max,
                reason=s.reason,
            )
            for s in report.ships
        ],
        riftNodes=report.rift_nodes,
        bonuses=report.bonuses,
        cargo=[
            MoveRouteCargo(
                position=c.position,
                zone=c.zone,
                baseType=c.base_type,
                count=c.count,
                capacityUsed=c.capacity_used,
            )
            for c in report.cargo
        ],
    )


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
    limit = production.production_limit(
        state, ctx.current_grid, ctx.registry, player_id
    )
    return ProductionHelpResponse(
        player_id=help_.player_id,
        available_resources=help_.available_resources,
        production_limit=limit,
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
