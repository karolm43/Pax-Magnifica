"""Hold-play: zagrana karta akcji czeka stały czas na ewentualne Sabotage (RULES.md 53.6, 54.11).

Gdy ktoś zagrywa kartę akcji (ACTION albo reakcję), a inny gracz MÓGŁBY odpowiedzieć Sabotage, efekt
karty nie wykonuje się od razu: karta wychodzi z ręki na stół (``GameState.held_play``), reszta gry
stoi, a uprawnieni mogą zagrać Sabotage (przeciągnięciem) albo spasować. Efekt wykonuje się po
upływie stałego czasu okna (ustawienie hosta, ``reaction_window``), albo karta jest anulowana. Pasy
nie skracają okna; silnik sam pasuje za graczy bez zagrywalnego Sabotage (54.11).

**Filtr jawny (43.4 pkt 5).** O tym, czy okno w ogóle się otworzy, decydują WYŁĄCZNIE informacje
jawne: czy w grze jest talia kart akcji, czy nie wszystkie Sabotage leżą na stosie odrzuconych i
czy ktoś inny ma w ręce choć jedną kartę akcji (liczba kart w ręce jest jawna). Treść ręki NIGDY nie
steruje zachowaniem - gracz bez Sabotage dostaje okno tak samo jak z Sabotage (i pasuje).

Moduł jest CZYSTY: czas (``now``, s epoch) podaje wołający (router z zegara serwera); funkcje
operują na klonie stanu, błąd = ``ValueError`` i zero zmian.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import action_budget, card_draw, reaction_window, rules_hooks
from src.core.game_state import GameState, HeldCounter, HeldPlay
from src.core.registry import StaticDataRegistry

SABOTAGE_IDS: tuple[str, ...] = ("sabo1", "sabo2", "sabo3", "sabo4")


def is_sabotage(card_id: str) -> bool:
    """Czy to karta Sabotage (nie wywołuje okna hold i nie może być anulowana)."""
    return card_id in SABOTAGE_IDS


def require_no_hold(state: GameState) -> None:
    """Brama: gdy karta czeka w ``held_play``, żadna inna akcja gracza nie jest legalna.

    Raises:
        ValueError: Trwa okno hold-play.
    """
    if state.held_play is not None:
        raise ValueError(
            "A played card is waiting for a possible Sabotage - wait until the window closes."
        )


def sabotage_possible(state: GameState) -> bool:
    """Filtr jawny: czy Sabotage może jeszcze paść (jest talia i nie wszystkie odrzucone)."""
    decks = state.decks
    if not decks.action_card_deck and not decks.action_card_discard:
        return False  # brak talii kart akcji (np. stan złożony ręcznie) - nic do czekania
    discarded = sum(1 for card in decks.action_card_discard if is_sabotage(card))
    return discarded < len(SABOTAGE_IDS)


def _seating(state: GameState) -> list[str]:
    order = [pid for pid in state.seating_order if pid in state.players]
    return order + [pid for pid in sorted(state.players) if pid not in order]


def cancellers(state: GameState, player_id: str, card_id: str) -> list[str]:
    """Inni gracze, którzy mogą anulować kartę BEZ karty w ręce (jawne; Instinct Training).

    Hook PERMIT ``action_cards.canceller`` (RULES.md 62.9) - także przeciw Sabotage (F_xxcha).
    """
    ctx = {"player": player_id, "card": card_id}
    return [
        pid for pid in _seating(state)
        if pid != player_id
        and rules_hooks.permits(rules_hooks.POINT_ACTION_CARD_CANCELLER, state, pid, ctx)
    ]


def eligible_players(state: GameState, player_id: str, card_id: str) -> list[str]:
    """Inni gracze z >=1 kartą akcji w ręce (kolejność przy stole), gdy okno hold ma sens, oraz
    gracze anulujący bez karty (:func:`cancellers`).

    Pusta lista = karta wykonuje się natychmiast (brak talii, wszystkie Sabotage odrzucone, nikt
    inny nie ma kart akcji i nikt nie anuluje bez karty). Sabotage czeka tylko na anulujących.
    """
    free = cancellers(state, player_id, card_id)
    if is_sabotage(card_id) or not sabotage_possible(state):
        return free
    return [
        pid
        for pid in _seating(state)
        if pid != player_id and (bool(state.players[pid].private.action_cards) or pid in free)
    ]


def begin(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any],
    eligible: list[str],
    *,
    now: float,
    is_action: bool,
    window: Mapping[str, Any] | None = None,
) -> GameState:
    """Kładzie kartę na stole: wyjmuje ją z ręki i otwiera ``held_play`` (nowy stan).

    Legalność zagrania i walidację parametrów robi wołający (``action_cards``); tu tylko mechanika.
    Okno trwa stały czas (``reaction_window``); silnik od razu pasuje za uprawnionych bez
    zagrywalnego Sabotage, za botów i za graczy z „Skip all reactions” (54.11, lista prywatna).

    Raises:
        ValueError: Okno już trwa albo karty nie ma w ręce.
    """
    require_no_hold(state)
    if not eligible:
        raise ValueError("Nobody can respond - the card should resolve immediately.")
    new_state = state.clone()
    card_draw.take_from_hand_to_table(new_state, player_id, card_id)
    new_state.held_play = HeldPlay(
        player_id=player_id,
        card_id=card_id,
        params=dict(params),
        opened_at=float(now),
        eligible=list(eligible),
        is_action=is_action,
        window=dict(window) if window is not None else None,
        seconds=float(reaction_window.window_seconds(new_state)),
    )
    new_state.held_play.passed = reaction_window.auto_passers(new_state, registry, eligible)
    return new_state


def begin_counter(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    params: Mapping[str, Any],
    eligible: list[str],
    *,
    now: float,
    window: Mapping[str, Any] | None = None,
) -> GameState:
    """Sabotage na czekającą kartę czeka samo na anulujących bez karty (nowy stan; F_xxcha).

    Karta Sabotage wychodzi z ręki na stół (``HeldPlay.counter``), okno startuje od nowa dla
    ``eligible`` (anulujący). Po upływie czasu Sabotage anuluje czekającą kartę (:func:`resolve`).

    Raises:
        ValueError: Brak czekającej karty, Sabotage już czeka albo nikt nie może anulować.
    """
    held = _held(state)
    if held.counter is not None:
        raise ValueError("A Sabotage is already waiting for a response.")
    if not eligible:
        raise ValueError("Nobody can respond - the card should resolve immediately.")
    new_state = state.clone()
    card_draw.take_from_hand_to_table(new_state, player_id, card_id)
    current = new_state.held_play
    assert current is not None
    current.counter = HeldCounter(
        player_id=player_id, card_id=card_id, params=dict(params),
        window=dict(window) if window is not None else None,
        held_eligible=list(current.eligible), held_passed=list(current.passed),
    )
    current.opened_at = float(now)
    current.seconds = float(reaction_window.window_seconds(new_state))
    current.eligible = list(eligible)
    current.passed = []
    current.extended_by = []
    current.passed = reaction_window.auto_passers(new_state, registry, eligible)
    return new_state


def target_of(held: HeldPlay) -> tuple[str, str]:
    """``(gracz, karta)``, które teraz można anulować: czekające Sabotage albo sama karta."""
    if held.counter is not None:
        return held.counter.player_id, held.counter.card_id
    return held.player_id, held.card_id


def cancel_by_component(state: GameState) -> None:
    """Anulowanie komponentem (Instinct Training) - MUTUJE ``state`` (F_xxcha, RULES.md 62.9).

    Czeka Sabotage: idzie na odrzucone bez efektu, wraca okno anulowanej karty (kolejna Sabotage
    nadal możliwa). Inaczej czekająca karta idzie na odrzucone bez kosztów, a karta ACTION oddaje
    akcję tury (gracz musi wykonać inną akcję albo spasować - inaczej niż przy Sabotage).

    Raises:
        ValueError: Brak okna.
    """
    held = _held(state)
    counter = held.counter
    if counter is not None:
        held.counter = None
        held.eligible = list(counter.held_eligible)
        held.passed = list(counter.held_passed)
        card_draw.return_table_card_to_hand(state, counter.player_id, counter.card_id)
        card_draw.discard_specific_action_cards(state, counter.player_id, [counter.card_id])
        return
    is_action, player_id = held.is_action, held.player_id
    cancel_in_place(state)
    if is_action:
        action_budget.unregister_action(state, player_id)


def _held(state: GameState) -> HeldPlay:
    if state.held_play is None:
        raise ValueError("There is no card waiting for a response.")
    return state.held_play


def expired(held: HeldPlay, now: float) -> bool:
    """Czy minął stały czas okna (z „More time”)."""
    return reaction_window.expired(held, now)


def can_respond(held: HeldPlay, player_id: str) -> bool:
    """Czy gracz może jeszcze zagrać Sabotage (uprawniony i nie spasował)."""
    return player_id in held.eligible and player_id not in held.passed


def pass_hold(state: GameState, registry: StaticDataRegistry, actor_id: str) -> GameState:
    """Pas uprawnionego gracza (nowy stan). Okno trwa dalej do końca czasu (54.11).

    Raises:
        ValueError: Brak okna, gracz nieuprawniony (np. zagrywający) albo już spasował.
    """
    held = _held(state)
    if actor_id == held.player_id:
        raise ValueError("You cannot pass for the other players.")
    if actor_id not in held.eligible:
        raise ValueError(f"{actor_id} cannot respond to this card.")
    if actor_id in held.passed:
        raise ValueError(f"{actor_id} has already passed.")
    new_state = state.clone()
    assert new_state.held_play is not None
    new_state.held_play.passed = [*held.passed, actor_id]
    return new_state


def ask_for_time(state: GameState, actor_id: str) -> GameState:
    """„More time” w oknie Sabotage (nowy stan; RULES.md 54.11).

    Raises:
        ValueError: Brak okna, gracz nieuprawniony albo już prosił.
    """
    _held(state)
    new_state = state.clone()
    assert new_state.held_play is not None
    reaction_window.ask_for_time(new_state.held_play, actor_id)
    return new_state


def release(
    state: GameState, registry: StaticDataRegistry, actor_id: str, *, now: float
) -> GameState:
    """Zwolnienie okna: wykonuje efekt karty, gdy minął stały czas okna.

    Raises:
        ValueError: Brak okna, nieznany gracz albo okno jeszcze trwa.
    """
    held = _held(state)
    if actor_id not in state.players:
        raise ValueError(f"Unknown player: {actor_id}")
    if not expired(held, now):
        raise ValueError("The response window is still open.")
    return resolve(state, registry)


def resolve(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Wykonuje zapisany efekt karty (z zapisanymi ``params``) i odrzuca ją. Nowy stan."""
    from src.core import action_cards  # lokalnie: action_cards importuje ten moduł

    held = _held(state)
    new_state = state.clone()
    counter = held.counter
    if counter is not None:
        # Nikt nie anulował Sabotage: wykonuje się ono (anuluje czekającą kartę) zwykłą ścieżką.
        assert new_state.held_play is not None
        new_state.held_play.counter = None
        card_draw.return_table_card_to_hand(new_state, counter.player_id, counter.card_id)
        action_cards.run_reaction(
            new_state, registry, counter.player_id, counter.card_id, counter.params,
            counter.window or {},
        )
        return new_state
    new_state.held_play = None
    # Karta wraca na chwilę do ręki: efekt i odrzucenie przebiegają jak przy zagraniu natychmiast.
    card_draw.return_table_card_to_hand(new_state, held.player_id, held.card_id)
    action_cards.execute_played(new_state, registry, held)
    return new_state


def cancel_in_place(state: GameState) -> None:
    """Anuluje czekającą kartę (Sabotage): idzie na odrzucone, efekt się nie wykonuje (mutuje).

    Akcja tury zagrywającego pozostaje zużyta (zużył ją w chwili zagrania).

    Raises:
        ValueError: Brak okna.
    """
    held = _held(state)
    state.held_play = None
    card_draw.return_table_card_to_hand(state, held.player_id, held.card_id)
    card_draw.discard_specific_action_cards(state, held.player_id, [held.card_id])
