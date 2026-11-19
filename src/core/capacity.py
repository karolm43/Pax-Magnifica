"""Limit pojemności (capacity) w przestrzeni systemu i usuwanie nadwyżki (RULES.md 39.6).

- ``capacity_report`` — pojemność gracza w systemie (ogólna + „tylko myśliwce" z doku) i ładunek
  w przestrzeni (myśliwce, piechota, mechy) z wyliczoną nadwyżką (C1/C4);
- ``open_capacity_check`` — otwiera okno ``CAPACITY`` dla graczy z nadwyżką (C3);
- ``resolve_capacity`` — gracz usuwa wybrane jednostki (walidacja C2: dokładnie tyle, ile trzeba).

Funkcje CZYSTE (``state -> state`` przez klon). Walidacja twarda: ``ValueError`` → HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core import floating_structures, timing, unit_ops
from src.core.combat import resolve_unit_variant
from src.core.game_state import CombatStep, GameState, WindowType
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause

# Ładunek zajmujący pojemność (R_capacity: „fighters and ground forces"). Kolejność = wyświetlanie.
CARGO_TYPES: tuple[str, ...] = ("fighter", "infantry", "mech")
_FIGHTER = "fighter"
FIGHTER_II_ALIAS = "ff2"  # alias z technologies/pok.json
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
    # Fighter II: „fighters in excess of your ships' capacity count against your fleet pool"
    # (C_units, Fighter) - nadmiar myśliwców NIE jest wtedy usuwany z capacity, tylko liczy się
    # do fleet pool.
    fighters_overflow_to_fleet: bool = False

    @property
    def used(self) -> int:
        return sum(self.cost.get(bt, 1) * n for bt, n in self.cargo.items())

    def _ground_cost(self, cargo: dict[str, int]) -> int:
        return sum(self.cost.get(bt, 1) * n for bt, n in cargo.items() if bt != _FIGHTER)

    def excess_for(self, cargo: dict[str, int]) -> int:
        """Nadwyżka (w jednostkach pojemności) dla podanego ładunku.

        Z Fighter II nadmiar myśliwców nie jest nadwyżką capacity (idzie do fleet pool), więc
        liczy się tylko to, czego siły naziemne nie mieszczą w pojemności ogólnej.
        """
        if self.fighters_overflow_to_fleet:
            return max(0, self._ground_cost(cargo) - self.general)
        fighters = self.cost.get(_FIGHTER, 1) * cargo.get(_FIGHTER, 0)
        total = sum(self.cost.get(bt, 1) * n for bt, n in cargo.items())
        need = total - min(fighters, self.fighter_only)
        return max(0, need - self.general)

    @property
    def fleet_fighters(self) -> int:
        """Sztuki myśliwców ponad capacity, liczone do fleet pool (tylko z Fighter II).

        Siły naziemne mają pierwszeństwo do pojemności ogólnej; myśliwce wypełniają najpierw
        miejsca „tylko dla myśliwców" (doki), potem resztę pojemności ogólnej.
        """
        if not self.fighters_overflow_to_fleet:
            return 0
        each = max(self.cost.get(_FIGHTER, 1), 1)
        count = self.cargo.get(_FIGHTER, 0)
        room = self.fighter_only + max(0, self.general - self._ground_cost(self.cargo))
        return max(0, count - room // each)

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
    report.fighters_overflow_to_fleet = FIGHTER_II_ALIAS in techs

    for base_type, count in system.space_units.get(player_id, {}).items():
        if count <= 0:
            continue
        capacity, used, cost, name = _variant_value(registry, faction, techs, base_type)
        if floating_structures.ground_moves_as_ship(state, player_id, base_type):
            continue  # Eidolon Maximum: statek - liczy się do puli floty (RULES.md 62.15)
        if base_type in CARGO_TYPES:
            report.cargo[base_type] = count
            report.cost[base_type] = used
            report.unit_cost[base_type] = cost
            report.names[base_type] = name
        else:
            report.general += capacity * count
    if report.general <= 0:
        # Siła naziemna o zerowym capacityUsed (Aerie Sentinel) nie liczy się do pojemności tylko
        # przy statku gracza z pojemnością w tej przestrzeni (F_argent) - bez niego jak zwykle 1.
        for base_type in list(report.cost):
            if base_type != _FIGHTER and report.cost[base_type] <= 0:
                report.cost[base_type] = 1
    for by_player in system.planet_units.values():
        docks = by_player.get(player_id, {}).get(_SPACEDOCK, 0)
        if docks > 0:
            capacity, _, _, _ = _variant_value(registry, faction, techs, _SPACEDOCK)
            report.fighter_only += capacity * docks
    return report


def combat_in_progress(state: GameState, position: str) -> bool:
    """Czy w systemie ``position`` trwa walka (krok inny niż DONE) - RULES.md 39.6 C3.

    W trakcie walki myśliwce i siły naziemne nie liczą się do capacity, a nadmiar Fighter II do
    fleet pool (R_capacity / R_fleet_pool, Notes); oba limity wracają po zakończeniu walki.
    """
    combat = state.active_combat
    return (
        combat is not None and combat.position == position and combat.step is not CombatStep.DONE
    )


def players_with_excess(
    state: GameState, registry: StaticDataRegistry, position: str
) -> list[str]:
    """Gracze z nadwyżką w systemie — od aktywnego, zgodnie z kolejnością zasiadania.

    W trakcie walki w tym systemie nikt nie ma nadwyżki capacity (C3).
    """
    system = state.systems.get(position)
    if system is None or combat_in_progress(state, position):
        return []
    order = list(state.seating_order) or list(state.players)
    active = state.active_player_id
    if active in order:
        i = order.index(active)
        order = order[i:] + order[:i]
    # Neutralni nie mają puli floty ani capacity (R_neutral_units) - nigdy nie usuwają nadwyżki.
    order = [pid for pid in order if pid != NEUTRAL_PLAYER_ID]
    order += [pid for pid in system.space_units if pid not in order and pid != NEUTRAL_PLAYER_ID]
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
    new_state = remove_forced_excess(state, registry, position)
    choose = players_with_excess(new_state, registry, position)
    if not choose:
        return new_state
    return timing.open_window(
        new_state, WindowType.CAPACITY, choose, context={"position": position}
    )


def remove_forced_excess(
    state: GameState, registry: StaticDataRegistry, position: str
) -> GameState:
    """Usuwa nadwyżkę graczy, którzy NIE mają wyboru (jedyne legalne usunięcie wg C2 - np. same
    myśliwce bez pojemności), bez okna. „Must remove the excess units" (R_capacity) - gracz
    wybiera tylko, gdy ma z czego (RULES.md 39.6 C5, decyzja użytkownika 2026-11-18)."""
    new_state = state
    for pid in players_with_excess(state, registry, position):
        forced = forced_removal(capacity_report(new_state, registry, position, pid))
        if forced is None:
            continue
        if new_state is state:
            new_state = state.clone()
        system = new_state.systems[position]
        for base_type, count in forced.items():
            unit_ops.remove_units(
                new_state, system, "space", pid, base_type, count, UnitCause.REMOVED
            )
    return new_state


def _valid_removals(report: CapacityReport) -> list[dict[str, int]]:
    """Wszystkie legalne usunięcia nadwyżki (C2: likwidują ją i nic ponad potrzebę)."""
    types = [bt for bt in CARGO_TYPES if report.cargo.get(bt, 0) > 0]
    found: list[dict[str, int]] = []

    def walk(i: int, picked: dict[str, int]) -> None:
        if len(found) > 1:
            return  # dwie możliwości = wybór gracza; dalej liczyć nie trzeba
        if i == len(types):
            try:
                _check_removal(report, picked)
            except ValueError:
                return
            found.append({bt: n for bt, n in picked.items() if n > 0})
            return
        for n in range(report.cargo[types[i]] + 1):
            walk(i + 1, {**picked, types[i]: n})

    walk(0, {})
    return found


def forced_removal(report: CapacityReport) -> dict[str, int] | None:
    """Jedyne legalne usunięcie nadwyżki albo ``None``, gdy gracz ma realny wybór (lub brak
    nadwyżki)."""
    if report.excess <= 0:
        return None
    options = _valid_removals(report)
    return options[0] if len(options) == 1 else None


def auto_removal(report: CapacityReport) -> dict[str, int]:
    """Podpowiedź: usuń najpierw najtańsze jednostki, aż nadwyżka zniknie (⚠️ ZAŁOŻENIE 39.6)."""
    remaining = dict(report.cargo)
    removal: dict[str, int] = {}
    order = sorted(remaining, key=lambda bt: (report.unit_cost.get(bt, 0.0), bt))
    for base_type in order:
        while remaining.get(base_type, 0) > 0 and (before := report.excess_for(remaining)) > 0:
            remaining[base_type] -= 1
            if report.excess_for(remaining) >= before:
                # Ta jednostka nie zmniejsza nadwyżki (Fighter II: myśliwce idą do fleet pool).
                remaining[base_type] += 1
                break
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
            unit_ops.remove_units(
                new_state, system, "space", player_id, base_type, count, UnitCause.REMOVED
            )
    new_state = timing.respond_current(new_state, player_id)
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
        # Po capacity od razu sprawdzamy pulę floty w tym samym systemie (ograniczenia mają być
        # egzekwowane natychmiast, np. po produkcji Sling Relay poza krokiem akcji).
        from src.core import (
            fleet_pool,  # lokalnie: fleet_pool importuje capacity
            strategic_action,
        )

        new_state = fleet_pool.open_fleet_pool_check(new_state, position)
        new_state = strategic_action.resume_after_limit_window(new_state)
    return new_state
