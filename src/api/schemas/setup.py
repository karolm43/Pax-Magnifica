"""DTO API: ręka, frakcje, nowa gra, edycja jednostek/graczy, karty strategii, agenda, status."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.core.objective_payment import ObjectivePayment


class SetPlayerHandRequest(BaseModel):
    """God-Mode: ustawienie prywatnej ręki gracza (karty akcji / sekrety / weksle).

    Każda lista opcjonalna — podana NADPISUJE daną rękę, pominięta zostaje bez
    zmian. Służy głównie do testów „paska ręki" na mapie (operator widzi wszystko).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    action_cards: list[str] | None = None
    secret_objectives: list[str] | None = None
    promissory_notes: list[str] | None = None


class PlayerHandResponse(BaseModel):
    """Prywatna ręka gracza (ID kart) dla „paska ręki" na mapie i zakładki gracza.

    Klucze w camelCase, by wprost pasowały do typu ``PlayerHandData`` na froncie
    (``actionCards``/``secretObjectives``/``promissoryNotes``). W trybie lokalnym
    operator widzi wszystko, więc endpoint zwraca jawne identyfikatory — inaczej
    niż web-data, które cudze ręce redaguje do liczników (R6.1).
    """

    model_config = ConfigDict(extra="forbid")

    actionCards: list[str] = Field(default_factory=list)  # noqa: N815
    secretObjectives: list[str] = Field(default_factory=list)  # noqa: N815
    promissoryNotes: list[str] = Field(default_factory=list)  # noqa: N815
    # Prywatne podglądy z kart (RULES.md 53.5): wiedza o talii agend (Insider Information, Politics;
    # 53.5.a1 - znane karty od góry i od spodu) i tajne cele pokazane przez Extreme Duress
    # ({właściciel: [cele]}).
    agendaPeek: list[str] = Field(default_factory=list)  # noqa: N815
    agendaPeekBottom: list[str] = Field(default_factory=list)  # noqa: N815
    revealedSecrets: dict[str, list[str]] = Field(default_factory=dict)  # noqa: N815


class StartingUnit(BaseModel):
    """Jeden wpis floty startowej frakcji — liczba + typ jednostki (pełna nazwa z danych).

    Buduje je backend z ``startingFleet`` przez ``parse_starting_fleet`` (jedno źródło
    parsera, RULES.md 2c). ``base_type`` to generyczny typ (np. ``carrier``), który front
    rozwiązuje na pełną nazwę przez swoje dane jednostek — zamiast pokazywać surowe kody
    (``cv``, ``dd``). ``placement`` (SPACE/PLANET) dla ewentualnego pogrupowania w UI.
    """

    model_config = ConfigDict(extra="forbid")

    base_type: str
    count: int
    placement: str


class FactionInfo(BaseModel):
    """Informacja o frakcji dla ekranu wyboru (setup)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    # Źródło/dodatek frakcji (np. „base", „pok", „thunders_edge", „codex3"). Front używa
    # go do pogrupowania listy wyboru wg dodatków (Base Game / PoK / Thunder's Edge).
    source: str
    home_system: str | None = None
    home_planets: list[str] = Field(default_factory=list)
    starting_fleet: str | None = None
    preferred_colours: list[str] = Field(default_factory=list)
    # Wybór technologii startowej (gdy frakcja nie ma stałej listy). Gdy
    # ``starting_tech_amount == 0``, frakcja nie wybiera (stałe technologie).
    starting_tech_options: list[str] = Field(default_factory=list)
    starting_tech_amount: int = 0
    # Pola bogate — do podglądu frakcji (faction summary) na ekranie setupu. To same
    # identyfikatory ze statycznego rejestru (``FactionDef``); front rozwiązuje je po
    # swoich danych AsyncTI4 (te same komponenty co panel gracza w grze). Dzięki temu
    # wybór frakcji pokazuje zdolności / technologie / liderów / jednostki bez stanu gry.
    starting_tech: list[str] = Field(default_factory=list)
    abilities: list[str] = Field(default_factory=list)
    faction_tech: list[str] = Field(default_factory=list)
    leaders: list[str] = Field(default_factory=list)
    units: list[str] = Field(default_factory=list)
    promissory_notes: list[str] = Field(default_factory=list)
    commodities: int = 0
    complexity: str | None = None
    # Przełom frakcji (breakthrough, Thunder's Edge) — identyfikator dopasowany po
    # ``BreakthroughDef.faction``; None, gdy frakcja go nie ma. Front rozwiązuje go po
    # swoich danych (komponent ``Breakthrough``), tak jak panel gracza w grze.
    breakthrough: str | None = None
    # Flota startowa rozbita na pozycje (liczba + typ jednostki). Zastępuje surowy
    # ``starting_fleet`` w UI pełnymi nazwami jednostek. ``starting_fleet`` zostaje jako
    # oryginalny string (zgodność wsteczna / debug).
    starting_units: list[StartingUnit] = Field(default_factory=list)
    # Frakcja ma pełną implementację w silniku (``core/faction_support``) - tymczasowy znacznik
    # w kreatorze (decyzja użytkownika 2026-11-18, do usunięcia po komplecie frakcji).
    implemented: bool = False


class EngineConfigInfo(BaseModel):
    """Konfiguracja silnika wystawiana frontendowi (setup).

    Obecnie niesie dozwolony zbiór poziomów trudności bota (R10.2) — front NIE
    trzyma własnej kopii tej listy, tylko pobiera ją stąd. Wartości pochodzą
    z ``engine_config.json`` czytanego przez ``StaticDataRegistry`` (⚠️ ZAŁOŻENIE,
    patrz docs/RULES.md 36), więc gdy zbiór się zmieni w assecie, front dostanie
    aktualny bez zmian w kodzie.
    """

    model_config = ConfigDict(extra="forbid")

    # Posortowana lista dozwolonych poziomów trudności bota (R10.2).
    valid_difficulties: list[str] = Field(default_factory=list)
    # Posortowana lista dozwolonych osobowości bota (⚠️ ZAŁOŻENIE).
    valid_personalities: list[str] = Field(default_factory=list)
    # Pozycje miejsc (slotów domowych) w kolejności stołu — front pozwala wybrać
    # miejsce gracza i wysyła je jako ``home_position`` (docs/RULES.md 24).
    seats: list[str] = Field(default_factory=list)


class MapSeatView(BaseModel):
    """Miejsce gracza wykryte w map stringu (``core.map_string.map_seats``)."""

    position: str
    # Frakcja, której kafelek domowy leży na tym miejscu (gotowa mapa); None = pusty slot.
    faction_id: str | None = None


class MapSeatsView(BaseModel):
    """Podgląd map stringa w kreatorze: miejsca graczy i kafelki spoza rejestru."""

    seats: list[MapSeatView] = Field(default_factory=list)
    unknown_tiles: list[str] = Field(default_factory=list)


class SetupPlayerRequest(BaseModel):
    """Żądanie setupu gracza: frakcja + kolor na wskazanym slocie domowym.

    ``faction_id`` jest opcjonalny — gdy pominięty, backend dobiera losową,
    nieprzypisaną frakcję (R8.5). ``name``/``control_type``/``difficulty``
    rozszerzają kontrakt o nazwę wyświetlaną i tryb sterowania (R10.1–R10.3);
    ``difficulty`` ma sens tylko dla ``control_type == "BOT"``.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    # Opcjonalny: None → losowa, nieprzypisana frakcja (R8.5).
    faction_id: str | None = None
    color: str
    home_position: str
    # Nazwa wyświetlana (R7.1); pusta/None → auto-nazwa przy setupie (R7.3).
    name: str | None = None
    # Tryb sterowania (R10.1): "HUMAN" (domyślnie) lub "BOT".
    control_type: str = "HUMAN"
    # Poziom trudności bota (R10.2/R10.3); wymagany dla BOT, ignorowany dla HUMAN.
    difficulty: str | None = None
    # Osobowość bota; brak → losowa (tylko BOT), ignorowana dla HUMAN.
    personality: str | None = None
    # Wybrane technologie startowe (dla frakcji z wyborem, np. Winnu/Argent).
    starting_tech: list[str] | None = None


class NewGamePlayer(BaseModel):
    """Pojedynczy gracz w żądaniu nowej gry (frakcja opcjonalna; reszta auto)."""

    model_config = ConfigDict(extra="forbid")

    # Opcjonalny: None → losowa, nieprzypisana frakcja (R8.5).
    faction_id: str | None = None
    # Opcjonalne: gdy pominięte, kolor/slot/id przydzielane automatycznie
    # wg kolejności (gracz 1 → red/301, 2 → green/304, ...).
    player_id: str | None = None
    # Nazwa wyświetlana (R7.1); pusta/None → auto-nazwa przy setupie (R7.3).
    name: str | None = None
    color: str | None = None
    # Tryb sterowania (R10.1): "HUMAN" (domyślnie) lub "BOT".
    control_type: str = "HUMAN"
    # Poziom trudności bota (R10.2/R10.3); wymagany dla BOT, ignorowany dla HUMAN.
    difficulty: str | None = None
    # Osobowość bota; brak → losowa (tylko BOT), ignorowana dla HUMAN.
    personality: str | None = None
    # Opcjonalny slot domowy — pod przyszły draft slice (R14.3).
    home_position: str | None = None
    # Wybrane technologie startowe (dla frakcji z wyborem, np. Winnu/Argent).
    starting_tech: list[str] | None = None


class ChessClockConfig(BaseModel):
    """Zegar szachowy nowej gry (RULES.md 58): pula minut na gracza + dodatek za turę."""

    model_config = ConfigDict(extra="forbid")

    total_minutes: int = Field(ge=1, le=1440)
    increment_seconds: int = Field(default=0, ge=0, le=3600)


class NewGameRequest(BaseModel):
    """Żądanie utworzenia nowej gry: mapa + gracze w jednym kroku.

    ``map_string`` opcjonalny — gdy pominięty, backend użyje mapy testowej.
    Kolory i sloty domowe są przydzielane automatycznie wg kolejności graczy,
    chyba że jawnie podane dla danego gracza.
    """

    model_config = ConfigDict(extra="forbid")

    players: list[NewGamePlayer] = Field(default_factory=list)
    map_string: str | None = None
    # Losowa mapa 6-osobowa (``core.map_string.random_map_string``); wygrywa z ``map_string``.
    random_map: bool = False
    include_center: bool = True
    # Moduły wariantów gry (id z ``assets/config/variants.json``); None = moduły domyślne.
    variants: list[str] | None = None
    # Zgodność wstecz: talia agend "standard" albo źródło modułu talii agend (np. "absol").
    agenda_deck: str = "standard"
    # Zegar szachowy (RULES.md 58) — None = gra bez zegara.
    chess_clock: ChessClockConfig | None = None
    # Stała długość okien reakcji w s (RULES.md 54.11) — None = domyślna (4 s).
    reaction_window_seconds: int | None = Field(default=None, ge=2, le=30)


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


class UnitEditRequest(BaseModel):
    """Edycja God-Mode jednostek w strefie systemu (delta w terminach asyncId).

    Operuje tak jak frontend: strefa (``"space"`` lub ID planety), klucz frakcji
    (jak w ``tileUnitData``), ``asyncId`` jednostki i przyrost ``delta`` (+/−).
    Backend tłumaczy ``asyncId`` → ``baseType`` i klucz frakcji → ``player_id``.
    Brak sprawdzania zasad — to narzędzie operatora (God-Mode).
    """

    model_config = ConfigDict(extra="forbid")

    zone: str  # "space" albo ID planety
    faction: str  # klucz frakcji z tileUnitData (faction lub player_id)
    async_id: str = Field(alias="asyncId")
    delta: int  # przyrost liczby (dodatni/ujemny)


class UnitMoveRequest(BaseModel):
    """Przesunięcie jednostek między strefami/systemami (God-Mode, bez reguł)."""

    model_config = ConfigDict(extra="forbid")

    from_position: str = Field(alias="fromPosition")
    from_zone: str = Field(alias="fromZone")  # "space" albo ID planety
    to_position: str = Field(alias="toPosition")
    to_zone: str = Field(alias="toZone")
    faction: str
    async_id: str = Field(alias="asyncId")
    count: int = 1


class PlayerEditRequest(BaseModel):
    """God-Mode: edycja pól gracza. Każde pole opcjonalne — podane nadpisuje.

    Bez sprawdzania zasad (narzędzie operatora). Pola odpowiadają ``PlayerState``.
    """

    model_config = ConfigDict(extra="forbid")

    faction: str | None = None
    color: str | None = None
    victory_points: int | None = None
    trade_goods: int | None = None
    commodities: int | None = None
    tactical_cc: int | None = None
    fleet_cc: int | None = None
    strategic_cc: int | None = None
    cc_reinf: int | None = None
    passed: bool | None = None
    strategy_cards: list[int] | None = None
    controlled_planets: list[str] | None = None
    exhausted_planets: list[str] | None = None
    technologies: list[str] | None = None
    exhausted_technologies: list[str] | None = None
    # Stan liderów: {leader_id: "locked"|"unlocked"|"exhausted"}.
    leader_states: dict[str, str] | None = None
    # Trade goods on leader cards (Artuno the Betrayer, RULES.md 62.21): {leader_id: TG}.
    leader_trade_goods: dict[str, int] | None = None
    # Przełom frakcji (Thunder's Edge): odblokowany / wyczerpany / odłożone TG.
    breakthrough_unlocked: bool | None = None
    breakthrough_exhausted: bool | None = None
    breakthrough_tg: int | None = None
    # Promissory notes w strefie gracza (play area) — jawne, odrębne od ręki
    # (RULES.md 2d). God-Mode zasila je ręcznie do czasu logiki zagrywania notek.
    promissory_notes_in_play: list[str] | None = None
    # Relikty przed graczem (jawne). Lista NADPISUJE; relikt znika z talii i od innych graczy.
    relics: list[str] | None = None
    # Fragmenty reliktów w strefie gracza (id kart eksploracji: crf*/hrf*/irf*/urf*). NADPISUJE;
    # dodany fragment znika z talii eksploracji, purge i od innych graczy.
    relic_fragments: list[str] | None = None


class PlayerComponentToggleRequest(BaseModel):
    """Przełączenie stanu komponentu gracza (planeta/technologia) — exhaust ↔ ready."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    component_id: str


class LeaderStateRequest(BaseModel):
    """Ustawienie stanu lidera gracza (locked/unlocked/exhausted)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    leader_id: str
    state: str


class StrategyCardInfo(BaseModel):
    """Karta strategii dla panelu fazy strategii (dane + stan)."""

    model_config = ConfigDict(extra="forbid")

    initiative: int
    id: str
    name: str
    primary_texts: list[str] = Field(default_factory=list)
    secondary_texts: list[str] = Field(default_factory=list)
    colour_hex_code: str | None = None
    # Stan w bieżącej grze:
    trade_goods: int = 0  # TG leżące na karcie (niewybrana)
    picked_by: str | None = None  # player_id właściciela (lub None)
    exhausted: bool = False  # czy zagrana (odwrócona)


class StrategyPickRequest(BaseModel):
    """Wybór karty strategii przez gracza (po numerze inicjatywy)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    initiative: int
    # Checks and Balances: gracz, który dostaje wybraną kartę (RULES.md 51.6).
    recipient: str | None = None


class StrategyPlayRequest(BaseModel):
    """Zagranie (wyczerpanie) karty strategii gracza."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    initiative: int


class StrategyPrimaryStepRequest(BaseModel):
    """Wybór aktywnego gracza dla bieżącego kroku wieloetapowego primary (E8-T5).

    ``player_id`` musi być właścicielem karty; ``payload`` ma kształt zależny od kroku
    karty (np. Trade: ``{"players": ["p2"]}``) i jest walidowany po stronie ``core/``.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class StrategySecondaryRequest(BaseModel):
    """Odpowiedź w oknie secondary karty strategii (E8-T3).

    ``player_id`` musi być bieżącym respondentem okna. ``execute=True`` → wykonaj
    secondary; ``False`` → pas (oba przesuwają kolejkę okna).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    execute: bool = False
    # Wybory respondenta dla „follow" (kształt zależy od karty, np. Leadership:
    # planety do wydania + rozkład żetonów). Walidowane po stronie ``core/``.
    payload: dict[str, Any] = Field(default_factory=dict)

class TurnActionRequest(BaseModel):
    """Zakończenie/pas tury (E8-T4). ``player_id`` opcjonalny — gdy podany, backend

    waliduje, że to tura tego gracza (RULES.md 31.2). Pominięty = bez kontroli
    tożsamości (zgodność wsteczna), faza nadal musi być akcji.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str | None = None


class AgendaVoteRequest(BaseModel):
    """Głos w fazie agendy: wynik + planety do wyczerpania (głosy = suma ich wpływów)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    outcome: str
    planets: list[str] = Field(default_factory=list)
    # Predictive Intelligence: +3 głosy (decyzja gracza).
    use_predictive: bool = False


class AgendaOutcomeRequest(BaseModel):
    """Wybór wyniku przez mówcę przy remisie / braku głosów (to nie jest głos)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    outcome: str


class EpilogueVoteRequest(BaseModel):
    """Głos w epilogu: ``choice`` = ``honorable`` albo ``dishonorable`` (walidacja w core)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    choice: str


class StatusScoreRequest(BaseModel):
    """Zdobycie celu w kroku 1 fazy statusu: ``kind`` = ``public`` albo ``secret``."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    kind: str
    objective_id: str
    # Jawna płatność za cel „Spend…" (brak => silnik dobiera sam).
    payment: ObjectivePayment | None = None


class StatusRedistributeRequest(BaseModel):
    """Rozdział żetonów dowodzenia w kroku 5 fazy statusu (suma = dostępne żetony)."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    tactical: int
    fleet: int
    strategic: int


class SetupSecretRequest(BaseModel):
    """Wybór tajnego celu w setupie: gracz zatrzymuje ``objective_id`` z dwóch dobranych."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    objective_id: str


class SetupActorRequest(BaseModel):
    """Akcja mówcy w setupie (żeton Custodians, odkrycie celów) — ``player_id`` = mówca."""

    model_config = ConfigDict(extra="forbid")

    player_id: str


class SetSpeakerRequest(BaseModel):
    """Ustawienie mówcy (speaker) — otwiera wybór kart w fazie strategii."""

    model_config = ConfigDict(extra="forbid")

    player_id: str


__all__ = [
    "AgendaOutcomeRequest",
    "AgendaVoteRequest",
    "ChessClockConfig",
    "EngineConfigInfo",
    "MapSeatView",
    "MapSeatsView",
    "EpilogueVoteRequest",
    "FactionInfo",
    "LeaderStateRequest",
    "NewGamePlayer",
    "NewGameRequest",
    "PlanetUnitsRequest",
    "PlayerComponentToggleRequest",
    "PlayerEditRequest",
    "PlayerHandResponse",
    "SetPlayerHandRequest",
    "SetSpeakerRequest",
    "SetupActorRequest",
    "SetupPlayerRequest",
    "SetupSecretRequest",
    "SpaceUnitsRequest",
    "StartingUnit",
    "StatusRedistributeRequest",
    "StatusScoreRequest",
    "StrategyCardInfo",
    "StrategyPickRequest",
    "StrategyPlayRequest",
    "StrategyPrimaryStepRequest",
    "StrategySecondaryRequest",
    "TurnActionRequest",
    "UnitChange",
    "UnitEditRequest",
    "UnitMoveRequest",
]
