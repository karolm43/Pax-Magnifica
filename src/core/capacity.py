"""Limit pojemności (capacity) w przestrzeni systemu i usuwanie nadwyżki (RULES.md 39.6).

- ``capacity_report`` — pojemność gracza w systemie (ogólna + „tylko myśliwce" z doku) i ładunek
  w przestrzeni (myśliwce, piechota, mechy) z wyliczoną nadwyżką (C1/C4);
- ``open_capacity_check`` — otwiera okno ``CAPACITY`` dla graczy z nadwyżką (C3);
- ``resolve_capacity`` — gracz usuwa wybrane jednostki (walidacja C2: dokładnie tyle, ile trzeba).

Funkcje CZYSTE (``state -> state`` przez klon). Walidacja twarda: ``ValueError`` → HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core import timing
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count, set_damaged
from src.core.game_state import GameState, SystemState, WindowType
from src.core.registry import StaticDataRegistry

# Ładunek zajmujący pojemność (R_capacity: „fighters and ground forces"). Kolejność = wyświetlanie.
CARGO_TYPES: tuple[str, ...] = ("fighter", "infantry", "mech")
_FIGHTER = "fighter"
_SPACEDOCK = "spacedock"


@dataclass
class CapacityReport:
    """Stan pojemności gracza w przestrzeni jednego systemu."""

    general: int = 0  # pojemność statków (i doku stojącego w przestrzeni — Saar)
    fighter_only: int = 0  # przydział doków na planetach — tylko dla myśliwców (C4)
    cargo: dict[str, int] = field(default_factory=dict)  # ładunek w przestrzeni
    cost: dict[str, int] = field(default_factory=dict)  # capacityUsed na sztukę
    unit_cost: dict[str, float] = field(default_factory=dict)  # koszt produkcji (podpowiedź)
    names: dict[str, str] = field(default_factory=dict)

    @property
    def used(self) -> int:
        return sum(self.cost.get(bt, 1) * n for bt, n in self.cargo.items())

    def excess_for(self, cargo: dict[str, int]) -> int:
        """Nadwyżka (w jednostkach pojemności) dla podanego ładunku."""
        fighters = self.cost.get(_FIGHTER, 1) * cargo.get(_FIGHTER, 0)
        total = sum(self.cost.get(bt, 1) * n for bt, n in cargo.items())
        need = total - min(fighters, self.fighter_only)
        return max(0, need - self.general)

    @property
    def excess(self) -> int:
        return self.excess_for(self.cargo)


def _variant_value(
    registry: StaticDataRegistry, faction: str | None, techs: list[str], base_type: str
) -> tuple[int, int, float, str]:
    """(capacityValue, capacityUsed, cost, nazwa) z wariantu gracza — zero liczb z pamięci."""
    unit = resolve_unit_variant(registry, faction, techs, base_type)
    if unit is None:
        return 0, 1, 0.0, base_type
    used = unit.capacity_used if unit.capacity_used is not None else 1
    return max(unit.capacity_value or 0, 0), max(used, 0), float(unit.cost or 0), unit.name


def capacity_report(
    state: GameState, registry: StaticDataRegistry, position: str, player_id: str
) -> CapacityReport:
    """Pojemność i ładunek gracza w przestrzeni systemu ``position`` (C1/C4)."""
    report = CapacityReport()
    system = state.systems.get(position)
    if system is None:
        return report
    player = state.players.get(player_id)
    faction = player.faction if player is not None else None
    techs = player.technologies if player is not None else []

    for base_type, count in system.space_units.get(player_id, {}).items():
        if count <= 0:
            continue
        capacity, used, cost, name = _variant_value(registry, faction, techs, base_type)
        if base_type in CARGO_TYPES:
            report.cargo[base_type] = count
            report.cost[base_type] = used
            report.unit_cost[base_type] = cost
            report.names[base_type] = name
        else:
            report.general += capacity * count
    for by_player in system.planet_units.values():
        docks = by_player.get(player_id, {}).get(_SPACEDOCK, 0)
        if docks > 0:
            capacity, _, _, _ = _variant_value(registry, faction, techs, _SPACEDOCK)
            report.fighter_only += capacity * docks
    return report


def players_with_excess(
    state: GameState, registry: StaticDataRegistry, position: str
) -> list[str]:
    """Gracze z nadwyżką w systemie — od aktywnego, zgodnie z kolejnością zasiadania."""
    system = state.systems.get(position)
    if system is None:
        return []
    order = list(state.seating_order) or list(state.players)
    active = state.active_player_id
    if active in order:
        i = order.index(active)
        order = order[i:] + order[:i]
    order += [pid for pid in system.space_units if pid not in order]
    return [
        pid
        for pid in order
        if pid in system.space_units and capacity_report(state, registry, position, pid).excess
    ]


def open_capacity_check(
    state: GameState, registry: StaticDataRegistry, position: str
) -> GameState:
    """Otwiera okno ``CAPACITY`` dla graczy z nadwyżką (C3).

    Bez nadwyżki albo gdy inne okno już trwa — stan bez zmian.
    """
    if state.pending_window is not None:
        return state
    queue = players_with_excess(state, registry, position)
    if not queue:
        return state
    return timing.open_window(
        state, WindowType.CAPACITY, queue, context={"position": position}
    )


def auto_removal(report: CapacityReport) -> dict[str, int]:
    """Podpowiedź: usuń najpierw najtańsze jednostki, aż nadwyżka zniknie (⚠️ ZAŁOŻENIE 39.6)."""
    remaining = dict(report.cargo)
    removal: dict[str, int] = {}
    order = sorted(remaining, key=lambda bt: (report.unit_cost.get(bt, 0.0), bt))
    for base_type in order:
        while remaining.get(base_type, 0) > 0 and report.excess_for(remaining) > 0:
            remaining[base_type] -= 1
            removal[base_type] = removal.get(base_type, 0) + 1
    return removal


def _check_removal(report: CapacityReport, remove: dict[str, int]) -> None:
    """C2: usunięcie likwiduje nadwyżkę i nie zabiera nic ponad potrzebę."""
    remaining = dict(report.cargo)
    for base_type, count in remove.items():
        if count <= 0:
            continue
        if base_type not in CARGO_TYPES:
            raise ValueError(
                f"Only fighters and ground forces count against capacity ({base_type})."
            )
        if count > remaining.get(base_type, 0):
            raise ValueError(f"You have only {remaining.get(base_type, 0)} {base_type} in space.")
        remaining[base_type] -= count
    if report.excess_for(remaining) > 0:
        raise ValueError(
            f"Still over capacity - remove more units ({report.excess_for(remaining)} left)."
        )
    for base_type, count in remove.items():
        if count <= 0:
            continue
        back = dict(remaining)
        back[base_type] = back.get(base_type, 0) + 1
        if report.excess_for(back) == 0:
            raise ValueError("You are removing more units than the capacity limit requires.")


def remove_space_units(
    system: SystemState, player_id: str, base_type: str, count: int
) -> None:
    units = system.space_units.get(player_id, {})
    left = units.get(base_type, 0) - count
    if left > 0:
        units[base_type] = left
    else:
        units.pop(base_type, None)
    if not units:
        system.space_units.pop(player_id, None)
    # Uszkodzenia nie mogą przekraczać liczby jednostek (mech z Sustain Damage).
    set_damaged(
        system, "space", player_id, base_type, damaged_count(system, "space", player_id, base_type)
    )


def resolve_capacity(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    remove: dict[str, int],
) -> GameState:
    """Gracz usuwa nadwyżkę ładunku z przestrzeni systemu z okna ``CAPACITY`` (C2).

    Raises:
        ValueError: Brak okna, nie kolej gracza, zły wybór (za mało / za dużo / zły typ).
    """
    window = state.pending_window
    if window is None or window.window_type is not WindowType.CAPACITY:
        raise ValueError("No capacity check is pending.")
    if window.current_responder != player_id:
        raise ValueError(
            f"It is now {window.current_responder}'s turn to remove excess units, not {player_id}."
        )
    position = str(window.context.get("position", ""))
    report = capacity_report(state, registry, position, player_id)
    _check_removal(report, remove)

    new_state = state.clone()
    system = new_state.systems[position]
    for base_type, count in remove.items():
        if count > 0:
            remove_space_units(system, player_id, base_type, count)
    new_state = timing.respond_current(new_state, player_id)
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
    return new_state
