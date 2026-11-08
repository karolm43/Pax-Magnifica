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
from typing import Any

from src.core.game_state import GameState

# Punkty zaczepienia (nazwy). Dopisuj tu, gdy reguła bazowa dostaje nowy punkt.
POINT_PRODUCTION_FORBIDS = "production.forbids"  # FORBID -> typy jednostek (ctx: producer_type)
POINT_MOVEMENT_ENTER_ASTEROIDS = "movement.enter_asteroids"  # PERMIT -> bool

# Rodzaje źródeł hooka (kto "posiada" wyjątek).
SOURCE_FACTION = "faction"
SOURCE_TECHNOLOGY = "technology"


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


@dataclass(frozen=True)
class Hook:
    """Jeden zarejestrowany wyjątek."""

    point: str
    source: HookSource
    kind: HookKind
    fn: HookFn
    seq: int  # kolejność rejestracji (rozstrzyga remis w obrębie rodzaju)


_REGISTRY: list[Hook] = []
_loaded = False


def register(
    point: str, source: HookSource, kind: HookKind
) -> Callable[[HookFn], HookFn]:
    """Dekorator rejestrujący funkcję jako hook na ``point`` dla ``source``."""

    def decorate(fn: HookFn) -> HookFn:
        _REGISTRY.append(Hook(point, source, kind, fn, len(_REGISTRY)))
        return fn

    return decorate


def _ensure_loaded() -> None:
    """Leniwie importuje pakiet ``core.hooks`` (jego moduły rejestrują się przy imporcie)."""
    global _loaded
    if not _loaded:
        _loaded = True
        import src.core.hooks  # noqa: F401  (import dla efektu ubocznego: rejestracja)


def owned_sources(state: GameState, player_id: str) -> frozenset[HookSource]:
    """Źródła wyjątków, które gracz aktualnie posiada (frakcja, technologie)."""
    player = state.players.get(player_id)
    if player is None:
        return frozenset()
    sources: set[HookSource] = {HookSource(SOURCE_TECHNOLOGY, t) for t in player.technologies}
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


def modify(
    point: str,
    state: GameState,
    player_id: str,
    base: int,
    ctx: Mapping[str, Any] | None = None,
) -> int:
    """Przepuszcza ``base`` przez hooki MODIFY (każdy: ``fn(...) -> delta`` dodawana do wyniku)."""
    context = ctx or {}
    value = base
    for hook in hooks_at(point, state, player_id):
        if hook.kind is HookKind.MODIFY:
            value += int(hook.fn(state, player_id, context))
    return value


@contextmanager
def temporary_hooks() -> Iterator[None]:
    """Testy: rejestracje dokonane w bloku znikają po wyjściu (rejestr wraca do stanu sprzed)."""
    _ensure_loaded()
    snapshot = list(_REGISTRY)
    try:
        yield
    finally:
        _REGISTRY[:] = snapshot
