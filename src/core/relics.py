"""Talia reliktów i dobieranie reliktu (RULES.md 50: planety The Fracture).

Zakres: TYLKO posiadanie karty (``PlayerState.relics``). Efekty reliktów nie są kodowane.
Talia powstaje leniwie z największej talii typu ``relic`` aktywnych źródeł (jak talia agend,
``card_draw.ensure_agenda_deck``); pusta talia tasuje się ze stosu odrzuconych.
"""

from __future__ import annotations

from src.core.dice import next_rng
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

_RELIC_DECK = "relic"


def ensure_relic_deck(state: GameState, registry: StaticDataRegistry) -> None:
    """Leniwie zasiewa talię reliktów (potasowana, seedowalnie). Mutuje ``state``."""
    from src.core.objectives import deck_card_ids  # lokalnie: objectives importuje card_draw

    decks = state.decks
    if decks.relic_deck_seeded:
        return
    # Relikty już leżące u graczy nie wracają do talii (np. stan z God-Mode).
    held = {relic for player in state.players.values() for relic in player.relics}
    cards = [c for c in deck_card_ids(registry, _RELIC_DECK) if c not in held]
    next_rng(state).shuffle(cards)
    decks.relic_deck = cards
    decks.relic_discard = []
    decks.relic_deck_seeded = True


def draw_relic(state: GameState, registry: StaticDataRegistry, player_id: str) -> str | None:
    """Gracz dobiera wierzchni relikt i kładzie go przed sobą. Mutuje ``state`` (klon).

    Returns:
        Id dobranego reliktu albo ``None``, gdy talia (i stos odrzuconych) jest pusta.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    ensure_relic_deck(state, registry)
    decks = state.decks
    if not decks.relic_deck and decks.relic_discard:
        reshuffled = list(decks.relic_discard)
        next_rng(state).shuffle(reshuffled)
        decks.relic_deck = reshuffled
        decks.relic_discard = []
    if not decks.relic_deck:
        return None
    relic = decks.relic_deck.pop(0)
    player.relics = [*player.relics, relic]
    return relic
