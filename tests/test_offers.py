"""Testy decyzji graczy: oferty technologii (RULES.md 56) - silnik nigdy nie wybiera za gracza."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import battle, damage, offers, triggers
from src.core.event_store import EventStore
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    CombatStep,
    GameState,
    PendingOffer,
    Phase,
    PlayerState,
    SystemState,
    TacticalStep,
    WindowType,
)
from src.core.registry import StaticDataRegistry
from tests.test_battle import _grid as battle_grid
from tests.test_battle import _state as battle_state


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _tech(state: GameState, player_id: str, *techs: str) -> GameState:
    state.players[player_id].technologies = list(techs)
    return state


def _only_offer(state: GameState) -> PendingOffer:
    assert len(state.pending_offers) == 1
    return state.pending_offers[0]


# --- Duranium Armor: wybór naprawianej jednostki ------------------------------------------


def _da_state() -> GameState:
    state = _tech(
        battle_state({"p1": {"dreadnought": 1, "cruiser": 1}, "p2": {"cruiser": 1}}), "p1", "da"
    )
    system = state.systems["000"]
    damage.set_damaged(system, "space", "p1", "dreadnought", 1)
    damage.set_damaged(system, "space", "p1", "cruiser", 1)
    return state


def _round_end(state: GameState) -> None:
    triggers.fire(
        state, GameEvent.COMBAT_ROUND, Moment.END,
        ctx={"kind": "space", "round": 1, "position": "000", "planet": "",
             "attacker": "p1", "defender": "p2", "phase": "combat", "sustained": {}},
    )


def test_duranium_armor_przy_dwoch_typach_pyta_gracza_i_niczego_nie_naprawia_sam() -> None:
    state = _da_state()
    _round_end(state)
    offer = _only_offer(state)
    assert offer.mandatory and offer.player_id == "p1"
    system = state.systems["000"]
    assert damage.damaged_count(system, "space", "p1", "dreadnought") == 1
    assert damage.damaged_count(system, "space", "p1", "cruiser") == 1
    assert state.pending_window is not None
    assert state.pending_window.window_type is WindowType.REACTION


def test_duranium_armor_odpowiedz_gracza_naprawia_wybrana_jednostke(
    registry: StaticDataRegistry,
) -> None:
    state = _da_state()
    _round_end(state)
    offer = _only_offer(state)
    view = offers.offer_view(state, registry, offer)
    assert view["name"] == "Duranium Armor" and view["mandatory"]
    values = {o["value"] for o in view["inputs"][0]["options"]}
    assert values == {"dreadnought", "cruiser"}
    done = triggers.accept_offer(state, "p1", offer.id, {"unit": "cruiser"})
    system = done.systems["000"]
    assert damage.damaged_count(system, "space", "p1", "cruiser") == 0  # wybór gracza
    assert damage.damaged_count(system, "space", "p1", "dreadnought") == 1
    assert done.pending_offers == [] and done.pending_window is None


def test_decyzji_obowiazkowej_nie_mozna_odrzucic_a_zly_wybor_jest_odrzucany() -> None:
    state = _da_state()
    _round_end(state)
    offer = _only_offer(state)
    with pytest.raises(ValueError, match="mandatory"):
        triggers.decline_offer(state, "p1", offer.id)
    with pytest.raises(ValueError, match="valid option"):
        triggers.accept_offer(state, "p1", offer.id, {"unit": "carrier"})
    with pytest.raises(ValueError, match="valid option"):
        triggers.accept_offer(state, "p1", offer.id, {})
    with pytest.raises(ValueError, match="belongs to p1"):
        triggers.accept_offer(state, "p2", offer.id, {"unit": "cruiser"})


def test_duranium_armor_przy_jednym_typie_nie_ma_czego_decydowac() -> None:
    state = _tech(battle_state({"p1": {"dreadnought": 2}, "p2": {"cruiser": 1}}), "p1", "da")
    damage.set_damaged(state.systems["000"], "space", "p1", "dreadnought", 2)
    _round_end(state)
    assert state.pending_offers == []
    assert damage.damaged_count(state.systems["000"], "space", "p1", "dreadnought") == 1


# --- Assault Cannon: decyduje OFIARA, walka czeka -------------------------------------------


def _ac_state() -> GameState:
    return _tech(
        battle_state({"p1": {"cruiser": 3}, "p2": {"cruiser": 1, "destroyer": 1, "fighter": 2}}),
        "p1",
        "asc",
    )


def test_assault_cannon_pyta_ofiare_a_walka_czeka_w_kroku_triggers(
    registry: StaticDataRegistry,
) -> None:
    started = battle.start_combat(_ac_state(), battle_grid(), registry)
    combat = started.active_combat
    assert combat is not None and combat.step is CombatStep.TRIGGERS
    offer = _only_offer(started)
    assert offer.player_id == "p2" and offer.owner_id == "p1" and offer.mandatory
    # nic nie zginęło, dopóki ofiara nie zdecyduje
    assert started.systems["000"].space_units["p2"] == {
        "cruiser": 1, "destroyer": 1, "fighter": 2,
    }
    with pytest.raises(ValueError, match="not the current combat step"):
        battle.roll_round(started, battle_grid(), registry)


def test_assault_cannon_ofiara_wybiera_a_walka_rusza_dalej(registry: StaticDataRegistry) -> None:
    started = battle.start_combat(_ac_state(), battle_grid(), registry)
    offer = _only_offer(started)
    view = offers.offer_view(started, registry, offer)
    assert {o["value"] for o in view["inputs"][0]["options"]} == {"cruiser", "destroyer"}
    with pytest.raises(ValueError, match="belongs to p2"):
        offers.accept(started, battle_grid(), registry, "p1", offer.id, {"ship": "cruiser"})
    done = offers.accept(started, battle_grid(), registry, "p2", offer.id, {"ship": "cruiser"})
    assert done.systems["000"].space_units["p2"] == {"destroyer": 1, "fighter": 2}
    assert done.active_combat is not None
    assert done.active_combat.step is CombatStep.AFB  # destroyer ma AFB; walka ruszyła dalej
    assert done.pending_window is None
    # Opcje z grafiką jednostki (sprite w kafelku), a okno bitwy dostaje efekt do animacji.
    assert {o["meta"]["unit"] for o in view["inputs"][0]["options"]} == {"cruiser", "destroyer"}
    assert done.active_combat.effects == [
        {"kind": "assault_cannon", "player": "p1", "victim": "p2", "unit": "cruiser"}
    ]


def test_assault_cannon_ofiara_z_jednym_typem_nie_ma_wyboru(registry: StaticDataRegistry) -> None:
    state = _tech(
        battle_state({"p1": {"cruiser": 3}, "p2": {"cruiser": 2, "fighter": 1}}), "p1", "asc"
    )
    started = battle.start_combat(state, battle_grid(), registry)
    assert started.pending_offers == []
    assert started.systems["000"].space_units["p2"] == {"cruiser": 1, "fighter": 1}


# --- Magen Defense Grid: cel wybiera właściciel ------------------------------------------------


def test_magen_pyta_wlasciciela_w_ktora_sile_trafic(registry: StaticDataRegistry) -> None:
    state = battle_state(
        planet={"p1": {"infantry": 2, "mech": 1}, "p2": {"infantry": 2, "pds": 1}}
    )
    state.tactical_step = TacticalStep.INVASION
    _tech(state, "p2", "md")
    started = battle.start_combat(state, battle_grid(), registry, "pl")
    assert started.active_combat is not None
    assert started.active_combat.step is CombatStep.TRIGGERS
    offer = _only_offer(started)
    assert offer.player_id == "p2" and offer.owner_id is None
    done = offers.accept(started, battle_grid(), registry, "p2", offer.id, {"target": "infantry"})
    assert done.systems["000"].planet_units["pl"]["p1"] == {"infantry": 1, "mech": 1}
    assert done.active_combat is not None and done.active_combat.step is CombatStep.ROLL


# --- Infantry II: wybór planety w domu --------------------------------------------------------


def _inf_state(planets: list[str]) -> GameState:
    home = SystemState(position="000", system_id="18", planet_owners={p: "p1" for p in planets})
    player = PlayerState(
        player_id="p1", color="red", technologies=["inf2"], home_position="000",
        infantry_ii_on_card=2,
    )
    return GameState(
        phase=Phase.ACTION, active_player_id="p2", seating_order=["p1", "p2"],
        players={"p1": player, "p2": PlayerState(player_id="p2", color="blue")},
        systems={"000": home},
    )


def test_infantry_ii_z_dwiema_planetami_pyta_gracza() -> None:
    state = _inf_state(["a", "b"])
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    offer = _only_offer(state)
    assert state.players["p1"].infantry_ii_on_card == 2  # nic nie stało się samo
    done = triggers.accept_offer(state, "p1", offer.id, {"planet": "b"})
    assert done.systems["000"].planet_units["b"]["p1"] == {"infantry": 2}
    assert done.players["p1"].infantry_ii_on_card == 0


def test_infantry_ii_z_jedna_planeta_nie_ma_wyboru() -> None:
    state = _inf_state(["a"])
    triggers.fire(state, GameEvent.TURN, Moment.START, subject="p1", ctx={"player": "p1"})
    assert state.pending_offers == []
    assert state.systems["000"].planet_units["a"]["p1"] == {"infantry": 2}


# --- Dacxive Animators / Bio-Stims: oferty "may" ----------------------------------------------


def _won_ctx() -> dict[str, object]:
    return {"kind": "ground", "position": "000", "planet": "pl", "winner": "p1",
            "attacker": "p1", "defender": "p2"}


def test_dacxive_animators_to_oferta_ktora_mozna_przyjac_albo_odrzucic() -> None:
    state = _tech(battle_state(planet={"p1": {"infantry": 1}}), "p1", "dxa")
    triggers.fire(state, GameEvent.COMBAT_WON, Moment.AFTER, subject="p1", ctx=_won_ctx())
    offer = _only_offer(state)
    assert not offer.mandatory
    assert state.systems["000"].planet_units["pl"]["p1"] == {"infantry": 1}  # nie automatycznie
    accepted = triggers.accept_offer(state, "p1", offer.id, {})
    assert accepted.systems["000"].planet_units["pl"]["p1"] == {"infantry": 2}
    declined = triggers.decline_offer(state, "p1", offer.id)
    assert declined.systems["000"].planet_units["pl"]["p1"] == {"infantry": 1}
    assert declined.pending_offers == []


def test_dacxive_nie_oferuje_przegranemu_ani_po_walce_kosmicznej() -> None:
    state = _tech(battle_state(planet={"p1": {"infantry": 1}}), "p1", "dxa")
    lost = {**_won_ctx(), "winner": "p2"}
    triggers.fire(state, GameEvent.COMBAT_WON, Moment.AFTER, subject="p2", ctx=lost)
    space = {**_won_ctx(), "kind": "space"}
    triggers.fire(state, GameEvent.COMBAT_WON, Moment.AFTER, subject="p1", ctx=space)
    assert state.pending_offers == []


def test_bio_stims_oferuje_odswiezenie_wyczerpanej_technologii(
    registry: StaticDataRegistry,
) -> None:
    state = _tech(battle_state(), "p1", "bs", "pi")
    state.players["p1"].exhausted_technologies = ["pi"]
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    offer = _only_offer(state)
    view = offers.offer_view(state, registry, offer)
    assert [o["value"] for o in view["inputs"][0]["options"]] == ["tech:pi"]
    done = triggers.accept_offer(state, "p1", offer.id, {"target": "tech:pi"})
    assert done.players["p1"].exhausted_technologies == ["bs"]  # karta wyczerpana, pi odświeżona


def test_bio_stims_nie_oferuje_bez_celu_ani_gdy_wyczerpana() -> None:
    state = _tech(battle_state(), "p1", "bs")
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    assert state.pending_offers == []  # nie ma co odświeżać
    state.players["p1"].technologies = ["bs", "pi"]
    state.players["p1"].exhausted_technologies = ["bs", "pi"]
    triggers.fire(state, GameEvent.TURN, Moment.END, subject="p1", ctx={"player": "p1"})
    assert state.pending_offers == []  # Bio-Stims sama jest wyczerpana


# --- Taktyka: oferty blokują wyjście z kroku ----------------------------------------------------


def test_nierozstrzygniete_decyzje_blokuja_zakonczenie_akcji(registry: StaticDataRegistry) -> None:
    from src.core import tactical

    state = _da_state()
    state.tactical_step = TacticalStep.INVASION
    _round_end(state)
    with pytest.raises(ValueError, match="decisions to make"):
        tactical.end_action(state, registry)


# --- API ---------------------------------------------------------------------------------------


def test_api_lista_i_odpowiedz_na_oferte(registry: StaticDataRegistry) -> None:
    state = _da_state()
    _round_end(state)
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=state)
    client = TestClient(app)
    listed = client.get("/offers", params={"player_id": "p1"}).json()["offers"]
    assert len(listed) == 1 and listed[0]["mandatory"] and listed[0]["name"] == "Duranium Armor"
    assert client.get("/offers", params={"player_id": "p2"}).json()["offers"] == []
    bad = client.post(
        "/offers/accept", json={"actor_id": "p1", "offer_id": listed[0]["id"], "params": {}}
    )
    assert bad.status_code == 422
    refuse = client.post(
        "/offers/decline", json={"actor_id": "p1", "offer_id": listed[0]["id"]}
    )
    assert refuse.status_code == 422 and "mandatory" in refuse.json()["detail"]
    ok = client.post(
        "/offers/accept",
        json={"actor_id": "p1", "offer_id": listed[0]["id"], "params": {"unit": "cruiser"}},
    )
    assert ok.status_code == 200
    assert client.get("/offers").json()["offers"] == []
