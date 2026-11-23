"""Wspólne pomocniki efektów kart akcji (wybory gracza, planety, stawianie z rezerwy)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import exploration, objectives, unit_ops
from src.core.game_state import GameState, SystemState
from src.core.production import reinforcements_left
from src.core.registry import StaticDataRegistry
from src.core.unit_ops import UnitCause


def controlled(state: GameState, player_id: str) -> list[str]:
    """Planety kontrolowane przez gracza (w kolejności systemów na mapie)."""
    owners = objectives.planet_owners(state)
    return [planet for planet, owner in owners.items() if owner == player_id]


def with_trait(
    state: GameState, registry: StaticDataRegistry, player_id: str, trait: str
) -> list[str]:
    """Kontrolowane planety z daną cechą (``industrial`` / ``cultural`` / ``hazardous``)."""
    return [
        planet
        for planet in controlled(state, player_id)
        if trait in exploration.planet_traits(registry, planet, state)
    ]


def own_planet_param(state: GameState, player_id: str, params: Mapping[str, Any]) -> str:
    """Parametr ``planet`` = planeta kontrolowana przez gracza (inaczej ``ValueError``)."""
    planet = params.get("planet")
    if not isinstance(planet, str) or planet not in controlled(state, player_id):
        raise ValueError("Choose 1 planet you control ('planet').")
    return planet


def system_of_planet(state: GameState, planet: str) -> SystemState:
    """System, w którym leży planeta (``ValueError``, gdy planety nie ma na planszy)."""
    for system in state.systems.values():
        if planet in system.planet_owners or planet in system.planet_units:
            return system
    raise ValueError(f"Planet {planet} is not on the board.")


def system_param(state: GameState, params: Mapping[str, Any], key: str = "position") -> SystemState:
    """Parametr ``position`` = istniejący system na planszy."""
    position = params.get(key)
    system = state.systems.get(position) if isinstance(position, str) else None
    if system is None:
        raise ValueError(f"Choose a system on the board ('{key}').")
    return system


def other_player_param(
    state: GameState, player_id: str, params: Mapping[str, Any], key: str = "player"
) -> str:
    """Parametr ``player`` = INNY gracz (karty ofensywne nie mogą celować w siebie)."""
    target = params.get(key)
    if not isinstance(target, str) or target not in state.players or target == player_id:
        raise ValueError(f"Choose another player ('{key}').")
    return target


def require_reinforcements(state: GameState, player_id: str, base_type: str, count: int) -> None:
    """Sprawdza, czy w rezerwie jest dość sztuk (``None`` = żetony zastępcze, bez limitu)."""
    left = reinforcements_left(state, player_id, base_type)
    if left is not None and left < count:
        raise ValueError(f"Not enough {base_type} in reinforcements: {left} < {count}.")


def place_from_reinforcements(
    state: GameState,
    system: SystemState,
    zone: str,
    player_id: str,
    base_type: str,
    count: int,
) -> None:
    """Stawia jednostki z rezerwy (z kontrolą limitu) - jedyna droga stawiania przez karty."""
    require_reinforcements(state, player_id, base_type, count)
    unit_ops.place_units(state, system, zone, player_id, base_type, count, UnitCause.PLACED)
