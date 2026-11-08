"""Technology (inicjatywa 7, base) — RULES.md 49.2, R_technology_sc + R_technology.

Primary: zbadaj 1 technologię (za darmo); potem MOŻESZ zbadać drugą, wydając 6 zasobów.
Secondary (1 żeton ze strategy pool): wydaj 4 zasoby i zbadaj 1 technologię. Prerekwizyty
obowiązują zawsze; druga technologia primary może korzystać z pierwszej. Planety wyczerpane
na specjalność (skip prerekwizytu) nie mogą jednocześnie płacić zasobami - są już wyczerpane.
"""

from __future__ import annotations

from typing import Any

from src.core import technology
from src.core.game_state import GameState
from src.core.payment import apply_payment, parse_payment, ready_planet_values, validate_payment
from src.core.strategy_cards.base import CardContext, CardSpec, Draft
from src.core.strategy_cards.common import str_list

INITIATIVE = 7
SECOND_RESEARCH_COST = 6  # primary: „spending six resources"
SECONDARY_COST = 4  # secondary: „one command token … and four resources"

STEP_FREE = "research"
STEP_PAID = "research_paid"


def _research_with_cost(
    state: GameState, ctx: CardContext, player_id: str, payload: dict[str, Any], cost: int
) -> str:
    """Bada technologię z payloadu i pobiera ``cost`` zasobów (mutuje klon). Zwraca id."""
    tech_id = payload.get("tech")
    if not isinstance(tech_id, str):
        raise ValueError("Choose a technology to research.")
    skips = str_list(payload, "skips")
    plan = technology.plan_research(state, ctx.registry, player_id, tech_id, skips)
    if cost > 0:
        planets, trade_goods = parse_payment(payload)
        overlap = set(planets) & set(plan.exhaust_planets)
        if overlap:
            raise ValueError(
                "A planet exhausted for its technology specialty cannot also pay resources: "
                + ", ".join(sorted(overlap))
            )
        paid = validate_payment(state, ctx.registry, player_id, "resources", planets, trade_goods)
        if paid < cost:
            raise ValueError(f"Spend at least {cost} resources (you chose {paid}).")
        apply_payment(state, player_id, planets, trade_goods)
    technology.apply_research(state, player_id, plan)
    return tech_id


def _on_step(
    state: GameState,
    ctx: CardContext,
    owner_id: str,
    step: str,
    draft: Draft,
    payload: dict[str, Any],
) -> None:
    if step == STEP_FREE:
        if payload.get("tech") is None:
            draft["researched"] = []  # „can research" - wolno zrezygnować
            return
        draft["researched"] = [_research_with_cost(state, ctx, owner_id, payload, 0)]
    elif step == STEP_PAID:
        if payload.get("tech") is None:
            return  # druga technologia jest opcjonalna
        tech_id = _research_with_cost(state, ctx, owner_id, payload, SECOND_RESEARCH_COST)
        draft["researched"] = [*draft.get("researched", []), tech_id]
    else:
        raise ValueError(f"Unknown Technology step: {step}")


def _secondary(
    state: GameState, ctx: CardContext, player_id: str, payload: dict[str, Any]
) -> None:
    _research_with_cost(state, ctx, player_id, payload, SECONDARY_COST)


def research_options(
    state: GameState, ctx: CardContext, player_id: str, cost: int
) -> dict[str, Any]:
    """Wszystko, czego okno badania potrzebuje (drzewo, specjalności, płatność, koszt)."""
    player = state.players[player_id]
    return {
        "tree": technology.tree_view(state, ctx.registry, player_id),
        "owned_colors": dict(technology.owned_colors(state, ctx.registry, player_id)),
        # Przełom frakcji: synergia dwóch kolorów, aktywna tylko gdy przełom odblokowany.
        "breakthrough": technology.breakthrough_view(state, ctx.registry, player_id),
        "specialties": technology.specialty_planets(state, ctx.registry, player_id),
        "aida": technology.aida_ready(state, player_id),
        "planets": ready_planet_values(state, ctx.registry, player_id, "resources"),
        "trade_goods": player.trade_goods,
        "cost": cost,
        "needs_input": True,
    }


def _options(
    state: GameState,
    ctx: CardContext,
    player_id: str,
    step: str | None,
    draft: Draft,
) -> dict[str, Any]:
    cost = {STEP_FREE: 0, STEP_PAID: SECOND_RESEARCH_COST}.get(step or "", SECONDARY_COST)
    result = research_options(state, ctx, player_id, cost)
    result["researched"] = list(draft.get("researched", []))
    return result


SPEC = CardSpec(
    primary_steps=(STEP_FREE, STEP_PAID),
    on_step=_on_step,
    secondary=_secondary,
    secondary_costs_token=True,
    options=_options,
)
