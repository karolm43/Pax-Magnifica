"""Fragmenty reliktów leżące w strefie gracza — JEDYNE miejsce zmiany (RULES.md 43.1a, C9).

Pole chronione przez strażnika (``tests/test_central_points.py``): ``relic_fragments``.
Funkcje MUTUJĄ przekazany stan — wołający pracuje na klonie. Punkt zaczepienia hooków:
zdobycie i przekazanie fragmentu (np. frakcje liczące fragmenty jako dowolny typ).
"""

from __future__ import annotations

from src.core.game_state import GameState


def gain(state: GameState, player_id: str, card_id: str) -> None:
    """Kładzie fragment (kartę eksploracji) odkryty w strefie gracza."""
    state.players[player_id].relic_fragments.append(card_id)


def transfer(state: GameState, giver_id: str, receiver_id: str, card_id: str) -> None:
    """Przenosi fragment ze strefy ``giver_id`` do strefy ``receiver_id`` (transakcja).

    Raises:
        ValueError: Gdy dawca nie ma takiego fragmentu.
    """
    giver_zone = state.players[giver_id].relic_fragments
    if card_id not in giver_zone:
        raise ValueError(f"Player {giver_id} does not have the relic fragment '{card_id}'.")
    giver_zone.remove(card_id)
    state.players[receiver_id].relic_fragments.append(card_id)


def purge(state: GameState, player_id: str, count: int) -> list[str]:
    """Purge ``count`` fragmentów gracza (dowolnego typu): znikają z gry, nie wracają do talii.

    Zdejmuje najstarsze fragmenty w strefie (cel Destroy Heretical Works nie rozróżnia typów).

    Raises:
        ValueError: Gracz ma mniej fragmentów, niż trzeba.
    """
    zone = state.players[player_id].relic_fragments
    if len(zone) < count:
        raise ValueError(f"You need {count} relic fragments but have only {len(zone)}.")
    purged = zone[:count]
    state.players[player_id].relic_fragments = zone[count:]
    from src.core import exploration  # lokalnie: exploration importuje ten moduł

    exploration.purge_cards(state, purged)
    return purged


def purge_chosen(state: GameState, player_id: str, card_ids: list[str]) -> None:
    """Purge WSKAZANYCH fragmentów gracza (cel Destroy Heretical Works); mutuje ``state``.

    Raises:
        ValueError: Gracz nie ma któregoś ze wskazanych fragmentów.
    """
    zone = list(state.players[player_id].relic_fragments)
    for card_id in card_ids:
        if card_id not in zone:
            raise ValueError(f"You do not have the relic fragment '{card_id}'.")
        zone.remove(card_id)
    state.players[player_id].relic_fragments = zone
    from src.core import exploration  # lokalnie: exploration importuje ten moduł

    exploration.purge_cards(state, list(card_ids))


def discard_all(state: GameState, player_id: str, deck_of: dict[str, str]) -> list[str]:
    """Wszystkie fragmenty gracza na stosy odrzuconych ich talii eksploracji (R_elimination).

    ``deck_of`` = {id fragmentu: talia} (``cultural``/``hazardous``/``industrial``/``frontier``);
    fragment bez talii w mapie znika z gry (purge). Zwraca odrzucone fragmenty.
    """
    from src.core import exploration  # lokalnie: exploration importuje ten moduł

    zone = list(state.players[player_id].relic_fragments)
    state.players[player_id].relic_fragments = []
    for card_id in zone:
        deck = deck_of.get(card_id)
        if deck is None:
            exploration.purge_cards(state, [card_id])
        else:
            exploration.discard_cards(state, deck, [card_id])
    return zone
