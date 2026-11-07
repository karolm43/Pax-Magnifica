"""Silnik walki: kosmicznej i naziemnej — rundy, AFB, rzuty, Sustain Damage, straty (RULES.md 39).

Przebieg (``ActiveCombat.step``): ``AFB`` (1. runda walki kosmicznej, gdy ktoś ma AFB) →
``ROLL`` (rzuty obu stron) → ``ASSIGN`` (okno ``COMBAT_ASSIGN_HITS``: obrońca, potem atakujący)
→ kolejna runda albo ``DONE``. Wszystkie wartości z WARIANTU jednostki gracza
(``combat.resolve_unit_variant``); rzuty przez ``core/dice.py`` (seedowalne, w stanie gry).

Funkcje CZYSTE (``state -> state``). Walidacja twarda: ``ValueError`` → HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core import capacity, timing
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count, set_damaged
from src.core.dice import DIE_SIDES, count_hits, roll_dice
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.movement import CargoPickup
from src.core.registry import StaticDataRegistry
from src.core.retreat import perform_retreat, retreat_destinations
from src.core.unit_catalog import is_space_unit

# Anomalia dająca obrońcy +1 do rzutów combat w walce kosmicznej (R_nebula; RULES.md 39 W6).
_NEBULA = "NEBULA"
_FIGHTER = "fighter"


@dataclass(frozen=True)
class CombatUnit:
    """Grupa jednostek gracza w walce (jeden typ) — wartości z wariantu gracza."""

    base_type: str
    unit_id: str
    name: str
    count: int
    damaged: int
    hits_on: int  # próg PO modyfikatorze (np. mgławica: obrońca 6 → 5)
    base_hits_on: int  # próg z danych
    modifier: int  # +N do wyniku rzutu (mgławica: +1 obrońcy)
    dice_per_unit: int
    sustain: bool
    afb_hits_on: int | None
    afb_dice: int

    @property
    def total_dice(self) -> int:
        return self.count * self.dice_per_unit

    @property
    def sustainable(self) -> int:
        """Ile egzemplarzy może jeszcze użyć Sustain Damage (nieuszkodzone, ze zdolnością)."""
        return self.count - self.damaged if self.sustain else 0

    @property
    def expected_hits(self) -> float:
        chance = max(0, min(DIE_SIDES, DIE_SIDES + 1 - self.hits_on)) / DIE_SIDES
        return round(self.total_dice * chance, 2)


def _zone(kind: str, planet: str | None) -> str:
    return "space" if kind == "space" else (planet or "")


def _units_map(system: SystemState | None, zone: str, player_id: str) -> dict[str, int]:
    if system is None:
        return {}
    if zone == "space":
        return system.space_units.get(player_id, {})
    return system.planet_units.get(zone, {}).get(player_id, {})


def combat_units(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    *,
    kind: str,
    position: str,
    planet: str | None,
    player_id: str,
    defender: bool = False,
) -> list[CombatUnit]:
    """Jednostki gracza biorące udział w walce (W2/W3), z wartościami jego wariantu.

    Kosmiczna: statki w przestrzeni z wartością combat. Naziemna: siły naziemne na
    planecie z wartością combat (struktury bez combat pomijane). ``defender`` włącza
    modyfikator mgławicy (+1, tylko walka kosmiczna — W6).
    """
    system = state.systems.get(position)
    player = state.players.get(player_id)
    zone = _zone(kind, planet)
    modifier = (
        1 if defender and kind == "space" and _NEBULA in grid.anomalies_at(position) else 0
    )
    units: list[CombatUnit] = []
    for base_type, count in sorted(_units_map(system, zone, player_id).items()):
        if count <= 0 or is_space_unit(base_type) != (kind == "space"):
            continue
        unit = resolve_unit_variant(
            registry,
            player.faction if player is not None else None,
            player.technologies if player is not None else [],
            base_type,
            player.breakthrough_unlocked if player is not None else False,
        )
        if unit is None or unit.combat_hits_on is None:
            continue
        units.append(
            CombatUnit(
                base_type=base_type,
                unit_id=unit.id,
                name=unit.name,
                count=count,
                damaged=damaged_count(system, zone, player_id, base_type),
                hits_on=unit.combat_hits_on - modifier,
                base_hits_on=unit.combat_hits_on,
                modifier=modifier,
                dice_per_unit=unit.combat_die_count or 1,
                sustain=unit.sustain_damage,
                afb_hits_on=unit.afb_hits_on if kind == "space" else None,
                afb_dice=unit.afb_die_count or 1,
            )
        )
    return units


def side_units(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player_id: str
) -> list[CombatUnit]:
    """Jednostki gracza w TRWAJĄCEJ walce (z modyfikatorem obrońcy)."""
    combat = _combat(state)
    return combat_units(
        state,
        grid,
        registry,
        kind=combat.kind,
        position=combat.position,
        planet=combat.planet,
        player_id=player_id,
        defender=player_id == combat.defender,
    )


def required_hits(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player_id: str
) -> int:
    """Ile trafień gracz musi pokryć: min(trafienia, jednostki + Sustain Damage) — W7."""
    combat = _combat(state)
    pending = combat.pending_hits.get(player_id, 0)
    units = side_units(state, grid, registry, player_id)
    absorbable = sum(u.count + u.sustainable for u in units)
    return min(pending, absorbable)


def _combat(state: GameState) -> ActiveCombat:
    if state.active_combat is None:
        raise ValueError("No combat is in progress.")
    return state.active_combat


# ------------------------------------------------------------------------------- start


def start_combat(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    planet: str | None = None,
) -> GameState:
    """Rozpoczyna walkę w aktywnym systemie: kosmiczną (``planet`` None) albo naziemną.

    Raises:
        ValueError: Zły krok akcji, trwa okno/walka, brak dokładnie dwóch stron (W1–W3).
    """
    active = state.active_system
    attacker = state.active_player_id
    if active is None or attacker is None:
        raise ValueError("Combat needs an active system and an active player.")
    kind = "space" if planet is None else "ground"
    required_step = TacticalStep.SPACE_COMBAT if kind == "space" else TacticalStep.INVASION
    if state.tactical_step is not required_step:
        raise ValueError(
            f"{kind.capitalize()} combat is fought in the {required_step.value} step."
        )
    if state.active_combat is not None and state.active_combat.step is not CombatStep.DONE:
        raise ValueError("A combat is already in progress.")
    if state.pending_window is not None:
        raise ValueError("Resolve the open timing window before starting combat.")
    if kind == "ground":
        system = state.systems.get(active)
        if system is None or planet not in system.planet_units:
            raise ValueError(f"There are no ground forces on {planet}.")

    participants = [
        pid
        for pid in state.players
        if combat_units(
            state, grid, registry, kind=kind, position=active, planet=planet, player_id=pid
        )
    ]
    others = [pid for pid in participants if pid != attacker]
    if attacker not in participants or not others:
        raise ValueError("There is no combat here: both sides need units able to fight.")
    if len(others) > 1:
        raise ValueError(
            "More than two players are in this combat - resolve it with God-Mode."
        )
    defender = others[0]

    new_state = state.clone()
    combat = ActiveCombat(
        kind=kind, position=active, planet=planet, attacker=attacker, defender=defender
    )
    new_state.active_combat = combat
    has_afb = kind == "space" and any(
        u.afb_hits_on is not None
        for pid in (attacker, defender)
        for u in side_units(new_state, grid, registry, pid)
    )
    if has_afb:
        combat.step = CombatStep.AFB
        return new_state
    return _begin_round(new_state, grid)


# ---------------------------------------------------------------------------- rzuty


def _roll_entry(unit: CombatUnit, dice: list[int], hits_on: int, hits: int) -> dict[str, Any]:
    return {
        "baseType": unit.base_type,
        "name": unit.name,
        "hitsOn": hits_on,
        "modifier": unit.modifier,
        "dice": dice,
        "hits": hits,
    }


def _remove_units(
    state: GameState, combat: ActiveCombat, player_id: str, base_type: str, count: int
) -> None:
    """Zdejmuje ``count`` jednostek gracza z miejsca walki (mutuje ``state``)."""
    remove_units_in_zone(
        state, combat.position, _zone(combat.kind, combat.planet), player_id, base_type, count
    )


def remove_units_in_zone(
    state: GameState, position: str, zone: str, player_id: str, base_type: str, count: int
) -> None:
    """Zdejmuje ``count`` jednostek gracza ze strefy (``"space"``/planeta) — mutuje ``state``."""
    system = state.systems[position]
    units = _units_map(system, zone, player_id)
    remaining = units.get(base_type, 0) - count
    if remaining > 0:
        units[base_type] = remaining
    else:
        units.pop(base_type, None)
    if not units:
        if zone == "space":
            system.space_units.pop(player_id, None)
        else:
            system.planet_units.get(zone, {}).pop(player_id, None)


def resolve_afb(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Anti-Fighter Barrage obu stron jednocześnie (W4): trafienia niszczą myśliwce przeciwnika."""
    combat = _combat(state)
    if combat.step is not CombatStep.AFB:
        raise ValueError("Anti-Fighter Barrage is not the current combat step.")
    new_state = state
    afb: dict[str, list[dict[str, Any]]] = {}
    hits_by: dict[str, int] = {}
    for pid in (combat.attacker, combat.defender):
        entries: list[dict[str, Any]] = []
        total = 0
        for unit in side_units(new_state, grid, registry, pid):
            if unit.afb_hits_on is None:
                continue
            new_state, dice = roll_dice(new_state, unit.count * unit.afb_dice)
            hits = count_hits(dice, unit.afb_hits_on)
            total += hits
            entries.append(_roll_entry(unit, dice, unit.afb_hits_on, hits))
        afb[pid] = entries
        hits_by[pid] = total

    new_state = new_state.clone()
    combat = _combat(new_state)
    losses: dict[str, dict[str, int]] = {}
    zone = _zone(combat.kind, combat.planet)
    for pid, opponent in (
        (combat.attacker, combat.defender),
        (combat.defender, combat.attacker),
    ):
        fighters = _units_map(new_state.systems.get(combat.position), zone, opponent).get(
            _FIGHTER, 0
        )
        destroyed = min(hits_by[pid], fighters)  # nadwyżka przepada (W4)
        if destroyed:
            _remove_units(new_state, combat, opponent, _FIGHTER, destroyed)
            losses[opponent] = {_FIGHTER: destroyed}
    combat.afb = afb
    combat.log.append(
        {"round": combat.round, "phase": "AFB", "rolls": afb, "hits": hits_by, "losses": losses}
    )
    return _after_losses(new_state, grid, registry)


def roll_round(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Rzuty combat obu stron (atakujący pierwszy — W5) i otwarcie przypisania strat."""
    combat = _combat(state)
    if combat.step is not CombatStep.ROLL:
        raise ValueError("Combat dice are not the current combat step.")
    new_state = state
    rolls: dict[str, list[dict[str, Any]]] = {}
    hits_by: dict[str, int] = {}
    for pid in (combat.attacker, combat.defender):
        entries: list[dict[str, Any]] = []
        total = 0
        for unit in side_units(new_state, grid, registry, pid):
            new_state, dice = roll_dice(new_state, unit.total_dice)
            hits = count_hits([d + unit.modifier for d in dice], unit.base_hits_on)
            total += hits
            entries.append(_roll_entry(unit, dice, unit.base_hits_on, hits))
        rolls[pid] = entries
        hits_by[pid] = total

    new_state = new_state.clone()
    combat = _combat(new_state)
    combat.rolls = rolls
    combat.pending_hits = {
        combat.defender: hits_by[combat.attacker],
        combat.attacker: hits_by[combat.defender],
    }
    combat.log.append(
        {
            "round": combat.round,
            "phase": "COMBAT",
            "rolls": rolls,
            "hits": hits_by,
            "losses": {},
            "sustained": {},
        }
    )
    queue = [
        pid
        for pid in (combat.defender, combat.attacker)
        if required_hits(new_state, grid, registry, pid) > 0
    ]
    if not queue:
        return _after_losses(new_state, grid, registry)
    combat.step = CombatStep.ASSIGN
    return timing.open_window(
        new_state,
        WindowType.COMBAT_ASSIGN_HITS,
        queue,
        context={"position": combat.position},
    )


# -------------------------------------------------------------------------- straty


def plan_losses(
    units: dict[str, CombatUnit],
    sustain: dict[str, int],
    destroy: dict[str, int],
    destroy_damaged: dict[str, int],
    required: int,
) -> dict[str, tuple[int, int]]:
    """Waliduje pokrycie trafień (W7/W8) i zwraca plan ``{base_type: (nowa liczba, uszkodzone)}``.

    Współdzielone przez walkę, bombardowanie i Space Cannon Defense (RULES.md 40): w każdym
    przypadku właściciel jednostek sam wybiera straty, a Sustain Damage anuluje trafienie.

    Raises:
        ValueError: Zła liczba/typ, nadużycie Sustain Damage, suma różna od ``required``.
    """
    plan: dict[str, tuple[int, int]] = {}
    total = 0
    for base_type in set(sustain) | set(destroy) | set(destroy_damaged):
        s = max(0, sustain.get(base_type, 0))
        d = max(0, destroy.get(base_type, 0))
        dd = max(0, destroy_damaged.get(base_type, 0))
        if s + d + dd == 0:
            continue
        unit = units.get(base_type)
        if unit is None:
            raise ValueError(f"You have no {base_type} in this combat.")
        if s > unit.sustainable:
            raise ValueError(
                f"Only {unit.sustainable} {unit.name} can use Sustain Damage."
            )
        damaged_after = unit.damaged + s
        undamaged_after = unit.count - damaged_after
        if d > undamaged_after or dd > damaged_after:
            raise ValueError(f"Not enough {unit.name} for these losses.")
        plan[base_type] = (unit.count - d - dd, damaged_after - dd)
        total += s + d + dd
    if total != required:
        raise ValueError(f"Cover exactly {required} hit(s).")
    return plan


def apply_losses(
    state: GameState,
    position: str,
    zone: str,
    player_id: str,
    units: dict[str, CombatUnit],
    plan: dict[str, tuple[int, int]],
) -> None:
    """Stosuje plan strat w strefie ``zone`` systemu ``position`` (MUTUJE ``state`` — klon)."""
    system = state.systems[position]
    for base_type, (count, damaged) in plan.items():
        lost = units[base_type].count - count
        if lost:
            remove_units_in_zone(state, position, zone, player_id, base_type, lost)
        set_damaged(system, zone, player_id, base_type, damaged)


def losses_of(
    units: dict[str, CombatUnit], plan: dict[str, tuple[int, int]]
) -> dict[str, int]:
    """Ile sztuk każdego typu zginęło wg planu (do dziennika)."""
    return {bt: units[bt].count - c for bt, (c, _) in plan.items() if units[bt].count - c}


def sustained_of(plan: dict[str, tuple[int, int]], sustain: dict[str, int]) -> dict[str, int]:
    """Ile razy użyto Sustain Damage per typ (do dziennika)."""
    return {bt: max(0, sustain.get(bt, 0)) for bt in plan if sustain.get(bt, 0) > 0}


def assign_combat_hits(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    *,
    sustain: dict[str, int],
    destroy: dict[str, int],
    destroy_damaged: dict[str, int],
) -> GameState:
    """Gracz pokrywa trafienia: Sustain Damage, potem niszczenie (W7/W8).

    Semantyka: najpierw ``sustain`` (nieuszkodzone ze zdolnością stają się uszkodzone), potem
    ``destroy`` (nieuszkodzone) i ``destroy_damaged`` (uszkodzone — także te właśnie uszkodzone).
    Suma = ``required_hits``.

    Raises:
        ValueError: Zła kolejność w oknie, zła liczba/typ, nadużycie Sustain Damage.
    """
    combat = _combat(state)
    window = state.pending_window
    if (
        combat.step is not CombatStep.ASSIGN
        or window is None
        or window.window_type is not WindowType.COMBAT_ASSIGN_HITS
    ):
        raise ValueError("There are no combat hits to assign right now.")
    if window.current_responder != player_id:
        raise ValueError(
            f"It is now {window.current_responder}'s turn to assign hits, not {player_id}."
        )

    units = {u.base_type: u for u in side_units(state, grid, registry, player_id)}
    required = required_hits(state, grid, registry, player_id)
    plan = plan_losses(units, sustain, destroy, destroy_damaged, required)

    new_state = state.clone()
    combat = _combat(new_state)
    zone = _zone(combat.kind, combat.planet)
    apply_losses(new_state, combat.position, zone, player_id, units, plan)

    entry = combat.log[-1] if combat.log else None
    if entry is not None:
        entry["losses"][player_id] = losses_of(units, plan)
        entry["sustained"][player_id] = sustained_of(plan, sustain)
    combat.pending_hits[player_id] = 0

    new_state = timing.respond_current(new_state, player_id)
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
        return _after_losses(new_state, grid, registry)
    return new_state


def _after_losses(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Koniec rundy (W9): zwycięzca/remis albo kolejna runda (bez AFB)."""
    new_state = state.clone()
    combat = _combat(new_state)
    alive = [
        pid
        for pid in (combat.attacker, combat.defender)
        if side_units(new_state, grid, registry, pid)
    ]
    if len(alive) <= 1:
        # Także O3: ogłoszony odwrót nie następuje, gdy przeciwnikowi nie zostały statki.
        combat.step = CombatStep.DONE
        combat.winner = alive[0] if alive else None
        combat.outcome = "winner" if alive else "draw"
        combat.pending_hits = {}
        combat.retreating = []
        # 39.6 C3: limit pojemności sprawdzany po wyłonieniu zwycięzcy walki kosmicznej.
        if combat.kind == "space":
            return capacity.open_capacity_check(new_state, registry, combat.position)
        return new_state
    combat.pending_hits = {}
    if combat.step is CombatStep.AFB:
        # AFB nie zmienia numeru rundy (to 1. runda) — dalej Announce Retreats (39.5).
        return _begin_round(new_state, grid)
    # O3: krok Retreat — ogłoszony odwrót MUSI się odbyć, o ile wciąż jest dozwolony cel.
    if combat.retreating and combat.step is not CombatStep.RETREAT:
        pid = combat.retreating[0]
        if retreat_destinations(new_state, grid, combat.position, pid):
            combat.step = CombatStep.RETREAT
            return new_state
        combat.retreating = []  # brak celu — odwrót nie następuje, walka trwa
    combat.retreating = []
    combat.round += 1
    return _begin_round(new_state, grid)


def _begin_round(state: GameState, grid: HexGrid) -> GameState:
    """Początek rundy po AFB: Announce Retreats (walka kosmiczna) albo od razu rzuty (39.5 O2).

    Kolejka okna ``COMBAT_RETREAT`` = obrońca, potem atakujący — tylko gracze z dozwolonym
    celem odwrotu. Pusta kolejka (albo walka naziemna, O1) = krok pomijany.
    """
    new_state = state.clone()
    combat = _combat(new_state)
    combat.retreating = []
    queue = (
        [
            pid
            for pid in (combat.defender, combat.attacker)
            if retreat_destinations(new_state, grid, combat.position, pid)
        ]
        if combat.kind == "space"
        else []
    )
    if not queue:
        combat.step = CombatStep.ROLL
        return new_state
    combat.step = CombatStep.ANNOUNCE
    return timing.open_window(
        new_state,
        WindowType.COMBAT_RETREAT,
        queue,
        context={"position": combat.position, "round": combat.round},
    )


def announce_retreat(
    state: GameState, grid: HexGrid, player_id: str, *, announce: bool
) -> GameState:
    """Gracz ogłasza odwrót (``announce=True``) albo walczy dalej (39.5 O2).

    Ogłoszenie obrońcy zamyka okno — atakujący nie może już ogłosić odwrotu w tej rundzie.

    Raises:
        ValueError: Nie ten krok/okno, nie kolej gracza, brak dozwolonego celu odwrotu.
    """
    combat = _combat(state)
    window = state.pending_window
    if (
        combat.step is not CombatStep.ANNOUNCE
        or window is None
        or window.window_type is not WindowType.COMBAT_RETREAT
    ):
        raise ValueError("Retreats are not being announced right now.")
    if window.current_responder != player_id:
        raise ValueError(
            f"It is now {window.current_responder}'s turn to announce a retreat, not {player_id}."
        )
    new_state = state.clone()
    combat = _combat(new_state)
    if announce:
        if not retreat_destinations(new_state, grid, combat.position, player_id):
            raise ValueError("There is no eligible system to retreat to.")
        combat.retreating = [*combat.retreating, player_id]
    new_state = timing.respond_current(new_state, player_id)
    defender_retreats = announce and player_id == _combat(new_state).defender
    if defender_retreats or timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
        _combat(new_state).step = CombatStep.ROLL
    return new_state


def retreat_from_combat(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    destination: str,
    *,
    cargo: list[CargoPickup] | None = None,
    token_pool: str | None = None,
) -> GameState:
    """Krok Retreat: gracz, który ogłosił odwrót, wycofuje się do ``destination`` (39.5 O3–O7).

    Po odwrocie: gdy obaj nadal mają statki w systemie — kolejna runda od Announce Retreats;
    inaczej walka się kończy (zwycięzca = gracz ze statkami).

    Raises:
        ValueError: Nie krok Retreat, gracz nie ogłaszał odwrotu, zły cel/ładunek/pula.
    """
    combat = _combat(state)
    if combat.step is not CombatStep.RETREAT or player_id not in combat.retreating:
        raise ValueError("You have no retreat to carry out right now.")
    new_state, result = perform_retreat(
        state,
        grid,
        registry,
        combat.position,
        player_id,
        destination,
        cargo=cargo,
        token_pool=token_pool,
    )
    combat = _combat(new_state)
    combat.retreating = []
    combat.retreated = {**combat.retreated, player_id: destination}
    combat.log.append(
        {
            "round": combat.round,
            "phase": "RETREAT",
            "rolls": {},
            "hits": {},
            "losses": {player_id: dict(result.removed)} if result.removed else {},
            "sustained": {},
            "retreat": {
                "player": player_id,
                "destination": destination,
                "units": dict(result.moved),
                "tokenPlaced": result.token_placed,
            },
        }
    )
    return _after_losses(new_state, grid, registry)


def close_combat(state: GameState) -> GameState:
    """Zamyka ZAKOŃCZONĄ walkę (okno pola bitwy znika).

    Raises:
        ValueError: Gdy walka jeszcze trwa.
    """
    combat = _combat(state)
    if combat.step is not CombatStep.DONE:
        raise ValueError("The combat is not finished yet.")
    new_state = state.clone()
    new_state.active_combat = None
    # Wynik walki naziemnej zapamiętujemy w inwazji — Establish Control potrzebuje wiedzieć,
    # czy był remis (obrońca zachowuje kontrolę — RULES.md 40.1 I8).
    if combat.kind == "ground" and combat.planet and new_state.invasion is not None:
        new_state.invasion.combat_results[combat.planet] = {
            "attacker": combat.attacker,
            "defender": combat.defender,
            "winner": combat.winner,
            "outcome": combat.outcome,
            "rounds": combat.round,
        }
    return new_state


def space_combat_required(state: GameState) -> bool:
    """Czy w aktywnym systemie statki ma co najmniej dwóch graczy (walka obowiązkowa — W2)."""
    active = state.active_system
    system = state.systems.get(active) if active is not None else None
    if system is None:
        return False
    owners = [
        pid
        for pid, by_type in system.space_units.items()
        if any(c > 0 and is_space_unit(bt) for bt, c in by_type.items())
    ]
    return len(owners) >= 2
