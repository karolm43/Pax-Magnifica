"""Akcja strategiczna: primary (wieloetapowe) + okno secondary kart strategii (E8-T3, E8-T5).

Rozstrzyga PRIMARY karty aktywnego gracza i otwiera OKNO CZASOWE ``STRATEGY_SECONDARY``
dla pozostałych graczy (kolejka od gracza po aktywnym, zgodnie z zegarem — RULES.md 30.1).
Każdy respondent okna wykonuje secondary („follow", z ewentualnym ``payload`` wyborów) albo
pasuje; po zamknięciu okna karta jest wyczerpana (uproszczenie: wyczerpujemy przy zagraniu,
bo w trakcie okna i tak nikt nie może jej użyć ponownie — patrz RULES.md 30.5).

Model (RULES.md 30.5, ``docs/PROJEKT_KARTY_STRATEGII.md``):

* **Primary jest krokowe.** Karta ze zdefiniowanymi ``primary_steps`` ustawia
  ``state.pending_strategy`` (krok + szkic wyborów). Aktywny gracz przesyła kolejne kroki
  (``submit_primary_step``); efekt primary stosuje się atomowo po OSTATNIM kroku, potem
  otwiera się okno secondary. Karta bez kroków stosuje primary od razu.
* **Secondary ma KOSZT** (``secondary_costs_token``): follow wydaje 1 żeton ze strategy pool
  (wraca do rezerwy), chyba że karta go nie wymaga (Leadership) albo gracz został wskazany
  przez aktywnego jako „free" (Trade) — wtedy secondary jest DARMOWE i OBOWIĄZKOWE.
* Spasowany gracz MOŻE robić secondary (R_action_phase) — kolejka nie pomija pasujących.
* Serwer jest autorytetem: primary tylko od ``owner_id``, secondary tylko od bieżącego
  respondenta okna. Funkcje są CZYSTE (``state -> state``, operują na klonie).

Definicje kart: pakiet ``core/strategy_cards`` (jedna karta = jeden moduł z ``SPEC``).
Karty bez wpisu mają domyślne zachowanie „brak efektu / bez kosztu".
"""

from __future__ import annotations

from typing import Any

from src.core import timing
from src.core.game_state import GameState, Phase, StrategyResolution, WindowType
from src.core.hex_grid import HexGrid
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards import CARDS, CardSpec, leadership, trade
from src.core.strategy_cards.base import CardContext, Draft

# Numery inicjatywy (z danych: zestaw ``te``); zgodność z rejestrem pilnują testy.
_LEADERSHIP_INITIATIVE = leadership.INITIATIVE
_TRADE_INITIATIVE = trade.INITIATIVE

# Klucz kontekstu okna: player_id graczy z DARMOWYM, obowiązkowym secondary (CSV).
_FREE_KEY = "free"
# Klucz kontekstu okna: respondent, który „follow" i czeka na koniec produkcji z karty
# (Warfare TE); kolejka stoi, dopóki produkcja się nie zakończy.
_AWAIT_PRODUCTION_KEY = "await_production"


def _spec(initiative: int) -> CardSpec:
    return CARDS.get(initiative, CardSpec())


def _free_players(context: dict[str, str | int]) -> set[str]:
    """Gracze z darmowym, obowiązkowym secondary (z kontekstu okna)."""
    raw = str(context.get(_FREE_KEY, ""))
    return {p for p in raw.split(",") if p}


def _finish_primary(
    state: GameState,
    ctx: CardContext,
    owner_id: str,
    initiative: int,
    draft: Draft,
) -> GameState:
    """Stosuje efekt primary (na klonie ``state``) i otwiera okno secondary.

    ``state`` MUSI być już klonem (mutowany w miejscu). Gdy NIE MA kogo pytać (gra solo /
    pozostali poza stołem), okna nie otwieramy — puste okno zostawałoby ustawione i
    blokowało End turn na stałe.
    """
    spec = _spec(initiative)
    if spec.primary is not None:
        spec.primary(state, ctx, owner_id, draft)
    state.pending_strategy = None

    queue = timing.build_response_queue(state, owner_id)
    if not queue:
        return state
    free = [p for p in draft.get("free_players", []) if p in queue]
    opened = timing.open_window(
        state,
        WindowType.STRATEGY_SECONDARY,
        queue,
        context={
            "initiative": initiative,
            _FREE_KEY: ",".join(free),
            # Czy follow kosztuje żeton (UI pokazuje koszt / blokuje Follow bez żetonu).
            "cost": 1 if spec.secondary_costs_token else 0,
        },
    )
    return _auto_resolve_free(opened, ctx)


def _auto_resolve_free(state: GameState, ctx: CardContext) -> GameState:
    """Rozstrzyga AUTOMATYCZNIE secondary graczy „free" (Trade), gdy przychodzi ich kolej.

    Wskazany gracz MUSI wykonać secondary (R_trade) i nie ma w nim żadnego wyboru (uzupełnienie
    commodities), więc nie pytamy go oknem - efekt stosujemy w jego kolejce (kolejność od
    lewej aktywnego zostaje zachowana). Zatrzymuje się na pierwszym nie-„free" respondencie.
    """
    current = state
    while True:
        window = current.pending_window
        if window is None or window.window_type is not WindowType.STRATEGY_SECONDARY:
            return current
        responder = window.current_responder
        if responder is None or responder not in _free_players(window.context):
            return current
        spec = _spec(int(window.context.get("initiative", 0)))
        current = current.clone()
        if spec.secondary is not None:
            spec.secondary(current, ctx, responder, {})
        current = _advance_window(current, responder)


def play_strategy_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    initiative: int,
    *,
    grid: HexGrid | None = None,
) -> GameState:
    """Akcja strategiczna: start rozstrzygania PRIMARY (RULES.md 30.1, 30.3, 30.5).

    Walidacja (silnik-sędzia): gracz istnieje i posiada kartę; faza ACTION; to jego tura;
    nie spasował; nie wykonał innej akcji w tej turze; karta nie jest wyczerpana; nie trwa
    okno ani wieloetapowe primary. Następnie karta jest oznaczana jako zagrana, a akcja
    tury jako wykonana. Karta z krokami ustawia ``pending_strategy`` (czeka na wybory);
    karta bez kroków stosuje primary od razu i otwiera okno secondary.

    Raises:
        ValueError: Gdy któryś warunek legalności nie jest spełniony.
    """
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    player = state.players[player_id]
    if initiative not in player.strategy_cards:
        raise ValueError(f"Player does not hold the initiative card {initiative}.")
    # SĘDZIA tury (RULES.md 30.3, R_action_phase): akcja strategiczna to JEDNA z akcji tury.
    if state.phase is not Phase.ACTION:
        raise ValueError("A strategic action can only be performed during the action phase.")
    if state.active_player_id != player_id:
        raise ValueError(
            f"It is not {player_id}'s turn (active: {state.active_player_id})."
        )
    if player.passed:
        raise ValueError("You have passed - you cannot perform a strategic action.")
    if player.took_action_this_turn:
        raise ValueError(
            "You already took an action this turn - end your turn before acting again."
        )
    if initiative in player.exhausted_strategy_cards:
        raise ValueError(f"Strategy card {initiative} was already played this round.")
    if state.pending_window is not None or state.pending_strategy is not None:
        raise ValueError(
            "Another timing window is already open - resolve it before the strategic action."
        )

    new_state = state.clone()
    target = new_state.players[player_id]
    # Oznacz kartę jako zagraną (idempotentnie) + akcja strategiczna = akcja tury
    # (RULES.md 31.7: End turn przestaje być zablokowany „brakiem akcji").
    if initiative not in target.exhausted_strategy_cards:
        target.exhausted_strategy_cards = [*target.exhausted_strategy_cards, initiative]
    target.took_action_this_turn = True

    spec = _spec(initiative)
    if spec.primary_steps:
        new_state.pending_strategy = StrategyResolution(
            initiative=initiative,
            owner_id=player_id,
            step=spec.primary_steps[0],
        )
        return new_state
    return _finish_primary(new_state, CardContext(registry, grid), player_id, initiative, {})


def submit_primary_step(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    payload: dict[str, Any],
    *,
    grid: HexGrid | None = None,
) -> GameState:
    """Przesyła wybór dla bieżącego kroku primary (tylko właściciel karty).

    Waliduje payload (dispatch karty), dopisuje go do szkicu i przechodzi do kolejnego
    kroku (liniowo wg ``primary_steps`` albo wg ``next_step`` karty); po ostatnim kroku
    stosuje primary i otwiera okno secondary.

    Raises:
        ValueError: Brak rozstrzygania primary, to nie właściciel, albo zły payload.
    """
    pending = state.pending_strategy
    if pending is None:
        raise ValueError("No strategy card primary is awaiting a choice.")
    if player_id != pending.owner_id:
        raise ValueError(
            f"Only {pending.owner_id} can resolve this primary ability, not {player_id}."
        )
    spec = _spec(pending.initiative)
    if spec.on_step is None:
        raise ValueError("This card has no interactive primary steps.")

    ctx = CardContext(registry, grid)
    new_state = state.clone()
    assert new_state.pending_strategy is not None  # zachowane przez clone
    current = new_state.pending_strategy
    spec.on_step(new_state, ctx, player_id, current.step, current.draft, payload)

    if spec.next_step is not None:
        following = spec.next_step(current.step, current.draft)
    else:
        index = spec.primary_steps.index(current.step)
        following = spec.primary_steps[index + 1] if index + 1 < len(spec.primary_steps) else None
    if following is not None:
        current.step = following
        return new_state
    return _finish_primary(new_state, ctx, player_id, current.initiative, current.draft)


def resolve_secondary(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    *,
    execute: bool,
    payload: dict[str, Any] | None = None,
    grid: HexGrid | None = None,
) -> GameState:
    """Rozstrzyga odpowiedź bieżącego respondenta w oknie secondary (RULES.md 30.1, 30.5).

    ``execute=True`` („follow") → opłata żetonem ze strategy pool (jeśli karta tego wymaga
    i gracz nie jest „free"), potem efekt secondary z wyborami z ``payload`` (planety do
    wydania, rozkład żetonów...). ``execute=False`` → PAS. Gracz „free" NIE może spasować
    (secondary Trade jest dla niego obowiązkowe). Kolejka okna przesuwa się o jeden; po
    dopełnieniu okno zamyka się automatycznie.

    Raises:
        ValueError: Brak okna secondary, zły respondent, brak żetonu w strategy pool, zły
            payload albo próba pasu przez gracza z obowiązkowym secondary. Stan bez zmian.
    """
    window = state.pending_window
    if window is None or window.window_type is not WindowType.STRATEGY_SECONDARY:
        raise ValueError("No open strategy card secondary window.")
    expected = window.current_responder
    if expected is not None and player_id != expected:
        raise ValueError(
            f"It is now {expected}'s turn to respond, not {player_id} (out-of-order response)."
        )

    if window.context.get(_AWAIT_PRODUCTION_KEY):
        raise ValueError("Finish the production first (use 'Finish production').")
    initiative = int(window.context.get("initiative", 0))
    spec = _spec(initiative)
    is_free = player_id in _free_players(window.context)

    new_state = state.clone()
    if execute:
        if spec.secondary_costs_token and not is_free:
            responder = new_state.players[player_id]
            if responder.strategic_cc < 1:
                raise ValueError(
                    "You need 1 command token in your strategy pool to follow this card."
                )
            responder.strategic_cc -= 1
            responder.cc_reinf += 1  # wydany żeton wraca do rezerwy
        if spec.secondary is not None:
            spec.secondary(new_state, CardContext(registry, grid), player_id, payload or {})
    elif is_free:
        raise ValueError(
            "The active player chose you - you must resolve this secondary ability."
        )

    grant = new_state.production_grant
    if execute and grant is not None and grant.standalone and grant.player_id == player_id:
        # Secondary otworzyło produkcję (Warfare TE): kolejka czeka na jej zakończenie.
        assert new_state.pending_window is not None
        new_state.pending_window.context = {
            **new_state.pending_window.context,
            _AWAIT_PRODUCTION_KEY: player_id,
        }
        return new_state

    return _auto_resolve_free(_advance_window(new_state, player_id), CardContext(registry, grid))


def _advance_window(state: GameState, player_id: str) -> GameState:
    """Przesuwa kolejkę okna secondary (waliduje respondenta) i zamyka je po dopełnieniu."""
    new_state = timing.respond_current(state, player_id)
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
    return new_state


def after_standalone_production(state: GameState) -> GameState:
    """Wznawia kartę strategii po zakończeniu produkcji standalone (grant zniknął).

    Wołane z warstwy API po ``production.skip_grant`` („Finish production"). Jeśli trwała
    produkcja z primary (Construction, krok ``production``) - przechodzi do kroku
    ``resume_step`` ze szkicu. Jeśli trwała produkcja z secondary (Warfare TE) - kończy
    odpowiedź respondenta i przesuwa kolejkę okna. W innych przypadkach nic nie robi.
    """
    grant = state.production_grant
    if grant is not None and grant.standalone:
        return state  # produkcja wciąż trwa
    pending = state.pending_strategy
    if pending is not None and pending.step == "production":
        new_state = state.clone()
        assert new_state.pending_strategy is not None
        resumed = new_state.pending_strategy
        resumed.step = str(resumed.draft.pop("resume_step", resumed.step))
        return new_state
    window = state.pending_window
    if (
        window is not None
        and window.window_type is WindowType.STRATEGY_SECONDARY
        and window.context.get(_AWAIT_PRODUCTION_KEY)
    ):
        responder = str(window.context[_AWAIT_PRODUCTION_KEY])
        new_state = state.clone()
        assert new_state.pending_window is not None
        context = dict(new_state.pending_window.context)
        context.pop(_AWAIT_PRODUCTION_KEY, None)
        new_state.pending_window.context = context
        return _advance_window(new_state, responder)
    return state


def step_options(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    grid: HexGrid | None = None,
) -> dict[str, Any] | None:
    """Dozwolone wybory dla UI gracza, który TERAZ musi odpowiedzieć (lub None).

    Zwraca opis bieżącego monitu: ``kind`` = ``primary`` (właściciel karty, krok z
    ``pending_strategy``) albo ``secondary`` (bieżący respondent okna), ``initiative``,
    ``step`` oraz ``options`` z modułu karty. Dane prywatne (np. podgląd agendy) karta
    zwraca wyłącznie dla ``player_id`` właściciela monitu — nigdy dla innych graczy.
    """
    ctx = CardContext(registry, grid)
    pending = state.pending_strategy
    if pending is not None and pending.owner_id == player_id:
        spec = _spec(pending.initiative)
        options = (
            spec.options(state, ctx, player_id, pending.step, pending.draft)
            if spec.options is not None
            else {}
        )
        return {
            "kind": "primary",
            "initiative": pending.initiative,
            "step": pending.step,
            "draft": dict(pending.draft),
            "options": options,
        }
    window = state.pending_window
    if (
        window is not None
        and window.window_type is WindowType.STRATEGY_SECONDARY
        and window.current_responder == player_id
    ):
        initiative = int(window.context.get("initiative", 0))
        spec = _spec(initiative)
        options = (
            spec.options(state, ctx, player_id, None, {})
            if spec.options is not None
            else {}
        )
        return {
            "kind": "secondary",
            "initiative": initiative,
            "step": None,
            "draft": {},
            "options": options,
        }
    return None
