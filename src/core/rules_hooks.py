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
POINT_COMBAT_REROLL_MISSES = "combat.reroll_misses"  # PERMIT -> przerzut chybień (ctx: base_type)
POINT_AGENDA_VOTE_MODIFIER = "agenda.vote_modifier"  # MODIFY -> delta głosów (ctx: agenda_id)
POINT_PRODUCTION_VALUE = "production.value"  # MODIFY -> delta PRODUCTION jednostki
# ctx: base_type, zone
POINT_PRODUCTION_COST = "production.cost"  # MODIFY -> delta łącznego kosztu zamówienia
POINT_PAYMENT_COMMODITIES_AS_TG = "payment.commodities_as_trade_goods"  # PERMIT -> bool
# Space Cannon: modyfikator wyniku rzutów PRZECIWKO właścicielowi hooka (pytamy właściciela CELU;
# ctx: shooter) - np. Antimass Deflectors: -1 do wyniku każdej kości.
POINT_SPACE_CANNON_ROLL_MODIFIER = "space_cannon.roll_modifier"
# Space Cannon: dodatkowe kości dla JEDNEJ jednostki strzelca przy jednym użyciu (Plasma Scoring).
POINT_SPACE_CANNON_EXTRA_DICE = "space_cannon.extra_dice"
# Bombardment: dodatkowe kości dla JEDNEJ jednostki przy jednym użyciu (Plasma Scoring).
POINT_BOMBARDMENT_EXTRA_DICE = "bombardment.extra_dice"
# Liczba akcji gracza w jego turze fazy akcji (bazowo 1; Fleet Logistics: +1).
POINT_TURN_ACTIONS = "turn.actions"
# Faza statusu: liczba kart akcji dobieranych przez gracza (bazowo 1; Neural Motivator: +1).
POINT_STATUS_ACTION_CARDS = "status.action_cards"
# Faza statusu: liczba żetonów dowodzenia zdobywanych przez gracza (bazowo 2; Hyper Metabolism: +1).
POINT_STATUS_COMMAND_TOKENS = "status.command_tokens"

# Rodzaje źródeł hooka (kto "posiada" wyjątek).
SOURCE_FACTION = "faction"
SOURCE_TECHNOLOGY = "technology"
SOURCE_AGENDA = "agenda"  # prawo w grze (decks.agenda_laws) - obowiązuje KAŻDEGO gracza
SOURCE_PROMISSORY = "promissory"  # notka leżąca w strefie gracza (promissory_notes_in_play)
SOURCE_RELIC = "relic"  # relikt przed graczem (PlayerState.relics)
SOURCE_LEADER = "leader"  # lider odblokowany lub gotowy (stan domyślny z danych frakcji)
SOURCE_BREAKTHROUGH = "breakthrough"  # odblokowany przełom frakcji
SOURCE_EFFECT = "effect"  # efekt trwały z magazynu (GameState.active_effects)


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


# Opis wyborów gracza dla efektu (formularz UI): (stan, rejestr, gracz) -> lista wejść.
InputsFn = Callable[[GameState, Any, str], list[dict[str, Any]]]

_REGISTRY: list[Hook] = []
_EFFECTS: dict[str, EffectFn] = {}
_INPUTS: dict[str, InputsFn] = {}
_DATA_DRIVEN: set[str] = set()
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
) -> Callable[[HookFn], HookFn]:
    """Rejestruje hook ZDARZENIA: ``fn(state, player_id, ctx)`` odpalane przez ``triggers.fire``.

    * ``kind=TRIGGER`` (domyślnie): reakcja. ``optional=False`` = obowiązkowa (komponent w grze),
      ``optional=True`` = „you may” -> oferta w oknie REACTION dla posiadacza publicznego źródła.
    * ``kind=REPLACE``: „instead of” — ``fn`` zwraca prawdę, gdy zastąpiła zdarzenie (wołający
      pomija wtedy swój krok); opcjonalny REPLACE też staje się ofertą.
    * ``where``: filtr kontekstu (np. ``{"phase": "strategy"}``); ``condition``: warunek
      sprawdzany przy wyzwoleniu.
    * ``covers``: komponent, który hook realizuje (status IMPLEMENTED w rejestrze efektów).
    """
    if kind not in (HookKind.TRIGGER, HookKind.REPLACE):
        raise ValueError("Event hooks must be TRIGGER or REPLACE.")
    where_items = tuple(sorted((k, str(v)) for k, v in (where or {}).items()))

    def decorate(fn: HookFn) -> HookFn:
        _REGISTRY.append(
            Hook(
                event_point(event, moment), source, kind, fn, len(_REGISTRY), covers,
                optional, where_items, condition, label,
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
            if player.leader_states.get(leader_id, default) != "locked":
                sources.add(HookSource(SOURCE_LEADER, leader_id))
    if player.breakthrough_unlocked:
        breakthrough = registry.breakthrough_for_faction(player.faction)
        if breakthrough is not None:
            sources.add(HookSource(SOURCE_BREAKTHROUGH, breakthrough.id))
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
    sources.update(HookSource(SOURCE_RELIC, r) for r in player.relics)
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
