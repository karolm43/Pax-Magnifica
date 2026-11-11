"""Talia reliktów, posiadanie, wyczerpywanie i purge reliktu (RULES.md 50, 59).

Efekty konkretnych reliktów: ``core/relic_cards.py`` (ACTION) i ``core/hooks/relics_*.py``
(pasywne i zdarzeniowe). Tu tylko wspólne operacje na karcie: dobranie z talii, przekazanie
(transakcja / Shard of the Throne), purge i wyjście z gry z haczykami „gdy tracisz tę kartę".

Talia powstaje leniwie z największej talii typu ``relic`` aktywnych źródeł (jak talia agend,
``card_draw.ensure_agenda_deck``); pusta talia tasuje się ze stosu odrzuconych.
"""

from __future__ import annotations

from collections.abc import Callable

from src.core import triggers
from src.core.dice import next_rng
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

_RELIC_DECK = "relic"

# Efekt „gdy tracisz tę kartę” (Shard of the Throne: -1 VP): (stan, gracz tracący) -> None.
LostFn = Callable[[GameState, str], None]
_ON_LOST: dict[str, LostFn] = {}


def on_lost(relic_id: str) -> Callable[[LostFn], LostFn]:
    """Rejestruje efekt utraty reliktu (przekazanie lub purge). Jeden efekt na relikt."""

    def decorate(fn: LostFn) -> LostFn:
        if relic_id in _ON_LOST:
            raise ValueError(f"Loss effect already registered for {relic_id}.")
        _ON_LOST[relic_id] = fn
        return fn

    return decorate


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


def _fire_gained(state: GameState, player_id: str, relic: str) -> None:
    """„When you gain this card”: karta jest już źródłem hooka, więc może zareagować na siebie."""
    triggers.fire(
        state, GameEvent.COMPONENT_GAINED, Moment.WHEN, subject=player_id,
        ctx={"player": player_id, "component": f"relics:{relic}"},
    )


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
    _fire_gained(state, player_id, relic)
    return relic


def relic_label(relic_id: str) -> str:
    """Nazwa reliktu z katalogu do komunikatów dla gracza (id, gdy katalog niedostępny)."""
    from src.core import rules_hooks  # lokalnie: unika cyklu importów
    from src.core.components import ComponentCategory

    registry = rules_hooks.bound_registry()
    card = registry.catalog.get(ComponentCategory.RELIC, relic_id) if registry else None
    name = getattr(card, "name", None)
    return str(name) if name else relic_id


def _remove(state: GameState, player_id: str, relic_id: str) -> None:
    """Zdejmuje relikt ze strefy gracza (także ze stanu wyczerpania) i odpala efekt utraty."""
    player = state.players[player_id]
    if relic_id not in player.relics:
        raise ValueError(f"{player_id} does not have the relic {relic_label(relic_id)}.")
    player.relics = [r for r in player.relics if r != relic_id]
    player.exhausted_relics = [r for r in player.exhausted_relics if r != relic_id]
    lost = _ON_LOST.get(relic_id)
    if lost is not None:
        lost(state, player_id)


def transfer(state: GameState, giver_id: str, receiver_id: str, relic_id: str) -> None:
    """Przenosi relikt ze strefy ``giver_id`` do strefy ``receiver_id`` (mutuje).

    Dawca traci kartę (efekt utraty), odbiorca ją zdobywa (hook „when you gain”). Karta trafia
    do odbiorcy GOTOWA.

    Raises:
        ValueError: Gracz nie ma tego reliktu.
    """
    giver = state.players[giver_id]
    if relic_id not in giver.relics:
        raise ValueError(f"{giver_id} does not have the relic {relic_label(relic_id)}.")
    _remove(state, giver_id, relic_id)
    receiver = state.players[receiver_id]
    receiver.relics = [*receiver.relics, relic_id]
    _fire_gained(state, receiver_id, relic_id)


def purge_relic(state: GameState, player_id: str, relic_id: str) -> None:
    """Purge reliktu gracza: karta wychodzi z gry na stałe (nie wraca do talii ani stosu).

    Mutuje ``state``. Raises:
        ValueError: Gracz nie ma tego reliktu.
    """
    _remove(state, player_id, relic_id)
    state.decks.purged = [*state.decks.purged, relic_id]


def detach(state: GameState, player_id: str, relic_id: str) -> None:
    """Zdejmuje relikt ze strefy gracza BEZ purge (np. Nano-Forge przyczepiony do planety).

    Karta nie wraca do talii ani nie trafia do purge - wołający kładzie ją gdzie indziej.
    Efekt utraty ("gdy tracisz tę kartę") odpala się jak przy każdym zejściu ze strefy.
    """
    _remove(state, player_id, relic_id)


def is_ready(state: GameState, player_id: str, relic_id: str) -> bool:
    """Czy gracz ma relikt i nie jest on wyczerpany."""
    player = state.players.get(player_id)
    return (
        player is not None
        and relic_id in player.relics
        and relic_id not in player.exhausted_relics
    )
