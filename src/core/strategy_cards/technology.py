"""Technology (inicjatywa 7, base) — RULES.md 49.2, R_technology_sc + R_technology.

Primary: zbadaj 1 technologię (za darmo); potem MOŻESZ zbadać drugą, wydając 6 zasobów.
Secondary (1 żeton ze strategy pool): wydaj 4 zasoby i zbadaj 1 technologię. Prerekwizyty
obowiązują zawsze; druga technologia primary może korzystać z pierwszej. Planety wyczerpane
na specjalność (skip prerekwizytu) nie mogą jednocześnie płacić zasobami - są już wyczerpane.
"""

from __future__ import annotations

from typing import Any

from src.core import ability_notes, exhaust, payment, rules_hooks, technology
from src.core.game_state import GameState
from src.core.payment import parse_payment, ready_planet_values
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
    cost = _card_cost(state, player_id, cost)
    tech_id = payload.get("tech")
    if not isinstance(tech_id, str):
        raise ValueError("Choose a technology to research.")
    skips = str_list(payload, "skips")
    plan = technology.plan_research(state, ctx.registry, player_id, tech_id, skips)
    compound = payload.get("compound_planet")
    if cost > 0 and isinstance(compound, str) and compound:
        # Specialist Compounds: planeta ze specjalnością zamiast zasobów (RULES.md 62.3).
        technology.validate_specialty_payment(state, ctx.registry, player_id, plan, compound)
        exhaust.exhaust_planets(state, player_id, (compound,))
        cost = 0
    elif cost > 0:
        # Centralna zapłata (zniżka Doctor Sucaban, ślad dla okien po zapłacie - RULES.md 62.3).
        planets, trade_goods = parse_payment(payload)
        technology.pay_research(
            state, ctx.registry, player_id, cost, planets, trade_goods,
            skip_planets=plan.exhaust_planets,
        )
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


def as_primary(state: GameState, player_id: str) -> bool:
    """Czy secondary gracza rozstrzyga się jak primary (hook PERMIT, Brilliant - RULES.md 62.3)."""
    return rules_hooks.permits(
        rules_hooks.POINT_STRATEGY_SECONDARY_AS_PRIMARY, state, player_id,
        {"initiative": INITIATIVE},
    )


def _secondary(
    state: GameState, ctx: CardContext, player_id: str, payload: dict[str, Any]
) -> None:
    if as_primary(state, player_id):
        # Primary zamiast secondary: 1 technologia za darmo, potem opcjonalnie druga za 6.
        ability_notes.note_point(
            state, player_id, rules_hooks.POINT_STRATEGY_SECONDARY_AS_PRIMARY,
            "resolved the Technology primary ability instead of the secondary",
        )
        if payload.get("tech") is not None:
            _research_with_cost(state, ctx, player_id, payload, 0)
        second = payload.get("second")
        if isinstance(second, dict) and second.get("tech") is not None:
            _research_with_cost(state, ctx, player_id, second, SECOND_RESEARCH_COST)
        return
    _research_with_cost(state, ctx, player_id, payload, SECONDARY_COST)


def _card_cost(state: GameState, player_id: str, cost: int) -> int:
    """Koszt badania kartą Technology (Minister of Sciences: bez zasobów - RULES.md 51.6)."""
    if cost > 0 and rules_hooks.permits(rules_hooks.POINT_TECHNOLOGY_SC_FREE, state, player_id):
        return 0
    return cost


def research_options(
    state: GameState, ctx: CardContext, player_id: str, cost: int
) -> dict[str, Any]:
    """Wszystko, czego okno badania potrzebuje (drzewo, specjalności, płatność, koszt)."""
    cost = _card_cost(state, player_id, cost)
    player = state.players[player_id]
    return {
        "tree": technology.tree_view(state, ctx.registry, player_id),
        "owned_colors": dict(technology.owned_colors(state, ctx.registry, player_id)),
        # Przełom frakcji: synergia dwóch kolorów, aktywna tylko gdy przełom odblokowany.
        "breakthrough": technology.breakthrough_view(state, ctx.registry, player_id),
        "specialties": technology.specialty_planets(state, ctx.registry, player_id),
        "aida": technology.aida_ready(state, player_id),
        # Gotowe relikty ignorujące 1 prerekwizyt (Prophet's Tears) - skip ``relic:<id>``.
        "relic_skips": technology.ignore_prerequisite_relics(state, player_id),
        "planets": ready_planet_values(state, ctx.registry, player_id, "resources"),
        "trade_goods": player.trade_goods,
        "trade_good_value": payment.trade_good_value(state, player_id),
        # Zniżka z Doctor Sucaban (już odjęta od ``cost``) i planety płacące specjalnością.
        "discount": min(cost, technology.research_discount(state, player_id)) if cost else 0,
        "compound_planets": (
            technology.specialty_payment_planets(state, ctx.registry, player_id) if cost else {}
        ),
        "cost": max(0, cost - technology.research_discount(state, player_id)),
        "needs_input": True,
    }


def _options(
    state: GameState,
    ctx: CardContext,
    player_id: str,
    step: str | None,
    draft: Draft,
) -> dict[str, Any]:
    brilliant = step is None and as_primary(state, player_id)
    default = 0 if brilliant else SECONDARY_COST
    cost = {STEP_FREE: 0, STEP_PAID: SECOND_RESEARCH_COST}.get(step or "", default)
    result = research_options(state, ctx, player_id, cost)
    result["researched"] = list(draft.get("researched", []))
    if brilliant:
        # Brilliant: secondary jak primary - druga technologia za 6 zasobów w tym samym oknie.
        result["as_primary"] = True
        result["second_cost"] = SECOND_RESEARCH_COST
        result["second"] = research_options(state, ctx, player_id, SECOND_RESEARCH_COST)
    return result


SPEC = CardSpec(
    primary_steps=(STEP_FREE, STEP_PAID),
    on_step=_on_step,
    secondary=_secondary,
    secondary_costs_token=True,
    options=_options,
)
