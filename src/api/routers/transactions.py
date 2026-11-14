"""Router stołu transakcji + żetonów długu (RULES.md 47.1b, 47.3, 47.4).

Cienka warstwa HTTP: walidacja i zmiana stanu siedzą w ``core.transaction_table``,
``core.transaction`` i ``core.debt``; tu tylko wywołanie, commit + broadcast i mapowanie
``ValueError`` → 422. Każdy gracz kładzie na stół własne rzeczy; dwa Ready = wymiana.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.actor import ActorId, viewer_player
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    DebtTokensRequest,
    StateEnvelope,
    TransactionPartnerView,
    TransactionSideRequest,
    TransactionSideView,
    TransactionStateResponse,
    TransactionTableReadyRequest,
    TransactionTableRequest,
    TransactionTableSideRequest,
    TransactionTableView,
)
from src.core import actor as actor_rules
from src.core import debt, transaction, transaction_table
from src.core.game_state import GameState, TransactionTable
from src.core.hex_grid import HexGrid

router = APIRouter()


async def _commit(ctx: AppContext, new_state: GameState, label: str) -> StateEnvelope:
    """Commit stanu + rozesłanie (ten sam wzorzec co pozostałe routery)."""
    ctx.service.replace_state(new_state, label=label)
    await ctx.service.broadcast()
    await ctx.broadcast_map()
    return ctx.service.envelope()


def _side(req: TransactionSideRequest) -> transaction.TransactionSide:
    return transaction.TransactionSide(
        trade_goods=req.trade_goods,
        commodities=req.commodities,
        promissory_note=req.promissory_note,
        relic_fragments=tuple(req.relic_fragments),
        action_cards=tuple(req.action_cards),
        planets=tuple(req.planets),
        debt_tokens=req.debt_tokens,
        trade_secondary=req.trade_secondary,
        wash=req.wash,
    )


def _side_view(side: transaction.TransactionSide) -> TransactionSideView:
    return TransactionSideView(
        trade_goods=side.trade_goods,
        commodities=side.commodities,
        promissory_note=side.promissory_note,
        relic_fragments=list(side.relic_fragments),
        action_cards=list(side.action_cards),
        relics=list(side.relics),
        secret_objectives=list(side.secret_objectives),
        planets=list(side.planets),
        debt_tokens=side.debt_tokens,
        trade_secondary=side.trade_secondary,
        wash=side.wash,
    )


def _table_view(
    state: GameState, grid: HexGrid, table: TransactionTable, viewer: str
) -> TransactionTableView:
    other = transaction_table.other_of(table, viewer)
    holder = transaction_table.trade_holder(state)
    return TransactionTableView(
        partner=other,
        partner_color=state.players[other].color,
        mine=_side_view(transaction_table.side_of(table, viewer)),
        theirs=_side_view(transaction_table.side_of(table, other)),
        my_ready=viewer in table.ready,
        their_ready=other in table.ready,
        components=transaction.components_allowed(state, grid, viewer, other),
        action_cards=transaction.action_cards_allowed(state, viewer, other),
        extras=transaction.extras_allowed(state, viewer, other),
        trade_holder=holder == viewer,
        trade_partner=holder == other,
        deal_components=transaction.reachable(state, grid, viewer, other),
        prefilled=table.prefilled,
    )


def _label(before: GameState, after: GameState, player: str, partner: str, what: str) -> str:
    """Etykieta commitu: wymiana (``transaction:<partner>``), umowa albo ruch przy stole."""
    active = before.active_player_id
    if active is not None and active in (player, partner):
        other = partner if active == player else player
        if len(after.players[active].transacted_with) > len(
            before.players[active].transacted_with
        ):
            return f"transaction:{other}"
    agreed = (
        what == "ready"
        and transaction_table.find_table(before, player, partner) is not None
        and transaction_table.find_table(after, player, partner) is None
    )
    return f"transaction-table:{'agreed' if agreed else what}:{player}:{partner}"


async def _table_action(
    ctx: AppContext,
    actor: str | None,
    request: TransactionTableRequest,
    what: str,
    fn: Callable[[GameState, HexGrid], GameState],
) -> StateEnvelope:
    state = ctx.service.current_state()
    actor_rules.check(state, actor, request.player_id, None, "Transaction table")
    try:
        new_state = fn(state, ctx.current_grid)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, _label(state, new_state, request.player_id, request.partner_id, what)
    )


@router.get("/transactions/state", response_model=TransactionStateResponse)
async def get_transaction_state(
    request: Request, player: str | None = None, ctx: AppContext = Depends(get_ctx)
) -> TransactionStateResponse:
    """Stoły oglądającego (zawartość tylko dla stron) + gracze, z którymi może usiąść."""
    state = ctx.service.current_state()
    grid = ctx.current_grid
    viewer = viewer_player(request, player) or state.active_player_id
    if viewer is None or viewer not in state.players:
        return TransactionStateResponse()
    tables = [
        _table_view(state, grid, t, viewer) for t in transaction_table.tables_of(state, viewer)
    ]
    done = set(state.players[viewer].transacted_with)
    active = state.active_player_id
    if active is not None and active != viewer and viewer in state.players[active].transacted_with:
        done.add(active)
    partners = [
        TransactionPartnerView(
            player_id=pid,
            color=state.players[pid].color,
            neighbor=transaction.reachable(state, grid, viewer, pid),
            components=transaction.components_allowed(state, grid, viewer, pid),
            done=pid in done,
        )
        for pid in state.players
        if pid != viewer
    ]
    return TransactionStateResponse(
        tables=tables,
        partners=partners,
        my_planets=transaction.tradable_planets(state, viewer),
        deal_players=transaction_table.deal_players(state),
    )


@router.post("/transactions/table/open", response_model=StateEnvelope)
async def post_open_table(
    actor: ActorId, request: TransactionTableRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz siada do stołu z partnerem (każda ze stron może zacząć, RULES.md 47.1b)."""
    return await _table_action(
        ctx, actor, request, "opened",
        lambda s, _g: transaction_table.open_table(s, request.player_id, request.partner_id),
    )


@router.post("/transactions/table/side", response_model=StateEnvelope)
async def post_table_side(
    actor: ActorId, request: TransactionTableSideRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz kładzie swoje rzeczy na stół (zdejmuje oba Ready)."""
    return await _table_action(
        ctx, actor, request, "side",
        lambda s, g: transaction_table.set_side(
            s, g, request.player_id, request.partner_id, _side(request.side)
        ),
    )


@router.post("/transactions/table/ready", response_model=StateEnvelope)
async def post_table_ready(
    actor: ActorId, request: TransactionTableReadyRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz daje (albo cofa) Ready; dwa Ready = wymiana."""
    return await _table_action(
        ctx, actor, request, "ready" if request.ready else "unready",
        lambda s, g: transaction_table.set_ready(
            s, g, request.player_id, request.partner_id, request.ready
        ),
    )


@router.post("/transactions/table/close", response_model=StateEnvelope)
async def post_close_table(
    actor: ActorId, request: TransactionTableRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Gracz wstaje od stołu — nic nie przechodzi."""
    return await _table_action(
        ctx, actor, request, "closed",
        lambda s, _g: transaction_table.close_table(s, request.player_id, request.partner_id),
    )


@router.post("/debt/give", response_model=StateEnvelope)
async def post_give_debt_tokens(
    actor: ActorId,
    request: DebtTokensRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Wystawca oddaje posiadaczowi żetony długu (zasada stołu, RULES.md 47.3)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.issuer_id, None, "Give debt tokens"
    )
    try:
        new_state = debt.give_debt_tokens(
            ctx.service.current_state(), request.issuer_id, request.holder_id, request.count
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, f"debt:give:{request.issuer_id}->{request.holder_id}"
    )


@router.post("/debt/return", response_model=StateEnvelope)
async def post_return_debt_tokens(
    actor: ActorId,
    request: DebtTokensRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Posiadacz zwraca wystawcy jego żetony długu (debt) (dług spłacony/odpuszczony)."""
    actor_rules.check(
        ctx.service.current_state(), actor, request.holder_id, None, "Return debt tokens"
    )
    try:
        new_state = debt.return_debt_tokens(
            ctx.service.current_state(), request.holder_id, request.issuer_id, request.count
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(
        ctx, new_state, f"debt:return:{request.holder_id}->{request.issuer_id}"
    )
