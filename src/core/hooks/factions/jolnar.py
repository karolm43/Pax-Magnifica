"""Universities of Jol-Nar — komplet komponentów frakcji (RULES.md 62.3).

Teksty w docstringach to cytaty z assetów (``catalog.faction_bundle("jolnar")``, ``units``).
Rulingi: ``docs/rules_tirules/F_jol_nar.md``. Gracz decyduje sam (RULES.md 56): „you may” = oferta
albo użycie w oknie (RULES.md 62.0), wybory celów liczy silnik.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    active_effects,
    economy,
    exhaust,
    faction_components,
    faction_units,
    invasion,
    leaders,
    promissory_play,
    research_offer,
    rules_hooks,
    space_cannon,
    technology,
    triggers,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, WindowType
from src.core.planet_stats import resources_of
from src.core.reaction_cards import OpenWindow, window_provider
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_COMBAT_NATURAL_EXTRA_HITS,
    POINT_COMBAT_ROLL_MODIFIER,
    POINT_MOVEMENT_EXTRA_ADJACENT,
    POINT_STRATEGY_SECONDARY_AS_PRIMARY,
    POINT_TECHNOLOGY_FREE_IGNORES,
    POINT_TECHNOLOGY_SPECIALTY_PAYS,
    SOURCE_BREAKTHROUGH,
    SOURCE_EFFECT,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_TECHNOLOGY,
    SOURCE_UNIT,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.strategy_cards import technology as technology_card
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

FACTION = "jolnar"
AGENT = "jolnaragent"
COMMANDER = "jolnarcommander"
HERO = "jolnarhero"
FLAGSHIP = "jolnar_flagship"
MECH = "jolnar_mech"
ERS = "ers"
SCC = "scc"
RESEARCH_AGREEMENT = "ra"
BREAKTHROUGH = "jolnarbt"

SCC_EFFECT = f"technologies:{SCC}"  # data: position - aktywny system połączony ze wszystkimi
COMMANDER_USED = f"leaders:{COMMANDER}:used"  # data: kind - jeden przerzut na rodzaj rzutu
_ERS_TRADE_GOODS = 4  # „gain 4 trade goods”
_FLAGSHIP_NATURAL = 9  # „each result of 9 or 10, before applying modifiers”
_FLAGSHIP_EXTRA = 2  # „produces 2 additional hits”
_COMMANDER_TECHS = 8  # „Own 8 technologies.”
_KEEP = "keep"

_ROLL_LABELS = {
    "offense": "Space Cannon Offense",
    "defense": "Space Cannon Defense",
    "bombardment": "Bombardment",
}


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _planet_name(registry: Any, planet: str) -> str:
    return registry.planets[planet].name if planet in registry.planets else planet


def _tech_name(registry: Any, tech_id: str) -> str:
    tech = registry.technologies.get(tech_id)
    return tech.name if tech is not None else tech_id


# ------------------------------------------------------------- Fragile, mech, flagowiec


@register(
    POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_FACTION, FACTION), HookKind.MODIFY,
    covers="abilities:fragile",
)
def fragile(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> int:
    """Fragile: Apply -1 to the result of each of your unit's combat rolls (obowiązkowo)."""
    return -1


@register(
    POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_UNIT, MECH), HookKind.MODIFY,
    covers=f"units:{MECH}",
)
def shield_paling(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Shield Paling: Your infantry on this planet are not affected by your Fragile faction
    ability (znosi −1 piechocie na planecie z mechem; sam mech nadal ma Fragile — F_jol_nar)."""
    if ctx.get("kind") != "ground" or ctx.get("base_type") != "infantry":
        return 0
    system = state.systems.get(str(ctx.get("position")))
    planet = str(ctx.get("planet") or "")
    if system is None or not planet:
        return 0
    if faction_units.variant_of(state, _registry(), player_id, "mech") != MECH:
        return 0
    mechs = system.planet_units.get(planet, {}).get(player_id, {}).get("mech", 0)
    return 1 if mechs > 0 else 0


@register(
    POINT_COMBAT_NATURAL_EXTRA_HITS, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.MODIFY,
    covers=f"units:{FLAGSHIP}",
)
def hylarim(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    """J.N.S. Hylarim: When making a combat roll for this ship, each result of 9 or 10, before
    applying modifiers, produces 2 additional hits."""
    if ctx.get("base_type") != "flagship":
        return 0
    return _FLAGSHIP_EXTRA if int(ctx.get("natural", 0)) >= _FLAGSHIP_NATURAL else 0


# ------------------------------------------------------------------- Analytical, Brilliant


@register(
    POINT_TECHNOLOGY_FREE_IGNORES, HookSource(SOURCE_FACTION, FACTION), HookKind.MODIFY,
    covers="abilities:analytical",
)
def analytical(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> int:
    """Analytical: When you research a technology that is not a unit upgrade technology: You may
    ignore 1 prerequisite."""
    return 0 if ctx.get("unit_upgrade") == "true" else 1


@register(
    POINT_STRATEGY_SECONDARY_AS_PRIMARY, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
    covers="abilities:brilliant",
)
def brilliant(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Brilliant: When you spend a command token to resolve the secondary ability of the
    "Technology" strategy card: You may resolve the primary ability instead."""
    return int(ctx.get("initiative", 0)) == technology_card.INITIATIVE


# ---------------------------------------------------------------------- E-Res Siphons


def _has_ships(state: GameState, player_id: str, position: str) -> bool:
    system = state.systems.get(position)
    if system is None:
        return False
    return any(
        n > 0 and is_space_unit(bt) for bt, n in system.space_units.get(player_id, {}).items()
    )


def _other_activated(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") != player_id and _has_ships(
        state, player_id, str(ctx.get("position"))
    )


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, ERS),
    condition=_other_activated, covers=f"technologies:{ERS}", label="E-Res Siphons",
)
def e_res_siphons(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """E-Res Siphons: After another player activates a system that contains 1 or more of your
    ships, gain 4 trade goods."""
    economy.gain_trade_goods(state, player_id, _ERS_TRADE_GOODS)


# --------------------------------------------------------------- Spatial Conduit Cylinder


def _unit_positions(state: GameState, player_id: str) -> set[str]:
    """Systemy z jakąkolwiek jednostką gracza (przestrzeń albo planety)."""
    found: set[str] = set()
    for position, system in state.systems.items():
        if any(n > 0 for n in system.space_units.get(player_id, {}).values()) or any(
            n > 0
            for by_player in system.planet_units.values()
            for n in by_player.get(player_id, {}).values()
        ):
            found.add(position)
    return found


def _scc_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("player") != player_id:
        return False
    if SCC in state.players[player_id].exhausted_technologies:
        return False
    units = _unit_positions(state, player_id)
    position = str(ctx.get("position"))
    return position in units and bool(units - {position})


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_TECHNOLOGY, SCC),
    optional=True, condition=_scc_ready, covers=f"technologies:{SCC}",
    label="Spatial Conduit Cylinder",
)
def spatial_conduit(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Spatial Conduit Cylinder: You may exhaust this card after you activate a system that
    contains 1 or more of your units; that system is adjacent to all other systems that contain 1
    or more of your units during this activation."""
    exhaust.exhaust_technology(state, player_id, SCC)
    active_effects.add_effect(
        state, SCC_EFFECT, Duration.TACTICAL_ACTION, owner=player_id,
        data={"position": str(ctx["position"])},
    )


@register(POINT_MOVEMENT_EXTRA_ADJACENT, HookSource(SOURCE_EFFECT, SCC_EFFECT), HookKind.FORBID)
def conduit_adjacency(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> set[str]:
    """Aktywny system sąsiaduje ze wszystkimi systemami z jednostkami gracza (i odwrotnie)."""
    position = str(ctx.get("position"))
    found: set[str] = set()
    units = _unit_positions(state, player_id)
    for effect in active_effects.effects_for(state, player_id, SCC_EFFECT):
        active = str(effect.data.get("position"))
        if position == active:
            found |= units - {active}
        elif position in units:
            found.add(active)
    return found


# ------------------------------------------------------------------- Research Agreement


@window_provider
def after_research(state: GameState) -> list[OpenWindow]:
    """„After <gracz> researches a technology”: badania od ostatniej akcji (``last_research``)."""
    return [
        OpenWindow(
            GameEvent.TECHNOLOGY_RESEARCH, Moment.AFTER,
            {"player": entry["player"], "technology": entry["technology"]},
        )
        for entry in state.last_research
        if entry.get("player") in state.players
    ]


def _jolnar_player(state: GameState) -> str | None:
    return next((pid for pid, p in state.players.items() if p.faction == FACTION), None)


def _agreement_techs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[str]:
    """Technologie zbadane przez Jol-Nar od ostatniej akcji, które posiadacz notki może zdobyć."""
    owner = _jolnar_player(state)
    if owner is None:
        return []
    pool = technology.tech_pool(state, registry, player_id)
    owned = set(state.players[player_id].technologies)
    found: list[str] = []
    for entry in state.last_research:
        tech_id = entry.get("technology", "")
        tech = registry.technologies.get(tech_id)
        if entry.get("player") != owner or tech is None or tech.faction:
            continue  # „not a faction technology”
        if tech_id in pool and tech_id not in owned and tech_id not in found:
            found.append(tech_id)
    return found


@promissory_play.condition(RESEARCH_AGREEMENT)
def _agreement_condition(
    state: GameState, registry: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> str | None:
    if not _agreement_techs(state, registry, player_id):
        return "The Jol-Nar player has not just researched a technology you can gain."
    return None


@register_effect_inputs(f"promissory_notes:{RESEARCH_AGREEMENT}")
def agreement_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    options = [
        oi.option(t, _tech_name(registry, t))
        for t in _agreement_techs(state, registry, player_id)
    ]
    return [oi.choice("technology", "Technology to gain", options)]


@register_effect(f"promissory_notes:{RESEARCH_AGREEMENT}")
def research_agreement(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Research Agreement: After the Jol-Nar player researches a technology that is not a faction
    technology: Gain that technology. Then, return this card to the Jol-Nar player."""
    tech_id = str(params.get("technology") or "")
    if tech_id not in _agreement_techs(state, registry, player_id):
        raise ValueError("Choose a technology the Jol-Nar player has just researched.")
    technology.grant_technology(state, player_id, tech_id)


# ------------------------------------------------------------------------ Doctor Sucaban


def research_payer(state: GameState) -> str | None:
    """Gracz, który TERAZ płaci zasobami za badanie (``None`` = nikt).

    Krok ``research_paid`` primary karty Technology, secondary bieżącego respondenta albo
    czekająca decyzja badania z komponentu (Focused Research - ``core/research_offer``) - RULES.md
    62.3. We wszystkich tych chwilach zapłata jeszcze NIE nastąpiła (Sucaban = zniżka).
    """
    payer = research_offer.pending_payer(state)
    if payer is not None:
        return payer
    pending = state.pending_strategy
    if (
        pending is not None
        and pending.initiative == technology_card.INITIATIVE
        and pending.step == technology_card.STEP_PAID
    ):
        return pending.owner_id
    window = state.pending_window
    if (
        window is not None
        and window.window_type is WindowType.STRATEGY_SECONDARY
        and int(window.context.get("initiative", 0)) == technology_card.INITIATIVE
    ):
        return window.current_responder
    return None


def _infantry_spots(state: GameState, player_id: str) -> list[tuple[str, str, int]]:
    """``(pozycja, strefa, liczba)`` piechoty gracza na planszy."""
    spots: list[tuple[str, str, int]] = []
    for position, system in sorted(state.systems.items()):
        in_space = system.space_units.get(player_id, {}).get("infantry", 0)
        if in_space > 0:
            spots.append((position, "space", in_space))
        for planet, by_player in sorted(system.planet_units.items()):
            count = by_player.get(player_id, {}).get("infantry", 0)
            if count > 0:
                spots.append((position, planet, count))
    return spots


def refund_payer(state: GameState) -> str | None:
    """Gracz, który WŁAŚNIE zapłacił zasobami za badanie rozstrzygnięte jednym ruchem (Reveal
    Prototype, Enigmatic Device, karta Technology) - Sucaban działa wtedy jako zwrot (62.3)."""
    trace = state.last_research_payment
    if trace is None or trace.get("reduced") or int(trace.get("cost", 0)) <= 0:
        return None
    player = trace.get("player")
    return player if isinstance(player, str) and player in state.players else None


def _sucaban_target(state: GameState) -> tuple[str, str] | None:
    """``(gracz, tryb)``: ``before`` = przed zapłatą (zniżka), ``after`` = po zapłacie (zwrot)."""
    payer = research_payer(state)
    if payer is not None:
        return payer, "before"
    payer = refund_payer(state)
    return (payer, "after") if payer is not None else None


@research_offer.register_potential_discount
def _sucaban_potential(state: GameState, registry: StaticDataRegistry, payer: str) -> int:
    """Ile Doctor Sucaban MOŻE obniżyć koszt badania płacącego: tyle, ile ma on piechoty na
    planszy - o ile jakiś gracz ma gotowego Sucabana (bramka zagrywalności Focused Research)."""
    ready = any(
        AGENT in leaders.leaders_of(registry, player)
        and leaders.is_ready(state, registry, pid, AGENT)
        for pid, player in state.players.items()
    )
    if not ready:
        return 0
    return sum(count for _pos, _zone, count in _infantry_spots(state, payer))


@faction_components.window_use("leader", AGENT)
def _agent_window(state: GameState, _registry: StaticDataRegistry, _player_id: str) -> str | None:
    target = _sucaban_target(state)
    if target is None:
        return "Use Doctor Sucaban when a player spends resources to research a technology."
    if not _infantry_spots(state, target[0]):
        return "That player has no infantry on the game board."
    return None


@register_effect(f"leaders:{AGENT}")
def doctor_sucaban(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Doctor Sucaban: When a player spends resources to research: You may exhaust this card to
    allow that player to remove any number of their infantry from the game board. For each unit
    removed, reduce the resources spent by 1. (Decyzję o piechocie podejmuje badający.)"""
    target = _sucaban_target(state)
    if target is None:
        raise ValueError("Nobody is spending resources to research right now.")
    payer, mode = target
    if mode == "after" and state.last_research_payment is not None:
        state.last_research_payment["reduced"] = True  # jeden zwrot na zapłatę
    triggers.fire(
        state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "ability": f"leaders:{AGENT}", "target": payer, "mode": mode},
    )


def _agent_target(_state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def sucaban_inputs(
    state: GameState, registry: Any, decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Ile piechoty zdjąć z każdego miejsca (każda = −1 do kosztu badania); po zapłacie także
    co odzyskać (planety do odświeżenia, TG)."""
    inputs: list[dict[str, Any]] = []
    for position, zone, count in _infantry_spots(state, decider):
        where = "space" if zone == "space" else _planet_name(registry, zone)
        inputs.append(
            oi.number(f"inf:{position}:{zone}", f"Infantry to remove ({where})", 0, count)
        )
    trace = state.last_research_payment if ctx.get("mode") == "after" else None
    if trace is not None:
        paid = [str(p) for p in trace.get("planets", [])]
        options = [
            oi.option(p, f"{_planet_name(registry, p)} ({resources_of(state, registry, p)})")
            for p in paid
        ]
        if options:
            inputs.append(oi.multi("refund_planets", "Planets to ready (refund)", options, 0,
                                   len(options)))
        spent_tg = int(trace.get("trade_goods", 0))
        if spent_tg:
            inputs.append(oi.number("refund_trade_goods", "Trade goods back", 0, spent_tg))
    return inputs


def _refund(state: GameState, registry: Any, target: str, removed: int,
            params: Mapping[str, Any]) -> None:
    """Zwrot po zapłacie: zostaje wydane co najmniej ``koszt - zdjęta piechota``."""
    trace = state.last_research_payment
    if trace is None:
        return
    paid_planets = [str(p) for p in trace.get("planets", [])]
    planets = [str(p) for p in params.get("refund_planets") or [] if str(p) in paid_planets]
    trade_goods = min(int(params.get("refund_trade_goods") or 0), int(trace.get("trade_goods", 0)))
    back = sum(resources_of(state, registry, p) for p in planets) + trade_goods
    if not back:
        return
    spent = sum(resources_of(state, registry, p) for p in paid_planets) + int(
        trace.get("trade_goods", 0)
    )
    need = max(0, int(trace.get("cost", 0)) - removed)
    if spent - back < need:
        raise ValueError(
            f"You must still spend at least {need} resources - refund less."
        )
    exhaust.ready_planets(state, target, planets)
    economy.refund_trade_goods(state, target, trade_goods)


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    where={"ability": f"leaders:{AGENT}"}, decide=True, decider=_agent_target,
    inputs=sucaban_inputs, covers=f"leaders:{AGENT}", label="Doctor Sucaban: remove infantry",
)
def sucaban_remove(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    target = str(ctx["decider"])
    removed = 0
    for key, value in ctx.get("params", {}).items():
        if not key.startswith("inf:") or not value:
            continue
        _, position, zone = key.split(":", 2)
        system = state.systems.get(position)
        if system is None:
            continue
        count = min(int(value), unit_ops.count_in_zone(system, zone, target, "infantry"))
        if count > 0:
            unit_ops.remove_units(state, system, zone, target, "infantry", count, UnitCause.REMOVED)
            removed += count
    if ctx.get("mode") == "after":
        _refund(state, _registry(), target, removed, ctx.get("params", {}))
        return
    if removed:
        active_effects.add_effect(
            state, technology.RESEARCH_DISCOUNT, Duration.TURN, owner=target,
            data={"amount": removed},
        )


# ----------------------------------------------------------------------------- Agnlan Oln


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Own 8 technologies."""
    return len(state.players[player_id].technologies) >= _COMMANDER_TECHS


def pending_unit_roll(state: GameState, player_id: str) -> tuple[str, list[dict[str, Any]]] | None:
    """Rzut zdolności jednostki gracza czekający na straty: ``(rodzaj, wpisy)`` albo ``None``."""
    shot = space_cannon.pending_hits(state)
    if shot is not None and shot.roller == player_id:
        return "offense", [dict(r) for r in shot.rolls]
    defense = invasion.pending_defense_entries(state)
    if defense is not None and defense[0] == player_id:
        return "defense", defense[1]
    bombard = invasion.pending_bombardment_entries(state)
    if bombard is not None and bombard[0] == player_id:
        return "bombardment", bombard[1]
    return None


def _commander_used(state: GameState, player_id: str, kind: str) -> bool:
    return any(
        e.data.get("kind") == kind
        for e in active_effects.effects_for(state, player_id, COMMANDER_USED)
    )


@faction_components.window_use("leader", COMMANDER)
def _commander_window(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> str | None:
    pending = pending_unit_roll(state, player_id)
    if pending is None:
        return "Use Agnlan Oln right after you roll dice for a unit ability."
    if _commander_used(state, player_id, pending[0]):
        return "Agnlan Oln was already used for this roll."
    return None


@register_effect_inputs(f"leaders:{COMMANDER}")
def commander_inputs(
    state: GameState, _registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    pending = pending_unit_roll(state, player_id)
    if pending is None:
        return []
    kind, entries = pending
    options = [
        oi.option(
            f"{e_index}:{d_index}", f"{entry.get('name', entry.get('baseType', ''))}: {value}",
            meta=oi.die_meta(int(value), int(entry["hitsOn"]), str(entry.get("baseType", ""))),
        )
        for e_index, entry in enumerate(entries)
        for d_index, value in enumerate(entry.get("dice", []))
    ]
    label = f"{_ROLL_LABELS.get(kind, kind)} dice to reroll"
    return [oi.multi("dice", label, options, 1, len(options))]


@register_effect(f"leaders:{COMMANDER}")
def agnlan_oln(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Agnlan Oln: After you roll dice for a unit ability: You may reroll any of those dice."""
    pending = pending_unit_roll(state, player_id)
    if pending is None:
        raise ValueError("You have no unit ability roll to reroll.")
    kind = pending[0]
    picks: set[tuple[int, int]] = set()
    for value in params.get("dice") or []:
        e_index, _, d_index = str(value).partition(":")
        picks.add((int(e_index), int(d_index)))
    if not picks:
        raise ValueError("Choose at least 1 die to reroll.")
    source = ("agnlan_oln", "Agnlan Oln")
    if kind == "offense":
        space_cannon.reroll_pending(state, picks, source)
    elif kind == "defense":
        invasion.reroll_pending_defense(state, picks, source)
    else:
        invasion.reroll_pending_bombardment(state, picks, source)
    active_effects.add_effect(
        state, COMMANDER_USED, Duration.TACTICAL_ACTION, owner=player_id, data={"kind": kind}
    )


def _afb_rolled(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    combat = state.active_combat
    return (
        ctx.get("player") == player_id
        and combat is not None
        and bool(combat.afb.get(player_id))
    )


def afb_inputs(
    state: GameState, _registry: Any, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Kości AFB gracza do przerzutu (każda osobno)."""
    combat = state.active_combat
    entries = combat.afb.get(player_id, []) if combat is not None else []
    options = [
        oi.option(
            f"{e_index}:{d_index}", f"{entry.get('name', entry.get('baseType', ''))}: {value}",
            meta=oi.die_meta(int(value), int(entry["hitsOn"]), str(entry.get("baseType", ""))),
        )
        for e_index, entry in enumerate(entries)
        for d_index, value in enumerate(entry.get("dice", []))
    ]
    return [oi.multi("dice", "Anti-Fighter Barrage dice to reroll", options, 1, len(options))]


@on_event(
    GameEvent.UNIT_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    where={"ability": "afb"}, optional=True, condition=_afb_rolled, inputs=afb_inputs,
    label="Agnlan Oln: reroll Anti-Fighter Barrage dice",
)
def agnlan_oln_afb(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Agnlan Oln (AFB): walka czeka po rzucie AFB na tę ofertę (``battle.resolve_afb``)."""
    combat = state.active_combat
    if combat is None:
        return
    picks: set[tuple[int, int]] = set()
    for value in ctx.get("params", {}).get("dice") or []:
        e_index, _, d_index = str(value).partition(":")
        picks.add((int(e_index), int(d_index)))
    fresh, _ = space_cannon.reroll_entries(
        state, combat.afb.get(player_id, []), roller=player_id, picks=picks,
        source=("agnlan_oln", "Agnlan Oln"),
    )
    combat.afb = {**combat.afb, player_id: fresh}


# ------------------------------------------------------------- Rin — Genetic Memory (hero)


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Dla każdej posiadanej technologii z kolorem: zostaw albo zamień na nieposiadaną tego
    samego koloru z talii gracza (zamiany jednoczesne - F_jol_nar)."""
    owned = state.players[player_id].technologies
    pool = technology.tech_pool(state, registry, player_id)
    inputs: list[dict[str, Any]] = []
    for tech_id in owned:
        tech = registry.technologies.get(tech_id)
        color = technology.tech_color(tech) if tech is not None else None
        if tech is None or color is None or technology.UNIT_UPGRADE in tech.types:
            continue
        options = [oi.option(_KEEP, f"Keep {tech.name}")] + [
            oi.option(other.id, other.name)
            for other in sorted(pool.values(), key=lambda t: t.name)
            if other.id not in owned and technology.tech_color(other) == color
            and technology.UNIT_UPGRADE not in other.types
        ]
        inputs.append(oi.choice(f"tech:{tech_id}", f"Replace {tech.name}", options))
    return inputs


@register_effect(f"leaders:{HERO}")
def genetic_memory(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Rin, the Master's Legacy — Genetic Memory: For each non-unit upgrade technology you own,
    you may replace that technology with any technology of the same color from the deck. Then,
    purge this card. (Bez prerekwizytów; nie wyzwala Research Agreement — to nie badanie.)"""
    swaps: list[tuple[str, str]] = []
    for key, value in params.items():
        if key.startswith("tech:") and value and value != _KEEP:
            swaps.append((key[5:], str(value)))
    new_ids = [new for _, new in swaps]
    if len(set(new_ids)) != len(new_ids):
        raise ValueError("Each replacement must be a different technology.")
    for old, _ in swaps:
        technology.return_technology(state, player_id, old)
    for _, new in swaps:
        technology.grant_technology(state, player_id, new)


# ------------------------------------------------------------ Specialist Compounds (BT)


@register(
    POINT_TECHNOLOGY_SPECIALTY_PAYS, HookSource(SOURCE_BREAKTHROUGH, BREAKTHROUGH),
    HookKind.PERMIT, covers=f"breakthroughs:{BREAKTHROUGH}",
)
def specialist_compounds(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Specialist Compounds: When you research technology using the 'Technology' strategy card,
    you may exhaust a planet that has a technology specialty instead of spending resources; if you
    do, you must research a technology of that color."""
    return True
