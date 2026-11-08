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

from src.core import objective_progress, objectives
from src.core.dice import next_rng
from src.core.game_state import GameState
from src.core.map_string import MECATOL_SYSTEM_ID
from src.core.strategy_cards.base import CardContext, CardSpec, Draft

INITIATIVE = 8
SECRET_LIMIT = 3  # „more than three secret objective cards"
DRAWN = "drawn"  # wartość ``return``: oddaj świeżo dobraną kartę


def controls_mecatol(state: GameState, player_id: str) -> bool:
    """Czy gracz kontroluje planetę w systemie Mecatol Rex."""
    for system in state.systems.values():
        if system.system_id == MECATOL_SYSTEM_ID:
            return player_id in system.planet_owners.values()
    return False


def _secret_count(state: GameState, player_id: str) -> int:
    player = state.players[player_id]
    return len(player.private.secret_objectives) + len(player.scored_secrets)


def over_limit_after_draw(state: GameState, player_id: str) -> bool:
    """Czy po dobraniu 1 tajnego celu gracz przekroczy limit (i jest co dobrać)."""
    has_cards = bool(state.decks.secret_objective_deck)
    return has_cards and _secret_count(state, player_id) >= SECRET_LIMIT


def draw_secret(state: GameState, player_id: str, give_back: str | None) -> None:
    """Dobiera tajny cel (mutuje klon); przy nadmiarze zwraca wskazany i tasuje talię.

    Raises:
        ValueError: Nadmiar bez wskazania zwrotu, zwrot celu spoza ręki albo zdobytego.
    """
    decks = state.decks
    private = state.players[player_id].private
    if not decks.secret_objective_deck:
        return  # brak kart do dobrania - nic się nie dzieje
    must_return = over_limit_after_draw(state, player_id)
    if must_return and give_back is None:
        raise ValueError(
            "You would hold more than 3 secret objectives - choose an unscored one to return."
        )
    if give_back is not None and not must_return:
        raise ValueError("You are not over the secret objective limit - nothing to return.")
    if give_back is not None and give_back != DRAWN and give_back not in private.secret_objectives:
        raise ValueError("You can only return an UNSCORED secret objective from your hand.")
    drawn = decks.secret_objective_deck.pop(0)
    private.secret_objectives.append(drawn)
    if give_back is not None:
        target = drawn if give_back == DRAWN else give_back
        private.secret_objectives.remove(target)
        decks.secret_objective_deck.append(target)
        next_rng(state).shuffle(decks.secret_objective_deck)


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
        scored = objectives.score_public(
            state, ctx.registry, ctx.require_grid(), owner_id, objective, ignore_phase=True
        )
        _adopt(state, scored)
        draft["scored"] = objective
    if controls_mecatol(state, owner_id):
        objectives.award_points(state, owner_id, 1)
        draft["gained"] = "victory_point"
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
        if objectives.has_scored_public(state, player_id, objective_id):
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
