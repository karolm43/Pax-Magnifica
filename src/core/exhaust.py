"""Wyczerpywanie i odświeżanie komponentów gracza — JEDYNE miejsce zmiany tych stanów.

RULES.md 43.1a (punkty centralne): każda zmiana ``exhausted_planets``,
``exhausted_technologies``, ``exhausted_strategy_cards``, ``leader_states`` oraz
``breakthrough_exhausted`` w ``core/`` idzie przez funkcje tego modułu
(wyjątek: God-Mode w ``core/board_edit.py``). Hook wpływający na wyczerpywanie
(np. „odśwież planetę po zdobyciu", „ta zdolność nie wyczerpuje") dopisujemy tu raz.

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


def exhaust_strategy_card(state: GameState, player_id: str, initiative: int) -> None:
    """Oznacza kartę strategii (numer inicjatywy) jako zagraną/wyczerpaną (idempotentnie)."""
    player = _player(state, player_id)
    if initiative not in player.exhausted_strategy_cards:
        player.exhausted_strategy_cards = [*player.exhausted_strategy_cards, initiative]


def ready_all_strategy_cards(state: GameState, player_id: str) -> None:
    """Odświeża wszystkie karty strategii gracza (status krok 6, nowa faza strategii)."""
    _player(state, player_id).exhausted_strategy_cards = []


def exhaust_leader(state: GameState, player_id: str, leader_id: str) -> None:
    """Wyczerpuje lidera (stan ``exhausted``). Legalność (lider gotowy) sprawdza wołający."""
    player = _player(state, player_id)
    player.leader_states = {**player.leader_states, leader_id: "exhausted"}


def ready_all_leaders(state: GameState, player_id: str) -> None:
    """Odświeża wyczerpanych liderów (``exhausted`` -> ``unlocked``); pozostałe bez zmian."""
    player = _player(state, player_id)
    player.leader_states = {
        leader_id: ("unlocked" if leader_state == "exhausted" else leader_state)
        for leader_id, leader_state in player.leader_states.items()
    }


def exhaust_breakthrough(state: GameState, player_id: str) -> None:
    """Wyczerpuje przełom frakcji (Thunder's Edge)."""
    _player(state, player_id).breakthrough_exhausted = True


def ready_breakthrough(state: GameState, player_id: str) -> None:
    """Odświeża przełom frakcji (Thunder's Edge)."""
    _player(state, player_id).breakthrough_exhausted = False


def exhaust_technology(state: GameState, player_id: str, tech_id: str) -> None:
    """Wyczerpuje technologię gracza (już wyczerpana nie dubluje się)."""
    player = _player(state, player_id)
    if tech_id not in player.exhausted_technologies:
        player.exhausted_technologies = [*player.exhausted_technologies, tech_id]


def ready_all_technologies(state: GameState, player_id: str) -> None:
    """Odświeża wszystkie technologie gracza (faza statusu, krok 6)."""
    _player(state, player_id).exhausted_technologies = []
