"""Efekty trwałe z czasem trwania — JEDYNE miejsce zmiany (RULES.md 43.1a, 54).

Efekt („do końca tury”, „w tej walce”, „do końca fazy”...) żyje w
``GameState.active_effects`` i jest
źródłem hooków (``HookSource(effect, key)``), dopóki nie wygaśnie. Wygasanie robi ``triggers.fire``
na zdarzeniach kończących zakres (``triggers.EXPIRY``). Funkcje MUTUJĄ przekazany stan (klon).

Reguła (R_abilities): efekt z określonym czasem trwania zostaje, nawet gdy komponent, który go
wywołał, zniknął z gry — dlatego efekt jest osobnym wpisem, a nie flagą na komponencie.
"""

from __future__ import annotations

from typing import Any

from src.core.game_events import Duration
from src.core.game_state import ActiveEffect, GameState


def next_id(state: GameState, prefix: str) -> str:
    """Kolejny unikalny identyfikator efektu/oferty (``fx3``, ``of4``) — wspólny licznik stanu."""
    state.effect_seq += 1
    return f"{prefix}{state.effect_seq}"


def add_effect(
    state: GameState,
    key: str,
    scope: Duration,
    *,
    owner: str | None = None,
    data: dict[str, Any] | None = None,
) -> ActiveEffect:
    """Dodaje efekt trwały; ``owner=None`` = dotyczy wszystkich graczy."""
    if owner is not None and owner not in state.players:
        raise ValueError(f"Unknown player: {owner}")
    effect = ActiveEffect(
        id=next_id(state, "fx"),
        key=key,
        scope=scope.value,
        owner=owner,
        created_round=state.round_number,
        data=dict(data or {}),
    )
    state.active_effects = [*state.active_effects, effect]
    return effect


def remove_effect(state: GameState, effect_id: str) -> bool:
    """Zdejmuje efekt po id; ``False``, gdy takiego nie było."""
    kept = [e for e in state.active_effects if e.id != effect_id]
    removed = len(kept) != len(state.active_effects)
    state.active_effects = kept
    return removed


def remove_by_key(state: GameState, key: str, *, owner: str | None = None) -> int:
    """Zdejmuje wszystkie efekty o danym kluczu (opcjonalnie tylko danego właściciela)."""
    kept = [
        e
        for e in state.active_effects
        if not (e.key == key and (owner is None or e.owner == owner))
    ]
    count = len(state.active_effects) - len(kept)
    state.active_effects = kept
    return count


def rearm(state: GameState, key: str, *, owner: str, flag: str, scope: Duration) -> None:
    """Re-arms a player's effects marked as met: drops ``data[flag]`` and restores ``scope``."""
    for effect in state.active_effects:
        if effect.key == key and effect.owner == owner and effect.data.pop(flag, None):
            effect.scope = scope.value


def expire(state: GameState, scope: Duration, *, owner: str | None = None) -> list[ActiveEffect]:
    """Wygasza efekty o danym zakresie (``owner`` ogranicza do efektów tego gracza).

    Returns:
        Lista zdjętych efektów (do dziennika/hooków wygaśnięcia).
    """
    expired = [
        e
        for e in state.active_effects
        if e.scope == scope.value and (owner is None or e.owner == owner)
    ]
    if expired:
        gone = {e.id for e in expired}
        state.active_effects = [e for e in state.active_effects if e.id not in gone]
    return expired


def effects_for(state: GameState, player_id: str, key: str | None = None) -> list[ActiveEffect]:
    """Efekty dotyczące gracza (jego własne i globalne), opcjonalnie o danym kluczu."""
    return [
        e
        for e in state.active_effects
        if (e.owner is None or e.owner == player_id) and (key is None or e.key == key)
    ]


def has_effect(state: GameState, player_id: str, key: str) -> bool:
    """Czy gracza dotyczy efekt o danym kluczu."""
    return bool(effects_for(state, player_id, key))
