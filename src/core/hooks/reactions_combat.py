"""Karty reakcji: walka - rundy, odwroty, trafienia, Sustain Damage, AFB (RULES.md 53.5.c).

Wzorzec jak ``reactions_tactical``: okna WYLICZANE ze stanu walki (``ActiveCombat``), adres karty
z tekstu okna albo ``declare_reaction`` (warunek), efekt = ``register_effect``, efekt trwały =
``active_effects`` + hook o źródle ``card_effect_source``.

Okna walki (stabilne pauzy silnika - walka stoi i czeka na gracza):

* **start walki** - runda 1, nic jeszcze nie rzucono (kroki AFB / ANNOUNCE / ROLL);
* **start rundy** - krok ROLL (rzut tej rundy jeszcze się nie odbył);
* **start kroku Announce Retreats** - okno ``COMBAT_RETREAT`` bez żadnej odpowiedzi;
* **odwrót ogłoszony** - ``ActiveCombat.retreating`` niepuste (kroki ROLL / ASSIGN / RETREAT);
* **przed przypisaniem trafień** - krok ASSIGN, gracz ma trafienia do pokrycia;
* **Sustain Damage użyte / statek zniszczony** - ślady ``sustained_ships`` / ``destroyed_ships``
  z ostatnich strat (czyszczone przy kolejnych rzutach), krok ASSIGN / ANNOUNCE / ROLL;
* **przed rzutem AFB** - krok AFB; **po rzutach walki naziemnej** - krok ASSIGN; **po wygranej** -
  krok DONE ze zwycięzcą.

Teksty kart w docstringach to cytaty z assetów kart akcji (``registry.catalog``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    battle,
    battle_rerolls,
    board_graph,
    capacity,
    command_tokens,
    damage,
    economy,
    payment,
    reaction_cards,
    research_offer,
    rules_hooks,
    space_cannon,
    technology,
    timing,
    triggers,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.combat import resolve_unit_variant
from src.core.dice import DIE_SIDES, count_hits, next_rng, record_table_roll
from src.core.fleet_pool import unit_cost, unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import ActiveCombat, CombatStep, GameState, WindowType
from src.core.hex_grid import HexGrid
from src.core.hooks.action_card_inputs import (
    Input,
    _choice,
    _multi,
    _number,
    _option,
    _system_label,
)
from src.core.models import TechnologyDef
from src.core.neutral import NEUTRAL_PLAYER_ID
from src.core.reaction_cards import (
    OpenWindow,
    card_effect_source,
    declare_reaction,
    window_provider,
)
from src.core.registry import StaticDataRegistry
from src.core.retreat import (
    TOKEN_POOLS,
    retreat_destinations,
    retreat_in_place,
    ships_move_destinations,
)
from src.core.rules_hooks import (
    HookKind,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

_MORALE_BOOST = ("mb1", "mb2", "mb3", "mb4")
_MORALE_BONUS = 1  # „Apply +1 to the result of each of your unit's combat rolls”
_SKILLED_RETREAT = ("s_retreat1", "s_retreat2", "s_retreat3", "s_retreat4")
_SHIELDS_HOLDING = ("sh1", "sh2", "sh3", "sh4")
_SHIELDS_MAX = 2  # „Cancel up to 2 hits”
DIRECT_HIT = ("dh1", "dh2", "dh3", "dh4")  # Sleeper Cell Mentaka (F_mentak 7.1)
_FIGHTER_PROTOTYPE_BONUS = 2  # „Apply +2 to the result of each of your fighters' combat rolls”
_REVEAL_DECISION = "reveal_prototype"
_REVEAL_COST = 4  # „Spend 4 resources”
_REFLECTIVE_HITS = 2  # „Produce 2 hits”
_COURAGEOUS_DICE = 2  # „Roll 2 dice”
_FIGHTER = "fighter"
_ANNOUNCE_STEP = "announce_retreats"
_AUTO = "auto"

# Kroki, w których ślady zniszczeń / odwrotów są jeszcze „świeże" (walka trwa).
_LIVE_STEPS = (CombatStep.ASSIGN, CombatStep.ANNOUNCE, CombatStep.ROLL)


# ----------------------------------------------------------------------------- pomocnicze


def _grid() -> HexGrid:
    """Siatka mapy podpięta przez kontekst aplikacji (pusta, gdy nikt jej nie podpiął)."""
    return board_graph.bound_grid() or HexGrid()


def _combat(state: GameState) -> ActiveCombat:
    if state.active_combat is None:
        raise ValueError("No combat is in progress.")
    return state.active_combat


def _players(combat: ActiveCombat) -> list[str]:
    """Uczestnicy walki będący graczami (bez neutralnych)."""
    return [p for p in (combat.attacker, combat.defender) if p != NEUTRAL_PLAYER_ID]


def _opponent(combat: ActiveCombat, player_id: str) -> str:
    return combat.defender if player_id == combat.attacker else combat.attacker


def _participant(state: GameState, player_id: str) -> bool:
    combat = state.active_combat
    return combat is not None and player_id in (combat.attacker, combat.defender)


def _ctx(combat: ActiveCombat, player: str, **extra: Any) -> dict[str, Any]:
    return {
        "player": player, "kind": combat.kind, "position": combat.position,
        "round": combat.round, "attacker": combat.attacker, "defender": combat.defender,
        **extra,
    }


def _window_player(params: Mapping[str, Any]) -> str:
    """Gracz-podmiot okna, na które karta reaguje (``params['__window']['ctx']['player']``)."""
    window = params.get(reaction_cards.WINDOW_KEY)
    ctx = window.get("ctx", {}) if isinstance(window, Mapping) else {}
    player = ctx.get("player") if isinstance(ctx, Mapping) else None
    if not isinstance(player, str):
        raise ValueError("This card needs an open combat window.")
    return player


def _responded(state: GameState) -> list[str]:
    window = state.pending_window
    if window is None or window.window_type is not WindowType.COMBAT_ASSIGN_HITS:
        return []
    return list(window.responded)


def _has_effect(state: GameState, player_id: str, card_ids: tuple[str, ...]) -> bool:
    return any(
        active_effects.has_effect(state, player_id, f"action_cards:{card_id}")
        for card_id in card_ids
    )


def _text(params: Mapping[str, Any], key: str, message: str) -> str:
    value = params.get(key)
    if not isinstance(value, str):
        raise ValueError(message)
    return value


def _damaged_units(state: GameState, player_id: str, position: str) -> list[tuple[str, str, int]]:
    """Uszkodzone jednostki gracza w systemie: ``[(strefa, typ, liczba)]``."""
    system = state.systems.get(position)
    if system is None:
        return []
    found: list[tuple[str, str, int]] = []
    for zone in sorted(system.damaged_units):
        for base_type in sorted(system.damaged_units[zone].get(player_id, {})):
            count = damage.damaged_count(system, zone, player_id, base_type)
            if count > 0:
                found.append((zone, base_type, count))
    return found


def _ships(state: GameState, player_id: str, position: str) -> dict[str, int]:
    """Statki gracza w przestrzeni systemu (typ -> liczba)."""
    system = state.systems.get(position)
    if system is None:
        return {}
    return {
        bt: n
        for bt, n in system.space_units.get(player_id, {}).items()
        if n > 0 and is_space_unit(bt)
    }


# ----------------------------------------------------------------------------- okna


@window_provider
def combat_windows(state: GameState) -> list[OpenWindow]:
    """Okna czasowe walki wyliczone z ``ActiveCombat`` (bez mutacji stanu)."""
    combat = state.active_combat
    if combat is None:
        return []
    out: list[OpenWindow] = []
    step = combat.step
    space = combat.kind == "space"

    def sustain_windows() -> list[OpenWindow]:
        """Okna „when/after Sustain Damage” ze śladu walki; trafienia ze startu walki (Ambush)
        mają osobny klucz pauzy od trafień 1. rundy (``stage``)."""
        stage = (
            {"stage": "start"} if combat.start_assign
            else {"stage": f"round_end{len(combat.sustained_ships)}"}  # new use = new window
            if combat.round_end_assign else {}
        )
        found: list[OpenWindow] = []
        for entry in combat.sustained_ships:
            ctx = _ctx(combat, str(entry["player"]), base_type=str(entry["base_type"]), **stage)
            found.append(OpenWindow(GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.WHEN, dict(ctx)))
            found.append(OpenWindow(GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, dict(ctx)))
        return found

    # Walka czekająca na decyzje ze startu walki / rundy (krok TRIGGERS) nadal JEST na starcie:
    # karty i notki „At the start of combat / of a combat round” wolno wtedy zagrać (RULES.md 53.5).
    at_start = step is CombatStep.TRIGGERS and combat.resume in (
        "start", "start_assault", "round_start"
    )
    # Wpis Ambush (rzut na starcie walki, RULES.md 62.8) nie kończy startu walki.
    started = [e for e in combat.log if e.get("phase") != "AMBUSH"]
    if combat.round == 1 and not started and (
        step in (CombatStep.AFB, CombatStep.ANNOUNCE, CombatStep.ROLL) or at_start
    ):
        out.append(OpenWindow(GameEvent.COMBAT, Moment.START, _ctx(combat, combat.attacker)))
    if step is CombatStep.ROLL or (
        step is CombatStep.TRIGGERS and combat.resume == "round_start"
    ):
        out.append(
            OpenWindow(GameEvent.COMBAT_ROUND, Moment.START, _ctx(combat, combat.attacker))
        )
    window = state.pending_window
    if (
        space
        and step is CombatStep.ANNOUNCE
        and window is not None
        and window.window_type is WindowType.COMBAT_RETREAT
        and window.cursor == 0
    ):
        out.append(
            OpenWindow(
                GameEvent.COMBAT_STEP, Moment.START,
                _ctx(combat, combat.defender, step=_ANNOUNCE_STEP),
            )
        )
    if space and step in (CombatStep.ROLL, CombatStep.ASSIGN, CombatStep.RETREAT):
        for retreater in combat.retreating:
            out.append(
                OpenWindow(GameEvent.RETREAT_DECLARED, Moment.AFTER, _ctx(combat, retreater))
            )
    if step is CombatStep.ASSIGN and combat.sustain_hold:
        # Wstrzymanie po Sustain Damage ostatniej strony: tylko okna „po Sustain Damage”.
        return sustain_windows()
    if space and step is CombatStep.ASSIGN:
        for pid in (combat.defender, combat.attacker):
            hits = combat.pending_hits.get(pid, 0)
            if hits > 0 and pid != NEUTRAL_PLAYER_ID:
                out.append(
                    OpenWindow(GameEvent.HITS_ASSIGNED, Moment.BEFORE, _ctx(combat, pid, hits=hits))
                )
        out.extend(sustain_windows())
    elif step is CombatStep.ASSIGN and combat.sustained_ships:
        out.extend(sustain_windows())  # walka naziemna: tylko statek-siła naziemna (Maximum)
    if space and step in _LIVE_STEPS:
        for lost in combat.destroyed_ships:
            out.append(
                OpenWindow(
                    GameEvent.UNIT_DESTROYED, Moment.AFTER,
                    _ctx(
                        combat, str(lost["player"]),
                        base_type=str(lost["base_type"]), hits_on=int(lost["hits_on"]),
                    ),
                )
            )
    if space and step is CombatStep.AFB:
        grid = _grid()
        registry = rules_hooks.bound_registry()
        for pid in _players(combat):
            units = battle.side_units(state, grid, registry, pid)
            if any(u.afb_hits_on is not None for u in units):
                out.append(
                    OpenWindow(GameEvent.COMBAT_ROLL, Moment.BEFORE, _ctx(combat, pid, kind="afb"))
                )
                # „When … your units make a roll for a unit ability” (Strike Wing Ambuscade).
                out.append(
                    OpenWindow(
                        GameEvent.UNIT_ABILITY_USED, Moment.WHEN, _ctx(combat, pid, ability="afb")
                    )
                )
    # „Po rzutach” w obu rodzajach walki (Fire Team sam wymaga walki naziemnej; War Funding —
    # kosmicznej, RULES.md 62.2).
    if step is CombatStep.ASSIGN and not combat.afb_assign and not combat.round_end_assign:
        for pid in _players(combat):
            if any(entry.get("dice") for entry in combat.rolls.get(pid, [])):
                out.append(OpenWindow(GameEvent.COMBAT_ROLL, Moment.AFTER, _ctx(combat, pid)))
    if space and step is CombatStep.DONE and combat.outcome == "winner" and combat.winner:
        out.append(OpenWindow(GameEvent.COMBAT_WON, Moment.AFTER, _ctx(combat, combat.winner)))
    return out


# ------------------------------------------------------------------ Morale Boost (mb1-mb4)


def _morale_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    # „A second Morale Boost cannot be played during a combat round” (C_action_cards).
    return _participant(state, player_id) and not _has_effect(state, player_id, _MORALE_BOOST)


def _register_morale_boost(card_id: str) -> None:
    """Morale Boost: Apply +1 to the result of each of your unit's combat rolls during this
    combat round.

    Nie dotyczy rzutów AFB (hook modyfikuje tylko wynik rzutu walki); +1 liczy się też przy
    przerzutach w tej rundzie.
    """

    def effect(
        state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
    ) -> None:
        active_effects.add_effect(
            state, f"action_cards:{card_id}", Duration.COMBAT_ROUND, owner=player_id
        )

    register_effect(f"action_cards:{card_id}")(effect)

    def bonus(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
        return _MORALE_BONUS

    register(
        rules_hooks.POINT_COMBAT_ROLL_MODIFIER, card_effect_source(card_id), HookKind.MODIFY
    )(bonus)


for _card in _MORALE_BOOST:
    _register_morale_boost(_card)
declare_reaction(*_MORALE_BOOST, condition=_morale_condition)


# ------------------------------------------------------------------ Fighter Prototype


def _fighter_prototype_condition(
    state: GameState, registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    combat = state.active_combat
    if combat is None or combat.kind != "space" or combat.round != 1:
        return False
    if not _participant(state, player_id) or _has_effect(state, player_id, ("f_prototype",)):
        return False
    units = battle.side_units(state, _grid(), registry, player_id)
    return any(u.base_type == _FIGHTER for u in units)


@register_effect("action_cards:f_prototype")
def fighter_prototype(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Fighter Prototype: Apply +2 to the result of each of your fighters' combat rolls during
    this combat round.
    """
    active_effects.add_effect(
        state, "action_cards:f_prototype", Duration.COMBAT_ROUND, owner=player_id
    )


@register(
    rules_hooks.POINT_COMBAT_ROLL_MODIFIER, card_effect_source("f_prototype"), HookKind.MODIFY
)
def _fighter_prototype_bonus(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    return _FIGHTER_PROTOTYPE_BONUS if ctx.get("base_type") == _FIGHTER else 0


declare_reaction("f_prototype", condition=_fighter_prototype_condition)


# ------------------------------------------------------------------ Emergency Repairs


_SC_OFFENSE_STEP = "space_cannon_offense"


@window_provider
def emergency_repairs_windows(state: GameState) -> list[OpenWindow]:
    """Dodatkowe okna Emergency Repairs („At the start or end of a combat round”, ruling):

    * koniec OSTATNIEJ rundy walki (krok DONE) - koniec wcześniejszych rund to ta sama chwila co
      początek następnej (okno ``COMBAT_ROUND/START`` w kroku ROLL);
    * krok Space Cannon Offense bieżącej akcji (ruling C_action_cards: naprawa statków
      uszkodzonych we wcześniejszej walce).
    """
    windows: list[OpenWindow] = []
    combat = state.active_combat
    if combat is not None and combat.step is CombatStep.DONE:
        windows.append(
            OpenWindow(GameEvent.COMBAT_ROUND, Moment.END, _ctx(combat, combat.attacker))
        )
    if space_cannon.is_open(state) and state.active_system and state.active_player_id:
        windows.append(
            OpenWindow(
                GameEvent.COMBAT_STEP, Moment.START,
                {
                    "player": state.active_player_id, "position": state.active_system,
                    "step": _SC_OFFENSE_STEP,
                },
            )
        )
    return windows


def _emergency_position(state: GameState, window: OpenWindow) -> str | None:
    """System naprawy: walka, a w kroku Space Cannon Offense - aktywny system."""
    if window.event is GameEvent.COMBAT_STEP:
        return state.active_system if window.ctx.get("step") == _SC_OFFENSE_STEP else None
    combat = state.active_combat
    return combat.position if combat is not None else None


def _emergency_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    position = _emergency_position(state, window)
    return position is not None and bool(_damaged_units(state, player_id, position))


@register_effect("action_cards:emergency")
def emergency_repairs(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Emergency Repairs: Repair all of your units that have SUSTAIN DAMAGE in the active system.

    Okna: początek rundy walki (krok ROLL), koniec ostatniej rundy (krok DONE) i krok Space Cannon
    Offense (RULES.md 53.5.c).
    """
    raw = params.get(reaction_cards.WINDOW_KEY)
    ctx = raw.get("ctx", {}) if isinstance(raw, Mapping) else {}
    if isinstance(raw, Mapping) and raw.get("event") == GameEvent.COMBAT_STEP.value:
        position = state.active_system if ctx.get("step") == _SC_OFFENSE_STEP else None
    else:
        position = _combat(state).position
    if position is None:
        raise ValueError("There is no active system to repair units in.")
    system = state.systems[position]
    repaired = _damaged_units(state, player_id, position)
    if not repaired:
        raise ValueError("You have no damaged units in the active system.")
    for zone, base_type, _count in repaired:
        damage.set_damaged(system, zone, player_id, base_type, 0)


declare_reaction(
    "emergency",
    points=(
        (GameEvent.COMBAT_ROUND, Moment.START),
        (GameEvent.COMBAT_ROUND, Moment.END),
        (GameEvent.COMBAT_STEP, Moment.START),
    ),
    condition=_emergency_condition,
)


# ------------------------------------------------------------------ Skilled Retreat


def _skilled_destinations(state: GameState, player_id: str) -> list[str]:
    combat = state.active_combat
    if combat is None or not _ships(state, player_id, combat.position):
        return []
    return ships_move_destinations(state, _grid(), combat.position, player_id)


def _skilled_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    combat = state.active_combat
    return (
        combat is not None
        and combat.kind == "space"
        and _participant(state, player_id)
        and bool(_skilled_destinations(state, player_id))
    )


def _register_skilled_retreat(card_id: str) -> None:
    """Skilled Retreat: Move all of your ships from the active system into an adjacent system
    that does not contain another player's ships. The space combat ends in a draw. Then, place a
    command token from your reinforcements in that system.

    To nie odwrót (nie da się go anulować Intercept). Rulingi C_action_cards: jadą WSZYSTKIE
    statki i ładunek z przestrzeni, także ponad pojemność (8), a nadwyżkę usuwa sprawdzenie
    pojemności w systemie docelowym (5). Bez żetonu w rezerwie gracz bierze go z puli arkusza
    (7): ``token_pool`` albo Auto (⚠ ZAŁOŻENIE: kolejność tactic → fleet → strategy).
    """

    def effect(
        state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
    ) -> None:
        combat = _combat(state)
        destination = _text(params, "destination", "Choose an adjacent system ('destination').")
        allowed = _skilled_destinations(state, player_id)
        if destination not in allowed:
            raise ValueError(f"Your ships cannot move to system {destination}.")
        pool = params.get("token_pool")
        result = retreat_in_place(
            state, _grid(), registry, combat.position, player_id, destination,
            token_pool=pool if isinstance(pool, str) and pool != _AUTO else None,
            destinations=allowed, carry_all=True,
        )
        if not result.moved:
            raise ValueError("None of your ships can move out of the active system.")
        combat.log.append(
            {
                "round": combat.round, "phase": "RETREAT", "rolls": {}, "hits": {},
                "losses": {player_id: dict(result.removed)} if result.removed else {},
                "sustained": {},
                "retreat": {
                    "player": player_id, "destination": destination,
                    "units": dict(result.moved), "tokenPlaced": result.token_placed,
                },
            }
        )
        combat.retreated = {**combat.retreated, player_id: destination}
        # Karta kończy walkę REMISEM (nawet gdy przeciwnikowi zostały statki).
        state.pending_window = None
        battle.end_combat_as_draw(state)
        # Pojemność w systemie docelowym (wymuszone usunięcie od razu, wybór w oknie CAPACITY).
        checked = capacity.open_capacity_check(state, registry, destination)
        if checked is not state:
            state.__dict__.update(checked.__dict__)

    register_effect(f"action_cards:{card_id}")(effect)

    def inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
        options = []
        for position in _skilled_destinations(state, player_id):
            system = state.systems.get(position)
            label = _system_label(registry, system) if system is not None else f"Tile {position}"
            options.append(_option(position, label))
        out = [_choice("destination", "Adjacent system to move your ships to", options)]
        if command_tokens.reinforcements(state, player_id) <= 0:
            pools = [
                _option(name, f"{name.capitalize()} pool")
                for name, sheet in TOKEN_POOLS.items()
                if command_tokens.pool_count(state, player_id, sheet) > 0
            ]
            if pools:
                out.append(
                    _choice(
                        "token_pool",
                        "No command token in reinforcements - take it from a pool",
                        [_option(_AUTO, "Auto (tactic, then fleet, then strategy)"), *pools],
                    )
                )
        return out

    register_effect_inputs(f"action_cards:{card_id}")(inputs)


for _card in _SKILLED_RETREAT:
    _register_skilled_retreat(_card)
declare_reaction(*_SKILLED_RETREAT, condition=_skilled_condition)


# ------------------------------------------------------------------ Reveal Prototype


def _upgrade_base_types(registry: StaticDataRegistry, tech_id: str) -> set[str]:
    """Typy jednostek ulepszane przez technologię (jednostki z ``required_tech_id`` = tech)."""
    return {
        unit.base_type
        for unit in registry.units.values()
        if unit.required_tech_id is not None and unit.required_tech_id.lower() == tech_id.lower()
    }


def _prototype_options(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[TechnologyDef]:
    """Ulepszenia jednostek tego samego typu co jednostka gracza uczestnicząca w walce."""
    if not _participant(state, player_id):
        return []
    taking_part = {u.base_type for u in battle.side_units(state, _grid(), registry, player_id)}
    return [
        tech
        for tech in technology.researchable_techs(state, registry, player_id)
        if (technology.UNIT_UPGRADE in tech.types or not tech.types)
        and _upgrade_base_types(registry, tech.id) & taking_part
    ]


def _can_pay(state: GameState, registry: StaticDataRegistry, player_id: str) -> bool:
    ready = payment.ready_planet_values(state, registry, player_id, "resources")
    return sum(ready.values()) + economy.spendable_trade_goods(state, player_id) >= _REVEAL_COST


def _reveal_condition(
    state: GameState, registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    # „A player cannot play Reveal Prototype if they have less than four resources available.”
    return _can_pay(state, registry, player_id) and bool(
        _prototype_options(state, registry, player_id)
    )


@register_effect("action_cards:reveal_prototype")
def reveal_prototype(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Reveal Prototype: Spend 4 resources to research a unit upgrade technology of the same type
    as 1 of your units that is participating in this combat.

    Technologię i zapłatę wybiera się PO zagraniu w oknie badania (``core/research_offer``),
    ograniczonym do pasujących ulepszeń; Doctor Sucaban obniża wtedy koszt przed zapłatą.
    """
    options = [t.id for t in _prototype_options(state, registry, player_id)]
    if not options or not _can_pay(state, registry, player_id):
        raise ValueError(
            "You need 4 resources and a unit upgrade of the same type as one of your units "
            "in this combat."
        )
    research_offer.begin(state, player_id, _REVEAL_DECISION, _REVEAL_COST, allowed=options)


research_offer.register_decision(
    _REVEAL_DECISION, "Reveal Prototype: research a unit upgrade", "action_cards:reveal_prototype"
)


@register_effect_inputs("action_cards:reveal_prototype")
def reveal_prototype_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    can_pay = _can_pay(state, registry, player_id)
    techs = _prototype_options(state, registry, player_id) if can_pay else []
    return [
        oi.info(
            "research_after",
            "After playing, choose the unit upgrade in the research window.",
            [_option(t.id, t.name or t.id) for t in techs],
            hint=f"Costs {_REVEAL_COST} resources.",
        )
    ]


declare_reaction("reveal_prototype", condition=_reveal_condition)


# ------------------------------------------------------------------ Rout


def _rout_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    combat = state.active_combat
    if combat is None or combat.kind != "space" or window.ctx.get("step") != _ANNOUNCE_STEP:
        return False
    if player_id != combat.defender or combat.attacker == NEUTRAL_PLAYER_ID:
        return False
    # „Your opponent must announce a retreat, if able” - bez legalnego celu karta nic nie daje.
    return bool(retreat_destinations(state, _grid(), combat.position, combat.attacker))


@register_effect("action_cards:rout")
def rout(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Rout: Your opponent must announce a retreat, if able.

    ⚠ ZAŁOŻENIE: odwrót atakującego jest ogłoszony od razu, a okno ogłaszania zamykamy (obrońca
    z Rout nie ogłasza już własnego odwrotu - ogłoszenie obrońcy i tak wykluczałoby atakującego).
    """
    combat = _combat(state)
    attacker = combat.attacker
    if player_id != combat.defender or not retreat_destinations(
        state, _grid(), combat.position, attacker
    ):
        raise ValueError("Your opponent has no eligible system to retreat to.")
    combat.retreating = [attacker]
    state.pending_window = None
    combat.step = CombatStep.ROLL
    triggers.fire(
        state, GameEvent.RETREAT_DECLARED, Moment.AFTER, subject=attacker,
        ctx={"player": attacker, "position": combat.position},
    )


declare_reaction("rout", condition=_rout_condition)


# ------------------------------------------------------------------ Intercept


def _intercept_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    combat = state.active_combat
    return (
        combat is not None
        and combat.kind == "space"
        and _participant(state, player_id)
        and window.subject in combat.retreating
    )


@register_effect("action_cards:intercept")
def intercept(
    state: GameState, _registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Intercept: Your opponent cannot retreat during this round of space combat.

    Ogłoszony odwrót przeciwnika zostaje anulowany; w następnej rundzie może ogłosić kolejny
    (C_action_cards). W kroku RETREAT walka od razu przechodzi do następnej rundy.
    """
    combat = _combat(state)
    target = _window_player(params)
    if target not in combat.retreating:
        raise ValueError("Your opponent has no announced retreat.")
    combat.retreating = [p for p in combat.retreating if p != target]
    if combat.step is CombatStep.RETREAT:
        combat.pending_hits = {}
        combat.round += 1
        battle.begin_round_in_place(state, _grid())


declare_reaction("intercept", condition=_intercept_condition)


# ------------------------------------------------------------------ Shields Holding (sh1-sh4)


def _shields_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    combat = state.active_combat
    return (
        combat is not None
        and combat.kind == "space"
        and window.subject == player_id
        and combat.pending_hits.get(player_id, 0) > 0
        and player_id not in _responded(state)
        and _shields_mark(combat, player_id) not in combat.effects
    )


def _shields_mark(combat: Any, player_id: str) -> dict[str, Any]:
    """Ślad Shields Holding na TEN rzut (runda + rodzaj trafień: AFB / koniec rundy / rzut walki).

    C_action_cards shields-holding 5: drugiej karty na te same trafienia gracz nie zagra."""
    source = "afb" if combat.afb_assign else "round_end" if combat.round_end_assign else "roll"
    return {"kind": "shields_holding", "player": player_id, "round": combat.round,
            "source": source}


def _register_shields_holding(card_id: str) -> None:
    """Shields Holding: Cancel up to 2 hits.

    Dotyczy trafień z rzutu walki i z AFB (zwykłe i Waylay - krok ASSIGN, RULES.md 39 W4) w walce
    kosmicznej; jedna karta gracza na ten sam rzut (C_action_cards 5). Po zejściu trafień do 0
    gracz zatwierdza przypisanie z pustym wyborem.
    """

    def effect(
        state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
    ) -> None:
        combat = _combat(state)
        pending = combat.pending_hits.get(player_id, 0)
        count = params.get("count", _SHIELDS_MAX)
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("Choose how many hits to cancel ('count', 1-2).")
        if count > _SHIELDS_MAX:
            raise ValueError(f"You can cancel at most {_SHIELDS_MAX} hits.")
        if pending <= 0:
            raise ValueError("You have no hits to cancel.")
        combat.pending_hits[player_id] = pending - min(count, pending)
        combat.effects.append(_shields_mark(combat, player_id))

    register_effect(f"action_cards:{card_id}")(effect)

    def inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
        window = reaction_cards.window_for(state, registry, player_id, card_id)
        hits = int(window.ctx.get("hits", _SHIELDS_MAX)) if window is not None else _SHIELDS_MAX
        most = max(1, min(_SHIELDS_MAX, hits))
        return [_number("count", "Hits to cancel", 1, most, auto=most)]  # Auto: jak najwięcej

    register_effect_inputs(f"action_cards:{card_id}")(inputs)


for _card in _SHIELDS_HOLDING:
    _register_shields_holding(_card)
declare_reaction(*_SHIELDS_HOLDING, condition=_shields_condition)


# ------------------------------------------------------------------ Courageous to the End


def _courageous_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    combat = state.active_combat
    if combat is None or combat.kind != "space" or window.subject != player_id:
        return False
    opponent = _opponent(combat, player_id)
    return opponent != NEUTRAL_PLAYER_ID and bool(_ships(state, opponent, combat.position))


@register_effect("action_cards:courageous")
def courageous(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Courageous to the End: Roll 2 dice. For each result equal to or greater than that ship's
    combat value, your opponent must choose and destroy 1 of their ships.

    Modyfikatory rzutów nie dotyczą tych kości (C_action_cards). ⚠ ZAŁOŻENIE: wyboru statków
    przeciwnika nie da się zapytać w trakcie cudzej karty - silnik niszczy jego NAJTAŃSZE statki
    (od najtańszych). ⚠ Karta jest zagrywalna tylko, gdy walka jeszcze trwa po stracie statku.
    """
    combat = _combat(state)
    base_type = _text(params, "ship", "Choose the destroyed ship ('ship').")
    entry = next(
        (
            lost
            for lost in combat.destroyed_ships
            if lost["player"] == player_id and lost["base_type"] == base_type
        ),
        None,
    )
    if entry is None:
        raise ValueError("That ship was not destroyed in this combat.")
    spent = combat.destroyed_ships.index(entry)  # karta „zużywa" jeden zniszczony statek
    combat.destroyed_ships = [
        lost for i, lost in enumerate(combat.destroyed_ships) if i != spent
    ]
    hits_on = int(entry["hits_on"])
    rng = next_rng(state)
    results = [rng.randint(1, DIE_SIDES) for _ in range(_COURAGEOUS_DICE)]
    hits = count_hits(results, hits_on)
    record_table_roll(
        state, player_id, "courageous", "Courageous to the End", results, hits_on=hits_on,
        summary=f"{hits} of the opponent's ships destroyed.",
    )
    opponent = _opponent(combat, player_id)
    system = state.systems[combat.position]
    ships = _ships(state, opponent, combat.position)
    for ship in sorted(ships, key=lambda bt: (unit_cost(state, registry, opponent, bt), bt)):
        if hits <= 0:
            break
        kill = min(hits, ships[ship])
        unit_ops.remove_units(state, system, "space", opponent, ship, kill, UnitCause.DESTROYED)
        hits -= kill


@register_effect_inputs("action_cards:courageous")
def courageous_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    combat = state.active_combat
    seen: dict[str, int] = {}
    for lost in combat.destroyed_ships if combat is not None else []:
        if lost["player"] == player_id:
            seen.setdefault(str(lost["base_type"]), int(lost["hits_on"]))
    options = [
        _option(bt, f"{unit_name(state, registry, player_id, bt)} (combat {hits_on})")
        for bt, hits_on in seen.items()
    ]
    return [_choice("ship", "Destroyed ship", options)]


declare_reaction("courageous", condition=_courageous_condition)


# ------------------------------------------------------------------ Direct Hit (dh1-dh4)


_DIRECT_HIT_IMMUNE = 'cannot be destroyed by "direct hit"'


def _direct_hit_immune(state: GameState, player_id: str, base_type: str) -> bool:
    """Wariant jednostki gracza ma w tekście „cannot be destroyed by "Direct Hit"” (dane)."""
    registry = rules_hooks.bound_registry()
    player = state.players.get(player_id)
    if registry is None or player is None:
        return False
    unit = resolve_unit_variant(
        registry, player.faction, player.technologies, base_type, player.breakthrough_unlocked,
        player.breakthrough_flipped,
    )
    return unit is not None and _DIRECT_HIT_IMMUNE in (unit.ability or "").lower()


def _sustained_of(combat: ActiveCombat, state: GameState, player_id: str) -> list[str]:
    """Typy statków gracza, które użyły Sustain Damage i wciąż są uszkodzone w systemie.

    Bez jednostek odpornych na Direct Hit (Exotrireme II i in. — tekst z danych, RULES.md 62.1).
    """
    system = state.systems.get(combat.position)
    return [
        str(entry["base_type"])
        for entry in combat.sustained_ships
        if entry["player"] == player_id
        and damage.damaged_count(
            system, _sustained_zone(combat, player_id, str(entry["base_type"])), player_id,
            str(entry["base_type"]),
        ) > 0
        and not _direct_hit_immune(state, player_id, str(entry["base_type"]))
    ]


def _sustained_zone(combat: ActiveCombat, player_id: str, base_type: str) -> str:
    """Strefa statku, który użył Sustain Damage: przestrzeń albo planeta (Eidolon Maximum na
    planecie, także w walce naziemnej - F_naaz_rokha eidolon-maximum 2.3)."""
    for entry in combat.sustained_ships:
        if entry["player"] == player_id and entry["base_type"] == base_type:
            return str(entry.get("zone") or "space")
    return "space"


_SC_SOURCE = "space_cannon"


@window_provider
def sustain_outside_combat(state: GameState) -> list[OpenWindow]:
    """Okna „po Sustain Damage” poza walką (Space Cannon Offense) ze śladu ``sustain_trace``."""
    if state.active_combat is not None:
        return []
    return [
        OpenWindow(
            GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER,
            {
                "player": str(e["player"]), "base_type": str(e["base_type"]),
                "by": str(e["by"]), "position": str(e["position"]), "source": _SC_SOURCE,
            },
        )
        for e in state.sustain_trace
        if e.get("position") == state.active_system
    ]


def _trace_types(state: GameState, target: str, by: str) -> list[str]:
    """Statki ``target`` uszkodzone Sustain Damage przeciw trafieniom ``by`` (Space Cannon)."""
    system = state.systems.get(state.active_system or "")
    if system is None:
        return []
    return [
        str(e["base_type"])
        for e in state.sustain_trace
        if e["player"] == target
        and e["by"] == by
        and damage.damaged_count(system, "space", target, str(e["base_type"])) > 0
        and not _direct_hit_immune(state, target, str(e["base_type"]))
    ]


def _direct_hit_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    if window.ctx.get("source") == _SC_SOURCE:
        target = window.subject
        return (
            target is not None
            and target != player_id
            and window.ctx.get("by") == player_id
            and window.ctx.get("base_type") in _trace_types(state, target, player_id)
        )
    combat = state.active_combat
    if combat is None or not _participant(state, player_id):
        return False
    target = window.subject
    return (
        target is not None
        and target != player_id
        and target == _opponent(combat, player_id)
        and window.ctx.get("base_type") in _sustained_of(combat, state, target)
    )


def _consume_sustain(combat: ActiveCombat, player_id: str, base_type: str) -> None:
    """Zdejmuje jedno użycie Sustain Damage ze śladu walki (karta je „zużywa")."""
    updated: list[dict[str, Any]] = []
    done = False
    for entry in combat.sustained_ships:
        if not done and entry["player"] == player_id and entry["base_type"] == base_type:
            done = True
            if int(entry["count"]) > 1:
                updated.append({**entry, "count": int(entry["count"]) - 1})
            continue
        updated.append(entry)
    if not done:
        raise ValueError("That ship did not use SUSTAIN DAMAGE.")
    combat.sustained_ships = updated


def _register_direct_hit(card_id: str) -> None:
    """Direct Hit: Destroy that ship.

    Niszczy statek (uszkodzony po Sustain Damage); mech nie jest statkiem (C_action_cards).
    Pojemność jest sprawdzana po walce (39.6 C3).
    """

    def effect(
        state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
    ) -> None:
        base_type = _text(params, "ship", "Choose the ship that used SUSTAIN DAMAGE ('ship').")
        if state.active_combat is None:
            _direct_hit_outside_combat(state, registry, player_id, params, base_type)
            return
        combat = _combat(state)
        target = _opponent(combat, player_id)
        if base_type not in _sustained_of(combat, state, target):
            raise ValueError("That ship did not use SUSTAIN DAMAGE.")
        system = state.systems[combat.position]
        zone = _sustained_zone(combat, target, base_type)
        damaged_before = damage.damaged_count(system, zone, target, base_type)
        _consume_sustain(combat, target, base_type)
        unit_ops.remove_units(state, system, zone, target, base_type, 1, UnitCause.DESTROYED)
        # Niszczymy właśnie ten, uszkodzony egzemplarz - uszkodzeń ma być o jedno mniej.
        damage.set_damaged(system, zone, target, base_type, damaged_before - 1)

    register_effect(f"action_cards:{card_id}")(effect)

    def inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
        combat = state.active_combat
        if combat is not None:
            target = _opponent(combat, player_id)
            types = list(dict.fromkeys(_sustained_of(combat, state, target)))
        else:  # Space Cannon: statki, które anulowały Twoje trafienia
            targets = [str(e["player"]) for e in state.sustain_trace if e["by"] == player_id]
            target = targets[0] if targets else ""
            types = list(dict.fromkeys(_trace_types(state, target, player_id)))
        options = [_option(bt, unit_name(state, registry, target, bt)) for bt in types]
        return [_choice("ship", "Ship that used SUSTAIN DAMAGE", options)]

    register_effect_inputs(f"action_cards:{card_id}")(inputs)


def _direct_hit_outside_combat(
    state: GameState,
    registry: StaticDataRegistry,
    player_id: str,
    params: Mapping[str, Any],
    base_type: str,
) -> None:
    """Direct Hit po Sustain Damage przeciw Twoim trafieniom Space Cannon (poza walką).

    Ruling C_action_cards direct-hit/4: nadwyżkę ładunku (myśliwce / siły naziemne) po
    zniszczeniu statku z pojemnością usuwa się OD RAZU - bez wyboru wprost, z wyborem w oknie
    ``CAPACITY``, które zawiesza bieżące okno Space Cannon (``timing.interrupt``).
    """
    raw = params.get(reaction_cards.WINDOW_KEY)
    ctx = raw.get("ctx", {}) if isinstance(raw, Mapping) else {}
    target = str(ctx.get("player", ""))
    if base_type not in _trace_types(state, target, player_id):
        raise ValueError("That ship did not use SUSTAIN DAMAGE against your hits.")
    system = state.systems[state.active_system or ""]
    damaged_before = damage.damaged_count(system, "space", target, base_type)
    trace: list[dict[str, Any]] = []
    done = False
    for entry in state.sustain_trace:
        if not done and entry["player"] == target and entry["base_type"] == base_type:
            done = True
            if int(entry["count"]) > 1:
                trace.append({**entry, "count": int(entry["count"]) - 1})
            continue
        trace.append(entry)
    state.sustain_trace = trace
    unit_ops.remove_units(state, system, "space", target, base_type, 1, UnitCause.DESTROYED)
    damage.set_damaged(system, "space", target, base_type, damaged_before - 1)
    _enforce_capacity_now(state, registry, system.position)


def _enforce_capacity_now(state: GameState, registry: StaticDataRegistry, position: str) -> None:
    """Usuwa nadwyżkę pojemności w systemie natychmiast (MUTUJE ``state``)."""
    forced = capacity.remove_forced_excess(state, registry, position)
    if forced is not state:
        state.__dict__.update(forced.__dict__)
    queue = capacity.players_with_excess(state, registry, position)
    if queue:
        opened = timing.interrupt(state, WindowType.CAPACITY, queue, context={"position": position})
        state.__dict__.update(opened.__dict__)


for _card in DIRECT_HIT:
    _register_direct_hit(_card)
declare_reaction(*DIRECT_HIT, condition=_direct_hit_condition)


# ------------------------------------------------------------------ Reflective Shielding


def _reflective_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    combat = state.active_combat
    if combat is None or combat.kind != "space" or window.subject != player_id:
        return False
    opponent = _opponent(combat, player_id)
    return (
        opponent != NEUTRAL_PLAYER_ID
        and opponent not in _responded(state)
        and bool(_ships(state, opponent, combat.position))
        and window.ctx.get("base_type") in [
            str(e["base_type"]) for e in combat.sustained_ships if e["player"] == player_id
        ]
    )


@register_effect("action_cards:reflective")
def reflective_shielding(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Reflective Shielding: Produce 2 hits against your opponent's ships in the active system.

    Trafienia dochodzą do trafień z rzutu (C_action_cards) i przeciwnik przypisuje je w kroku
    ASSIGN. Gdy Sustain Damage użyła ostatnia strona przypisania, walka czeka
    (``ActiveCombat.sustain_hold``), a karta otwiera przeciwnikowi nowe przypisanie.
    """
    combat = _combat(state)
    opponent = _opponent(combat, player_id)
    base_type = _window_ship(params)
    _consume_sustain(combat, player_id, base_type)
    battle.add_combat_hits(state, opponent, _REFLECTIVE_HITS)


def _window_ship(params: Mapping[str, Any]) -> str:
    window = params.get(reaction_cards.WINDOW_KEY)
    ctx = window.get("ctx", {}) if isinstance(window, Mapping) else {}
    base_type = ctx.get("base_type") if isinstance(ctx, Mapping) else None
    if not isinstance(base_type, str):
        raise ValueError("This card needs an open SUSTAIN DAMAGE window.")
    return base_type


declare_reaction("reflective", condition=_reflective_condition)


# ------------------------------------------------------------------ Fire Team


def _fire_team_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    combat = state.active_combat
    if combat is None or combat.kind != "ground" or window.subject != player_id:
        return False
    return _opponent(combat, player_id) not in _responded(state)


@register_effect("action_cards:fire_team")
def fire_team(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Fire Team: Reroll any number of your dice.

    Modyfikatory z pierwotnego rzutu obowiązują przy przerzucie (C_action_cards). Trafienia
    przeciwnika są liczone od nowa (``battle_rerolls.reroll_combat_dice``: z premiami kości
    i trafieniem
    Valkyrie Particle Weave); gdy nie był w kolejce przypisania, a ma teraz trafienia, dołącza.
    """
    combat = _combat(state)
    picked = params.get("dice")
    if not isinstance(picked, list) or not picked or not all(isinstance(p, str) for p in picked):
        raise ValueError("Choose the dice to reroll ('dice').")
    rolls = combat.rolls.get(player_id, [])
    chosen: set[tuple[int, int]] = set()
    for token in picked:
        try:
            left, right = token.split(":")
            index, die = int(left), int(right)
        except ValueError as exc:
            raise ValueError(f"Unknown die: {token}") from exc
        if not (0 <= index < len(rolls)) or not (0 <= die < len(rolls[index]["dice"])):
            raise ValueError(f"Unknown die: {token}")
        chosen.add((index, die))
    battle_rerolls.reroll_combat_dice(state, player_id, chosen, "fire_team", "Fire Team")


@register_effect_inputs("action_cards:fire_team")
def fire_team_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    combat = state.active_combat
    options: list[dict[str, Any]] = []
    rolls = combat.rolls.get(player_id, []) if combat is not None else []
    for index, entry in enumerate(rolls):
        for die, value in enumerate(entry["dice"]):
            hit = int(value) + int(entry["modifier"]) >= int(entry["hitsOn"])
            options.append(
                _option(
                    f"{index}:{die}",
                    f"{entry['name']}: {value} ({'hit' if hit else 'miss'})",
                    f"{index}:{die}",
                )
            )
    return [_multi("dice", "Dice to reroll", options, 1, len(options))]


declare_reaction("fire_team", condition=_fire_team_condition)


# ------------------------------------------------------------------ Salvage


def _salvage_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    combat = state.active_combat
    if combat is None or combat.kind != "space" or window.subject != player_id:
        return False
    opponent = _opponent(combat, player_id)
    loser = state.players.get(opponent)
    return loser is not None and loser.commodities > 0


@register_effect("action_cards:salvage")
def salvage(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Salvage: Your opponent gives you all of their commodities.

    Oddane commodities stają się u odbiorcy trade goods (R_commodities).
    """
    combat = _combat(state)
    opponent = _opponent(combat, player_id)
    loser = state.players.get(opponent)
    if combat.winner != player_id or loser is None or loser.commodities <= 0:
        raise ValueError("Your opponent has no commodities to give you.")
    economy.give_to_player(state, opponent, player_id, commodities=loser.commodities)


declare_reaction("salvage", condition=_salvage_condition)


# ------------------------------------------------------------------ Waylay


def _waylay_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    return (
        window.ctx.get("kind") == "afb"
        and window.subject == player_id
        and not _has_effect(state, player_id, ("waylay",))
    )


@register_effect("action_cards:waylay")
def waylay(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Waylay: Hits from this roll are produced against all ships (not just fighters).

    Efekt trwa do końca kroku AFB (zdarzenie końca rundy); trafienia przypisuje przeciwnik.
    """
    active_effects.add_effect(state, "action_cards:waylay", Duration.COMBAT_ROUND, owner=player_id)


@register(rules_hooks.POINT_COMBAT_AFB_ALL_SHIPS, card_effect_source("waylay"), HookKind.PERMIT)
def _waylay_permit(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return True


declare_reaction("waylay", condition=_waylay_condition)
