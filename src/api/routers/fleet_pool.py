"""Router fleet pool (RULES.md 42): ostrzeżenie o przekroczeniu puli i usunięcie nadwyżki.

Cienka warstwa nad ``core.fleet_pool``. ``GET /tactical/fleet-pool`` zwraca stan puli:
- gdy trwa okno ``FLEET_POOL`` — dla bieżącego respondenta (``active=True``, modal wymuszony),
- w przeciwnym razie — dla aktywnego gracza w aktywnym systemie (``active=False``), żeby UI
  mogło OSTRZEC (produkcja, ruch), zanim nadwyżka zostanie wymuszona.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.api.actor import ActorId
from src.api.context import AppContext, get_ctx
from src.api.schemas import BattleLossItem, StateEnvelope
from src.api.web_data import entity_key_map
from src.core import actor as actor_rules
from src.core import board_edit, capacity, fleet_pool, floating_structures
from src.core.game_state import WindowType
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

router = APIRouter()


class FleetShipView(BaseModel):
    """Statek liczony do puli: typ, nazwa wariantu, liczba."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    count: int


class CapacityInfo(BaseModel):
    """Pojemność gracza w przestrzeni systemu (RULES.md 39.6) - do prognozy w produkcji.

    ``fighter_only`` = miejsca doków na planetach TYLKO dla myśliwców (np. „do 3 myśliwców nie
    liczy się do capacity"), ``used`` = zajęta pojemność ładunku (myśliwce, piechota, mechy).
    """

    model_config = ConfigDict(populate_by_name=True)

    general: int = 0
    fighter_only: int = Field(default=0, serialization_alias="fighterOnly")
    fighters: int = 0  # myśliwce w przestrzeni (sztuki)
    fighter_cost: int = Field(default=1, serialization_alias="fighterCost")
    other_load: int = Field(default=0, serialization_alias="otherLoad")  # reszta ładunku
    excess: int = 0
    # Fighter II: myśliwce ponad capacity liczą się do fleet pool (a nie są usuwane z capacity);
    # ``fleet_fighters`` = ile ich już teraz leży w puli.
    fighters_to_fleet: bool = Field(default=False, serialization_alias="fightersToFleet")
    fleet_fighters: int = Field(default=0, serialization_alias="fleetFighters")


class FleetPoolView(BaseModel):
    """Pula floty gracza w systemie: żetony, statki, nadwyżka i podpowiedź „Auto"."""

    model_config = ConfigDict(populate_by_name=True)

    active: bool  # True = trwa okno FLEET_POOL (usunięcie wymuszone)
    known: bool = False  # False = brak aktywnego systemu / gracza
    position: str | None = None
    player: str | None = None  # klucz encji (kolor/frakcja)
    player_id: str | None = Field(default=None, serialization_alias="playerId")
    pool: int = 0
    # Limit puli nie obowiązuje (np. bohater Letnev do końca rundy) — UI nie rysuje kratek.
    unlimited: bool = False
    total: int = 0
    excess: int = 0
    ships: list[FleetShipView] = Field(default_factory=list)
    suggestion: dict[str, int] = Field(default_factory=dict)
    remaining: int = 0  # ilu graczy czeka w kolejce (łącznie z bieżącym)
    capacity: CapacityInfo = Field(default_factory=CapacityInfo)
    # Siła naziemna-statek (Eidolon Maximum): ``fleet`` albo ``capacity`` (wybór gracza).
    ground_ship_pool: str = Field(default="fleet", serialization_alias="groundShipPool")


class FleetPoolResolveRequest(BaseModel):
    """Statki wracające do rezerwy (dokładnie tyle, ile trzeba)."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    remove: list[BattleLossItem] = Field(default_factory=list)


@router.get("/tactical/fleet-pool", response_model=FleetPoolView, response_model_by_alias=True)
async def get_fleet_pool(ctx: AppContext = Depends(get_ctx)) -> FleetPoolView:
    """Stan fleet pool: respondent okna albo aktywny gracz w aktywnym systemie."""
    state = ctx.service.current_state()
    window = state.pending_window
    in_window = (
        window is not None
        and window.window_type is WindowType.FLEET_POOL
        and window.current_responder is not None
    )
    pid: str | None
    position: str | None
    if in_window and window is not None:
        pid = window.current_responder
        position = str(window.context.get("position", ""))
        remaining = len(window.queue) - window.cursor
    else:
        pid = state.active_player_id
        position = state.active_system
        remaining = 0
    if pid is None or position is None or pid not in state.players:
        return FleetPoolView(active=False)
    report = fleet_pool.fleet_report(state, position, pid, ctx.registry)
    cap = capacity.capacity_report(state, ctx.registry, position, pid)
    fighters = cap.cargo.get("fighter", 0)
    fighter_cost = cap.cost.get("fighter", 1)
    return FleetPoolView(
        active=bool(in_window),
        known=True,
        position=position,
        player=entity_key_map(state).get(pid, pid),
        player_id=pid,
        pool=report.pool,
        unlimited=report.unlimited,
        total=report.total,
        excess=report.excess,
        ships=[
            FleetShipView(
                base_type=bt,
                async_id=ASYNC_ID_BY_BASE_TYPE.get(bt, bt),
                name=fleet_pool.unit_name(state, ctx.registry, pid, bt),
                count=n,
            )
            for bt, n in report.ships.items()
        ],
        suggestion=fleet_pool.auto_removal(state, ctx.registry, pid, report),
        remaining=remaining,
        ground_ship_pool=state.players[pid].ground_ship_pool,
        capacity=CapacityInfo(
            general=cap.general,
            fighter_only=cap.fighter_only,
            fighters=fighters,
            fighter_cost=fighter_cost,
            other_load=cap.used - fighters * fighter_cost,
            excess=cap.excess,
            fighters_to_fleet=cap.fighters_overflow_to_fleet,
            fleet_fighters=cap.fleet_fighters,
        ),
    )


@router.post("/tactical/fleet-pool/resolve", response_model=StateEnvelope)
async def post_fleet_pool_resolve(
    actor: ActorId,
    request: FleetPoolResolveRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz zwraca nadwyżkę statków do rezerwy (RULES.md 42)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Resolve fleet pool"
    )
    state = ctx.service.current_state()
    remove: dict[str, int] = {}
    for item in request.remove:
        if item.count > 0:
            remove[item.base_type] = remove.get(item.base_type, 0) + item.count
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = fleet_pool.resolve_fleet_pool(state, ctx.registry, player_id, remove)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label=f"fleet-pool:{player_id}")
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


class GroundShipPoolRequest(BaseModel):
    """Wybór puli dla siły naziemnej-statku w przestrzeni: ``fleet`` | ``capacity`` | ``auto``."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    pool: str


@router.post("/tactical/fleet-pool/ground-ship-pool", response_model=StateEnvelope)
async def post_ground_ship_pool(
    actor: ActorId,
    request: GroundShipPoolRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Eidolon Maximum liczy się albo do pojemności, albo do puli floty (F_naaz_rokha 3)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.faction, None, "Choose ground ship pool"
    )
    state = ctx.service.current_state()
    try:
        player_id = board_edit.resolve_player_id(request.faction, state)
        new_state = floating_structures.choose_ground_ship_pool(state, player_id, request.pool)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    ctx.service.replace_state(new_state, label=f"ground-ship-pool:{player_id}")
    await ctx.service.broadcast()
    return ctx.service.envelope()
