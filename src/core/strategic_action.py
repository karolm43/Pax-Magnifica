"""Akcja strategiczna: primary (wieloetapowe) + okno secondary kart strategii (E8-T3, E8-T5).

Rozstrzyga PRIMARY karty aktywnego gracza i otwiera OKNO CZASOWE ``STRATEGY_SECONDARY``
dla pozostałych graczy (kolejka od gracza po aktywnym, zgodnie z zegarem — RULES.md 30.1).
Każdy respondent okna wykonuje secondary („follow") albo pasuje; po zamknięciu okna karta
jest wyczerpana (uproszczenie: wyczerpujemy przy zagraniu, bo w trakcie okna i tak nikt nie
może jej użyć ponownie — patrz RULES.md 30.5).

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

Dokładanie karty = wpis ``CardSpec`` w ``_CARDS`` + reguła w ``docs/RULES.md`` ze źródłem.
Karty bez wpisu mają domyślne zachowanie „brak efektu / bez kosztu" (szkielet okna działa).
Aktualnie zaimplementowane: Leadership (szkielet), Trade (pełne, jako wzór karty krokowej).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.core import timing
from src.core.game_state import GameState, Phase, StrategyResolution, WindowType
from src.core.registry import StaticDataRegistry

# Numery inicjatywy (z danych, nie z pamięci: assets/.../strategy_cards → zestaw ``te``).
# Stałe lokalne dla czytelności dispatchu; zgodność z rejestrem pilnują testy.
_LEADERSHIP_INITIATIVE = 1
_TRADE_INITIATIVE = 5

# Ile żetonów dowodzenia daje primary Leadership (RULES.md 30.2; LRR R_leadership).
_LEADERSHIP_PRIMARY_TOKENS = 3
# Ile dóbr handlowych daje primary Trade (RULES.md 30.6; LRR R_trade, krok 1).
_TRADE_PRIMARY_TRADE_GOODS = 3

# Klucz kontekstu okna: player_id graczy z DARMOWYM, obowiązkowym secondary (CSV).
_FREE_KEY = "free"

# Szkic wyborów primary: dowolne wartości JSON (listy id, napisy, liczby).
Draft = dict[str, Any]
# Efekt primary: (klon_stanu, registry, owner_id, szkic) -> None (mutuje klon w miejscu).
PrimaryFn = Callable[[GameState, StaticDataRegistry, str, Draft], None]
# Efekt secondary: (klon_stanu, registry, respondent_id) -> None.
SecondaryFn = Callable[[GameState, StaticDataRegistry, str], None]
# Obsługa kroku primary: (klon, registry, owner_id, krok, szkic, payload) -> None; waliduje
# payload (ValueError przy błędzie) i dopisuje wybór do szkicu.
StepFn = Callable[[GameState, StaticDataRegistry, str, str, Draft, dict[str, Any]], None]


@dataclass(frozen=True)
class CardSpec:
    """Definicja zachowania karty strategii (po numerze inicjatywy).

    Attributes:
        primary_steps: Kolejne kroki wymagające wyboru aktywnego gracza (puste = primary
            stosowane od razu).
        on_step: Walidacja i zapis wyboru dla kroku (wymagane, gdy są kroki).
        primary: Efekt primary stosowany po ostatnim kroku.
        secondary: Efekt secondary respondenta, który „follow".
        secondary_costs_token: Czy follow wydaje 1 żeton ze strategy pool.
    """

    primary_steps: tuple[str, ...] = ()
    on_step: StepFn | None = None
    primary: PrimaryFn | None = None
    secondary: SecondaryFn | None = None
    secondary_costs_token: bool = False


# --- Leadership (szkielet; model wpływu dojdzie później — RULES.md 30.2) --------------------


def _leadership_primary(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _draft: Draft
) -> None:
    """Primary Leadership: +3 żetony dowodzenia (RULES.md 30.2).

    ⚠️ ZAŁOŻENIE (do rozbudowy): żetony trafiają do puli TAKTYCZNEJ. Docelowo gracz
    wybiera pulę (krok primary). TODO: kupno żetonów za wpływ — wymaga modelu wpływu.
    """
    player = state.players.get(player_id)
    if player is None:
        return
    player.tactical_cc += _LEADERSHIP_PRIMARY_TOKENS


# --- Trade (RULES.md 30.6) ------------------------------------------------------------------


def _replenish_commodities(state: GameState, player_id: str) -> None:
    """Uzupełnia commodities gracza do wartości z jego arkusza frakcji (nie więcej)."""
    player = state.players[player_id]
    player.commodities = max(player.commodities, player.commodity_value)


def _trade_step(
    state: GameState,
    _registry: StaticDataRegistry,
    owner_id: str,
    step: str,
    draft: Draft,
    payload: dict[str, Any],
) -> None:
    """Krok Trade „choose_free_players": aktywny wskazuje graczy z darmowym secondary."""
    if step != "choose_free_players":
        raise ValueError(f"Unknown Trade step: {step}")
    raw = payload.get("players", [])
    if not isinstance(raw, list) or not all(isinstance(p, str) for p in raw):
        raise ValueError("'players' must be a list of player ids.")
    chosen: list[str] = []
    for pid in raw:
        if pid not in state.players:
            raise ValueError(f"Unknown player: {pid}")
        if pid == owner_id:
            raise ValueError("You cannot choose yourself - choose OTHER players.")
        if pid in chosen:
            raise ValueError(f"Player chosen twice: {pid}")
        chosen.append(pid)
    draft["free_players"] = chosen


def _trade_primary(
    state: GameState, _registry: StaticDataRegistry, owner_id: str, _draft: Draft
) -> None:
    """Primary Trade: +3 TG, uzupełnij commodities (kroki 1-2; wybór graczy = krok 3)."""
    state.players[owner_id].trade_goods += _TRADE_PRIMARY_TRADE_GOODS
    _replenish_commodities(state, owner_id)


def _trade_secondary(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> None:
    """Secondary Trade: uzupełnij commodities."""
    _replenish_commodities(state, player_id)


# Dispatch po inicjatywie. Brak wpisu = domyślny ``CardSpec()`` (brak efektu, bez kosztu).
_CARDS: dict[int, CardSpec] = {
    _LEADERSHIP_INITIATIVE: CardSpec(primary=_leadership_primary),
    _TRADE_INITIATIVE: CardSpec(
        primary_steps=("choose_free_players",),
        on_step=_trade_step,
        primary=_trade_primary,
        secondary=_trade_secondary,
        secondary_costs_token=True,
    ),
}


def _spec(initiative: int) -> CardSpec:
    return _CARDS.get(initiative, CardSpec())


def _free_players(context: dict[str, str | int]) -> set[str]:
    """Gracze z darmowym, obowiązkowym secondary (z kontekstu okna)."""
    raw = str(context.get(_FREE_KEY, ""))
    return {p for p in raw.split(",") if p}


def _card_initiative_of_player(state: GameState, player_id: str) -> int | None:
    """Najniższy numer karty strategii gracza (jego karta do zagrania), lub None."""
    player = state.players.get(player_id)
    if player is None or not player.strategy_cards:
        return None
    return min(player.strategy_cards)


def _finish_primary(
    state: GameState,
    registry: StaticDataRegistry,
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
        spec.primary(state, registry, owner_id, draft)
    state.pending_strategy = None

    queue = timing.build_response_queue(state, owner_id)
    if not queue:
        return state
    free = [p for p in draft.get("free_players", []) if p in queue]
    return timing.open_window(
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


def play_strategy_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    initiative: int,
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
    return _finish_primary(new_state, registry, player_id, initiative, {})


def submit_primary_step(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    payload: dict[str, Any],
) -> GameState:
    """Przesyła wybór dla bieżącego kroku primary (tylko właściciel karty).

    Waliduje payload (dispatch karty), dopisuje go do szkicu i przechodzi do kolejnego
    kroku; po ostatnim kroku stosuje primary i otwiera okno secondary.

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

    new_state = state.clone()
    assert new_state.pending_strategy is not None  # zachowane przez clone
    current = new_state.pending_strategy
    spec.on_step(new_state, registry, player_id, current.step, current.draft, payload)

    index = spec.primary_steps.index(current.step)
    if index + 1 < len(spec.primary_steps):
        current.step = spec.primary_steps[index + 1]
        return new_state
    return _finish_primary(new_state, registry, player_id, current.initiative, current.draft)


def resolve_secondary(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    *,
    execute: bool,
) -> GameState:
    """Rozstrzyga odpowiedź bieżącego respondenta w oknie secondary (RULES.md 30.1, 30.5).

    ``execute=True`` („follow") → opłata żetonem ze strategy pool (jeśli karta tego wymaga
    i gracz nie jest „free"), potem efekt secondary. ``execute=False`` → PAS. Gracz „free"
    NIE może spasować (secondary Trade jest dla niego obowiązkowe). W obu przypadkach
    kolejka okna przesuwa się o jeden; po dopełnieniu okno zamyka się automatycznie.

    Raises:
        ValueError: Brak okna secondary, zły respondent, brak żetonu w strategy pool albo
            próba pasu przez gracza z obowiązkowym secondary. Przy błędzie stan bez zmian.
    """
    window = state.pending_window
    if window is None or window.window_type is not WindowType.STRATEGY_SECONDARY:
        raise ValueError("No open strategy card secondary window.")
    expected = window.current_responder
    if expected is not None and player_id != expected:
        raise ValueError(
            f"It is now {expected}'s turn to respond, not {player_id} (out-of-order response)."
        )

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
            spec.secondary(new_state, registry, player_id)
    elif is_free:
        raise ValueError(
            "The active player chose you - you must resolve this secondary ability."
        )

    # Przesunięcie kolejki (waliduje, że player_id to bieżący respondent).
    new_state = timing.respond_current(new_state, player_id)
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
    return new_state
