"""Hold-rewind (RULES.md 53.7): zagranie karty reakcji W OKNIE, KTÓRE JUŻ MINĘŁO.

Gra nie czeka na reakcje (kolejka poszła dalej). Gracz z kartą reakcji (KAŻDA karta akcji z oknem
when / after / at start... poza Sabotage - ``reaction_cards.is_rewindable``) wybiera ze stosu
migawek ``EventStore`` krok, w którym chciał ją zagrać, a silnik w JEDNYM commicie cofa stan do
tej migawki (późniejsze kroki odpadają, historia się rozgałęzia) i od razu zagrywa kartę
w tamtym oknie.

ZAKAZ OSZUSTWA - cofać wolno tylko, gdy na drodze od migawki do teraźniejszości NIE nastąpiło:
rzut kośćmi, ujawnienie informacji ukrytej (talie, dobranie kart do ręki), zmiana fazy/rundy,
wcześniejszy hold-rewind lub zagranie karty (zmiana stosu odrzuconych), a od migawki nie dzieli
nas więcej niż ``MAX_REWIND_STEPS`` kroków. Test kroku: :func:`is_irreversible_step`.

Moduł jest CZYSTY (bez IO): dostaje łańcuch migawek ``(seq, label, stan)`` od najstarszej do
bieżącej; zapis historii robi ``api/state_service`` (``replace_state(branch_from=...)``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any

from src.core import action_cards, reaction_cards
from src.core.components import ActionCardDef, ComponentCategory
from src.core.game_state import GameState
from src.core.registry import StaticDataRegistry

MAX_REWIND_STEPS = 8  # decyzja użytkownika: najwyżej 8 kroków wstecz
CHAIN_LIMIT = MAX_REWIND_STEPS + 2  # tyle migawek czytamy ze stosu (+1 do wykrycia limitu)
REWIND_LABEL_PREFIX = "hold-rewind"  # etykieta zatwierdzenia po cofnięciu (zakaz kolejnego)


@dataclass(frozen=True)
class Snapshot:
    """Migawka historii: numer, etykieta zatwierdzenia i stan."""

    seq: int
    label: str
    state: GameState


@dataclass(frozen=True)
class Reachable:
    """Migawka dostępna dla cofnięcia i liczba kroków wstecz od teraźniejszości (0 = teraz)."""

    index: int
    snapshot: Snapshot
    steps_back: int


def is_irreversible_step(prev: GameState, nxt: GameState) -> str | None:
    """Powód, dla którego krok ``prev -> nxt`` blokuje cofanie za siebie (``None`` = czysty).

    Blokują: rzut kośćmi (licznik RNG / rzutów na stół), zmiana talii (dobranie, tasowanie,
    podgląd) albo stosu odrzuconych kart akcji (zagranie karty, wcześniejszy hold-rewind),
    dobranie karty do ręki, zmiana fazy lub rundy, trwający ``held_play``.
    """
    if (
        prev.rng_seed != nxt.rng_seed
        or prev.rng_counter != nxt.rng_counter
        or prev.table_roll_seq != nxt.table_roll_seq
    ):
        return "Dice were rolled"
    if prev.phase != nxt.phase or prev.round_number != nxt.round_number:
        return "The game phase changed"
    prev_decks, next_decks = prev.decks.model_dump(), nxt.decks.model_dump()
    discard = "action_card_discard"
    if any(prev_decks[key] != next_decks[key] for key in prev_decks if key != discard):
        return "A deck was drawn from or shuffled"
    for player_id, player in nxt.players.items():
        before = prev.players.get(player_id)
        if before is None:
            continue
        gained = [
            card
            for card in set(player.private.action_cards)
            if player.private.action_cards.count(card) > before.private.action_cards.count(card)
        ]
        if gained:
            return "A player drew a card"
    if prev_decks[discard] != next_decks[discard]:
        return "An action card was played"
    if prev.held_play != nxt.held_play:
        return "A played card is waiting for a response"
    return None


def reachable_snapshots(chain: Sequence[Snapshot]) -> tuple[list[Reachable], str | None]:
    """Migawki, do których wolno się cofnąć (od najnowszej = teraz do najstarszej) + powód limitu.

    ``chain`` = ostatnie migawki od najstarszej do bieżącej. Drugi element wyniku to powód,
    dla którego dalsze cofanie jest zablokowane (``None``, gdy nic nie blokuje w obrębie łańcucha).
    """
    if not chain:
        return [], None
    last = len(chain) - 1
    if chain[last].state.held_play is not None:
        return [], "A played card is waiting for a response"
    found = [Reachable(last, chain[last], 0)]
    for index in range(last - 1, -1, -1):
        steps = last - index
        if steps > MAX_REWIND_STEPS:
            return found, f"Limit of {MAX_REWIND_STEPS} steps back"
        reason = is_irreversible_step(chain[index].state, chain[index + 1].state)
        if reason is None and chain[index + 1].label.startswith(REWIND_LABEL_PREFIX):
            reason = "An earlier hold-rewind"
        if reason is not None:
            return found, reason
        found.append(Reachable(index, chain[index], steps))
    return found, None


def _future_of(chain: Sequence[Snapshot], index: int) -> GameState | None:
    """Stan tuż PO migawce (krok, który cofamy); ``None`` dla bieżącej."""
    return chain[index + 1].state if index + 1 < len(chain) else None


def _scope(chain: Sequence[Snapshot], index: int) -> Any:
    future = _future_of(chain, index)
    return reaction_cards.hindsight_scope(future) if future is not None else nullcontext()


def _cards_at(
    chain: Sequence[Snapshot],
    item: Reachable,
    registry: StaticDataRegistry,
    player_id: str,
    hand_now: Sequence[str],
) -> list[dict[str, Any]]:
    """Karty hold-rewind z ręki (teraz i w migawce) zagrywalne w migawce ``item``."""
    state = item.snapshot.state
    if player_id not in state.players:
        return []
    cards: list[dict[str, Any]] = []
    with _scope(chain, item.index):
        for row in action_cards.playability(state, registry, player_id):
            card_id = str(row["card_id"])
            if not row["playable"] or not reaction_cards.is_rewindable(registry, card_id):
                continue
            if card_id not in hand_now:
                continue
            definition = registry.catalog.get(ComponentCategory.ACTION_CARD, card_id)
            cards.append(
                {
                    "card_id": card_id,
                    "name": (definition.name if definition is not None else None) or card_id,
                    "window": (
                        definition.window
                        if isinstance(definition, ActionCardDef) and definition.window
                        else ""
                    ),
                }
            )
    return cards


def just_passed(
    chain: Sequence[Snapshot], registry: StaticDataRegistry, player_id: str
) -> dict[str, int]:
    """Karty hold-rewind grywalne w oknie, które minęło OSTATNIM krokiem: ``{card_id: seq}``.

    Okno „when another player chooses a strategy card" (Public Disgrace) itp. zamyka się samym
    krokiem rywala, więc „teraz" karta nie ma okna. Dok ręki traktuje ją jak reakcję na ten krok:
    podnosi ją i zagrywa przez hold-rewind do migawki ``seq`` (1 krok wstecz). Starsze kroki
    zostają dla przycisku Hold (:func:`candidates`).
    """
    if len(chain) < 2:
        return {}
    me_now = chain[-1].state.players.get(player_id)
    if me_now is None:
        return {}
    reach, _limit = reachable_snapshots(chain[-2:])
    previous = next((item for item in reach if item.steps_back == 1), None)
    if previous is None:
        return {}
    return {
        str(card["card_id"]): previous.snapshot.seq
        for card in _cards_at(chain[-2:], previous, registry, player_id,
                              me_now.private.action_cards)
    }


def candidates(
    chain: Sequence[Snapshot], registry: StaticDataRegistry, player_id: str
) -> tuple[list[dict[str, Any]], str | None]:
    """Kroki z kartami hold-rewind zagrywalnymi w TYM stanie: ``(kroki, limitReason)``.

    Karta musi być w ręce gracza TERAZ i w migawce. Krok = ``seq``, etykieta, runda, faza,
    ``stepsBack`` i lista kart ``{card_id, name, window}`` (od najnowszej migawki do najstarszej).
    """
    if not chain:
        return [], None
    current = chain[-1].state
    me_now = current.players.get(player_id)
    if me_now is None:
        raise ValueError(f"Unknown player: {player_id}")
    reach, limit = reachable_snapshots(chain)
    steps: list[dict[str, Any]] = []
    for item in reach:
        cards = _cards_at(chain, item, registry, player_id, me_now.private.action_cards)
        if cards:
            future = _future_of(chain, item.index)
            steps.append(
                {
                    "seq": item.snapshot.seq,
                    "label": item.snapshot.label,
                    "nextLabel": chain[item.index + 1].label if future is not None else None,
                    # Numer cofanego kroku - front opisuje go wpisem feedu Activity o tym ``seq``.
                    "nextSeq": chain[item.index + 1].seq if future is not None else None,
                    "round": item.snapshot.state.round_number,
                    "phase": item.snapshot.state.phase.name.lower(),
                    "stepsBack": item.steps_back,
                    "cards": cards,
                }
            )
    return steps, limit


def _locate(chain: Sequence[Snapshot], seq: int) -> Reachable:
    reach, limit = reachable_snapshots(chain)
    for item in reach:
        if item.snapshot.seq == seq:
            return item
    if any(snapshot.seq == seq for snapshot in chain):
        raise ValueError(f"You cannot go back to that point: {limit or 'it is out of reach'}.")
    raise ValueError("That moment is no longer in the history.")


def snapshot_state(chain: Sequence[Snapshot], seq: int) -> tuple[GameState, int]:
    """Stan migawki ``seq`` (tylko dostępnej) i jej indeks w łańcuchu - do formularza karty.

    Raises:
        ValueError: Migawka poza zasięgiem cofania (zakaz oszustwa / limit kroków).
    """
    item = _locate(chain, seq)
    return item.snapshot.state, item.index


def inputs_at(
    chain: Sequence[Snapshot], registry: StaticDataRegistry, player_id: str, card_id: str, seq: int
) -> tuple[bool, list[dict[str, Any]]]:
    """Formularz karty liczony na migawce ``seq`` (opcje z tamtego stanu)."""
    state, index = snapshot_state(chain, seq)
    _require_hand(chain, player_id, card_id)
    if index != len(chain) - 1 and not reaction_cards.is_rewindable(registry, card_id):
        raise ValueError("This card cannot be played by going back in time.")
    with _scope(chain, index):
        return action_cards.card_inputs(state, registry, player_id, card_id)


def _require_hand(chain: Sequence[Snapshot], player_id: str, card_id: str) -> None:
    current = chain[-1].state
    player = current.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    if card_id not in player.private.action_cards:
        raise ValueError(f"You do not have the action card {card_id}.")


def play_at(
    chain: Sequence[Snapshot],
    registry: StaticDataRegistry,
    player_id: str,
    card_id: str,
    seq: int,
    params: Mapping[str, Any] | None = None,
    *,
    actor_id: str | None = None,
    now: float | None = None,
) -> tuple[GameState, bool]:
    """Cofa stan do migawki ``seq`` i zagrywa tam kartę; zwraca ``(nowy stan, implemented)``.

    Wynik jest następcą migawki ``seq`` (zapis: ``replace_state(branch_from=seq)``). Zegar
    szachowy NIE cofa się (czas rzeczywisty minął). Błąd = ``ValueError`` i zero zmian.

    Raises:
        ValueError: Cofnięcie zabronione (kości, talie, faza, wcześniejszy rewind/zagranie,
            limit kroków), karta spoza ręki albo nieobsługiwana przez hold-rewind, złe parametry.
    """
    if actor_id is not None and actor_id != player_id:
        raise ValueError(f"{actor_id} cannot play a card for {player_id}.")
    if not chain:
        raise ValueError("There is no history to go back to.")
    item = _locate(chain, seq)
    _require_hand(chain, player_id, card_id)
    rewinding = item.index != len(chain) - 1
    if rewinding and not reaction_cards.is_rewindable(registry, card_id):
        raise ValueError("This card cannot be played by going back in time.")
    with _scope(chain, item.index):
        new_state, implemented = action_cards.play_action_card(
            item.snapshot.state, registry, player_id, card_id, params or {}, actor_id=actor_id,
            now=now,
        )
    new_state.clock = chain[-1].state.clock.model_copy(deep=True)
    return new_state, implemented
