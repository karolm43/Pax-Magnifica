"""GameState — dynamiczny, walidowany i serializowalny stan gry.

Model opisuje bieżący stan fizycznej planszy odwzorowany cyfrowo: graczy wraz
z zasobami i punktami zwycięstwa, jednostki rozmieszczone w systemach, właścicieli
planet oraz bieżącą turę i fazę. Jest w pełni serializowalny do JSON, co pozwala
zapisywać go jako lekkie migawki (Snapshot Stack) w ``EventStore``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Phase(StrEnum):
    """Fazy rundy Twilight Imperium."""

    STRATEGY = "STRATEGY"
    ACTION = "ACTION"
    STATUS = "STATUS"
    AGENDA = "AGENDA"


class TacticalStep(StrEnum):
    """Kroki akcji taktycznej (okna czasowe fazy akcji — E3).

    Sekwencja wg LRR / AsyncTI4 (``service/tactical/``): aktywacja systemu →
    ruch → space cannon offense → walka kosmiczna → inwazja → produkcja. To
    maszyna stanów PROWADZĄCA gracza przez kroki; aplikacja NIE waliduje reguł
    (gracze grają fizycznie i wprowadzają wynik), więc kroki służą strukturze i
    podpowiedziom, nie egzekwowaniu.
    """

    ACTIVATION = "ACTIVATION"
    MOVEMENT = "MOVEMENT"
    SPACE_CANNON = "SPACE_CANNON"
    SPACE_COMBAT = "SPACE_COMBAT"
    INVASION = "INVASION"
    PRODUCTION = "PRODUCTION"


class PlayerState(BaseModel):
    """Stan pojedynczego gracza."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    faction: str | None = None
    color: str | None = None
    # Pozycja ``RPP`` slotu domowego gracza (gdzie stoi jego kafelek domowy).
    # Ustawiana przy setupie frakcji; kotwiczy heks stat-area niezależnie od tego,
    # które planety gracz aktualnie kontroluje (po podbojach — patrz RULES.md 4).
    home_position: str | None = None

    victory_points: int = 0
    trade_goods: int = 0
    commodities: int = 0

    # Żetony dowodzenia (command counters). Start TI4: 3 taktyczne, 3 floty,
    # 2 strategiczne (reguła spisana w docs/RULES.md 5). Rezerwa = ccReinf.
    tactical_cc: int = 3
    fleet_cc: int = 3
    strategic_cc: int = 2
    cc_reinf: int = 8

    # Czy gracz spasował w fazie akcji.
    passed: bool = False
    # Karty strategii gracza (numery inicjatywy, np. [3]); puste poza fazą.
    strategy_cards: list[int] = Field(default_factory=list)
    # Zagrane (wyczerpane) karty strategii gracza — po użyciu primary (odwrócone).
    exhausted_strategy_cards: list[int] = Field(default_factory=list)

    # Planety kontrolowane przez gracza (identyfikatory planet).
    controlled_planets: list[str] = Field(default_factory=list)
    # Planety WYCZERPANE (exhausted) — po wydaniu ich zasobów/wpływów. Gotowe
    # (ready) planety to te kontrolowane, których tu NIE ma. Odświeżenie w fazie
    # statusu czyści tę listę (RULES.md — Status Phase „ready cards"). Trzymamy
    # jawnie, bo kontrola (``planet_owners``) nie niesie stanu wyczerpania.
    exhausted_planets: list[str] = Field(default_factory=list)
    # Technologie posiadane przez gracza (identyfikatory technologii).
    technologies: list[str] = Field(default_factory=list)
    # Technologie WYCZERPANE (exhausted) — np. część technologii jednostkowych/akcji.
    # Gotowe = posiadane, których tu nie ma. Odświeżane w fazie statusu.
    exhausted_technologies: list[str] = Field(default_factory=list)
    # Stan liderów: {leader_id: "locked"|"unlocked"|"exhausted"}. Brak wpisu =
    # stan domyślny z danych frakcji (agent gotowy, commander/hero zablokowani).
    leader_states: dict[str, str] = Field(default_factory=dict)

    # Stan przełomu frakcji (breakthrough — mechanika Thunder's Edge). Przełom jest
    # jeden per frakcja (dane w BreakthroughDef, mapowane po frakcji), więc trzymamy
    # tu tylko jego stan: odblokowany (po spełnieniu synergii), wyczerpany (po użyciu
    # akcji), oraz liczba odłożonych trade goods. Start: zablokowany.
    breakthrough_unlocked: bool = False
    breakthrough_exhausted: bool = False
    breakthrough_tg: int = 0


class SystemState(BaseModel):
    """Dynamiczny stan pojedynczego systemu na mapie."""

    model_config = ConfigDict(extra="forbid")

    position: str
    system_id: str
    # Jednostki w przestrzeni: {player_id: {unit_base_type: liczba}}.
    space_units: dict[str, dict[str, int]] = Field(default_factory=dict)
    # Jednostki na planetach: {planet_id: {player_id: {unit_base_type: liczba}}}.
    planet_units: dict[str, dict[str, dict[str, int]]] = Field(default_factory=dict)
    # Właściciele planet: {planet_id: player_id}.
    planet_owners: dict[str, str] = Field(default_factory=dict)
    # Żetony dowodzenia (command counters) POŁOŻONE w przestrzeni systemu — lista
    # player_id. Aktywacja systemu kładzie tu żeton aktywnego gracza (odpowiednik
    # ``Space.ccList`` w AsyncTI4; patrz RULES.md 19). Kontrola przestrzeni NIE jest
    # tu trzymana — wynika z obecności statków (``space_units``).
    command_tokens: list[str] = Field(default_factory=list)


class GameState(BaseModel):
    """Pełny, serializowalny stan gry."""

    model_config = ConfigDict(extra="forbid")

    round_number: int = 1
    phase: Phase = Phase.STRATEGY
    active_player_id: str | None = None
    # Mówca (speaker) — zaczyna wybór kart strategii; None dopóki nieustalony.
    speaker_id: str | None = None
    # Kolejność zasiadania graczy przy stole (player_id), zgodnie z ruchem
    # wskazówek zegara. Ustalana przy nowej grze (kolejność podanych graczy).
    # Z niej wynika SPEAKER ORDER (rotacja zaczynająca się od ``speaker_id``),
    # używany w fazie strategii przy wyborze kart (RULES.md 24). Faza akcji
    # używa INICJATYWY kart (RULES.md 9), nie tej kolejności.
    seating_order: list[str] = Field(default_factory=list)

    # Akcja taktyczna (E3). ``active_system`` = pozycja aktualnie aktywowanego
    # systemu (odpowiednik ``Game.activeSystem``); ``tactical_step`` = bieżący krok
    # maszyny stanów (None = brak trwającej akcji taktycznej). Oba czyszczone po
    # zakończeniu akcji. Aplikacja prowadzi kroki, ale nie waliduje reguł.
    active_system: str | None = None
    tactical_step: TacticalStep | None = None
    # Trade goods leżące na kartach strategii: {numer_inicjatywy: liczba_TG}.
    # Niewybrane karty akumulują +1 TG na koniec fazy strategii; wybór przekazuje
    # TG graczowi i zeruje licznik (RULES.md 13).
    strategy_card_tg: dict[int, int] = Field(default_factory=dict)

    players: dict[str, PlayerState] = Field(default_factory=dict)
    systems: dict[str, SystemState] = Field(default_factory=dict)

    def clone(self) -> GameState:
        """Zwraca głęboką kopię stanu (przez walidowaną serializację)."""
        return GameState.model_validate(self.model_dump())
