"""Rejestr hooków reguł: wyjątki frakcji, technologii i kart BEZ edycji reguły bazowej.

RULES.md 43.1: reguła bazowa nie zna wyjątków. W miejscu, na które coś może wpływać, wywołuje
PUNKT ZACZEPIENIA (``point``, napis), a wyjątek rejestruje się osobno (pakiet ``core/hooks/``)
jako ``(źródło, punkt, rodzaj, funkcja)``. Hook jest CZYSTĄ funkcją ``(state, player_id, ctx)``.

Hook obowiązuje gracza tylko wtedy, gdy ten POSIADA jego źródło (frakcja, technologia, ...) —
patrz ``owned_sources``. Kolejność wielu hooków na jednym punkcie jest deterministyczna
(RULES.md 43.1 pkt 5): REPLACE, FORBID, PERMIT, MODIFY, TRIGGER, PERSISTENT, a w obrębie rodzaju
kolejność rejestracji.

Zaimplementowane API (rodzaje używane dziś): ``forbidden`` (FORBID), ``permits`` (PERMIT),
``modify`` (MODIFY). REPLACE/TRIGGER/PERSISTENT są zarezerwowane w ``HookKind`` — dochodzą
razem z pierwszym użyciem (TRIGGER przez ``core/timing.py``, RULES.md 43.1 pkt 6).

God-Mode omija hooki tak jak resztę reguł (RULES.md 43.1 pkt 11).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

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

# Rodzaje źródeł hooka (kto "posiada" wyjątek).
SOURCE_FACTION = "faction"
SOURCE_TECHNOLOGY = "technology"
SOURCE_AGENDA = "agenda"  # prawo w grze (decks.agenda_laws) - obowiązuje KAŻDEGO gracza
SOURCE_PROMISSORY = "promissory"  # notka leżąca w strefie gracza (promissory_notes_in_play)


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


# Opis wyborów gracza dla efektu (formularz UI): (stan, rejestr, gracz) -> lista wejść.
InputsFn = Callable[[GameState, Any, str], list[dict[str, Any]]]

_REGISTRY: list[Hook] = []
_EFFECTS: dict[str, EffectFn] = {}
_INPUTS: dict[str, InputsFn] = {}
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


def covered_components() -> frozenset[str]:
    """Klucze ``"<kategoria>:<id>"`` komponentów, które mają zarejestrowany hook."""
    _ensure_loaded()
    covered = {h.covers for h in _REGISTRY if h.covers is not None}
    return frozenset(covered | set(_EFFECTS))


def owned_sources(state: GameState, player_id: str) -> frozenset[HookSource]:
    """Źródła wyjątków gracza: frakcja, technologie, notki w jego strefie i prawa w grze.

    Prawa (``decks.agenda_laws``) obowiązują KAŻDEGO gracza; hook prawa sam sprawdza w kontekście,
    kogo dotyczy (np. wynik wyborów w ``state.decks.agenda_laws[id]``).
    NIE ujęte (świadomie): liderzy (stan domyślny wymaga rejestru), relikty (brak modelu własności),
    przełom (id zależy od frakcji) - dochodzą z pierwszym hookiem tego typu.
    """
    player = state.players.get(player_id)
    if player is None:
        return frozenset()
    sources: set[HookSource] = {HookSource(SOURCE_TECHNOLOGY, t) for t in player.technologies}
    sources.update(HookSource(SOURCE_PROMISSORY, n) for n in player.promissory_notes_in_play)
    sources.update(HookSource(SOURCE_AGENDA, law) for law in state.decks.agenda_laws)
    if player.faction is not None:
        sources.add(HookSource(SOURCE_FACTION, player.faction))
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
