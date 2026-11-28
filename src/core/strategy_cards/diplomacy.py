"""Diplomacy (inicjatywa 2, errata Codex I) — RULES.md 30.8, R_diplomacy.

Primary: wybierz system (nie Mecatol Rex) z planetą, którą kontrolujesz; każdy inny gracz
kładzie tam żeton dowodzenia ze SWOJEJ REZERWY (pomija, jeśli już ma tam żeton). Potem
odnów do 2 swoich wyczerpanych planet. Secondary (1 żeton ze strategy pool): odnów do 2
swoich wyczerpanych planet.
"""

from __future__ import annotations

from typing import Any

from src.core import command_tokens
from src.core.game_state import GameState
from src.core.map_string import is_mecatol_system
from src.core.strategy_cards.base import CardContext, CardSpec, Draft
from src.core.strategy_cards.common import (
    exhausted_owned_planets,
    owned_planets,
    ready_planets_by_choice,
    str_list,
)

INITIATIVE = 2
READY_LIMIT = 2  # „ready up to 2 exhausted planets"


def eligible_systems(state: GameState, player_id: str) -> dict[str, list[str]]:
    """Systemy (pozycja → własne planety) legalne dla primary: nie Mecatol, z własną planetą."""
    result: dict[str, list[str]] = {}
    for position, system in state.systems.items():
        if is_mecatol_system(system.system_id):
            continue
        mine = [p for p, owner in system.planet_owners.items() if owner == player_id]
        if mine:
            result[position] = mine
    return result


def _take_token_from_sheet(state: GameState, player_id: str) -> bool:
    """Zdejmuje żeton z arkusza gracza, gdy rezerwa pusta.

    ⚠️ ZAŁOŻENIE: reguła daje wybór puli GRACZOWI; silnik wybiera automatycznie
    (taktyczna → floty → strategiczna), bo nie pytamy innych graczy w trakcie primary.
    """
    for pool in command_tokens.POOLS:
        if command_tokens.pool_count(state, player_id, pool) > 0:
            command_tokens.spend_from_pool(state, player_id, pool)
            return True
    return False


def _on_step(
    state: GameState,
    _ctx: CardContext,
    owner_id: str,
    step: str,
    draft: Draft,
    payload: dict[str, Any],
) -> None:
    if step == "choose_system":
        position = payload.get("system")
        if position is None and not eligible_systems(state, owner_id):
            # Brak legalnego systemu (nota R_diplomacy): akcja nadal wolna, nikt nic nie kładzie.
            draft["system"] = None
            return
        if not isinstance(position, str) or position not in eligible_systems(state, owner_id):
            raise ValueError(
                "Choose a system (not Mecatol Rex) that contains a planet you control."
            )
        draft["system"] = position
    elif step == "ready_planets":
        chosen = str_list(payload, "planets")
        # Walidacja na kopii: faktyczne odnowienie dopiero w ``_primary`` (atomowo).
        ready_planets_by_choice(state.clone(), owner_id, chosen, READY_LIMIT)
        draft["planets"] = chosen
    else:
        raise ValueError(f"Unknown Diplomacy step: {step}")


def _primary(
    state: GameState, _ctx: CardContext, owner_id: str, draft: Draft
) -> None:
    position = draft.get("system")
    if position is not None:
        system = state.systems[position]
        # Kolejność: od gracza po lewej aktywnego, zegarowo (kolejka seating_order).
        order = [p for p in state.seating_order if p in state.players]
        start = order.index(owner_id) if owner_id in order else -1
        for pid in order[start + 1 :] + order[: start + 1]:
            if pid == owner_id or pid in system.command_tokens:
                continue
            if command_tokens.reinforcements(state, pid) > 0:
                command_tokens.take_from_reinforcements(state, pid)
            elif not _take_token_from_sheet(state, pid):
                continue  # brak jakiegokolwiek żetonu - nic do położenia
            command_tokens.place_token(state, system, pid)
    ready_planets_by_choice(state, owner_id, list(draft.get("planets", [])), READY_LIMIT)


def _secondary(
    state: GameState, _ctx: CardContext, player_id: str, payload: dict[str, Any]
) -> None:
    ready_planets_by_choice(state, player_id, str_list(payload, "planets"), READY_LIMIT)


def _options(
    state: GameState,
    _ctx: CardContext,
    player_id: str,
    step: str | None,
    _draft: Draft,
) -> dict[str, Any]:
    if step == "choose_system":
        return {"systems": eligible_systems(state, player_id)}
    return {
        "exhausted": exhausted_owned_planets(state, player_id),
        "limit": READY_LIMIT,
        "owned": owned_planets(state, player_id),
        "needs_input": True,
    }


SPEC = CardSpec(
    primary_steps=("choose_system", "ready_planets"),
    on_step=_on_step,
    primary=_primary,
    secondary=_secondary,
    secondary_costs_token=True,
    options=_options,
)
