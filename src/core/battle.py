"""Silnik walki: kosmicznej i naziemnej — rundy, AFB, rzuty, Sustain Damage, straty (RULES.md 39).

Przebieg (``ActiveCombat.step``): ``AFB`` (1. runda walki kosmicznej, gdy ktoś ma AFB) →
``ROLL`` (rzuty obu stron) → ``ASSIGN`` (okno ``COMBAT_ASSIGN_HITS``: obrońca, potem atakujący)
→ kolejna runda albo ``DONE``. Wszystkie wartości z WARIANTU jednostki gracza
(``combat.resolve_unit_variant``); rzuty przez ``core/dice.py`` (seedowalne, w stanie gry).

Funkcje CZYSTE (``state -> state``). Walidacja twarda: ``ValueError`` → HTTP 422.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core import (
    ability_notes,
    capacity,
    chronicle,
    exhaust,
    objective_events,
    rules_hooks,
    timing,
    triggers,
    unit_ops,
)
from src.core.combat import resolve_unit_variant
from src.core.damage import damaged_count, set_damaged
from src.core.dice import DIE_SIDES, count_hits, next_rng, record_table_roll, roll_dice
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    SystemState,
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

# Anomalia dająca obrońcy +1 do rzutów combat w walce kosmicznej (R_nebula; RULES.md 39 W6).
_NEBULA = "NEBULA"
_FIGHTER = "fighter"


@dataclass(frozen=True)
class CombatUnit:
    """Grupa jednostek gracza w walce (jeden typ) — wartości z wariantu gracza."""

    base_type: str
    unit_id: str
    name: str
    count: int
    damaged: int
    hits_on: int  # próg PO modyfikatorze (np. mgławica: obrońca 6 → 5)
    base_hits_on: int  # próg z danych
    modifier: int  # +N do wyniku rzutu (mgławica: +1 obrońcy)
    dice_per_unit: int
    sustain: bool
    afb_hits_on: int | None
    afb_dice: int
    # Sustain Damage NADANY przez komponent jednostce bez własnego (Metali Void Shielding): ile
    # egzemplarzy może go teraz użyć. Łącznie wolno użyć najwyżej 1 takiego (zob. ``plan_losses``).
    granted: int = 0
    # Dodatkowe kości dla całej grupy (nie na egzemplarz) — agent Letnev (RULES.md 62.2).
    bonus_dice: int = 0
    # +X do wyników kości JEDNEGO egzemplarza (pierwszego w grupie) — Gravleash Maneuvers.
    single_bonus: int = 0

    @property
    def total_dice(self) -> int:
        return self.count * self.dice_per_unit + self.bonus_dice

    @property
    def sustainable(self) -> int:
        """Ile egzemplarzy może jeszcze użyć Sustain Damage (własnego albo nadanego)."""
        return self.count - self.damaged if self.sustain else self.granted

    @property
    def expected_hits(self) -> float:
        chance = max(0, min(DIE_SIDES, DIE_SIDES + 1 - self.hits_on)) / DIE_SIDES
        return round(self.total_dice * chance, 2)


def _zone(kind: str, planet: str | None) -> str:
    return "space" if kind == "space" else (planet or "")


def _units_map(system: SystemState | None, zone: str, player_id: str) -> dict[str, int]:
    if system is None:
        return {}
    if zone == "space":
        return system.space_units.get(player_id, {})
    return system.planet_units.get(zone, {}).get(player_id, {})


def combat_units(
    state: GameState,
    grid: HexGrid | None,
    registry: StaticDataRegistry,
    *,
    kind: str,
    position: str,
    planet: str | None,
    player_id: str,
    defender: bool = False,
) -> list[CombatUnit]:
    """Jednostki gracza biorące udział w walce (W2/W3), z wartościami jego wariantu.

    Kosmiczna: statki w przestrzeni z wartością combat. Naziemna: siły naziemne na
    planecie z wartością combat (struktury bez combat pomijane). ``defender`` włącza
    modyfikator mgławicy (+1, tylko walka kosmiczna — W6).
    """
    system = state.systems.get(position)
    player = state.players.get(player_id)
    zone = _zone(kind, planet)
    terrain_modifier = (
        1
        if defender and kind == "space" and grid is not None
        and _NEBULA in grid.anomalies_at(position)
        else 0
    )
    no_sustain = sustain_denied(state, player_id, position, zone)
    units: list[CombatUnit] = []
    for base_type, count in sorted(_units_map(system, zone, player_id).items()):
        if count <= 0 or is_space_unit(base_type) != (kind == "space"):
            continue
        unit = resolve_unit_variant(
            registry,
            player.faction if player is not None else None,
            player.technologies if player is not None else [],
            base_type,
            player.breakthrough_unlocked if player is not None else False,
        )
        if unit is None or unit.combat_hits_on is None:
            continue
        # Hooki MODIFY: +N do wyniku rzutu i dodatkowe kości (zdolności, technologie) obok
        # terenu (mgławica).
        hook_ctx = {
            "kind": kind, "position": position, "planet": planet,
            "defender": defender, "base_type": base_type,
        }
        modifier = terrain_modifier + rules_hooks.modify(
            rules_hooks.POINT_COMBAT_ROLL_MODIFIER, state, player_id, 0, hook_ctx
        )
        extra_dice = rules_hooks.modify(
            rules_hooks.POINT_COMBAT_EXTRA_DICE, state, player_id, 0, hook_ctx
        )
        bonus_dice = rules_hooks.modify(
            rules_hooks.POINT_COMBAT_BONUS_DICE, state, player_id, 0, hook_ctx
        )
        single_bonus = rules_hooks.modify(
            rules_hooks.POINT_COMBAT_SINGLE_UNIT_BONUS, state, player_id, 0, hook_ctx
        )
        units.append(
            CombatUnit(
                base_type=base_type,
                unit_id=unit.id,
                name=unit.name,
                count=count,
                damaged=damaged_count(system, zone, player_id, base_type),
                hits_on=unit.combat_hits_on - modifier,
                base_hits_on=unit.combat_hits_on,
                modifier=modifier,
                # 0 kości dozwolone (Salai Sai Corian bez statków niemyśliwskich przeciwnika).
                dice_per_unit=max(0, (unit.combat_die_count or 1) + extra_dice),
                sustain=unit.sustain_damage and not no_sustain and base_type not in (
                    rules_hooks.forbidden(rules_hooks.POINT_UNIT_SUSTAIN_LOST, state, player_id)
                ),
                afb_hits_on=unit.afb_hits_on if kind == "space" else None,
                afb_dice=unit.afb_die_count or 1,
                granted=(
                    min(1, count - damaged_count(system, zone, player_id, base_type))
                    if kind == "space"
                    and not no_sustain
                    and base_type != _FIGHTER
                    and not unit.sustain_damage
                    and rules_hooks.permits(
                        rules_hooks.POINT_COMBAT_GRANTED_SUSTAIN, state, player_id, hook_ctx
                    )
                    else 0
                ),
                bonus_dice=max(0, bonus_dice),
                single_bonus=single_bonus,
            )
        )
    return units


def sustain_denied(state: GameState, player_id: str, position: str, zone: str) -> bool:
    """Czy jednostki gracza w strefie systemu tracą SUSTAIN DAMAGE (hook innego gracza).

    Punkt ``combat.sustain_denied`` pytany o KAŻDEGO innego gracza (Fourth Moon: statki w
    systemie, Moll Terminus: siły naziemne na planecie — RULES.md 62.8). Jedno miejsce dla walki,
    Space Cannon i inwazji (wszystkie biorą jednostki z ``combat_units``).
    """
    ctx = {"victim": player_id, "position": position, "zone": zone}
    return any(
        rules_hooks.permits(rules_hooks.POINT_COMBAT_SUSTAIN_DENIED, state, other, ctx)
        for other in state.players
        if other != player_id
    )


def side_units(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player_id: str
) -> list[CombatUnit]:
    """Jednostki gracza w TRWAJĄCEJ walce (z modyfikatorem obrońcy)."""
    combat = _combat(state)
    return combat_units(
        state,
        grid,
        registry,
        kind=combat.kind,
        position=combat.position,
        planet=combat.planet,
        player_id=player_id,
        defender=player_id == combat.defender,
    )


def required_hits(
    state: GameState, grid: HexGrid, registry: StaticDataRegistry, player_id: str
) -> int:
    """Ile trafień gracz musi pokryć: min(trafienia, jednostki + Sustain Damage) — W7."""
    combat = _combat(state)
    pending = combat.pending_hits.get(player_id, 0)
    units = side_units(state, grid, registry, player_id)
    return min(pending, absorbable_hits(units, sustain_cancels(state, player_id)))


def absorbable_hits(units: list[CombatUnit], cancels: int) -> int:
    """Ile trafień strona może jeszcze pochłonąć: jednostki + użycia Sustain Damage × ``cancels``.

    Nadany Sustain Damage (Void Shielding) pochłania najwyżej 1 dodatkowe użycie naraz. To samo
    „życie" pokazuje okno walki (pasek HP), więc licznik strat i pasek zawsze się zgadzają.
    """
    return sum(
        u.count + (cancels * u.sustainable if u.sustain else 0) for u in units
    ) + (cancels if any(u.granted > 0 for u in units) else 0)


def sustain_cancels(state: GameState, player_id: str) -> int:
    """Ile trafień anuluje jedno użycie Sustain Damage gracza (1; Non-Euclidean Shielding: 2)."""
    return 1 + max(
        0, rules_hooks.modify(rules_hooks.POINT_COMBAT_SUSTAIN_CANCELS, state, player_id, 0, {})
    )


def _combat(state: GameState) -> ActiveCombat:
    if state.active_combat is None:
        raise ValueError("No combat is in progress.")
    return state.active_combat


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
    triggers.fire(
        new_state, GameEvent.COMBAT, Moment.START, subject=attacker,
        ctx={"kind": kind, "position": active, "planet": planet or "",
             "attacker": attacker, "defender": defender},
    )
    # Decyzje graczy z hooków startu walki (np. Assault Cannon, Magen Defense Grid): walka czeka
    # w kroku TRIGGERS, aż wszyscy zdecydują (RULES.md 56); potem ``resume_after_triggers``.
    if new_state.pending_offers:
        combat.step = CombatStep.TRIGGERS
        combat.resume = "start"
        return new_state
    return _after_start(new_state, grid, registry)


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
    has_afb = combat.kind == "space" and (
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
    if combat.kind != "space" or not is_space_unit(base_type):
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
        bonus_unit = _afb_bonus_unit(new_state, pid, afb_units)
        for unit in afb_units:
            assert unit.afb_hits_on is not None
            extra = bonus_unit[1] if bonus_unit and bonus_unit[0] == unit.base_type else 0
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


def _afb_bonus_unit(
    state: GameState, player_id: str, units: list[CombatUnit]
) -> tuple[str, int] | None:
    """Dodatkowe kości AFB dla JEDNEJ grupy (hook ``combat.afb_extra_dice``: commander Argent,
    Strike Wing Ambuscade - „choose 1 of those units to roll 1 additional die”).

    Kości dostaje grupa z najlepszym progiem AFB: dodatkowa kość nie ma wad, więc ten wybór jest
    zawsze najlepszy dla gracza (RULES.md 62.11). ``None`` = brak premii albo brak jednostek AFB.
    """
    if not units:
        return None
    extra = rules_hooks.modify(rules_hooks.POINT_COMBAT_AFB_EXTRA_DICE, state, player_id, 0)
    if extra <= 0:
        return None
    best = min(units, key=lambda u: (u.afb_hits_on or 99, u.base_type))
    return best.base_type, extra


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
        destroyed = min(hits_by[pid], fighters)  # nadwyżka przepada (W4)
        if destroyed:
            hits_on = next(
                (
                    u.base_hits_on
                    for u in side_units(new_state, grid, registry, opponent)
                    if u.base_type == _FIGHTER
                ),
                0,
            )
            _remove_units(new_state, combat, opponent, _FIGHTER, destroyed)
            losses.setdefault(opponent, {})[_FIGHTER] = destroyed
            note_destroyed(combat, opponent, _FIGHTER, destroyed, hits_on)
    log_entry: dict[str, Any] = {
        "round": combat.round, "phase": "AFB", "rolls": afb, "hits": hits_by,
        "losses": losses, "sustained": {},
    }
    if raid:
        log_entry["raidDamaged"] = raid  # Raid Formation: statki uszkodzone (nie Sustain Damage)
    combat.log.append(log_entry)
    if waylay_hits:
        # Waylay: przeciwnik sam przypisuje trafienia (Sustain Damage, wybór statków) w kroku
        # ASSIGN; po nim ``_after_losses`` kończy krok AFB (``afb_assign``).
        combat.afb_assign = True
        combat.pending_hits = dict(waylay_hits)
        for pid in waylay_hits:
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


def roll_round(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Rzuty combat obu stron (atakujący pierwszy — W5) i otwarcie przypisania strat."""
    timing.require_no_reaction_pause(state)  # pauza ochronna (RULES.md 54.10)
    timing.require_no_limit_window(state)  # nadwyżka puli floty najpierw (RULES.md 42.1)
    combat = _combat(state)
    if combat.step is not CombatStep.ROLL:
        raise ValueError("Combat dice are not the current combat step.")
    sides = (combat.attacker, combat.defender)
    if any(not side_units(state, grid, registry, pid) for pid in sides):
        # Strona straciła ostatnie jednostki przed rzutem (Indoctrination, Greyfire Mutagen):
        # przegrywa natychmiast, bez rzutów (F_yin, RULES.md 62.10).
        return _finish_round(state.clone(), grid, registry)
    new_state = state
    rolls: dict[str, list[dict[str, Any]]] = {}
    hits_by: dict[str, int] = {}
    for pid in (combat.attacker, combat.defender):
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
    extra_by = _extra_hits(state, combat, hits_by)
    for pid, extra in extra_by.items():
        hits_by[pid] += extra

    new_state = new_state.clone()
    combat = _combat(new_state)
    combat.destroyed_ships = []  # ślady kart reakcji dotyczą ostatnich strat
    combat.sustained_ships = []
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


def _open_assign(state: GameState, grid: HexGrid, registry: StaticDataRegistry) -> GameState:
    """Okno przypisania strat po rzutach rundy (albo koniec rundy, gdy nikt nie ma trafień)."""
    combat = _combat(state)
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
        lost = units[base_type].count - count
        if lost:
            remove_units_in_zone(state, position, zone, player_id, base_type, lost)
        set_damaged(system, zone, player_id, base_type, damaged)


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
    triggers.fire(
        new_state, GameEvent.HITS_ASSIGNED, Moment.BEFORE, subject=player_id,
        ctx={"player": player_id, "kind": combat.kind, "hits": required},
    )
    apply_losses(new_state, combat.position, zone, player_id, units, plan)
    for base_type, lost in losses_of(units, plan).items():
        note_destroyed(combat, player_id, base_type, lost, units[base_type].base_hits_on)
    for base_type, used in sustained_of(plan, sustain).items():
        if used > 0 and combat.kind == "space" and is_space_unit(base_type):
            combat.sustained_ships = [
                *combat.sustained_ships,
                {"player": player_id, "base_type": base_type, "count": used},
            ]
        if used > 0:
            triggers.fire(
                new_state, GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, subject=player_id,
                ctx={"player": player_id, "base_type": base_type, "count": used},
            )

    entry = combat.log[-1] if combat.log else None
    if entry is not None:
        entry["losses"][player_id] = losses_of(units, plan)
        entry["sustained"][player_id] = sustained_of(plan, sustain)
    combat.pending_hits[player_id] = 0

    new_state = timing.respond_current(new_state, player_id)
    if timing.is_window_complete(new_state):
        new_state = timing.close_window(new_state)
        if _hold_for_sustain(new_state, registry, sustained_of(plan, sustain)):
            return new_state
        return _after_losses(new_state, grid, registry)
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
    if combat.kind != "space" or not any(
        n > 0 and is_space_unit(bt) for bt, n in used.items()
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
    return len(owners) >= 2


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
