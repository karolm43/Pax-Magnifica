"""Wydanie kosztu celów typu „Spend…" przy ich zdobywaniu (RULES.md 41.4).

R_objective_cards: cel wymagający wydania zasobów/żetonów trzeba opłacić w chwili
punktowania (w fazie statusu albo przy Imperial). Gracz może JAWNIE wskazać płatność
(``ObjectivePayment``: planety, trade goods, pule żetonów, karty, fragmenty); bez wskazania
silnik dobiera ją sam (``auto_payment``): najpierw wyczerpuje planety, brak dopłaca trade goods;
żetony dowodzenia schodzą najpierw z puli taktycznej, potem strategicznej.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.core import card_draw, command_tokens, economy, relic_fragments
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.objective_progress import (
    SPEND_OBJECTIVES,
    View,
    mixed_spend_plan,
    threshold,
)
from src.core.payment import apply_payment, ready_planet_values, validate_payment
from src.core.planet_stats import effective_planets, planet_stats
from src.core.registry import StaticDataRegistry

_TRADE_GOODS = {"trade_routes", "centralize_trade"}
_TOKENS = {"lead", "galvanize"}
_RESOURCES = {"monument", "golden_age"}
_INFLUENCE = {"sway_council", "manipulate_law"}
_MIXED = {"amass_wealth": 3, "vast_reserves": 6}


class ObjectivePayment(BaseModel):
    """Płatność za cel „Spend…": które zasoby gracz wydaje (puste pola = nie dotyczy celu)."""

    model_config = ConfigDict(extra="forbid")

    # Cele „X resources/influence": planety do wyczerpania + trade goods w zastępstwie.
    planets: list[str] = Field(default_factory=list)
    trade_goods: int = 0
    # Cele mieszane (Amass Wealth / Vast Reserves): planety osobno na zasoby i na wpływ.
    resource_planets: list[str] = Field(default_factory=list)
    influence_planets: list[str] = Field(default_factory=list)
    # Cele z żetonami dowodzenia: ile z której puli (tactical / fleet / strategic).
    tokens: dict[str, int] = Field(default_factory=dict)
    # Fire Shield Network: odrzucane karty akcji; Destroy Heretical Works: purgowane fragmenty.
    cards: list[str] = Field(default_factory=list)
    fragments: list[str] = Field(default_factory=list)


def spend_kind(objective_id: str) -> str | None:
    """Rodzaj kosztu celu: trade_goods / tokens / resources / influence / mixed / cards /
    fragments; ``None`` gdy cel niczego nie kosztuje."""
    if objective_id not in SPEND_OBJECTIVES:
        return None
    if objective_id in _TRADE_GOODS:
        return "trade_goods"
    if objective_id in _TOKENS:
        return "tokens"
    if objective_id == "dhw":
        return "fragments"
    if objective_id == "fsn":
        return "cards"
    if objective_id in _MIXED:
        return "mixed"
    return "resources" if objective_id in _RESOURCES else "influence"


def _pick_planets(
    candidates: list[tuple[str, int]], need: int
) -> tuple[list[str], int]:
    """Dobiera planety (id, wartość) tak, by pokryć ``need``; zwraca (id…, reszta do TG)."""
    chosen: list[str] = []
    remaining = need
    pool = sorted((c for c in candidates if c[1] > 0), key=lambda c: -c[1])
    while remaining > 0 and pool:
        fitting = [c for c in pool if c[1] <= remaining]
        pick = fitting[0] if fitting else min(pool, key=lambda c: c[1])
        pool.remove(pick)
        chosen.append(pick[0])
        remaining -= pick[1]
    return chosen, max(remaining, 0)


def auto_payment(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    objective_id: str,
) -> ObjectivePayment:
    """Płatność dobrana przez silnik (domyślna i podpowiedź w UI).

    Raises:
        ValueError: Gdy gracza nie stać.
    """
    kind = spend_kind(objective_id)
    player = state.players[player_id]
    goal = threshold(objective_id, state)
    if kind is None or kind == "trade_goods":
        return ObjectivePayment(trade_goods=goal if kind else 0)
    if kind == "tokens":
        from_tactical = min(command_tokens.pool_count(state, player_id, "tactical"), goal)
        return ObjectivePayment(
            tokens={"tactical": from_tactical, "strategic": goal - from_tactical}
        )
    if kind == "fragments":
        return ObjectivePayment(fragments=list(player.relic_fragments[:goal]))
    if kind == "cards":
        return ObjectivePayment(cards=list(player.private.action_cards[:goal]))
    ready = View(state, registry, grid, player_id).ready_planets()
    if kind == "mixed":
        plan = mixed_spend_plan(
            ready, effective_planets(state, registry), player.trade_goods, _MIXED[objective_id]
        )
        if plan is None:
            raise ValueError("You cannot afford this objective.")
        res_planets, inf_planets, tg_spent = plan
        return ObjectivePayment(
            resource_planets=res_planets, influence_planets=inf_planets, trade_goods=tg_spent
        )
    values = [
        (p, (stats.resources if kind == "resources" else stats.influence))
        for p in ready
        if (stats := planet_stats(state, registry, p)) is not None
    ]
    spent, rest = _pick_planets(values, goal)
    if rest > player.trade_goods:
        raise ValueError("You cannot afford this objective.")
    return ObjectivePayment(planets=spent, trade_goods=rest)


def _validate_tokens(
    state: GameState, player_id: str, tokens: dict[str, int], goal: int
) -> None:
    for pool, amount in tokens.items():
        if pool not in command_tokens.POOLS:
            raise ValueError(f"Unknown command token pool: {pool}.")
        if amount < 0:
            raise ValueError("The number of command tokens cannot be negative.")
        if amount > command_tokens.pool_count(state, player_id, pool):
            raise ValueError(f"Not enough command tokens in the {pool} pool.")
    if sum(tokens.values()) != goal:
        raise ValueError(f"You must spend exactly {goal} command tokens.")


def _validate_mixed(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    payment: ObjectivePayment,
    goal: int,
) -> None:
    if set(payment.resource_planets) & set(payment.influence_planets):
        raise ValueError("A planet cannot pay for both resources and influence.")
    resources = validate_payment(
        state, registry, player_id, "resources", payment.resource_planets, 0
    )
    influence = validate_payment(
        state, registry, player_id, "influence", payment.influence_planets, 0
    )
    needed = goal + max(0, goal - resources) + max(0, goal - influence)
    if payment.trade_goods < needed:
        raise ValueError(
            f"Payment too low: {payment.trade_goods} trade goods, {needed} needed."
        )
    if payment.trade_goods > economy.spendable_trade_goods(state, player_id):
        raise ValueError("Not enough trade goods.")


def _validate(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    objective_id: str,
    kind: str,
    payment: ObjectivePayment,
) -> None:
    """Sprawdza jawną płatność gracza względem kosztu celu (``ValueError`` = 422)."""
    goal = threshold(objective_id, state)
    if kind == "tokens":
        _validate_tokens(state, player_id, payment.tokens, goal)
    elif kind == "fragments":
        if len(payment.fragments) != goal or len(set(payment.fragments)) != goal:
            raise ValueError(f"You must purge exactly {goal} relic fragments.")
    elif kind == "cards":
        if len(payment.cards) != goal or len(set(payment.cards)) != goal:
            raise ValueError(f"You must discard exactly {goal} action cards.")
    elif kind == "mixed":
        _validate_mixed(state, registry, player_id, payment, goal)
    elif kind in ("resources", "influence"):
        total = validate_payment(
            state, registry, player_id, kind, payment.planets, payment.trade_goods  # type: ignore[arg-type]
        )
        if total < goal:
            raise ValueError(f"Payment too low: {total}/{goal} {kind}.")


def pay_for_objective(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    objective_id: str,
    payment: ObjectivePayment | None = None,
) -> GameState:
    """Zwraca NOWY stan po opłaceniu celu; cele bez kosztu zwraca bez zmian (klon).

    ``payment=None`` => płatność dobiera silnik (``auto_payment``); w przeciwnym razie
    wykonuje się dokładnie wskazana płatność gracza (po walidacji).

    Raises:
        ValueError: Gdy gracza nie stać albo wskazana płatność jest nielegalna.
    """
    new_state = state.clone()
    kind = spend_kind(objective_id)
    if kind is None:
        return new_state
    pay = (
        payment
        if payment is not None
        else auto_payment(new_state, registry, grid, player_id, objective_id)
    )
    if payment is not None:
        _validate(new_state, registry, player_id, objective_id, kind, pay)
    goal = threshold(objective_id, new_state)
    if kind == "trade_goods":
        economy.spend_trade_goods(new_state, player_id, goal)
    elif kind == "tokens":
        # Żetony z wybranych pul wracają do rezerwy.
        for pool, amount in pay.tokens.items():
            command_tokens.spend_to_reinforcements(new_state, player_id, pool, amount)
    elif kind == "fragments":
        relic_fragments.purge_chosen(new_state, player_id, pay.fragments)
    elif kind == "cards":
        card_draw.discard_chosen_action_cards(new_state, player_id, pay.cards)
    elif kind == "mixed":
        apply_payment(
            new_state, player_id, [*pay.resource_planets, *pay.influence_planets], pay.trade_goods
        )
    else:
        apply_payment(new_state, player_id, pay.planets, pay.trade_goods)
    return new_state


def spend_spec(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    objective_id: str,
) -> dict[str, Any] | None:
    """Opis kosztu celu dla UI (camelCase): co można wydać + podpowiedź silnika.

    ``None`` dla celów bez kosztu. ``suggested`` bywa ``None``, gdy gracza nie stać.
    """
    kind = spend_kind(objective_id)
    player = state.players.get(player_id)
    if kind is None or player is None:
        return None
    spec: dict[str, Any] = {
        "kind": kind,
        "goal": threshold(objective_id, state),
        "tradeGoods": economy.spendable_trade_goods(state, player_id),
    }
    if kind in ("resources", "influence"):
        spec["planets"] = ready_planet_values(state, registry, player_id, kind)  # type: ignore[arg-type]
    elif kind == "mixed":
        spec["resourcePlanets"] = ready_planet_values(state, registry, player_id, "resources")
        spec["influencePlanets"] = ready_planet_values(state, registry, player_id, "influence")
    elif kind == "tokens":
        spec["pools"] = {
            p: command_tokens.pool_count(state, player_id, p) for p in command_tokens.POOLS
        }
    elif kind == "cards":
        spec["cards"] = list(player.private.action_cards)
    elif kind == "fragments":
        spec["fragments"] = list(player.relic_fragments)
    try:
        suggested = auto_payment(state, registry, grid, player_id, objective_id)
        spec["suggested"] = suggested.model_dump()
    except ValueError:
        spec["suggested"] = None
    return spec
