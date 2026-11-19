"""Pauza ochronna w kluczowych oknach (RULES.md 54.10–54.11): otwarcie, bramki, pas, czas."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import agenda_phase, battle, reaction_pause, strategic_action
from src.core.event_store import EventStore
from src.core.game_state import ActiveCombat, CombatStep, DecksState, GameState
from src.core.registry import StaticDataRegistry
from tests.test_hold_rewind import _action_state
from tests.test_reactions_agenda import DIRECTIVE, LAW, _revealed


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _agenda(registry: StaticDataRegistry) -> GameState:
    """Ujawniona agenda; p1 ma ridera, p3 dowolną kartę akcji (liczy się liczba kart, nie treść)."""
    return _revealed(registry, [LAW, DIRECTIVE], {"p1": ["lead_rider"], "p3": ["salvage"]})


def test_ujawniona_agenda_otwiera_pauze_i_blokuje_glos(registry: StaticDataRegistry) -> None:
    state = _agenda(registry)
    reaction_pause.sync(state, registry, now=100.0)
    pause = state.reaction_pause
    assert pause is not None and pause.event == "agenda.revealed"
    assert pause.eligible == ["p1", "p3"]  # ridery: każdy gracz z kartą w ręce (jawna liczba)
    voter = agenda_phase.current_voter(state)
    assert voter is not None
    with pytest.raises(ValueError, match="react"):
        agenda_phase.abstain(state, registry, voter)
    # Auto-pas (54.11): p3 nie ma karty zagrywalnej w tym oknie - silnik pasuje za niego.
    assert pause.passed == ["p3"]
    state = reaction_pause.pass_pause(state, "p1")
    assert state.reaction_pause is not None and state.reaction_pause.passed == ["p3", "p1"]
    with pytest.raises(ValueError, match="not asked"):
        reaction_pause.pass_pause(state, "p2")  # bez kart akcji - nie jest pytany
    assert state.reaction_pause is not None  # pasy nie skracają pauzy
    state = reaction_pause.release(state, now=105.0)
    assert state.reaction_pause is None
    reaction_pause.sync(state, registry, now=105.0)
    assert state.reaction_pause is None  # to samo okno drugi raz nie pauzuje
    agenda_phase.abstain(state, registry, voter)


def test_bez_kart_w_grze_nie_ma_pauzy(registry: StaticDataRegistry) -> None:
    """Filtr jawny: żadna karta spoza odrzuconych nie reaguje na okno - gra nie czeka."""
    state = _revealed(registry, [LAW, DIRECTIVE], {"p1": ["salvage"]})
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is None


def test_pauza_trwa_staly_czas_hosta(registry: StaticDataRegistry) -> None:
    state = _agenda(registry)
    state.reaction_window_seconds = 6
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None and state.reaction_pause.seconds == 6
    with pytest.raises(ValueError, match="still open"):
        reaction_pause.release(state, now=105.0)
    released = reaction_pause.release(state, now=106.0)
    assert released.reaction_pause is None


def test_ogloszona_akcja_strategiczna_pauza_dla_innych(registry: StaticDataRegistry) -> None:
    """Coup d'Etat („another player”): pytani tylko inni gracze, primary czeka."""
    state = strategic_action.play_strategy_card(_action_state(["coup"]), registry, "p1", 1)
    state.players["p1"].private.action_cards = ["salvage"]
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    assert state.reaction_pause.eligible == ["p2"]
    with pytest.raises(ValueError, match="react"):
        strategic_action.submit_primary_step(state, registry, "p1", {})


def test_wygrana_walka_pauza_blokuje_zamkniecie(registry: StaticDataRegistry) -> None:
    """Salvage („after YOU win”): pytany tylko zwycięzca; bitwa nie zamknie się w pauzie."""
    state = _action_state(["salvage"])
    state.players["p1"].private.action_cards = ["salvage"]
    state.decks = DecksState(action_card_deck=["salvage"])
    state.active_system = "000"
    state.active_combat = ActiveCombat(
        kind="space", position="000", attacker="p1", defender="p2",
        step=CombatStep.DONE, winner="p1", outcome="winner",
    )
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None and state.reaction_pause.eligible == ["p1"]
    with pytest.raises(ValueError, match="react"):
        battle.close_combat(state)


def test_api_czas_mija_wg_zegara_serwera(registry: StaticDataRegistry) -> None:
    """Middleware zwalnia przeterminowaną pauzę przy kolejnym POST - gra nie zależy od klienta."""
    clock = [100.0]
    app = create_app(
        registry=registry, store=EventStore(":memory:"), initial_state=GameState(),
        now=lambda: clock[0],
    )
    client = TestClient(app)
    service = app.state.service
    state = _agenda(registry)
    service.replace_state(state, label="agenda:reveal")
    assert service.current_state().reaction_pause is not None
    voter = agenda_phase.current_voter(service.current_state())
    body = {"player_id": voter}
    clock[0] = 102.0
    blocked = client.post("/agenda/abstain", json=body)
    assert blocked.status_code == 422 and "react" in blocked.text
    early = client.post("/reaction-pause/release", json={"actor_id": "p1"})
    assert early.status_code == 422
    clock[0] = 105.0
    ok = client.post("/agenda/abstain", json=body)
    assert ok.status_code == 200, ok.text
    assert service.current_state().reaction_pause is None
