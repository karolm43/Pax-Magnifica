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

from src.core import objectives, strategy_phase, turn_flow
from src.core.damage import repair_all
from src.core.dice import next_rng
from src.core.game_state import (
    GameState,
    Phase,
    StatusPhaseState,
    StatusStep,
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

    # Krok 2 — odkrycie celu przez mówcę (albo koniec gry).
    state, revealed = objectives.reveal_next_public(state)
    assert state.status is not None
    status = state.status
    if revealed is None:
        state.winner_id = objectives.leaders_by_points(state, order)
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
        gained = min(COMMAND_TOKENS_GAINED, player.cc_reinf)
        player.cc_reinf -= gained
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
    decks = state.decks
    drawn: dict[str, int] = {}
    draw_order = list(order)
    if len(decks.action_card_deck) < len(order):
        draw_order = list(reversed(order))
    for player_id in draw_order:
        if not decks.action_card_deck and decks.action_card_discard:
            rng = next_rng(state)
            reshuffled = list(decks.action_card_discard)
            rng.shuffle(reshuffled)
            decks.action_card_deck = reshuffled
            decks.action_card_discard = []
        if not decks.action_card_deck:
            break
        card = decks.action_card_deck.pop(0)
        state.players[player_id].private.action_cards.append(card)
        drawn[player_id] = drawn.get(player_id, 0) + 1
    return drawn


def _remove_command_tokens(state: GameState) -> dict[str, int]:
    """Zdejmuje żetony wszystkich graczy z systemów i zwraca je do rezerwy."""
    returned: dict[str, int] = {}
    for system in state.systems.values():
        for owner in system.command_tokens:
            if owner in state.players:
                state.players[owner].cc_reinf += 1
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
    target = new_state.players[player_id]
    target.tactical_cc, target.fleet_cc, target.strategic_cc = tactical, fleet, strategic
    new_state.status.unassigned_cc[player_id] = 0
    new_state.status.done.append(player_id)
    excess = fleet_excess(new_state, player_id)
    if excess:
        new_state.status.fleet_excess[player_id] = excess
    else:
        new_state.status.fleet_excess.pop(player_id, None)
    _log(
        new_state.status,
        5,
        "redistributed",
        player=player_id,
        tactical=tactical,
        fleet=fleet,
        strategic=strategic,
    )
    if all(p in new_state.status.done for p in new_state.players):
        return finalize_status(new_state, registry)
    return new_state


def finalize_status(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Kroki 6 (Ready Cards) i 7 (Repair Units); potem czeka na mówcę (krok 8)."""
    del registry
    assert state.status is not None
    for player in state.players.values():
        player.exhausted_planets = []
        player.exhausted_technologies = []
        player.exhausted_strategy_cards = []
        player.breakthrough_exhausted = False
        player.leader_states = {
            leader_id: ("unlocked" if leader_state == "exhausted" else leader_state)
            for leader_id, leader_state in player.leader_states.items()
        }
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
    new_state = strategy_phase.accumulate_unpicked_tg(state, registry)
    new_state = strategy_phase.reset_strategy_cards(new_state)
    new_state.status = None
    if not new_state.custodians_removed:
        return turn_flow.next_round(new_state)
    new_state.phase = Phase.AGENDA
    for player in new_state.players.values():
        player.passed = False
        player.took_action_this_turn = False
    # Bez kart strategii porządek wyznacza mówca (R_victory_points: „nearest the speaker").
    new_state.active_player_id = new_state.speaker_id
    return new_state


def complete_status(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Tryb testowy (God-Mode): domyka CAŁĄ fazę statusu domyślnymi decyzjami.

    Pomija punktowanie, nowe żetony trafiają do puli taktycznej, potem krok 8. Gdy stan
    wszedł w STATUS bez inicjalizacji (God-Mode), inicjuje ją.
    """
    work = state.clone()
    if work.status is None:
        work.status = StatusPhaseState()
    if work.status.step is StatusStep.SCORE_OBJECTIVES:
        work = _after_scoring(work, registry)
    if work.status is not None and work.status.step is StatusStep.REDISTRIBUTE:
        for player_id, player in work.players.items():
            player.tactical_cc += work.status.unassigned_cc.get(player_id, 0)
            work.status.unassigned_cc[player_id] = 0
        work = finalize_status(work, registry)
    if work.winner_id is not None or work.status is None:
        return work
    return finish_status(work, registry)
