"""Trwałe skutki PRAW agendy w grze (RULES.md 51.6) - hooki punktów reguł bazowych.

Źródło: ``HookSource(agenda, <id>)`` posiada każdy gracz, dopóki prawo leży w grze (albo karta
jest właśnie rozstrzygana - wtedy ``agenda_laws`` może nie mieć wyniku „For"). Dlatego każdy hook
sprawdza WYNIK prawa (``_law_for`` / ``_owner``). Teksty kart: ``assets/data/agendas/``,
rulingi: ``docs/rules_tirules/C_agendas.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    action_budget,
    agenda_phase,
    board_graph,
    card_draw,
    command_tokens,
    economy,
    rules_hooks,
    strategy_phase,
    tactical,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, Phase, ProductionGrant
from src.core.hooks.action_card_inputs import Input, _choice, _option, _player_label
from src.core.hooks.agendas_common import (
    agenda_source,
    bound_registry,
    chosen_units,
    covers,
    destroy_choice_input,
    destroy_units,
    effect_key,
    effect_source,
    lose_points,
    unit_instances,
)
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    HookKind,
    on_event,
    register,
    register_unit_ability_filter,
)
from src.core.unit_catalog import is_space_unit

# --- Stałe z tekstów kart ------------------------------------------------------------------
FLEET_REGULATIONS_CAP = 4  # Fleet Regulations: „cannot have more than 4 tokens in their fleet pool"
_SANCTIONS_HAND = 3  # Executive Sanctions: „maximum of 3 action cards"
_PROPHECY_FIGHTERS = 2  # Prophecy of Ixth: „unless they produce 2 or more fighters"
_CRAFTY = "crafty"  # Yssaril: bez limitu kart - Executive Sanctions go nie dotyczy (C_agendas)
_NEXUS_NAME = "wormhole nexus"
_ALPHA_BETA = frozenset({"ALPHA", "BETA"})


def _law(state: GameState, card: str) -> str | None:
    return state.decks.agenda_laws.get(card)


def _law_for(state: GameState, card: str) -> bool:
    return _law(state, card) == "for"


def _owner(state: GameState, card: str) -> str | None:
    outcome = _law(state, card)
    return outcome if outcome in state.players else None


def _faction(state: GameState, player_id: str) -> str:
    return state.players[player_id].faction or ""


def _has_ability(state: GameState, player_id: str, ability: str) -> bool:
    registry = rules_hooks.bound_registry()
    faction = registry.factions.get(_faction(state, player_id)) if registry is not None else None
    return faction is not None and ability in faction.abilities


def _params(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    params = ctx.get("params")
    return params if isinstance(params, Mapping) else {}


# =========================================================================================
# Głosowanie i karty akcji
# =========================================================================================


# Representative Government - For: 1 vote each, no planets, no additional votes.
@register(rules_hooks.POINT_AGENDA_SINGLE_VOTE, agenda_source("rep_govt"), HookKind.PERMIT,
          covers=covers("rep_govt"))
def _rep_govt(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> bool:
    return _law_for(state, "rep_govt")


# Executive Sanctions - For: max 3 action cards in hand (nie Yssaril).
@register(rules_hooks.POINT_HAND_LIMIT, agenda_source("sanctions"), HookKind.MODIFY,
          covers=covers("sanctions"))
def _sanctions(state: GameState, pid: str, ctx: Mapping[str, Any]) -> int:
    if not _law_for(state, "sanctions") or _has_ability(state, pid, _CRAFTY):
        return 0
    return min(0, _SANCTIONS_HAND - int(ctx.get("base", 0)))


# Political Censure - the owner cannot play action cards; losing the card costs 1 VP.
@register(rules_hooks.POINT_ACTION_CARDS_FORBIDDEN, agenda_source("censure"), HookKind.FORBID,
          covers=covers("censure"))
def _censure_ban(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> set[str]:
    if _owner(state, "censure") == pid:
        return {"Political Censure: you cannot play action cards."}
    return set()


@on_event(GameEvent.LAW_DISCARDED, Moment.WHEN, agenda_source("censure"), where={"law": "censure"},
          condition=lambda s, p, c: p == c.get("outcome"), covers=covers("censure"),
          label="Political Censure")
def _censure_lost(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    lose_points(state, pid, 1, source="agendas:censure")


# Classified Document Leaks - po odrzuceniu prawa cel zostaje w grze, ale nie da się go zdobyć
# (C_agendas: „not returned to the original player, and it is no longer scorable").
@on_event(GameEvent.LAW_DISCARDED, Moment.WHEN, agenda_source("classified"),
          where={"law": "classified"}, condition=lambda s, p, c: p == s.speaker_id,
          covers=covers("classified"), label="Classified Document Leaks")
def _classified_discarded(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    from src.core import objectives

    objective = str(ctx.get("outcome") or "")
    if objective in state.objectives.revealed:
        objectives.retire(state, objective)


# Committee Formation - before voting on an "elect a player" agenda the owner may discard this
# card to choose the elected player; players do not vote.
def _committee_ready(state: GameState, pid: str, ctx: Mapping[str, Any]) -> bool:
    return (
        _owner(state, "committee") == pid
        and agenda_phase.is_player_election(state)
        and state.agenda is not None
        and not state.agenda.votes
    )


def _committee_inputs(
    state: GameState, registry: StaticDataRegistry, _pid: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    outcomes = [o for o in (state.agenda.outcomes if state.agenda else []) if o in state.players]
    options = [_option(p, _player_label(state, registry, p)) for p in outcomes]
    return [_choice("player", "Player to elect", options)]


@on_event(GameEvent.AGENDA_REVEALED, Moment.AFTER, agenda_source("committee"),
          condition=_committee_ready, optional=True, inputs=_committee_inputs,
          covers=covers("committee"), label="Committee Formation")
def _committee(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    chosen = str(_params(ctx).get("player") or "")
    if chosen not in state.players or _owner(state, "committee") != pid:
        raise ValueError("Choose a player to elect ('player').")
    agenda_phase.remove_law(state, "committee")
    agenda_phase.elect_without_vote(state, bound_registry(), chosen)


# =========================================================================================
# Faza strategii
# =========================================================================================


# Checks and Balances - For: the chosen strategy card goes to another player.
@register(rules_hooks.POINT_STRATEGY_GIVE_CHOSEN, agenda_source("checks"), HookKind.PERMIT,
          covers=covers("checks"))
def _checks(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> bool:
    return _law_for(state, "checks")


# Checks and Balances - Against: each player readies only 3 planets at the end of this phase.
_CHECKS_READY = 3


@on_event(GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.DURING, agenda_source("checks"),
          where={"agenda": "checks", "outcome": "against"}, covers=covers("checks"),
          label="Checks and Balances")
def _checks_against(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    from src.core import active_effects

    active_effects.add_effect(state, effect_key("checks", "against"), Duration.PHASE, owner=pid)


@register(rules_hooks.POINT_PLANETS_READY_LIMIT, effect_source("checks", "against"),
          HookKind.FORBID, covers=covers("checks"))
def _checks_limit(_state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> set[str]:
    return {str(_CHECKS_READY)}


def _checks_inputs(
    state: GameState, registry: StaticDataRegistry, pid: str, ctx: Mapping[str, Any]
) -> list[Input]:
    from src.core.hooks.action_card_inputs import _planet_label
    from src.core.offer_inputs import multi

    limit = int(ctx.get("limit", _CHECKS_READY))
    exhausted = list(state.players[pid].exhausted_planets)
    options = [_option(p, _planet_label(state, registry, p)) for p in exhausted]
    return [multi("planets", f"Planets to ready ({limit})", options, limit, limit)]


@on_event(GameEvent.COMPONENT_READIED, Moment.WHEN, effect_source("checks", "against"),
          where={"component": "planets"}, decide=True, inputs=_checks_inputs,
          covers=covers("checks"), label="Checks and Balances: ready 3 planets")
def _checks_ready(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    from src.core import active_effects, exhaust

    picks = [str(p) for p in _params(ctx).get("planets", [])]
    exhausted = state.players[pid].exhausted_planets
    exhaust.ready_planets(state, pid, [p for p in picks if p in exhausted])
    active_effects.remove_by_key(state, effect_key("checks", "against"), owner=pid)


# Imperial Arbiter - at the end of the strategy phase the owner may discard this card to swap
# 1 of their strategy cards with 1 of another player's.
def _arbiter_ready(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> bool:
    return (
        state.phase is Phase.STRATEGY
        and _owner(state, "arbiter") == pid
        and strategy_phase.next_strategy_picker(state) is None
        and bool(state.players[pid].strategy_cards)
    )


def _arbiter_inputs(
    state: GameState, registry: StaticDataRegistry, pid: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    # Pełne nazwy kart (np. „3 Politics”), nie same numery inicjatywy.
    names = {sc.initiative: sc.name for sc in registry.strategy_card_set()}

    def card(n: int) -> str:
        return f"{n} {names[n]}" if n in names else str(n)

    options = []
    for mine in state.players[pid].strategy_cards:
        for other, player in state.players.items():
            if other == pid:
                continue
            for theirs in player.strategy_cards:
                label = (f"Your {card(mine)} <-> {card(theirs)} - "
                         f"{_player_label(state, registry, other)}")
                options.append(_option(f"{mine}|{other}|{theirs}", label))
    return [_choice("swap", "Strategy cards to swap", options)]


@on_event(GameEvent.STRATEGY_CARD_CHOSEN, Moment.AFTER, agenda_source("arbiter"),
          condition=_arbiter_ready, optional=True, inputs=_arbiter_inputs,
          covers=covers("arbiter"), label="Imperial Arbiter")
def _arbiter(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    mine_raw, other, theirs_raw = str(_params(ctx).get("swap") or "||").split("|")
    mine, theirs = int(mine_raw or 0), int(theirs_raw or 0)
    me, them = state.players[pid], state.players.get(other)
    if them is None or mine not in me.strategy_cards or theirs not in them.strategy_cards:
        raise ValueError("Choose 2 strategy cards to swap ('swap').")
    me.strategy_cards = sorted([c for c in me.strategy_cards if c != mine] + [theirs])
    them.strategy_cards = sorted([c for c in them.strategy_cards if c != theirs] + [mine])
    agenda_phase.remove_law(state, "arbiter")


# =========================================================================================
# Ruch, walka, jednostki
# =========================================================================================


def _wormhole_law_immune(state: GameState, pid: str) -> bool:
    """Creuss are not affected by Enforced Travel Ban / Nexus Sovereignty (RULES.md 62.19)."""
    return rules_hooks.permits(rules_hooks.POINT_MOVEMENT_WORMHOLE_LAWS_IMMUNE, state, pid)


def _nexus_positions(state: GameState) -> set[str]:
    registry = rules_hooks.bound_registry()
    if registry is None:
        return set()
    found = set()
    for position in board_graph.board_positions(state):  # nexus nie musi mieć wpisu w stanie
        definition = registry.systems.get(board_graph.system_id_at(state, position))
        if definition is not None and (definition.name or "").strip().lower() == _NEXUS_NAME:
            found.add(position)
    return found


# Enforced Travel Ban - For: alpha and beta wormholes have no effect during movement.
@register(rules_hooks.POINT_MOVEMENT_WORMHOLES_BLOCKED, agenda_source("travel_ban"),
          HookKind.FORBID, covers=covers("travel_ban"))
def _travel_ban(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> frozenset[str]:
    if not _law_for(state, "travel_ban") or _wormhole_law_immune(state, pid):
        return frozenset()
    if _law_for(state, "wormhole_recon"):
        return frozenset()  # C_agendas: przy Wormhole Reconstruction zakaz nie działa
    return _ALPHA_BETA


# Nexus Sovereignty - For: alpha/beta wormholes in the Wormhole Nexus have no effect in movement.
@register(rules_hooks.POINT_MOVEMENT_WORMHOLES_BLOCKED, agenda_source("nexus"), HookKind.FORBID,
          covers=covers("nexus"))
def _nexus(state: GameState, pid: str, ctx: Mapping[str, Any]) -> frozenset[str]:
    if not _law_for(state, "nexus") or _wormhole_law_immune(state, pid):
        return frozenset()
    nexus = _nexus_positions(state)
    if ctx.get("position") in nexus or ctx.get("neighbor") in nexus:
        return _ALPHA_BETA
    return frozenset()


# Wormhole Reconstruction - For: all alpha and beta systems are adjacent to each other.
@register(rules_hooks.POINT_MOVEMENT_ALPHA_BETA_ADJACENT, agenda_source("wormhole_recon"),
          HookKind.PERMIT, covers=covers("wormhole_recon"))
def _recon(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> bool:
    return _law_for(state, "wormhole_recon")


# Shared Research - For: each player's units can move through nebulae.
@register(rules_hooks.POINT_MOVEMENT_THROUGH_NEBULA, agenda_source("shared_research"),
          HookKind.PERMIT, covers=covers("shared_research"))
def _shared_research(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> bool:
    return _law_for(state, "shared_research")


# Articles of War - For: all mechs lose their printed abilities except SUSTAIN DAMAGE.
@register_unit_ability_filter
def _articles(state: GameState, _pid: str) -> frozenset[str]:
    return frozenset({"mech"}) if _law_for(state, "articles_war") else frozenset()


# Conventions of War - For: no BOMBARDMENT against units on cultural planets.
@register(rules_hooks.POINT_BOMBARDMENT_FORBIDDEN_TRAITS, agenda_source("conventions"),
          HookKind.FORBID, covers=covers("conventions"))
def _conventions(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> set[str]:
    return {"cultural"} if _law_for(state, "conventions") else set()


# Homeland Defense Act - For: any number of PDS on planets you control.
@register(rules_hooks.POINT_PDS_UNLIMITED, agenda_source("defense_act"), HookKind.PERMIT,
          covers=covers("defense_act"))
def _defense_act(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> bool:
    return _law_for(state, "defense_act")


# C_agendas: po odrzuceniu prawa gracze zdejmują PDS ponad 2 na planecie (bez „destroyed").
_PDS_PER_PLANET = 2  # R_structures: „a maximum of two PDS units on each planet"


@on_event(GameEvent.LAW_DISCARDED, Moment.WHEN, agenda_source("defense_act"),
          where={"law": "defense_act", "outcome": "for"},
          condition=lambda s, p, c: p == s.speaker_id, covers=covers("defense_act"),
          label="Homeland Defense Act")
def _defense_act_discarded(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> None:
    from src.core import unit_ops

    for system in state.systems.values():
        for planet, by_player in list(system.planet_units.items()):
            for player, units in list(by_player.items()):
                excess = units.get("pds", 0) - _PDS_PER_PLANET
                if excess > 0:
                    unit_ops.remove_units(
                        state, system, planet, player, "pds", excess, unit_ops.UnitCause.REMOVED
                    )


# Fleet Regulations - For: no more than 4 tokens in the fleet pool.
@register(rules_hooks.POINT_FLEET_POOL_TOKEN_CAP, agenda_source("regulations"), HookKind.MODIFY,
          covers=covers("regulations"))
def _regulations(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> int:
    return FLEET_REGULATIONS_CAP if _law_for(state, "regulations") else 0


# Regulated Conscription - For: 1 fighter / infantry for its cost instead of 2.
@register(rules_hooks.POINT_PRODUCTION_UNITS_PER_COST, agenda_source("conscription"),
          HookKind.MODIFY, covers=covers("conscription"))
def _conscription(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> int:
    return -1 if _law_for(state, "conscription") else 0


# Prophecy of Ixth - +1 to fighter combat rolls; discarded on PRODUCTION with fewer than 2 fighters.
@register(rules_hooks.POINT_COMBAT_ROLL_MODIFIER, agenda_source("prophecy"), HookKind.MODIFY,
          covers=covers("prophecy"))
def _prophecy(state: GameState, pid: str, ctx: Mapping[str, Any]) -> int:
    return 1 if _owner(state, "prophecy") == pid and ctx.get("base_type") == "fighter" else 0


@on_event(GameEvent.PRODUCTION_USED, Moment.AFTER, agenda_source("prophecy"),
          condition=lambda s, p, c: _owner(s, "prophecy") == p == c.get("player"),
          covers=covers("prophecy"), label="Prophecy of Ixth")
def _prophecy_discard(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    units = ctx.get("units") or {}
    fighters = int(units.get("fighter", 0)) if isinstance(units, Mapping) else 0
    if fighters < _PROPHECY_FIGHTERS:
        agenda_phase.remove_law(state, "prophecy")


# Publicize Weapon Schematics - For: war suns lose SUSTAIN DAMAGE; if any player owns a war sun
# technology, all players ignore prerequisites on war sun technologies.
def war_sun_techs(registry: StaticDataRegistry) -> set[str]:
    """Technologie, które odblokowują war sun (ulepszenie jednostki ``warsun``)."""
    return {
        u.required_tech_id for u in registry.units.values()
        if u.base_type == "warsun" and u.required_tech_id
    }


def owns_war_sun_tech(state: GameState, registry: StaticDataRegistry, pid: str) -> bool:
    return bool(war_sun_techs(registry) & set(state.players[pid].technologies))


@register(rules_hooks.POINT_UNIT_SUSTAIN_LOST, agenda_source("schematics"), HookKind.FORBID,
          covers=covers("schematics"))
def _schematics_sustain(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> set[str]:
    return {"warsun"} if _law_for(state, "schematics") else set()


@register(rules_hooks.POINT_TECHNOLOGY_FREE_IGNORES, agenda_source("schematics"), HookKind.MODIFY,
          covers=covers("schematics"))
def _schematics_prereqs(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> int:
    registry = rules_hooks.bound_registry()
    if registry is None or not _law_for(state, "schematics"):
        return 0
    if str(ctx.get("technology")) not in war_sun_techs(registry):
        return 0
    if not any(owns_war_sun_tech(state, registry, p) for p in state.players):
        return 0
    tech = registry.technologies.get(str(ctx.get("technology")))
    from src.core import technology

    return sum(technology.prerequisites(tech).values()) if tech is not None else 0


# Anti-Intellectual Revolution - For: after a player researches a technology, they destroy 1 of
# their non-fighter ships (gracz bez statków nadal może badać - C_agendas).
def _non_fighter_ships(state: GameState, pid: str) -> list[tuple[str, str, str]]:
    return [
        u for u in unit_instances(state, pid, zone_filter=lambda z: z == "space")
        if is_space_unit(u[2]) and u[2] != "fighter"
    ]


def _revolution_inputs(
    state: GameState, registry: StaticDataRegistry, pid: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    return destroy_choice_input(state, registry, _non_fighter_ships(state, pid), 1, pid,
                                label="Non-fighter ship to destroy")


@on_event(GameEvent.TECHNOLOGY_RESEARCH, Moment.AFTER, agenda_source("revolution"),
          condition=lambda s, p, c: _law_for(s, "revolution") and p == c.get("player")
          and bool(_non_fighter_ships(s, p)),
          decide=True, inputs=_revolution_inputs, covers=covers("revolution"),
          label="Anti-Intellectual Revolution")
def _revolution(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    ships = _non_fighter_ships(state, pid)
    destroy_units(state, pid, chosen_units(_params(ctx), ships, 1))


# =========================================================================================
# Ministrowie (prawa „Elect Player")
# =========================================================================================


# Minister of Commerce - after replenishing commodities gain 1 TG per neighbor.
@on_event(GameEvent.COMMODITIES_REPLENISHED, Moment.AFTER, agenda_source("minister_commerce"),
          condition=lambda s, p, c: _owner(s, "minister_commerce") == p == c.get("player"),
          covers=covers("minister_commerce"), label="Minister of Commerce")
def _commerce(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    from src.core import neighbors

    grid = board_graph.bound_grid()
    if grid is None:
        return
    count = len(neighbors.neighbors_of(pid, state, grid))
    if count:
        economy.gain_trade_goods(state, pid, count, cause="agenda")


# Minister of Exploration - when the owner gains control of a planet, they gain 1 TG.
@on_event(GameEvent.PLANET_CONTROL_GAINED, Moment.AFTER, agenda_source("minister_exploration"),
          condition=lambda s, p, c: _owner(s, "minister_exploration") == p == c.get("player"),
          covers=covers("minister_exploration"), label="Minister of Exploration")
def _exploration(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    economy.gain_trade_goods(state, pid, 1, cause="agenda")


# Minister of Industry - when the owner places a space dock, their units in that system may
# use PRODUCTION.
@on_event(GameEvent.UNIT_PLACED, Moment.AFTER, agenda_source("minister_industry"),
          where={"base_type": "spacedock"},
          condition=lambda s, p, c: _owner(s, "minister_industry") == p == c.get("player")
          and s.production_grant is None,
          optional=True, covers=covers("minister_industry"), label="Minister of Industry")
def _industry(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    position = str(ctx.get("position") or "")
    if position not in state.systems:
        return
    state.production_grant = ProductionGrant(
        player_id=pid, position=position, standalone=True, source=covers("minister_industry")
    )


# Minister of Peace - after a player activates a system with another player's units, the owner
# may discard this card to end the active player's turn (akcja taktyczna kończy się od razu).
def _peace_ready(state: GameState, pid: str, ctx: Mapping[str, Any]) -> bool:
    active = state.active_player_id
    system = state.systems.get(str(ctx.get("position") or ""))
    if _owner(state, "minister_peace") != pid or system is None or active is None:
        return False
    others = set(system.space_units) | {o for u in system.planet_units.values() for o in u}
    return any(o != active and o in state.players for o in others)


@on_event(GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, agenda_source("minister_peace"),
          condition=_peace_ready, optional=True, covers=covers("minister_peace"),
          label="Minister of Peace")
def _peace(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> None:
    agenda_phase.remove_law(state, "minister_peace")
    active = state.active_player_id
    if active is not None and action_budget.outside_turn(state, active):
        # C_action_cards/puppets-on-a-string/4: there is no turn to end - the card is discarded
        # (its cost), yet the extra action is still performed.
        return
    ended = tactical.end_tactical_action(state)
    state.__dict__.update(ended.__dict__)


# Minister of Policy - at the end of the status phase the owner draws 1 action card.
@on_event(GameEvent.PHASE, Moment.END, agenda_source("minister_policy"), where={"phase": "status"},
          condition=lambda s, p, c: _owner(s, "minister_policy") == p,
          covers=covers("minister_policy"), label="Minister of Policy")
def _policy(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    card_draw.draw_action_card(state, pid)


# Minister of Sciences - Technology strategy card research without spending resources.
@register(rules_hooks.POINT_TECHNOLOGY_SC_FREE, agenda_source("minister_sciences"),
          HookKind.PERMIT, covers=covers("minister_sciences"))
def _sciences(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> bool:
    return _owner(state, "minister_sciences") == pid


# Minister of War - after performing an action the owner may discard this card to return 1 of
# their command tokens from the board to reinforcements, then perform 1 additional action.
def _war_ready(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> bool:
    return (
        _owner(state, "minister_war") == pid
        and state.active_player_id == pid
        and state.phase is Phase.ACTION
        and any(pid in s.command_tokens for s in state.systems.values())
    )


def _war_inputs(
    state: GameState, registry: StaticDataRegistry, pid: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    from src.core.hooks.action_card_inputs import _system_label

    options = [
        _option(pos, _system_label(registry, s))
        for pos, s in state.systems.items() if pid in s.command_tokens
    ]
    return [_choice("position", "System to remove your command token from", options)]


def _minister_war(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    from src.core import active_effects

    position = str(_params(ctx).get("position") or "")
    system = state.systems.get(position)
    if system is None or pid not in system.command_tokens:
        raise ValueError("Choose a system with your command token ('position').")
    agenda_phase.remove_law(state, "minister_war")
    command_tokens.remove_from_board(state, system, pid)
    active_effects.add_effect(state, effect_key("minister_war", "action"), Duration.TURN, owner=pid)


def _war_ready_primary(state: GameState, pid: str, ctx: Mapping[str, Any]) -> bool:
    """Strategic action: only the primary ability is the owner's action (secondaries are not)."""
    return ctx.get("ability") == "primary" and _war_ready(state, pid, ctx)


for _event, _moment, _cond in (
    (GameEvent.TACTICAL_ACTION, Moment.END, _war_ready),
    (GameEvent.COMPONENT_ACTION, Moment.AFTER, _war_ready),
    (GameEvent.STRATEGIC_ACTION, Moment.AFTER, _war_ready_primary),  # C_agendas/minister-of-war/1
):
    on_event(_event, _moment, agenda_source("minister_war"), condition=_cond, optional=True,
             inputs=_war_inputs, covers=covers("minister_war"),
             label="Minister of War")(_minister_war)


@register(rules_hooks.POINT_TURN_ACTIONS, effect_source("minister_war", "action"),
          HookKind.MODIFY, covers=covers("minister_war"))
def _war_extra_action(_state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> int:
    return 1


# Search Warrant - the owner plays with their secret objectives revealed.
def revealed_secrets(state: GameState, player_id: str) -> list[str]:
    """Tajne cele gracza jawne dla wszystkich (właściciel Search Warrant)."""
    if _owner(state, "warrant") != player_id:
        return []
    return list(state.players[player_id].private.secret_objectives)

