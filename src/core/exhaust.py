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

from src.core import relic_planets
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
        if relic_planets.is_pseudo(planet):  # relikt działający jak planeta (The Triad)
            exhaust_relic(state, player_id, relic_planets.relic_of(planet))
        elif planet not in current:
            current.append(planet)
    player.exhausted_planets = current


def ready_planets(state: GameState, player_id: str, planets: Iterable[str]) -> None:
    """Odświeża wskazane planety (zdejmuje je z listy wyczerpanych)."""
    player = _player(state, player_id)
    to_ready = set(planets)
    for planet in to_ready:
        if relic_planets.is_pseudo(planet):
            ready_relic(state, player_id, relic_planets.relic_of(planet))
    player.exhausted_planets = [p for p in player.exhausted_planets if p not in to_ready]


def ready_all_planets(state: GameState, player_id: str) -> None:
    """Odświeża wszystkie planety gracza (faza statusu, krok 6)."""
    player = _player(state, player_id)
    player.exhausted_planets = []
    for relic in relic_planets.registered():  # relikty jak planety odświeżają się z planetami
        ready_relic(state, player_id, relic)


def exhaust_strategy_card(state: GameState, player_id: str, initiative: int) -> None:
    """Oznacza kartę strategii (numer inicjatywy) jako zagraną/wyczerpaną (idempotentnie)."""
    player = _player(state, player_id)
    if initiative not in player.exhausted_strategy_cards:
        player.exhausted_strategy_cards = [*player.exhausted_strategy_cards, initiative]


def ready_strategy_card(state: GameState, player_id: str, initiative: int) -> None:
    """Odświeża jedną kartę strategii (Coup d'Etat: „the strategy card is not exhausted”)."""
    player = _player(state, player_id)
    player.exhausted_strategy_cards = [
        i for i in player.exhausted_strategy_cards if i != initiative
    ]


def ready_all_strategy_cards(state: GameState, player_id: str) -> None:
    """Odświeża wszystkie karty strategii gracza (status krok 6, nowa faza strategii)."""
    _player(state, player_id).exhausted_strategy_cards = []


def _proxy(state: GameState, player_id: str, leader_id: str) -> str:
    from src.core import rules_hooks  # local: the hooks package imports this module

    return rules_hooks.leader_proxy(state, player_id, leader_id)


def exhaust_leader(state: GameState, player_id: str, leader_id: str) -> None:
    """Wyczerpuje lidera (stan ``exhausted``). Legalność (lider gotowy) sprawdza wołający.

    A borrowed leader exhausts its proxy (Ssruu, RULES.md 62.22)."""
    player = _player(state, player_id)
    leader_id = _proxy(state, player_id, leader_id)
    player.leader_states = {**player.leader_states, leader_id: "exhausted"}


def ready_leader(state: GameState, player_id: str, leader_id: str) -> None:
    """Odświeża jednego wyczerpanego lidera (``exhausted`` -> ``unlocked``); inny stan bez zmian.

    A readied leader fires ``COMPONENT_READIED/AFTER`` (``component = leaders:<id>``): "When this
    card readies" (Artuno the Betrayer, RULES.md 62.21).
    """
    player = _player(state, player_id)
    leader_id = _proxy(state, player_id, leader_id)
    if player.leader_states.get(leader_id) == "exhausted":
        player.leader_states = {**player.leader_states, leader_id: "unlocked"}
        _leaders_readied(state, player_id, [leader_id])


def ready_all_leaders(state: GameState, player_id: str) -> None:
    """Odświeża wyczerpanych liderów (``exhausted`` -> ``unlocked``); pozostałe bez zmian."""
    player = _player(state, player_id)
    readied = [lid for lid, st in player.leader_states.items() if st == "exhausted"]
    player.leader_states = {
        leader_id: ("unlocked" if leader_state == "exhausted" else leader_state)
        for leader_id, leader_state in player.leader_states.items()
    }
    _leaders_readied(state, player_id, readied)


def _leaders_readied(state: GameState, player_id: str, leader_ids: list[str]) -> None:
    if not leader_ids:
        return
    from src.core import triggers  # lokalnie: triggers ładuje hooki, które importują ten moduł
    from src.core.game_events import GameEvent, Moment

    for leader_id in leader_ids:
        triggers.fire(
            state, GameEvent.COMPONENT_READIED, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "component": f"leaders:{leader_id}"},
        )


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


def ready_technology(state: GameState, player_id: str, tech_id: str) -> None:
    """Odświeża jedną technologię gracza (np. Bio-Stims)."""
    player = _player(state, player_id)
    player.exhausted_technologies = [t for t in player.exhausted_technologies if t != tech_id]


def ready_all_technologies(state: GameState, player_id: str) -> None:
    """Odświeża wszystkie technologie gracza (faza statusu, krok 6)."""
    _player(state, player_id).exhausted_technologies = []


def exhaust_legendary(state: GameState, player_id: str, planet_id: str) -> None:
    """Wyczerpuje kartę zdolności legendarnej planety (niezależnie od karty planety)."""
    player = _player(state, player_id)
    if planet_id not in player.exhausted_legendaries:
        player.exhausted_legendaries = [*player.exhausted_legendaries, planet_id]


def ready_legendary(state: GameState, player_id: str, planet_id: str) -> None:
    """Odświeża jedną kartę zdolności legendarnej (efekty „odśwież planetę" jej NIE ruszają)."""
    player = _player(state, player_id)
    player.exhausted_legendaries = [p for p in player.exhausted_legendaries if p != planet_id]


def ready_all_legendaries(state: GameState, player_id: str) -> None:
    """Odświeża wszystkie karty zdolności legendarnych gracza (faza statusu, krok 6)."""
    _player(state, player_id).exhausted_legendaries = []


def exhaust_relic(state: GameState, player_id: str, relic_id: str) -> None:
    """Wyczerpuje relikt gracza (już wyczerpany nie dubluje się). Legalność sprawdza wołający."""
    player = _player(state, player_id)
    if relic_id not in player.exhausted_relics:
        player.exhausted_relics = [*player.exhausted_relics, relic_id]


def ready_relic(state: GameState, player_id: str, relic_id: str) -> None:
    """Odświeża jeden relikt gracza."""
    player = _player(state, player_id)
    player.exhausted_relics = [r for r in player.exhausted_relics if r != relic_id]


def ready_all_relics(state: GameState, player_id: str) -> None:
    """Odświeża wszystkie relikty gracza (faza statusu, krok 6)."""
    _player(state, player_id).exhausted_relics = []
