"""Schematy API łączenia fragmentów reliktów w relikt (RULES.md 59.7)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas import StateEnvelope


class ForgeOption(BaseModel):
    """Typ fragmentów z ACTION gracza i czy zestaw da się teraz połączyć."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str
    needed: int
    owned: int
    wildcards: int
    fragments: list[str] = Field(default_factory=list)
    reason: str | None = None
    deck_empty: bool = Field(default=False, alias="deckEmpty")


class ForgeOptionsResponse(BaseModel):
    """Legalne zestawy fragmentów gracza (UI pokazuje przycisk „Forge relic”)."""

    options: list[ForgeOption]


class ForgeRelicRequest(BaseModel):
    """Purge zestawu fragmentów za relikt — akcja komponentu gracza (RULES.md 59.7).

    `actor_id` (RULES.md 44.1) - kto wykonuje akcję; gdy podany, musi być równy `player_id`.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    fragments: list[str]
    actor_id: str | None = None


class ForgeRelicResponse(BaseModel):
    """Stan po akcji + dobrany relikt (``None`` = talia była pusta)."""

    envelope: StateEnvelope
    relic_id: str | None = None
