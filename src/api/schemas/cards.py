"""DTO API: transakcje, karty akcji, reakcje, relikty, okna czasowe, Undo gracza."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.api.schemas.common import StateEnvelope


class TransactionSideRequest(BaseModel):
    """Strona stołu: to, co gracz kładzie (ODDAJE partnerowi) — RULES.md 47.1b."""

    model_config = ConfigDict(extra="forbid")

    trade_goods: int = 0
    commodities: int = 0
    promissory_note: str | None = None
    relic_fragments: list[str] = Field(default_factory=list)
    # Karty akcji (Arbiters / Black Market Dealings) — silnik odrzuci je bez takiego efektu.
    action_cards: list[str] = Field(default_factory=list)
    # Karty planet (Pride of Kenara): ``"<planeta>><planeta docelowa>"``.
    planets: list[str] = Field(default_factory=list)
    # Przechwycone statki/mechy partnera zwracane mu (typy bazowe, RULES.md 61.5).
    captured_units: list[str] = Field(default_factory=list)
    # Żetony długu (47.3), darmowe secondary Trade i obietnica „wash −N” (47.4).
    debt_tokens: int = 0
    trade_secondary: bool = False
    wash: int | None = None


class TransactionTableRequest(BaseModel):
    """Otwarcie / zamknięcie stołu z ``partner_id`` (RULES.md 47.1b)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    partner_id: str


class TransactionTableSideRequest(TransactionTableRequest):
    """Gracz kładzie swoją stronę na stół (zastępuje poprzednią)."""

    side: TransactionSideRequest = Field(default_factory=TransactionSideRequest)


class TransactionTableReadyRequest(TransactionTableRequest):
    """Gracz potwierdza (albo cofa) obecny stan stołu."""

    ready: bool = True


class TransactionSideView(BaseModel):
    """Strona stołu: co dany gracz położył (widoczne tylko dla stron stołu)."""

    model_config = ConfigDict(populate_by_name=True)

    trade_goods: int = Field(0, serialization_alias="tradeGoods")
    commodities: int = 0
    promissory_note: str | None = Field(None, serialization_alias="promissoryNote")
    relic_fragments: list[str] = Field(default_factory=list, serialization_alias="relicFragments")
    action_cards: list[str] = Field(default_factory=list, serialization_alias="actionCards")
    relics: list[str] = Field(default_factory=list)
    secret_objectives: list[str] = Field(
        default_factory=list, serialization_alias="secretObjectives"
    )
    planets: list[str] = Field(default_factory=list)
    captured_units: list[str] = Field(default_factory=list, serialization_alias="capturedUnits")
    debt_tokens: int = Field(0, serialization_alias="debtTokens")
    trade_secondary: bool = Field(False, serialization_alias="tradeSecondary")
    wash: int | None = None


class TransactionTableView(BaseModel):
    """Stół, przy którym siedzi oglądający: obie strony + Ready + co wolno położyć."""

    model_config = ConfigDict(populate_by_name=True)

    partner: str
    partner_color: str | None = Field(None, serialization_alias="partnerColor")
    mine: TransactionSideView
    theirs: TransactionSideView
    my_ready: bool = Field(False, serialization_alias="myReady")
    their_ready: bool = Field(False, serialization_alias="theirReady")
    # Wolno teraz kłaść komponenty (inaczej tylko dług) i karty akcji (Arbiters / BMD).
    components: bool = False
    action_cards: bool = Field(False, serialization_alias="actionCards")
    extras: bool = False
    # Krok 3 Trade: ja jestem posiadaczem (mogę dać darmowe secondary) / partner jest (wash).
    trade_holder: bool = Field(False, serialization_alias="tradeHolder")
    trade_partner: bool = Field(False, serialization_alias="tradePartner")
    # Umowa Trade: komponenty z wash przejdą po uzupełnieniu (sąsiad / Guild Ships).
    deal_components: bool = Field(False, serialization_alias="dealComponents")
    prefilled: bool = False
    # Moje relikty, które wolno teraz położyć (Black Market Dealings albo The Silver Flame).
    tradable_relics: list[str] = Field(
        default_factory=list, serialization_alias="tradableRelics"
    )


class TransactionPartnerView(BaseModel):
    """Gracz, z którym oglądający może usiąść do stołu."""

    model_config = ConfigDict(populate_by_name=True)

    player_id: str = Field(serialization_alias="playerId")
    color: str | None = None
    # Sąsiad (albo Guild Ships / Trade Convoys) — inaczej stół tylko na dług.
    neighbor: bool = True
    # Komponenty wolno teraz wymieniać (jego/moja tura, bez transakcji w tej turze).
    components: bool = False
    done: bool = False


class TransactionStateResponse(BaseModel):
    """Stoły oglądającego + gracze, z którymi może usiąść (RULES.md 47.1b)."""

    model_config = ConfigDict(populate_by_name=True)

    tables: list[TransactionTableView] = Field(default_factory=list)
    partners: list[TransactionPartnerView] = Field(default_factory=list)
    # Planety, których kartę oglądający może oddać (Pride of Kenara).
    my_planets: list[str] = Field(default_factory=list, serialization_alias="myPlanets")
    # Gracze wskazani umową w kroku 3 Trade (zablokowani jako „free”).
    deal_players: list[str] = Field(default_factory=list, serialization_alias="dealPlayers")


class DebtTokensRequest(BaseModel):
    """Żetony długu (debt) między graczami (RULES.md 47.3): wystawca → posiadacz lub zwrot."""

    model_config = ConfigDict(extra="forbid")

    issuer_id: str
    holder_id: str
    count: int = 1


class PlayActionCardResponse(BaseModel):
    """Wynik zagrania karty: stan + czy silnik zastosował efekt (false = rozstrzyga operator)."""

    envelope: StateEnvelope
    implemented: bool
    # True = efekt czeka w ``held_play`` na ewentualne Sabotage (RULES.md 53.6).
    held: bool = False


class HeldActionRequest(BaseModel):
    """Pas / zwolnienie okna hold-play (``/action-card/held/pass`` i ``.../release``)."""

    actor_id: str


class AutoPassRequest(BaseModel):
    """„Skip all reactions” gracza (``/reaction-settings/auto-pass``, RULES.md 54.11)."""

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    enabled: bool


class QuickWindowsRequest(BaseModel):
    """„Quick windows” hosta (``/reaction-settings/quick``, RULES.md 54.12)."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool


class ReactionPrefsRequest(BaseModel):
    """Zmiana prywatnych preferencji reakcji (``/reaction-settings/prefs``, RULES.md 54.12).

    ``declare``: kategoria -> czas trwania (``None`` = odwołanie); ``mute_*``: klucz -> wł./wył.
    Pola pominięte zostają bez zmian.
    """

    model_config = ConfigDict(extra="forbid")

    actor_id: str
    declare: dict[str, str | None] | None = None
    only_involved: bool | None = None
    mute_cards: dict[str, bool] | None = None
    mute_offers: dict[str, bool] | None = None


class ReactionWindowRequest(BaseModel):
    """Długość okien reakcji ustawiana przez hosta (``/reaction-settings/window``, 54.11)."""

    model_config = ConfigDict(extra="forbid")

    seconds: int = Field(ge=2, le=30)


class ActionCardInputsResponse(BaseModel):
    """Opis formularza zagrania karty akcji: tekst karty i wybory gracza (RULES.md 53)."""

    card_id: str
    name: str
    text: str
    implemented: bool
    inputs: list[dict[str, Any]]
    # Krótki opis „dotyczy: …" z bieżącego stanu gracza (None = brak podglądu dla karty).
    summary: str | None = None


class ActionCardPlayability(BaseModel):
    """Czy karta z ręki jest zagrywalna teraz jako akcja (przeciąganie z ręki w UI)."""

    card_id: str
    playable: bool
    reason: str | None = None
    implemented: bool = False
    reaction: bool = False  # karta reakcji (okno inne niż ACTION) - RULES.md 54.8
    # Okno minęło ostatnim krokiem (Public Disgrace po wyborze rywala): zagranie = hold-rewind
    # do tej migawki (RULES.md 53.7). ``None`` = zwykłe zagranie w bieżącym stanie.
    hold_seq: int | None = None


class ActionCardPlayabilityResponse(BaseModel):
    """Zagrywalność wszystkich unikalnych kart akcji z ręki gracza.

    ``discard`` — ile kart gracz musi odrzucić do limitu ręki (R_action_cards; 0 = w limicie).
    """

    model_config = ConfigDict(populate_by_name=True)

    cards: list[ActionCardPlayability]
    discard: int = 0
    hand_limit: int | None = Field(default=None, alias="handLimit")


class DiscardExcessRequest(BaseModel):
    """Odrzucenie wybranej karty akcji ponad limit ręki (``/action-card/discard-excess``)."""

    actor_id: str
    card_id: str


class PlayRelicRequest(BaseModel):
    """Zagranie „ACTION:” reliktu jako akcji komponentu (RULES.md 59).

    `actor_id` (RULES.md 44.1) - kto wykonuje akcję; gdy podany, musi być równy `player_id`.
    `params` - wybory gracza zależne od reliktu (np. `{"planet": "jord"}`).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    relic_id: str
    actor_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class PlayRelicResponse(BaseModel):
    """Wynik zagrania reliktu: stan + czy silnik zastosował efekt (false = rozstrzyga operator)."""

    envelope: StateEnvelope
    implemented: bool


class RelicInputsResponse(BaseModel):
    """Opis reliktu i formularza jego ACTION: tekst karty, rodzaj i wybory gracza."""

    relic_id: str
    name: str
    text: str
    kind: str  # "action" | "passive"
    implemented: bool
    exhausted: bool = False
    inputs: list[dict[str, Any]]
    summary: str | None = None


class RelicPlayability(BaseModel):
    """Relikt gracza i czy jego ACTION jest zagrywalna teraz (zakładka Relics na ręce)."""

    relic_id: str
    kind: str  # "action" | "passive"
    playable: bool
    reason: str | None = None
    implemented: bool = False
    exhausted: bool = False


class RelicPlayabilityResponse(BaseModel):
    """Wszystkie relikty gracza z zagrywalnością."""

    relics: list[RelicPlayability]


class OpenTimingWindow(BaseModel):
    """Jawne okno czasowe otwarte teraz (RULES.md 54.9)."""

    key: str
    event: str
    moment: str
    label: str
    subject: str | None = None
    position: str | None = None
    closes: str


class OpenTimingWindowsResponse(BaseModel):
    windows: list[OpenTimingWindow]


class PlayerUndoStatus(BaseModel):
    """Czy gracz może teraz cofnąć swój ostatni krok (RULES.md 44.7)."""

    model_config = ConfigDict(extra="forbid")

    available: bool
    reason: str | None = None
    # Etykieta i numer migawki cofanego kroku (front opisuje go wpisem feedu Activity).
    label: str | None = None
    undone_seq: int | None = None


class PlayerUndoRequest(BaseModel):
    """Undo gracza: kto cofa swój ostatni krok (w sieci musi się zgadzać z tokenem)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str


__all__ = [
    "ActionCardInputsResponse",
    "ActionCardPlayability",
    "ActionCardPlayabilityResponse",
    "AutoPassRequest",
    "DebtTokensRequest",
    "DiscardExcessRequest",
    "HeldActionRequest",
    "OpenTimingWindow",
    "OpenTimingWindowsResponse",
    "PlayActionCardResponse",
    "PlayRelicRequest",
    "PlayRelicResponse",
    "PlayerUndoRequest",
    "PlayerUndoStatus",
    "QuickWindowsRequest",
    "ReactionPrefsRequest",
    "ReactionWindowRequest",
    "RelicInputsResponse",
    "RelicPlayability",
    "RelicPlayabilityResponse",
    "TransactionPartnerView",
    "TransactionSideRequest",
    "TransactionSideView",
    "TransactionStateResponse",
    "TransactionTableReadyRequest",
    "TransactionTableRequest",
    "TransactionTableSideRequest",
    "TransactionTableView",
]
