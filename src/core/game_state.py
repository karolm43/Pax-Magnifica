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

from src.core.expedition_state import ExpeditionState, FractureState


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


class StrategyResolution(BaseModel):
    """Trwające, WIELOETAPOWE rozstrzyganie PRIMARY karty strategii (RULES.md 30.5).

    Większość kart wymaga wyborów aktywnego gracza (kogo wskazać, który system, jaką
    technologię...). Zamiast jednego strzału, primary idzie krok po kroku: ``step`` to
    bieżący krok, ``draft`` zbiera dotychczasowe wybory (walidowane, ale jeszcze NIE
    zastosowane). Efekt stosuje się atomowo po ostatnim kroku. Tylko ``owner_id`` może
    odpowiadać (serwer sprawdza tożsamość — pod grę sieciową). Po primary otwiera się
    okno ``STRATEGY_SECONDARY`` (``pending_window``), a ten obiekt znika.
    """

    model_config = ConfigDict(extra="forbid")

    initiative: int
    owner_id: str
    step: str
    draft: dict[str, Any] = Field(default_factory=dict)
    # Primary wykonane z karty akcji Overrule: po nim NIE otwiera się okno secondary
    # (wykonujemy wyłącznie primary; RULES.md 53).
    no_secondary: bool = False
    # Tylko ci gracze mogą rozstrzygnąć secondary (Mathis Mathinus, RULES.md 62.7); None = wszyscy.
    secondary_players: list[str] | None = None


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

class ActiveEffect(BaseModel):
    """Efekt trwały z czasem trwania (RULES.md 54): wygasa na końcu swojego zakresu.

    ``scope`` to wartość ``game_events.Duration`` (turn / tactical_action / combat / combat_round /
    invasion / agenda / phase / round / game). Efekt zostaje, nawet gdy komponent, który go
    wywołał, zniknął z gry (R_abilities). ``key`` wskazuje źródło hooka
    (``HookSource(effect, key)``).
    Zmienia go WYŁĄCZNIE ``core/active_effects.py``.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    key: str
    scope: str
    owner: str | None = None  # None = dotyczy wszystkich graczy
    created_round: int = 1
    data: dict[str, Any] = Field(default_factory=dict)


class PendingOffer(BaseModel):
    """Opcjonalna reakcja („you may ...”) czekająca na decyzję gracza (RULES.md 54).

    Powstaje z hooka TRIGGER/REPLACE oznaczonego ``optional``, gdy źródło jest PUBLICZNE (frakcja,
    technologia, relikt w grze, lider...). Karty z ręki nie tworzą ofert (nie zdradzamy ręki).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    player_id: str  # decydent (odpowiada na ofertę)
    event: str
    moment: str
    hook_seq: int
    label: str = ""
    ctx: dict[str, Any] = Field(default_factory=dict)
    # Właściciel źródła hooka, gdy to NIE decydent (np. Assault Cannon: ofiara decyduje, kogo
    # statek ginie); None = właściciel == ``player_id``.
    owner_id: str | None = None
    # Decyzja obowiązkowa (bez prawa odmowy), np. wybór celu efektu, który i tak następuje.
    mandatory: bool = False


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


class AgendaStep(StrEnum):
    """Krok fazy agendy, na którym stoi gra (R_agenda_phase, RULES.md 51).

    - ``REVEAL`` — mówca ma ujawnić kolejną agendę (krok 1/2: „Reveal Agenda");
    - ``VOTE`` — gracze głosują po kolei od lewej mówcy (mówca ostatni);
    - ``TIEBREAK`` — remis albo brak głosów: mówca (nie głosem) wybiera wynik;
    - ``COUNTED`` — głosy policzone, wynik (``pending_outcome``) jeszcze NIE rozstrzygnięty:
      pauza na reakcje (Bribery, Distinguished Councilor, Confounding/Confusing Legal Text,
      Deadly Plot - RULES.md 53.5.a); mówca potwierdza (``confirm_outcome``). Pauza powstaje
      tylko wtedy, gdy któryś gracz trzyma kartę reakcji na ten moment (⚠ ZAŁOŻENIE);
    - ``RESOLVED`` — wynik ustalony i widoczny, czeka na „dalej" mówcy;
    - ``COMPLETE`` — obie agendy rozstrzygnięte, planety odświeżone (krok 3);
      czeka na „Next phase" mówcy.
    """

    REVEAL = "REVEAL"
    VOTE = "VOTE"
    TIEBREAK = "TIEBREAK"
    COUNTED = "COUNTED"
    RESOLVED = "RESOLVED"
    COMPLETE = "COMPLETE"


class AgendaVote(BaseModel):
    """Oddane głosy jednego gracza: jeden wynik, wyczerpane planety i suma głosów."""

    model_config = ConfigDict(extra="forbid")

    outcome: str
    votes: int
    planets: list[str] = Field(default_factory=list)
    # Technologie użyte do tego głosu (Predictive Intelligence: +3 głosy). Wyczerpanie karty
    # zapada dopiero po rozstrzygnięciu agendy (gdy wynik głosu przegrał).
    techs: list[str] = Field(default_factory=list)


class AgendaPhaseState(BaseModel):
    """Stan trwającej fazy agendy (``None`` poza nią) — RULES.md 51.

    ``agenda_number`` = 1 albo 2 (faza rozstrzyga dwie agendy). ``kind`` = rodzaj wyniku
    wyliczony z pola ``target`` karty (``for_against``, ``player``, ``planet``…), a
    ``outcomes`` = dopuszczalne wyniki zamrożone w chwili ujawnienia (głosowanie nie zmienia
    się w trakcie). ``votes`` = oddane głosy (klucz = player_id), ``abstained`` = gracze,
    którzy zrezygnowali, ``blocked`` = gracze, którzy NIE mogą głosować przez efekt gry.
    ``history`` = rozstrzygnięte agendy tej fazy (panel i podsumowanie).
    """

    model_config = ConfigDict(extra="forbid")

    step: AgendaStep = AgendaStep.REVEAL
    agenda_number: int = 1
    agenda_id: str | None = None
    kind: str = ""
    outcomes: list[str] = Field(default_factory=list)
    # Nie da się rozstrzygnąć (brak kandydatów, np. „Elect Law" bez praw w grze) — mówca odrzuca.
    unresolvable: bool = False
    vote_order: list[str] = Field(default_factory=list)
    votes: dict[str, AgendaVote] = Field(default_factory=dict)
    abstained: list[str] = Field(default_factory=list)
    blocked: list[str] = Field(default_factory=list)
    tied: list[str] = Field(default_factory=list)
    resolved_outcome: str | None = None
    decided_by_speaker: bool = False
    # Gracz, który OSTATNI oddał głosy (okno „po tym, jak oddasz głosy"); czyści go następna
    # decyzja (wstrzymanie się innego gracza) albo rozstrzygnięcie. Karty: Distinguished Councilor.
    last_vote_by: str | None = None
    # Wynik czekający na rozstrzygnięcie w kroku ``COUNTED`` (po podmianie wybranego gracza
    # przez Confounding/Confusing Legal Text zawiera już nowego wybranego).
    pending_outcome: str | None = None
    pending_by_speaker: bool = False
    history: list[dict[str, Any]] = Field(default_factory=list)
    # Gracze, którzy NIE mogą głosować do końca TEJ FAZY (Public Execution) - dopisywani do
    # ``blocked`` każdej kolejnej agendy fazy.
    phase_blocked: list[str] = Field(default_factory=list)
    # Covert Legislation: ukryta agenda dobrana przez mówcę; gracze głosują nad jej wynikami,
    # rozstrzyga się JEJ efekt (jawna dopiero przy rozstrzygnięciu; widzi ją tylko mówca).
    covert_card: str | None = None
    # Karta, której efekt właśnie się rozstrzyga (krok RESOLVED) - źródło hooków agendy dla
    # KAŻDEGO gracza, dopóki decyzje graczy z jej efektu nie zostaną podjęte.
    resolving: str | None = None
    # Miscount Disclosed: prawo, nad którym głosuje się ponownie po „dalej” mówcy.
    revote_law: str | None = None
    # Agenda, przy której ktoś już zagrał kartę w oknie „after an agenda is revealed” (ridery,
    # Sanction...): okno „when revealed” (Veto, Diplomatic Pressure) jest wtedy zamknięte -
    # wszystkie „when” przed „after” (R_abilities, ruling Veto). Veto zmienia agendę = nowe okno.
    after_reveal_played: str | None = None


class ObjectivesState(BaseModel):
    """Cele publiczne gry: talie, odkryte i zdobyte (RULES.md 41.1).

    ``stage1_deck`` / ``stage2_deck`` = ZAKRYTE cele (od góry talii, ``[0]`` = następny do
    odkrycia). Setup losuje po 5 z każdego etapu, a mówca odkrywa dwa cele I etapu
    (R_objective_cards). ``revealed`` = odkryte w kolejności odsłaniania (I i II etap).
    ``scored`` = ``{id_celu: [player_id, ...]}`` — kto zdobył dany cel publiczny (też
    „inne punkty": custodians itd.); powtórzony gracz = punkt zdobyty wielokrotnie.
    ``custom_points`` = ``{klucz: VP}`` dla punktów spoza kart (custodians, imperial...).
    ``point_sources`` = rejestr VP spoza kart celów: ``{źródło: {player_id: VP netto}}``
    (``objectives.award_points(source=...)``; np. ``relics:shard``, ``planets:styx``).
    Klucz źródła zostaje po utracie punktu - panel „Other points" dalej go pokazuje.
    """

    model_config = ConfigDict(extra="forbid")

    stage1_deck: list[str] = Field(default_factory=list)
    stage2_deck: list[str] = Field(default_factory=list)
    revealed: list[str] = Field(default_factory=list)
    scored: dict[str, list[str]] = Field(default_factory=dict)
    custom_points: dict[str, int] = Field(default_factory=dict)
    point_sources: dict[str, dict[str, int]] = Field(default_factory=dict)


class DecksState(BaseModel):
    """Talie wspólne: karty akcji i tajne cele (kolejność = od góry, ``[0]`` dobierana)."""

    model_config = ConfigDict(extra="forbid")

    action_card_deck: list[str] = Field(default_factory=list)
    action_card_discard: list[str] = Field(default_factory=list)
    secret_objective_deck: list[str] = Field(default_factory=list)
    # Talia agend (kolejność = od góry) i stos odrzuconych. Powstaje LENIWIE przy pierwszym
    # użyciu (Politics: podgląd; faza agendy) - ``agenda_deck_seeded`` odróżnia „jeszcze nie
    # zasiana" od „zużyta". Mechanika: ``core/card_draw.py``.
    agenda_deck: list[str] = Field(default_factory=list)
    agenda_discard: list[str] = Field(default_factory=list)
    agenda_deck_seeded: bool = False
    # Moduły wariantów gry (``assets/config/variants.json``, ``core/variants.py``): fanowskie
    # talie, erraty kart, własne komponenty. Ustawiane raz w ``/game/new``; decydują o składzie
    # talii (agendy, relikty, karty akcji, eksploracje, cele) i podmianie wspólnych notek.
    variants: list[str] = Field(default_factory=list)
    # Talia agend gry - "standard" albo źródło modułu talii agend (np. "absol"). Pole zgodności
    # wstecz (front: ``cardPool.agendaVariant``); źródłem prawdy jest ``variants``.
    agenda_variant: str = "standard"
    # Prawa (laws) w grze: {id agendy: rozstrzygnięty wynik ("for" / id gracza / id planety…)}.
    # Prawo zostaje w grze po wyniku „For" albo „Elect" (R_agenda_card); dyrektywy i „Against"
    # trafiają na ``agenda_discard``. Efekty praw NIE są kodowane - to tylko ewidencja
    # (RULES.md 51).
    agenda_laws: dict[str, str] = Field(default_factory=dict)
    # Talie eksploracji (RULES.md 46): klucz = "cultural"/"hazardous"/"industrial"/"frontier".
    # Talia powstaje LENIWIE przy pierwszym dobraniu (brak klucza = jeszcze niezasiana);
    # pusta talia tasuje się z własnego stosu odrzuconych. Karty, które się purge'ują
    # (żetony wormhole), nie trafiają na stos odrzuconych.
    exploration_deck: dict[str, list[str]] = Field(default_factory=dict)
    exploration_discard: dict[str, list[str]] = Field(default_factory=dict)
    # Stos kart PURGE'OWANYCH (usuniętych z gry): karty eksploracji i inne — wspólny dla
    # wszystkich talii. Purge to nie odrzucenie: te karty nie wracają przy tasowaniu.
    purged: list[str] = Field(default_factory=list)
    # Karty leżące we WSPÓLNEJ strefie gry (Ion Storm: żeton w systemie, karta obok planszy).
    common_play_area: list[str] = Field(default_factory=list)
    # Talia reliktów (Thunder's Edge: planety The Fracture, RULES.md 50) — od góry; tworzona
    # LENIWIE (``core/relics.py``), ``relic_deck_seeded`` odróżnia „niezasiana" od „zużyta".
    relic_deck: list[str] = Field(default_factory=list)
    relic_discard: list[str] = Field(default_factory=list)
    relic_deck_seeded: bool = False


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
    # Tajne cele INNYCH graczy pokazane tej osobie przez efekt karty (Extreme Duress):
    # {właściciel: [cele]}. Migawka z chwili pokazania; pole prywatne, więc projekcja ukrywa je.
    revealed_secrets: dict[str, list[str]] = Field(default_factory=dict)
    # Podgląd wierzchnich agend (Insider Information) - TAJNY, tylko dla właściciela; zmienia go
    # wyłącznie ``card_draw.peek_agenda_top``, czyści ``card_draw.clear_agenda_peek``.
    agenda_peek: list[str] = Field(default_factory=list)
    # „Skip all reactions” (RULES.md 54.11): silnik pasuje za gracza w każdym oknie reakcji, także
    # gdy ma kartę do zagrania. Ustawienie TAJNE (okno trwa tyle samo, z zewnątrz nic nie widać).
    auto_pass_reactions: bool = False


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
    # Jednostki piechoty „leżące na karcie" Infantry II (odrodzone rzutem 6+); na początku
    # następnej tury wracają na planetę w systemie domowym (RULES.md 55.8).
    infantry_ii_on_card: int = 0

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
    # Ile akcji gracz wykonał w BIEŻĄCEJ turze (limit: ``core/action_budget``; bazowo 1, Fleet
    # Logistics 2). ``took_action_this_turn`` zostaje flagą „co najmniej jedna" (End turn).
    actions_this_turn: int = 0
    # Z kim (``player_id`` partnera) aktywny gracz JUŻ rozstrzygnął transakcję w tej turze
    # (RULES.md 47, R_transactions: „up to one transaction with each of their neighbors").
    # Resetowane razem z ``took_action_this_turn`` (nowa tura). Utrata i ponowne uzyskanie
    # sąsiedztwa w tej samej turze NIE daje drugiej transakcji — stąd lista, nie wyliczenie.
    transacted_with: list[str] = Field(default_factory=list)
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

    # Fragmenty reliktów (karty eksploracji) leżące odkryte w strefie gracza — identyfikatory
    # kart (RULES.md 46). JAWNE: reguła każe położyć je „faceup in play area".
    relic_fragments: list[str] = Field(default_factory=list)
    # Relikty gracza (karty z talii reliktów) leżące odkryte w jego strefie. JAWNE.
    # Efekty: ``core/relic_cards.py`` + ``core/hooks/relics_*.py`` (RULES.md 59).
    relics: list[str] = Field(default_factory=list)
    # Karty frontier leżące odkryte u gracza (Enigmatic Device). JAWNE; w UI w zakładce Action
    # cards, zagrywane jak akcja komponentu (``core/frontier_cards.py``).
    frontier_cards: list[str] = Field(default_factory=list)
    # Relikty WYCZERPANE (exhaust) - gotowy = posiadany, którego tu nie ma. Odświeżane w statusie.
    exhausted_relics: list[str] = Field(default_factory=list)
    # Karty zdolności legendarnych planet WYCZERPANE (id planety). Wyczerpują się i odświeżają
    # NIEZALEŻNIE od karty planety (R_legendary_planets); odświeżane w statusie, krok 6.
    exhausted_legendaries: list[str] = Field(default_factory=list)

    # Prywatne ręce gracza (karty akcji, tajne obiektywy, promissory notes) —
    # TAJNE (Private_Info), widoczne tylko właścicielowi (R1.1–R1.3, R2.3).
    # Domyślnie puste ręce (R1.10).
    private: PlayerPrivateState = Field(default_factory=PlayerPrivateState)
    # Liczniki ukrytych kart — wypełniane WYŁĄCZNIE przez projekcję widoczności dla
    # graczy ≠ viewer (R4.4). W pełnym (niezredagowanym) stanie zawsze pusty słownik.
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
    # Żeton frontier w przestrzeni systemu (R_frontier_tokens): kładziony w setupie na każdym
    # systemie bez planet; max jeden na system. Zdejmowany przez eksplorację (poza zakresem).
    frontier_token: bool = False
    # Żetony wormhole położone w systemie (np. Gamma Wormhole z eksploracji): lista typów
    # ("GAMMA"...). Dodają systemowi sąsiedztwo przez wormhole — mapa (HexGrid) jest z nich
    # synchronizowana przy każdym odczycie stanu (RULES.md 46).
    wormhole_tokens: list[str] = Field(default_factory=list)
    # Żeton Ion Storm (karta frontier): aktywna strona = typ wormhole ("ALPHA"/"BETA"), None =
    # brak żetonu. Obraca go ``core/ion_storm.py`` na końcu kroku ruchu / odwrotu.
    ion_storm: str | None = None
    # Żeton ingress (The Fracture, RULES.md 50): system z ingressem sąsiaduje z każdym systemem
    # z egressem. Max jeden na system. Mapa jest z niego synchronizowana (jak wormhole_tokens).
    ingress_token: bool = False
    # Planety DOŁOŻONE do systemu w trakcie gry (Thunder's Edge kładziony na pusty system).
    # Pełna lista planet systemu = ``SystemDef.planets`` + to pole (``core/system_planets.py``).
    added_planets: list[str] = Field(default_factory=list)
    # Planety ZNISZCZONE w trakcie gry (Stellar Converter): leży na nich „destroyed planet token”,
    # system liczy się tak, jakby ich nie miał (``core/system_planets.py``).
    destroyed_planets: list[str] = Field(default_factory=list)

    def token_wormholes(self) -> list[str]:
        """Typy wormhole z żetonów w systemie: Gamma itd. + aktywna strona Ion Storm."""
        found = list(self.wormhole_tokens)
        if self.ion_storm and self.ion_storm not in found:
            found.append(self.ion_storm)
        return found


class CombatStep(StrEnum):
    """Krok trwającej walki (RULES.md 39.2)."""

    AFB = "AFB"  # Anti-Fighter Barrage (tylko 1. runda walki kosmicznej)
    ANNOUNCE = "ANNOUNCE"  # ogłoszenie odwrotów (okno COMBAT_RETREAT) — RULES.md 39.5
    ROLL = "ROLL"  # rzuty combat obu stron
    ASSIGN = "ASSIGN"  # przypisanie strat (okno COMBAT_ASSIGN_HITS)
    RETREAT = "RETREAT"  # wykonanie ogłoszonego odwrotu (wybór systemu) — RULES.md 39.5
    TRIGGERS = "TRIGGERS"  # walka czeka na decyzje graczy w ofertach (zdolności startu/końca rundy)
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
    # Jednorazowe efekty komponentów poza rundami (np. Assault Cannon: kto, czyj statek, jaki typ)
    # — tylko do animacji w oknie bitwy; NIE wpisy ``log`` (pusty ``log`` = start walki).
    effects: list[dict[str, Any]] = Field(default_factory=list)
    winner: str | None = None
    # Wynik zakończonej walki: "winner" / "draw" (None, dopóki trwa).
    outcome: str | None = None
    # Odwroty (RULES.md 39.5): gracze, którzy OGŁOSILI odwrót w bieżącej rundzie (wykonanie w
    # kroku RETREAT) oraz wykonane odwroty {player_id: pozycja systemu docelowego}.
    retreating: list[str] = Field(default_factory=list)
    retreated: dict[str, str] = Field(default_factory=dict)
    # Od czego wznowić walkę po rozstrzygnięciu decyzji graczy w kroku TRIGGERS (RULES.md 56):
    # "start" (po hookach startu walki) albo "round_end:<KROK>" (po hookach końca rundy).
    resume: str = ""
    # Ślady dla kart reakcji w walce (RULES.md 53.5.c): statki zniszczone / użycia Sustain Damage
    # od ostatnich rzutów (czyszczone na początku kolejnej rundy rzutów). Wpis zniszczenia:
    # ``{"player", "base_type", "hits_on"}``; wpis sustain: ``{"player", "base_type", "count"}``.
    destroyed_ships: list[dict[str, Any]] = Field(default_factory=list)
    # Gracze, których okręt flagowy został zniszczony W TEJ walce (przez kogokolwiek, także
    # przez siebie). Cały czas walki - nie czyszczone co rundę. Cel Unveil Flagship (uf).
    flagships_destroyed: list[str] = Field(default_factory=list)
    # Gracze, którzy zdobyli cel W TRAKCIE albo PO tej walce: najwyżej jeden cel dowolnego typu
    # na walkę (R_objective_cards, C_relics Neuraloop). Osobna walka = osobny limit.
    objective_scorers: list[str] = Field(default_factory=list)
    sustained_ships: list[dict[str, Any]] = Field(default_factory=list)
    # Przypisanie strat po AFB z Waylay: krok ASSIGN traktowany jak koniec kroku AFB.
    afb_assign: bool = False
    # Gracze, którzy w tej walce użyją nadanego AFB (Metali Void Armaments: „you may resolve AFB
    # 6 (x3)"): zgoda z oferty na starcie walki; rzut dopisuje ``battle.resolve_afb``.
    afb_extra: list[str] = Field(default_factory=list)
    # Dodatkowe kości AFB (commander Argent, Strike Wing Ambuscade): wybór gracza przed rzutem
    # ``{gracz: {źródło: base_type | "auto" | "none"}}``; brak wpisu = „auto” (RULES.md 62.11).
    afb_picks: dict[str, dict[str, str]] = Field(default_factory=dict)
    # Trafienia z rzutów „na starcie walki” (Ambush, RULES.md 62.8) czekające na przypisanie przez
    # ``{gracz: liczba}`` — przypisuje je zwykły krok ASSIGN przed AFB (``start_assign``).
    start_hits: dict[str, int] = Field(default_factory=dict)
    start_assign: bool = False
    # Ostatnia strona przypisania użyła Sustain Damage, a ktoś może odpowiedzieć (Direct Hit,
    # Reflective Shielding): walka stoi w kroku ASSIGN (okno zamknięte) na czas pauzy ochronnej,
    # potem ``battle.release_sustain_hold`` (z ``step_settle``) prowadzi ją dalej (RULES.md 54.10).
    sustain_hold: bool = False
    # Wszystkie statki zniszczone w TEJ walce (nie czyszczone co rundę, w odróżnieniu od
    # ``destroyed_ships``); wpis ``{"player", "base_type"}`` z ``unit_ops._note_combat_loss``.
    # Salvage Operations, Sleeper Cell (RULES.md 62.8).
    destroyed_all: list[dict[str, Any]] = Field(default_factory=list)
    # Wymagany cel trafień czekających na przypisanie (Impulse Core, Devotion - RULES.md 62.10):
    # ``{gracz: {"types": [base_type…], "count": n}}`` - co najmniej ``n`` trafień na te typy.
    hit_targets: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # Trafienia po rundzie (Devotion) czekające na przypisanie / krok ASSIGN dla nich: po nim runda
    # kończy się bez ponownych zdarzeń końca rundy (``battle.add_round_end_hits``).
    round_end_hits: dict[str, int] = Field(default_factory=dict)
    round_end_assign: bool = False


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
    # Aktywny gracz zdjął w tej inwazji żeton Custodians => MUSI zlądować na Mecatol Rex
    # (R_custodians_token); bez tego nie przejdzie z kroku Commit Ground Forces.
    custodians_claimed: bool = False
    # Ostatnie zaangażowanie sił naziemnych ``{planeta: {base_type: n}}`` w kroku COMMIT - okno
    # kart reakcji „po zaangażowaniu jednostek” (Ghost Squad, Parley). Zerowane przy wejściu w
    # inny podkrok inwazji.
    last_commit: dict[str, dict[str, int]] = Field(default_factory=dict)
    # Siły naziemne zwrócone do przestrzeni przez Parley: w tej akcji nie wolno ich zaangażować
    # na inną planetę (R_parley, Notes) - ``{base_type: n}`` odejmowane od puli do lądowania.
    parley_locked: dict[str, int] = Field(default_factory=dict)
    # Inwazja komponentu poza akcją taktyczną (Quantum Dissemination, RULES.md 62.10): klucz
    # źródła (``leaders:yinhero``) i kolejne systemy ``[{"position", "committed"}]`` - po
    # zamknięciu tej inwazji otwiera się następna. Pusty ``source`` = zwykła inwazja taktyczna.
    source: str = ""
    queue: list[dict[str, Any]] = Field(default_factory=list)


class ProductionGrant(BaseModel):
    """Jednorazowe prawo do produkcji z efektu karty (np. Freelancers), poza krokiem PRODUCTION.

    ``units`` = ile jednostek wolno wyprodukować (zamiast limitu z wartości PRODUCTION),
    ``influence_as_resources`` = planeta płaci wpływem tak, jakby był zasobami. Znika po
    produkcji albo rezygnacji (RULES.md 46).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    position: str
    units: int = 1
    influence_as_resources: bool = False
    source: str = ""
    # ``standalone`` = produkcja POZA akcją taktyczną (karty strategii: Construction/Warfare).
    # Obowiązują wtedy ZWYKŁE reguły produkcji (limit z wartości PRODUCTION, typy, blokada)
    # w systemie ``position`` dla ``player_id`` (może to być nie-aktywny gracz), a ``units``
    # jest ignorowane. Granta nie zużywa jedno ``produce`` - trwa do ``skip_grant`` („Finish").
    standalone: bool = False
    # Opcjonalne zawężenie do jednego producenta (Construction: JEDEN dok) - id planety,
    # na której stoi dok. ``None`` = wszyscy producenci w systemie (Warfare, TE).
    zone: str | None = None
    # ``free`` = produkcja BEZ użycia PRODUCTION jednostek, poza akcją taktyczną i w dowolnym
    # systemie (Sling Relay, Integrated Economy): limit to ``units``, bez wymogu doków, strefy
    # ograniczone do ``zone`` (planeta) i przestrzeni. ``max_cost`` = górny limit łącznego
    # kosztu (Integrated Economy: zasoby planety), ``ships_only`` = tylko statki (Sling Relay).
    free: bool = False
    max_cost: float | None = None
    ships_only: bool = False
    # Dozwolone typy jednostek (``base_type``); pusta lista = bez ograniczenia. Salvage Operations:
    # typy statków zniszczonych w walce (RULES.md 62.8).
    allowed_types: list[str] = Field(default_factory=list)
    # Kolejne systemy tej samej produkcji (bohater Arborec: „in any number of systems") - po
    # produkcji/rezygnacji grant przechodzi do następnej pozycji (``production.next_grant``).
    queue: list[str] = Field(default_factory=list)


class ExploreCurrent(BaseModel):
    """Odkryta (ujawniona wszystkim) karta eksploracji czekająca na rozstrzygnięcie."""

    model_config = ConfigDict(extra="forbid")

    planet: str
    deck: str  # "cultural" / "hazardous" / "industrial"
    card_id: str


class ExplorationState(BaseModel):
    """Okno eksploracji po Establish Control (RULES.md 46).

    ``queue`` = planety czekające na eksplorację (gracz wybiera kolejność; jedna karta
    rozstrzygana w całości przed następną). ``current`` = ujawniona karta. ``log`` = historia
    rozstrzygnięć tego okna. Okno zamyka ``exploration.finish`` (gdy kolejka pusta).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    position: str
    queue: list[str] = Field(default_factory=list)
    current: ExploreCurrent | None = None
    log: list[dict[str, Any]] = Field(default_factory=list)


class GameChronicle(BaseModel):
    """Dziennik wydarzeń partii do podsumowania końcowego (``core/chronicle.py``).

    Tylko do odczytu dla UI: bitwy, podboje planet i transakcje między graczami. Wpisy to
    proste słowniki (runda, gracze, liczby) — z nich powstają „wnioski" (największa bitwa,
    zdrady itd.).
    """

    model_config = ConfigDict(extra="forbid")

    battles: list[dict[str, Any]] = Field(default_factory=list)
    conquests: list[dict[str, Any]] = Field(default_factory=list)
    deals: list[dict[str, Any]] = Field(default_factory=list)
    # Migawki VP po punktowaniu każdej rundy: ``{"round": n, "vp": {player_id: punkty}}``.
    rounds: list[dict[str, Any]] = Field(default_factory=list)


class EpilogueState(BaseModel):
    """Głosowanie nad rodzajem zwycięstwa (honorowe / niehonorowe) po końcu gry.

    Głosują wszyscy gracze OPRÓCZ zwycięzcy (``core/epilogue.py``). ``votes`` =
    ``{player_id: "honorable" | "dishonorable"}``; ``result`` ustawiane, gdy zagłosują
    wszyscy uprawnieni.
    """

    model_config = ConfigDict(extra="forbid")

    votes: dict[str, str] = Field(default_factory=dict)
    result: str | None = None


class GameClock(BaseModel):
    """Zegar szachowy graczy — funkcja PROJEKTOWA, nie reguła TI4 (RULES.md 58).

    Każdy gracz ma pulę czasu (``remaining_ms``); tyka zegar tylko tego gracza, który
    TERAZ podejmuje decyzję (``holder_id`` — patrz ``core.game_clock.clock_holder``).
    Czas jest rozliczany przy każdym commicie stanu (``core.game_clock.settle``), a
    pomiędzy commitami UI dolicza go sam od ``running_since``. Zmienia go WYŁĄCZNIE
    ``core/game_clock.py``.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    # Startowa pula czasu na gracza i dodatek (Fischer) za każdą zakończoną turę.
    initial_ms: int = 0
    increment_ms: int = 0
    # Pozostały czas gracza (rozliczony do ``running_since``). Może zejść poniżej zera —
    # silnik nie karze za przekroczenie, tylko je pokazuje (⚠ ZAŁOŻENIE, RULES.md 58).
    remaining_ms: dict[str, int] = Field(default_factory=dict)
    # Gracz, którego zegar tyka, i rozliczony czas jego bieżącej „tury" (ciągu decyzji).
    holder_id: str | None = None
    holder_turn_ms: int = 0
    # Czas UNIX (s) początku nierozliczonego odcinka; None = zegar stoi (pauza/brak holdera).
    running_since: float | None = None
    paused: bool = False
    # ``active_player_id`` z ostatniego rozliczenia — jego zmiana = koniec tury (dodatek).
    turn_owner_id: str | None = None


class TurnEndWindow(BaseModel):
    """Pauza „tura właśnie się skończyła, następny gracz jeszcze nic nie zrobił” (karty reakcji).

    Ustawiana w ``turn_flow.end_turn``; zerowana przy pierwszej akcji/pasie następnego gracza,
    przy nowej turze i przy zmianie fazy. Na niej opierają się okna „at the end of a player's
    turn” i „at the start of another player's turn” (RULES.md 53.5).

    ``ended_player = None`` = pierwsza tura fazy akcji (``turn_flow.next_phase``): nikt nie
    skończył tury, jest tylko okno „początek tury” pierwszego gracza (RULES.md 54.8).
    """

    model_config = ConfigDict(extra="forbid")

    ended_player: str | None = None
    ended_passed: bool = False
    next_player: str | None = None


class ActionDiscardTrace(BaseModel):
    """Ślad ostatnio odrzuconej karty akcji (okno „after a player discards an action card”)."""

    model_config = ConfigDict(extra="forbid")

    player: str
    card: str


class TransactionTable(BaseModel):
    """Stół transakcji pary graczy (RULES.md 47.1b).

    ``sides[gracz]`` = to, co ten gracz POŁOŻYŁ na stole (pola ``TransactionSide``);
    każdy kładzie wyłącznie własne rzeczy. ``ready`` = kto potwierdził obecny stan stołu (każda
    zmiana zawartości go zeruje). Zawartość znają tylko strony; publicznie widać samą parę.
    """

    model_config = ConfigDict(extra="forbid")

    opener: str
    partner: str
    sides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    ready: list[str] = Field(default_factory=list)
    # Stół otwarty sam po uzupełnieniu commodities z umowy Trade (wash, RULES.md 47.4).
    prefilled: bool = False


class TradeDeal(BaseModel):
    """Umowa z kroku 3 Trade czekająca na uzupełnienie commodities wskazanego (RULES.md 47.4).

    ``holder_side`` / ``player_side`` = odroczone komponenty stron; ``wash`` = obietnica „wash −N”
    wskazanego (None = bez wash). Po uzupełnieniu silnik otwiera stół wstępnie wypełniony.
    """

    model_config = ConfigDict(extra="forbid")

    holder: str
    holder_side: dict[str, Any] = Field(default_factory=dict)
    player_side: dict[str, Any] = Field(default_factory=dict)
    wash: int | None = None


class HeldCounter(BaseModel):
    """Sabotage zagrane na kartę czekającą w ``HeldPlay``, które samo czeka, bo ktoś może je
    anulować bez karty (Instinct Training - F_xxcha: „may cancel a Sabotage”; RULES.md 62.9).

    ``eligible``/``passed`` okna anulowanej karty zachowane, by po anulowaniu Sabotage wróciło
    zwykłe okno tej karty (kolejna Sabotage wciąż możliwa).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    card_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    window: dict[str, Any] | None = None
    held_eligible: list[str] = Field(default_factory=list)
    held_passed: list[str] = Field(default_factory=list)


class HeldPlay(BaseModel):
    """Zagrana karta akcji CZEKAJĄCA na ewentualną reakcję Sabotage (RULES.md 53.6).

    Karta leży jawnie na stole (wyszła z ręki), a jej efekt jeszcze się NIE wykonał. Okno kończy się
    pasami wszystkich uprawnionych, upływem czasu albo anulowaniem. ``opened_at`` to czas serwera
    (s epoch) podany przez router - silnik sam zegara nie czyta (``core/card_hold.py``).
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    card_id: str
    params: dict[str, Any] = Field(default_factory=dict)
    opened_at: float
    # Inni gracze z >=1 kartą akcji w ręce w chwili zagrania (kto może zagrać Sabotage / spasować).
    eligible: list[str] = Field(default_factory=list)
    passed: list[str] = Field(default_factory=list)
    # Czy to karta okna ACTION (akcja komponentu, po efekcie odpala się "po akcji") czy reakcja.
    is_action: bool = True
    # Okno, na które reaguje karta reakcji (``OpenWindow.as_dict()``); None dla kart ACTION.
    window: dict[str, Any] | None = None
    # Stała długość okna w s (RULES.md 54.11): ustawienie hosta w chwili otwarcia + „More time”.
    seconds: float = 4.0
    # Kto poprosił o więcej czasu (prywatne - projekcja zostawia tylko patrzącego).
    extended_by: list[str] = Field(default_factory=list)
    # Sabotage na tę kartę czekające na ewentualne Instinct Training (``None`` = brak).
    counter: HeldCounter | None = None


class ReactionPause(BaseModel):
    """Pauza ochronna w kluczowym oknie reakcji (RULES.md 43.4 pkt 4, 54.10): gra czeka do 10 s.

    Otwiera ją ``core/reaction_pause.sync`` po zatwierdzonym kroku, gdy pojawi się kluczowe okno
    (ogłoszona akcja strategiczna, ujawniona agenda, wygrana walka, Sustain Damage), a z informacji
    JAWNEJ wynika, że ktoś może zareagować. Uprawnieni = gracze z >=1 kartą akcji, którzy mogą być
    właściwą stroną okna. Kończy się pasami wszystkich uprawnionych albo upływem czasu.
    """

    model_config = ConfigDict(extra="forbid")

    key: str  # klucz okna (runda + zdarzenie + kontekst) - to samo okno nie pauzuje drugi raz
    event: str
    moment: str
    label: str  # angielska etykieta okna (``timing_view.label``)
    subject: str | None = None
    opened_at: float
    eligible: list[str] = Field(default_factory=list)
    # Kto nie reaguje (pas ręczny albo auto-pas silnika, RULES.md 54.11) - PRYWATNE: projekcja
    # zostawia tylko patrzącego, bo lista zdradzałaby, kto ma kartę.
    passed: list[str] = Field(default_factory=list)
    # Stała długość okna w s (RULES.md 54.11): ustawienie hosta w chwili otwarcia + „More time”.
    seconds: float = 4.0
    extended_by: list[str] = Field(default_factory=list)


class BonusTurn(BaseModel):
    """Dodatkowa akcja gracza, który już spasował (Puppets on a String), poza kolejką tur.

    Po jej zakończeniu ``end_turn`` przywraca spasowanie i oddaje turę ``resume_player``
    (ten, który miał zacząć turę), z oknem pauzy sprzed bonusu (``resume_window``).
    """

    model_config = ConfigDict(extra="forbid")

    player: str
    resume_player: str | None = None
    resume_window: TurnEndWindow | None = None
    # Czy po bonusowej akcji gracz wraca do stanu „spasował" (Puppets on a String) - dla gracza,
    # który NIE spasował (Jupiter Brain), flaga ``passed`` zostaje fałszywa.
    restore_passed: bool = True


class EliminatedPlayer(BaseModel):
    """Gracz wyeliminowany (R_elimination): nie jest już częścią gry, zostaje tylko ślad.

    Jego system domowy nadal jest systemem domowym (R_elimination, Notes) - ``home_position``.
    """

    model_config = ConfigDict(extra="forbid")

    player_id: str
    faction: str | None = None
    color: str | None = None
    display_name: str = ""
    home_position: str | None = None
    round_number: int = 0


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
    # Gracze wyeliminowani (R_elimination, ``core/elimination.py``): usunięci z ``players``
    # i ``seating_order``; liczba graczy na start gry = ``players`` + ta lista (RULES.md 13).
    eliminated_players: list[EliminatedPlayer] = Field(default_factory=list)

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
    # Czy w tej akcji taktycznej zużyto już „+1 do ruchu dla jednego statku" (Gravity Drive,
    # RULES.md 55.6). Zerowane przy aktywacji i zakończeniu akcji.
    gravity_drive_used: bool = False
    # Czy w tej akcji taktycznej zużyto już „+1 do ruchu dla jednego statku" z Ionian Fuel
    # Refinery (Tempesta, RULES.md 60). Osobne od Gravity Drive; zerowane jak ono.
    tempesta_used: bool = False
    # Czy zużyto „+1 do ruchu jednego statku” z przełomu Imperator (Winnu, RULES.md 62.7).
    # Osobne od Gravity Drive (decyzja użytkownika: premie mogą trafić na różne statki).
    imperator_used: bool = False
    # Czy w tej akcji taktycznej poruszono już jakiś statek (okno „po aktywacji systemu” kart
    # reakcji zamyka się z pierwszym ruchem). Zerowane przy aktywacji i zakończeniu akcji.
    tactical_moved: bool = False

    # Systemy z Ion Storm, przez których wormhole przeszły statki w tej akcji (flip na końcu
    # kroku ruchu / odwrotu, R: C_exploration_cards). Zerowane przy aktywacji i końcu akcji.
    ion_storm_used: list[str] = Field(default_factory=list)

    # Przejściowy znacznik „kto niszczy jednostki": ustawiany tylko na czas efektu, który niszczy
    # WŁASNE jednostki (Crown of Thalnos), żeby cele typu Destroy Their Greatest Ship nie
    # przypisały zasługi przeciwnikowi. Poza takim efektem ``None``.
    destroyed_by: str | None = None

    # Właściciele notek, które aktywny gracz miał w strefie gry na starcie akcji taktycznej
    # (tajny cel Betray a Friend, ``core/objective_events.py``). Zerowane z akcją taktyczną.
    tactical_pn_owners: list[str] = Field(default_factory=list)

    # Tajne cele zdobyte AUTOMATYCZNIE zdarzeniem (faza Action/Agenda): gracz, cel, runda.
    auto_scored: list[dict[str, Any]] = Field(default_factory=list)
    # Trwałe ślady dla okien kart reakcji (RULES.md 53.5.e): pauza po końcu tury, strony ostatniej
    # transakcji, ostatnio odrzucona karta akcji i dodatkowa tura spasowanego gracza. Zerowane
    # przy kolejnej akcji dowolnego gracza (``action_budget.register_action``) i nowej turze.
    turn_end_window: TurnEndWindow | None = None
    last_transaction: list[str] = Field(default_factory=list)
    # Stoły transakcji (RULES.md 47.1b) — najwyżej jeden na parę graczy.
    transaction_tables: list[TransactionTable] = Field(default_factory=list)
    # Umowy Trade czekające na uzupełnienie commodities wskazanego: {gracz: umowa} (RULES.md 47.4).
    trade_deals: dict[str, TradeDeal] = Field(default_factory=dict)
    last_action_discard: ActionDiscardTrace | None = None
    # Kto uzupełnił commodities od ostatniej akcji (okno Trade Agreement, RULES.md 61.2).
    last_replenished: list[str] = Field(default_factory=list)
    # Badania od ostatniej akcji: ``{player, technology}`` (okno Research Agreement, RULES.md 62.3).
    last_research: list[dict[str, str]] = Field(default_factory=list)
    # Ostatnia zapłata zasobami za badanie (``technology.pay_research``): gracz, koszt, planety, TG,
    # ``reduced`` - okno Doctor Sucaban / commandera Deepwrought po zapłacie (RULES.md 62.3).
    last_research_payment: dict[str, Any] | None = None
    # Notatki o zdolnościach stosowanych automatycznie (feed + powiadomienia, ``ability_notes``).
    ability_notes: list[dict[str, str]] = Field(default_factory=list)
    ability_note_seq: int = 0
    bonus_turn: BonusTurn | None = None
    # Ślad zmian kontroli planet w TEJ akcji taktycznej (karty reakcji Infiltrate / Reparations):
    # wpisy ``{"planet", "position", "player" (nowy kontroler), "previous" (poprzedni | None)}``.
    # Dopisuje ``control.set_planet_control``; zerowane przy aktywacji i zakończeniu akcji.
    control_changes: list[dict[str, str | None]] = Field(default_factory=list)
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
    # Okno przerwane przez okno limitu (FLEET_POOL / CAPACITY): limity sprawdzamy NATYCHMIAST,
    # także w trakcie innego okna (RULES.md 42.1). ``timing.close_window`` przywraca je po
    # usunięciu nadwyżki.
    suspended_window: TimingWindow | None = None
    # Efekty trwałe z czasem trwania i opcjonalne reakcje czekające na decyzję (RULES.md 54).
    active_effects: list[ActiveEffect] = Field(default_factory=list)
    pending_offers: list[PendingOffer] = Field(default_factory=list)
    effect_seq: int = 0
    # Trwające wieloetapowe PRIMARY karty strategii (wybory aktywnego gracza) — None, gdy
    # brak. Blokuje End turn i inne akcje do czasu rozstrzygnięcia (RULES.md 30.5).
    pending_strategy: StrategyResolution | None = None
    # Zagrana karta akcji czekająca na ewentualne Sabotage (``core/card_hold.py``, RULES.md 53.6).
    held_play: HeldPlay | None = None
    # Pauza ochronna w kluczowym oknie reakcji (``core/reaction_pause.py``, RULES.md 54.10) i klucze
    # okien, które już miały pauzę (ostatnie kilkanaście; to samo okno nie pauzuje ponownie).
    reaction_pause: ReactionPause | None = None
    reaction_pause_seen: list[str] = Field(default_factory=list)
    # Stała długość okien reakcji w s (pauza ochronna, okno Sabotage); ustawia host (RULES 54.11).
    reaction_window_seconds: int = 4
    # Ślad Sustain Damage poza walką (Space Cannon Offense): ``{player, base_type, count, by,
    # position}`` - okno Direct Hit trwa do następnego kroku Space Cannon (RULES.md 53.5.c).
    sustain_trace: list[dict[str, Any]] = Field(default_factory=list)
    # Generator losowy silnika (rzuty kośćmi — ``core/dice.py``). ``rng_seed`` = 0 oznacza
    # „jeszcze nie zasiane": pierwszy rzut losuje ziarno i zapisuje je w stanie. Ziarno +
    # licznik są częścią stanu, więc Undo/Redo i powtórka migawki dają TE SAME wyniki.
    rng_seed: int = 0
    rng_counter: int = 0
    # Ostatni rzut „na stół" poza walką (The Fracture, karty akcji…) — dla animacji kości w UI
    # (``dice.record_table_roll``). ``table_roll_seq`` rośnie z każdym rzutem, więc UI odróżnia
    # NOWY rzut od starego; sam wynik jest już rozstrzygnięty przez silnik.
    table_roll_seq: int = 0
    table_roll: dict[str, Any] | None = None
    # Ostatnie odsłonięcie reliktu z talii (fragmenty, The Fracture, eksploracja) — widowisko
    # dla WSZYSTKICH graczy (``relics.record_reveal``, RULES.md 59.8). ``relic_reveal_seq``
    # rośnie z każdym dobraniem, więc UI odróżnia nowe odsłonięcie od starego.
    relic_reveal_seq: int = 0
    relic_reveal: dict[str, Any] | None = None
    # Dziennik ostatniego rozstrzygnięcia Space Cannon Offense (JSON listy wpisów). Okno
    # czasowe znika po ostatnim graczu, a panel musi nadal pokazać, co się stało (rzuty,
    # trafienia, straty) — do końca akcji taktycznej (RULES.md 38.3).
    space_cannon_log: str = "[]"
    # Trwająca walka (kosmiczna/naziemna) — None, gdy żadna nie trwa (RULES.md 39).
    active_combat: ActiveCombat | None = None
    # Trwająca inwazja (krok INVASION akcji taktycznej) — None, gdy żadna (RULES.md 40).
    invasion: InvasionState | None = None
    # Trwająca eksploracja planet (po Establish Control) — None, gdy żadna (RULES.md 46).
    exploration: ExplorationState | None = None
    # The Fracture i ekspedycje Thunder's Edge (RULES.md 50).
    fracture: FractureState = Field(default_factory=FractureState)
    expeditions: ExpeditionState = Field(default_factory=ExpeditionState)
    # Jednorazowa produkcja z efektu karty (Freelancers) — None, gdy brak (RULES.md 46).
    production_grant: ProductionGrant | None = None
    # Karty eksploracji PRZYCZEPIONE do planet (attach): {planet_id: [card_id, ...]}. Zostają
    # przy planecie niezależnie od zmiany kontroli (R_attach).
    planet_attachments: dict[str, list[str]] = Field(default_factory=dict)

    # Karty akcji leżące jawnie NA karcie zdolności legendarnej planety: {planet_id: [card_id]}
    # (Dok 'N Pic's Salvage Yard na Garbozii). Zostają przy karcie, gdy zmienia ona kontrolera.
    legendary_cards: dict[str, list[str]] = Field(default_factory=dict)
    # Trade goods leżące na kartach strategii: {numer_inicjatywy: liczba_TG}.
    # Niewybrane karty akumulują +1 TG na koniec fazy strategii; wybór przekazuje
    # TG graczowi i zeruje licznik (RULES.md 13).
    strategy_card_tg: dict[int, int] = Field(default_factory=dict)
    # Ile kart strategii WYBRAŁ każdy gracz w tej fazie strategii (Checks and Balances: wybrana
    # karta trafia do innego gracza, więc wybory ≠ posiadane karty - RULES.md 51.6).
    strategy_choices: dict[str, int] = Field(default_factory=dict)
    # Żetony długu (debt) (nieformalna zasada stołu, NIE reguła TI4 — RULES.md 47.3): małe żetony
    # kontroli gracza-wystawcy oddane innemu graczowi jako „dług"/obietnica (np. 3 TG do
    # zapłaty = 3 żetony). Niewiążące dla silnika, tylko pamięć stołu. Format:
    # ``{holder_id: {issuer_id: liczba}}`` — kto trzyma czyje żetony. Wpisy z zerem znikają.
    debt_tokens: dict[str, dict[str, int]] = Field(default_factory=dict)

    # Cele publiczne, talie wspólne i stan fazy statusu (RULES.md 41). ``status`` = None
    # poza fazą statusu (i dla stanów wprowadzonych God-Mode bez inicjalizacji kroków).
    objectives: ObjectivesState = Field(default_factory=ObjectivesState)
    decks: DecksState = Field(default_factory=DecksState)
    status: StatusPhaseState | None = None
    # Stan fazy agendy (RULES.md 51) - None poza nią i dla stanów wprowadzonych God-Mode
    # bez inicjalizacji (wtedy faza zachowuje się starą ścieżką ``turn_flow``).
    agenda: AgendaPhaseState | None = None
    # Setup startowy (tajne cele, żeton Custodians, odkrycie celów) — None, gdy zakończony
    # albo gdy stan nie przechodził przez ``/game/new`` (testy, God-Mode). RULES.md 43.
    setup: SetupState | None = None
    # Żeton Custodians zdjęty z Mecatol Rex => faza agendy dodana do KAŻDEJ rundy
    # (R_custodians_token). Do czasu zdjęcia status kończy rundę bez fazy agendy.
    custodians_removed: bool = False
    # God-Mode (testy): wyłączony limit ręki kart akcji (RULES.md 53.8) - ``hand_limit``
    # zwraca wtedy „bez limitu”. Domyślnie limit obowiązuje.
    action_card_limit_disabled: bool = False
    # Próg punktów zwycięstwa (R_victory_points: 10, albo 14 na drugiej stronie toru).
    vps_to_win: int = 10
    # Zwycięzca (koniec gry) — None, dopóki gra trwa.
    winner_id: str | None = None
    # Limit rund (projektowy, NIE reguła TI4): po zakończeniu tylu rund gra się kończy,
    # wygrywa lider VP. 0 = bez limitu. Patrz RULES.md (koniec gry).
    max_rounds: int = 10
    # Dlaczego gra się skończyła: "victory_points" | "round_limit" | "no_objectives".
    end_reason: str | None = None
    # Głosowanie nad zwycięstwem honorowym/niehonorowym — None, dopóki nie otwarte.
    epilogue: EpilogueState | None = None
    # Dziennik bitew/podbojów/transakcji dla podsumowania końcowego.
    chronicle: GameChronicle = Field(default_factory=GameChronicle)
    # Zegar szachowy graczy (opcja nowej gry, RULES.md 58) — wyłączony domyślnie.
    clock: GameClock = Field(default_factory=GameClock)

    players: dict[str, PlayerState] = Field(default_factory=dict)
    systems: dict[str, SystemState] = Field(default_factory=dict)

    def clone(self) -> GameState:
        """Zwraca głęboką kopię stanu (przez walidowaną serializację)."""
        return GameState.model_validate(self.model_dump())
