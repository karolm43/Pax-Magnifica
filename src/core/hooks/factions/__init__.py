"""Hooki frakcji — jeden moduł na frakcję (RULES.md 61, plan ``docs/PLAN_FRAKCJE.md``).

Moduł ``<frakcja>.py`` rejestruje WSZYSTKIE komponenty frakcji: zdolności, technologie frakcyjne,
liderów (efekty + warunki odblokowania), przełom, promissory note i jednostki frakcyjne z polem
``ability``. Teksty z assetów, reguła w ``docs/rules/R62.md`` zanim trafi do kodu. Nowa frakcja =
nowy moduł + import poniżej + ``tests/factions/test_<frakcja>.py``.
"""

from src.core.hooks.factions import (
    arborec,
    argent,
    cabal,
    ghost,
    hacan,
    jolnar,
    l1z1x,
    letnev,
    mentak,
    muaat,
    naalu,
    naaz,
    saar,
    sardakk,
    sol,
    titans,
    winnu,
    xxcha,
    yin,
)

__all__ = [
    "arborec", "argent", "cabal", "ghost", "hacan", "jolnar", "l1z1x", "letnev", "mentak", "muaat",
    "naalu", "naaz",
    "saar", "sardakk",
    "sol", "titans",
    "winnu", "xxcha", "yin",
]
