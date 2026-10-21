"""Schematy DTO warstwy API (Pydantic v2).

Oddzielają kontrakt sieciowy od wewnętrznych modeli domenowych. Mapa jest
serializowana jako lista pozycji ze współrzędnymi kubicznymi (dla renderera SVG)
oraz lista krawędzi sąsiedztwa. God-Mode używa generycznego patcha w tym bloku;
typowane kreatory (wizards) dojdą w kolejnych blokach.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.core.game_state import GameState


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


class StateEnvelope(BaseModel):
    """Koperta rozsyłana klientom: stan gry + metadane historii.

    Jest to jednocześnie ładunek wiadomości WebSocket (``type="state"``) i
    odpowiedź endpointów REST zmieniających stan.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["state"] = "state"
    state: GameState
    history: HistoryInfo


class FactionInfo(BaseModel):
    """Informacja o frakcji dla ekranu wyboru (setup)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    home_system: str | None = None
    home_planets: list[str] = Field(default_factory=list)
    starting_fleet: str | None = None
    preferred_colours: list[str] = Field(default_factory=list)


class SetupPlayerRequest(BaseModel):
    """Żądanie setupu gracza: frakcja + kolor na wskazanym slocie domowym."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    faction_id: str
    color: str
    home_position: str


class NewGamePlayer(BaseModel):
    """Pojedynczy gracz w żądaniu nowej gry (frakcja; reszta auto)."""

    model_config = ConfigDict(extra="forbid")

    faction_id: str
    # Opcjonalne: gdy pominięte, kolor/slot/id przydzielane automatycznie
    # wg kolejności (gracz 1 → red/301, 2 → green/304, ...).
    player_id: str | None = None
    color: str | None = None
    home_position: str | None = None


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
    technologies: list[str] | None = None
    # Stan liderów: {leader_id: "locked"|"unlocked"|"exhausted"}.
    leader_states: dict[str, str] | None = None


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
    players: dict[str, dict[str, object]] | None = None
    systems: dict[str, dict[str, object]] | None = None
