"""Hooki reguł pogrupowane tematycznie (RULES.md 43.1 pkt 12).

Import tego pakietu rejestruje wszystkie hooki w ``core.rules_hooks`` (efekt uboczny importu —
robi to leniwie ``rules_hooks``). Nowy temat = nowy moduł + jedna linia importu poniżej.
"""

from src.core.hooks import action_cards, factions_base, technologies

__all__ = ["action_cards", "factions_base", "technologies"]
