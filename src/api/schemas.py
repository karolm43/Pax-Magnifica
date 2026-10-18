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
