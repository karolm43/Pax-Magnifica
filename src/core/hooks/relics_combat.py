"""Relikty walki, kości, ruchu i ekonomii (RULES.md 59): działają przez punkty zaczepienia.

Zawiera: Lightrail Ordnance (Space Cannon stoczni), Metali Void Shielding (Sustain Damage),
Metali Void Armaments (AFB), The Crown of Thalnos (przerzut), Heart of Ixth (±1 do kości),
Scepter of Emelpar (żeton z rezerwy), The Triad (relikt jak planeta), The Prophet's Tears
(ignorowanie prerekwizytu). Liczby (progi, kości) są z tekstów kart w ``assets/data/relics``.
Decyzje „you may" idą ofertami albo świadomym wyborem gracza w formularzu - nigdy automatycznie.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import card_draw, exhaust, relic_planets, relics
from src.core.components import ComponentCategory, ExplorationDef
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.rules_hooks import (
    POINT_COMBAT_AFB_GRANTED,
    POINT_COMBAT_GRANTED_SUSTAIN,
    POINT_COMBAT_REROLL_PLUS_ONE,
    POINT_DIE_ADJUST,
    POINT_SPACE_CANNON_GRANTED,
    POINT_STRATEGY_TOKEN_FROM_REINFORCEMENTS,
    POINT_TECHNOLOGY_IGNORE_PREREQUISITE,
    SOURCE_RELIC,
    HookKind,
    HookSource,
    declare_data_driven,
    on_event,
    register,
)

_LIGHTRAIL_GRANT = "spacedock:5:2"  # „Your space docks gain SPACE CANNON 5 (x2)”
_ARMAMENTS_GRANT = "6:3"  # „ANTI-FIGHTER BARRAGE 6 (x3)”
_TRIAD_BASE = 3  # „3 plus the number of different types of relic fragments you own”


def _src(relic_id: str) -> HookSource:
    return HookSource(SOURCE_RELIC, relic_id)


def _ready_ids(relic_id: str) -> Any:
    """Hook FORBID zwracający ``{relic_id}``, gdy relikt jest GOTOWY (wyczerpywany przy użyciu)."""

    def hook(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
        return {relic_id} if relics.is_ready(state, player_id, relic_id) else set()

    return hook


# --- Lightrail Ordnance ----------------------------------------------------------------------


@register(
    POINT_SPACE_CANNON_GRANTED, _src("lightrailordnance"), HookKind.FORBID,
    covers="relics:lightrailordnance",
)
def lightrail_ordnance(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> set[str]:
    """Lightrail Ordnance: Your space docks gain SPACE CANNON 5 (x2). You may use your space
    dock's SPACE CANNON against ships that are adjacent to their systems.

    Działa w Space Cannon Offense i Defense (C_relics); „deep” = strzał na sąsiednie systemy.
    """
    return {_LIGHTRAIL_GRANT}


# --- Metali Void Shielding -------------------------------------------------------------------


@register(
    POINT_COMBAT_GRANTED_SUSTAIN, _src("metalivoidshielding"), HookKind.PERMIT,
    covers="relics:metalivoidshielding",
)
def metali_void_shielding(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Metali Void Shielding: Each time hits are produced against 1 or more of your non-fighter
    ships, 1 of those ships may use SUSTAIN DAMAGE as if it had that ability.

    Gracz sam wskazuje statek w przypisaniu strat (``battle.plan_losses``: najwyżej 1 nadany).
    """
    return True


# --- Metali Void Armaments -------------------------------------------------------------------


@register(
    POINT_COMBAT_AFB_GRANTED, _src("metalivoidarmaments"), HookKind.FORBID,
    covers="relics:metalivoidarmaments",
)
def metali_void_armaments_grant(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> set[str]:
    return {_ARMAMENTS_GRANT}


def _space_combatant(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("kind") == "space" and player_id in (ctx.get("attacker"), ctx.get("defender"))


@on_event(
    GameEvent.COMBAT,
    Moment.START,
    _src("metalivoidarmaments"),
    optional=True,
    condition=_space_combatant,
    label="Metali Void Armaments: resolve ANTI-FIGHTER BARRAGE 6 (x3)",
)
def metali_void_armaments(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Metali Void Armaments: During the "Anti-Fighter Barrage" step of space combat, you may
    resolve ANTI-FIGHTER BARRAGE 6 (x3) against your opponent's units.

    Zgoda z oferty na starcie walki; rzut dopisuje ``battle.resolve_afb``.
    """
    del ctx
    combat = state.active_combat
    if combat is not None and player_id not in combat.afb_extra:
        combat.afb_extra = [*combat.afb_extra, player_id]


# --- The Crown of Thalnos / Heart of Ixth ----------------------------------------------------


@register(
    POINT_COMBAT_REROLL_PLUS_ONE, _src("thalnos"), HookKind.PERMIT, covers="relics:thalnos"
)
def crown_of_thalnos(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """The Crown of Thalnos: During each combat round, this card's owner may reroll any number of
    their dice, applying +1 to the results, any units that reroll dice but do not produce at
    least 1 hit are destroyed.

    Przerzut wykonuje ``battle_rerolls.reroll_with_relic`` (po rzucie, przed przypisaniem strat).
    """
    return True


register(POINT_DIE_ADJUST, _src("heartofixth"), HookKind.FORBID, covers="relics:heartofixth")(
    _ready_ids("heartofixth")
)
# Heart of Ixth: After any die is rolled, you may exhaust this card to add or subtract 1 from its
# result. Kości walki: ``battle_rerolls.adjust_die_with_relic`` (własne i przeciwnika,
# przed stratami).


# --- Scepter of Emelpar ----------------------------------------------------------------------

register(
    POINT_STRATEGY_TOKEN_FROM_REINFORCEMENTS, _src("emelpar"), HookKind.FORBID,
    covers="relics:emelpar",
)(_ready_ids("emelpar"))
# Scepter of Emelpar: When you would spend a token from your strategy pool, you may exhaust this
# card to spend a token from your reinforcements instead. Secondary karty strategii: parametr
# ``scepter`` w ``strategic_action`` (``command_tokens.spend_strategy_token``).


# --- The Prophet's Tears ---------------------------------------------------------------------

register(
    POINT_TECHNOLOGY_IGNORE_PREREQUISITE, _src("prophetstears"), HookKind.FORBID,
    covers="relics:prophetstears",
)(_ready_ids("prophetstears"))


def _own_research(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and relics.is_ready(state, player_id, "prophetstears")


@on_event(
    GameEvent.TECHNOLOGY_RESEARCH,
    Moment.WHEN,
    _src("prophetstears"),
    optional=True,
    condition=_own_research,
    covers="relics:prophetstears",
    label="The Prophet's Tears: exhaust to draw 1 action card",
)
def prophets_tears_draw(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The Prophet's Tears: When you research a technology, you may exhaust this card to ignore 1
    prerequisite or draw 1 action card.

    „Ignore 1 prerequisite" to skip ``relic:prophetstears`` w badaniu
    (``technology.plan_research``); tu druga opcja. Nie działa przy bezpośrednim zdobyciu
    technologii (C_relics).
    """
    del ctx
    if not relics.is_ready(state, player_id, "prophetstears"):
        raise ValueError("The Prophet's Tears is exhausted.")
    exhaust.exhaust_relic(state, player_id, "prophetstears")
    card_draw.draw_action_card(state, player_id)


# --- The Triad -------------------------------------------------------------------------------


@relic_planets.register("thetriad")
def triad_value(state: GameState, registry: Any, player_id: str) -> int:
    """The Triad: Its resource and influence values are equal to 3 plus the number of different
    types of relic fragments you own."""
    kinds: set[str] = set()
    for fragment in state.players[player_id].relic_fragments:
        card = registry.catalog.get(ComponentCategory.EXPLORATION, fragment)
        if isinstance(card, ExplorationDef) and card.type:
            kinds.add(card.type)
    return _TRIAD_BASE + len(kinds)


# The Triad: „This card can be readied and spent as if it were a planet card.” - płatności i
# głosowanie widzą pseudo-planetę ``relic:thetriad`` (``relic_planets``).
declare_data_driven("relics:thetriad")
