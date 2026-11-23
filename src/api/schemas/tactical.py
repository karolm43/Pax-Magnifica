"""DTO API: ruch, akcja taktyczna, pomoc walki, produkcja, okna czasowe."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    # System, z którego statki zabierają ładunek (pickup po drodze, RULES.md 32.3 T3).
    # Brak = system startu ruchu; inny musi leżeć na ``route`` żądania.
    from_position: str | None = Field(default=None, alias="fromPosition")


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
    # Gracz ŚWIADOMIE używa Gravity Drive (+1 do ruchu jednego statku w tej akcji).
    gravity_drive: bool = Field(default=False, alias="gravityDrive")
    # Gracz ŚWIADOMIE używa Ionian Fuel Refinery (+1 do ruchu jednego statku w tej akcji).
    tempesta: bool = False
    # Gracz ŚWIADOMIE używa premii Imperatora (Winnu: +1 do ruchu jednego statku w tej akcji).
    imperator: bool = False
    # Trasa wybrana przez gracza: systemy od źródła do aktywnego (None = najkrótsza legalna).
    route: list[str] | None = None
    # Ion Storm w systemie z własnym wormholem tego typu: True = przez żeton (obraca się),
    # False = przez własny wormhole systemu. Wymagane tylko wtedy (``ionStormChoice`` w podglądzie).
    ion_storm_token: bool | None = Field(default=None, alias="ionStormToken")


class MoveRouteShip(BaseModel):
    """Statek ze źródła ruchu w podglądzie trasy."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(alias="baseType")
    count: int
    capacity: int
    reachable: bool
    # Dolatuje sam, bez premii i bez towarzyszy.
    alone: bool
    # Typy statków, z którymi dolatuje bez premii, gdy lecą razem (Gravleash Maneuvers).
    with_ships: list[str] = Field(default_factory=list, alias="withShips")
    # Zestawy premii (gravity_drive / tempesta), z którymi dolatuje.
    bonus_options: list[list[str]] = Field(default_factory=list, alias="bonusOptions")
    # Ile sztuk wolno ruszyć z premią (1, a z Gravleash cała grupa).
    bonus_max: int = Field(alias="bonusMax")
    reason: str


class MoveRouteCargo(BaseModel):
    """Ładunek (myśliwce / siły naziemne) do zabrania w systemie na trasie."""

    model_config = ConfigDict(populate_by_name=True)

    position: str
    zone: str
    base_type: str = Field(alias="baseType")
    count: int
    capacity_used: int = Field(alias="capacityUsed")


class MoveRouteResponse(BaseModel):
    """Podgląd trasy ruchu (RULES.md 32.1, 32.3): trasa, alternatywy, waypointy, statki, ładunek."""

    model_config = ConfigDict(populate_by_name=True)

    active: str | None
    route: list[str] | None
    reason: str
    alternatives: list[list[str]] = Field(default_factory=list)
    waypoints: list[str] = Field(default_factory=list)
    ships: list[MoveRouteShip] = Field(default_factory=list)
    cargo: list[MoveRouteCargo] = Field(default_factory=list)
    rift_nodes: list[str] = Field(default_factory=list, alias="riftNodes")
    # Czy statki rzucają za szczeliny (Circlet of the Void: +1 do ruchu bez rzutu).
    rift_rolls: bool = Field(default=True, alias="riftRolls")
    # Premie +1 do ruchu, które gracz może teraz włączyć (gravity_drive / tempesta).
    bonuses: list[str] = Field(default_factory=list)
    # Trasa przechodzi przez Ion Storm w systemie z własnym wormholem tego typu: gracz wybiera,
    # którego wormholu używa (``ionStormToken`` w ruchu). Pozycja systemu z żetonem albo None.
    ion_storm_choice: str | None = Field(default=None, alias="ionStormChoice")


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
    # Wybory gracza dla efektu technologii z „ACTION:" (formularz z GET /technology/{id}/form).
    params: dict[str, Any] = Field(default_factory=dict)


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
    # Pusta rezerwa: źródła na planszy (``"<pozycja>|<strefa>"``), z których gracz zdejmuje
    # jednostki tego typu (R_component_limitations).
    sources: list[str] = Field(default_factory=list)


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
    # Gracz ŚWIADOMIE wyczerpuje AI Development Algorithm (zniżka = liczba ulepszeń jednostek).
    exhaust_aida: bool = False
    # Amalgamation (RULES.md 62.17): przechwycone jednostki zwracane zamiast zasobów
    # {typ: {pierwotny właściciel | "token": sztuki}}.
    captured: dict[str, dict[str, int]] = Field(default_factory=dict)
    # Tungstantus (RULES.md 62.18): 1 TG „when your units use PRODUCTION” - przed zapłatą.
    commander_trade_good: bool = False

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


__all__ = [
    "ActivateSystemRequest",
    "CapturePlanetRequest",
    "CombatHelpResponse",
    "CombatSideHelp",
    "CombatUnitHelp",
    "CommandTokenRequest",
    "ComponentActionRequest",
    "MoveCargoItem",
    "MoveRangeResponse",
    "MoveRouteCargo",
    "MoveRouteResponse",
    "MoveRouteShip",
    "MoveShipsRequest",
    "ProduceOrderItem",
    "ProduceRequest",
    "ProduceSpend",
    "ProducibleUnitHelp",
    "ProductionHelpResponse",
    "TacticalStepRequest",
    "WindowOpenRequest",
]
