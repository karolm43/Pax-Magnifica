"""Wydanie kosztu celów typu „Spend…" przy ich zdobywaniu (RULES.md 41.4).

R_objective_cards: cel wymagający wydania zasobów/żetonów trzeba opłacić w chwili
punktowania (w fazie statusu). Silnik wybiera płatność AUTOMATYCZNIE (⚠ ZAŁOŻENIE —
gracz nie wskazuje planet/pul): najpierw wyczerpuje planety, brak dopłaca trade goods;
żetony dowodzenia schodzą najpierw z puli taktycznej, potem strategicznej.
"""

from __future__ import annotations

from src.core import card_draw, command_tokens, economy
from src.core.game_state import GameState
from src.core.hex_grid import HexGrid
from src.core.objective_progress import (
    SPEND_OBJECTIVES,
    View,
    mixed_spend_plan,
    threshold,
)
from src.core.payment import apply_payment
from src.core.planet_stats import effective_planets, planet_stats
from src.core.registry import StaticDataRegistry

_TRADE_GOODS = {"trade_routes", "centralize_trade"}
_TOKENS = {"lead", "galvanize"}
_RESOURCES = {"monument", "golden_age"}
_INFLUENCE = {"sway_council", "manipulate_law"}
_MIXED = {"amass_wealth": 3, "vast_reserves": 6}


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


def pay_for_objective(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    objective_id: str,
) -> GameState:
    """Zwraca NOWY stan po opłaceniu celu; cele bez kosztu zwraca bez zmian (klon).

    Raises:
        ValueError: Gdy gracza nie stać (nie powinno się zdarzyć po sprawdzeniu postępu).
    """
    new_state = state.clone()
    if objective_id not in SPEND_OBJECTIVES:
        return new_state
    player = new_state.players[player_id]
    goal = threshold(objective_id, new_state)
    if objective_id in _TRADE_GOODS:
        economy.spend_trade_goods(new_state, player_id, goal)
    elif objective_id in _TOKENS:
        # Żetony schodzą najpierw z puli taktycznej, potem strategicznej; wracają do rezerwy.
        from_tactical = min(command_tokens.pool_count(new_state, player_id, "tactical"), goal)
        command_tokens.spend_to_reinforcements(new_state, player_id, "tactical", from_tactical)
        command_tokens.spend_to_reinforcements(
            new_state, player_id, "strategic", goal - from_tactical
        )
    elif objective_id == "fsn":
        card_draw.discard_action_cards(new_state, player_id, goal)
    elif objective_id in _MIXED:
        ready = View(new_state, registry, grid, player_id).ready_planets()
        plan = mixed_spend_plan(
            ready, effective_planets(new_state, registry), player.trade_goods, _MIXED[objective_id]
        )
        if plan is None:
            raise ValueError("You cannot afford this objective.")
        res_planets, inf_planets, tg_spent = plan
        apply_payment(new_state, player_id, [*res_planets, *inf_planets], tg_spent)
    else:
        kind = "resources" if objective_id in _RESOURCES else "influence"
        ready = View(new_state, registry, grid, player_id).ready_planets()
        values = [
            (p, (stats.resources if kind == "resources" else stats.influence))
            for p in ready
            if (stats := planet_stats(new_state, registry, p)) is not None
        ]
        spent, rest = _pick_planets(values, goal)
        if rest > player.trade_goods:
            raise ValueError("You cannot afford this objective.")
        apply_payment(new_state, player_id, spent, rest)
    return new_state
