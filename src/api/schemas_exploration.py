"""Schematy API eksploracji (RULES.md 46): widok okna eksploracji + żądania."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExploreParamView(BaseModel):
    """Dodatkowy wybór opcji (np. pula żetonu dowodzenia)."""

    id: str
    label: str


class ExploreOptionView(BaseModel):
    """Opcja rozstrzygnięcia ujawnionej karty."""

    id: str
    label: str
    enabled: bool = True
    reason: str = ""
    params: list[ExploreParamView] = Field(default_factory=list)


class ExploreCardView(BaseModel):
    """Karta eksploracji (dane z katalogu komponentów)."""

    model_config = ConfigDict(populate_by_name=True)

    card_id: str = Field(serialization_alias="cardId")
    name: str
    deck: str
    resolution: str
    text: str
    flavor_text: str = Field(default="", serialization_alias="flavorText")


class ExploreQueueItem(BaseModel):
    """Planeta czekająca na eksplorację (gracz wybiera kolejność i — przy kilku cechach — talię)."""

    model_config = ConfigDict(populate_by_name=True)

    planet: str
    traits: list[str]
    # Distant Suns: gracz może dobrać 1 dodatkową kartę (decyzja przed ujawnieniem).
    extra_draw: bool = Field(default=False, serialization_alias="extraDraw")


class ExploreCurrentView(BaseModel):
    """Ujawniona karta + planeta + opcje jej rozstrzygnięcia."""

    planet: str
    card: ExploreCardView
    options: list[ExploreOptionView]
    # Distant Suns: dobrane karty do wyboru (niepuste = gracz wybiera jedną, ``card`` to pierwsza).
    candidates: list[ExploreCardView] = Field(default_factory=list)


class ExploreLogItem(BaseModel):
    """Rozstrzygnięta karta (historia okna)."""

    model_config = ConfigDict(populate_by_name=True)

    planet: str
    deck: str
    card: ExploreCardView
    summary: str
    fate: str


class ExplorationResponse(BaseModel):
    """Widok okna eksploracji (``active=False``, gdy żadna nie trwa)."""

    model_config = ConfigDict(populate_by_name=True)

    active: bool
    player: str | None = None
    position: str | None = None
    queue: list[ExploreQueueItem] = Field(default_factory=list)
    current: ExploreCurrentView | None = None
    log: list[ExploreLogItem] = Field(default_factory=list)
    # Wszystko rozstrzygnięte — zostaje zamknąć okno.
    done: bool = False


class ExplorationDrawRequest(BaseModel):
    """Wybór planety (kolejność) i opcjonalnie talii (planeta z kilkoma cechami)."""

    planet: str
    deck: str | None = None
    # Distant Suns: dobierz 1 dodatkową kartę (wybór jednej z nich - ``/exploration/choose``).
    extra: bool = False


class ExplorationChooseRequest(BaseModel):
    """Karta wybrana do rozstrzygnięcia spośród dobranych (Distant Suns)."""

    card: str


class ExplorationResolveRequest(BaseModel):
    """Wybrana opcja rozstrzygnięcia karty (+ parametr, gdy opcja go wymaga)."""

    option: str
    param: str | None = None
