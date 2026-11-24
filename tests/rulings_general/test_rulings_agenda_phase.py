"""Faza agendy i karty agendy — rulingi ``R_agenda_phase.md`` i ``R_agenda_card.md``.

Część punktów sprawdzają też testy przebiegu fazy w ``tests/test_agenda_phase.py`` (oznaczone
``@ruling`` na miejscu). Statusy bez testu: ``tests/rulings_status.json``.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from src.core import action_cards, agenda_phase, economy, rules_hooks, status_phase
from src.core.components import AgendaDef, ComponentCategory
from src.core.game_state import AgendaStep, GameState, Phase, StatusPhaseState, StatusStep
from src.core.planet_stats import influence_of
from src.core.registry import StaticDataRegistry
from tests.rulings import ruling
from tests.rulings_general.test_rulings_agendas import _abstain_all, _resolve, _reveal, _state
from tests.test_agenda_effects import _planet
from tests.test_agenda_effects import registry as registry  # noqa: F401 - fixture modułu
from tests.test_reactions_agenda import _play, _playable

LAW = "revolution"  # For/Against, prawo (base)


@pytest.fixture(autouse=True)
def _bound(registry: StaticDataRegistry) -> Iterator[None]:
    rules_hooks.bind_registry(registry)
    yield


def _voting(registry: StaticDataRegistry, deck: list[str] | None = None) -> GameState:
    return _reveal(_state(registry, deck or [LAW]), registry)


# ======================================================================= Kiedy jest faza agendy


@ruling("R_agenda_phase/rules-reference/1")
def test_agenda_phase_only_after_custodians_removed(registry: StaticDataRegistry) -> None:
    def status_done(removed: bool) -> GameState:
        state = _state(registry, [LAW])
        state.phase, state.agenda = Phase.STATUS, None
        state.status = StatusPhaseState(step=StatusStep.COMPLETE)
        state.custodians_removed = removed
        for pid, cards in zip(sorted(state.players), ([1, 2], [3, 4], [5, 6]), strict=False):
            state.players[pid].strategy_cards = cards  # faza strategii rundy zakończona
        return status_phase.finish_status(state, registry)

    early = status_done(False)
    assert early.phase is Phase.STRATEGY and early.round_number == 4  # agenda pominięta
    late = status_done(True)
    assert late.phase is Phase.AGENDA and late.agenda is not None
    assert late.agenda.step is AgendaStep.REVEAL


# ======================================================================= Głosy


@ruling("R_agenda_phase/rules-reference/5.1")
def test_planet_gives_its_full_influence(registry: StaticDataRegistry) -> None:
    out = _voting(registry)
    planet = _planet(out, "p3")
    out = agenda_phase.cast_vote(out, registry, "p3", "for", [planet])
    assert out.agenda is not None and out.agenda.votes["p3"].votes == influence_of(
        out, registry, planet
    )
    import inspect

    assert "votes" not in inspect.signature(agenda_phase.cast_vote).parameters  # bez części


@ruling("R_agenda_phase/notes/2")
def test_space_stations_and_the_triad_give_votes(registry: StaticDataRegistry) -> None:
    """Stacja kosmiczna (TE) i The Triad głosują wpływem jak planety; Oceany należą do frakcji
    Deepwrought (jeszcze bez modułu frakcji)."""
    state = _state(registry, [LAW])
    state.systems["101"].planet_owners["oluzstation"] = "p1"
    state.players["p1"].relics = ["thetriad"]
    rows = {r["planet"]: r for r in agenda_phase.voting_planets(state, registry, "p1")}
    assert rows["oluzstation"]["influence"] == registry.planets["oluzstation"].influence
    triad = next(p for p in rows if "thetriad" in p)
    assert rows[triad]["influence"] > 0
    out = _reveal(state, registry)
    out = agenda_phase.abstain(out, registry, "p3")
    out = agenda_phase.cast_vote(out, registry, "p1", "for", ["oluzstation", triad])
    assert out.agenda is not None
    assert out.agenda.votes["p1"].votes == rows["oluzstation"]["influence"] + rows[triad][
        "influence"
    ]


@ruling("R_agenda_phase/rules-reference/6", "R_agenda_phase/rules-reference/14")
def test_all_votes_of_a_player_go_to_one_outcome(registry: StaticDataRegistry) -> None:
    out = _voting(registry)
    out = agenda_phase.cast_vote(out, registry, "p3", "for", [_planet(out, "p3")])
    with pytest.raises(ValueError):  # drugi głos tego samego gracza
        agenda_phase.cast_vote(out, registry, "p3", "against", [_planet(out, "p3")])
    work = out.clone()
    agenda_phase.add_votes(work, registry, "p3", 2)  # dodatkowe głosy: ten sam wynik
    assert work.agenda is not None and work.agenda.votes["p3"].outcome == "for"
    assert work.agenda.votes["p3"].votes == out.agenda.votes["p3"].votes + 2  # type: ignore


@ruling("R_agenda_phase/rules-reference/8", "R_agenda_phase/rules-reference/10")
def test_elect_only_eligible_controlled_planets(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["disarmament"])
    out = _reveal(state, registry)
    assert out.agenda is not None
    owned = sorted(state.systems["101"].planet_owners)
    assert out.agenda.outcomes == owned  # tylko planety kontrolowane przez graczy
    loose = next(p for p in sorted(registry.planets) if p not in owned)
    with pytest.raises(ValueError, match="possible outcome"):
        agenda_phase.cast_vote(out, registry, "p3", loose, [_planet(out, "p3")])


@ruling(
    "R_agenda_phase/rules-reference/9",
    "R_agenda_phase/rules-reference/9.1",
    "R_agenda_phase/rules-reference/10.1",
)
def test_vote_for_yourself_and_most_votes_elect(registry: StaticDataRegistry) -> None:
    out = _voting(registry, ["secret"])
    out = agenda_phase.cast_vote(out, registry, "p3", "p3", [_planet(out, "p3")])  # na siebie
    out = _abstain_all(out, registry)
    assert out.agenda is not None and out.agenda.resolved_outcome == "p3"
    out = _voting(registry, ["disarmament"])
    target = _planet(out, "p1")
    out = agenda_phase.cast_vote(out, registry, "p3", target, [_planet(out, "p3")])
    out = _abstain_all(out, registry)
    assert out.agenda is not None and out.agenda.resolved_outcome == target


@ruling("R_agenda_phase/rules-reference/11")
def test_votes_are_public(registry: StaticDataRegistry) -> None:
    from src.api import web_agenda

    out = _voting(registry)
    out = agenda_phase.cast_vote(out, registry, "p3", "for", [_planet(out, "p3")])
    payload = web_agenda.build_agenda_payload(out, registry)
    assert payload is not None and payload["votes"]["p3"]["outcome"] == "for"
    assert payload["totals"]["for"] == out.agenda.votes["p3"].votes  # type: ignore[union-attr]


@ruling("R_agenda_phase/rules-reference/12")
def test_trade_goods_buy_no_votes(registry: StaticDataRegistry) -> None:
    out = _voting(registry)
    out.players["p3"].trade_goods = 10
    with pytest.raises(ValueError, match="zero votes"):
        agenda_phase.cast_vote(out, registry, "p3", "for", [])
    assert agenda_phase.extra_votes(out, registry, "p3") == 0


@ruling("R_agenda_phase/rules-reference/13")
def test_abstaining_exhausts_nothing(registry: StaticDataRegistry) -> None:
    out = agenda_phase.abstain(_voting(registry), registry, "p3")
    assert out.agenda is not None and out.agenda.abstained == ["p3"]
    assert out.players["p3"].exhausted_planets == []


@ruling("R_agenda_phase/rules-reference/15")
def test_blocked_player_cannot_cast_votes_any_way(registry: StaticDataRegistry) -> None:
    out = _voting(registry)
    agenda_phase.block_voter(out, registry, "p1")
    out = agenda_phase.abstain(out, registry, "p3")
    assert agenda_phase.current_voter(out) == "p2"  # p1 pominięty
    with pytest.raises(ValueError):
        agenda_phase.cast_vote(out, registry, "p1", "for", [_planet(out, "p1")])
    with pytest.raises(ValueError):
        agenda_phase.add_votes(out.clone(), registry, "p1", 3)  # żadnym innym efektem


@ruling("R_agenda_phase/rules-reference/16")
def test_only_the_speaker_resolves_and_moves_on(registry: StaticDataRegistry) -> None:
    out = _voting(registry)
    out.players["p3"].private.action_cards = ["sabo1"]  # pauza przed wynikiem
    out = agenda_phase.cast_vote(out, registry, "p3", "for", [_planet(out, "p3")])
    out = _abstain_all(out, registry)
    with pytest.raises(ValueError, match="speaker"):
        agenda_phase.confirm_outcome(out, registry, "p3")
    out = agenda_phase.confirm_outcome(out, registry, "p2")
    with pytest.raises(ValueError, match="speaker"):
        agenda_phase.continue_agenda(out, registry, "p1")


@ruling("R_agenda_phase/rules-reference/17.1")
def test_speaker_decision_adds_no_votes(registry: StaticDataRegistry) -> None:
    out = _abstain_all(_voting(registry), registry)
    out = agenda_phase.decide_tie(out, registry, "p2", "against")
    assert out.agenda is not None and out.agenda.decided_by_speaker
    assert agenda_phase.totals(out.agenda) == {"for": 0, "against": 0}
    assert out.agenda.history[-1]["votes"] == {}


@ruling("R_agenda_phase/rules-reference/20", "R_agenda_phase/rules-reference/20.1")
def test_predictions_after_reveal_before_votes(registry: StaticDataRegistry) -> None:
    state = _state(registry, [LAW])
    state.players["p1"].private.action_cards = ["trade_rider"]
    assert not _playable(state, registry, "p1", "trade_rider")  # agenda nieujawniona
    out = _reveal(state, registry)
    with pytest.raises(ValueError, match="possible outcomes"):
        action_cards.play_action_card(out, registry, "p1", "trade_rider", {"outcome": "p3"})
    assert _playable(out, registry, "p1", "trade_rider")
    voted = agenda_phase.cast_vote(out, registry, "p3", "for", [_planet(out, "p3")])
    assert not _playable(voted, registry, "p1", "trade_rider")  # po pierwszym głosie za późno


@ruling("R_agenda_phase/notes/1")
def test_voting_is_not_the_voters_turn(registry: StaticDataRegistry) -> None:
    out = _voting(registry)
    out.players["p3"].private.action_cards = ["f_researched"]  # ACTION: tylko w swojej turze
    assert agenda_phase.current_voter(out) == "p3"
    assert not _playable(out, registry, "p3", "f_researched")


def _gain_order(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    order: list[str] = []
    real = economy.gain_trade_goods

    def spy(st: GameState, pid: str, amount: int, *, cause: str = "") -> None:
        order.append(pid)
        real(st, pid, amount, cause=cause)

    monkeypatch.setattr(economy, "gain_trade_goods", spy)
    return order


@ruling("R_agenda_card/notes/2", "R_agenda_phase/notes/7")
def test_outcome_affects_players_in_speaker_order(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    order = _gain_order(monkeypatch)
    _resolve(registry, _state(registry, ["economic_equality"]), "for")
    assert order == ["p2", "p3", "p1"]


@ruling("R_agenda_phase/notes/8")
def test_riders_resolve_after_the_agenda_in_speaker_order(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _state(registry, ["economic_equality"])
    state.players["p1"].private.action_cards = ["trade_rider"]
    state.players["p3"].private.action_cards = ["trade_rider"]
    out = _reveal(state, registry)
    out = _play(out, registry, "p1", "trade_rider", outcome="for")
    out = _play(out, registry, "p3", "trade_rider", outcome="for")
    order = _gain_order(monkeypatch)
    out = agenda_phase.decide_tie(_abstain_all(out, registry), registry, "p2", "for")
    if out.agenda is not None and out.agenda.step is AgendaStep.COUNTED:
        out = agenda_phase.confirm_outcome(out, registry, "p2")
    assert order == ["p2", "p3", "p1", "p3", "p1"]  # efekt agendy, potem riders od mówcy


@ruling("R_agenda_phase/notes/11")
def test_only_planets_ready_at_the_end_of_the_phase(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    state.agenda.agenda_number = 2  # type: ignore[union-attr]
    state.agenda.step = AgendaStep.RESOLVED  # type: ignore[union-attr]
    player = state.players["p1"]
    player.exhausted_planets = [_planet(state, "p1")]
    player.technologies, player.exhausted_technologies = ["pi"], ["pi"]
    player.relics, player.exhausted_relics = ["thetriad", "x"], ["x"]
    out = agenda_phase.continue_agenda(state, registry, "p2")
    assert out.players["p1"].exhausted_planets == []
    assert out.players["p1"].exhausted_technologies == ["pi"]
    assert out.players["p1"].exhausted_relics == ["x"]


# ======================================================================= Karty agendy


def _agenda_defs(registry: StaticDataRegistry) -> dict[str, AgendaDef]:
    from src.core import objectives

    ids = objectives.agenda_deck_ids(registry)
    found = {i: registry.catalog.get(ComponentCategory.AGENDA, i) for i in ids}
    return {i: d for i, d in found.items() if isinstance(d, AgendaDef)}


@ruling("R_agenda_card/rules-reference/1")
def test_every_agenda_is_a_law_or_a_directive(registry: StaticDataRegistry) -> None:
    defs = _agenda_defs(registry)
    assert defs and {(d.type or "").strip().lower() for d in defs.values()} == {"law", "directive"}


@ruling("R_agenda_card/rules-reference/2", "R_agenda_card/rules-reference/5")
def test_law_changes_rules_until_discarded_to_the_top(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    state.decks.agenda_discard = ["mutiny"]
    state.decks.agenda_laws = {"rep_govt": "for"}
    assert agenda_phase.single_vote(state, "p1")  # prawo zmienia zasady głosowania
    agenda_phase.remove_law(state, "rep_govt")
    assert not agenda_phase.single_vote(state, "p1")
    assert state.decks.agenda_discard[-1] == "rep_govt"  # wierzch stosu = koniec listy


@ruling("R_agenda_card/rules-reference/7", "R_agenda_card/rules-reference/8")
def test_directive_is_one_time_and_discarded(registry: StaticDataRegistry) -> None:
    out = _resolve(registry, _state(registry, ["economic_equality"]), "for")
    assert out.decks.agenda_laws == {} and out.decks.agenda_discard == ["economic_equality"]
    assert not [e for e in out.active_effects if "economic_equality" in e.key]

