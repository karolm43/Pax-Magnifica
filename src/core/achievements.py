"""Katalog osiągnięć ekranu końcowego (``assets/config/achievements.json``).

Tytuły, progi i włączanie osiągnięć.

Jedno miejsce prawdy dla tytułów i progów (kod nie zna liczb). Opisy zdań składa
``chronicle`` / ``chronicle_awards`` z danych partii. To warstwa PREZENTACYJNA.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from src import config

ACHIEVEMENTS_PATH = config.ASSETS_DIR / "config" / "achievements.json"


@lru_cache(maxsize=1)
def catalog() -> dict[str, dict[str, Any]]:
    """Wpisy katalogu po kluczu osiągnięcia (wczytane raz na proces)."""
    raw = json.loads(ACHIEVEMENTS_PATH.read_text(encoding="utf-8"))
    return dict(raw["achievements"])


def title(key: str) -> str:
    return str(catalog()[key]["title"])


def enabled(key: str) -> bool:
    entry = catalog().get(key)
    return entry is not None and entry.get("enabled", True)


def param(key: str, name: str) -> int:
    """Próg ``name`` osiągnięcia ``key`` (KeyError, gdy brak wpisu w pliku — to błąd danych)."""
    return int(catalog()[key]["params"][name])
