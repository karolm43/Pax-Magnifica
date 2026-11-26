"""Żetony frakcji leżące na mapie — JEDNO miejsce zmian (RULES.md 61.6, RULES 43.1a).

Żeton leży w strefie systemu (``space`` albo id planety), najwyżej jeden danego rodzaju na
strefę. Stan: ``SystemState.faction_tokens = {strefa: {rodzaj: właściciel}}``. Pula gracza =
``SUPPLY[rodzaj]`` minus jego żetony na planszy (liczby z AsyncTI4, RULES.md 61.6).

Funkcje MUTUJĄ przekazany stan (wołający pracuje na klonie).
"""

from __future__ import annotations

from src.core.game_state import GameState

SLEEPER = "sleeper"
SPACE = "space"
# Creuss wormhole tokens (RULES.md 62.19): kind = AsyncTI4 token id, value = the wormhole type it
# creates (``assets/data/tokens`` ``wormholes`` field - a test compares them). One of each.
CREUSS_WORMHOLES: dict[str, str] = {
    "creussalpha": "ALPHA", "creussbeta": "BETA", "creussgamma": "GAMMA",
}
# Liczba żetonów frakcji (AsyncTI4 WebPlayerArea / PlayerAreaGenerator: Sleepers 5).
SUPPLY: dict[str, int] = {SLEEPER: 5, **dict.fromkeys(CREUSS_WORMHOLES, 1)}


def wormhole_types(kinds: dict[str, str]) -> list[str]:
    """Wormhole types created by the faction tokens of one space zone (Creuss tokens)."""
    return [CREUSS_WORMHOLES[kind] for kind in sorted(kinds) if kind in CREUSS_WORMHOLES]


def owner_at(state: GameState, position: str, zone: str, kind: str) -> str | None:
    """Właściciel żetonu ``kind`` w strefie albo ``None``."""
    system = state.systems.get(position)
    if system is None:
        return None
    return system.faction_tokens.get(zone, {}).get(kind)


def planet_position(state: GameState, planet: str) -> str | None:
    """Pozycja systemu z planetą (planety bez kontrolera też - po definicji i żetonach)."""
    from src.core.strategy_cards.common import planet_position as owned_position

    found = owned_position(state, planet)
    if found is not None:
        return found
    for position, system in state.systems.items():
        if planet in system.planet_units or planet in system.faction_tokens:
            return position
    from src.core import rules_hooks  # lokalnie: rules_hooks ładuje hooki

    registry = rules_hooks.bound_registry()
    if registry is None:
        return None
    for position, system in state.systems.items():
        definition = registry.systems.get(system.system_id)
        if definition is not None and planet in definition.planets:
            return position
        if planet in system.added_planets:
            return position
    return None


def on_planet(state: GameState, planet: str, kind: str) -> str | None:
    """Właściciel żetonu ``kind`` na planecie (``None`` = brak)."""
    position = planet_position(state, planet)
    return owner_at(state, position, planet, kind) if position is not None else None


def tokens_of(state: GameState, owner: str, kind: str) -> list[tuple[str, str]]:
    """``[(pozycja, strefa)]`` żetonów gracza danego rodzaju (posortowane)."""
    return sorted(
        (position, zone)
        for position, system in state.systems.items()
        for zone, kinds in system.faction_tokens.items()
        if kinds.get(kind) == owner
    )


def supply_left(state: GameState, owner: str, kind: str) -> int:
    """Ile żetonów zostało w puli gracza."""
    return max(0, SUPPLY.get(kind, 0) - len(tokens_of(state, owner, kind)))


def place(state: GameState, owner: str, kind: str, position: str, zone: str) -> None:
    """Kładzie żeton z puli gracza.

    Raises:
        ValueError: Pusta pula, nieznany system albo strefa ma już żeton tego rodzaju.
    """
    if supply_left(state, owner, kind) <= 0:
        raise ValueError(f"You have no {kind} tokens left in your reinforcements.")
    _put(state, owner, kind, position, zone)


def move(
    state: GameState, owner: str, kind: str, source: tuple[str, str], position: str, zone: str
) -> None:
    """Przenosi żeton gracza ze strefy ``source = (pozycja, strefa)`` na nowe miejsce."""
    if owner_at(state, source[0], source[1], kind) != owner:
        raise ValueError(f"There is no {kind} token of yours there.")
    _put(state, owner, kind, position, zone)
    remove(state, source[0], source[1], kind)


def remove(state: GameState, position: str, zone: str, kind: str) -> str | None:
    """Zdejmuje żeton ze strefy (wraca do puli właściciela). Zwraca właściciela albo ``None``."""
    system = state.systems.get(position)
    if system is None:
        return None
    kinds = system.faction_tokens.get(zone)
    if not kinds or kind not in kinds:
        return None
    owner = kinds.pop(kind)
    if not kinds:
        system.faction_tokens.pop(zone, None)
    return owner


def clear_zone(state: GameState, position: str, zone: str) -> None:
    """Wszystkie żetony strefy wracają do pul właścicieli (kafel wymieniony, planeta zniszczona)."""
    system = state.systems.get(position)
    if system is not None:
        system.faction_tokens.pop(zone, None)


def _put(state: GameState, owner: str, kind: str, position: str, zone: str) -> None:
    system = state.systems.get(position)
    if system is None:
        raise ValueError(f"Unknown system {position}.")
    kinds = system.faction_tokens.setdefault(zone, {})
    if kind in kinds:
        raise ValueError(f"There already is a {kind} token there.")
    kinds[kind] = owner
