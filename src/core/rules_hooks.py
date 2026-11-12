"""Rejestr hooków reguł: wyjątki frakcji, technologii i kart BEZ edycji reguły bazowej.

RULES.md 43.1: reguła bazowa nie zna wyjątków. W miejscu, na które coś może wpływać, wywołuje
PUNKT ZACZEPIENIA (``point``, napis), a wyjątek rejestruje się osobno (pakiet ``core/hooks/``)
jako ``(źródło, punkt, rodzaj, funkcja)``. Hook jest CZYSTĄ funkcją ``(state, player_id, ctx)``.

Hook obowiązuje gracza tylko wtedy, gdy ten POSIADA jego źródło (frakcja, technologia, ...) —
patrz ``owned_sources``. Kolejność wielu hooków na jednym punkcie jest deterministyczna
(RULES.md 43.1 pkt 5): REPLACE, FORBID, PERMIT, MODIFY, TRIGGER, PERSISTENT, a w obrębie rodzaju
kolejność rejestracji.

API: ``forbidden`` (FORBID), ``permits`` (PERMIT), ``modify`` (MODIFY) — pytania „w miejscu”;
``on_event`` rejestruje hooki zdarzeń (TRIGGER/REPLACE), które uruchamia ``core/triggers.fire``
(RULES.md 54). PERSISTENT = efekt trwały w ``GameState.active_effects`` (``core/active_effects``),
będący źródłem hooków (``SOURCE_EFFECT``) do czasu wygaśnięcia.

God-Mode omija hooki tak jak resztę reguł (RULES.md 43.1 pkt 11).
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from src.core.game_events import GameEvent, Moment, event_point
from src.core.game_state import GameState

# Punkty zaczepienia (nazwy). Dopisuj tu, gdy reguła bazowa dostaje nowy punkt.
POINT_PRODUCTION_FORBIDS = "production.forbids"  # FORBID -> typy jednostek (ctx: producer_type)
POINT_MOVEMENT_ENTER_ASTEROIDS = "movement.enter_asteroids"  # PERMIT -> bool
POINT_MOVEMENT_MOVE_VALUE = "movement.move_value"  # MODIFY -> delta (ctx: base_type)
POINT_MOVEMENT_PASS_FOREIGN_SHIPS = "movement.pass_foreign_ships"  # PERMIT (ctx: position)
POINT_COMBAT_ROLL_MODIFIER = "combat.roll_modifier"  # MODIFY -> +N do wyniku rzutu
# ctx: kind, position, planet, defender, base_type
POINT_COMBAT_EXTRA_DICE = "combat.extra_dice"  # MODIFY -> delta kości na jednostkę (ctx jak wyżej)
# MODIFY -> dodatkowe trafienia strony po rzutach obu stron (ctx: kind, opponent_hits, own_hits);
# Valkyrie Particle Weave (RULES.md 62.1).
POINT_COMBAT_EXTRA_HITS = "combat.extra_hits"
# MODIFY -> dodatkowe kości dla GRUPY jednostek łącznie (nie na egzemplarz), ctx: kind, base_type;
# agent Letnev „that ship rolls 1 additional die" (RULES.md 62.2).
POINT_COMBAT_BONUS_DICE = "combat.bonus_dice"
# MODIFY -> +X do wyników kości JEDNEJ jednostki danego typu (ctx: kind, base_type); Gravleash.
POINT_COMBAT_SINGLE_UNIT_BONUS = "combat.single_unit_bonus"
# MODIFY -> o ile więcej trafień anuluje jedno użycie Sustain Damage (Non-Euclidean Shielding).
POINT_COMBAT_SUSTAIN_CANCELS = "combat.sustain_cancels"
# MODIFY -> +N do pojemności puli floty w każdym systemie (Armada).
POINT_FLEET_POOL_CAPACITY = "fleet_pool.capacity"
# PERMIT -> statki niemyśliwskie gracza nie są ograniczone pulą floty (Darktalon Treilla).
POINT_FLEET_POOL_UNLIMITED = "fleet_pool.unlimited"
# PERMIT -> jednostki INNYCH graczy w systemie (ctx: position) tracą PLANETARY SHIELD (Arc
# Secundus).
POINT_STRIPS_PLANETARY_SHIELD = "invasion.strips_planetary_shield"
# PERMIT -> w inwazji Space Cannon nie strzela w jednostki gracza (L4 Disruptors).
POINT_SPACE_CANNON_DEFENSE_IMMUNE = "space_cannon.defense_immune"
POINT_COMBAT_REROLL_MISSES = "combat.reroll_misses"  # PERMIT -> przerzut chybień (ctx: base_type)
# PERMIT -> trafienia z rzutu AFB właściciela hooka są wyprodukowane przeciw WSZYSTKIM statkom
# przeciwnika, nie tylko myśliwcom (Waylay; przypisuje je przeciwnik w kroku ASSIGN).
POINT_COMBAT_AFB_ALL_SHIPS = "combat.afb_all_ships"
POINT_AGENDA_VOTE_MODIFIER = "agenda.vote_modifier"  # MODIFY -> delta głosów (ctx: agenda_id)
POINT_PRODUCTION_VALUE = "production.value"  # MODIFY -> delta PRODUCTION jednostki
# ctx: base_type, zone
POINT_PRODUCTION_TOTAL_VALUE = "production.total_value"  # MODIFY -> delta SUMY PRODUCTION gracza
POINT_MOVEMENT_ALPHA_BETA_ADJACENT = "movement.alpha_beta_adjacent"  # PERMIT (Lost Star Chart)
POINT_MOVEMENT_IGNORE_ANOMALIES = "movement.ignore_anomalies"  # PERMIT (Nav Suite)
POINT_SPACE_CANNON_OFFENSE_IMMUNE = "space_cannon.offense_immune"  # PERMIT (Solar Flare)
POINT_PRODUCTION_COST = "production.cost"  # MODIFY -> delta łącznego kosztu zamówienia
POINT_PAYMENT_COMMODITIES_AS_TG = "payment.commodities_as_trade_goods"  # PERMIT -> bool
# Space Cannon: modyfikator wyniku rzutów PRZECIWKO właścicielowi hooka (pytamy właściciela CELU;
# ctx: shooter) - np. Antimass Deflectors: -1 do wyniku każdej kości.
POINT_SPACE_CANNON_ROLL_MODIFIER = "space_cannon.roll_modifier"
# Space Cannon: dodatkowe kości dla JEDNEJ jednostki strzelca przy jednym użyciu (Plasma Scoring).
POINT_SPACE_CANNON_EXTRA_DICE = "space_cannon.extra_dice"
# Bombardment: dodatkowe kości dla JEDNEJ jednostki przy jednym użyciu (Plasma Scoring).
POINT_BOMBARDMENT_EXTRA_DICE = "bombardment.extra_dice"

# Bombardment: statki niefighterowe BEZ własnego Bombardment zyskują go (Blitz: BOMBARDMENT 6).
# Hook FORBID użyty jako „zbiór wartości": zwraca napisy z progiem trafienia (np. {"6"}); silnik
# bierze najniższy próg (pytamy atakującego).
POINT_BOMBARDMENT_GRANTED = "bombardment.granted_hits_on"

# Bombardment: modyfikator wyniku każdej kości rzutu PRZECIW planecie właściciela hooka
# (pytamy kontrolującego planetę; Bunker: -4). ctx: planet, attacker.
POINT_BOMBARDMENT_ROLL_MODIFIER = "bombardment.roll_modifier"

# PDS gracza ``ctx["victim"]`` traci PLANETARY SHIELD i SPACE CANNON (Disable). PERMIT pytany
# o KAŻDEGO gracza przy stole (właściciel efektu odpowiada, czyje PDS wyłącza).
POINT_PDS_DISABLED = "space_cannon.pds_disabled"
# Mnożnik trafień z rzutów (bazowo 1; X-89 ΩΩ: ×2). ctx: kind = ground | space | bombardment.
POINT_COMBAT_HIT_MULTIPLIER = "combat.hit_multiplier"
# PERMIT -> inwazja zaczyna się od Commit Ground Forces (bez Bombardment): Tekklar Conditioning.
POINT_INVASION_SKIP_BOMBARDMENT = "invasion.skip_bombardment"
# Bombardment wolno rzucać także przeciw planecie cudzej BEZ sił naziemnych (X-89 ΩΩ).
POINT_BOMBARD_EMPTY_PLANETS = "bombardment.empty_planets"  # PERMIT -> bool
# Odwrót do sąsiedniego systemu bez cudzych jednostek, także bez własnej obecności
# (Dark Energy Tap).
POINT_RETREAT_ANYWHERE = "retreat.anywhere"  # PERMIT -> bool
# Specjalności technologii planet działają bez wyczerpywania, także na wyczerpanych planetach
# (Psychoarchaeology).
POINT_TECHNOLOGY_SPECIALTY_FREE = "technology.specialty_without_exhaust"  # PERMIT -> bool
# Liczba akcji gracza w jego turze fazy akcji (bazowo 1; Fleet Logistics: +1).
POINT_TURN_ACTIONS = "turn.actions"
# Gracz właśnie rozpoczął akcję (``action_budget.register_action``); hooki PERSISTENT uruchamiane
# przez ``run_persistent`` (ctx: strategic = czy to akcja strategiczna). Np. Extreme Duress.
POINT_ACTION_STARTED = "turn.action_started"
# Transakcja może obejmować relikty, karty akcji i nieodsłonięte tajne cele (Black Market Dealings);
# PERMIT -> bool (pytamy obu uczestników transakcji; ctx: partner).
POINT_TRANSACTION_EXTRA_ITEMS = "transaction.extra_items"
# Faza statusu: liczba kart akcji dobieranych przez gracza (bazowo 1; Neural Motivator: +1).
POINT_STATUS_ACTION_CARDS = "status.action_cards"
# Faza statusu: liczba żetonów dowodzenia zdobywanych przez gracza (bazowo 2; Hyper Metabolism: +1).
POINT_STATUS_COMMAND_TOKENS = "status.command_tokens"

# Commodity value gracza (bazowo z arkusza frakcji; Dynamis Core: +2). MODIFY -> delta.
POINT_COMMODITY_VALUE = "economy.commodity_value"

# Space Cannon nadany jednostce BEZ własnego (Lightrail Ordnance: stocznia). Hook FORBID jako zbiór
# napisów "<base_type>:<próg trafienia>:<kości na jednostkę>"; strzela też na sąsiednie systemy.
POINT_SPACE_CANNON_GRANTED = "space_cannon.granted"

# Sustain Damage nadany statkom niemyśliwskim bez własnego (Metali Void Shielding). PERMIT -> bool.
POINT_COMBAT_GRANTED_SUSTAIN = "combat.granted_sustain"
# AFB nadany właścicielowi hooka (Metali Void Armaments): FORBID jako zbiór "<próg>:<kości>".
POINT_COMBAT_AFB_GRANTED = "combat.afb_granted"
# Właściciel może w KAŻDEJ rundzie walki przerzucić kości z +1 do wyniku (Thalnos). PERMIT.
POINT_COMBAT_REROLL_PLUS_ONE = "combat.reroll_plus_one"
# Zmiana wyniku DOWOLNEJ kości o ±1 po rzucie (Heart of Ixth). Hook FORBID jako zbiór id GOTOWYCH
# reliktów, którymi wolno to zrobić (silnik wyczerpuje wskazany relikt).
POINT_DIE_ADJUST = "dice.adjust_result"

# Zamiast wydać żeton z puli strategicznej gracz może wydać żeton z rezerwy (Scepter of Emelpar).
# Hook FORBID jako zbiór id GOTOWYCH reliktów, którymi wolno (silnik wyczerpuje wskazany).
POINT_STRATEGY_TOKEN_FROM_REINFORCEMENTS = "command_tokens.strategy_from_reinforcements"

# Ruch i transport z systemów zawierających WŁASNY żeton dowodzenia (Dominus Orb). PERMIT -> bool.
POINT_MOVEMENT_IGNORE_OWN_CC = "movement.ignore_own_command_token"

# Ignorowanie 1 prerekwizytu przy badaniu przez wyczerpanie reliktu (Prophet's Tears).
# Hook FORBID jako zbiór id GOTOWYCH reliktów; skip w planie badania: ``relic:<id>``.
POINT_TECHNOLOGY_IGNORE_PREREQUISITE = "technology.ignore_prerequisite"

# Synergia dla WSZYSTKICH czterech typów technologii (The Quantumcore). PERMIT -> bool.
POINT_TECHNOLOGY_SYNERGY_ALL = "technology.synergy_all"

# Limit tajnych celów gracza (bazowo 3; The Obsidian: +1). MODIFY -> delta.
POINT_SECRET_OBJECTIVE_LIMIT = "objectives.secret_limit"

# Rodzaje źródeł hooka (kto "posiada" wyjątek).
SOURCE_FACTION = "faction"
SOURCE_TECHNOLOGY = "technology"
SOURCE_AGENDA = "agenda"  # prawo w grze (decks.agenda_laws) - obowiązuje KAŻDEGO gracza
SOURCE_PROMISSORY = "promissory"  # notka leżąca w strefie gracza (promissory_notes_in_play)
SOURCE_RELIC = "relic"  # relikt przed graczem (PlayerState.relics)
SOURCE_LEADER = "leader"  # lider odblokowany lub gotowy (stan domyślny z danych frakcji)
SOURCE_BREAKTHROUGH = "breakthrough"  # odblokowany przełom frakcji
SOURCE_EFFECT = "effect"  # efekt trwały z magazynu (GameState.active_effects)
# Legendarna planeta kontrolowana przez gracza (karta zdolności legendarnej, RULES.md 60).
SOURCE_PLANET = "planet"
# Jednostka frakcyjna z polem ``ability`` (flagowiec, mech, ulepszenie frakcyjne) — id WARIANTU,
# którego gracz używa (RULES.md 61.3). Hook sam sprawdza, czy jednostka jest w danym systemie.
SOURCE_UNIT = "unit"


class HookKind(Enum):
    """Rodzaj hooka; kolejność wartości = kolejność rozstrzygania (RULES.md 43.1 pkt 5)."""

    REPLACE = 0
    FORBID = 1
    PERMIT = 2
    MODIFY = 3
    TRIGGER = 4
    PERSISTENT = 5


@dataclass(frozen=True)
class HookSource:
    """Komponent, który wnosi wyjątek (np. frakcja ``arborec``, technologia ``amd``)."""

    kind: str
    component_id: str


HookFn = Callable[[GameState, str, Mapping[str, Any]], Any]
# Warunek hooka zdarzenia sprawdzany w chwili wyzwolenia: (stan, gracz, kontekst) -> bool.
ConditionFn = Callable[[GameState, str, Mapping[str, Any]], bool]
# Efekt jednorazowy komponentu (np. karty akcji): (stan-klon, rejestr, gracz, parametry) -> None.
# Mutuje przekazany klon; błąd walidacji = ValueError (wołający pracuje na klonie).
# ``registry`` typowany jako Any, by uniknąć cyklu importów (registry importuje ten moduł).
EffectFn = Callable[[GameState, Any, str, Mapping[str, Any]], None]


@dataclass(frozen=True)
class Hook:
    """Jeden zarejestrowany wyjątek."""

    point: str
    source: HookSource
    kind: HookKind
    fn: HookFn
    seq: int  # kolejność rejestracji (rozstrzyga remis w obrębie rodzaju)
    covers: str | None = None  # "<kategoria>:<id>" komponentu, który hook implementuje
    # --- tylko hooki zdarzeń (``on_event``) ---
    optional: bool = False  # „you may ...” -> oferta zamiast automatycznego uruchomienia
    where: tuple[tuple[str, str], ...] = ()  # filtr kontekstu zdarzenia (np. phase=strategy)
    condition: ConditionFn | None = None  # warunek sprawdzany przy wyzwoleniu
    label: str = ""  # opis dla UI/oferty
    # Wybór gracza (RULES.md 56): opis wejść formularza (liczy legalne opcje silnik). Z ``optional``
    # = oferta „may" (można odmówić); z ``decide`` = decyzja OBOWIĄZKOWA: gdy wybór jest realny,
    # silnik pyta gracza (nigdy nie wybiera za niego), a gdy opcja jest jedna - stosuje ją od razu.
    inputs: OfferInputsFn | None = None
    decide: bool = False
    # Kto podejmuje decyzję, jeśli to NIE właściciel źródła (np. ofiara Assault Cannon).
    decider: DeciderFn | None = None


# Opis wyborów gracza dla efektu (formularz UI): (stan, rejestr, gracz) -> lista wejść.
InputsFn = Callable[[GameState, Any, str], list[dict[str, Any]]]
# Opis wyborów dla oferty/decyzji hooka zdarzenia: (stan, rejestr, decydent, kontekst) -> wejścia.
OfferInputsFn = Callable[[GameState, Any, str, Mapping[str, Any]], list[dict[str, Any]]]
# Wskazanie decydenta: (stan, właściciel źródła, kontekst) -> id gracza.
DeciderFn = Callable[[GameState, str, Mapping[str, Any]], str]

_REGISTRY: list[Hook] = []
_EFFECTS: dict[str, EffectFn] = {}
_INPUTS: dict[str, InputsFn] = {}
_DATA_DRIVEN: set[str] = set()
# Zdolności technologii używane NIE jako akcja (np. Psychoarchaeology) - RULES.md 57.
_ABILITIES: dict[str, EffectFn] = {}
_ABILITY_INPUTS: dict[str, InputsFn] = {}
_loaded = False


def register(
    point: str, source: HookSource, kind: HookKind, covers: str | None = None
) -> Callable[[HookFn], HookFn]:
    """Dekorator rejestrujący funkcję jako hook na ``point`` dla ``source``.

    ``covers`` (``"<kategoria>:<id>"``, np. ``"technologies:amd"``) wskazuje komponent,
    którego efekt hook realizuje; na tej podstawie rejestr efektów oznacza go jako
    IMPLEMENTED i powstaje raport pokrycia (H3). Brak = hook bez przypisanego komponentu.
    """

    def decorate(fn: HookFn) -> HookFn:
        _REGISTRY.append(Hook(point, source, kind, fn, len(_REGISTRY), covers))
        return fn

    return decorate


def on_event(
    event: GameEvent,
    moment: Moment,
    source: HookSource,
    *,
    kind: HookKind = HookKind.TRIGGER,
    optional: bool = False,
    where: Mapping[str, str] | None = None,
    condition: ConditionFn | None = None,
    covers: str | None = None,
    label: str = "",
    inputs: OfferInputsFn | None = None,
    decide: bool = False,
    decider: DeciderFn | None = None,
) -> Callable[[HookFn], HookFn]:
    """Rejestruje hook ZDARZENIA: ``fn(state, player_id, ctx)`` odpalane przez ``triggers.fire``.

    * ``kind=TRIGGER`` (domyślnie): reakcja. ``optional=False`` = obowiązkowa (komponent w grze),
      ``optional=True`` = „you may” -> oferta w oknie REACTION dla posiadacza publicznego źródła.
    * ``kind=REPLACE``: „instead of” — ``fn`` zwraca prawdę, gdy zastąpiła zdarzenie (wołający
      pomija wtedy swój krok); opcjonalny REPLACE też staje się ofertą.
    * ``where``: filtr kontekstu (np. ``{"phase": "strategy"}``); ``condition``: warunek
      sprawdzany przy wyzwoleniu.
    * ``covers``: komponent, który hook realizuje (status IMPLEMENTED w rejestrze efektów).
    * ``inputs`` / ``decide`` / ``decider``: decyzje gracza (RULES.md 56) - patrz ``Hook``. Hook z
      ``decide`` czyta wybór z ``ctx["params"]`` (gdy wyboru nie ma, ``params`` zawiera jedyną
      legalną odpowiedź), a ``ctx["decider"]`` to gracz podejmujący decyzję.
    """
    if kind not in (HookKind.TRIGGER, HookKind.REPLACE):
        raise ValueError("Event hooks must be TRIGGER or REPLACE.")
    where_items = tuple(sorted((k, str(v)) for k, v in (where or {}).items()))

    def decorate(fn: HookFn) -> HookFn:
        _REGISTRY.append(
            Hook(
                event_point(event, moment), source, kind, fn, len(_REGISTRY), covers,
                optional, where_items, condition, label, inputs, decide, decider,
            )
        )
        return fn

    return decorate


def register_effect(component_key: str) -> Callable[[EffectFn], EffectFn]:
    """Rejestruje efekt jednorazowy komponentu (``\"<kategoria>:<id>\"``), np. karty akcji.

    Komponent z efektem jest IMPLEMENTED (``covered_components``). Jeden efekt na komponent.
    """

    def decorate(fn: EffectFn) -> EffectFn:
        if component_key in _EFFECTS:
            raise ValueError(f"Effect already registered for {component_key}.")
        _EFFECTS[component_key] = fn
        return fn

    return decorate


def register_effect_inputs(component_key: str) -> Callable[[InputsFn], InputsFn]:
    """Rejestruje opis wyborów gracza dla efektu komponentu (patrz ``hooks/action_card_inputs``)."""

    def decorate(fn: InputsFn) -> InputsFn:
        if component_key in _INPUTS:
            raise ValueError(f"Inputs already registered for {component_key}.")
        _INPUTS[component_key] = fn
        return fn

    return decorate


def register_ability(tech_id: str) -> Callable[[EffectFn], EffectFn]:
    """Rejestruje zdolność technologii używaną poza akcją (``technologies:<id>`` = pokryta)."""

    def decorate(fn: EffectFn) -> EffectFn:
        if tech_id in _ABILITIES:
            raise ValueError(f"Ability already registered for {tech_id}.")
        _ABILITIES[tech_id] = fn
        _DATA_DRIVEN.add(f"technologies:{tech_id}")
        return fn

    return decorate


def register_ability_inputs(tech_id: str) -> Callable[[InputsFn], InputsFn]:
    """Rejestruje opis wyborów zdolności technologii (formularz w UI)."""

    def decorate(fn: InputsFn) -> InputsFn:
        _ABILITY_INPUTS[tech_id] = fn
        return fn

    return decorate


def ability_for(tech_id: str) -> tuple[EffectFn, InputsFn | None] | None:
    """Zdolność technologii używana poza akcją albo ``None``."""
    _ensure_loaded()
    fn = _ABILITIES.get(tech_id)
    return None if fn is None else (fn, _ABILITY_INPUTS.get(tech_id))


def all_abilities() -> list[str]:
    """Id technologii z zarejestrowaną zdolnością poza akcją."""
    _ensure_loaded()
    return sorted(_ABILITIES)


def inputs_for(component_key: str) -> InputsFn | None:
    """Opis wyborów efektu albo ``None`` (efekt bez parametrów lub brak efektu)."""
    _ensure_loaded()
    return _INPUTS.get(component_key)


def effect_for(component_key: str) -> EffectFn | None:
    """Efekt jednorazowy komponentu albo ``None`` (brak = MANUAL, rozstrzyga operator)."""
    _ensure_loaded()
    return _EFFECTS.get(component_key)


def _ensure_loaded() -> None:
    """Leniwie importuje pakiet ``core.hooks`` (jego moduły rejestrują się przy imporcie)."""
    global _loaded
    if not _loaded:
        _loaded = True
        import src.core.hooks  # noqa: F401  (import dla efektu ubocznego: rejestracja)


def all_hooks() -> list[Hook]:
    """Wszystkie zarejestrowane hooki (po załadowaniu pakietu ``core.hooks``)."""
    _ensure_loaded()
    return list(_REGISTRY)


def hook_by_seq(seq: int) -> Hook | None:
    """Hook o danym numerze rejestracji (do rozstrzygania ofert) albo ``None``."""
    _ensure_loaded()
    return next((h for h in _REGISTRY if h.seq == seq), None)


def declare_superseded(*component_keys: str) -> None:
    """Oznacza wersje kart zastąpione errata (np. Magen Defense Grid bez Ω).

    Talia gry zawiera tylko najnowszą wersję (``technology.generic_pool``), więc starsze nie
    wchodzą do rozgrywki i nie potrzebują hooka; liczą się jako pokryte w raporcie.
    """
    _DATA_DRIVEN.update(component_keys)


def declare_player_option(*component_keys: str) -> None:
    """Oznacza komponenty zrealizowane jako JAWNY wybór gracza w regule bazowej (parametr akcji).

    Np. Graviton Laser System (``exhaust_gls`` przy strzale Space Cannon) i AI Development
    Algorithm (``exhaust_aida`` przy produkcji): gracz świadomie włącza efekt, więc nie ma
    hooka, a komponent liczy się jako pokryty w raporcie.
    """
    _DATA_DRIVEN.update(component_keys)


def declare_data_driven(*component_keys: str) -> None:
    """Oznacza komponenty, których efekt w całości wynika z DANYCH (statystyki z assetów).

    Np. ulepszenia jednostek: liczby (koszt, walka, ruch, pojemność, Space Cannon...) czyta silnik
    z wariantu jednostki (``combat.resolve_unit_variant``), więc nie potrzeba hooka. Komponent
    liczy się jako pokryty (IMPLEMENTED) w raporcie, ale NIE ma funkcji hooka.
    """
    _DATA_DRIVEN.update(component_keys)


def covered_components() -> frozenset[str]:
    """Klucze ``"<kategoria>:<id>"`` komponentów, które mają zarejestrowany hook."""
    _ensure_loaded()
    covered = {h.covers for h in _REGISTRY if h.covers is not None}
    return frozenset(covered | set(_EFFECTS) | _DATA_DRIVEN)


# Podgląd skutku efektu (UI: „dotyczy: …"): (stan, rejestr, gracz) -> krótki tekst.
PreviewFn = Callable[[GameState, Any, str], str]
_PREVIEWS: dict[str, PreviewFn] = {}


def register_effect_preview(component_key: str) -> Callable[[PreviewFn], PreviewFn]:
    """Rejestruje podgląd skutku efektu liczony z bieżącego stanu (pole ``summary`` formularza)."""

    def decorate(fn: PreviewFn) -> PreviewFn:
        if component_key in _PREVIEWS:
            raise ValueError(f"Preview already registered for {component_key}.")
        _PREVIEWS[component_key] = fn
        return fn

    return decorate


def preview_for(component_key: str) -> PreviewFn | None:
    """Podgląd skutku komponentu albo ``None``."""
    _ensure_loaded()
    return _PREVIEWS.get(component_key)


def all_previews() -> list[str]:
    """Klucze komponentów z zarejestrowanym podglądem."""
    _ensure_loaded()
    return sorted(_PREVIEWS)


def all_input_keys() -> list[str]:
    """Klucze komponentów z zarejestrowanym formularzem wyborów."""
    _ensure_loaded()
    return sorted(_INPUTS)


_BOUND_REGISTRY: Any = None


def bind_registry(registry: Any) -> None:
    """Wiąże rejestr danych statycznych (ustawia go ``StaticDataRegistry``).

    Dane statyczne (frakcje, liderzy, przełomy) są niezmienne i identyczne dla każdej instancji,
    więc dopuszczamy jeden globalny dostęp — bez niego ``owned_sources`` nie znałoby domyślnych
    stanów liderów ani przełomu frakcji, a każdy punkt zaczepienia musiałby dostać ``registry``.
    Stanu GRY tu nie ma.
    """
    global _BOUND_REGISTRY
    _BOUND_REGISTRY = registry
    _unit_sources_cached.cache_clear()


def bound_registry() -> Any:
    """Powiązany rejestr danych statycznych (``None`` przed pierwszą inicjalizacją)."""
    return _BOUND_REGISTRY


def _registry_sources(player: Any) -> set[HookSource]:
    """Źródła wymagające danych statycznych: rodzina frakcji, liderzy, przełom."""
    registry = _BOUND_REGISTRY
    sources: set[HookSource] = set()
    if registry is None or player.faction is None:
        return sources
    faction = registry.factions.get(player.faction)
    if faction is not None:
        sources.add(HookSource(SOURCE_FACTION, registry.faction_family(faction)))
        for leader_id in faction.leaders:
            leader = registry.leaders.get(leader_id)
            default = "unlocked" if leader is not None and leader.type == "agent" else "locked"
            # Zablokowany i purge'owany lider nie jest źródłem (RULES.md 61.1).
            if player.leader_states.get(leader_id, default) not in ("locked", "purged"):
                sources.add(HookSource(SOURCE_LEADER, leader_id))
    if player.breakthrough_unlocked:
        breakthrough = registry.breakthrough_for_faction(player.faction)
        if breakthrough is not None:
            sources.add(HookSource(SOURCE_BREAKTHROUGH, breakthrough.id))
    return sources


def _unit_sources(player: Any) -> frozenset[HookSource]:
    """Warianty jednostek frakcyjnych ze zdolnością, których gracz używa (RULES.md 61.3)."""
    if _BOUND_REGISTRY is None or player.faction is None:
        return frozenset()
    return _unit_sources_cached(
        player.faction, tuple(sorted(player.technologies)), bool(player.breakthrough_unlocked)
    )


@functools.lru_cache(maxsize=512)
def _unit_sources_cached(
    faction_id: str, technologies: tuple[str, ...], breakthrough: bool
) -> frozenset[HookSource]:
    from src.core.combat import resolve_unit_variant  # lokalnie: combat importuje rules_hooks

    registry = _BOUND_REGISTRY
    if registry is None:
        return frozenset()
    base_types = {unit.base_type for unit in registry.units.values()}
    found: set[HookSource] = set()
    for base_type in base_types:
        unit = resolve_unit_variant(
            registry, faction_id, list(technologies), base_type, breakthrough
        )
        if unit is not None and unit.faction and unit.ability:
            found.add(HookSource(SOURCE_UNIT, unit.id))
    return frozenset(found)


def _promissory_sources(state: GameState, player_id: str) -> set[HookSource]:
    """Szablony notek w strefie (``<color>_sftt``) + commanderzy z Alliance (RULES.md 61.2)."""
    registry = _BOUND_REGISTRY
    player = state.players[player_id]
    if registry is None or not player.promissory_notes_in_play:
        return set()
    from src.core import promissory_play  # lokalnie: promissory_play importuje ten moduł
    from src.core.hooks import promissory_generic

    sources: set[HookSource] = set()
    for note_id in player.promissory_notes_in_play:
        try:
            template, _owner = promissory_play.resolve(state, registry, note_id)
        except ValueError:
            continue
        sources.add(HookSource(SOURCE_PROMISSORY, template))
    sources.update(
        HookSource(SOURCE_LEADER, leader_id)
        for leader_id in promissory_generic.alliance_commanders(state, player_id)
    )
    return sources


def _legendary_sources(player: Any) -> set[HookSource]:
    """Karty zdolności legendarnych planet, które gracz ma (kontroluje ich planety)."""
    registry = _BOUND_REGISTRY
    if registry is None:
        return set()
    sources: set[HookSource] = set()
    for planet_id in player.controlled_planets:
        planet = registry.planets.get(planet_id)
        if planet is not None and planet.legendary_ability_name:
            sources.add(HookSource(SOURCE_PLANET, planet_id))
    return sources


def owned_sources(state: GameState, player_id: str) -> frozenset[HookSource]:
    """Źródła wyjątków gracza (RULES.md 54).

    Publiczne i zawsze widoczne dla wszystkich: frakcja (i jej rodzina), technologie, relikty przed
    graczem, notki w jego strefie, odblokowani liderzy, odblokowany przełom, prawa w grze
    (``decks.agenda_laws`` - obowiązują KAŻDEGO gracza; hook prawa sprawdza w kontekście, kogo
    dotyczy) oraz efekty trwałe z magazynu (własne i globalne).

    Karty NA RĘCE (karty akcji, ukryte notki) NIE są źródłami — gra się nimi przez STOP
    (RULES.md 43.4), żeby pytanie nie zdradzało ręki. Liderzy i przełom wymagają
    ``bind_registry`` (dane statyczne); bez niego są pomijani.
    """
    player = state.players.get(player_id)
    if player is None:
        return frozenset()
    sources: set[HookSource] = {HookSource(SOURCE_TECHNOLOGY, t) for t in player.technologies}
    sources.update(HookSource(SOURCE_PROMISSORY, n) for n in player.promissory_notes_in_play)
    sources.update(_promissory_sources(state, player_id))
    sources.update(_unit_sources(player))
    sources.update(HookSource(SOURCE_RELIC, r) for r in player.relics)
    sources.update(_legendary_sources(player))
    sources.update(HookSource(SOURCE_AGENDA, law) for law in state.decks.agenda_laws)
    sources.update(
        HookSource(SOURCE_EFFECT, e.key)
        for e in state.active_effects
        if e.owner is None or e.owner == player_id
    )
    if player.faction is not None:
        sources.add(HookSource(SOURCE_FACTION, player.faction))
    sources.update(_registry_sources(player))
    return frozenset(sources)


def hooks_at(point: str, state: GameState, player_id: str) -> list[Hook]:
    """Hooki punktu ``point`` należące do gracza, w deterministycznej kolejności."""
    _ensure_loaded()
    owned = owned_sources(state, player_id)
    found = [h for h in _REGISTRY if h.point == point and h.source in owned]
    return sorted(found, key=lambda h: (h.kind.value, h.seq))


def forbidden(
    point: str, state: GameState, player_id: str, ctx: Mapping[str, Any] | None = None
) -> frozenset[str]:
    """Suma zakazów ze wszystkich hooków FORBID punktu (każdy zwraca iterowalne napisy)."""
    context = ctx or {}
    result: set[str] = set()
    for hook in hooks_at(point, state, player_id):
        if hook.kind is HookKind.FORBID:
            result.update(hook.fn(state, player_id, context))
    return frozenset(result)


def permits(
    point: str, state: GameState, player_id: str, ctx: Mapping[str, Any] | None = None
) -> bool:
    """Czy którykolwiek hook PERMIT punktu zezwala (brak hooków = ``False``)."""
    context = ctx or {}
    return any(
        bool(hook.fn(state, player_id, context))
        for hook in hooks_at(point, state, player_id)
        if hook.kind is HookKind.PERMIT
    )


def run_persistent(
    point: str, state: GameState, player_id: str, ctx: Mapping[str, Any] | None = None
) -> int:
    """Uruchamia hooki PERSISTENT punktu (efekt trwały reaguje na zdarzenie silnika).

    Zwraca liczbę uruchomionych hooków. Hook MUTUJE ``state`` (klon wołającego).
    """
    context = ctx or {}
    count = 0
    for hook in hooks_at(point, state, player_id):
        if hook.kind is HookKind.PERSISTENT:
            hook.fn(state, player_id, context)
            count += 1
    return count


def modify[N: (int, float)](
    point: str,
    state: GameState,
    player_id: str,
    base: N,
    ctx: Mapping[str, Any] | None = None,
) -> N:
    """Przepuszcza ``base`` przez hooki MODIFY (każdy: ``fn(...) -> delta`` dodawana do wyniku).

    Typ wyniku = typ ``base`` (int dla liczb całkowitych, float dla kosztów ułamkowych).
    """
    context = ctx or {}
    total = float(base)
    for hook in hooks_at(point, state, player_id):
        if hook.kind is HookKind.MODIFY:
            total += float(hook.fn(state, player_id, context))
    result: int | float = int(total) if isinstance(base, int) else total
    return cast(N, result)


@contextmanager
def temporary_hooks() -> Iterator[None]:
    """Testy: rejestracje dokonane w bloku znikają po wyjściu (rejestr wraca do stanu sprzed)."""
    _ensure_loaded()
    snapshot = list(_REGISTRY)
    effects = dict(_EFFECTS)
    inputs = dict(_INPUTS)
    try:
        yield
    finally:
        _REGISTRY[:] = snapshot
        _EFFECTS.clear()
        _EFFECTS.update(effects)
        _INPUTS.clear()
        _INPUTS.update(inputs)
