"""Które frakcje mają pełną implementację w silniku (moduł ``core/hooks/factions/<frakcja>.py``).

Frakcja „zrobiona” = ma własny moduł hooków (kontrakt frakcji: testy rulingów i scenariusze
``tests/factions``, strażniki ``test_ruling_coverage`` i ``test_flow_coverage``). Reszta grywalnych
frakcji działa w grze bez swoich zdolności. Lista zasila znacznik w kreatorze (tymczasowy, do
usunięcia po komplecie frakcji) i losowanie frakcji (najpierw zrobione).
"""

from __future__ import annotations

import importlib.util
import pkgutil
from functools import cache


@cache
def implemented_factions() -> frozenset[str]:
    """Identyfikatory frakcji z modułem hooków (= nazwy modułów w ``core/hooks/factions``)."""
    # Bez importu pakietu (ten rejestruje hooki wszystkich frakcji) - tylko lista modułów.
    spec = importlib.util.find_spec("src.core.hooks.factions")
    paths = list(spec.submodule_search_locations or []) if spec is not None else []
    return frozenset(m.name for m in pkgutil.iter_modules(paths) if not m.name.startswith("_"))


def is_implemented(faction_id: str) -> bool:
    return faction_id in implemented_factions()
