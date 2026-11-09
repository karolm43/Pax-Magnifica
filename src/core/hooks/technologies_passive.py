"""Hooki technologii pasywnych i obowiązkowych (bez wyboru gracza) — RULES.md 55.8.

Części „you may” tych samych kart (np. Self-Assembly: postawienie mecha) wymagają okna wyboru;
dopóki go nie ma, kart z niezamodelowaną częścią NIE oznaczamy jako pokrytych (brak ``covers``),
mimo że część pasywna działa.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import dice, economy, rules_hooks, unit_ops
from src.core import offer_inputs as oi
from src.core.dice import DIE_SIDES, count_hits
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.rules_hooks import (
    POINT_RETREAT_ANYWHERE,
    POINT_TECHNOLOGY_SPECIALTY_FREE,
    SOURCE_TECHNOLOGY,
    ConditionFn,
    HookKind,
    HookSource,
    on_event,
    register,
)

DARK_ENERGY_TAP_ALIAS = "det"
PSYCHOARCHAEOLOGY_ALIAS = "pa"
SELF_ASSEMBLY_ALIAS = "sar"
INFANTRY_II_ALIAS = "inf2"

# Próg odrodzenia Infantry II: „If the result is 6 or greater" (tekst karty w assetach).
_INFANTRY_II_REVIVE_ON = 6

rules_hooks.declare_data_driven("technologies:sd2", "technologies:dn2")


def _source(alias: str) -> HookSource:
    return HookSource(SOURCE_TECHNOLOGY, alias)


def _own_event(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Warunek: zdarzenie dotyczy gracza-właściciela hooka (ctx['player'])."""
    return ctx.get("player") == player_id


# --- Dark Energy Tap: odwrót ---------------------------------------------------------------


@register(POINT_RETREAT_ANYWHERE, _source(DARK_ENERGY_TAP_ALIAS), HookKind.PERMIT)
def dark_energy_tap_retreat(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> bool:
    """Dark Energy Tap: statki mogą wycofać się do sąsiedniego systemu bez cudzych jednostek.

    ⚠ Część „zbadaj żeton frontier po akcji taktycznej” wymaga eksploracji frontier (RULES.md
    46.3 - poza zakresem), więc karta NIE jest oznaczona jako pokryta.
    """
    return True


# --- Psychoarchaeology: specjalności -----------------------------------------------------


@register(POINT_TECHNOLOGY_SPECIALTY_FREE, _source(PSYCHOARCHAEOLOGY_ALIAS), HookKind.PERMIT)
def psychoarchaeology_specialties(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> bool:
    """Psychoarchaeology: specjalności technologii działają bez wyczerpywania planet, także
    wyczerpanych. ⚠ Część „wyczerp planetę → 1 TG w fazie akcji” wymaga akcji gracza (UI).
    """
    return True


# --- Self-Assembly Routines: handel za mecha -----------------------------------------------


@on_event(
    GameEvent.UNIT_DESTROYED,
    Moment.AFTER,
    _source(SELF_ASSEMBLY_ALIAS),
    where={"base_type": "mech"},
    condition=_own_event,
    label="Self-Assembly Routines: trade good",
)
def self_assembly_trade_good(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Self-Assembly Routines: po zniszczeniu Twojego mecha zdobywasz 1 TG (za każdego mecha;
    także gdy karta jest wyczerpana - C_technology).

    ⚠ Część „postaw mecha po PRODUCTION (wyczerp kartę)” wymaga okna wyboru - niezamodelowana.
    """
    economy.gain_trade_goods(state, player_id, int(ctx.get("count", 1)))


# --- Infantry II: odrodzenie ----------------------------------------------------------------


@on_event(
    GameEvent.UNIT_DESTROYED,
    Moment.AFTER,
    _source(INFANTRY_II_ALIAS),
    where={"base_type": "infantry"},
    condition=_own_event,
    covers=f"technologies:{INFANTRY_II_ALIAS}",
    label="Infantry II: revive roll",
)
def infantry_ii_revive_roll(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Infantry II: po zniszczeniu piechoty rzuć kością; przy 6+ jednostka trafia na kartę.

    Rzut jest fizyczną kością na stole (``dice.record_table_roll``); wynik liczy silnik.
    """
    rolls = int(ctx.get("count", 1))
    rng = dice.next_rng(state)
    results = [rng.randint(1, DIE_SIDES) for _ in range(rolls)]
    revived = count_hits(results, _INFANTRY_II_REVIVE_ON)
    state.players[player_id].infantry_ii_on_card += revived
    dice.record_table_roll(
        state, player_id, "infantry_ii", "Infantry II", results,
        hits_on=_INFANTRY_II_REVIVE_ON,
        summary=f"{revived} infantry placed on the Infantry II card" if revived else "",
    )


def _home_planets(state: GameState, player_id: str) -> list[str]:
    """Planety kontrolowane przez gracza w jego systemie domowym."""
    player = state.players[player_id]
    home = state.systems.get(player.home_position or "")
    if home is None:
        return []
    return sorted(p for p, owner in home.planet_owners.items() if owner == player_id)


def _returns_now(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return state.players[player_id].infantry_ii_on_card > 0 and bool(
        _home_planets(state, player_id)
    )


def _no_home_planet(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return state.players[player_id].infantry_ii_on_card > 0 and not _home_planets(
        state, player_id
    )


def infantry_ii_inputs(
    state: GameState, registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Wybór gracza: na której planecie w systemie domowym stawia piechotę z karty."""
    return [
        oi.choice(
            "planet",
            "Home-system planet for the infantry on your Infantry II card",
            [
                oi.option(p, registry.planets[p].name if p in registry.planets else p)
                for p in _home_planets(state, player_id)
            ],
        )
    ]


def infantry_ii_place(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Piechota z karty Infantry II trafia na wybraną planetę w systemie domowym."""
    player = state.players[player_id]
    planet = ctx.get("params", {}).get("planet")
    home = state.systems.get(player.home_position or "")
    if planet is None or home is None or player.infantry_ii_on_card <= 0:
        return
    waiting = player.infantry_ii_on_card
    player.infantry_ii_on_card = 0
    unit_ops.place_units(state, home, planet, player_id, "infantry", waiting)


def infantry_ii_to_reserve(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Bez kontrolowanej planety w systemie domowym piechota z karty wraca do rezerwy
    (C_units: Infantry)."""
    state.players[player_id].infantry_ii_on_card = 0


def _first_action_turn(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return state.active_player_id == player_id


def _both(first: ConditionFn, second: ConditionFn) -> ConditionFn:
    """Warunek hooka: oba warunki naraz."""

    def condition(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
        return first(state, player_id, ctx) and second(state, player_id, ctx)

    return condition


# Początek Twojej tury (TURN START) oraz początek pierwszej tury fazy akcji (PHASE START - tam
# nie odpala się TURN START). Obie ścieżki: wybór planety przez gracza / zwrot do rezerwy.
for _event, _moment, _where, _owns_turn in (
    (GameEvent.TURN, Moment.START, None, _own_event),
    (
        GameEvent.PHASE,
        Moment.START,
        {"phase": "action"},
        _first_action_turn,
    ),
):
    on_event(
        _event, _moment, _source(INFANTRY_II_ALIAS), where=_where,
        condition=_both(_owns_turn, _returns_now),
        covers=f"technologies:{INFANTRY_II_ALIAS}", label="Infantry II: return",
        inputs=infantry_ii_inputs, decide=True,
    )(infantry_ii_place)
    on_event(
        _event, _moment, _source(INFANTRY_II_ALIAS), where=_where,
        condition=_both(_owns_turn, _no_home_planet),
        covers=f"technologies:{INFANTRY_II_ALIAS}", label="Infantry II: reserve",
    )(infantry_ii_to_reserve)
