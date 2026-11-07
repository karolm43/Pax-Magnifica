"""Schematy API inwazji (RULES.md 40): widok okna inwazji + żądania podkroków."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas import BattleLossItem


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


class BombardView(BaseModel):
    """Stan podkroku Bombardment."""

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


class DefensePlanetView(BaseModel):
    """Planeta ze Space Cannon Defense: strzelcy i status (open / pending / resolved)."""

    planet: str
    shooters: list[DefenseShooterView] = Field(default_factory=list)
    status: str = "open"
    hits: int = 0
    required: int = 0


class InvasionResponse(BaseModel):
    """Pełny stan okna inwazji (jeden odczyt na całe okno)."""

    model_config = ConfigDict(populate_by_name=True)

    active: bool
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

    model_config = ConfigDict(extra="forbid")

    planet: str


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
