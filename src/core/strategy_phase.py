"""Faza strategii — wybór kart strategii (Etap E2 planu pełnej rozgrywki).

Czyste funkcje nad ``GameState``: przyjmują stan, zwracają NOWY stan (przez ``clone``),
nie mutując wejścia — spójne z Event Sourcingiem. Reguły spisane w ``docs/RULES.md`` 13
na podstawie danych AsyncTI4 (`strategy_cards/pok.json`) i logiki bota
(`StrategyCardManager.incrementTradeGoods`, `PickStrategyCardButtonHandler`). Zero reguł
z pamięci; numery/nazwy kart pochodzą z rejestru.

Zakres E2 (szkielet): pula kart, wybór (transfer trade goods z karty do gracza),
akumulacja +1 TG na niewybranych kartach na koniec fazy, oznaczenie karty jako zagranej
(exhausted). Rozstrzyganie efektów primary/secondary (Leadership +3 CC itd.) to etap E4.
"""

from __future__ import annotations

from src.core.game_state import GameState
from src.core.models import StrategyCardDef
from src.core.registry import StaticDataRegistry


def available_initiatives(
    registry: StaticDataRegistry, set_alias: str = "pok"
) -> list[int]:
    """Lista numerów inicjatywy kart w aktywnym zestawie (rosnąco)."""
    return [card.initiative for card in registry.strategy_card_set(set_alias)]


def picked_initiatives(state: GameState) -> set[int]:
    """Zbiór numerów inicjatywy kart już wybranych przez graczy."""
    picked: set[int] = set()
    for player in state.players.values():
        picked.update(player.strategy_cards)
    return picked


def speaker_order(state: GameState) -> list[str]:
    """Kolejność graczy wg SPEAKER ORDER (mówca pierwszy, zegarowo) (RULES.md 24).

    Rotuje ``seating_order`` tak, by zaczynał się od ``speaker_id``. Gdy brak
    seating order (np. gra utworzona ręcznie), awaryjnie używa kolejności po id
    graczy — dalej zaczynając od mówcy, jeśli jest znany.
    """
    order = list(state.seating_order) or sorted(state.players)
    # Zostaw tylko istniejących graczy (seating_order może mieć nieaktualne id).
    order = [pid for pid in order if pid in state.players]
    if not order:
        return []
    speaker = state.speaker_id
    if speaker in order:
        idx = order.index(speaker)
        return order[idx:] + order[:idx]
    return order


def pick_count(state: GameState) -> int:
    """Liczba kart strategii na gracza wg liczby graczy (RULES.md 13).

    Reguła TI4: 2 karty/gracz przy 3–4 graczach, 1 karta/gracz przy 5–8. Liczba
    graczy liczona jako ``len(state.players)``. Czysta funkcja — tylko oblicza,
    nie zmienia stanu.

    Raises:
        ValueError: Gdy liczba graczy jest mniejsza niż 3 lub większa niż 8
            (liczba nieobsługiwana przez regułę); stan pozostaje bez zmian, bo
            funkcja go nie dotyka.
    """
    n = len(state.players)
    if n < 3 or n > 8:
        raise ValueError(f"Nieprawidłowa liczba graczy: {n} (dozwolone 3–8).")
    return 2 if n <= 4 else 1


def next_strategy_picker(state: GameState) -> str | None:
    """Następny gracz w speaker order poniżej ``Pick_Count`` (lub None).

    Startuje od mówcy (``speaker_order`` zawsze liczy od mówcy) i zwraca pierwszego
    gracza, który ma mniej niż ``pick_count(state)`` kart. Gdy wszyscy osiągnęli
    ``Pick_Count`` — zwraca None (faza strategii gotowa do przejścia w akcję).

    Obsługuje drugą rundę przy 3–4 graczach bez licznika rund: warunek
    ``< pick_count`` nie patrzy na numer rundy, a ``speaker_order`` zawsze zaczyna
    od mówcy, więc po skompletowaniu pierwszej karty przez wszystkich pierwszym
    graczem z <Pick_Count znów będzie mówca — naturalnie realizuje „drugą rundę od
    mówcy" (RULES.md 13, 24).

    Robustność dla niepełnego setu (<3 lub >8 graczy): ``pick_count`` rzuca wtedy
    ``ValueError``; tutaj ŁAPIEMY go i zwracamy None, by nie psuć wywołań
    wewnętrznych z niepełnym setem (np. setup, gra budowana w God-Mode). Twardy błąd
    liczby graczy pozostaje tam, gdzie to świadoma akcja gracza
    (``pick_strategy_card``/``ensure_strategy_complete``). Sygnatura bez zmian —
    wszystkie dotychczasowe wywołania działają bez zmian; przy 5–8 graczach
    (``pick_count == 1``) wynik jest identyczny jak dawniej (pierwszy bez karty).
    """
    try:
        needed = pick_count(state)
    except ValueError:
        return None
    for pid in speaker_order(state):
        if len(state.players[pid].strategy_cards) < needed:
            return pid
    return None


def pick_strategy_card(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    initiative: int,
    *,
    set_alias: str = "pok",
) -> GameState:
    """Gracz wybiera kartę strategii o danym numerze inicjatywy.

    Efekty (RULES.md 13):
    - Karta musi należeć do aktywnego zestawu i nie być wcześniej wybrana.
    - Wybór musi odbywać się w kolejności (to tura danego gracza) i poniżej
      limitu ``Pick_Count`` (2 karty/gracz przy 3–4 graczach, 1 przy 5–8).
    - Gracz otrzymuje wszystkie trade goods leżące na karcie; licznik karty → 0.
    - Numer karty trafia do ``player.strategy_cards`` (lista utrzymywana rosnąco,
      ustala inicjatywę tur).

    Kolejność walidacji (wszystkie PRZED ``clone`` — stan wejściowy niezmieniony
    przy błędzie, R5): gracz istnieje → karta w zestawie → karta niewybrana →
    kolejność wyboru → limit ``Pick_Count``. Walidacje „co" (gracz/karta) idą
    przed „kiedy" (kolejność/limit), bo błąd „nie twoja kolej" ma sens dopiero dla
    istniejącego gracza i realnej karty.

    Raises:
        ValueError: Gdy gracz nie istnieje (R5.6), karta spoza zestawu (R5.4),
            karta już wybrana (R5.5), wybór poza kolejnością (R4.5) lub osiągnięto
            limit ``Pick_Count`` (R3.5).
    """
    if player_id not in state.players:
        raise ValueError(f"Nieznany gracz: {player_id}")
    if initiative not in available_initiatives(registry, set_alias):
        raise ValueError(f"Karta inicjatywy {initiative} nie jest w zestawie.")
    if initiative in picked_initiatives(state):
        raise ValueError(f"Karta inicjatywy {initiative} już wybrana.")
    # Kolejność (R4.5): wybierać może tylko bieżący picker w speaker order.
    picker = next_strategy_picker(state)
    if player_id != picker:
        raise ValueError(f"Wybór poza kolejnością: teraz wybiera {picker}.")
    # Limit Pick_Count (R3.5): gracz nie może przekroczyć dozwolonej liczby kart.
    allowed = pick_count(state)
    if len(state.players[player_id].strategy_cards) >= allowed:
        raise ValueError(f"Przekroczono dozwoloną liczbę kart ({allowed}).")

    new_state = state.clone()
    player = new_state.players[player_id]
    # Transfer trade goods z karty do gracza, zerowanie licznika karty.
    tg_on_card = new_state.strategy_card_tg.get(initiative, 0)
    if tg_on_card:
        player.trade_goods += tg_on_card
    new_state.strategy_card_tg[initiative] = 0
    # Lista kart utrzymywana rosnąco (R5.1) — ustala poprawną inicjatywę tur.
    player.strategy_cards = sorted([*player.strategy_cards, initiative])
    # Przekaż turę wyboru następnemu graczowi w speaker order (lub None, gdy
    # wszyscy już wybrali — faza gotowa do przejścia w akcję). RULES.md 24.
    new_state.active_player_id = next_strategy_picker(new_state)
    return new_state


def play_strategy_card(
    state: GameState, player_id: str, initiative: int
) -> GameState:
    """Oznacza kartę strategii gracza jako ZAGRANĄ (exhausted/odwróconą).

    Nie rozstrzyga efektów primary (to etap E4) — jedynie zmienia stan karty, by
    panel pokazał ją jako zużytą. Idempotentne (ponowne zagranie nie duplikuje).

    Raises:
        ValueError: Gdy gracz nie posiada tej karty.
    """
    if player_id not in state.players:
        raise ValueError(f"Nieznany gracz: {player_id}")
    player = state.players[player_id]
    if initiative not in player.strategy_cards:
        raise ValueError(f"Gracz nie posiada karty inicjatywy {initiative}.")

    new_state = state.clone()
    target = new_state.players[player_id]
    if initiative not in target.exhausted_strategy_cards:
        target.exhausted_strategy_cards = [
            *target.exhausted_strategy_cards,
            initiative,
        ]
    return new_state


def accumulate_unpicked_tg(
    state: GameState, registry: StaticDataRegistry, *, set_alias: str = "pok"
) -> GameState:
    """Dokłada +1 trade good na każdej NIEWYBRANEJ karcie zestawu (koniec fazy).

    Port reguły ``StrategyCardManager.incrementTradeGoods``: dla każdego numeru karty
    spoza zbioru wybranych licznik TG rośnie o 1. Wywoływane przy przejściu do nowej
    rundy (karty wracają do puli, niechciane zyskują TG).
    """
    new_state = state.clone()
    picked = picked_initiatives(new_state)
    for initiative in available_initiatives(registry, set_alias):
        if initiative not in picked:
            new_state.strategy_card_tg[initiative] = (
                new_state.strategy_card_tg.get(initiative, 0) + 1
            )
    return new_state


def reset_strategy_cards(state: GameState) -> GameState:
    """Zwraca wszystkie karty strategii do puli (czyści wybory graczy).

    Używane na starcie nowej fazy strategii: karty wracają do puli, ``strategy_cards``
    i ``exhausted_strategy_cards`` graczy są czyszczone. Trade goods na kartach
    (``strategy_card_tg``) NIE są czyszczone — akumulują się między rundami.
    """
    new_state = state.clone()
    for player in new_state.players.values():
        player.strategy_cards = []
        player.exhausted_strategy_cards = []
    # Nowa faza strategii zaczyna wybierać mówca (speaker) — RULES.md 24.
    new_state.active_player_id = next_strategy_picker(new_state)
    return new_state


def validate_strategy_card_set(
    registry: StaticDataRegistry, *, set_alias: str = "pok"
) -> list[StrategyCardDef]:
    """Zwraca 8 kart zestawu lub ``ValueError``, gdy łamany komplet/unikalność.

    Guard spójności danych rejestru — reguła inicjalizacji fazy strategii
    (Requirement 6.1, 6.2), dlatego żyje w ``core/``, a nie w routerze: woła go
    zarówno ``api/``, jak i przyszłe ``ai/``. Dane kart pochodzą WYŁĄCZNIE z
    ``StaticDataRegistry.strategy_card_set`` — zero hardkodowania.

    Sprawdza niezmienniki zestawu podstawowego TI4:
    - dokładnie 8 kart,
    - każdy ``Initiative`` mieści się w zakresie 1..8,
    - brak duplikatów ``Initiative``.

    Returns:
        Lista ``StrategyCardDef`` (ta sama, co z rejestru — posortowana po
        ``initiative``), gdy zestaw jest spójny.

    Raises:
        ValueError: Gdy komplet (dokładnie 8) lub unikalność ``Initiative`` 1–8
            jest złamana; komunikat „Niespójny zestaw kart: {szczegół}.".
    """
    cards = registry.strategy_card_set(set_alias)

    if len(cards) != 8:
        raise ValueError(
            f"Niespójny zestaw kart: oczekiwano 8 kart, jest {len(cards)}."
        )

    initiatives = [card.initiative for card in cards]

    out_of_range = sorted({i for i in initiatives if i < 1 or i > 8})
    if out_of_range:
        raise ValueError(
            "Niespójny zestaw kart: inicjatywa poza zakresem 1–8: "
            f"{out_of_range}."
        )

    duplicates = sorted({i for i in initiatives if initiatives.count(i) > 1})
    if duplicates:
        raise ValueError(
            f"Niespójny zestaw kart: zduplikowane inicjatywy: {duplicates}."
        )

    return cards
