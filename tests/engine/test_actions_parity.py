"""Zgodność katalogu akcji bota z HTTP dla akcji spoza krótkich gier + strażnik pokrycia (B1).

Każdy rodzaj z ``ACTION_KINDS`` musi być (a) w mapie HTTP, (b) sprawdzony w scenariuszu gry
(``test_passive_games.SCENARIOS``) albo celowanym teście tutaj, albo (c) jawnie wpisany do
``NOT_YET_COVERED`` z powodem — lista ma się kurczyć z kolejnymi blokami bota.
"""

from __future__ import annotations

import pytest

from src.core import agenda_phase
from src.core.game_state import AgendaStep, GameState, Phase
from src.core.registry import StaticDataRegistry
from src.engine import actions as act
from src.engine.legal import legal_actions
from src.engine.observation import observe
from tests.engine.driver import BotTable
from tests.engine.http_map import HTTP
from tests.engine.test_passive_games import FOUR, SCENARIO_KINDS

TARGETED_KINDS = {"discard_excess", "phase_step", "round_next", "agenda_vote"}
"""Rodzaje sprawdzane celowanymi testami w tym pliku."""

NOT_YET_COVERED: dict[str, str] = {
    "battle_assign": "walka powstaje dopiero z ruchu i aktywacji - scenariusz w B5",
    "held_pass": "okno hold-play otwiera zagranie karty akcji - bot zagrywa karty od B5",
    "held_release": "jak held_pass",
    "offer_decline": "oferty opcjonalne wypadają dopiero w 4. rundzie gry ludzi (za wolno na "
    "szybki zestaw); celowany scenariusz w B5",
}


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def test_every_action_kind_has_http_mapping() -> None:
    assert set(HTTP) == act.ACTION_KINDS


def test_every_action_kind_is_covered_or_listed() -> None:
    covered = SCENARIO_KINDS | TARGETED_KINDS
    listed = set(NOT_YET_COVERED)
    assert not covered & listed, f"covered now - remove from NOT_YET_COVERED: {covered & listed}"
    assert covered | listed == act.ACTION_KINDS, sorted(act.ACTION_KINDS - covered - listed)


def _first_for(table: BotTable, pid: str) -> act.Action:
    ctx = table.ctx()
    candidates = legal_actions(observe(table.state, ctx, pid), ctx)
    assert candidates, f"no legal action for {pid}"
    return candidates[0]


def test_discard_excess_over_hand_limit(registry: StaticDataRegistry) -> None:
    table = BotTable(registry, FOUR)
    table.run(until_round=9, stop=lambda s: s.phase is Phase.ACTION)
    state = table.state.clone()
    pid = state.active_player_id
    assert pid is not None
    hand = state.players[pid].private.action_cards
    deck = state.decks.action_card_deck
    while len(hand) < 8:  # limit ręki to 7 (engine_config.json) => jedna nadwyżka
        hand.append(deck.pop(0))
    table.inject(state)

    action = _first_for(table, pid)

    assert action.kind == "discard_excess"
    assert table.check(action) == []


def test_phase_step_in_status_without_steps(registry: StaticDataRegistry) -> None:
    table = BotTable(registry, FOUR)
    table.run(until_round=9, stop=lambda s: s.phase is Phase.STATUS)
    state = table.state.clone()
    state.status = None  # faza statusu bez kroków (stan z God-Mode)
    table.inject(state)
    pid = state.active_player_id
    assert pid is not None

    action = _first_for(table, pid)

    assert action.kind == "phase_step"
    assert table.check(action) == []


def test_round_next_in_agenda_without_steps(registry: StaticDataRegistry) -> None:
    table = BotTable(registry, FOUR, patch={"custodians_removed": True})
    table.run(until_round=9, stop=lambda s: s.phase is Phase.AGENDA)
    state = table.state.clone()
    state.agenda = None  # agenda bez kroków (God-Mode): UI ogłasza „Next round”
    table.inject(state)
    assert state.speaker_id is not None

    action = _first_for(table, state.speaker_id)

    assert action.kind == "round_next"
    assert table.check(action) == []


def _voting(state: GameState) -> bool:
    agenda = state.agenda
    if agenda is None or state.reaction_pause is not None:
        return False
    return agenda.step is AgendaStep.VOTE and bool(agenda.outcomes)


def test_agenda_vote_matches_http(registry: StaticDataRegistry) -> None:
    table = BotTable(registry, FOUR, patch={"custodians_removed": True})
    table.run(until_round=9, stop=_voting)
    state = table.state
    assert state.agenda is not None
    voter = agenda_phase.current_voter(state)
    assert voter is not None
    ready = [
        row["planet"]
        for row in agenda_phase.voting_planets(state, registry, voter)
        if not row["exhausted"]
    ]
    action = act.AgendaVote(player_id=voter, outcome=state.agenda.outcomes[0], planets=ready[:1])

    assert table.check(action) == []
