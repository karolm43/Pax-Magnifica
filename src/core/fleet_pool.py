"""Fleet pool: limit statków nie-myśliwskich w systemie i usuwanie nadwyżki (RULES.md 42).

Źródło: ``docs/rules_tirules/R_fleet_pool.md``. Liczba żetonów w puli floty (``fleet_cc``) to
maksymalna liczba statków NIE-myśliwskich gracza w jednym systemie. Nadwyżkę gracz wybiera i
zwraca do rezerwy „w każdej chwili" — ale ruch/produkcja/umieszczenie WOLNO wykonać mimo
przekroczenia (statki trzeba usunąć zaraz po). Dlatego silnik nie blokuje akcji, tylko:

- ``fleet_report`` — stan puli w systemie (do OSTRZEŻENIA przed i w trakcie akcji);
- ``open_fleet_pool_check`` — otwiera okno ``FLEET_POOL`` dla graczy z nadwyżką (wołane przed
  przejściem kroku akcji taktycznej: po ruchu, produkcji, walce);
- ``resolve_fleet_pool`` — gracz wskazuje, które statki wracają do rezerwy (dokładnie tyle,
  ile trzeba).

Myśliwce i siły naziemne NIE liczą się do fleet pool (liczą się do capacity — RULES.md 39.6).
WYJĄTEK - Fighter II: myśliwce ponad capacity liczą się do fleet pool (zamiast być usuwane);
Hybrid Crystal Fighter II (Naalu): 2 takie myśliwce = 1 statek (``fighters_per_ship``, 62.16).
Statki przewożone w ruchu i jednostki na planetach też nie. Funkcje CZYSTE (``state -> state``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core import capacity, timing, unit_ops
from src.core.combat import resolve_unit_variant
from src.core.game_state import GameState, WindowType
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import PLACEMENT_BY_BASE_TYPE, Placement
from src.core.unit_ops import UnitCause

_FIGHTER = "fighter"


def counts_toward_pool(base_type: str) -> bool:
    """Czy typ liczy się do fleet pool: statek w przestrzeni, ale nie myśliwiec."""
    return base_type != _FIGHTER and PLACEMENT_BY_BASE_TYPE.get(base_type) is Placement.SPACE


def _pool_unit(state: GameState, player_id: str, base_type: str) -> bool:
    """Statek niemyśliwski albo siła naziemna, która jest statkiem (Eidolon Maximum)."""
    from src.core import floating_structures  # lokalnie: unika cyklu importów

    return counts_toward_pool(base_type) or floating_structures.ground_moves_as_ship(
        state, player_id, base_type
    )


@dataclass
class FleetReport:
    """Stan fleet pool gracza w jednym systemie."""

    pool: int = 0  # żetony w puli floty = maks. liczba statków
    # Statki liczone do puli, wg typu; ``fighter`` = SZTUKI myśliwców ponad pojemność.
    ships: dict[str, int] = field(default_factory=dict)
    # Ile myśliwców ponad pojemność liczy się razem jako 1 statek (HCF II: 2 - „1/2 of a ship”).
    fighters_per_ship: int = 1
    # „not limited by the number of command tokens in your fleet pool” (Darktalon Treilla):
    # limit nie obowiązuje. ``pool`` zostaje prawdziwą liczbą żetonów (do wyświetlenia) —
    # NIE podmieniamy jej na sztuczną wielką liczbę.
    unlimited: bool = False

    def total_after(self, remove: dict[str, int] | None = None) -> int:
        """Statki liczone do puli po zdjęciu ``remove`` (myśliwce ważone, w górę)."""
        gone = remove or {}
        ships = sum(
            max(0, n - gone.get(bt, 0)) for bt, n in self.ships.items() if bt != _FIGHTER
        )
        fighters = max(0, self.ships.get(_FIGHTER, 0) - gone.get(_FIGHTER, 0))
        per_ship = max(1, self.fighters_per_ship)
        return ships + -(-fighters // per_ship)

    def excess_after(self, remove: dict[str, int] | None = None) -> int:
        if self.unlimited:
            return 0
        return max(0, self.total_after(remove) - self.pool)

    @property
    def total(self) -> int:
        return self.total_after()

    @property
    def excess(self) -> int:
        return self.excess_after()


def _registry_or_bound(registry: StaticDataRegistry | None) -> StaticDataRegistry | None:
    if registry is not None:
        return registry
    from src.core import rules_hooks  # lokalnie: unika cyklu importów

    bound: StaticDataRegistry | None = rules_hooks.bound_registry()
    return bound


def _overflow_fighters(
    state: GameState, registry: StaticDataRegistry | None, position: str, player_id: str
) -> int:
    """Fighter II: myśliwce ponad capacity liczą się do fleet pool (C_units, Fighter).

    W trakcie walki w tym systemie - nie: „any number of Fighter II may be in a system during
    combat, regardless of capacity and fleet pool" (R_fleet_pool, Notes). Statki nie-myśliwskie
    liczą się do puli zawsze (RULES.md 42.1).
    """
    if not capacity.fighters_overflow_to_fleet(state, player_id):
        return 0
    if capacity.combat_in_progress(state, position):
        return 0
    reg = _registry_or_bound(registry)
    if reg is None:
        return 0
    return capacity.capacity_report(state, reg, position, player_id).fleet_fighters


def fleet_report(
    state: GameState,
    position: str,
    player_id: str,
    registry: StaticDataRegistry | None = None,
) -> FleetReport:
    """Pula floty i statki gracza w przestrzeni systemu ``position``.

    Z Fighter II do ``ships`` wchodzą też myśliwce ponad capacity (klucz ``fighter``).
    """
    player = state.players.get(player_id)
    report = FleetReport(pool=player.fleet_cc if player is not None else 0)
    # Hooki: Armada (+2 w każdym systemie), Darktalon Treilla (bez limitu) — RULES.md 62.2.
    from src.core import rules_hooks  # lokalnie: unika cyklu importów

    if player is not None:
        report.pool += rules_hooks.modify(
            rules_hooks.POINT_FLEET_POOL_CAPACITY, state, player_id, 0, {"position": position}
        )
        if rules_hooks.permits(rules_hooks.POINT_FLEET_POOL_UNLIMITED, state, player_id):
            report.unlimited = True
    system = state.systems.get(position)
    if system is None:
        return report
    for base_type, count in system.space_units.get(player_id, {}).items():
        if count > 0 and _pool_unit(state, player_id, base_type):
            report.ships[base_type] = count
    overflow = _overflow_fighters(state, registry, position, player_id)
    if overflow > 0:
        report.ships[_FIGHTER] = overflow
        report.fighters_per_ship = fighters_per_ship(state, player_id)
    return report


def fighters_per_ship(state: GameState, player_id: str) -> int:
    """Ile myśliwców ponad pojemność liczy się jako 1 statek puli floty (baza 1, HCF II: 2)."""
    from src.core import rules_hooks  # lokalnie: unika cyklu importów

    return max(1, 1 + rules_hooks.modify(
        rules_hooks.POINT_FLEET_POOL_FIGHTERS_PER_SHIP, state, player_id, 0
    ))


def unit_cost(
    state: GameState, registry: StaticDataRegistry, player_id: str, base_type: str
) -> float:
    """Koszt wariantu jednostki gracza (do podpowiedzi „usuń najtańsze")."""
    player = state.players.get(player_id)
    faction = player.faction if player is not None else None
    techs = player.technologies if player is not None else []
    unit = resolve_unit_variant(registry, faction, techs, base_type)
    return float(unit.cost) if unit is not None and unit.cost is not None else 0.0


def unit_name(
    state: GameState, registry: StaticDataRegistry, player_id: str, base_type: str
) -> str:
    """Nazwa wariantu jednostki gracza (np. Duha Menaimon zamiast „flagship")."""
    player = state.players.get(player_id)
    faction = player.faction if player is not None else None
    techs = player.technologies if player is not None else []
    unit = resolve_unit_variant(registry, faction, techs, base_type)
    return unit.name if unit is not None else base_type


def ships_by_system(state: GameState, player_id: str) -> dict[str, int]:
    """Statki gracza liczone do puli w każdym systemie, gdzie jakieś ma: ``{pozycja: ile}``.

    Do podglądu przy zmianie puli floty (faza statusu): największa flota = minimalna pula
    bez strat.
    """
    result: dict[str, int] = {}
    per_ship = fighters_per_ship(state, player_id)
    for position, system in state.systems.items():
        n = sum(
            c
            for bt, c in system.space_units.get(player_id, {}).items()
            if c > 0 and _pool_unit(state, player_id, bt)
        ) + -(-_overflow_fighters(state, None, position, player_id) // per_ship)
        if n > 0:
            result[position] = n
    return result


def players_with_excess(state: GameState, position: str) -> list[str]:
    """Gracze z nadwyżką statków w systemie — od aktywnego, zgodnie z kolejnością zasiadania."""
    system = state.systems.get(position)
    if system is None:
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
        if pid in system.space_units and fleet_report(state, position, pid).excess > 0
    ]


def open_fleet_pool_check(state: GameState, position: str) -> GameState:
    """Otwiera okno ``FLEET_POOL`` dla graczy z nadwyżką. Bez nadwyżki / przy innym oknie —
    stan bez zmian."""
    if state.pending_window is not None:
        return state
    queue = players_with_excess(state, position)
    if not queue:
        return state
    return timing.open_window(
        state, WindowType.FLEET_POOL, queue, context={"position": position}
    )


def auto_removal(
    state: GameState, registry: StaticDataRegistry, player_id: str, report: FleetReport
) -> dict[str, int]:
    """Podpowiedź: usuń najtańsze statki najpierw, aż mieszczą się w puli (⚠️ ZAŁOŻENIE)."""
    removal: dict[str, int] = {}
    order = sorted(
        report.ships, key=lambda bt: (unit_cost(state, registry, player_id, bt), bt)
    )
    for base_type in order:
        while report.excess_after(removal) > 0 and (
            removal.get(base_type, 0) < report.ships[base_type]
        ):
            removal[base_type] = removal.get(base_type, 0) + 1
    return _trimmed(report, removal)


def _trimmed(report: FleetReport, removal: dict[str, int]) -> dict[str, int]:
    """Bez zbędnych sztuk: jednostka, którą da się oddać bez nadwyżki, nie musi być zdjęta."""
    result = {bt: n for bt, n in removal.items() if n > 0}
    for base_type in sorted(result):
        while result[base_type] > 0:
            fewer = {**result, base_type: result[base_type] - 1}
            if report.excess_after(fewer) > 0:
                break
            result = fewer
    return {bt: n for bt, n in result.items() if n > 0}


def check_removal(report: FleetReport, remove: dict[str, int]) -> None:
    """Usunięcie ma zlikwidować nadwyżkę i nie zabrać nic ponad potrzebę.

    Raises:
        ValueError: Zły typ (myśliwiec/naziemna), za mało/za dużo sztuk.
    """
    picked = {bt: n for bt, n in remove.items() if n > 0}
    for base_type, count in picked.items():
        if base_type not in report.ships and not counts_toward_pool(base_type):
            raise ValueError(
                f"Only non-fighter ships count against the fleet pool ({base_type})."
            )
        if count > report.ships.get(base_type, 0):
            raise ValueError(f"You have only {report.ships.get(base_type, 0)} {base_type} here.")
    left = report.excess_after(picked)
    if left > 0:
        raise ValueError(f"Still over the fleet pool - remove {left} more ship(s).")
    # Bez zbędnych: po oddaniu którejkolwiek zdjętej jednostki nadwyżka musiałaby wrócić.
    if _trimmed(report, picked) != picked:
        raise ValueError("You are removing more ships than the fleet pool requires.")


def resolve_fleet_pool(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    remove: dict[str, int],
) -> GameState:
    """Gracz zwraca nadwyżkę statków do rezerwy z okna ``FLEET_POOL``.

    Raises:
        ValueError: Brak okna, nie kolej gracza, zły wybór.
    """
    window = state.pending_window
    if window is None or window.window_type is not WindowType.FLEET_POOL:
        raise ValueError("No fleet pool check is pending.")
    if window.current_responder != player_id:
        raise ValueError(
            f"It is now {window.current_responder}'s turn to remove excess ships, "
            f"not {player_id}."
        )
    position = str(window.context.get("position", ""))
    report = fleet_report(state, position, player_id, registry)
    check_removal(report, remove)
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
        # Faza statusu (zmiana puli floty): kolejny system / gracz z nadwyżką albo kroki 6–7.
        if new_state.status is not None:
            from src.core import status_phase  # lokalnie: status_phase importuje fleet_pool

            new_state = status_phase.advance_fleet_check(new_state, registry)
        from src.core import strategic_action  # lokalnie: unikamy cyklu importów

        new_state = strategic_action.resume_after_limit_window(new_state)
    return new_state
