"""Relikty działające jak karta planety (The Triad) - RULES.md 59.

„This card can be readied and spent as if it were a planet card." Silnik trzyma taki relikt jako
PSEUDO-PLANETĘ o id ``relic:<id>``: płatności (``payment``) i głosowanie (``agenda_phase``) widzą ją
na liście gotowych „planet", a wyczerpanie/odświeżenie idzie przez ``exhaust`` do
``PlayerState.exhausted_relics``. To NIE jest planeta dla innych efektów (nie można na niej stawiać
jednostek, nie ma cech ani specjalności, nie liczy się do celów) - jest poza ``planet_owners``.

Wartość pseudo-planety rejestruje hook relikt (``relic_planets.register``); zasoby i wpływ są
równe. Moduł jest liściem (bez importów silnika), by korzystały z niego ``exhaust`` i ``payment``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

PREFIX = "relic:"

# relikt -> (stan, rejestr, gracz) -> wartość zasobów i wpływu.
ValueFn = Callable[[Any, Any, str], int]
_VALUES: dict[str, ValueFn] = {}


def register(relic_id: str) -> Callable[[ValueFn], ValueFn]:
    """Rejestruje relikt jako pseudo-planetę o podanej funkcji wartości."""

    def decorate(fn: ValueFn) -> ValueFn:
        if relic_id in _VALUES:
            raise ValueError(f"Relic planet already registered for {relic_id}.")
        _VALUES[relic_id] = fn
        return fn

    return decorate


def planet_id(relic_id: str) -> str:
    """Id pseudo-planety reliktu (``relic:<id>``)."""
    return f"{PREFIX}{relic_id}"


def is_pseudo(planet: str) -> bool:
    """Czy ``planet`` to pseudo-planeta (relikt), a nie prawdziwa planeta."""
    return planet.startswith(PREFIX)


def relic_of(planet: str) -> str:
    """Id reliktu z id pseudo-planety."""
    return planet[len(PREFIX):]


def registered() -> list[str]:
    """Relikty zarejestrowane jako pseudo-planety (po załadowaniu hooków)."""
    from src.core import rules_hooks

    rules_hooks.all_hooks()  # leniwe załadowanie pakietu hooków (rejestruje wartości)
    return sorted(_VALUES)


def values(state: Any, registry: Any, player_id: str) -> dict[str, int]:
    """Pseudo-planety, które gracz MA (relikt przed nim): ``{relic:<id>: wartość}``.

    Także wyczerpane - wołający sam sprawdza gotowość (``exhausted_relics``).
    """
    player = state.players.get(player_id)
    if player is None:
        return {}
    return {
        planet_id(relic): _VALUES[relic](state, registry, player_id)
        for relic in registered()
        if relic in player.relics
    }
