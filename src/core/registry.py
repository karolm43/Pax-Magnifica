"""StaticDataRegistry — niemutowalny rejestr statycznych danych gry.

Wczytuje definicje jednostek, planet i systemów z lokalnych assetów AsyncTI4,
filtrując je po polu ``source`` względem aktywnego manifestu
(``enabled_sources.json``). Buduje mapowania identyfikatorów tekstowych na gęste
indeksy całkowitoliczbowe (pod przyszły FastState) oraz raportuje referencje do
źródeł, które nie zostały załadowane.

Filtrowanie odbywa się po POLU ``source`` wewnątrz każdego wpisu, a nie po nazwie
pliku — nazwy plików w AsyncTI4 nie odpowiadają 1:1 identyfikatorom źródeł
(np. jednostki bazowe leżą w ``baseUnits.json``, nie ``base.json``).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, TypeVar, cast

from pydantic import BaseModel

from src import config
from src.core.models import (
    AbilityDef,
    BreakthroughDef,
    FactionDef,
    LeaderDef,
    PlanetDef,
    StrategyCardDef,
    SystemDef,
    TechnologyDef,
    UnitDef,
)


class _HasId(Protocol):
    """Protokół dla modeli posiadających pole ``id``."""

    id: str


TModel = TypeVar("TModel", bound=BaseModel)


def _load_json_entries(path: Path) -> list[dict[str, object]]:
    """Wczytuje plik JSON i zwraca listę wpisów (słowników).

    Obsługuje zarówno pliki będące listą obiektów, jak i pojedynczy obiekt.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [entry for entry in raw if isinstance(entry, dict)]
    if isinstance(raw, dict):
        return [raw]
    return []


def _iter_dir_entries(directory: Path) -> Iterable[dict[str, object]]:
    """Iteruje wszystkie wpisy ze wszystkich plików ``*.json`` w katalogu."""
    for path in sorted(directory.glob("*.json")):
        yield from _load_json_entries(path)


@dataclass(frozen=True)
class RegistryReport:
    """Raport spójności po załadowaniu danych."""

    enabled_sources: list[str]
    unit_count: int
    planet_count: int
    system_count: int
    skipped_sources: dict[str, int] = field(default_factory=dict)
    """Źródła pominięte (nieaktywne) wraz z liczbą pominiętych wpisów."""

    def summary(self) -> str:
        """Czytelne podsumowanie raportu."""
        lines = [
            f"Aktywne źródła: {', '.join(self.enabled_sources)}",
            f"Jednostki:  {self.unit_count}",
            f"Planety:    {self.planet_count}",
            f"Systemy:    {self.system_count}",
        ]
        if self.skipped_sources:
            skipped = ", ".join(
                f"{src} ({cnt})" for src, cnt in sorted(self.skipped_sources.items())
            )
            lines.append(f"Pominięte źródła: {skipped}")
        return "\n".join(lines)


class StaticDataRegistry:
    """Niemutowalny rejestr statycznych danych gry dla aktywnych źródeł."""

    def __init__(self, enabled_sources: list[str] | None = None) -> None:
        self._enabled: set[str] = set(
            enabled_sources
            if enabled_sources is not None
            else config.load_enabled_sources()
        )
        self._skipped: dict[str, int] = {}

        self.units: dict[str, UnitDef] = {}
        self.planets: dict[str, PlanetDef] = {}
        self.systems: dict[str, SystemDef] = {}
        self.factions: dict[str, FactionDef] = {}
        self.strategy_cards: dict[str, StrategyCardDef] = {}
        self.leaders: dict[str, LeaderDef] = {}
        self.abilities: dict[str, AbilityDef] = {}
        self.technologies: dict[str, TechnologyDef] = {}
        self.breakthroughs: dict[str, BreakthroughDef] = {}

        # Mapowania id -> gęsty indeks int (pod FastState)
        self.unit_index: dict[str, int] = {}
        self.planet_index: dict[str, int] = {}
        self.system_index: dict[str, int] = {}

        self._load()

    # --- Ładowanie ------------------------------------------------------

    def _collect(
        self,
        entries: Iterable[dict[str, object]],
        model_cls: type[TModel],
    ) -> dict[str, TModel]:
        """Filtruje wpisy po aktywnym ``source`` i buduje słownik id -> model."""
        result: dict[str, TModel] = {}
        for entry in entries:
            source = entry.get("source")
            if not isinstance(source, str):
                continue
            if source not in self._enabled:
                self._skipped[source] = self._skipped.get(source, 0) + 1
                continue
            model = model_cls.model_validate(entry)
            entry_id = cast("_HasId", model).id
            result[entry_id] = model
        return result

    def _load(self) -> None:
        self.units = self._collect(
            _iter_dir_entries(config.UNITS_DATA_DIR), UnitDef
        )
        self.planets = self._collect(
            _iter_dir_entries(config.PLANETS_DIR), PlanetDef
        )
        self.systems = self._collect(
            _iter_dir_entries(config.SYSTEMS_DIR), SystemDef
        )
        self.factions = self._collect(
            _iter_dir_entries(config.FACTIONS_DATA_DIR), FactionDef
        )
        self.strategy_cards = self._collect(
            _iter_dir_entries(config.STRATEGY_CARDS_DIR), StrategyCardDef
        )
        self.leaders = self._collect(
            _iter_dir_entries(config.LEADERS_DATA_DIR), LeaderDef
        )
        self.abilities = self._collect(
            _iter_dir_entries(config.ABILITIES_DATA_DIR), AbilityDef
        )
        self.technologies = self._collect(
            _iter_dir_entries(config.TECHNOLOGIES_DATA_DIR), TechnologyDef
        )
        self.breakthroughs = self._collect(
            _iter_dir_entries(config.BREAKTHROUGHS_DATA_DIR), BreakthroughDef
        )

        self.unit_index = {uid: i for i, uid in enumerate(sorted(self.units))}
        self.planet_index = {pid: i for i, pid in enumerate(sorted(self.planets))}
        self.system_index = {sid: i for i, sid in enumerate(sorted(self.systems))}

    # --- Karty strategii -----------------------------------------------

    def strategy_card_set(self, set_alias: str = "pok") -> list[StrategyCardDef]:
        """Zwraca uporządkowane karty strategii wskazanego zestawu (domyślnie PoK).

        Czyta listę ``scIDs`` z ``strategyCardSets.json`` dla podanego aliasu i mapuje
        je na załadowane ``StrategyCardDef`` (po ``id``), sortując po inicjatywie.
        Pomija karty, których definicji brak w rejestrze (nieaktywne źródło).

        Returns:
            Lista ``StrategyCardDef`` posortowana rosnąco po ``initiative``. Pusta,
            gdy zestaw nie istnieje lub żadna karta nie jest załadowana.
        """
        if not config.STRATEGY_CARD_SETS_PATH.is_file():
            return []
        raw = json.loads(config.STRATEGY_CARD_SETS_PATH.read_text(encoding="utf-8"))
        sets = raw if isinstance(raw, list) else []
        sc_ids: list[str] = []
        for entry in sets:
            if isinstance(entry, dict) and entry.get("alias") == set_alias:
                ids = entry.get("scIDs")
                if isinstance(ids, list):
                    sc_ids = [sid for sid in ids if isinstance(sid, str)]
                break
        cards = [self.strategy_cards[sid] for sid in sc_ids if sid in self.strategy_cards]
        return sorted(cards, key=lambda c: c.initiative)

    # --- Walidacja spójności -------------------------------------------

    def missing_planet_references(self) -> dict[str, list[str]]:
        """Zwraca systemy odwołujące się do planet spoza załadowanego zbioru.

        Returns:
            Mapę ``{system_id: [brakujące_id_planet]}``. Pusta, gdy spójne.
        """
        missing: dict[str, list[str]] = {}
        for system in self.systems.values():
            absent = [pid for pid in system.planets if pid not in self.planets]
            if absent:
                missing[system.id] = absent
        return missing

    def report(self) -> RegistryReport:
        """Buduje raport spójności po załadowaniu."""
        return RegistryReport(
            enabled_sources=sorted(self._enabled),
            unit_count=len(self.units),
            planet_count=len(self.planets),
            system_count=len(self.systems),
            skipped_sources=dict(self._skipped),
        )


def main() -> None:
    """Punkt wejścia CLI: wypisuje statystyki załadowanego rejestru."""
    registry = StaticDataRegistry()
    print(registry.report().summary())

    missing = registry.missing_planet_references()
    if missing:
        print(f"\nUWAGA: {len(missing)} systemów ma brakujące referencje do planet:")
        for system_id, planets in sorted(missing.items())[:20]:
            print(f"  system {system_id}: {planets}")
    else:
        print("\nSpójność referencji planet: OK")


if __name__ == "__main__":
    main()
