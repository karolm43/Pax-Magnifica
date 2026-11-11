"""Testy hold-rewind (RULES.md 53.7): cofnięcie do okna, które minęło + 4 karty reakcji."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import (
    action_cards,
    hold_rewind,
    reaction_cards,
    status_phase,
    strategic_action,
    strategy_phase,
)
from src.core.event_store import EventStore
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    Phase,
    PlayerState,
    StatusPhaseState,
    StatusStep,
    SystemState,
)
from src.core.hold_rewind import Snapshot
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _players(**hands: list[str]) -> dict[str, PlayerState]:
    players = {
        "p1": PlayerState(player_id="p1", color="red"),
        "p2": PlayerState(player_id="p2", color="blue"),
    }
    for pid, hand in hands.items():
        players[pid].private.action_cards = list(hand)
    return players


def _chain(*states: GameState, labels: list[str] | None = None) -> list[Snapshot]:
    names = labels or [f"step{i}" for i in range(len(states))]
    return [Snapshot(i + 1, names[i], state) for i, state in enumerate(states)]


# ------------------------------------------------------------------ is_irreversible_step


def test_krok_czysty_nie_blokuje() -> None:
    a = GameState(players=_players())
    b = a.clone()
    b.active_player_id = "p2"
    assert hold_rewind.is_irreversible_step(a, b) is None


@pytest.mark.parametrize("field", ["rng_counter", "table_roll_seq"])
def test_rzut_kosmi_blokuje(field: str) -> None:
    a = GameState(players=_players())
    b = a.clone()
    setattr(b, field, 3)
    assert hold_rewind.is_irreversible_step(a, b) == "Dice were rolled"


def test_talia_faza_runda_dobranie_i_odrzucone_blokuja() -> None:
    a = GameState(players=_players())
    deck = a.clone()
    deck.decks.action_card_deck = ["x"]
    assert "deck" in (hold_rewind.is_irreversible_step(a, deck) or "")
    exploration = a.clone()
    exploration.decks.exploration_deck = {"cultural": ["c1"]}
    assert hold_rewind.is_irreversible_step(a, exploration) is not None
    phase = a.clone()
    phase.phase = Phase.STATUS
    assert hold_rewind.is_irreversible_step(a, phase) == "The game phase changed"
    rnd = a.clone()
    rnd.round_number = 2
    assert hold_rewind.is_irreversible_step(a, rnd) == "The game phase changed"
    draw = a.clone()
    draw.players["p1"].private.action_cards = ["sabo1"]
    assert hold_rewind.is_irreversible_step(a, draw) == "A player drew a card"
    played = a.clone()
    played.decks.action_card_discard = ["sabo1"]
    assert hold_rewind.is_irreversible_step(a, played) == "An action card was played"


# ------------------------------------------------------------------ zasięg cofania


def test_limit_osmiu_krokow_i_powod() -> None:
    states = [GameState(players=_players()) for _ in range(12)]
    chain = _chain(*states)
    reach, limit = hold_rewind.reachable_snapshots(chain)
    assert [r.steps_back for r in reach] == list(range(hold_rewind.MAX_REWIND_STEPS + 1))
    assert limit is not None and "8" in limit


def test_kosci_odcinaja_zasieg() -> None:
    clean = GameState(players=_players())
    rolled = clean.clone()
    rolled.rng_counter = 1
    after = rolled.clone()
    after.active_player_id = "p2"
    reach, limit = hold_rewind.reachable_snapshots(_chain(clean, rolled, after))
    assert [r.steps_back for r in reach] == [0, 1]  # migawka sprzed rzutu poza zasięgiem
    assert limit == "Dice were rolled"


def test_wczesniejszy_rewind_odcina_zasieg() -> None:
    base = GameState(players=_players())
    nxt = base.clone()
    nxt.active_player_id = "p2"
    chain = _chain(base, nxt, nxt.clone(), labels=["a", "hold-rewind:coup:1", "b"])
    reach, limit = hold_rewind.reachable_snapshots(chain)
    assert [r.snapshot.seq for r in reach] == [3, 2]
    assert limit == "An earlier hold-rewind"


# ------------------------------------------------------------------ Public Disgrace


def _strategy_state(hand: list[str]) -> GameState:
    return GameState(
        phase=Phase.STRATEGY, speaker_id="p1", seating_order=["p1", "p2"],
        active_player_id="p1", players=_players(p2=hand),
    )


def test_disgrace_zakazuje_cofnietej_karty(registry: StaticDataRegistry) -> None:
    before = _strategy_state(["disgrace"])
    after = strategy_phase.pick_strategy_card(before, registry, "p1", 3)
    chain = _chain(before, after)
    steps, _limit = hold_rewind.candidates(chain, registry, "p2")
    assert [s["seq"] for s in steps] == [1]  # w teraźniejszości nie ma czego cofać
    assert steps[0]["cards"][0]["card_id"] == "disgrace"
    assert steps[0]["stepsBack"] == 1

    new_state, implemented = hold_rewind.play_at(chain, registry, "p2", "disgrace", 1)
    assert implemented
    assert new_state.players["p1"].strategy_cards == []  # wybór cofnięty
    assert new_state.players["p2"].private.action_cards == []
    assert new_state.decks.action_card_discard == ["disgrace"]
    with pytest.raises(ValueError, match="different strategy card"):
        strategy_phase.pick_strategy_card(new_state, registry, "p1", 3)
    picked = strategy_phase.pick_strategy_card(new_state, registry, "p1", 4)
    assert picked.players["p1"].strategy_cards == [4]
    assert strategy_phase.forbidden_picks(picked, "p1") == set()  # zakaz spełniony


def test_disgrace_bez_wyboru_w_przyszlosci_nie_jest_oferowana(
    registry: StaticDataRegistry,
) -> None:
    state = _strategy_state(["disgrace"])
    chain = _chain(state)
    assert hold_rewind.candidates(chain, registry, "p2")[0] == []
    with pytest.raises(ValueError, match="no open window"):
        action_cards.play_action_card(state, registry, "p2", "disgrace")


def test_play_at_odrzuca_karte_spoza_reki_i_obcego_aktora(registry: StaticDataRegistry) -> None:
    before = _strategy_state(["disgrace"])
    chain = _chain(before, strategy_phase.pick_strategy_card(before, registry, "p1", 3))
    with pytest.raises(ValueError, match="cannot play a card for"):
        hold_rewind.play_at(chain, registry, "p2", "disgrace", 1, actor_id="p1")
    with pytest.raises(ValueError, match="do not have"):
        hold_rewind.play_at(chain, registry, "p1", "disgrace", 1)
    with pytest.raises(ValueError, match="no longer in the history"):
        hold_rewind.play_at(chain, registry, "p2", "disgrace", 99)


def test_zakaz_oszustwa_blokuje_play_at(registry: StaticDataRegistry) -> None:
    before = _strategy_state(["disgrace"])
    picked = strategy_phase.pick_strategy_card(before, registry, "p1", 3)
    rolled = picked.clone()
    rolled.rng_counter = 5
    chain = _chain(before, picked, rolled)
    with pytest.raises(ValueError, match="Dice were rolled"):
        hold_rewind.play_at(chain, registry, "p2", "disgrace", 1)
    # ... a z migawki za rzutem nadal wolno (ale tam już nie ma okna Disgrace)
    assert hold_rewind.candidates(chain, registry, "p2")[0] == []


# ------------------------------------------------------------------ Coup d'Etat


def _action_state(hand: list[str]) -> GameState:
    players = _players(p2=hand)
    players["p1"].strategy_cards = [1]
    players["p2"].strategy_cards = [2]
    return GameState(
        phase=Phase.ACTION, speaker_id="p1", seating_order=["p1", "p2"],
        active_player_id="p1", players=players,
    )


def test_coup_konczy_ture_bez_akcji_strategicznej(registry: StaticDataRegistry) -> None:
    before = _action_state(["coup"])
    after = strategic_action.play_strategy_card(before, registry, "p1", 1)
    assert after.players["p1"].exhausted_strategy_cards == [1]
    chain = _chain(before, after)
    steps, _ = hold_rewind.candidates(chain, registry, "p2")
    assert [s["seq"] for s in steps] == [1]

    new_state, _ = hold_rewind.play_at(chain, registry, "p2", "coup", 1)
    assert new_state.active_player_id == "p2"  # tura przeszła dalej
    assert new_state.players["p1"].exhausted_strategy_cards == []  # karta nie wyczerpana
    assert not new_state.players["p1"].took_action_this_turn
    assert new_state.pending_strategy is None and new_state.pending_window is None


def test_coup_nie_jest_oferowany_gdy_nie_bylo_akcji_strategicznej(
    registry: StaticDataRegistry,
) -> None:
    before = _action_state(["coup"])
    other = before.clone()
    other.players["p1"].private.action_cards = ["x"]  # krok bez akcji strategicznej
    chain = _chain(before, other)
    steps = hold_rewind.candidates(chain, registry, "p2")[0]
    assert [s["seq"] for s in steps] == [2]  # tylko zwykłe okno TERAZ, nie cofnięcie do seq 1


def test_coup_zwykla_sciezka_w_oknie_otwartym_teraz(registry: StaticDataRegistry) -> None:
    state = _action_state(["coup"])
    ok, _reason, window = reaction_cards.available(state, registry, "p2", "coup")
    assert ok and window is not None
    new_state, _ = action_cards.play_action_card(state, registry, "p2", "coup", actor_id="p2")
    assert new_state.active_player_id == "p2"
    # własna tura: nie można "puczem" przejąć własnej akcji
    own = _action_state(["coup"])
    own.players["p1"].private.action_cards = ["coup"]
    own.players["p2"].private.action_cards = []
    assert not reaction_cards.available(own, registry, "p1", "coup")[0]


# ------------------------------------------------------------------ Political Stability


def _status_state() -> GameState:
    players = _players(p1=["stability"])
    players["p1"].strategy_cards = [1, 2]
    players["p2"].strategy_cards = [3, 4]
    return GameState(
        phase=Phase.STATUS, speaker_id="p1", seating_order=["p1", "p2"], active_player_id="p1",
        players=players, status=StatusPhaseState(step=StatusStep.COMPLETE),
    )


def test_stability_zatrzymuje_karty_i_pomija_wybor(registry: StaticDataRegistry) -> None:
    state = _status_state()
    ok, _reason, _window = reaction_cards.available(state, registry, "p1", "stability")
    assert ok
    played, _ = action_cards.play_action_card(state, registry, "p1", "stability", actor_id="p1")
    done = status_phase.finish_status(played, registry)
    assert done.players["p1"].strategy_cards == [1, 2]  # nie wróciły
    assert done.players["p2"].strategy_cards == []
    assert done.phase is Phase.STRATEGY and done.round_number == 2
    assert strategy_phase.next_strategy_picker(done) == "p2"  # p1 nie wybiera
    assert not any(e.key == strategy_phase.STABILITY_KEY for e in done.active_effects)
    # kolejna runda zwraca karty normalnie
    assert not strategy_phase.retains_strategy_cards(done, "p1")


def test_stability_przechodzi_przez_faze_agendy(registry: StaticDataRegistry) -> None:
    state = _status_state()
    state.custodians_removed = True
    played, _ = action_cards.play_action_card(state, registry, "p1", "stability")
    in_agenda = status_phase.finish_status(played, registry)
    assert in_agenda.phase is Phase.AGENDA
    closed = strategy_phase.close_round_cards(in_agenda, registry)
    assert closed.players["p1"].strategy_cards == [1, 2]
    assert closed.strategy_card_tg == in_agenda.strategy_card_tg  # bez podwójnej akumulacji TG


def test_stability_nie_ma_okna_poza_krokiem_zwrotu(registry: StaticDataRegistry) -> None:
    state = _status_state()
    assert state.status is not None
    state.status.step = StatusStep.REDISTRIBUTE
    assert not reaction_cards.available(state, registry, "p1", "stability")[0]
    state.status.step = StatusStep.COMPLETE
    state.players["p1"].strategy_cards = []
    assert not reaction_cards.available(state, registry, "p1", "stability")[0]


# ------------------------------------------------------------------ Crash Landing


def _crash_state(registry: StaticDataRegistry, hits: int = 1) -> tuple[GameState, list[str]]:
    system_def = next(
        s for s in registry.systems.values()
        if s.planets and s.id != "18" and all(p in registry.planets for p in s.planets)
    )
    system = SystemState(
        position="101", system_id=system_def.id,
        space_units={"p1": {"cruiser": 1, "infantry": 2}, "p2": {"cruiser": 2}},
    )
    state = GameState(
        phase=Phase.ACTION, active_player_id="p2", active_system="101",
        players=_players(p1=["crashlanding"]), systems={"101": system},
        active_combat=ActiveCombat(
            kind="space", position="101", attacker="p2", defender="p1",
            step=CombatStep.ASSIGN, pending_hits={"p1": hits},
        ),
    )
    return state, list(system_def.planets)


def test_crashlanding_laduje_sile_naziemna_na_planete(registry: StaticDataRegistry) -> None:
    state, planets = _crash_state(registry)
    ok, _reason, window = reaction_cards.available(state, registry, "p1", "crashlanding")
    assert ok and window is not None and window.ctx["position"] == "101"
    implemented, inputs = action_cards.card_inputs(state, registry, "p1", "crashlanding")
    assert implemented
    assert {o["value"] for o in inputs[1]["options"]} == set(planets)
    assert inputs[0]["options"][0]["value"] == "infantry"
    assert "orbit" in inputs[0]["options"][0]["label"]

    new_state, _ = action_cards.play_action_card(
        state, registry, "p1", "crashlanding",
        {"unit": "infantry", "planet": planets[0]}, actor_id="p1",
    )
    system = new_state.systems["101"]
    assert system.space_units["p1"]["infantry"] == 1
    assert system.planet_units[planets[0]]["p1"]["infantry"] == 1
    with pytest.raises(ValueError, match="planet"):
        action_cards.play_action_card(
            state, registry, "p1", "crashlanding", {"unit": "infantry", "planet": "zzz"}
        )


def test_crashlanding_wymaga_zniszczenia_wszystkich_statkow(registry: StaticDataRegistry) -> None:
    state, _planets = _crash_state(registry, hits=0)
    assert not reaction_cards.available(state, registry, "p1", "crashlanding")[0]
    state2, _ = _crash_state(registry)
    state2.systems["101"].space_units["p1"]["cruiser"] = 2  # 1 trafienie nie zniszczy wszystkich
    assert not reaction_cards.available(state2, registry, "p1", "crashlanding")[0]
    state3, _ = _crash_state(registry)
    state3.systems["101"].space_units["p1"].pop("infantry")  # brak sił naziemnych w orbicie
    assert not reaction_cards.available(state3, registry, "p1", "crashlanding")[0]


def test_crashlanding_hold_rewind_do_kroku_przypisania(registry: StaticDataRegistry) -> None:
    before, planets = _crash_state(registry)
    after = before.clone()
    after.active_combat = None  # strata zadana, statki zniszczone
    after.systems["101"].space_units["p1"] = {}
    chain = _chain(before, after)
    steps, _ = hold_rewind.candidates(chain, registry, "p1")
    assert [s["seq"] for s in steps] == [1] and steps[0]["stepsBack"] == 1
    inputs = hold_rewind.inputs_at(chain, registry, "p1", "crashlanding", 1)[1]
    assert inputs[0]["options"]  # formularz liczony na migawce (są siły w orbicie)
    new_state, _ = hold_rewind.play_at(
        chain, registry, "p1", "crashlanding", 1, {"unit": "infantry", "planet": planets[0]}
    )
    assert new_state.systems["101"].planet_units[planets[0]]["p1"]["infantry"] == 1
    assert new_state.active_combat is not None  # walka wciąż w kroku przypisania


# ------------------------------------------------------------------ endpointy


def _client(registry: StaticDataRegistry, first: GameState) -> TestClient:
    app = create_app(registry=registry, store=EventStore(":memory:"), initial_state=first)
    return TestClient(app)


def test_endpointy_hold_candidates_inputs_play(registry: StaticDataRegistry) -> None:
    before = _action_state(["coup"])
    client = _client(registry, before)
    service = client.app.state.service  # type: ignore[attr-defined]
    after = strategic_action.play_strategy_card(before, registry, "p1", 1)
    service.replace_state(after, label="strategy:1")
    seq_before = service.recent_chain(5)[0][0]

    resp = client.get("/hold/candidates?player_id=p2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["steps"][0]["seq"] == seq_before
    assert body["steps"][0]["stepsBack"] == 1
    assert body["steps"][0]["cards"][0]["card_id"] == "coup"
    assert body["steps"][0]["nextLabel"] == "strategy:1"
    assert "limitReason" in body

    form = client.get(f"/hold/coup/inputs?player_id=p2&seq={seq_before}")
    assert form.status_code == 200 and form.json()["implemented"] is True

    bad = client.post(
        "/hold/play",
        json={"actor_id": "p1", "player_id": "p2", "card_id": "coup", "seq": seq_before},
    )
    assert bad.status_code == 422

    ok = client.post(
        "/hold/play",
        json={"actor_id": "p2", "player_id": "p2", "card_id": "coup", "seq": seq_before},
    )
    assert ok.status_code == 200 and ok.json()["implemented"] is True
    state = ok.json()["envelope"]["state"]
    assert state["active_player_id"] == "p2"
    assert state["players"]["p1"]["exhausted_strategy_cards"] == []
    # historia rozgałęziona: nowy krok jest następcą migawki seq_before, bez starego kroku
    labels = [label for _seq, label, _cur in service.history_entries()]
    assert labels[-1].startswith("hold-rewind:coup")
    assert "strategy:1" not in labels
    assert service.current_state().active_player_id == "p2"

    # po rewindzie kolejne cofnięcie jest zablokowane (czyste cofnięcie, zakaz 4)
    again = client.get("/hold/candidates?player_id=p2").json()
    assert again["steps"] == []


def test_endpoint_candidates_422_dla_nieznanego_gracza(registry: StaticDataRegistry) -> None:
    client = _client(registry, _action_state([]))
    assert client.get("/hold/candidates?player_id=zzz").status_code == 422
