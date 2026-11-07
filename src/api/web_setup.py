"""Fragmenty web-data dotyczące setupu startowego (RULES.md 45).

``build_setup_payload`` zasila okno setupu na froncie (``gameState.setup``);
``custodian_on_board`` mówi, czy żeton Custodians ma być narysowany na Mecatol Rex.
Dokument web-data jest budowany z PROJEKCJI stanu, więc kandydaci na tajne cele widoczni
są tylko dla gracza patrzącego (aktywny = ten, kto wybiera).
"""

from __future__ import annotations

from typing import Any

from src.core import game_setup
from src.core.game_state import ControlType, GameState


def custodian_on_board(state: GameState) -> bool:
    """Czy żeton Custodians leży na Mecatol Rex.

    Leży od położenia w setupie aż do zdjęcia (``custodians_removed``). Stany bez setupu
    (testy, God-Mode, starsze migawki) traktujemy jak gotowe — żeton jest na planszy.
    """
    if state.custodians_removed:
        return False
    return state.setup is None or state.setup.custodians_placed


def build_setup_payload(state: GameState) -> dict[str, Any] | None:
    """Stan setupu dla frontu albo ``None``, gdy setup zakończony."""
    setup = state.setup
    if setup is None:
        return None
    chooser = game_setup.current_chooser(state)
    candidates: list[str] = []
    if chooser is not None:
        candidates = list(state.players[chooser].private.secret_candidates)
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
        "players": players,
        "candidates": candidates,
        "custodiansPlaced": setup.custodians_placed,
        "stage1Hidden": len(state.objectives.stage1_deck),
        "stage2Hidden": len(state.objectives.stage2_deck),
    }
