"""Undo gracza (RULES.md 44.7): cofnięcie WŁASNEGO ostatniego kroku, nie tylko przez hosta.

Host ma pełne Undo/Redo historii (God-Mode). Gracz cofa wyłącznie swój ostatni krok, po jednym,
i tylko dopóki cofnięcie niczego nie zdradza ani nie odbiera innym:

* krok wykonało żądanie TEGO gracza (``author`` migawki; bot / host / operacja techniczna = nie);
* od tamtej chwili nie działał nikt inny (każdy cudzy krok zamyka drogę wstecz);
* krok jest odwracalny jak przy hold-rewind (``hold_rewind.is_irreversible_step``): bez rzutu
  kośćmi, dobrania / tasowania talii, dobrania karty do ręki, zmiany fazy lub rundy, zagrania karty
  akcji, okna hold-play;
* tura nie przeszła na innego gracza (koniec tury, pas, wybór karty strategii...);
* krok nie zmienił stanu innego gracza (transakcja, przejęcie jego planety, zniszczenie jego
  jednostek...) - tego gracz nie cofa sam;
* krok nie otworzył pauzy ochronnej ani nie trafił w trwającą (inni mogą właśnie reagować).

Cofnięcie = nowa migawka będąca kopią stanu sprzed kroku (``replace_state(branch_from=...)``),
z zegarem szachowym z teraźniejszości (czas rzeczywisty minął). Migawki cofnięcia
(``UNDO_LABEL_PREFIX``) są przezroczyste: kolejne Undo sięga do kroku przed nimi, więc gracz może
cofać się krok po kroku przez całą swoją serię odwracalnych kroków w tej turze.
Presence snapshots (``reaction_prefs.PRESENCE_LABEL``, "I'm back" bookkeeping written by the HTTP
middleware for ANY player's request) are transparent too, whoever wrote them: they record no game
step, so another player's click does not close the way back. Presence itself is carried forward
into the restored state, like the clock.

Moduł jest CZYSTY: dostaje łańcuch ``(seq, label, author, stan)`` od najstarszej do bieżącej.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.core import hold_rewind, reaction_prefs
from src.core.game_state import GameState

UNDO_LABEL_PREFIX = "player-undo"
CHAIN_LIMIT = 24  # ile migawek czytamy (seria cofnięć + krok do cofnięcia z zapasem)
# Kroki techniczne / systemowe, których gracz nigdy nie cofa (nawet gdy padły w jego żądaniu).
_BLOCKED_PREFIXES = (
    "initial",
    "game:new",
    "setup",
    "god-mode",
    "replace",
    "hold-rewind",
    "reaction-pause",
    "clock:",
)


@dataclass(frozen=True)
class Step:
    """Migawka historii z autorem kroku, który do niej doprowadził."""

    seq: int
    label: str
    author: str | None
    state: GameState


@dataclass(frozen=True)
class UndoTarget:
    """Wynik oceny: do której migawki wolno się cofnąć (``seq``) albo dlaczego nie."""

    seq: int | None
    label: str | None = None  # etykieta cofanego kroku
    undone_seq: int | None = None  # numer cofanego kroku (opis z feedu Activity)
    reason: str | None = None


def batch_tag(label: str) -> str | None:
    """Flight-plan tag of a move snapshot (``tactical:move:<from>:b<n>``), else ``None``."""
    parts = label.split(":")
    if parts[:2] != ["tactical", "move"] or len(parts) < 4 or not parts[3].startswith("b"):
        return None
    return parts[3]


def _others_changed(prev: GameState, nxt: GameState, player_id: str) -> bool:
    ids = (set(prev.players) | set(nxt.players)) - {player_id}
    for pid in ids:
        before, after = prev.players.get(pid), nxt.players.get(pid)
        if before is None or after is None or before.model_dump() != after.model_dump():
            return True
    return False


def step_block_reason(prev: GameState, step: Step, player_id: str) -> str | None:
    """Dlaczego gracz NIE może cofnąć kroku ``prev -> step`` (``None`` = może)."""
    nxt = step.state
    if step.label.startswith(_BLOCKED_PREFIXES):
        return "The last change was not one of your moves"
    if step.author != player_id:
        return "Another player has acted since"
    reason = hold_rewind.is_irreversible_step(prev, nxt)
    if reason is not None:
        return reason
    if prev.active_player_id != nxt.active_player_id:
        return "The turn has passed to another player"
    if _others_changed(prev, nxt, player_id):
        return "It affected another player"
    if nxt.reaction_pause is not None or prev.reaction_pause != nxt.reaction_pause:
        return "Other players may be reacting to it"
    return None


def undo_target(chain: Sequence[Step], player_id: str) -> UndoTarget:
    """Ocena Undo gracza: migawka sprzed jego ostatniego (nie-cofnięciowego) kroku albo powód.

    Migawki cofnięć (``UNDO_LABEL_PREFIX``) tego gracza są przezroczyste - liczy się krok przed
    nimi. Cofnięcie cudzego Undo nie wchodzi w grę (autor inny = cudzy krok).
    """
    if not chain:
        return UndoTarget(None, reason="There is no history")
    current = chain[-1].state
    if player_id not in current.players:
        return UndoTarget(None, reason=f"Unknown player: {player_id}")
    if current.held_play is not None:
        return UndoTarget(None, reason="A played card is waiting for a response")
    if current.reaction_pause is not None:
        return UndoTarget(None, reason="Other players may be reacting")
    index = len(chain) - 1
    while index > 0:
        label = chain[index].label
        if label == reaction_prefs.PRESENCE_LABEL:
            index -= 1
            continue
        if not label.startswith(UNDO_LABEL_PREFIX):
            break
        if chain[index].author != player_id:
            return UndoTarget(None, reason="Another player has acted since")
        index -= 1
    if index == 0:
        return UndoTarget(None, reason="Nothing of yours to undo")
    # A flight plan (RULES.md 32.4) is one declaration committed as several leg snapshots
    # sharing a batch tag - undo it as a whole: step back to the snapshot before its first leg.
    tag = batch_tag(chain[index].label)
    first = index
    while (
        tag is not None
        and first > 1
        and batch_tag(chain[first - 1].label) == tag
        and chain[first - 1].author == chain[index].author
    ):
        first -= 1
    step, prev = chain[index], chain[first - 1]
    reason = step_block_reason(prev.state, step, player_id)
    if reason is not None:
        return UndoTarget(None, label=step.label, undone_seq=step.seq, reason=reason)
    return UndoTarget(prev.seq, label=step.label, undone_seq=step.seq)


def undo(chain: Sequence[Step], player_id: str) -> tuple[GameState, int, str]:
    """Stan po cofnięciu, migawka ``branch_from`` i etykieta zatwierdzenia.

    Raises:
        ValueError: Cofnięcie niedozwolone (powód w komunikacie).
    """
    target = undo_target(chain, player_id)
    if target.seq is None:
        raise ValueError(f"You cannot undo: {target.reason}.")
    restored = next(step.state for step in chain if step.seq == target.seq).clone()
    restored.clock = chain[-1].state.clock.model_copy(deep=True)
    reaction_prefs.carry_presence(restored, chain[-1].state)
    label = f"{UNDO_LABEL_PREFIX}:{player_id}:{target.label}"
    return restored, target.seq, label
