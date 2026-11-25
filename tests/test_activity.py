"""Testy feedu aktywności (``core.activity``) i endpointu ``/history/activity``."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.activity import derive_activity
from src.core.event_store import EventStore
from src.core.game_state import (
    GameState,
    MoveCargo,
    MoveLoss,
    MoveRecord,
    Phase,
    PlayerState,
    SystemState,
)
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


def test_skip_player_shows_turn_handover() -> None:
    """God-Mode „Skip player": w feedzie jak zwykłe przekazanie tury."""
    after = _state()
    after.active_player_id = "p2"
    entry = derive_activity("turn:skip-player", _state(), after)
    assert entry is not None
    assert (entry.action, entry.actor_id, entry.target_id) == ("turn.next", "p1", "p2")


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


def test_return_own_captured_units_in_feed() -> None:
    entry = derive_activity("captured:return-own:p1:1 Cruiser (Arborec)", _state(), _state())
    assert entry is not None and entry.kind == "economy"
    assert entry.action == "capture.return_own" and entry.actor_id == "p1"
    assert entry.detail == "1 Cruiser (Arborec)"


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


def test_stol_transakcji_w_feedzie() -> None:
    """RULES.md 47.1b: usiadł / umowa / wstał w feedzie; kładzenie rzeczy i Ready - nie."""
    opened = derive_activity("transaction-table:opened:p2:p1", _state(), _state())
    assert opened is not None
    assert (opened.action, opened.actor_id, opened.target_id) == (
        "transaction.opened", "p2", "p1"
    )
    agreed = derive_activity("transaction-table:agreed:p1:p2", _state(), _state())
    assert agreed is not None and agreed.action == "transaction.agreed"
    closed = derive_activity("transaction-table:closed:p1:p2", _state(), _state())
    assert closed is not None and closed.action == "transaction.closed"
    assert derive_activity("transaction-table:side:p1:p2", _state(), _state()) is None


def test_transakcja_w_agendzie_aktor_z_etykiety() -> None:
    """RULES.md 47.5: w agendzie stroną nie jest aktywny - aktor z etykiety commitu."""
    entry = derive_activity("transaction:p1:p3", _state(), _state())
    assert entry is not None
    assert (entry.action, entry.actor_id, entry.target_id) == ("transaction", "p3", "p1")


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


def test_rider_pokazuje_przewidziany_wynik() -> None:
    """RULES.md 51.6: zagrany rider jest jawny - feed mówi, NA JAKI wynik go zagrano."""
    from src.core.game_state import ActiveEffect

    before = _state()
    before.phase = Phase.AGENDA
    before.players["p1"].private.action_cards = ["trade_rider"]
    after = _state()
    after.phase = Phase.AGENDA
    after.decks.action_card_discard = ["trade_rider"]
    after.active_effects = [
        ActiveEffect(id="fx1", key="action_cards:trade_rider", scope="agenda", owner="p1",
                     data={"outcome": "for"})
    ]
    entry = derive_activity("action-card:play:trade_rider", before, after)
    assert entry is not None
    riders = [(f.player_id, f.value, f.detail) for f in entry.facts if f.type == "rider"]
    assert riders == [("p1", "trade_rider", "for")]


def test_wejscie_fracture_jako_fakt() -> None:
    """RULES.md 64: wejście The Fracture do gry to fakt feedu (kluczowy moment dla wszystkich)."""
    before = _state()
    after = _state()
    after.fracture.in_play = True
    after.fracture.entered_by = "p2"
    entry = derive_activity("expedition:breakthrough:p2", before, after)
    assert entry is not None
    assert ("fracture_entered", "p2") in {(f.type, f.player_id) for f in entry.facts}
    # Fracture już w grze -> brak ponownego faktu.
    again = derive_activity("expedition:breakthrough:p2", after, after.model_copy(deep=True))
    assert again is None or all(f.type != "fracture_entered" for f in again.facts)


def test_component_use_by_non_active_player() -> None:
    """Quash / Instinct Training używa gracz nieaktywny: aktorem jest on (RULES.md 62.9)."""
    before = _state()
    after = _state()
    entry = derive_activity("component-use:ability:quash:p2", before, after)
    assert entry is not None and entry.actor_id == "p2"


def test_bohater_dolaczony_do_planety_ma_sprawce_i_fakt_attached() -> None:
    """Geoform (Ul the Progenitor) nie purge'uje karty - scena bohatera (RULES.md 64) startuje
    z faktu ``attached`` i sprawcy wpisu."""
    before = _state()
    after = _state()
    after.planet_attachments["elysium"] = ["titanshero"]
    entry = derive_activity("component-use:leader:titanshero", before, after)
    assert entry is not None
    assert entry.actor_id == "p1"
    facts = {(f.type, f.value, f.detail) for f in entry.facts}
    assert ("attached", "titanshero", "elysium") in facts


def _system(position: str, **kw: object) -> SystemState:
    return SystemState(position=position, system_id="2" + position[-1], **kw)  # type: ignore[arg-type]


def test_obszar_bohatera_zetony_i_jednostki() -> None:
    """Użycie bohatera dopisuje fakty ``area`` (miejsce efektu na planszy, RULES.md 64.4)."""
    before = _state()
    before.players["p1"].leader_states["solhero"] = "unlocked"
    before.systems["101"] = _system("101", command_tokens=["p1"])
    before.systems["102"] = _system("102", space_units={"p2": {"fighter": 2}})
    after = _state()
    after.players["p1"].leader_states["solhero"] = "purged"
    after.systems["101"] = _system("101")
    after.systems["102"] = _system("102", space_units={"p1": {"dreadnought": 1}})
    entry = derive_activity("component-use:leader:solhero:p1", before, after)
    assert entry is not None
    areas = {(f.player_id, f.value, f.detail) for f in entry.facts if f.type == "area"}
    assert areas == {("p1", "101", "token_removed"), ("p2", "102", "loss"), ("p1", "102", "gain")}


def test_bez_bohatera_brak_faktow_obszaru() -> None:
    before = _state()
    before.systems["102"] = _system("102")
    after = _state()
    after.systems["102"] = _system("102", space_units={"p1": {"dreadnought": 1}})
    entry = derive_activity("tactical:produce", before, after)
    assert entry is None or not [f for f in entry.facts if f.type == "area"]


def test_ruch_floty_i_desant_maja_cel_i_liczby() -> None:
    """Ruch i desant nie zmieniają sum jednostek — osobne fakty ``moved`` i ``landed``."""
    before = _state()
    after = _state()
    def system(pos: str, cruisers: int = 0) -> SystemState:
        units = {"p1": {"cruiser": cruisers}} if cruisers else {}
        return SystemState(position=pos, system_id="27", space_units=units)

    before.systems["101"], before.systems["102"] = system("101", 2), system("102")
    after.systems["101"], after.systems["102"] = system("101", 1), system("102", 1)
    after.active_system = "102"
    move = derive_activity("tactical:move:101", before, after)
    assert move is not None
    assert [(f.type, f.value, f.delta, f.detail) for f in move.facts if f.type == "moved"] == [
        ("moved", "cruiser", 1, "102")
    ]

    land_before = _state()
    land_after = _state()
    land_after.active_system = "102"
    land_before.systems["102"] = SystemState(position="102", system_id="28")
    land_after.systems["102"] = SystemState(
        position="102", system_id="28", planet_units={"lodor": {"p1": {"infantry": 3}}}
    )
    land = derive_activity("invasion:commit", land_before, land_after)
    assert land is not None
    assert [(f.value, f.delta, f.detail) for f in land.facts if f.type == "landed"] == [
        ("infantry", 3, "lodor")
    ]


def test_ruch_floty_niesie_trase_i_ladunek_do_odtworzenia_lotu() -> None:
    """``tactical.move`` carries the route (``move_route``) and cargo (``carried``) of the move,
    so every client can replay the physical flight; another player's stale record is ignored."""
    before = _state()
    after = _state()
    before.systems["202"] = SystemState(
        position="202", system_id="27", space_units={"p1": {"carrier": 1, "infantry": 2}}
    )
    after.systems["202"] = SystemState(position="202", system_id="27")
    after.systems["000"] = SystemState(
        position="000", system_id="18", space_units={"p1": {"carrier": 1, "infantry": 2}}
    )
    after.active_system = "000"
    after.last_move = MoveRecord(
        player_id="p1", route=["202", "101", "000"], hops=["lane", "wormhole"],
        anomalies={"101": ["GRAVITY_RIFT"]}, ships={"carrier": 1},
        cargo=[MoveCargo(base_type="infantry", count=2, from_position="202")],
    )
    entry = derive_activity("tactical:move:202", before, after)
    assert entry is not None
    route = [f for f in entry.facts if f.type == "move_route"]
    assert [(f.player_id, f.route, f.hops, f.anomalies) for f in route] == [
        ("p1", ["202", "101", "000"], ["lane", "wormhole"], {"101": ["GRAVITY_RIFT"]})
    ]
    assert [(f.value, f.delta, f.detail) for f in entry.facts if f.type == "carried"] == [
        ("infantry", 2, "space")
    ]

    after.last_move = after.last_move.model_copy(update={"player_id": "p2"})
    other = derive_activity("tactical:move:202", before, after)
    assert other is not None
    assert not [f for f in other.facts if f.type in ("move_route", "carried")]


def test_ruch_floty_niesie_straty_w_gravity_rift() -> None:
    """Ships (and their cargo) a gravity rift removed on the move become ``rift_lost`` facts
    naming the rift system, so clients replay them being swallowed there."""
    before = _state()
    after = _state()
    before.systems["202"] = SystemState(
        position="202", system_id="27", space_units={"p1": {"carrier": 2, "fighter": 1}}
    )
    after.systems["202"] = SystemState(position="202", system_id="27")
    after.systems["000"] = SystemState(
        position="000", system_id="18", space_units={"p1": {"carrier": 1}}
    )
    after.active_system = "000"
    after.last_move = MoveRecord(
        player_id="p1", route=["202", "101", "000"], hops=["lane", "lane"],
        anomalies={"101": ["GRAVITY_RIFT"]}, ships={"carrier": 1},
        lost=[
            MoveLoss(base_type="carrier", count=1, at="101"),
            MoveLoss(base_type="fighter", count=1, at="101"),
        ],
    )
    entry = derive_activity("tactical:move:202", before, after)
    assert entry is not None
    assert [(f.value, f.delta, f.detail) for f in entry.facts if f.type == "rift_lost"] == [
        ("carrier", 1, "101"),
        ("fighter", 1, "101"),
    ]


def test_ruch_floty_niesie_uzycie_gravity_drive() -> None:
    """A ship type that spent Gravity Drive on the move becomes a ``gravity_drive`` fact, so
    clients replay the ship with its gravity field."""
    before = _state()
    after = _state()
    before.systems["202"] = SystemState(
        position="202", system_id="27", space_units={"p1": {"cruiser": 1}}
    )
    after.systems["202"] = SystemState(position="202", system_id="27")
    after.systems["000"] = SystemState(
        position="000", system_id="18", space_units={"p1": {"cruiser": 1}}
    )
    after.active_system = "000"
    after.last_move = MoveRecord(
        player_id="p1", route=["202", "101", "000"], hops=["lane", "lane"],
        ships={"cruiser": 1}, boosted=["cruiser"],
    )
    entry = derive_activity("tactical:move:202", before, after)
    assert entry is not None
    assert [(f.player_id, f.value) for f in entry.facts if f.type == "gravity_drive"] == [
        ("p1", "cruiser")
    ]


def test_strzal_space_cannon_niesie_grupy_rzutow_do_odtworzenia() -> None:
    """``spacecannon.fire`` carries one ``cannon_shot`` per roll group (shooter system and zone,
    target player, hits) so every client can replay the volley; a pass carries none."""
    import json

    before = _state()
    after = _state()
    after.active_system = "000"
    entry_log = {
        "roller": "p1", "target": "p2", "hits": 2, "passed": False, "destroyed": {},
        "rolls": [
            {"baseType": "pds", "zone": "lodor", "position": "000", "hits": 2, "dice": [9, 10]},
            {"baseType": "pds", "zone": "space", "position": "101", "hits": 0, "dice": [3]},
        ],
    }
    after.space_cannon_log = json.dumps([entry_log])
    fired = derive_activity("space-cannon:fire:p1", before, after)
    assert fired is not None
    shots = [f for f in fired.facts if f.type == "cannon_shot"]
    assert [(f.player_id, f.value, f.detail, f.delta, f.dice, f.route) for f in shots] == [
        ("p1", "p2", "lodor", 2, 2, ["000", "000"]),
        ("p1", "p2", "space", 0, 1, ["101", "000"]),
    ]

    after.space_cannon_log = json.dumps([{**entry_log, "passed": True}])
    passed = derive_activity("space-cannon:fire:p1", before, after)
    assert passed is not None
    assert not [f for f in passed.facts if f.type == "cannon_shot"]
