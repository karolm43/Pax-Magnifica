"""Karty reakcji grane w fazie agendy (RULES.md 53.5.a): riders, Veto, Bribery, Deadly Plot...

Okna WYLICZANE z ``GameState.agenda`` (krok ``AgendaStep``):

* początek fazy agendy      - ``REVEAL`` przed pierwszą agendą (Ancient Burial Sites);
* agenda ujawniona          - ``VOTE`` bez żadnego głosu i wstrzymania (Veto, Diplomatic Pressure
  "when"; riders, Assassinate Representative, Hack Election, Insider Information "after");
* po głosach gracza         - ``agenda.last_vote_by`` (Distinguished Councilor) oraz „mówca już
  głosował / wstrzymał się" (Bribery);
* wynik ma być rozstrzygnięty / wybrany gracz - krok ``COUNTED`` (Deadly Plot, Confounding/
  Confusing Legal Text). Krok ``COUNTED`` powstaje, gdy ktoś trzyma kartę na ten moment
  (``agenda_phase.PAUSE_BEFORE_RESOLUTION_ALWAYS``).

Zmiany stanu agendy WYŁĄCZNIE przez funkcje ``agenda_phase`` (``block_voter``,
``vote_last``, ``veto_agenda``, ``add_votes``, ``replace_elected``, ``void_agenda``).
Predykcje riderów to efekty trwałe (``active_effects``, zakres ``AGENDA``) z danymi
``{outcome, ...nagroda}``; rozstrzyga je hook zdarzenia ``AGENDA_OUTCOME_RESOLVED`` / AFTER
(efekt agendy jest już zapisany - C_action_cards:
„effect of a successful rider will be resolved after the effect of the agenda").
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from src.core import (
    active_effects,
    agenda_phase,
    board_reinforcements,
    card_draw,
    command_tokens,
    economy,
    exhaust,
    exploration,
    objectives,
    promissory_notes,
    rules_hooks,
    strategy_phase,
    technology,
    triggers,
)
from src.core import offer_inputs as oi
from src.core.components import ComponentCategory
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import (
    AgendaPhaseState,
    AgendaStep,
    GameState,
    Phase,
    SystemState,
)
from src.core.hooks import card_targets_economy as targets
from src.core.hooks.action_card_inputs import (
    Input,
    _choice,
    _multi,
    _number,
    _option,
    _planet_label,
    _player_label,
    _system_label,
)
from src.core.hooks.card_helpers import controlled, system_of_planet
from src.core.reaction_cards import (
    OpenWindow,
    card_effect_source,
    declare_reaction,
    window_provider,
)
from src.core.registry import StaticDataRegistry
from src.core.rules_hooks import on_event, register_effect, register_effect_inputs
from src.core.strategy_cards.common import structure_problem
from src.core.unit_catalog import is_space_unit

# --- Stałe z tekstów kart (assets/data/action_cards) --------------------------------------
_IMPERIAL_RIDER_VP = 1  # „gain 1 victory point"
_LEADERSHIP_RIDER_TOKENS = 3  # „gain 3 command tokens"
_POLITICS_RIDER_CARDS = 3  # „draw 3 action cards"
_TRADE_RIDER_TG = 5  # „gain 5 trade goods"
_DISTINGUISHED_VOTES = 5  # „Cast 5 additional votes for that outcome"
_INSIDER_COUNT = 3  # „Look at the top 3 cards of the agenda deck"

_NO_SOURCE = "none"  # form value: do not take a unit from the board

_VOTING_STEPS = (AgendaStep.VOTE, AgendaStep.TIEBREAK, AgendaStep.COUNTED)

_KIND_VOTED = "voted"  # okno „po tym, jak gracz oddał głosy"
_KIND_SPEAKER = "speaker"  # okno „po tym, jak mówca zagłosował / wstrzymał się"
# Hack Election Ω: kto głosuje ostatni w tej agendzie (nie zagra Bribery - ruling).
HACK_ELECTION = "action_cards:hack:vote_last"
# Confounding/Confusing Legal Text changed the elected player: no more additional votes
# (Bribery / Distinguished Councilor come before outcome-changing effects, C_action_cards).
OUTCOME_CHANGED = "action_cards:legal_text:outcome_changed"


# =========================================================================================
# Okna
# =========================================================================================


def _speaker_window_open(state: GameState, agenda: Any, speaker: str) -> bool:
    """Okno „po głosie mówcy” (Bribery): mówca już zagłosował / wstrzymał się, a nikt po nim w
    kolejce jeszcze nie głosował. Mówca Argent głosuje PIERWSZY (Zeal), więc Bribery zagrywa tylko
    on i tylko od razu po swoim głosie (C_action_cards). Głos gracza z Hack Election Ω (ostatni,
    po mówcy) okna nie zamyka - on sam Bribery i tak nie zagra."""
    order = list(agenda.vote_order)
    place = order.index(speaker) if speaker in order else len(order)
    done = {*agenda.votes, *agenda.abstained, *agenda.blocked}
    if not (speaker in agenda.votes or speaker in agenda.abstained):
        # A speaker who cannot vote: the window opens when they "would vote", not at the reveal.
        if speaker not in agenda.blocked or any(p not in done for p in order[:place]):
            return False
    later = order[place + 1:]
    return not any(
        (p in agenda.votes or p in agenda.abstained)
        and not active_effects.has_effect(state, p, HACK_ELECTION)
        for p in later
    )


@window_provider
def agenda_windows(state: GameState) -> list[OpenWindow]:
    """Okna fazy agendy wyliczone z kroku ``AgendaPhaseState`` (bez mutacji)."""
    agenda = state.agenda
    speaker = state.speaker_id
    if state.phase is not Phase.AGENDA or agenda is None or speaker is None:
        return []
    windows: list[OpenWindow] = []
    card = agenda.agenda_id
    if (
        agenda.step is AgendaStep.REVEAL
        and card is None
        and agenda.agenda_number == 1
        and not agenda.history
    ):
        start_ctx = {"player": speaker, "phase": "agenda"}
        windows.append(OpenWindow(GameEvent.PHASE, Moment.START, start_ctx))
    if card is None:
        return windows
    base: dict[str, Any] = {"agenda": card}
    if agenda.step is AgendaStep.VOTE and not agenda.votes and not agenda.abstained:
        ctx = {**base, "player": speaker}
        # „When” zamyka się, gdy ktoś zagrał kartę „after” (ridery): when przed after (R_abilities).
        if agenda.after_reveal_played != card:
            windows.append(OpenWindow(GameEvent.AGENDA_REVEALED, Moment.WHEN, dict(ctx)))
        windows.append(OpenWindow(GameEvent.AGENDA_REVEALED, Moment.AFTER, dict(ctx)))
    if agenda.step in _VOTING_STEPS:
        last = agenda.last_vote_by
        if last is not None and last in agenda.votes:
            cast = agenda.votes[last]
            windows.append(
                OpenWindow(
                    GameEvent.AGENDA_VOTES_CAST,
                    Moment.AFTER,
                    {**base, "player": last, "outcome": cast.outcome, "votes": cast.votes,
                     "kind": _KIND_VOTED},
                )
            )
        if _speaker_window_open(state, agenda, speaker):
            windows.append(
                OpenWindow(
                    GameEvent.AGENDA_VOTES_CAST,
                    Moment.AFTER,
                    {**base, "player": speaker, "kind": _KIND_SPEAKER},
                )
            )
    if agenda.step is AgendaStep.COUNTED and agenda.pending_outcome is not None:
        count_ctx = {**base, "outcome": agenda.pending_outcome}
        resolving = {**count_ctx, "player": speaker}
        windows.append(OpenWindow(GameEvent.AGENDA_OUTCOME_RESOLVED, Moment.DURING, resolving))
        elected = agenda_phase.elected_player(state)
        if elected is not None:
            windows.append(
                OpenWindow(GameEvent.AGENDA_ELECTED, Moment.WHEN, {**count_ctx, "player": elected})
            )
    return windows


# =========================================================================================
# Pomocnicze: formularze i walidacje
# =========================================================================================


def _agenda_or_fail(state: GameState) -> AgendaPhaseState:
    if state.phase is not Phase.AGENDA or state.agenda is None or state.agenda.agenda_id is None:
        raise ValueError("There is no agenda being resolved right now.")
    return state.agenda


def _outcome_label(state: GameState, registry: StaticDataRegistry, outcome: str) -> str:
    if outcome in state.players:
        return _player_label(state, registry, outcome)
    planet = registry.planets.get(outcome)
    if planet is not None:
        return _planet_label(state, registry, outcome)
    return outcome.replace("_", " ").title()


def _outcome_input(state: GameState, registry: StaticDataRegistry) -> Input:
    """Wejście „przewidywany wynik": opcje to wyniki bieżącej agendy (``agenda.outcomes``)."""
    agenda = state.agenda
    outcomes = list(agenda.outcomes) if agenda is not None else []
    options = [_option(o, _outcome_label(state, registry, o)) for o in outcomes]
    return _choice(
        "outcome",
        "Predicted outcome",
        options,
        hint="Pick the outcome of the current agenda you predict; the rider pays off "
        "if it wins.",
    )


def _player_options(
    state: GameState, registry: StaticDataRegistry, players: list[str]
) -> list[dict[str, Any]]:
    return [_option(pid, _player_label(state, registry, pid)) for pid in players]


def _own_planet_systems(state: GameState, player_id: str) -> list[str]:
    owned = set(controlled(state, player_id))
    return [
        position
        for position, system in state.systems.items()
        if owned.intersection(system.planet_owners)
    ]


def _ship_systems(state: GameState, player_id: str) -> list[str]:
    return [
        position
        for position, system in state.systems.items()
        if any(
            n > 0 and is_space_unit(bt)  # carried ground forces are not ships
            for bt, n in system.space_units.get(player_id, {}).items()
        )
    ]


def _system_option(state: GameState, registry: StaticDataRegistry, position: str) -> dict[str, Any]:
    return _option(position, _system_label(registry, state.systems[position]))


def _system_choice(
    state: GameState, registry: StaticDataRegistry, label: str, positions: list[str]
) -> Input:
    return _choice("position", label, [_system_option(state, registry, p) for p in positions])


def _position_param(
    state: GameState, params: Mapping[str, Any], allowed: list[str], what: str
) -> str:
    position = params.get("position")
    if not isinstance(position, str) or position not in allowed or position not in state.systems:
        raise ValueError(f"Choose {what} ('position').")
    return position


# =========================================================================================
# Riders (predykcje)
# =========================================================================================

InputsFn = Callable[[GameState, StaticDataRegistry, str], list[Input]]
ValidateFn = Callable[[GameState, StaticDataRegistry, str, Mapping[str, Any]], dict[str, Any]]
RewardFn = Callable[[GameState, StaticDataRegistry, str, Mapping[str, Any], str], None]


@dataclass(frozen=True)
class _Rider:
    """Rider: dodatkowe wejścia formularza, walidacja wyborów i nagroda za trafne przewidywanie."""

    inputs: InputsFn
    validate: ValidateFn
    reward: RewardFn


def _no_inputs(_s: GameState, _r: StaticDataRegistry, _p: str) -> list[Input]:
    return []


def _no_validation(
    _s: GameState, _r: StaticDataRegistry, _p: str, _params: Mapping[str, Any]
) -> dict[str, Any]:
    return {}


# Empty reinforcements: the unit may be taken from the board instead (C_action_cards).
# The source is clicked on the map; "Auto" = "Do not place" (⚠️ ASSUMPTION, RULES.md 53:
# nothing leaves the board without the player's manual choice - R_component_limitations).
def _source_inputs(
    state: GameState, registry: StaticDataRegistry, player_id: str, base_type: str
) -> list[Input]:
    if not board_reinforcements.needs_board_source(state, player_id, base_type):
        return []
    sources = board_reinforcements.map_source_options(state, registry, player_id, base_type)
    if not sources:
        return []
    name = "space dock" if base_type == targets.SPACE_DOCK else base_type
    return [oi.choice(
        "source", f"No {name} in your reinforcements - take one from the board?",
        [_option(_NO_SOURCE, f"Do not place a {name}"), *sources],
        "Click your unit on the map (systems without your command token).",
        auto=_NO_SOURCE,
    )]


def _source_data(
    state: GameState, player_id: str, base_type: str, params: Mapping[str, Any]
) -> dict[str, Any]:
    source = params.get("source")
    if source in (None, "", _NO_SOURCE):
        return {}
    if source not in board_reinforcements.board_sources(state, player_id, base_type):
        raise ValueError(
            f"Choose your {base_type} on the board in a system without your command token."
        )
    return {"source": source}


def _place_reward_unit(
    state: GameState, system: SystemState, zone: str, player_id: str, base_type: str,
    data: Mapping[str, Any],
) -> None:
    source = data.get("source")
    if not source and board_reinforcements.needs_board_source(state, player_id, base_type):
        return  # "Do not place" (Auto): reinforcements empty and no unit taken from the board
    board_reinforcements.place_unit(
        state, system, zone, player_id, base_type, source=str(source) if source else None
    )


# Construction Rider - place 1 space dock from your reinforcements on a planet you control.
def _dock_problem(state: GameState, player_id: str, planet: str) -> str | None:
    return structure_problem(state, player_id, planet, targets.SPACE_DOCK, allow_board=True)


def _const_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    options = [
        _option(p, _planet_label(state, registry, p))
        for p in controlled(state, player_id)
        if _dock_problem(state, player_id, p) is None
    ]
    return [
        _choice("planet", "Planet you control (for the space dock)", options),
        *_source_inputs(state, registry, player_id, targets.SPACE_DOCK),
    ]


def _const_validate(
    state: GameState, _r: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> dict[str, Any]:
    planet = params.get("planet")
    if not isinstance(planet, str) or planet not in controlled(state, player_id):
        raise ValueError("Choose 1 planet you control ('planet').")
    problem = _dock_problem(state, player_id, planet)
    if problem is not None:
        raise ValueError(problem)
    return {"planet": planet, **_source_data(state, player_id, targets.SPACE_DOCK, params)}


def _const_reward(
    state: GameState, _r: StaticDataRegistry, player_id: str, data: Mapping[str, Any], _o: str
) -> None:
    planet = str(data.get("planet"))
    if planet not in controlled(state, player_id):
        raise ValueError(f"{player_id} no longer controls {planet}.")
    problem = _dock_problem(state, player_id, planet)
    if problem is not None:
        raise ValueError(problem)
    _place_reward_unit(
        state, system_of_planet(state, planet), planet, player_id, targets.SPACE_DOCK, data
    )


# Diplomacy Rider - choose 1 system that contains a planet you control. Each other player places
# a command token from their reinforcements in that system.
def _diplo_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    systems = _own_planet_systems(state, player_id)
    return [_system_choice(state, registry, "System with a planet you control", systems)]


def _diplo_validate(
    state: GameState, _r: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> dict[str, Any]:
    position = _position_param(
        state, params, _own_planet_systems(state, player_id), "a system with a planet you control"
    )
    return {"position": position}


def _diplo_reward(
    state: GameState, _r: StaticDataRegistry, player_id: str, data: Mapping[str, Any], _o: str
) -> None:
    position = str(data.get("position"))
    if position not in _own_planet_systems(state, player_id):
        raise ValueError(f"{player_id} no longer controls a planet in system {position}.")
    system = state.systems[position]
    for other in state.players:
        if other == player_id:
            continue
        try:
            command_tokens.place_on_board_from_reinforcements(state, system, other)
        except ValueError:
            continue  # ma już żeton w systemie albo pustą rezerwę - nic nie kładzie


def _imperial_reward(
    state: GameState, _r: StaticDataRegistry, player_id: str, _d: Mapping[str, Any], _o: str
) -> None:
    objectives.award_points(state, player_id, _IMPERIAL_RIDER_VP, source="action_cards:imp_rider")


# Leadership Rider - gain 3 command tokens (rozkład na pule wybiera gracz przy zagraniu karty).
def _lead_inputs(_s: GameState, _r: StaticDataRegistry, _p: str) -> list[Input]:
    return [
        _number(
            pool,
            f"Tokens to the {pool} pool",
            0,
            _LEADERSHIP_RIDER_TOKENS,
            f"The three pools must add up to {_LEADERSHIP_RIDER_TOKENS}.",
            # Auto: po równo (3 żetony = 1 na pulę; RULES.md 53.5.a - ⚠️ ZAŁOŻENIE „Auto”).
            auto=_LEADERSHIP_RIDER_TOKENS // len(command_tokens.POOLS)
            + (1 if index < _LEADERSHIP_RIDER_TOKENS % len(command_tokens.POOLS) else 0),
        )
        for index, pool in enumerate(command_tokens.POOLS)
    ]


def _lead_validate(
    _s: GameState, _r: StaticDataRegistry, _p: str, params: Mapping[str, Any]
) -> dict[str, Any]:
    pools: dict[str, int] = {}
    for pool in command_tokens.POOLS:
        value = params.get(pool, 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"Enter a non-negative number of tokens for the {pool} pool.")
        pools[pool] = value
    if sum(pools.values()) != _LEADERSHIP_RIDER_TOKENS:
        raise ValueError(f"Distribute exactly {_LEADERSHIP_RIDER_TOKENS} command tokens.")
    return pools


def _lead_reward(
    state: GameState, _r: StaticDataRegistry, player_id: str, data: Mapping[str, Any], _o: str
) -> None:
    room = command_tokens.reinforcements(state, player_id)  # tyle żetonów, ile jest w rezerwie
    gains: dict[str, int] = {}
    for pool in command_tokens.POOLS:
        take = min(int(data.get(pool, 0)), room)
        if take > 0:
            gains[pool] = take
            room -= take
    if gains:
        command_tokens.gain_from_reinforcements(state, player_id, gains)


# Politics Rider - draw 3 action cards and gain the speaker token.
def _politics_reward(
    state: GameState, _r: StaticDataRegistry, player_id: str, _d: Mapping[str, Any], _o: str
) -> None:
    card_draw.draw_action_cards(state, player_id, _POLITICS_RIDER_CARDS)
    strategy_phase.set_speaker(state, player_id)


# Sanction - each player that voted for that outcome returns 1 command token from their fleet
# supply to their reinforcements.
def _sanction_reward(
    state: GameState, _r: StaticDataRegistry, _player: str, _d: Mapping[str, Any], outcome: str
) -> None:
    agenda = state.agenda
    if agenda is None:
        return
    for voter, vote in agenda.votes.items():
        if vote.outcome == outcome:
            command_tokens.remove_fleet_token(state, voter)  # own first (F_mahact edict 2)


# Technology Rider - research 1 technology (wybór przy zagraniu karty). C_action_cards: wolno
# wyczerpać planetę ze specjalnością / AI Development Algorithm, by zignorować prerekwizyt.
def _directly_researchable(
    state: GameState, registry: StaticDataRegistry, player_id: str, skips: list[str] | None = None
) -> list[str]:
    return [
        tech.id for tech in technology.researchable_techs(state, registry, player_id)
        if technology.plan_with_skips(state, registry, player_id, tech.id, skips or []) is not None
    ]


def _skips(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    return [v for v, _ in technology.skip_choices(state, registry, player_id)]


def _tech_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    everything = _skips(state, registry, player_id)
    options = [
        _option(tech_id, registry.technologies[tech_id].name)
        for tech_id in _directly_researchable(state, registry, player_id, everything)
        if tech_id in registry.technologies
    ]
    inputs = [_choice("tech", "Technology to research", options)]
    skips = technology.skip_choices(state, registry, player_id)
    if skips:
        inputs.append(_multi(
            "skips", "Exhaust to ignore prerequisites (optional)",
            [_option(v, label) for v, label in skips], 0, len(skips),
        ))
    return inputs


def _tech_validate(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> dict[str, Any]:
    tech = params.get("tech")
    raw = params.get("skips") or []
    skips = [str(s) for s in raw] if isinstance(raw, list) else []
    allowed = set(_skips(state, registry, player_id))
    if any(s not in allowed for s in skips):
        raise ValueError("Choose ready planets with a technology specialty ('skips').")
    if not isinstance(tech, str) or tech not in _directly_researchable(
        state, registry, player_id, skips
    ):
        raise ValueError("Choose a technology you can research ('tech').")
    return {"tech": tech, "skips": skips}


def _tech_reward(
    state: GameState, registry: StaticDataRegistry, player_id: str, data: Mapping[str, Any], _o: str
) -> None:
    skips = [str(s) for s in data.get("skips") or []]
    plan = technology.plan_with_skips(state, registry, player_id, str(data.get("tech")), skips)
    if plan is None:
        raise ValueError("You can no longer research that technology (prerequisites).")
    technology.apply_research(state, player_id, plan)


def _trade_reward(
    state: GameState, _r: StaticDataRegistry, player_id: str, _d: Mapping[str, Any], _o: str
) -> None:
    economy.gain_trade_goods(state, player_id, _TRADE_RIDER_TG)


# Warfare Rider - place 1 dreadnought from your reinforcements in a system that contains 1 or
# more of your ships.
def _war_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    systems = _ship_systems(state, player_id)
    return [
        _system_choice(state, registry, "System with your ships", systems),
        *_source_inputs(state, registry, player_id, "dreadnought"),
    ]


def _war_validate(
    state: GameState, _r: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> dict[str, Any]:
    position = _position_param(
        state, params, _ship_systems(state, player_id), "a system that contains your ships"
    )
    return {"position": position, **_source_data(state, player_id, "dreadnought", params)}


def _war_reward(
    state: GameState, _r: StaticDataRegistry, player_id: str, data: Mapping[str, Any], _o: str
) -> None:
    position = str(data.get("position"))
    if position not in _ship_systems(state, player_id):
        raise ValueError(f"{player_id} has no ships in system {position} any more.")
    _place_reward_unit(state, state.systems[position], "space", player_id, "dreadnought", data)


_RIDERS: dict[str, _Rider] = {
    "const_rider": _Rider(_const_inputs, _const_validate, _const_reward),
    "diplo_rider": _Rider(_diplo_inputs, _diplo_validate, _diplo_reward),
    "imp_rider": _Rider(_no_inputs, _no_validation, _imperial_reward),
    "lead_rider": _Rider(_lead_inputs, _lead_validate, _lead_reward),
    "politic_rider": _Rider(_no_inputs, _no_validation, _politics_reward),
    "sanction": _Rider(_no_inputs, _no_validation, _sanction_reward),
    "tech_rider": _Rider(_tech_inputs, _tech_validate, _tech_reward),
    "trade_rider": _Rider(_no_inputs, _no_validation, _trade_reward),
    "war_rider": _Rider(_war_inputs, _war_validate, _war_reward),
}


def _effect_key(card_id: str) -> str:
    return f"action_cards:{card_id}"


def predictions(state: GameState, player_id: str) -> list[tuple[str, str]]:
    """Przewidywania gracza w bieżącej agendzie: ``[(id karty, przewidywany wynik)]``."""
    keys = {_effect_key(card): card for card in _RIDERS}
    return [
        (keys[e.key], str(e.data.get("outcome")))
        for e in state.active_effects
        if e.owner == player_id and e.key in keys
    ]


def _log_rider(state: GameState, note: dict[str, Any]) -> None:
    """Zapisuje wynik rozstrzygnięcia ridera w historii ostatniej agendy (jawne, do panelu)."""
    if state.agenda is not None and state.agenda.history:
        state.agenda.history[-1].setdefault("riders", []).append(note)


def _register_rider(card_id: str, rider: _Rider) -> None:
    key = _effect_key(card_id)

    def inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
        return [_outcome_input(state, registry), *rider.inputs(state, registry, player_id)]

    def effect(
        state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
    ) -> None:
        """Rider: You cannot vote on this agenda. Predict aloud an outcome of this agenda. If your
        prediction is correct, <nagroda z tekstu karty> (rozstrzygana po efekcie agendy).
        """
        agenda = _agenda_or_fail(state)
        outcome = params.get("outcome")
        if not isinstance(outcome, str) or outcome not in agenda.outcomes:
            raise ValueError("Predict one of the possible outcomes of this agenda ('outcome').")
        data = rider.validate(state, registry, player_id, params)
        # Predykcja musi istnieć ZANIM zablokowanie głosu pozwoli agendzie się rozstrzygnąć.
        active_effects.add_effect(
            state, key, Duration.AGENDA, owner=player_id, data={"outcome": outcome, **data}
        )
        agenda_phase.block_voter(state, registry, player_id)

    def settle(state: GameState, player_id: str, ctx: Mapping[str, Any]) -> None:
        registry = rules_hooks.bound_registry()
        resolved = str(ctx.get("outcome"))
        for found in [e for e in state.active_effects if e.key == key and e.owner == player_id]:
            predicted = str(found.data.get("outcome"))
            note: dict[str, Any] = {
                "player": player_id, "card": card_id, "predicted": predicted,
                "correct": predicted == resolved,
            }
            if predicted == resolved:
                try:
                    rider.reward(state, registry, player_id, found.data, resolved)
                except ValueError as exc:  # nagroda niewykonalna (np. brak w rezerwie)
                    note["skipped"] = str(exc)
            _log_rider(state, note)

    register_effect(key)(effect)
    register_effect_inputs(key)(inputs)
    on_event(
        GameEvent.AGENDA_OUTCOME_RESOLVED,
        Moment.AFTER,
        card_effect_source(card_id),
        label=f"Prediction ({card_id})",
    )(settle)


for _card_id, _rider in _RIDERS.items():
    _register_rider(_card_id, _rider)


# =========================================================================================
# Assassinate Representative, Hack Election, Insider Information
# =========================================================================================


@register_effect_inputs("action_cards:assassin")
def assassin_inputs(state: GameState, registry: StaticDataRegistry, _player_id: str) -> list[Input]:
    agenda = state.agenda
    blocked = set(agenda.blocked) if agenda is not None else set()
    players = [pid for pid in state.players if pid not in blocked]
    return [_choice("player", "Player who cannot vote", _player_options(state, registry, players))]


@register_effect("action_cards:assassin")
def assassin(
    state: GameState, registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Assassinate Representative: Choose 1 player. That player cannot vote on this agenda."""
    target = params.get("player")
    if not isinstance(target, str) or target not in state.players:
        raise ValueError("Choose 1 player ('player').")
    _agenda_or_fail(state)
    agenda_phase.block_voter(state, registry, target)


@register_effect("action_cards:hack")
def hack(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Hack Election Ω (Thunder's Edge): During this agenda, you vote last.

    Zagrywający głosuje po mówcy; nie może potem zagrać Bribery (ruling ``C_action_cards``) -
    znacznik ``HACK_ELECTION`` (zakres agendy) sprawdza warunek Bribery.
    """
    _agenda_or_fail(state)
    agenda_phase.vote_last(state, player_id)
    active_effects.add_effect(state, HACK_ELECTION, Duration.AGENDA, owner=player_id)


@register_effect("action_cards:insider")
def insider(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Insider Information: Look at the top 3 cards of the agenda deck.

    Podgląd trafia do prywatnego ``player.private.agenda_peek`` (widzi go tylko właściciel).
    """
    card_draw.peek_agenda_top(state, player_id, _INSIDER_COUNT)


# =========================================================================================
# Diplomatic Pressure (dp1..dp4)
# =========================================================================================

_DP_GIVE = "dp_give"  # klucz efektu/hooka oferty „oddaj notkę" (nie jest kartą)
_DP_TRACK = "agenda_phase:dp_target"  # kogo gracz już wskazał w tej agendzie (ruling)
_DIPLOMATIC_PRESSURE = ("dp1", "dp2", "dp3", "dp4")


def _dp_already_targeted(state: GameState, player_id: str) -> set[str]:
    return {
        str(e.data.get("target"))
        for e in state.active_effects
        if e.key == _DP_TRACK and e.owner == player_id
    }


def _note_label(registry: StaticDataRegistry, note_id: str) -> str:
    note = registry.catalog.get(ComponentCategory.PROMISSORY_NOTE, note_id)
    name = getattr(note, "name", None)
    return str(name) if name else note_id


def _dp_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    taken = _dp_already_targeted(state, player_id)
    players = [
        pid
        for pid in state.players
        if pid != player_id and pid not in taken and state.players[pid].private.promissory_notes
    ]
    options = _player_options(state, registry, players)
    return [_choice("player", "Player who gives you a promissory note", options)]


def _dp_effect(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Diplomatic Pressure: Choose another player. That player must give you 1 promissory note
    from their hand.

    Notkę wybiera OSTATNI krok - gracz wskazany (ruling: „the target player chooses"), przez
    obowiązkową ofertę ``decide``; przy jednej notce oddawana jest od razu.
    """
    target = params.get("player")
    if (
        not isinstance(target, str)
        or target == player_id
        or target not in _dp_inputs_players(state, registry, player_id)
    ):
        raise ValueError("Choose another player who has a promissory note and was not chosen yet.")
    active_effects.add_effect(
        state, _DP_TRACK, Duration.AGENDA, owner=player_id, data={"target": target}
    )
    pending = active_effects.add_effect(
        state, _effect_key(_DP_GIVE), Duration.ROUND, owner=player_id, data={"target": target}
    )
    result = triggers.fire(
        state, GameEvent.ACTION_CARD_PLAYED, Moment.AFTER, subject=player_id,
        ctx={"player": player_id, "card": _DP_GIVE, "target": target},
    )
    if not result.offers:  # oddane od razu (jedna notka) albo nic do oddania - bez wiszącego efektu
        active_effects.remove_effect(state, pending.id)


def _dp_inputs_players(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[str]:
    options = _dp_inputs(state, registry, player_id)[0]["options"]
    return [str(o["value"]) for o in options]


def _dp_give_inputs(
    state: GameState, registry: StaticDataRegistry, decider: str, _ctx: Mapping[str, Any]
) -> list[Input]:
    # Hubris: only notes the receiver may get (F_mahact hubris 1).
    hand = promissory_notes.giveable(state, decider, str(_ctx.get("player") or ""))
    options = [_option(n, _note_label(registry, n), f"{n}#{i}") for i, n in enumerate(hand)]
    return [_choice("note", "Promissory note to give", options)]


def _dp_decider(_state: GameState, _owner: str, ctx: Mapping[str, Any]) -> str:
    return str(ctx["target"])


@on_event(
    GameEvent.ACTION_CARD_PLAYED,
    Moment.AFTER,
    card_effect_source(_DP_GIVE),
    where={"card": _DP_GIVE},
    inputs=_dp_give_inputs,
    decide=True,
    decider=_dp_decider,
    label="Diplomatic Pressure: give a promissory note",
)
def _dp_give(state: GameState, owner_id: str, ctx: Mapping[str, Any]) -> None:
    params = ctx.get("params") or {}
    target = str(ctx["target"])
    note = params.get("note")
    if not isinstance(note, str):
        raise ValueError("Choose a promissory note to give ('note').")
    promissory_notes.transfer(state, target, owner_id, note)
    for found in [
        e
        for e in state.active_effects
        if e.key == _effect_key(_DP_GIVE) and e.owner == owner_id and e.data.get("target") == target
    ]:
        active_effects.remove_effect(state, found.id)


def _register_diplomatic_pressure(card_id: str) -> None:
    register_effect(_effect_key(card_id))(_dp_effect)
    register_effect_inputs(_effect_key(card_id))(_dp_inputs)


for _dp in _DIPLOMATIC_PRESSURE:
    _register_diplomatic_pressure(_dp)


# =========================================================================================
# Veto
# =========================================================================================


def _veto_effect(
    state: GameState, registry: StaticDataRegistry, _player_id: str, _params: Mapping[str, Any]
) -> None:
    """Veto: Discard that agenda and reveal 1 agenda from the top of the deck. Players vote on
    this agenda instead.
    """
    _agenda_or_fail(state)
    agenda_phase.veto_agenda(state, registry)


for _veto in ("veto", "veto3", "veto4"):
    register_effect(_effect_key(_veto))(_veto_effect)


def _veto_ok(state: GameState, _r: StaticDataRegistry, _p: str, _w: OpenWindow) -> bool:
    return bool(state.decks.agenda_deck)  # jest co ujawnić


declare_reaction("veto", "veto3", "veto4", condition=_veto_ok)


# =========================================================================================
# Bribery, Distinguished Councilor
# =========================================================================================


def _outcome_changed(state: GameState) -> bool:
    return any(e.key == OUTCOME_CHANGED for e in state.active_effects)


def _bribery_ok(
    state: GameState, _r: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    agenda = state.agenda
    return (
        window.ctx.get("kind") == _KIND_SPEAKER
        and agenda is not None
        and player_id in agenda.votes  # „you voted" - dodatkowe głosy na ten sam wynik
        and not _outcome_changed(state)
        # Hack Election Ω: zagrywający nie może zagrać Bribery (C_action_cards).
        and not active_effects.has_effect(state, player_id, HACK_ELECTION)
    )


def _distinguished_ok(
    state: GameState, _r: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    agenda = state.agenda
    return (
        window.ctx.get("kind") == _KIND_VOTED
        and agenda is not None
        and player_id in agenda.votes
        and not _outcome_changed(state)
    )


declare_reaction("bribery", condition=_bribery_ok)
declare_reaction("distinguished", condition=_distinguished_ok)


@register_effect_inputs("action_cards:bribery")
def bribery_inputs(state: GameState, _registry: StaticDataRegistry, player_id: str) -> list[Input]:
    return [
        _number(
            "trade_goods", "Trade goods to spend (1 additional vote each)", 0,
            economy.spendable_trade_goods(state, player_id),
            # Auto: wszystkie trade goods (cel karty = przeważyć głosowanie; ⚠️ ZAŁOŻENIE).
            auto=economy.spendable_trade_goods(state, player_id),
        )
    ]


@register_effect("action_cards:bribery")
def bribery(
    state: GameState, registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Bribery: Spend any number of trade goods. For each trade good spent, cast 1 additional vote
    for the outcome on which you voted.
    """
    amount = params.get("trade_goods", 0)
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        raise ValueError("Enter how many trade goods to spend ('trade_goods').")
    _agenda_or_fail(state)
    if player_id not in (state.agenda.votes if state.agenda else {}):
        raise ValueError("You must have cast votes on this agenda to play Bribery.")
    economy.spend_as_trade_goods(state, player_id, amount)
    agenda_phase.add_votes(state, registry, player_id, amount)


@register_effect("action_cards:distinguished")
def distinguished(
    state: GameState, registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Distinguished Councilor: Cast 5 additional votes for that outcome."""
    _agenda_or_fail(state)
    agenda_phase.add_votes(state, registry, player_id, _DISTINGUISHED_VOTES)


# =========================================================================================
# Confounding / Confusing Legal Text, Deadly Plot
# =========================================================================================


@register_effect("action_cards:confounding")
def confounding(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Confounding Legal Text: You are the elected player instead."""
    if agenda_phase.elected_player(state) in (None, player_id):
        raise ValueError("Another player must be about to be elected.")
    agenda_phase.replace_elected(state, player_id)
    active_effects.add_effect(state, OUTCOME_CHANGED, Duration.AGENDA, owner=player_id)


@register_effect_inputs("action_cards:confusing")
def confusing_inputs(state: GameState, registry: StaticDataRegistry, player_id: str) -> list[Input]:
    others = [pid for pid in state.players if pid != player_id]
    return [_choice("player", "Player elected instead", _player_options(state, registry, others))]


@register_effect("action_cards:confusing")
def confusing(
    state: GameState, _registry: StaticDataRegistry, player_id: str, params: Mapping[str, Any]
) -> None:
    """Confusing Legal Text: Choose 1 player. That player is the elected player instead."""
    target = params.get("player")
    if not isinstance(target, str) or target not in state.players or target == player_id:
        raise ValueError("Choose another player ('player').")
    if agenda_phase.elected_player(state) != player_id:
        raise ValueError("You must be the player about to be elected.")
    agenda_phase.replace_elected(state, target)
    active_effects.add_effect(state, OUTCOME_CHANGED, Duration.AGENDA, owner=player_id)


def _voted_or_predicted_other(state: GameState, player_id: str, outcome: str) -> bool:
    agenda = state.agenda
    vote = agenda.votes.get(player_id) if agenda is not None else None
    if vote is not None and vote.outcome != outcome:
        return True
    return any(predicted != outcome for _card, predicted in predictions(state, player_id))


def _deadly_plot_ok(
    state: GameState, _r: StaticDataRegistry, player_id: str, window: OpenWindow
) -> bool:
    """„If you voted for or predicted another outcome" - bez tego karta nic by nie zrobiła."""
    return _voted_or_predicted_other(state, player_id, str(window.ctx.get("outcome")))


declare_reaction("deadly_plot", condition=_deadly_plot_ok)


@register_effect("action_cards:deadly_plot")
def deadly_plot(
    state: GameState, _registry: StaticDataRegistry, player_id: str, _params: Mapping[str, Any]
) -> None:
    """Deadly Plot: If you voted for or predicted another outcome, discard the agenda instead.
    The agenda is resolved with no effect and it is not replaced. Then, exhaust all of your planets.
    """
    agenda = _agenda_or_fail(state)
    if agenda.pending_outcome is None or not _voted_or_predicted_other(
        state, player_id, agenda.pending_outcome
    ):
        raise ValueError("You did not vote for or predict another outcome.")
    agenda_phase.void_agenda(state)
    exhaust.exhaust_planets(state, player_id, controlled(state, player_id))


# =========================================================================================
# Ancient Burial Sites
# =========================================================================================


@register_effect_inputs("action_cards:abs")
def abs_inputs(state: GameState, registry: StaticDataRegistry, _player_id: str) -> list[Input]:
    return [_choice("player", "Player", _player_options(state, registry, list(state.players)))]


@register_effect("action_cards:abs")
def ancient_burial_sites(
    state: GameState, registry: StaticDataRegistry, _player_id: str, params: Mapping[str, Any]
) -> None:
    """Ancient Burial Sites: Choose 1 player. Exhaust each cultural planet owned by that player."""
    target = params.get("player")
    if not isinstance(target, str) or target not in state.players:
        raise ValueError("Choose 1 player ('player').")
    cultural = [
        planet
        for planet in controlled(state, target)
        if "cultural" in exploration.planet_traits(registry, planet, state)
    ]
    exhaust.exhaust_planets(state, target, cultural)
