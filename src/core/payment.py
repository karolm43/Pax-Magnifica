"""Wydawanie wpływu / zasobów z planet i trade goods (wspólne dla kart strategii).

R_influence / R_resources / R_trade_goods: wartość planety wydaje się, WYCZERPUJĄC jej kartę;
trade good może zastąpić 1 wpływ lub 1 zasób. Wydanie jest dobrowolnie nadpłacalne
(nadwyżka przepada). Funkcje są CZYSTE; ``apply_payment`` mutuje przekazany KLON.

Produkcja (``core/production.py``: ``Spend``, ``auto_pay``) dobiera płatność po swojemu, ale
samo WYDANIE (wyczerpanie planet + zdjęcie TG) idzie tą samą funkcją ``apply_payment``, tak jak
płatności za cele (``core/objective_payment.py``); ten moduł obsługuje też karty strategii
(Leadership — wpływ, Technology — zasoby), gdzie gracz JAWNIE wskazuje planety. Trade goods
zmienia wyłącznie ``core/economy.py`` (RULES.md 43.1a).
"""

from __future__ import annotations

from typing import Any, Literal

from src.core import economy, exhaust
from src.core.game_state import GameState
from src.core.planet_stats import influence_of, resources_of
from src.core.registry import StaticDataRegistry

Kind = Literal["influence", "resources"]


def ready_planet_values(
    state: GameState, registry: StaticDataRegistry, player_id: str, kind: Kind
) -> dict[str, int]:
    """Planety gracza GOTOWE do wydania → ich wartość (wpływ lub zasoby)."""
    player = state.players.get(player_id)
    if player is None:
        return {}
    exhausted = set(player.exhausted_planets)
    value_of = influence_of if kind == "influence" else resources_of
    values: dict[str, int] = {}
    for system in state.systems.values():
        for planet_id, owner in system.planet_owners.items():
            if owner == player_id and planet_id not in exhausted:
                values[planet_id] = value_of(state, registry, planet_id)
    return values


def parse_payment(payload: dict[str, Any]) -> tuple[list[str], int]:
    """Wyciąga z payloadu ``planets`` (lista id) i ``trade_goods`` (int ≥ 0)."""
    planets = payload.get("planets", [])
    if not isinstance(planets, list) or not all(isinstance(p, str) for p in planets):
        raise ValueError("'planets' must be a list of planet ids.")
    tg = payload.get("trade_goods", 0)
    if isinstance(tg, bool) or not isinstance(tg, int) or tg < 0:
        raise ValueError("'trade_goods' must be a non-negative integer.")
    return list(planets), tg


def validate_payment(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    kind: Kind,
    planets: list[str],
    trade_goods: int,
) -> int:
    """Sprawdza legalność płatności i zwraca wydaną wartość (planety + TG).

    Raises:
        ValueError: Duplikat planety, planeta nie gotowa / nie gracza, za mało TG.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if len(set(planets)) != len(planets):
        raise ValueError("The same planet was selected twice.")
    ready = ready_planet_values(state, registry, player_id, kind)
    for planet_id in planets:
        if planet_id not in ready:
            raise ValueError(f"Planet {planet_id} is not yours or is already exhausted.")
    if trade_goods > player.trade_goods:
        raise ValueError(f"Not enough trade goods: {trade_goods} > {player.trade_goods}.")
    return sum(ready[p] for p in planets) + trade_goods


def apply_payment(state: GameState, player_id: str, planets: list[str], trade_goods: int) -> None:
    """Wyczerpuje planety i zabiera TG (mutuje klon; zakłada wcześniejszą walidację)."""
    exhaust.exhaust_planets(state, player_id, planets)
    economy.spend_trade_goods(state, player_id, trade_goods)
