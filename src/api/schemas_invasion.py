"""Schematy API inwazji (RULES.md 40): widok okna inwazji + żądania podkroków."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas import BattleLossItem, ExtraDieView


class InvasionUnitView(BaseModel):
    """Grupa jednostek (jeden typ) w widoku inwazji."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    count: int
    damaged: int = 0
    # Zdolność Sustain Damage wariantu (mech) i próg combat — do klikanego przypisania strat.
    sustain: bool = False
    base_hits_on: int = Field(default=0, serialization_alias="baseHitsOn")


class InvasionPlanetView(BaseModel):
    """Planeta aktywnego systemu: właściciel, siły, struktury, tarcza, lądowanie."""

    model_config = ConfigDict(populate_by_name=True)

    planet: str
    owner: str | None = None
    shielded: bool = False
    # Tarcza fizycznie stoi, ale war sun ją łamie (shielded=False) — animacja „zapadnięcia".
    has_shield: bool = Field(default=False, serialization_alias="hasShield")
    has_space_cannon: bool = Field(default=False, serialization_alias="hasSpaceCannon")
    # Siły naziemne i struktury per gracz (klucz tożsamości gracza).
    forces: dict[str, list[InvasionUnitView]] = Field(default_factory=dict)
    structures: dict[str, list[InvasionUnitView]] = Field(default_factory=dict)
    committed: dict[str, int] = Field(default_factory=dict)
    contested: bool = False
    bombardable: bool = False


class BombardGroupView(BaseModel):
    """Grupa statków z Bombardment: wartości z wariantu gracza."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    count: int
    hits_on: int = Field(serialization_alias="hitsOn")
    dice_per_unit: int = Field(serialization_alias="dicePerUnit")
    expected_hits: float = Field(serialization_alias="expectedHits")


class BombardPendingView(BaseModel):
    """Trafienia bombardowania czekające na przypisanie strat przez obrońcę planety."""

    planet: str
    defender: str
    hits: int
    required: int
    # Ile trafień anuluje jedno użycie Sustain Damage obrońcy (Non-Euclidean Shielding: 2).
    cancels: int = 1


class BombardView(BaseModel):
    """Stan podkroku Bombardment."""

    model_config = ConfigDict(populate_by_name=True)

    # Ile kości dodałby Plasma Scoring jednej jednostce (0 = atakujący nie ma tej technologii).
    plasma_dice: int = Field(default=0, serialization_alias="plasmaDice")
    # Źródła dodatkowych kości atakującego - każde przypisywane osobno (RULES.md 62.11).
    extra_dice: list[ExtraDieView] = Field(default_factory=list, serialization_alias="extraDice")
    groups: list[BombardGroupView] = Field(default_factory=list)
    targets: list[str] = Field(default_factory=list)
    done: bool = False
    pending: list[BombardPendingView] = Field(default_factory=list)


class DefenseShooterView(BaseModel):
    """Grupa strzelców Space Cannon Defense na planecie."""

    model_config = ConfigDict(populate_by_name=True)

    base_type: str = Field(serialization_alias="baseType")
    async_id: str = Field(serialization_alias="asyncId")
    name: str
    owner: str
    count: int
    hits_on: int = Field(serialization_alias="hitsOn")
    dice_per_unit: int = Field(serialization_alias="dicePerUnit")
    # Klucz grupy (wybór jednostki Plasma Scoring) i ile kości dodałby Plasma Scoring.
    key: str = ""
    plasma_dice: int = Field(default=0, serialization_alias="plasmaDice")


class DefensePlanetView(BaseModel):
    """Planeta ze Space Cannon Defense: strzelcy i status (open / pending / resolved)."""

    model_config = ConfigDict(populate_by_name=True)

    planet: str
    shooters: list[DefenseShooterView] = Field(default_factory=list)
    # Źródła dodatkowych kości obrońcy - każde przypisywane osobno (RULES.md 62.11).
    extra_dice: list[ExtraDieView] = Field(default_factory=list, serialization_alias="extraDice")
    status: str = "open"
    hits: int = 0
    required: int = 0
    # Ile trafień anuluje jedno użycie Sustain Damage atakującego (Non-Euclidean Shielding: 2).
    cancels: int = 1


class InvasionResponse(BaseModel):
    """Pełny stan okna inwazji (jeden odczyt na całe okno)."""

    model_config = ConfigDict(populate_by_name=True)

    active: bool
    # Prosta inwazja: nie ma co bombardować, nikt nie broni planet ani nie ma Space Cannon —
    # wystarczy lądowanie w panelu pomocy, bez pełnego okna (kroki 1, 3, 4 pominięte).
    simple: bool = False
    # Inwazja komponentu (Quantum Dissemination): klucz źródła, np. ``leaders:yinhero`` - zawsze
    # pełne okno, bez lądowania z orbity, Commit -> Ground Combat -> Establish Control.
    source: str = ""
    phase: str | None = None
    position: str | None = None
    attacker: str | None = None
    # Siły naziemne atakującego w przestrzeni systemu (do lądowania).
    cargo: list[InvasionUnitView] = Field(default_factory=list)
    planets: list[InvasionPlanetView] = Field(default_factory=list)
    bombard: BombardView = Field(default_factory=BombardView)
    defense: list[DefensePlanetView] = Field(default_factory=list)
    combat_planets: list[str] = Field(default_factory=list, serialization_alias="combatPlanets")
    in_combat: bool = Field(default=False, serialization_alias="inCombat")
    results: list[dict[str, Any]] = Field(default_factory=list)
    log: list[dict[str, Any]] = Field(default_factory=list)
    combat_results: dict[str, dict[str, Any]] = Field(
        default_factory=dict, serialization_alias="combatResults"
    )
    custodians: CustodiansView | None = None


class CustodiansView(BaseModel):
    """Żeton Custodians w oknie inwazji na Mecatol Rex (R_custodians_token)."""

    model_config = ConfigDict(populate_by_name=True)

    on_board: bool = Field(serialization_alias="onBoard")
    # Aktywny gracz zdjął żeton w tej inwazji (musi zlądować na Mecatol Rex).
    claimed: bool = False
    can_claim: bool = Field(default=False, serialization_alias="canClaim")
    reason: str | None = None
    cost: int
    # Gotowe planety atakującego → wpływ oraz trade goods do wydania.
    influence: dict[str, int] = Field(default_factory=dict)
    trade_goods: int = Field(default=0, serialization_alias="tradeGoods")
    # Wartość 1 TG w płatności (Mirror Computing: 2, RULES.md 62.8).
    trade_good_value: int = Field(default=1, serialization_alias="tradeGoodValue")
    # Planety, na które nie wolno lądować, dopóki żeton leży.
    blocked_planets: list[str] = Field(default_factory=list, serialization_alias="blockedPlanets")


class InvasionCustodiansRequest(BaseModel):
    """Zdjęcie żetonu Custodians: planety do wyczerpania i trade goods."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    planets: list[str] = Field(default_factory=list)
    trade_goods: int = Field(default=0, alias="tradeGoods")


class InvasionBombardItem(BaseModel):
    """Przydział statków do bombardowania planety."""

    model_config = ConfigDict(extra="forbid")

    base_type: str = Field(alias="baseType")
    planet: str
    count: int = 1


class InvasionBombardRequest(BaseModel):
    """Bombardowanie: lista przydziałów (każda jednostka z Bombardment musi być użyta)."""

    model_config = ConfigDict(extra="forbid")

    assignments: list[InvasionBombardItem]
    # Przydział (typ|planeta), którego jednostka rzuca 1 kością więcej (Plasma Scoring, "may").
    plasma_unit: str | None = Field(default=None, alias="plasmaUnit")
    # Każde źródło dodatkowych kości osobno: ``{źródło: przydział | auto | none}``.
    extra_dice: dict[str, str] | None = Field(default=None, alias="extraDice")


class InvasionCommitItem(BaseModel):
    """Lądowanie ``count`` sił naziemnych typu ``base_type`` na ``planet``."""

    model_config = ConfigDict(extra="forbid")

    planet: str
    base_type: str = Field(alias="baseType")
    count: int = 1


class InvasionCommitRequest(BaseModel):
    """Commit Ground Forces: lista lądowań."""

    model_config = ConfigDict(extra="forbid")

    commits: list[InvasionCommitItem]


class InvasionPlanetRequest(BaseModel):
    """Wskazanie planety (Space Cannon Defense: strzał / rezygnacja)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    planet: str
    # Space Cannon Defense: klucz grupy strzelców z dodatkową kością (Plasma Scoring, "may").
    plasma_unit: str | None = Field(default=None, alias="plasmaUnit")
    # Każde źródło dodatkowych kości osobno: ``{źródło: klucz grupy | auto | none}``.
    extra_dice: dict[str, str] | None = Field(default=None, alias="extraDice")


class InvasionAssignRequest(BaseModel):
    """Pokrycie trafień na planecie: Sustain Damage + niszczone jednostki."""

    model_config = ConfigDict(extra="forbid")

    planet: str
    faction: str
    sustain: list[BattleLossItem] = Field(default_factory=list)
    destroy: list[BattleLossItem] = Field(default_factory=list)
    destroy_damaged: list[BattleLossItem] = Field(
        default_factory=list, alias="destroyDamaged"
    )
