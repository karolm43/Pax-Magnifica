"""Testy feedu aktywności (``core.activity``) i endpointu ``/history/activity``."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.activity import derive_activity
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState
from src.core.registry import StaticDataRegistry


def _state() -> GameState:
    return GameState(
        round_number=2,
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", faction="arborec", color="green"),
            "p2": PlayerState(player_id="p2", faction="sol", color="blue"),
        },
    )


def test_strategy_pick_names_actor_and_card() -> None:
    after = _state()
    entry = derive_activity("strategy:pick:p2:3", _state(), after)
    assert entry is not None
    assert (entry.kind, entry.action) == ("strategy", "strategy.pick")
    assert entry.actor_id == "p2"
    assert entry.subject == "3"


def test_turn_pass_actor_is_previous_active_player() -> None:
    before = _state()
    after = _state()
    after.active_player_id = "p2"
    entry = derive_activity("turn:pass", before, after)
    assert entry is not None
    assert entry.actor_id == "p1"
    assert entry.target_id == "p2"


def test_internal_step_without_effect_is_hidden() -> None:
    assert derive_activity("tactical:step", _state(), _state()) is None


def test_internal_step_with_effect_surfaces_facts() -> None:
    before = _state()
    after = _state()
    after.players["p1"].technologies = ["neural_motivator"]
    entry = derive_activity("strategy:primary-step:p1", before, after)
    assert entry is not None
    assert entry.kind == "misc"
    assert [(f.type, f.player_id, f.value) for f in entry.facts] == [
        ("tech", "p1", "neural_motivator")
    ]


def test_tech_lost_fact_when_technology_returned() -> None:
    before = _state()
    before.players["p1"].technologies = ["neural_motivator"]
    after = _state()
    after.players["p1"].technologies = ["hyper_metabolism"]
    entry = derive_activity("component-use:leader:jolnarhero", before, after)
    assert entry is not None
    facts = {(f.type, f.value) for f in entry.facts}
    assert ("tech", "hyper_metabolism") in facts
    assert ("tech_lost", "neural_motivator") in facts


def test_ability_note_becomes_fact() -> None:
    from src.core import ability_notes

    before = _state()
    after = _state()
    ability_notes.note(after, "p1", "abilities:analytical", "ignored 1 prerequisite(s) of X")
    entry = derive_activity("strategy:secondary:p1", before, after)
    assert entry is not None
    assert ("ability_used", "p1", "abilities:analytical") in {
        (f.type, f.player_id, f.value) for f in entry.facts
    }


def test_pillage_widoczny_w_feedzie() -> None:
    """Pillage (RULES.md 62.8): fakt ``ability_used`` z celem i przepływ TG obu graczy."""
    from src.core.game_state import SystemState
    from src.core.hooks.factions import mentak

    StaticDataRegistry()  # wiąże rejestr dla hooków (nazwa frakcji w opisie)
    before = _state()
    before.players["p1"].faction = "mentak"
    before.players["p2"].trade_goods = 3
    before.systems = {
        "000": SystemState(position="000", system_id="18", space_units={"p1": {"cruiser": 1}}),
        "101": SystemState(position="101", system_id="20", space_units={"p2": {"cruiser": 1}}),
    }
    after = before.clone()
    mentak.pillage_on_gain(after, "p1", {"player": "p2", "params": {"take": "trade_good"}})
    entry = derive_activity("offer:accept:of1", before, after)
    assert entry is not None
    facts = {(f.type, f.player_id, f.value, f.detail, f.delta) for f in entry.facts}
    pillage = ("ability_used", "p1", "abilities:pillage", "against The Federation of Sol", None)
    assert pillage in facts
    assert ("tg", "p2", None, None, -1) in facts
    assert ("tg", "p1", None, None, 1) in facts

def test_vp_and_planet_facts_from_diff() -> None:
    before = _state()
    after = _state()
    after.players["p1"].victory_points = 1
    after.players["p1"].controlled_planets = ["jord"]
    entry = derive_activity("status:score:x", before, after)
    assert entry is not None
    types = {(f.type, f.value, f.delta) for f in entry.facts}
    assert ("vp", None, 1) in types
    assert ("planet_gained", "jord", None) in types


def test_godmode_without_effect_is_hidden() -> None:
    assert derive_activity("god-mode-patch", _state(), _state()) is None


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


@pytest.fixture
def client(registry: StaticDataRegistry) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=_state())
    return TestClient(app)


def test_activity_endpoint_lists_players_and_entries(client: TestClient) -> None:
    client.post("/turn/pass")
    data = client.get("/history/activity").json()
    assert data["players"]["p1"]["faction"] == "arborec"
    actions = [e["activity"]["action"] for e in data["entries"]]
    assert "turn.pass" in actions
    assert all(e["created_at"] is not None for e in data["entries"])


def test_played_action_card_is_public_but_hand_stays_hidden() -> None:
    before = _state()
    before.players["p1"].private.action_cards = ["sabotage", "secret_card"]
    after = _state()
    after.players["p1"].private.action_cards = ["secret_card"]
    after.decks.action_card_discard = ["sabotage"]
    entry = derive_activity("component-action:other", before, after)
    assert entry is not None
    played = [f for f in entry.facts if f.type == "action_card"]
    assert [(f.player_id, f.value) for f in played] == [("p1", "sabotage")]
    assert "secret_card" not in entry.model_dump_json()


def test_discarded_action_card_is_not_shown_as_played() -> None:
    """Odrzucenie do limitu ręki (RULES.md 53.8) to „discarded”, nie „played”."""
    from src.core import card_draw

    before = _state()
    before.players["p1"].private.action_cards = ["sabotage", "secret_card"]
    after = before.clone()
    card_draw.discard_chosen_action_cards(after, "p1", ["sabotage"])
    entry = derive_activity("action-card:discard-excess:sabotage", before, after)
    assert entry is not None
    facts = [(f.type, f.player_id, f.value) for f in entry.facts if "action_card" in f.type]
    assert facts == [("action_card_discarded", "p1", "sabotage")]


def test_revealed_exploration_card_is_listed() -> None:
    from src.core.game_state import ExplorationState, ExploreCurrent

    before = _state()
    after = _state()
    after.exploration = ExplorationState(
        player_id="p1",
        position="101",
        current=ExploreCurrent(planet="jord", deck="cultural", card_id="cultural_card"),
    )
    entry = derive_activity("exploration:draw:jord", before, after)
    assert entry is not None
    fact = next(f for f in entry.facts if f.type == "explore_card")
    assert (fact.value, fact.detail, fact.player_id) == ("cultural_card", "cultural", "p1")


def test_explore_resolve_names_card_and_summary() -> None:
    from src.core.game_state import ExplorationState

    before = _state()
    after = _state()
    after.exploration = ExplorationState(
        player_id="p1",
        position="101",
        log=[{"cardId": "c1", "summary": "Gained 1 TG.", "fate": "discarded"}],
    )
    entry = derive_activity("exploration:resolve:x", before, after)
    assert entry is not None
    assert (entry.subject, entry.detail, entry.actor_id) == ("c1", "Gained 1 TG.", "p1")


def test_resource_unit_and_table_facts_from_diff() -> None:
    from src.core.game_state import SystemState

    before = _state()
    after = _state()
    before.systems["101"] = SystemState(position="101", system_id="27")
    after.systems["101"] = SystemState(
        position="101", system_id="27", space_units={"p1": {"cruiser": 2}}, command_tokens=["p1"]
    )
    after.players["p1"].commodities = 2
    after.players["p1"].tactical_cc = 2
    after.players["p1"].relics = ["the_crown_of_emphidia"]
    after.players["p1"].private.action_cards = ["a", "b"]
    after.decks.agenda_laws["minister_of_policy"] = "p2"

    entry = derive_activity("tactical:produce:101", before, after)
    assert entry is not None
    got = {(f.type, f.player_id, f.value, f.delta) for f in entry.facts}
    assert ("units", "p1", "cruiser", 2) in got
    assert ("commodities", "p1", None, 2) in got
    assert ("cc", "p1", "tactical_cc", -1) in got
    assert ("hand", "p1", "action_cards", 2) in got
    assert ("system_token", "p1", "101", None) in got
    assert ("relic", "p1", "the_crown_of_emphidia", None) in got
    assert ("law_enacted", None, "minister_of_policy", None) in got


def test_uzycie_lidera_i_purge_w_feedzie() -> None:
    """RULES.md 61.3: użycie komponentu frakcji + zmiana stanu lidera (purge) jako fakt."""
    before = _state()
    after = _state()
    after.players["p1"].leader_states = {"arborechero": "purged"}
    entry = derive_activity("component-use:leader:arborechero", before, after)
    assert entry is not None
    assert entry.action == "component.use"
    assert entry.subject == "arborechero" and entry.detail == "leader"
    facts = [(f.type, f.value, f.detail) for f in entry.facts]
    assert ("leader", "arborechero", "purged") in facts


def test_zagrana_notka_w_feedzie() -> None:
    """RULES.md 61.2: zagrana notka jest jawna (aktor = grający, nie aktywny gracz)."""
    entry = derive_activity("promissory:p2:green_cf", _state(), _state())
    assert entry is not None
    assert entry.action == "promissory.play"
    assert entry.actor_id == "p2" and entry.subject == "green_cf"


def test_propozycja_i_odrzucenie_transakcji_w_feedzie() -> None:
    """RULES.md 47.1a: propozycja (aktor = aktywny) i odrzucenie (aktor = partner)."""
    proposed = derive_activity("transaction-offer:proposed:p2", _state(), _state())
    assert proposed is not None
    assert (proposed.action, proposed.actor_id, proposed.target_id) == (
        "transaction.proposed", "p1", "p2"
    )
    declined = derive_activity("transaction-offer:declined:p2", _state(), _state())
    assert declined is not None
    assert (declined.action, declined.actor_id, declined.target_id) == (
        "transaction.declined", "p2", "p1"
    )


def _battle_states() -> tuple[GameState, GameState]:
    """Walka kosmiczna p1 vs p2 w systemie 101: przed przypisaniem strat p2 i po nim."""
    from src.core.game_state import ActiveCombat, SystemState

    before = _state()
    before.systems["101"] = SystemState(
        position="101", system_id="27",
        space_units={"p1": {"cruiser": 2}, "p2": {"destroyer": 2}},
    )
    before.active_combat = ActiveCombat(
        kind="space", position="101", attacker="p1", defender="p2", round=2
    )
    after = before.clone()
    after.systems["101"].space_units["p2"] = {"destroyer": 1}
    return before, after


def test_straty_w_rundzie_walki_maja_nazwe_bitwy() -> None:
    before, after = _battle_states()
    entry = derive_activity("battle:assign:p2", before, after)
    assert entry is not None
    assert (entry.kind, entry.action) == ("combat", "combat.losses")
    assert (entry.actor_id, entry.target_id) == ("p2", "p1")
    assert (entry.subject, entry.detail) == ("space", "101")
    assert ("units", "p2", "destroyer", -1) in {
        (f.type, f.player_id, f.value, f.delta) for f in entry.facts
    }


def test_rzut_bez_skutku_nie_trafia_do_feedu() -> None:
    before, _ = _battle_states()
    assert derive_activity("battle:roll", before, before.clone()) is None


def test_zamkniecie_walki_daje_podsumowanie() -> None:
    before, _ = _battle_states()
    assert before.active_combat is not None
    before.active_combat.log = [
        {"round": 1, "phase": "COMBAT", "losses": {"p2": {"destroyer": 1}}},
        {"round": 2, "phase": "COMBAT", "losses": {"p1": {"cruiser": 1}, "p2": {"destroyer": 1}}},
    ]
    before.active_combat.winner = "p1"
    before.active_combat.outcome = "winner"
    after = before.clone()
    after.active_combat = None
    entry = derive_activity("battle:close", before, after)
    assert entry is not None
    assert entry.action == "combat.end"
    assert (entry.subject, entry.detail) == ("space", "101")
    got = {(f.type, f.player_id, f.value, f.delta, f.detail) for f in entry.facts}
    assert ("battle_result", "p1", None, 2, "winner") in got
    assert ("units", "p2", "destroyer", -2, None) in got
    assert ("units", "p1", "cruiser", -1, None) in got
