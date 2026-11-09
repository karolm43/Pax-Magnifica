"""Hooki reguł pogrupowane tematycznie (RULES.md 43.1 pkt 12).

Import tego pakietu rejestruje wszystkie hooki i efekty w ``core.rules_hooks`` (efekt uboczny
importu - robi to leniwie ``rules_hooks``). Nowy temat = nowy moduł + wpis w importach poniżej.
"""

from src.core.hooks import (
    action_card_inputs,
    action_cards,
    action_cards_other,
    action_cards_units,
    factions_base,
    technologies,
    technologies_choices,
    technologies_combat,
    technologies_passive,
)

__all__ = [
    "action_card_inputs",
    "action_cards",
    "action_cards_other",
    "action_cards_units",
    "factions_base",
    "technologies",
    "technologies_choices",
    "technologies_combat",
    "technologies_passive",
]
