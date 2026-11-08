"""Karty strategii zestawu ``te`` (RULES.md 30.4): jedna karta = jeden moduł z ``SPEC``."""

from __future__ import annotations

from src.core.strategy_cards import leadership, trade
from src.core.strategy_cards.base import CardSpec

# Dispatch po numerze inicjatywy. Brak wpisu = domyślny ``CardSpec()`` (brak efektu).
CARDS: dict[int, CardSpec] = {
    leadership.INITIATIVE: leadership.SPEC,
    trade.INITIATIVE: trade.SPEC,
}

__all__ = ["CARDS", "CardSpec"]
