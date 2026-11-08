"""Construction (inicjatywa 4, Thunder's Edge: ``te4construction``) — RULES.md 30.12.

Primary: albo połóż 1 strukturę na swojej planecie, albo użyj PRODUKCJI jednego ze swoich
doków; potem połóż 1 strukturę na swojej planecie. Secondary (1 żeton ze strategy pool):
połóż 1 strukturę na swojej planecie. Struktura = PDS albo dok (limity: 1 dok i 2 PDS na
planetę, brak na Demilitarized Zone). Wersję TE opisuje ``rules_tirules/R_construction.md``.

Produkcja doku to zwykła produkcja (``production.py``) w systemie doku, zawężona do tego
jednego doku (``ProductionGrant.zone``); primary czeka w kroku ``production`` aż gracz ją
zakończy („Finish production" → hook ``strategic_action.after_standalone_production``).
"""

from __future__ import annotations

from typing import Any

from src.core import production
from src.core.game_state import GameState
from src.core.strategy_cards.base import CardContext, CardSpec, Draft
from src.core.strategy_cards.common import (
    owned_planets,
    place_structure,
    placeable_structures,
    planet_position,
    start_standalone_production,
)

INITIATIVE = 4

STEP_OPTION = "choose_option"
STEP_PLACE = "place_structure"
STEP_DOCK = "choose_dock"
STEP_PRODUCTION = "production"
STEP_PLACE_2 = "place_structure_2"
OPTION_STRUCTURE = "structure"
OPTION_PRODUCTION = "production"


def docks(state: GameState, ctx: CardContext, player_id: str) -> list[dict[str, Any]]:
    """Doki gracza zdolne do produkcji: planeta, pozycja systemu i wartość PRODUCTION."""
    result: list[dict[str, Any]] = []
    for planet_id in owned_planets(state, player_id):
        position = planet_position(state, planet_id)
        if position is None:
            continue
        for producer in production.producers(state, ctx.registry, player_id, position):
            if producer.zone == planet_id and producer.base_type == "spacedock":
                result.append(
                    {"planet": planet_id, "position": position, "value": producer.value}
                )
    return result


def _place(state: GameState, owner_id: str, payload: dict[str, Any]) -> None:
    """Krok położenia struktury; brak legalnego miejsca pozwala pominąć krok (``planet: null``)."""
    planet = payload.get("planet")
    if planet is None and not placeable_structures(state, owner_id):
        return
    structure = payload.get("structure")
    if not isinstance(planet, str) or not isinstance(structure, str):
        raise ValueError("Choose a planet and a structure (pds / spacedock).")
    place_structure(state, owner_id, planet, structure)


def _on_step(
    state: GameState,
    ctx: CardContext,
    owner_id: str,
    step: str,
    draft: Draft,
    payload: dict[str, Any],
) -> None:
    if step == STEP_OPTION:
        option = payload.get("option")
        if option == OPTION_PRODUCTION and not docks(state, ctx, owner_id):
            raise ValueError("You have no space dock with a PRODUCTION ability.")
        if option not in (OPTION_STRUCTURE, OPTION_PRODUCTION):
            raise ValueError("Choose to place a structure or to use a space dock's PRODUCTION.")
        draft["option"] = option
    elif step in (STEP_PLACE, STEP_PLACE_2):
        _place(state, owner_id, payload)
    elif step == STEP_DOCK:
        planet = payload.get("planet")
        chosen = next((d for d in docks(state, ctx, owner_id) if d["planet"] == planet), None)
        if chosen is None:
            raise ValueError("Choose one of your space docks.")
        start_standalone_production(
            state, owner_id, chosen["position"], "Construction", zone=chosen["planet"]
        )
        draft["resume_step"] = STEP_PLACE_2
    elif step == STEP_PRODUCTION:
        raise ValueError("Finish the production first (use 'Finish production').")
    else:
        raise ValueError(f"Unknown Construction step: {step}")


def _next_step(step: str, draft: Draft) -> str | None:
    if step == STEP_OPTION:
        return STEP_PLACE if draft.get("option") == OPTION_STRUCTURE else STEP_DOCK
    if step == STEP_PLACE:
        return STEP_PLACE_2
    if step == STEP_DOCK:
        return STEP_PRODUCTION
    return None  # STEP_PLACE_2 kończy primary


def _secondary(
    state: GameState, _ctx: CardContext, player_id: str, payload: dict[str, Any]
) -> None:
    if not placeable_structures(state, player_id):
        raise ValueError("You have no legal place for a structure.")
    _place(state, player_id, payload)


def _options(
    state: GameState,
    ctx: CardContext,
    player_id: str,
    step: str | None,
    _draft: Draft,
) -> dict[str, Any]:
    if step == STEP_OPTION:
        return {"docks": docks(state, ctx, player_id), "can_place": bool(
            placeable_structures(state, player_id)
        )}
    if step == STEP_DOCK:
        return {"docks": docks(state, ctx, player_id)}
    if step in (STEP_PLACE, STEP_PLACE_2, None):
        return {"placeable": placeable_structures(state, player_id), "needs_input": True}
    return {}


SPEC = CardSpec(
    primary_steps=(STEP_OPTION, STEP_PLACE, STEP_DOCK, STEP_PRODUCTION, STEP_PLACE_2),
    on_step=_on_step,
    next_step=_next_step,
    secondary=_secondary,
    secondary_costs_token=True,
    options=_options,
)
