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
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any, cast

from src.core import (
    action_adjacency,
    battle,
    capacity,
    entropic_scar,
    exhaust,
    extra_dice,
    legendary_planets,
    planet_stats,
    rules_hooks,
    timing,
    triggers,
)
from src.core.combat import resolve_unit_variant
from src.core.dice import DIE_SIDES, count_hits, next_rng, record_table_roll, roll_dice
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, TimingWindow, WindowType
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import is_space_unit

# Klucze kontekstu okna dotyczące trwającego przypisywania strat.
_PENDING_KEYS = ("roller", "target", "hits", "rolls", "gls")
# Graviton Laser System (RULES.md 57): trafienia strzelca, który go wyczerpał, idą w statki
# niemyśliwskie, o ile są.
GLS = "gls"


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
    def key(self) -> str:
        """Identyfikator grupy (właściciel|system|strefa|typ) - wybór jednostki Plasma Scoring."""
        return f"{self.player_id}|{self.position}|{self.zone}|{self.base_type}"

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


def pds_disabled(state: GameState, owner_id: str) -> bool:
    """Czy PDS gracza ``owner_id`` są wyłączone (Disable: tracą PLANETARY SHIELD i SPACE CANNON).

    Efekt jest własnością gracza, który go zagrał, więc pytamy KAŻDEGO gracza przy stole, czy
    wyłącza PDS ``owner_id`` (hook PERMIT ``POINT_PDS_DISABLED``, ctx ``victim``).
    """
    return any(
        rules_hooks.permits(rules_hooks.POINT_PDS_DISABLED, state, pid, {"victim": owner_id})
        for pid in state.players
    )


def granted_space_cannon(
    state: GameState, player_id: str, base_type: str
) -> tuple[int, int] | None:
    """Space Cannon nadany jednostce przez komponent: ``(próg trafienia, kości)`` albo ``None``.

    Hook FORBID punktu ``space_cannon.granted`` jako zbiór napisów ``"<typ>:<próg>:<kości>"``
    (jak ``bombardment.granted_hits_on``); przy wielu bierzemy najniższy próg.
    """
    best: tuple[int, int] | None = None
    for item in rules_hooks.forbidden(rules_hooks.POINT_SPACE_CANNON_GRANTED, state, player_id):
        unit_type, hits_on, dice = item.split(":")
        if unit_type == base_type and (best is None or int(hits_on) < best[0]):
            best = (int(hits_on), int(dice))
    return best


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
    pds_off: bool | None = None  # liczone leniwie: tylko gdy gracz w ogóle ma PDS
    if entropic_scar.unit_abilities_blocked(state, position, registry):
        groups = []  # Entropic Scar: jednostki w bliźnie nie używają SPACE CANNON (RULES.md 1.5)
    for zone, by_type in groups:
        for base_type in sorted(by_type):
            count = by_type[base_type]
            if count <= 0:
                continue
            if base_type == "pds":
                if pds_off is None:
                    pds_off = pds_disabled(state, player_id)
                if pds_off:
                    continue
            unit = resolve_unit_variant(
                registry,
                player.faction,
                player.technologies,
                base_type,
                player.breakthrough_unlocked, player.breakthrough_flipped,
            )
            if unit is None:
                continue
            hits_on = unit.space_cannon_hits_on
            dice_per_unit = unit.space_cannon_die_count or 1
            deep = unit.deep_space_cannon
            if hits_on is None:
                # Hook: jednostka bez własnego Space Cannon dostaje go z komponentu (Lightrail
                # Ordnance: stocznia ma SPACE CANNON 5 (x2) także na sąsiednie systemy).
                granted = granted_space_cannon(state, player_id, base_type)
                if granted is None:
                    continue
                hits_on, dice_per_unit = granted
                deep = True
            shooters.append(
                SpaceCannonShooter(
                    player_id=player_id,
                    base_type=base_type,
                    unit_id=unit.id,
                    name=unit.name,
                    count=count,
                    hits_on=hits_on,
                    dice_per_unit=dice_per_unit,
                    position=position,
                    zone=zone,
                    deep=deep,
                )
            )
    # Attachment z SPACE CANNON „as if it were a unit” (Geoform Titans, RULES.md 62.18): strzela
    # kontroler planety (F_ul geoform 1); grupa jak Custodian's Favour - id attachmentu w roli typu.
    if not entropic_scar.unit_abilities_blocked(state, position, registry):
        for planet_id, owner in sorted(system.planet_owners.items()):
            if owner != player_id:
                continue
            for attachment in planet_stats.attachment_defs(state, registry, planet_id):
                if attachment.space_cannon_hits_on is None:
                    continue
                shooters.append(
                    SpaceCannonShooter(
                        player_id=player_id,
                        base_type=attachment.id,
                        unit_id=attachment.id,
                        name=attachment.name or attachment.id,
                        count=1,
                        hits_on=attachment.space_cannon_hits_on,
                        dice_per_unit=attachment.space_cannon_die_count or 1,
                        position=position,
                        zone=planet_id,
                        deep=False,
                    )
                )
    # Custodian's Favour (Custodia Vigilia): kontrolowany Mecatol Rex sam dostaje SPACE CANNON.
    # To nie jednostka, więc strzelec to „grupa" z id planety w roli typu i strefy.
    mecatol = legendary_planets.mecatol_grants_planet(state, player_id, position)
    cannon = legendary_planets.favour_space_cannon(registry)
    if mecatol is not None and cannon is not None:
        favour = registry.planets[legendary_planets.CUSTODIAN_FAVOUR_PLANET]
        shooters.append(
            SpaceCannonShooter(
                player_id=player_id,
                base_type=mecatol,
                unit_id=favour.id,
                name=favour.legendary_ability_name or favour.name,
                count=1,
                hits_on=cannon[0],
                dice_per_unit=cannon[1],
                position=position,
                zone=mecatol,
                deep=False,
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
    if active is None or entropic_scar.unit_abilities_blocked(state, active, registry):
        # Entropic Scar: SPACE CANNON nie strzela w jednostki w bliźnie (RULES.md 1.5).
        return []
    result = _system_shooters(state, registry, player_id, active)
    # Sąsiedztwo z akcji taktycznej (SCC, Lazax Gate Folding) działa też dla Deep Space Cannon.
    for neighbor in sorted(action_adjacency.neighbors(state, grid, active)):
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
        if entropic_scar.unit_abilities_blocked(state, position, registry):
            continue  # Entropic Scar: nikt nie strzela w jednostki w bliźnie (RULES.md 1.5)
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
    modifier: int = 0  # modyfikator wyniku kości (Antimass Deflectors celu: -1)


def plasma_extra_dice(state: GameState, shooter: SpaceCannonShooter) -> int:
    """Ile dodatkowych kości dałby Plasma Scoring tej grupie (0 = właściciel nie ma technologii)."""
    return max(
        0,
        rules_hooks.modify(
            rules_hooks.POINT_SPACE_CANNON_EXTRA_DICE, state, shooter.player_id, 0,
            {"base_type": shooter.base_type, "zone": shooter.zone},
        ),
    )


def cannon_extra(
    state: GameState,
    shooters: list[SpaceCannonShooter],
    plasma_unit: str | None = None,
    extra_picks: Mapping[str, str] | None = None,
) -> dict[str, int]:
    """Dodatkowe kości grup strzelców ``{klucz grupy: kości}`` (``core/extra_dice``).

    ``extra_picks`` = ``{źródło: grupa | auto | none}`` (każde źródło osobno - decyzja
    użytkownika 2026-11-18); ``plasma_unit`` (zgodność wsteczna) = wszystkie źródła tej grupie.

    Raises:
        ValueError: Wybór wskazuje grupę, która nie strzela, albo brak źródła kości.
    """
    if plasma_unit and plasma_unit not in {s.key for s in shooters}:
        raise ValueError("Plasma Scoring: choose one of the units that fire.")
    bonus: dict[str, int] = {}
    for owner in sorted({s.player_id for s in shooters}):
        mine = {s.key: s.hits_on for s in shooters if s.player_id == owner}
        extra = extra_dice.sources(state, owner, rules_hooks.POINT_SPACE_CANNON_EXTRA_DICE)
        if plasma_unit:
            if plasma_unit not in mine:
                continue
            if not extra:
                raise ValueError("Plasma Scoring is not available.")
            picks = {e.key: plasma_unit for e in extra}
        else:
            keys = {e.key for e in extra}
            picks = {
                k: v for k, v in (extra_picks or {}).items()
                if k in keys and (v in mine or v in (extra_dice.AUTO, "none"))
            }
        bonus.update(extra_dice.assign(extra, mine, picks))
    return bonus


def roll_cannon(
    state: GameState,
    shooters: list[SpaceCannonShooter],
    target_id: str,
    plasma_unit: str | None = None,
    extra_picks: Mapping[str, str] | None = None,
) -> tuple[GameState, list[CannonRoll], int]:
    """Rzuca Space Cannon grupy strzelców w ``target_id`` (Offense i Defense) — jeden punkt rzutu.

    Hooki (RULES.md 55): ``space_cannon.extra_dice`` (Plasma Scoring: „1 z tych jednostek MOŻE
    rzucić 1 dodatkową kością" - gracz wskazuje grupę kluczem ``plasma_unit``, bez wyboru nie ma
    dodatkowej kości) oraz ``space_cannon.roll_modifier`` pytany o właściciela CELU (Antimass
    Deflectors: -1 do wyniku każdej kości). Zwraca (stan, rzuty, suma trafień). Rzut każdej
    grupy to osobne ``roll_dice`` (kolejność jak w grze bez hooków).

    Raises:
        ValueError: ``plasma_unit`` nie wskazuje strzelającej grupy albo brak Plasma Scoring.
    """
    bonus = cannon_extra(state, shooters, plasma_unit, extra_picks)
    rolled = state
    results: list[CannonRoll] = []
    total_hits = 0
    for shooter in shooters:
        extra = bonus.get(shooter.key, 0)
        modifier = rules_hooks.modify(
            rules_hooks.POINT_SPACE_CANNON_ROLL_MODIFIER, state, target_id, 0,
            {"shooter": shooter.player_id, "base_type": shooter.base_type},
        )
        rolled, dice = roll_dice(rolled, shooter.total_dice + extra)
        hits = count_hits([d + modifier for d in dice], shooter.hits_on)
        total_hits += hits
        results.append(CannonRoll(shooter, dice, hits, extra, modifier))
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
    # Solar Flare: inni gracze nie mogą używać Space Cannon Offense przeciw statkom właściciela
    # hooka (aktywnego gracza). Space Cannon Defense (inwazja) tego nie dotyczy.
    if rules_hooks.permits(
        rules_hooks.POINT_SPACE_CANNON_OFFENSE_IMMUNE, state, active_id, {"shooter": player_id}
    ):
        return []
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


def _advance_in_place(state: GameState) -> None:
    """To samo co ``_advance``, ale MUTUJE ``state`` (dla efektów kart pracujących na klonie)."""
    advanced = _advance(state)
    state.pending_window = advanced.pending_window
    state.space_cannon_log = advanced.space_cannon_log


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


def _without_sustain_trace(state: GameState) -> GameState:
    """Kolejny krok Space Cannon zamyka okno Direct Hit po poprzednim przypisaniu (nowy stan)."""
    if not state.sustain_trace:
        return state
    cleared = state.clone()
    cleared.sustain_trace = []
    return cleared


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
    *,
    exhaust_gls: bool = False,
    plasma_unit: str | None = None,
    extra_picks: Mapping[str, str] | None = None,
) -> GameState:
    """Bieżący gracz strzela WSZYSTKIM swoim Space Cannon (S4/S5) w wybranego gracza (S3).

    ``plasma_unit`` = klucz grupy (``SpaceCannonShooter.key``), której jednostka rzuca 1 kością
    więcej dzięki Plasma Scoring (decyzja gracza; ``None`` = bez dodatkowej kości).

    ``exhaust_gls=True`` = gracz ŚWIADOMIE wyczerpuje Graviton Laser System przed strzałem:
    trafienia trzeba wtedy przypisać do statków niemyśliwskich, o ile są (decyzja gracza).

    Rzuca kośćmi dla każdej grupy strzelców. Gdy są trafienia i cel ma statki, okno czeka na
    przypisanie strat (``assign_hits``); inaczej tura od razu przechodzi dalej.

    Raises:
        ValueError: Zła kolejność, brak strzelców/celu, nielegalny cel.
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    state = _without_sustain_trace(state)
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

    if exhaust_gls:
        owner = state.players[player_id]
        if GLS not in owner.technologies or GLS in owner.exhausted_technologies:
            raise ValueError("Graviton Laser System is not ready.")
    rolled, cannon_rolls, total_hits = roll_cannon(
        state, shooters, target_id, plasma_unit, extra_picks
    )
    if exhaust_gls:
        rolled = rolled.clone()
        exhaust.exhaust_technology(rolled, player_id, GLS)
    rolls: list[dict[str, Any]] = [
        {
            "baseType": r.shooter.base_type,
            "name": r.shooter.name,
            "hitsOn": r.shooter.hits_on,
            "position": r.shooter.position,
            "zone": r.shooter.zone,
            "dice": r.dice,
            "hits": r.hits,
            "modifier": r.modifier,
            "extraDice": r.extra_dice,
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
        gls=1 if exhaust_gls else 0,
    )


def pass_offense(state: GameState, player_id: str) -> GameState:
    """Bieżący gracz rezygnuje ze strzału (Space Cannon jest opcjonalny — S1)."""
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    state = _without_sustain_trace(state)
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


def combat_view(
    state: GameState, target_id: str, registry: StaticDataRegistry | None
) -> dict[str, battle.CombatUnit]:
    """Statki celu jako jednostki walki (Sustain Damage, uszkodzenia) — do przypisania strat."""
    reg = registry if registry is not None else rules_hooks.bound_registry()
    active = state.active_system
    if reg is None or active is None:
        return {}
    units = battle.combat_units(
        state, None, reg, kind="space", position=active, planet=None, player_id=target_id
    )
    return {u.base_type: u for u in battle.ability_hit_targets(state, target_id, units)}


def required_hits(
    state: GameState, target_id: str, registry: StaticDataRegistry | None = None
) -> int:
    """Ile trafień cel musi pokryć: min(trafienia, statki + użycia Sustain Damage) — S7.

    ``R_sustain_damage``: Sustain Damage działa przeciw KAŻDEMU trafieniu, także z Space Cannon.
    """
    pending = pending_hits(state)
    if pending is None:
        return 0
    units = combat_view(state, target_id, registry)
    if not units:
        return min(pending.hits, sum(target_ships(state, target_id).values()))
    cancels = battle.sustain_cancels(state, target_id)
    absorbable = sum(
        u.count + (cancels * u.sustainable if u.sustain else 0) for u in units.values()
    ) + (cancels if any(u.granted > 0 for u in units.values()) else 0)
    return min(pending.hits, absorbable)


def assign_hits(
    state: GameState,
    target_id: str,
    losses: dict[str, int] | None = None,
    *,
    sustain: dict[str, int] | None = None,
    destroy_damaged: dict[str, int] | None = None,
    registry: StaticDataRegistry | None = None,
) -> GameState:
    """Gracz-cel pokrywa trafienia (S7): Sustain Damage albo zniszczenie, okno idzie dalej.

    ``losses`` = niszczone NIEUSZKODZONE statki ``{base_type: liczba}``, ``sustain`` = użycia
    Sustain Damage (statek staje się uszkodzony), ``destroy_damaged`` = niszczone uszkodzone.
    Walidacja planu wspólna z walką i Space Cannon Defense (``battle.plan_losses``); suma musi
    pokryć ``required_hits``.

    Raises:
        ValueError: Brak trafień do przypisania, zły gracz, zła liczba/typ strat.
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    pending = pending_hits(state)
    if pending is None:
        raise ValueError("There are no Space Cannon hits to assign.")
    if target_id != pending.target:
        raise ValueError("Only the targeted player assigns the hits.")
    ships = target_ships(state, target_id)
    destroy = {bt: c for bt, c in (losses or {}).items() if c > 0}
    sustained = {bt: c for bt, c in (sustain or {}).items() if c > 0}
    destroyed_damaged = {bt: c for bt, c in (destroy_damaged or {}).items() if c > 0}
    for base_type in set(destroy) | set(sustained) | set(destroyed_damaged):
        if base_type not in ships:
            raise ValueError(f"Cannot assign hits to {base_type}: only 0 in the system.")
    units = combat_view(state, target_id, registry)
    required = required_hits(state, target_id, registry)
    plan = battle.plan_losses(
        units, sustained, destroy, destroyed_damaged, required,
        battle.sustain_cancels(state, target_id),
    )
    if state.pending_window is not None and int(state.pending_window.context.get("gls", 0)):
        non_fighters = sum(n for bt, n in ships.items() if bt != "fighter")
        chosen = sum(
            sustained.get(bt, 0) + destroy.get(bt, 0) + destroyed_damaged.get(bt, 0)
            for bt in ships
            if bt != "fighter"
        )
        if chosen < min(required, non_fighters):
            raise ValueError(
                "Graviton Laser System: hits must be assigned to non-fighter ships if able."
            )

    new_state = state.clone()
    assert new_state.active_system is not None
    battle.apply_losses(new_state, new_state.active_system, "space", target_id, units, plan)
    used = battle.sustained_of(plan, sustained)
    for base_type, count in used.items():
        triggers.fire(
            new_state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject=target_id,
            ctx={"player": target_id, "base_type": base_type, "count": count},
        )
    # Ślad dla Direct Hit („after another player's ship uses SUSTAIN DAMAGE to cancel a hit
    # produced by your units” - także poza walką, ruling C_action_cards; RULES.md 53.5.c).
    new_state.sustain_trace = [
        {
            "player": target_id, "base_type": base_type, "count": count,
            "by": pending.roller, "position": new_state.active_system,
        }
        for base_type, count in used.items()
        if count > 0
    ]

    log = read_log(new_state)
    if log:
        log[-1]["destroyed"] = battle.losses_of(units, plan)
        log[-1]["sustained"] = used
    assert new_state.pending_window is not None
    context = {
        k: v for k, v in new_state.pending_window.context.items() if k not in _PENDING_KEYS
    }
    context["log"] = json.dumps(log)
    new_state.pending_window.context = context
    return _capacity_now(_advance(new_state), registry, target_id)


def _capacity_now(
    state: GameState, registry: StaticDataRegistry | None, target_id: str
) -> GameState:
    """Cel stracił nosicieli: nadwyżkę ładunku usuwa NATYCHMIAST, zanim Space Cannon pójdzie dalej.

    F_xxcha (Indomitus): „their ships are removed by another player's space cannon roll, they must
    immediately remove units to meet their capacity limit. They will not resolve the Space Cannon
    abilities of any of their removed mechs" (RULES.md 39.6 C3, 42.1). Okno ``CAPACITY`` zawiesza
    okno Space Cannon (``timing.interrupt``); gracz sam wybiera, co usuwa.
    """
    position = state.active_system
    if registry is None or position is None:
        return state
    if target_id not in capacity.players_with_excess(state, registry, position):
        return state
    return timing.interrupt(
        state, WindowType.CAPACITY, [target_id], context={"position": position}
    )


# ------------------------------------------------- reakcje kart (RULES.md 53.5.d, MUTUJĄ stan)
# Poniższe funkcje wołają efekty kart akcji grane W REAKCJI: pracują na klonie wołającego
# (jak ``register_effect``), więc zmieniają przekazany ``state`` w miejscu.


def cancel_pending_hits(state: GameState, count: int = 1) -> int:
    """Anuluje do ``count`` trafień czekających na przypisanie (Maneuvering Jets).

    Gdy zostaje 0 trafień, nie ma czego przypisywać: tura strzelającego przechodzi dalej tak,
    jak po rzucie bez trafień. Zwraca liczbę faktycznie anulowanych trafień.

    Raises:
        ValueError: Brak trafień Space Cannon do przypisania.
    """
    pending = pending_hits(state)
    if pending is None:
        raise ValueError("There are no Space Cannon hits to cancel.")
    cancelled = min(max(0, count), pending.hits)
    left = pending.hits - cancelled
    log = read_log(state)
    if log:
        log[-1]["hits"] = left
        log[-1]["cancelled"] = int(log[-1].get("cancelled", 0)) + cancelled
    window = _window(state)
    context = dict(window.context)
    context["log"] = json.dumps(log)
    if left > 0:
        context["hits"] = left
        window.context = context
        return cancelled
    window.context = {k: v for k, v in context.items() if k not in _PENDING_KEYS}
    _advance_in_place(state)
    return cancelled


def reroll_entries(
    state: GameState,
    entries: list[dict[str, Any]],
    *,
    roller: str,
    multiplier: Callable[[dict[str, Any]], int] | None = None,
    picks: set[tuple[int, int]] | None = None,
    source: tuple[str, str] = ("scramble_frequency", "Scramble Frequency"),
) -> tuple[list[dict[str, Any]], int]:
    """Przerzuca WSZYSTKIE kości zapisanych rzutów (Scramble Frequency) - MUTUJE licznik RNG.

    ``entries`` = wpisy rzutów jak w dzienniku (``dice``, ``hitsOn``, ``modifier``). Liczba kości
    zostaje ta sama (łącznie z dodatkową kością Plasma Scoring), trafienia liczone od nowa
    (``multiplier(wpis)`` = mnożnik trafień, np. X-89 ΩΩ; domyślnie 1). Rzut idzie na stół
    (``record_table_roll``). Zwraca (nowe wpisy, suma trafień).

    ``picks`` = przerzuć TYLKO te kości ``(indeks wpisu, indeks kości)`` (Agnlan Oln: „reroll any
    of those dice"); ``source`` = (id, nazwa) źródła przerzutu na stole kości.
    """
    rng = next_rng(state)
    fresh: list[dict[str, Any]] = []
    total = 0
    all_dice: list[int] = []
    for e_index, entry in enumerate(entries):
        old = [int(d) for d in entry.get("dice", [])]
        dice_now = [
            rng.randint(1, DIE_SIDES) if picks is None or (e_index, d_index) in picks else d
            for d_index, d in enumerate(old)
        ]
        modifier = int(entry.get("modifier", 0))
        factor = multiplier(entry) if multiplier is not None else 1
        hits = count_hits([d + modifier for d in dice_now], int(entry["hitsOn"])) * factor
        fresh.append({**entry, "dice": dice_now, "hits": hits})
        total += hits
        all_dice.extend(
            d for d_index, d in enumerate(dice_now)
            if picks is None or (e_index, d_index) in picks
        )
    thresholds = {int(e["hitsOn"]) for e in entries}
    record_table_roll(
        state, roller, source[0], source[1], all_dice,
        hits_on=thresholds.pop() if len(thresholds) == 1 else None,
        summary=f"{total} hit(s) after the reroll",
    )
    return fresh, total


def reroll_pending(
    state: GameState,
    picks: set[tuple[int, int]] | None = None,
    source: tuple[str, str] = ("scramble_frequency", "Scramble Frequency"),
) -> int:
    """Scramble Frequency na Space Cannon Offense: przerzuca kości rzutu czekającego na straty.

    Zwraca nową liczbę trafień. Po przerzucie bez trafień (albo bez celów do trafienia) tura
    strzelającego przechodzi dalej.

    Raises:
        ValueError: Brak rzutu Space Cannon czekającego na przypisanie strat.
    """
    pending = pending_hits(state)
    if pending is None:
        raise ValueError("There is no Space Cannon roll to reroll.")
    fresh, total = reroll_entries(
        state, pending.rolls, roller=pending.roller, picks=picks, source=source
    )
    log = read_log(state)
    if log:
        log[-1].update({"hits": total, "rolls": fresh, "rerolled": True})
    window = _window(state)
    context = dict(window.context)
    context["log"] = json.dumps(log)
    if total == 0 or not target_ships(state, pending.target):
        window.context = {k: v for k, v in context.items() if k not in _PENDING_KEYS}
        _advance_in_place(state)
        return total
    context["hits"] = total
    context["rolls"] = json.dumps(fresh)
    window.context = context
    return total


def open_remote_shot(
    state: GameState, shooter: SpaceCannonShooter, target_id: str
) -> int:
    """Pojedynczy strzał Space Cannon POZA kolejką Offense (Experimental Battlestation).

    Rzuca ``shooter`` w statki ``target_id`` w aktywnym systemie. Trafienia czekają w oknie
    ``SPACE_CANNON`` na przypisanie strat przez gracza-cel (``assign_hits``); bez trafień okno
    się nie otwiera (wynik trafia do dziennika). Zwraca liczbę trafień.

    Raises:
        ValueError: Brak aktywnego systemu albo trwa inne okno czasowe.
    """
    if state.active_system is None:
        raise ValueError("There is no active system.")
    if state.pending_window is not None:
        raise ValueError("Another timing window is still open - resolve it first.")
    rolled, cannon_rolls, total = roll_cannon(state, [shooter], target_id)
    state.rng_seed = rolled.rng_seed
    state.rng_counter = rolled.rng_counter
    rolls: list[dict[str, Any]] = [
        {
            "baseType": r.shooter.base_type,
            "name": r.shooter.name,
            "hitsOn": r.shooter.hits_on,
            "position": r.shooter.position,
            "zone": r.shooter.zone,
            "dice": r.dice,
            "hits": r.hits,
            "modifier": r.modifier,
            "extraDice": r.extra_dice,
        }
        for r in cannon_rolls
    ]
    owner = shooter.player_id
    entry: dict[str, Any] = {
        "roller": owner, "target": target_id, "hits": total, "rolls": rolls,
        "destroyed": {}, "passed": False,
    }
    triggers.fire(
        state, GameEvent.UNIT_ABILITY_USED, Moment.AFTER, subject=owner,
        ctx={"ability": "space_cannon", "player": owner, "hits": total, "target": target_id},
    )
    log_json = json.dumps([entry])
    if total == 0 or not target_ships(state, target_id):
        state.space_cannon_log = log_json
        return total
    state.pending_window = TimingWindow(
        window_type=WindowType.SPACE_CANNON,
        queue=[owner],
        context={
            "position": state.active_system,
            "log": log_json,
            "roller": owner,
            "target": target_id,
            "hits": total,
            "rolls": json.dumps(rolls),
            "gls": 0,
        },
    )
    return total
