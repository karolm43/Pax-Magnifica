"""The Fracture (Thunder's Edge) — wejście do gry, jednostki neutralne, ingress/egress.

Reguły: ``docs/rules_tirules/R_fracture.md``, ``R_breakthroughs.md``, ``R_neutral_units.md``
(RULES.md 50). Zero logiki zdolności przełomów — tu tylko CO się dzieje, gdy Fracture wchodzi
do gry (z rzutu po zdobyciu przełomu albo z efektu), nie KTO ją wywołuje.

Mapa (``HexGrid``) nie jest częścią ``GameState``: kafle The Fracture dosynchronizowuje
``sync_grid`` ze stanu (``state.fracture.in_play``) przy każdym odczycie, tak jak żetony wormhole,
więc Undo/Redo wycofuje je razem ze stanem.

Funkcje publiczne zwracają NOWY ``GameState`` (klon) albo rzucają ``ValueError``.
"""

from __future__ import annotations

from typing import Any

from src.core import variants
from src.core.board_edit import planet_position
from src.core.dice import DIE_SIDES, next_rng, record_table_roll
from src.core.expedition_state import IngressChoice
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, SystemState
from src.core.hex_grid import Hex, HexGrid
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.planet_stats import planet_stats
from src.core.registry import StaticDataRegistry
from src.core.system_planets import planets_of_system
from src.core.technology import COLORS
from src.core.unit_ops import UnitCause, place_units

# Kafle The Fracture i ich pozycje (AsyncTI4: ``frac1..frac7`` obok krawędzi planszy).
FRACTURE_TILE_IDS: tuple[str, ...] = tuple(f"fracture{i}" for i in range(1, 8))
FRACTURE_POSITIONS: tuple[str, ...] = tuple(f"frac{i}" for i in range(1, 8))

# Wynik kości, przy którym Fracture wchodzi do gry (R_fracture: „On a result of 1 or 10";
# „0" na kości d10 to 10).
FRACTURE_ROLL_SUCCESS: frozenset[int] = frozenset({1, 10})

# Liczba żetonów ingress na kolor: przełom z synergią -> 3 na każdy z 2 kolorów; inaczej
# (efekt bez synergii, Nekro) -> po 1 na każdy z 4 kolorów (R_fracture).
INGRESS_PER_SYNERGY_COLOR = 3
INGRESS_PER_COLOR_NO_SYNERGY = 1

# Układ kafli: łuk 7 sąsiadujących heksów (frac1..frac4 w górę-prawo, frac4..frac7 w dół-prawo),
# daleko od pierścieni planszy — Fracture nie sąsiaduje geometrycznie z mapą (lokalizacja jest
# dowolna i bez skutków mechanicznych — R_fracture). Kierunki z tabeli pozycji AsyncTI4.
_ORIGIN = Hex(-60, 30, 30)
_UP_RIGHT = (1, 0, -1)
_DOWN_RIGHT = (1, -1, 0)


def fracture_hex(position: str) -> Hex:
    """Współrzędna kubiczna kafla ``frac1..frac7`` (łuk sąsiadujących heksów)."""
    index = FRACTURE_POSITIONS.index(position)
    q, r, s = _ORIGIN.q, _ORIGIN.r, _ORIGIN.s
    for step in range(index):
        dq, dr, ds = _UP_RIGHT if step < 3 else _DOWN_RIGHT
        q, r, s = q + dq, r + dr, s + ds
    return Hex(q, r, s)


# Jednostki neutralne wystawiane z odwrotu kafli (R_neutral_units: „as indicated on the reverse
# side of The Fracture tiles"). Klucz: id kafla -> strefa ("space" albo planeta) -> typ -> liczba.
# ⚠️ ZAŁOŻENIE: liczby z AsyncTI4 (``FractureService.spawnFracture``) — tył kafli to
# komponent fizyczny, którego nie ma w zrzucie tirules; do potwierdzenia przez użytkownika.
NEUTRAL_SETUP: dict[str, dict[str, dict[str, int]]] = {
    "fracture1": {"space": {"cruiser": 2}, "cocytus": {"infantry": 2}},
    "fracture4": {
        "space": {"dreadnought": 2, "destroyer": 1},
        "styx": {"infantry": 3},
    },
    "fracture7": {
        "space": {"carrier": 1, "fighter": 4},
        "lethe": {"infantry": 1},
        "phlegethon": {"infantry": 1},
    },
}


# Parametry setupu/reguł Fracture nadpisywalne przez moduły wariantów (``rules`` w
# ``assets/config/variants.json``, core/variants.rule_value). Domyślnie wartości wyżej.
RULE_ROLL_SUCCESS = "fracture.roll_success"
RULE_INGRESS_SYNERGY = "fracture.ingress_per_synergy_color"
RULE_INGRESS_NO_SYNERGY = "fracture.ingress_per_color_no_synergy"
RULE_NEUTRAL_SETUP = "fracture.neutral_setup"


def roll_success(registry: StaticDataRegistry) -> frozenset[int]:
    """Wyniki d10 wprowadzające Fracture w grze (moduły mogą zmienić)."""
    default = sorted(FRACTURE_ROLL_SUCCESS)
    return frozenset(variants.rule_value(registry, RULE_ROLL_SUCCESS, default))


def neutral_setup(registry: StaticDataRegistry) -> dict[str, dict[str, dict[str, int]]]:
    """Jednostki neutralne z odwrotu kafli Fracture w grze (moduły mogą zmienić)."""
    return variants.rule_value(registry, RULE_NEUTRAL_SETUP, NEUTRAL_SETUP)


def is_fracture_position(position: str) -> bool:
    """Czy pozycja należy do The Fracture."""
    return position in FRACTURE_POSITIONS


# --------------------------------------------------------------------------- synchronizacja mapy


def sync_grid(grid: HexGrid, state: GameState, registry: StaticDataRegistry) -> None:
    """Dosynchronizowuje kafle The Fracture i portale ingress/egress mapy ze stanem gry.

    Tanie, gdy nic się nie zmieniło. Kafel bez definicji w rejestrze (wyłączone źródło) jest
    pomijany.
    """
    changed = False
    for position, tile_id in zip(FRACTURE_POSITIONS, FRACTURE_TILE_IDS, strict=True):
        present = position in grid.positions
        if state.fracture.in_play and not present:
            definition = registry.systems.get(tile_id)
            if definition is None:
                continue
            grid.place_system(
                position,
                tile_id,
                wormholes=list(definition.wormholes),
                anomalies=set(definition.anomalies),
                hex_override=fracture_hex(position),
            )
            changed = True
        elif not state.fracture.in_play and present:
            grid.remove_system(position)
            changed = True
    if changed:
        grid.build_edges()
    ingress = {pos for pos, s in state.systems.items() if s.ingress_token}
    egress = {
        pos
        for pos in FRACTURE_POSITIONS
        if pos in grid.positions
        and (d := registry.systems.get(grid.system_id_at(pos))) is not None
        and d.has_egress
    }
    grid.sync_portals(ingress, egress)


# ------------------------------------------------------------------------------ ingress


def _ensure_system(state: GameState, grid: HexGrid, position: str) -> SystemState:
    system = state.systems.get(position)
    if system is None:
        system = SystemState(position=position, system_id=grid.system_id_at(position))
        state.systems[position] = system
    return system


def ingress_candidates(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid, color: str
) -> list[str]:
    """Pozycje systemów z planetą o specjalności ``color`` i BEZ żetonu ingress.

    System z dwiema planetami o specjalnościach to jeden kandydat (jeden ingress na system —
    R_fracture). Systemy The Fracture nie są kandydatami: ingress leży na zwykłej mapie.
    """
    wanted = color.upper()
    result: list[str] = []
    for position in sorted(grid.positions):
        if is_fracture_position(position):
            continue
        system = state.systems.get(position)
        if system is not None and system.ingress_token:
            continue
        for planet_id in planets_of_system(state, registry, position, grid):
            stats = planet_stats(state, registry, planet_id)
            if stats is not None and wanted in {s.upper() for s in stats.tech_specialties}:
                result.append(position)
                break
    return result


def _put_ingress(state: GameState, grid: HexGrid, position: str) -> None:
    _ensure_system(state, grid, position).ingress_token = True


def _log(state: GameState, entry: dict[str, Any]) -> None:
    state.fracture.log.append(entry)


def announce_ingress_placed(state: GameState) -> None:
    """Emituje „The Fracture w grze, wszystkie ingressy rozłożone” (AFTER) - MUTUJE ``state``.

    Tu reagują efekty „po wejściu Fracture” (Al'raith Ix Ianovar, F_vuilraith 1.2: przesunięcie
    dopiero po rozłożeniu WSZYSTKICH ingressów). Nic nie robi, dopóki są ingressy do położenia.
    """
    from src.core import triggers  # lokalnie: triggers -> hooki -> fracture

    fracture = state.fracture
    if not fracture.in_play or fracture.pending or fracture.entered_by is None:
        return
    if extra_ingress_deferred(state):
        return  # the final ingress still waits for Thunder's Edge (R_fracture notes/5)
    triggers.fire(
        state, GameEvent.FRACTURE_INGRESS_PLACED, Moment.AFTER, subject=fracture.entered_by,
        ctx={"player": fracture.entered_by, "breakthrough": fracture.breakthrough_id},
    )


def _settle_pending(state: GameState, registry: StaticDataRegistry, grid: HexGrid) -> None:
    """Kładzie ingress automatycznie, gdy kandydatów jest nie więcej niż trzeba (R_fracture).

    „If there are fewer than three planets ... as many planets as possible are chosen." Pętla
    do stabilizacji, bo położony żeton zmniejsza pulę kandydatów innych kolorów.
    """
    pending = state.fracture.pending
    changed = True
    while changed:
        changed = False
        for choice in list(pending):
            candidates = ingress_candidates(state, registry, grid, choice.color)
            if len(candidates) <= choice.remaining:
                for position in candidates:
                    _put_ingress(state, grid, position)
                    _log(state, {"type": "ingress", "position": position, "auto": True})
                pending.remove(choice)
                changed = True


def extra_ingress_deferred(state: GameState) -> bool:
    """Whether the final ingress token waits for Thunder's Edge to be placed.

    R_fracture notes/5: when The Fracture enters play from the expedition that also places
    Thunder's Edge, Thunder's Edge is placed first and the final ingress goes into its system.
    """
    log = state.fracture.log
    return (
        state.fracture.in_play
        and any(e.get("type") == "extra_deferred" for e in log)
        and not any(e.get("extra") for e in log)
    )


def place_deferred_extra_ingress(state: GameState, grid: HexGrid) -> None:
    """Places the deferred final ingress in the Thunder's Edge system - MUTATES ``state``.

    Called right after Thunder's Edge is placed; does nothing when nothing was deferred.
    """
    position = state.expeditions.thunders_edge_position
    if not extra_ingress_deferred(state) or position is None:
        return
    if not _ensure_system(state, grid, position).ingress_token:  # never 2 ingress in 1 system
        _put_ingress(state, grid, position)
    _log(state, {"type": "ingress", "position": position, "auto": True, "extra": True})
    announce_ingress_placed(state)


def _extra_ingress_position(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid
) -> str | None:
    """System dodatkowego ingressu: Thunder's Edge, jeśli na planszy, inaczej Mecatol Rex."""
    if state.expeditions.thunders_edge_position is not None:
        return state.expeditions.thunders_edge_position
    return planet_position("mr", state, grid, registry)


def _synergy_colors(registry: StaticDataRegistry, breakthrough_id: str | None) -> list[str] | None:
    """Dwa kolory synergii przełomu albo ``None`` (brak przełomu / brak synergii — Nekro)."""
    if breakthrough_id is None:
        return None
    breakthrough = registry.breakthroughs.get(breakthrough_id)
    if breakthrough is None:
        return None
    colors = [c for c in breakthrough.synergy if c in COLORS]
    return colors if colors else None


def _place_neutrals(state: GameState, registry: StaticDataRegistry) -> None:
    setup = neutral_setup(registry)
    for position, tile_id in zip(FRACTURE_POSITIONS, FRACTURE_TILE_IDS, strict=True):
        system = SystemState(position=position, system_id=tile_id)
        state.systems[position] = system
        for zone, units in setup.get(tile_id, {}).items():
            for base_type, count in units.items():
                place_units(
                    state, system, zone, NEUTRAL_PLAYER_ID, base_type, count, UnitCause.SETUP
                )


def _enter(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    breakthrough_id: str | None,
) -> None:
    """Wprowadza The Fracture do gry — MUTUJE ``state`` (klon wołającego)."""
    if state.fracture.in_play:
        raise ValueError("The Fracture is already in play.")
    missing = [t for t in FRACTURE_TILE_IDS if t not in registry.systems]
    if missing:
        raise ValueError(f"The Fracture tiles are not loaded (check enabled sources): {missing}")
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")

    fracture = state.fracture
    fracture.in_play = True
    fracture.entered_by = player_id
    fracture.breakthrough_id = breakthrough_id
    _place_neutrals(state, registry)
    _log(state, {"type": "enter", "playerId": player_id, "breakthroughId": breakthrough_id})

    # Dodatkowy ingress (po ingressach z kolorów — kolejność nie ma znaczenia dla wyniku, ale
    # kładziemy go PIERWSZY, by nie liczył się jako kandydat koloru).
    if state.expeditions.pending_placement is not None:
        # Sixth expedition: Thunder's Edge is placed first, then the final ingress goes into its
        # system (R_fracture notes/5) - ``place_deferred_extra_ingress``.
        _log(state, {"type": "extra_deferred"})
        extra = None
    else:
        extra = _extra_ingress_position(state, registry, grid)
    if extra is not None:
        _put_ingress(state, grid, extra)
        _log(state, {"type": "ingress", "position": extra, "auto": True, "extra": True})

    colors = _synergy_colors(registry, breakthrough_id)
    if colors is not None:
        fracture.pending = [
            IngressChoice(
                color=c,
                remaining=variants.rule_value(
                    registry, RULE_INGRESS_SYNERGY, INGRESS_PER_SYNERGY_COLOR
                ),
            )
            for c in colors
        ]
    else:
        fracture.pending = [
            IngressChoice(
                color=c,
                remaining=variants.rule_value(
                    registry, RULE_INGRESS_NO_SYNERGY, INGRESS_PER_COLOR_NO_SYNERGY
                ),
            )
            for c in COLORS
        ]
    _settle_pending(state, registry, grid)
    announce_ingress_placed(state)


def put_into_play(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    breakthrough_id: str | None = None,
) -> None:
    """Wprowadza The Fracture do gry efektem karty (np. Silver Flame) - MUTUJE ``state``.

    Wersja mutująca :func:`enter_play` dla efektów, które pracują na klonie wołającego.
    Nic nie robi, gdy Fracture już jest w grze ("if it is not already").
    """
    if not state.fracture.in_play:
        _enter(state, registry, grid, player_id, breakthrough_id)


def enter_play(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    breakthrough_id: str | None = None,
) -> GameState:
    """Wprowadza The Fracture do gry (efekt / God-Mode) i zwraca nowy stan.

    ``breakthrough_id`` — przełom, z którego synergii liczy się ingress; ``None`` oznacza efekt
    bez synergii (po jednym ingressie na każdy z czterech kolorów).

    Raises:
        ValueError: Fracture już w grze, kafle niezaładowane, nieznany gracz.
    """
    new_state = state.clone()
    _enter(new_state, registry, grid, player_id, breakthrough_id)
    return new_state


def roll_for_fracture(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    breakthrough_id: str | None,
) -> None:
    """Rzut d10 po zdobyciu przełomu (R_breakthroughs) — MUTUJE ``state`` (klon wołającego).

    1 albo 10 wprowadza The Fracture. Gdy Fracture jest już w grze, rzutu nie ma. Wynik
    zapisuje ``fracture.last_roll`` (UI animuje go po stronie klienta — rzut jest silnikowy,
    seedowalny: ``dice.next_rng``).
    """
    if state.fracture.in_play:
        return
    result = next_rng(state).randint(1, DIE_SIDES)
    hits = roll_success(registry)
    success = result in hits
    record_table_roll(
        state,
        player_id,
        "fracture",
        "The Fracture",
        [result],
        hit_values=sorted(hits),
        summary=(
            "The Fracture enters play!"
            if success
            else "The Fracture needs "
            + " or ".join(f"a {v}" for v in sorted(hits))
            + ". Better luck next time."
        ),
    )
    state.fracture.last_roll = {
        "playerId": player_id,
        "result": result,
        "success": success,
        # Numer rzutu w dzienniku - UI po nim odróżnia NOWY rzut od starego (animacja kostki).
        "seq": len(state.fracture.log) + 1,
    }
    _log(state, {"type": "roll", "playerId": player_id, "result": result, "success": success})
    if success:
        _enter(state, registry, grid, player_id, breakthrough_id)


def breakthrough_roll(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    breakthrough_id: str | None,
) -> GameState:
    """Czysta wersja :func:`roll_for_fracture` — zwraca nowy stan."""
    new_state = state.clone()
    roll_for_fracture(new_state, registry, grid, player_id, breakthrough_id)
    return new_state


def choose_ingress(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    color: str,
    position: str,
) -> GameState:
    """Kładzie żeton ingress w systemie ``position`` dla koloru ``color`` (wybór gracza).

    Raises:
        ValueError: Brak oczekującego wyboru, zły gracz, kolor bez wyboru, system spoza
            kandydatów (brak planety o tej specjalności albo już ma ingress).
    """
    fracture = state.fracture
    if not fracture.pending:
        raise ValueError("There is no ingress token to place.")
    if player_id != fracture.entered_by:
        raise ValueError(f"Only {fracture.entered_by} places the ingress tokens.")
    wanted = color.upper()
    if not any(c.color == wanted for c in fracture.pending):
        raise ValueError(f"No ingress token to place for {wanted}.")
    if position not in ingress_candidates(state, registry, grid, wanted):
        raise ValueError(
            f"System {position} has no planet with a {wanted} specialty "
            "or already contains an ingress token."
        )
    new_state = state.clone()
    _put_ingress(new_state, grid, position)
    _log(new_state, {"type": "ingress", "position": position, "color": wanted, "auto": False})
    choice = next(c for c in new_state.fracture.pending if c.color == wanted)
    choice.remaining -= 1
    if choice.remaining <= 0:
        new_state.fracture.pending.remove(choice)
    _settle_pending(new_state, registry, grid)
    announce_ingress_placed(new_state)
    return new_state


def pending_candidates(
    state: GameState, registry: StaticDataRegistry, grid: HexGrid
) -> dict[str, list[str]]:
    """Kandydaci per oczekujący kolor (dla UI)."""
    return {
        c.color: ingress_candidates(state, registry, grid, c.color) for c in state.fracture.pending
    }
