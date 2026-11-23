"""Inwazja: Bombardment → Commit Ground Forces → Space Cannon Defense → Ground Combat →
Establish Control (RULES.md 40).

Krok INVASION akcji taktycznej. Stan w ``GameState.invasion`` (``InvasionState``), podkroki w
``InvasionPhase``. Walka naziemna to istniejący silnik ``core/battle.py`` (kind="ground") — tu
tylko wskazujemy planety do walki i zapamiętujemy wynik (remis → obrońca zachowuje kontrolę).

Funkcje CZYSTE (``state -> state``), rzuty przez ``core/dice.py`` (seedowalne). Twarda walidacja:
``ValueError`` → HTTP 422. Wartości (Bombardment, Planetary Shield, Space Cannon) z WARIANTU
jednostki gracza (``combat.resolve_unit_variant``).
"""

from __future__ import annotations

from typing import Any

from src.core import (
    chronicle,
    control,
    custodians,
    exhaust,
    exploration,
    planet_stats,
    rules_hooks,
    space_cannon,
    triggers,
    unit_ops,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    GameState,
    InvasionPhase,
    InvasionState,
    SystemState,
    TacticalStep,
)
from src.core.hex_grid import HexGrid
from src.core.invasion_bombard import assign_bombard_hits as assign_bombard_hits
from src.core.invasion_bombard import bombard as bombard
from src.core.invasion_bombard import bombard_defender as bombard_defender
from src.core.invasion_bombard import bombard_groups as bombard_groups
from src.core.invasion_bombard import bombard_modifier as bombard_modifier
from src.core.invasion_bombard import bombard_targets as bombard_targets
from src.core.invasion_bombard import ground_bombarders as ground_bombarders
from src.core.invasion_bombard import plasma_bombard_dice as plasma_bombard_dice
from src.core.invasion_bombard import required_bombard_hits as required_bombard_hits
from src.core.invasion_common import _DMZ_REASON, _defenders, _ground_in_zone, _inv, _phase, _system
from src.core.invasion_common import GROUND_FORCES as GROUND_FORCES
from src.core.invasion_common import BombardAssignment as BombardAssignment
from src.core.invasion_common import BombardGroup as BombardGroup
from src.core.invasion_common import _attacker_ignores_shield as _attacker_ignores_shield
from src.core.invasion_common import _ground_units as _ground_units
from src.core.invasion_common import attacker_ground_types as attacker_ground_types
from src.core.invasion_common import planet_infos as planet_infos
from src.core.invasion_common import planet_shield as planet_shield
from src.core.invasion_common import structure_ground_types as structure_ground_types
from src.core.invasion_common import system_planets as system_planets
from src.core.invasion_common import unit_variant as unit_variant
from src.core.invasion_defense import _defense_open
from src.core.invasion_defense import assign_defense_hits as assign_defense_hits
from src.core.invasion_defense import defense_fire as defense_fire
from src.core.invasion_defense import defense_pass as defense_pass
from src.core.invasion_defense import defense_planets as defense_planets
from src.core.invasion_defense import defense_shooters as defense_shooters
from src.core.invasion_defense import required_defense_hits as required_defense_hits
from src.core.invasion_defense import undefended_open as undefended_open
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

# ------------------------------------------------------------------------------ początek


def _enter(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, phase: InvasionPhase
) -> GameState:
    """Wchodzi w podkrok (MUTUJE klon) i pomija te, w których nie ma nic do roboty."""
    new_state = state.clone()
    inv = _inv(new_state)
    inv.phase = phase
    inv.last_commit = {}  # okno „po zaangażowaniu” (Ghost Squad, Parley) żyje tylko w COMMIT
    if phase is InvasionPhase.SPACE_CANNON_DEFENSE and not defense_planets(new_state, registry):
        return _enter(new_state, grid, registry, InvasionPhase.GROUND_COMBAT)
    if phase is InvasionPhase.GROUND_COMBAT and not combat_planets(new_state, registry):
        return _enter(new_state, grid, registry, InvasionPhase.ESTABLISH)
    if phase is InvasionPhase.ESTABLISH:
        return_ships_to_space(new_state)  # Matriarch: myśliwce nie dają kontroli (F_naalu 1)
        _establish_control(new_state, registry)
    return new_state


def return_ships_to_space(state: GameState, planet: str | None = None) -> dict[str, int]:
    """Statki atakującego zaangażowane na planety jak siły naziemne (Matriarch) wracają do
    przestrzeni aktywnego systemu - MUTUJE ``state``. ``planet=None`` = wszystkie planety.

    F_naalu matriarch 1: po walce naziemnej (i najpóźniej przed Establish Control) - nie stoją
    na planecie, więc nie dają kontroli; uszkodzenia jadą razem z jednostkami.
    """
    inv = state.invasion
    system = state.systems.get(inv.position) if inv is not None else None
    if inv is None or system is None:
        return {}
    moved: dict[str, int] = {}
    for target in sorted(system.planet_units):
        if planet is not None and target != planet:
            continue
        for base_type, count in sorted(system.planet_units[target].get(inv.attacker, {}).items()):
            if count > 0 and is_space_unit(base_type):
                unit_ops.transfer_units(
                    state, system, target, system, "space", inv.attacker, base_type, count
                )
                moved[base_type] = moved.get(base_type, 0) + count
    return moved


def begin_invasion(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Otwiera inwazję przy wejściu w krok INVASION (None, gdy nie ma co robić).

    Pomija Bombardment, gdy nikt nie może bombardować, a przy braku sił naziemnych w
    przestrzeni (nic do lądowania) w ogóle nie otwiera okna inwazji.
    """
    active = state.active_system
    attacker = state.active_player_id
    if state.tactical_step is not TacticalStep.INVASION or active is None or attacker is None:
        raise ValueError("Invasion starts in the INVASION step of a tactical action.")
    if state.invasion is not None:
        return state.clone()
    # RULES.md 40.1: krok INVASION jest jeden - zamkniętej inwazji nie otwiera się ponownie.
    if state.invasion_resolved:
        raise ValueError("The invasion of this tactical action is already resolved.")
    new_state = state.clone()
    new_state.invasion = InvasionState(position=active, attacker=attacker)
    system = new_state.systems.get(active)
    # Matriarch (RULES.md 62.16): myśliwce w przestrzeni też mogą lądować.
    landable = system is not None and bool(
        _ground_in_zone(system, "space", attacker, attacker_ground_types(new_state))
    )
    # RULES.md 40.1 I7a: sporna planeta (siły aktywnego obok cudzych, np. po Crash Landing) też
    # otwiera inwazję - walka naziemna wybucha bez lądowania.
    landable = landable or bool(_contested(new_state, registry, active, attacker))
    # Lądowanie prosto z planet (G'hom Sek'kus) - także bez statków i sił w przestrzeni (F_norr).
    landable = landable or rules_hooks.permits(
        rules_hooks.POINT_INVASION_COMMIT_FROM_PLANETS, new_state, attacker
    )
    # Tekklar Conditioning (RULES.md 62.1): prosto do Commit Ground Forces, bez Bombardment.
    skip_bombard = rules_hooks.permits(
        rules_hooks.POINT_INVASION_SKIP_BOMBARDMENT, new_state, attacker
    )
    if skip_bombard or not bombard_groups(new_state, registry):
        if not landable:
            new_state.invasion = None
            return new_state
        triggers.fire(
            new_state, GameEvent.INVASION, Moment.START, subject=attacker,
            ctx={"position": active, "player": attacker},
        )
        return _enter(new_state, grid, registry, InvasionPhase.COMMIT)
    triggers.fire(
        new_state, GameEvent.INVASION, Moment.START, subject=attacker,
        ctx={"position": active, "player": attacker},
    )
    return new_state


def clear_invasion(state: GameState) -> GameState:
    """Zamyka inwazję (wyjście z kroku, koniec akcji) — nie rusza jednostek.

    Emituje ``INVASION`` / ``END``: wygasają efekty „do końca inwazji” (Blitz, Bunker, Disable).
    """
    new_state = state.clone()
    if new_state.invasion is not None:
        triggers.fire(
            new_state, GameEvent.INVASION, Moment.END, subject=new_state.invasion.attacker,
            ctx={"position": new_state.invasion.position, "player": new_state.invasion.attacker},
        )
    new_state.invasion = None
    return new_state


# ----------------------------------------------------------------------- commit ground


def commit_ground_forces(
    state: GameState,
    registry: StaticDataRegistry,
    commits: dict[str, dict[str, int]],
) -> GameState:
    """Ląduje siły naziemne z przestrzeni na planety: ``{planeta: {base_type: liczba}}`` (I2).

    Jednostki od tej chwili stoją NA planecie (liczą się dla efektów gry). Można wołać wiele
    razy; razem nie można zlądować więcej, niż stoi w przestrzeni. Uszkodzenia jadą z
    jednostkami. Kontrolę planety ustala dopiero Establish Control.

    Raises:
        ValueError: Zły podkrok, planeta spoza systemu, to nie siła naziemna, brak jednostek.
    """
    inv = _phase(state, InvasionPhase.COMMIT, "Commit Ground Forces")
    _require_tactical_commit(inv)
    planets = set(system_planets(state, registry, inv.position))
    sealed = custodians.landing_blocked(state, registry, inv.position)
    system = _system(state)
    as_ground = attacker_ground_types(state)  # Matriarch: myśliwce jak siły naziemne (62.16)
    # Parley: siły zwrócone do przestrzeni nie mogą w tej akcji lądować na inną planetę.
    available = {
        bt: n - inv.parley_locked.get(bt, 0)
        for bt, n in _ground_in_zone(system, "space", inv.attacker, as_ground).items()
    }
    wanted: dict[str, int] = {}
    for planet, by_type in commits.items():
        for base_type, count in by_type.items():
            if count <= 0:
                continue
            if planet not in planets:
                raise ValueError(f"{planet} is not a planet of the active system.")
            if planet in sealed:
                raise ValueError(
                    "The Custodians token blocks landing on Mecatol Rex - "
                    "remove it first (spend 6 influence)."
                )
            if planet_stats.is_demilitarized(state, planet):
                raise ValueError(_DMZ_REASON)
            if base_type not in GROUND_FORCES and base_type not in as_ground:
                raise ValueError(f"{base_type} is not a ground force.")
            wanted[base_type] = wanted.get(base_type, 0) + count
    if not wanted:
        raise ValueError("Choose ground forces to commit.")
    for base_type, count in wanted.items():
        if count > available.get(base_type, 0):
            raise ValueError(
                f"Only {available.get(base_type, 0)} {base_type} in the space area."
            )

    new_state = state.clone()
    new_inv = _inv(new_state)
    new_system = _system(new_state)
    commit_ctx = {"player": new_inv.attacker, "position": new_inv.position, "units": dict(wanted)}
    new_inv.last_commit = {}  # okno „po zaangażowaniu” dotyczy TEGO zaangażowania
    triggers.fire(
        new_state, GameEvent.UNITS_COMMITTED, Moment.WHEN, subject=new_inv.attacker,
        ctx=commit_ctx,
    )
    for planet, by_type in commits.items():
        for base_type, count in by_type.items():
            if count <= 0:
                continue
            # Lądowanie: z przestrzeni na planetę, uszkodzenia jadą razem z jednostkami.
            unit_ops.transfer_units(
                new_state, new_system, "space", new_system, planet, new_inv.attacker,
                base_type, count,
            )
            landed = new_inv.committed.setdefault(planet, {})
            landed[base_type] = landed.get(base_type, 0) + count
            latest = new_inv.last_commit.setdefault(planet, {})
            latest[base_type] = latest.get(base_type, 0) + count
    triggers.fire(
        new_state, GameEvent.UNITS_COMMITTED, Moment.AFTER, subject=new_inv.attacker,
        ctx=commit_ctx,
    )
    return new_state


def commit_from_planets(
    state: GameState,
    registry: StaticDataRegistry,
    moves: list[tuple[str, str, str, str]],
) -> GameState:
    """Lądowanie sił naziemnych PROSTO z planet (nie z przestrzeni) — RULES.md 62.1.

    ``moves`` = ``[(pozycja źródła, planeta źródła, base_type, planeta celu)]``; po 1 jednostce na
    wpis. Legalność źródeł (np. „up to 1 from each planet”, sąsiedztwo, żetony) sprawdza efekt
    komponentu, który to umożliwia (G'hom Sek'kus); tu: krok COMMIT, cel w aktywnym systemie,
    Custodians, typ siły naziemnej i dostępność jednostki. Emituje ``UNITS_COMMITTED`` jak zwykłe
    lądowanie.

    Raises:
        ValueError: Zły podkrok, cel spoza aktywnego systemu, brak jednostki na planecie źródła.
    """
    new_state = state.clone()
    apply_commit_from_planets(new_state, registry, moves)
    return new_state


def apply_commit_from_planets(
    new_state: GameState,
    registry: StaticDataRegistry,
    moves: list[tuple[str, str, str, str]],
) -> None:
    """Jak :func:`commit_from_planets`, ale MUTUJE ``new_state`` (efekty komponentów na klonie)."""
    inv = _phase(new_state, InvasionPhase.COMMIT, "Commit Ground Forces")
    _require_tactical_commit(inv)
    planets = set(system_planets(new_state, registry, inv.position))
    sealed = custodians.landing_blocked(new_state, registry, inv.position)
    if not moves:
        raise ValueError("Choose ground forces to commit.")
    new_inv = _inv(new_state)
    target_system = _system(new_state)
    wanted: dict[str, int] = {}
    for _pos, _src, base_type, _dest in moves:
        wanted[base_type] = wanted.get(base_type, 0) + 1
    commit_ctx = {"player": new_inv.attacker, "position": new_inv.position, "units": wanted}
    new_inv.last_commit = {}
    triggers.fire(
        new_state, GameEvent.UNITS_COMMITTED, Moment.WHEN, subject=new_inv.attacker,
        ctx=commit_ctx,
    )
    for position, source_planet, base_type, dest in moves:
        if dest not in planets:
            raise ValueError(f"{dest} is not a planet of the active system.")
        if dest in sealed:
            raise ValueError(
                "The Custodians token blocks landing on Mecatol Rex - remove it first."
            )
        if planet_stats.is_demilitarized(new_state, dest):
            raise ValueError(_DMZ_REASON)
        if base_type not in GROUND_FORCES:
            raise ValueError(f"{base_type} is not a ground force.")
        source = new_state.systems.get(position)
        have = (
            source.planet_units.get(source_planet, {}).get(new_inv.attacker, {}).get(base_type, 0)
            if source is not None
            else 0
        )
        if source is None or have <= 0:
            raise ValueError(f"No {base_type} of yours on {source_planet}.")
        unit_ops.transfer_units(
            new_state, source, source_planet, target_system, dest, new_inv.attacker,
            base_type, 1,
        )
        landed = new_inv.committed.setdefault(dest, {})
        landed[base_type] = landed.get(base_type, 0) + 1
        latest = new_inv.last_commit.setdefault(dest, {})
        latest[base_type] = latest.get(base_type, 0) + 1
    triggers.fire(
        new_state, GameEvent.UNITS_COMMITTED, Moment.AFTER, subject=new_inv.attacker,
        ctx=commit_ctx,
    )


# ------------------------------------------------------------------- żeton Custodians


def custodians_block_reason(state: GameState, registry: StaticDataRegistry) -> str | None:
    """Dlaczego aktywny gracz NIE może teraz zdjąć żetonu Custodians (``None`` = może).

    Żeton wolno zdjąć przed Commit Ground Forces (Bombardment albo początek Commit, zanim
    cokolwiek wylądowało), gdy leży na Mecatol Rex i gracz ma siły naziemne do zlądowania.
    """
    inv = _inv(state)
    if not custodians.mecatol_planets(state, registry, inv.position):
        return "This is not the Mecatol Rex system."
    if not custodians.on_board(state):
        return "The Custodians token has already been removed."
    if inv.phase not in (InvasionPhase.BOMBARDMENT, InvasionPhase.COMMIT) or inv.committed:
        return "The token can be removed only before the Commit Ground Forces step."
    if not _ground_in_zone(_system(state), "space", inv.attacker):
        return "You need ground forces in orbit to land on Mecatol Rex."
    return None


def claim_custodians(
    state: GameState,
    registry: StaticDataRegistry,
    planets: list[str],
    trade_goods: int,
) -> GameState:
    """Aktywny gracz zdejmuje żeton Custodians za 6 wpływu (+1 VP, faza agendy w grze).

    Od tej chwili musi zlądować co najmniej jedną siłę naziemną na Mecatol Rex
    (``advance`` nie wypuści z Commit bez tego).

    Raises:
        ValueError: Zły moment, brak sił naziemnych, żeton już zdjęty, zła płatność.
    """
    inv = _inv(state)
    reason = custodians_block_reason(state, registry)
    if reason is not None:
        raise ValueError(reason)
    new_state = custodians.remove_token(state, registry, inv.attacker, planets, trade_goods)
    _inv(new_state).custodians_claimed = True
    return new_state


# ------------------------------------------------------------------------- ground combat


def _contested(
    state: GameState, registry: StaticDataRegistry, position: str, attacker: str
) -> list[str]:
    """Planety systemu, na których ``attacker`` i inny gracz mają siły naziemne (I7 / I7a).

    Nie patrzy na ``committed``: siły mogły trafić na planetę bez lądowania (Crash Landing,
    koegzystencja) - walka i tak wybucha w kroku Invasion (decyzja użytkownika, RULES.md 40.1).
    """
    system = state.systems.get(position)
    if system is None:
        return []
    as_ground = attacker_ground_types(state)  # Matriarch: same myśliwce też walczą (62.16)
    return [
        p
        for p in system_planets(state, registry, position)
        if _ground_in_zone(system, p, attacker, as_ground)
        and _defenders(state, p, position, attacker)
    ]


def combat_planets(state: GameState, registry: StaticDataRegistry) -> list[str]:
    """Planety, na których atakujący i inny gracz mają siły naziemne — tu toczy się walka (I7)."""
    inv = _inv(state)
    return _contested(state, registry, inv.position, inv.attacker)


# ------------------------------------------------------------------------ establish control


def _establish_control(state: GameState, registry: StaticDataRegistry) -> None:
    """Establish Control (I5) — MUTUJE ``state`` (klon): przejęcie planet, struktury, karta.

    Planety przejęte bez wcześniejszego właściciela są EKSPLOROWANE (RULES.md 46): otwiera się
    okno eksploracji, które blokuje zamknięcie inwazji do rozstrzygnięcia kart.
    """
    inv = _inv(state)
    system = _system(state)
    attacker = state.players.get(inv.attacker)
    results: list[dict[str, Any]] = []
    # Planety lądowania + planety walki bez lądowania (Crash Landing - RULES.md 40.1 I7a).
    for planet in sorted(set(inv.committed) | set(inv.combat_results)):
        owner = system.planet_owners.get(planet)
        combat_result = inv.combat_results.get(planet)
        # Hel-Titan atakującego też utrzymuje planetę (struktura i siła naziemna - 62.18).
        own_structures = structure_ground_types(state, inv.attacker)
        attacker_present = bool(_ground_in_zone(system, planet, inv.attacker, own_structures))
        result: dict[str, Any] = {
            "planet": planet,
            "previousOwner": owner,
            "outcome": "lost",
            "destroyedStructures": {},
            "explore": False,
        }
        if attacker_present and owner == inv.attacker:
            result["outcome"] = "already_controlled"
        elif attacker_present:
            destroyed: dict[str, dict[str, int]] = {}
            # Assimilate (RULES.md 62.12): struktury wymienia hook „gain control” - nie niszczymy.
            keeps = rules_hooks.permits(
                rules_hooks.POINT_CONTROL_STRUCTURES_REPLACED, state, inv.attacker
            )
            for pid in list(system.planet_units.get(planet, {})):
                if pid == inv.attacker or keeps:
                    continue
                structures = {
                    bt: n
                    for bt, n in system.planet_units[planet][pid].items()
                    if n > 0 and bt not in GROUND_FORCES and not is_space_unit(bt)
                }
                # Struktury przeciwnika znikają przy zdobyciu planety (nie wracają przez rezerwę).
                for bt, n in structures.items():
                    unit_ops.remove_units(
                        state, system, planet, pid, bt, n, UnitCause.DESTROYED
                    )
                if structures:
                    destroyed[pid] = structures
            control.set_planet_control(state, inv.position, planet, inv.attacker, registry)
            if destroyed:
                # Ślad dla Infiltrate („when you gain control”): struktury zniszczone w tej
                # samej chwili wymienia karta zagrana w oknie zdobycia (RULES.md 53).
                for change in reversed(state.control_changes):
                    if change.get("planet") == planet:
                        change["destroyed"] = {pid: dict(v) for pid, v in destroyed.items()}
                        break
            if attacker is not None:
                # Zdobyta planeta zostaje wyczerpana (zachowanie bez zmian, RULES.md 21/40).
                exhaust.exhaust_planets(state, inv.attacker, [planet])
            result["outcome"] = "captured"
            if owner is not None and owner in state.players:
                chronicle.record_conquest(state, inv.attacker, owner, planet)
            result["destroyedStructures"] = destroyed
            result["explore"] = owner is None and exploration.explorable(registry, planet)
        elif combat_result is not None and combat_result.get("outcome") == "draw":
            defender = str(combat_result["defender"])
            result["outcome"] = "retained"
            if owner != defender:
                control.set_planet_control(state, inv.position, planet, defender)
        results.append(result)
    inv.results = results
    explored = [str(r["planet"]) for r in results if r["explore"]]
    if explored:
        exploration.start_exploration(state, registry, inv.attacker, inv.position, explored)


# --------------------------------------------------------------- inwazja komponentu (62.10)


def _require_tactical_commit(inv: InvasionState) -> None:
    if inv.source:
        raise ValueError(
            "Only the units committed by the ability take part in this invasion "
            "(ground forces in the space area cannot be committed)."
        )


def _has_capacity_ship(state: GameState, system: SystemState, player_id: str) -> bool:
    registry = rules_hooks.bound_registry()
    if registry is None:
        return False
    for base_type, count in system.space_units.get(player_id, {}).items():
        unit = unit_variant(state, registry, player_id, base_type) if count > 0 else None
        if unit is not None and unit.is_ship and (unit.capacity_value or 0) > 0:
            return True
    return False


def _open_component(
    state: GameState,
    attacker: str,
    source: str,
    position: str,
    committed: dict[str, dict[str, int]],
    queue: list[dict[str, Any]],
) -> None:
    """Otwiera inwazję komponentu w systemie ``position`` w kroku COMMIT (MUTUJE ``state``).

    Jednostki już stoją na planetach (zaangażowane przez efekt); okno „po zaangażowaniu”
    (Ghost Squad, Parley) dotyczy tego zaangażowania. Bez zdarzenia startu inwazji i bez
    aktywacji systemu (F_yin Ω).
    """
    landed = {planet: dict(by_type) for planet, by_type in committed.items()}
    state.invasion = InvasionState(
        position=position, attacker=attacker, phase=InvasionPhase.COMMIT,
        committed=landed, last_commit={p: dict(b) for p, b in landed.items()},
        source=source, queue=list(queue),
    )
    units: dict[str, int] = {}
    for by_type in landed.values():
        for base_type, count in by_type.items():
            units[base_type] = units.get(base_type, 0) + count
    triggers.fire(
        state, GameEvent.UNITS_COMMITTED, Moment.AFTER, subject=attacker,
        ctx={"player": attacker, "position": position, "units": units},
    )


def start_component_invasion(
    state: GameState,
    attacker: str,
    source: str,
    commits: dict[str, dict[str, dict[str, int]]],
) -> None:
    """Inwazja komponentu poza akcją taktyczną (Quantum Dissemination) — MUTUJE ``state``.

    ``commits`` = ``{pozycja: {planeta: {base_type: n}}}`` jednostek JUŻ postawionych na
    planetach. Systemy rozstrzygane po kolei (kolejność pozycji), każdy w oknie inwazji od kroku
    Commit Ground Forces, potem Ground Combat i Establish Control (RULES.md 62.10).

    Raises:
        ValueError: Trwa inna inwazja albo brak zaangażowanych jednostek.
    """
    if state.invasion is not None:
        raise ValueError("Another invasion is in progress.")
    order = [pos for pos in sorted(commits) if commits[pos]]
    if not order:
        raise ValueError("No ground forces were committed.")
    queue = [{"position": pos, "committed": commits[pos]} for pos in order[1:]]
    _open_component(state, attacker, source, order[0], commits[order[0]], queue)


# ------------------------------------------------------------------------------ nawigacja


def advance(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Przechodzi do następnego podkroku inwazji; z ESTABLISH — zamyka inwazję.

    Raises:
        ValueError: Gdy bieżący podkrok jest nierozstrzygnięty (oczekujące straty, trwa walka,
            niewykorzystane Space Cannon Defense, planeta czeka na walkę).
    """
    inv = _inv(state)
    if inv.phase is InvasionPhase.BOMBARDMENT:
        if inv.bombard_pending:
            raise ValueError("Assign the bombardment hits first.")
        return _enter(state, grid, registry, InvasionPhase.COMMIT)
    if inv.phase is InvasionPhase.COMMIT:
        if inv.custodians_claimed and not any(
            p in inv.committed for p in custodians.mecatol_planets(state, registry, inv.position)
        ):
            raise ValueError(
                "You removed the Custodians token - commit at least one ground force "
                "to Mecatol Rex."
            )
        if not inv.committed and not combat_planets(state, registry):
            # Brak lądowania i spornych planet: od razu do Establish Control — I2 / I7a.
            return _enter(state, grid, registry, InvasionPhase.ESTABLISH)
        if inv.source:
            # Quantum Dissemination: „Players cannot use SPACE CANNON against these units” i tylko
            # Commit / Ground Combat / Establish Control (F_yin Ω, RULES.md 62.10).
            return _enter(state, grid, registry, InvasionPhase.GROUND_COMBAT)
        return _enter(state, grid, registry, InvasionPhase.SPACE_CANNON_DEFENSE)
    if inv.phase is InvasionPhase.SPACE_CANNON_DEFENSE:
        if inv.defense_pending:
            raise ValueError("Assign the Space Cannon hits first.")
        if _defense_open(inv, state, registry):
            raise ValueError("Resolve (or decline) Space Cannon Defense on every planet first.")
        return _enter(state, grid, registry, InvasionPhase.GROUND_COMBAT)
    if inv.phase is InvasionPhase.GROUND_COMBAT:
        if state.active_combat is not None:
            raise ValueError("Finish and close the ground combat first.")
        if combat_planets(state, registry):
            raise ValueError("Ground combat is still to be fought on a planet.")
        return _enter(state, grid, registry, InvasionPhase.ESTABLISH)
    if state.exploration is not None:
        raise ValueError("Finish exploring the captured planets first.")
    closed = clear_invasion(state)
    if not inv.source:
        # Zwykła inwazja taktyczna zamknięta - krok INVASION tej akcji jest rozstrzygnięty.
        closed.invasion_resolved = True
    if inv.queue:
        # Inwazja komponentu: kolejny system z kolejki (RULES.md 62.10).
        nxt, *rest = inv.queue
        _open_component(
            closed, inv.attacker, inv.source, str(nxt["position"]), nxt["committed"], rest
        )
    return closed


# ------------------------------------------------- reakcje kart (RULES.md 53.5.d, MUTUJĄ stan)
# Efekty kart akcji grane W REAKCJI na okno inwazji pracują na klonie wołającego (jak
# ``register_effect``), więc poniższe funkcje zmieniają przekazany ``state`` w miejscu.


def parley_return(state: GameState, planet: str) -> dict[str, int]:
    """Parley: zwraca siły zaangażowane OSTATNIO na ``planet`` do przestrzeni aktywnego systemu.

    Źródło: C_action_cards (Parley) - dotyczy sił tylko JEDNEJ planety, a zwrócone jednostki
    nie mogą w tej akcji lądować na inną planetę (``parley_locked``). ⚠ ZAŁOŻENIE: „zaangażowane
    jednostki” = ostatnie zaangażowanie na tę planetę (``last_commit``), bez tych, które
    zdążyły zniknąć. Zwraca ``{base_type: liczba}`` faktycznie zwróconych.

    Raises:
        ValueError: Zły podkrok albo brak świeżo zaangażowanych sił na planecie.
    """
    inv = _phase(state, InvasionPhase.COMMIT, "Commit Ground Forces")
    latest = inv.last_commit.get(planet)
    if not latest:
        raise ValueError(f"No units were just committed to {planet}.")
    system = _system(state)
    returned: dict[str, int] = {}
    # Quantum Dissemination (F_yin Ω): bez statków z pojemnością w systemie piechota schodzi z
    # planszy; z nimi wraca do przestrzeni (limit pojemności sprawdzany później).
    to_board = not inv.source or _has_capacity_ship(state, system, inv.attacker)
    for base_type, count in sorted(latest.items()):
        here = _ground_in_zone(system, planet, inv.attacker).get(base_type, 0)
        move = min(count, here)
        if move <= 0:
            continue
        if to_board:
            unit_ops.transfer_units(
                state, system, planet, system, "space", inv.attacker, base_type, move
            )
        else:
            unit_ops.remove_units(state, system, planet, inv.attacker, base_type, move)
        returned[base_type] = move
        landed = inv.committed.get(planet, {})
        landed[base_type] = landed.get(base_type, 0) - move
        if landed[base_type] <= 0:
            del landed[base_type]
        inv.parley_locked[base_type] = inv.parley_locked.get(base_type, 0) + move
    if not returned:
        raise ValueError(f"The committed units are no longer on {planet}.")
    if not inv.committed.get(planet):
        inv.committed.pop(planet, None)
    del inv.last_commit[planet]
    return returned


def _bombard_log_entry(inv: InvasionState, planet: str) -> dict[str, Any]:
    for entry in reversed(inv.log):
        if entry.get("phase") == "BOMBARDMENT" and entry.get("planet") == planet:
            found: dict[str, Any] = entry
            return found
    raise ValueError(f"No bombardment roll was made against {planet}.")


def _defense_log_entry(inv: InvasionState, planet: str) -> dict[str, Any]:
    for entry in reversed(inv.log):
        if entry.get("phase") == "DEFENSE" and entry.get("planet") == planet:
            found: dict[str, Any] = entry
            return found
    raise ValueError(f"No Space Cannon Defense roll was made on {planet}.")


def defense_roller(state: GameState, planet: str) -> str:
    """Gracz, który rzucił Space Cannon Defense na ``planet`` (z dziennika inwazji)."""
    return str(_defense_log_entry(_inv(state), planet)["defender"])


def cancel_defense_hits(state: GameState, planet: str, count: int = 1) -> int:
    """Anuluje do ``count`` trafień Space Cannon Defense czekających na ``planet``.

    Bez trafień planeta jest rozstrzygnięta (jak po rzucie bez trafień). Zwraca anulowane.

    Raises:
        ValueError: Brak trafień do przypisania na planecie.
    """
    inv = _inv(state)
    pending = inv.defense_pending.get(planet, 0)
    if pending <= 0:
        raise ValueError(f"There are no Space Cannon hits to cancel on {planet}.")
    cancelled = min(max(0, count), pending)
    entry = _defense_log_entry(inv, planet)
    entry["hits"] = pending - cancelled
    entry["cancelled"] = int(entry.get("cancelled", 0)) + cancelled
    if pending - cancelled > 0:
        inv.defense_pending[planet] = pending - cancelled
    else:
        del inv.defense_pending[planet]
        inv.defense_resolved.append(planet)
    return cancelled


def cancel_bombardment_hits(state: GameState, planet: str, count: int = 1) -> int:
    """Anuluje do ``count`` trafień bombardowania czekających na ``planet`` (Tellurian, 62.18).

    Bez trafień planeta jest rozstrzygnięta jak po rzucie bez trafień. Zwraca anulowane.

    Raises:
        ValueError: Brak trafień bombardowania do przypisania na planecie.
    """
    inv = _inv(state)
    pending = inv.bombard_pending.get(planet, 0)
    if pending <= 0:
        raise ValueError(f"There are no bombardment hits to cancel on {planet}.")
    cancelled = min(max(0, count), pending)
    entry = _bombard_log_entry(inv, planet)
    entry["hits"] = pending - cancelled
    entry["cancelled"] = int(entry.get("cancelled", 0)) + cancelled
    if pending - cancelled > 0:
        inv.bombard_pending[planet] = pending - cancelled
    else:
        del inv.bombard_pending[planet]
    return cancelled


def pending_defense_entries(state: GameState) -> tuple[str, list[dict[str, Any]]] | None:
    """Rzuty Space Cannon Defense czekające na straty jako płaska lista wpisów (kolejność jak
    w :func:`reroll_pending_defense`) i strzelający; ``None`` = brak."""
    inv = state.invasion
    if inv is None or not inv.defense_pending:
        return None
    entries = [_defense_log_entry(inv, p) for p in sorted(inv.defense_pending)]
    flat = [dict(roll) for entry in entries for roll in entry["rolls"]]
    return str(entries[0]["defender"]), flat


def pending_bombardment_entries(state: GameState) -> tuple[str, list[dict[str, Any]]] | None:
    """Rzuty Bombardment czekające na straty (płasko, kolejność jak przy przerzucie)."""
    inv = state.invasion
    if inv is None or not inv.bombard_pending:
        return None
    entries = [_bombard_log_entry(inv, p) for p in sorted(inv.bombard_pending)]
    return inv.attacker, [dict(roll) for entry in entries for roll in entry["rolls"]]


def reroll_pending_defense(
    state: GameState,
    picks: set[tuple[int, int]] | None = None,
    source: tuple[str, str] = ("scramble_frequency", "Scramble Frequency"),
) -> int:
    """Scramble Frequency na Space Cannon Defense: przerzuca kości rzutów czekających na straty.

    ⚠ ZAŁOŻENIE: gdy trafienia czekają na kilku planetach, przerzucane są wszystkie rzuty.
    Planeta bez trafień po przerzucie jest rozstrzygnięta. Zwraca sumę trafień po przerzucie.

    Raises:
        ValueError: Brak rzutu Space Cannon Defense czekającego na przypisanie strat.
    """
    inv = _inv(state)
    planets = sorted(inv.defense_pending)
    if not planets:
        raise ValueError("There is no Space Cannon Defense roll to reroll.")
    entries = [_defense_log_entry(inv, p) for p in planets]
    flat = [dict(roll) for entry in entries for roll in entry["rolls"]]
    roller = str(entries[0]["defender"])
    fresh, total = space_cannon.reroll_entries(
        state, flat, roller=roller, picks=picks, source=source
    )
    cursor = 0
    for planet, entry in zip(planets, entries, strict=True):
        size = len(entry["rolls"])
        mine = fresh[cursor : cursor + size]
        cursor += size
        hits = sum(int(r["hits"]) for r in mine)
        entry.update({"rolls": mine, "hits": hits, "rerolled": True})
        if hits > 0:
            inv.defense_pending[planet] = hits
        else:
            del inv.defense_pending[planet]
            inv.defense_resolved.append(planet)
    return total


def reroll_pending_bombardment(
    state: GameState,
    picks: set[tuple[int, int]] | None = None,
    source: tuple[str, str] = ("scramble_frequency", "Scramble Frequency"),
) -> int:
    """Scramble Frequency na Bombardment: przerzuca kości rzutów czekających na straty.

    ⚠ ZAŁOŻENIE: przerzucane są rzuty wszystkich planet, na których trafienia wciąż czekają na
    przypisanie (to jedno użycie Bombardment). Planeta bez trafień po przerzucie jest wolna.
    Zwraca sumę trafień po przerzucie.

    Raises:
        ValueError: Brak rzutu Bombardment czekającego na przypisanie strat.
    """
    inv = _inv(state)
    planets = sorted(inv.bombard_pending)
    if not planets:
        raise ValueError("There is no Bombardment roll to reroll.")
    entries = [_bombard_log_entry(inv, p) for p in planets]
    flat = [dict(roll) for entry in entries for roll in entry["rolls"]]

    def multiplier(roll: dict[str, Any]) -> int:
        return rules_hooks.modify(
            rules_hooks.POINT_COMBAT_HIT_MULTIPLIER, state, inv.attacker, 1,
            {"kind": "bombardment", "base_type": roll.get("baseType")},
        )

    fresh, total = space_cannon.reroll_entries(
        state, flat, roller=inv.attacker, multiplier=multiplier, picks=picks, source=source
    )
    cursor = 0
    for planet, entry in zip(planets, entries, strict=True):
        size = len(entry["rolls"])
        mine = fresh[cursor : cursor + size]
        cursor += size
        hits = sum(int(r["hits"]) for r in mine)
        entry.update({"rolls": mine, "hits": hits, "rerolled": True})
        if hits > 0:
            inv.bombard_pending[planet] = hits
        else:
            del inv.bombard_pending[planet]
    return total
