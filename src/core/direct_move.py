"""Ruch statków komponentem „prosto do celu” poza zwykłym ruchem taktycznym (RULES.md 62.11/62.12).

Wspólne dla bohaterów i przełomów, które przenoszą statki bez trasy: Helix Protocol i Wing
Transfer (Argent), Dark Space Navigation (L1Z1X). Formularz = ``oi.unit_moves`` (przeciąganie
jednostek na mapie na świecące cele, jak ruch taktyczny).

Reguły wspólne (F_argent, F_lizix + ruling użytkownika 2026-11-18): statki lecą prosto do celu
i zabierają ładunek tylko z systemu, z którego wyruszają; przy ruchu ZDOLNOŚCIĄ (L1Z1X Hero,
Argent Hero, Mahact Hero) wolno transportować jednostki także z systemu z własnym żetonem
dowodzenia; wyjście ze szczeliny grawitacyjnej = rzut na usunięcie. Pojemność po ruchu
egzekwuje ``limits.enforce_limits`` po akcji (R_capacity: ruch może spowodować usunięcie).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import movement, unit_ops
from src.core import offer_inputs as oi
from src.core.fleet_pool import unit_name
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry
from src.core.state_grid import grid_from_state
from src.core.unit_ops import UnitCause

GROUND_FORCES = ("infantry", "mech")
SPACE = "space"


def ship_options(
    state: GameState,
    registry: Any,
    player_id: str,
    sources: list[str],
    *,
    only: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Jednostki gracza w przestrzeni systemów ``sources`` - każdy egzemplarz osobno (mapa).

    ``only`` - typy, które w ogóle mogą ruszyć (np. flagowiec, pancerniki i ich ładunek)."""
    options: list[dict[str, Any]] = []
    for position in sources:
        system = state.systems.get(position)
        for bt, n in sorted((system.space_units.get(player_id, {}) if system else {}).items()):
            if only is not None and bt not in only:
                continue
            name = unit_name(state, registry, player_id, bt)
            for i in range(n):
                options.append(oi.option(
                    f"{position}|{bt}|{i}", name,
                    meta=oi.unit_at(state, player_id, bt, position=position),
                ))
    return options


def move_inputs(
    state: GameState,
    registry: Any,
    player_id: str,
    sources: list[str],
    dests: list[str],
    *,
    only: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Formularz ruchu: przeciąganie jednostek na mapie na świecące cele (``oi.unit_moves``)."""
    ships = ship_options(state, registry, player_id, sources, only=only)
    return [oi.unit_moves("moves", "Move ships", ships, dests)]


def parse_moves(params: Mapping[str, Any]) -> dict[str, dict[str, dict[str, int]]]:
    """``{cel: {źródło: {typ: n}}}`` z ``moves`` (``"<źródło>|<typ>|<n>><cel>"``)."""
    seen: set[str] = set()
    moves: dict[str, dict[str, dict[str, int]]] = {}
    for raw in params.get("moves") or []:
        unit, dest = oi.split_move(str(raw))
        if unit in seen:
            raise ValueError("A unit cannot move to two systems.")
        seen.add(unit)
        source, bt, _ = unit.split("|")
        by_type = moves.setdefault(dest, {}).setdefault(source, {})
        by_type[bt] = by_type.get(bt, 0) + 1
    return moves


def apply_moves(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    moves: dict[str, dict[str, dict[str, int]]],
    *,
    fighters_free: bool,
    carriers: tuple[str, ...] | None = None,
) -> None:
    """Przenosi jednostki (MUTUJE): rzut szczeliny grawitacyjnej przy wyjściu.

    ``fighters_free`` - myśliwce lecą bez transportu (Helix Protocol); ``carriers`` - typy
    statków, które mogą ruszyć i zabrać ładunek (``None`` = każdy statek). Ładunek (siły naziemne,
    myśliwce bez ``fighters_free``) leci tylko ze statkiem z tego samego systemu źródłowego
    (F_argent, F_lizix: „They may only transport units from their origin system”)."""
    grid = grid_from_state(state, registry)
    carried = GROUND_FORCES if fighters_free else (*GROUND_FORCES, "fighter")
    for dest, by_source in sorted(moves.items()):
        target = state.systems.get(dest)
        if target is None:
            raise ValueError(f"Unknown system {dest}.")
        for source, by_type in sorted(by_source.items()):
            origin = state.systems.get(source)
            if origin is None or source == dest:
                raise ValueError("Units must move to another system.")
            own = origin.space_units.get(player_id, {})
            for bt, n in by_type.items():
                if own.get(bt, 0) < n:
                    raise ValueError(f"Not enough {bt} in system {source}.")
            cargo = {bt: n for bt, n in by_type.items() if bt in carried}
            ships = {bt: n for bt, n in by_type.items() if bt not in GROUND_FORCES}
            movers = {bt: n for bt, n in ships.items() if bt not in cargo}
            if carriers is not None and any(bt not in carriers for bt in movers):
                raise ValueError("Only the listed ships can move with this ability.")
            if cargo and not any(n > 0 and bt != "fighter" for bt, n in movers.items()):
                raise ValueError("Units without a move value must be transported by ships moving "
                                 "with them.")
            lost: dict[str, int] = {}
            if movement.is_gravity_rift(grid, source):
                lost = movement.roll_rift_exit(state, player_id, ships, source)
            for bt, n in by_type.items():
                unit_ops.transfer_units(state, origin, SPACE, target, SPACE, player_id, bt, n)
            for bt, n in lost.items():
                unit_ops.remove_units(state, target, SPACE, player_id, bt, n, UnitCause.DESTROYED)
            arrived = {bt: n - lost.get(bt, 0) for bt, n in ships.items()}
            movement.fire_ships_moved(state, player_id, dest, source, arrived, kind="direct")
