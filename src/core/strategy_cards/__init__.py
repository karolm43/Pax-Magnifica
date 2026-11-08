"""Karty strategii zestawu ``te`` (RULES.md 30.4): jedna karta = jeden moduł z ``SPEC``."""

from __future__ import annotations

from src.core.strategy_cards import (
    construction,
    diplomacy,
    imperial,
    leadership,
    politics,
    technology,
    trade,
    warfare,
)
from src.core.strategy_cards.base import CardSpec

# Dispatch po numerze inicjatywy. Brak wpisu = domyślny ``CardSpec()`` (brak efektu).
CARDS: dict[int, CardSpec] = {
    leadership.INITIATIVE: leadership.SPEC,
    diplomacy.INITIATIVE: diplomacy.SPEC,
    politics.INITIATIVE: politics.SPEC,
    construction.INITIATIVE: construction.SPEC,
    trade.INITIATIVE: trade.SPEC,
    warfare.INITIATIVE: warfare.SPEC,
    technology.INITIATIVE: technology.SPEC,
    imperial.INITIATIVE: imperial.SPEC,
}

__all__ = ["CARDS", "CardSpec"]
