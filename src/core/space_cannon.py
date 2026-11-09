"""Space Cannon Offense: strzelcy, zasięg (deep), kolejka okna, rzuty, straty (RULES.md 38).

Krok SPACE_CANNON akcji taktycznej. Po ruchu KAŻDY gracz mający jednostki z Space Cannon w
aktywnym systemie (albo ``deepSpaceCannon`` w systemie sąsiednim) może strzelić — nie tylko
aktywny gracz. Kolejka: od aktywnego gracza zgodnie z zegarem, bez graczy pozbawionych celu.
Okno to ``WindowType.SPACE_CANNON`` z ``core/timing.py`` (RULES.md 29.2).

Wszystkie parametry (``hitsOn``, kości, deep) pochodzą z WARIANTU jednostki gracza
(``combat.resolve_unit_variant``), więc ulepszenie (PDS II) samo zmienia zasięg. Funkcje CZYSTE
(``state -> state``); rzuty przez ``core/dice.py`` (seedowalne, w stanie gry).

Stan okna w ``TimingWindow.context`` (tylko str/int):
- ``position`` — aktywny system, ``log`` — JSON listy wpisów (kto, w kogo, trafienia, rzuty,
  straty);
- gdy trwa przypisywanie strat: ``roller``, ``target``, ``hits``, ``rolls`` (JSON).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, cast

from src.core import rules_hooks, timing, triggers, unit_ops
from src.core.combat import resolve_unit_variant
from src.core.dice import DIE_SIDES, count_hits, roll_dice
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, TimingWindow, WindowType
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

# Klucze kontekstu okna dotyczące trwającego przypisywania strat.
_PENDING_KEYS = ("roller", "target", "hits", "rolls")


@dataclass(frozen=True)
class SpaceCannonShooter:
    """Grupa jednostek gracza z Space Cannon w jednym miejscu (statki / planeta)."""

    player_id: str
    base_type: str
    unit_id: str
    name: str
    count: int
    hits_on: int
    dice_per_unit: int
    position: str  # system, w którym stoją
    zone: str  # "space" albo id planety
    deep: bool  # wariant ma deepSpaceCannon (może strzelać z systemu sąsiedniego)
    remote: bool = False  # strzela z systemu SĄSIEDNIEGO do aktywnego

    @property
    def total_dice(self) -> int:
        return self.count * self.dice_per_unit

    @property
    def expected_hits(self) -> float:
        """Oczekiwane trafienia grupy: kości × (11 − hitsOn)/10 (d10, wynik ≥ hitsOn)."""
        chance = max(0, min(DIE_SIDES, DIE_SIDES + 1 - self.hits_on)) / DIE_SIDES
        return round(self.total_dice * chance, 2)


@dataclass(frozen=True)
class PendingHits:
    """Trafienia czekające na przypisanie strat przez gracza-cel."""

    roller: str
    target: str
    hits: int
    rolls: list[dict[str, Any]]


# --------------------------------------------------------------------------- strzelcy


def _system_shooters(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
) -> list[SpaceCannonShooter]:
    """Wszystkie grupy z Space Cannon gracza w systemie ``position`` (statki + planety)."""
    system = state.systems.get(position)
    player = state.players.get(player_id)
    if system is None or player is None:
        return []
    groups: list[tuple[str, dict[str, int]]] = [
        ("space", system.space_units.get(player_id, {}))
    ]
    for planet_id in sorted(system.planet_units):
        groups.append((planet_id, system.planet_units[planet_id].get(player_id, {})))

    shooters: list[SpaceCannonShooter] = []
    for zone, by_type in groups:
        for base_type in sorted(by_type):
            count = by_type[base_type]
            if count <= 0:
                continue
            unit = resolve_unit_variant(
                registry,
                player.faction,
                player.technologies,
                base_type,
                player.breakthrough_unlocked,
            )
            if unit is None or unit.space_cannon_hits_on is None:
                continue
            shooters.append(
                SpaceCannonShooter(
                    player_id=player_id,
                    base_type=base_type,
                    unit_id=unit.id,
                    name=unit.name,
                    count=count,
                    hits_on=unit.space_cannon_hits_on,
                    dice_per_unit=unit.space_cannon_die_count or 1,
                    position=position,
                    zone=zone,
                    deep=unit.deep_space_cannon,
                )
            )
    return shooters


def zone_shooters(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    position: str,
    zone: str,
) -> list[SpaceCannonShooter]:
    """Grupy z Space Cannon gracza w JEDNEJ strefie systemu (np. planeta — Space Cannon Defense)."""
    return [
        s for s in _system_shooters(state, registry, player_id, position) if s.zone == zone
    ]


def offense_shooters(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
) -> list[SpaceCannonShooter]:
    """Strzelcy gracza w Space Cannon Offense aktywnego systemu (S4–S6).

    Jednostki w aktywnym systemie (statki + planety) ORAZ jednostki z ``deepSpaceCannon``
    w systemach sąsiednich (``remote=True``). Pusta lista, gdy brak aktywnego systemu.
    """
    active = state.active_system
    if active is None:
        return []
    result = _system_shooters(state, registry, player_id, active)
    for neighbor in sorted(grid.neighbors(active)):
        result.extend(
            replace(s, remote=True)
            for s in _system_shooters(state, registry, player_id, neighbor)
            if s.deep
        )
    return result


def coverage(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> dict[str, dict[str, tuple[int, float]]]:
    """Pokrycie ostrzałem: ``{pozycja: {player_id: (liczba jednostek, oczekiwane trafienia)}}``.

    Dla każdego kafelka sumuje jednostki z Space Cannon stojące w nim oraz jednostki z
    ``deepSpaceCannon`` w sąsiednich (RULES.md 38.2). Tylko kafelki faktycznie pod ostrzałem.
    Zasila soczewkę „Space Cannon range" (web-data ``pds``).
    """
    by_player_pos: dict[str, dict[str, list[SpaceCannonShooter]]] = {}
    for player_id in state.players:
        for position in state.systems:
            found = _system_shooters(state, registry, player_id, position)
            if found:
                by_player_pos.setdefault(player_id, {})[position] = found

    result: dict[str, dict[str, tuple[int, float]]] = {}
    for position in sorted(grid.positions):
        neighbors = grid.neighbors(position)
        for player_id, positions in by_player_pos.items():
            covering = list(positions.get(position, []))
            for neighbor in sorted(neighbors):
                covering.extend(s for s in positions.get(neighbor, []) if s.deep)
            if not covering:
                continue
            count = sum(s.count for s in covering)
            expected = round(sum(s.expected_hits for s in covering), 2)
            result.setdefault(position, {})[player_id] = (count, expected)
    return result


@dataclass(frozen=True)
class CannonRoll:
    """Wynik rzutu jednej grupy strzelców: kości, trafienia i dodatkowa kość (Plasma Scoring)."""

    shooter: SpaceCannonShooter
    dice: list[int]
    hits: int
    extra_dice: int = 0


def roll_cannon(
    state: GameState, shooters: list[SpaceCannonShooter], target_id: str
) -> tuple[GameState, list[CannonRoll], int]:
    """Rzuca Space Cannon grupy strzelców w ``target_id`` (Offense i Defense) — jeden punkt rzutu.

    Hooki (RULES.md 55): ``space_cannon.extra_dice`` (Plasma Scoring: +1 kość dla JEDNEJ jednostki
    właściciela, wybieramy grupę z najlepszym progiem) oraz ``space_cannon.roll_modifier`` pytany
    o właściciela CELU (Antimass Deflectors: -1 do wyniku każdej kości). Zwraca (stan, rzuty,
    suma trafień). Rzut każdej grupy to osobne ``roll_dice`` (kolejność jak w grze bez hooków).
    """
    best_by_owner: dict[str, int] = {}
    for index, shooter in enumerate(shooters):
        current = best_by_owner.get(shooter.player_id)
        if current is None or shooter.hits_on < shooters[current].hits_on:
            best_by_owner[shooter.player_id] = index
    rolled = state
    results: list[CannonRoll] = []
    total_hits = 0
    for index, shooter in enumerate(shooters):
        extra = 0
        if best_by_owner[shooter.player_id] == index:
            extra = max(
                0,
                rules_hooks.modify(
                    rules_hooks.POINT_SPACE_CANNON_EXTRA_DICE, state, shooter.player_id, 0,
                    {"base_type": shooter.base_type, "zone": shooter.zone},
                ),
            )
        modifier = rules_hooks.modify(
            rules_hooks.POINT_SPACE_CANNON_ROLL_MODIFIER, state, target_id, 0,
            {"shooter": shooter.player_id, "base_type": shooter.base_type},
        )
        rolled, dice = roll_dice(rolled, shooter.total_dice + extra)
        hits = count_hits([d + modifier for d in dice], shooter.hits_on)
        total_hits += hits
        results.append(CannonRoll(shooter, dice, hits, extra))
    return rolled, results, total_hits


# ----------------------------------------------------------------------- cele i kolejka


def _table_order(state: GameState) -> list[str]:
    """Kolejność przy stole (zgodnie z zegarem) tylko dla istniejących graczy."""
    order = [pid for pid in state.seating_order if pid in state.players]
    return order or sorted(state.players)


def target_ships(state: GameState, player_id: str) -> dict[str, int]:
    """Statki gracza w aktywnym systemie (``{base_type: liczba}``) — cele i straty (S7)."""
    active = state.active_system
    system = state.systems.get(active) if active is not None else None
    if system is None:
        return {}
    return {
        bt: c
        for bt, c in sorted(system.space_units.get(player_id, {}).items())
        if c > 0 and is_space_unit(bt)
    }


def offense_targets(state: GameState, player_id: str) -> list[str]:
    """Gracze, w których ``player_id`` może wycelować Space Cannon (S3)."""
    active_id = state.active_player_id
    if active_id is None:
        return []
    if player_id == active_id:
        return [
            pid
            for pid in _table_order(state)
            if pid != active_id and target_ships(state, pid)
        ]
    return [active_id] if target_ships(state, active_id) else []


def offense_queue(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> list[str]:
    """Kolejka strzelających: od AKTYWNEGO gracza zgodnie z zegarem (S2), bez graczy bez celu."""
    order = _table_order(state)
    active_id = state.active_player_id
    if active_id in order:
        start = order.index(active_id)
        order = order[start:] + order[:start]
    return [
        pid
        for pid in order
        if offense_shooters(state, grid, registry, pid) and offense_targets(state, pid)
    ]


# ------------------------------------------------------------------------- okno i stan


def _window(state: GameState) -> TimingWindow:
    window = state.pending_window
    if window is None or window.window_type is not WindowType.SPACE_CANNON:
        raise ValueError("No Space Cannon window is open.")
    return window


def is_open(state: GameState) -> bool:
    """Czy trwa okno Space Cannon Offense."""
    window = state.pending_window
    return window is not None and window.window_type is WindowType.SPACE_CANNON


def read_log(state: GameState) -> list[dict[str, Any]]:
    """Dziennik rozstrzygnięć (kto, w kogo, trafienia, rzuty, straty).

    Gdy okno trwa — z jego kontekstu; po zamknięciu — z ``GameState.space_cannon_log``
    (zachowany do końca akcji taktycznej, żeby panel pokazał wynik).
    """
    if state.pending_window is not None and is_open(state):
        raw = state.pending_window.context.get("log", "[]")
    else:
        raw = state.space_cannon_log
    return cast("list[dict[str, Any]]", json.loads(str(raw)))


def pending_hits(state: GameState) -> PendingHits | None:
    """Trafienia czekające na przypisanie strat (None, gdy brak)."""
    if not is_open(state):
        return None
    assert state.pending_window is not None
    ctx = state.pending_window.context
    hits = int(ctx.get("hits", 0))
    if hits <= 0:
        return None
    return PendingHits(
        roller=str(ctx["roller"]),
        target=str(ctx["target"]),
        hits=hits,
        rolls=cast("list[dict[str, Any]]", json.loads(str(ctx.get("rolls", "[]")))),
    )


def _set_context(state: GameState, **updates: str | int) -> GameState:
    """Zwraca klon stanu z uzupełnionym kontekstem okna."""
    new_state = state.clone()
    assert new_state.pending_window is not None
    new_state.pending_window.context = {**new_state.pending_window.context, **updates}
    return new_state


def _append_log(state: GameState, entry: dict[str, Any]) -> GameState:
    log = read_log(state)
    log.append(entry)
    return _set_context(state, log=json.dumps(log))


def _advance(state: GameState) -> GameState:
    """Kończy turę bieżącego respondenta; po ostatnim zamyka okno."""
    window = _window(state)
    responder = window.current_responder
    assert responder is not None
    log_json = str(window.context.get("log", "[]"))
    new_state = timing.respond_current(state, responder)
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
        # Okno znika, wynik zostaje w stanie (panel pokazuje rozstrzygnięcie).
        new_state.space_cannon_log = log_json
    return new_state


def open_offense(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Otwiera okno Space Cannon Offense dla aktywnego systemu (lub nic, gdy nikt nie strzela).

    Raises:
        ValueError: Gdy brak aktywnego systemu/gracza albo trwa INNE okno czasowe.
    """
    if state.active_system is None or state.active_player_id is None:
        raise ValueError("Space Cannon Offense needs an active system and active player.")
    if state.pending_window is not None:
        raise ValueError(
            "Another timing window is still open - resolve it before Space Cannon."
        )
    queue = offense_queue(state, grid, registry)
    if not queue:
        nothing = state.clone()
        nothing.space_cannon_log = "[]"
        return nothing
    opened = timing.open_window(
        state,
        WindowType.SPACE_CANNON,
        queue,
        context={"position": state.active_system, "log": "[]"},
    )
    opened.space_cannon_log = "[]"
    return opened


def _require_turn(state: GameState, player_id: str) -> TimingWindow:
    window = _window(state)
    if pending_hits(state) is not None:
        raise ValueError("Assign the pending hits before the next player acts.")
    if window.current_responder != player_id:
        raise ValueError(
            f"It is now {window.current_responder}'s turn for Space Cannon, not {player_id}."
        )
    return window


def fire_offense(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    target_id: str | None = None,
) -> GameState:
    """Bieżący gracz strzela WSZYSTKIM swoim Space Cannon (S4/S5) w wybranego gracza (S3).

    Rzuca kośćmi dla każdej grupy strzelców. Gdy są trafienia i cel ma statki, okno czeka na
    przypisanie strat (``assign_hits``); inaczej tura od razu przechodzi dalej.

    Raises:
        ValueError: Zła kolejność, brak strzelców/celu, nielegalny cel.
    """
    _require_turn(state, player_id)
    shooters = offense_shooters(state, grid, registry, player_id)
    if not shooters:
        raise ValueError("This player has no Space Cannon units in range.")
    targets = offense_targets(state, player_id)
    if not targets:
        raise ValueError("No legal target for Space Cannon.")
    if target_id is None:
        if len(targets) != 1:
            raise ValueError("Choose which player to shoot at.")
        target_id = targets[0]
    elif target_id not in targets:
        raise ValueError(f"Illegal Space Cannon target: {target_id}.")

    rolled, cannon_rolls, total_hits = roll_cannon(state, shooters, target_id)
    rolls: list[dict[str, Any]] = [
        {
            "baseType": r.shooter.base_type,
            "name": r.shooter.name,
            "hitsOn": r.shooter.hits_on,
            "position": r.shooter.position,
            "zone": r.shooter.zone,
            "dice": r.dice,
            "hits": r.hits,
        }
        for r in cannon_rolls
    ]

    entry: dict[str, Any] = {
        "roller": player_id,
        "target": target_id,
        "hits": total_hits,
        "rolls": rolls,
        "destroyed": {},
        "passed": False,
    }
    rolled = _append_log(rolled, entry)
    triggers.fire(
        rolled, GameEvent.UNIT_ABILITY_USED, Moment.AFTER, subject=player_id,
        ctx={"ability": "space_cannon", "player": player_id, "hits": total_hits,
             "target": target_id},
    )
    if total_hits == 0 or not target_ships(rolled, target_id):
        return _advance(rolled)
    return _set_context(
        rolled,
        roller=player_id,
        target=target_id,
        hits=total_hits,
        rolls=json.dumps(rolls),
    )


def pass_offense(state: GameState, player_id: str) -> GameState:
    """Bieżący gracz rezygnuje ze strzału (Space Cannon jest opcjonalny — S1)."""
    _require_turn(state, player_id)
    logged = _append_log(
        state,
        {
            "roller": player_id,
            "target": "",
            "hits": 0,
            "rolls": [],
            "destroyed": {},
            "passed": True,
        },
    )
    return _advance(logged)


def assign_hits(
    state: GameState, target_id: str, losses: dict[str, int]
) -> GameState:
    """Gracz-cel niszczy własne statki za trafienia (S7) i okno przechodzi dalej.

    ``losses`` = ``{base_type: liczba}``. Suma musi być równa min(trafienia, jego statki w
    aktywnym systemie); nie wolno niszczyć więcej niż ma dany typ.

    Raises:
        ValueError: Brak trafień do przypisania, zły gracz, zła liczba/typ strat.
    """
    pending = pending_hits(state)
    if pending is None:
        raise ValueError("There are no Space Cannon hits to assign.")
    if target_id != pending.target:
        raise ValueError("Only the targeted player assigns the hits.")
    ships = target_ships(state, target_id)
    required = min(pending.hits, sum(ships.values()))
    cleaned = {bt: c for bt, c in losses.items() if c > 0}
    for base_type, count in cleaned.items():
        if count > ships.get(base_type, 0):
            raise ValueError(
                f"Cannot destroy {count} {base_type}: only {ships.get(base_type, 0)} in the system."
            )
    if sum(cleaned.values()) != required:
        raise ValueError(f"Destroy exactly {required} ship(s) for these hits.")

    new_state = state.clone()
    assert new_state.active_system is not None
    system = new_state.systems[new_state.active_system]
    for base_type, count in cleaned.items():
        unit_ops.remove_units(
            new_state, system, "space", target_id, base_type, count, UnitCause.DESTROYED
        )

    log = read_log(new_state)
    if log:
        log[-1]["destroyed"] = cleaned
    assert new_state.pending_window is not None
    context = {
        k: v for k, v in new_state.pending_window.context.items() if k not in _PENDING_KEYS
    }
    context["log"] = json.dumps(log)
    new_state.pending_window.context = context
    return _advance(new_state)
