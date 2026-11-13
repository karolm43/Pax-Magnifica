"""Testy fazy agendy (RULES.md 51): kolejność, głosowanie, wyniki, krok 3 i brama fazy."""

from __future__ import annotations

import pytest

from src.core import agenda_phase, turn_flow
from src.core.components import ComponentCategory
from src.core.game_state import (
    AgendaPhaseState,
    AgendaStep,
    GameState,
    Phase,
    PlayerState,
    SystemState,
)
from src.core.planet_stats import influence_of
from src.core.registry import StaticDataRegistry

LAW = "revolution"  # For/Against, Law (base)
DIRECTIVE = "secret"  # Elect Player, Directive (base)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _planets_with_influence(registry: StaticDataRegistry, state: GameState, n: int) -> list[str]:
    found = [pid for pid in sorted(registry.planets) if influence_of(state, registry, pid) >= 1]
    assert len(found) >= n
    return found[:n]


def _state(registry: StaticDataRegistry, deck: list[str]) -> GameState:
    """3 graczy (p1,p2,p3), mówca p2 => kolejność głosowania p3, p1, p2."""
    state = GameState(
        phase=Phase.AGENDA,
        round_number=3,
        seating_order=["p1", "p2", "p3"],
        speaker_id="p2",
        active_player_id="p2",
        custodians_removed=True,
        players={p: PlayerState(player_id=p, color=p) for p in ("p1", "p2", "p3")},
        agenda=AgendaPhaseState(),
    )
    state.decks.agenda_deck = list(deck)
    state.decks.agenda_deck_seeded = True
    planets = _planets_with_influence(registry, state, 3)
    state.systems["101"] = SystemState(
        position="101",
        system_id="1",
        planet_owners={planets[0]: "p1", planets[1]: "p2", planets[2]: "p3"},
    )
    return state


def _planet_of(state: GameState, pid: str) -> str:
    owners = state.systems["101"].planet_owners
    return next(planet for planet, owner in owners.items() if owner == pid)


def test_classify_target() -> None:
    assert agenda_phase.classify_target("For/Against") == "for_against"
    assert agenda_phase.classify_target("Elect Player") == "player"
    assert agenda_phase.classify_target("Elect Player (The elected player...)") == "player"
    assert agenda_phase.classify_target("Elect Planet") == "planet"
    assert agenda_phase.classify_target("Elect Non-Home Planet") == "planet_non_home"
    assert agenda_phase.classify_target("Elect Planet Trait") == "planet_trait"
    assert agenda_phase.classify_target("Elect Law") == "law"
    assert agenda_phase.classify_target("Elect Something Weird") == "manual"
    assert agenda_phase.classify_target(None) == "manual"


def test_reveal_opens_vote_from_left_of_speaker(registry: StaticDataRegistry) -> None:
    state = _state(registry, [LAW, DIRECTIVE, LAW])
    out = agenda_phase.reveal_agenda(state, registry, "p2")
    assert out.agenda is not None and out.agenda.step is AgendaStep.VOTE
    assert out.agenda.agenda_id == LAW and out.agenda.kind == "for_against"
    assert out.agenda.vote_order == ["p3", "p1", "p2"]  # mówca ostatni
    assert out.active_player_id == "p3"
    assert out.decks.agenda_deck == [DIRECTIVE, LAW]
    assert state.agenda is not None and state.agenda.step is AgendaStep.REVEAL  # bez mutacji


def test_only_speaker_reveals(registry: StaticDataRegistry) -> None:
    state = _state(registry, [LAW, DIRECTIVE])
    with pytest.raises(ValueError, match="speaker"):
        agenda_phase.reveal_agenda(state, registry, "p1")


def test_empty_deck_rejects_reveal(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    with pytest.raises(ValueError, match="empty"):
        agenda_phase.reveal_agenda(state, registry, "p2")


def test_vote_turn_order_and_validation(registry: StaticDataRegistry) -> None:
    state = agenda_phase.reveal_agenda(_state(registry, [LAW, DIRECTIVE]), registry, "p2")
    p1_planet = _planet_of(state, "p1")
    with pytest.raises(ValueError, match="turn to vote"):
        agenda_phase.cast_vote(state, registry, "p1", "for", [p1_planet])
    p3_planet = _planet_of(state, "p3")
    with pytest.raises(ValueError, match="zero votes"):
        agenda_phase.cast_vote(state, registry, "p3", "for", [])
    with pytest.raises(ValueError, match="possible outcome"):
        agenda_phase.cast_vote(state, registry, "p3", "maybe", [p3_planet])
    with pytest.raises(ValueError, match="cannot give votes"):
        agenda_phase.cast_vote(state, registry, "p3", "for", [p1_planet])
    with pytest.raises(ValueError, match="twice"):
        agenda_phase.cast_vote(state, registry, "p3", "for", [p3_planet, p3_planet])


def test_vote_exhausts_planets_and_counts_influence(registry: StaticDataRegistry) -> None:
    state = agenda_phase.reveal_agenda(_state(registry, [LAW, DIRECTIVE]), registry, "p2")
    planet = _planet_of(state, "p3")
    out = agenda_phase.cast_vote(state, registry, "p3", "for", [planet])
    assert out.agenda is not None
    assert out.agenda.votes["p3"].votes == influence_of(out, registry, planet)
    assert planet in out.players["p3"].exhausted_planets
    assert out.active_player_id == "p1"
    # Wyczerpanej planety nie da się użyć ponownie w tej fazie.
    again = agenda_phase.cast_vote(out, registry, "p1", "against", [_planet_of(out, "p1")])
    assert again.agenda is not None and again.agenda.votes["p1"].outcome == "against"


def test_unique_winner_law_for_stays_in_play(registry: StaticDataRegistry) -> None:
    state = agenda_phase.reveal_agenda(_state(registry, [LAW, DIRECTIVE]), registry, "p2")
    state = agenda_phase.cast_vote(state, registry, "p3", "for", [_planet_of(state, "p3")])
    state = agenda_phase.abstain(state, registry, "p1")
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.agenda is not None
    assert state.agenda.step is AgendaStep.RESOLVED
    assert state.agenda.resolved_outcome == "for" and not state.agenda.decided_by_speaker
    assert state.decks.agenda_laws == {LAW: "for"}
    assert LAW not in state.decks.agenda_discard


def test_law_against_and_directive_go_to_discard(registry: StaticDataRegistry) -> None:
    state = agenda_phase.reveal_agenda(_state(registry, [LAW, DIRECTIVE]), registry, "p2")
    state = agenda_phase.cast_vote(state, registry, "p3", "against", [_planet_of(state, "p3")])
    state = agenda_phase.abstain(state, registry, "p1")
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.decks.agenda_discard == [LAW] and not state.decks.agenda_laws
    # Dyrektywa (Elect Player) po wyniku też idzie na stos odrzuconych.
    state = agenda_phase.continue_agenda(state, registry, "p2")
    state = agenda_phase.reveal_agenda(state, registry, "p2")
    assert state.agenda is not None and state.agenda.outcomes == ["p2", "p3", "p1"]
    # Planeta p3 jest już wyczerpana pierwszą agendą - w drugiej głosuje p1.
    with pytest.raises(ValueError, match="cannot give votes"):
        agenda_phase.cast_vote(state, registry, "p3", "p3", [_planet_of(state, "p3")])
    state = agenda_phase.abstain(state, registry, "p3")
    state = agenda_phase.cast_vote(state, registry, "p1", "p3", [_planet_of(state, "p1")])
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.agenda is not None and state.agenda.resolved_outcome == "p3"
    assert state.decks.agenda_discard == [LAW, DIRECTIVE]


def test_no_votes_means_speaker_decides(registry: StaticDataRegistry) -> None:
    state = agenda_phase.reveal_agenda(_state(registry, [LAW, DIRECTIVE]), registry, "p2")
    for pid in ("p3", "p1", "p2"):
        state = agenda_phase.abstain(state, registry, pid)
    assert state.agenda is not None and state.agenda.step is AgendaStep.TIEBREAK
    assert sorted(state.agenda.tied) == ["against", "for"]
    assert state.active_player_id == "p2"
    with pytest.raises(ValueError, match="speaker"):
        agenda_phase.decide_tie(state, registry, "p1", "for")
    out = agenda_phase.decide_tie(state, registry, "p2", "for")
    assert out.agenda is not None
    assert out.agenda.resolved_outcome == "for" and out.agenda.decided_by_speaker


def test_tie_limits_choice_to_tied_outcomes(registry: StaticDataRegistry) -> None:
    state = agenda_phase.reveal_agenda(_state(registry, [DIRECTIVE, LAW]), registry, "p2")
    state = agenda_phase.cast_vote(state, registry, "p3", "p3", [_planet_of(state, "p3")])
    state = agenda_phase.cast_vote(state, registry, "p1", "p1", [_planet_of(state, "p1")])
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.agenda is not None
    totals = agenda_phase.totals(state.agenda)
    if totals["p3"] == totals["p1"]:
        assert state.agenda.step is AgendaStep.TIEBREAK
        assert sorted(state.agenda.tied) == ["p1", "p3"]
        with pytest.raises(ValueError, match="tied"):
            agenda_phase.decide_tie(state, registry, "p2", "p2")
    else:
        assert state.agenda.step is AgendaStep.RESOLVED


def test_full_phase_readies_planets_and_ends_round(registry: StaticDataRegistry) -> None:
    state = _state(registry, [LAW, DIRECTIVE])
    state.players["p3"].exhausted_planets = [_planet_of(state, "p3")]
    for expected in (AgendaStep.RESOLVED, AgendaStep.RESOLVED):
        state = agenda_phase.reveal_agenda(state, registry, "p2")
        for pid in ("p3", "p1", "p2"):
            state = agenda_phase.abstain(state, registry, pid)
        state = agenda_phase.decide_tie(
            state, registry, "p2", state.agenda.tied[0]  # type: ignore[union-attr]
        )
        assert state.agenda is not None and state.agenda.step is expected
        assert not turn_flow.can_advance_phase(state)
        state = agenda_phase.continue_agenda(state, registry, "p2")
    assert state.agenda is not None and state.agenda.step is AgendaStep.COMPLETE
    assert state.players["p3"].exhausted_planets == []  # krok 3: Ready Planets
    assert len(state.agenda.history) == 2
    assert turn_flow.can_advance_phase(state)
    out = agenda_phase.finish_agenda(state, registry)
    assert out.phase is Phase.STRATEGY and out.agenda is None and out.round_number == 4


def test_agenda_needing_laws_is_discarded_and_next_revealed(registry: StaticDataRegistry) -> None:
    # Judicial Abolishment bez praw w grze: tekst karty - odrzuć i ujawnij kolejną agendę.
    state = agenda_phase.reveal_agenda(_state(registry, ["abolishment", LAW]), registry, "p2")
    assert state.agenda is not None and state.agenda.agenda_id == LAW
    assert state.agenda.step is AgendaStep.VOTE and state.agenda.agenda_number == 1
    assert state.decks.agenda_discard == ["abolishment"]


def test_unresolvable_agenda_is_discarded_by_speaker(registry: StaticDataRegistry) -> None:
    # Elect Law bez zwrotu „reveal another" (karta Absol) nie odrzuca się sama - robi to mówca.
    state = _state(registry, ["abolishment", LAW])
    state.decks.agenda_laws = {}
    st = agenda_phase.reveal_agenda(state, registry, "p2")
    st.decks.agenda_deck = ["abolishment", *st.decks.agenda_deck]
    st.agenda = st.agenda.model_copy(update={"step": AgendaStep.REVEAL}) if st.agenda else None
    st.decks.agenda_laws = {LAW: "for"}
    revealed = agenda_phase.reveal_agenda(st, registry, "p2")
    assert revealed.agenda is not None and revealed.agenda.agenda_id == "abolishment"
    revealed.agenda.unresolvable = True  # brak kandydatów (np. prawo zniknęło)
    with pytest.raises(ValueError, match="no valid outcome"):
        agenda_phase.abstain(revealed, registry, revealed.active_player_id or "")
    out = agenda_phase.discard_unresolvable(revealed, registry, "p2")
    assert out.agenda is not None and out.agenda.step is AgendaStep.REVEAL
    assert out.decks.agenda_discard[-1] == "abolishment"


def test_entering_agenda_phase_initialises_state(registry: StaticDataRegistry) -> None:
    state = _state(registry, [LAW])
    state.phase = Phase.STATUS
    state.agenda = None
    out = turn_flow.next_phase(state)
    assert out.phase is Phase.AGENDA and out.agenda is not None
    assert out.agenda.step is AgendaStep.REVEAL
    assert out.active_player_id == "p2"
    with pytest.raises(ValueError, match="steps"):
        turn_flow.advance_active_player(out)


def test_elected_player_owns_law_in_play(registry: StaticDataRegistry) -> None:
    from src.api import web_agenda

    elect_law = next(
        agenda_id
        for agenda_id, a in registry.catalog.all(ComponentCategory.AGENDA).items()
        if agenda_phase.classify_target(getattr(a, "target", None)) == "player"
        and (getattr(a, "type", "") or "").lower() == "law"
    )
    state = agenda_phase.reveal_agenda(_state(registry, [elect_law]), registry, "p2")
    state = agenda_phase.cast_vote(state, registry, "p3", "p1", [_planet_of(state, "p3")])
    state = agenda_phase.abstain(state, registry, "p1")
    state = agenda_phase.abstain(state, registry, "p2")
    assert state.decks.agenda_laws == {elect_law: "p1"}
    assert agenda_phase.owned_laws(state, registry, "p1") == [elect_law]
    assert agenda_phase.owned_laws(state, registry, "p3") == []
    laws = web_agenda.build_laws_in_play(state, registry, {"p1": "faction_a"})
    assert laws[0]["id"] == elect_law
    assert laws[0]["electedFaction"] == "faction_a" and laws[0]["displaysElectedFaction"]
