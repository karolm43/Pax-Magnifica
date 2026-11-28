"""Uszkodzenia jednostek (Sustain Damage, RULES.md 39 W8/W10) — odczyt, zapis, ruch, naprawa.

Stan: ``SystemState.damaged_units`` = ``{strefa: {player_id: {base_type: liczba}}}``. Strefa
to ``"space"`` albo id planety. Liczba uszkodzonych nigdy nie przekracza liczby jednostek —
odczyt jest przycinany (God-Mode może zmienić liczby jednostek bez znajomości uszkodzeń).

Funkcje mutujące działają na PRZEKAZANYM ``SystemState`` (wołający pracuje na klonie stanu).
"""

from __future__ import annotations

from src.core.game_state import GameState, SystemState


def _units_in(system: SystemState, zone: str, player_id: str) -> dict[str, int]:
    if zone == "space":
        return system.space_units.get(player_id, {})
    return system.planet_units.get(zone, {}).get(player_id, {})


def damaged_count(
    system: SystemState | None, zone: str, player_id: str, base_type: str
) -> int:
    """Liczba uszkodzonych jednostek (przycięta do liczby jednostek w strefie)."""
    if system is None:
        return 0
    raw = system.damaged_units.get(zone, {}).get(player_id, {}).get(base_type, 0)
    return max(0, min(raw, _units_in(system, zone, player_id).get(base_type, 0)))


def set_damaged(
    system: SystemState, zone: str, player_id: str, base_type: str, count: int
) -> None:
    """Ustawia liczbę uszkodzonych (przycina do jednostek; zero usuwa wpis)."""
    limit = _units_in(system, zone, player_id).get(base_type, 0)
    value = max(0, min(count, limit))
    by_player = system.damaged_units.setdefault(zone, {}).setdefault(player_id, {})
    if value > 0:
        by_player[base_type] = value
    else:
        by_player.pop(base_type, None)
    if not by_player:
        system.damaged_units[zone].pop(player_id, None)
    if not system.damaged_units.get(zone):
        system.damaged_units.pop(zone, None)


def move_damage(
    source: SystemState,
    source_zone: str,
    dest: SystemState,
    dest_zone: str,
    player_id: str,
    base_type: str,
    moved: int,
    source_before: int,
) -> None:
    """Przenosi uszkodzenia razem z ``moved`` jednostkami (RULES.md 39.3).

    ⚠️ ZAŁOŻENIE: najpierw ruszają NIEuszkodzone egzemplarze — uszkodzone wyjeżdżają
    dopiero, gdy nieuszkodzonych zabraknie (wybór egzemplarza nie jest modelowany).
    Woła się PO zmianie liczników jednostek; ``source_before`` = liczba w źródle przed ruchem.
    """
    raw = source.damaged_units.get(source_zone, {}).get(player_id, {}).get(base_type, 0)
    damaged_src = max(0, min(raw, source_before))
    undamaged_src = source_before - damaged_src
    damaged_moving = max(0, moved - undamaged_src)
    if damaged_src == 0:
        return
    set_damaged(source, source_zone, player_id, base_type, damaged_src - damaged_moving)
    if damaged_moving > 0:
        current = (
            dest.damaged_units.get(dest_zone, {}).get(player_id, {}).get(base_type, 0)
        )
        set_damaged(dest, dest_zone, player_id, base_type, current + damaged_moving)


def clear_zone_damage(system: SystemState, zone: str) -> None:
    """Zdejmuje WSZYSTKIE uszkodzenia ze strefy (np. po wyczyszczeniu planety kartą)."""
    system.damaged_units.pop(zone, None)


def repair_all(state: GameState) -> None:
    """Naprawia wszystkie uszkodzone jednostki (faza statusu, krok 7 — W10). Mutuje ``state``."""
    for system in state.systems.values():
        system.damaged_units = {}


def _spent_key(player_id: str, zone: str, base_type: str) -> str:
    return f"{player_id}|{zone}|{base_type}"


def sustain_spent(
    state: GameState, position: str, zone: str, player_id: str, base_type: str
) -> int:
    """Undamaged units of the group that already used SUSTAIN DAMAGE in the ongoing combat's
    timing window and were repaired since: they cannot use it again in that window (F_empyrean
    dynamo 1, C_action_cards reflective-shielding 1.1). 0 outside that combat."""
    combat = state.active_combat
    if combat is None or combat.position != position:
        return 0
    return max(0, combat.sustain_spent.get(_spent_key(player_id, zone, base_type), 0))


def forget_sustain_spent(
    state: GameState, position: str, zone: str, player_id: str, base_type: str, lost: int
) -> None:
    """``lost`` undamaged units of the group left the combat: the spent ones go first (the owner
    picks which identical unit is destroyed - keeping a unit that can still SUSTAIN DAMAGE is
    never worse). MUTATES ``state``."""
    combat = state.active_combat
    key = _spent_key(player_id, zone, base_type)
    if combat is None or combat.position != position or key not in combat.sustain_spent:
        return
    if lost <= 0:
        return
    left = combat.sustain_spent[key] - lost
    if left > 0:
        combat.sustain_spent[key] = left
    else:
        combat.sustain_spent.pop(key)


def repair_after_sustain(
    state: GameState, position: str, zone: str, player_id: str, base_type: str, count: int
) -> int:
    """Repairs ``count`` units that just used SUSTAIN DAMAGE (Dynamo) - THE point for such repairs.

    In the ongoing combat in ``position`` the repaired units are recorded for the timing window:
    they stay unable to use SUSTAIN DAMAGE again until the next Roll Dice step (F_empyrean
    dynamo 1). Returns how many were repaired. MUTATES ``state``.
    """
    system = state.systems[position]
    hurt = damaged_count(system, zone, player_id, base_type)
    repaired = max(0, min(count, hurt))
    if repaired == 0:
        return 0
    set_damaged(system, zone, player_id, base_type, hurt - repaired)
    combat = state.active_combat
    if combat is not None and combat.position == position:
        key = _spent_key(player_id, zone, base_type)
        combat.sustain_spent[key] = combat.sustain_spent.get(key, 0) + repaired
    return repaired
