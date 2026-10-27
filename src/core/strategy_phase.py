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


def next_strategy_picker(state: GameState) -> str | None:
    """Następny gracz w speaker order, który NIE wybrał jeszcze karty (lub None).

    Startuje od mówcy; pomija graczy, którzy już mają kartę. Gdy wszyscy wybrali —
    zwraca None (faza strategii gotowa do przejścia w akcję). Nie zależy od
    bieżącego ``active_player_id`` — zawsze liczy od mówcy, więc jest stabilny
    nawet gdy operator nadpisał wybór poza kolejnością (asystent, nie sędzia).
    """
    for pid in speaker_order(state):
        if not state.players[pid].strategy_cards:
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
    - Gracz otrzymuje wszystkie trade goods leżące na karcie; licznik karty → 0.
    - Numer karty trafia do ``player.strategy_cards`` (ustala inicjatywę tur).

    Raises:
        ValueError: Gdy gracz nie istnieje, karta spoza zestawu lub już wybrana.
    """
    if player_id not in state.players:
        raise ValueError(f"Nieznany gracz: {player_id}")
    if initiative not in available_initiatives(registry, set_alias):
        raise ValueError(f"Karta inicjatywy {initiative} nie jest w zestawie.")
    if initiative in picked_initiatives(state):
        raise ValueError(f"Karta inicjatywy {initiative} już wybrana.")

    new_state = state.clone()
    player = new_state.players[player_id]
    # Transfer trade goods z karty do gracza, zerowanie licznika karty.
    tg_on_card = new_state.strategy_card_tg.get(initiative, 0)
    if tg_on_card:
        player.trade_goods += tg_on_card
    new_state.strategy_card_tg[initiative] = 0
    player.strategy_cards = [*player.strategy_cards, initiative]
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
