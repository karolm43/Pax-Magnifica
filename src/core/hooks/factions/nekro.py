"""The Nekro Virus — every faction component (RULES.md 62.24).

Texts in docstrings are quotes from the assets (``catalog.faction_bundle("nekro")``, units
``nekro_flagship`` / ``nekro_mech``, breakthrough ``nekrobt``). Rulings:
``docs/rules_tirules/F_nekro.md`` (cross-checked: ``R_technology`` Valefar Assimilator,
``R_unit_upgrades``, ``R_agenda_phase``, ``R_promissory_notes``, ``C_agendas``, ``C_action_cards``,
``C_relics``, ``C_objectives``, ``F_xxcha``, ``F_mentak``, ``F_muaat``, ``F_nomad``).

Engine points used/added for the Nekro: Valefar copies (``technology.assimilate`` /
``release_assimilated``, ``PlayerState.assimilated``, exhaust mirroring in ``core/exhaust.py``,
copied faction unit upgrades in ``combat.resolve_unit_variant``), Valefar Z flagship texts
(``rules_hooks.register_unit_source_provider``, ``PlayerState.assimilated_flagships``),
``technology.research_replaced`` (Propagation, in ``technology.apply_research``),
``agenda.cannot_vote`` (Galactic Threat, in ``agenda_phase._open_card``) and
``ActiveCombat.ground_as_ships`` (The Alastor, read by ``ship_roles``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.core import (
    ability_notes,
    active_effects,
    agenda_phase,
    card_draw,
    command_tokens,
    cooperative,
    economy,
    faction_components,
    leaders,
    promissory_play,
    rules_hooks,
    technology,
    unit_ops,
)
from src.core import offer_inputs as oi
from src.core.fleet_pool import unit_name
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, Phase
from src.core.hooks import card_labels
from src.core.hooks.factions.yssaril import card_name
from src.core.hooks.promissory_generic import has_units, return_on_activation
from src.core.planet_stats import planet_stats
from src.core.reaction_cards import OpenWindow
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import (
    POINT_AGENDA_CANNOT_VOTE,
    POINT_COMBAT_ROLL_MODIFIER,
    POINT_TECHNOLOGY_RESEARCH_REPLACED,
    SOURCE_FACTION,
    SOURCE_LEADER,
    SOURCE_UNIT,
    HookKind,
    HookSource,
    on_event,
    register,
    register_effect,
    register_effect_inputs,
)
from src.core.unit_ops import UnitCause

FACTION = "nekro"
GALACTIC = "galactic_threat"
SINGULARITY = "technological_singularity"
PROPAGATION = "propagation"
VAX, VAY = technology.ASSIMILATORS
BREAKTHROUGH = "nekrobt"
AGENT = "nekroagent"
COMMANDER = "nekrocommander"
HERO = "nekrohero"
ANTIVIRUS = "antivirus"
FLAGSHIP = "nekro_flagship"
MECH = "nekro_mech"

# ``FACTION_ABILITY_USED`` abilities of the follow-up decisions (ctx ``ability``):
GAIN = f"abilities:{GALACTIC}:gain"  # correct prediction: gain a voter's technology
MALLEON = f"leaders:{AGENT}:choice"  # the chosen player: discard / spend a token / decline
# Active effects:
PREDICTION = f"abilities:{GALACTIC}:prediction"  # data: agenda, outcome (once per agenda phase)
SINGULARITY_USED = f"abilities:{SINGULARITY}:used"  # once per combat
DEVOUR = f"leaders:{HERO}:devour"  # KeyMoment area (the devoured planet's system)

Z_PREFIX = "z|"
_TOKEN_NAMES = {VAX: "Valefar Assimilator X", VAY: "Valefar Assimilator Y"}
_PROPAGATION_TOKENS = 3  # "Gain 3 command tokens instead."
_COMMANDER_TECHS = 3  # "Own 3 technologies."
_AGENT_TRADE_GOODS = 2  # "to gain 2 trade goods"
_MORDRED_BONUS = 2  # "apply +2 to the result"
_POOLS = ("tactical", "fleet", "strategic")
_POOL_NAMES = {"tactical": "tactic pool", "fleet": "fleet pool", "strategic": "strategy pool"}
_GROUND_FORCES = ("infantry", "mech")
_DECLINE = "decline"


def _registry() -> StaticDataRegistry:
    registry = rules_hooks.bound_registry()
    if registry is None:
        raise ValueError("Static data registry is not bound.")
    return registry  # type: ignore[no-any-return]


def _fire(state: GameState, player_id: str, ctx: dict[str, Any]) -> None:
    from src.core import triggers  # local: the hooks package loads before triggers

    triggers.fire(state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=player_id,
                  ctx={"player": player_id, **ctx})


def _family(state: GameState, player_id: str) -> str | None:
    registry = rules_hooks.bound_registry()
    player = state.players.get(player_id)
    if registry is None or player is None or player.faction is None:
        return None
    faction = registry.factions.get(player.faction)
    return registry.faction_family(faction) if faction is not None else None


def _is_nekro(state: GameState, player_id: str) -> bool:
    """The player plays the Nekro (faction family) - read directly, no hooks."""
    return _family(state, player_id) == FACTION


def nekro_player(state: GameState) -> str | None:
    """The Nekro player at the table (owner of Antivirus), or None."""
    return next((pid for pid in sorted(state.players) if _is_nekro(state, pid)), None)


def _name(state: GameState, player_id: str) -> str:
    return card_labels.describe_player(state, _registry(), player_id)


def _tech_name(registry: StaticDataRegistry, tech_id: str) -> str:
    tech = registry.technologies.get(tech_id)
    return tech.name if tech is not None and tech.name else tech_id


def _decider(_state: GameState, _owner: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


def _params(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    return ctx.get("params") or {}


# =============================================================== Starting Valefar Assimilators


@on_event(GameEvent.SETUP, Moment.DURING, HookSource(SOURCE_FACTION, FACTION),
          label="Valefar Assimilators: starting technologies")
def starting_assimilators(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """User decision 2026-11-28 (RULES.md 62.24): the Nekro begins the game owning both Valefar
    Assimilators - it cannot research them (Propagation) and its commander's unlock condition
    presupposes owning them. Setup - not a gain (no ``TECHNOLOGY_GAINED``). An idle assimilator
    does not count as a technology for objectives/effects; only the copied card does."""
    technology.add_setup_technologies(state, player_id, list(technology.ASSIMILATORS))


# ============================================================== Gaining another player's tech


def _deck(state: GameState, registry: StaticDataRegistry, player_id: str) -> set[str]:
    return set(technology.tech_pool(state, registry, player_id))


def gainable_techs(
    state: GameState, registry: StaticDataRegistry, nekro: str, owners: list[str]
) -> dict[str, list[str]]:
    """``{tech id: [owners]}`` the Nekro may GAIN from ``owners``: non-faction technologies they
    own that the Nekro does not own and never purged (R_technology - faction technologies only
    via a Valefar Assimilator)."""
    player = state.players[nekro]
    deck = _deck(state, registry, nekro)
    found: dict[str, list[str]] = {}
    for owner in owners:
        other = state.players.get(owner)
        if other is None or owner == nekro:
            continue
        copies = set(other.assimilated.values())
        for tech_id in other.technologies:
            tech = registry.technologies.get(tech_id)
            if tech is None or tech.faction or tech_id in copies:
                continue
            if tech_id in player.technologies or tech_id not in deck:
                continue
            found.setdefault(tech_id, []).append(owner)
    return found


def assimilable_techs(
    state: GameState, registry: StaticDataRegistry, nekro: str, owners: list[str]
) -> dict[str, str]:
    """``{faction tech id: owner}`` an X/Y token may go on: faction technologies owned by that
    player, not the Nekro's own, without an assimilator token (vax/vay 3). Never a mech or a
    breakthrough unit - they are not technologies (valefar-assimilator 4, 5; F_mentak)."""
    player = state.players[nekro]
    if not any(t in player.technologies for t in technology.ASSIMILATORS):
        return {}
    taken = {t for p in state.players.values() for t in p.assimilated.values()}
    found: dict[str, str] = {}
    for owner in owners:
        other = state.players.get(owner)
        if other is None or owner == nekro:
            continue
        copies = set(other.assimilated.values())
        for tech_id in other.technologies:
            tech = registry.technologies.get(tech_id)
            if tech is None or not tech.faction or tech_id in copies or tech_id in taken:
                continue
            if tech.faction == player.faction or tech_id in player.technologies:
                continue
            found.setdefault(tech_id, owner)
    return found


def z_targets(state: GameState, nekro: str, owners: list[str]) -> list[str]:
    """Players whose faction sheet may take a Z token (breakthrough unlocked, one per sheet -
    valefar-assimilator-z 2)."""
    player = state.players[nekro]
    if not player.breakthrough_unlocked:
        return []
    found: list[str] = []
    for owner in owners:
        other = state.players.get(owner)
        if other is None or owner == nekro or other.faction is None:
            continue
        if other.faction in player.assimilated_flagships or _is_nekro(state, owner):
            continue
        if owner not in found:
            found.append(owner)
    return found


def has_gain_option(
    state: GameState, registry: StaticDataRegistry, nekro: str, owners: list[str]
) -> bool:
    return bool(
        gainable_techs(state, registry, nekro, owners)
        or assimilable_techs(state, registry, nekro, owners)
        or z_targets(state, nekro, owners)
    )


def gain_inputs_for(
    state: GameState, registry: StaticDataRegistry, nekro: str, owners: list[str], label: str
) -> list[dict[str, Any]]:
    """The technology in the TechnologyOverlay + the assimilator token when needed (X/Y on a
    faction technology, Z on a faction sheet); no "Auto" (user decision 2026-11-27)."""
    gain = gainable_techs(state, registry, nekro, owners)
    assim = assimilable_techs(state, registry, nekro, owners)
    zs = z_targets(state, nekro, owners)
    options = [
        oi.option(t, f"{_tech_name(registry, t)} ({', '.join(_name(state, o) for o in who)})")
        for t, who in sorted(gain.items())
    ] + [
        oi.option(t, f"{_tech_name(registry, t)} ({_name(state, o)}) - Valefar Assimilator")
        for t, o in sorted(assim.items())
    ]
    player = state.players[nekro]
    tokens: list[dict[str, Any]] = []
    if assim:
        for token in technology.ASSIMILATORS:
            if token not in player.technologies:
                continue
            copied = player.assimilated.get(token)
            suffix = f" (moves from {_tech_name(registry, copied)})" if copied else ""
            tokens.append(oi.option(token, f"{_TOKEN_NAMES[token]}{suffix}", ref=("tech", token)))
    tokens += [
        oi.option(f"{Z_PREFIX}{o}", f"Valefar Assimilator Z: {_name(state, o)}'s faction sheet",
                  ref=("breakthrough", BREAKTHROUGH))
        for o in zs
    ]
    fields = [oi.choice("technology", label, options, always=True, optional=bool(zs))]
    if tokens:
        fields.append(oi.choice(
            "token", "Assimilator token (only for a faction technology or a faction sheet)",
            tokens, optional=True,
        ))
    return fields


def _same_type_token(
    state: GameState, registry: StaticDataRegistry, nekro: str, tech_id: str
) -> str | None:
    """The token already copying a faction unit upgrade of the same unit type: the new one MUST
    use it (valefar-assimilator 3, R_technology)."""
    tech = registry.technologies.get(tech_id)
    base_type = technology.upgraded_base_type(tech) if tech is not None else None
    if base_type is None:
        return None
    for token, copied in state.players[nekro].assimilated.items():
        other = registry.technologies.get(copied)
        if other is not None and technology.upgraded_base_type(other) == base_type:
            return token
    return None


def apply_gain(
    state: GameState, registry: StaticDataRegistry, nekro: str, owners: list[str],
    params: Mapping[str, Any], component: str,
) -> None:
    """Resolves "gain 1 technology owned by that player" with the Valefar alternatives."""
    token = str(params.get("token") or "")
    tech_id = str(params.get("technology") or "")
    player = state.players[nekro]
    if token.startswith(Z_PREFIX):
        owner = token[len(Z_PREFIX):]
        if owner not in z_targets(state, nekro, owners):
            raise ValueError("You cannot place a Z assimilator token on that faction sheet.")
        faction = str(state.players[owner].faction)
        player.assimilated_flagships = [*player.assimilated_flagships, faction]
        ability_notes.note(state, nekro, f"breakthroughs:{BREAKTHROUGH}",
                           f"places a Z token on {_name(state, owner)}'s faction sheet: the "
                           "flagship gains that faction's flagship abilities")
        return
    gain = gainable_techs(state, registry, nekro, owners)
    if tech_id in gain:
        technology.grant_technology(state, nekro, tech_id)
        ability_notes.note(state, nekro, component,
                           f"gains {_tech_name(registry, tech_id)} from "
                           f"{_name(state, gain[tech_id][0])}")
        return
    assim = assimilable_techs(state, registry, nekro, owners)
    if tech_id not in assim:
        raise ValueError("Choose a technology that player owns (or a Z token).")
    if token not in technology.ASSIMILATORS or token not in player.technologies:
        raise ValueError("A faction technology needs your X or Y assimilator token.")
    forced = _same_type_token(state, registry, nekro, tech_id)
    if forced is not None and forced != token:
        raise ValueError(f"You already copy a faction upgrade of that unit - use "
                         f"{_TOKEN_NAMES[forced]}.")
    technology.assimilate(state, nekro, token, tech_id)
    ability_notes.note(state, nekro, f"technologies:{token}",
                       f"copies {_tech_name(registry, tech_id)} ({_name(state, assim[tech_id])})")


rules_hooks.declare_core_rule(f"technologies:{VAX}", f"technologies:{VAY}")


@rules_hooks.register_unit_source_provider
def _z_flagships(state: GameState, player_id: str) -> list[str]:
    """Valefar Assimilator Z: the flagship text sources of the factions holding a Z token (the
    owning player's current variant; an eliminated faction's base flagship - z 9)."""
    registry = rules_hooks.bound_registry()
    player = state.players.get(player_id)
    if registry is None or player is None or not player.assimilated_flagships:
        return []
    from src.core.combat import resolve_unit_variant  # local: combat imports rules_hooks

    found: list[str] = []
    for faction_id in player.assimilated_flagships:
        owner = next((p for p in state.players.values() if p.faction == faction_id), None)
        if owner is not None:
            unit = resolve_unit_variant(registry, owner.faction, owner.technologies, "flagship",
                                        owner.breakthrough_unlocked, owner.breakthrough_flipped)
        else:
            unit = resolve_unit_variant(registry, faction_id, [], "flagship")
        if unit is not None and unit.faction and unit.ability:
            found.append(unit.id)
    return found


rules_hooks.declare_core_rule(f"breakthroughs:{BREAKTHROUGH}")  # the provider + apply_gain


# =================================================================================== Propagation


@register(POINT_TECHNOLOGY_RESEARCH_REPLACED, HookSource(SOURCE_FACTION, FACTION),
          HookKind.PERMIT, covers=f"abilities:{PROPAGATION}")
def propagation(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Propagation: You cannot research technology. When you would research a technology: Gain 3
    command tokens instead (``technology.apply_research``)."""
    return True


def _propagation_count(state: GameState, player_id: str) -> int:
    return min(_PROPAGATION_TOKENS, command_tokens.reinforcements(state, player_id))


def propagation_inputs(
    state: GameState, _registry_: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """A pool for each token (one choice per token, R_command_tokens) - no "Auto" (user decision
    2026-11-27)."""
    options = [oi.option(pool, _POOL_NAMES[pool].capitalize()) for pool in _POOLS]
    return [
        oi.choice(f"token_{k + 1}", f"Command token {k + 1}: pool", options, always=True)
        for k in range(_propagation_count(state, decider))
    ]


def _propagation_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    return ctx.get("target") == player_id


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": technology.RESEARCH_REPLACED}, decide=True, decider=_decider,
    condition=_propagation_ready, inputs=propagation_inputs,
    label="Propagation: gain 3 command tokens instead",
)
def propagation_tokens(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The tokens come from reinforcements (fewer there = fewer tokens - R_command_tokens)."""
    count = _propagation_count(state, player_id)
    params = _params(ctx)
    chosen = [str(params.get(f"token_{k + 1}") or "") for k in range(count)]
    if any(pool not in _POOLS for pool in chosen):
        raise ValueError(f"Choose a pool for each of the {count} command token(s).")
    pools: dict[str, int] = {}
    for pool in chosen:
        pools[pool] = pools.get(pool, 0) + 1
    if count:
        command_tokens.gain_from_reinforcements(state, player_id, pools)
    tech = _tech_name(_registry(), str(ctx.get("technology") or ""))
    ability_notes.note(state, player_id, f"abilities:{PROPAGATION}",
                       f"gains {count} command token(s) instead of researching {tech}")


# ====================================================================== Technological Singularity


def _combat_opponent(state: GameState, player_id: str) -> str | None:
    combat = state.active_combat
    if combat is None or player_id not in (combat.attacker, combat.defender):
        return None
    return combat.defender if combat.attacker == player_id else combat.attacker


def antivirus_protects(state: GameState, victim: str) -> bool:
    """The victim has the Nekro's Antivirus in their play area (antivirus 3: not from the hand)."""
    registry = rules_hooks.bound_registry()
    if registry is None or victim not in state.players:
        return False
    return bool(promissory_play.notes_in_play(state, registry, victim, ANTIVIRUS))


def _singularity_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    combat = state.active_combat
    victim = str(ctx.get("player") or "")
    if combat is None or ctx.get("position") != combat.position or combat.outcome is not None:
        return False
    if _combat_opponent(state, player_id) != victim or victim not in state.players:
        return False
    if active_effects.has_effect(state, player_id, SINGULARITY_USED):
        return False
    if antivirus_protects(state, victim):
        return False
    return has_gain_option(state, _registry(), player_id, [victim])


def singularity_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    victim = str(ctx.get("player") or "")
    return gain_inputs_for(state, registry, decider, [victim],
                           f"Technology owned by {_name(state, victim)}")


@on_event(
    GameEvent.UNIT_DESTROYED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_singularity_ready, inputs=singularity_inputs,
    covers=f"abilities:{SINGULARITY}", label="Technological Singularity",
)
def technological_singularity(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Technological Singularity: Once per combat, after 1 of your opponent's units is destroyed:
    You may gain 1 technology that is owned by that player.

    Any destruction inside the combat counts (AFB, Direct Hit, the opponent's own cost - 3, 3.1);
    removal does not (3.2); space cannon / bombardment are outside a combat (3.3). A gained unit
    upgrade is in effect from now on (combat units are rebuilt from the state - 4)."""
    victim = str(ctx.get("player") or "")
    if not _singularity_ready(state, player_id, ctx):
        raise ValueError("Technological Singularity cannot be used now.")
    active_effects.add_effect(state, SINGULARITY_USED, Duration.COMBAT, owner=player_id)
    apply_gain(state, _registry(), player_id, [victim], _params(ctx),
               f"abilities:{SINGULARITY}")


# ================================================================================ Galactic Threat


@register(POINT_AGENDA_CANNOT_VOTE, HookSource(SOURCE_FACTION, FACTION), HookKind.PERMIT,
          covers=f"abilities:{GALACTIC}")
def cannot_vote(_state: GameState, _player_id: str, _ctx: Mapping[str, Any]) -> bool:
    """Galactic Threat: You cannot vote on agendas (``agenda_phase._open_card``)."""
    return True


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


def _can_predict(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> bool:
    return (
        state.phase is Phase.AGENDA
        and not active_effects.has_effect(state, player_id, PREDICTION)
        and bool(_outcomes(state))
    )


def predict_inputs(
    state: GameState, registry: StaticDataRegistry, _decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """An outcome of the agenda (abstaining is not one - galactic-threat 1); no "Auto"."""
    options = [_outcome_option(state, registry, o) for o in _outcomes(state)]
    return [oi.choice("outcome", "Your prediction", options, always=True)]


@on_event(
    GameEvent.AGENDA_REVEALED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    optional=True, condition=_can_predict, inputs=predict_inputs,
    covers=f"abilities:{GALACTIC}", label="Galactic Threat: predict the outcome",
)
def galactic_threat(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """Galactic Threat: Once per agenda phase, after an agenda is revealed: You may predict aloud
    the outcome of that agenda (after the "when revealed" Veto / Quash; riders stay playable -
    galactic-threat 1, 1.1)."""
    outcomes = _outcomes(state)
    outcome = str(_params(ctx).get("outcome") or "")
    if outcome not in outcomes:
        raise ValueError("Predict one of the outcomes of this agenda.")
    agenda = state.agenda
    active_effects.add_effect(state, PREDICTION, Duration.PHASE, owner=player_id, data={
        "agenda": str(agenda.agenda_id if agenda is not None else ctx.get("agenda") or ""),
        "outcome": outcome,
    })
    label = _outcome_option(state, _registry(), outcome)["label"]
    ability_notes.note(state, player_id, f"abilities:{GALACTIC}", f"predicts: {label}")


def _prediction(state: GameState, player_id: str) -> dict[str, Any] | None:
    effects = active_effects.effects_for(state, player_id, PREDICTION)
    return dict(effects[0].data) if effects else None


def _prediction_correct(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    prediction = _prediction(state, player_id)
    agenda = state.agenda
    if prediction is None or prediction.get("done") or agenda is None:
        return False
    return (
        prediction.get("agenda") == str(agenda.agenda_id or ctx.get("agenda") or "")
        and prediction.get("outcome") == str(ctx.get("outcome") or "")
    )


@on_event(
    GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    condition=_prediction_correct, covers=f"abilities:{GALACTIC}",
    label="Galactic Threat: correct prediction",
)
def prediction_check(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """If your prediction is correct, gain 1 technology that is owned by a player who voted how
    you predicted (cast votes - the speaker's tie-break is not a vote: 3; nobody - 3.1)."""
    outcome = str(ctx.get("outcome") or "")
    for effect in state.active_effects:
        if effect.key == PREDICTION and effect.owner == player_id:
            effect.data = {**effect.data, "done": True}
    voters = [p for p in agenda_phase.voters_for(state, outcome) if p != player_id]
    ability_notes.note(state, player_id, f"abilities:{GALACTIC}", "the prediction is correct")
    if voters and has_gain_option(state, _registry(), player_id, voters):
        _fire(state, player_id, {"ability": GAIN, "target": player_id, "voters": voters})


def gain_decision_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    voters = [str(v) for v in ctx.get("voters") or []]
    return gain_inputs_for(state, registry, decider, voters,
                           "Technology owned by a player who voted as you predicted")


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_FACTION, FACTION),
    where={"ability": GAIN}, decide=True, decider=_decider, inputs=gain_decision_inputs,
    label="Galactic Threat: gain 1 technology",
)
def prediction_gain(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    voters = [str(v) for v in ctx.get("voters") or []]
    apply_gain(state, _registry(), player_id, voters, _params(ctx), f"abilities:{GALACTIC}")


# ========================================================================== Nekro Malleon (agent)


@faction_components.window_use("leader", AGENT, standing=True)
def _agent_window(state: GameState, _registry_: StaticDataRegistry, _player_id: str) -> str | None:
    if state.phase is not Phase.ACTION:
        return "Nekro Malleon is used during the action phase."
    if state.exploration is not None and state.exploration.current is not None:
        return "Resolve the current exploration card first."  # nekro-malleon 2
    return None


def _everyone(state: GameState, _owner: str) -> list[str]:
    return list(state.players)


cooperative.register_pull_component("leader", AGENT, _everyone, mutual=True, target="target")


@register_effect_inputs(f"leaders:{AGENT}")
def agent_inputs(
    state: GameState, _registry_: StaticDataRegistry, _player_id: str
) -> list[dict[str, Any]]:
    """The player as a chip - no "Auto" (user decision 2026-11-27)."""
    order = [p for p in state.seating_order if p in state.players] or sorted(state.players)
    return [oi.choice("target", "Player who may discard or spend a token for 2 trade goods",
                      [oi.option(p, _name(state, p)) for p in order], always=True)]


@register_effect(f"leaders:{AGENT}")
def nekro_malleon(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Nekro Malleon: During the action phase: You may exhaust this card to choose a player; that
    player may discard 1 action card or spend 1 command token from their command sheet to gain 2
    trade goods (exhaust = the card's cost)."""
    target = str(params.get("target") or "")
    if target not in state.players:
        raise ValueError("Choose a player.")
    ability_notes.note(state, player_id, f"leaders:{AGENT}", f"chooses {_name(state, target)}")
    _fire(state, player_id, {"ability": MALLEON, "target": target})


def malleon_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """An action card (chip), a pool of the command sheet, or nothing - no "Auto"."""
    hand = state.players[decider].private.action_cards
    options = [
        oi.option(f"card|{card}", f"Discard {card_name(registry, card)}",
                  ref=("actionCard", card))
        for card in dict.fromkeys(hand)
    ] + [
        oi.option(f"pool|{pool}", f"Spend 1 command token from your {_POOL_NAMES[pool]}")
        for pool in _POOLS if command_tokens.pool_count(state, decider, pool) > 0
    ] + [oi.option(_DECLINE, "Do not gain trade goods")]
    return [oi.choice("choice", f"Nekro Malleon: gain {_AGENT_TRADE_GOODS} trade goods",
                      options, always=True)]


@on_event(
    GameEvent.FACTION_ABILITY_USED, Moment.AFTER, HookSource(SOURCE_LEADER, AGENT),
    where={"ability": MALLEON}, decide=True, decider=_decider, inputs=malleon_inputs,
    label="Nekro Malleon: discard 1 action card or spend 1 command token",
)
def malleon_choice(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    target = str(ctx["target"])
    choice = str(_params(ctx).get("choice") or _DECLINE)
    kind, _, value = choice.partition("|")
    if kind == "card":
        card_draw.discard_chosen_action_cards(state, target, [value])
    elif kind == "pool":
        if value not in _POOLS or command_tokens.pool_count(state, target, value) <= 0:
            raise ValueError("Choose a pool of your command sheet that holds a token.")
        command_tokens.spend_from_pool(state, target, value)
    else:
        return
    economy.gain_trade_goods(state, target, _AGENT_TRADE_GOODS, from_supply=True)
    ability_notes.note(state, target, f"leaders:{AGENT}",
                       f"{'discards an action card' if kind == 'card' else 'spends a token'} "
                       f"and gains {_AGENT_TRADE_GOODS} trade goods")


# ======================================================================== Nekro Acidos (commander)


def counted_technologies(state: GameState, player_id: str) -> int:
    """Technologies for the commander: a Valefar Assimilator counts only while its X/Y token is
    on a technology - the copied card stands in its place."""
    player = state.players[player_id]
    return sum(1 for t in player.technologies if t not in technology.ASSIMILATORS)


@leaders.register_unlock(COMMANDER)
def _commander_unlocked(state: GameState, _registry_: StaticDataRegistry, player_id: str) -> bool:
    """Unlock: Own 3 technologies. A "Valefar Assimilator" technology counts only if its X or Y
    token is on a technology."""
    return counted_technologies(state, player_id) >= _COMMANDER_TECHS


def _gained_by_me(_state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    """Own gains only; a card swapped in (Genetic Memory) is not one (F_jol_nar
    rin-the-masters-legacy-genetic-memory 4 - Acidos through the Nekro's Alliance)."""
    return ctx.get("player") == player_id and not ctx.get("replacement")


@on_event(
    GameEvent.TECHNOLOGY_GAINED, Moment.AFTER, HookSource(SOURCE_LEADER, COMMANDER),
    optional=True, condition=_gained_by_me, covers=f"leaders:{COMMANDER}",
    label="Nekro Acidos: draw 1 action card",
)
def nekro_acidos(state: GameState, player_id: str, _ctx: Mapping[str, Any]) -> None:
    """Nekro Acidos: After you gain a technology: You may draw 1 action card."""
    card_draw.draw_action_cards(state, player_id, 1)
    ability_notes.note(state, player_id, f"leaders:{COMMANDER}", "draws 1 action card")


# ============================================================ UNIT.DSGN.FLAYESH (hero)


def devour_planets(state: GameState, registry: StaticDataRegistry, player_id: str
                   ) -> dict[str, tuple[str, tuple[str, ...]]]:
    """``{planet: (position, specialties)}``: planets with a technology specialty in a system
    that contains the Nekro's units."""
    found: dict[str, tuple[str, tuple[str, ...]]] = {}
    for position, system in sorted(state.systems.items()):
        if not has_units(system, player_id):
            continue
        for planet in sorted(set(system.planet_units) | set(system.planet_owners)):
            stats = planet_stats(state, registry, planet)
            if stats is not None and stats.tech_specialties:
                found[planet] = (position, tuple(stats.tech_specialties))
    return found


def _specialty_techs(
    state: GameState, registry: StaticDataRegistry, player_id: str, colors: tuple[str, ...]
) -> list[str]:
    """Technologies of those colours in the player's deck, not owned (unit upgrades have no
    colour - unit-dsgn-flayesh 2)."""
    owned = set(state.players[player_id].technologies)
    wanted = {c.upper() for c in colors}
    return sorted(
        tech.id for tech in technology.tech_pool(state, registry, player_id).values()
        if tech.id not in owned and technology.tech_color(tech) in wanted
    )


@register_effect_inputs(f"leaders:{HERO}")
def hero_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str
) -> list[dict[str, Any]]:
    """The planet on the MAP and the technology in the TechnologyOverlay - no "Auto"."""
    planets = devour_planets(state, registry, player_id)
    techs: list[str] = []
    for _pos, colors in planets.values():  # the first planet's colour(s) first
        techs += [t for t in _specialty_techs(state, registry, player_id, colors) if t not in techs]
    return [
        oi.choice("planet", "Planet with a technology specialty",
                  [oi.option(p, card_labels.planet_name(registry, p), ref=("planet", p))
                   for p in planets], always=True),
        oi.choice("technology", "Technology matching that planet's specialty",
                  [oi.option(t, _tech_name(registry, t)) for t in techs], always=True,
                  optional=True),
    ]


@register_effect(f"leaders:{HERO}")
def devour_world(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """UNIT.DSGN.FLAYESH — Polymorphic Algorithm: Devour World: ACTION: Choose a planet that has a
    technology specialty in a system that contains your units. Destroy any other player's units on
    that planet. Gain trade goods equal to the planet's combined resource and influence values and
    gain 1 technology that matches the specialty of that planet. Then, purge this card (purge =
    the leader's cost). Outside a combat - no Technological Singularity (unit-dsgn-flayesh 1)."""
    planets = devour_planets(state, registry, player_id)
    planet = str(params.get("planet") or "")
    if planet not in planets:
        raise ValueError("Choose a planet with a technology specialty in a system with your units.")
    position, colors = planets[planet]
    techs = _specialty_techs(state, registry, player_id, colors)
    tech_id = str(params.get("technology") or "")
    if techs and tech_id not in techs:
        raise ValueError("Choose a technology that matches the planet's specialty.")
    active_effects.add_effect(state, DEVOUR, Duration.TURN, owner=player_id,
                              data={"areas": {position: "nekro_devour"}, "planets": [planet]})
    system = state.systems[position]
    for pid, units in sorted(system.planet_units.get(planet, {}).items()):
        if pid == player_id:
            continue
        for base_type, count in sorted(units.items()):
            if count > 0:
                unit_ops.remove_units(state, system, planet, pid, base_type, count,
                                      UnitCause.DESTROYED)
    stats = planet_stats(state, registry, planet)
    value = (stats.resources + stats.influence) if stats is not None else 0
    if value:
        economy.gain_trade_goods(state, player_id, value)
    ability_notes.note(state, player_id, f"leaders:{HERO}",
                       f"devours {card_labels.planet_name(registry, planet)}: {value} trade goods")
    if tech_id:
        technology.grant_technology(state, player_id, tech_id)
        ability_notes.note(state, player_id, f"leaders:{HERO}",
                           f"gains {_tech_name(registry, tech_id)}")


# ===================================================================================== Antivirus


@promissory_play.condition(ANTIVIRUS)
def _antivirus_condition(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, _window: OpenWindow
) -> str | None:
    """Only at the start of a combat the holder participates in (antivirus 2; the Nekro need not
    - 2.1)."""
    if _combat_opponent(state, player_id) is None:
        return "Play Antivirus at the start of a combat you participate in."
    return None


promissory_play.any_subject(ANTIVIRUS)


@register_effect(f"promissory_notes:{ANTIVIRUS}")
def antivirus(
    state: GameState, _registry_: StaticDataRegistry, player_id: str, _params_: Mapping[str, Any]
) -> None:
    """Antivirus: At the start of a combat: Place this card faceup in your play area. While this
    card is in your play area, the Nekro player cannot use their Technological Singularity faction
    ability against you (placement = the note's ``playArea``; the check -
    ``antivirus_protects``)."""
    ability_notes.note(state, player_id, f"promissory_notes:{ANTIVIRUS}",
                       "is protected from Technological Singularity")


# "If you activate a system that contains 1 or more of the Nekro player's units, return this card
# to the Nekro player." - structures too, without any hostility (4, 5); only an activation (6).
return_on_activation(ANTIVIRUS)


# ==================================================================================== The Alastor


def _alastor_units(state: GameState, player_id: str, position: str) -> dict[str, int]:
    system = state.systems.get(position)
    if system is None:
        return {}
    space = system.space_units.get(player_id, {})
    if space.get("flagship", 0) <= 0:
        return {}
    return {bt: space[bt] for bt in _GROUND_FORCES if space.get(bt, 0) > 0}


def _alastor_ready(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> bool:
    combat = state.active_combat
    return (
        combat is not None and combat.kind == "space" and ctx.get("kind") == "space"
        and _combat_opponent(state, player_id) is not None
        and bool(_alastor_units(state, player_id, combat.position))
    )


def alastor_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """How many of each ground force fight as ships - no "Auto" (not a hit assignment)."""
    combat = state.active_combat
    units = _alastor_units(state, player_id, combat.position) if combat is not None else {}
    return [
        oi.number(bt, f"{unit_name(state, registry, player_id, bt)} that fight as "
                      "ships", 0, n)
        for bt, n in sorted(units.items())
    ]


@on_event(
    GameEvent.COMBAT, Moment.START, HookSource(SOURCE_UNIT, FLAGSHIP),
    optional=True, condition=_alastor_ready, inputs=alastor_inputs,
    covers=f"units:{FLAGSHIP}", label="The Alastor: ground forces fight as ships",
)
def the_alastor(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
    """The Alastor: At the start of a space combat, choose any number of your ground forces in
    this system to participate in that combat as if they were ships (``ship_roles``: they roll,
    take hits and count as ships, never for the fleet pool - the-alastor 1, 7; they stay in the
    combat if The Alastor dies - 5). Ground forces on planets: gap (RULES.md 62.24)."""
    combat = state.active_combat
    if combat is None:
        raise ValueError("The Alastor is used at the start of a space combat.")
    units = _alastor_units(state, player_id, combat.position)
    params = _params(ctx)
    chosen = {bt: int(params.get(bt) or 0) for bt in units}
    if any(n < 0 or n > units[bt] for bt, n in chosen.items()):
        raise ValueError("You do not have that many ground forces in the space area.")
    chosen = {bt: n for bt, n in chosen.items() if n > 0}
    combat.ground_as_ships = {**combat.ground_as_ships, player_id: chosen}
    if chosen:
        listed = ", ".join(f"{n} {bt}" for bt, n in sorted(chosen.items()))
        ability_notes.note(state, player_id, f"units:{FLAGSHIP}", f"{listed} fight as ships")


# ======================================================================================== Mordred


def _opponent_assimilated(state: GameState, nekro: str, opponent: str) -> bool:
    """A technology of ``opponent`` carries a Nekro X/Y token (+2 once - mordred 1)."""
    other = state.players.get(opponent)
    copies = set(state.players[nekro].assimilated.values())
    return other is not None and any(t in other.technologies for t in copies)


@register(POINT_COMBAT_ROLL_MODIFIER, HookSource(SOURCE_UNIT, MECH), HookKind.MODIFY,
          covers=f"units:{MECH}")
def mordred(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> int:
    """Mordred: During combat against an opponent who has an "X" or "Y" token on 1 or more of
    their technologies, apply +2 to the result of each of this unit's combat rolls."""
    if ctx.get("base_type") != "mech":
        return 0
    opponent = _combat_opponent(state, player_id)
    if opponent is None or not _opponent_assimilated(state, player_id, opponent):
        return 0
    return _MORDRED_BONUS

