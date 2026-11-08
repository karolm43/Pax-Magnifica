"""Epilog gry: głosowanie nad zwycięstwem honorowym / niehonorowym.

Czyste funkcje nad ``GameState`` (``state -> state``). To reguła PROJEKTOWA (house rule),
nie reguła TI4 — patrz RULES.md (Epilog). Po zakończeniu gry (``winner_id``) pozostali
gracze głosują, czy zwycięstwo było honorowe. Głos zwycięzcy się nie liczy (nie głosuje).

⚠️ ZAŁOŻENIA (do potwierdzenia przez użytkownika):
- decyduje zwykła większość głosów; REMIS rozstrzyga głos gracza z DRUGIEGO MIEJSCA
  (najwięcej VP wśród głosujących; przy równych VP wcześniejszy przy stole),
- boty głosują automatycznie (na razie deterministyczny pseudolosowy wybór z lekkim
  przechyleniem ku „honorowe", dopóki nie ma warstwy AI).
"""

from __future__ import annotations

import zlib

from src.core.game_state import ControlType, EpilogueState, GameState

HONORABLE = "honorable"
DISHONORABLE = "dishonorable"
CHOICES = (HONORABLE, DISHONORABLE)


def voters(state: GameState) -> list[str]:
    """Gracze uprawnieni do głosu (wszyscy poza zwycięzcą), w kolejności zasiadania."""
    if state.winner_id is None:
        return []
    ordered = [p for p in state.seating_order if p in state.players]
    ordered += [p for p in state.players if p not in ordered]
    return [p for p in ordered if p != state.winner_id]


def _require_open(state: GameState) -> None:
    if state.winner_id is None:
        raise ValueError("The game has not ended yet.")


def runner_up(state: GameState) -> str | None:
    """Gracz z drugiego miejsca: najwięcej VP poza zwycięzcą (remis → wcześniej przy stole)."""
    eligible = voters(state)
    if not eligible:
        return None
    best = max(state.players[p].victory_points for p in eligible)
    return next(p for p in eligible if state.players[p].victory_points == best)


def _resolve(state: GameState, epilogue: EpilogueState, eligible: list[str]) -> None:
    """Wynik po komplecie głosów: większość, a remis rozstrzyga drugie miejsce."""
    if any(player_id not in epilogue.votes for player_id in eligible):
        return
    honorable = sum(1 for v in epilogue.votes.values() if v == HONORABLE)
    dishonorable = sum(1 for v in epilogue.votes.values() if v == DISHONORABLE)
    if honorable == dishonorable:
        second = runner_up(state)
        epilogue.result = epilogue.votes[second] if second else HONORABLE
    else:
        epilogue.result = DISHONORABLE if dishonorable > honorable else HONORABLE


def open_vote(state: GameState) -> GameState:
    """Otwiera głosowanie (idempotentnie) i oddaje głosy botów.

    Bez uprawnionych graczy (gra jednoosobowa) wynik od razu = honorowe.
    """
    _require_open(state)
    new_state = state.clone()
    if new_state.epilogue is None:
        new_state.epilogue = EpilogueState()
    epilogue = new_state.epilogue
    eligible = voters(new_state)
    for player_id in eligible:
        player = new_state.players[player_id]
        if player.control_type is ControlType.BOT and player_id not in epilogue.votes:
            epilogue.votes[player_id] = _bot_choice(new_state, player_id)
    if not eligible:
        epilogue.result = HONORABLE
    else:
        _resolve(new_state, epilogue, eligible)
    return new_state


def _bot_choice(state: GameState, player_id: str) -> str:
    """Deterministyczny głos bota (placeholder do czasu warstwy AI): ~1/3 niehonorowe."""
    key = f"{state.winner_id}:{player_id}:{state.round_number}".encode()
    return DISHONORABLE if zlib.crc32(key) % 3 == 0 else HONORABLE


def cast_vote(state: GameState, player_id: str, choice: str) -> GameState:
    """Oddaje głos gracza. Zwycięzca, nieznany gracz, powtórny głos i zły wybór → ValueError."""
    _require_open(state)
    if choice not in CHOICES:
        raise ValueError("Vote must be 'honorable' or 'dishonorable'.")
    if player_id not in state.players:
        raise ValueError(f"Unknown player: {player_id}")
    if player_id == state.winner_id:
        raise ValueError("The winner does not vote on their own victory.")
    new_state = open_vote(state)
    epilogue = new_state.epilogue
    assert epilogue is not None
    if epilogue.result is not None or player_id in epilogue.votes:
        raise ValueError("This player has already voted.")
    epilogue.votes[player_id] = choice
    _resolve(new_state, epilogue, voters(new_state))
    return new_state
