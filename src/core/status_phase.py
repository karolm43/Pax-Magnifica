"""Faza statusu — 8 kroków wg R_status_phase (RULES.md 41). Czyste funkcje ``state -> state``.

Kroki LRR i ich realizacja:

1. Score Objectives — INTERAKCJA: gracze po kolei (initiative order) zdobywają do jednego
   celu publicznego i jednego tajnego (``score_objective`` / ``finish_scoring``).
2. Reveal Public Objective — AUTOMAT po kroku 1: mówca odkrywa następny cel; gdy nie ma
   zakrytych celów, gra kończy się (zwycięzca: najwięcej VP, remis → inicjatywa).
3. Draw Action Cards — AUTOMAT: każdy dobiera jedną kartę akcji (przy braku kart: najpierw
   gracze o NAJNIŻSZYM priorytecie, potem przetasowanie talii odrzuconych).
4. Remove Command Tokens — AUTOMAT: żetony z planszy wracają do rezerwy (``cc_reinf``).
5. Gain and Redistribute — INTERAKCJA (równoległa): +2 żetony z rezerwy, rozdział
   strategy/tactic/fleet (``redistribute``); kolizje rozstrzyga initiative order.
6. Ready Cards — AUTOMAT po kroku 5: planety, technologie, liderzy, karty strategii gotowe.
7. Repair Units — AUTOMAT: wszystkie uszkodzone jednostki naprawione.
8. Return Strategy Cards — mówca (``finish_status``): karty wracają do puli, potem agenda
   (gdy zdjęto żeton Custodians) albo nowa runda.

``GameState.status`` trzyma stan pod-kroków; ``None`` = faza nie została zainicjowana
(np. wejście God-Mode) — wtedy zachowuje się starą ścieżką ``turn_flow``.
"""

from __future__ import annotations

from src.core import (
    action_budget,
    card_draw,
    chronicle,
    command_tokens,
    exhaust,
    objectives,
    rules_hooks,
    strategy_phase,
    timing,
    triggers,
    turn_flow,
)
from src.core.damage import repair_all
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    AgendaPhaseState,
    GameState,
    Phase,
    StatusPhaseState,
    StatusStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.unit_catalog import PLACEMENT_BY_BASE_TYPE, Placement

# R_status_phase, krok 5: „Each player gains two command tokens".
COMMAND_TOKENS_GAINED = 2
# Typ jednostki niepodlegający fleet pool (R_fleet_pool: „non-fighter ships").
_FIGHTER = "fighter"


# --- Dostęp / walidacja -------------------------------------------------------------------


def _require_status(state: GameState, step: StatusStep) -> StatusPhaseState:
    """Waliduje: faza STATUS, gra trwa, stan statusu zainicjowany i na kroku ``step``."""
    if state.winner_id is not None:
        raise ValueError("The game has ended.")
    if state.phase is not Phase.STATUS:
        raise ValueError("This action is only available in the status phase.")
    if state.status is None:
        raise ValueError("The status phase has not been initialised.")
    if state.status.step is not step:
        raise ValueError(
            f"Wrong status step (now: {state.status.step.value}, expected: {step.value})."
        )
    return state.status


def _initiative(state: GameState) -> list[str]:
    """Kolejność graczy wg inicjatywy kart (jak w akcji); bez karty → na końcu."""
    return turn_flow.initiative_order(state)


def _log(status: StatusPhaseState, step: int, label: str, **extra: object) -> None:
    status.log.append({"step": step, "label": label, **extra})


# --- Krok 1: punktowanie ------------------------------------------------------------------


def score_objective(
    state: GameState,
    registry: StaticDataRegistry,
    grid: HexGrid,
    player_id: str,
    kind: str,
    objective_id: str,
) -> GameState:
    """Aktywny gracz zdobywa cel w kroku 1: ``kind`` = ``"public"`` albo ``"secret"``.

    Limity R_objective_cards: po jednym celu publicznym i jednym tajnym na fazę statusu.
    Tylko gracz, którego kolej (``active_player_id``), może punktować.

    Raises:
        ValueError: Przy złym kroku/kolejności, przekroczeniu limitu albo celu niespełniającym
            warunków (patrz ``objectives.score_public`` / ``score_secret``).
    """
    status = _require_status(state, StatusStep.SCORE_OBJECTIVES)
    if player_id != state.active_player_id:
        raise ValueError(
            f"It is not {player_id}'s turn to score (active: {state.active_player_id})."
        )
    if player_id in status.done:
        raise ValueError("You have already finished scoring.")
    if kind == "public":
        if player_id in status.scored_public:
            raise ValueError("You have already scored a public objective this phase.")
        new_state = objectives.score_public(state, registry, grid, player_id, objective_id)
        assert new_state.status is not None
        new_state.status.scored_public.append(player_id)
    elif kind == "secret":
        if player_id in status.scored_secret:
            raise ValueError("You have already scored a secret objective this phase.")
        new_state = objectives.score_secret(state, registry, grid, player_id, objective_id)
        assert new_state.status is not None
        new_state.status.scored_secret.append(player_id)
    else:
        raise ValueError(f"Unknown objective kind: {kind!r} (expected public/secret).")
    assert new_state.status is not None
    _log(
        new_state.status,
        1,
        "scored",
        player=player_id,
        kind=kind,
        objective=objective_id,
    )
    return new_state


def finish_scoring(
    state: GameState, registry: StaticDataRegistry, player_id: str | None = None
) -> GameState:
    """Gracz kończy krok 1 (punktował albo pasuje); ostatni uruchamia kroki 2–4 i początek 5.

    Raises:
        ValueError: Przy złym kroku albo gdy ``player_id`` nie jest graczem, którego kolej.
    """
    status = _require_status(state, StatusStep.SCORE_OBJECTIVES)
    current = state.active_player_id
    if current is None:
        raise ValueError("No active player in the status phase.")
    if player_id is not None and player_id != current:
        raise ValueError(f"It is not {player_id}'s turn (active: {current}).")
    new_state = state.clone()
    assert new_state.status is not None
    new_state.status.done.append(current)
    del status
    remaining = [p for p in _initiative(new_state) if p not in new_state.status.done]
    if remaining:
        new_state.active_player_id = remaining[0]
        return new_state
    return _after_scoring(new_state, registry)


# --- Kroki 2–4 i początek 5 (automaty po punktowaniu) ---------------------------------------


def _after_scoring(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Kroki 2, 3, 4 i część 5: odkrycie celu, karty akcji, zebranie żetonów, +2 żetony."""
    del registry
    order = _initiative(state)
    chronicle.snapshot_round(state)

    # Limit rund: punktowanie ostatniej rundy jest ostatnim ruchem gry — kończymy od razu
    # po nim (bez odkrywania celu, dobierania kart itd.). Wygrywa lider VP.
    if (
        state.winner_id is None
        and state.max_rounds > 0
        and state.round_number >= state.max_rounds
        and state.status is not None
    ):
        state.winner_id = objectives.leaders_by_points(state, order)
        state.end_reason = "round_limit"
        state.status.step = StatusStep.COMPLETE
        return state

    # Krok 2 — odkrycie celu przez mówcę (albo koniec gry).
    state, revealed = objectives.reveal_next_public(state)
    assert state.status is not None
    status = state.status
    if revealed is None:
        state.winner_id = objectives.leaders_by_points(state, order)
        state.end_reason = "no_objectives"
        status.step = StatusStep.COMPLETE
        _log(status, 2, "game_end_no_objectives", winner=state.winner_id)
        return state
    _log(status, 2, "revealed", objective=revealed)

    # Krok 3 — dobór kart akcji.
    drawn = _draw_action_cards(state, order)
    _log(status, 3, "drew_action_cards", drawn=drawn)

    # Krok 4 — zdjęcie żetonów dowodzenia z planszy.
    returned = _remove_command_tokens(state)
    _log(status, 4, "removed_command_tokens", returned=returned)

    # Krok 5 (część automatyczna) — zdobycie dwóch żetonów z rezerwy.
    for player_id in order:
        player = state.players[player_id]
        # Punkt zaczepienia: technologie/zdolności zmieniają liczbę żetonów (Hyper Metabolism: 3).
        entitled = max(
            0,
            rules_hooks.modify(
                rules_hooks.POINT_STATUS_COMMAND_TOKENS, state, player_id, COMMAND_TOKENS_GAINED
            ),
        )
        gained = min(entitled, player.cc_reinf)
        command_tokens.take_from_reinforcements(state, player_id, gained)
        status.unassigned_cc[player_id] = gained
    _log(status, 5, "gained_command_tokens", gained=dict(status.unassigned_cc))

    status.step = StatusStep.REDISTRIBUTE
    status.done = []
    state.active_player_id = order[0] if order else state.speaker_id
    return state


def _draw_action_cards(state: GameState, order: list[str]) -> dict[str, int]:
    """Każdy gracz dobiera 1 kartę akcji; przy niedoborze najpierw najniżsi w inicjatywie.

    R_status_phase (Notes): gdy w talii jest za mało kart, rozdaje się je najpierw graczom
    NAJNIŻEJ w kolejności inicjatywy, potem talia odrzuconych jest tasowana i dobierają
    pozostali. ⚠️ ZAŁOŻENIE: limit ręki (7 kart) i odrzucanie nadmiaru przed przetasowaniem
    nie są modelowane (RULES.md 41.5).
    """
    drawn: dict[str, int] = {}
    draw_order = list(order)
    if len(state.decks.action_card_deck) < len(order):
        draw_order = list(reversed(order))
    for player_id in draw_order:
        # Punkt zaczepienia: liczba dobieranych kart (Neural Motivator: 2 zamiast 1).
        wanted = max(
            1, rules_hooks.modify(rules_hooks.POINT_STATUS_ACTION_CARDS, state, player_id, 1)
        )
        for _ in range(wanted):
            # draw_action_card tasuje stos odrzuconych, gdy talia jest pusta; False = brak kart.
            if not card_draw.draw_action_card(state, player_id):
                return drawn
            drawn[player_id] = drawn.get(player_id, 0) + 1
    return drawn


def _remove_command_tokens(state: GameState) -> dict[str, int]:
    """Zdejmuje żetony wszystkich graczy z systemów i zwraca je do rezerwy."""
    returned: dict[str, int] = {}
    for system in state.systems.values():
        for owner in system.command_tokens:
            if owner in state.players:
                command_tokens.return_to_reinforcements(state, owner, 1)
                returned[owner] = returned.get(owner, 0) + 1
        system.command_tokens = []
    return returned


# --- Krok 5: rozdział żetonów -------------------------------------------------------------


def fleet_excess(
    state: GameState, player_id: str
) -> dict[str, int]:
    """Nadwyżka statków (nie-myśliwców) ponad fleet pool gracza: ``{pozycja: ile}``.

    R_fleet_pool: liczba żetonów w puli floty = maks. liczba statków nie-myśliwskich w
    jednym systemie. Transportowane jednostki i ładunek nie liczą się.
    """
    player = state.players[player_id]
    excess: dict[str, int] = {}
    for position, system in state.systems.items():
        ships = sum(
            count
            for base_type, count in system.space_units.get(player_id, {}).items()
            if base_type != _FIGHTER
            and PLACEMENT_BY_BASE_TYPE.get(base_type) is Placement.SPACE
        )
        if ships > player.fleet_cc:
            excess[position] = ships - player.fleet_cc
    return excess


def redistribute(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    tactical: int,
    fleet: int,
    strategic: int,
) -> GameState:
    """Gracz zatwierdza rozdział WSZYSTKICH swoich żetonów (łącznie z nowymi) w pulach.

    Suma musi równać się bieżącym pulom + żetonom zdobytym w kroku 5. Gdy ostatni gracz
    zatwierdzi, wykonują się kroki 6–7 i faza przechodzi w ``COMPLETE``.

    Raises:
        ValueError: Przy złym kroku, ujemnych wartościach, złej sumie albo gdy gracz już
            zatwierdził rozdział.
    """
    status = _require_status(state, StatusStep.REDISTRIBUTE)
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    if player_id in status.done:
        raise ValueError("You have already confirmed your command tokens.")
    if min(tactical, fleet, strategic) < 0:
        raise ValueError("Command token pools cannot be negative.")
    player = state.players[player_id]
    available = (
        player.tactical_cc
        + player.fleet_cc
        + player.strategic_cc
        + status.unassigned_cc.get(player_id, 0)
    )
    if tactical + fleet + strategic != available:
        raise ValueError(
            f"You must distribute exactly {available} command tokens "
            f"(got {tactical + fleet + strategic})."
        )
    new_state = state.clone()
    assert new_state.status is not None
    command_tokens.set_pools(
        new_state, player_id, {"tactical": tactical, "fleet": fleet, "strategic": strategic}
    )
    new_state.status.unassigned_cc[player_id] = 0
    new_state.status.done.append(player_id)
    _log(
        new_state.status,
        5,
        "redistributed",
        player=player_id,
        tactical=tactical,
        fleet=fleet,
        strategic=strategic,
    )
    return advance_fleet_check(new_state, registry)


def _refresh_fleet_excess(state: GameState) -> None:
    """Przelicza ``status.fleet_excess`` dla graczy, którzy już zatwierdzili pule."""
    assert state.status is not None
    for pid in state.status.done:
        excess = fleet_excess(state, pid)
        if excess:
            state.status.fleet_excess[pid] = excess
        else:
            state.status.fleet_excess.pop(pid, None)


def advance_fleet_check(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Fleet pool po zmianie puli floty (RULES.md 42): nadwyżkę trzeba usunąć od razu.

    Dla graczy, którzy zatwierdzili rozdział (w kolejności zatwierdzania), otwiera okno
    ``FLEET_POOL`` na pierwszym systemie z nadwyżką. Gdy nadwyżek brak, a wszyscy zatwierdzili
    — kroki 6–7 (``finalize_status``). Wołane po ``redistribute`` i po zamknięciu okna puli.
    """
    if state.status is None or state.status.step is not StatusStep.REDISTRIBUTE:
        return state
    _refresh_fleet_excess(state)
    if state.pending_window is not None:
        return state
    for pid in state.status.done:
        excess = state.status.fleet_excess.get(pid)
        if excess:
            position = sorted(excess)[0]
            return timing.open_window(
                state,
                WindowType.FLEET_POOL,
                [pid],
                context={"position": position, "phase": "status"},
            )
    if all(p in state.status.done for p in state.players):
        return finalize_status(state, registry)
    return state


def finalize_status(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Kroki 6 (Ready Cards) i 7 (Repair Units); potem czeka na mówcę (krok 8)."""
    del registry
    assert state.status is not None
    for player_id in state.players:
        exhaust.ready_all_planets(state, player_id)
        exhaust.ready_all_technologies(state, player_id)
        exhaust.ready_all_strategy_cards(state, player_id)
        exhaust.ready_breakthrough(state, player_id)
        exhaust.ready_all_leaders(state, player_id)
    _log(state.status, 6, "readied_cards")
    repair_all(state)
    _log(state.status, 7, "repaired_units")
    state.status.step = StatusStep.COMPLETE
    for player in state.players.values():
        player.passed = True
    # Krok 8 ogłasza mówca (RULES.md 31.4: zawsze jest aktywny gracz).
    state.active_player_id = state.speaker_id or state.active_player_id
    return state


# --- Krok 8: zwrot kart strategii i przejście dalej ---------------------------------------


def finish_status(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Krok 8: karty strategii wracają do puli, potem agenda albo nowa runda.

    R_status_phase: jeśli ktoś zdjął żeton Custodians, runda trwa dalej w fazie agendy;
    w przeciwnym razie zaczyna się nowa runda od fazy strategii. Trade goods na
    niewybranych kartach doliczamy PRZED zwrotem (jak dotychczas w ``/round/next``).

    Raises:
        ValueError: Gdy faza statusu nie ukończyła kroków 1–7 albo wybór kart jest niepełny.
    """
    _require_status(state, StatusStep.COMPLETE)
    # Limit rund (decyzja projektowa): po rundzie ``max_rounds`` gra się kończy, wygrywa
    # lider VP (remis → pierwszy w inicjatywie). ⚠️ ZAŁOŻENIE: faza agendy tej rundy pomijana.
    if state.max_rounds > 0 and state.round_number >= state.max_rounds:
        ended = state.clone()
        ended.winner_id = objectives.leaders_by_points(ended, _initiative(ended))
        ended.end_reason = "round_limit"
        return ended
    new_state = strategy_phase.accumulate_unpicked_tg(state, registry)
    new_state = strategy_phase.reset_strategy_cards(new_state)
    new_state.status = None
    if not new_state.custodians_removed:
        return turn_flow.next_round(new_state)
    triggers.fire(new_state, GameEvent.PHASE, Moment.END, ctx={"phase": "status"})
    new_state.phase = Phase.AGENDA
    new_state.agenda = AgendaPhaseState()  # RULES.md 51: mówca ujawnia pierwszą agendę
    for player_id, player in new_state.players.items():
        player.passed = False
        action_budget.reset_turn(new_state, player_id)
        player.transacted_with = []
    # Bez kart strategii porządek wyznacza mówca (R_victory_points: „nearest the speaker").
    new_state.active_player_id = new_state.speaker_id
    triggers.fire(new_state, GameEvent.PHASE, Moment.START, ctx={"phase": "agenda"})
    return new_state


def complete_status(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Tryb testowy (God-Mode): domyka CAŁĄ fazę statusu domyślnymi decyzjami.

    Pomija punktowanie, nowe żetony trafiają do puli taktycznej, potem krok 8. Gdy stan
    wszedł w STATUS bez inicjalizacji (God-Mode), inicjuje ją.
    """
    work = state.clone()
    if work.status is None:
        work.status = StatusPhaseState()
    # Wentyl testowy: niedokończone usuwanie nadwyżki floty nie blokuje domknięcia fazy.
    window = work.pending_window
    if window is not None and window.window_type is WindowType.FLEET_POOL:
        work.pending_window = None
    if work.status.step is StatusStep.SCORE_OBJECTIVES:
        work = _after_scoring(work, registry)
    if work.status is not None and work.status.step is StatusStep.REDISTRIBUTE:
        for player_id in work.players:
            command_tokens.add_to_pool(
                work, player_id, "tactical", work.status.unassigned_cc.get(player_id, 0)
            )
            work.status.unassigned_cc[player_id] = 0
        work = finalize_status(work, registry)
    if work.winner_id is not None or work.status is None:
        return work
    return finish_status(work, registry)
