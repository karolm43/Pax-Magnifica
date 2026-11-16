"""Strażnik RULES.md 64.4: każdy bohater zaimplementowany w silniku ma efekt na planszy we froncie.

Lista w ``heroBoardFx.test.ts`` jest wpisana ręcznie, więc nowy bohater (np. Xxekir Grom) mógł
przejść bez przepisu w ``HERO_BOARD_FX`` - gracz widział wtedy samą scenę bez reakcji planszy.
"""

from __future__ import annotations

import re
from pathlib import Path

from src.core import rules_hooks
from src.core.registry import StaticDataRegistry

_FX = Path("frontend/src/domains/game-shell/components/KeyMoments/heroBoardFx.ts")


def test_kazdy_bohater_silnika_ma_efekt_na_planszy() -> None:
    registry = StaticDataRegistry()
    rules_hooks.bind_registry(registry)
    heroes = {
        key.removeprefix("leaders:")
        for key in rules_hooks.covered_components()
        if key.startswith("leaders:")
        and getattr(registry.leaders.get(key.removeprefix("leaders:")), "type", None) == "hero"
    }
    assert heroes, "brak bohaterów w silniku - zmienił się rejestr efektów?"
    source = _FX.read_text(encoding="utf-8")
    recipes = set(re.findall(r'^\s*"?([a-z0-9-]+)"?: \{ ', source, flags=re.MULTILINE))
    assert sorted(heroes - recipes) == []
