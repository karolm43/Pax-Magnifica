"""Operacje na jednostkach w strefach systemu: jedyne miejsce zmiany liczby jednostek.

Dotyczy pól ``space_units`` i ``planet_units``.

RULES.md 43.1a (punkty centralne): każda zmiana liczby jednostek w przestrzeni lub na planecie
w ``core/`` idzie przez funkcje tego modułu (wyjątek: God-Mode w ``core/board_edit.py``).
Hook „gdy jednostka zostaje zniszczona / postawiona / przeniesiona" dopisujemy tu raz, a nie
w każdej walce, ruchu, odwrocie czy eksploracji. Do tego służy ``cause`` (``UnitCause``): hook
rozróżnia zniszczenie od usunięcia i od ruchu, więc np. „gdy twój statek zostanie zniszczony"
nie odpali przy odwrocie ani przy usunięciu nadwyżki floty.

Strefa (``zone``) to ``"space"`` (przestrzeń systemu) albo id planety. Uszkodzenia (Sustain Damage)
trzyma ``core/damage.py`` — ten moduł tylko z nim współpracuje (przycina albo przenosi uszkodzenia).

Funkcje operują na przekazanym ``state`` i ``system`` (KLON roboczy wołającego) i same go nie
klonują. ``state`` jest parametrem dla przyszłych hooków (RULES.md 43); dziś nie jest używany.
"""

from __future__ import annotations

from enum import StrEnum

from src.core import floating_structures, triggers
from src.core.damage import damaged_count, move_damage, set_damaged
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, SystemState
from src.core.unit_catalog import is_space_unit


class UnitCause(StrEnum):
    """Dlaczego zmienia się liczba jednostek (kontekst dla hooków)."""

    PLACED = "placed"  # postawione: produkcja, struktura z karty, eksploracja
    SETUP = "setup"  # rozstawienie startowe frakcji
    MOVED = "moved"  # przeniesione: ruch, odwrót, lądowanie, ewakuacja z planety
    DESTROYED = "destroyed"  # zniszczone: walka, AFB, space cannon, bombardowanie, zdobycie planety
    REMOVED = "removed"  # usunięte bez zniszczenia: limit pojemności/floty, eksploracja, DMZ


def _bucket(system: SystemState, zone: str, player_id: str) -> dict[str, int]:
    """Odczyt: słownik jednostek gracza w strefie (``{}`` gdy brak; bez tworzenia wpisów)."""
    if zone == "space":
        return system.space_units.get(player_id, {})
    return system.planet_units.get(zone, {}).get(player_id, {})


def count_in_zone(system: SystemState | None, zone: str, player_id: str, base_type: str) -> int:
    """Ile jednostek danego typu ma gracz w strefie."""
    if system is None:
        return 0
    return _bucket(system, zone, player_id).get(base_type, 0)


def _prune(system: SystemState, zone: str, player_id: str) -> None:
    """Usuwa pusty słownik jednostek gracza w strefie (puste słowniki planet zostają)."""
    if zone == "space":
        if not system.space_units.get(player_id, True):
            system.space_units.pop(player_id, None)
    else:
        by_player = system.planet_units.get(zone)
        if by_player is not None and not by_player.get(player_id, True):
            by_player.pop(player_id, None)


def place_units(
    state: GameState,
    system: SystemState,
    zone: str,
    player_id: str,
    base_type: str,
    count: int,
    cause: UnitCause = UnitCause.PLACED,
) -> None:
    """Dokłada ``count`` jednostek gracza do strefy (tworzy wpisy, gdy ich brak)."""
    if count < 0:
        raise ValueError("The number of units cannot be negative.")
    # Struktura pływająca (Floating Factory) staje w przestrzeni, nie na planecie (RULES.md 62.14).
    zone = floating_structures.landing_zone(state, player_id, base_type, zone)
    if zone == "space":
        bucket = system.space_units.setdefault(player_id, {})
    else:
        bucket = system.planet_units.setdefault(zone, {}).setdefault(player_id, {})
    bucket[base_type] = bucket.get(base_type, 0) + count
    if cause is UnitCause.PLACED and count > 0:
        triggers.fire(
            state, GameEvent.UNIT_PLACED, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "base_type": base_type, "zone": zone,
                 "position": system.position, "count": count},
        )


def replace_zone_units(
    state: GameState,
    system: SystemState,
    zone: str,
    player_id: str,
    units: dict[str, int],
    cause: UnitCause = UnitCause.SETUP,
) -> None:
    """Zastępuje WSZYSTKIE jednostki gracza w strefie podanym zestawem (rozstawienie startowe)."""
    del cause  # miejsce na hooki (RULES.md 43)
    floating = {
        bt: n for bt, n in units.items()
        if floating_structures.landing_zone(state, player_id, bt, zone) != zone
    }
    if zone == "space":
        system.space_units[player_id] = dict(units)
    else:
        system.planet_units.setdefault(zone, {})[player_id] = {
            bt: n for bt, n in units.items() if bt not in floating
        }
        if floating:  # Floating Factory: rozstawienie startowe w przestrzeni (RULES.md 62.14)
            space = system.space_units.setdefault(player_id, {})
            for bt, n in floating.items():
                space[bt] = space.get(bt, 0) + n


def take_units(
    state: GameState,
    system: SystemState,
    zone: str,
    player_id: str,
    base_type: str,
    count: int,
    cause: UnitCause = UnitCause.MOVED,
) -> int:
    """Zdejmuje do ``count`` jednostek ze strefy BEZ dotykania uszkodzeń.

    Dla przeniesień: wołający sam przenosi uszkodzenia (``move_damage``) na podstawie zwróconej
    liczby sprzed zdjęcia. Zdejmuje tyle, ile jest (nigdy poniżej zera).

    Returns:
        Liczba jednostek tego typu w strefie PRZED zdjęciem.
    """
    del state, cause  # miejsce na hooki (RULES.md 43)
    if count < 0:
        raise ValueError("The number of units cannot be negative.")
    units = _bucket(system, zone, player_id)
    before = units.get(base_type, 0)
    left = before - count
    if left > 0:
        units[base_type] = left
    else:
        units.pop(base_type, None)
    _prune(system, zone, player_id)
    return before


def remove_units(
    state: GameState,
    system: SystemState,
    zone: str,
    player_id: str,
    base_type: str,
    count: int,
    cause: UnitCause = UnitCause.REMOVED,
) -> int:
    """Usuwa ``count`` jednostek ze strefy (zniszczone/usunięte) i przycina uszkodzenia.

    Uszkodzonych nie może być więcej niż jednostek (Sustain Damage, RULES.md 39).

    Returns:
        Liczba jednostek tego typu w strefie PRZED usunięciem.
    """
    before = take_units(state, system, zone, player_id, base_type, count, cause)
    remaining = damaged_count(system, zone, player_id, base_type)
    set_damaged(system, zone, player_id, base_type, remaining)
    if cause is UnitCause.DESTROYED and min(count, before) > 0:
        _note_combat_loss(state, system.position, zone, player_id, base_type, min(count, before))
        triggers.fire(
            state, GameEvent.UNIT_DESTROYED, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "base_type": base_type, "zone": zone,
                 "position": system.position, "count": min(count, before)},
        )
        from src.core import objective_events  # lokalnie: unika cyklu importów

        objective_events.on_unit_destroyed(state, system.position, zone, player_id, base_type)
    return before


def _note_combat_loss(
    state: GameState, position: str, zone: str, player_id: str, base_type: str, count: int
) -> None:
    """Statek zniszczony w trwającej walce kosmicznej → ``ActiveCombat.destroyed_all``.

    Jedno miejsce dla każdej przyczyny (straty z rzutów, AFB, karty, Assault Cannon): ślad całej
    walki dla Salvage Operations i Sleeper Cell (RULES.md 62.8).
    """
    combat = state.active_combat
    if (
        combat is None
        or combat.kind != "space"
        or combat.position != position
        or zone != "space"
        or not is_space_unit(base_type)
    ):
        return
    combat.destroyed_all = [
        *combat.destroyed_all, *({"player": player_id, "base_type": base_type},) * count
    ]


def transfer_units(
    state: GameState,
    src: SystemState,
    src_zone: str,
    dest: SystemState,
    dest_zone: str,
    player_id: str,
    base_type: str,
    count: int,
    cause: UnitCause = UnitCause.MOVED,
) -> None:
    """Przenosi ``count`` jednostek między strefami (także tego samego systemu) z uszkodzeniami."""
    before = take_units(state, src, src_zone, player_id, base_type, count, cause)
    place_units(state, dest, dest_zone, player_id, base_type, count, cause)
    move_damage(src, src_zone, dest, dest_zone, player_id, base_type, count, before)


def clear_planet(system: SystemState, planet: str) -> None:
    """Usuwa z planety WSZYSTKIE wpisy jednostek (po zniszczeniu/purge planety; bez zdarzeń).

    Wołaj po ``remove_units`` dla każdej jednostki (zdarzenia i uszkodzenia), by zostały puste
    słowniki posprzątać.
    """
    system.planet_units.pop(planet, None)
