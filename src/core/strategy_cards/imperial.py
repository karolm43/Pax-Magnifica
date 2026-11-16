"""Imperial (inicjatywa 8, base) — RULES.md 30.10, R_imperial.

Primary: natychmiast zdobądź 1 cel publiczny, jeśli spełniasz jego wymagania (opcjonalnie;
trzeba kontrolować wszystkie planety w home system); potem, jeśli kontrolujesz Mecatol Rex,
zdobywasz 1 VP (obowiązkowo - nie można zamiast tego dobrać tajnego celu), w przeciwnym razie
dobierasz 1 tajny cel. Secondary (1 żeton ze strategy pool): dobierz 1 tajny cel.

Limit: po dobraniu tajnego celu gracz ma najwyżej 3 (ręka + zdobyte); nadmiar → zwraca
jeden NIEzdobyty tajny cel do talii i tasuje ją. Zwracany może być także świeżo dobrany
(``"drawn"``) - gracz decyduje, nie widząc go wcześniej, więc to osobna opcja.
"""

from __future__ import annotations

from typing import Any

from src.core import objective_progress, objectives, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.map_string import MECATOL_SYSTEM_ID
from src.core.objective_payment import ObjectivePayment, spend_spec
from src.core.secret_objectives import draw as draw_secret
from src.core.secret_objectives import over_limit_after_draw
from src.core.strategy_cards.base import CardContext, CardSpec, Draft

INITIATIVE = 8


def controls_mecatol(state: GameState, player_id: str) -> bool:
    """Czy gracz kontroluje planetę w systemie Mecatol Rex."""
    for system in state.systems.values():
        if system.system_id == MECATOL_SYSTEM_ID:
            return player_id in system.planet_owners.values()
    return False


def _give_back(payload: dict[str, Any]) -> str | None:
    value = payload.get("return")
    if value is not None and not isinstance(value, str):
        raise ValueError("'return' must be a secret objective id or 'drawn'.")
    return value


def _on_step(
    state: GameState,
    ctx: CardContext,
    owner_id: str,
    step: str,
    draft: Draft,
    payload: dict[str, Any],
) -> None:
    """Jedyny krok „score_and_draw": cel publiczny (opcjonalnie) + VP albo tajny cel.

    Efekty stosujemy od razu na klonie stanu (kroku nie da się przerwać w połowie: błąd
    odrzuca cały klon). Zachowuje kolejność z karty: najpierw cel publiczny, potem VP/tajny.
    """
    if step != "score_and_draw":
        raise ValueError(f"Unknown Imperial step: {step}")
    objective = payload.get("objective")
    give_back = _give_back(payload)
    if objective is not None and not isinstance(objective, str):
        raise ValueError("'objective' must be an objective id or null.")
    if controls_mecatol(state, owner_id) and give_back is not None:
        raise ValueError("You control Mecatol Rex - you gain a victory point, nothing to return.")

    if objective is not None:
        raw_payment = payload.get("payment")
        scored = objectives.score_public(
            state, ctx.registry, ctx.require_grid(), owner_id, objective, ignore_phase=True,
            payment=(
                ObjectivePayment.model_validate(raw_payment) if raw_payment is not None else None
            ),
        )
        _adopt(state, scored)
        draft["scored"] = objective
    if controls_mecatol(state, owner_id):
        objectives.award_points(state, owner_id, 1, source=objectives.SOURCE_IMPERIAL)
        draft["gained"] = "victory_point"
        triggers.fire(
            state, GameEvent.IMPERIAL_VICTORY_POINT, Moment.AFTER, subject=owner_id,
            ctx={"player": owner_id},
        )
    else:
        draw_secret(state, owner_id, give_back)
        draft["gained"] = "secret_objective"


def _adopt(dst: GameState, src: GameState) -> None:
    """Przenosi zawartość ``src`` do ``dst`` w miejscu (efekt zwrócony jako nowy stan)."""
    for name in type(dst).model_fields:
        if name == "pending_strategy":
            continue  # szkic kroku jest współdzielony z wywołującym - nie podmieniamy
        setattr(dst, name, getattr(src, name))


def _secondary(
    state: GameState, _ctx: CardContext, player_id: str, payload: dict[str, Any]
) -> None:
    draw_secret(state, player_id, _give_back(payload))


def _options(
    state: GameState,
    ctx: CardContext,
    player_id: str,
    step: str | None,
    _draft: Draft,
) -> dict[str, Any]:
    player = state.players[player_id]
    result: dict[str, Any] = {
        "will_draw": not (step is not None and controls_mecatol(state, player_id)),
        "over_limit": over_limit_after_draw(state, player_id),
        "unscored": list(player.private.secret_objectives),
        "secret_deck": len(state.decks.secret_objective_deck),
        "needs_input": over_limit_after_draw(state, player_id),
    }
    if step is not None:
        result["mecatol"] = controls_mecatol(state, player_id)
        result["home_controlled"] = objectives.controls_home_planets(
            state, ctx.registry, player_id
        )
        result["objectives"] = (
            objectives.scoreable_public_objectives(
                state, ctx.registry, ctx.require_grid(), player_id, ignore_phase=True
            )
            if ctx.grid is not None
            else []
        )
        # Pełna lista odkrytych, niezdobytych celów z postępem - ten sam kształt co
        # ``status.publicOptions`` (panel punktowania fazy statusu), dla spójnego UI.
        result["public_options"] = (
            _public_options(state, ctx, player_id) if ctx.grid is not None else []
        )
    return result


def _public_options(state: GameState, ctx: CardContext, player_id: str) -> list[dict[str, Any]]:
    home = objectives.controls_home_planets(state, ctx.registry, player_id)
    options: list[dict[str, Any]] = []
    for objective_id in state.objectives.revealed:
        if objectives.has_scored_public(state, player_id, objective_id) or objectives.is_retired(
            state, objective_id
        ):
            continue
        value, goal, ok = objective_progress.evaluate(
            state, ctx.registry, ctx.require_grid(), player_id, objective_id
        )
        options.append(
            {
                "key": objective_id,
                "progress": value,
                "threshold": goal,
                "ready": ok and home,
                "manual": value is None,
                "spend": spend_spec(
                    state, ctx.registry, ctx.require_grid(), player_id, objective_id
                ),
            }
        )
    return options


SPEC = CardSpec(
    primary_steps=("score_and_draw",),
    on_step=_on_step,
    secondary=_secondary,
    secondary_costs_token=True,
    options=_options,
)
