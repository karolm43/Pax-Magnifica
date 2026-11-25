"""Testy hold-play i kart Sabotage (RULES.md 53.6, 54.11): karta czeka stały czas, potem działa."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import action_cards, card_hold, exploration, reaction_window
from src.core.event_store import EventStore
from src.core.game_state import GameState, Phase, PlayerState, SystemState, TacticalStep
from src.core.registry import StaticDataRegistry

NOW = 1000.0
WINDOW = reaction_window.DEFAULT_SECONDS  # stała długość okna (54.11)


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(
    p1_hand: list[str], p2_hand: list[str], *, deck: bool = True, tactical: bool = False
) -> GameState:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        seating_order=["p1", "p2", "p3"],
        active_system="101" if tactical else None,
        tactical_step=TacticalStep.MOVEMENT if tactical else None,
        players={
            "p1": PlayerState(player_id="p1", color="red", trade_goods=1),
            "p2": PlayerState(player_id="p2", color="blue"),
            "p3": PlayerState(player_id="p3", color="green"),
        },
        systems={"101": SystemState(position="101", system_id="18")},
    )
    state.players["p1"].private.action_cards = list(p1_hand)
    state.players["p2"].private.action_cards = list(p2_hand)
    if deck:
        state.decks.action_card_deck = ["filler"]
    return state


def _industrial(registry: StaticDataRegistry) -> tuple[str, list[str]]:
    planets = [
        pid
        for pid in sorted(registry.planets)
        if exploration.planet_traits(registry, pid) == ["industrial"]
    ][:2]
    return "industrial_initiative", planets


def _own(state: GameState, planets: list[str]) -> None:
    state.systems["101"].planet_owners = {p: "p1" for p in planets}


def _play(state: GameState, registry: StaticDataRegistry, card: str, *, params=None) -> GameState:  # type: ignore[no-untyped-def]
    new, _ = action_cards.play_action_card(
        state, registry, "p1", card, params or {}, now=NOW
    )
    return new


# --- filtr jawny: zachowanie natychmiastowe ---------------------------------------------------


def test_bez_now_karta_wykonuje_sie_od_razu(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    new, _ = action_cards.play_action_card(state, registry, "p1", card)
    assert new.held_play is None
    assert new.players["p1"].trade_goods == 3


def test_brak_kart_u_innych_wykonuje_od_razu(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], [])
    _own(state, planets)
    new = _play(state, registry, card)
    assert new.held_play is None
    assert new.players["p1"].trade_goods == 3


def test_wszystkie_sabotage_odrzucone_wykonuje_od_razu(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["fs1"])
    _own(state, planets)
    state.decks.action_card_discard = list(card_hold.SABOTAGE_IDS)
    assert _play(state, registry, card).held_play is None


def test_brak_talii_kart_akcji_wykonuje_od_razu(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["fs1"], deck=False)
    _own(state, planets)
    assert _play(state, registry, card).held_play is None


def test_okno_otwiera_sie_tak_samo_bez_sabotage_w_rece(registry: StaticDataRegistry) -> None:
    """Treść ręki nie steruje zachowaniem: ktokolwiek z kartą akcji dostaje okno."""
    card, planets = _industrial(registry)
    for hand in (["sabo1"], ["fs1"]):
        state = _state([card], hand)
        _own(state, planets)
        held = _play(state, registry, card).held_play
        assert held is not None
        assert held.eligible == ["p2"]


# --- stan w trakcie okna -----------------------------------------------------------------------


def test_karta_czeka_na_stole_a_efekt_sie_nie_wykonal(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    new = _play(state, registry, card)
    assert new.held_play is not None
    assert new.held_play.card_id == card
    assert new.held_play.opened_at == NOW
    assert new.players["p1"].private.action_cards == []
    assert new.decks.action_card_discard == []
    assert new.players["p1"].trade_goods == 1  # efekt jeszcze się nie wykonał
    assert new.players["p1"].took_action_this_turn  # akcja zużyta od razu


def test_efekt_z_losowaniem_wykonuje_sie_dopiero_przy_zwolnieniu(
    registry: StaticDataRegistry,
) -> None:
    planet = next(
        pid
        for pid in sorted(registry.planets)
        if exploration.planet_traits(registry, pid) == ["hazardous"]
    )
    state = _state(["plague"], ["sabo1"])
    state.rng_seed = 7
    state.systems["101"].planet_owners = {planet: "p2"}
    state.systems["101"].planet_units = {planet: {"p2": {"infantry": 12}}}
    held = _play(state, registry, "plague", params={"planet": planet})
    assert held.held_play is not None
    assert held.rng_counter == state.rng_counter and held.table_roll_seq == state.table_roll_seq
    assert held.systems["101"].planet_units[planet]["p2"]["infantry"] == 12
    released = card_hold.release(held, registry, "p1", now=NOW + WINDOW)
    assert released.held_play is None
    assert released.table_roll is not None and released.table_roll["kind"] == "plague"
    assert released.table_roll_seq == state.table_roll_seq + 1


def test_zle_parametry_odrzucane_przy_zagraniu_nie_przy_zwolnieniu(
    registry: StaticDataRegistry,
) -> None:
    state = _state(["plague"], ["sabo1"])
    with pytest.raises(ValueError, match="zzz"):
        _play(state, registry, "plague", params={"planet": "zzz"})
    assert state.players["p1"].private.action_cards == ["plague"]


# --- zwolnienie: pasy / czas -------------------------------------------------------------------


def test_pasy_nie_skracaja_okna_a_silnik_pasuje_za_graczy_bez_sabotage(
    registry: StaticDataRegistry,
) -> None:
    """54.11: p3 bez Sabotage spasowany od razu; pas p2 nie kończy okna - kończy je czas."""
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    state.players["p3"].private.action_cards = ["fs1"]
    held = _play(state, registry, card)
    assert held.held_play is not None and held.held_play.eligible == ["p2", "p3"]
    assert held.held_play.passed == ["p3"] and held.held_play.seconds == WINDOW
    both = card_hold.pass_hold(held, registry, "p2")
    assert both.held_play is not None and both.held_play.passed == ["p3", "p2"]
    with pytest.raises(ValueError, match="still open"):
        card_hold.release(both, registry, "p1", now=NOW + WINDOW - 1)
    done = card_hold.release(both, registry, "p1", now=NOW + WINDOW)
    assert done.held_play is None
    assert done.players["p1"].trade_goods == 3
    assert done.decks.action_card_discard == [card]


def test_zagrywajacy_nie_moze_pasowac_za_innych(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    held = _play(state, registry, card)
    with pytest.raises(ValueError, match="pass for the other"):
        card_hold.pass_hold(held, registry, "p1")
    with pytest.raises(ValueError, match="cannot respond"):
        card_hold.pass_hold(held, registry, "p3")  # p3 nie ma kart akcji
    twice = card_hold.pass_hold(
        _two_eligible(registry), registry, "p2"
    )
    with pytest.raises(ValueError, match="already passed"):
        card_hold.pass_hold(twice, registry, "p2")


def _two_eligible(registry: StaticDataRegistry) -> GameState:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    state.players["p3"].private.action_cards = ["fs1"]
    return _play(state, registry, card)


def test_timeout_zwalnia_a_wczesniej_nie(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    held = _play(state, registry, card)
    with pytest.raises(ValueError, match="still open"):
        card_hold.release(held, registry, "p1", now=NOW + WINDOW - 1)
    done = card_hold.release(held, registry, "p1", now=NOW + WINDOW)
    assert done.held_play is None
    assert done.players["p1"].trade_goods == 3
    assert done.decks.action_card_discard == [card]
    assert done.players["p1"].private.action_cards == []


# --- blokada innych akcji ----------------------------------------------------------------------


def test_inne_akcje_zablokowane_w_trakcie_okna(registry: StaticDataRegistry) -> None:
    from src.core import component_action, tactical, turn_flow

    card, planets = _industrial(registry)
    state = _state([card, "fs1"], ["sabo1"])
    _own(state, planets)
    held = _play(state, registry, card)
    with pytest.raises(ValueError, match="Sabotage"):
        turn_flow.end_turn(held, "p1")
    with pytest.raises(ValueError, match="Sabotage"):
        turn_flow.pass_turn(held, "p1")
    with pytest.raises(ValueError, match="Sabotage"):
        turn_flow.next_phase(held)
    with pytest.raises(ValueError, match="Sabotage"):
        component_action.play_component_action(held, "p1", "x")
    from src.api.demo_map import build_demo_grid

    with pytest.raises(ValueError, match="timing window"):
        tactical.activate_system(held, build_demo_grid(registry), "101")

    with pytest.raises(ValueError, match="Sabotage"):
        action_cards.play_action_card(held, registry, "p1", "fs1", now=NOW)
    rows = {r["card_id"]: r for r in action_cards.playability(held, registry, "p1")}
    assert not rows["fs1"]["playable"]


# --- Sabotage ----------------------------------------------------------------------------------


def test_sabotage_anuluje_karte_action(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    held = _play(state, registry, card)
    assert action_cards.playability(held, registry, "p2")[0]["playable"]
    done, implemented = action_cards.play_action_card(held, registry, "p2", "sabo1", now=NOW)
    assert implemented
    assert done.held_play is None
    assert done.players["p1"].trade_goods == 1  # efekt się nie wykonał
    assert done.players["p1"].took_action_this_turn  # akcja zostaje zużyta
    assert sorted(done.decks.action_card_discard) == sorted([card, "sabo1"])
    assert done.players["p2"].private.action_cards == []


def test_sabotage_anuluje_karte_reakcji(registry: StaticDataRegistry) -> None:
    state = _state(["fs1"], ["sabo2"], tactical=True)
    held = _play(state, registry, "fs1")
    assert held.held_play is not None and not held.held_play.is_action
    assert not held.players["p1"].took_action_this_turn
    done, _ = action_cards.play_action_card(held, registry, "p2", "sabo2", now=NOW)
    assert done.held_play is None
    assert sorted(done.decks.action_card_discard) == ["fs1", "sabo2"]
    assert not done.active_effects  # Flank Speed nie dodał efektu


def test_reakcja_bez_sabotage_wykonuje_sie_po_zwolnieniu(registry: StaticDataRegistry) -> None:
    state = _state(["fs1"], ["fs2"], tactical=True)
    held = _play(state, registry, "fs1")
    assert held.held_play is not None and held.held_play.passed == ["p2"]  # auto-pas: bez Sabotage
    done = card_hold.release(held, registry, "p1", now=NOW + WINDOW)
    assert done.held_play is None
    assert len(done.active_effects) == 1
    assert done.decks.action_card_discard == ["fs1"]


def test_sabotage_nie_anuluje_sabotage(registry: StaticDataRegistry) -> None:
    state = _state(["sabo1"], ["sabo2"], tactical=True)
    # Sabotage nie ma okna w żadnym stanie bez karty czekającej - i sama nie otwiera okna hold.
    assert card_hold.eligible_players(state, "p1", "sabo1") == []
    with pytest.raises(ValueError, match="no open window"):
        action_cards.play_action_card(state, registry, "p1", "sabo1", now=NOW)
    # Karta, która jest już w held_play, nie jest Sabotage (okno dostawcy).
    from src.core import reaction_cards

    assert reaction_cards.open_windows(state) == [
        w for w in reaction_cards.open_windows(state) if w.event.value != "cards.action_played"
    ]


def test_sabotage_tylko_inny_gracz_i_tylko_uprawniony(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    state.players["p1"].private.action_cards.append("sabo3")
    held = _play(state, registry, card)
    with pytest.raises(ValueError, match="no open window"):
        action_cards.play_action_card(held, registry, "p1", "sabo3", now=NOW)  # własna karta
    passed = card_hold.pass_hold(_two_eligible(registry), registry, "p2")
    assert passed.held_play is not None
    passed.players["p2"].private.action_cards.append("sabo1")
    with pytest.raises(ValueError, match="no open window"):
        action_cards.play_action_card(passed, registry, "p2", "sabo1", now=NOW)  # już spasował


# --- API ---------------------------------------------------------------------------------------


def _client(state: GameState, clock: list[float]) -> TestClient:
    app = create_app(store=EventStore(), initial_state=state, now=lambda: clock[0])
    return TestClient(app)


def test_api_play_pass_release_i_blokada(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    clock = [NOW]
    client = _client(state, clock)
    body = {"actor_id": "p1", "player_id": "p1", "card_id": card}
    resp = client.post("/action-card/play", json=body)
    assert resp.status_code == 200, resp.text
    assert resp.json()["held"] is True
    # blokada: End turn i zmiana fazy => 422; God-Mode i karty wolno
    assert client.post("/turn/end", json={"player_id": "p1"}).status_code == 422
    assert client.post("/phase/next").status_code == 422
    assert client.post("/tactical/activate", json={"position": "101"}).status_code == 422
    # zagrywający nie pasuje za innych; za wcześnie na zwolnienie
    assert client.post("/action-card/held/pass", json={"actor_id": "p1"}).status_code == 422
    assert client.post("/action-card/held/release", json={"actor_id": "p1"}).status_code == 422
    clock[0] = NOW + WINDOW + 1
    assert client.post("/action-card/held/release", json={"actor_id": "p1"}).status_code == 200
    assert client.get("/state").json()["state"]["held_play"] is None


def test_api_web_data_pokazuje_held_a_pas_nie_skraca(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    client = _client(state, [NOW])
    client.post("/action-card/play", json={"actor_id": "p1", "player_id": "p1", "card_id": card})
    from src.api.web_game import _held_play

    held = _held_play(client.app.state.ctx.service.current_state(), registry)  # type: ignore[attr-defined]
    assert held is not None
    assert held["playerId"] == "p1" and held["cardId"] == card
    assert held["eligible"] == ["p2"] and held["passed"] == []
    assert held["holdSeconds"] == WINDOW and held["openedAt"] == NOW
    assert held["cardName"] and held["text"]
    assert client.post("/action-card/held/pass", json={"actor_id": "p2"}).status_code == 200
    assert client.app.state.ctx.service.current_state().held_play is not None  # type: ignore[attr-defined]


# --- zatrzymanie zegara na czas zagrywania Sabotage ---------------------------------------------


def _held_industrial(registry: StaticDataRegistry) -> GameState:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    return _play(state, registry, card)


def test_freeze_zatrzymuje_zegar_a_unfreeze_wznawia_z_reszta_czasu(
    registry: StaticDataRegistry,
) -> None:
    held = _held_industrial(registry)
    frozen = card_hold.freeze(held, "p2", NOW + 2)
    assert frozen.held_play is not None and frozen.held_play.frozen_by == "p2"
    # Po upływie okna zatrzymane okno NIE wygasa (i nie da się go zwolnić).
    assert not card_hold.expired(frozen.held_play, NOW + WINDOW + 20)
    with pytest.raises(ValueError, match="still open"):
        card_hold.release(frozen, registry, "p1", now=NOW + WINDOW + 20)
    # Wznowienie po 20 s: do końca nadal zostaje tyle, ile zostało przy zatrzymaniu.
    resumed = card_hold.unfreeze(frozen, "p2", NOW + 22)
    assert resumed.held_play is not None and resumed.held_play.frozen_at is None
    assert not card_hold.expired(resumed.held_play, NOW + 22 + WINDOW - 2 - 0.5)
    assert card_hold.expired(resumed.held_play, NOW + 22 + WINDOW - 2)


def test_freeze_tylko_dla_uprawnionego_i_porzucone_zatrzymanie_wygasa(
    registry: StaticDataRegistry,
) -> None:
    held = _held_industrial(registry)
    with pytest.raises(ValueError, match="cannot respond"):
        card_hold.freeze(held, "p3", NOW + 1)
    frozen = card_hold.freeze(held, "p2", NOW + 1)
    assert frozen.held_play is not None
    assert card_hold.expired(frozen.held_play, NOW + 1 + card_hold.FREEZE_MAX_SECONDS)
    # Cudze wznowienie nic nie zmienia.
    assert card_hold.unfreeze(frozen, "p3", NOW + 5).held_play.frozen_at is not None  # type: ignore[union-attr]


def test_sabotage_zamyka_zatrzymanie(registry: StaticDataRegistry) -> None:
    held = _held_industrial(registry)
    frozen = card_hold.freeze(held, "p2", NOW + 1)
    assert frozen.held_play is not None
    # Anulowanie przez Sabotage kończy okno razem z zatrzymaniem.
    after, _ = action_cards.play_action_card(frozen, registry, "p2", "sabo1", {}, now=NOW + 3)
    assert after.held_play is None
