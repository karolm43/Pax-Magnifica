"""Wspólne narzędzia efektów kart agendy (RULES.md 51.6).

Efekt WYNIKU agendy = hook zdarzenia ``AGENDA_OUTCOME_RESOLVED``/DURING ze źródłem
``HookSource(agenda, <id>)``. Źródło posiada KAŻDY gracz: prawo w grze (``decks.agenda_laws``) albo
karta właśnie rozstrzygana (``agenda.resolving``, także dyrektywa i „Against"). Hook dostaje
``ctx = {agenda, outcome, kind, previous, speaker}`` i jest wołany raz na gracza w kolejności od
mówcy; efekty „jednorazowe" (nie „each player") biegną tylko u mówcy (``once=True``).

Wybory graczy = decyzje obowiązkowe (``decide=True``) albo oferty „you may" (``optional=True``) -
istniejące okno ofert (RULES.md 56). Mówca nie przejdzie dalej, dopóki decyzje czekają.

Efekty odroczone („at the start of the next strategy phase…") to efekty trwałe
(``active_effects``) z kluczem ``agendas:<id>:<wariant>``, każdy dla jednego gracza; hook efektu
zdejmuje go po wykonaniu.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from src.core import active_effects, objectives, rules_hooks, unit_ops
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, SystemState
from src.core.hooks.action_card_inputs import Input, _option, _planet_label
from src.core.offer_inputs import multi, unit_at
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    SOURCE_AGENDA,
    SOURCE_EFFECT,
    ConditionFn,
    HookFn,
    HookSource,
    OfferInputsFn,
    on_event,
)
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

GROUND_FORCES = ("infantry", "mech")


def covers(card: str) -> str:
    return f"agendas:{card}"


def agenda_source(card: str) -> HookSource:
    """Źródło hooków agendy (prawo w grze albo karta rozstrzygana)."""
    return HookSource(SOURCE_AGENDA, card)


def effect_key(card: str, variant: str) -> str:
    """Klucz efektu trwałego agendy (``agendas:<id>:<wariant>``)."""
    return f"agendas:{card}:{variant}"


def effect_source(card: str, variant: str) -> HookSource:
    return HookSource(SOURCE_EFFECT, effect_key(card, variant))


def _is_speaker(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return player_id == ctx.get("speaker")


def _both(first: ConditionFn | None, second: ConditionFn | None) -> ConditionFn | None:
    if first is None or second is None:
        return first or second

    def combined(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
        return first(state, player_id, ctx) and second(state, player_id, ctx)

    return combined


def on_outcome(
    card: str,
    *,
    outcome: str | None = None,
    once: bool = False,
    decide: bool = False,
    optional: bool = False,
    inputs: OfferInputsFn | None = None,
    condition: ConditionFn | None = None,
    label: str = "",
    moment: Moment = Moment.DURING,
) -> Callable[[HookFn], HookFn]:
    """Hook efektu wyniku ``card`` (``outcome`` = filtr ``for``/``against``; brak = każdy wynik)."""
    where = {"agenda": card}
    if outcome is not None:
        where["outcome"] = outcome
    return on_event(
        GameEvent.AGENDA_OUTCOME_RESOLVED,
        moment,
        agenda_source(card),
        where=where,
        covers=covers(card),
        condition=_both(_is_speaker if once else None, condition),
        decide=decide,
        optional=optional,
        inputs=inputs,
        label=label or card,
    )


def elected(ctx: Mapping[str, Any]) -> str:
    return str(ctx.get("outcome") or "")


def is_elected(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Warunek: hook biegnie u wybranego gracza (Elect Player)."""
    return player_id == ctx.get("outcome")


def schedule(
    state: GameState,
    card: str,
    variant: str,
    player_id: str,
    *,
    scope: Duration = Duration.GAME,
    **data: Any,
) -> None:
    """Efekt odroczony agendy dla gracza (zdejmuje go hook efektu; ``scope`` = najpóźniej kiedy)."""
    active_effects.add_effect(
        state, effect_key(card, variant), scope, owner=player_id, data=dict(data)
    )


def finish(state: GameState, card: str, variant: str, player_id: str) -> None:
    """Zdejmuje efekt odroczony gracza (wykonany)."""
    active_effects.remove_by_key(state, effect_key(card, variant), owner=player_id)


def lose_points(
    state: GameState, player_id: str, points: int, *, source: str | None = None
) -> None:
    """Utrata punktów (nie poniżej zera) przez centralny ``award_points`` (``source`` = rejestr)."""
    have = state.players[player_id].victory_points
    lost = min(points, have)
    if lost > 0:
        objectives.award_points(state, player_id, -lost, source=source)


def most_and_fewest(state: GameState) -> tuple[list[str], list[str]]:
    """Gracze z najwięcej i najmniej punktami; kolejność od mówcy (C_agendas)."""
    from src.core import strategy_phase  # lokalnie: strategy_phase -> triggers -> hooki

    order = strategy_phase.speaker_order(state)
    points = {pid: state.players[pid].victory_points for pid in order}
    if not points:
        return [], []
    top, bottom = max(points.values()), min(points.values())
    return [p for p in order if points[p] == top], [p for p in order if points[p] == bottom]


# --- Jednostki: wybór „których N zniszczyć" ---------------------------------------------------


def unit_instances(
    state: GameState,
    player_id: str,
    *,
    positions: list[str] | None = None,
    base_types: tuple[str, ...] | None = None,
    zone_filter: Callable[[str], bool] | None = None,
) -> list[tuple[str, str, str]]:
    """Pojedyncze jednostki gracza: ``[(pozycja, strefa, typ)]`` (jedna krotka na sztukę)."""
    found: list[tuple[str, str, str]] = []
    for position in positions if positions is not None else list(state.systems):
        system = state.systems.get(position)
        if system is None:
            continue
        zones: list[tuple[str, dict[str, int]]] = [("space", system.space_units.get(player_id, {}))]
        zones += [
            (planet, units.get(player_id, {})) for planet, units in system.planet_units.items()
        ]
        for zone, units in zones:
            if zone_filter is not None and not zone_filter(zone):
                continue
            for base_type, count in sorted(units.items()):
                if base_types is not None and base_type not in base_types:
                    continue
                found.extend((position, zone, base_type) for _ in range(count))
    return found


def unit_options(
    state: GameState,
    registry: StaticDataRegistry,
    units: list[tuple[str, str, str]],
    player_id: str,
) -> list[dict[str, Any]]:
    """Opcje formularza: jedna na sztukę (``value`` = ``pozycja|strefa|typ|n``), z ``unit_at``
    (UI: system na mapie, potem licznik każdego typu jednostki - nie lista „carrier #1”)."""
    options: list[dict[str, Any]] = []
    seen: dict[tuple[str, str, str], int] = {}
    for position, zone, base_type in units:
        n = seen.get((position, zone, base_type), 0)
        seen[(position, zone, base_type)] = n + 1
        where = "space" if zone == "space" else _planet_label(state, registry, zone)
        name = unit_name(state, registry, player_id, base_type)
        meta = unit_at(
            state, player_id, base_type, position=position,
            planet=None if zone == "space" else zone,
        )
        options.append(_option(
            f"{position}|{zone}|{base_type}|{n}", f"{name} - {where} ({position})", meta=meta
        ))
    return options


def destroy_choice_input(
    state: GameState,
    registry: StaticDataRegistry,
    units: list[tuple[str, str, str]],
    count: int,
    player_id: str,
    key: str = "units",
    label: str = "Units to destroy",
) -> list[Input]:
    """Wejście „wybierz dokładnie ``count`` sztuk"; pusta lista, gdy wybór nic nie zmienia."""
    if count <= 0 or len(units) <= count or len(set(units)) <= 1:
        return []
    return [multi(key, label, unit_options(state, registry, units, player_id), count, count)]


def destroy_units(
    state: GameState,
    player_id: str,
    picks: list[tuple[str, str, str]],
    cause: UnitCause = UnitCause.DESTROYED,
) -> int:
    """Niszczy wskazane sztuki (centralne ``unit_ops.remove_units``); zwraca liczbę zniszczonych."""
    grouped: dict[tuple[str, str, str], int] = {}
    for pick in picks:
        grouped[pick] = grouped.get(pick, 0) + 1
    destroyed = 0
    for (position, zone, base_type), count in grouped.items():
        system = state.systems.get(position)
        if system is None:
            continue
        before = unit_ops.remove_units(state, system, zone, player_id, base_type, count, cause)
        destroyed += min(before, count)
    return destroyed


def chosen_units(
    params: Mapping[str, Any], available: list[tuple[str, str, str]], count: int, key: str = "units"
) -> list[tuple[str, str, str]]:
    """Sztuki z odpowiedzi gracza; bez realnego wyboru - pierwsze ``count`` z ``available``."""
    raw = params.get(key)
    if not isinstance(raw, list) or not raw:
        return available[:count]
    picks: list[tuple[str, str, str]] = []
    for value in raw:
        position, zone, base_type, _n = str(value).split("|")
        picks.append((position, zone, base_type))
    return picks


def ships_of(system: SystemState, player_id: str) -> dict[str, int]:
    """Statki gracza w przestrzeni systemu (bez sił naziemnych na pokładzie)."""
    return {
        b: n for b, n in system.space_units.get(player_id, {}).items()
        if n > 0 and is_space_unit(b)
    }


def bound_registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data is not bound.")
    return registry  # type: ignore[no-any-return]
