"""Fragmenty web-data dotyczące setupu startowego (RULES.md 45).

``build_setup_payload`` zasila okno setupu na froncie (``gameState.setup``);
``custodian_on_board`` mówi, czy żeton Custodians ma być narysowany na Mecatol Rex.
Payload setupu liczony jest z pełnego stanu (projekcja czyści cudze ręce, więc z niej nie
dałoby się ustalić, kto jeszcze wybiera), a kandydatów ujawnia jednemu graczowi naraz.
"""

from __future__ import annotations

from typing import Any

from src.core import custodians, game_setup
from src.core.game_state import ControlType, GameState


def custodian_on_board(state: GameState) -> bool:
    """Czy żeton Custodians leży na Mecatol Rex.

    Leży od położenia w setupie aż do zdjęcia (``custodians_removed``). Stany bez setupu
    (testy, God-Mode, starsze migawki) traktujemy jak gotowe — żeton jest na planszy.
    """
    return custodians.on_board(state)


def build_setup_payload(
    state: GameState, viewer: str | None = None, *, own_only: bool = False
) -> dict[str, Any] | None:
    """Stan setupu dla frontu albo ``None``, gdy setup zakończony.

    Liczone z PEŁNEGO stanu (kto jeszcze wybiera — informacja jawna), ale kandydatów
    ujawnia tylko jednemu graczowi (``candidatesFor``):

    * ``own_only`` (gra sieciowa, RULES.md 44.3) — wyłącznie ``viewer`` i tylko póki sam
      jeszcze wybiera; wszyscy wybierają równocześnie;
    * inaczej (jeden ekran / host-operator) — gracz, którego kolej (``chooserId``), za bramką
      „przekaż ekran" na froncie.
    """
    setup = state.setup
    if setup is None:
        return None
    chooser = game_setup.current_chooser(state)
    pending = game_setup.pending_choosers(state)
    shown = (viewer if viewer in pending else None) if own_only else chooser
    candidates: list[str] = []
    if shown is not None:
        candidates = list(state.players[shown].private.secret_candidates)
    players = [
        {
            "id": player_id,
            "name": player.display_name or player_id,
            "color": player.color,
            "faction": player.faction,
            "isBot": player.control_type is ControlType.BOT,
            "chosen": player_id in setup.secrets_chosen,
        }
        for player_id in state.seating_order
        if (player := state.players.get(player_id)) is not None
    ]
    return {
        "stage": setup.stage.value,
        "speakerId": state.speaker_id,
        "chooserId": chooser,
        "pending": pending,
        "simultaneous": own_only,
        "candidatesFor": shown,
        "players": players,
        "candidates": candidates,
        "custodiansPlaced": setup.custodians_placed,
        "stage1Hidden": len(state.objectives.stage1_deck),
        "stage2Hidden": len(state.objectives.stage2_deck),
    }
