"""Karty strategii zestawu ``te`` (RULES.md 30.4): jedna karta = jeden moduł z ``SPEC``."""

from __future__ import annotations

from src.core.strategy_cards import diplomacy, imperial, leadership, politics, trade
from src.core.strategy_cards.base import CardSpec

# Dispatch po numerze inicjatywy. Brak wpisu = domyślny ``CardSpec()`` (brak efektu).
CARDS: dict[int, CardSpec] = {
    leadership.INITIATIVE: leadership.SPEC,
    diplomacy.INITIATIVE: diplomacy.SPEC,
    politics.INITIATIVE: politics.SPEC,
    trade.INITIATIVE: trade.SPEC,
    imperial.INITIATIVE: imperial.SPEC,
}

__all__ = ["CARDS", "CardSpec"]
