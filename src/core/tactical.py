"""Akcja taktyczna — maszyna kroków i aktywacja systemu (czyste funkcje nad ``GameState``).

Etap E3 planu pełnej rozgrywki (``docs/PLAN_PELNA_ROZGRYWKA.md``). Aplikacja PROWADZI
gracza przez kroki akcji taktycznej (aktywacja → ruch → space cannon → walka kosmiczna →
inwazja → produkcja), ale NIE waliduje reguł TI4: gracze grają fizycznie i wprowadzają
wynik do aplikacji (decyzja projektowa — asystent stołu, nie sędzia). Te funkcje realizują
mechaniczne operacje na stanie (połóż żeton dowodzenia, ustaw aktywny system, przejdź do
kolejnego kroku), nie egzekwując legalności.

Reguły (jako referencja TI4) spisane w ``docs/RULES.md`` 19 na podstawie AsyncTI4
(``CommandCounterHelper.addCC``, ``Tile.addCC``, ``Game.activeSystem``,
``service/tactical/``). Zero reguł z pamięci.

Funkcje są czyste: przyjmują ``GameState``, zwracają NOWY ``GameState`` (przez ``clone``),
nie mutując wejścia — spójne z Event Sourcingiem.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.combat import resolve_unit_variant
from src.core.game_state import GameState, SystemState, TacticalStep
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE

# Kolejność kroków akcji taktycznej (okna czasowe fazy akcji — RULES.md 19).
_STEP_SEQUENCE: list[TacticalStep] = [
    TacticalStep.ACTIVATION,
    TacticalStep.MOVEMENT,
    TacticalStep.SPACE_CANNON,
    TacticalStep.SPACE_COMBAT,
    TacticalStep.INVASION,
    TacticalStep.PRODUCTION,
]


def _ensure_system(state: GameState, position: str, grid: HexGrid) -> SystemState:
    """Zwraca system ze stanu lub tworzy nowy (z ``system_id`` z grida).

    Mutuje przekazany ``state`` (zakłada się, że to już klon), zapisując system
    w ``state.systems`` gdy go nie było.
    """
    system = state.systems.get(position)
    if system is None:
        system_id = grid.system_id_at(position) if position in grid.positions else ""
        system = SystemState(position=position, system_id=system_id)
        state.systems[position] = system
    return system


def activate_system(state: GameState, grid: HexGrid, position: str) -> GameState:
    """Aktywuje system przez aktywnego gracza (fundament akcji taktycznej).

    Kładzie żeton dowodzenia aktywnego gracza w przestrzeni systemu, ustawia
    ``active_system`` i rozpoczyna maszynę kroków (``tactical_step = MOVEMENT`` —
    aktywacja sama jest krokiem zerowym, od razu przechodzimy do ruchu). Zużywa
    1 żeton z puli taktycznej gracza (``tactical_cc``), odkładając go na system
    (odpowiednik ``CommandCounterHelper.addCC`` z ``useTactic=true``).

    Aplikacja NIE waliduje reguł TI4 (np. „nie aktywuj systemu z własnym CC",
    „musisz mieć żeton w puli") — to operator pilnuje legalności. Jedyny twardy
    warunek to istnienie aktywnego gracza.

    Raises:
        ValueError: Gdy nie ustawiono aktywnego gracza (``active_player_id``).
    """
    active_id = state.active_player_id
    if active_id is None:
        raise ValueError("Brak aktywnego gracza — nie można aktywować systemu.")

    new_state = state.clone()
    system = _ensure_system(new_state, position, grid)

    # Żeton dowodzenia aktywnego gracza w przestrzeni (bez duplikatu).
    if active_id not in system.command_tokens:
        system.command_tokens.append(active_id)

    # Zużycie z puli taktycznej (nie schodzimy poniżej zera — to tylko licznik,
    # nie reguła; operator może i tak grać dalej).
    player = new_state.players.get(active_id)
    if player is not None and player.tactical_cc > 0:
        player.tactical_cc -= 1

    new_state.active_system = position
    new_state.tactical_step = TacticalStep.MOVEMENT
    return new_state


def next_step(state: GameState) -> GameState:
    """Przechodzi do następnego kroku akcji taktycznej.

    Po ostatnim kroku (``PRODUCTION``) kończy akcję taktyczną (czyści krok i aktywny
    system — patrz ``end_tactical_action``). Gdy akcja nie trwa (``tactical_step`` jest
    None) — bez zmian.
    """
    if state.tactical_step is None:
        return state.clone()
    idx = _STEP_SEQUENCE.index(state.tactical_step)
    if idx >= len(_STEP_SEQUENCE) - 1:
        return end_tactical_action(state)
    new_state = state.clone()
    new_state.tactical_step = _STEP_SEQUENCE[idx + 1]
    return new_state


def set_step(state: GameState, step: TacticalStep) -> GameState:
    """Ustawia konkretny krok akcji taktycznej (skok do kroku — np. z UI).

    Przydatne, gdy operator chce wrócić/przeskoczyć (np. pominąć walkę). Zero reguł.
    """
    new_state = state.clone()
    new_state.tactical_step = step
    return new_state


def end_tactical_action(state: GameState) -> GameState:
    """Kończy bieżącą akcję taktyczną: czyści ``active_system`` i ``tactical_step``.

    NIE zdejmuje żetonu dowodzenia z systemu (żeton zostaje — tak jak na stole).
    Tura gracza idzie dalej przez ``turn_flow.end_turn`` (osobna akcja).
    """
    new_state = state.clone()
    new_state.active_system = None
    new_state.tactical_step = None
    return new_state


def capture_planet(
    state: GameState,
    grid: HexGrid,
    position: str,
    planet: str,
    faction_key: str,
) -> GameState:
    """Przejęcie kontroli planety przez gracza (po wygranej inwazji).

    Reguła (źródło: AsyncTI4 ``UnitHolder.addControl`` — ``controlList.clear(); add()``,
    oraz ``AddPlanetService`` usuwający poprzedniego właściciela; RULES.md 21): planeta ma
    DOKŁADNIE JEDNEGO właściciela — nowy nadpisuje poprzedniego. Aplikacja NIE sprawdza
    legalności (czy gracz faktycznie wygrał inwazję) — operator potwierdza przejęcie.

    ``faction_key`` to klucz z tileUnitData (frakcja lub player_id); rozwiązywany na
    ``player_id`` jak w God-Mode (board_edit.resolve_player_id).
    """
    # Import lokalny, by uniknąć cyklu (board_edit importuje game_state, nie tactical).
    from src.core.board_edit import resolve_player_id

    new_state = state.clone()
    player_id = resolve_player_id(faction_key, new_state)
    system = _ensure_system(new_state, position, grid)
    # Nadpisanie właściciela (jeden kontroler planety — poprzedni traci kontrolę).
    system.planet_owners[planet] = player_id
    return new_state


@dataclass(frozen=True)
class ProducibleUnit:
    """Pomoc produkcji dla jednego typu jednostki gracza (koszt z UnitDef)."""

    base_type: str
    async_id: str
    unit_id: str
    name: str
    cost: float
    # Ile sztuk powstaje za jedną produkcję (fighter/piechota = 2 za koszt).
    units_per_cost: int


@dataclass(frozen=True)
class ProductionHelp:
    """Pomoc liczbowa kroku produkcji: dostępne zasoby + koszty jednostek."""

    player_id: str
    available_resources: int
    units: list[ProducibleUnit]


# Jednostki produkowane „podwójnie" (2 sztuki za pojedynczy koszt) — reguła TI4
# (fighter, infantry). Źródło: LRR „Producing Units"; standardowa reguła, dane kosztu
# z UnitDef. Trzymane jawnie jako tabela (RULES.md 22).
_DUAL_PRODUCTION: set[str] = {"fighter", "infantry"}


def _controlled_resources(
    state: GameState, player_id: str, registry: StaticDataRegistry
) -> int:
    """Suma ``resources`` planet kontrolowanych przez gracza (z rejestru)."""
    total = 0
    for system in state.systems.values():
        for planet_id, owner in system.planet_owners.items():
            if owner != player_id:
                continue
            planet = registry.planets.get(planet_id)
            if planet is not None:
                total += planet.resources
    return total


def production_help(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
) -> ProductionHelp:
    """Pomoc liczbowa produkcji: dostępne zasoby gracza + koszt jego jednostek.

    NIE waliduje limitów produkcji ani kosztu (gracz stawia jednostki God-Mode). To
    tylko podpowiedź: ile zasobów daje kontrola planet (``resources``) oraz koszt
    każdej jednostki, jaką gracz może produkować (wariant frakcyjny/ulepszony wg
    posiadanych technologii — ``combat.resolve_unit_variant``). Reguła: RULES.md 22.
    """
    player = state.players.get(player_id)
    faction_id = player.faction if player is not None else None
    technologies = player.technologies if player is not None else []
    available = _controlled_resources(state, player_id, registry)

    units: list[ProducibleUnit] = []
    for base_type in sorted(ASYNC_ID_BY_BASE_TYPE):
        # Struktury (dok/PDS) nie są produkowane w kroku produkcji przez koszt —
        # pomijamy te bez kosztu (brak ``cost`` w danych).
        unit = resolve_unit_variant(registry, faction_id, technologies, base_type)
        if unit is None or unit.cost is None:
            continue
        units.append(
            ProducibleUnit(
                base_type=base_type,
                async_id=ASYNC_ID_BY_BASE_TYPE[base_type],
                unit_id=unit.id,
                name=unit.name,
                cost=unit.cost,
                units_per_cost=2 if base_type in _DUAL_PRODUCTION else 1,
            )
        )
    return ProductionHelp(
        player_id=player_id,
        available_resources=available,
        units=units,
    )
