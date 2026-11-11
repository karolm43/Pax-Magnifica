"""Przepływ tur i faz (czyste funkcje nad ``GameState``).

Implementuje szkielet maszyny faz TI4 i kolejności tur fazy akcji — Etap E1 planu
pełnej rozgrywki (``docs/PLAN_PELNA_ROZGRYWKA.md``). Reguły spisane w ``docs/RULES.md`` 9
na podstawie AsyncTI4 (``EndTurnService.findNextUnpassedPlayer``). Zero reguł z pamięci.

Funkcje są czyste: przyjmują ``GameState``, zwracają NOWY ``GameState`` (przez ``clone``),
nie mutując wejścia — spójne z Event Sourcingiem (każdy wynik = nowa migawka).
"""

from __future__ import annotations

from src.core import action_budget, objective_events, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    AgendaPhaseState,
    AgendaStep,
    BonusTurn,
    GameState,
    Phase,
    StatusPhaseState,
    StatusStep,
    TurnEndWindow,
)
from src.core.registry import StaticDataRegistry
from src.core.strategy_phase import ensure_strategy_complete, next_strategy_picker

# Kolejność faz rundy TI4.
_PHASE_SEQUENCE: list[Phase] = [
    Phase.STRATEGY,
    Phase.ACTION,
    Phase.STATUS,
    Phase.AGENDA,
]


def turn_order(state: GameState) -> list[str]:
    """Kolejność graczy wg inicjatywy (najniższy numer karty strategii pierwszy).

    Gracze bez karty strategii trafiają na koniec, w stabilnej kolejności po ``player_id``.
    """

    def key(player_id: str) -> tuple[int, str]:
        player = state.players[player_id]
        initiative = min(player.strategy_cards) if player.strategy_cards else 99
        return (initiative, player_id)

    return sorted(state.players, key=key)


def strict_initiative_order(state: GameState) -> list[str]:
    """Ścisła kolejność inicjatywy — permutacja WSZYSTKICH graczy (RULES.md 9).

    W odróżnieniu od miękkiego ``turn_order`` (gracz bez karty dostaje klucz 99 i trafia
    na koniec bez błędu), tutaj KAŻDY gracz MUSI mieć przypisaną co najmniej jedną kartę
    strategii. Gracze są uporządkowani rosnąco po najniższym numerze wybranej karty
    (``min(player.strategy_cards)``); remisy rozstrzygane stabilnie po ``player_id``.

    Używane przy przejściu STRATEGY→ACTION (zadanie 4.2) PO ``ensure_strategy_complete``,
    gdzie komplet jest już zagwarantowany — w normalnym flow nie rzuci. ``ValueError``
    stanowi tu twardą gwarancję reguły R9.6.

    Raises:
        ValueError: Gdy którykolwiek gracz nie ma przypisanej karty strategii.
    """
    for player_id in state.players:
        if not state.players[player_id].strategy_cards:
            raise ValueError(
                f"Player {player_id} has no strategy card assigned."
            )

    def key(player_id: str) -> tuple[int, str]:
        return (min(state.players[player_id].strategy_cards), player_id)

    return sorted(state.players, key=key)


def next_unpassed_player(state: GameState, current_id: str | None) -> str | None:
    """Następny gracz w kolejności, który nie spasował (ani nie jest wyeliminowany).

    Rotuje listę za bieżącego gracza i zwraca pierwszego aktywnego. Gdy wszyscy
    spasowali — zwraca None (koniec fazy akcji).
    """
    order = turn_order(state)
    if not order:
        return None
    # Ustaw punkt startowy tuż za bieżącym graczem.
    if current_id in order:
        idx = order.index(current_id)
        rotated = order[idx + 1 :] + order[: idx + 1]
    else:
        rotated = order
    for pid in rotated:
        if not state.players[pid].passed:
            return pid
    return None


def all_passed(state: GameState) -> bool:
    """Czy wszyscy gracze spasowali / skończyli swoją część bieżącej fazy.

    Flaga ``passed`` jest resetowana przy każdym wejściu w fazę (``next_phase``), więc
    znaczy „skończył swoją część TEJ fazy": pas w akcji, krok w statusie, reakcja/głos
    w agendzie. ``all_passed`` liczy komplet dla bieżącej fazy.
    """
    if not state.players:
        return False
    return all(player.passed for player in state.players.values())


def can_advance_phase(state: GameState) -> bool:
    """Czy MÓWCA może już ogłosić przejście fazy (przycisk „Next phase" widoczny).

    DECYZJA PROJEKTOWA (2026-11): w fazach, gdzie każdy gracz robi swoją część po kolei
    (AKCJA — pasy; STATUS — kroki), ``Next phase`` pojawia się dopiero, gdy WSZYSCY
    skończyli (``all_passed``). W STRATEGII bramą jest kompletny wybór kart
    (``ensure_strategy_complete``). W AGENDZIE przejście (koniec agendy → nowa runda)
    jest zawsze dostępne dla mówcy — kolejne głosowania są modelowane oknami, nie tą
    bramą. To projekcja do UI; twarda walidacja i tak siedzi w ``next_phase``.
    """
    if state.phase is Phase.STRATEGY:
        try:
            ensure_strategy_complete(state)
        except ValueError:
            return False
        return True
    if state.phase is Phase.STATUS and state.status is not None:
        # Zainicjowana faza statusu (RULES.md 41): mówca ogłasza krok 8 dopiero, gdy
        # kroki 1–7 są wykonane (i gra nie zakończyła się w kroku 2).
        return state.status.step is StatusStep.COMPLETE and state.winner_id is None
    if state.phase is Phase.AGENDA and state.agenda is not None:
        # Zainicjowana faza agendy (RULES.md 51): koniec dopiero po obu agendach i kroku 3.
        return state.agenda.step is AgendaStep.COMPLETE and state.winner_id is None
    if state.phase in (Phase.ACTION, Phase.STATUS):
        return all_passed(state)
    # AGENDA bez stanu (God-Mode) i stany spoza głównej czwórki: mówca decyduje bez bramy.
    return True


# Alias czytelnościowy: kolejność inicjatywy = kolejność tur fazy akcji ORAZ kroków
# fazy statusu (RULES.md 31.3). Ta sama funkcja, inna nazwa w kontekście statusu.
initiative_order = turn_order


def _require_action_turn(state: GameState, player_id: str | None) -> None:
    """Twarda walidacja: jesteśmy w fazie akcji i to tura ``player_id`` (RULES.md 31.2).

    ``player_id=None`` pomija kontrolę tożsamości (zgodność wsteczna / wywołania
    wewnętrzne) — ale faza nadal musi być ACTION. God-Mode nie przechodzi tędy.

    Raises:
        ValueError: Gdy faza != ACTION, brak aktywnego gracza, lub ``player_id`` nie
            jest aktywnym graczem.
    """
    if state.phase is not Phase.ACTION:
        raise ValueError("A turn can only be ended/passed during the action phase.")
    if state.held_play is not None:  # okno hold-play (core/card_hold.py, RULES.md 53.6)
        raise ValueError("A played card is waiting for a possible Sabotage - wait for it.")
    if state.active_player_id is None:
        raise ValueError("No active player in the action phase.")
    if player_id is not None and player_id != state.active_player_id:
        raise ValueError(
            f"It is not {player_id}'s turn (active: {state.active_player_id})."
        )


def end_turn(
    state: GameState,
    player_id: str | None = None,
    *,
    registry: StaticDataRegistry | None = None,
    forced: bool = False,
) -> GameState:
    """Kończy turę aktywnego gracza i przekazuje ją następnemu niespasowanemu.

    ``forced=True`` (Coup d'Etat, RULES.md 53.7): tura kończy się BEZ wymogu wykonania akcji.

    JEDYNE miejsce oddające turę w fazie akcji (RULES.md 31.2). Działa tak samo po
    zwykłej akcji, jak i po pasie: spasowany gracz (``passed=True``) również kończy
    turę tym klikiem — a że jest już spasowany, ``next_unpassed_player`` go pominie
    w kolejnych okrążeniach.

    Twardo waliduje fazę akcji i (gdy podano) tożsamość aktywnego gracza — RULES.md 31.2.
    Gdy nikt nie został (wszyscy spasowali) — faza AKCJI pozostaje aktywna, a aktywny
    gracz wskazuje MÓWCĘ (RULES.md 31.4): to on ogłosi przejście fazy przez
    ``/phase/next`` (przycisk „Next phase" pojawia się dopiero, gdy ``all_passed``).
    NIE przechodzimy automatycznie do statusu — między ostatnim pasem a przejściem są
    okna czasowe końca tury/fazy ("end of turn"/"end of action phase").
    ``active_player_id`` NIGDY nie staje się tu ``None`` (zasada "zawsze czyjaś tura").

    SĘDZIA okna czasowego (RULES.md 29, R_strategic_action): dopóki trwa OTWARTE OKNO
    (``pending_window`` ≠ None), aktywny gracz NIE może zakończyć tury. Odpowiada to
    regule TI4: po zagraniu karty strategii KAŻDY inny gracz (od lewej aktywnego,
    zegarowo) ma OKAZJĘ na secondary, i DOPIERO gdy wszyscy zdecydowali (okno się
    domknie i zamknie), aktywny gracz kontynuuje/kończy turę. Blokada dotyczy każdego
    typu okna (secondary, przypisanie strat, space cannon, reakcja) — turę można oddać
    tylko „między" oknami, nie w ich trakcie.

    SĘDZIA akcji (RULES.md 31.7, R_action_phase „perform a single action"): aktywny
    gracz musi w tej turze WYKONAĆ akcję (``took_action_this_turn``) albo SPASOWAĆ
    (``passed``), zanim odda turę. Nie wolno oddać tury „bez niczego". Po przekazaniu
    tury flaga akcji NASTĘPNEGO gracza jest resetowana (to jego świeża tura).

    SĘDZIA akcji taktycznej (RULES.md 31.9, R_tactical_action): koniec tury kończy też
    TRWAJĄCĄ akcję taktyczną — z tą samą walidacją co „End action" (``tactical.end_action``):
    trwająca walka, niedokończona inwazja, otwarte okno Space Cannon i obowiązkowa walka
    kosmiczna blokują (``ValueError``). Gdy zamknięcie akcji wykryje nadwyżkę pojemności /
    puli floty (albo otworzy reakcje „po akcji taktycznej"), zwracany jest stan z OTWARTYM
    oknem, a tura ZOSTAJE przy graczu — najpierw rozstrzyga okno, potem kończy turę ponownie.
    ``registry`` włącza sprawdzenie pojemności (RULES.md 39.6); bez niego tylko pula floty.

    Raises:
        ValueError: Gdy nie wolno zakończyć tury (patrz ``_require_action_turn``),
            gdy trwa otwarte okno czasowe (najpierw je rozstrzygnij), gdy akcji taktycznej
            nie da się zamknąć (walka / inwazja w toku), lub gdy aktywny gracz nie wykonał
            w tej turze żadnej akcji ani nie spasował.
    """
    _require_action_turn(state, player_id)
    if state.pending_strategy is not None:
        raise ValueError(
            "Cannot end the turn - finish resolving the strategy card's primary ability."
        )
    if state.exploration is not None:
        raise ValueError("Cannot end the turn - finish the exploration first.")
    if state.pending_window is not None:
        raise ValueError(
            "Cannot end the turn while a timing window is open - every player must "
            "decide on the secondary first."
        )
    if state.tactical_step is not None:
        # Import lokalny: ``tactical`` → ``triggers`` → ``turn_flow`` (cykl na poziomie modułu).
        from src.core import tactical

        closed = tactical.end_action(state, registry)
        if closed.pending_window is not None:
            # Nadwyżka (capacity / fleet pool) albo reakcje po akcji: gracz najpierw je
            # rozstrzyga; tura nie została oddana.
            return closed
        state = closed
    current = state.active_player_id
    assert current is not None  # zagwarantowane przez _require_action_turn
    current_player = state.players.get(current)
    if (
        not forced
        and current_player is not None
        and not current_player.took_action_this_turn
        and not current_player.passed
    ):
        raise ValueError(
            "You must take an action (strategic, tactical, or component) or pass "
            "before ending your turn."
        )
    new_state = state.clone()
    bonus = new_state.bonus_turn
    if bonus is not None and bonus.player == current:
        return _finish_bonus_turn(new_state, current)
    triggers.fire(new_state, GameEvent.TURN, Moment.END, subject=current, ctx={"player": current})
    nxt = next_unpassed_player(new_state, new_state.active_player_id)
    if nxt is None:
        # Wszyscy spasowali: faza akcji "wyczerpana", ale wciąż ACTION. Aktywny =
        # mówca (ogłosi tranzycję); fallback na dotychczasowego, gdy mówca nieznany.
        new_state.active_player_id = new_state.speaker_id or new_state.active_player_id
    else:
        new_state.active_player_id = nxt
    # Nowa tura: limit „jedna ekspedycja na turę" (RULES.md 50) zaczyna się od nowa.
    new_state.expeditions.performed_by = None
    # Nowa tura dla następnego aktywnego gracza — zeruj jego znacznik „akcja w turze".
    nxt_id = new_state.active_player_id
    if nxt_id is not None and nxt_id in new_state.players:
        action_budget.reset_turn(new_state, nxt_id)
        new_state.players[nxt_id].transacted_with = []
        if nxt is not None:
            triggers.fire(
                new_state, GameEvent.TURN, Moment.START, subject=nxt_id,
                ctx={"player": nxt_id},
            )
    # Stabilna pauza „tura się skończyła, następny jeszcze nic nie zrobił” - na niej opierają się
    # okna kart reakcji „at the end of a turn” / „at the start of another player's turn”.
    new_state.turn_end_window = TurnEndWindow(
        ended_player=current,
        ended_passed=new_state.players[current].passed if current in new_state.players else False,
        next_player=nxt,
    )
    return new_state


def begin_bonus_action(state: GameState, player_id: str) -> None:
    """Zaczyna dodatkową akcję gracza tuż po końcu tury (Puppets on a String, Jupiter Brain).

    MUTUJE ``state`` (klon). Gracz zostaje aktywny, wykonuje JEDNĄ akcję, a ``end_turn`` oddaje
    turę temu, kto miał ją zacząć (pauza ``turn_end_window`` wraca sprzed bonusu). Na czas akcji
    ``passed=False`` (silnik blokuje akcje spasowanych); po niej flaga wraca do stanu sprzed
    bonusu (``BonusTurn.restore_passed``).

    Raises:
        ValueError: Brak pauzy po końcu tury albo trwa już dodatkowa akcja.
    """
    window = state.turn_end_window
    if window is None or state.bonus_turn is not None:
        raise ValueError("You can only perform the extra action right after a turn.")
    player = state.players[player_id]
    state.bonus_turn = BonusTurn(
        player=player_id,
        resume_player=window.next_player,
        resume_window=window.model_copy(),
        restore_passed=player.passed,
    )
    player.passed = False
    action_budget.reset_turn(state, player_id)  # zeruje też ślad pauzy (zapisany w bonus_turn)
    player.transacted_with = []
    state.active_player_id = player_id


def _finish_bonus_turn(state: GameState, player_id: str) -> GameState:
    """Kończy dodatkową akcję spasowanego gracza (Puppets on a String) i wraca do kolejki.

    To NIE jest tura: nie ma zdarzeń końca tury (efekty z czasem trwania ``TURN`` zostają), gracz
    z powrotem jest spasowany, a tura wraca do gracza, który miał ją zacząć, z oknem pauzy sprzed
    bonusu (jego tura jeszcze się nie zaczęła).
    """
    bonus = state.bonus_turn
    assert bonus is not None
    state.bonus_turn = None
    state.players[player_id].passed = bonus.restore_passed
    resume = bonus.resume_player
    if resume is None or resume not in state.players or state.players[resume].passed:
        resume = next_unpassed_player(state, player_id)
    state.active_player_id = resume or state.speaker_id or player_id
    state.turn_end_window = bonus.resume_window
    return state


def skip_next_turn(state: GameState) -> None:
    """Pomija turę gracza, który ma ją właśnie zacząć (Crisis); MUTUJE ``state`` (klon).

    Działa w pauzie po końcu tury (``turn_end_window``): pomijany gracz nie wykonuje akcji, a tura
    przechodzi na kolejnego niespasowanego. Pauza zostaje otwarta dla nowego „następnego”.

    ⚠ ZAŁOŻENIE: zdarzenie „początek tury” pomijanego gracza zdążyło się już wykonać w
    ``end_turn`` (silnik nie ma pauzy przed nim), a pominięta tura nie emituje „końca tury”.

    Raises:
        ValueError: Brak pauzy po końcu tury, albo brak następnego niespasowanego gracza.
    """
    window = state.turn_end_window
    if window is None or window.next_player is None:
        raise ValueError("There is no next player's turn to skip right now.")
    skipped = window.next_player
    nxt = next_unpassed_player(state, skipped)
    if nxt is None or nxt == skipped:
        raise ValueError("There is no other player who could take the turn after the skipped one.")
    state.active_player_id = nxt
    action_budget.reset_turn(state, nxt)
    state.players[nxt].transacted_with = []
    triggers.fire(state, GameEvent.TURN, Moment.START, subject=nxt, ctx={"player": nxt})
    state.turn_end_window = TurnEndWindow(
        ended_player=window.ended_player, ended_passed=window.ended_passed, next_player=nxt
    )


def pass_turn(state: GameState, player_id: str | None = None) -> GameState:
    """Aktywny gracz pasuje — oznacza go jako spasowanego, ale NIE oddaje tury.

    DECYZJA PROJEKTOWA (2026-11): pas jest „jak akcja", nie zakończeniem tury. Gracz
    najpierw PASUJE (``passed=True``), a dopiero potem kończy swoją turę przez
    ``end_turn`` (tak jak po każdej innej akcji). Dzięki temu każda tura w fazie akcji
    kończy się jednym, spójnym klikiem ``End turn`` — niezależnie od tego, czy był to
    zwykły ruch, czy pas. ``active_player_id`` pozostaje bez zmian (to nadal jego tura
    aż do ``end_turn``).

    Twardo waliduje fazę akcji i tożsamość (RULES.md 31.2). Dodatkowo:
    - gracz NIE MOŻE spasować, dopóki nie wykona akcji strategicznej swojej karty
      (zagranie karty = wpis w ``exhausted_strategy_cards``) — reguła R_action_phase;
    - gracz NIE MOŻE spasować, jeśli W TEJ TURZE wykonał już AKCJĘ
      (``took_action_this_turn``) — pas jest ALTERNATYWĄ dla akcji w danej turze
      („perform a single action … or pass"), nie dodatkiem po akcji. Gdy zagrałeś
      kartę/aktywowałeś system w tej turze, jedyne wyjście to ``end_turn``
      (RULES.md 31.7). Powtórny pas niespasowanego-jeszcze gracza jest idempotentny.

    Raises:
        ValueError: Gdy nie wolno spasować (zła faza/tura, brak akcji strategicznej,
            albo gracz już wykonał akcję w tej turze).
    """
    _require_action_turn(state, player_id)
    current = state.active_player_id
    assert current is not None  # zagwarantowane przez _require_action_turn
    player = state.players.get(current)
    # Pas dopiero po akcji strategicznej: gracz z kartą strategii musi ją zagrać.
    if (
        player is not None
        and not set(player.strategy_cards) <= set(player.exhausted_strategy_cards)
    ):
        # Przy 3-4 graczach (2 karty) trzeba zagrać KAŻDĄ kartę (R_action_phase).
        raise ValueError(
            "Cannot pass before performing the strategic action (play a strategy card)."
        )
    # Nie można pasować PO wykonaniu akcji w tej turze — pas zastępuje akcję, nie
    # następuje po niej. Wyjątek: gracz już spasowany (idempotentny powtórny pas).
    if (
        player is not None
        and player.took_action_this_turn
        and not player.passed
    ):
        raise ValueError(
            "You already took an action this turn - end your turn instead of passing."
        )
    new_state = state.clone()
    new_state.turn_end_window = None  # pas zamyka pauzę po poprzedniej turze
    triggers.fire(
        new_state,
        GameEvent.PLAYER_PASSED,
        Moment.WHEN,
        subject=current,
        ctx={"player": current},
    )
    new_state.players[current].passed = True
    triggers.fire(
        new_state,
        GameEvent.PLAYER_PASSED,
        Moment.AFTER,
        subject=current,
        ctx={"player": current},
    )
    if all_passed(new_state):
        triggers.fire(
            new_state, GameEvent.LAST_PLAYER_PASSED, Moment.AFTER, subject=current,
            ctx={"player": current},
        )
        objective_events.on_last_pass(new_state, current)  # tajny cel Prove Endurance
    # Pas NIE przekazuje tury — gracz nadal aktywny, odda turę przez end_turn.
    return new_state


def advance_active_player(
    state: GameState,
    player_id: str | None = None,
    *,
    mark_passed: bool = False,
) -> GameState:
    """Przekazuje „bycie aktywnym" następnemu graczowi w kolejności INICJATYWY.

    Używane w fazach STATUS i AGENDA, gdzie — wg decyzji projektowej (RULES.md 31.4) —
    zawsze jest wskazany aktywny gracz (UI/bot). To przesunięcie wskaźnika aktywnego
    gracza po kręgu (initiative order), żeby operator mógł przeklikać kolejnych graczy
    (status: krok po kroku wg inicjatywy R31.3; agenda: kolejni gracze reagują/głosują).
    Owinięcie listy jest cykliczne — po ostatnim wraca pierwszy.

    ``mark_passed`` (DECYZJA PROJEKTOWA 2026-11): gdy ``True``, bieżący gracz jest
    oznaczany jako „skończył swoją część tej fazy" (``passed=True``) ZANIM przesuniemy
    wskaźnik. Jedna flaga ``passed`` jest resetowana przy każdym wejściu w nową fazę
    (``next_phase``), więc służy uniwersalnie: w AKCJI (pas), w STATUSIE (gracz zrobił
    swój krok — ``Next player``) i w AGENDZIE (gracz spasował reakcję/głos — ``Pass``).
    Pozwala to wykryć „wszyscy skończyli" (``all_passed``) i dopiero wtedy pokazać
    mówcy ``Next phase``. Gdy ``False`` (agenda ``Next player``), tylko przesuwamy
    wskaźnik bez oznaczania — operator przewija graczy, nikogo nie kończąc.

    ``player_id`` (gdy podany) musi być bieżącym aktywnym graczem — spójnie z
    ``end_turn``/``pass_turn``. Faza MUSI być STATUS albo AGENDA.

    Raises:
        ValueError: Gdy faza != STATUS/AGENDA, brak aktywnego gracza, albo
            ``player_id`` nie jest aktywnym graczem.
    """
    if state.phase not in (Phase.STATUS, Phase.AGENDA):
        raise ValueError(
            "Advancing to the next player is only allowed in the status/agenda phase."
        )
    if state.phase is Phase.STATUS and state.status is not None:
        raise ValueError(
            "The status phase runs in steps - use the status-phase actions instead."
        )
    if state.phase is Phase.AGENDA and state.agenda is not None:
        raise ValueError(
            "The agenda phase runs in steps - use the agenda actions instead."
        )
    current = state.active_player_id
    if current is None:
        raise ValueError("No active player to advance from.")
    if player_id is not None and player_id != current:
        raise ValueError(
            f"It is not {player_id}'s turn (active: {current})."
        )
    order = turn_order(state)
    if not order:
        return state.clone()
    new_state = state.clone()
    if mark_passed and current in new_state.players:
        new_state.players[current].passed = True
    if current in order:
        idx = order.index(current)
        new_state.active_player_id = order[(idx + 1) % len(order)]
    else:
        new_state.active_player_id = order[0]
    return new_state


def next_phase(state: GameState) -> GameState:
    """Przechodzi do następnej fazy w sekwencji (bez zmiany rundy).

    Wchodząc w fazę AKCJI, ustawia aktywnego gracza na pierwszego wg inicjatywy.

    Przy przejściu STRATEGY→ACTION silnik działa jak SĘDZIA (RULES.md 29): PRZED
    jakąkolwiek zmianą fazy waliduje, że wybór kart strategii jest ukończony
    (``ensure_strategy_complete``). Gdy nie jest — propaguje ``ValueError`` i faza
    STRATEGY pozostaje NIEZMIENIONA (walidacja na ``state``, nie na klonie). To
    jedyna brama przejść faz (``/phase/next``), więc reguła R9.2–R9.4 trzyma się
    w jednym miejscu.

    Raises:
        ValueError: Przy STRATEGY→ACTION, gdy wybór kart strategii nie jest
            ukończony (propaguje z ``ensure_strategy_complete``).
    """
    if state.held_play is not None:  # okno hold-play (core/card_hold.py, RULES.md 53.6)
        raise ValueError("A played card is waiting for a possible Sabotage - wait for it.")
    # Walidacja PRZED zmianą fazy: przy ValueError faza zostaje bez zmian (R9.2–R9.4).
    if state.phase is Phase.STRATEGY:
        ensure_strategy_complete(state)
    new_state = state.clone()
    triggers.fire(
        new_state, GameEvent.PHASE, Moment.END,
        ctx={"phase": new_state.phase.name.lower()},
    )
    idx = _PHASE_SEQUENCE.index(new_state.phase)
    new_state.phase = _PHASE_SEQUENCE[(idx + 1) % len(_PHASE_SEQUENCE)]
    # Jedna flaga ``passed`` niesie „gracz skończył swoją część TEJ fazy" (pas w akcji,
    # krok w statusie, reakcja/głos w agendzie). Resetujemy ją przy KAŻDYM wejściu w
    # nową fazę, żeby „wszyscy skończyli" (all_passed) liczyło się od nowa i przycisk
    # mówcy „Next phase" pojawiał się dopiero po komplecie (DECYZJA PROJEKTOWA 2026-11).
    for player in new_state.players.values():
        player.passed = False
    # Wejście w nową fazę = świeże tury: zeruj znacznik „akcja w turze" wszystkim
    # (dotyczy fazy akcji; w innych fazach pole i tak nieużywane, ale trzymamy czysto).
    for player_id, player in new_state.players.items():
        action_budget.reset_turn(new_state, player_id)
        player.transacted_with = []
    new_state.expeditions.performed_by = None
    new_state.bonus_turn = None
    # Faza statusu (RULES.md 41): wejście inicjuje kroki (punktowanie → ... → zwrot kart);
    # naprawa jednostek to krok 7 (``status_phase``), nie samo wejście w fazę. Poza statusem
    # stan kroków jest czyszczony.
    new_state.status = StatusPhaseState() if new_state.phase is Phase.STATUS else None
    # Faza agendy (RULES.md 51): wejście inicjuje kroki; poza nią stan jest czyszczony.
    new_state.agenda = AgendaPhaseState() if new_state.phase is Phase.AGENDA else None
    if new_state.phase is Phase.AGENDA:
        # Agendę prowadzi MÓWCA (ujawnia kartę, głosowanie zaczyna się od jego lewej).
        new_state.active_player_id = new_state.speaker_id or (
            turn_order(new_state)[0] if turn_order(new_state) else None
        )
    elif new_state.phase is Phase.ACTION:
        # Faza akcji: kolejność tur wg ŚCISŁEJ INICJATYWY kart (RULES.md 9, R9.6).
        # Komplet kart zagwarantowany przez ensure_strategy_complete powyżej.
        new_state.active_player_id = strict_initiative_order(new_state)[0]
    elif new_state.phase is Phase.STRATEGY:
        # Faza strategii: wybór zaczyna MÓWCA, dalej speaker order (RULES.md 24).
        # Przy komplecie/niepełnym secie picker = None → fallback na mówcę, by w
        # toczącej się partii zawsze ktoś był aktywny (RULES.md 31.4).
        new_state.active_player_id = (
            next_strategy_picker(new_state) or new_state.speaker_id
        )
    else:
        # Status/Agenda: wg DECYZJI PROJEKTOWEJ (RULES.md 31.4) aktywny = pierwszy
        # gracz w INITIATIVE ORDER (odejście od reguły "no active player" z LRR 2.0,
        # by UI/bot zawsze miały wskazanego gracza). Gdy brak graczy z kartą (np.
        # stan przejściowy), fallback na mówcę.
        order = turn_order(new_state)
        new_state.active_player_id = order[0] if order else new_state.speaker_id
    triggers.fire(
        new_state, GameEvent.PHASE, Moment.START,
        ctx={"phase": new_state.phase.name.lower()},
    )
    return new_state


def next_round(state: GameState) -> GameState:
    """Rozpoczyna nową rundę: runda +1, faza = strategia, reset pasów i aktywnego."""
    new_state = state.clone()
    triggers.fire(
        new_state, GameEvent.PHASE, Moment.END,
        ctx={"phase": new_state.phase.name.lower()},
    )
    triggers.fire(new_state, GameEvent.ROUND, Moment.END, ctx={"round": new_state.round_number})
    new_state.round_number += 1
    new_state.phase = Phase.STRATEGY
    new_state.status = None
    new_state.agenda = None
    for player in new_state.players.values():
        player.passed = False
    # Nowa runda zaczyna się fazą strategii: wybiera mówca (RULES.md 24).
    # Wołane po reset_strategy_cards (flow.py), więc karty są już wyczyszczone.
    # Fallback na mówcę, gdy picker = None (niepełny set), by nie zostawić None
    # w toczącej się partii (RULES.md 31.4).
    new_state.active_player_id = (
        next_strategy_picker(new_state) or new_state.speaker_id
    )
    triggers.fire(new_state, GameEvent.ROUND, Moment.START, ctx={"round": new_state.round_number})
    triggers.fire(new_state, GameEvent.PHASE, Moment.START, ctx={"phase": "strategy"})
    return new_state
