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
    board_graph,
    capacity,
    damage,
    economy,
    payment,
    reaction_cards,
    rules_hooks,
    technology,
    triggers,
    unit_ops,
)
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
    _planet_label,
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
from src.core.retreat import retreat_destinations, retreat_in_place, ships_move_destinations
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
_DIRECT_HIT = ("dh1", "dh2", "dh3", "dh4")
_FIGHTER_PROTOTYPE_BONUS = 2  # „Apply +2 to the result of each of your fighters' combat rolls”
_REVEAL_COST = 4  # „Spend 4 resources”
_REFLECTIVE_HITS = 2  # „Produce 2 hits”
_COURAGEOUS_DICE = 2  # „Roll 2 dice”
_FIGHTER = "fighter"
_ANNOUNCE_STEP = "announce_retreats"

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

    if combat.round == 1 and not combat.log and step in (
        CombatStep.AFB, CombatStep.ANNOUNCE, CombatStep.ROLL
    ):
        out.append(OpenWindow(GameEvent.COMBAT, Moment.START, _ctx(combat, combat.attacker)))
    if step is CombatStep.ROLL:
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
    if space and step is CombatStep.ASSIGN:
        for pid in (combat.defender, combat.attacker):
            hits = combat.pending_hits.get(pid, 0)
            if hits > 0 and pid != NEUTRAL_PLAYER_ID:
                out.append(
                    OpenWindow(GameEvent.HITS_ASSIGNED, Moment.BEFORE, _ctx(combat, pid, hits=hits))
                )
        for entry in combat.sustained_ships:
            ctx = _ctx(combat, str(entry["player"]), base_type=str(entry["base_type"]))
            out.append(OpenWindow(GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.WHEN, dict(ctx)))
            out.append(OpenWindow(GameEvent.UNIT_SUSTAIN_DAMAGE, Moment.AFTER, dict(ctx)))
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
    if step is CombatStep.ASSIGN and combat.kind == "ground":
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


def _emergency_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> bool:
    combat = state.active_combat
    return combat is not None and bool(_damaged_units(state, player_id, combat.position))


@register_effect("action_cards:emergency")
def emergency_repairs(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Emergency Repairs: Repair all of your units that have SUSTAIN DAMAGE in the active system.

    ⚠ ZAŁOŻENIE: okno „koniec rundy" nie ma stabilnej pauzy (po przypisaniu strat silnik od razu
    startuje następną rundę), więc karta jest zagrywalna na starcie rundy (krok ROLL).
    """
    combat = _combat(state)
    system = state.systems[combat.position]
    repaired = _damaged_units(state, player_id, combat.position)
    if not repaired:
        raise ValueError("You have no damaged units in the active system.")
    for zone, base_type, _count in repaired:
        damage.set_damaged(system, zone, player_id, base_type, 0)


declare_reaction("emergency", condition=_emergency_condition)


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

    To nie odwrót (nie da się go anulować Intercept). ⚠ ZAŁOŻENIE: ładunek jak w odwrocie
    (mechy → piechota → myśliwce do pojemności, reszta zdjęta); żeton tylko z rezerwy.
    """

    def effect(
        state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
    ) -> None:
        combat = _combat(state)
        destination = _text(params, "destination", "Choose an adjacent system ('destination').")
        allowed = _skilled_destinations(state, player_id)
        if destination not in allowed:
            raise ValueError(f"Your ships cannot move to system {destination}.")
        result = retreat_in_place(
            state, _grid(), registry, combat.position, player_id, destination,
            destinations=allowed, token_pools=False,
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
        checked = capacity.open_capacity_check(state, registry, destination)
        state.pending_window = checked.pending_window

    register_effect(f"action_cards:{card_id}")(effect)

    def inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
        options = []
        for position in _skilled_destinations(state, player_id):
            system = state.systems.get(position)
            label = _system_label(registry, system) if system is not None else f"Tile {position}"
            options.append(_option(position, label))
        return [_choice("destination", "Adjacent system to move your ships to", options)]

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
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Reveal Prototype: Spend 4 resources to research a unit upgrade technology of the same type
    as 1 of your units that is participating in this combat.
    """
    tech_id = _text(params, "technology", "Choose a unit upgrade to research ('technology').")
    if tech_id not in {t.id for t in _prototype_options(state, registry, player_id)}:
        raise ValueError(
            "Choose a unit upgrade of the same type as one of your units in this combat."
        )
    skips = params.get("skips", [])
    if not isinstance(skips, list) or not all(isinstance(s, str) for s in skips):
        raise ValueError("'skips' must be a list of ids.")
    planets, trade_goods = payment.parse_payment(dict(params))
    if set(planets) & set(skips):
        raise ValueError("A planet cannot both pay for the card and be used as a skip.")
    paid = payment.validate_payment(state, registry, player_id, "resources", planets, trade_goods)
    if paid < _REVEAL_COST:
        raise ValueError(f"Spend at least {_REVEAL_COST} resources (you chose {paid}).")
    plan = technology.plan_research(state, registry, player_id, tech_id, list(skips))
    payment.apply_payment(state, player_id, planets, trade_goods)
    technology.apply_research(state, player_id, plan)


@register_effect_inputs("action_cards:reveal_prototype")
def reveal_prototype_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[Input]:
    can_pay = _can_pay(state, registry, player_id)
    techs = _prototype_options(state, registry, player_id) if can_pay else []
    ready = payment.ready_planet_values(state, registry, player_id, "resources")
    spendable = economy.spendable_trade_goods(state, player_id)
    skips = [
        _option(planet, _planet_label(state, registry, planet, "skips 1 prerequisite"))
        for planet in technology.specialty_planets(state, registry, player_id)
    ]
    if technology.aida_ready(state, player_id):
        skips.append(_option(technology.AIDA_SKIP, "AI Development Algorithm (unit upgrades)"))
    pay_planets = [
        _option(p, _planet_label(state, registry, p, f"spend {value} resources"), p)
        for p, value in ready.items()
        if value > 0
    ]
    return [
        _choice(
            "technology", "Unit upgrade to research",
            [_option(t.id, t.name or t.id) for t in techs],
            hint=f"Costs {_REVEAL_COST} resources.",
        ),
        _multi("skips", "Skips: exhaust to ignore a prerequisite", skips, 0, len(skips)),
        _multi(
            "planets", "Planets to exhaust", pay_planets, 0, len(pay_planets),
            f"Spend at least {_REVEAL_COST} resources.",
        ),
        _number("trade_goods", "Trade goods to spend", 0, spendable),
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
    )


def _register_shields_holding(card_id: str) -> None:
    """Shields Holding: Cancel up to 2 hits.

    Dotyczy trafień z rzutu walki i z AFB (Waylay) w walce kosmicznej. ⚠ ZAŁOŻENIE: trafienia z
    zwykłego AFB są rozstrzygane automatycznie (bez kroku ASSIGN), więc Shields Holding ich nie
    anuluje; po zejściu trafień do 0 gracz zatwierdza przypisanie z pustym wyborem.
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

    register_effect(f"action_cards:{card_id}")(effect)

    def inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
        window = reaction_cards.window_for(state, registry, player_id, card_id)
        hits = int(window.ctx.get("hits", _SHIELDS_MAX)) if window is not None else _SHIELDS_MAX
        return [_number("count", "Hits to cancel", 1, max(1, min(_SHIELDS_MAX, hits)))]

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


def _sustained_of(combat: ActiveCombat, state: GameState, player_id: str) -> list[str]:
    """Typy statków gracza, które użyły Sustain Damage i wciąż są uszkodzone w systemie."""
    system = state.systems.get(combat.position)
    return [
        str(entry["base_type"])
        for entry in combat.sustained_ships
        if entry["player"] == player_id
        and damage.damaged_count(system, "space", player_id, str(entry["base_type"])) > 0
    ]


def _direct_hit_condition(
    state: GameState, _registry: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    combat = state.active_combat
    if combat is None or combat.kind != "space" or not _participant(state, player_id):
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
        state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
    ) -> None:
        combat = _combat(state)
        target = _opponent(combat, player_id)
        base_type = _text(params, "ship", "Choose the ship that used SUSTAIN DAMAGE ('ship').")
        if base_type not in _sustained_of(combat, state, target):
            raise ValueError("That ship did not use SUSTAIN DAMAGE.")
        system = state.systems[combat.position]
        damaged_before = damage.damaged_count(system, "space", target, base_type)
        _consume_sustain(combat, target, base_type)
        unit_ops.remove_units(state, system, "space", target, base_type, 1, UnitCause.DESTROYED)
        # Niszczymy właśnie ten, uszkodzony egzemplarz - uszkodzeń ma być o jedno mniej.
        damage.set_damaged(system, "space", target, base_type, damaged_before - 1)

    register_effect(f"action_cards:{card_id}")(effect)

    def inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
        combat = state.active_combat
        target = _opponent(combat, player_id) if combat is not None else ""
        types = (
            list(dict.fromkeys(_sustained_of(combat, state, target))) if combat is not None else []
        )
        options = [_option(bt, unit_name(state, registry, target, bt)) for bt in types]
        return [_choice("ship", "Ship that used SUSTAIN DAMAGE", options)]

    register_effect_inputs(f"action_cards:{card_id}")(inputs)


for _card in _DIRECT_HIT:
    _register_direct_hit(_card)
declare_reaction(*_DIRECT_HIT, condition=_direct_hit_condition)


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
    ASSIGN. ⚠ Karta jest zagrywalna tylko, gdy przeciwnik jeszcze nie przypisał strat (czyli
    gdy to obrońca użył Sustain Damage jako pierwszy).
    """
    combat = _combat(state)
    opponent = _opponent(combat, player_id)
    base_type = _window_ship(params)
    _consume_sustain(combat, player_id, base_type)
    combat.pending_hits[opponent] = combat.pending_hits.get(opponent, 0) + _REFLECTIVE_HITS
    window = state.pending_window
    if window is not None and opponent not in window.queue:
        window.queue = [*window.queue, opponent]


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


def _die_hits(state: GameState, combat: ActiveCombat, player_id: str, entry: dict[str, Any]) -> int:
    """Trafienia jednej grupy rzutów (jak w ``battle.roll_round``: modyfikator, mnożnik)."""
    hits = count_hits(
        [int(d) + int(entry["modifier"]) for d in entry["dice"]], int(entry["hitsOn"])
    )
    return hits * rules_hooks.modify(
        rules_hooks.POINT_COMBAT_HIT_MULTIPLIER, state, player_id, 1,
        {"kind": combat.kind, "base_type": entry["baseType"]},
    )


@register_effect("action_cards:fire_team")
def fire_team(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Fire Team: Reroll any number of your dice.

    Modyfikatory z pierwotnego rzutu obowiązują przy przerzucie (C_action_cards). Trafienia
    przeciwnika są liczone od nowa; gdy nie był w kolejce przypisania, a ma teraz trafienia,
    dołącza do niej.
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
    rng = next_rng(state)
    results: list[int] = []
    for index, die in sorted(chosen):
        value = rng.randint(1, DIE_SIDES)
        rolls[index]["dice"][die] = value
        results.append(value)
    total = 0
    for entry in rolls:
        entry["hits"] = _die_hits(state, combat, player_id, entry)
        total += int(entry["hits"])
    opponent = _opponent(combat, player_id)
    combat.pending_hits[opponent] = total
    if combat.log:
        last = combat.log[-1]
        last.setdefault("rolls", {})[player_id] = rolls
        last.setdefault("hits", {})[player_id] = total
    window = state.pending_window
    if total > 0 and window is not None and opponent not in window.queue:
        window.queue = [*window.queue, opponent]
    record_table_roll(
        state, player_id, "fire_team", "Fire Team", results,
        summary=f"{total} hit(s) after the reroll.",
    )


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
