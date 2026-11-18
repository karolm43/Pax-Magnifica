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
    _check_fleet_cap(state, player_id, pool, int(getattr(player, attr)) + amount)
    setattr(player, attr, int(getattr(player, attr)) + amount)


def fleet_token_cap(state: GameState, player_id: str) -> int | None:
    """Maks. liczba żetonów w fleet pool (``None`` = bez limitu; Fleet Regulations - RULES.md 51.6).

    Hook MODIFY ``fleet_pool.token_cap``: baza 0 = brak limitu, dodatnia wartość = limit.
    """
    from src.core import rules_hooks  # lokalnie: rules_hooks -> hooki -> command_tokens

    cap = int(rules_hooks.modify(rules_hooks.POINT_FLEET_POOL_TOKEN_CAP, state, player_id, 0))
    return cap if cap > 0 else None


def _check_fleet_cap(state: GameState, player_id: str, pool: str, new_value: int) -> None:
    if pool != "fleet":
        return
    cap = fleet_token_cap(state, player_id)
    if cap is not None and new_value > cap and new_value > pool_count(state, player_id, "fleet"):
        raise ValueError(f"Fleet Regulations: you cannot have more than {cap} tokens in your "
                         "fleet pool.")


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
    _check_fleet_cap(state, player_id, "fleet", pools["fleet"])
    for pool, amount in pools.items():
        setattr(player, _attr(pool), amount)


# Źródło żetonu wydawanego „z puli strategicznej" (parametr ``token_source`` efektów).
SOURCE_POOL = "pool"
SOURCE_SCEPTER = "scepter"


def _scepter_relic(state: GameState, player_id: str) -> str | None:
    """Gotowy relikt pozwalający wydać żeton z rezerwy zamiast z puli (Scepter of Emelpar)."""
    from src.core import rules_hooks  # leniwie: rules_hooks -> hooks -> command_tokens

    ready = rules_hooks.forbidden(
        rules_hooks.POINT_STRATEGY_TOKEN_FROM_REINFORCEMENTS, state, player_id
    )
    return next(iter(sorted(ready)), None)


def strategy_token_sources(state: GameState, player_id: str) -> list[str]:
    """Skąd gracz może teraz wydać żeton „z puli strategicznej": ``pool`` i/lub ``scepter``.

    C_relics (Scepter of Emelpar): relikt działa przy KAŻDYM wydaniu z puli strategicznej
    (secondary, zdolności frakcji, cele); bez żetonu w rezerwie trzeba wydać żeton z arkusza.
    """
    player = state.players.get(player_id)
    if player is None:
        return []
    sources: list[str] = []
    if player.strategic_cc >= 1:
        sources.append(SOURCE_POOL)
    if player.cc_reinf >= 1 and _scepter_relic(state, player_id) is not None:
        sources.append(SOURCE_SCEPTER)
    return sources


def can_spend_strategy_token(state: GameState, player_id: str) -> bool:
    """Czy gracz może wydać 1 żeton z puli strategicznej (wprost albo przez Scepter)."""
    return bool(strategy_token_sources(state, player_id))


def strategy_token_input(state: GameState, player_id: str) -> list[dict[str, object]]:
    """Wejście decyzji „skąd żeton" dla efektów wydających żeton z puli strategicznej.

    Pusta lista, gdy Scepter nie wchodzi w grę (płaci się po prostu z puli). Gdy wchodzi, gracz
    WIDZI wybór (``always``) - wyczerpanie reliktu to jego decyzja (C_relics: „you may").
    """
    from src.core import offer_inputs as oi

    sources = strategy_token_sources(state, player_id)
    if SOURCE_SCEPTER not in sources:
        return []
    relic = _scepter_relic(state, player_id) or "emelpar"
    labels = {
        SOURCE_POOL: "Spend a token from your strategy pool",
        SOURCE_SCEPTER: "Exhaust the Scepter of Emelpar: spend a token from your reinforcements",
    }
    options = [
        oi.option(src, labels[src], ref=("relic", relic) if src == SOURCE_SCEPTER else None)
        for src in sources
    ]
    return [oi.choice("token_source", "Command token", options, always=True)]


def spend_strategy_token(
    state: GameState, player_id: str, *, source: object = SOURCE_POOL
) -> None:
    """Wydaje 1 żeton z puli strategicznej (secondary, cele, zdolności) - JEDYNY punkt takiego
    wydania.

    ``source="scepter"`` (Scepter of Emelpar: „spend a token from your reinforcements instead"):
    silnik wyczerpuje gotowy relikt, żeton schodzi z REZERWY i wydany wraca do rezerwy - liczniki
    się nie zmieniają. Gdy rezerwa jest pusta, gracz musi wydać żeton z arkusza (C_relics).
    Inna wartość (``None``, ``"pool"``) = zwykłe wydanie z puli strategicznej.

    Raises:
        ValueError: Za mało żetonów w puli strategicznej albo w rezerwie / brak gotowego reliktu.
    """
    if source == SOURCE_SCEPTER:
        relic = _scepter_relic(state, player_id)
        if relic is None:
            raise ValueError("You have no ready relic that lets you spend a reserve token.")
        if _player(state, player_id).cc_reinf < 1:
            raise ValueError(
                "You have no command token in your reinforcements - spend one from your "
                "command sheet instead."
            )
        from src.core import exhaust  # leniwie (exhaust nie zależy od tego modułu)

        exhaust.exhaust_relic(state, player_id, relic)
        return  # żeton z rezerwy zostaje wydany i wraca do rezerwy: bez zmiany liczników
    if _player(state, player_id).strategic_cc < 1:
        raise ValueError("You need 1 command token in your strategy pool.")
    spend_to_reinforcements(state, player_id, "strategic")
    # „After you spend a token from your strategy pool” (Magmus, RULES.md 62.13): każdy żeton
    # osobno (C_objectives: Lead From the Front = 3 razy); Scepter (wyżej) nie wydaje z puli.
    from src.core import triggers  # lokalnie: triggers importuje hooki
    from src.core.game_events import GameEvent, Moment

    triggers.fire(
        state, GameEvent.STRATEGY_TOKEN_SPENT, Moment.AFTER, subject=player_id,
        ctx={"player": player_id},
    )
