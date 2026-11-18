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

# Offline'owy zrzut reguł TI4 (tirules2.com) — źródło treści przeglądarki Zasad.
RULES_DIR: Path = PROJECT_ROOT / "docs" / "rules_tirules"

DATA_DIR: Path = ASSETS_DIR / "data"
SYSTEMS_DIR: Path = ASSETS_DIR / "systems"
PLANETS_DIR: Path = ASSETS_DIR / "planets"

# Katalogi danych per-kategoria (pliki per-źródło: <source>.json)
UNITS_DATA_DIR: Path = DATA_DIR / "units"
TECHNOLOGIES_DATA_DIR: Path = DATA_DIR / "technologies"
FACTIONS_DATA_DIR: Path = DATA_DIR / "factions"

# Kolory graczy AsyncTI4 (solid / split / gradient) — pliki ``*Colors.json``.
PLAYER_COLORS_DIR: Path = DATA_DIR / "colors"
# Karty strategii (definicje kart + zestawy kart gry).
STRATEGY_CARDS_DIR: Path = DATA_DIR / "strategy_cards"
STRATEGY_CARD_SETS_PATH: Path = DATA_DIR / "strategy_card_sets" / "strategyCardSets.json"
# Liderzy frakcji (agent/commander/hero) — definicje z typem i opisem zdolności.
LEADERS_DATA_DIR: Path = DATA_DIR / "leaders"
# Zdolności frakcji (faction abilities) — definicje z nazwą i efektem.
ABILITIES_DATA_DIR: Path = DATA_DIR / "abilities"
# Przełomy (breakthroughs) frakcji — mechanika Thunder's Edge (karta per frakcja).
BREAKTHROUGHS_DATA_DIR: Path = DATA_DIR / "breakthroughs"

# Katalogi danych kategorii Katalogu_Komponentów (karty, cele, żetony, talie…).
ACTION_CARDS_DATA_DIR: Path = DATA_DIR / "action_cards"
AGENDAS_DATA_DIR: Path = DATA_DIR / "agendas"
PUBLIC_OBJECTIVES_DATA_DIR: Path = DATA_DIR / "public_objectives"
SECRET_OBJECTIVES_DATA_DIR: Path = DATA_DIR / "secret_objectives"
ATTACHMENTS_DATA_DIR: Path = DATA_DIR / "attachments"
EXPLORES_DATA_DIR: Path = DATA_DIR / "explores"
RELICS_DATA_DIR: Path = DATA_DIR / "relics"
PROMISSORY_NOTES_DATA_DIR: Path = DATA_DIR / "promissory_notes"
TOKENS_DATA_DIR: Path = DATA_DIR / "tokens"
BORDER_ANOMALIES_DATA_DIR: Path = DATA_DIR / "border_anomalies"
GALACTIC_EVENTS_DATA_DIR: Path = DATA_DIR / "galactic_events"
GENERIC_CARDS_DATA_DIR: Path = DATA_DIR / "genericcards"
DECKS_DATA_DIR: Path = DATA_DIR / "decks"

# Wersjonowane pliki konfiguracyjne audytu (baseline, wyjątki, manifest) — w repo,
# poza ``assets/`` (które jest w .gitignore).
AUDIT_DIR: Path = PROJECT_ROOT / "audit"

# Statusy implementacji efektów komponentów (Rejestr_Efektów).
EFFECTS_STATUS_PATH: Path = ASSETS_DIR / "config" / "effects_status.json"

# Kod frontendu (skanowany przez Strażnika_Lokalności i Audytora).
FRONTEND_DIR: Path = PROJECT_ROOT / "frontend"

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

# Konfiguracja silnika (limity rąk TI4 + zbiór poziomów trudności bota).
# Edytowalna bez dotykania kodu; czytana przez StaticDataRegistry. Zasada projektu:
# limity rąk to reguły TI4 (źródło: docs/RULES.md 36), a nie wartości z pamięci;
# zbiór poziomów trudności to ⚠️ ZAŁOŻENIE (koncepcja warstwy AI, nie reguła TI4).
ENGINE_CONFIG_PATH: Path = ASSETS_DIR / "config" / "engine_config.json"

# Moduły wariantów gry (fanowskie talie, erraty, własne komponenty) - core/variants.py,
# instrukcja: docs/WARIANTY.md.
VARIANTS_PATH: Path = ASSETS_DIR / "config" / "variants.json"


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
            f"Missing active sources manifest: {ENABLED_SOURCES_PATH}"
        )

    raw = json.loads(ENABLED_SOURCES_PATH.read_text(encoding="utf-8"))

    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(
            f"{ENABLED_SOURCES_PATH} must contain a list of strings (source identifiers)."
        )

    return raw
