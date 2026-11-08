"""Wspólne pomocnicze funkcje kart strategii (żetony dowodzenia, parsowanie payloadu)."""

from __future__ import annotations

from typing import Any

from src.core.game_state import GameState

POOLS = ("tactical", "fleet", "strategic")


def str_list(payload: dict[str, Any], key: str) -> list[str]:
    """Pobiera z payloadu listę napisów (brak klucza = pusta lista)."""
    raw = payload.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        raise ValueError(f"'{key}' must be a list of strings.")
    return list(raw)


def parse_pools(payload: dict[str, Any]) -> dict[str, int]:
    """Rozkład żetonów po pulach: ``tactical``/``fleet``/``strategic`` (liczby ≥ 0)."""
    result: dict[str, int] = {}
    for pool in POOLS:
        value = payload.get(pool, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"'{pool}' must be a non-negative integer.")
        result[pool] = value
    return result


def gainable_tokens(state: GameState, player_id: str, wanted: int) -> int:
    """Ile żetonów gracz realnie zdobędzie: nie więcej niż ma w rezerwie."""
    return max(0, min(wanted, state.players[player_id].cc_reinf))


def gain_tokens(state: GameState, player_id: str, pools: dict[str, int]) -> None:
    """Dodaje żetony do wybranych pul, zabierając je z rezerwy (mutuje klon)."""
    player = state.players[player_id]
    total = sum(pools.values())
    if total > player.cc_reinf:
        raise ValueError("Not enough command tokens in your reinforcements.")
    player.tactical_cc += pools["tactical"]
    player.fleet_cc += pools["fleet"]
    player.strategic_cc += pools["strategic"]
    player.cc_reinf -= total


def check_distribution(pools: dict[str, int], expected: int) -> None:
    """Suma rozkładu musi równać się liczbie zdobywanych żetonów."""
    if sum(pools.values()) != expected:
        raise ValueError(f"Distribute exactly {expected} command token(s) between your pools.")
