"""Schematy DTO warstwy API (Pydantic v2).

Oddzielają kontrakt sieciowy od wewnętrznych modeli domenowych. Mapa jest
serializowana jako lista pozycji ze współrzędnymi kubicznymi (dla renderera SVG)
oraz lista krawędzi sąsiedztwa. God-Mode używa generycznego patcha w tym bloku;
typowane kreatory (wizards) dojdą w kolejnych blokach.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.core.activity import Activity
from src.core.game_state import GameState
from src.core.rules_content import (
    TopicContent,
    TopicGroup,
    TopicIndexEntry,
)


class UnitStack(BaseModel):
    """Stos jednostek jednego typu należących do jednego gracza."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    base_type: str
    count: int
    color: str | None = None
    # URL grafiki jednostki (assets/units/<kolor>_<asyncId>.png) pod /static.
    image_url: str | None = None


class PlanetUnits(BaseModel):
    """Jednostki naziemne i struktury na pojedynczej planecie."""

    model_config = ConfigDict(extra="forbid")

    planet_id: str
    owner_id: str | None = None
    stacks: list[UnitStack] = Field(default_factory=list)


class MapTile(BaseModel):
    """Pojedynczy kafelek mapy w reprezentacji dla frontendu."""

    model_config = ConfigDict(extra="forbid")

    position: str
    system_id: str
    q: int
    r: int
    s: int
    wormholes: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    planets: list[str] = Field(default_factory=list)
    name: str | None = None
    # URL grafiki kafelka (serwowana z assets/tiles pod /static). None, gdy brak.
    image_url: str | None = None
    # Slot domowy gracza (kolorowy róg bez kafelka — zależny od wyboru frakcji).
    is_home_slot: bool = False
    home_color: str | None = None
    # Jednostki w przestrzeni systemu (statki) oraz na planetach (naziemne/struktury).
    space_units: list[UnitStack] = Field(default_factory=list)
    planet_units: list[PlanetUnits] = Field(default_factory=list)


class MapEdge(BaseModel):
    """Krawędź grafu mapy (sąsiedztwo geometryczne lub wormhole)."""

    model_config = ConfigDict(extra="forbid")

    a: str
    b: str
    kind: Literal["adjacent", "wormhole"]


class MapView(BaseModel):
    """Pełna reprezentacja mapy dla renderera SVG."""

    model_config = ConfigDict(extra="forbid")

    tiles: list[MapTile] = Field(default_factory=list)
    edges: list[MapEdge] = Field(default_factory=list)


class MapStringRequest(BaseModel):
    """Żądanie załadowania mapy z map stringa AsyncTI4."""

    model_config = ConfigDict(extra="forbid")

    map_string: str
    # Czy automatycznie dodać Mecatol Rex w centrum (string zwykle go pomija).
    include_center: bool = True


class HistoryInfo(BaseModel):
    """Informacja o dostępności Undo/Redo i rozmiarze historii."""

    model_config = ConfigDict(extra="forbid")

    can_undo: bool
    can_redo: bool
    history_size: int


class HistoryEntry(BaseModel):
    """Pojedyncza migawka w historii (do panelu historii/undo)."""

    model_config = ConfigDict(extra="forbid")

    seq: int
    label: str
    is_current: bool


class HistoryList(BaseModel):
    """Lista migawek historii."""

    model_config = ConfigDict(extra="forbid")

    entries: list[HistoryEntry] = Field(default_factory=list)


class ActivityEntry(BaseModel):
    """Wpis feedu aktywności: migawka historii + opis „kto co zrobił"."""

    model_config = ConfigDict(extra="forbid")

    seq: int
    is_current: bool
    # Czas zapisu (sekundy epoki); None dla migawek sprzed wprowadzenia feedu.
    created_at: float | None = None
    activity: Activity


class ActivityPlayer(BaseModel):
    """Dane gracza do wyświetlenia we feedzie (rozwiązują ``actor_id``/``target_id``)."""

    model_config = ConfigDict(extra="forbid")

    faction: str | None = None
    color: str | None = None
    display_name: str = ""
    is_bot: bool = False


class ActivityFeed(BaseModel):
    """Feed aktywności: wpisy chronologicznie + słownik graczy po ``player_id``."""

    model_config = ConfigDict(extra="forbid")

    entries: list[ActivityEntry] = Field(default_factory=list)
    players: dict[str, ActivityPlayer] = Field(default_factory=dict)
    # Bieżąca migawka; wpisy o większym ``seq`` są „cofnięte" (gałąź redo).
    current_seq: int | None = None


class StateEnvelope(BaseModel):
    """Koperta rozsyłana klientom: stan gry + metadane historii.

    Jest to jednocześnie ładunek wiadomości WebSocket (``type="state"``) i
    odpowiedź endpointów REST zmieniających stan.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["state"] = "state"
    state: GameState
    history: HistoryInfo


class SetPlayerHandRequest(BaseModel):
    """God-Mode: ustawienie prywatnej ręki gracza (karty akcji / sekrety / weksle).

    Każda lista opcjonalna — podana NADPISUJE daną rękę, pominięta zostaje bez
    zmian. Służy głównie do testów „paska ręki" na mapie (operator widzi wszystko).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    action_cards: list[str] | None = None
    secret_objectives: list[str] | None = None
    promissory_notes: list[str] | None = None


class PlayerHandResponse(BaseModel):
    """Prywatna ręka gracza (ID kart) dla „paska ręki" na mapie i zakładki gracza.

    Klucze w camelCase, by wprost pasowały do typu ``PlayerHandData`` na froncie
    (``actionCards``/``secretObjectives``/``promissoryNotes``). W trybie lokalnym
    operator widzi wszystko, więc endpoint zwraca jawne identyfikatory — inaczej
    niż web-data, które cudze ręce redaguje do liczników (R6.1).
    """

    model_config = ConfigDict(extra="forbid")

    actionCards: list[str] = Field(default_factory=list)  # noqa: N815
    secretObjectives: list[str] = Field(default_factory=list)  # noqa: N815
    promissoryNotes: list[str] = Field(default_factory=list)  # noqa: N815


class StartingUnit(BaseModel):
    """Jeden wpis floty startowej frakcji — liczba + typ jednostki (pełna nazwa z danych).

    Buduje je backend z ``startingFleet`` przez ``parse_starting_fleet`` (jedno źródło
    parsera, RULES.md 2c). ``base_type`` to generyczny typ (np. ``carrier``), który front
    rozwiązuje na pełną nazwę przez swoje dane jednostek — zamiast pokazywać surowe kody
    (``cv``, ``dd``). ``placement`` (SPACE/PLANET) dla ewentualnego pogrupowania w UI.
    """

    model_config = ConfigDict(extra="forbid")

    base_type: str
    count: int
    placement: str


class FactionInfo(BaseModel):
    """Informacja o frakcji dla ekranu wyboru (setup)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    # Źródło/dodatek frakcji (np. „base", „pok", „thunders_edge", „codex3"). Front używa
    # go do pogrupowania listy wyboru wg dodatków (Base Game / PoK / Thunder's Edge).
    source: str
    home_system: str | None = None
    home_planets: list[str] = Field(default_factory=list)
    starting_fleet: str | None = None
    preferred_colours: list[str] = Field(default_factory=list)
    # Wybór technologii startowej (gdy frakcja nie ma stałej listy). Gdy
    # ``starting_tech_amount == 0``, frakcja nie wybiera (stałe technologie).
    starting_tech_options: list[str] = Field(default_factory=list)
    starting_tech_amount: int = 0
    # Pola bogate — do podglądu frakcji (faction summary) na ekranie setupu. To same
    # identyfikatory ze statycznego rejestru (``FactionDef``); front rozwiązuje je po
    # swoich danych AsyncTI4 (te same komponenty co panel gracza w grze). Dzięki temu
    # wybór frakcji pokazuje zdolności / technologie / liderów / jednostki bez stanu gry.
    starting_tech: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    faction_tech: list[str] = Field(default_factory=list)
    leaders: list[str] = Field(default_factory=list)
    units: list[str] = Field(default_factory=list)
    promissory_notes: list[str] = Field(default_factory=list)
    commodities: int = 0
    complexity: str | None = None
    # Przełom frakcji (breakthrough, Thunder's Edge) — identyfikator dopasowany po
    # ``BreakthroughDef.faction``; None, gdy frakcja go nie ma. Front rozwiązuje go po
    # swoich danych (komponent ``Breakthrough``), tak jak panel gracza w grze.
    breakthrough: str | None = None
    # Flota startowa rozbita na pozycje (liczba + typ jednostki). Zastępuje surowy
    # ``starting_fleet`` w UI pełnymi nazwami jednostek. ``starting_fleet`` zostaje jako
    # oryginalny string (zgodność wsteczna / debug).
    starting_units: list[StartingUnit] = Field(default_factory=list)


class EngineConfigInfo(BaseModel):
    """Konfiguracja silnika wystawiana frontendowi (setup).

    Obecnie niesie dozwolony zbiór poziomów trudności bota (R10.2) — front NIE
    trzyma własnej kopii tej listy, tylko pobiera ją stąd. Wartości pochodzą
    z ``engine_config.json`` czytanego przez ``StaticDataRegistry`` (⚠️ ZAŁOŻENIE,
    patrz docs/RULES.md 36), więc gdy zbiór się zmieni w assecie, front dostanie
    aktualny bez zmian w kodzie.
    """

    model_config = ConfigDict(extra="forbid")

    # Posortowana lista dozwolonych poziomów trudności bota (R10.2).
    valid_difficulties: list[str] = Field(default_factory=list)
    # Posortowana lista dozwolonych osobowości bota (⚠️ ZAŁOŻENIE).
    valid_personalities: list[str] = Field(default_factory=list)


class SetupPlayerRequest(BaseModel):
    """Żądanie setupu gracza: frakcja + kolor na wskazanym slocie domowym.

    ``faction_id`` jest opcjonalny — gdy pominięty, backend dobiera losową,
    nieprzypisaną frakcję (R8.5). ``name``/``control_type``/``difficulty``
    rozszerzają kontrakt o nazwę wyświetlaną i tryb sterowania (R10.1–R10.3);
    ``difficulty`` ma sens tylko dla ``control_type == "BOT"``.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    # Opcjonalny: None → losowa, nieprzypisana frakcja (R8.5).
    faction_id: str | None = None
    color: str
    home_position: str
    # Nazwa wyświetlana (R7.1); pusta/None → auto-nazwa przy setupie (R7.3).
    name: str | None = None
    # Tryb sterowania (R10.1): "HUMAN" (domyślnie) lub "BOT".
    control_type: str = "HUMAN"
    # Poziom trudności bota (R10.2/R10.3); wymagany dla BOT, ignorowany dla HUMAN.
    difficulty: str | None = None
    # Osobowość bota; brak → losowa (tylko BOT), ignorowana dla HUMAN.
    personality: str | None = None
    # Wybrane technologie startowe (dla frakcji z wyborem, np. Winnu/Argent).
    starting_tech: list[str] | None = None


class NewGamePlayer(BaseModel):
    """Pojedynczy gracz w żądaniu nowej gry (frakcja opcjonalna; reszta auto)."""

    model_config = ConfigDict(extra="forbid")

    # Opcjonalny: None → losowa, nieprzypisana frakcja (R8.5).
    faction_id: str | None = None
    # Opcjonalne: gdy pominięte, kolor/slot/id przydzielane automatycznie
    # wg kolejności (gracz 1 → red/301, 2 → green/304, ...).
    player_id: str | None = None
    # Nazwa wyświetlana (R7.1); pusta/None → auto-nazwa przy setupie (R7.3).
    name: str | None = None
    color: str | None = None
    # Tryb sterowania (R10.1): "HUMAN" (domyślnie) lub "BOT".
    control_type: str = "HUMAN"
    # Poziom trudności bota (R10.2/R10.3); wymagany dla BOT, ignorowany dla HUMAN.
    difficulty: str | None = None
    # Osobowość bota; brak → losowa (tylko BOT), ignorowana dla HUMAN.
    personality: str | None = None
    # Opcjonalny slot domowy — pod przyszły draft slice (R14.3).
    home_position: str | None = None
    # Wybrane technologie startowe (dla frakcji z wyborem, np. Winnu/Argent).
    starting_tech: list[str] | None = None


class NewGameRequest(BaseModel):
    """Żądanie utworzenia nowej gry: mapa + gracze w jednym kroku.

    ``map_string`` opcjonalny — gdy pominięty, backend użyje mapy testowej.
    Kolory i sloty domowe są przydzielane automatycznie wg kolejności graczy,
    chyba że jawnie podane dla danego gracza.
    """

    model_config = ConfigDict(extra="forbid")

    players: list[NewGamePlayer] = Field(default_factory=list)
    map_string: str | None = None
    include_center: bool = True


class UnitChange(BaseModel):
    """Ustawienie liczby jednostek danego typu gracza (0 = usunięcie)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    base_type: str
    count: int


class SpaceUnitsRequest(BaseModel):
    """Ustawienie jednostek w przestrzeni danego systemu (God-Mode)."""

    model_config = ConfigDict(extra="forbid")

    changes: list[UnitChange] = Field(default_factory=list)


class PlanetUnitsRequest(BaseModel):
    """Ustawienie jednostek na planecie danego systemu (God-Mode)."""

    model_config = ConfigDict(extra="forbid")

    changes: list[UnitChange] = Field(default_factory=list)
    owner_id: str | None = None


class UnitEditRequest(BaseModel):
    """Edycja God-Mode jednostek w strefie systemu (delta w terminach asyncId).

    Operuje tak jak frontend: strefa (``"space"`` lub ID planety), klucz frakcji
    (jak w ``tileUnitData``), ``asyncId`` jednostki i przyrost ``delta`` (+/−).
    Backend tłumaczy ``asyncId`` → ``baseType`` i klucz frakcji → ``player_id``.
    Brak sprawdzania zasad — to narzędzie operatora (God-Mode).
    """

    model_config = ConfigDict(extra="forbid")

    zone: str  # "space" albo ID planety
    faction: str  # klucz frakcji z tileUnitData (faction lub player_id)
    async_id: str = Field(alias="asyncId")
    delta: int  # przyrost liczby (dodatni/ujemny)


class UnitMoveRequest(BaseModel):
    """Przesunięcie jednostek między strefami/systemami (God-Mode, bez reguł)."""

    model_config = ConfigDict(extra="forbid")

    from_position: str = Field(alias="fromPosition")
    from_zone: str = Field(alias="fromZone")  # "space" albo ID planety
    to_position: str = Field(alias="toPosition")
    to_zone: str = Field(alias="toZone")
    faction: str
    async_id: str = Field(alias="asyncId")
    count: int = 1


class PlayerEditRequest(BaseModel):
    """God-Mode: edycja pól gracza. Każde pole opcjonalne — podane nadpisuje.

    Bez sprawdzania zasad (narzędzie operatora). Pola odpowiadają ``PlayerState``.
    """

    model_config = ConfigDict(extra="forbid")

    faction: str | None = None
    color: str | None = None
    victory_points: int | None = None
    trade_goods: int | None = None
    commodities: int | None = None
    tactical_cc: int | None = None
    fleet_cc: int | None = None
    strategic_cc: int | None = None
    cc_reinf: int | None = None
    passed: bool | None = None
    strategy_cards: list[int] | None = None
    controlled_planets: list[str] | None = None
    exhausted_planets: list[str] | None = None
    technologies: list[str] | None = None
    exhausted_technologies: list[str] | None = None
    # Stan liderów: {leader_id: "locked"|"unlocked"|"exhausted"}.
    leader_states: dict[str, str] | None = None
    # Przełom frakcji (Thunder's Edge): odblokowany / wyczerpany / odłożone TG.
    breakthrough_unlocked: bool | None = None
    breakthrough_exhausted: bool | None = None
    breakthrough_tg: int | None = None
    # Promissory notes w strefie gracza (play area) — jawne, odrębne od ręki
    # (RULES.md 2d). God-Mode zasila je ręcznie do czasu logiki zagrywania notek.
    promissory_notes_in_play: list[str] | None = None


class PlayerComponentToggleRequest(BaseModel):
    """Przełączenie stanu komponentu gracza (planeta/technologia) — exhaust ↔ ready."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    component_id: str


class LeaderStateRequest(BaseModel):
    """Ustawienie stanu lidera gracza (locked/unlocked/exhausted)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    leader_id: str
    state: str


class StrategyCardInfo(BaseModel):
    """Karta strategii dla panelu fazy strategii (dane + stan)."""

    model_config = ConfigDict(extra="forbid")

    initiative: int
    id: str
    name: str
    primary_texts: list[str] = Field(default_factory=list)
    secondary_texts: list[str] = Field(default_factory=list)
    colour_hex_code: str | None = None
    # Stan w bieżącej grze:
    trade_goods: int = 0  # TG leżące na karcie (niewybrana)
    picked_by: str | None = None  # player_id właściciela (lub None)
    exhausted: bool = False  # czy zagrana (odwrócona)


class StrategyPickRequest(BaseModel):
    """Wybór karty strategii przez gracza (po numerze inicjatywy)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    initiative: int


class StrategyPlayRequest(BaseModel):
    """Zagranie (wyczerpanie) karty strategii gracza."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    initiative: int


class StrategyPrimaryStepRequest(BaseModel):
    """Wybór aktywnego gracza dla bieżącego kroku wieloetapowego primary (E8-T5).

    ``player_id`` musi być właścicielem karty; ``payload`` ma kształt zależny od kroku
    karty (np. Trade: ``{"players": ["p2"]}``) i jest walidowany po stronie ``core/``.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class StrategySecondaryRequest(BaseModel):
    """Odpowiedź w oknie secondary karty strategii (E8-T3).

    ``player_id`` musi być bieżącym respondentem okna. ``execute=True`` → wykonaj
    secondary; ``False`` → pas (oba przesuwają kolejkę okna).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    execute: bool = False
    # Wybory respondenta dla „follow" (kształt zależy od karty, np. Leadership:
    # planety do wydania + rozkład żetonów). Walidowane po stronie ``core/``.
    payload: dict[str, Any] = Field(default_factory=dict)

class TurnActionRequest(BaseModel):
    """Zakończenie/pas tury (E8-T4). ``player_id`` opcjonalny — gdy podany, backend

    waliduje, że to tura tego gracza (RULES.md 31.2). Pominięty = bez kontroli
    tożsamości (zgodność wsteczna), faza nadal musi być akcji.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str | None = None


class EpilogueVoteRequest(BaseModel):
    """Głos w epilogu: ``choice`` = ``honorable`` albo ``dishonorable`` (walidacja w core)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    choice: str


class StatusScoreRequest(BaseModel):
    """Zdobycie celu w kroku 1 fazy statusu: ``kind`` = ``public`` albo ``secret``."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    kind: str
    objective_id: str


class StatusRedistributeRequest(BaseModel):
    """Rozdział żetonów dowodzenia w kroku 5 fazy statusu (suma = dostępne żetony)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    tactical: int
    fleet: int
    strategic: int


class SetupSecretRequest(BaseModel):
    """Wybór tajnego celu w setupie: gracz zatrzymuje ``objective_id`` z dwóch dobranych."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    objective_id: str


class SetupActorRequest(BaseModel):
    """Akcja mówcy w setupie (żeton Custodians, odkrycie celów) — ``player_id`` = mówca."""

    model_config = ConfigDict(extra="forbid")

    player_id: str


class SetSpeakerRequest(BaseModel):
    """Ustawienie mówcy (speaker) — otwiera wybór kart w fazie strategii."""

    model_config = ConfigDict(extra="forbid")

    player_id: str


class MoveCargoItem(BaseModel):
    """Pozycja ładunku transportu (RULES.md 32.3): typ, liczba i strefa źródłowa.

    Ładunek to myśliwce / siły naziemne przewożone statkami w tym samym ruchu
    (``fighter``/``infantry``/``mech``). ``from_zone`` = ``"space"`` (z przestrzeni
    systemu źródłowego) albo id PLANETY w tym systemie (statek zabiera piechotę/mecha
    z planety). Backend waliduje typ, strefę i limit capacity.
    """

    model_config = ConfigDict(extra="forbid")

    base_type: str = Field(alias="baseType")
    count: int = 1
    from_zone: str = Field(default="space", alias="fromZone")


class MoveShipsRequest(BaseModel):
    """Ruch floty w akcji taktycznej (E8): źródło + statki + ładunek + gracz.

    Walidowana akcja (RULES.md 32), w odróżnieniu od God-Mode ``/units/move``.
    ``faction`` to klucz tożsamości gracza (jak w tileUnitData) — rozwiązywany na
    ``player_id`` jak w pozostałych endpointach taktycznych. Cel = aktywny system.

    Dwa warianty wejścia (łączone):
    - ``base_type`` + ``count`` — pojedynczy stos statków (zgodność wsteczna z T5);
    - ``ships`` — lista typów statków ruszających naraz (pełna flota, dla UI ruchu).
    ``cargo`` = myśliwce/siły naziemne przewożone razem w ramach łącznej capacity
    WSZYSTKICH ruszających statków (RULES.md 32.3).
    """

    model_config = ConfigDict(extra="forbid")

    from_position: str = Field(alias="fromPosition")
    base_type: str | None = Field(default=None, alias="baseType")
    count: int = 1
    faction: str
    ships: list[MoveCargoItem] = Field(default_factory=list)
    cargo: list[MoveCargoItem] = Field(default_factory=list)

class MoveRangeResponse(BaseModel):
    """Podgląd zasięgu ruchu (RULES.md 32): legalne systemy źródłowe do aktywnego.

    ``sources`` = mapa {pozycja -> lista base_type statków, które mogą stamtąd ruszyć
    do aktywnego systemu}. ``active`` = pozycja aktywnego systemu (cel). Służy
    podświetleniu zasięgu/ścieżki na mapie; pusta mapa = brak legalnego ruchu.
    """

    model_config = ConfigDict(populate_by_name=True)

    active: str | None
    sources: dict[str, list[str]] = Field(default_factory=dict)


class ActivateSystemRequest(BaseModel):
    """Aktywacja systemu w akcji taktycznej (E3): pozycja kafelka."""

    model_config = ConfigDict(extra="forbid")

    position: str


class ComponentActionRequest(BaseModel):
    """Akcja komponentu — trzeci typ akcji fazy akcji (RULES.md 31.8).

    ``player_id`` opcjonalny — gdy podany, backend waliduje, że to tura tego gracza.
    ``component_id`` to ADNOTACJA „co zagrano" (karta akcji / relikt / tech / zdolność);
    na razie nie steruje żadnym efektem (szkielet), trafia tylko do etykiety eventu.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str | None = None
    component_id: str | None = None


class TacticalStepRequest(BaseModel):
    """Skok do konkretnego kroku akcji taktycznej (E3)."""

    model_config = ConfigDict(extra="forbid")

    step: str


class CommandTokenRequest(BaseModel):
    """God-Mode: dodanie/zdjęcie żetonu dowodzenia w przestrzeni systemu (E3)."""

    model_config = ConfigDict(extra="forbid")

    faction: str  # klucz frakcji z tileUnitData (faction lub player_id)


class CombatUnitHelp(BaseModel):
    """Pomoc liczbowa dla jednego typu jednostki w walce (E3)."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    unit_id: str = Field(serialization_alias="unitId")
    name: str
    count: int
    combat_hits_on: int = Field(serialization_alias="combatHitsOn")
    combat_die_count: int = Field(serialization_alias="combatDieCount")
    expected_hits: float = Field(serialization_alias="expectedHits")


class CombatSideHelp(BaseModel):
    """Siły jednego gracza w walce + sumaryczne pomoce (E3)."""

    model_config = ConfigDict(populate_by_name=True)

    faction: str  # klucz tożsamości (frakcja lub player_id) — spójny z web-data
    player_id: str = Field(serialization_alias="playerId")
    units: list[CombatUnitHelp]
    total_dice: int = Field(serialization_alias="totalDice")
    expected_hits: float = Field(serialization_alias="expectedHits")


class CombatHelpResponse(BaseModel):
    """Odpowiedź asystenta walki: miejsce + strony (lub pusto, gdy brak walki)."""

    model_config = ConfigDict(populate_by_name=True)

    position: str
    planet: str | None = None
    kind: str  # "space" albo "ground"
    sides: list[CombatSideHelp]


class ProduceOrderItem(BaseModel):
    """Pozycja zamówienia produkcji: typ jednostki + liczba sztuk + strefa docelowa."""

    model_config = ConfigDict(extra="forbid")

    base_type: str = Field(alias="baseType")
    count: int = 1
    # Strefa: "space" (statki) albo ID planety (siły naziemne/struktury). Gdy pominięta,
    # backend wybiera wg umiejscowienia (statek→space; naziemne wymaga planety → błąd).
    zone: str | None = None


class ProduceSpend(BaseModel):
    """Płatność za produkcję: planety do wyczerpania + trade goods."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    planets: list[str] = Field(default_factory=list)
    trade_goods: int = Field(default=0, alias="tradeGoods")


class ProduceRequest(BaseModel):
    """Walidowana produkcja jednostek w aktywnym systemie (E8-T6).

    Egzekwuje limit/budżet/blokadę (RULES.md 33.2); przy sukcesie stawia jednostki.
    ``faction`` rozwiązywany na player_id jak w pozostałych endpointach taktycznych.
    """

    model_config = ConfigDict(extra="forbid")

    faction: str
    orders: list[ProduceOrderItem] = Field(default_factory=list)
    # Czym płacimy; pominięte = płatność automatyczna (najmniejsza nadwyżka).
    spend: ProduceSpend | None = None

class CapturePlanetRequest(BaseModel):
    """Przejęcie kontroli planety po inwazji (E3): planeta + gracz."""

    model_config = ConfigDict(extra="forbid")

    planet: str
    faction: str  # klucz frakcji z tileUnitData (faction lub player_id)


class ProducibleUnitHelp(BaseModel):
    """Pomoc produkcji dla jednego typu jednostki (koszt z UnitDef)."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    unit_id: str = Field(serialization_alias="unitId")
    name: str
    cost: float
    units_per_cost: int = Field(serialization_alias="unitsPerCost")
    placement: str


class ProductionHelpResponse(BaseModel):
    """Pomoc liczbowa kroku produkcji: dostępne zasoby + koszty jednostek (E3)."""

    model_config = ConfigDict(populate_by_name=True)

    player_id: str = Field(serialization_alias="playerId")
    available_resources: int = Field(serialization_alias="availableResources")
    # Łączna wartość PRODUCTION jednostek gracza w aktywnym systemie (limit sztuk).
    production_limit: int = Field(default=0, serialization_alias="productionLimit")
    units: list[ProducibleUnitHelp]


class WindowOpenRequest(BaseModel):
    """Otwarcie okna czasowego (narzędzie/testowe) — typ + kolejka lub inicjator.

    Podaj ``queue`` jawnie ALBO ``initiator_id`` (backend wyliczy kolejkę od gracza
    po inicjatorze, zgodnie z zegarem). ``window_type`` musi być jedną z wartości
    ``WindowType`` (STRATEGY_SECONDARY / COMBAT_ASSIGN_HITS / SPACE_CANNON / REACTION).
    """

    model_config = ConfigDict(extra="forbid")

    window_type: str
    queue: list[str] | None = None
    initiator_id: str | None = None
    include_initiator: bool = False
    context: dict[str, str | int] | None = None

class WindowRespondRequest(BaseModel):
    """Odpowiedź bieżącego respondenta w otwartym oknie czasowym (E8-T2).

    ``player_id`` MUSI być bieżącym respondentem okna (``current_responder``),
    inaczej backend odrzuca (odpowiedź poza kolejnością → 422). ``decision`` to
    luźna etykieta decyzji panelu (np. ``"secondary"`` / ``"pass"``); w T2 jest
    tylko przekazywana do etykiety commitu — efekty decyzji dojdą od T3.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    decision: str | None = None

class GodModePatch(BaseModel):
    """Generyczny patch God-Mode na pola ``GameState``.

    Każde pole jest opcjonalne — podane wartości nadpisują bieżący stan, pominięte
    pozostają bez zmian. ``players`` i ``systems`` nadpisują CAŁE słowniki, zgodnie
    z semantyką ręcznej korekty (operator podaje docelowy obraz danej sekcji).
    Typowane, drobnoziarniste kreatory (set-victory-points itd.) dojdą w Bloku 4.
    """

    model_config = ConfigDict(extra="forbid")

    round_number: int | None = None
    phase: str | None = None
    active_player_id: str | None = None
    # Żeton Custodians zdjęty z Mecatol Rex (dodaje fazę agendy do każdej rundy). Do czasu
    # pełnej obsługi inwazji na Mecatol Rex ustawiany ręcznie (RULES.md 41.6).
    custodians_removed: bool | None = None
    # Cele publiczne (talie, odkryte, zdobyte) — nadpisuje CAŁY podstan celów.
    objectives: dict[str, object] | None = None
    players: dict[str, dict[str, object]] | None = None
    systems: dict[str, dict[str, object]] | None = None


# --- DTO przeglądarki Zasad (Rules_Browser) ----------------------------
#
# Lustro frozen dataclass z ``src/core/rules_content.py`` w warstwie API.
# Treść reguł jest tylko do odczytu, więc DTO są jednokierunkowe: budowane z
# obiektów core przez fabryki ``from_core`` (core → DTO). Kolejność grup w
# ``RulesIndexResponse`` wynika wprost z ``load_index`` (Reguły → Frakcje →
# Komponenty) — DTO jej nie zmienia.


class TopicIndexEntryDTO(BaseModel):
    """DTO pojedynczej pozycji indeksu tematów (lustro ``TopicIndexEntry``)."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    group: str

    @classmethod
    def from_core(cls, entry: TopicIndexEntry) -> TopicIndexEntryDTO:
        """Buduje DTO z core'owej pozycji indeksu ``TopicIndexEntry``."""
        return cls(slug=entry.slug, title=entry.title, group=entry.group)


class TopicGroupDTO(BaseModel):
    """DTO grupy tematów w indeksie (lustro ``TopicGroup``).

    ``entries`` to lista (krotka z core rozwijana do listy) pozycji w kolejności
    ustalonej przez ``load_index``.
    """

    model_config = ConfigDict(extra="forbid")

    group: str
    label: str
    entries: list[TopicIndexEntryDTO] = Field(default_factory=list)

    @classmethod
    def from_core(cls, group: TopicGroup) -> TopicGroupDTO:
        """Buduje DTO z core'owej grupy ``TopicGroup`` (krotka → lista DTO)."""
        return cls(
            group=group.group,
            label=group.label,
            entries=[TopicIndexEntryDTO.from_core(entry) for entry in group.entries],
        )


class RulesIndexResponse(BaseModel):
    """Odpowiedź ``GET /rules``: pełny indeks tematów pogrupowany po grupach.

    ``groups`` zachowuje kolejność z ``load_index``: Reguły → Frakcje → Komponenty.
    """

    model_config = ConfigDict(extra="forbid")

    groups: list[TopicGroupDTO] = Field(default_factory=list)

    @classmethod
    def from_core(cls, groups: list[TopicGroup]) -> RulesIndexResponse:
        """Buduje odpowiedź indeksu z listy core'owych grup (np. z ``load_index``)."""
        return cls(groups=[TopicGroupDTO.from_core(group) for group in groups])


class TopicContentDTO(BaseModel):
    """DTO treści pojedynczego tematu (lustro ``TopicContent``).

    Odpowiedź ``GET /rules/{slug}``: surowy ``markdown`` renderowany po stronie
    klienta oraz metadane (tytuł, grupa, flaga pustej noty F/C).
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    group: str
    markdown: str
    is_empty_note: bool

    @classmethod
    def from_core(cls, topic: TopicContent) -> TopicContentDTO:
        """Buduje DTO z core'owej treści tematu ``TopicContent``."""
        return cls(
            slug=topic.slug,
            title=topic.title,
            group=topic.group,
            markdown=topic.markdown,
            is_empty_note=topic.is_empty_note,
        )


# --- Space Cannon Offense (RULES.md 38) ---


class SpaceCannonShooterHelp(BaseModel):
    """Grupa jednostek z Space Cannon (panel kroku SPACE_CANNON)."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    count: int
    hits_on: int = Field(serialization_alias="hitsOn")
    dice_per_unit: int = Field(serialization_alias="dicePerUnit")
    total_dice: int = Field(serialization_alias="totalDice")
    expected_hits: float = Field(serialization_alias="expectedHits")
    position: str
    zone: str
    deep: bool
    remote: bool


class SpaceCannonSideHelp(BaseModel):
    """Strona w kolejce Space Cannon: gracz, jego strzelcy i legalne cele."""

    model_config = ConfigDict(populate_by_name=True)

    faction: str
    player_id: str = Field(serialization_alias="playerId")
    shooters: list[SpaceCannonShooterHelp]
    total_dice: int = Field(serialization_alias="totalDice")
    expected_hits: float = Field(serialization_alias="expectedHits")
    targets: list[str]


class SpaceCannonRollHelp(BaseModel):
    """Wynik rzutu jednej grupy strzelców: kości i trafienia."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    hits_on: int = Field(serialization_alias="hitsOn")
    position: str
    zone: str
    dice: list[int]
    hits: int


class SpaceCannonPendingHelp(BaseModel):
    """Trafienia czekające na przypisanie strat."""

    roller: str
    target: str
    hits: int
    required: int  # ile statków trzeba zniszczyć (min(trafienia, statki celu))
    rolls: list[SpaceCannonRollHelp]


class SpaceCannonShipHelp(BaseModel):
    """Statek gracza-celu w aktywnym systemie (do przypisania strat)."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    count: int


class SpaceCannonLogEntry(BaseModel):
    """Wpis dziennika okna: kto strzelił w kogo, ile trafień i jakie straty."""

    roller: str
    target: str
    hits: int
    passed: bool
    rolls: list[SpaceCannonRollHelp]
    destroyed: dict[str, int]


class SpaceCannonPanelResponse(BaseModel):
    """Stan panelu Space Cannon Offense (jeden odczyt na cały panel)."""

    model_config = ConfigDict(populate_by_name=True)

    position: str | None
    is_open: bool = Field(serialization_alias="isOpen")
    # Okno już zamknięte, ale było rozstrzygnięcie (dziennik niepusty) — panel pokazuje wynik.
    resolved: bool = False
    queue: list[str]
    responded: list[str]
    current: str | None
    sides: list[SpaceCannonSideHelp]
    pending: SpaceCannonPendingHelp | None
    target_ships: list[SpaceCannonShipHelp] = Field(serialization_alias="targetShips")
    log: list[SpaceCannonLogEntry]


class SpaceCannonFireRequest(BaseModel):
    """Strzał: kto strzela i (opcjonalnie) w kogo — klucze tożsamości jak w tileUnitData."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    target: str | None = None


class SpaceCannonPassRequest(BaseModel):
    """Rezygnacja ze strzału bieżącego gracza."""

    model_config = ConfigDict(extra="forbid")

    faction: str


class SpaceCannonLossItem(BaseModel):
    """Pozycja strat: typ statku + liczba zniszczonych."""

    model_config = ConfigDict(extra="forbid")

    base_type: str = Field(alias="baseType")
    count: int = 1


class SpaceCannonAssignRequest(BaseModel):
    """Przypisanie strat przez gracza-cel (``faction`` = klucz gracza-celu)."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    losses: list[SpaceCannonLossItem]


# --- Walka: okno pola bitwy (RULES.md 39) ---


class BattleUnitView(BaseModel):
    """Grupa jednostek strony w walce (jeden typ) — wartości wariantu gracza."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    count: int
    damaged: int
    hits_on: int = Field(serialization_alias="hitsOn")
    base_hits_on: int = Field(serialization_alias="baseHitsOn")
    modifier: int
    dice_per_unit: int = Field(serialization_alias="dicePerUnit")
    total_dice: int = Field(serialization_alias="totalDice")
    expected_hits: float = Field(serialization_alias="expectedHits")
    sustain: bool
    sustainable: int
    afb_hits_on: int | None = Field(serialization_alias="afbHitsOn")
    afb_dice: int = Field(serialization_alias="afbDice")


class BattleSideView(BaseModel):
    """Strona walki: kto, rola, jednostki i sumy (kości, oczekiwane trafienia, „życie")."""

    model_config = ConfigDict(populate_by_name=True)

    faction: str
    player_id: str = Field(serialization_alias="playerId")
    role: str  # "attacker" | "defender"
    units: list[BattleUnitView]
    unit_count: int = Field(serialization_alias="unitCount")
    total_dice: int = Field(serialization_alias="totalDice")
    expected_hits: float = Field(serialization_alias="expectedHits")
    # „Życie" strony = trafienia, które może jeszcze przyjąć (jednostki + Sustain Damage).
    hp: int


class BattleRollView(BaseModel):
    """Rzut jednej grupy jednostek: kości, próg i trafienia."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    hits_on: int = Field(serialization_alias="hitsOn")
    modifier: int
    dice: list[int]
    hits: int


class BattleLogView(BaseModel):
    """Wpis historii walki: runda, faza (AFB/COMBAT), rzuty, trafienia, straty."""

    round: int
    phase: str
    rolls: dict[str, list[BattleRollView]]
    hits: dict[str, int]
    losses: dict[str, dict[str, int]]
    sustained: dict[str, dict[str, int]]
    # Wpis RETREAT (RULES.md 39.5): {"player", "destination", "units", "tokenPlaced"}.
    retreat: dict[str, Any] | None = None


class RetreatOptionView(BaseModel):
    """Dozwolony system odwrotu (RULES.md 39.5 O4)."""

    model_config = ConfigDict(populate_by_name=True)

    position: str
    system_id: str = Field(serialization_alias="systemId")


class BattleResponse(BaseModel):
    """Pełny stan okna pola bitwy (jeden odczyt na całe okno)."""

    model_config = ConfigDict(populate_by_name=True)

    active: bool
    kind: str | None = None
    position: str | None = None
    planet: str | None = None
    round: int = 0
    step: str | None = None
    nebula: bool = False
    attacker: BattleSideView | None = None
    defender: BattleSideView | None = None
    pending_hits: dict[str, int] = Field(default_factory=dict, serialization_alias="pendingHits")
    required: dict[str, int] = Field(default_factory=dict)
    assigning: str | None = None
    rolls: dict[str, list[BattleRollView]] = Field(default_factory=dict)
    afb: dict[str, list[BattleRollView]] = Field(default_factory=dict)
    log: list[BattleLogView] = Field(default_factory=list)
    winner: str | None = None
    outcome: str | None = None
    # Odwroty (RULES.md 39.5): kto teraz ogłasza (okno COMBAT_RETREAT), kto ogłosił odwrót
    # w tej rundzie, wykonane odwroty {strona: system} i dozwolone cele per strona.
    announcing: str | None = None
    retreating: list[str] = Field(default_factory=list)
    retreated: dict[str, str] = Field(default_factory=dict)
    retreat_options: dict[str, list[RetreatOptionView]] = Field(
        default_factory=dict, serialization_alias="retreatOptions"
    )


class BattleAnnounceRetreatRequest(BaseModel):
    """Ogłoszenie odwrotu (``announce=True``) albo walka dalej (``False``)."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    announce: bool = True


class RetreatCargoItem(BaseModel):
    """Ładunek odwrotu: typ, liczba i strefa (``space`` albo id planety kontrolowanej)."""

    model_config = ConfigDict(extra="forbid")

    base_type: str = Field(alias="baseType")
    count: int = 1
    from_zone: str = Field(default="space", alias="fromZone")


class BattleRetreatRequest(BaseModel):
    """Wykonanie odwrotu do ``destination``. Brak ``cargo`` = ładunek domyślny."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    destination: str
    cargo: list[RetreatCargoItem] | None = None
    token_pool: str | None = Field(default=None, alias="tokenPool")


class BattleStartRequest(BaseModel):
    """Start walki w aktywnym systemie: bez planety = kosmiczna, z planetą = naziemna."""

    model_config = ConfigDict(extra="forbid")

    planet: str | None = None


class BattleLossItem(BaseModel):
    """Pozycja strat: typ jednostki + liczba."""

    model_config = ConfigDict(extra="forbid")

    base_type: str = Field(alias="baseType")
    count: int = 1


class BattleAssignRequest(BaseModel):
    """Pokrycie trafień przez gracza: Sustain Damage + niszczone (nieuszkodzone/uszkodzone)."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    sustain: list[BattleLossItem] = Field(default_factory=list)
    destroy: list[BattleLossItem] = Field(default_factory=list)
    destroy_damaged: list[BattleLossItem] = Field(
        default_factory=list, alias="destroyDamaged"
    )


class TransactionSideRequest(BaseModel):
    """Jedna strona transakcji: to, co dany gracz ODDAJE (RULES.md 47)."""

    model_config = ConfigDict(extra="forbid")

    trade_goods: int = 0
    commodities: int = 0
    promissory_note: str | None = None
    relic_fragments: list[str] = Field(default_factory=list)


class TransactionRequest(BaseModel):
    """Transakcja aktywnego gracza z sąsiadem (RULES.md 47): ``give`` oddaje, ``receive`` bierze."""

    model_config = ConfigDict(extra="forbid")

    partner_id: str
    give: TransactionSideRequest = Field(default_factory=TransactionSideRequest)
    receive: TransactionSideRequest = Field(default_factory=TransactionSideRequest)
    player_id: str | None = None


class DebtTokensRequest(BaseModel):
    """Żetony długu (debt) między graczami (RULES.md 47.3): wystawca → posiadacz lub zwrot."""

    model_config = ConfigDict(extra="forbid")

    issuer_id: str
    holder_id: str
    count: int = 1
