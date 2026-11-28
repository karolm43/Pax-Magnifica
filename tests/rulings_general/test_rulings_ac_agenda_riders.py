"""Agenda action cards and riders — ``docs/rules_tirules/C_action_cards.md``.

Each test tags the points it checks with ``@ruling(...)`` (guard ``tests/test_ruling_coverage.py``).
Basic card behaviour lives in ``tests/test_reactions_agenda.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from src.core import (
    action_cards,
    agenda_phase,
    production,
    promissory_play,
    rules_hooks,
    strategy_phase,
    technology,
    triggers,
)
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    AgendaStep,
    GameState,
    Phase,
    PlayerState,
    StatusPhaseState,
    StatusStep,
    SystemState,
)
from src.core.hex_grid import HexGrid
from src.core.hooks import reactions_agenda
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.test_reactions_agenda import (
    ALL_RIDERS,
    DIRECTIVE,
    LAW,
    _hand,
    _planet,
    _play,
    _playable,
    _resolve_for,
    _revealed,
    _state,
)

EQUALITY = "economic_equality"  # For: everyone's TG replaced by 5; Against: everyone discards all
INDUSTRY = "minister_industry"

# Slug of the ruling section of every rider except Sanction (whose section has a single point).
RIDER_SECTIONS = {
    "const_rider": "construction-rider",
    "diplo_rider": "diplomacy-rider",
    "imp_rider": "imperial-rider",
    "lead_rider": "leadership-rider",
    "politic_rider": "politics-rider",
    "tech_rider": "technology-rider",
    "trade_rider": "trade-rider",
    "war_rider": "warfare-rider",
}


def _ids(point: str) -> list[str]:
    return [f"C_action_cards/{section}/{point}" for section in RIDER_SECTIONS.values()]


@pytest.fixture(scope="module")
def registry() -> Iterator[StaticDataRegistry]:
    reg = StaticDataRegistry()
    rules_hooks.bind_registry(reg)
    yield reg


def _vote(state: GameState, registry: StaticDataRegistry, pid: str, outcome: str) -> GameState:
    return agenda_phase.cast_vote(state, registry, pid, outcome, [_planet(state, pid)])


def _abstain_rest(state: GameState, registry: StaticDataRegistry) -> GameState:
    while state.agenda is not None and state.agenda.step is AgendaStep.VOTE:
        voter = agenda_phase.current_voter(state)
        assert voter is not None
        state = agenda_phase.abstain(state, registry, voter)
    return state


def _confirm(state: GameState, registry: StaticDataRegistry) -> GameState:
    assert state.agenda is not None
    if state.agenda.step is AgendaStep.COUNTED:
        return agenda_phase.confirm_outcome(state, registry, "p2")
    return state


def _ships(state: GameState, pid: str, **units: int) -> None:
    state.systems["101"].space_units[pid] = dict(units)


def _rider_setup(
    registry: StaticDataRegistry, card: str, *, deck: list[str] | None = None
) -> tuple[GameState, dict[str, Any]]:
    """Revealed agenda with ``card`` in p1's hand plus the form values the card needs."""
    state = _revealed(registry, deck or [LAW], {"p1": [card]})
    params: dict[str, Any] = {}
    if card == "const_rider":
        params["planet"] = _planet(state, "p1")
    elif card == "diplo_rider":
        params["position"] = "101"
    elif card == "war_rider":
        _ships(state, "p1", cruiser=1)
        params["position"] = "101"
    elif card == "lead_rider":
        params.update(tactical=1, fleet=1, strategic=1)
    elif card == "politic_rider":
        state.decks.action_card_deck = ["a1", "a2", "a3"]
    elif card == "tech_rider":
        state.players["p1"].faction = "sol"
        params["tech"] = reactions_agenda._directly_researchable(state, registry, "p1")[0]
    return state, params


# ============================================================================ Riders (shared)


@pytest.mark.parametrize("card", RIDER_SECTIONS)
@ruling(*_ids("1"), *_ids("1.1"))
def test_other_riders_may_follow_on_the_same_or_another_outcome(
    registry: StaticDataRegistry, card: str
) -> None:
    extras = [c for c in ("imp_rider", "trade_rider", "sanction") if c != card][:2]
    state, params = _rider_setup(registry, card)
    state.players["p1"].private.action_cards = [card, *extras]
    state = _play(state, registry, "p1", card, outcome="for", **params)
    for extra, outcome in zip(extras, ("for", "against"), strict=True):
        assert _playable(state, registry, "p1", extra), extra
        state = _play(state, registry, "p1", extra, outcome=outcome)
    assert reactions_agenda.predictions(state, "p1") == [
        (card, "for"), (extras[0], "for"), (extras[1], "against"),
    ]


@pytest.mark.parametrize("card", RIDER_SECTIONS)
@ruling(*_ids("2"))
def test_rider_resolves_after_the_agenda_effect(
    registry: StaticDataRegistry, card: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    state, params = _rider_setup(registry, card)
    state = _play(state, registry, "p1", card, outcome="for", **params)
    real = triggers.fire
    pending_after_effect: list[int] = []

    def spy(work: GameState, event: GameEvent, moment: Moment, **kwargs: Any) -> Any:
        result = real(work, event, moment, **kwargs)
        if event is GameEvent.AGENDA_OUTCOME_RESOLVED and moment is Moment.DURING:
            history = work.agenda.history if work.agenda else []
            assert not history[-1].get("riders")  # nothing rewarded while the effect resolves
            pending_after_effect.append(len(reactions_agenda.predictions(work, "p1")))
        return result

    monkeypatch.setattr(triggers, "fire", spy)
    done = _resolve_for(state, registry)
    assert pending_after_effect == [1]
    note = done.agenda.history[-1]["riders"][0]  # type: ignore[union-attr]
    assert note["correct"] is True and "skipped" not in note


@ruling("C_action_cards/trade-rider/2")
def test_trade_rider_gain_survives_economic_equality(registry: StaticDataRegistry) -> None:
    """Economic Equality "Against" wipes all trade goods first, then the rider pays 5."""
    state = _revealed(registry, [EQUALITY], {"p1": ["trade_rider"]})
    state.players["p1"].trade_goods = 7
    state = _play(state, registry, "p1", "trade_rider", outcome="against")
    state = _abstain_rest_with_vote(state, registry, "against")
    assert state.players["p1"].trade_goods == 5


def _abstain_rest_with_vote(
    state: GameState, registry: StaticDataRegistry, outcome: str
) -> GameState:
    state = _vote(state, registry, "p3", outcome)
    return _confirm(_abstain_rest(state, registry), registry)


@pytest.mark.parametrize("card", RIDER_SECTIONS)
@ruling(*_ids("3"))
def test_a_player_who_cannot_vote_may_still_play_a_rider(
    registry: StaticDataRegistry, card: str
) -> None:
    state, params = _rider_setup(registry, card)
    assert state.agenda is not None
    state.agenda.blocked = ["p1"]
    assert _playable(state, registry, "p1", card)
    state = _play(state, registry, "p1", card, outcome="for", **params)
    assert reactions_agenda.predictions(state, "p1") == [(card, "for")]


@ruling("C_action_cards/sanction/1")
def test_riders_may_follow_a_sanction(registry: StaticDataRegistry) -> None:
    assert "sanction" in ALL_RIDERS
    state = _revealed(registry, [LAW], {"p1": ["sanction", "imp_rider"]})
    state = _play(state, registry, "p1", "sanction", outcome="for")
    assert _playable(state, registry, "p1", "imp_rider")
    state = _play(state, registry, "p1", "imp_rider", outcome="for")
    assert _resolve_for(state, registry).players["p1"].victory_points == 1


@ruling("C_action_cards/assassinate-representative/1")
def test_assassinated_player_may_still_play_riders(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p2": ["assassin"], "p1": ["imp_rider"]})
    state = _play(state, registry, "p2", "assassin", player="p1")
    assert state.agenda is not None and "p1" in state.agenda.blocked
    assert _playable(state, registry, "p1", "imp_rider")
    state = _play(state, registry, "p1", "imp_rider", outcome="for")
    assert reactions_agenda.predictions(state, "p1") == [("imp_rider", "for")]


# ============================================================================ Construction Rider


def _all_docks_elsewhere(state: GameState, registry: StaticDataRegistry, base: str, n: int) -> str:
    """Put all ``n`` units of ``base`` of p1 into system 102 (empties reinforcements)."""
    taken = set(state.systems["101"].planet_owners)
    planet = next(p for p in sorted(registry.planets) if p not in taken)
    system = SystemState(position="102", system_id="2", planet_owners={planet: "p3"})
    if base == "spacedock":
        system.planet_units[planet] = {"p1": {base: n}}
        zone = planet
    else:
        system.space_units["p1"] = {base: n}
        zone = "space"
    state.systems["102"] = system
    return f"102|{zone}"


@ruling("C_action_cards/construction-rider/4")
def test_construction_rider_takes_a_dock_from_the_board(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["const_rider"]})
    source = _all_docks_elsewhere(state, registry, "spacedock", 3)
    planet = _planet(state, "p1")
    inputs = rules_hooks.inputs_for("action_cards:const_rider")
    assert inputs is not None
    form = {f["key"]: f for f in inputs(state, registry, "p1")}
    assert source in [o["value"] for o in form["source"]["options"]]
    # Source clicked on the map, or the explicit "Do not place" - no "Auto" (2026-11-27).
    assert "auto" not in form["source"]
    assert "none" in [o["value"] for o in form["source"]["options"]]
    pick = next(o for o in form["source"]["options"] if o["value"] == source)
    assert pick["meta"]["unit"] == "spacedock" and pick["meta"]["position"] == "102"

    # A system with the player's command token is not a legal source.
    tokened = state.clone()
    tokened.systems["102"].command_tokens = ["p1"]
    with pytest.raises(ValueError):
        action_cards.play_action_card(
            tokened, registry, "p1", "const_rider",
            {"outcome": "for", "planet": planet, "source": source},
        )

    played = _play(
        state, registry, "p1", "const_rider", outcome="for", planet=planet, source=source
    )
    done = _resolve_for(played, registry)
    assert done.systems["101"].planet_units[planet]["p1"]["spacedock"] == 1
    assert done.systems["102"].planet_units[source.split("|")[1]]["p1"]["spacedock"] == 2

    # "may": without a source nothing is removed and nothing is placed.
    kept = _resolve_for(
        _play(state, registry, "p1", "const_rider", outcome="for", planet=planet, source="none"),
        registry,
    )
    assert kept.systems["102"].planet_units[source.split("|")[1]]["p1"]["spacedock"] == 3
    assert planet not in kept.systems["101"].planet_units
    # Skipped field (Auto) behaves the same: nothing leaves the board, no error.
    skipped = _resolve_for(
        _play(state, registry, "p1", "const_rider", outcome="for", planet=planet), registry
    )
    assert skipped.systems["102"].planet_units[source.split("|")[1]]["p1"]["spacedock"] == 3
    assert planet not in skipped.systems["101"].planet_units


@ruling("C_action_cards/construction-rider/4")
def test_construction_rider_respects_one_dock_per_planet(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["const_rider"]})
    planet = _planet(state, "p1")
    state.systems["101"].planet_units[planet] = {"p1": {"spacedock": 1}}
    assert not _playable(state, registry, "p1", "const_rider")
    with pytest.raises(ValueError, match="maximum number"):
        action_cards.play_action_card(
            state, registry, "p1", "const_rider", {"outcome": "for", "planet": planet}
        )


@ruling("C_action_cards/construction-rider/5")
def test_saar_places_the_dock_in_the_system_of_a_planet(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["const_rider"]})
    state.players["p1"].faction = "saar"
    assert _playable(state, registry, "p1", "const_rider")
    planet = _planet(state, "p1")
    state = _play(state, registry, "p1", "const_rider", outcome="for", planet=planet)
    done = _resolve_for(state, registry)
    assert done.systems["101"].space_units["p1"]["spacedock"] == 1  # Floating Factory
    assert planet not in done.systems["101"].planet_units


def _industry(registry: StaticDataRegistry) -> tuple[GameState, str]:
    state = _revealed(registry, [LAW], {"p1": ["const_rider"]})
    state.decks.agenda_laws[INDUSTRY] = "p1"
    state.players["p1"].faction = "sol"
    planet = _planet(state, "p1")
    state = _play(state, registry, "p1", "const_rider", outcome="for", planet=planet)
    return _resolve_for(state, registry), planet


@ruling("C_action_cards/construction-rider/6", "C_action_cards/construction-rider/6.1")
def test_minister_of_industry_produces_and_planets_stay_unusable(
    registry: StaticDataRegistry,
) -> None:
    state, planet = _industry(registry)
    offer = next(o for o in state.pending_offers if "Industry" in o.label)
    state = triggers.accept_offer(state, "p1", offer.id, {})
    assert state.production_grant is not None and state.production_grant.position == "101"
    state.players["p1"].exhausted_planets = []
    done = production.produce(
        state, HexGrid(), registry, "p1",
        [production.ProductionOrder("infantry", 1, planet)],
        production.Spend(planets=(planet,)),
    )
    assert done.systems["101"].planet_units[planet]["p1"]["infantry"] == 1
    # Exhausted for resources: no votes for the rest of the phase...
    row = next(
        r for r in agenda_phase.voting_planets(done, registry, "p1") if r["planet"] == planet
    )
    assert row["exhausted"] is True
    # ...and readied at the end of the agenda phase.
    done.production_grant = None
    assert done.agenda is not None
    done.agenda.agenda_number = agenda_phase.AGENDAS_PER_PHASE
    ended = agenda_phase.continue_agenda(done, registry, "p2")
    assert planet not in ended.players["p1"].exhausted_planets


# ============================================================================ Warfare Rider


@ruling("C_action_cards/warfare-rider/4")
def test_warfare_rider_takes_a_damaged_dreadnought_and_places_it_undamaged(
    registry: StaticDataRegistry,
) -> None:
    state = _revealed(registry, [LAW], {"p1": ["war_rider"]})
    _ships(state, "p1", cruiser=1)
    source = _all_docks_elsewhere(state, registry, "dreadnought", 5)
    state.systems["102"].damaged_units = {"space": {"p1": {"dreadnought": 5}}}
    state = _play(
        state, registry, "p1", "war_rider", outcome="for", position="101", source=source
    )
    done = _resolve_for(state, registry)
    assert done.systems["101"].space_units["p1"]["dreadnought"] == 1
    assert done.systems["102"].space_units["p1"]["dreadnought"] == 4
    assert not done.systems["101"].damaged_units.get("space", {}).get("p1", {}).get("dreadnought")


@ruling("C_action_cards/warfare-rider/4")
def test_warfare_rider_needs_ships_not_carried_ground_forces(
    registry: StaticDataRegistry,
) -> None:
    state = _revealed(registry, [LAW], {"p1": ["war_rider"]})
    _ships(state, "p1", infantry=2)
    assert not _playable(state, registry, "p1", "war_rider")


# ============================================================================ Diplomacy Rider


@ruling("C_action_cards/diplomacy-rider/4")
def test_diplomacy_rider_may_choose_mecatol_rex(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["diplo_rider"]})
    mecatol = next(k for k, p in registry.planets.items() if p.name == "Mecatol Rex")
    state.systems["000"] = SystemState(
        position="000", system_id="18", planet_owners={mecatol: "p1"}
    )
    state = _play(state, registry, "p1", "diplo_rider", outcome="for", position="000")
    done = _resolve_for(state, registry)
    assert sorted(done.systems["000"].command_tokens) == ["p2", "p3"]


# ============================================================================ Technology Rider


def _tech_state(registry: StaticDataRegistry) -> tuple[GameState, str, str]:
    """p1 (Sol) + a technology with 1 missing prerequisite and a specialty planet for it."""
    state = _revealed(registry, [LAW], {"p1": ["tech_rider"]})
    state.players["p1"].faction = "sol"
    state.players["p1"].technologies = []
    pool = technology.tech_pool(state, registry, "p1")
    for planet_id in sorted(registry.planets):
        probe = state.clone()
        probe.systems["103"] = SystemState(
            position="103", system_id="3", planet_owners={planet_id: "p1"}
        )
        if not technology.specialty_planets(probe, registry, "p1").get(planet_id):
            continue
        for tech_id in pool:
            if technology.missing_prerequisites(probe, registry, "p1", pool[tech_id]) and (
                technology.plan_with_skips(probe, registry, "p1", tech_id, [planet_id])
            ):
                return probe, tech_id, planet_id
    raise AssertionError("no specialty planet / technology pair found")


@ruling("C_action_cards/technology-rider/4")
def test_technology_rider_still_requires_prerequisites(registry: StaticDataRegistry) -> None:
    state, tech, _planet_id = _tech_state(registry)
    with pytest.raises(ValueError, match="technology you can research"):
        action_cards.play_action_card(
            state, registry, "p1", "tech_rider", {"outcome": "for", "tech": tech}
        )


@ruling("C_action_cards/technology-rider/4.1")
def test_technology_rider_specialty_ignores_a_prerequisite(
    registry: StaticDataRegistry,
) -> None:
    state, tech, planet = _tech_state(registry)
    state = _play(
        state, registry, "p1", "tech_rider", outcome="for", tech=tech, skips=[planet]
    )
    done = _resolve_for(state, registry)
    assert tech in done.players["p1"].technologies
    assert planet in done.players["p1"].exhausted_planets


# ============================================================================ Veto


@ruling("C_action_cards/veto/1")
def test_veto_replaces_the_agenda_and_players_vote_on_the_new_one(
    registry: StaticDataRegistry,
) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["veto"]})
    state = _play(state, registry, "p1", "veto")
    assert state.agenda is not None and state.agenda.agenda_id == DIRECTIVE
    assert state.decks.agenda_discard == [LAW]
    state = _vote(state, registry, "p3", "p1")
    assert state.agenda is not None and state.agenda.votes["p3"].outcome == "p1"


@ruling("C_action_cards/veto/2")
def test_veto_and_political_secret_come_before_the_rider_window(
    registry: StaticDataRegistry,
) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["veto"], "p3": ["imp_rider"]})
    state.players["p1"].private.promissory_notes = ["blue_ps"]
    state.players["p1"].color = "red"
    state.players["p2"].color = "blue"

    def note_playable(current: GameState) -> bool:
        rows = promissory_play.playability(current, registry, "p1")
        return any(r["note_id"] == "blue_ps" and r["playable"] for r in rows)

    assert _playable(state, registry, "p1", "veto") and note_playable(state)
    state = _play(state, registry, "p3", "imp_rider", outcome="for")
    assert not _playable(state, registry, "p1", "veto")
    assert not note_playable(state)


@ruling("C_action_cards/veto/2.1")
def test_political_secret_has_no_effect_on_the_replacement(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["veto"]})
    state.players["p1"].private.promissory_notes = ["blue_ps"]
    state.players["p1"].color = "red"
    state.players["p2"].color = "blue"
    state, _ = promissory_play.play(state, registry, "p1", "blue_ps")
    assert promissory_play.silenced(state, "p2")
    state = _play(state, registry, "p1", "veto")
    assert not promissory_play.silenced(state, "p2")
    assert state.agenda is not None and "p2" not in state.agenda.blocked


@ruling("C_action_cards/veto/3")
def test_a_second_veto_may_hit_the_replacement(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE, EQUALITY], {"p1": ["veto"], "p3": ["veto3"]})
    state = _play(state, registry, "p1", "veto")
    state = _play(state, registry, "p3", "veto3")
    assert state.agenda is not None and state.agenda.agenda_id == EQUALITY


@ruling("C_action_cards/veto/4")
def test_replacement_agenda_allows_a_new_transaction(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["veto"]})
    state.players["p1"].transacted_with = ["p3"]
    state.players["p3"].transacted_with = ["p1"]
    state = _play(state, registry, "p1", "veto")
    assert state.players["p1"].transacted_with == []
    assert state.players["p3"].transacted_with == []


# ============================================================================ Repeal Law


@ruling("C_action_cards/repeal-law/1")
def test_repeal_law_needs_a_law_in_play(registry: StaticDataRegistry) -> None:
    state = _state(registry, [LAW])
    state.phase = Phase.ACTION
    state.agenda = None
    state.active_player_id = "p1"
    for pid, card in zip(state.players, (1, 2, 3), strict=True):
        state.players[pid].strategy_cards = [card]
    _hand(state, "p1", "repeal")
    assert not _playable(state, registry, "p1", "repeal")
    with pytest.raises(ValueError):
        action_cards.play_action_card(state, registry, "p1", "repeal", {"law": LAW})
    state.decks.agenda_laws[LAW] = "for"
    assert _playable(state, registry, "p1", "repeal")
    done = _play(state, registry, "p1", "repeal", law=LAW)
    assert LAW not in done.decks.agenda_laws


# ============================================================================ Bribery


def _bribery_state(registry: StaticDataRegistry, **hands: list[str]) -> GameState:
    state = _revealed(registry, [LAW], dict(hands))
    for player in state.players.values():
        player.trade_goods = 4
    return state


def _votes(state: GameState, pid: str) -> int:
    assert state.agenda is not None
    return state.agenda.votes[pid].votes


@ruling("C_action_cards/bribery/1", "C_action_cards/bribery/4")
def test_bribery_adds_votes_to_the_own_outcome(registry: StaticDataRegistry) -> None:
    state = _bribery_state(registry, p3=["bribery"], p1=["bribery"])
    state = _vote(state, registry, "p3", "for")
    state = agenda_phase.abstain(state, registry, "p1")
    state = _vote(state, registry, "p2", "against")
    assert not _playable(state, registry, "p1", "bribery")  # p1 cast no votes
    before = _votes(state, "p3")
    state = _play(state, registry, "p3", "bribery", trade_goods=3)
    assert state.agenda is not None and state.agenda.votes["p3"].outcome == "for"
    assert _votes(state, "p3") == before + 3
    assert state.players["p3"].trade_goods == 1


@ruling("C_action_cards/bribery/2")
def test_bribery_after_the_speaker_abstains(registry: StaticDataRegistry) -> None:
    state = _bribery_state(registry, p3=["bribery"])
    state = _vote(state, registry, "p3", "for")
    state = agenda_phase.abstain(state, registry, "p1")
    assert not _playable(state, registry, "p3", "bribery")
    state = agenda_phase.abstain(state, registry, "p2")
    assert _playable(state, registry, "p3", "bribery")


@ruling("C_action_cards/bribery/2")
def test_bribery_when_the_speaker_cannot_vote_waits_for_their_turn(
    registry: StaticDataRegistry,
) -> None:
    state = _bribery_state(registry, p3=["bribery"], p1=["assassin"])
    state = _play(state, registry, "p1", "assassin", player="p2")  # the speaker
    state = _vote(state, registry, "p3", "for")
    assert not _playable(state, registry, "p3", "bribery")  # p1 still before the speaker
    state = _vote(state, registry, "p1", "against")
    assert _playable(state, registry, "p3", "bribery")


@ruling("C_action_cards/bribery/3")
def test_bribery_may_spend_zero(registry: StaticDataRegistry) -> None:
    state = _bribery_state(registry, p3=["bribery"])
    state.players["p3"].trade_goods = 0
    state = _vote(state, registry, "p3", "for")
    state = _abstain_rest(state, registry)
    assert _playable(state, registry, "p3", "bribery")
    before = _votes(state, "p3")
    state = _play(state, registry, "p3", "bribery", trade_goods=0)
    assert _votes(state, "p3") == before
    assert state.players["p3"].private.action_cards == []


@ruling("C_action_cards/bribery/4.1")
def test_argent_speaker_bribes_only_right_after_their_vote(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, [LAW])
    state.players["p2"].faction = "argent"
    _hand(state, "p2", "bribery")
    _hand(state, "p3", "bribery")
    state = agenda_phase.reveal_agenda(state, registry, "p2")
    assert agenda_phase.current_voter(state) == "p2"
    state = _vote(state, registry, "p2", "for")
    assert _playable(state, registry, "p2", "bribery")
    assert not _playable(state, registry, "p3", "bribery")
    state = _vote(state, registry, "p3", "for")
    assert not _playable(state, registry, "p2", "bribery")
    assert not _playable(state, registry, "p3", "bribery")


@ruling("C_action_cards/bribery/5", "C_action_cards/distinguished-councilor/2")
def test_bribery_votes_do_not_open_distinguished_councilor(
    registry: StaticDataRegistry,
) -> None:
    state = _bribery_state(registry, p3=["bribery", "distinguished"])
    state = _vote(state, registry, "p3", "for")
    assert _playable(state, registry, "p3", "distinguished")  # after the normal vote
    state = _vote(state, registry, "p1", "against")
    state = _vote(state, registry, "p2", "against")
    state = _play(state, registry, "p3", "bribery", trade_goods=4)
    assert not _playable(state, registry, "p3", "distinguished")


@ruling("C_action_cards/bribery/5.1", "C_action_cards/distinguished-councilor/2.1")
def test_speaker_may_play_distinguished_after_a_bribery(registry: StaticDataRegistry) -> None:
    state = _bribery_state(registry, p3=["bribery"], p2=["distinguished"])
    state = _vote(state, registry, "p3", "for")
    state = agenda_phase.abstain(state, registry, "p1")
    state = _vote(state, registry, "p2", "against")
    state = _play(state, registry, "p3", "bribery", trade_goods=1)
    assert _playable(state, registry, "p2", "distinguished")


@ruling("C_action_cards/distinguished-councilor/1")
def test_distinguished_needs_cast_votes(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p3": ["distinguished"]})
    assert not _playable(state, registry, "p3", "distinguished")
    state = agenda_phase.abstain(state, registry, "p3")
    assert not _playable(state, registry, "p3", "distinguished")


# ============================================================================ Legal Texts


def _election(
    registry: StaticDataRegistry, hands: dict[str, list[str]], *, deck: list[str] | None = None
) -> GameState:
    """p3 votes to elect p1; the outcome waits in the COUNTED step."""
    state = _revealed(registry, deck or [DIRECTIVE], hands)
    state = _vote(state, registry, "p3", "p1")
    state = _abstain_rest(state, registry)
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    assert agenda_phase.elected_player(state) == "p1"
    return state


@ruling("C_action_cards/confounding-legal-text/1", "C_action_cards/confusing-legal-text/1")
@pytest.mark.parametrize(
    ("card", "player", "params"),
    [("confounding", "p2", {}), ("confusing", "p1", {"player": "p2"})],
)
def test_predictions_follow_the_new_elected_player(
    registry: StaticDataRegistry, card: str, player: str, params: dict[str, str]
) -> None:
    state = _revealed(registry, [DIRECTIVE], {"p3": ["imp_rider"], player: [card]})
    state = _play(state, registry, "p3", "imp_rider", outcome="p2")
    state = _vote(state, registry, "p1", "p1")
    state = _abstain_rest(state, registry)
    state = _play(state, registry, player, card, **params)
    done = _confirm(state, registry)
    assert done.agenda is not None and done.agenda.resolved_outcome == "p2"
    assert done.players["p3"].victory_points == 1


@ruling(
    "C_action_cards/confounding-legal-text/2",
    "C_action_cards/confusing-legal-text/2",
    "C_action_cards/bribery/6",
    "C_action_cards/distinguished-councilor/3",
)
@pytest.mark.parametrize(
    ("card", "player", "params"),
    [("confounding", "p2", {}), ("confusing", "p1", {"player": "p2"})],
)
def test_no_additional_votes_after_the_outcome_was_changed(
    registry: StaticDataRegistry, card: str, player: str, params: dict[str, str]
) -> None:
    state = _revealed(registry, [DIRECTIVE], {"p3": ["bribery", "distinguished"], player: [card]})
    state.players["p3"].trade_goods = 4
    state = _vote(state, registry, "p3", "p1")
    state = _abstain_rest(state, registry)
    assert _playable(state, registry, "p3", "bribery")
    changed = _play(state, registry, player, card, **params)
    assert agenda_phase.elected_player(changed) == "p2"
    assert not _playable(changed, registry, "p3", "bribery")
    assert not _playable(changed, registry, "p3", "distinguished")
    # The votes come first: after them the text card is still playable.
    first = _play(state, registry, "p3", "bribery", trade_goods=4)
    assert _playable(first, registry, player, card)


@ruling("C_action_cards/confounding-legal-text/3", "C_action_cards/confusing-legal-text/3")
@pytest.mark.parametrize(
    ("card", "player", "params", "elected"),
    [("confounding", "p2", {}, "p2"), ("confusing", "p1", {"player": "p3"}, "p3")],
)
def test_legal_text_precedes_covert_reveal_and_drive_the_debate(
    registry: StaticDataRegistry,
    card: str,
    player: str,
    params: dict[str, str],
    elected: str,
) -> None:
    state = _state(registry, [agenda_phase.COVERT_LEGISLATION, DIRECTIVE])
    _hand(state, player, card)
    state.players[elected].private.secret_objectives = ["dtd"]
    state = agenda_phase.reveal_agenda(state, registry, "p2")
    state = _vote(state, registry, "p3", "p1")
    state = _abstain_rest(state, registry)
    assert state.agenda is not None and not state.agenda.history  # hidden card not revealed yet
    state = _play(state, registry, player, card, **params)
    assert "dtd" in state.players[elected].private.secret_objectives  # not scored yet
    done = _confirm(state, registry)
    assert done.agenda is not None and done.agenda.history[-1]["agenda"] == DIRECTIVE
    assert "dtd" in done.players[elected].scored_secrets


@ruling("C_action_cards/confounding-legal-text/4")
def test_confounding_may_follow_confusing(registry: StaticDataRegistry) -> None:
    state = _election(registry, {"p1": ["confusing"], "p3": ["confounding"]})
    state = _play(state, registry, "p1", "confusing", player="p2")
    state = _play(state, registry, "p3", "confounding")
    assert agenda_phase.elected_player(state) == "p3"


@ruling("C_action_cards/confusing-legal-text/4")
def test_confusing_may_follow_confounding(registry: StaticDataRegistry) -> None:
    state = _election(registry, {"p2": ["confounding", "confusing"]})
    state = _play(state, registry, "p2", "confounding")
    state = _play(state, registry, "p2", "confusing", player="p3")
    assert agenda_phase.elected_player(state) == "p3"


# ============================================================================ Deadly Plot


@ruling("C_action_cards/deadly-plot/1")
def test_deadly_plot_makes_predictions_fail(registry: StaticDataRegistry) -> None:
    state = _revealed(
        registry, [LAW], {"p1": ["imp_rider"], "p2": ["trade_rider", "deadly_plot"]}
    )
    state = _play(state, registry, "p1", "imp_rider", outcome="for")
    state = _play(state, registry, "p2", "trade_rider", outcome="against")
    state = _abstain_rest(_vote(state, registry, "p3", "for"), registry)
    done = _play(state, registry, "p2", "deadly_plot")
    assert done.players["p1"].victory_points == 0  # the correct prediction does not pay
    assert reactions_agenda.predictions(done, "p1") == []
    assert done.agenda is not None and not done.agenda.history[-1].get("riders")


@ruling("C_action_cards/deadly-plot/2")
def test_deadly_plot_itself_cannot_be_predicted(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p1": ["imp_rider"]})
    assert state.agenda is not None and state.agenda.outcomes == ["for", "against"]
    with pytest.raises(ValueError, match="possible outcomes"):
        action_cards.play_action_card(
            state, registry, "p1", "imp_rider", {"outcome": "deadly_plot"}
        )


@ruling("C_action_cards/deadly-plot/3")
def test_deadly_plot_follows_extra_votes_and_a_changed_outcome(
    registry: StaticDataRegistry,
) -> None:
    state = _revealed(
        registry, [DIRECTIVE], {"p3": ["distinguished", "deadly_plot"], "p1": ["confusing"]}
    )
    state = _vote(state, registry, "p3", "p1")
    state = _play(state, registry, "p3", "distinguished")
    state = _abstain_rest(state, registry)
    assert not _playable(state, registry, "p3", "deadly_plot")  # p3 voted for the winner
    state = _play(state, registry, "p1", "confusing", player="p2")
    assert _playable(state, registry, "p3", "deadly_plot")
    done = _play(state, registry, "p3", "deadly_plot")
    assert done.agenda is not None and done.agenda.history[-1]["voided"] is True


@ruling("C_action_cards/deadly-plot/4")
def test_deadly_plot_precedes_the_covert_reveal(registry: StaticDataRegistry) -> None:
    state = _state(registry, [agenda_phase.COVERT_LEGISLATION, DIRECTIVE])
    _hand(state, "p2", "imp_rider", "deadly_plot")
    state = agenda_phase.reveal_agenda(state, registry, "p2")
    state = _play(state, registry, "p2", "imp_rider", outcome="p3")
    state = _abstain_rest(_vote(state, registry, "p3", "p1"), registry)
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    assert not state.decks.agenda_discard and not state.agenda.history  # nothing revealed yet
    assert _playable(state, registry, "p2", "deadly_plot")
    done = _play(state, registry, "p2", "deadly_plot")
    assert done.agenda is not None and done.agenda.resolved_outcome is None


@ruling("C_action_cards/deadly-plot/5")
def test_deadly_plot_with_two_predictions_whichever_wins(registry: StaticDataRegistry) -> None:
    state = _revealed(
        registry, [LAW], {"p1": ["imp_rider", "trade_rider", "deadly_plot"]}
    )
    state = _play(state, registry, "p1", "imp_rider", outcome="for")
    state = _play(state, registry, "p1", "trade_rider", outcome="against")
    for outcome in ("for", "against"):
        counted = _abstain_rest(_vote(state.clone(), registry, "p3", outcome), registry)
        assert _playable(counted, registry, "p1", "deadly_plot"), outcome


@ruling("C_action_cards/deadly-plot/5.1")
def test_elder_qanoj_votes_one_way_and_predicts_another(registry: StaticDataRegistry) -> None:
    state = _revealed(registry, [LAW], {"p3": ["imp_rider", "deadly_plot"]})
    state.players["p3"].faction = "xxcha"
    state.players["p3"].leader_states = {"xxchacommander": "unlocked"}
    state = _play(state, registry, "p3", "imp_rider", outcome="against")
    state = _vote(state, registry, "p3", "for")  # the rider cannot stop the commander's owner
    state = _abstain_rest(state, registry)
    assert state.agenda is not None and state.agenda.pending_outcome == "for"
    assert _playable(state, registry, "p3", "deadly_plot")  # voted "for", predicted "against"


# ============================================================================ Hack Election Ω


@ruling("C_action_cards/hack-election-omega/1", "C_action_cards/hack-election-omega/1.1")
def test_hack_voter_follows_the_speaker_and_cannot_bribe(registry: StaticDataRegistry) -> None:
    state = _bribery_state(registry, p3=["hack", "bribery"], p1=["bribery"])
    state = _play(state, registry, "p3", "hack")
    assert state.agenda is not None and state.agenda.vote_order == ["p1", "p2", "p3"]
    state = _vote(state, registry, "p1", "for")
    state = _vote(state, registry, "p2", "for")  # the speaker, before the hack player
    assert _playable(state, registry, "p1", "bribery")
    state = _vote(state, registry, "p3", "against")
    assert not _playable(state, registry, "p3", "bribery")


@ruling("C_action_cards/hack-election-omega/2")
def test_argent_with_hack_election_votes_last(registry: StaticDataRegistry) -> None:
    state = _state(registry, [LAW])
    state.players["p1"].faction = "argent"
    _hand(state, "p1", "hack")
    state = agenda_phase.reveal_agenda(state, registry, "p2")
    assert state.agenda is not None and state.agenda.vote_order[0] == "p1"
    state = _play(state, registry, "p1", "hack")
    assert state.agenda is not None and state.agenda.vote_order[-1] == "p1"


# ============================================================================ Political Stability


def _status(step: StatusStep = StatusStep.COMPLETE) -> GameState:
    players = {p: PlayerState(player_id=p, color=p) for p in ("p1", "p2", "p3")}
    players["p1"].strategy_cards = [7, 8]
    players["p2"].strategy_cards = [1, 2]
    players["p3"].strategy_cards = [3, 4]
    players["p1"].private.action_cards = ["stability"]
    return GameState(
        phase=Phase.STATUS, speaker_id="p2", seating_order=["p1", "p2", "p3"],
        active_player_id="p1", players=players, status=StatusPhaseState(step=step),
    )


@ruling("C_action_cards/political-stability/1")
def test_stability_keeps_both_cards_and_skips_the_picks(registry: StaticDataRegistry) -> None:
    state = _play(_status(), registry, "p1", "stability")
    state = strategy_phase.close_round_cards(state, registry)
    state.phase = Phase.STRATEGY
    assert state.players["p1"].strategy_cards == [7, 8]
    picks = []
    for initiative in (1, 2, 3, 4):
        picker = strategy_phase.next_strategy_picker(state)
        assert picker is not None
        picks.append(picker)
        state.players[picker].strategy_cards.append(initiative)
    assert picks == ["p2", "p3", "p2", "p3"]
    assert strategy_phase.next_strategy_picker(state) is None


@ruling("C_action_cards/political-stability/1", "C_agendas/checks-and-balances/2")
def test_stability_holder_does_not_choose_under_checks_and_balances(
    registry: StaticDataRegistry,
) -> None:
    """Checks and Balances counts choices, not held cards - the kept hand still skips the picks
    ("You do not choose strategy cards during the next strategy phase")."""
    state = _play(_status(), registry, "p1", "stability")
    state = strategy_phase.close_round_cards(state, registry)
    state.phase, state.agenda = Phase.STRATEGY, None
    state.decks.agenda_laws = {"checks": "for"}
    assert strategy_phase.gives_chosen_cards(state)
    assert state.strategy_kept == ["p1"]
    plan = [("p2", 1, "p3"), ("p3", 2, "p2"), ("p2", 3, "p3"), ("p3", 4, "p2")]
    for chooser, initiative, recipient in plan:
        assert strategy_phase.next_strategy_picker(state) == chooser
        assert "p1" not in strategy_phase.card_recipients(state, chooser)  # full kept hand
        state = strategy_phase.pick_strategy_card(
            state, registry, chooser, initiative, recipient=recipient
        )
    assert strategy_phase.next_strategy_picker(state) is None
    assert state.players["p1"].strategy_cards == [7, 8]
    strategy_phase.ensure_strategy_complete(state)
    # Next round (the ROUND-long effect has expired): the reset forgets the marker.
    from src.core import active_effects

    active_effects.remove_by_key(state, strategy_phase.STABILITY_KEY, owner="p1")
    state = strategy_phase.reset_strategy_cards(state)
    assert state.strategy_kept == []


@ruling("C_action_cards/political-stability/2")
def test_stability_agenda_abilities_use_speaker_order(registry: StaticDataRegistry) -> None:
    state = _play(_status(), registry, "p1", "stability")
    state.phase = Phase.AGENDA
    # p1 keeps strategy cards 7/8, yet the order starts at the speaker, not at initiative.
    assert triggers.resolution_order(state) == ["p2", "p3", "p1"]
    assert agenda_phase.vote_order(state) == ["p3", "p1", "p2"]


@ruling("C_action_cards/political-stability/3")
def test_stability_readies_the_kept_cards_when_played(registry: StaticDataRegistry) -> None:
    state = _status()
    state.players["p1"].exhausted_strategy_cards = [7, 8]
    state = _play(state, registry, "p1", "stability")
    assert state.players["p1"].exhausted_strategy_cards == []


@ruling("C_action_cards/political-stability/4")
def test_stability_waits_for_every_other_status_step(registry: StaticDataRegistry) -> None:
    for step in StatusStep:
        assert _playable(_status(step), registry, "p1", "stability") is (
            step is StatusStep.COMPLETE
        ), step


@ruling("C_action_cards/political-stability/4.1")
def test_stability_drawn_in_the_status_phase_is_playable_in_it(
    registry: StaticDataRegistry,
) -> None:
    state = _status(StatusStep.REDISTRIBUTE)
    state.players["p1"].private.action_cards = []
    assert state.status is not None
    state.players["p1"].private.action_cards.append("stability")  # drawn during this phase
    state.status.step = StatusStep.COMPLETE
    assert _playable(state, registry, "p1", "stability")
