"""Silnik walki: kosmicznej i naziemnej — rundy, AFB, rzuty, Sustain Damage, straty (RULES.md 39).

Przebieg (``ActiveCombat.step``): ``AFB`` (1. runda walki kosmicznej, gdy ktoś ma AFB) →
``ROLL`` (rzuty obu stron) → ``ASSIGN`` (okno ``COMBAT_ASSIGN_HITS``: obrońca, potem atakujący)
→ kolejna runda albo ``DONE``. Wszystkie wartości z WARIANTU jednostki gracza
(``combat.resolve_unit_variant``); rzuty przez ``core/dice.py`` (seedowalne, w stanie gry).

Funkcje CZYSTE (``state -> state``). Walidacja twarda: ``ValueError`` → HTTP 422.
"""

from __future__ import annotations

from typing import Any

from src.core import (
    ability_notes,
    capacity,
    chronicle,
    coexistence,
    entropic_scar,
    extra_dice,
    floating_structures,
    objective_events,
    rules_hooks,
    ship_roles,
    timing,
    triggers,
    unit_ops,
)
from src.core.battle_units import _FIGHTER, _combat, _units_map, _zone
from src.core.battle_units import CombatUnit as CombatUnit
from src.core.battle_units import ability_hit_targets as ability_hit_targets
from src.core.battle_units import absorbable_hits as absorbable_hits
from src.core.battle_units import combat_units as combat_units
from src.core.battle_units import required_hits as required_hits
from src.core.battle_units import side_units as side_units
from src.core.battle_units import sustain_cancels as sustain_cancels
from src.core.battle_units import sustain_denied as sustain_denied
from src.core.damage import damaged_count, set_damaged
from src.core.dice import count_hits, roll_dice
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    TacticalStep,
    WindowType,
)
from src.core.hex_grid import HexGrid
from src.core.movement import CargoPickup
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.registry import StaticDataRegistry
from src.core.retreat import perform_retreat, retreat_destinations
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

# ------------------------------------------------------------------------------- start


def start_combat(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    planet: str | None = None,
) -> GameState:
    """Rozpoczyna walkę w aktywnym systemie: kosmiczną (``planet`` None) albo naziemną.

    Raises:
        ValueError: Zły krok akcji, trwa okno/walka, brak dokładnie dwóch stron (W1–W3).
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    if state.sustain_trace:  # walka zamyka okno Direct Hit po Space Cannon
        state = state.clone()
        state.sustain_trace = []
    kind = "space" if planet is None else "ground"
    # Inwazja komponentu (Quantum Dissemination, RULES.md 62.10): walka naziemna w systemie
    # inwazji, poza akcją taktyczną (system nie jest aktywowany).
    component = kind == "ground" and state.invasion is not None and bool(state.invasion.source)
    if component and state.invasion is not None:
        active: str | None = state.invasion.position
        attacker: str | None = state.invasion.attacker
    else:
        active = state.active_system
        attacker = state.active_player_id
    if active is None or attacker is None:
        raise ValueError("Combat needs an active system and an active player.")
    required_step = TacticalStep.SPACE_COMBAT if kind == "space" else TacticalStep.INVASION
    if not component and state.tactical_step is not required_step:
        raise ValueError(
            f"{kind.capitalize()} combat is fought in the {required_step.value} step."
        )
    if state.active_combat is not None and state.active_combat.step is not CombatStep.DONE:
        raise ValueError("A combat is already in progress.")
    if state.pending_window is not None:
        raise ValueError("Resolve the open timing window before starting combat.")
    if kind == "ground":
        system = state.systems.get(active)
        if system is None or planet not in system.planet_units:
            raise ValueError(f"There are no ground forces on {planet}.")

    # Neutralni nie są graczem (R_neutral_units), ale walczą jak inny gracz.
    participants = [
        pid
        for pid in (*state.players, NEUTRAL_PLAYER_ID)
        if combat_units(
            state, grid, registry, kind=kind, position=active, planet=planet, player_id=pid
        )
    ]
    others = [pid for pid in participants if pid != attacker]
    if kind == "ground" and planet is not None:
        # Koegzystencja z wyboru (Slumberstate, RULES.md 40.1 I7b): ci gracze nie walczą.
        committed = state.invasion is not None and planet in state.invasion.committed
        others = coexistence.fighting(
            state, active, planet, attacker, others, committed=committed
        )
    if attacker not in participants or not others:
        raise ValueError("There is no combat here: both sides need units able to fight.")
    if len(others) > 1:
        raise ValueError(
            "More than two players are in this combat - resolve it with God-Mode."
        )
    defender = others[0]

    new_state = state.clone()
    combat = ActiveCombat(
        kind=kind, position=active, planet=planet, attacker=attacker, defender=defender
    )
    new_state.active_combat = combat
    # Assault Cannon dopiero PO pozostałych zdolnościach startu walki (osobny etap niżej).
    triggers.fire(
        new_state, GameEvent.COMBAT, Moment.START, subject=attacker,
        ctx=_start_ctx(combat), hook_filter=lambda h: h.covers != ASSAULT_CANNON_COVERS,
    )
    # Decyzje graczy z hooków startu walki (np. Magen Defense Grid): walka czeka
    # w kroku TRIGGERS, aż wszyscy zdecydują (RULES.md 56); potem ``resume_after_triggers``.
    if new_state.pending_offers:
        combat.step = CombatStep.TRIGGERS
        combat.resume = "start"
        return new_state
    return _assault_cannon_stage(new_state, grid, registry)


# Zdolność Assault Cannon (``hooks/technologies_combat``) - osobny etap startu walki.
ASSAULT_CANNON_COVERS = "technologies:asc"
_RESUME_ASSAULT = "start_assault"  # po decyzjach Assault Cannon: reszta startu walki


def _start_ctx(combat: ActiveCombat) -> dict[str, Any]:
    return {
        "kind": combat.kind, "position": combat.position, "planet": combat.planet or "",
        "attacker": combat.attacker, "defender": combat.defender,
    }


def _assault_cannon_stage(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Assault Cannon po wszystkich innych zdolnościach startu walki (C_technology
    assault-cannon 3.1): statki dołożone przez zdolności startu walki liczą się do wymogu, a
    każdy inny gracz miał okazję użyć swojej zdolności, zanim wlaściciel dostał Assault Cannon.

    ⚠️ ZAŁOŻENIE: „jedna zdolność każdego innego gracza” = okno ofert startu walki całe przed
    Assault Cannon (gracz może użyć kilku niezależnych zdolności).
    """
    combat = _combat(state)
    triggers.fire(
        state, GameEvent.COMBAT, Moment.START, subject=combat.attacker,
        ctx=_start_ctx(combat), hook_filter=lambda h: h.covers == ASSAULT_CANNON_COVERS,
    )
    if state.pending_offers:
        combat.step = CombatStep.TRIGGERS
        combat.resume = _RESUME_ASSAULT
        return state
    return _after_start(state, grid, registry)


def _after_start(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Dalszy ciąg startu walki po hookach: koniec, gdy strona straciła jednostki, AFB, runda."""
    combat = _combat(state)
    attacker, defender = combat.attacker, combat.defender
    # Hooki startu walki mogą zniszczyć ostatnie jednostki strony - walka kończy się od razu
    # (C_technology: strona przegrywa natychmiast).
    if any(not side_units(state, grid, registry, pid) for pid in (attacker, defender)):
        return _after_losses(state, grid, registry)
    if any(n > 0 for n in combat.start_hits.values()):
        return _open_start_assign(state, grid, registry)
    # Entropic Scar: AFB (także nadany komponentem) nie działa przeciw jednostkom w bliźnie.
    has_afb = combat.kind == "space" and not entropic_scar.unit_abilities_blocked(
        state, combat.position, registry
    ) and (
        bool(combat.afb_extra)
        or any(
            u.afb_hits_on is not None
            for pid in (attacker, defender)
            for u in side_units(state, grid, registry, pid)
        )
    )
    if has_afb:
        combat.step = CombatStep.AFB
        return state
    return _begin_round(state, grid)


def add_start_hits(
    state: GameState,
    against: str,
    amount: int,
    *,
    only: list[str] | None = None,
    damaged: bool | None = None,
    chooser: str = "",
    label: str = "",
) -> None:
    """Trafienia z rzutu „na starcie walki” przeciw ``against`` (Ambush) — MUTUJE ``state``.

    Przypisuje je przeciwnik w zwykłym kroku ASSIGN (Sustain Damage, karty reakcji), zanim walka
    przejdzie do AFB i 1. rundy (``_open_start_assign``, RULES.md 62.8). ``only`` = typy jednostek,
    na które te trafienia MUSZĄ paść (Impulse Core: nie-myśliwce „if able”, RULES.md 62.10);
    ``damaged`` + ``chooser`` = konkretną jednostkę wskazał ``chooser`` (Magen Defense Grid Ω:
    właściciel technologii, C_technology) - ``against`` decyduje już tylko o jej Sustain Damage.
    """
    combat = _combat(state)
    if amount > 0:
        total = combat.start_hits.get(against, 0) + amount
        combat.start_hits = {**combat.start_hits, against: total}
        if only:
            _add_hit_target(
                combat, against, only, amount, label, damaged=damaged, chooser=chooser
            )


def add_round_end_hits(
    state: GameState,
    against: str,
    amount: int,
    *,
    only: list[str],
    damaged: bool | None = None,
    chooser: str = "",
    label: str = "",
) -> None:
    """Trafienia „po rundzie walki” przeciw ``against`` (Devotion) — MUTUJE ``state``.

    Cel wskazuje ``chooser`` (Devotion: Yin wybiera KONKRETNY statek - F_yin): typ ``only``
    i stan ``damaged`` (``True`` = uszkodzony egzemplarz, ``False`` = nieuszkodzony). ``against``
    w kroku ASSIGN decyduje już tylko, czy ten statek użyje Sustain Damage (albo zagrywa
    Shields Holding). Potem runda kończy się bez ponownych zdarzeń końca rundy (RULES.md 62.10).
    """
    combat = _combat(state)
    if amount <= 0:
        return
    combat.round_end_hits = {
        **combat.round_end_hits, against: combat.round_end_hits.get(against, 0) + amount
    }
    _add_hit_target(combat, against, only, amount, label, damaged=damaged, chooser=chooser)


def _add_hit_target(
    combat: ActiveCombat,
    against: str,
    types: list[str],
    amount: int,
    label: str,
    *,
    damaged: bool | None = None,
    chooser: str = "",
) -> None:
    current = combat.hit_targets.get(against)
    count = amount + (int(current["count"]) if current else 0)
    merged = sorted(set(types) | set(current["types"] if current else []))
    target: dict[str, Any] = {"types": merged, "count": count, "label": label or "this effect"}
    # Stan uszkodzenia ma sens tylko dla jednego, wskazanego statku (bez łączenia celów).
    if damaged is not None and current is None:
        target["damaged"] = damaged
    if chooser:
        target["chooser"] = chooser
    combat.hit_targets = {**combat.hit_targets, against: target}


def _check_hit_targets(
    combat: ActiveCombat,
    player_id: str,
    units: dict[str, CombatUnit],
    plan_parts: tuple[dict[str, int], dict[str, int], dict[str, int]],
    required: int,
) -> None:
    """Wymagany cel trafień (RULES.md 62.10): co najmniej ``count`` trafień na wskazane typy.

    „If able”: wymaganie obejmuje tyle trafień, ile jednostek tych typów może je przyjąć.
    """
    target = combat.hit_targets.get(player_id)
    if not target:
        return
    types = set(target["types"])
    damaged = target.get("damaged")
    if damaged is True and not any(u.damaged for bt, u in units.items() if bt in types):
        # Wskazany statek naprawiono przed przypisaniem (Duranium Armor w tym samym oknie końca
        # rundy) - to nadal ten statek, teraz nieuszkodzony.
        damaged = False
    sustain, destroy, destroy_damaged = plan_parts

    def _n(part: dict[str, int], bt: str) -> int:
        return max(0, part.get(bt, 0))

    if damaged is True:
        # Wskazany USZKODZONY statek: tylko zniszczenie uszkodzonego, który nie użył teraz
        # Sustain Damage (inne statki nie anulują tego trafienia - F_yin).
        able = sum(u.damaged for bt, u in units.items() if bt in types)
        landed = sum(max(0, _n(destroy_damaged, bt) - _n(sustain, bt)) for bt in types)
    elif damaged is False:
        # Wskazany NIEUSZKODZONY statek: jego Sustain Damage albo zniszczenie.
        able = sum(u.count - u.damaged for bt, u in units.items() if bt in types)
        landed = sum(_n(sustain, bt) + _n(destroy, bt) for bt in types)
    else:
        able = sum(u.count + (u.sustainable or 0) for bt, u in units.items() if bt in types)
        landed = sum(_n(part, bt) for part in (sustain, destroy, destroy_damaged) for bt in types)
    need = min(int(target["count"]), required, able)
    if need <= 0:
        return
    if landed < need:
        names = ", ".join(units[bt].name for bt in sorted(types) if bt in units)
        state_word = "damaged " if damaged is True else "undamaged " if damaged is False else ""
        raise ValueError(
            f"Assign {need} hit(s) from {target.get('label', 'this effect')} to the "
            f"{state_word}{names}."
        )


def _open_start_assign(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Okno przypisania trafień ze startu walki (MUTUJE ``state``); bez pokrycia - dalej start."""
    combat = _combat(state)
    combat.pending_hits = dict(combat.start_hits)
    combat.start_hits = {}
    combat.start_assign = True
    for pid in list(combat.pending_hits):
        if pid == NEUTRAL_PLAYER_ID:
            _auto_assign_neutral(state, grid, registry, pid)
    queue = [
        pid
        for pid in (combat.defender, combat.attacker)
        if required_hits(state, grid, registry, pid) > 0
    ]
    if not queue:
        combat.start_assign = False
        combat.pending_hits = {}
        return _after_start(state, grid, registry)
    combat.step = CombatStep.ASSIGN
    return timing.open_window(
        state, WindowType.COMBAT_ASSIGN_HITS, queue, context={"position": combat.position}
    )


def resume_after_triggers(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Wznawia walkę zaparkowaną w kroku TRIGGERS, gdy nikt już nie musi decydować.

    Wołane po każdej odpowiedzi na ofertę. Gdy zostały oferty albo trwa okno czasowe - stan bez
    zmian. Zwraca stan z przywróconym krokiem i dalszym przebiegiem (RULES.md 56).
    """
    combat = state.active_combat
    if combat is None or combat.step is not CombatStep.TRIGGERS:
        return state
    if state.pending_offers or state.pending_window is not None:
        return state
    new_state = state.clone()
    combat = _combat(new_state)
    resume = combat.resume
    combat.resume = ""
    if resume.startswith("round_end:"):
        combat.step = CombatStep(resume.split(":", 1)[1])
        if combat.round_end_hits:
            return _open_round_end_assign(new_state, grid, registry)
        return _finish_round(new_state, grid, registry)
    if resume == "round_start":
        _open_round(new_state, grid)
        return new_state
    if resume == _RESUME_AFB:
        combat.step = CombatStep.AFB
        return _apply_afb(new_state, grid, registry)
    if resume == _RESUME_ASSIGN:
        return _open_assign(new_state, grid, registry)
    if resume == _RESUME_RETREAT:
        # Straty rundy przypisane: ponownie oceń krok Retreat (strona mogła stracić statki).
        combat.step = CombatStep.ASSIGN
        return _after_losses(new_state, grid, registry)
    combat.step = CombatStep.ROLL
    if resume == "start":
        return _assault_cannon_stage(new_state, grid, registry)
    return _after_start(new_state, grid, registry)


# ---------------------------------------------------------------------------- rzuty


def natural_extra_hits(
    state: GameState, player_id: str, kind: str, base_type: str, dice: list[int]
) -> int:
    """Dodatkowe trafienia z wyników kości PRZED modyfikatorami (``combat.natural_extra_hits``).

    Jedno miejsce dla rzutu i przerzutów (RULES.md 62.3, J.N.S. Hylarim: „each result of 9 or 10,
    before applying modifiers, produces 2 additional hits"). Bez mnożnika trafień (X-89).
    """
    if not rules_hooks.hooks_at(rules_hooks.POINT_COMBAT_NATURAL_EXTRA_HITS, state, player_id):
        return 0
    return sum(
        rules_hooks.modify(
            rules_hooks.POINT_COMBAT_NATURAL_EXTRA_HITS, state, player_id, 0,
            {"kind": kind, "base_type": base_type, "natural": int(d)},
        )
        for d in dice
    )


def _roll_entry(
    unit: CombatUnit, dice: list[int], hits_on: int, hits: int, *, modifier: int | None = None
) -> dict[str, Any]:
    """Wpis rzutu do dziennika; ``modifier`` domyślnie modyfikator combat jednostki."""
    return {
        "baseType": unit.base_type,
        "name": unit.name,
        "hitsOn": hits_on,
        "modifier": unit.modifier if modifier is None else modifier,
        "dice": dice,
        "hits": hits,
    }


def _remove_units(
    state: GameState, combat: ActiveCombat, player_id: str, base_type: str, count: int
) -> None:
    """Zdejmuje ``count`` jednostek gracza z miejsca walki (mutuje ``state``)."""
    remove_units_in_zone(
        state, combat.position, _zone(combat.kind, combat.planet), player_id, base_type, count
    )


def note_destroyed(
    combat: ActiveCombat, player_id: str, base_type: str, count: int, hits_on: int
) -> None:
    """Zapisuje w walce ślad zniszczonych statków (karta Courageous to the End, RULES.md 53.5.c)."""
    if combat.kind != "space":  # w walce kosmicznej walczą tylko statki (także Z-Grav)
        return
    combat.destroyed_ships = [
        *combat.destroyed_ships,
        *({"player": player_id, "base_type": base_type, "hits_on": hits_on},) * count,
    ]


def remove_units_in_zone(
    state: GameState, position: str, zone: str, player_id: str, base_type: str, count: int
) -> None:
    """Zdejmuje ``count`` jednostek gracza ze strefy (``"space"``/planeta) — mutuje ``state``."""
    unit_ops.remove_units(
        state, state.systems[position], zone, player_id, base_type, count, UnitCause.DESTROYED
    )


def resolve_afb(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Anti-Fighter Barrage obu stron jednocześnie (W4): trafienia niszczą myśliwce przeciwnika."""
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    timing.require_no_limit_window(state)  # nadwyżka puli floty najpierw (RULES.md 42.1)
    combat = _combat(state)
    if combat.step is not CombatStep.AFB:
        raise ValueError("Anti-Fighter Barrage is not the current combat step.")
    new_state = state
    afb: dict[str, list[dict[str, Any]]] = {}
    hits_by: dict[str, int] = {}
    for pid in (combat.attacker, combat.defender):
        entries: list[dict[str, Any]] = []
        total = 0
        afb_units = [u for u in side_units(new_state, grid, registry, pid) if u.afb_hits_on]
        bonus = afb_extra_by_type(new_state, pid, afb_units)
        for unit in afb_units:
            assert unit.afb_hits_on is not None
            extra = bonus.get(unit.base_type, 0)
            new_state, dice = roll_dice(new_state, unit.count * unit.afb_dice + extra)
            hits = count_hits(dice, unit.afb_hits_on)
            total += hits
            # Modyfikatory combat (Fragile) nie dotyczą AFB (F_jol_nar): przerzut liczy bez nich.
            entry = _roll_entry(unit, dice, unit.afb_hits_on, hits, modifier=0)
            if extra:
                entry["extraDice"] = extra
            entries.append(entry)
        if pid in combat.afb_extra:
            # AFB nadany komponentem (Metali Void Armaments): gracz zgodził się go użyć w ofercie
            # na starcie walki; hook podaje próg i liczbę kości.
            grants = rules_hooks.forbidden(rules_hooks.POINT_COMBAT_AFB_GRANTED, state, pid)
            for grant in sorted(grants):
                grant_hits_on, grant_dice = (int(x) for x in grant.split(":"))
                new_state, dice = roll_dice(new_state, grant_dice)
                hits = count_hits(dice, grant_hits_on)
                total += hits
                entries.append(
                    {"baseType": "relic", "name": "Anti-Fighter Barrage (relic)",
                     "hitsOn": grant_hits_on, "modifier": 0, "dice": dice, "hits": hits}
                )
        afb[pid] = entries
        hits_by[pid] = total

    new_state = new_state.clone()
    combat = _combat(new_state)
    combat.afb = afb
    for pid, entries in afb.items():
        if entries:
            triggers.fire(
                new_state, GameEvent.UNIT_ABILITY_USED, Moment.AFTER, subject=pid,
                ctx={"ability": "afb", "player": pid, "hits": hits_by[pid]},
            )
    if new_state.pending_offers:
        # Decyzje „po rzucie AFB" (Agnlan Oln: przerzut, RULES.md 62.3): skutki po odpowiedziach.
        combat.step = CombatStep.TRIGGERS
        combat.resume = _RESUME_AFB
        return new_state
    return _apply_afb(new_state, grid, registry)


def afb_extra_sources(state: GameState, player_id: str) -> list[extra_dice.ExtraDie]:
    """Źródła dodatkowych kości AFB gracza (commander Argent, Strike Wing Ambuscade)."""
    return extra_dice.sources(state, player_id, rules_hooks.POINT_COMBAT_AFB_EXTRA_DICE)


def afb_extra_by_type(
    state: GameState, player_id: str, units: list[CombatUnit]
) -> dict[str, int]:
    """Dodatkowe kości AFB ``{base_type: kości}`` - każde źródło osobno, wg wyboru gracza
    (``ActiveCombat.afb_picks``); bez wyboru „auto” = najcelniejsza grupa (decyzja użytkownika
    2026-11-18, RULES.md 62.11)."""
    sources = afb_extra_sources(state, player_id)
    groups = {u.base_type: u.afb_hits_on or 99 for u in units if u.afb_hits_on}
    if not sources or not groups:
        return {}
    combat = state.active_combat
    chosen = dict(combat.afb_picks.get(player_id, {})) if combat is not None else {}
    picks = {
        e.key: chosen.get(e.key) or extra_dice.AUTO for e in sources
    }
    picks = {k: (v if v in groups or v == "none" else extra_dice.AUTO) for k, v in picks.items()}
    return extra_dice.assign(sources, groups, picks)


def set_afb_picks(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player_id: str,
    picks: dict[str, str],
) -> GameState:
    """Gracz przypisuje dodatkowe kości AFB do grup przed rzutem (``auto`` / ``none`` / typ).

    Raises:
        ValueError: Poza krokiem AFB, gracz nie walczy, nieznane źródło albo grupa bez AFB.
    """
    combat = _combat(state)
    if combat.step is not CombatStep.AFB or player_id not in (combat.attacker, combat.defender):
        raise ValueError("Extra dice can be assigned only before your Anti-Fighter Barrage.")
    units = [u for u in side_units(state, grid, registry, player_id) if u.afb_hits_on]
    groups = {u.base_type for u in units}
    sources = {e.key for e in afb_extra_sources(state, player_id)}
    for source, target in picks.items():
        if source not in sources:
            raise ValueError(f"No extra die from {source}.")
        if target not in groups and target not in (extra_dice.AUTO, "none"):
            raise ValueError("Choose one of your units with Anti-Fighter Barrage.")
    new_state = state.clone()
    _combat(new_state).afb_picks[player_id] = dict(picks)
    return new_state


_AFB_INFANTRY = "afb_infantry"  # ślad: piechota zniszczona przez wyniki AFB
AFB_RAID = "raid_formation"  # zdolność „trafienia AFB ponad myśliwce uszkadzają statki”


def _afb_infantry_kills(state: GameState, player_id: str, entries: list[dict[str, Any]]) -> int:
    """Ile piechoty przeciwnika niszczą wyniki AFB gracza (hook ``combat.afb_infantry_kill``:
    Strike Wing Alpha II - „each result of 9 or 10”). Liczy końcowe kości (po przerzutach)."""
    rules: dict[str, int] = {}
    for item in rules_hooks.forbidden(rules_hooks.POINT_COMBAT_AFB_INFANTRY_KILL, state, player_id):
        base_type, _, lowest = item.partition(":")
        rules[base_type] = int(lowest)
    kills = 0
    for entry in entries:
        need = rules.get(str(entry.get("baseType")))
        if need is not None:
            kills += sum(1 for d in entry.get("dice") or [] if int(d) >= need)
    return kills


def _destroy_space_infantry(
    state: GameState, registry: StaticDataRegistry, combat: ActiveCombat, roller: str,
    victim: str, kills: int,
) -> int:
    """Strike Wing Alpha II: niszczy piechotę ``victim`` w PRZESTRZENI aktywnego systemu na końcu
    kroku rzutu AFB (przed Sustain Damage i przypisaniem; anulowanie trafień tego nie cofa -
    F_argent). Ostatnie siły naziemne gracza spełniającego resztę warunków = natychmiastowa
    eliminacja (F_argent, R_elimination). Zwraca liczbę zniszczonych."""
    system = state.systems.get(combat.position)
    infantry = _units_map(system, "space", victim).get("infantry", 0)
    destroyed = min(kills, infantry)
    if destroyed <= 0:
        return 0
    _remove_units(state, combat, victim, "infantry", destroyed)
    ability_notes.note_point(
        state, roller, rules_hooks.POINT_COMBAT_AFB_INFANTRY_KILL,
        f"destroyed {destroyed} infantry",
    )
    from src.core import elimination  # lokalnie: elimination importuje moduły z triggerami

    if elimination.meets_conditions(state, registry, victim):
        elimination.eliminate(state, registry, victim)
        combat.effects.append({"kind": "eliminated", "player": victim, "by": roller})
    return destroyed


def raid_targets(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, victim: str
) -> tuple[dict[str, int], dict[str, int]]:
    """Statki ``victim`` z WŁASNYM Sustain Damage: ``(nieuszkodzone, uszkodzone)`` po typach.

    Sustain Damage nadany komponentem (Metali Void Shielding) się nie liczy (C_relics)."""
    fresh: dict[str, int] = {}
    hurt: dict[str, int] = {}
    for unit in side_units(state, grid, registry, victim):
        if not unit.sustain or not is_space_unit(unit.base_type):
            continue
        if unit.count - unit.damaged > 0:
            fresh[unit.base_type] = unit.count - unit.damaged
        if unit.damaged > 0:
            hurt[unit.base_type] = unit.damaged
    return fresh, hurt


def raid_damage(state: GameState, victim: str, ships: dict[str, int]) -> None:
    """Uszkadza wskazane statki ``victim`` w walce (Raid Formation, MUTUJE). Uszkodzenie nie jest
    użyciem Sustain Damage: bez okien Direct Hit / Reflective Shielding (F_argent)."""
    combat = _combat(state)
    system = state.systems[combat.position]
    for base_type, count in ships.items():
        now = damaged_count(system, "space", victim, base_type)
        set_damaged(system, "space", victim, base_type, now + count)


def _raid_formation(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, hits_by: dict[str, int]
) -> bool:
    """Raid Formation (RULES.md 62.11): trafienia AFB ponad myśliwce przeciwnika uszkadzają jego
    statki z Sustain Damage. Wybór jest prawdziwy tylko, gdy nieuszkodzonych celów jest więcej
    niż nadwyżki - wtedy decyzja gracza (``FACTION_ABILITY_USED``) i ``True`` (pauza).

    Liczone przy wyprodukowaniu trafień (po przerzutach, przed przypisaniem i przed zniszczeniem
    myśliwców); Waylay nie zmienia nadwyżki (F_argent)."""
    combat = _combat(state)
    for pid, opponent in ((combat.attacker, combat.defender), (combat.defender, combat.attacker)):
        if any(e.get("kind") == AFB_RAID and e.get("player") == pid for e in combat.effects):
            continue  # już rozstrzygnięte (także wznowienie po decyzji)
        if not rules_hooks.permits(rules_hooks.POINT_COMBAT_AFB_RAID, state, pid):
            continue
        fighters = _units_map(state.systems.get(combat.position), "space", opponent).get(
            _FIGHTER, 0
        )
        excess = hits_by.get(pid, 0) - fighters
        fresh, hurt = raid_targets(state, grid, registry, opponent)
        count = min(max(excess, 0), sum(fresh.values()) + sum(hurt.values()))
        entry: dict[str, Any] = {"kind": AFB_RAID, "player": pid, "target": opponent,
                                 "count": count}
        combat.effects.append(entry)
        if count <= 0:
            continue
        if sum(fresh.values()) <= count:
            raid_damage(state, opponent, fresh)  # każdy cel i tak zostaje uszkodzony
            entry["damaged"] = dict(fresh)
            if fresh:
                ability_notes.note_point(state, pid, rules_hooks.POINT_COMBAT_AFB_RAID,
                                         f"{sum(fresh.values())} ship(s) damaged")
            continue
        entry["pending"] = True
        from src.core import faction_components  # lokalnie: unika cyklu przy ładowaniu

        faction_components.ability_used(state, pid, AFB_RAID, opponent)
        if state.pending_offers:
            return True
    return False


_RESUME_AFB = "afb_apply"
_RESUME_ASSIGN = "assign"  # po ofertach „po rzucie”: otwórz przypisanie strat
_RESUME_RETREAT = "retreat"  # po decyzjach ze strat (Brother Milor): krok Retreat albo koniec rundy


def _apply_afb(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Skutki rzutów AFB zapisanych w ``combat.afb`` (MUTUJE ``state`` - klon wołającego)."""
    new_state = state
    combat = _combat(new_state)
    afb = combat.afb
    hits_by = {
        pid: sum(int(e.get("hits", 0)) for e in afb.get(pid, []))
        for pid in (combat.attacker, combat.defender)
    }
    losses: dict[str, dict[str, int]] = {}
    waylay_hits: dict[str, int] = {}  # trafienia przeciw WSZYSTKIM statkom (karta Waylay)
    fighter_hits: dict[str, int] = {}  # zwykłe trafienia AFB - tylko myśliwce
    zone = _zone(combat.kind, combat.planet)
    if not any(e.get("kind") == _AFB_INFANTRY for e in combat.effects):
        # Strike Wing Alpha II: koniec kroku rzutu - piechota ginie przed przypisaniem (F_argent).
        killed: dict[str, int] = {}
        for pid, opponent in (
            (combat.attacker, combat.defender), (combat.defender, combat.attacker)
        ):
            kills = _afb_infantry_kills(new_state, pid, afb.get(pid, []))
            if kills and opponent in new_state.players:
                gone = _destroy_space_infantry(new_state, registry, combat, pid, opponent, kills)
                if gone:
                    killed[opponent] = gone
        combat.effects.append({"kind": _AFB_INFANTRY, "killed": killed})
    if _raid_formation(new_state, grid, registry, hits_by):
        combat.step = CombatStep.TRIGGERS
        combat.resume = _RESUME_AFB
        return new_state
    raid: dict[str, dict[str, int]] = {}
    for entry in combat.effects:
        if entry.get("kind") == _AFB_INFANTRY:
            for victim, n in dict(entry.get("killed") or {}).items():
                losses.setdefault(str(victim), {})["infantry"] = int(n)
        if entry.get("kind") == AFB_RAID and entry.get("damaged"):
            raid[str(entry["target"])] = {str(k): int(v) for k, v in entry["damaged"].items()}
    for pid, opponent in (
        (combat.attacker, combat.defender),
        (combat.defender, combat.attacker),
    ):
        if hits_by[pid] > 0 and rules_hooks.permits(
            rules_hooks.POINT_COMBAT_AFB_ALL_SHIPS, new_state, pid
        ):
            waylay_hits[opponent] = hits_by[pid]
            continue
        fighters = _units_map(new_state.systems.get(combat.position), zone, opponent).get(
            _FIGHTER, 0
        )
        landed = min(hits_by[pid], fighters)  # nadwyżka przepada (W4)
        if landed:
            # Trafienia AFB przypisuje właściciel myśliwców w kroku ASSIGN (wybór + „Auto”),
            # więc przed przypisaniem można je anulować (Shields Holding, Tellurian - 62.18).
            fighter_hits[opponent] = landed
    log_entry: dict[str, Any] = {
        "round": combat.round, "phase": "AFB", "rolls": afb, "hits": hits_by,
        "losses": losses, "sustained": {},
    }
    if raid:
        log_entry["raidDamaged"] = raid  # Raid Formation: statki uszkodzone (nie Sustain Damage)
    combat.log.append(log_entry)
    if waylay_hits or fighter_hits:
        # Przeciwnik sam przypisuje trafienia AFB w kroku ASSIGN: Waylay - dowolne statki
        # (Sustain Damage), zwykłe AFB - tylko myśliwce (wymagany cel ``hit_targets``). Po nim
        # ``_after_losses`` kończy krok AFB (``afb_assign``).
        combat.afb_assign = True
        combat.pending_hits = {**fighter_hits, **waylay_hits}
        for opponent, landed in fighter_hits.items():
            combat.hit_targets[opponent] = {
                "types": [_FIGHTER], "count": landed, "label": "Anti-Fighter Barrage",
            }
        for pid in combat.pending_hits:
            if pid == NEUTRAL_PLAYER_ID:
                _auto_assign_neutral(new_state, grid, registry, pid)
        queue = [
            pid
            for pid in (combat.defender, combat.attacker)
            if required_hits(new_state, grid, registry, pid) > 0
        ]
        if queue:
            combat.step = CombatStep.ASSIGN
            return timing.open_window(
                new_state,
                WindowType.COMBAT_ASSIGN_HITS,
                queue,
                context={"position": combat.position},
            )
        combat.afb_assign = False
        combat.pending_hits = {}
    return _after_losses(new_state, grid, registry)


def _reroll_misses(
    state: GameState, unit: CombatUnit, dice: list[int]
) -> tuple[GameState, list[int]]:
    """Przerzuca chybienia raz (hook ``combat.reroll_misses``); trafienia zostają bez zmian."""
    misses = [i for i, d in enumerate(dice) if d + unit.modifier < unit.base_hits_on]
    if not misses:
        return state, dice
    new_state, again = roll_dice(state, len(misses))
    result = list(dice)
    for index, value in zip(misses, again, strict=True):
        result[index] = value
    return new_state, result


def roll_round(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    side: str | None = None,
) -> GameState:
    """Rzuty combat i otwarcie przypisania strat.

    ``side=None`` rzuca za wszystkie strony, które jeszcze nie rzuciły (atakujący pierwszy — W5).
    ``side=<gracz>`` rzuca TYLKO za tę stronę (każdy gracz klika swój rzut, nie muszą jednocześnie):
    wynik czeka w ``combat.side_rolls``, a gdy rzuciły obie strony, runda idzie dalej
    (trafienia dodatkowe, przypisanie strat) tak samo jak przy rzucie za obie naraz.
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    timing.require_no_limit_window(state)  # nadwyżka puli floty najpierw (RULES.md 42.1)
    combat = _combat(state)
    if combat.step is not CombatStep.ROLL:
        raise ValueError("Combat dice are not the current combat step.")
    sides = (combat.attacker, combat.defender)
    if side is not None:
        if side not in sides:
            raise ValueError("That player is not a side of this combat.")
        if side in combat.side_rolls:
            raise ValueError("This side has already rolled its combat dice this round.")
    if any(not side_units(state, grid, registry, pid) for pid in sides):
        # Strona straciła ostatnie jednostki przed rzutem (Indoctrination, Greyfire Mutagen):
        # przegrywa natychmiast, bez rzutów (F_yin, RULES.md 62.10).
        return _finish_round(state.clone(), grid, registry)
    new_state = state
    rolls: dict[str, list[dict[str, Any]]] = {}
    hits_by: dict[str, int] = {}
    for pid in sides:
        # Neutralni nie mają kto kliknąć: rzucają razem z drugą stroną.
        if pid in combat.side_rolls or (
            side is not None and pid != side and pid != NEUTRAL_PLAYER_ID
        ):
            continue
        entries: list[dict[str, Any]] = []
        total = 0
        for unit in side_units(new_state, grid, registry, pid):
            new_state, dice = roll_dice(new_state, unit.total_dice)
            if rules_hooks.permits(
                rules_hooks.POINT_COMBAT_REROLL_MISSES, state, pid, {"base_type": unit.base_type}
            ):
                new_state, dice = _reroll_misses(new_state, unit, dice)
            # Gravleash: +X tylko do kości pierwszego egzemplarza (RULES.md 62.2).
            bonus = [
                unit.single_bonus if i < unit.dice_per_unit else 0 for i in range(len(dice))
            ]
            hits = sum(
                1 for d, b in zip(dice, bonus, strict=False)
                if d + unit.modifier + b >= unit.base_hits_on
            )
            # Hook MODIFY: mnożnik trafień (X-89 ΩΩ: ×2 w walce naziemnej, nie w kosmicznej).
            hits *= rules_hooks.modify(
                rules_hooks.POINT_COMBAT_HIT_MULTIPLIER, state, pid, 1,
                {"kind": combat.kind, "base_type": unit.base_type},
            )
            hits += natural_extra_hits(state, pid, combat.kind, unit.base_type, dice)
            total += hits
            entry = _roll_entry(unit, dice, unit.base_hits_on, hits)
            if unit.single_bonus:
                entry["bonus"] = bonus
            entries.append(entry)
        rolls[pid] = entries
        hits_by[pid] = total
    # Strona, która rzuciła wcześniej, wraca z ``side_rolls`` (trafienia = suma wpisów rzutu).
    rolls = {pid: rolls.get(pid) or combat.side_rolls.get(pid, []) for pid in sides
             if pid in rolls or pid in combat.side_rolls}
    for pid in combat.side_rolls:
        hits_by.setdefault(pid, sum(int(e.get("hits") or 0) for e in combat.side_rolls[pid]))
    if len(rolls) < len(sides):
        # Rzuciła dopiero jedna strona: wynik czeka na drugą, runda stoi w kroku ROLL.
        waiting = new_state.clone()
        _combat(waiting).side_rolls = rolls
        return waiting
    extra_by = _extra_hits(state, combat, hits_by)
    for pid, extra in extra_by.items():
        hits_by[pid] += extra

    early = list(combat.side_rolls)  # strony, które rzuciły wcześniej osobno
    new_state = new_state.clone()
    combat = _combat(new_state)
    combat.side_rolls = {}
    combat.destroyed_ships = []  # ślady kart reakcji dotyczą ostatnich strat
    combat.sustained_ships = []
    combat.stepwise_assign = []
    offers_before = len(new_state.pending_offers)
    for pid in rolls:
        triggers.fire(
            new_state, GameEvent.COMBAT_ROLL, Moment.AFTER, subject=pid,
            ctx={"kind": "combat", "player": pid, "hits": hits_by[pid]},
        )
    combat.rolls = rolls
    combat.pending_hits = {
        combat.defender: hits_by[combat.attacker],
        combat.attacker: hits_by[combat.defender],
    }
    combat.log.append(
        {
            "round": combat.round,
            "phase": "COMBAT",
            "rolls": rolls,
            "early": early,
            "hits": hits_by,
            "extra": extra_by,
            "losses": {},
            "sustained": {},
        }
    )
    for pid in (combat.defender, combat.attacker):
        if pid == NEUTRAL_PLAYER_ID:
            _auto_assign_neutral(new_state, grid, registry, pid)
    # Oferty „po rzucie” (Wrath of Kenara) zmieniają kości PRZED przypisaniem strat: walka czeka
    # w TRIGGERS, a przypisanie otwiera ``resume_after_triggers`` (RULES.md 56, 62.6).
    if len(new_state.pending_offers) > offers_before:
        combat.step = CombatStep.TRIGGERS
        combat.resume = _RESUME_ASSIGN
        return new_state
    return _open_assign(new_state, grid, registry)


def _extra_hits(
    state: GameState, combat: ActiveCombat, dice_hits: dict[str, int]
) -> dict[str, int]:
    """Hook MODIFY: dodatkowe trafienia po rzutach OBU stron (Valkyrie Particle Weave, RULES 62.1).

    ``dice_hits`` = trafienia z kości każdej strony. Liczone przy rzucie i od nowa po każdej zmianie
    kości przed przypisaniem strat (przerzut, premia) - trafienie VPW nie przepada przy przerzucie.
    """
    opponent_of = {combat.attacker: combat.defender, combat.defender: combat.attacker}
    return {
        pid: rules_hooks.modify(
            rules_hooks.POINT_COMBAT_EXTRA_HITS, state, pid, 0,
            {
                "kind": combat.kind,
                "own_hits": dice_hits[pid],
                "opponent_hits": dice_hits.get(opponent_of[pid], 0),
            },
        )
        for pid in dice_hits
    }


def _direct_hits_to_non_fighters(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, combat: ActiveCombat
) -> None:
    """Hook FORBID ``combat.hits_to_non_fighters`` ([0.0.1], RULES.md 62.12) - MUTUJE klon.

    Trafienia z rzutów wskazanych grup (końcowe kości rundy, po przerzutach) stają się wymaganym
    celem przypisania: statki przeciwnika poza myśliwcami, „if able” (``_check_hit_targets``).
    """
    if combat.kind != "space":
        return
    opponent_of = {combat.attacker: combat.defender, combat.defender: combat.attacker}
    for pid, entries in combat.rolls.items():
        types = rules_hooks.forbidden(
            rules_hooks.POINT_COMBAT_HITS_TO_NON_FIGHTERS, state, pid,
            {"position": combat.position},
        )
        if not types:
            continue
        hits = sum(int(e.get("hits") or 0) for e in entries if e.get("baseType") in types)
        victim = opponent_of.get(pid)
        if hits <= 0 or victim is None:
            continue
        targets = [
            u.base_type for u in side_units(state, grid, registry, victim)
            if u.base_type != "fighter"
        ]
        if targets:
            # Etykieta = pełne nazwy rzucających grup z danych (np. „[0.0.1]”).
            names = sorted({str(e.get("name")) for e in entries if e.get("baseType") in types})
            _add_hit_target(combat, victim, targets, hits, " / ".join(names))


def _open_assign(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Okno przypisania strat po rzutach rundy (albo koniec rundy, gdy nikt nie ma trafień)."""
    combat = _combat(state)
    _direct_hits_to_non_fighters(state, grid, registry, combat)
    queue = [
        pid
        for pid in (combat.defender, combat.attacker)
        if required_hits(state, grid, registry, pid) > 0
    ]
    if not queue:
        return _after_losses(state, grid, registry)
    combat.step = CombatStep.ASSIGN
    return timing.open_window(
        state,
        WindowType.COMBAT_ASSIGN_HITS,
        queue,
        context={"position": combat.position},
    )


# -------------------------------------------------------------------------- straty


def neutral_loss_choice(
    units: list[CombatUnit], costs: dict[str, float], hits: int
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """Straty jednostek neutralnych (R_neutral_units): każde trafienie w NAJTAŃSZĄ jednostkę.

    „When a hit is assigned against a group of neutral units, it is assigned to the unit that is
    lowest on the neutral unit reference card; generally ... the lowest cost." Neutralni zawsze
    używają każdej zdolności, więc Sustain Damage (jeśli jednostka go ma i jest nieuszkodzona)
    pochłania trafienie zamiast zniszczenia. Zwraca ``(sustain, destroy, destroy_damaged)``.
    """
    state = {u.base_type: [u.count, u.damaged, u.sustain] for u in units}
    sustain: dict[str, int] = {}
    destroy: dict[str, int] = {}
    destroy_damaged: dict[str, int] = {}
    for _ in range(hits):
        alive = [bt for bt, (count, _, _) in state.items() if count > 0]
        if not alive:
            break
        base_type = min(alive, key=lambda bt: (costs.get(bt, 0.0), bt))
        count, damaged, can_sustain = state[base_type]
        if can_sustain and count - damaged > 0:
            sustain[base_type] = sustain.get(base_type, 0) + 1
            state[base_type][1] = damaged + 1
        elif damaged > 0:
            destroy_damaged[base_type] = destroy_damaged.get(base_type, 0) + 1
            state[base_type][0] = count - 1
            state[base_type][1] = damaged - 1
        else:
            destroy[base_type] = destroy.get(base_type, 0) + 1
            state[base_type][0] = count - 1
    return sustain, destroy, destroy_damaged


def _auto_assign_neutral(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player_id: str
) -> None:
    """Przypisuje straty neutralnych automatycznie (nikt ich nie wybiera) — MUTUJE ``state``."""
    combat = _combat(state)
    required = required_hits(state, grid, registry, player_id)
    if required <= 0:
        combat.pending_hits[player_id] = 0
        return
    units = side_units(state, grid, registry, player_id)
    costs = {
        u.base_type: (registry.units[u.unit_id].cost or 0.0)
        for u in units
        if u.unit_id in registry.units
    }
    sustain, destroy, destroy_damaged = neutral_loss_choice(units, costs, required)
    by_type = {u.base_type: u for u in units}
    plan = plan_losses(
        by_type, sustain, destroy, destroy_damaged, required, sustain_cancels(state, player_id)
    )
    apply_losses(
        state, combat.position, _zone(combat.kind, combat.planet), player_id, by_type, plan
    )
    entry = combat.log[-1] if combat.log else None
    if entry is not None:
        entry["losses"][player_id] = losses_of(by_type, plan)
        entry["sustained"][player_id] = sustained_of(plan, sustain)
    combat.pending_hits[player_id] = 0


def plan_losses(
    units: dict[str, CombatUnit],
    sustain: dict[str, int],
    destroy: dict[str, int],
    destroy_damaged: dict[str, int],
    required: int,
    cancels: int = 1,
) -> dict[str, tuple[int, int]]:
    """Waliduje pokrycie trafień (W7/W8) i zwraca plan ``{base_type: (nowa liczba, uszkodzone)}``.

    ``cancels`` = ile trafień anuluje jedno użycie Sustain Damage (``sustain_cancels``). Przy
    ``cancels > 1`` ostatnie użycie może anulować mniej tylko wtedy, gdy zostało mniej trafień -
    czyli bez niszczenia jednostek: zniszczenie + Sustain anulujący 1 to „anulowanie tylko jednego”
    przy kilku trafieniach (F_letnev/noneuclidean-shielding/3).

    Współdzielone przez walkę, bombardowanie i Space Cannon Defense (RULES.md 40): w każdym
    przypadku właściciel jednostek sam wybiera straty, a Sustain Damage anuluje trafienie.

    Raises:
        ValueError: Zła liczba/typ, nadużycie Sustain Damage, suma różna od ``required``.
    """
    plan: dict[str, tuple[int, int]] = {}
    total = 0
    sustains_total = 0
    granted_used = 0  # Sustain Damage nadany komponentem: łącznie najwyżej 1 na przypisanie
    for base_type in set(sustain) | set(destroy) | set(destroy_damaged):
        s = max(0, sustain.get(base_type, 0))
        d = max(0, destroy.get(base_type, 0))
        dd = max(0, destroy_damaged.get(base_type, 0))
        if s + d + dd == 0:
            continue
        unit = units.get(base_type)
        if unit is None:
            raise ValueError(f"You have no {base_type} in this combat.")
        if s > unit.sustainable:
            raise ValueError(
                f"Only {unit.sustainable} {unit.name} can use Sustain Damage."
            )
        if not unit.sustain:
            granted_used += s
        damaged_after = unit.damaged + s
        undamaged_after = unit.count - damaged_after
        if d > undamaged_after or dd > damaged_after:
            raise ValueError(f"Not enough {unit.name} for these losses.")
        plan[base_type] = (unit.count - d - dd, damaged_after - dd)
        total += s * cancels + d + dd
        sustains_total = sustains_total + s
    if granted_used > 1:
        raise ValueError("Only 1 of your ships can use Sustain Damage granted by a relic.")
    destroyed = total - sustains_total * cancels
    if total != required and not (
        cancels > 1 and sustains_total > 0 and destroyed == 0
        and required < total < required + cancels
    ):
        raise ValueError(f"Cover exactly {required} hit(s).")
    return plan


def apply_losses(
    state: GameState,
    position: str,
    zone: str,
    player_id: str,
    units: dict[str, CombatUnit],
    plan: dict[str, tuple[int, int]],
) -> None:
    """Stosuje plan strat w strefie ``zone`` systemu ``position`` (MUTUJE ``state`` — klon)."""
    system = state.systems[position]
    for base_type, (count, damaged) in plan.items():
        unit_zone = units[base_type].zone or zone
        lost = units[base_type].count - count
        if lost:
            remove_units_in_zone(state, position, unit_zone, player_id, base_type, lost)
        set_damaged(system, unit_zone, player_id, base_type, damaged)


def losses_of(
    units: dict[str, CombatUnit], plan: dict[str, tuple[int, int]]
) -> dict[str, int]:
    """Ile sztuk każdego typu zginęło wg planu (do dziennika)."""
    return {bt: units[bt].count - c for bt, (c, _) in plan.items() if units[bt].count - c}


def sustained_of(plan: dict[str, tuple[int, int]], sustain: dict[str, int]) -> dict[str, int]:
    """Ile razy użyto Sustain Damage per typ (do dziennika)."""
    return {bt: max(0, sustain.get(bt, 0)) for bt in plan if sustain.get(bt, 0) > 0}


def assign_combat_hits(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    *,
    sustain: dict[str, int],
    destroy: dict[str, int],
    destroy_damaged: dict[str, int],
) -> GameState:
    """Gracz pokrywa trafienia: Sustain Damage, potem niszczenie (W7/W8).

    Semantyka: najpierw ``sustain`` (nieuszkodzone ze zdolnością stają się uszkodzone), potem
    ``destroy`` (nieuszkodzone) i ``destroy_damaged`` (uszkodzone — także te właśnie uszkodzone).
    Suma = ``required_hits``.

    Raises:
        ValueError: Zła kolejność w oknie, zła liczba/typ, nadużycie Sustain Damage.
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    timing.require_no_limit_window(state)  # nadwyżka puli floty najpierw (RULES.md 42.1)
    combat = _combat(state)
    window = state.pending_window
    if (
        combat.step is not CombatStep.ASSIGN
        or window is None
        or window.window_type is not WindowType.COMBAT_ASSIGN_HITS
    ):
        raise ValueError("There are no combat hits to assign right now.")
    if window.current_responder != player_id:
        raise ValueError(
            f"It is now {window.current_responder}'s turn to assign hits, not {player_id}."
        )

    units = {u.base_type: u for u in side_units(state, grid, registry, player_id)}
    required = required_hits(state, grid, registry, player_id)
    plan = plan_losses(
        units, sustain, destroy, destroy_damaged, required, sustain_cancels(state, player_id)
    )
    _check_hit_targets(combat, player_id, units, (sustain, destroy, destroy_damaged), required)

    new_state = state.clone()
    combat = _combat(new_state)
    combat.hit_targets = {p: t for p, t in combat.hit_targets.items() if p != player_id}
    zone = _zone(combat.kind, combat.planet)
    if player_id in combat.stepwise_assign:
        # Started with ``sustain_one``: "before you assign hits" already fired for these hits.
        combat.stepwise_assign = [p for p in combat.stepwise_assign if p != player_id]
    else:
        triggers.fire(
            new_state, GameEvent.HITS_ASSIGNED, Moment.BEFORE, subject=player_id,
            ctx={"player": player_id, "kind": combat.kind, "hits": required},
        )
    apply_losses(new_state, combat.position, zone, player_id, units, plan)
    for base_type, lost in losses_of(units, plan).items():
        note_destroyed(combat, player_id, base_type, lost, units[base_type].base_hits_on)
    _note_sustains(new_state, combat, player_id, units, zone, sustained_of(plan, sustain))

    entry = combat.log[-1] if combat.log else None
    if entry is not None:
        entry["losses"][player_id] = losses_of(units, plan)
        entry["sustained"][player_id] = _merged(
            entry["sustained"].get(player_id, {}), sustained_of(plan, sustain)
        )
    combat.pending_hits[player_id] = 0

    new_state = timing.respond_current(new_state, player_id)
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
        if _hold_for_sustain(new_state, registry, sustained_of(plan, sustain)):
            return new_state
        return _after_losses(new_state, grid, registry)
    return new_state


def _note_sustains(
    state: GameState,
    combat: ActiveCombat,
    player_id: str,
    units: dict[str, CombatUnit],
    zone: str,
    used_by_type: dict[str, int],
) -> None:
    """Records Sustain Damage uses for reaction cards (Direct Hit) and fires its AFTER event.

    MUTATES ``state`` (the caller's clone).
    """
    for base_type, used in used_by_type.items():
        # W walce kosmicznej walczą tylko statki; w naziemnej - tylko siła naziemna-statek
        # (Eidolon Maximum: Direct Hit działa też na niego, F_naaz_rokha eidolon-maximum 2.3).
        if used > 0 and (
            combat.kind == "space" or floating_structures.ground_moves_as_ship(
                state, player_id, base_type
            )
        ):
            where = units[base_type].zone or zone
            combat.sustained_ships = [
                *combat.sustained_ships,
                {"player": player_id, "base_type": base_type, "count": used,
                 **({"zone": where} if where != "space" else {})},
            ]
        if used > 0:
            triggers.fire(
                state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject=player_id,
                ctx={"player": player_id, "base_type": base_type, "count": used,
                     "position": combat.position, "zone": units[base_type].zone or zone},
            )


def _merged(old: dict[str, int], new: dict[str, int]) -> dict[str, int]:
    """Sums two ``{base_type: count}`` logs (step-by-step Sustain Damage + final assignment)."""
    return {bt: old.get(bt, 0) + new.get(bt, 0) for bt in {*old, *new}}


def sustain_one(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    base_type: str,
) -> GameState:
    """Step-by-step hit assignment: ONE ship uses SUSTAIN DAMAGE now; the other hits wait.

    C_action_cards/direct-hit/3: "When a player uses the Sustain Damage ability of one of their
    ships, they do not have to decide if another of their ships in the same combat will use its
    Sustain Damage ability until after their opponent has used or declined to use a Direct Hit."
    The assign window stays with this player: the reaction pause offers Direct Hit, then they
    sustain with another ship (again this function) or assign the rest (``assign_combat_hits``,
    which also confirms when nothing is left to cover).

    User decision (RULES.md 53.10): with an effect that directs hits to particular units
    (``hit_targets``) the hits are assigned in one go - no step-by-step Sustain Damage.

    Raises:
        ValueError: Not this player's assignment, no hits left, the ship cannot sustain, or the
            hits are directed by an effect.
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    timing.require_no_limit_window(state)  # nadwyżka puli floty najpierw (RULES.md 42.1)
    combat = _combat(state)
    window = state.pending_window
    if (
        combat.step is not CombatStep.ASSIGN
        or window is None
        or window.window_type is not WindowType.COMBAT_ASSIGN_HITS
    ):
        raise ValueError("There are no combat hits to assign right now.")
    if window.current_responder != player_id:
        raise ValueError(
            f"It is now {window.current_responder}'s turn to assign hits, not {player_id}."
        )
    if combat.hit_targets.get(player_id):
        raise ValueError("These hits must go to particular units - assign them all at once.")
    units = {u.base_type: u for u in side_units(state, grid, registry, player_id)}
    required = required_hits(state, grid, registry, player_id)
    if required <= 0:
        raise ValueError("There are no hits left to cover - confirm the assignment.")
    cancels = sustain_cancels(state, player_id)
    cancelled = min(cancels, required)
    plan = plan_losses(units, {base_type: 1}, {}, {}, cancelled, cancels)

    new_state = state.clone()
    combat = _combat(new_state)
    zone = _zone(combat.kind, combat.planet)
    if player_id not in combat.stepwise_assign:
        triggers.fire(
            new_state, GameEvent.HITS_ASSIGNED, Moment.BEFORE, subject=player_id,
            ctx={"player": player_id, "kind": combat.kind, "hits": required},
        )
        combat.stepwise_assign = [*combat.stepwise_assign, player_id]
    apply_losses(new_state, combat.position, zone, player_id, units, plan)
    _note_sustains(new_state, combat, player_id, units, zone, {base_type: 1})
    entry = combat.log[-1] if combat.log else None
    if entry is not None:
        entry["sustained"][player_id] = _merged(
            entry["sustained"].get(player_id, {}), {base_type: 1}
        )
    combat.pending_hits[player_id] = max(0, combat.pending_hits.get(player_id, 0) - cancelled)
    return new_state


def _hold_for_sustain(
    state: GameState, registry: StaticDataRegistry, used: dict[str, int]
) -> bool:
    """Ostatnia strona użyła Sustain Damage: walka czeka w kroku ASSIGN, jeśli ktoś może jeszcze
    odpowiedzieć (Direct Hit, Reflective Shielding - F_mentak ambush/4.1, C_action_cards).

    Bez tego okno „po Sustain Damage” ostatniej strony zamykało się w tym samym kroku (od razu
    AFB / runda / koniec walki). Pauzę otwiera ``reaction_pause.sync``; dalej prowadzi
    ``release_sustain_hold``. MUTUJE ``state`` (klon wołającego).
    """
    from src.core import reaction_pause  # lokalnie: reaction_pause -> reaction_cards -> hooki

    combat = _combat(state)
    if not any(n > 0 for n in used.values()) or (
        combat.kind != "space" and not combat.sustained_ships
    ):
        return False
    combat.sustain_hold = True
    if reaction_pause.would_open(state, registry):
        return True
    combat.sustain_hold = False
    return False


def release_sustain_hold(state: GameState, registry: StaticDataRegistry) -> GameState:
    """Walka wstrzymana po Sustain Damage idzie dalej, gdy pauza ochronna minęła (nowy stan).

    Wołane po każdym kroku (``step_settle``). Reflective Shielding w trakcie wstrzymania otwiera
    nowe przypisanie (``add_combat_hits``) - wtedy wstrzymania już nie ma.
    """
    from src.core.state_grid import grid_from_state  # lokalnie: unika cyklu importów

    combat = state.active_combat
    if (
        combat is None
        or not combat.sustain_hold
        or state.reaction_pause is not None
        or state.pending_window is not None
    ):
        return state
    new_state = state.clone()
    _combat(new_state).sustain_hold = False
    return _after_losses(new_state, grid_from_state(new_state, registry), registry)


def add_combat_hits(state: GameState, against: str, amount: int) -> None:
    """Dodatkowe trafienia przeciw ``against`` w bieżącym kroku przypisywania (MUTUJE ``state``).

    Punkt centralny dla efektów „produces 1 hit” po rzutach (mech Sardakk, RULES.md 62.1): trafienia
    dołączają do bieżącego kroku Roll Dice; gdy ``against`` już przypisał straty, wraca na koniec
    kolejki okna przypisywania. W wstrzymaniu po Sustain Damage (``sustain_hold``, Reflective
    Shielding) otwiera nowe okno przypisania dla ``against``.
    """
    combat = _combat(state)
    if amount <= 0 or combat.step is not CombatStep.ASSIGN:
        return
    combat.pending_hits[against] = combat.pending_hits.get(against, 0) + amount
    window = state.pending_window
    if window is None and combat.sustain_hold:
        combat.sustain_hold = False
        state.pending_window = timing.open_window(
            state, WindowType.COMBAT_ASSIGN_HITS, [against],
            context={"position": combat.position},
        ).pending_window
        return
    if window is None or window.window_type is not WindowType.COMBAT_ASSIGN_HITS:
        return
    if against not in window.queue[window.cursor:]:
        window.queue = [*window.queue, against]


def _after_losses(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Koniec rundy (W9): zwycięzca/remis albo kolejna runda (bez AFB)."""
    new_state = state.clone()
    combat = _combat(new_state)
    if combat.start_assign:
        # Straty z trafień startu walki (Ambush) przypisane - start walki biegnie dalej (AFB/runda),
        # bez zdarzeń końca rundy (to nie runda walki).
        combat.start_assign = False
        combat.pending_hits = {}
        combat.hit_targets = {}
        combat.step = CombatStep.ROLL
        return _after_start(new_state, grid, registry)
    if combat.round_end_assign:
        # Straty z trafień po rundzie (Devotion) przypisane - koniec rundy bez ponownych zdarzeń
        # końca rundy; decyzje z nich (np. agent Yin po zniszczeniu) czekają w TRIGGERS.
        combat.round_end_assign = False
        combat.pending_hits = {}
        combat.hit_targets = {}
        if new_state.pending_offers:
            combat.resume = f"round_end:{combat.step.value}"
            combat.step = CombatStep.TRIGGERS
            return new_state
        return _finish_round(new_state, grid, registry)
    # Wpis salwy tej rundy (po odwrocie ostatni jest wpis RETREAT - bez „sustained”).
    last: dict[str, Any] = next(
        (e for e in reversed(combat.log) if e.get("phase") != "RETREAT"), {}
    )
    is_roll_round = combat.step is not CombatStep.AFB and not combat.afb_assign
    if is_roll_round and _retreat_due(new_state, grid, registry):
        # Krok 5 (Retreat) idzie PRZED zdarzeniami „po rundzie walki” (R_space_combat; F_yin,
        # F_norr: po odwrocie Devotion/Exotrireme II nie trafią uciekiniera). Zdarzenia końca
        # rundy odpalą się raz - po odwrocie (``retreat_from_combat`` → ``_after_losses``).
        if new_state.pending_offers:
            # Decyzje ze strat tej rundy (np. Brother Milor) najpierw - odwrót czeka.
            combat.resume = _RESUME_RETREAT
            combat.step = CombatStep.TRIGGERS
            return new_state
        combat.step = CombatStep.RETREAT
        return new_state
    triggers.fire(
        new_state, GameEvent.COMBAT_ROUND, Moment.END,
        ctx={
            "kind": combat.kind, "round": combat.round, "position": combat.position,
            "planet": combat.planet or "", "attacker": combat.attacker,
            "defender": combat.defender,
            # „phase": runda rzutów (po przypisaniu strat) vs krok AFB; „sustained": kto ile razy
            # użył Sustain Damage w TEJ rundzie (Duranium Armor nie naprawia takich jednostek).
            "phase": "combat" if is_roll_round else "afb",
            "sustained": last.get("sustained", {}) if is_roll_round else {},
        },
    )
    # Decyzje graczy z hooków końca rundy (np. Duranium Armor): walka czeka w kroku TRIGGERS.
    if new_state.pending_offers:
        combat.resume = f"round_end:{combat.step.value}"
        combat.step = CombatStep.TRIGGERS
        return new_state
    return _finish_round(new_state, grid, registry)


def _retreat_due(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> bool:
    """Czy po przypisaniu strat rundy następuje krok Retreat (39.5 O3).

    Ogłoszony odwrót odbywa się, gdy obie strony mają jeszcze statki i jest dozwolony cel;
    inaczej walka kończy się (albo trwa) bez odwrotu - jak w ``_finish_round``.
    """
    combat = _combat(state)
    if not combat.retreating or combat.step is CombatStep.RETREAT:
        return False
    sides = (combat.attacker, combat.defender)
    if any(not side_units(state, grid, registry, pid) for pid in sides):
        return False
    return bool(retreat_destinations(state, grid, combat.position, combat.retreating[0]))


def _open_round_end_assign(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry
) -> GameState:
    """Krok ASSIGN dla trafień po rundzie (Devotion, RULES.md 62.10) — MUTUJE ``state`` (klon)."""
    combat = _combat(state)
    combat.pending_hits = dict(combat.round_end_hits)
    combat.round_end_hits = {}
    combat.round_end_assign = True
    for pid in list(combat.pending_hits):
        if pid == NEUTRAL_PLAYER_ID:
            _auto_assign_neutral(state, grid, registry, pid)
    queue = [
        pid
        for pid in (combat.defender, combat.attacker)
        if required_hits(state, grid, registry, pid) > 0
    ]
    if not queue:
        combat.round_end_assign = False
        combat.pending_hits = {}
        combat.hit_targets = {}
        return _finish_round(state, grid, registry)
    combat.step = CombatStep.ASSIGN
    return timing.open_window(
        state, WindowType.COMBAT_ASSIGN_HITS, queue, context={"position": combat.position}
    )


def _finish_round(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Koniec rundy (W9) po hookach: zwycięzca/remis albo kolejna runda."""
    new_state = state
    combat = _combat(new_state)
    alive = [
        pid
        for pid in (combat.attacker, combat.defender)
        if side_units(new_state, grid, registry, pid)
    ]
    if len(alive) <= 1:
        # Także O3: ogłoszony odwrót nie następuje, gdy przeciwnikowi nie zostały statki.
        combat.step = CombatStep.DONE
        combat.afb_assign = False
        combat.winner = alive[0] if alive else None
        combat.outcome = "winner" if alive else "draw"
        combat.pending_hits = {}
        combat.retreating = []
        chronicle.record_battle(new_state, combat)
        end_ctx = {
            "kind": combat.kind, "position": combat.position, "winner": combat.winner or "",
            "planet": combat.planet or "", "attacker": combat.attacker,
            "defender": combat.defender,
        }
        if combat.winner is not None:
            triggers.fire(
                new_state,
                GameEvent.COMBAT_WON,
                Moment.AFTER,
                subject=combat.winner,
                ctx=end_ctx,
            )
        triggers.fire(new_state, GameEvent.COMBAT, Moment.END, ctx=end_ctx)
        objective_events.on_combat_end(new_state, grid, combat, combat.winner)
        # 39.6 C3: limit pojemności sprawdzany po wyłonieniu zwycięzcy walki kosmicznej.
        if combat.kind == "space":
            return capacity.open_capacity_check(new_state, registry, combat.position)
        return new_state
    combat.pending_hits = {}
    if combat.step is CombatStep.AFB or combat.afb_assign:
        # AFB nie zmienia numeru rundy (to 1. runda) — dalej Announce Retreats (39.5).
        return _begin_round(new_state, grid)
    # O3: krok Retreat — ogłoszony odwrót MUSI się odbyć, o ile wciąż jest dozwolony cel.
    if combat.retreating and combat.step is not CombatStep.RETREAT:
        pid = combat.retreating[0]
        if retreat_destinations(new_state, grid, combat.position, pid):
            combat.step = CombatStep.RETREAT
            return new_state
        combat.retreating = []  # brak celu — odwrót nie następuje, walka trwa
    combat.retreating = []
    combat.round += 1
    return _begin_round(new_state, grid)


def _begin_round(state: GameState, grid: HexGrid) -> GameState:
    """Początek rundy po AFB: Announce Retreats (walka kosmiczna) albo od razu rzuty (39.5 O2).

    Kolejka okna ``COMBAT_RETREAT`` = obrońca, potem atakujący — tylko gracze z dozwolonym
    celem odwrotu. Pusta kolejka (albo walka naziemna, O1) = krok pomijany.
    """
    new_state = state.clone()
    begin_round_in_place(new_state, grid)
    return new_state


def end_combat_as_draw(state: GameState) -> None:
    """Kończy trwającą walkę REMISEM (Skilled Retreat) - MUTUJE stan (klon wołającego).

    Jak koniec walki w ``_finish_round``, ale bez zwycięzcy (nie ma zdarzenia „wygrał walkę").
    Sprawdzenie pojemności (39.6 C3) robi wołający, jeśli statki zmieniły system.
    """
    combat = _combat(state)
    combat.step = CombatStep.DONE
    combat.winner = None
    combat.outcome = "draw"
    combat.pending_hits = {}
    combat.retreating = []
    combat.afb_assign = False
    chronicle.record_battle(state, combat)
    triggers.fire(
        state, GameEvent.COMBAT, Moment.END,
        ctx={
            "kind": combat.kind, "position": combat.position, "winner": "",
            "planet": combat.planet or "", "attacker": combat.attacker,
            "defender": combat.defender,
        },
    )
    objective_events.on_combat_end(state, None, combat, None)


def begin_round_in_place(state: GameState, grid: HexGrid) -> None:
    """Jak ``_begin_round``, ale MUTUJE przekazany stan (klon wołającego) - dla efektów kart."""
    combat = _combat(state)
    combat.retreating = []
    combat.afb_assign = False
    triggers.fire(
        state, GameEvent.COMBAT_ROUND, Moment.START,
        ctx={
            "kind": combat.kind, "round": combat.round, "position": combat.position,
            "planet": combat.planet or "", "attacker": combat.attacker,
            "defender": combat.defender,
        },
    )
    # Decyzje z hooków początku rundy (np. agent Letnev, Munitions Reserves): walka czeka w kroku
    # TRIGGERS, potem ``resume_after_triggers`` otwiera rundę (RULES.md 56, 62.2).
    if state.pending_offers:
        combat.resume = "round_start"
        combat.step = CombatStep.TRIGGERS
        return
    _open_round(state, grid)


def _open_round(state: GameState, grid: HexGrid) -> None:
    """Announce Retreats (walka kosmiczna, gdy ktoś ma dokąd) albo od razu rzuty (MUTUJE)."""
    combat = _combat(state)
    queue = (
        [
            pid
            for pid in (combat.defender, combat.attacker)
            if pid != NEUTRAL_PLAYER_ID
            and retreat_destinations(state, grid, combat.position, pid)
        ]
        if combat.kind == "space"
        else []
    )
    if not queue:
        combat.step = CombatStep.ROLL
        return
    combat.step = CombatStep.ANNOUNCE
    opened = timing.open_window(
        state,
        WindowType.COMBAT_RETREAT,
        queue,
        context={"position": combat.position, "round": combat.round},
    )
    state.pending_window = opened.pending_window


def announce_retreat(
    state: GameState, grid: HexGrid, player_id: str, *, announce: bool
) -> GameState:
    """Gracz ogłasza odwrót (``announce=True``) albo walczy dalej (39.5 O2).

    Ogłoszenie obrońcy zamyka okno — atakujący nie może już ogłosić odwrotu w tej rundzie.

    Raises:
        ValueError: Nie ten krok/okno, nie kolej gracza, brak dozwolonego celu odwrotu.
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    combat = _combat(state)
    window = state.pending_window
    if (
        combat.step is not CombatStep.ANNOUNCE
        or window is None
        or window.window_type is not WindowType.COMBAT_RETREAT
    ):
        raise ValueError("Retreats are not being announced right now.")
    if window.current_responder != player_id:
        raise ValueError(
            f"It is now {window.current_responder}'s turn to announce a retreat, not {player_id}."
        )
    new_state = state.clone()
    combat = _combat(new_state)
    if announce:
        if not retreat_destinations(new_state, grid, combat.position, player_id):
            raise ValueError("There is no eligible system to retreat to.")
        combat.retreating = [*combat.retreating, player_id]
        triggers.fire(
            new_state, GameEvent.RETREAT_DECLARED, Moment.AFTER, subject=player_id,
            ctx={"player": player_id, "position": combat.position},
        )
    new_state = timing.respond_current(new_state, player_id)
    defender_retreats = announce and player_id == _combat(new_state).defender
    if defender_retreats or timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
        _combat(new_state).step = CombatStep.ROLL
    return new_state


def retreat_from_combat(
    state: GameState,
    grid: HexGrid,
    registry: StaticDataRegistry,
    player_id: str,
    destination: str,
    *,
    cargo: list[CargoPickup] | None = None,
    token_pool: str | None = None,
    ion_storm_token: bool | None = None,
) -> GameState:
    """Krok Retreat: gracz, który ogłosił odwrót, wycofuje się do ``destination`` (39.5 O3–O7).

    Po odwrocie: gdy obaj nadal mają statki w systemie — kolejna runda od Announce Retreats;
    inaczej walka się kończy (zwycięzca = gracz ze statkami).

    Raises:
        ValueError: Nie krok Retreat, gracz nie ogłaszał odwrotu, zły cel/ładunek/pula.
    """
    timing.require_no_limit_window(state)  # nadwyżka puli floty najpierw (RULES.md 42.1)
    combat = _combat(state)
    if combat.step is not CombatStep.RETREAT or player_id not in combat.retreating:
        raise ValueError("You have no retreat to carry out right now.")
    new_state, result = perform_retreat(
        state,
        grid,
        registry,
        combat.position,
        player_id,
        destination,
        cargo=cargo,
        token_pool=token_pool,
        ion_storm_token=ion_storm_token,
    )
    combat = _combat(new_state)
    combat.retreating = []
    combat.retreated = {**combat.retreated, player_id: destination}
    combat.log.append(
        {
            "round": combat.round,
            "phase": "RETREAT",
            "rolls": {},
            "hits": {},
            "losses": {player_id: dict(result.removed)} if result.removed else {},
            "sustained": {},
            "retreat": {
                "player": player_id,
                "destination": destination,
                "units": dict(result.moved),
                "tokenPlaced": result.token_placed,
            },
        }
    )
    return _after_losses(new_state, grid, registry)


def close_combat(state: GameState) -> GameState:
    """Zamyka ZAKOŃCZONĄ walkę (okno pola bitwy znika).

    Raises:
        ValueError: Gdy walka jeszcze trwa.
    """
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    combat = _combat(state)
    if combat.step is not CombatStep.DONE:
        raise ValueError("The combat is not finished yet.")
    if state.pending_offers:
        # Oferty „after the combat” (Salvage Operations) żyją danymi walki - zamknięcie by je
        # uśmierciło bez wiedzy gracza (RULES.md 54.9).
        raise ValueError(
            "Players still have decisions from this combat - "
            "resolve them before closing the battle."
        )
    new_state = state.clone()
    new_state.active_combat = None
    # Wynik walki naziemnej zapamiętujemy w inwazji — Establish Control potrzebuje wiedzieć,
    # czy był remis (obrońca zachowuje kontrolę — RULES.md 40.1 I8).
    if combat.kind == "ground" and combat.planet and new_state.invasion is not None:
        new_state.invasion.combat_results[combat.planet] = {
            "attacker": combat.attacker,
            "defender": combat.defender,
            "winner": combat.winner,
            "outcome": combat.outcome,
            "rounds": combat.round,
        }
    return new_state


def space_combat_required(state: GameState) -> bool:
    """Czy w aktywnym systemie statki ma co najmniej dwóch graczy (walka obowiązkowa — W2)."""
    active = state.active_system
    system = state.systems.get(active) if active is not None else None
    if system is None:
        return False
    owners = [
        pid
        for pid, by_type in system.space_units.items()
        if any(c > 0 and is_space_unit(bt) for bt, c in by_type.items())
    ]
    # Eidolon Maximum na planecie uczestniczy w walce kosmicznej (F_naaz_rokha 2.1).
    owners += [
        pid for pid in state.players
        if pid not in owners and ship_roles.has_planet_ships(state, pid, str(active))
    ]
    return len(owners) >= 2


