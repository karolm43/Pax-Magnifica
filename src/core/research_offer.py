"""Badanie z komponentu jako decyzja w oknie badania (RULES.md 62.3, 53 - Focused Research).

Komponent „spend X … to research 1 technology” (karta akcji, frontier) NIE pyta o technologię
przy zagraniu: po zagraniu powstaje obowiązkowa decyzja gracza z wejściem ``research``, którą UI
pokazuje tym samym pełnym oknem badania co karta Technology (drzewo + płatność). Dopóki ta decyzja
czeka, gracz „wydaje zasoby na badanie” - zdolności z tym oknem (Doctor Sucaban) działają PRZED
zapłatą i obniżają koszt (zniżka ``technology.RESEARCH_DISCOUNT``), a nie jako zwrot po fakcie.

Marker w ``PendingOffer.ctx``: ``research_cost`` (koszt przed zniżką) i ``trade_goods_only``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from src.core import economy, offer_inputs, technology
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

RESEARCH_KEY = "research"
COST_KEY = "research_cost"
TG_ONLY_KEY = "trade_goods_only"

# Dostawcy MOŻLIWEJ zniżki przed zapłatą (np. Doctor Sucaban: tyle, ile piechoty ma płacący).
# HOOK-CANDIDATE: zniżka należy do komponentu INNEGO gracza niż płacący, więc punkt MODIFY
# (źródła płacącego) jej nie widzi; rejestracja w module frakcji (``hooks/factions/jolnar.py``).
DiscountFn = Callable[[GameState, StaticDataRegistry, str], int]
_discounts: list[DiscountFn] = []


def register_potential_discount(fn: DiscountFn) -> DiscountFn:
    """Rejestruje dostawcę możliwej zniżki badania (do bramki zagrywalności)."""
    _discounts.append(fn)
    return fn


def potential_discount(state: GameState, registry: StaticDataRegistry, payer: str) -> int:
    """Najwyższa możliwa zniżka badania płacącego: już przyznana + dostępne zdolności."""
    granted = technology.research_discount(state, payer)
    offered = max((fn(state, registry, payer) for fn in _discounts), default=0)
    return granted + offered


def can_afford_trade_goods(
    state: GameState, registry: StaticDataRegistry, player_id: str, cost: int
) -> bool:
    """Czy gracz pokryje koszt w TG (Focused Research), licząc możliwą zniżkę przed zapłatą."""
    need = max(0, cost - potential_discount(state, registry, player_id))
    return economy.spendable_trade_goods(state, player_id) >= need


def research_input(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    cost: int,
    *,
    trade_goods_only: bool = False,
    label: str = "Research 1 technology",
) -> offer_inputs.Input:
    """Wejście ``research`` z pełnym widokiem okna badania (koszt już po zniżce)."""
    from src.core.strategy_cards.technology import research_view  # lokalnie: bez cyklu importów

    view = research_view(state, registry, player_id, cost, trade_goods_only=trade_goods_only)
    unit = "trade goods" if trade_goods_only else "resources"
    return offer_inputs.research(
        RESEARCH_KEY, label, view, hint=f"Costs {view['cost']} {unit}."
    )


def offer_ctx(cost: int, *, trade_goods_only: bool = False) -> dict[str, Any]:
    """Kontekst zdarzenia tworzącego decyzję badania (marker dla ``pending_payer``)."""
    return {COST_KEY: cost, TG_ONLY_KEY: trade_goods_only}


def pending_payer(state: GameState) -> str | None:
    """Gracz, którego decyzja badania z komponentu czeka (płaci TERAZ), albo ``None``."""
    for offer in state.pending_offers:
        if COST_KEY in offer.ctx:
            return offer.player_id
    return None


def resolve(
    state: GameState, registry: StaticDataRegistry, player_id: str, ctx: Mapping[str, Any]
) -> str | None:
    """Rozstrzyga odpowiedź z okna badania (MUTUJE klon). Zwraca id technologii albo ``None``,
    gdy gracz zrezygnował (``tech: None``) - komponent i tak został zużyty.

    Raises:
        ValueError: Zły format, brak prerekwizytów albo za mało zasobów / TG.
    """
    params = ctx.get("params") or {}
    payload = params.get(RESEARCH_KEY)
    if not isinstance(payload, Mapping):
        raise ValueError("Choose a technology to research.")
    tech_id = payload.get("tech")
    if tech_id is None:
        technology.consume_research_discount(state, player_id)  # niewykorzystana zniżka przepada
        return None
    if not isinstance(tech_id, str):
        raise ValueError("Choose a technology to research.")
    skips = _str_list(payload.get("skips"))
    plan = technology.plan_research(state, registry, player_id, tech_id, skips)
    trade_goods_only = bool(ctx.get(TG_ONLY_KEY))
    planets = [] if trade_goods_only else _str_list(payload.get("planets"))
    trade_goods = payload.get("trade_goods", 0)
    if not isinstance(trade_goods, int) or isinstance(trade_goods, bool):
        raise ValueError("'trade_goods' must be a number.")
    technology.pay_research(
        state, registry, player_id, int(ctx.get(COST_KEY, 0)), planets, trade_goods,
        skip_planets=plan.exhaust_planets, trade_goods_only=trade_goods_only,
    )
    technology.apply_research(state, player_id, plan)
    return tech_id


def _str_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        raise ValueError("Expected a list of ids.")
    return list(raw)
