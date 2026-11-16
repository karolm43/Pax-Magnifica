"""Efekty kart agendy (RULES.md 51.6): dyrektywy, skutki „Against" i trwałe prawa."""

from __future__ import annotations

import pytest

from src.core import (
    action_cards,
    agenda_phase,
    command_tokens,
    hand_limit,
    offers,
    production,
    rules_hooks,
    strategy_phase,
    triggers,
)
from src.core.game_state import (
    AgendaPhaseState,
    AgendaStep,
    AgendaVote,
    GameState,
    Phase,
    PlayerState,
    SystemState,
    WindowType,
)
from src.core.planet_stats import influence_of
from src.core.registry import StaticDataRegistry
from src.core.strategy_cards.common import structure_problem


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


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
    found = [pid for pid in sorted(registry.planets) if influence_of(state, registry, pid) >= 1]
    state.systems["101"] = SystemState(
        position="101",
        system_id="1",
        planet_owners={found[0]: "p1", found[1]: "p2", found[2]: "p3"},
    )
    return state


def _planet(state: GameState, pid: str) -> str:
    owners = state.systems["101"].planet_owners
    return next(planet for planet, owner in owners.items() if owner == pid)


def _resolve(
    registry: StaticDataRegistry,
    state: GameState,
    outcome: str,
    votes: dict[str, str] | None = None,
) -> GameState:
    """Ujawnia wierzchnią agendę i rozstrzyga ``outcome`` (głosy ``votes`` albo wybór mówcy)."""
    st = agenda_phase.reveal_agenda(state, registry, "p2")
    for _ in range(3):
        voter = agenda_phase.current_voter(st)
        if voter is None:
            break
        if votes and voter in votes:
            st = agenda_phase.cast_vote(st, registry, voter, votes[voter], [_planet(st, voter)])
        else:
            st = agenda_phase.abstain(st, registry, voter)
    assert st.agenda is not None
    if st.agenda.step is AgendaStep.TIEBREAK:
        st = agenda_phase.decide_tie(st, registry, "p2", outcome)
    if st.agenda is not None and st.agenda.step is AgendaStep.COUNTED:
        st = agenda_phase.confirm_outcome(st, registry, "p2")
    assert st.agenda is not None and st.agenda.resolved_outcome == outcome
    return st


# --- Dyrektywy ---------------------------------------------------------------------------


def test_economic_equality_for_and_against(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["economic_equality"])
    state.players["p1"].trade_goods = 9
    out = _resolve(registry, state, "for")
    assert {p.trade_goods for p in out.players.values()} == {5}
    state = _state(registry, ["economic_equality"])
    state.players["p1"].trade_goods = 9
    out = _resolve(registry, state, "against")
    assert out.players["p1"].trade_goods == 0


def test_mutiny_rewards_or_punishes_for_voters(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["mutiny"])
    state.players["p3"].victory_points = 2
    out = _resolve(registry, state, "for", votes={"p3": "for"})
    assert out.players["p3"].victory_points == 3 and out.players["p1"].victory_points == 0
    state = _state(registry, ["mutiny"])
    state.players["p3"].victory_points = 2
    votes = {"p3": "for", "p1": "against", "p2": "against"}
    out = _resolve(registry, state, "against", votes=votes)
    assert out.players["p3"].victory_points == 1
    assert out.objectives.point_sources["agendas:mutiny"] == {"p3": -1}


def test_seed_of_an_empire_ties_all_gain(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["seed_empire"])
    state.players["p1"].victory_points = 4
    out = _resolve(registry, state, "against")
    assert [out.players[p].victory_points for p in ("p1", "p2", "p3")] == [4, 1, 1]


def test_public_execution(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["execution", "economic_equality"])
    state.players["p2"].private.action_cards = ["sabo1", "sabo2"]
    out = _resolve(registry, state, "p2")
    assert out.players["p2"].private.action_cards == []
    assert out.speaker_id == "p3"  # mówca oddaje żeton graczowi po lewej
    out = agenda_phase.continue_agenda(out, registry, "p3")
    out = agenda_phase.reveal_agenda(out, registry, "p3")
    assert out.agenda is not None and "p2" in out.agenda.blocked  # bez głosu do końca fazy


def test_judicial_abolishment_discards_law(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["abolishment"])
    state.decks.agenda_laws = {"conscription": "for"}
    out = _resolve(registry, state, "conscription")
    assert out.decks.agenda_laws == {} and "conscription" in out.decks.agenda_discard


def test_miscount_revotes_the_law(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["miscount"])
    state.decks.agenda_laws = {"conscription": "for"}
    out = _resolve(registry, state, "conscription")
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert out.agenda is not None and out.agenda.agenda_id == "conscription"
    assert out.agenda.step is AgendaStep.VOTE and out.agenda.agenda_number == 1
    st = out
    for _ in range(3):
        voter = agenda_phase.current_voter(st)
        if voter is None:
            break
        st = agenda_phase.abstain(st, registry, voter)
    st = agenda_phase.decide_tie(st, registry, "p2", "against")
    assert "conscription" not in st.decks.agenda_laws
    assert "conscription" in st.decks.agenda_discard


def test_new_constitution_needs_laws_and_discards_them(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["constitution", "economic_equality"])
    out = agenda_phase.reveal_agenda(state, registry, "p2")
    assert out.agenda is not None and out.agenda.agenda_id == "economic_equality"
    state = _state(registry, ["constitution"])
    state.decks.agenda_laws = {"conscription": "for", "sanctions": "for"}
    out = _resolve(registry, state, "for")
    assert out.decks.agenda_laws == {}
    assert len(agenda_phase.effects_of(out, "agendas:constitution:for")) == 3


def test_covert_legislation_resolves_hidden_agenda(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["covert", "conscription"])
    out = agenda_phase.reveal_agenda(state, registry, "p2")
    assert out.agenda is not None and out.agenda.agenda_id == "covert"
    assert out.agenda.covert_card == "conscription" and out.agenda.kind == "for_against"
    state = _state(registry, ["covert", "conscription"])
    out = _resolve(registry, state, "for")
    assert out.decks.agenda_laws == {"conscription": "for"}
    assert out.decks.agenda_discard == ["covert"]


def test_armed_forces_standardization(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["standardization"])
    player = state.players["p1"]
    player.tactical_cc, player.fleet_cc, player.strategic_cc, player.cc_reinf = 1, 5, 0, 8
    out = _resolve(registry, state, "p1")
    pools = {p: command_tokens.pool_count(out, "p1", p) for p in command_tokens.POOLS}
    assert pools == {"tactical": 3, "fleet": 3, "strategic": 2}
    assert command_tokens.reinforcements(out, "p1") == 6


def test_arms_reduction_destroys_excess(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["arms_reduction"])
    state.systems["101"].space_units = {"p1": {"dreadnought": 4, "cruiser": 5}}
    out = _resolve(registry, state, "for")
    assert out.systems["101"].space_units["p1"] == {"dreadnought": 2, "cruiser": 4}


def test_incentive_program_reveals_stage(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["incentive"])
    state.objectives.stage1_deck = ["a1"]
    state.objectives.stage2_deck = ["b1"]
    out = _resolve(registry, state, "against")
    assert out.objectives.revealed == ["b1"] and out.objectives.stage1_deck == ["a1"]


def test_classified_document_leaks(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["classified"])
    state.players["p1"].scored_secrets = ["dp"]
    out = _resolve(registry, state, "dp")
    assert "dp" in out.objectives.revealed and out.players["p1"].scored_secrets == []
    assert out.objectives.scored["dp"] == ["p1"]  # pierwotny właściciel nie zdobędzie go ponownie


def test_classified_without_scored_secrets_is_replaced(registry: StaticDataRegistry) -> None:
    out = agenda_phase.reveal_agenda(
        _state(registry, ["classified", "mutiny"]), registry, "p2"
    )
    assert out.agenda is not None and out.agenda.agenda_id == "mutiny"


def test_grant_reallocation_asks_the_elected_player(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["grant_reallocation"])
    out = _resolve(registry, state, "p1")
    offers = [o for o in out.pending_offers if o.player_id == "p1"]
    assert offers and offers[0].mandatory
    with pytest.raises(ValueError, match="decisions"):
        agenda_phase.continue_agenda(out, registry, "p2")


def test_grant_reallocation_okno_drzewa_bez_prerekwizytow(registry: StaticDataRegistry) -> None:
    """Decyzja = pełne okno drzewa technologii (nie lista): każda nieposiadana dostępna,
    na kaflu koszt w żetonach floty = liczba prerekwizytów (C_agendas)."""
    from src.core import technology

    state = _state(registry, ["grant_reallocation"])
    state.players["p1"].fleet_cc = 3
    out = _resolve(registry, state, "p1")
    offer = next(o for o in out.pending_offers if o.player_id == "p1")
    (field,) = offers.offer_view(out, registry, offer)["inputs"]
    assert field["kind"] == "research" and field["key"] == "research"
    view = field["research"]
    assert view["gain"]["mandatory"] and view["gain"]["tokens"] == 3
    rows = {r["id"]: r for r in view["tree"]}
    assert all(r["status"] in {"available", "owned", "exhausted"} for r in rows.values())
    hard = next(
        t for t in technology.tech_pool(out, registry, "p1").values()
        if sum(technology.prerequisites(t).values()) == 3
    )
    assert rows[hard.id]["tokenCost"] == 3
    # Zdobycie z 3 prerekwizytami przy 3 żetonach floty: pula floty pusta.
    done = triggers.accept_offer(out, "p1", offer.id, {"research": {"tech": hard.id}})
    assert hard.id in done.players["p1"].technologies
    assert done.players["p1"].fleet_cc == 0


def test_grant_reallocation_bez_wyboru_odrzucone(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["grant_reallocation"])
    out = _resolve(registry, state, "p1")
    offer = next(o for o in out.pending_offers if o.player_id == "p1")
    with pytest.raises(ValueError):
        triggers.accept_offer(out, "p1", offer.id, {"research": {"tech": None}})


def test_galactic_crisis_pact_opens_free_secondary(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["crisis"])
    out = _resolve(registry, state, "3")
    window = out.pending_window
    assert window is not None and window.window_type is WindowType.STRATEGY_SECONDARY
    assert window.queue == ["p2", "p3", "p1"] and window.context["initiative"] == 3


# --- Prawa -------------------------------------------------------------------------------


def test_political_censure_vp_and_action_card_ban(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["censure"])
    out = _resolve(registry, state, "p1")
    assert out.players["p1"].victory_points == 1
    assert action_cards.forbidden_reason(out, "p1") is not None
    assert action_cards.forbidden_reason(out, "p2") is None
    agenda_phase.remove_law(out, "censure")
    assert out.players["p1"].victory_points == 0


def test_representative_government_single_vote(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["mutiny"])
    state.decks.agenda_laws = {"rep_govt": "for"}
    st = agenda_phase.reveal_agenda(state, registry, "p2")
    with pytest.raises(ValueError, match="Representative Government"):
        agenda_phase.cast_vote(st, registry, "p3", "for", [_planet(st, "p3")])
    st = agenda_phase.cast_vote(st, registry, "p3", "for", [])
    assert st.agenda is not None and st.agenda.votes["p3"].votes == 1


def test_executive_sanctions(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["sanctions"])
    state.players["p1"].private.action_cards = ["a", "b", "c", "d"]
    out = _resolve(registry, state, "for")
    assert hand_limit.action_card_limit(out, "p1") == 3
    assert hand_limit.action_card_excess(out, "p1") == 1
    state = _state(registry, ["sanctions"])
    state.players["p1"].private.action_cards = ["a", "b"]
    out = _resolve(registry, state, "against")
    assert len(out.players["p1"].private.action_cards) == 1


def test_fleet_regulations_cap(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["regulations"])
    state.players["p1"].fleet_cc = 6
    out = _resolve(registry, state, "for")
    assert command_tokens.pool_count(out, "p1", "fleet") == 4
    with pytest.raises(ValueError, match="Fleet Regulations"):
        command_tokens.gain_from_reinforcements(out, "p1", {"fleet": 1})


def test_checks_and_balances_against_limits_ready(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["checks", "economic_equality"])
    extra = [p for p in sorted(registry.planets) if p not in state.systems["101"].planet_owners]
    state.systems["102"] = SystemState(
        position="102", system_id="2", planet_owners={p: "p1" for p in extra[:4]}
    )
    out = _resolve(registry, state, "against")
    out.players["p1"].exhausted_planets = [*extra[:4], _planet(out, "p1")]
    out = agenda_phase.continue_agenda(out, registry, "p2")
    out = _resolve(registry, out, "for")
    out = agenda_phase.continue_agenda(out, registry, "p2")
    assert len(out.players["p1"].exhausted_planets) == 5  # czeka na wybór 3 planet
    offer = next(o for o in out.pending_offers if o.player_id == "p1")
    picks = extra[:3]
    out = triggers.accept_offer(out, "p1", offer.id, {"planets": picks})
    assert sorted(out.players["p1"].exhausted_planets) == sorted([extra[3], _planet(out, "p1")])


def test_checks_and_balances_for_gives_cards(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["checks"])
    out = _resolve(registry, state, "for")
    out.phase = Phase.STRATEGY
    out.agenda = None
    with pytest.raises(ValueError, match="Checks and Balances"):
        strategy_phase.pick_strategy_card(out, registry, "p2", 1)
    out = strategy_phase.pick_strategy_card(out, registry, "p2", 1, recipient="p3")
    assert out.players["p3"].strategy_cards == [1] and out.players["p2"].strategy_cards == []
    assert strategy_phase.next_strategy_picker(out) == "p3"


def test_regulated_conscription(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    assert production.dual_production(state, "p1")
    state.decks.agenda_laws = {"conscription": "for"}
    assert not production.dual_production(state, "p1")


def test_homeland_defense_act_lifts_pds_limit(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    planet = _planet(state, "p1")
    state.systems["101"].planet_units = {planet: {"p1": {"pds": 2}}}
    assert structure_problem(state, "p1", planet, "pds") is not None
    state.decks.agenda_laws = {"defense_act": "for"}
    assert structure_problem(state, "p1", planet, "pds") is None


def test_articles_of_war_strips_mech_abilities(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    assert not rules_hooks.unit_abilities_lost(state, "p1", "mech")
    state.decks.agenda_laws = {"articles_war": "for"}
    assert rules_hooks.unit_abilities_lost(state, "p1", "mech")


def test_minister_of_sciences_and_prophecy(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    state.decks.agenda_laws = {"minister_sciences": "p1", "prophecy": "p2"}
    assert rules_hooks.permits(rules_hooks.POINT_TECHNOLOGY_SC_FREE, state, "p1")
    assert not rules_hooks.permits(rules_hooks.POINT_TECHNOLOGY_SC_FREE, state, "p2")
    ctx = {"base_type": "fighter"}
    assert rules_hooks.modify(rules_hooks.POINT_COMBAT_ROLL_MODIFIER, state, "p2", 0, ctx) == 1
    assert rules_hooks.modify(rules_hooks.POINT_COMBAT_ROLL_MODIFIER, state, "p1", 0, ctx) == 0


def test_committee_formation_elects_without_vote(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["secret"])
    state.decks.agenda_laws = {"committee": "p1"}
    st = agenda_phase.reveal_agenda(state, registry, "p2")
    offer = next(o for o in st.pending_offers if o.player_id == "p1")
    with pytest.raises(ValueError, match="Waiting for"):
        agenda_phase.abstain(st, registry, "p3")
    st = triggers.accept_offer(st, "p1", offer.id, {"player": "p3"})
    assert st.agenda is not None and st.agenda.resolved_outcome == "p3"
    assert "committee" not in st.decks.agenda_laws


def test_riders_resolve_after_agenda_effect(registry: StaticDataRegistry) -> None:
    state = _state(registry, ["economic_equality"])
    state.players["p1"].private.action_cards = ["trade_rider"]
    st = agenda_phase.reveal_agenda(state, registry, "p2")
    st, _impl = action_cards.play_action_card(st, registry, "p1", "trade_rider", {"outcome": "for"})
    for _ in range(3):
        voter = agenda_phase.current_voter(st)
        if voter is None:
            break
        st = agenda_phase.abstain(st, registry, voter)
    st = agenda_phase.decide_tie(st, registry, "p2", "for")
    if st.agenda is not None and st.agenda.step is AgendaStep.COUNTED:
        st = agenda_phase.confirm_outcome(st, registry, "p2")
    # Economic Equality: wszyscy po 5 TG, potem rider: +5 TG (po efekcie agendy).
    assert st.players["p1"].trade_goods == 10
    assert st.players["p2"].trade_goods == 5


def test_vote_record_helper(registry: StaticDataRegistry) -> None:
    state = _state(registry, [])
    state.agenda = AgendaPhaseState(
        vote_order=["p3", "p1", "p2"],
        votes={"p1": AgendaVote(outcome="for", votes=2), "p3": AgendaVote(outcome="for", votes=1)},
    )
    assert agenda_phase.voters_for(state, "for") == ["p3", "p1"]


# --- Web: jawność riderów, Covert, Search Warrant -------------------------------------------


def test_payload_shows_what_each_rider_was_played_on(registry: StaticDataRegistry) -> None:
    from src.api import web_agenda

    state = _state(registry, ["mutiny"])
    state.players["p1"].private.action_cards = ["trade_rider"]
    st = agenda_phase.reveal_agenda(state, registry, "p2")
    st, _impl = action_cards.play_action_card(st, registry, "p1", "trade_rider", {"outcome": "for"})
    payload = web_agenda.build_agenda_payload(st, registry)
    assert payload is not None
    assert payload["predictions"] == [
        {"playerId": "p1", "card": "trade_rider", "cardName": "Trade Rider",
         "outcome": "for", "outcomeLabel": "For"}
    ]


def test_covert_card_only_for_speaker(registry: StaticDataRegistry) -> None:
    from src.api import web_agenda

    st = agenda_phase.reveal_agenda(_state(registry, ["covert", "conscription"]), registry, "p2")
    shown = web_agenda.covert_for_viewer(st, registry, "p2")
    assert shown is not None and shown["id"] == "conscription"
    assert web_agenda.covert_for_viewer(st, registry, "p1") is None
    payload = web_agenda.build_agenda_payload(st, registry)
    assert payload is not None and payload["covert"] is True
    assert "conscription" not in str(payload["card"])


def test_search_warrant_reveals_secrets(registry: StaticDataRegistry) -> None:
    from src.api import web_agenda

    state = _state(registry, [])
    state.players["p1"].private.secret_objectives = ["dp"]
    assert web_agenda.revealed_secrets(state) == {}
    state.decks.agenda_laws = {"warrant": "p1"}
    assert web_agenda.revealed_secrets(state) == {"p1": ["dp"]}
    players = web_agenda.with_revealed_secrets([{"discordId": "p1"}, {"discordId": "p2"}], state)
    assert players[0]["knownUnscoredSecrets"] == {"dp": 1}
    assert "knownUnscoredSecrets" not in players[1]


def test_imperial_arbiter_opcje_z_pelnymi_nazwami_kart(registry: StaticDataRegistry) -> None:
    """Wybór zamiany kart strategii pokazuje nazwy kart, nie same numery inicjatywy."""
    from src.core.hooks import agendas_laws

    state = _state(registry, [])
    state.players["p1"].strategy_cards = [3]
    state.players["p2"].strategy_cards = [5]
    (field,) = agendas_laws._arbiter_inputs(state, registry, "p1", {})
    names = {sc.initiative: sc.name for sc in registry.strategy_card_set()}
    (option,) = field["options"]
    assert option["value"] == "3|p2|5"
    assert names[3] in option["label"] and names[5] in option["label"]
