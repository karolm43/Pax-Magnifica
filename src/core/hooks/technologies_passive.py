"""Hooki technologii pasywnych i obowiązkowych (bez wyboru gracza) — RULES.md 55.8.

Części „you may” tych samych kart (np. Self-Assembly: postawienie mecha) wymagają okna wyboru;
dopóki go nie ma, kart z niezamodelowaną częścią NIE oznaczamy jako pokrytych (brak ``covers``),
mimo że część pasywna działa.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import dice, economy, rules_hooks, unit_ops
from src.core.dice import DIE_SIDES, count_hits
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.rules_hooks import (
    POINT_RETREAT_ANYWHERE,
    POINT_TECHNOLOGY_SPECIALTY_FREE,
    SOURCE_TECHNOLOGY,
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


def _place_revived_infantry(state: GameState, player_id: str) -> None:
    """Początek tury: piechota z karty wraca na planetę gracza w systemie domowym.

    Gdy gracz nie kontroluje żadnej planety w systemie domowym, jednostki wracają do rezerwy
    (C_units: Infantry). ⚠ ZAŁOŻENIE (RULES.md 55.8): planeta wybierana automatycznie
    (pierwsza alfabetycznie), do czasu okna wyboru w UI.
    """
    player = state.players[player_id]
    waiting = player.infantry_ii_on_card
    if waiting <= 0:
        return
    player.infantry_ii_on_card = 0
    home = state.systems.get(player.home_position or "")
    if home is None:
        return
    planets = sorted(p for p, owner in home.planet_owners.items() if owner == player_id)
    if planets:
        unit_ops.place_units(state, home, planets[0], player_id, "infantry", waiting)


@on_event(
    GameEvent.TURN,
    Moment.START,
    _source(INFANTRY_II_ALIAS),
    condition=_own_event,
    covers=f"technologies:{INFANTRY_II_ALIAS}",
    label="Infantry II: return",
)
def infantry_ii_return_on_turn(
    state: GameState, player_id: str, _ctx: Mapping[str, Any]
) -> None:
    """Infantry II: na początku Twojej tury piechota z karty trafia do systemu domowego."""
    _place_revived_infantry(state, player_id)


@on_event(
    GameEvent.PHASE,
    Moment.START,
    _source(INFANTRY_II_ALIAS),
    where={"phase": "action"},
    condition=lambda state, pid, _ctx: state.active_player_id == pid,
    covers=f"technologies:{INFANTRY_II_ALIAS}",
    label="Infantry II: return (first turn)",
)
def infantry_ii_return_on_first_turn(
    state: GameState, player_id: str, _ctx: Mapping[str, Any]
) -> None:
    """To samo dla pierwszej tury fazy akcji (tam nie odpala się zdarzenie TURN START)."""
    _place_revived_infantry(state, player_id)
