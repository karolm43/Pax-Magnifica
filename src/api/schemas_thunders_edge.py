"""Schematy API modułu Thunder's Edge (RULES.md 50): ekspedycje, The Fracture, Thunder's Edge."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SlicePayment(BaseModel):
    """Czym gracz płaci za plaster (używane pola zależą od plastra)."""

    planets: list[str] = Field(default_factory=list)
    trade_goods: int = 0
    action_cards: list[str] = Field(default_factory=list)
    secret: str | None = None
    tech_planet: str | None = None


class ExpeditionRequest(BaseModel):
    """Wykonanie ekspedycji przez gracza (RULES.md 44.1: ``actor_id``; brak = aktywny gracz)."""

    actor_id: str | None = None
    slice: str
    payment: SlicePayment = Field(default_factory=SlicePayment)


class IngressRequest(BaseModel):
    """Wybór systemu na żeton ingress dla koloru technologii."""

    actor_id: str | None = None
    color: str
    position: str


class ThundersEdgeRequest(BaseModel):
    """Położenie Thunder's Edge w systemie (+ wybór piechoty przy remisie)."""

    actor_id: str | None = None
    position: str
    infantry_player_id: str | None = None


class FractureEnterRequest(BaseModel):
    """God-Mode: wprowadza The Fracture do gry bez rzutu (``breakthrough_id`` = synergia)."""

    actor_id: str | None = None
    breakthrough_id: str | None = None


class SliceView(BaseModel):
    """Plaster żetonu ekspedycji."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    claimed_by: str | None = Field(default=None, serialization_alias="claimedBy")


class IngressChoiceView(BaseModel):
    """Oczekujący wybór ingress: kolor, ile jeszcze, i systemy do wyboru."""

    color: str
    remaining: int
    candidates: list[str]


class PaymentOptions(BaseModel):
    """Czym AKTYWNY gracz może zapłacić za plaster (gotowe planety i trade goods)."""

    model_config = ConfigDict(populate_by_name=True)

    resources: dict[str, int] = Field(default_factory=dict)
    influence: dict[str, int] = Field(default_factory=dict)
    trade_goods: int = Field(default=0, serialization_alias="tradeGoods")
    specialty_planets: list[str] = Field(
        default_factory=list, serialization_alias="specialtyPlanets"
    )


class ThundersEdgeView(BaseModel):
    """Widok całego modułu dla UI (jeden endpoint ``GET /thunders-edge``)."""

    model_config = ConfigDict(populate_by_name=True)

    slices: list[SliceView]
    free_slices: list[str] = Field(serialization_alias="freeSlices")
    # Gracz, który może TERAZ wykonać ekspedycję (aktywny, po akcji/pasie) i powód blokady.
    can_perform: bool = Field(serialization_alias="canPerform")
    block_reason: str = Field(default="", serialization_alias="blockReason")
    fracture_in_play: bool = Field(serialization_alias="fractureInPlay")
    fracture_entered_by: str | None = Field(default=None, serialization_alias="fractureEnteredBy")
    last_roll: dict[str, Any] | None = Field(default=None, serialization_alias="lastRoll")
    pending_ingress: list[IngressChoiceView] = Field(
        default_factory=list, serialization_alias="pendingIngress"
    )
    # Thunder's Edge czeka na położenie: gracz, systemy do wyboru, remis o piechotę.
    placement_player: str | None = Field(default=None, serialization_alias="placementPlayer")
    placement_targets: list[str] = Field(
        default_factory=list, serialization_alias="placementTargets"
    )
    placement_counts: dict[str, int] = Field(
        default_factory=dict, serialization_alias="placementCounts"
    )
    placement_leaders: list[str] = Field(
        default_factory=list, serialization_alias="placementLeaders"
    )
    thunders_edge_position: str | None = Field(
        default=None, serialization_alias="thundersEdgePosition"
    )
    payment: PaymentOptions = Field(default_factory=PaymentOptions)
    # Identyfikatory graczy w widoku to ID SILNIKA; ta mapa daje ich klucz tożsamości z web-data
    # (faction/kolor), żeby UI mógł pokazać portret / kolor.
    players: dict[str, str] = Field(default_factory=dict)
    log: list[dict[str, Any]] = Field(default_factory=list)
