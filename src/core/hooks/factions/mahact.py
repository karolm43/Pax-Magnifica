"""The Mahact Gene-Sorcerers — every faction component (RULES.md 62.23).

Texts in docstrings are quotes from the assets (``catalog.faction_bundle("mahact")``, units
``mahact_flagship`` / ``mahact_mech`` / ``mahact_infantry`` / ``mahact_infantry2``, breakthrough
``mahactbt``). Rulings: ``docs/rules_tirules/F_mahact.md`` (cross-checked: ``R_command_tokens``,
``R_fleet_pool``, ``R_space_combat``, ``R_agenda_phase``, ``R_promissory_notes``, ``C_agendas``,
``C_action_cards``, ``C_technology``, ``F_mentak``, ``F_muaat``, ``F_creuss``).

Engine points used/added for the Mahact: other players' tokens in the fleet pool
(``PlayerState.foreign_fleet_tokens`` + ``command_tokens.fleet_pool_count`` /
``remove_fleet_token``), the commander provider (``rules_hooks.register_commander_provider`` -
Imperia), ``tactical.activate_own_token`` (Il Na Viroset), ``agenda.required_outcome`` (Genetic
Recombination), ``promissory.cannot_receive`` (Hubris), a secondary token alternative
(``command_tokens.register_secondary_alternative`` - Jae Mir Kan), component space combat
(``battle.start_combat(source=...)`` - Benediction) and ``technology.purge_technology`` (Vaults of
the Heir).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    agenda_phase,
    board_graph,
    capacity,
    command_tokens,
    direct_move,
    economy,
    faction_components,
    leaders,
    movement_paths,
    promissory_notes,
    promissory_play,
    relics,
    rules_hooks,
    technology,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, Phase, SystemState
from src.core.hooks import agendas_directives, card_labels
from src.core.hooks.promissory_generic import has_units
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_AGENDA_REQUIRED_OUTCOME,
    POINT_COMBAT_ROLL_MODIFIER,
    POINT_PROMISSORY_CANNOT_RECEIVE,
    POINT_TACTICAL_ACTIVATE_OWN_TOKEN,
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
from src.core.state_grid import grid_from_state
from src.core.tactical import OWN_TOKEN_ACTIVATION
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

FACTION = "mahact"
EDICT = "edict"
IMPERIA = "imperia"
HUBRIS = "hubris"
GR = "gr"  # Genetic Recombination
CL2 = "cl2"  # Crimson Legionnaire II (unit upgrade)
AGENT = "mahactagent"
COMMANDER = "mahactcommander"
HERO = "mahacthero"
SCEPTER = "scepter"
FLAGSHIP = "mahact_flagship"
MECH = "mahact_mech"
INFANTRY = "mahact_infantry"
INFANTRY2 = "mahact_infantry2"
BREAKTHROUGH = "mahactbt"
ALLIANCE = "<color>_an"

# ``FACTION_ABILITY_USED`` abilities of the follow-up decisions (ctx ``ability``):
EDICT_GIVE = f"abilities:{EDICT}:give"  # opponent with empty reinforcements gives a sheet token
EDICT_CAP = f"abilities:{EDICT}:cap"  # Fleet Regulations: the Mahact returns 1 fleet token
CL_PICK = f"units:{INFANTRY}:pick"  # gain 1 commodity / convert 1 commodity
CL_RETURN = f"technologies:{CL2}:return"  # units on the card go to a home planet
GR_CHOICE = f"technologies:{GR}:choice"  # the voter: vote for the outcome / remove a fleet token
STARLANCER_GAIN = f"units:{MECH}:gain"  # the activator places the gained token
SCEPTER_POOL = f"promissory_notes:{SCEPTER}:pool"  # a placer without reinforcements picks a pool
# Active effects:
EDICT_FRESH = f"abilities:{EDICT}:fresh"  # tokens gained in the open combat (edict 6)
CL_CARD = f"technologies:{CL2}:card"  # units on the Crimson Legionnaire II card (data.count)
GR_VOTE = f"technologies:{GR}:vote"  # the voter must vote for data.outcome
BENEDICTION = f"leaders:{HERO}:benediction"  # KeyMoment areas (origin + combat system)

COMBAT_SOURCE = f"leaders:{HERO}"
_POOLS = ("tactical", "fleet", "strategic")
_POOL_NAMES = {"tactical": "tactic pool", "fleet": "fleet pool", "strategic": "strategy pool"}
_GIVE_TIE_ORDER = ("strategic", "tactical", "fleet")  # ⚠️ ASSUMPTION "Auto" ties (62.23)
_FLAGSHIP_BONUS = 2  # "apply +2 to the results"
_COMMANDER_TOKENS = 2  # "Have 2 other factions' command tokens in your fleet pool."
_GAIN, _CONVERT = "gain", "convert"
_VOTE, _REMOVE = "vote", "remove"
_OWN = "own"
_INFANTRY = "infantry"
_MECH = "mech"
_FLAGSHIP = "flagship"
_SPACE = "space"
_ASTEROID, _SUPERNOVA = "ASTEROID_FIELD", "SUPERNOVA"
_GROUND_FORCES = ("infantry", "mech")


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _fire(state: GameState, player_id: str, ctx: dict[str, Any]) -> None:
    from src.core import triggers  # local: the hooks package loads before triggers

    triggers.fire(state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
                  ctx={"player": player_id, **ctx})


def _adopt(dst: GameState, src: GameState) -> None:
    dst.__dict__.update(src.__dict__)


def _is_mahact(state: GameState, player_id: str) -> bool:
    """The player plays the Mahact (faction family) - read directly, no hooks."""
    registry = rules_hooks.bound_registry()
    player = state.players.get(player_id)
    if registry is None or player is None or player.faction is None:
        return False
    faction = registry.factions.get(player.faction)
    return faction is not None and registry.faction_family(faction) == FACTION


def mahact_player(state: GameState) -> str | None:
    """The Mahact player at the table (owner of the Scepter of Dominion), or None."""
    return next((pid for pid in sorted(state.players) if _is_mahact(state, pid)), None)


def _name(state: GameState, player_id: str) -> str:
    return card_labels.describe_player(state, _registry(), player_id)


def _decider(_state: GameState, _owner: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def _params(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    return ctx.get("params") or {}


def _pool_options(state: GameState, player_id: str) -> list[dict[str, Any]]:
    return [
        oi.option(pool, f"{_POOL_NAMES[pool].capitalize()} "
                        f"({command_tokens.pool_count(state, player_id, pool)})")
        for pool in _POOLS if command_tokens.pool_count(state, player_id, pool) > 0
    ]


def _fullest_pool(state: GameState, player_id: str) -> str | None:
    """⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = the pool with the most tokens, ties strategy ->
    tactic -> fleet."""
    counts = {p: command_tokens.pool_count(state, player_id, p) for p in _GIVE_TIE_ORDER}
    best = max(counts.values(), default=0)
    return next((p for p in _GIVE_TIE_ORDER if counts[p] == best), None) if best > 0 else None


# ========================================================================================= Edict


def _opponent(ctx: Mapping[str, Any], player_id: str) -> str:
    attacker, defender = str(ctx.get("attacker") or ""), str(ctx.get("defender") or "")
    return defender if attacker == player_id else attacker


def _edict_applies(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    if ctx.get("winner") != player_id:
        return False
    opponent = _opponent(ctx, player_id)
    player = state.players[player_id]
    return opponent in state.players and opponent != player_id and (
        opponent not in player.foreign_fleet_tokens
    )


@on_event(
    GameEvent.COMBAT_WON, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    condition=_edict_applies, covers=f"abilities:{EDICT}", label="Edict",
)
def edict(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Edict: When you win a combat: Place 1 command token from your opponent's reinforcements in
    your fleet pool if it does not already contain 1 of that player's tokens.

    Fired before the fleet pool / capacity checks of the combat (edict 1). An opponent without
    reinforcements gives a token of their sheet (their decision - edict 4); none anywhere ->
    nothing (4.1)."""
    opponent = _opponent(ctx, player_id)
    if command_tokens.reinforcements(state, opponent) > 0:
        command_tokens.take_from_reinforcements(state, opponent, 1)
        _gain_foreign(state, player_id, opponent)
    elif command_tokens.sheet_total(state, opponent) > 0:
        _fire(state, player_id, {"ability": EDICT_GIVE, "target": opponent})


def _gain_foreign(state: GameState, player_id: str, owner: str) -> None:
    """``owner``'s token (already taken) joins the Mahact fleet pool + Fleet Regulations check."""
    command_tokens.add_foreign_fleet_token(state, player_id, owner)
    if state.active_combat is not None:  # edict 6: no Imperia commander from this combat
        active_effects.add_effect(state, EDICT_FRESH, Duration.COMBAT, owner=player_id,
                                  data={"owner": owner})
    ability_notes.note(state, player_id, f"abilities:{EDICT}",
                       f"{_name(state, owner)}'s command token joins the fleet pool")
    cap = command_tokens.fleet_token_cap(state, player_id)
    if cap is not None and command_tokens.fleet_pool_count(state, player_id) > cap:
        _fire(state, player_id, {"ability": EDICT_CAP, "target": player_id, "gained": owner})


def edict_give_inputs(
    state: GameState, _registry_: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    options = _pool_options(state, decider)
    return [oi.choice("pool", "Command token you give to the Mahact player's fleet pool",
                      options, always=True, auto=_fullest_pool(state, decider))]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": EDICT_GIVE}, decide=True, decider=_decider, inputs=edict_give_inputs,
    label="Edict: give 1 command token from your command sheet",
)
def edict_give(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    giver = str(ctx["target"])
    pool = str(_params(ctx).get("pool") or _fullest_pool(state, giver) or "")
    if pool not in _POOLS or command_tokens.pool_count(state, giver, pool) <= 0:
        raise ValueError("Choose a pool of your command sheet that holds a token.")
    command_tokens.spend_from_pool(state, giver, pool)
    _gain_foreign(state, player_id, giver)


def edict_cap_inputs(
    state: GameState, _registry_: StaticDataRegistry, decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = one of the Mahact's own tokens, else the token
    just gained."""
    player = state.players[decider]
    options = []
    if player.fleet_cc > 0:
        options.append(oi.option(_OWN, "One of your own fleet tokens"))
    options += [
        oi.option(owner, f"{_name(state, owner)}'s token") for owner in player.foreign_fleet_tokens
    ]
    auto = _OWN if player.fleet_cc > 0 else str(ctx.get("gained") or "")
    return [oi.choice("token", "Fleet Regulations: token you return to its reinforcements",
                      options, always=True, auto=auto)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": EDICT_CAP}, decide=True, decider=_decider, inputs=edict_cap_inputs,
    label="Edict: Fleet Regulations - return 1 fleet pool token",
)
def edict_cap(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Fleet Regulations at the cap: the token was added, now 1 token returns (edict 3)."""
    player = state.players[player_id]
    choice = str(_params(ctx).get("token") or (_OWN if player.fleet_cc > 0 else ctx["gained"]))
    if choice == _OWN:
        command_tokens.spend_to_reinforcements(state, player_id, "fleet")
    else:
        command_tokens.return_foreign_fleet_token(state, player_id, choice)


def _standardize_inputs(
    state: GameState, _registry_: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = keep the other players' tokens."""
    return [
        oi.choice(f"token|{owner}", f"{_name(state, owner)}'s token in your fleet pool",
                  [oi.option("keep", "Keep it"),
                   oi.option("return", "Return it (take one of your own tokens instead)")],
                  always=True, auto="keep")
        for owner in state.players[decider].foreign_fleet_tokens
    ]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": agendas_directives.STANDARDIZE_FOREIGN}, decide=True, decider=_decider,
    inputs=_standardize_inputs, label="Armed Forces Standardization: your fleet pool tokens",
)
def edict_standardize(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """C_agendas armed-forces-standardization 1: the Mahact chooses which fleet tokens leave;
    other players' tokens go back to their owners' reinforcements."""
    for owner in list(state.players[player_id].foreign_fleet_tokens):
        if _params(ctx).get(f"token|{owner}") != "return":
            continue
        command_tokens.return_foreign_fleet_token(state, player_id, owner)
        if command_tokens.reinforcements(state, player_id) > 0:
            command_tokens.gain_from_reinforcements(state, player_id, {"fleet": 1})


# ======================================================================================= Imperia


@rules_hooks.register_commander_provider
def imperia_commanders(state: GameState, player_id: str) -> list[str]:
    """Imperia: While another player's command token is in your fleet pool, you can use the
    ability of that player's commander, if it is unlocked (not from the combat that gained the
    token - edict 6)."""
    registry = rules_hooks.bound_registry()
    player = state.players.get(player_id)
    if registry is None or player is None or not player.foreign_fleet_tokens:
        return []
    if not _is_mahact(state, player_id):
        return []
    fresh = {
        str(e.data.get("owner")) for e in state.active_effects
        if e.key == EDICT_FRESH and e.owner == player_id
    }
    found: list[str] = []
    for owner in player.foreign_fleet_tokens:
        other = state.players.get(owner)
        if other is None or owner in fresh:
            continue
        for leader_id in leaders.leaders_of(registry, other):
            leader = registry.leaders.get(leader_id)
            if leader is not None and leader.type == "commander" and (
                other.leader_states.get(leader_id, "locked") == leaders.UNLOCKED
            ):
                found.append(leader_id)
    return found


rules_hooks.declare_core_rule(f"abilities:{IMPERIA}")  # the commander provider above


# ======================================================================================== Hubris


@on_event(GameEvent.SETUP, Moment.DURING, HookSource(SOURCE_FACTION, FACTION),
          covers=f"abilities:{HUBRIS}", label="Hubris: purge your Alliance")
def hubris_purge(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Hubris: During setup, purge your "Alliance" promissory note."""
    registry = _registry()
    hand = state.players[player_id].private.promissory_notes
    for note in list(hand):
        try:
            template, owner = promissory_play.resolve(state, registry, note)
        except ValueError:
            continue
        if template == ALLIANCE and owner == player_id:
            promissory_notes.purge_from_hand(state, player_id, note)
            ability_notes.note(state, player_id, f"abilities:{HUBRIS}",
                               "purges their Alliance promissory note")


@register(POINT_PROMISSORY_CANNOT_RECEIVE, HookSource(SOURCE_FACTION, FACTION), HookKind.FORBID)
def hubris_no_alliance(
    _state: GameState, _player_id: str, _ctx: Mapping[str, Any]
) -> frozenset[str]:
    """Hubris: Other players cannot give you their "Alliance" promissory notes."""
    return frozenset({ALLIANCE})


# ============================================================================ Crimson Legionnaire


def _own_infantry(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("player") == player_id and ctx.get("base_type") == _INFANTRY


def _legionnaire_picks(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """One decision per destroyed unit, resolved one after another (crimson-legionnaire 1)."""
    for _ in range(int(ctx.get("count") or 1)):
        _fire(state, player_id, {"ability": CL_PICK, "target": player_id})


@on_event(
    GameEvent.UNIT_DESTROYED, Moment.AFTER, HookSource(SOURCE_UNIT, INFANTRY),
    condition=_own_infantry, covers=f"units:{INFANTRY}", label="Crimson Legionnaire I",
)
def legionnaire_destroyed(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Crimson Legionnaire I: After this unit is destroyed, gain 1 commodity or convert 1 of your
    commodities to a trade good."""
    _legionnaire_picks(state, player_id, ctx)


@on_event(
    GameEvent.UNIT_DESTROYED, Moment.AFTER, HookSource(SOURCE_UNIT, INFANTRY2),
    condition=_own_infantry, covers=f"units:{INFANTRY2}", label="Crimson Legionnaire II",
)
def legionnaire2_destroyed(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Crimson Legionnaire II: After this unit is destroyed, gain 1 commodity or convert 1 of
    your commodities to a trade good. Then, place the unit on this card."""
    _legionnaire_picks(state, player_id, ctx)
    count = int(ctx.get("count") or 1)
    card = next(iter(active_effects.effects_for(state, player_id, CL_CARD)), None)
    if card is None:
        active_effects.add_effect(state, CL_CARD, Duration.GAME, owner=player_id,
                                  data={"count": count})
    else:
        card.data["count"] = int(card.data.get("count") or 0) + count


def legionnaire_inputs(
    state: GameState, _registry_: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = convert when you have a commodity, else gain."""
    player = state.players[decider]
    options = [oi.option(_GAIN, "Gain 1 commodity")]
    if player.commodities > 0:
        options.append(oi.option(_CONVERT, "Convert 1 commodity to a trade good"))
    auto = _CONVERT if player.commodities > 0 else _GAIN
    return [oi.choice("pick", "Crimson Legionnaire destroyed", options, auto=auto)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": CL_PICK}, decide=True, decider=_decider, inputs=legionnaire_inputs,
    label="Crimson Legionnaire: gain or convert 1 commodity",
)
def legionnaire_pick(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    player = state.players[player_id]
    pick = str(_params(ctx).get("pick") or (_CONVERT if player.commodities > 0 else _GAIN))
    if pick == _CONVERT:
        economy.convert_commodities_to_trade_goods(state, player_id, 1)
        detail = "converts 1 commodity to a trade good"
    else:
        economy.gain_commodities(state, player_id, 1)
        detail = "gains 1 commodity"
    ability_notes.note(state, player_id, f"units:{INFANTRY}", detail)


def _home_planets(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """(planet, position) the player controls in their home system, board order."""
    homes = board_graph.home_positions_by_player(state, _registry()).get(player_id, [])
    return [
        (planet, pos) for pos in sorted(homes)
        for planet, owner in sorted(state.systems[pos].planet_owners.items())
        if pos in state.systems and owner == player_id
    ]


def _card_count(state: GameState, player_id: str) -> int:
    return sum(int(e.data.get("count") or 0)
               for e in active_effects.effects_for(state, player_id, CL_CARD))


def _cl_return_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return (
        ctx.get("player") == player_id and _card_count(state, player_id) > 0
        and bool(_home_planets(state, player_id))
    )


@on_event(
    GameEvent.TURN, Moment.START, HookSource(SOURCE_TECHNOLOGY, CL2),
    condition=_cl_return_ready, covers=f"technologies:{CL2}",
    label="Crimson Legionnaire II: units return to your home system",
)
def legionnaire_return(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Crimson Legionnaire II: At the start of your next turn, place each unit that is on this
    card on a planet you control in your home system (the planet = your decision)."""
    _fire(state, player_id, {"ability": CL_RETURN, "target": player_id})


def cl_return_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = the first controlled home planet."""
    planets = _home_planets(state, decider)
    options = [
        oi.option(planet, card_labels.planet_name(registry, planet), ref=("planet", planet))
        for planet, _pos in planets
    ]
    return [oi.choice("planet", "Planet for the Crimson Legionnaires on the card", options,
                      auto=planets[0][0] if planets else None)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": CL_RETURN}, decide=True, decider=_decider, inputs=cl_return_inputs,
    label="Crimson Legionnaire II: place the units on a home planet",
)
def legionnaire_place(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    planets = dict(_home_planets(state, player_id))
    planet = str(_params(ctx).get("planet") or next(iter(planets), ""))
    if planet not in planets:
        raise ValueError("Choose a planet you control in your home system.")
    count = _card_count(state, player_id)
    active_effects.remove_by_key(state, CL_CARD, owner=player_id)
    if count > 0:
        unit_ops.place_units(state, state.systems[planets[planet]], planet, player_id,
                             _INFANTRY, count)
        ability_notes.note(state, player_id, f"technologies:{CL2}",
                           f"{count} infantry return from the card")


# ========================================================================= Genetic Recombination


def gr_target(state: GameState, player_id: str) -> str | None:
    """The voter Genetic Recombination may target now (current voter, another player, able to
    vote - gr 1, 1.1)."""
    voter = agenda_phase.current_voter(state)
    if voter is None or voter == player_id or state.agenda is None:
        return None
    if voter in state.agenda.blocked:
        return None
    if agenda_phase.single_vote(state, voter):
        return voter
    rows = agenda_phase.voting_planets(state, _registry(), voter)
    readied = sum(int(r["influence"]) for r in rows if not r["exhausted"])
    return voter if readied > 0 else None


@faction_components.window_use("technology", GR)
def _gr_window(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> str | None:
    if state.phase is not Phase.AGENDA or agenda_phase.current_voter(state) is None:
        return "Use Genetic Recombination before a player casts votes."
    if gr_target(state, player_id) is None:
        return "The player about to vote cannot vote (or it is you)."
    if active_effects.has_effect(state, str(agenda_phase.current_voter(state)), GR_VOTE):
        return "That player is already bound by Genetic Recombination."
    return None


def _outcomes(state: GameState) -> list[str]:
    agenda = state.agenda
    if agenda is None:
        return []
    if agenda.outcomes:
        return list(agenda.outcomes)
    return agenda_phase.candidate_outcomes(state, _registry(), agenda.kind)


def _outcome_option(state: GameState, registry: StaticDataRegistry, outcome: str
                    ) -> dict[str, Any]:
    if outcome in state.players:
        return oi.option(outcome, _name(state, outcome))
    if outcome in registry.planets:
        return oi.option(outcome, card_labels.planet_name(registry, outcome),
                         ref=("planet", outcome))
    return oi.option(outcome, outcome.capitalize())


@register_effect_inputs(f"technologies:{GR}")
def gr_inputs(
    state: GameState, registry: StaticDataRegistry, _player_id: str
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = the first outcome of the agenda."""
    outcomes = _outcomes(state)
    options = [_outcome_option(state, registry, o) for o in outcomes]
    return [oi.choice("outcome", "Outcome the voter must vote for", options, always=True,
                      auto=outcomes[0] if outcomes else None)]


@register_effect(f"technologies:{GR}")
def genetic_recombination(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Genetic Recombination: You may exhaust this card before a player casts votes; that player
    must cast at least 1 vote for an outcome of your choice or remove 1 token from their fleet
    pool and return it to their reinforcements (exhaust = the card's cost)."""
    voter = gr_target(state, player_id)
    outcomes = _outcomes(state)
    outcome = str(params.get("outcome") or (outcomes[0] if outcomes else ""))
    if voter is None:
        raise ValueError("No player can be targeted by Genetic Recombination now.")
    if outcome not in outcomes:
        raise ValueError("Choose an outcome of this agenda.")
    ability_notes.note(state, player_id, f"technologies:{GR}",
                       f"{_name(state, voter)} must vote for {outcome} or lose a fleet token")
    from src.core import triggers  # local: the hooks package loads before triggers

    # "before a player casts votes" - an agenda decision: voting waits for it
    # (``agenda_phase.require_no_agenda_decisions``).
    triggers.fire(
        state, GameEvent.AGENDA_VOTES_CAST, Moment.BEFORE, subject=player_id,
        ctx={"player": player_id, "ability": GR_CHOICE, "target": voter, "outcome": outcome},
        hook_filter=lambda h: h.fn is gr_choice,
    )


def gr_choice_inputs(
    state: GameState, _registry_: StaticDataRegistry, decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = remove a fleet token when you have one."""
    outcome = str(ctx.get("outcome") or "")
    options = [oi.option(_VOTE, f"Cast at least 1 vote for {outcome}")]
    has_token = command_tokens.fleet_pool_count(state, decider) > 0
    if has_token:
        options.append(oi.option(_REMOVE, "Remove 1 token from your fleet pool"))
    return [oi.choice("choice", "Genetic Recombination", options, always=True,
                      auto=_REMOVE if has_token else _VOTE)]


@on_event(
    GameEvent.AGENDA_VOTES_CAST, Moment.BEFORE, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": GR_CHOICE}, decide=True, decider=_decider, inputs=gr_choice_inputs,
    label="Genetic Recombination: vote or lose a fleet token",
)
def gr_choice(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    voter, outcome = str(ctx["target"]), str(ctx.get("outcome") or "")
    has_token = command_tokens.fleet_pool_count(state, voter) > 0
    choice = str(_params(ctx).get("choice") or (_REMOVE if has_token else _VOTE))
    if choice == _REMOVE and has_token:
        command_tokens.remove_fleet_token(state, voter)
        ability_notes.note(state, voter, f"technologies:{GR}",
                           "removes 1 token from their fleet pool")
        return
    active_effects.add_effect(state, GR_VOTE, Duration.AGENDA, owner=voter,
                              data={"outcome": outcome, "by": player_id})
    ability_notes.note(state, voter, f"technologies:{GR}", f"must vote for {outcome}")


@register(POINT_AGENDA_REQUIRED_OUTCOME, HookSource(SOURCE_EFFECT, GR_VOTE), HookKind.FORBID)
def gr_required(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(
        str(e.data.get("outcome")) for e in active_effects.effects_for(state, player_id, GR_VOTE)
    )


# ============================================================================== Jae Mir Kan


def jae_mir_kan_systems(state: GameState, player_id: str) -> list[str]:
    """Systems with the active player's tokens - when the agent may pay this secondary."""
    active = state.active_player_id
    window = state.pending_window
    if (
        active is None or active == player_id or window is None
        or window.current_responder != player_id
        or HookSource(SOURCE_LEADER, AGENT) not in rules_hooks.owned_sources(state, player_id)
        or not leaders.is_ready(state, _registry(), player_id, AGENT)
    ):
        return []
    return sorted(pos for pos, s in state.systems.items() if active in s.command_tokens)


def jae_mir_kan_spend(state: GameState, player_id: str, position: str) -> None:
    """Jae Mir Kan: When you would spend a command token during the secondary ability of a
    strategic action: You may exhaust this card to remove 1 of the active player's command
    tokens from the board and use it instead (the token goes back to its owner's reinforcements;
    no strategy-pool spend - jae-mir-kan 1, 2)."""
    active = str(state.active_player_id)
    faction_components.pay_cost(state, _registry(), player_id, "leader", AGENT)
    command_tokens.remove_from_board(state, state.systems[position], active)
    ability_notes.note(state, player_id, f"leaders:{AGENT}",
                       f"uses {_name(state, active)}'s command token from system {position}")


command_tokens.register_secondary_alternative(
    f"leaders:{AGENT}", "Exhaust Jae Mir Kan: use the active player's command token from the board",
    jae_mir_kan_systems, jae_mir_kan_spend,
)


rules_hooks.declare_core_rule(f"leaders:{AGENT}")  # the secondary token alternative above


# ============================================================================ Il Na Viroset


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Have 2 other factions' command tokens in your fleet pool."""
    return len(state.players[player_id].foreign_fleet_tokens) >= _COMMANDER_TOKENS


@register(POINT_TACTICAL_ACTIVATE_OWN_TOKEN, HookSource(SOURCE_LEADER, COMMANDER),
          HookKind.PERMIT, covers=f"leaders:{COMMANDER}")
def il_na_viroset(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Il Na Viroset: During your tactical actions: you can activate systems that contain your
    command tokens. If you do, return both command tokens to your reinforcements and end your
    turn (``tactical.activate_system``)."""
    return True


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    where={"ability": OWN_TOKEN_ACTIVATION}, label="Il Na Viroset",
)
def il_na_viroset_note(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Activity: the own-token activation (both tokens return, the turn ends)."""
    if ctx.get("player") == player_id:
        ability_notes.note(state, player_id, f"leaders:{COMMANDER}",
                           f"activates system {ctx.get('position')} again: both command tokens "
                           "return, the turn ends")


# ========================================================================= Airo Shir Aur (hero)


def _space_owner(system: SystemState) -> str | None:
    """The single player with units in the space area (None: empty, neutral or several)."""
    owners = [
        pid for pid, units in system.space_units.items() if any(n > 0 for n in units.values())
    ]
    return owners[0] if len(owners) == 1 else None


def _ship_owners(system: SystemState) -> set[str]:
    return {
        pid for pid, units in system.space_units.items()
        if any(n > 0 and is_space_unit(bt) for bt, n in units.items())
    }


def _enterable(state: GameState, owner: str, position: str) -> bool:
    """The moved player's own anomaly rules (benediction 3, 4)."""
    grid = grid_from_state(state, _registry())
    anomalies = grid.anomalies_at(position)
    if _ASTEROID in anomalies and not movement_paths._can_enter_asteroids(state, owner):
        return False
    return not (_SUPERNOVA in anomalies and not movement_paths.can_enter_supernova(state, owner))


def benediction_pairs(state: GameState, player_id: str) -> list[tuple[str, str, str]]:
    """Legal ``(source, destination, owner)`` moves of Benediction, board order."""
    grid = grid_from_state(state, _registry())
    pairs: list[tuple[str, str, str]] = []
    for source in sorted(state.systems):
        owner = _space_owner(state.systems[source])
        if owner is None or owner not in state.players:
            continue
        for dest in sorted(board_graph.neighbors_for_player(state, grid, player_id, source)):
            system = state.systems.get(dest)
            if system is None or dest == source:
                continue
            others = {p for p in _ship_owners(system) if p != owner and p in state.players}
            if others and _enterable(state, owner, dest):
                pairs.append((source, dest, owner))
    return pairs


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """Source and destination on the MAP, plus how many of your ground forces on planets of the
    source your own ships take along (benediction 1.1). ⚠️ ASSUMPTION (RULES.md 62.23): "Auto" =
    the first legal pair (board order) and no ground forces taken."""
    pairs = benediction_pairs(state, player_id)
    sources = sorted({s for s, _d, _o in pairs})
    dests = sorted({d for _s, d, _o in pairs})
    src_opts = [oi.option(p, card_labels.describe_system(state, registry, p),
                          meta={"position": p}) for p in sources]
    dst_opts = [oi.option(p, card_labels.describe_system(state, registry, p),
                          meta={"position": p}) for p in dests]
    fields = [
        oi.choice("source", "System whose space area moves", src_opts, always=True,
                  auto=pairs[0][0] if pairs else None),
        oi.choice("destination", "Adjacent system with another player's ships", dst_opts,
                  always=True, auto=pairs[0][1] if pairs else None),
    ]
    own_sources = sorted({s for s, _d, owner in pairs if owner == player_id})
    for source in own_sources:
        for (planet, bt), n in _transportable(state, player_id, source).items():
            fields.append(oi.number(
                _take_key(source, planet, bt),
                f"{bt.capitalize()} from {card_labels.planet_name(registry, planet)} "
                f"(if your ships in {source} move)", 0, n, auto=0,
            ))
    return fields


def _take_key(source: str, planet: str, base_type: str) -> str:
    return f"take|{source}|{planet}|{base_type}"


@register_effect(f"leaders:{HERO}")
def benediction(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Airo Shir Aur — Benediction: ACTION: Move all units in the space area of any system to an
    adjacent system that contains a different player's ships. Space combat is resolved in that
    system; neither player can retreat or resolve abilities that would move their ships. Then,
    purge this card (purge = the leader's cost)."""
    pairs = benediction_pairs(state, player_id)
    if not pairs:
        raise ValueError("No space area can be moved next to another player's ships.")
    source = str(params.get("source") or pairs[0][0])
    dest = str(params.get("destination") or pairs[0][1])
    match = next((p for p in pairs if p[0] == source and p[1] == dest), None)
    if match is None:
        raise ValueError("Choose a system and an ADJACENT system with another player's ships.")
    owner = match[2]
    taken: dict[tuple[str, str], int] = {}
    if owner == player_id:  # own ships may take ground forces from planets (benediction 1.1)
        for (planet, bt), n in _transportable(state, player_id, source).items():
            want = int(params.get(_take_key(source, planet, bt)) or 0)
            if want < 0 or want > n:
                raise ValueError(f"You have {n} {bt} on that planet.")
            if want:
                taken[(planet, bt)] = want
    active_effects.add_effect(state, BENEDICTION, Duration.TURN, owner=player_id,
                              data={"areas": {source: "benediction_origin",
                                              dest: "benediction"},
                                    "owner": owner})
    _benediction_move(state, registry, player_id, owner, source, dest, taken)


def _transportable(state: GameState, player_id: str, source: str) -> dict[tuple[str, str], int]:
    """{(planet, ground force): count} of the Mahact on planets of ``source`` (benediction 1.1)."""
    system = state.systems[source]
    found: dict[tuple[str, str], int] = {}
    for planet, by_player in sorted(system.planet_units.items()):
        for bt in _GROUND_FORCES:
            n = int(by_player.get(player_id, {}).get(bt, 0))
            if n > 0:
                found[(planet, bt)] = n
    return found


def _benediction_move(
    state: GameState, registry: StaticDataRegistry, player_id: str, owner: str, source: str,
    dest: str, taken: Mapping[tuple[str, str], int],
) -> None:
    """Moves the space area (+ taken ground forces), checks capacity, starts the space combat."""
    from src.core import battle  # local: battle imports the hooks

    origin, target = state.systems[source], state.systems[dest]
    for (planet, bt), n in sorted(taken.items()):
        unit_ops.transfer_units(state, origin, planet, origin, _SPACE, owner, bt, n)
    moving = {bt: n for bt, n in origin.space_units.get(owner, {}).items() if n > 0}
    # "After ships move" offers (Sai Seravus - F_creuss 2.2) wait for the combat's start-trigger
    # step instead of opening a window of their own that would block the combat.
    direct_move.apply_moves(state, registry, owner, {dest: {source: moving}}, fighters_free=True,
                            mover=player_id, open_window=False)
    ability_notes.note(state, player_id, f"leaders:{HERO}",
                       f"moves {_name(state, owner)}'s space area from {source} to {dest}")
    if taken and capacity.capacity_report(state, registry, dest, owner).excess:
        raise ValueError("Your ships cannot carry that many ground forces.")
    # Capacity before the combat (benediction 10): forced removals at once; a remaining choice
    # takes the engine's cheapest-first suggestion (⚠️ ASSUMPTION, RULES.md 62.23).
    _adopt(state, capacity.remove_forced_excess(state, registry, dest))
    for pid in capacity.players_with_excess(state, registry, dest):
        removal = capacity.auto_removal(capacity.capacity_report(state, registry, dest, pid))
        for bt, n in sorted(removal.items()):
            unit_ops.remove_units(state, target, _SPACE, pid, bt, n, UnitCause.REMOVED)
    target = state.systems[dest]
    if not _ship_owners(target) - {owner} or owner not in _ship_owners(target):
        return  # a side lost every ship on the way (gravity rift) - no combat
    grid = grid_from_state(state, registry)
    _adopt(state, battle.start_combat(state, grid, registry, None, position=dest, attacker=owner,
                                      source=COMBAT_SOURCE, no_retreat=True))


# ======================================================================== Scepter of Dominion


def scepter_placers(state: GameState, holder: str) -> list[str]:
    """Players != holder with a token on the Mahact's command sheet (scepter 3: the Mahact when
    its sheet holds an own token)."""
    mahact = mahact_player(state)
    if mahact is None:
        return []
    found = list(state.players[mahact].foreign_fleet_tokens)
    if command_tokens.sheet_total(state, mahact) > 0:
        found.append(mahact)
    order = [p for p in state.seating_order if p in state.players] or sorted(state.players)
    return [p for p in order if p in found and p != holder]


def scepter_systems(state: GameState, holder: str) -> list[str]:
    """Non-home systems with the holder's units (never an eliminated player's home - scepter 4)."""
    registry = _registry()
    homes = {pos for positions in board_graph.home_positions_by_player(state, registry).values()
             for pos in positions}
    eliminated = {e.home_position for e in state.eliminated_players}
    return sorted(
        pos for pos, s in state.systems.items()
        if pos not in homes and pos not in eliminated and has_units(s, holder)
    )


@promissory_play.condition(SCEPTER)
def _scepter_condition(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> str | None:
    if not scepter_systems(state, player_id):
        return "You have no units in a non-home system."
    return None


promissory_play.any_subject(SCEPTER)


@register_effect_inputs(f"promissory_notes:{SCEPTER}")
def scepter_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = the first legal system."""
    systems = scepter_systems(state, player_id)
    options = [oi.option(p, card_labels.describe_system(state, registry, p), meta={"position": p})
               for p in systems]
    return [oi.choice("system", "Non-home system with your units", options, always=True,
                      auto=systems[0] if systems else None)]


@register_effect(f"promissory_notes:{SCEPTER}")
def scepter_of_dominion(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Scepter of Dominion: At the start of the strategy phase: Choose 1 non-home system that
    contains your units; each other player who has a token on the Mahact player's command sheet
    places a token from their reinforcements in that system. Then, return this card to the
    Mahact player (return - ``promissory_play``)."""
    systems = scepter_systems(state, player_id)
    position = str(params.get("system") or (systems[0] if systems else ""))
    if position not in systems:
        raise ValueError("Choose a non-home system that contains your units.")
    system = state.systems[position]
    active_effects.add_effect(state, f"promissory_notes:{SCEPTER}:played", Duration.TURN,
                              owner=player_id, data={"areas": {position: "scepter"}})
    for placer in scepter_placers(state, player_id):
        if placer in system.command_tokens:
            continue  # scepter 1
        if command_tokens.reinforcements(state, placer) > 0:
            command_tokens.place_on_board_from_reinforcements(state, system, placer)
        elif command_tokens.sheet_total(state, placer) > 0:  # scepter 2
            _fire(state, player_id, {"ability": SCEPTER_POOL, "target": placer,
                                     "position": position})
    ability_notes.note(state, player_id, f"promissory_notes:{SCEPTER}",
                       f"command tokens are placed in system {position}")


def scepter_pool_inputs(
    state: GameState, _registry_: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    return [oi.choice("pool", "Scepter of Dominion: pool your token comes from",
                      _pool_options(state, decider), always=True,
                      auto=_fullest_pool(state, decider))]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": SCEPTER_POOL}, decide=True, decider=_decider, inputs=scepter_pool_inputs,
    label="Scepter of Dominion: place a token from your command sheet",
)
def scepter_pool(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    placer = str(ctx["target"])
    pool = str(_params(ctx).get("pool") or _fullest_pool(state, placer) or "")
    system = state.systems[str(ctx["position"])]
    if placer in system.command_tokens:
        return
    if pool not in _POOLS or command_tokens.pool_count(state, placer, pool) <= 0:
        raise ValueError("Choose a pool of your command sheet that holds a token.")
    command_tokens.place_on_board_from_pool(state, system, placer, pool)


# ============================================================================== Arvicon Rex


@register(POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_UNIT, FLAGSHIP), HookKind.MODIFY,
          covers=f"units:{FLAGSHIP}")
def arvicon_rex(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Arvicon Rex: During combat against an opponent whose command token is not in your fleet
    pool, apply +2 to the results of this unit's combat rolls."""
    combat = state.active_combat
    if ctx.get("base_type") != _FLAGSHIP or combat is None:
        return 0
    opponent = combat.defender if combat.attacker == player_id else combat.attacker
    if opponent in state.players[player_id].foreign_fleet_tokens:
        return 0
    return _FLAGSHIP_BONUS


# ================================================================================ Starlancer


def _starlancer_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    activator = str(ctx.get("player") or "")
    system = state.systems.get(str(ctx.get("position") or ""))
    if activator not in state.players or system is None:
        return False
    has_mech = any(
        int(units.get(player_id, {}).get(_MECH, 0)) > 0 for units in system.planet_units.values()
    ) or int(system.space_units.get(player_id, {}).get(_MECH, 0)) > 0
    player = state.players[player_id]
    token = activator in player.foreign_fleet_tokens or (
        activator == player_id and player.fleet_cc > 0  # starlancer 4
    )
    return has_mech and token


@on_event(
    GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, HookSource(SOURCE_UNIT, MECH), optional=True,
    condition=_starlancer_ready, covers=f"units:{MECH}",
    label="Starlancer: spend their token to end their turn",
)
def starlancer(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Starlancer: After a player whose command token is in your fleet pool activates this
    system, you may spend their token from your fleet pool to end their turn; they gain that
    token (other "after activation" abilities lapse - starlancer 2, 2.1)."""
    from src.core import tactical, triggers, turn_flow  # local: they import the hooks

    activator = str(ctx["player"])
    if activator == player_id:
        command_tokens.spend_from_pool(state, player_id, "fleet")
    else:
        command_tokens.take_foreign_fleet_token(state, player_id, activator)
    command_tokens.return_to_reinforcements(state, activator, 1)
    ability_notes.note(state, player_id, f"units:{MECH}",
                       f"ends {_name(state, activator)}'s turn")
    triggers.drop_offers(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER)
    if state.active_system is not None:
        _adopt(state, tactical.end_tactical_action(state))
    if state.pending_window is None and not state.pending_offers:
        _adopt(state, turn_flow.end_turn(state, activator, registry=_registry(), forced=True))
    _fire(state, player_id, {"ability": STARLANCER_GAIN, "target": activator})


def starlancer_gain_inputs(
    _state: GameState, _registry_: StaticDataRegistry, _decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = tactic pool."""
    return [oi.choice("pool", "Pool for the command token you gain",
                      [oi.option(p, _POOL_NAMES[p].capitalize()) for p in _POOLS],
                      always=True, auto="tactical")]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": STARLANCER_GAIN}, decide=True, decider=_decider,
    inputs=starlancer_gain_inputs, label="Starlancer: place the command token you gain",
)
def starlancer_gain(state: GameState, _player_id: str, ctx: Mapping[str, Any]) -> None:
    gainer = str(ctx["target"])
    pool = str(_params(ctx).get("pool") or "tactical")
    if pool not in _POOLS:
        raise ValueError("Choose a pool of your command sheet.")
    if command_tokens.reinforcements(state, gainer) > 0:
        command_tokens.gain_from_reinforcements(state, gainer, {pool: 1})


# ========================================================================== Vaults of the Heir


def _purgeable(state: GameState, player_id: str) -> list[str]:
    return sorted(state.players[player_id].technologies)


@register_effect_inputs(f"breakthroughs:{BREAKTHROUGH}")
def vaults_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """The technology in the TechnologyOverlay. ⚠️ ASSUMPTION (RULES.md 62.23): "Auto" = the
    first owned non-unit-upgrade technology."""
    techs = _purgeable(state, player_id)
    options = [oi.option(t, technology_name(registry, t)) for t in techs]
    colored = [t for t in techs if (d := registry.technologies.get(t)) is not None and d.types]
    auto = colored[0] if colored else (techs[0] if techs else None)
    return [oi.choice("technology", "Technology you purge", options, always=True, auto=auto)]


def technology_name(registry: StaticDataRegistry, tech_id: str) -> str:
    tech = registry.technologies.get(tech_id)
    return tech.name if tech is not None and tech.name else tech_id


@register_effect(f"breakthroughs:{BREAKTHROUGH}")
def vaults_of_the_heir(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Vaults of the Heir: ACTION: Exhaust this card and purge 1 of your technologies to gain 1
    relic (exhaust = the card's cost; exhausted technologies may be purged - vaults 1.1)."""
    techs = _purgeable(state, player_id)
    tech = str(params.get("technology") or (techs[0] if techs else ""))
    if tech not in techs:
        raise ValueError("Choose a technology you own.")
    technology.purge_technology(state, player_id, tech)
    ability_notes.note(state, player_id, f"breakthroughs:{BREAKTHROUGH}",
                       f"purges {technology_name(registry, tech)}")
    relics.draw_relic(state, registry, player_id, source="vaults_of_the_heir")


@faction_components.blocker("breakthrough", BREAKTHROUGH)
def _vaults_blocker(state: GameState, _registry_: StaticDataRegistry, player_id: str
                    ) -> str | None:
    return None if _purgeable(state, player_id) else "You have no technology to purge."

