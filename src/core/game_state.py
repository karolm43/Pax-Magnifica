"""GameState — dynamiczny, walidowany i serializowalny stan gry.

Model opisuje bieżący stan fizycznej planszy odwzorowany cyfrowo: graczy wraz
z zasobami i punktami zwycięstwa, jednostki rozmieszczone w systemach, właścicieli
planet oraz bieżącą turę i fazę. Jest w pełni serializowalny do JSON, co pozwala
zapisywać go jako lekkie migawki (Snapshot Stack) w ``EventStore``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

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


class ControlType(StrEnum):
    """Typ sterowania graczem (R1.6).

    Dokładnie dwie wartości: gracz-człowiek oraz gracz-bot (docelowo sterowany
    przez warstwę AI). Wartość spoza tego zbioru jest odrzucana przez Pydantic
    jako ``ValidationError`` (R1.7).
    """

    HUMAN = "HUMAN"
    BOT = "BOT"


class WindowType(StrEnum):
    """Typ okna czasowego (timing window) — RULES.md 29.2.

    Jednolite pojęcie dla wszystkich momentów, w których gracze reagują PO KOLEI:
    - ``STRATEGY_SECONDARY`` — secondary karty strategii (po primary aktywnego gracza);
    - ``COMBAT_ASSIGN_HITS`` — przypisanie strat w walce (obrońca wskazuje, co ginie);
    - ``SPACE_CANNON`` — space cannon offense (okno przed walką kosmiczną);
    - ``REACTION`` — uniwersalne okno „when/after" (karty akcji, technologie reagujące);
    - ``COMBAT_RETREAT`` — ogłoszenie odwrotu w walce kosmicznej (obrońca, potem atakujący);
    - ``CAPACITY`` — usunięcie nadwyżki myśliwców/sił naziemnych ponad pojemność (RULES.md 39.6).
    - ``FLEET_POOL`` — usunięcie statków ponad pulę floty w systemie (RULES.md 42).

    Model kolejki jest WSPÓLNY (``TimingWindow``); typ niesie tylko znaczenie okna
    i pozwala warstwom wyżej (``core`` fazy/walki, UI) rozpoznać, co rozstrzygać.
    """

    STRATEGY_SECONDARY = "STRATEGY_SECONDARY"
    COMBAT_ASSIGN_HITS = "COMBAT_ASSIGN_HITS"
    SPACE_CANNON = "SPACE_CANNON"
    REACTION = "REACTION"
    COMBAT_RETREAT = "COMBAT_RETREAT"
    CAPACITY = "CAPACITY"
    FLEET_POOL = "FLEET_POOL"


class TimingWindow(BaseModel):
    """Otwarte okno czasowe — kolejka graczy pytanych PO KOLEI (RULES.md 29.2).

    Mechanika kolejki jest NEUTRALNA względem reguł konkretnego okna: trzyma listę
    graczy do zapytania (``queue``), wskaźnik bieżącego respondenta (``cursor``),
    listę tych, którzy już odpowiedzieli (``responded``), oraz dowolne dane
    kontekstowe (``context`` — np. numer karty strategii, pozycja systemu walki).

    Kolejność ustala warstwa otwierająca okno (zwykle speaker order rotowany od
    gracza PO aktywnym, zgodnie z zegarem — ``core.timing.open_window``). Tu trzymamy
    już gotową listę ``queue``, żeby model był niezależny od sposobu jej wyliczenia.

    Bieżący respondent = ``queue[cursor]`` dopóki ``cursor < len(queue)``. Gdy
    ``cursor`` dojdzie do końca kolejki, okno jest ZAKOŃCZONE (``is_complete``) —
    warstwa wyżej je zamyka (``close_window``) i stosuje efekty.
    """

    model_config = ConfigDict(extra="forbid")

    window_type: WindowType
    # Gracze do zapytania, w ustalonej kolejności reagowania.
    queue: list[str] = Field(default_factory=list)
    # Indeks bieżącego respondenta w ``queue`` (0..len). len == koniec okna.
    cursor: int = 0
    # Gracze, którzy już odpowiedzieli (w kolejności odpowiedzi) — audyt/UI.
    responded: list[str] = Field(default_factory=list)
    # Dane kontekstowe okna (np. {"initiative": 1} dla secondary, {"position": "101"}
    # dla walki). Luźny słownik — konkretne klucze definiuje warstwa otwierająca.
    context: dict[str, str | int] = Field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """Czy wszyscy z kolejki już odpowiedzieli (okno gotowe do zamknięcia)."""
        return self.cursor >= len(self.queue)

    @property
    def current_responder(self) -> str | None:
        """Gracz, którego teraz kolej odpowiadać (None, gdy okno zakończone)."""
        if self.is_complete:
            return None
        return self.queue[self.cursor]

class StatusStep(StrEnum):
    """Krok fazy statusu, na którym aktualnie stoi gra (R_status_phase).

    Fazę statusu dzielimy na trzy etapy INTERAKCJI; reszta kroków LRR jest automatyczna:
    - ``SCORE_OBJECTIVES`` — krok 1: gracze po kolei (initiative order) punktują cele;
    - ``REDISTRIBUTE`` — kroki 2–4 wykonane automatycznie, krok 5: gracze rozdzielają
      żetony dowodzenia (równolegle);
    - ``COMPLETE`` — kroki 6–7 wykonane automatycznie; czeka na krok 8 (mówca „Next phase").
    """

    SCORE_OBJECTIVES = "SCORE_OBJECTIVES"
    REDISTRIBUTE = "REDISTRIBUTE"
    COMPLETE = "COMPLETE"


class StatusPhaseState(BaseModel):
    """Stan trwającej fazy statusu (``None`` poza nią) — RULES.md 41.

    ``scored_public`` / ``scored_secret`` = gracze, którzy W TEJ fazie statusu zdobyli już
    publiczny / tajny cel (limit: po jednym na fazę — R_objective_cards). ``done`` = gracze,
    którzy zakończyli swoją część bieżącego kroku (krok 1: „skończyłem punktować", krok 5:
    „zatwierdziłem rozdział żetonów"). ``unassigned_cc`` = żetony zdobyte w kroku 5, a jeszcze
    nieprzydzielone do puli (strategy/tactic/fleet). ``fleet_excess`` = nadwyżka statków ponad
    fleet pool po redystrybucji (pozycja → liczba), do ręcznego usunięcia. ``log`` = dziennik
    automatycznych kroków 2–8 (zasila panel).
    """

    model_config = ConfigDict(extra="forbid")

    step: StatusStep = StatusStep.SCORE_OBJECTIVES
    scored_public: list[str] = Field(default_factory=list)
    scored_secret: list[str] = Field(default_factory=list)
    done: list[str] = Field(default_factory=list)
    unassigned_cc: dict[str, int] = Field(default_factory=dict)
    fleet_excess: dict[str, dict[str, int]] = Field(default_factory=dict)
    log: list[dict[str, Any]] = Field(default_factory=list)


class ObjectivesState(BaseModel):
    """Cele publiczne gry: talie, odkryte i zdobyte (RULES.md 41.1).

    ``stage1_deck`` / ``stage2_deck`` = ZAKRYTE cele (od góry talii, ``[0]`` = następny do
    odkrycia). Setup losuje po 5 z każdego etapu, a mówca odkrywa dwa cele I etapu
    (R_objective_cards). ``revealed`` = odkryte w kolejności odsłaniania (I i II etap).
    ``scored`` = ``{id_celu: [player_id, ...]}`` — kto zdobył dany cel publiczny (też
    „inne punkty": custodians itd.); powtórzony gracz = punkt zdobyty wielokrotnie.
    ``custom_points`` = ``{klucz: VP}`` dla punktów spoza kart (custodians, imperial...).
    """

    model_config = ConfigDict(extra="forbid")

    stage1_deck: list[str] = Field(default_factory=list)
    stage2_deck: list[str] = Field(default_factory=list)
    revealed: list[str] = Field(default_factory=list)
    scored: dict[str, list[str]] = Field(default_factory=dict)
    custom_points: dict[str, int] = Field(default_factory=dict)


class DecksState(BaseModel):
    """Talie wspólne: karty akcji i tajne cele (kolejność = od góry, ``[0]`` dobierana)."""

    model_config = ConfigDict(extra="forbid")

    action_card_deck: list[str] = Field(default_factory=list)
    action_card_discard: list[str] = Field(default_factory=list)
    secret_objective_deck: list[str] = Field(default_factory=list)


class PlayerPrivateState(BaseModel):
    """Prywatne (tajne) komponenty gracza — widoczne tylko właścicielowi (R2.3).

    Wydzielone w osobny podmodel, aby klasyfikacja Public/Private pozostała
    jednopoziomowa i oczywista (całe pole ``private`` jest tajne), a redakcja
    w projekcji widoczności sprowadzała się do podmiany jednego pola. Listy
    trzymają identyfikatory kart (Hand_Card) i domyślnie są puste (R1.10).

    Limity rozmiarów rąk (max kart akcji / tajnych obiektywów / promissory notes)
    to ⚠️ ZAŁOŻENIE wg R1 — NIE są tu hardkodowane; górny limit (gdy potwierdzony
    ze źródła) dojdzie jako wartość czytana ze ``StaticDataRegistry`` w warstwie setup.
    """

    model_config = ConfigDict(extra="forbid")

    action_cards: list[str] = Field(default_factory=list)  # R1.1
    secret_objectives: list[str] = Field(default_factory=list)  # R1.2
    promissory_notes: list[str] = Field(default_factory=list)  # R1.3
    # Dwa tajne cele dobrane w setupie, z których gracz zatrzymuje JEDEN (drugi wraca do
    # talii). Pusta lista poza etapem wyboru (RULES.md 45).
    secret_candidates: list[str] = Field(default_factory=list)


class SetupStage(StrEnum):
    """Etap setupu gry po rozstawieniu graczy, a przed pierwszą fazą strategii (RULES.md 45).

    - ``SECRETS`` — każdy gracz po kolei dobiera 2 tajne cele i zatrzymuje 1;
    - ``CUSTODIANS`` — mówca kładzie żeton Custodians na Mecatol Rex;
    - ``OBJECTIVES`` — mówca odkrywa dwa cele publiczne I etapu.
    """

    SECRETS = "SECRETS"
    CUSTODIANS = "CUSTODIANS"
    OBJECTIVES = "OBJECTIVES"


class SetupState(BaseModel):
    """Trwający setup gry (``None`` w ``GameState.setup`` = setup zakończony).

    ``secrets_chosen`` = gracze, którzy już wybrali tajny cel. ``custodians_placed`` = żeton
    leży na Mecatol Rex (widoczny na mapie).
    """

    model_config = ConfigDict(extra="forbid")

    stage: SetupStage = SetupStage.SECRETS
    secrets_chosen: list[str] = Field(default_factory=list)
    custodians_placed: bool = False


class PlayerState(BaseModel):
    """Stan pojedynczego gracza."""

    model_config = ConfigDict(extra="forbid")

    player_id: str
    # Nazwa wyświetlana gracza — odrębna od ``player_id`` (R1.4). Docelowy zakres
    # 1..50 znaków wymuszany w warstwie setup; default ``""`` zapewnia wsteczną
    # kompatybilność migawek bez tego pola (R3.3). Pole JAWNE (Public_Info).
    display_name: str = ""
    # Typ sterowania graczem — domyślnie HUMAN (R1.11). Pole JAWNE (Public_Info).
    control_type: ControlType = ControlType.HUMAN
    # Poziom trudności bota — ustawiany wyłącznie dla ``BOT``; dla ``HUMAN`` None
    # (R10.4). Dozwolony zbiór wartości to ⚠️ ZAŁOŻENIE (R1.8) — nie enum, bo zbiór
    # jest danymi konfigurowalnymi, nie strukturą kodu. Pole JAWNE (Public_Info).
    difficulty: str | None = None
    # Osobowość (styl gry) bota — tylko dla ``BOT``, dla ``HUMAN`` None. Pole JAWNE.
    personality: str | None = None
    faction: str | None = None
    color: str | None = None
    # Pozycja ``RPP`` slotu domowego gracza (gdzie stoi jego kafelek domowy).
    # Ustawiana przy setupie frakcji; kotwiczy heks stat-area niezależnie od tego,
    # które planety gracz aktualnie kontroluje (po podbojach — patrz RULES.md 4).
    home_position: str | None = None

    victory_points: int = 0
    trade_goods: int = 0
    # Commodities AKTUALNIE posiadane. Gracz ZACZYNA GRĘ Z ZEREM
    # (tirules R_commodities: „A player starts the game with zero commodities").
    # Uzupełniane dopiero przez efekty (np. Trade) do ``commodity_value``.
    commodities: int = 0
    # Commodity value = MAKSIMUM commodities gracza (z karty frakcji). To NIE jest
    # ilość startowa — to górny limit, do którego gracz „replenishuje" (R_commodities).
    # Ustawiane przy setupie z ``faction.commodities``. Viewer pokazuje
    # ``commodities / commodity_value`` (bieżące / maks).
    commodity_value: int = 0

    # Żetony dowodzenia (command counters). Start TI4: 3 taktyczne, 3 floty,
    # 2 strategiczne (reguła spisana w docs/RULES.md 5). Rezerwa = ccReinf.
    tactical_cc: int = 3
    fleet_cc: int = 3
    strategic_cc: int = 2
    cc_reinf: int = 8

    # Czy gracz spasował w fazie akcji.
    passed: bool = False
    # Czy gracz WYKONAŁ już akcję w BIEŻĄCEJ turze fazy akcji (RULES.md 31.7,
    # R_action_phase: „During a player's turn, they perform a single action"). Jedna
    # z: akcja strategiczna, taktyczna (aktywacja systemu) albo komponentu — pas jest
    # osobną ścieżką (``passed``). Flaga jest RESETOWANA przy każdym przekazaniu tury
    # (``end_turn``) i przy wejściu w fazę akcji, bo dotyczy POJEDYNCZEJ tury, nie całej
    # fazy. End turn jest zablokowany, dopóki gracz nie wykona akcji LUB nie spasuje.
    took_action_this_turn: bool = False
    # Karty strategii gracza (numery inicjatywy, np. [3]); puste poza fazą.
    strategy_cards: list[int] = Field(default_factory=list)
    # Zagrane (wyczerpane) karty strategii gracza — po użyciu primary (odwrócone).
    exhausted_strategy_cards: list[int] = Field(default_factory=list)

    # Planety kontrolowane przez gracza (identyfikatory planet).
    # Z kim (``player_id`` partnera) aktywny gracz JU┼╗ rozstrzygn─ů┼é transakcj─Ö w tej turze
    # (RULES.md 47, R_transactions: ÔÇ×up to one transaction with each of their neighbors").
    # Resetowane razem z ``took_action_this_turn`` (nowa tura). Utrata i ponowne uzyskanie
    # s─ůsiedztwa w tej samej turze NIE daje drugiej transakcji ÔÇö st─ůd lista, nie wyliczenie.
    transacted_with: list[str] = Field(default_factory=list)
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

    # Promissory notes POŁOŻONE w strefie gracza (play area) — identyfikatory kart
    # zagranych i leżących odkryte, np. Support for the Throne, Alliance (RULES.md 2d,
    # R_promissory_notes: „promissory notes in the play area cannot be traded").
    # Pole JAWNE (Public_Info) — ODRĘBNE od prywatnej RĘKI (``private.promissory_notes``,
    # tajnej). Puste do czasu, aż silnik zacznie obsługiwać zagrywanie notek; dziś
    # edytowalne przez God-Mode. NIE mieszać z ręką: ręka jest ukryta, strefa — jawna.
    promissory_notes_in_play: list[str] = Field(default_factory=list)

    # Zdobyte (ujawnione) tajne cele gracza — identyfikatory kart, w kolejności zdobycia.
    # JAWNE: tajny cel po zdobyciu leży odkryty w strefie gracza (R_objective_cards).
    scored_secrets: list[str] = Field(default_factory=list)

    # Prywatne ręce gracza (karty akcji, tajne obiektywy, promissory notes) —
    # TAJNE (Private_Info), widoczne tylko właścicielowi (R1.1–R1.3, R2.3).
    # Domyślnie puste ręce (R1.10).
    private: PlayerPrivateState = Field(default_factory=PlayerPrivateState)
    # Liczniki ukrytych kart — wypełniane WYŁĄCZNIE przez projekcję widoczności dla
    # graczy ≠ viewer (R4.4). W pełnym (niezredagowanym) stanie zawsze pusty słownik.
    # Fragmenty relikt├│w (karty eksploracji) le┼╝─ůce odkryte w strefie gracza ÔÇö identyfikatory
    # kart (RULES.md 46). JAWNE: regu┼éa ka┼╝e po┼éo┼╝y─ç je ÔÇ×faceup in play area".
    relic_fragments: list[str] = Field(default_factory=list)

    # Klucze: "action_cards" / "secret_objectives" / "promissory_notes".
    hidden_card_counts: dict[str, int] = Field(default_factory=dict)


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
    # Jednostki USZKODZONE (Sustain Damage, RULES.md 39 W8): {strefa: {player_id:
    # {base_type: liczba}}}, strefa = "space" albo id planety. Liczba ≤ liczba jednostek
    # (odczyt przycinany w ``core/damage.py``). Naprawa w fazie statusu (W10).
    damaged_units: dict[str, dict[str, dict[str, int]]] = Field(default_factory=dict)


class CombatStep(StrEnum):
    """Krok trwającej walki (RULES.md 39.2)."""

    AFB = "AFB"  # Anti-Fighter Barrage (tylko 1. runda walki kosmicznej)
    ANNOUNCE = "ANNOUNCE"  # ogłoszenie odwrotów (okno COMBAT_RETREAT) — RULES.md 39.5
    ROLL = "ROLL"  # rzuty combat obu stron
    ASSIGN = "ASSIGN"  # przypisanie strat (okno COMBAT_ASSIGN_HITS)
    RETREAT = "RETREAT"  # wykonanie ogłoszonego odwrotu (wybór systemu) — RULES.md 39.5
    DONE = "DONE"  # walka zakończona (zwycięzca/remis), czeka na zamknięcie okna


class ActiveCombat(BaseModel):
    """Trwająca walka w aktywnym systemie (RULES.md 39.3).

    ``kind`` = "space" albo "ground" (wtedy ``planet`` = id planety). ``attacker`` to
    aktywny gracz (W1). ``pending_hits`` = trafienia do pokrycia przez danego gracza
    (wyprodukowane przez przeciwnika). ``rolls`` = rzuty bieżącej rundy per gracz,
    ``afb`` = rzuty AFB, ``log`` = historia rund (zasila okno pola bitwy).
    """

    model_config = ConfigDict(extra="forbid")

    kind: str
    position: str
    planet: str | None = None
    attacker: str
    defender: str
    round: int = 1
    step: CombatStep = CombatStep.ROLL
    pending_hits: dict[str, int] = Field(default_factory=dict)
    rolls: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    afb: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    log: list[dict[str, Any]] = Field(default_factory=list)
    winner: str | None = None
    # Wynik zakończonej walki: "winner" / "draw" (None, dopóki trwa).
    outcome: str | None = None
    # Odwroty (RULES.md 39.5): gracze, którzy OGŁOSILI odwrót w bieżącej rundzie (wykonanie w
    # kroku RETREAT) oraz wykonane odwroty {player_id: pozycja systemu docelowego}.
    retreating: list[str] = Field(default_factory=list)
    retreated: dict[str, str] = Field(default_factory=dict)


class InvasionPhase(StrEnum):
    """Podkrok inwazji (RULES.md 40.2): Bombardment → Commit → Space Cannon Defense →
    Ground Combat → Establish Control."""

    BOMBARDMENT = "BOMBARDMENT"
    COMMIT = "COMMIT"
    SPACE_CANNON_DEFENSE = "SPACE_CANNON_DEFENSE"
    GROUND_COMBAT = "GROUND_COMBAT"
    ESTABLISH = "ESTABLISH"


class InvasionState(BaseModel):
    """Trwająca inwazja w aktywnym systemie (RULES.md 40.3).

    ``committed`` = siły naziemne zlądowane w tej inwazji ``{planeta: {base_type: n}}``.
    ``bombard_pending`` / ``defense_pending`` = trafienia czekające na przypisanie strat
    (bombardowanie: obrońca planety; Space Cannon Defense: atakujący). ``log`` = historia
    rozstrzygnięć bombardowania i obrony (zasila okno inwazji), ``combat_results`` = wynik
    zamkniętej walki naziemnej per planeta, ``results`` = wyniki Establish Control.
    """

    model_config = ConfigDict(extra="forbid")

    position: str
    attacker: str
    phase: InvasionPhase = InvasionPhase.BOMBARDMENT
    bombarded: bool = False
    bombard_pending: dict[str, int] = Field(default_factory=dict)
    committed: dict[str, dict[str, int]] = Field(default_factory=dict)
    defense_resolved: list[str] = Field(default_factory=list)
    defense_pending: dict[str, int] = Field(default_factory=dict)
    combat_results: dict[str, dict[str, Any]] = Field(default_factory=dict)
    results: list[dict[str, Any]] = Field(default_factory=list)
    log: list[dict[str, Any]] = Field(default_factory=list)


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
    # Ile jednostek wyprodukowano już w TEJ akcji taktycznej (limit PRODUCTION jest
    # wspólny dla całego kroku, nie per zamówienie — RULES.md 33.3). Zerowane przy
    # aktywacji i zakończeniu akcji.
    production_used: int = 0
    # Co wyprodukowano w tej akcji i gdzie: strefa ("space"/id planety) → typ → sztuki.
    # Potrzebne, bo (1) osobne zdolności PRODUCTION mają ograniczenia typów (Arborec: dok nie
    # produkuje piechoty), (2) świeżo wyprodukowane jednostki NIE dokładają PRODUCTION w tym
    # samym kroku (np. piechota Arborec).
    production_placed: dict[str, dict[str, int]] = Field(default_factory=dict)
    # Otwarte okno czasowe (timing window) — None, gdy żadne nie trwa. Trzyma kolejkę
    # graczy reagujących po kolei (secondary kart strategii, przypisanie strat w walce,
    # space cannon, reakcje „when/after"). Jedno pojęcie dla całej interakcji między
    # graczami (RULES.md 29.2). Mechanika: ``core/timing.py``.
    pending_window: TimingWindow | None = None
    # Generator losowy silnika (rzuty kośćmi — ``core/dice.py``). ``rng_seed`` = 0 oznacza
    # „jeszcze nie zasiane": pierwszy rzut losuje ziarno i zapisuje je w stanie. Ziarno +
    # licznik są częścią stanu, więc Undo/Redo i powtórka migawki dają TE SAME wyniki.
    rng_seed: int = 0
    rng_counter: int = 0
    # Dziennik ostatniego rozstrzygnięcia Space Cannon Offense (JSON listy wpisów). Okno
    # czasowe znika po ostatnim graczu, a panel musi nadal pokazać, co się stało (rzuty,
    # trafienia, straty) — do końca akcji taktycznej (RULES.md 38.3).
    space_cannon_log: str = "[]"
    # Trwająca walka (kosmiczna/naziemna) — None, gdy żadna nie trwa (RULES.md 39).
    active_combat: ActiveCombat | None = None
    # Trwająca inwazja (krok INVASION akcji taktycznej) — None, gdy żadna (RULES.md 40).
    invasion: InvasionState | None = None
    # Trade goods leżące na kartach strategii: {numer_inicjatywy: liczba_TG}.
    # Niewybrane karty akumulują +1 TG na koniec fazy strategii; wybór przekazuje
    # TG graczowi i zeruje licznik (RULES.md 13).
    strategy_card_tg: dict[int, int] = Field(default_factory=dict)

    # Cele publiczne, talie wspólne i stan fazy statusu (RULES.md 41). ``status`` = None
    # poza fazą statusu (i dla stanów wprowadzonych God-Mode bez inicjalizacji kroków).
    objectives: ObjectivesState = Field(default_factory=ObjectivesState)
    decks: DecksState = Field(default_factory=DecksState)
    status: StatusPhaseState | None = None
    # Setup startowy (tajne cele, żeton Custodians, odkrycie celów) — None, gdy zakończony
    # albo gdy stan nie przechodził przez ``/game/new`` (testy, God-Mode). RULES.md 43.
    setup: SetupState | None = None
    # Żeton Custodians zdjęty z Mecatol Rex => faza agendy dodana do KAŻDEJ rundy
    # (R_custodians_token). Do czasu zdjęcia status kończy rundę bez fazy agendy.
    custodians_removed: bool = False
    # Próg punktów zwycięstwa (R_victory_points: 10, albo 14 na drugiej stronie toru).
    vps_to_win: int = 10
    # Zwycięzca (koniec gry) — None, dopóki gra trwa.
    winner_id: str | None = None

    players: dict[str, PlayerState] = Field(default_factory=dict)
    systems: dict[str, SystemState] = Field(default_factory=dict)

    def clone(self) -> GameState:
        """Zwraca głęboką kopię stanu (przez walidowaną serializację)."""
        return GameState.model_validate(self.model_dump())
    # ┼╗etony obietnic (nieformalna zasada sto┼éu, NIE regu┼éa TI4 ÔÇö RULES.md 47.3): ma┼ée ┼╝etony
    # kontroli gracza-wystawcy oddane innemu graczowi jako ÔÇ×d┼éug"/obietnica (np. 3 TG do
    # zap┼éaty = 3 ┼╝etony). Niewi─ů┼╝─ůce dla silnika, tylko pami─Ö─ç sto┼éu. Format:
    # ``{holder_id: {issuer_id: liczba}}`` ÔÇö kto trzyma czyje ┼╝etony. Wpisy z zerem znikaj─ů.
    promise_tokens: dict[str, dict[str, int]] = Field(default_factory=dict)
