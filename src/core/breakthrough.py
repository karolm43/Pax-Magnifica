"""Przełom frakcji (breakthrough, Thunder's Edge) — JEDYNE miejsce odblokowania przełomu.

RULES.md 43.1a (punkty centralne) i 50: odblokowanie przełomu (``breakthrough_unlocked``) idzie
przez :func:`unlock_breakthrough` (wyjątek: God-Mode w ``core/board_edit.py``). Hook „gdy
zdobywasz przełom" (np. natychmiastowe skutki przełomu danej frakcji) dopisujemy tu raz.
Zdolności przełomów NIE są kodowane — tylko stan (odblokowany / gotowy).

Źródło reguł: ``docs/rules_tirules/R_breakthroughs.md``.
"""

from __future__ import annotations

from src.core import exhaust, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState
from src.core.models import BreakthroughDef
from src.core.registry import StaticDataRegistry


def unlock_breakthrough(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> BreakthroughDef | None:
    """Odblokowuje przełom frakcji gracza (gotowy). MUTUJE ``state`` (klon wołającego).

    Returns:
        Zdobyty przełom albo ``None``, gdy frakcja nie ma przełomu w danych albo gracz już go ma
        (nic się wtedy nie zmienia — „gain" następuje tylko raz).

    Raises:
        ValueError: Nieznany gracz.
    """
    player = state.players.get(player_id)
    if player is None:
        raise ValueError(f"Unknown player: {player_id}")
    breakthrough = registry.breakthrough_for_faction(player.faction)
    if breakthrough is None or player.breakthrough_unlocked:
        return None
    player.breakthrough_unlocked = True
    exhaust.ready_breakthrough(state, player_id)
    triggers.fire(
        state, GameEvent.COMPONENT_GAINED, Moment.WHEN, subject=player_id,
        ctx={"player": player_id, "component": f"breakthroughs:{breakthrough.id}"},
    )
    return breakthrough
