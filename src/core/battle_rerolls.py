"""Walka: przerzuty i zmiany kości PO rzucie (relikty, Fire Team, War Funding) — RULES.md 39.

Warstwa NAD ``battle.py`` (korzysta z jego przebiegu rund); wydzielone z ``battle.py``.
"""

from __future__ import annotations

from typing import Any

from src.core import (
    exhaust,
    rules_hooks,
)
from src.core.battle import (
    _RESUME_ASSIGN,
    _after_losses,
    _auto_assign_neutral,
    _extra_hits,
    _remove_units,
    natural_extra_hits,
    note_destroyed,
)
from src.core.battle_units import _combat, required_hits, side_units
from src.core.dice import DIE_SIDES, next_rng, record_table_roll, roll_dice
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry

# ----------------------------------------------------------------- relikty: kości po rzucie


def _entry_hits(
    state: GameState, player_id: str, combat: ActiveCombat, entry: dict[str, Any]
) -> int:
    """Trafienia wpisu rzutu z uwzględnieniem poprawek pojedynczych kości (``bonus``)."""
    dice = [int(d) for d in entry.get("dice", [])]
    bonus = list(entry.get("bonus") or [0] * len(dice))
    modifier = int(entry.get("modifier", 0))
    hits = sum(1 for d, b in zip(dice, bonus, strict=False) if d + modifier + b >= entry["hitsOn"])
    base_type = str(entry.get("baseType", ""))
    return hits * rules_hooks.modify(
        rules_hooks.POINT_COMBAT_HIT_MULTIPLIER, state, player_id, 1,
        {"kind": combat.kind, "base_type": base_type},
    ) + natural_extra_hits(state, player_id, combat.kind, base_type, dice)


def _require_dice_window(state: GameState) -> ActiveCombat:
    """Rzuty rundy leżą na stole, a nikt jeszcze nie przypisał strat (okno ASSIGN)."""
    combat = _combat(state)
    if combat.step is CombatStep.TRIGGERS and combat.resume == _RESUME_ASSIGN:
        return combat  # rzut leży, oferty „po rzucie” jeszcze przed przypisaniem strat
    window = state.pending_window
    if (
        combat.step is not CombatStep.ASSIGN
        or window is None
        or window.window_type is not WindowType.COMBAT_ASSIGN_HITS
        or combat.afb_assign
        or not combat.log
        or combat.log[-1].get("phase") != "COMBAT"
    ):
        raise ValueError(
            "Combat dice can be changed only after the roll, before hits are assigned."
        )
    if combat.log[-1].get("losses") or window.cursor > 0:
        raise ValueError("Hits have already been assigned this round.")
    return combat


def _refresh_after_dice_change(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Przelicza trafienia z rzutów po zmianie kości i odbudowuje okno przypisania strat."""
    combat = _combat(state)
    hits_by = {
        pid: sum(_entry_hits(state, pid, combat, e) for e in combat.rolls.get(pid, []))
        for pid in (combat.attacker, combat.defender)
    }
    for pid, entries in combat.rolls.items():
        for entry in entries:
            entry["hits"] = _entry_hits(state, pid, combat, entry)
    extra = _extra_hits(state, combat, hits_by)
    hits_by = {pid: hits + extra[pid] for pid, hits in hits_by.items()}
    combat.pending_hits = {
        combat.defender: hits_by[combat.attacker],
        combat.attacker: hits_by[combat.defender],
    }
    combat.log[-1]["hits"] = hits_by
    combat.log[-1]["extra"] = extra
    combat.log[-1]["rolls"] = combat.rolls
    for pid in (combat.defender, combat.attacker):
        if pid == NEUTRAL_PLAYER_ID:
            _auto_assign_neutral(state, grid, registry, pid)
    queue = [
        pid
        for pid in (combat.defender, combat.attacker)
        if required_hits(state, grid, registry, pid) > 0
    ]
    window = state.pending_window
    assert window is not None
    if queue:
        window.queue = queue
        window.cursor = 0
        window.responded = []
        return state
    state.pending_window = None
    return _after_losses(state, grid, registry)


def _recount_dice(state: GameState, combat: ActiveCombat, owner: str) -> int:
    """Po zmianie kości ``owner`` (MUTUJE): jego trafienia od nowa + dodatkowe trafienia (VPW).

    Trafienia ``owner`` przeciw przeciwnikowi liczone od nowa (kości + ``_extra_hits``). Dodatkowe
    trafienie PRZECIWNIKA zależy od trafień ``owner`` (VPW: „if your opponent produced 1 or more
    hits”), więc jego pula zmienia się tylko o różnicę - wcześniejsze anulowania zostają.
    Zwraca nowe trafienia ``owner``.
    """
    opponent = combat.defender if owner == combat.attacker else combat.attacker
    for entry in combat.rolls.get(owner, []):
        entry["hits"] = _entry_hits(state, owner, combat, entry)
    dice_hits = {
        pid: sum(int(e["hits"]) for e in combat.rolls.get(pid, []))
        for pid in (combat.attacker, combat.defender)
    }
    last: dict[str, Any] = combat.log[-1] if combat.log else {}
    before = {str(k): int(v) for k, v in (last.get("extra") or {}).items()}
    extra = _extra_hits(state, combat, dice_hits)
    total = dice_hits[owner] + extra[owner]
    combat.pending_hits[opponent] = total
    delta = extra[opponent] - before.get(opponent, 0)
    if delta:
        combat.pending_hits[owner] = max(0, combat.pending_hits.get(owner, 0) + delta)
        window = state.pending_window
        if delta > 0 and window is not None and owner not in window.queue:
            window.queue = [*window.queue, owner]
    if combat.log:
        last.setdefault("rolls", {})[owner] = combat.rolls.get(owner, [])
        hits = last.setdefault("hits", {})
        hits[owner] = total
        hits[opponent] = dice_hits[opponent] + extra[opponent]
        last["extra"] = extra
    return total


def reroll_combat_dice(
    state: GameState, owner: str, chosen: set[tuple[int, int]], source: str, name: str,
    *, roller: str | None = None,
) -> int:
    """Przerzuca wybrane kości rzutu ``owner`` (MUTUJE ``state``); zwraca jego nowe trafienia.

    ``chosen`` = ``{(indeks wpisu, indeks kości)}``. Modyfikatory pierwotnego rzutu obowiązują
    (C_action_cards). Trafienia przeciw przeciwnikowi liczone od nowa; gdy nie był w kolejce
    przypisania, a ma teraz trafienia, dołącza do niej. ``roller`` = kto przerzuca (do dziennika).
    """
    combat = _combat(state)
    rolls = combat.rolls.get(owner, [])
    for index, die in chosen:
        if not (0 <= index < len(rolls)) or not (0 <= die < len(rolls[index]["dice"])):
            raise ValueError(f"Unknown die: {index}:{die}")
    rng = next_rng(state)
    results: list[int] = []
    for index, die in sorted(chosen):
        value = rng.randint(1, DIE_SIDES)
        rolls[index]["dice"][die] = value
        results.append(value)
    total = _recount_dice(state, combat, owner)
    opponent = combat.defender if owner == combat.attacker else combat.attacker
    window = state.pending_window
    if total > 0 and window is not None and opponent not in window.queue:
        window.queue = [*window.queue, opponent]
    record_table_roll(
        state, roller or owner, source, name, results, summary=f"{total} hit(s) after the reroll."
    )
    return total


def boost_combat_dice(
    state: GameState, owner: str, chosen: set[tuple[int, int]], source: str, amount: int = 1
) -> int:
    """+``amount`` do wyniku wybranych kości rzutu ``owner`` (MUTUJE); zwraca jego trafienia.

    Ślad ``boosted[source]`` w wpisie rzutu pilnuje, by jedna kość dostała premię z danego źródła
    najwyżej raz (Wrath of Kenara, F_hacan). Tylko między rzutem a przypisaniem strat.
    """
    _require_dice_window(state)
    combat = _combat(state)
    rolls = combat.rolls.get(owner, [])
    for index, die in chosen:
        if not (0 <= index < len(rolls)) or not (0 <= die < len(rolls[index]["dice"])):
            raise ValueError(f"Unknown die: {index}:{die}")
        if die in rolls[index].get("boosted", {}).get(source, []):
            raise ValueError("This die was already improved by this ability.")
    for index, die in sorted(chosen):
        entry = rolls[index]
        bonus = list(entry.get("bonus") or [0] * len(entry["dice"]))
        bonus[die] += amount
        entry["bonus"] = bonus
        boosted = dict(entry.get("boosted", {}))
        boosted[source] = sorted({*boosted.get(source, []), die})
        entry["boosted"] = boosted
    total = _recount_dice(state, combat, owner)
    opponent = combat.defender if owner == combat.attacker else combat.attacker
    window = state.pending_window
    if (
        combat.step is CombatStep.ASSIGN
        and total > 0
        and window is not None
        and opponent not in window.queue
    ):
        window.queue = [*window.queue, opponent]
    return total


def dice_relic_tools(state: GameState) -> list[dict[str, str]]:
    """Narzędzia reliktów dostępne TERAZ nad rzutami rundy: ``[{player, tool}]``.

    ``reroll`` (Crown of Thalnos) i ``adjust`` (Heart of Ixth). Pusta lista poza oknem przypisania
    strat albo po pierwszym przypisaniu.
    """
    try:
        _require_dice_window(state)
    except ValueError:
        return []
    tools: list[dict[str, str]] = []
    for pid in state.players:
        if rules_hooks.permits(rules_hooks.POINT_COMBAT_REROLL_PLUS_ONE, state, pid):
            tools.append({"player": pid, "tool": "reroll"})
        if rules_hooks.forbidden(rules_hooks.POINT_DIE_ADJUST, state, pid):
            tools.append({"player": pid, "tool": "adjust"})
    return tools


def reroll_with_relic(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    picks: dict[int, list[int]],
) -> GameState:
    """Przerzut kości z +1 do wyniku (hook ``combat.reroll_plus_one``, Crown of Thalnos).

    ``picks`` = ``{indeks wpisu rzutu gracza: [indeksy kości]}``. Przerzucone kości dostają +1 do
    wyniku, a jednostka, która przerzucała kości i NIE ma po nich trafienia, ginie (bez Sustain
    Damage) - na końcu kroku rzutów, przed przypisaniem strat.

    Raises:
        ValueError: Brak relikt/okna, zły wybór kości albo straty już przypisano.
    """
    _require_dice_window(state)
    if not rules_hooks.permits(rules_hooks.POINT_COMBAT_REROLL_PLUS_ONE, state, player_id):
        raise ValueError("You cannot reroll combat dice.")
    entries_in = state.active_combat.rolls.get(player_id, []) if state.active_combat else []
    chosen = {i: sorted(set(d)) for i, d in picks.items() if d}
    if not chosen:
        raise ValueError("Choose at least one die to reroll.")
    for index, dice_idx in chosen.items():
        if not 0 <= index < len(entries_in) or any(
            not 0 <= d < len(entries_in[index]["dice"]) for d in dice_idx
        ):
            raise ValueError("Choose dice from your own combat rolls.")
    total = sum(len(d) for d in chosen.values())
    rolled, fresh = roll_dice(state, total)
    new_state = rolled.clone()
    combat = _combat(new_state)
    entries = combat.rolls[player_id]
    units = {u.base_type: u for u in side_units(new_state, grid, registry, player_id)}
    cursor = 0
    destroyed: dict[str, int] = {}
    for index, dice_idx in chosen.items():
        entry = entries[index]
        bonus = list(entry.get("bonus") or [0] * len(entry["dice"]))
        per = units[entry["baseType"]].dice_per_unit if entry["baseType"] in units else 1
        touched: set[int] = set()
        for die in dice_idx:
            entry["dice"][die] = fresh[cursor]
            bonus[die] += 1
            cursor += 1
            touched.add(die // per)
        entry["bonus"] = bonus
        entry["rerolled"] = sorted({*entry.get("rerolled", []), *dice_idx})
        modifier = int(entry.get("modifier", 0))
        for unit_index in touched:
            span = range(unit_index * per, (unit_index + 1) * per)
            if not any(
                entry["dice"][d] + modifier + bonus[d] >= entry["hitsOn"]
                for d in span
                if d < len(entry["dice"])
            ):
                destroyed[entry["baseType"]] = destroyed.get(entry["baseType"], 0) + 1
    record_table_roll(
        new_state, player_id, "relic", "The Crown of Thalnos", fresh,
        summary="Rerolled with +1; units without a hit are destroyed",
    )
    new_state.destroyed_by = player_id  # własne straty: przeciwnik nie zdobywa celów za zniszczenie
    for base_type, count in destroyed.items():
        _remove_units(new_state, combat, player_id, base_type, count)
        note_destroyed(combat, player_id, base_type, count, units[base_type].base_hits_on)
    new_state.destroyed_by = None
    return _refresh_after_dice_change(new_state, grid, registry)


def adjust_die_with_relic(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    *,
    target: str,
    entry_index: int,
    die_index: int,
    delta: int,
) -> GameState:
    """Zmiana wyniku JEDNEJ kości o ±1 (hook ``dice.adjust_result``, Heart of Ixth).

    Dotyczy dowolnego rzutu rundy (własnego lub przeciwnika). Wskazany relikt się wyczerpuje;
    wynik zostaje w zakresie kości (1-10).

    Raises:
        ValueError: Brak gotowego relikt/okna, zła kość albo straty już przypisano.
    """
    _require_dice_window(state)
    if delta not in (-1, 1):
        raise ValueError("A die can change by 1 up or down.")
    ready = sorted(rules_hooks.forbidden(rules_hooks.POINT_DIE_ADJUST, state, player_id))
    if not ready:
        raise ValueError("You have no ready relic that changes die results.")
    combat = _combat(state)
    entries = combat.rolls.get(target, [])
    if not 0 <= entry_index < len(entries) or not 0 <= die_index < len(
        entries[entry_index]["dice"]
    ):
        raise ValueError("Choose one of the dice rolled this round.")
    new_value = entries[entry_index]["dice"][die_index] + delta
    if not 1 <= new_value <= DIE_SIDES:
        raise ValueError(f"A die result must stay between 1 and {DIE_SIDES}.")
    new_state = state.clone()
    exhaust.exhaust_relic(new_state, player_id, ready[0])
    _combat(new_state).rolls[target][entry_index]["dice"][die_index] = new_value
    return _refresh_after_dice_change(new_state, grid, registry)
