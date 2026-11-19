"""Zgodność katalogu akcji bota z HTTP dla akcji spoza krótkich gier + strażnik pokrycia (B1).

Każdy rodzaj z ``ACTION_KINDS`` musi być (a) w mapie HTTP, (b) sprawdzony w scenariuszu gry
(``test_passive_games.SCENARIOS``) albo celowanym teście tutaj, albo (c) jawnie wpisany do
``NOT_YET_COVERED`` z powodem — lista ma się kurczyć z kolejnymi blokami bota.
"""

from __future__ import annotations

import pytest

from src.api.bot_http import HTTP
from src.core import agenda_phase, fleet_pool
from src.core.game_state import AgendaStep, GameState, Phase
from src.core.registry import StaticDataRegistry
from src.engine import actions as act
from src.engine.legal import legal_actions
from src.engine.observation import observe
from tests.engine.driver import BotTable
from tests.engine.test_passive_games import FOUR, SCENARIO_KINDS

TARGETED_KINDS = {
    "discard_excess", "phase_step", "round_next", "agenda_vote", "production_skip",
    "fleet_pool_resolve",
}
"""Rodzaje sprawdzane celowanymi testami w tym pliku."""

_B5_FUZZ_ONLY = "B5: pokrywa tylko fuzzer losowych partii, brak celowanego scenariusza"

NOT_YET_COVERED: dict[str, str] = {
    "battle_assign": "walka powstaje dopiero z ruchu i aktywacji - scenariusz w B5",
    "held_pass": "okno hold-play otwiera zagranie karty akcji - bot zagrywa karty od B5",
    "held_release": "jak held_pass",
    "offer_decline": "oferty opcjonalne wypadają dopiero w 4. rundzie gry ludzi (za wolno na "
    "szybki zestaw); celowany scenariusz w B5",
    # B5 (akcja taktyczna): dziś tylko losowe partie fuzzera (``test_fuzz_games``, duża próba
    # ``python -m tests.engine.fuzz``) - celowane scenariusze zgodności HTTP do dopisania.
    "action_card_play": _B5_FUZZ_ONLY,
    "battle_afb": _B5_FUZZ_ONLY,
    "battle_announce_retreat": _B5_FUZZ_ONLY,
    "battle_close": _B5_FUZZ_ONLY,
    "battle_retreat": _B5_FUZZ_ONLY,
    "battle_roll": _B5_FUZZ_ONLY,
    "battle_start": _B5_FUZZ_ONLY,
    "capacity_resolve": _B5_FUZZ_ONLY,
    "exploration_choose": _B5_FUZZ_ONLY,
    "exploration_draw": _B5_FUZZ_ONLY,
    "exploration_finish": _B5_FUZZ_ONLY,
    "exploration_resolve": _B5_FUZZ_ONLY,
    "invasion_begin": _B5_FUZZ_ONLY,
    "invasion_bombard": _B5_FUZZ_ONLY,
    "invasion_bombard_assign": _B5_FUZZ_ONLY,
    "invasion_commit": _B5_FUZZ_ONLY,
    "invasion_custodians": _B5_FUZZ_ONLY,
    "invasion_defense_assign": _B5_FUZZ_ONLY,
    "invasion_defense_fire": _B5_FUZZ_ONLY,
    "invasion_defense_pass": _B5_FUZZ_ONLY,
    "invasion_next": _B5_FUZZ_ONLY,
    "space_cannon_assign": _B5_FUZZ_ONLY,
    "space_cannon_fire": _B5_FUZZ_ONLY,
    "space_cannon_pass": _B5_FUZZ_ONLY,
    "tactical_activate": _B5_FUZZ_ONLY,
    "tactical_move": _B5_FUZZ_ONLY,
    "tactical_next": _B5_FUZZ_ONLY,
    "tactical_produce": _B5_FUZZ_ONLY,
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


def _prefer_construction_production(candidates: list[act.Action]) -> list[act.Action]:
    """Polityka testowa: weź Construction (4), zagraj ją i wybierz PRODUCTION doku."""

    def wanted(a: act.Action) -> bool:
        if isinstance(a, (act.StrategyPick, act.StrategyPlay)):
            return a.initiative == 4
        if isinstance(a, act.StrategyPrimaryStep):
            return a.payload.get("option") == "production" or "planet" in a.payload
        return False

    return sorted(candidates, key=lambda a: not wanted(a))


def test_production_skip_after_construction_dock(registry: StaticDataRegistry) -> None:
    """Construction -> PRODUCTION doku -> „Finish production” (ta sama trasa co przycisk UI)."""
    table = BotTable(registry, FOUR, policy=_prefer_construction_production)
    table.run(until_round=3, stop=lambda s: s.production_grant is not None)
    state = table.state
    assert state.production_grant is not None, "Construction production did not start"
    grantee = state.production_grant.player_id

    action = _first_for(table, grantee)

    assert action.kind == "production_skip"
    assert table.check(action) == []
    after = table.state
    assert after.production_grant is None
    # Primary wraca do drugiej struktury (krok ``place_structure_2``) - przepływ karty trwa.
    assert after.pending_strategy is not None
    assert after.pending_strategy.step == "place_structure_2"


def test_fleet_pool_resolve_matches_http(registry: StaticDataRegistry) -> None:
    """Okno FLEET_POOL (np. po agendzie Clandestine Operations): bot zwraca nadwyżkę statków."""
    table = BotTable(registry, FOUR)
    table.run(until_round=9, stop=lambda s: s.phase is Phase.ACTION)
    state = table.state.clone()
    pid = state.active_player_id
    assert pid is not None
    home = state.players[pid].home_position
    assert home is not None
    state.players[pid].fleet_cc = 1
    state.systems[home].space_units.setdefault(pid, {})["cruiser"] = 3
    state = fleet_pool.open_fleet_pool_check(state, home)
    assert state.pending_window is not None
    table.inject(state)

    action = _first_for(table, pid)

    assert action.kind == "fleet_pool_resolve"
    assert table.check(action) == []
    after = table.state
    assert after.pending_window is None
    assert fleet_pool.fleet_report(after, home, pid, registry).excess == 0
