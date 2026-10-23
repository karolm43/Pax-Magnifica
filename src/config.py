"""Scentralizowana konfiguracja ścieżek do assetów i aktywnych źródeł danych.

Zgodnie ze specyfikacją (sekcja 5.1) żadne dane gry nie są hardkodowane w logice.
Wszystkie ścieżki do plików danych są zdefiniowane tutaj, a lista aktywnych
źródeł jest trzymana w edytowalnym pliku ``assets/enabled_sources.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

# --- Korzeń projektu i katalogi assetów ---------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
ASSETS_DIR: Path = PROJECT_ROOT / "assets"

DATA_DIR: Path = ASSETS_DIR / "data"
SYSTEMS_DIR: Path = ASSETS_DIR / "systems"
PLANETS_DIR: Path = ASSETS_DIR / "planets"

# Katalogi danych per-kategoria (pliki per-źródło: <source>.json)
UNITS_DATA_DIR: Path = DATA_DIR / "units"
TECHNOLOGIES_DATA_DIR: Path = DATA_DIR / "technologies"
FACTIONS_DATA_DIR: Path = DATA_DIR / "factions"
# Karty strategii (definicje kart + zestawy kart gry).
STRATEGY_CARDS_DIR: Path = DATA_DIR / "strategy_cards"
STRATEGY_CARD_SETS_PATH: Path = DATA_DIR / "strategy_card_sets" / "strategyCardSets.json"
# Liderzy frakcji (agent/commander/hero) — definicje z typem i opisem zdolności.
LEADERS_DATA_DIR: Path = DATA_DIR / "leaders"
# Zdolności frakcji (faction abilities) — definicje z nazwą i efektem.
ABILITIES_DATA_DIR: Path = DATA_DIR / "abilities"
# Przełomy (breakthroughs) frakcji — mechanika Thunder's Edge (karta per frakcja).
BREAKTHROUGHS_DATA_DIR: Path = DATA_DIR / "breakthroughs"

# Grafiki kafelków mapy (poza repo — .gitignore; serwowane lokalnie z dysku).
TILES_DIR: Path = ASSETS_DIR / "tiles"

# Alias pozycji AsyncTI4 (autorytatywne mapowanie pozycja RPP -> axial TTPG).
POSITION_ALIAS_PATH: Path = ASSETS_DIR / "alias" / "position_alias.properties"

# Podścieżka URL, pod którą warstwa API serwuje assety (StaticFiles).
STATIC_URL_PREFIX: str = "/static"

# Pliki pojedyncze
SOURCES_PATH: Path = DATA_DIR / "sources" / "sources.json"

# Manifest aktywnych źródeł (edytowalny bez dotykania kodu)
ENABLED_SOURCES_PATH: Path = ASSETS_DIR / "enabled_sources.json"


# --- Ładowanie manifestu aktywnych źródeł -------------------------------


def load_enabled_sources() -> list[str]:
    """Wczytuje listę aktywnych źródeł z ``enabled_sources.json``.

    Returns:
        Lista identyfikatorów źródeł (np. ``["base", "pok", ...]``).

    Raises:
        FileNotFoundError: Gdy plik manifestu nie istnieje.
        ValueError: Gdy zawartość nie jest listą napisów.
    """
    if not ENABLED_SOURCES_PATH.is_file():
        raise FileNotFoundError(
            f"Brak manifestu aktywnych źródeł: {ENABLED_SOURCES_PATH}"
        )

    raw = json.loads(ENABLED_SOURCES_PATH.read_text(encoding="utf-8"))

    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(
            f"{ENABLED_SOURCES_PATH} musi zawierać listę napisów (identyfikatorów źródeł)."
        )

    return raw
