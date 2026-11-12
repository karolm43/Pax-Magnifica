"""Router transakcji między graczami + żetonów długu (RULES.md 47).

Cienka warstwa HTTP: walidacja i zmiana stanu siedzą w ``core.transaction`` oraz
``core.debt``; tu tylko wywołanie, commit + broadcast i mapowanie ``ValueError`` → 422.
Transakcja wymaga zgody partnera (RULES.md 47.1a): ``propose`` → ``respond`` / ``cancel``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.actor import ActorId, viewer_player
from src.api.context import AppContext, get_ctx
from src.api.schemas import (
    DebtTokensRequest,
    StateEnvelope,
    TransactionCancelRequest,
    TransactionOfferView,
    TransactionPartnerView,
    TransactionRequest,
    TransactionRespondRequest,
    TransactionSideRequest,
    TransactionSideView,
    TransactionStateResponse,
)
from src.core import actor as actor_rules
from src.core import debt, transaction
from src.core.game_state import GameState
from src.core.neighbors import neighbors_of

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
    )


def _side_view(side: transaction.TransactionSide) -> TransactionSideView:
    return TransactionSideView(
        trade_goods=side.trade_goods,
        commodities=side.commodities,
        promissory_note=side.promissory_note,
        relic_fragments=list(side.relic_fragments),
        action_cards=list(side.action_cards),
    )


def _answer_label(before: GameState, after: GameState, partner: str) -> str:
    """Etykieta commitu po odpowiedzi: wymiana (``transaction:<partner>``) albo odrzucenie."""
    active = before.active_player_id
    if active is not None and len(after.players[active].transacted_with) > len(
        before.players[active].transacted_with
    ):
        return f"transaction:{partner}"
    return f"transaction-offer:declined:{partner}"


def _offer_partner(state: GameState) -> list[str | None]:
    offer = state.transaction_offer
    return [offer.partner] if offer is not None else []


def _offer_proposer(state: GameState) -> list[str | None]:
    offer = state.transaction_offer
    return [offer.proposer] if offer is not None else []


@router.get("/transactions/state", response_model=TransactionStateResponse)
async def get_transaction_state(
    request: Request, player: str | None = None, ctx: AppContext = Depends(get_ctx)
) -> TransactionStateResponse:
    """Propozycja w toku (zawartość tylko dla jej stron) + partnerzy aktywnego gracza."""
    state = ctx.service.current_state()
    viewer = viewer_player(request, player)
    offer = transaction.pending_offer(state)
    offer_view: TransactionOfferView | None = None
    if offer is not None:
        give, receive = transaction.offer_sides(offer)
        party = viewer is None or viewer in (offer.proposer, offer.partner)
        offer_view = TransactionOfferView(
            proposer=offer.proposer,
            partner=offer.partner,
            proposer_color=state.players[offer.proposer].color,
            partner_color=state.players[offer.partner].color,
            give=_side_view(give) if party else None,
            receive=_side_view(receive) if party else None,
        )
    partners: list[TransactionPartnerView] = []
    active = state.active_player_id
    if active is not None and active in state.players:
        near = neighbors_of(active, state, ctx.current_grid)
        done = set(state.players[active].transacted_with)
        for pid in transaction.trade_partners(state, ctx.current_grid, active):
            partners.append(
                TransactionPartnerView(
                    player_id=pid,
                    color=state.players[pid].color,
                    neighbor=pid in near,
                    action_cards=transaction.action_cards_allowed(state, active, pid),
                    done=pid in done,
                )
            )
    return TransactionStateResponse(offer=offer_view, partners=partners)


@router.post("/transactions/propose", response_model=StateEnvelope)
async def post_propose_transaction(
    actor: ActorId,
    request: TransactionRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Aktywny gracz proponuje transakcję; wymiana dopiero po zgodzie partnera (RULES.md 47.1a)."""
    state = ctx.service.current_state()
    actor_rules.check(state, actor, request.player_id, actor_rules.turn_player, "Transaction")
    try:
        new_state = transaction.propose_transaction(
            state,
            ctx.current_grid,
            request.partner_id,
            _side(request.give),
            _side(request.receive),
            request.player_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if new_state.transaction_offer is None:  # partner-bot odpowiedział od razu
        return await _commit(ctx, new_state, _answer_label(state, new_state, request.partner_id))
    return await _commit(ctx, new_state, f"transaction-offer:proposed:{request.partner_id}")


@router.post("/transactions/respond", response_model=StateEnvelope)
async def post_respond_transaction(
    actor: ActorId,
    request: TransactionRespondRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Partner przyjmuje albo odrzuca propozycję transakcji (RULES.md 47.1a)."""
    state = ctx.service.current_state()
    actor_rules.check(state, actor, request.player_id, _offer_partner, "Answer the transaction")
    offer = state.transaction_offer
    responder = request.player_id or (offer.partner if offer is not None else "")
    try:
        new_state = transaction.respond_to_offer(
            state, ctx.current_grid, responder, accept=request.accept
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, _answer_label(state, new_state, responder))


@router.post("/transactions/cancel", response_model=StateEnvelope)
async def post_cancel_transaction(
    actor: ActorId,
    request: TransactionCancelRequest, ctx: AppContext = Depends(get_ctx)
) -> StateEnvelope:
    """Proponujący wycofuje propozycję transakcji przed odpowiedzią partnera."""
    state = ctx.service.current_state()
    actor_rules.check(state, actor, request.player_id, _offer_proposer, "Withdraw the offer")
    offer = state.transaction_offer
    proposer = request.player_id or (offer.proposer if offer is not None else "")
    partner = offer.partner if offer is not None else ""
    try:
        new_state = transaction.cancel_offer(state, proposer)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await _commit(ctx, new_state, f"transaction-offer:cancelled:{partner}")


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
