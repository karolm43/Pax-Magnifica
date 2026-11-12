"""Ogólne promissory notes (RULES.md 61.2): Ceasefire, Political Secret, Support for the Throne,
Trade Agreement, Alliance.

Teksty w docstringach to cytaty z ``assets/data/promissory_notes`` (szablon ``<color>``).
Zagrywanie, zwrot i strefę gry obsługuje ``core/promissory_play.py``; tu tylko efekty, warunki
zagrania i zwroty ze strefy gry. Rulingi: ``docs/rules_tirules/C_promissory_notes.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    agenda_phase,
    economy,
    objectives,
    promissory_notes,
    promissory_play,
    rules_hooks,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, Phase, SystemState
from src.core.reaction_cards import OpenWindow, window_provider
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import SOURCE_PROMISSORY, HookSource, on_event, register_effect

CEASEFIRE = "<color>_cf"
POLITICAL_SECRET = "<color>_ps"
SUPPORT = "<color>_sftt"
TRADE_AGREEMENT = "<color>_ta"
ALLIANCE = "<color>_an"

CEASEFIRE_EFFECT = promissory_play.CEASEFIRE_EFFECT
POLITICAL_SECRET_EFFECT = promissory_play.POLITICAL_SECRET_EFFECT
_SUPPORT_VP = 1  # „gain 1 victory point" / „lose 1 victory point"


def has_units(system: SystemState | None, player_id: str) -> bool:
    """Czy gracz ma w systemie jakąkolwiek jednostkę (przestrzeń albo planeta)."""
    if system is None:
        return False
    if any(system.space_units.get(player_id, {}).values()):
        return True
    return any(any(units.get(player_id, {}).values()) for units in system.planet_units.values())


def _window(params: Mapping[str, Any]) -> Mapping[str, Any]:
    window = params.get("__window")
    return window if isinstance(window, Mapping) else {}


def _owner(params: Mapping[str, Any]) -> str:
    owner = params.get("__owner")
    if not isinstance(owner, str):
        raise ValueError("The owner of this promissory note is not in the game.")
    return owner


# ------------------------------------------------------------------------------- Ceasefire


@promissory_play.condition(CEASEFIRE)
def _ceasefire_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> str | None:
    """„… activates a system that contains 1 or more of your units"."""
    position = window.ctx.get("position")
    if not has_units(state.systems.get(str(position)), player_id):
        return "The active system does not contain any of your units."
    return None


@register_effect(f"promissory_notes:{CEASEFIRE}")
def ceasefire(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """After the <color> player activates a system that contains 1 or more of your units: The
    <color> player cannot move units to the active system. Then return this card."""
    owner = _owner(params)
    active_effects.add_effect(
        state, CEASEFIRE_EFFECT, Duration.TACTICAL_ACTION, owner=owner,
        data={"position": str(_window(params).get("ctx", {}).get("position", ""))},
    )


# ------------------------------------------------------------------------ Political Secret


@register_effect(f"promissory_notes:{POLITICAL_SECRET}")
def political_secret(
    state: GameState, registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """When an agenda is revealed: The <color> player cannot vote, play action cards, or use
    faction abilities until after that agenda has been resolved. Then, return this card."""
    owner = _owner(params)
    active_effects.add_effect(state, POLITICAL_SECRET_EFFECT, Duration.AGENDA, owner=owner)
    agenda_phase.block_voter(state, registry, owner)


# ---------------------------------------------------------------- Support for the Throne


@register_effect(f"promissory_notes:{SUPPORT}")
def support_received(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """When you receive this card, if you are not the <color> player, you must place it faceup
    in your play area and gain 1 victory point."""
    if params.get("__received"):
        objectives.award_points(state, player_id, _SUPPORT_VP)


def _activates_owner_units(template: str) -> Any:
    """Warunek zwrotu Alliance / SftT: aktywowany system zawiera jednostki właściciela notki."""

    def condition(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
        registry = rules_hooks.bound_registry()
        if registry is None or ctx.get("player") != player_id:
            return False
        system = state.systems.get(str(ctx.get("position")))
        return any(
            owner is not None and has_units(system, owner)
            for _note, owner in promissory_play.notes_in_play(state, registry, player_id, template)
        )

    return condition


def _return_on_activation(template: str, vp_loss: int) -> None:
    @on_event(
        GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_PROMISSORY, template),
        condition=_activates_owner_units(template), covers=f"promissory_notes:{template}",
        label=f"{template}: return",
    )
    def _back(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
        registry = rules_hooks.bound_registry()
        system = state.systems.get(str(ctx.get("position")))
        for note_id, owner in promissory_play.notes_in_play(state, registry, player_id, template):
            if owner is not None and has_units(system, owner):
                if vp_loss:
                    objectives.award_points(state, player_id, -vp_loss)
                promissory_notes.return_from_play(state, player_id, owner, note_id)


_return_on_activation(SUPPORT, _SUPPORT_VP)
_return_on_activation(ALLIANCE, 0)


# ---------------------------------------------------------------------------- Alliance


@register_effect(f"promissory_notes:{ALLIANCE}")
def alliance_received(
    _state: GameState, _registry: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """When you receive this card … place it faceup in your play area. While this card is in your
    play area, you can use the <color> player's commander ability, if it is unlocked.

    Sama strefa wystarcza: ``rules_hooks.owned_sources`` daje posiadaczowi źródło odblokowanego
    commandera właściciela (:func:`alliance_commanders`).
    """


def alliance_commanders(state: GameState, player_id: str) -> list[str]:
    """Commanderzy innych graczy dostępni przez Alliance w strefie gracza (odblokowani)."""
    from src.core import leaders  # lokalnie: leaders importuje triggers

    registry = rules_hooks.bound_registry()
    if registry is None:
        return []
    found: list[str] = []
    for _note, owner in promissory_play.notes_in_play(state, registry, player_id, ALLIANCE):
        if owner is None or owner == player_id:
            continue
        for leader_id in leaders.leaders_of(registry, state.players[owner]):
            leader = registry.leaders.get(leader_id)
            if leader is not None and leader.type == "commander" and leaders.state_of(
                state, registry, owner, leader_id
            ) == leaders.UNLOCKED:
                found.append(leader_id)
    return found


# -------------------------------------------------------------------------- Trade Agreement


@window_provider
def replenished(state: GameState) -> list[OpenWindow]:
    """„When the <color> player replenishes commodities": ślad uzupełnień do następnej akcji."""
    if state.phase is not Phase.ACTION and state.phase is not Phase.STATUS:
        return []
    return [
        OpenWindow(GameEvent.COMMODITIES_REPLENISHED, Moment.WHEN, {"player": pid})
        for pid in state.last_replenished
        if pid in state.players
    ]


@promissory_play.condition(TRADE_AGREEMENT)
def _trade_condition(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, window: OpenWindow
) -> str | None:
    owner = window.subject
    if owner is None or state.players[owner].commodities <= 0:
        return "The owner has no commodities to give."
    return None


@register_effect(f"promissory_notes:{TRADE_AGREEMENT}")
def trade_agreement(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """When the <color> player replenishes commodities: The <color> player gives you all of
    their commodities. Then, return this card (R_commodities: u odbiorcy to trade goods)."""
    owner = _owner(params)
    amount = state.players[owner].commodities
    economy.give_to_player(state, owner, player_id, commodities=amount)
