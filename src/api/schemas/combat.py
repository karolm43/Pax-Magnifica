"""DTO API: Space Cannon Offense (RULES.md 38) i okno pola bitwy (RULES.md 39)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
    # Klucz grupy (wybór jednostki Plasma Scoring) i ile kości dodałby Plasma Scoring (0 = brak).
    key: str = ""
    plasma_dice: int = Field(default=0, serialization_alias="plasmaDice")


class ExtraDieView(BaseModel):
    """Źródło dodatkowych kości AFB i wybór gracza (``auto`` / ``none`` / base_type)."""

    key: str
    name: str
    dice: int
    pick: str = "auto"


class SpaceCannonSideHelp(BaseModel):
    """Strona w kolejce Space Cannon: gracz, jego strzelcy i legalne cele."""

    model_config = ConfigDict(populate_by_name=True)

    faction: str
    player_id: str = Field(serialization_alias="playerId")
    shooters: list[SpaceCannonShooterHelp]
    # Źródła dodatkowych kości (Plasma Scoring, commander Argent, Ambuscade) - każde osobno.
    extra_dice: list[ExtraDieView] = Field(default_factory=list, serialization_alias="extraDice")
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
    # Modyfikator wyniku kości celu (Antimass Deflectors: -1) i kość dodana przez Plasma Scoring.
    modifier: int = 0
    extra_dice: int = Field(default=0, serialization_alias="extraDice")


class SpaceCannonPendingHelp(BaseModel):
    """Trafienia czekające na przypisanie strat."""

    roller: str
    target: str
    hits: int
    required: int  # ile statków trzeba zniszczyć (min(trafienia, statki celu))
    rolls: list[SpaceCannonRollHelp]
    # Ile trafień anuluje jedno użycie Sustain Damage celu (Non-Euclidean Shielding: 2).
    cancels: int = 1


class SpaceCannonShipHelp(BaseModel):
    """Statek gracza-celu w aktywnym systemie (do przypisania strat)."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    count: int
    # Ile już uszkodzonych i czy typ może użyć Sustain Damage (R_sustain_damage).
    damaged: int = 0
    sustain: bool = False


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
    # Gracz ŚWIADOMIE wyczerpuje Graviton Laser System przed strzałem (RULES.md 57).
    exhaust_gls: bool = False
    # Klucz grupy strzelców, której jednostka rzuca 1 kością więcej (Plasma Scoring, "may").
    plasma_unit: str | None = None
    # Każde źródło dodatkowych kości osobno: ``{źródło: klucz grupy | auto | none}``.
    extra_dice: dict[str, str] | None = Field(default=None, alias="extraDice")


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
    # Niszczone NIEUSZKODZONE statki (dawne pole — zgodność wstecz).
    losses: list[SpaceCannonLossItem] = Field(default_factory=list)
    # Sustain Damage (R_sustain_damage: działa też przeciw Space Cannon) i niszczone uszkodzone.
    sustain: list[SpaceCannonLossItem] = Field(default_factory=list)
    destroy_damaged: list[SpaceCannonLossItem] = Field(
        default_factory=list, alias="destroyDamaged"
    )


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


class BattleEffectView(BaseModel):
    """Efekt komponentu w walce do animacji (np. Assault Cannon: strzelec, ofiara, typ statku)."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str
    player: str  # klucz frakcji właściciela komponentu
    victim: str  # klucz frakcji ofiary
    unit: str  # base type zniszczonego statku


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
    # Ile trafień anuluje jedno użycie Sustain Damage (1; Non-Euclidean Shielding: 2).
    sustain_cancels: int = Field(default=1, serialization_alias="sustainCancels")


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
    """Wpis historii walki: runda, faza (AFB/COMBAT/AMBUSH/BOMBARDMENT), rzuty, trafienia."""

    round: int
    phase: str
    # Nazwa zdolności wpisu spoza rund (np. „Harrow” przy BOMBARDMENT w walce naziemnej).
    label: str = ""
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
    # Odwrót przez Ion Storm w systemie z własnym wormholem tego typu: gracz wybiera wormhole.
    ion_storm_choice: bool = Field(default=False, serialization_alias="ionStormChoice")


class BattleRelicToolView(BaseModel):
    """Narzędzie reliktu nad rzutami rundy: ``reroll`` (Thalnos) albo ``adjust`` (Heart)."""

    faction: str
    tool: str


class BattleAbilityToolView(BaseModel):
    """Zdolność frakcji zmieniająca kości rundy (np. Munitions Reserves): wybór kości + użycie."""

    model_config = ConfigDict(populate_by_name=True)

    faction: str
    player_id: str = Field(serialization_alias="playerId")
    kind: str
    component_id: str = Field(serialization_alias="componentId")
    name: str
    text: str
    min: int
    max: int


class BattleHitTargetView(BaseModel):
    """Wymuszony cel trafień strony (Devotion: wskazany statek; Impulse Core: nie-myśliwce).

    ``damaged`` = stan wskazanego egzemplarza (``None`` = dowolny tego typu); ``chooser`` =
    strona (klucz frakcji), która wskazała cel (pusta, gdy wybiera sam przypisujący).
    """

    types: list[str]
    count: int
    label: str
    damaged: bool | None = None
    chooser: str = ""


class BattleExtraDiceRequest(BaseModel):
    """Przypisanie dodatkowych kości AFB: ``{źródło: base_type | auto | none}``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    player_id: str = Field(alias="playerId")
    picks: dict[str, str] = Field(default_factory=dict)


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
    # Walka czeka na reakcje po Sustain Damage ostatniej strony (Direct Hit, Reflective Shielding).
    sustain_hold: bool = Field(default=False, serialization_alias="sustainHold")
    hit_targets: dict[str, BattleHitTargetView] = Field(
        default_factory=dict, serialization_alias="hitTargets"
    )
    rolls: dict[str, list[BattleRollView]] = Field(default_factory=dict)
    afb: dict[str, list[BattleRollView]] = Field(default_factory=dict)
    log: list[BattleLogView] = Field(default_factory=list)
    # Jednorazowe efekty poza rundami (Assault Cannon) — okno bitwy je animuje.
    effects: list[BattleEffectView] = Field(default_factory=list)
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
    # Relikty zmieniające kości po rzucie, przed przypisaniem strat (RULES.md 59).
    relic_tools: list[BattleRelicToolView] = Field(
        default_factory=list, serialization_alias="relicTools"
    )
    ability_tools: list[BattleAbilityToolView] = Field(
        default_factory=list, serialization_alias="abilityTools"
    )
    # Dodatkowe kości AFB do przypisania przed rzutem (klucz = strona walki, RULES.md 62.11).
    afb_extra: dict[str, list[ExtraDieView]] = Field(
        default_factory=dict, serialization_alias="afbExtra"
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
    # Odwrót przez Ion Storm w systemie z własnym wormholem tego typu (jak w ruchu).
    ion_storm_token: bool | None = Field(default=None, alias="ionStormToken")


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


class BattleRelicPick(BaseModel):
    """Kości jednego wpisu rzutu wybrane do przerzutu."""

    model_config = ConfigDict(extra="forbid")

    entry: int
    dice: list[int]


class BattleRelicRerollRequest(BaseModel):
    """Przerzut kości z +1 (Crown of Thalnos): wybrane kości własnych rzutów rundy."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    picks: list[BattleRelicPick]


class BattleRelicAdjustRequest(BaseModel):
    """Zmiana wyniku jednej kości o ±1 (Heart of Ixth) w rzucie strony ``target``."""

    model_config = ConfigDict(extra="forbid")

    faction: str
    target: str
    entry: int
    die: int
    delta: int


__all__ = [
    "BattleAbilityToolView",
    "BattleAnnounceRetreatRequest",
    "BattleAssignRequest",
    "BattleEffectView",
    "BattleExtraDiceRequest",
    "BattleHitTargetView",
    "BattleLogView",
    "BattleLossItem",
    "BattleRelicAdjustRequest",
    "BattleRelicPick",
    "BattleRelicRerollRequest",
    "BattleRelicToolView",
    "BattleResponse",
    "BattleRetreatRequest",
    "BattleRollView",
    "BattleSideView",
    "BattleStartRequest",
    "BattleUnitView",
    "ExtraDieView",
    "RetreatCargoItem",
    "RetreatOptionView",
    "SpaceCannonAssignRequest",
    "SpaceCannonFireRequest",
    "SpaceCannonLogEntry",
    "SpaceCannonLossItem",
    "SpaceCannonPanelResponse",
    "SpaceCannonPassRequest",
    "SpaceCannonPendingHelp",
    "SpaceCannonRollHelp",
    "SpaceCannonShipHelp",
    "SpaceCannonShooterHelp",
    "SpaceCannonSideHelp",
]
