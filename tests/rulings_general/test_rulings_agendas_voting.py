"""Agendy zmieniające samo głosowanie — rulingi ``C_agendas.md``: Committee Formation, Covert
Legislation, Judicial Abolishment, Miscount Disclosed, Political Censure.

Wspólne helpery: ``test_rulings_agendas.py``. Statusy bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.core import action_cards, agenda_phase, promissory_play, rules_hooks
from src.core.game_state import AgendaStep, GameState
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.rulings_general.test_rulings_agendas import (
    _abstain_all,
    _accept,
    _offer,
    _resolve,
    _reveal,
    _state,
)
from tests.test_agenda_effects import _planet
from tests.test_agenda_effects import registry as registry  # noqa: F401 - fixture modułu
from tests.test_reactions_agenda import _play, _playable


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    yield


def _counted(state: GameState, registry: StaticDataRegistry, outcome: str) -> GameState:
    """Wszyscy się wstrzymują, mówca wybiera ``outcome``; wynik czeka w kroku COUNTED."""
    state = _abstain_all(state, registry)
    if state.agenda is not None and state.agenda.step is AgendaStep.TIEBREAK:
        state = agenda_phase.decide_tie(state, registry, "p2", outcome)
    assert state.agenda is not None and state.agenda.step is AgendaStep.COUNTED
    return state


def _finish(state: GameState, registry: StaticDataRegistry, outcome: str) -> GameState:
    state = _abstain_all(state, registry)
    if state.agenda is not None and state.agenda.step is AgendaStep.TIEBREAK:
        state = agenda_phase.decide_tie(state, registry, "p2", outcome)
    if state.agenda is not None and state.agenda.step is AgendaStep.COUNTED:
        state = agenda_phase.confirm_outcome(state, registry, "p2")
    return state


# ======================================================================= Committee Formation


def _committee(registry: StaticDataRegistry, hands: dict[str, list[str]]) -> GameState:
    state = _state(registry, ["secret"])
    state.decks.agenda_laws = {"committee": "p1"}
    for pid, cards in hands.items():
        state.players[pid].private.action_cards = list(cards)
    return _reveal(state, registry)


@ruling("C_agendas/committee-formation/1", "C_agendas/committee-formation/1.1")
def test_committee_riders_first_then_matching_rider_pays(registry: StaticDataRegistry) -> None:
    out = _committee(registry, {"p1": ["trade_rider"], "p3": ["trade_rider"]})
    assert _offer(out, "p1").label == "Committee Formation"  # czeka, właściciel nie musi od razu
    out = _play(out, registry, "p1", "trade_rider", outcome="p3")  # właściciel też gra ridera
    out = _play(out, registry, "p3", "trade_rider", outcome="p1")
    out = _accept(out, "p1", {"player": "p3"})
    if out.agenda is not None and out.agenda.step is AgendaStep.COUNTED:
        out = agenda_phase.confirm_outcome(out, registry, "p2")
    assert out.agenda is not None and out.agenda.resolved_outcome == "p3"
    assert out.players["p1"].trade_goods == 5 and out.players["p3"].trade_goods == 0


@ruling("C_agendas/committee-formation/2")
def test_committee_choice_can_be_changed_by_legal_text(registry: StaticDataRegistry) -> None:
    out = _committee(registry, {"p3": ["confusing"]})
    out = _accept(out, "p1", {"player": "p3"})
    assert out.agenda is not None and out.agenda.step is AgendaStep.COUNTED
    assert "committee" not in out.decks.agenda_laws  # już odrzucona
    assert _playable(out, registry, "p3", "confusing")
    out = _play(out, registry, "p3", "confusing", player="p2")
    out = agenda_phase.confirm_outcome(out, registry, "p2")
    assert out.agenda is not None and out.agenda.resolved_outcome == "p2"


@ruling("C_agendas/committee-formation/2.1")
def test_committee_deadly_plot_only_with_a_different_prediction(
    registry: StaticDataRegistry,
) -> None:
    out = _committee(registry, {"p3": ["deadly_plot", "trade_rider"]})
    blank = _accept(out, "p1", {"player": "p1"})
    assert not _playable(blank, registry, "p3", "deadly_plot")  # nikt nie głosował
    out = _play(out, registry, "p3", "trade_rider", outcome="p2")  # inny wynik z rider
    out = _accept(out, "p1", {"player": "p1"})
    assert _playable(out, registry, "p3", "deadly_plot")
    out = _play(out, registry, "p3", "deadly_plot")
    assert out.agenda is not None and out.agenda.resolved_outcome is None


# ======================================================================= Covert Legislation


@ruling("C_agendas/covert-legislation/1")
def test_covert_hidden_card_needing_laws_discards_both(registry: StaticDataRegistry) -> None:
    out = _reveal(_state(registry, ["covert", "abolishment", "mutiny"]), registry)
    assert out.agenda is not None and out.agenda.agenda_id == "mutiny"
    assert sorted(out.decks.agenda_discard) == ["abolishment", "covert"]


@ruling("C_agendas/covert-legislation/2")
def test_covert_reveal_effects_fire_for_the_hidden_agenda(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["covert", "secret"])
    state.decks.agenda_laws = {"committee": "p1"}
    out = _reveal(state, registry)
    assert out.agenda is not None and out.agenda.covert_card == "secret"
    assert _offer(out, "p1").label == "Committee Formation"  # „Elect Player” ukrytej agendy


@ruling("C_agendas/covert-legislation/3")
def test_covert_veto_discards_both_cards(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["covert", "conscription", "mutiny"])
    state.players["p1"].private.action_cards = ["veto"]
    out = _reveal(state, registry)
    out = _play(out, registry, "p1", "veto")
    assert out.agenda is not None and out.agenda.agenda_id == "mutiny"
    assert {"covert", "conscription"} <= set(out.decks.agenda_discard)


@ruling("C_agendas/covert-legislation/4")
def test_covert_hidden_until_resolved_reactions_before(registry: StaticDataRegistry) -> None:
    from src.api import web_agenda

    state = _state(registry, ["covert", "conscription"])
    state.players["p3"].private.action_cards = ["bribery"]
    out = _reveal(state, registry)
    out = agenda_phase.cast_vote(out, registry, "p3", "for", [_planet(out, "p3")])
    out = _abstain_all(out, registry)
    assert out.agenda is not None and out.agenda.step is AgendaStep.COUNTED
    payload = web_agenda.build_agenda_payload(out, registry)
    assert payload is not None and "conscription" not in str(payload)  # jeszcze ukryta
    assert _playable(out, registry, "p3", "bribery")  # karty „po głosach” - przed ujawnieniem
    out = agenda_phase.confirm_outcome(out, registry, "p2")
    payload = web_agenda.build_agenda_payload(out, registry)
    assert payload is not None and payload["history"][-1]["agenda"] == "conscription"


@ruling("C_agendas/covert-legislation/5")
def test_covert_speaker_still_votes(registry: StaticDataRegistry) -> None:
    out = _reveal(_state(registry, ["covert", "conscription"]), registry)
    out = agenda_phase.abstain(out, registry, "p3")
    out = agenda_phase.abstain(out, registry, "p1")
    assert agenda_phase.current_voter(out) == "p2"
    out = agenda_phase.cast_vote(out, registry, "p2", "for", [_planet(out, "p2")])
    assert out.decks.agenda_laws == {"conscription": "for"}


# ================================================================== Judicial Abolishment / Miscount


@ruling(
    "C_agendas/judicial-abolishment/1",
    "C_agendas/judicial-abolishment/1.1",
    "C_agendas/miscount-disclosed/1",
    "C_agendas/miscount-disclosed/1.1",
)
@pytest.mark.parametrize("card", ["abolishment", "miscount"])
def test_single_law_is_the_only_outcome_riders_allowed(
    registry: StaticDataRegistry, card: str
) -> None:
    state = _state(registry, [card])
    state.decks.agenda_laws = {"conscription": "for"}
    state.players["p3"].private.action_cards = ["trade_rider"]
    out = _reveal(state, registry)
    assert out.agenda is not None and out.agenda.outcomes == ["conscription"]
    assert _playable(out, registry, "p3", "trade_rider")
    out = _play(out, registry, "p3", "trade_rider", outcome="conscription")
    out = _abstain_all(out, registry)
    assert out.agenda is not None and out.agenda.tied == ["conscription"]  # mówca musi je wybrać
    with pytest.raises(ValueError):
        agenda_phase.decide_tie(out, registry, "p2", "for")


def _miscount(registry: StaticDataRegistry, law: str, outcome: str = "for",
              deck: list[str] | None = None) -> GameState:
    """Miscount Disclosed wybiera ``law``; po „dalej” mówcy trwa ponowne głosowanie."""
    state = _state(registry, ["miscount", *(deck or [])])
    state.decks.agenda_laws = {law: outcome}
    out = _resolve(registry, state, law)
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert out.agenda is not None and out.agenda.agenda_id == law
    return out


@ruling("C_agendas/miscount-disclosed/2", "C_agendas/miscount-disclosed/2.3")
def test_miscount_law_stays_in_force_during_the_revote(registry: StaticDataRegistry) -> None:
    out = _miscount(registry, "rep_govt")
    assert out.decks.agenda_laws == {"rep_govt": "for"}
    with pytest.raises(ValueError, match="Representative Government"):
        agenda_phase.cast_vote(out, registry, "p3", "for", [_planet(out, "p3")])
    out = agenda_phase.cast_vote(out, registry, "p3", "against", [])
    assert out.agenda is not None and out.agenda.votes["p3"].votes == 1


@ruling("C_agendas/miscount-disclosed/2")
def test_miscount_articles_of_war_still_strip_mechs(registry: StaticDataRegistry) -> None:
    out = _miscount(registry, "articles_war")
    out.players["p1"].faction = "hacan"
    assert rules_hooks.unit_abilities_lost(out, "p1", "mech")  # Pride of Kenara bez zdolności


@ruling("C_agendas/miscount-disclosed/2.1")
def test_miscount_committee_owner_may_use_it_on_the_revote(registry: StaticDataRegistry) -> None:
    out = _miscount(registry, "committee", outcome="p1")
    offer = _offer(out, "p1")
    assert offer.label == "Committee Formation"
    out = _accept(out, "p1", {"player": "p3"})
    if out.agenda is not None and out.agenda.step is AgendaStep.COUNTED:
        out = agenda_phase.confirm_outcome(out, registry, "p2")
    assert out.decks.agenda_laws == {"committee": "p3"}  # wybrany bierze ją ze stosu odrzuconych
    assert "committee" not in out.decks.agenda_discard


@ruling("C_agendas/miscount-disclosed/2")
def test_miscount_defense_act_for_again_keeps_pds(registry: StaticDataRegistry) -> None:
    out = _miscount(registry, "defense_act")
    planet = _planet(out, "p1")
    out.systems["101"].planet_units = {planet: {"p1": {"pds": 4}}}
    out = _finish(out, registry, "for")
    assert out.decks.agenda_laws == {"defense_act": "for"}
    assert out.systems["101"].planet_units[planet]["p1"] == {"pds": 4}


@ruling("C_agendas/miscount-disclosed/2.2", "C_agendas/political-censure/1")
def test_censure_owner_silenced_new_elect_may_react(registry: StaticDataRegistry) -> None:
    out = _miscount(registry, "censure", outcome="p1")
    out.players["p1"].private.action_cards = ["confounding"]
    out.players["p3"].private.action_cards = ["confusing", "sabo1"]
    assert action_cards.forbidden_reason(out, "p1") is not None  # wciąż właściciel
    out = agenda_phase.cast_vote(out, registry, "p3", "p3", [_planet(out, "p3")])
    out = _abstain_all(out, registry)
    assert out.agenda is not None and out.agenda.pending_outcome == "p3"
    assert not _playable(out, registry, "p1", "confounding")
    assert _playable(out, registry, "p3", "confusing")  # wybrany zagra przed rozstrzygnięciem


@ruling("C_agendas/miscount-disclosed/3", "C_agendas/miscount-disclosed/3.3")
def test_miscount_riders_resolve_then_new_riders_on_the_law(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["miscount"])
    state.decks.agenda_laws = {"conscription": "for"}
    state.players["p3"].private.action_cards = ["trade_rider", "trade_rider"]
    out = _reveal(state, registry)
    out = _play(out, registry, "p3", "trade_rider", outcome="conscription")
    out = _finish(out, registry, "conscription")
    assert out.players["p3"].trade_goods == 5  # rider na Miscount - przed ponownym głosowaniem
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert _playable(out, registry, "p3", "trade_rider")
    out = _play(out, registry, "p3", "trade_rider", outcome="against")
    out = _finish(out, registry, "against")
    assert out.players["p3"].trade_goods == 10


@ruling("C_agendas/miscount-disclosed/3.2")
def test_miscount_veto_on_the_law_discards_and_replaces(registry: StaticDataRegistry) -> None:
    out = _miscount(registry, "conscription", deck=["mutiny"])
    out.players["p1"].private.action_cards = ["veto"]
    assert _playable(out, registry, "p1", "veto")
    out = _play(out, registry, "p1", "veto")
    assert "conscription" not in out.decks.agenda_laws
    assert out.agenda is not None and out.agenda.agenda_id == "mutiny"


@ruling("C_agendas/miscount-disclosed/3")
def test_miscount_political_secret_on_the_law(registry: StaticDataRegistry) -> None:
    out = _miscount(registry, "conscription")
    out.players["p3"].private.promissory_notes = ["p1_ps"]
    rows = {r["note_id"]: r for r in promissory_play.playability(out, registry, "p3")}
    assert rows["p1_ps"]["playable"]


@ruling("C_agendas/miscount-disclosed/3.4", "C_agendas/miscount-disclosed/6")
def test_miscount_keeps_planets_exhausted_and_allows_a_second_transaction(
    registry: StaticDataRegistry,
) -> None:
    state = _state(registry, ["miscount", "mutiny", "secret"])
    state.decks.agenda_laws = {"conscription": "for"}
    planet = _planet(state, "p3")
    out = _reveal(state, registry)
    out.players["p1"].transacted_with = ["p3"]  # transaction made while voting on Miscount
    out.players["p3"].transacted_with = ["p1"]
    out = agenda_phase.cast_vote(out, registry, "p3", "conscription", [planet])
    out = _abstain_all(out, registry)
    out = _finish(out, registry, "conscription")
    out = agenda_phase.continue_agenda(out, registry, "p2")  # revote on the elected law
    assert out.agenda is not None and out.agenda.agenda_id == "conscription"
    assert planet in out.players["p3"].exhausted_planets  # planets are not readied in between
    assert out.agenda.agenda_number == 1  # the revote does not replace the second agenda
    assert out.players["p1"].transacted_with == []  # one more transaction per pair is allowed
    assert out.players["p3"].transacted_with == []
    out = _finish(out, registry, "for")
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert out.agenda is not None and out.agenda.step is AgendaStep.REVEAL
    assert out.agenda.agenda_number == 2  # ...so a third agenda vote happens in the phase
    assert planet in out.players["p3"].exhausted_planets


@ruling("C_agendas/miscount-disclosed/4")
def test_deadly_plot_on_miscount_keeps_the_law(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["miscount"])
    state.decks.agenda_laws = {"conscription": "for", "sanctions": "for"}
    state.players["p3"].private.action_cards = ["deadly_plot", "trade_rider"]
    out = _reveal(state, registry)
    out = _play(out, registry, "p3", "trade_rider", outcome="sanctions")
    out = _counted(out, registry, "conscription")
    out = _play(out, registry, "p3", "deadly_plot")
    assert out.decks.agenda_laws["conscription"] == "for"  # prawo zostaje, bez głosowania
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert out.agenda is not None and out.agenda.step is AgendaStep.REVEAL


@ruling("C_agendas/miscount-disclosed/5")
def test_deadly_plot_on_the_revote_discards_the_law(registry: StaticDataRegistry) -> None:
    out = _miscount(registry, "conscription")
    out.players["p3"].private.action_cards = ["deadly_plot"]
    out = agenda_phase.cast_vote(out, registry, "p3", "against", [_planet(out, "p3")])
    out = agenda_phase.cast_vote(out, registry, "p1", "for", [_planet(out, "p1")])
    out = agenda_phase.cast_vote(out, registry, "p2", "for", [_planet(out, "p2")])
    assert out.agenda is not None and out.agenda.step is AgendaStep.COUNTED
    out = _play(out, registry, "p3", "deadly_plot")
    assert "conscription" not in out.decks.agenda_laws
    assert "conscription" in out.decks.agenda_discard


# ======================================================================= Political Censure


@ruling("C_agendas/political-censure/2")
def test_censure_miscount_moves_the_point_to_the_new_owner(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["miscount"])
    state.decks.agenda_laws = {"censure": "p1"}
    state.players["p1"].victory_points = 1  # punkt z poprzedniego wyboru
    out = _resolve(registry, state, "censure")
    out = agenda_phase.continue_agenda(out, registry, "p2")
    out = agenda_phase.cast_vote(out, registry, "p3", "p3", [_planet(out, "p3")])
    out = _finish(out, registry, "p3")
    assert out.decks.agenda_laws["censure"] == "p3"
    assert out.players["p1"].victory_points == 0  # poprzedni właściciel traci punkt
    assert out.players["p3"].victory_points == 1  # nowy go zdobywa


@ruling("C_agendas/political-censure/2")
def test_censure_miscount_same_player_again_keeps_the_point(registry: StaticDataRegistry) -> None:
    """Ponownie wybrany gracz traci i odzyskuje punkt - w sumie nadal ma 1 punkt i kartę."""
    state = _state(registry, ["miscount"])
    state.decks.agenda_laws = {"censure": "p1"}
    state.players["p1"].victory_points = 1
    out = _resolve(registry, state, "censure")
    out = agenda_phase.continue_agenda(out, registry, "p2")
    out = agenda_phase.cast_vote(out, registry, "p3", "p1", [_planet(out, "p3")])
    out = _finish(out, registry, "p1")
    assert out.decks.agenda_laws["censure"] == "p1"
    assert out.players["p1"].victory_points == 1


@ruling("C_agendas/political-censure/2.1")
def test_censure_stays_in_play_during_the_revote(registry: StaticDataRegistry) -> None:
    out = _miscount_censure(registry)
    assert out.decks.agenda_laws["censure"] == "p1"
    assert action_cards.forbidden_reason(out, "p1") is not None  # do końca głosowania
    assert action_cards.forbidden_reason(out, "p3") is None


def _miscount_censure(registry: StaticDataRegistry) -> GameState:
    state = _state(registry, ["miscount"])
    state.decks.agenda_laws = {"censure": "p1"}
    state.players["p1"].victory_points = 1
    out = _resolve(registry, state, "censure")
    return agenda_phase.continue_agenda(out, registry, "p2")


@ruling("C_agendas/political-censure/3")
def test_censure_only_blocks_action_cards_and_cannot_be_discarded_by_owner(
    registry: StaticDataRegistry,
) -> None:
    from src.core import strategic_action
    from src.core.game_state import Phase
    from src.core.hooks.agendas_common import agenda_source

    state = _state(registry, [])
    state.phase, state.agenda = Phase.ACTION, None
    state.active_player_id = "p1"
    state.players["p1"].strategy_cards = [3]
    state.decks.agenda_laws = {"censure": "p1"}
    assert action_cards.forbidden_reason(state, "p1") is not None
    started = strategic_action.play_strategy_card(state, registry, "p1", 3)  # karty strategii OK
    assert started.pending_strategy is not None or started.pending_window is not None
    # Żaden hook Political Censure nie daje właścicielowi własnej oferty/akcji odrzucenia.
    own = [h for h in rules_hooks._REGISTRY if h.source == agenda_source("censure")]
    assert own and not any(h.optional for h in own)
