"""Żetony dowodzenia gracza: rezerwa + trzy pule na arkuszu — JEDYNE miejsce ich zmiany.

RULES.md 43.1a (punkty centralne): każda zmiana ``PlayerState.cc_reinf`` (rezerwa) oraz
``tactical_cc`` / ``fleet_cc`` / ``strategic_cc`` (pule na arkuszu dowodzenia) w ``core/``
idzie przez funkcje tego modułu (wyjątek: God-Mode w ``core/board_edit.py``).
Hook zmieniający żetony
(np. „zdobywasz dodatkowy żeton", „aktywacja bez żetonu") dopisujemy tu raz, a nie w każdym
miejscu, które kładzie, zdejmuje albo przenosi żeton.

Źródło reguł: ``docs/rules_tirules/R_command_tokens.md``, ``R_command_sheet.md``,
``R_fleet_pool.md`` (RULES.md 5). Żetony położone NA PLANSZY (``SystemState.command_tokens``)
to osobna sprawa i nie są tu zmieniane — ten moduł liczy wyłącznie to, co jest na arkuszu
i w rezerwie.

Ruchy żetonu, które modelujemy (żeton nigdy nie znika bez śladu):
  * rezerwa -> pula arkusza            (``gain_from_reinforcements``)
  * pula arkusza -> plansza / poza     (``spend_from_pool``; plansza obsługiwana przez wołającego)
  * pula arkusza -> rezerwa            (``spend_to_reinforcements``)
  * rezerwa -> plansza                 (``take_from_reinforcements``)
  * plansza -> rezerwa                 (``return_to_reinforcements``)

Funkcje operują na przekazanym ``state`` (KLON roboczy wołającego) i same go nie klonują.
"""

from __future__ import annotations

from src.core.game_state import GameState, PlayerState, SystemState

POOLS: tuple[str, ...] = ("tactical", "fleet", "strategic")

_POOL_ATTR: dict[str, str] = {
    "tactical": "tactical_cc",
    "fleet": "fleet_cc",
    "strategic": "strategic_cc",
}


def _player(state: GameState, player_id: str) -> PlayerState:
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    return player


def _attr(pool: str) -> str:
    attr = _POOL_ATTR.get(pool)
    if attr is None:
        raise ValueError(f"Unknown command token pool: {pool}.")
    return attr


def pool_count(state: GameState, player_id: str, pool: str) -> int:
    """Ile żetonów jest w puli ``pool`` na arkuszu gracza."""
    return int(getattr(_player(state, player_id), _attr(pool)))


def sheet_total(state: GameState, player_id: str) -> int:
    """Suma żetonów we wszystkich trzech pulach arkusza (bez rezerwy)."""
    return sum(pool_count(state, player_id, pool) for pool in POOLS)


def reinforcements(state: GameState, player_id: str) -> int:
    """Ile żetonów gracz ma w rezerwie."""
    return _player(state, player_id).cc_reinf


def spend_from_pool(state: GameState, player_id: str, pool: str, amount: int = 1) -> None:
    """Zdejmuje ``amount`` żetonów z puli arkusza (żeton idzie na planszę lub poza grę).

    Raises:
        ValueError: Nieznana pula, ujemna ilość albo za mało żetonów w puli.
    """
    if amount < 0:
        raise ValueError("The number of command tokens cannot be negative.")
    player = _player(state, player_id)
    attr = _attr(pool)
    have = int(getattr(player, attr))
    if amount > have:
        raise ValueError(f"Not enough command tokens in the {pool} pool: {amount} > {have}.")
    setattr(player, attr, have - amount)


def spend_to_reinforcements(
    state: GameState, player_id: str, pool: str, amount: int = 1
) -> None:
    """Wydaje ``amount`` żetonów z puli arkusza i zwraca je do rezerwy (np. secondary, cele)."""
    spend_from_pool(state, player_id, pool, amount)
    return_to_reinforcements(state, player_id, amount)


def take_from_reinforcements(state: GameState, player_id: str, amount: int = 1) -> None:
    """Zabiera ``amount`` żetonów z rezerwy (żeton idzie na planszę lub do puli)."""
    if amount < 0:
        raise ValueError("The number of command tokens cannot be negative.")
    player = _player(state, player_id)
    if amount > player.cc_reinf:
        raise ValueError("Not enough command tokens in your reinforcements.")
    player.cc_reinf -= amount


def return_to_reinforcements(state: GameState, player_id: str, amount: int = 1) -> None:
    """Oddaje ``amount`` żetonów do rezerwy (np. zdjęte z planszy)."""
    if amount < 0:
        raise ValueError("The number of command tokens cannot be negative.")
    _player(state, player_id).cc_reinf += amount


def remove_from_board(state: GameState, system: SystemState, player_id: str) -> None:
    """Zdejmuje żeton gracza z systemu na planszy i oddaje go do rezerwy.

    Raises:
        ValueError: Gdy gracz nie ma w tym systemie swojego żetonu.
    """
    if player_id not in system.command_tokens:
        raise ValueError(f"You have no command token in system {system.position}.")
    system.command_tokens.remove(player_id)
    return_to_reinforcements(state, player_id, 1)


def place_on_board_from_pool(
    state: GameState, system: SystemState, player_id: str, pool: str
) -> None:
    """Kładzie w systemie żeton gracza zabrany z PULI ARKUSZA (Stymie Ω przy pustej rezerwie).

    Raises:
        ValueError: Gracz ma już żeton w systemie albo pusta pula (stan bez zmian).
    """
    if player_id in system.command_tokens:
        raise ValueError(f"{player_id} already has a command token in system {system.position}.")
    spend_from_pool(state, player_id, pool)
    system.command_tokens.append(player_id)


def return_board_token_to_pool(
    state: GameState, system: SystemState, player_id: str, pool: str = "tactical"
) -> None:
    """Zdejmuje żeton gracza z systemu i kładzie go w puli arkusza (np. Counterstroke).

    W odróżnieniu od ``remove_from_board`` żeton NIE trafia do rezerwy, tylko do ``pool``.

    Raises:
        ValueError: Gdy gracz nie ma w tym systemie swojego żetonu albo nieznana pula.
    """
    _attr(pool)
    if player_id not in system.command_tokens:
        raise ValueError(f"You have no command token in system {system.position}.")
    system.command_tokens.remove(player_id)
    add_to_pool(state, player_id, pool, 1)


def place_on_board_from_reinforcements(
    state: GameState, system: SystemState, player_id: str
) -> None:
    """Kładzie w systemie żeton gracza zabrany Z JEGO REZERWY (np. Signal Jamming).

    Gracz ma w systemie najwyżej jeden swój żeton (R_command_tokens).

    Raises:
        ValueError: Gdy gracz ma już żeton w tym systemie albo pustą rezerwę (stan bez zmian).
    """
    if player_id in system.command_tokens:
        raise ValueError(f"{player_id} already has a command token in system {system.position}.")
    take_from_reinforcements(state, player_id, 1)
    system.command_tokens.append(player_id)


def add_to_pool(state: GameState, player_id: str, pool: str, amount: int = 1) -> None:
    """Dodaje ``amount`` żetonów do puli arkusza (źródło żetonu obsługuje wołający)."""
    if amount < 0:
        raise ValueError("The number of command tokens cannot be negative.")
    player = _player(state, player_id)
    attr = _attr(pool)
    setattr(player, attr, int(getattr(player, attr)) + amount)


def gain_from_reinforcements(state: GameState, player_id: str, pools: dict[str, int]) -> None:
    """Przenosi żetony z rezerwy do wskazanych pul (``{"tactical": n, ...}``).

    Raises:
        ValueError: Nieznana pula albo łączna ilość większa niż rezerwa (stan bez zmian).
    """
    for pool in pools:
        _attr(pool)
    total = sum(pools.values())
    take_from_reinforcements(state, player_id, total)
    for pool, amount in pools.items():
        add_to_pool(state, player_id, pool, amount)


def set_pools(state: GameState, player_id: str, pools: dict[str, int]) -> None:
    """Ustawia rozkład żetonów w pulach arkusza (przerozdzielenie; suma ustalona przez wołającego).

    ``pools`` musi zawierać wszystkie trzy pule i nie może mieć wartości ujemnych.
    """
    if set(pools) != set(POOLS):
        raise ValueError("Specify all command token pools (tactical, fleet, strategic).")
    if min(pools.values()) < 0:
        raise ValueError("Command token pools cannot be negative.")
    player = _player(state, player_id)
    for pool, amount in pools.items():
        setattr(player, _attr(pool), amount)


def spend_strategy_token(
    state: GameState, player_id: str, *, via_reinforcements: bool = False
) -> None:
    """Wydaje 1 żeton z puli strategicznej (secondary, cele) - JEDYNY punkt takiego wydania.

    ``via_reinforcements`` (Scepter of Emelpar: „spend a token from your reinforcements instead"):
    żeton schodzi z REZERWY zamiast z puli, a wydany wraca do rezerwy - pula strategiczna się nie
    zmienia. Gdy rezerwa jest pusta, gracz musi wydać żeton z arkusza (C_relics), czyli odmowa.
    Uprawnienie (gotowy relikt, wyczerpanie) sprawdza i wykonuje wołający.

    Raises:
        ValueError: Za mało żetonów w puli strategicznej albo w rezerwie.
    """
    if via_reinforcements:
        if _player(state, player_id).cc_reinf < 1:
            raise ValueError(
                "You have no command token in your reinforcements - spend one from your "
                "command sheet instead."
            )
        return  # żeton z rezerwy zostaje wydany i wraca do rezerwy: bez zmiany liczników
    spend_to_reinforcements(state, player_id, "strategic")
