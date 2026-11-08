"""Wyczerpywanie i odświeżanie planet oraz technologii — JEDYNE miejsce zmiany tych list.

RULES.md 43.1a (punkty centralne): każda zmiana ``PlayerState.exhausted_planets`` i
``PlayerState.exhausted_technologies`` w ``core/`` idzie przez funkcje tego modułu (wyjątek:
God-Mode w ``core/board_edit.py``). Hook wpływający na wyczerpywanie (np. „odśwież planetę po
zdobyciu", „ta zdolność nie wyczerpuje") dopisujemy tu raz.

Źródło reguł: ``docs/rules_tirules/R_exhausted.md``, ``R_readied.md`` (RULES.md 27). Stan „gotowy"
= posiadana planeta/technologia, której nie ma na liście wyczerpanych; odczyt nadal wprost z listy.

Funkcje operują na przekazanym ``state`` (KLON roboczy wołającego) i same go nie klonują.
"""

from __future__ import annotations

from collections.abc import Iterable

from src.core.game_state import GameState, PlayerState


def _player(state: GameState, player_id: str) -> PlayerState:
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    return player


def exhaust_planets(state: GameState, player_id: str, planets: Iterable[str]) -> None:
    """Wyczerpuje planety gracza (kolejność zachowana; już wyczerpana nie dubluje się)."""
    player = _player(state, player_id)
    current = list(player.exhausted_planets)
    for planet in planets:
        if planet not in current:
            current.append(planet)
    player.exhausted_planets = current


def ready_planets(state: GameState, player_id: str, planets: Iterable[str]) -> None:
    """Odświeża wskazane planety (zdejmuje je z listy wyczerpanych)."""
    player = _player(state, player_id)
    to_ready = set(planets)
    player.exhausted_planets = [p for p in player.exhausted_planets if p not in to_ready]


def ready_all_planets(state: GameState, player_id: str) -> None:
    """Odświeża wszystkie planety gracza (faza statusu, krok 6)."""
    _player(state, player_id).exhausted_planets = []


def exhaust_technology(state: GameState, player_id: str, tech_id: str) -> None:
    """Wyczerpuje technologię gracza (już wyczerpana nie dubluje się)."""
    player = _player(state, player_id)
    if tech_id not in player.exhausted_technologies:
        player.exhausted_technologies = [*player.exhausted_technologies, tech_id]


def ready_all_technologies(state: GameState, player_id: str) -> None:
    """Odświeża wszystkie technologie gracza (faza statusu, krok 6)."""
    _player(state, player_id).exhausted_technologies = []
