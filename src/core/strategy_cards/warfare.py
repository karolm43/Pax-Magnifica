"""Warfare (inicjatywa 6, Thunder's Edge: ``te6warfare``) — RULES.md 30.11.

Primary: wykonaj akcję taktyczną w DOWOLNYM systemie BEZ kładzenia żetonu (także gdy leży tam
już twój żeton) - system i tak liczy się jako aktywowany; przed i po akcji możesz zmienić
rozkład żetonów dowodzenia po pulach. Secondary (1 żeton ze strategy pool): użyj zdolności
PRODUCTION jednostek w swoim home system (żeton nie ląduje w systemie). Wersję TE opisuje
``rules_tirules/R_warfare.md``.

Akcja taktyczna toczy się w istniejącym przepływie (ruch, walka, inwazja, produkcja); primary
czeka w kroku ``tactical_action``, a ``tactical.end_tactical_action`` wznawia je od
``redistribute_after``. Secondary otwiera produkcję standalone (``ProductionGrant``) w home
system i czeka na jej zakończenie.
"""

from __future__ import annotations

from typing import Any

from src.core import command_tokens, production, tactical
from src.core.game_state import GameState
from src.core.strategy_cards.base import CardContext, CardSpec, Draft
from src.core.strategy_cards.common import parse_pools, start_standalone_production

INITIATIVE = 6

STEP_BEFORE = "redistribute_before"
STEP_ACTIVATE = "activate_system"
STEP_TACTICAL = tactical.STRATEGY_TACTICAL_STEP
STEP_AFTER = "redistribute_after"


def _pool_total(state: GameState, player_id: str) -> int:
    return command_tokens.sheet_total(state, player_id)


def redistribute(state: GameState, player_id: str, payload: dict[str, Any]) -> None:
    """Zmienia rozkład żetonów po pulach (mutuje klon); pusty payload = bez zmian.

    Suma musi równać się liczbie żetonów gracza na arkuszu (nie dodajemy i nie ujmujemy).
    """
    if not any(key in payload for key in ("tactical", "fleet", "strategic")):
        return
    pools = parse_pools(payload)
    if sum(pools.values()) != _pool_total(state, player_id):
        raise ValueError(
            f"Distribute exactly {_pool_total(state, player_id)} command token(s) "
            "between your pools."
        )
    command_tokens.set_pools(state, player_id, pools)


def _adopt(dst: GameState, src: GameState) -> None:
    """Przenosi zawartość ``src`` do ``dst`` w miejscu (pomijając szkic kroku primary)."""
    for name in type(dst).model_fields:
        if name == "pending_strategy":
            continue
        setattr(dst, name, getattr(src, name))


def _on_step(
    state: GameState,
    ctx: CardContext,
    owner_id: str,
    step: str,
    draft: Draft,
    payload: dict[str, Any],
) -> None:
    if step in (STEP_BEFORE, STEP_AFTER):
        redistribute(state, owner_id, payload)
    elif step == STEP_ACTIVATE:
        position = payload.get("system")
        grid = ctx.require_grid()
        if not isinstance(position, str) or position not in grid.positions:
            raise ValueError("Choose a system on the map to activate.")
        activated = tactical.activate_system(state, grid, position, free=True)
        _adopt(state, activated)
        # Po zakończeniu akcji taktycznej (hook w tactical) primary wznawia ten krok.
        draft[tactical.STRATEGY_RESUME_KEY] = STEP_AFTER
    elif step == STEP_TACTICAL:
        raise ValueError("Finish the tactical action first (use 'End action').")
    else:
        raise ValueError(f"Unknown Warfare step: {step}")


def _next_step(step: str, _draft: Draft) -> str | None:
    return {
        STEP_BEFORE: STEP_ACTIVATE,
        STEP_ACTIVATE: STEP_TACTICAL,
    }.get(step)  # STEP_AFTER kończy primary


def home_position(state: GameState, ctx: CardContext, player_id: str) -> str | None:
    """Pozycja systemu domowego gracza (z ``home_position`` albo po id systemu frakcji)."""
    player = state.players[player_id]
    if player.home_position is not None and player.home_position in state.systems:
        return player.home_position
    faction = ctx.registry.factions.get(player.faction or "")
    if faction is not None and faction.home_system:
        for position, system in state.systems.items():
            if system.system_id == faction.home_system:
                return position
    return None


def _secondary(
    state: GameState, ctx: CardContext, player_id: str, _payload: dict[str, Any]
) -> None:
    position = home_position(state, ctx, player_id)
    if position is None or not production.producers(state, ctx.registry, player_id, position):
        raise ValueError("You have no unit with PRODUCTION in your home system.")
    start_standalone_production(state, player_id, position, "Warfare")


def _options(
    state: GameState,
    ctx: CardContext,
    player_id: str,
    step: str | None,
    _draft: Draft,
) -> dict[str, Any]:
    player = state.players[player_id]
    if step == STEP_ACTIVATE:
        # Każdy system na mapie (karta: „in any system"); UI podświetla je do kliknięcia.
        return {"systems": sorted(ctx.grid.positions) if ctx.grid is not None else []}
    if step in (STEP_BEFORE, STEP_AFTER):
        return {
            "total": _pool_total(state, player_id),
            "tactical": player.tactical_cc,
            "fleet": player.fleet_cc,
            "strategic": player.strategic_cc,
        }
    position = home_position(state, ctx, player_id)
    can = position is not None and bool(
        production.producers(state, ctx.registry, player_id, position)
    )
    return {"home": position, "can_produce": can, "needs_input": False}


SPEC = CardSpec(
    primary_steps=(STEP_BEFORE, STEP_ACTIVATE, STEP_TACTICAL, STEP_AFTER),
    on_step=_on_step,
    next_step=_next_step,
    secondary=_secondary,
    secondary_costs_token=True,
    options=_options,
)
