"""Efekty WYNIKU agend (RULES.md 51.6): dyrektywy oraz jednorazowe skutki praw („Against", „gains").

Teksty kart: ``assets/data/agendas/{base,pok}.json`` (talia ``agendas_pok``), rulingi:
``docs/rules_tirules/C_agendas.md``. Hooki biegną w ``AGENDA_OUTCOME_RESOLVED``/DURING (po zapisie
prawa / odrzuceniu karty, PRZED riderami). Trwałe skutki praw - ``agendas_laws.py``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from src.core import (
    agenda_phase,
    board_graph,
    board_reinforcements,
    card_draw,
    command_tokens,
    control,
    custodians,
    economy,
    exhaust,
    objectives,
    relics,
    research_offer,
    rules_hooks,
    secret_objectives,
    strategic_action,
    strategy_phase,
    technology,
    unit_ops,
)
from src.core.dice import DIE_SIDES, next_rng, record_table_roll
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, TimingWindow, WindowType
from src.core.hooks.action_card_inputs import Input, _choice, _number, _option, _planet_label
from src.core.hooks.agendas_common import (
    GROUND_FORCES,
    bound_registry,
    chosen_units,
    covers,
    destroy_choice_input,
    destroy_units,
    effect_source,
    elected,
    finish,
    is_elected,
    lose_points,
    most_and_fewest,
    on_outcome,
    schedule,
    ships_of,
    unit_instances,
)
from src.core.hooks.card_helpers import controlled, place_from_reinforcements, system_of_planet
from src.core.offer_inputs import multi
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import on_event
from src.core.unit_catalog import is_space_unit
from src.core.unit_ops import UnitCause

# --- Stałe z tekstów kart ------------------------------------------------------------------
_ARMS_KEEP = {"dreadnought": 2, "cruiser": 4}  # Arms Reduction: „all but 2 … all but 4"
_ARTICLES_TG = 3  # Articles of War „Against": 3 trade goods
_CLANDESTINE_FOR = 2  # Clandestine Operations „For": 2 żetony z arkusza
_EQUALITY_TG = 5  # Economic Equality „For": 5 trade goods
_ARTIFACT_HIT = 6  # Ixthian Artifact: 6-10 = technologie, 1-5 = katastrofa
_ARTIFACT_TECHS = 2  # „may research 2 technologies"
_ARTIFACT_LOSSES = 3  # „destroys 3 of their own units in each of those systems"
_STANDARD_POOLS = {"tactical": 3, "fleet": 3, "strategic": 2}  # Armed Forces Standardization
_UNCONVENTIONAL_DRAW = 2  # Unconventional Measures „For": 2 action cards
_WARRANT_SECRETS = 2  # Search Warrant: „draws 2 secret objectives"
_ALPHA_BETA = {"ALPHA", "BETA"}


def _registry() -> StaticDataRegistry:
    return bound_registry()


def _params(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
    params = ctx.get("params")
    return params if isinstance(params, Mapping) else {}


def _voted(state: GameState, outcome: str) -> list[str]:
    return agenda_phase.voters_for(state, outcome)


def _home_planets(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    """Planety systemu domowego gracza, które gracz kontroluje (C_agendas: nie cudzych domów)."""
    positions = board_graph.home_positions_by_player(state, registry).get(player_id, [])
    owned = set(controlled(state, player_id))
    found: list[str] = []
    for position in positions:
        system = state.systems.get(position)
        if system is not None:
            found += [p for p in system.planet_owners if p in owned]
    return found


def _discard_hand(state: GameState, player_id: str) -> None:
    hand = state.players[player_id].private.action_cards
    if hand:
        card_draw.discard_action_cards(state, player_id, len(hand))


def _draw_revealed(state: GameState, card: str, player_id: str, count: int) -> None:
    """Dobiera ``count`` tajnych celów do ręki; nadmiar gracz oddaje PO obejrzeniu (C_agendas)."""
    for _ in range(count):
        secret_objectives.draw_to_hand(state, player_id)
    if secret_objectives.excess(state, player_id) > 0:
        schedule(state, card, "return", player_id, scope=Duration.PHASE)


def _return_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    count = secret_objectives.excess(state, player_id)
    hand = state.players[player_id].private.secret_objectives
    options = [
        _option(o, getattr(objectives.objective_def(registry, o), "name", o)) for o in hand
    ]
    return [multi("objectives", f"Over the secret objective limit - return {count} to the deck",
                  options, count, count)]


def _return_excess(card: str) -> Any:
    def apply(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
        finish(state, card, "return", pid)
        count = secret_objectives.excess(state, pid)
        picks = [str(o) for o in _params(ctx).get("objectives", [])][:count]
        hand = state.players[pid].private.secret_objectives
        if len(picks) < count:
            picks += [o for o in reversed(hand) if o not in picks][: count - len(picks)]
        for objective in picks:
            secret_objectives.discard_unscored(state, pid, objective)

    return apply


for _card, _name in (("secret", "Archived Secret"), ("warrant", "Search Warrant")):
    on_event(GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER, effect_source(_card, "return"),
             where={"agenda": _card}, covers=covers(_card), decide=True, inputs=_return_inputs,
             label=f"{_name}: return secret objectives over the limit")(_return_excess(_card))


# =========================================================================================
# Dyrektywy
# =========================================================================================

# Covert Legislation: ukrytą agendę dobiera i rozstrzyga ``agenda_phase`` (``covert_card``).
rules_hooks.declare_core_rule(covers("covert"))


# Judicial Abolishment - Discard the elected law from play.
@on_outcome("abolishment", once=True, label="Judicial Abolishment")
def _abolishment(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    law = elected(ctx)
    if law in state.decks.agenda_laws:
        agenda_phase.remove_law(state, law)


# Arms Reduction - For: destroy all but 2 dreadnoughts and all but 4 cruisers.
def _arms_excess(state: GameState, player_id: str, base_type: str) -> list[tuple[str, str, str]]:
    return unit_instances(
        state, player_id, base_types=(base_type,), zone_filter=lambda z: z == "space"
    )


def _arms_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    inputs: list[Input] = []
    for base_type, keep in _ARMS_KEEP.items():
        units = _arms_excess(state, player_id, base_type)
        inputs += destroy_choice_input(
            state, registry, units, len(units) - keep, key=base_type,
            label=f"{base_type.capitalize()}s to destroy (keep {keep})",
        )
    return inputs


@on_outcome("arms_reduction", outcome="for", decide=True, inputs=_arms_inputs,
            label="Arms Reduction")
def _arms_for(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    for base_type, keep in _ARMS_KEEP.items():
        units = _arms_excess(state, pid, base_type)
        excess = len(units) - keep
        if excess > 0:
            destroy_units(state, pid, chosen_units(_params(ctx), units, excess, key=base_type))


# Arms Reduction - Against: start of the next strategy phase: exhaust tech-specialty planets.
@on_outcome("arms_reduction", outcome="against", label="Arms Reduction")
def _arms_against(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    schedule(state, "arms_reduction", "against", pid)


@on_event(GameEvent.PHASE, Moment.START, effect_source("arms_reduction", "against"),
          where={"phase": "strategy"}, covers=covers("arms_reduction"), label="Arms Reduction")
def _arms_against_apply(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    registry = _registry()
    planets = [
        p for p in controlled(state, pid)
        if (d := registry.planets.get(p)) is not None and d.tech_specialties
    ]
    exhausted = state.players[pid].exhausted_planets
    exhaust.exhaust_planets(state, pid, [p for p in planets if p not in exhausted])
    finish(state, "arms_reduction", "against", pid)


# Ixthian Artifact - speaker rolls: 6-10 each player may research 2 techs; 1-5 Mecatol disaster.
def _artifact_roll(state: GameState, speaker: str) -> int:
    value = next_rng(state).randint(1, DIE_SIDES)
    record_table_roll(
        state, speaker, "agenda", "Ixthian Artifact", [value], hits_on=_ARTIFACT_HIT,
        summary="6-10: research 2 technologies; 1-5: destruction around Mecatol Rex",
    )
    return value


def _researchable(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    result: list[str] = []
    for tech in technology.researchable_techs(state, registry, player_id):
        try:
            technology.plan_research(state, registry, player_id, tech.id, [])
        except ValueError:
            continue
        result.append(tech.id)
    return result


def _research_inputs_n(count: int) -> Any:
    def inputs(
        state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
    ) -> list[Input]:
        # Druga technologia może korzystać z pierwszej jako prerekwizytu (C_agendas).
        names = {t.id: t.name for t in technology.researchable_techs(state, registry, player_id)}
        candidates = list(_researchable(state, registry, player_id))
        skips = [
            _option(v, label) for v, label in technology.skip_choices(state, registry, player_id)
        ]
        if count > 1 or skips:
            candidates += [t for t in names if t not in candidates]
        options = [_option(t, names.get(t, t)) for t in candidates]
        found = [multi("techs", f"Technologies to research (up to {count})", options, 0, count)]
        if skips:
            found.append(multi(
                "skips", "Exhaust to ignore prerequisites (optional)", skips, 0, len(skips),
                hint="A planet with a technology specialty ignores 1 prerequisite of its color.",
            ))
        return found

    return inputs


def research_chosen(
    state: GameState, player_id: str, techs: list[str], skips: list[str] | None = None
) -> None:
    """Badanie wybranych technologii bez kosztu (kolejność dowolna: pierwsza bywa prerekwizytem).

    ``skips`` - planety ze specjalnością / AI Development Algorithm, które gracz zgodził się
    wyczerpać (C_agendas); każda technologia bierze najmniejszy potrzebny podzbiór."""
    registry = _registry()
    pending = list(techs)
    left = list(skips or [])
    while pending:
        progressed = False
        for tech in list(pending):
            plan = technology.plan_with_skips(state, registry, player_id, tech, left)
            if plan is None:
                continue
            technology.apply_research(state, player_id, plan)
            used = set(plan.exhaust_planets)
            if plan.exhaust_aida:
                used.add(technology.AIDA_SKIP)
            left = [s for s in left if s not in used]
            pending.remove(tech)
            progressed = True
        if not progressed:
            raise ValueError(f"You cannot research: {', '.join(pending)} (prerequisites).")


@on_outcome("artifact", outcome="for", once=True, label="Ixthian Artifact")
def _artifact(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    if _artifact_roll(state, pid) >= _ARTIFACT_HIT:
        for player in strategy_phase.speaker_order(state):
            schedule(state, "artifact", "research", player, scope=Duration.PHASE)
        return
    # 1-5: zniszcz wszystko w systemie Mecatol Rex, a sąsiedzi niszczą po 3 jednostki.
    mecatol = next(
        (pos for pos in state.systems if custodians.is_mecatol_position(state, pos)), None
    )
    if mecatol is None:
        return
    for player in list(state.players):
        destroy_units(state, player, unit_instances(state, player, positions=[mecatol]))
    for player in strategy_phase.speaker_order(state):
        hit = [
            pos for pos in sorted(board_graph.adjacent_positions(mecatol))
            if unit_instances(state, player, positions=[pos])
        ]
        if hit:
            schedule(state, "artifact", "losses", player, scope=Duration.PHASE, positions=hit)


def _artifact_research_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, ctx: Mapping[str, Any]
) -> list[Input]:
    inputs: list[Input] = _research_inputs_n(_ARTIFACT_TECHS)(state, registry, player_id, ctx)
    return inputs


@on_event(GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER, effect_source("artifact", "research"),
          where={"agenda": "artifact"},
          covers=covers("artifact"), optional=True, inputs=_artifact_research_inputs,
          label="Ixthian Artifact: research 2 technologies")
def _artifact_research(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    finish(state, "artifact", "research", pid)
    techs = [str(t) for t in _params(ctx).get("techs", [])]
    if techs:
        research_chosen(state, pid, techs, [str(x) for x in _params(ctx).get("skips", [])])


def _losses(state: GameState, player_id: str) -> list[str]:
    from src.core import active_effects

    for effect in active_effects.effects_for(state, player_id, "agendas:artifact:losses"):
        if effect.owner == player_id:
            return [str(p) for p in effect.data.get("positions", [])]
    return []


def _artifact_losses_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    inputs: list[Input] = []
    for position in _losses(state, player_id):
        units = unit_instances(state, player_id, positions=[position])
        inputs += destroy_choice_input(
            state, registry, units, _ARTIFACT_LOSSES, key=f"units_{position}",
            label=f"Destroy {_ARTIFACT_LOSSES} units in system {state.systems[position].system_id}",
        )
    return inputs


@on_event(GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER, effect_source("artifact", "losses"),
          where={"agenda": "artifact"},
          covers=covers("artifact"), decide=True, inputs=_artifact_losses_inputs,
          label="Ixthian Artifact: destroy units next to Mecatol Rex")
def _artifact_losses(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    positions = _losses(state, pid)
    finish(state, "artifact", "losses", pid)
    for position in positions:  # „all units are destroyed simultaneously"
        units = unit_instances(state, pid, positions=[position])
        picks = chosen_units(_params(ctx), units, _ARTIFACT_LOSSES, key=f"units_{position}")
        destroy_units(state, pid, picks)


# Clandestine Operations - For: remove 2 tokens from the command sheet (any pools; C_agendas).
def _sheet_inputs(count: int) -> Any:
    def inputs(
        state: GameState, _registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
    ) -> list[Input]:
        pools = {p: command_tokens.pool_count(state, player_id, p) for p in command_tokens.POOLS}
        need = min(count, sum(pools.values()))
        if need == 0 or sum(1 for n in pools.values() if n > 0) <= 1:
            return []  # brak realnego wyboru
        return [
            _number(pool, f"Tokens to remove from the {pool} pool", 0, min(n, need),
                    f"Remove {need} tokens in total.")
            for pool, n in pools.items()
        ]

    return inputs


def _remove_from_sheet(
    state: GameState, player_id: str, count: int, params: Mapping[str, Any]
) -> None:
    pools = {p: command_tokens.pool_count(state, player_id, p) for p in command_tokens.POOLS}
    need = min(count, sum(pools.values()))
    chosen = {p: int(params.get(p, 0) or 0) for p in command_tokens.POOLS}
    if sum(chosen.values()) != need:
        if any(chosen.values()):
            raise ValueError(f"Remove exactly {need} command tokens.")
        chosen = {}
        left = need
        for pool, have in pools.items():  # bez wyboru: jedyna pula z żetonami
            take = min(have, left)
            if take:
                chosen[pool] = take
                left -= take
    for pool, amount in chosen.items():
        if amount > 0:
            command_tokens.spend_to_reinforcements(state, player_id, pool, amount)


@on_outcome("cladenstine", outcome="for", decide=True, inputs=_sheet_inputs(_CLANDESTINE_FOR),
            label="Clandestine Operations")
def _clandestine_for(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    _remove_from_sheet(state, pid, _CLANDESTINE_FOR, _params(ctx))


@on_outcome("cladenstine", outcome="against", label="Clandestine Operations")
def _clandestine_against(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    if command_tokens.pool_count(state, pid, "fleet") > 0:
        command_tokens.spend_to_reinforcements(state, pid, "fleet", 1)


# New Constitution - For: discard all laws; next strategy phase exhaust home planets.
@on_outcome("constitution", outcome="for", once=True, label="New Constitution")
def _constitution(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> None:
    for law in list(state.decks.agenda_laws):
        agenda_phase.remove_law(state, law)
    for player in state.players:
        schedule(state, "constitution", "for", player)


@on_event(GameEvent.PHASE, Moment.START, effect_source("constitution", "for"),
          where={"phase": "strategy"}, covers=covers("constitution"), label="New Constitution")
def _constitution_apply(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    planets = _home_planets(state, _registry(), pid)
    exhaust.exhaust_planets(
        state, pid, [p for p in planets if p not in state.players[pid].exhausted_planets]
    )
    finish(state, "constitution", "for", pid)


# Galactic Crisis Pact - each player may perform the elected secondary without a token.
@on_outcome("crisis", once=True, label="Galactic Crisis Pact")
def _crisis(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    initiative = int(elected(ctx) or 0)
    queue = strategy_phase.speaker_order(state)  # C_agendas: w kolejności od mówcy
    if not initiative or not queue or state.pending_window is not None:
        return
    state.pending_window = TimingWindow(
        window_type=WindowType.STRATEGY_SECONDARY,
        queue=queue,
        context={
            "initiative": initiative,
            "free": "",
            "cost": 0,
            strategic_action.NO_COST_KEY: ",".join(queue),
            strategic_action.NO_COST_WHY_KEY: ";".join(f"{p}=agendas:crisis" for p in queue),
            "agenda": "crisis",
        },
    )


# Compensated Disarmament - destroy each ground force on the planet; controller gains 1 TG each.
@on_outcome("disarmament", once=True, label="Compensated Disarmament")
def _disarmament(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    planet = elected(ctx)
    system = system_of_planet(state, planet)
    owner = system.planet_owners.get(planet)
    destroyed = 0
    for player in list(system.planet_units.get(planet, {})):
        for base_type in GROUND_FORCES:
            count = unit_ops.count_in_zone(system, planet, player, base_type)
            if count:
                unit_ops.remove_units(state, system, planet, player, base_type, count,
                                      UnitCause.DESTROYED)
                destroyed += count
    if owner in state.players and destroyed:
        economy.gain_trade_goods(state, owner, destroyed, cause="agenda")


# Economic Equality - For: return all TG, gain 5. Against: return all TG.
def _return_trade_goods(state: GameState, player_id: str) -> None:
    have = state.players[player_id].trade_goods
    if have:
        economy.spend_trade_goods(state, player_id, have)


@on_outcome("economic_equality", label="Economic Equality")
def _equality(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    _return_trade_goods(state, pid)
    if ctx.get("outcome") == "for":
        economy.gain_trade_goods(state, pid, _EQUALITY_TG, cause="agenda")


# Public Execution - discard all action cards; pass the speaker token left; no voting this phase.
@on_outcome("execution", once=True, label="Public Execution")
def _execution(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    target = elected(ctx)
    if target not in state.players:
        return
    _discard_hand(state, target)
    if state.speaker_id == target:
        order = strategy_phase.speaker_order(state)
        if len(order) > 1:
            strategy_phase.set_speaker(state, order[1])  # gracz po lewej = następny zegarowo
    agenda_phase.block_voter_for_phase(state, target)


# Research Grant Reallocation - gain any technology; remove 1 fleet token per prerequisite.
def _grant_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    # Pełne okno drzewa technologii (opisy, kolory, prerekwizyty) zamiast listy nazw.
    return [research_offer.gain_input(
        state, registry, player_id, label="Gain any 1 technology", token_pool="fleet",
        hint="For each prerequisite on it, remove 1 token from your fleet pool "
             "(all of them if you have fewer).",
    )]


@on_outcome("grant_reallocation", decide=True, condition=is_elected, inputs=_grant_inputs,
            label="Research Grant Reallocation")
def _grant(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    registry = _registry()
    tech_id = research_offer.chosen_tech(_params(ctx))
    definition = technology.tech_pool(state, registry, pid).get(tech_id or "")
    if tech_id is None or definition is None:
        raise ValueError("Choose a technology to gain.")
    if tech_id in state.players[pid].technologies:
        raise ValueError("You already own that technology.")
    technology.grant_technology(state, pid, tech_id)
    # Za każdy prerekwizyt żeton z fleet pool; przy braku - wszystkie (C_agendas).
    cost = min(sum(technology.prerequisites(definition).values()),
               command_tokens.pool_count(state, pid, "fleet"))
    if cost > 0:
        command_tokens.spend_to_reinforcements(state, pid, "fleet", cost)


# Incentive Program - For: reveal a stage I objective; Against: a stage II objective.
@on_outcome("incentive", once=True, label="Incentive Program")
def _incentive(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    objectives.reveal_from_stage(state, 1 if ctx.get("outcome") == "for" else 2)


# Minister of Antiquities - the elected player gains 1 relic.
@on_outcome("minister_antiquities", condition=is_elected, label="Minister of Antiquities")
def _antiquities(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    relics.draw_relic(state, _registry(), pid, source="agenda")


# Miscount Disclosed - vote on the elected law as if it were just revealed.
@on_outcome("miscount", once=True, label="Miscount Disclosed")
def _miscount(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    agenda_phase.schedule_revote(state, elected(ctx))


# Mutiny - For: voters "For" gain 1 VP; Against: voters "For" lose 1 VP (kolejność od mówcy).
@on_outcome("mutiny", once=True, label="Mutiny")
def _mutiny(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    voters = set(_voted(state, "for"))
    for player in strategy_phase.speaker_order(state):
        if player not in voters:
            continue
        if ctx.get("outcome") == "for":
            objectives.award_points(state, player, 1)
        else:
            lose_points(state, player, 1)


# Swords to Plowshares - For: destroy half of infantry per planet (round up), gain TG;
# Against: place 1 infantry on each planet you control.
@on_outcome("plowshares", label="Swords to Plowshares")
def _plowshares(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    gained = 0
    for planet in controlled(state, pid):
        system = system_of_planet(state, planet)
        if ctx.get("outcome") == "for":
            infantry = unit_ops.count_in_zone(system, planet, pid, "infantry")
            kill = math.ceil(infantry / 2)
            if kill:
                unit_ops.remove_units(state, system, planet, pid, "infantry", kill,
                                      UnitCause.DESTROYED)
                gained += kill
        else:
            try:
                place_from_reinforcements(state, system, planet, pid, "infantry", 1)
            except ValueError:
                break  # rezerwa pusta
    if gained:
        economy.gain_trade_goods(state, pid, gained, cause="agenda")


# Rearmament Agreement - For: 1 mech on a home planet; Against: replace each mech with infantry.
# C_agendas: brak mecha w rezerwie => gracz MOŻE zdjąć mecha z systemu bez swojego żetonu
# (postawiony nieuszkodzony; R_component_limitations - zdolność nie może do tego zmusić).
_NO_SOURCE = "none"


def _rearm_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    planets = _home_planets(state, registry, player_id)
    options = [_option(p, _planet_label(state, registry, p)) for p in planets]
    inputs = [_choice("planet", "Home planet for the mech", options)]
    if planets and board_reinforcements.needs_board_source(state, player_id, "mech"):
        sources = board_reinforcements.source_options(state, registry, player_id, "mech")
        if sources:
            inputs.append(_choice(
                "source", "No mech in your reinforcements - take one from the board?",
                [_option(_NO_SOURCE, "Do not place a mech")]
                + [_option(value, label) for value, label in sources],
            ))
    return inputs


@on_outcome("rearmament", outcome="for", decide=True, inputs=_rearm_inputs,
            label="Rearmament Agreement")
def _rearm_for(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    params = _params(ctx)
    planet = str(params.get("planet") or "")
    if planet not in _home_planets(state, _registry(), pid):
        return
    source = str(params.get("source") or _NO_SOURCE)
    if board_reinforcements.needs_board_source(state, pid, "mech") and source == _NO_SOURCE:
        return  # rezerwa pusta, a gracz nie zdejmuje mecha z planszy
    board_reinforcements.place_unit(
        state, system_of_planet(state, planet), planet, pid, "mech",
        source=None if source == _NO_SOURCE else source,
    )


@on_outcome("rearmament", outcome="against", label="Rearmament Agreement")
def _rearm_against(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    for position, zone, _base in unit_instances(state, pid, base_types=("mech",)):
        system = state.systems[position]
        unit_ops.remove_units(state, system, zone, pid, "mech", 1, UnitCause.REMOVED)
        try:
            place_from_reinforcements(state, system, zone, pid, "infantry", 1)
        except ValueError:
            continue


# Colonial Redistribution - destroy each unit on the planet; its controller picks a player with
# the fewest VP, who places 1 infantry there.
def _redistribution_inputs(
    state: GameState, registry: StaticDataRegistry, _player_id: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    _most, fewest = most_and_fewest(state)
    from src.core.hooks.action_card_inputs import _player_label

    options = [_option(p, _player_label(state, registry, p)) for p in fewest]
    return [_choice("player", "Player with the fewest victory points to place 1 infantry", options)]


def _redistribution_controller(state: GameState, _owner: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx.get("controller") or ctx.get("speaker") or "")


@on_outcome("redistribution", once=True, label="Colonial Redistribution")
def _redistribution(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    planet = elected(ctx)
    system = system_of_planet(state, planet)
    for player in list(system.planet_units.get(planet, {})):
        for base_type, count in list(system.planet_units.get(planet, {}).get(player, {}).items()):
            if count:
                unit_ops.remove_units(state, system, planet, player, base_type, count,
                                      UnitCause.DESTROYED)
    controller = system.planet_owners.get(planet)
    if controller in state.players:
        schedule(state, "redistribution", "choose", controller, scope=Duration.PHASE,
                 planet=planet)


@on_event(GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.AFTER,
          effect_source("redistribution", "choose"), where={"agenda": "redistribution"},
          covers=covers("redistribution"),
          decide=True, inputs=_redistribution_inputs,
          label="Colonial Redistribution: choose who places 1 infantry")
def _redistribution_place(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    from src.core import active_effects, triggers

    effects = active_effects.effects_for(state, pid, "agendas:redistribution:choose")
    planet = str(effects[0].data.get("planet")) if effects else ""
    finish(state, "redistribution", "choose", pid)
    chosen = str(_params(ctx).get("player") or "")
    if not planet or chosen not in state.players:
        return
    # Karta: „that player MAY place 1 infantry” - decyduje wybrany gracz (oferta, RULES.md 56).
    schedule(state, "redistribution", "place", chosen, scope=Duration.PHASE, planet=planet)
    triggers.fire(
        state, GameEvent.FACTION_ABILITY_USED, Moment.AFTER, subject=chosen,
        ctx={"player": chosen, "ability": _REDISTRIBUTION_PLACE, "planet": planet},
    )


_REDISTRIBUTION_PLACE = "agendas:redistribution:place"


@on_event(GameEvent.FACTION_ABILITY_USED, Moment.AFTER, effect_source("redistribution", "place"),
          where={"ability": _REDISTRIBUTION_PLACE},
          condition=lambda s, p, c: p == c.get("player"), optional=True,
          covers=covers("redistribution"), label="Colonial Redistribution: place 1 infantry")
def _redistribution_infantry(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    finish(state, "redistribution", "place", pid)
    planet = str(ctx.get("planet") or "")
    system = system_of_planet(state, planet)
    try:
        place_from_reinforcements(state, system, planet, pid, "infantry", 1)
    except ValueError:
        return
    control.recompute_from_units(state, system.position, planet)


# Archived Secret - the elected player draws 1 secret objective (nadmiar oddawany po obejrzeniu).
@on_outcome("secret", condition=is_elected, label="Archived Secret")
def _archived_secret(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    _draw_revealed(state, "secret", pid, 1)


# Seed of an Empire - For: most VP gains 1; Against: fewest VP gains 1 (remis: wszyscy, od mówcy).
@on_outcome("seed_empire", once=True, label="Seed of an Empire")
def _seed(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    most, fewest = most_and_fewest(state)
    for player in most if ctx.get("outcome") == "for" else fewest:
        objectives.award_points(state, player, 1)


# Armed Forces Standardization - 3 tactic / 3 fleet / 2 strategy from reinforcements.
@on_outcome("standardization", condition=is_elected, label="Armed Forces Standardization")
def _standardization(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    current = {p: command_tokens.pool_count(state, pid, p) for p in command_tokens.POOLS}
    available = sum(current.values()) + command_tokens.reinforcements(state, pid)
    target: dict[str, int] = {}
    for pool in command_tokens.POOLS:  # ⚠️ za mało żetonów: pule wypełniane po kolei
        take = min(_STANDARD_POOLS.get(pool, 0), available)
        target[pool] = take
        available -= take
    delta = sum(target.values()) - sum(current.values())
    if delta > 0:
        command_tokens.take_from_reinforcements(state, pid, delta)
    elif delta < 0:
        command_tokens.return_to_reinforcements(state, pid, -delta)
    command_tokens.set_pools(state, pid, target)


# Unconventional Measures - For: voters "For" draw 2 AC; Against: voters "For" discard all AC.
@on_outcome("unconventional", once=True, label="Unconventional Measures")
def _unconventional(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    for player in _voted(state, "for"):
        if ctx.get("outcome") == "for":
            for _ in range(_UNCONVENTIONAL_DRAW):
                card_draw.draw_action_card(state, player)
        else:
            _discard_hand(state, player)


# Wormhole Research - For: ships in a wormhole system may research 1 tech; then destroy all ships
# in alpha/beta systems. Against: voters "Against" remove 1 token from the command sheet.
def _wormhole_systems(state: GameState, types: set[str] | None = None) -> list[str]:
    registry = _registry()
    return [
        pos for pos in state.systems
        if (found := board_graph.wormholes_at(state, registry, pos))
        and (types is None or found & types)
    ]


def _has_ships_in(state: GameState, player_id: str, positions: list[str]) -> bool:
    return any(ships_of(state.systems[p], player_id) for p in positions)


def _wr_can_research(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> bool:
    return _has_ships_in(state, pid, _wormhole_systems(state))


def _wr_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    # To samo okno badania co karta Technology (darmowe: koszt 0, skipy specjalnościami).
    return [research_offer.research_input(state, registry, player_id, 0)]


@on_outcome("wormhole_research", outcome="for", optional=True, condition=_wr_can_research,
            inputs=_wr_inputs, label="Wormhole Research: research 1 technology")
def _wr_research(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    if research_offer.chosen_tech(_params(ctx)) is None:
        return  # rezygnacja („may”) - bez zużycia zniżek badania
    research_offer.resolve(state, _registry(), pid, {"params": _params(ctx)})


@on_outcome("wormhole_research", outcome="for", once=True, moment=Moment.AFTER,
            label="Wormhole Research")
def _wr_destroy(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> None:
    for position in _wormhole_systems(state, _ALPHA_BETA):
        system = state.systems[position]
        for player, units in list(system.space_units.items()):
            for base_type, count in list(units.items()):
                if count <= 0:
                    continue
                # Statki niszczone; siły naziemne na orbicie znikają bez „destroyed" (C_agendas).
                # Struktury w przestrzeni (Floating Factory Saar) zostają - to nie statki
                # (C_agendas: „Floating Factories will not be destroyed by Wormhole Research").
                if is_space_unit(base_type):
                    cause = UnitCause.DESTROYED
                elif base_type in GROUND_FORCES:
                    cause = UnitCause.REMOVED
                else:
                    continue
                unit_ops.remove_units(state, system, "space", player, base_type, count, cause)


@on_outcome("wormhole_research", outcome="against", decide=True, inputs=_sheet_inputs(1),
            condition=lambda s, p, c: p in agenda_phase.voters_for(s, "against"),
            label="Wormhole Research")
def _wr_against(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    _remove_from_sheet(state, pid, 1, _params(ctx))


# =========================================================================================
# Jednorazowe skutki praw (przy rozstrzygnięciu)
# =========================================================================================


# Articles of War - Against: each player that voted "For" gains 3 TG.
@on_outcome("articles_war", outcome="against", once=True, label="Articles of War")
def _articles_against(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> None:
    for player in _voted(state, "for"):
        economy.gain_trade_goods(state, player, _ARTICLES_TG, cause="agenda")


# Political Censure - the elected player gains this card and 1 VP (ponowny wybór: Miscount).
@on_outcome("censure", once=True, label="Political Censure")
def _censure(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    target, previous = elected(ctx), str(ctx.get("previous") or "")
    if previous == target or target not in state.players:
        return
    if previous in state.players:
        lose_points(state, previous, 1)  # poprzedni właściciel traci kartę (i punkt)
    objectives.award_points(state, target, 1)


# Classified Document Leaks - the elected secret objective becomes a public objective.
@on_outcome("classified", once=True, label="Classified Document Leaks")
def _classified(state: GameState, _pid: str, ctx: Mapping[str, Any]) -> None:
    objectives.make_secret_public(state, elected(ctx))


# Conventions of War - Against: each player that voted "Against" discards all action cards.
@on_outcome("conventions", outcome="against", once=True, label="Conventions of War")
def _conventions_against(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> None:
    for player in _voted(state, "against"):
        _discard_hand(state, player)


# Homeland Defense Act - Against: each player destroys 1 of their PDS units.
def _pds_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    return destroy_choice_input(
        state, registry, unit_instances(state, player_id, base_types=("pds",)), 1,
        label="PDS to destroy",
    )


@on_outcome("defense_act", outcome="against", decide=True, inputs=_pds_inputs,
            label="Homeland Defense Act")
def _defense_against(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    units = unit_instances(state, pid, base_types=("pds",))
    if units:
        destroy_units(state, pid, chosen_units(_params(ctx), units, 1))


# Nexus Sovereignty - Against: place a gamma wormhole token in the Mecatol Rex system.
@on_outcome("nexus", outcome="against", once=True, label="Nexus Sovereignty")
def _nexus_against(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> None:
    for position, system in state.systems.items():
        if not custodians.is_mecatol_position(state, position):
            continue
        if "GAMMA" not in system.wormhole_tokens:
            system.wormhole_tokens.append("GAMMA")


# Fleet Regulations - For: ⚠️ nadmiar ponad 4 w fleet pool wraca do rezerwy;
# Against: each player places 1 token from reinforcements in their fleet pool.
@on_outcome("regulations", label="Fleet Regulations")
def _regulations(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    if ctx.get("outcome") == "for":
        from src.core.hooks.agendas_laws import FLEET_REGULATIONS_CAP

        excess = command_tokens.pool_count(state, pid, "fleet") - FLEET_REGULATIONS_CAP
        if excess > 0:
            command_tokens.spend_to_reinforcements(state, pid, "fleet", excess)
    elif command_tokens.reinforcements(state, pid) > 0:
        command_tokens.gain_from_reinforcements(state, pid, {"fleet": 1})


# Representative Government - Against: next strategy phase, voters "Against" exhaust cultural
# planets.
@on_outcome("rep_govt", outcome="against", once=True, label="Representative Government")
def _rep_against(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> None:
    for player in _voted(state, "against"):
        schedule(state, "rep_govt", "against", player)


@on_event(GameEvent.PHASE, Moment.START, effect_source("rep_govt", "against"),
          where={"phase": "strategy"}, covers=covers("rep_govt"),
          label="Representative Government")
def _rep_against_apply(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    from src.core.hooks.card_helpers import with_trait

    planets = with_trait(state, _registry(), pid, "cultural")
    exhaust.exhaust_planets(
        state, pid, [p for p in planets if p not in state.players[pid].exhausted_planets]
    )
    finish(state, "rep_govt", "against", pid)


# Anti-Intellectual Revolution - Against: next strategy phase each player exhausts 1 planet per
# technology they own (planety wybiera gracz; tylko kontrolowane - C_agendas).
@on_outcome("revolution", outcome="against", label="Anti-Intellectual Revolution")
def _revolution_against(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    schedule(state, "revolution", "against", pid)


def _revolution_targets(state: GameState, player_id: str) -> tuple[list[str], int]:
    ready = [p for p in controlled(state, player_id)
             if p not in state.players[player_id].exhausted_planets]
    return ready, min(len(state.players[player_id].technologies), len(ready))


def _revolution_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    ready, count = _revolution_targets(state, player_id)
    if count == 0 or count >= len(ready):
        return []
    options = [_option(p, _planet_label(state, registry, p)) for p in ready]
    return [multi("planets", f"Planets to exhaust ({count})", options, count, count)]


@on_event(GameEvent.PHASE, Moment.START, effect_source("revolution", "against"),
          where={"phase": "strategy"}, covers=covers("revolution"), decide=True,
          inputs=_revolution_inputs, label="Anti-Intellectual Revolution")
def _revolution_apply(state: GameState, pid: str, ctx: Mapping[str, Any]) -> None:
    ready, count = _revolution_targets(state, pid)
    picks = [str(p) for p in _params(ctx).get("planets", [])] or ready[:count]
    exhaust.exhaust_planets(state, pid, [p for p in picks if p in ready][:count])
    finish(state, "revolution", "against", pid)


# Executive Sanctions - Against: each player discards 1 random action card.
@on_outcome("sanctions", outcome="against", label="Executive Sanctions")
def _sanctions_against(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    hand = state.players[pid].private.action_cards
    if hand:
        card = hand[next_rng(state).randrange(len(hand))]
        card_draw.discard_specific_action_cards(state, pid, [card])


# Publicize Weapon Schematics - Against: each player that owns a war sun technology discards
# all of their action cards.
@on_outcome("schematics", outcome="against", label="Publicize Weapon Schematics")
def _schematics_against(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    from src.core.hooks.agendas_laws import owns_war_sun_tech

    if owns_war_sun_tech(state, _registry(), pid):
        _discard_hand(state, pid)


# Shared Research - Against: each player places a command token in their home system, if able.
@on_outcome("shared_research", outcome="against", label="Shared Research")
def _shared_against(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    for position in board_graph.home_positions_by_player(state, _registry()).get(pid, [])[:1]:
        system = state.systems.get(position)
        if system is None:
            continue
        try:
            command_tokens.place_on_board_from_reinforcements(state, system, pid)
        except ValueError:
            return


# Enforced Travel Ban - Against: destroy each PDS in or adjacent to a system with a wormhole.
@on_outcome("travel_ban", outcome="against", once=True, label="Enforced Travel Ban")
def _travel_ban_against(state: GameState, _pid: str, _ctx: Mapping[str, Any]) -> None:
    wormholes = set(_wormhole_systems(state))
    hit = set(wormholes)
    for position in wormholes:
        hit |= board_graph.adjacent_positions(position)
    for player in list(state.players):
        destroy_units(state, player, unit_instances(
            state, player, positions=sorted(p for p in hit if p in state.systems),
            base_types=("pds",),
        ))


# Search Warrant - the elected player draws 2 secret objectives (prawo: jawne cele - laws).
# C_agendas: dobrane karty są odkryte, zanim gracz wybierze, które oddać ponad limit.
@on_outcome("warrant", condition=lambda s, p, c: p == c.get("outcome")
            and c.get("previous") != p, label="Search Warrant")
def _warrant(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    _draw_revealed(state, "warrant", pid, _WARRANT_SECRETS)


# Wormhole Reconstruction - Against: each player places a token in each wormhole system that
# contains 1 or more of their ships.
@on_outcome("wormhole_recon", outcome="against", label="Wormhole Reconstruction")
def _recon_against(state: GameState, pid: str, _ctx: Mapping[str, Any]) -> None:
    for position in _wormhole_systems(state):
        system = state.systems[position]
        if not ships_of(system, pid) or pid in system.command_tokens:
            continue
        try:
            command_tokens.place_on_board_from_reinforcements(state, system, pid)
        except ValueError:
            return
