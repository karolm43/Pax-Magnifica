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

from src.core import (
    action_budget,
    command_tokens,
    control,
    ion_storm,
    objective_events,
    production,
    rules_hooks,
    triggers,
)
from src.core.battle import space_combat_required
from src.core.capacity import open_capacity_check, remove_forced_excess
from src.core.combat import resolve_unit_variant
from src.core.fleet_pool import open_fleet_pool_check
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    CombatStep,
    GameState,
    InvasionPhase,
    Phase,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.invasion import begin_invasion
from src.core.planet_stats import resources_of
from src.core.production import active_grant, dual_production, producers
from src.core.registry import StaticDataRegistry
from src.core.space_cannon import open_offense
from src.core.unit_catalog import ASYNC_ID_BY_BASE_TYPE, is_space_unit

# Krok ``pending_strategy``, w którym karta strategii czeka na koniec akcji taktycznej, oraz
# klucz szkicu z nazwą kroku do wznowienia po jej zakończeniu (Warfare TE, RULES.md 30.11).
STRATEGY_TACTICAL_STEP = "tactical_action"
STRATEGY_RESUME_KEY = "resume_step"

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


def activate_system(
    state: GameState, grid: HexGrid, position: str, *, free: bool = False
) -> GameState:
    """Aktywuje system przez aktywnego gracza (fundament akcji taktycznej).

    Kładzie żeton dowodzenia aktywnego gracza w przestrzeni systemu, ustawia
    ``active_system`` i rozpoczyna maszynę kroków (``tactical_step = MOVEMENT`` —
    aktywacja sama jest krokiem zerowym, od razu przechodzimy do ruchu). Zużywa
    1 żeton z puli taktycznej gracza (``tactical_cc``), odkładając go na system
    (odpowiednik ``CommandCounterHelper.addCC`` z ``useTactic=true``).

    WALIDACJA (twarda, RULES.md 33.1): musi być aktywny gracz; gracz NIE może aktywować
    systemu z własnym żetonem dowodzenia; gracz musi mieć ≥1 żeton w puli taktycznej.
    SĘDZIA tury (RULES.md 31.7, 33.1a — jak akcja strategiczna i komponentu): tylko w fazie
    AKCJI, nie po pasie, nie w trakcie otwartego okna czasowego ani wieloetapowego primary.
    ``free=True`` (Warfare, Thunder's Edge): system jest aktywowany BEZ kładzenia żetonu i bez
    zużycia puli taktycznej - także gdy leży w nim już własny żeton; system i tak „liczy się
    jako aktywowany" (RULES.md 30.11); kontrole tury robi wtedy karta strategii.
    God-Mode (``board_edit.place_command_token``) omija tę ścieżkę (korekta bez zużycia puli).

    Raises:
        ValueError: Gdy brak aktywnego gracza, zła faza, gracz spasował, trwa okno czasowe
            / primary, system ma już własny żeton gracza, albo pula taktyczna jest pusta.
    """
    active_id = state.active_player_id
    if active_id is None:
        raise ValueError("No active player - cannot activate a system.")
    if not free:
        if state.phase is not Phase.ACTION:
            raise ValueError(
                "A tactical action can only be performed during the action phase."
            )
        if state.pending_window is not None or state.held_play is not None:
            raise ValueError(
                "Cannot activate a system while a timing window is open - resolve it first."
            )
        if state.pending_strategy is not None:
            raise ValueError(
                "Finish resolving the strategy card's primary ability before activating "
                "a system."
            )

    # R: nie można aktywować systemu z własnym żetonem dowodzenia.
    existing = state.systems.get(position)
    if not free and existing is not None and active_id in existing.command_tokens:
        raise ValueError(
            "Cannot activate a system that already contains your command token."
        )

    # Zdolność INNEGO gracza zabrania aktywacji tego systemu (Chaos Mapping, RULES.md 62.14).
    blocked_by = next(
        (
            pid for pid in sorted(state.players)
            if pid != active_id and rules_hooks.permits(
                rules_hooks.POINT_TACTICAL_ACTIVATION_BLOCKED, state, pid,
                {"activator": active_id, "position": position},
            )
        ),
        None,
    )
    if blocked_by is not None:
        raise ValueError(
            "Another player's ability prevents you from activating this system "
            "(an asteroid field that contains their ships)."
        )

    # R: potrzebny żeton w puli taktycznej.
    player0 = state.players.get(active_id)
    if player0 is None or (not free and player0.tactical_cc <= 0):
        raise ValueError("No token in the tactical pool - cannot activate a system.")
    if not free and player0.passed:
        raise ValueError("You have passed - you cannot perform a tactical action.")
    # Jedna akcja na turę (R_action_phase, RULES.md 30.3): aktywacja = akcja taktyczna, więc nie
    # po innej akcji (strategicznej / komponentu). Warfare TE aktywuje w ramach SWOJEJ akcji.
    if not free:
        action_budget.require_free_action(state, active_id)

    new_state = state.clone()
    triggers.fire(
        new_state, GameEvent.SYSTEM_ACTIVATED, Moment.WHEN, subject=active_id,
        ctx={"player": active_id, "position": position},
    )
    system = _ensure_system(new_state, position, grid)

    # Zużycie z puli taktycznej (gwarantowane > 0 przez walidację), potem żeton w przestrzeni
    # systemu (bez duplikatu — już sprawdzone wyżej; ``place_token`` emituje zdarzenie).
    if not free:
        command_tokens.spend_from_pool(new_state, active_id, "tactical")
    if not free and active_id not in system.command_tokens:
        command_tokens.place_token(new_state, system, active_id)
    # RULES.md 31.7: aktywacja systemu rozpoczyna AKCJĘ TAKTYCZNĄ — liczy się jako
    # akcja tury, więc gracz będzie mógł zakończyć turę (End turn).
    if free:
        new_state.players[active_id].took_action_this_turn = True
    else:
        action_budget.register_action(new_state, active_id)

    new_state.active_system = position
    new_state.tactical_step = TacticalStep.MOVEMENT
    new_state.production_used = 0
    new_state.gravity_drive_used = False
    new_state.tempesta_used = False
    new_state.imperator_used = False
    new_state.tactical_moved = False
    new_state.invasion_resolved = False
    new_state.ion_storm_used = []
    objective_events.snapshot_tactical_start(new_state)
    new_state.control_changes = []
    new_state.production_placed = {}
    triggers.fire(
        new_state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject=active_id,
        ctx={"player": active_id, "position": position},
    )
    return new_state


def _without_forced_excess(state: GameState, registry: StaticDataRegistry | None) -> GameState:
    """Nadwyżka bez wyboru w aktywnym systemie znika od razu (RULES.md 39.6 C5) - zanim bramka
    kroku zdecyduje o oknie CAPACITY. W trakcie walki / innego okna bez zmian (C3)."""
    if registry is None or state.active_system is None or state.pending_window is not None:
        return state
    return remove_forced_excess(state, registry, state.active_system)


def _check_can_leave(
    state: GameState,
    registry: StaticDataRegistry | None,
    what: str,
    *,
    require_space_combat: bool,
) -> GameState | None:
    """Wspólne blokady opuszczenia kroku / zakończenia akcji taktycznej.

    Rzuca ``ValueError``, gdy coś jest nierozstrzygnięte (okno, walka, inwazja,
    obowiązkowa walka kosmiczna). Zwraca stan z otwartym oknem CAPACITY / FLEET_POOL,
    gdy wykryto nadwyżkę (krok zostaje, gracz najpierw ją usuwa), a ``None``, gdy
    droga wolna. ``what`` — fraza do komunikatu („the next step" / „ending the action").
    """
    # Produkcja innego gracza z grantu (Dirzuga Rophal) - najpierw ona (RULES.md 62.5).
    if state.active_player_id is not None:
        waiting = production.foreign_grant_reason(state, state.active_player_id)
        if waiting is not None:
            raise ValueError(waiting)
    # Nie wolno opuścić kroku, dopóki trwa okno Space Cannon (gracze jeszcze strzelają /
    # przypisują straty — RULES.md 38): inaczej kroki „uciekałyby" sprzed rozstrzygnięcia.
    window = state.pending_window
    # Limit pojemności (RULES.md 39.6): nadwyżkę trzeba usunąć, zanim akcja pójdzie dalej.
    if window is not None and window.window_type is WindowType.CAPACITY:
        raise ValueError(f"Some units exceed capacity - remove the excess before {what}.")
    if window is not None and window.window_type is WindowType.FLEET_POOL:
        raise ValueError(f"Some ships exceed the fleet pool - remove the excess before {what}.")
    if window is not None and window.window_type is WindowType.SPACE_CANNON:
        raise ValueError(f"Space Cannon is still being resolved - finish it before {what}.")
    # Decyzje graczy (oferty technologii i zdolności - RULES.md 56) trzeba rozstrzygnąć wcześniej.
    if window is not None and window.window_type is WindowType.REACTION:
        raise ValueError(f"Players still have decisions to make - resolve them before {what}.")
    # Walka (RULES.md 39): trwającej nie wolno porzucić; walka kosmiczna jest obowiązkowa,
    # gdy dwóch graczy ma statki w aktywnym systemie (W2).
    combat = state.active_combat
    if combat is not None and combat.step is not CombatStep.DONE:
        raise ValueError(f"A combat is in progress - finish it before {what}.")
    # Inwazja (RULES.md 40): z kroku INVASION wychodzi się dopiero po rozstrzygnięciu
    # (ESTABLISH = wszystko załatwione, zostaje tylko zamknięcie).
    invasion = state.invasion
    if (
        state.tactical_step is TacticalStep.INVASION
        and invasion is not None
        and invasion.phase is not InvasionPhase.ESTABLISH
    ):
        raise ValueError(f"The invasion is in progress - finish it before {what}.")
    # Eksploracja (RULES.md 46): karta musi zostać rozstrzygnięta, zanim akcja pójdzie dalej.
    if state.exploration is not None:
        raise ValueError(f"Exploration is in progress - finish it before {what}.")
    if require_space_combat and space_combat_required(state):
        raise ValueError(
            "Two players have ships in the active system - resolve the space combat first."
        )
    # 39.6 C3: przed przejściem dalej (np. przed Space Cannon / walką, gdy nosiciel zginął)
    # wykryta nadwyżka otwiera okno CAPACITY — krok zostaje, gracz najpierw usuwa nadmiar.
    if registry is not None and state.active_system is not None and window is None:
        checked = open_capacity_check(state, registry, state.active_system)
        if checked.pending_window is not None:
            return checked
    # Fleet pool (RULES.md 42): ruch/produkcja/umieszczenie WOLNO wykonać ponad pulę, ale
    # nadwyżkę statków trzeba zwrócić do rezerwy, zanim akcja pójdzie dalej.
    if state.active_system is not None and window is None:
        pooled = open_fleet_pool_check(state, state.active_system)
        if pooled.pending_window is not None:
            return pooled
    return None


def end_action(state: GameState, registry: StaticDataRegistry | None = None) -> GameState:
    """Walidowane zakończenie akcji taktycznej z dowolnego kroku (przycisk „End action").

    W przeciwieństwie do ``end_tactical_action`` (surowe czyszczenie, używane przez
    ``next_step`` i God-Mode) NIE pozwala porzucić nierozstrzygniętych spraw: trwającej
    walki, okna Space Cannon / pojemności / puli floty, niedokończonej inwazji ani
    obowiązkowej walki kosmicznej (gdy dwóch graczy ma statki w aktywnym systemie, a
    krok walki jeszcze nie minął). Pominięcie ruchu / inwazji / produkcji jest legalne.
    """
    if state.tactical_step is None:
        return state.clone()
    combat_pending = _STEP_SEQUENCE.index(state.tactical_step) <= _STEP_SEQUENCE.index(
        TacticalStep.SPACE_COMBAT
    )
    state = _without_forced_excess(state, registry)
    blocked = _check_can_leave(
        state, registry, "ending the action", require_space_combat=combat_pending
    )
    if blocked is not None:
        return blocked
    return end_tactical_action(state)


def next_step(state: GameState, registry: StaticDataRegistry | None = None) -> GameState:
    """Przechodzi do następnego kroku akcji taktycznej.

    Po ostatnim kroku (``PRODUCTION``) kończy akcję taktyczną (czyści krok i aktywny
    system — patrz ``end_tactical_action``). Gdy akcja nie trwa (``tactical_step`` jest
    None) — bez zmian.
    """
    if state.tactical_step is None:
        return state.clone()
    state = _without_forced_excess(state, registry)
    blocked = _check_can_leave(
        state,
        registry,
        "the next step",
        require_space_combat=state.tactical_step is TacticalStep.SPACE_COMBAT,
    )
    if blocked is not None or state.tactical_step is None:
        return blocked if blocked is not None else state.clone()
    idx = _STEP_SEQUENCE.index(state.tactical_step)
    if idx >= len(_STEP_SEQUENCE) - 1:
        return end_tactical_action(state)
    new_state = state.clone()
    if state.tactical_step is TacticalStep.MOVEMENT:
        ion_storm.flip_used(new_state)  # koniec kroku Move Ships
    new_state.tactical_step = _STEP_SEQUENCE[idx + 1]
    new_state.active_combat = None  # zakończona walka zostaje za nami
    new_state.invasion = None
    new_state.exploration = None
    return new_state


def _step_is_empty(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, step: TacticalStep
) -> bool:
    """Czy w kroku nie ma nic do rozstrzygnięcia (wtedy ``advance_skipping_empty`` go pomija).

    SPACE_CANNON / SPACE_COMBAT / INVASION / PRODUCTION: patrz komentarze niżej. Kroki
    ACTIVATION i MOVEMENT nigdy nie są puste (ruch zawsze jest opcją gracza).
    """
    player_id = state.active_player_id
    if step is TacticalStep.SPACE_COMBAT:
        return not space_combat_required(state)
    if step is TacticalStep.INVASION:
        if state.active_system is None or player_id is None or state.invasion_resolved:
            return True
        probe = state.clone()
        probe.tactical_step = TacticalStep.INVASION
        # begin_invasion zwraca stan bez inwazji, gdy nie ma ani bombardowania, ani lądowania.
        return begin_invasion(probe, grid, registry).invasion is None
    if step is TacticalStep.PRODUCTION:
        if player_id is None or state.active_system is None:
            return True
        return (
            not producers(state, registry, player_id, state.active_system)
            and active_grant(state, player_id) is None
        )
    return False


def advance_skipping_empty(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """``next_step`` + automatyczne pominięcie kroków, w których nic się nie dzieje.

    Wejście w SPACE_CANNON otwiera okno offense (jeśli ktoś strzela — zostajemy w kroku);
    SPACE_COMBAT bez dwóch flot, INVASION bez lądowania/bombardowania i PRODUCTION bez
    producentów są pomijane od razu. Gdy pominięty zostaje ostatni krok, akcja się kończy.
    Zatrzymuje się, gdy krok się nie zmienił (okno CAPACITY / FLEET_POOL, blokada).
    """
    previous = state.tactical_step
    current = next_step(state, registry)
    while current.tactical_step is not None:
        step = current.tactical_step
        if step is previous:
            # krok się nie zmienił (okno CAPACITY / FLEET_POOL) — nic nie pomijamy
            return current
        if step is TacticalStep.SPACE_CANNON:
            current = open_offense(current, grid, registry)
            if current.pending_window is not None:
                return current
        elif not _step_is_empty(current, grid, registry, step):
            return current
        previous = step
        current = next_step(current, registry)
    return current


def set_step(state: GameState, step: TacticalStep) -> GameState:
    """Ustawia konkretny krok akcji taktycznej (skok do kroku — np. z UI).

    Przydatne, gdy operator chce wrócić/przeskoczyć (np. pominąć walkę). Zero reguł.
    """
    new_state = state.clone()
    if state.tactical_step is TacticalStep.MOVEMENT and step is not TacticalStep.MOVEMENT:
        ion_storm.flip_used(new_state)
    new_state.tactical_step = step
    new_state.invasion = None
    new_state.exploration = None
    return new_state


def end_tactical_action(state: GameState) -> GameState:
    """Kończy bieżącą akcję taktyczną: czyści ``active_system`` i ``tactical_step``.

    NIE zdejmuje żetonu dowodzenia z systemu (żeton zostaje — tak jak na stole).
    Tura gracza idzie dalej przez ``turn_flow.end_turn`` (osobna akcja).
    """
    new_state = state.clone()
    new_state.active_system = None
    if state.tactical_step is TacticalStep.MOVEMENT:
        ion_storm.flip_used(new_state)
    new_state.tactical_step = None
    new_state.production_used = 0
    new_state.gravity_drive_used = False
    new_state.tempesta_used = False
    new_state.imperator_used = False
    new_state.tactical_moved = False
    new_state.invasion_resolved = False
    new_state.ion_storm_used = []
    new_state.tactical_pn_owners = []
    new_state.control_changes = []
    new_state.production_placed = {}
    new_state.space_cannon_log = "[]"
    new_state.active_combat = None
    if new_state.invasion is not None:
        # Inwazja urwana końcem akcji też się kończy: wygasają efekty „do końca inwazji”.
        triggers.fire(
            new_state, GameEvent.INVASION, Moment.END, subject=new_state.invasion.attacker,
            ctx={"position": new_state.invasion.position, "player": new_state.invasion.attacker},
        )
    new_state.invasion = None
    new_state.exploration = None
    # Produkcja z karty strategii (standalone) jest niezależna od akcji taktycznej - zostaje.
    grant_now = new_state.production_grant
    if grant_now is not None and not (grant_now.standalone or grant_now.free):
        new_state.production_grant = None
    # Akcja taktyczna wywołana kartą strategii (Warfare TE) dobiegła końca - wznów primary.
    pending = new_state.pending_strategy
    if pending is not None and pending.step == STRATEGY_TACTICAL_STEP:
        pending.step = str(pending.draft.pop(STRATEGY_RESUME_KEY, pending.step))
    # Okna Space Cannon / przypisania strat dotyczą aktywnego systemu — po zakończeniu akcji
    # nie ma już czego rozstrzygać (wentyl: operator może zakończyć akcję w trakcie okna).
    window = new_state.pending_window
    if window is not None and window.window_type in (
        WindowType.SPACE_CANNON,
        WindowType.COMBAT_ASSIGN_HITS,
        WindowType.COMBAT_RETREAT,
        WindowType.CAPACITY,
        WindowType.FLEET_POOL,
    ):
        new_state.pending_window = None
        new_state.suspended_window = None
    # Reakcje „po akcji taktycznej” (np. Dark Energy Tap: eksploracja żetonu frontier) idą na
    # końcu, żeby stan, który otwierają (eksploracja, oferty), nie został wyczyszczony powyżej.
    if state.active_system is not None:
        # ``gained`` = planety przejęte przez aktywnego gracza w tej akcji (Reclamation, Reclaimer).
        gained = [
            str(c["planet"]) for c in state.control_changes
            if c.get("player") == state.active_player_id and c.get("planet")
        ]
        triggers.fire(
            new_state, GameEvent.TACTICAL_ACTION, Moment.END, subject=state.active_player_id,
            ctx={"position": state.active_system, "player": state.active_player_id,
                 "gained": gained},
        )
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
    _ensure_system(new_state, position, grid)
    # Nadpisanie właściciela (jeden kontroler planety — poprzedni traci kontrolę).
    control.set_planet_control(new_state, position, planet, player_id)
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
    # Gdzie jednostka ląduje: "space" (statek) albo "planet" (siła naziemna /
    # struktura). Panel produkcji decyduje, czy stawiać w przestrzeni, czy na
    # planecie (RULES.md 26) — źródło: ``unit_catalog.placement_of``.
    placement: str
    # CAPACITY wariantu jednostki (Bellum Gloriosum liczy z niej ładunek poza limitem).
    capacity: int = 0


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
            total += resources_of(state, registry, planet_id)
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
    dual = dual_production(state, player_id)  # Regulated Conscription: 1 sztuka za koszt
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
                # Cena JEDNEJ produkcji: dane trzymają koszt per sztuka (0.5), a para
                # fighter/infantry kosztuje 1 (R_cost: dwie ikony = dwie sztuki za koszt).
                cost=unit.cost * (2 if base_type in _DUAL_PRODUCTION else 1),
                units_per_cost=2 if base_type in _DUAL_PRODUCTION and dual else 1,
                placement="space" if is_space_unit(base_type) else "planet",
                capacity=int(unit.capacity_value or 0),
            )
        )
    return ProductionHelp(
        player_id=player_id,
        available_resources=available,
        units=units,
    )
