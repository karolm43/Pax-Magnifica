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
from src.core import rules_hooks
from src.core.component_loader import LoadReport, load_components
from src.core.components import ComponentCatalog, build_timing_specs
from src.core.effects_registry import EffectRegistry
from src.core.models import (
    AbilityDef,
    BreakthroughDef,
    EngineConfig,
    FactionDef,
    HandLimits,
    LeaderDef,
    PlanetDef,
    StrategyCardDef,
    SystemDef,
    TechnologyDef,
    UnitDef,
)
from src.core.references import (
    ReferenceReport,
    UnresolvedReference,
    build_reference_report,
    find_unresolved_references,
)
from src.core.rules_links import RulesTopicIndex
from src.core.sources import SOURCE_PRIORITY, known_source_ids, validate_enabled_sources


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
            f"Active sources: {', '.join(self.enabled_sources)}",
            f"Units:      {self.unit_count}",
            f"Planets:    {self.planet_count}",
            f"Systems:    {self.system_count}",
        ]
        if self.skipped_sources:
            skipped = ", ".join(
                f"{src} ({cnt})" for src, cnt in sorted(self.skipped_sources.items())
            )
            lines.append(f"Skipped sources: {skipped}")
        return "\n".join(lines)


class StaticDataRegistry:
    """Niemutowalny rejestr statycznych danych gry dla aktywnych źródeł."""

    def __init__(self, enabled_sources: list[str] | None = None) -> None:
        self._enabled: set[str] = set(
            enabled_sources
            if enabled_sources is not None
            else config.load_enabled_sources()
        )
        # Nieznane identyfikatory źródeł to błąd konfiguracji — przerywamy przed _load().
        validate_enabled_sources(self._enabled, known_source_ids())
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

        # Katalog_Komponentów (nowe kategorie: karty, cele, żetony, talie…) i raport
        # jego ładowania. Budowane w _load() z load_components (design: R4.1, R5.1).
        self.catalog: ComponentCatalog = ComponentCatalog({})
        self.load_report: LoadReport = LoadReport()
        # Raport spójności referencji (frakcje, talie, eksploracje, żetony, planety).
        # Budowany w _load() po złożeniu katalogu — patrz core/references.py (R7).
        self.reference_report: ReferenceReport = ReferenceReport()
        # Kolizje id w 9 STARYCH kategoriach: kategoria -> posortowane id, które
        # wystąpiły w wielu aktywnych wpisach. Tylko RAPORT (D9) — zachowanie
        # „ostatni wpis wygrywa" pozostaje bez zmian, by uniknąć regresji.
        self.legacy_id_collisions: dict[str, list[str]] = {}

        # Konfiguracja silnika (limity rąk TI4 + zbiór poziomów trudności bota).
        # Ładowana z assetów (NIE hardkodowana) — patrz docs/RULES.md 36.
        self.engine_config: EngineConfig = EngineConfig()

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
        label: str | None = None,
    ) -> dict[str, TModel]:
        """Filtruje wpisy po aktywnym ``source`` i buduje słownik id -> model.

        Gdy podano ``label``, kolizje ``id`` między aktywnymi wpisami są tylko
        raportowane w ``legacy_id_collisions`` (D9); wygrywa ostatni wpis jak dotąd.
        """
        result: dict[str, TModel] = {}
        collided: set[str] = set()
        for entry in entries:
            source = entry.get("source")
            if not isinstance(source, str):
                continue
            if source not in self._enabled:
                self._skipped[source] = self._skipped.get(source, 0) + 1
                continue
            model = model_cls.model_validate(entry)
            entry_id = cast("_HasId", model).id
            if entry_id in result:
                collided.add(entry_id)
            result[entry_id] = model
        if label is not None and collided:
            self.legacy_id_collisions[label] = sorted(collided)
        return result

    def _load(self) -> None:
        self.units = self._collect(
            _iter_dir_entries(config.UNITS_DATA_DIR), UnitDef, "units"
        )
        self.planets = self._collect(
            _iter_dir_entries(config.PLANETS_DIR), PlanetDef, "planets"
        )
        self.systems = self._collect(
            _iter_dir_entries(config.SYSTEMS_DIR), SystemDef, "systems"
        )
        self.factions = self._collect(
            _iter_dir_entries(config.FACTIONS_DATA_DIR), FactionDef, "factions"
        )
        self.strategy_cards = self._collect(
            _iter_dir_entries(config.STRATEGY_CARDS_DIR), StrategyCardDef,
            "strategy_cards",
        )
        self.leaders = self._collect(
            _iter_dir_entries(config.LEADERS_DATA_DIR), LeaderDef, "leaders"
        )
        self.abilities = self._collect(
            _iter_dir_entries(config.ABILITIES_DATA_DIR), AbilityDef, "abilities"
        )
        self.technologies = self._collect(
            _iter_dir_entries(config.TECHNOLOGIES_DATA_DIR), TechnologyDef,
            "technologies",
        )
        self.breakthroughs = self._collect(
            _iter_dir_entries(config.BREAKTHROUGHS_DATA_DIR), BreakthroughDef,
            "breakthroughs",
        )

        self._apply_thunders_edge_breakthrough_techs()

        # Katalog_Komponentów: nowe kategorie przez czysty loader (filtr po source,
        # deterministyczny wybór przy kolizji id — D9). Specyfikacje czasowe budujemy
        # z kart akcji, zdolności frakcji i liderów (R8.2).
        tables, self.load_report = load_components(self._enabled)
        timing_specs = build_timing_specs(
            tables, leaders=self.leaders, abilities=self.abilities
        )
        # Rejestr efektów (status implementacji per komponent; brak pliku = pusty,
        # R9.4) oraz indeks tematów zrzutu reguł (brak tirules.json = pusty, R10.2).
        # Oba są opcjonalne i wczytywane z lokalnych assetów — nic nie jest w kodzie.
        # Efekty z zarejestrowanym hookiem (core/rules_hooks.py, ``covers``) są IMPLEMENTED;
        # jawne wpisy z pliku mają pierwszeństwo.
        self.effect_registry: EffectRegistry = EffectRegistry.load().with_hook_coverage(
            rules_hooks.covered_components()
        )
        self.rules_index: RulesTopicIndex = RulesTopicIndex.from_json()

        # Słowniki kategorii spoza katalogu (frakcje, liderzy, zdolności, technologie,
        # jednostki, przełomy) przekazujemy do katalogu, by faction_bundle mógł złożyć
        # paczkę frakcji w jednym wywołaniu (R5.6), wyłącznie z list FactionDef. Wpięty
        # rejestr efektów i indeks reguł udostępniają catalog.effect_status i
        # catalog.rules_topics (R9.3, R10.1).
        self.catalog = ComponentCatalog(
            tables,
            timing_specs,
            factions=self.factions,
            leaders=self.leaders,
            abilities=self.abilities,
            technologies=self.technologies,
            units=self.units,
            breakthroughs=self.breakthroughs,
            effect_registry=self.effect_registry,
            rules_index=self.rules_index,
        )

        # Spójność referencji (R7): po złożeniu katalogu, bo sprawdzamy m.in. talie,
        # eksploracje i żetony. Nierozwiązane referencje NIE blokują startu (dane są
        # lokalne, God-Mode ma działać); Audytor_Danych zgłasza je i ustawia kod ≠ 0.
        self.reference_report = build_reference_report(self)

        self.engine_config = self._load_engine_config()

        self.unit_index = {uid: i for i, uid in enumerate(sorted(self.units))}
        self.planet_index = {pid: i for i, pid in enumerate(sorted(self.planets))}
        self.system_index = {sid: i for i, sid in enumerate(sorted(self.systems))}

    # --- Rodzina frakcji i przełomy (Thunder's Edge) --------------------

    @staticmethod
    def faction_family(faction: FactionDef) -> str:
        """Klucz „rodziny" frakcji: ``shortName`` z danych (małe litery) lub id.

        Warianty jednej frakcji (Keleres: keleresm/keleresx/keleresa) dzielą
        ``shortName``, a karty (przełom, technologie, liderzy) są przypisane do
        rodziny (``faction="keleres"``), nie do id wariantu.
        """
        return (faction.short_name or faction.id).lower()

    def breakthrough_for_faction(self, faction_id: str | None) -> BreakthroughDef | None:
        """Przełom frakcji (TE) — dopasowanie po id wariantu LUB po jego rodzinie."""
        if faction_id is None:
            return None
        faction = self.factions.get(faction_id)
        keys = {faction_id}
        if faction is not None:
            keys.add(self.faction_family(faction))
        return next(
            (bt for bt in self.breakthroughs.values() if bt.faction in keys), None
        )

    def _apply_thunders_edge_breakthrough_techs(self) -> None:
        """Przy włączonym TE zamienia technologię frakcyjną na jej przełom.

        W Thunder's Edge część technologii frakcyjnych została zastąpiona przełomem
        (Keleres: technologia „I.I.H.Q. Modernization" → przełom o tej samej nazwie)
        i dostała nowe technologie z TE (Keleres: „Executive Order"). Reguła z danych,
        bez listy frakcji: dla frakcji z przełomem TE usuwamy z ``factionTech``
        technologię o nazwie równej nazwie przełomu, a w jej miejsce dodajemy
        technologie ``thunders_edge`` tej rodziny frakcji, których jeszcze brak.
        Frakcje bez takiego zbiegu nazw pozostają bez zmian.
        """
        if "thunders_edge" not in self._enabled:
            return
        for faction_id, faction in list(self.factions.items()):
            breakthrough = self.breakthrough_for_faction(faction_id)
            if breakthrough is None or breakthrough.source != "thunders_edge":
                continue
            replaced = [
                t
                for t in faction.faction_tech
                if t in self.technologies
                and self.technologies[t].name == breakthrough.name
            ]
            if not replaced:
                continue
            family = self.faction_family(faction)
            kept = [t for t in faction.faction_tech if t not in replaced]
            added = [
                t.id
                for t in self.technologies.values()
                if t.source == "thunders_edge"
                and t.faction == family
                and t.id not in kept
            ]
            self.factions[faction_id] = faction.model_copy(
                update={"faction_tech": added + kept}
            )

    @staticmethod
    def _load_engine_config() -> EngineConfig:
        """Wczytuje konfigurację silnika z ``engine_config.json``.

        Gdy plik nie istnieje, zwraca domyślną (pustą) konfigurację — dzięki temu
        rejestr działa też bez pliku (limity ``None`` = brak kapu, zbiór trudności
        pusty). Zasada projektu: limity rąk i zbiór trudności NIE są hardkodowane
        w logice, tylko czytane stąd (patrz docs/RULES.md 36).
        """
        if not config.ENGINE_CONFIG_PATH.is_file():
            return EngineConfig()
        raw = json.loads(config.ENGINE_CONFIG_PATH.read_text(encoding="utf-8"))
        return EngineConfig.model_validate(raw)

    # --- Konfiguracja silnika (limity rąk, poziomy trudności) ----------

    def hand_limits(self) -> HandLimits:
        """Limity rozmiarów rąk gracza (reguły TI4; docs/RULES.md 36).

        ``None`` dla danej ręki = brak górnego limitu. Czytane z assetów, nie
        hardkodowane — warstwa setup/``core`` używa tych wartości do walidacji.
        """
        return self.engine_config.hand_limits

    def valid_difficulties(self) -> frozenset[str]:
        """Dozwolony, skończony zbiór poziomów trudności bota (R1.8).

        ⚠️ ZAŁOŻENIE — poziomy trudności nie są regułą TI4 (to koncepcja warstwy AI),
        więc zbiór jest wartością konfigurowalną czytaną z ``engine_config.json``,
        a nie stałą w kodzie. Patrz docs/RULES.md 36.
        """
        return frozenset(self.engine_config.valid_difficulties)

    def valid_personalities(self) -> frozenset[str]:
        """Dozwolony zbiór osobowości bota (⚠️ ZAŁOŻENIE) — z ``engine_config.json``."""
        return frozenset(self.engine_config.valid_personalities)

    # --- Karty strategii -----------------------------------------------

    # Priorytet źródeł STANDARDOWEGO zestawu kart strategii (najwyższy → najniższy).
    # Reguła wyboru wariantu: przy wielu włączonych źródłach obowiązuje zestaw
    # najwyższego z tej listy — Thunder's Edge nadpisuje PoK (Construction/Warfare),
    # PoK nadpisuje erraty Codex, te nadpisują zestaw bazowy. Źródła spoza tej listy
    # (homebrew: anarchy, luminous, tispoon…) są IGNOROWANE przy wyborze kanonicznym,
    # by nie nadpisały standardowego zestawu. Reguła: RULES.md 14,
    # ``active_strategy_card_set_alias``.
    _STRATEGY_SET_SOURCE_PRIORITY: tuple[str, ...] = SOURCE_PRIORITY

    def _read_strategy_card_sets(self) -> list[dict[str, object]]:
        """Wczytuje surowe definicje zestawów z ``strategyCardSets.json``.

        Zwraca listę słowników (każdy z polami ``alias``, ``scIDs``, ``source``).
        Pusta, gdy plik nie istnieje lub ma nieoczekiwany kształt.
        """
        if not config.STRATEGY_CARD_SETS_PATH.is_file():
            return []
        raw = json.loads(config.STRATEGY_CARD_SETS_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        return [entry for entry in raw if isinstance(entry, dict)]

    def active_strategy_card_set_alias(self) -> str:
        """Wybiera alias KANONICZNEGO zestawu kart strategii wg włączonych źródeł.

        Reguła (RULES.md 14): spośród zestawów z ``strategyCardSets.json``, których
        pole ``source`` jest zarazem WŁĄCZONE (``self._enabled``) i figuruje na liście
        priorytetu ``_STRATEGY_SET_SOURCE_PRIORITY``, bierzemy ten o NAJWYŻSZYM
        priorytecie źródła. Dzięki temu przy włączonym Thunder's Edge obowiązuje
        zestaw ``te`` (Construction=te4construction, Warfare=te6warfare), a bez niego
        — ``pok``, itd. w dół do ``base``.

        Źródła spoza listy priorytetu (homebrew) są IGNOROWANE — nie chcemy, by np.
        anarchy/luminous nadpisały standardowy zestaw. Gdy żaden standardowy zestaw
        nie pasuje (same homebrew lub puste źródła), zwracamy bezpieczny domyślny
        ``"pok"``.

        Returns:
            Alias zestawu (np. ``"te"``, ``"pok"``, ``"base_game"``). Fallback ``"pok"``.
        """
        sets = self._read_strategy_card_sets()
        # Mapa source -> alias dla STANDARDOWYCH zestawów (po pierwszym trafieniu).
        alias_by_source: dict[str, str] = {}
        for entry in sets:
            source = entry.get("source")
            alias = entry.get("alias")
            if not isinstance(source, str) or not isinstance(alias, str):
                continue
            if source not in self._STRATEGY_SET_SOURCE_PRIORITY:
                continue  # homebrew — pomijamy przy wyborze kanonicznym
            alias_by_source.setdefault(source, alias)
        # Wybór najwyższego priorytetu, który jest włączony i ma zestaw.
        for source in self._STRATEGY_SET_SOURCE_PRIORITY:
            if source in self._enabled and source in alias_by_source:
                return alias_by_source[source]
        return "pok"

    def strategy_card_set(self, set_alias: str | None = None) -> list[StrategyCardDef]:
        """Zwraca uporządkowane karty strategii wskazanego lub KANONICZNEGO zestawu.

        Gdy ``set_alias is None`` (domyślnie), wybiera zestaw kanoniczny wg włączonych
        źródeł przez ``active_strategy_card_set_alias`` (RULES.md 14) — przy włączonym
        Thunder's Edge to ``te`` (te4construction/te6warfare), inaczej ``pok`` itd.
        Jawny alias (dla testów/kompatybilności) wymusza konkretny zestaw.

        Czyta listę ``scIDs`` z ``strategyCardSets.json`` dla aliasu i mapuje je na
        załadowane ``StrategyCardDef`` (po ``id``), sortując po inicjatywie. Pomija
        karty, których definicji brak w rejestrze (nieaktywne źródło).

        Returns:
            Lista ``StrategyCardDef`` posortowana rosnąco po ``initiative``. Pusta,
            gdy zestaw nie istnieje lub żadna karta nie jest załadowana.
        """
        if set_alias is None:
            set_alias = self.active_strategy_card_set_alias()
        sets = self._read_strategy_card_sets()
        sc_ids: list[str] = []
        for entry in sets:
            if entry.get("alias") == set_alias:
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

    def unresolved_references(self) -> list[UnresolvedReference]:
        """Nierozwiązane (lub przeciekające) referencje między danymi (R7.1-7.6).

        Szablony ``<color>`` (promissory notes) nie są tu liczone — pełny raport,
        w tym szablony, trzyma ``self.reference_report``.
        """
        return find_unresolved_references(self)

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
        print(f"\nWARNING: {len(missing)} systems have missing planet references:")
        for system_id, planets in sorted(missing.items())[:20]:
            print(f"  system {system_id}: {planets}")
    else:
        print("\nPlanet reference consistency: OK")


if __name__ == "__main__":
    main()
