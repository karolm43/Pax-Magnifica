"""Modele domenowe Pydantic v2 dla statycznych encji gry.

Modele celowo opisują wyłącznie pola istotne dla logiki silnika. Pliki JSON
AsyncTI4 zawierają również wiele pól wizualnych (pozycje tokenów, ścieżki
obrazów, układy planet), które są ignorowane dzięki ``extra="ignore"``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StaticModel(BaseModel):
    """Baza dla modeli statycznych: ignoruje nadmiarowe pola z JSON."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class UnitDef(_StaticModel):
    """Definicja typu jednostki (statystyki bojowe, ruch, pojemność)."""

    id: str
    base_type: str = Field(alias="baseType")
    async_id: str | None = Field(default=None, alias="asyncId")
    name: str
    source: str
    # Frakcja właściciela jednostki (np. "sol" dla Advanced Carrier II). None =
    # jednostka generyczna. Pozwala jednoznacznie dopasować wariant frakcyjny bez
    # polegania na prefiksie id (który kolidował — Bug 10).
    faction: str | None = None

    cost: float | None = None
    move_value: int | None = Field(default=None, alias="moveValue")
    capacity_value: int | None = Field(default=None, alias="capacityValue")
    # Wartość PRODUCTION jednostki (ile jednostek może wyprodukować). Może być liczbą
    # (np. Saar dok = 5) ALBO modyfikatorem względem planety jako string (np. bazowy dok
    # "+2" = wartość zasobów planety + 2; ``basic_production="res"``). RULES.md 33.2.
    production_value: int | str | None = Field(default=None, alias="productionValue")
    basic_production: str | None = Field(default=None, alias="basicProduction")
    capacity_used: int | None = Field(default=None, alias="capacityUsed")
    combat_hits_on: int | None = Field(default=None, alias="combatHitsOn")
    combat_die_count: int | None = Field(default=None, alias="combatDieCount")
    # Space Cannon (RULES.md 38): trafia na X+ (``spaceCannonHitsOn``), ``spaceCannonDieCount``
    # kości (brak = 1). ``deepSpaceCannon`` = jednostka strzela też do SĄSIEDNICH systemów
    # (np. PDS II). Wariant jednostki zależy od technologii gracza (resolve_unit_variant).
    space_cannon_hits_on: int | None = Field(default=None, alias="spaceCannonHitsOn")
    space_cannon_die_count: int | None = Field(default=None, alias="spaceCannonDieCount")
    deep_space_cannon: bool = Field(default=False, alias="deepSpaceCannon")
    # Anti-Fighter Barrage (RULES.md 39 W4) i Sustain Damage (W8) — z wariantu jednostki.
    afb_hits_on: int | None = Field(default=None, alias="afbHitsOn")
    afb_die_count: int | None = Field(default=None, alias="afbDieCount")
    sustain_damage: bool = Field(default=False, alias="sustainDamage")

    is_ship: bool = Field(default=False, alias="isShip")
    is_structure: bool = Field(default=False, alias="isStructure")

    upgrades_to_unit_id: str | None = Field(default=None, alias="upgradesToUnitId")
    upgrades_from_unit_id: str | None = Field(default=None, alias="upgradesFromUnitId")
    required_tech_id: str | None = Field(default=None, alias="requiredTechId")


class PlanetDef(_StaticModel):
    """Definicja planety (zasoby, wpływy, typ, zdolności)."""

    id: str
    name: str
    source: str
    tile_id: str | None = Field(default=None, alias="tileId")

    resources: int = 0
    influence: int = 0
    planet_type: str | None = Field(default=None, alias="planetType")
    # Niektóre źródła (np. thunders_edge) używają listy ``planetTypes`` zamiast
    # pojedynczego ``planetType``. Trzymamy ją, by nie gubić typu planety.
    planet_types: list[str] | None = Field(default=None, alias="planetTypes")
    tech_specialties: list[str] | None = Field(default=None, alias="techSpecialties")

    faction_homeworld: str | None = Field(default=None, alias="factionHomeworld")
    legendary_ability_name: str | None = Field(
        default=None, alias="legendaryAbilityName"
    )
    legendary_ability_text: str | None = Field(
        default=None, alias="legendaryAbilityText"
    )

    aliases: list[str] = Field(default_factory=list)


# Zdolność oznaczająca „tej frakcji nie można wybrać przy setupie" (wchodzi do gry
# tylko przez inną frakcję). Źródło: AsyncTI4 ``te_abilities.json`` — ``nocturne``
# (Obsidian): permanentEffect „This faction cannot be chosen during setup.". Trzymamy
# jako stałą, bo to pojedyncza, jawnie zweryfikowana reguła danych (RULES.md 28).
NO_SETUP_CHOICE_ABILITY = "nocturne"


class FactionDef(_StaticModel):
    """Definicja frakcji (setup startowy: dom, flota, planety, technologie)."""

    id: str = Field(alias="alias")
    name: str = Field(alias="factionName")
    source: str
    # Nazwa skrócona z danych (np. „Keleres" dla keleresm/x/a). Wspólna dla wariantów
    # jednej frakcji — pozwala dopasować karty przypisane do „rodziny" (przełom TE,
    # technologie, liderzy mają ``faction="keleres"``, a nie id wariantu).
    short_name: str | None = Field(default=None, alias="shortName")

    home_system: str | None = Field(default=None, alias="homeSystem")
    home_planets: list[str] = Field(default_factory=list, alias="homePlanets")
    starting_fleet: str | None = Field(default=None, alias="startingFleet")
    starting_tech: list[str] = Field(default_factory=list, alias="startingTech")
    # Wybór technologii startowej (gdy frakcja NIE ma stałej listy): gracz wybiera
    # ``starting_tech_amount`` spośród ``starting_tech_options`` (np. Winnu 1 z 8,
    # Argent 2 z 3). Źródło: pola startingTechOptions/startingTechAmount danych frakcji.
    starting_tech_options: list[str] = Field(
        default_factory=list, alias="startingTechOptions"
    )
    starting_tech_amount: int = Field(default=0, alias="startingTechAmount")
    commodities: int = 0
    # Złożoność frakcji (Low/Moderate/High) z danych AsyncTI4 — czysto informacyjna,
    # pokazywana w podglądzie frakcji na ekranie setupu. Brak w danych → None.
    complexity: str | None = None
    preferred_colours: list[str] = Field(default_factory=list, alias="preferredColours")
    # Liderzy frakcji (agent/commander/hero) — identyfikatory z danych AsyncTI4.
    leaders: list[str] = Field(default_factory=list)
    # Zdolności frakcji (faction abilities), np. ["mitosis"] dla Arborec. Identyfikatory
    # z danych frakcji; opisy w AbilityDef (assets/data/abilities/).
    abilities: list[str] = Field(default_factory=list)
    # Weksle frakcji (promissory notes), np. ["stymie"] dla Arborec. Pole ``promissoryNotes``
    # danych frakcji; definicje po stronie frontendu (AsyncTI4). Potrzebne do podglądu
    # frakcji na ekranie setupu (faction summary).
    promissory_notes: list[str] = Field(
        default_factory=list, alias="promissoryNotes"
    )
    # Technologie frakcyjne (faction tech), np. ["bio", "lw2"] dla Arborec. Identyfikatory
    # z POLA factionTech danych frakcji; definicje w TechnologyDef.
    faction_tech: list[str] = Field(default_factory=list, alias="factionTech")
    # Jednostki frakcji (bazowe generyczne + warianty frakcyjne, np. keleres_flagship).
    # AUTORYTATYWNA lista „co ta frakcja ma" — ważniejsza niż pole ``faction`` jednostki,
    # które bywa przypisane tylko do jednego wariantu (Keleres dzieli jednostki między 3).
    units: list[str] = Field(default_factory=list)

    @property
    def is_playable(self) -> bool:
        """Czy frakcję MOŻNA wybrać przy setupie (jest w puli wyboru).

        Wyklucza dwa przypadki, OBA odczytane z danych (nie z pamięci):

        1. Placeholdery systemowe (``neutral``, ``lazax``, `other.json`): puste
           ``homeSystem`` i brak liderów — służą jednostkom neutralnym / scenom,
           nie da się nimi grać (setup nie ma gdzie postawić domu).
        2. Frakcje z jawną zdolnością „nie można wybrać przy setupie". W danych
           Thunder's Edge to ``nocturne`` (Obsidian): ``permanentEffect`` =
           „This faction cannot be chosen during setup." Obsidian wchodzi do gry
           wyłącznie przez akcję Firmamentu (THE BLADE'S ORCHESTRA — flip dwustronnych
           komponentów). Źródło: ``assets/data/abilities/te_abilities.json``
           (id ``nocturne``, faction ``obsidian``) + franken errata ``undraftable``.
        """
        if not self.home_system or not self.leaders:
            return False
        return NO_SETUP_CHOICE_ABILITY not in self.abilities


class LeaderDef(_StaticModel):
    """Definicja lidera frakcji (agent/commander/hero) z jego typem i opisem.

    Typ czytamy z POLA ``type`` danych (``agent``/``commander``/``hero``), NIE z końcówki
    id — niektóre id (np. ``keleresherokuuasi``) nie kończą się nazwą typu.
    """

    id: str
    type: str
    name: str
    source: str

    faction: str | None = None
    title: str | None = None
    ability_name: str | None = Field(default=None, alias="abilityName")
    ability_text: str | None = Field(default=None, alias="abilityText")
    # Fraza okna użycia lidera (np. „When a player's unit is destroyed", „ACTION:").
    # Parsowana do TimingSpec w core/timing_spec.py.
    ability_window: str | None = Field(default=None, alias="abilityWindow")
    unlock_condition: str | None = Field(default=None, alias="unlockCondition")


class AbilityDef(_StaticModel):
    """Definicja zdolności frakcji (faction ability) z jej efektem i oknem czasowym.

    Zdolności są przypisane do frakcji przez pole ``faction`` i opisane przez
    ``permanentEffect`` (efekt pasywny) oraz ``window``/``windowEffect`` (reakcja
    w oknie czasowym). Identyfikator (``id``) jest tym, co trafia do web-data i co
    frontend rozwiązuje w swoich statycznych danych.
    """

    id: str
    name: str
    source: str

    faction: str | None = None
    short_name: str | None = Field(default=None, alias="shortName")
    permanent_effect: str | None = Field(default=None, alias="permanentEffect")
    window: str | None = None
    window_effect: str | None = Field(default=None, alias="windowEffect")


class TechnologyDef(_StaticModel):
    """Definicja technologii (generyczna lub frakcyjna).

    AsyncTI4 używa pola ``alias`` jako identyfikatora technologii (mapujemy je na
    ``id``). Pole ``faction`` wskazuje technologię frakcyjną (np. ``bio`` → arborec);
    jego brak oznacza technologię generyczną. ``types`` to kolory technologii
    (BIOTIC/PROPULSION/CYBERNETIC/WARFARE) lub puste dla ulepszeń jednostek.
    """

    id: str = Field(alias="alias")
    name: str
    source: str

    faction: str | None = None
    types: list[str] = Field(default_factory=list)
    requirements: str | None = None
    text: str | None = None
    short_name: str | None = Field(default=None, alias="shortName")


class BreakthroughDef(_StaticModel):
    """Definicja przełomu frakcji (breakthrough) — mechanika Thunder's Edge.

    Każda frakcja ma jeden przełom (karta) przypisany przez pole ``faction``.
    AsyncTI4 używa ``alias`` jako identyfikatora; mapujemy go na ``id``. ``synergy``
    to para kolorów technologii odblokowujących przełom.
    """

    id: str = Field(alias="alias")
    name: str
    source: str

    faction: str | None = None
    short_name: str | None = Field(default=None, alias="shortName")
    synergy: list[str] = Field(default_factory=list)
    text: str | None = None


class StrategyCardDef(_StaticModel):
    """Definicja karty strategii (inicjatywa, nazwa, teksty primary/secondary)."""

    id: str
    initiative: int
    name: str
    source: str

    primary_texts: list[str] = Field(default_factory=list, alias="primaryTexts")
    secondary_texts: list[str] = Field(default_factory=list, alias="secondaryTexts")
    colour_hex_code: str | None = Field(default=None, alias="colourHexCode")


class SystemDef(_StaticModel):
    """Definicja systemu (kafelka): planety, wormhole, przynależność."""

    id: str
    name: str | None = None
    source: str
    tile_back: str | None = Field(default=None, alias="tileBack")
    # Nazwa pliku grafiki kafelka w assets/tiles/ (czytana z danych, nie zgadywana).
    image_path: str | None = Field(default=None, alias="imagePath")

    planets: list[str] = Field(default_factory=list)
    wormholes: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)

    # Anomalie (AsyncTI4 koduje je osobnymi flagami boolowskimi)
    is_nebula: bool = Field(default=False, alias="isNebula")
    is_asteroid_field: bool = Field(default=False, alias="isAsteroidField")
    is_supernova: bool = Field(default=False, alias="isSupernova")
    is_gravity_rift: bool = Field(default=False, alias="isGravityRift")

    @property
    def anomalies(self) -> set[str]:
        """Zbiór nazw anomalii obecnych w systemie."""
        result: set[str] = set()
        if self.is_nebula:
            result.add("NEBULA")
        if self.is_asteroid_field:
            result.add("ASTEROID_FIELD")
        if self.is_supernova:
            result.add("SUPERNOVA")
        if self.is_gravity_rift:
            result.add("GRAVITY_RIFT")
        return result


class HandLimits(BaseModel):
    """Limity rozmiarów rąk gracza (reguły TI4 — patrz docs/RULES.md 36).

    ``None`` oznacza BRAK górnego limitu dla danej ręki (reguła TI4 nie nakłada
    limitu). Wartości liczbowe pochodzą z assetów (``engine_config.json``), nie są
    hardkodowane w logice silnika.

    Źródła reguł (tirules2.com, zrzut offline w ``docs/rules_tirules/``):
    - ``action_cards`` — max 7 kart akcji na ręce (R_action_cards: „maximum of seven
      action cards"); efekty gry mogą zmienić limit.
    - ``secret_objectives`` — max 3 tajne obiektywy (zrealizowane + niezrealizowane)
      łącznie (R_objective_cards: „up to three total scored and unscored").
    - ``promissory_notes`` — reguły NIE nakładają limitu na rękę promissory notes
      (R_promissory_notes); liczebność ręki jest informacją jawną, ale bez górnego
      kapu → ``None``.
    """

    model_config = ConfigDict(extra="forbid")

    action_cards: int | None = None
    secret_objectives: int | None = None
    promissory_notes: int | None = None


class EngineConfig(BaseModel):
    """Konfiguracja silnika czytana z ``assets/config/engine_config.json``.

    Jedno autorytatywne źródło dla wartości, których NIE wolno hardkodować z pamięci:
    limitów rąk (reguły TI4) oraz zbioru poziomów trudności bota (⚠️ ZAŁOŻENIE —
    poziomy trudności nie istnieją w TI4, to koncepcja warstwy AI silnika).

    Pole ``_comment`` w pliku JSON jest ignorowane (``extra="ignore"``) — służy tylko
    jako notatka dla edytującego plik.
    """

    model_config = ConfigDict(extra="ignore")

    hand_limits: HandLimits = Field(default_factory=HandLimits)
    # Dozwolony, skończony zbiór poziomów trudności bota (R1.8). ⚠️ ZAŁOŻENIE —
    # wartości konfigurowalne, nie reguła TI4 (patrz docs/RULES.md 36).
    valid_difficulties: list[str] = Field(default_factory=list)
    # Dozwolony zbiór osobowości (stylów gry) bota. ⚠️ ZAŁOŻENIE — koncepcja warstwy AI.
    valid_personalities: list[str] = Field(default_factory=list)
