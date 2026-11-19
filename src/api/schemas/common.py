"""DTO API: mapa, historia, Activity, koperta stanu, God-Mode, przeglądarka Zasad."""

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
    """Krawędź grafu mapy (sąsiedztwo geometryczne, wormhole albo portal ingress–egress)."""

    model_config = ConfigDict(extra="forbid")

    a: str
    b: str
    kind: Literal["adjacent", "wormhole", "portal"]


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


class PlayActionCardRequest(BaseModel):
    """Zagranie karty akcji z oknem ACTION jako akcji komponentu (RULES.md 53).

    `actor_id` (RULES.md 44.1) - kto wykonuje akcję; gdy podany, musi być równy `player_id`.
    `params` - wybory gracza zależne od karty (np. `{"planet": "jord"}`).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    card_id: str
    actor_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class StateEnvelope(BaseModel):
    """Koperta rozsyłana klientom: stan gry + metadane historii.

    Jest to jednocześnie ładunek wiadomości WebSocket (``type="state"``) i
    odpowiedź endpointów REST zmieniających stan.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["state"] = "state"
    state: GameState
    history: HistoryInfo


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
    # Wyłączenie limitu ręki kart akcji (testy; RULES.md 53.8).
    action_card_limit_disabled: bool | None = None
    # Cele publiczne (talie, odkryte, zdobyte) — nadpisuje CAŁY podstan celów.
    objectives: dict[str, object] | None = None
    players: dict[str, dict[str, object]] | None = None
    systems: dict[str, dict[str, object]] | None = None
    # Ziarno kości (testy scenariuszy: powtarzalne rzuty; licznik rzutów bez zmian).
    rng_seed: int | None = None


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


__all__ = [
    "ActivityEntry",
    "ActivityFeed",
    "ActivityPlayer",
    "GodModePatch",
    "HistoryEntry",
    "HistoryInfo",
    "HistoryList",
    "MapEdge",
    "MapStringRequest",
    "MapTile",
    "MapView",
    "PlanetUnits",
    "PlayActionCardRequest",
    "RulesIndexResponse",
    "StateEnvelope",
    "TopicContentDTO",
    "TopicGroupDTO",
    "TopicIndexEntryDTO",
    "UnitStack",
]
