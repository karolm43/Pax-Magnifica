"""Entropic Scar - technologia frakcyjna na starcie fazy statusu (RULES.md 1.5).

R_entropic_scars: „At the start of the status phase, a player with ships in an entropic scar may
spend a command token from their strategy pool to gain one of their faction-specific
technologies” - bez prerekwizytów (5.1), tylko za STATKI (5.2), za statki w dwóch bliznach dwa
żetony i obie technologie (5.3).

Oferta „may” dla każdego gracza ze statkami w bliźnie: pełne okno drzewa technologii (tryb GAIN,
tylko jego nieposiadane technologie frakcyjne). Każda kolejna blizna = kolejna oferta (decyzja
komponentu ``entropic_scar``), dopóki gracz ma żeton i technologię do wzięcia.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    command_tokens,
    entropic_scar,
    research_offer,
    rules_hooks,
    technology,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.rules_hooks import on_event

SOURCE = rules_hooks.declare_rule_source("entropic_scar")
DECISION = "entropic_scar"  # kolejna blizna (R_entropic_scars 5.3)
_LABEL = "Entropic Scar"
_USED = "scar_techs_used"  # ile technologii gracz już wziął z blizn na tym starcie statusu


def _registry() -> Any:
    return rules_hooks.bound_registry()


def missing_faction_techs(state: GameState, player_id: str) -> list[str]:
    """Nieposiadane technologie frakcyjne gracza (posortowane)."""
    owned = set(state.players[player_id].technologies)
    own = technology.faction_techs(state, _registry(), player_id)
    return sorted(t for t in own if t not in owned)


def _allowance(state: GameState, player_id: str, used: int) -> bool:
    """Czy gracz może wziąć KOLEJNĄ technologię: blizna ze statkami ponad zużyte, żeton, tech."""
    return (
        len(entropic_scar.scars_with_ships(state, player_id)) > used
        and command_tokens.can_spend_strategy_token(state, player_id)
        and bool(missing_faction_techs(state, player_id))
    )


def _ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return _allowance(state, player_id, 0)


def _again(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and _allowance(state, player_id, int(ctx.get(_USED, 0)))


def scar_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Okno drzewa technologii w trybie GAIN - dostępne tylko nieposiadane technologie frakcyjne."""
    allowed = set(missing_faction_techs(state, player_id))
    tree_input = research_offer.gain_input(
        state, registry, player_id, label="Gain 1 of your faction technologies",
        hint="Spend 1 command token from your strategy pool (ships in an entropic scar). "
             "Prerequisites are ignored.",
    )
    view = tree_input["research"]
    for row in view["tree"]:
        if row["id"] not in allowed and row["status"] == "available":
            row["status"] = "locked"
    view["gain"]["mandatory"] = False  # „may” - gracz może zrezygnować
    return [tree_input]


def _gain(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    tech_id = research_offer.chosen_tech(ctx.get("params") or {})
    if tech_id is None:
        return  # rezygnacja: żeton zostaje w puli
    if tech_id not in missing_faction_techs(state, player_id):
        raise ValueError("Choose one of your faction technologies that you do not own yet.")
    source = (
        command_tokens.SOURCE_POOL
        if state.players[player_id].strategic_cc >= 1
        else command_tokens.SOURCE_SCEPTER
    )
    command_tokens.spend_strategy_token(state, player_id, source=source)
    technology.grant_technology(state, player_id, tech_id)
    used = int(ctx.get(_USED, 0)) + 1
    if _allowance(state, player_id, used):
        triggers.fire(
            state, GameEvent.COMPONENT_DECISION, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "decision": DECISION, _USED: used},
        )


@on_event(
    GameEvent.PHASE, Moment.START, SOURCE, where={"phase": "status"}, optional=True,
    condition=_ready, inputs=scar_inputs, label=_LABEL,
)
def entropic_scar_tech(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Statki w bliźnie: żeton z puli strategii -> technologia frakcyjna (R_entropic_scars 5)."""
    _gain(state, player_id, ctx)


@on_event(
    GameEvent.COMPONENT_DECISION, Moment.AFTER, SOURCE, where={"decision": DECISION},
    optional=True, condition=_again, inputs=scar_inputs, label=_LABEL,
)
def entropic_scar_next(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Statki w drugiej bliźnie: druga technologia za drugi żeton (R_entropic_scars 5.3)."""
    _gain(state, player_id, ctx)
