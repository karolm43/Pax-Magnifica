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
    # Technologie posiadane przez gracza (identyfikatory technologii).
    technologies: list[str] = Field(default_factory=list)
    # Stan liderów: {leader_id: "locked"|"unlocked"|"exhausted"}. Brak wpisu =
    # stan domyślny z danych frakcji (agent gotowy, commander/hero zablokowani).
    leader_states: dict[str, str] = Field(default_factory=dict)


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


class GameState(BaseModel):
    """Pełny, serializowalny stan gry."""

    model_config = ConfigDict(extra="forbid")

    round_number: int = 1
    phase: Phase = Phase.STRATEGY
    active_player_id: str | None = None
    # Mówca (speaker) — zaczyna wybór kart strategii; None dopóki nieustalony.
    speaker_id: str | None = None
    # Trade goods leżące na kartach strategii: {numer_inicjatywy: liczba_TG}.
    # Niewybrane karty akumulują +1 TG na koniec fazy strategii; wybór przekazuje
    # TG graczowi i zeruje licznik (RULES.md 13).
    strategy_card_tg: dict[int, int] = Field(default_factory=dict)

    players: dict[str, PlayerState] = Field(default_factory=dict)
    systems: dict[str, SystemState] = Field(default_factory=dict)

    def clone(self) -> GameState:
        """Zwraca głęboką kopię stanu (przez walidowaną serializację)."""
        return GameState.model_validate(self.model_dump())
