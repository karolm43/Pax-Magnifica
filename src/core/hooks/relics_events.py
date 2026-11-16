"""Relikty zdarzeniowe (RULES.md 59): Crown of Emphidia, Dominus Orb, Neuraloop.

Każdy to oferta „you may" w oknie decyzji (RULES.md 56) - gracz zawsze decyduje sam, a legalne
opcje liczy silnik. Teksty w docstringach to dosłowne cytaty z ``assets/data/relics``;
przypadki brzegowe: ``docs/rules_tirules/C_relics.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    exhaust,
    exploration,
    objectives,
    relics,
    rules_hooks,
    triggers,
)
from src.core import offer_inputs as oi
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState
from src.core.hooks import card_labels
from src.core.hooks.card_helpers import controlled
from src.core.planet_stats import attachment_defs
from src.core.rules_hooks import (
    POINT_MOVEMENT_IGNORE_OWN_CC,
    SOURCE_EFFECT,
    SOURCE_RELIC,
    HookKind,
    HookSource,
    on_event,
    register,
)

_TOMB_ATTACHMENT = "tombofemphidia"  # attachment „Tomb of Emphidia” (tekst karty)
_DOMINUS_EFFECT = "relics:dominusorb"


def _src(relic_id: str) -> HookSource:
    return HookSource(SOURCE_RELIC, relic_id)


def _own(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id


# --- The Crown of Emphidia -------------------------------------------------------------------


def _explorable_planets(state: GameState, registry: Any, player_id: str) -> list[str]:
    return [p for p in controlled(state, player_id) if exploration.explorable(registry, p)]


def _after_own_tactical(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    registry = rules_hooks.bound_registry()
    return (
        ctx.get("player") == player_id
        and relics.is_ready(state, player_id, "emphidia")
        and registry is not None
        and bool(_explorable_planets(state, registry, player_id))
    )


def emphidia_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Planeta z cechą, którą gracz kontroluje (eksploracja)."""
    return [
        oi.choice(
            "planet", "Planet to explore",
            [
                oi.option(p, card_labels.describe_planet(state, registry, p))
                for p in _explorable_planets(state, registry, decider)
            ],
        )
    ]


@on_event(
    GameEvent.TACTICAL_ACTION,
    Moment.END,
    _src("emphidia"),
    optional=True,
    condition=_after_own_tactical,
    covers="relics:emphidia",
    label="The Crown of Emphidia: exhaust to explore 1 planet you control",
    inputs=emphidia_inputs,
)
def emphidia_explore(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The Crown of Emphidia: After you perform a tactical action, you may exhaust this card to
    explore 1 planet you control."""
    registry = rules_hooks.bound_registry()
    planet = str(ctx.get("params", {}).get("planet", ""))
    if planet not in _explorable_planets(state, registry, player_id):
        raise ValueError("Choose a planet you control that can be explored ('planet').")
    position = card_labels.system_position_of_planet(state, planet)
    if position is None:
        raise ValueError(f"Planet {planet} is not on the board.")
    exhaust.exhaust_relic(state, player_id, "emphidia")
    exploration.start_exploration(state, registry, player_id, position, [planet])


def _controls_tomb(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    registry = rules_hooks.bound_registry()
    return registry is not None and any(
        any(a.id == _TOMB_ATTACHMENT for a in attachment_defs(state, registry, planet))
        for planet in controlled(state, player_id)
    )


@on_event(
    GameEvent.PHASE,
    Moment.END,
    _src("emphidia"),
    optional=True,
    where={"phase": "status"},
    condition=_controls_tomb,
    covers="relics:emphidia",
    label="The Crown of Emphidia: purge for 1 victory point (Tomb of Emphidia)",
)
def emphidia_tomb(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The Crown of Emphidia: At the end of the status phase, if you control the "Tomb of
    Emphidia," you may purge this card to gain 1 victory point."""
    del ctx
    relics.purge_relic(state, player_id, "emphidia")
    objectives.award_points(state, player_id, 1, source="relics:emphidia")


# --- Dominus Orb -----------------------------------------------------------------------------


@on_event(
    GameEvent.SYSTEM_ACTIVATED,
    Moment.AFTER,
    _src("dominusorb"),
    optional=True,
    condition=_own,
    covers="relics:dominusorb",
    label="Dominus Orb: purge to move units out of systems with your command tokens",
)
def dominus_orb(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Dominus Orb: Before you move units during a tactical action, you may purge this card to
    move and transport units that are in systems that contain 1 of your command tokens.

    Efekt trwa do końca tej akcji taktycznej (``Duration.TACTICAL_ACTION``) i znosi zakaz ruchu /
    pickupu z systemów z własnym żetonem (R3, T4 w ``movement``).
    """
    del ctx
    relics.purge_relic(state, player_id, "dominusorb")
    active_effects.add_effect(state, _DOMINUS_EFFECT, Duration.TACTICAL_ACTION, owner=player_id)


def _always(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return True


register(POINT_MOVEMENT_IGNORE_OWN_CC, HookSource(SOURCE_EFFECT, _DOMINUS_EFFECT), HookKind.PERMIT)(
    _always
)


# --- Neuraloop -------------------------------------------------------------------------------

_ATTACHED = "attached:"  # wartość opcji: relikt przyczepiony do planety (Nano-Forge)
_HELD = "relic:"  # wartość opcji: relikt leżący przed graczem


def _relic_name(registry: Any, relic_id: str) -> str:
    from src.core import relic_actions

    return relic_actions.relic_def(registry, relic_id).name or relic_id


def neuraloop_inputs(
    state: GameState, registry: Any, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Relikty do purge: własne oraz Nano-Forge przyczepiony do kontrolowanej planety."""
    options = [
        oi.option(f"{_HELD}{r}", f"{_relic_name(registry, r)} - purge", ref=("relic", r))
        for r in state.players[decider].relics
    ]
    for planet in controlled(state, decider):
        if "nanoforge" in state.planet_attachments.get(planet, []):
            name = card_labels.planet_name(registry, planet)
            options.append(
                oi.option(
                    f"{_ATTACHED}{planet}",
                    f"{_relic_name(registry, 'nanoforge')} - purge, attached to {name}",
                    ref=("relic", "nanoforge"),
                )
            )
    return [oi.choice("relic", "Relic to purge", options)]


def _holds_relic(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return bool(state.players[player_id].relics) or any(
        "nanoforge" in state.planet_attachments.get(p, []) for p in controlled(state, player_id)
    )


@on_event(
    GameEvent.OBJECTIVE_REVEALED,
    Moment.AFTER,
    _src("neuraloop"),
    optional=True,
    condition=_holds_relic,
    covers="relics:neuraloop",
    label="Neuraloop: purge a relic to replace the revealed objective",
    inputs=neuraloop_inputs,
)
def neuraloop(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Neuraloop: When a public objective is revealed, you may purge one of your relics to discard
    that objective and replace it with a random objective from any objective deck; that
    objective is a public objective, even if it is a secret objective.

    Purge innego reliktu NIE rozstrzyga jego zdolności „purge" (C_relics), ale odpala efekt utraty
    karty (np. Shard -1 VP). Nowy cel znów odpala „when revealed", więc można go wymienić ponownie.
    """
    registry = rules_hooks.bound_registry()
    choice = str(ctx.get("params", {}).get("relic", ""))
    old_id = str(ctx["objective"])
    if choice.startswith(_HELD) and choice[len(_HELD):] in state.players[player_id].relics:
        relics.purge_relic(state, player_id, choice[len(_HELD):])
    elif choice.startswith(_ATTACHED) and choice[len(_ATTACHED):] in controlled(state, player_id):
        exploration.purge_attachment(state, choice[len(_ATTACHED):], "nanoforge")
    else:
        raise ValueError("Choose one of your relics to purge ('relic').")
    new_id = objectives.replace_revealed(state, registry, old_id)
    if new_id is not None:
        triggers.fire(
            state, GameEvent.OBJECTIVE_REVEALED, Moment.AFTER, ctx={"objective": new_id}
        )
