"""Jawny widok okien czasowych i bramka zamknięcia walki (RULES.md 54.9)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import battle, reaction_cards, timing_view
from src.core.event_store import EventStore
from src.core.game_events import GameEvent, Moment
from src.core.game_state import (
    ActiveCombat,
    CombatStep,
    GameState,
    PendingOffer,
    Phase,
    PlayerState,
)
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _done_combat_state() -> GameState:
    """Zakończona walka kosmiczna w 000: p1 wygrał z p2 (krok DONE, okno „after combat won”)."""
    return GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="000",
        seating_order=["p1", "p2"],
        players={
            "p1": PlayerState(player_id="p1", color="red"),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        active_combat=ActiveCombat(
            kind="space", position="000", attacker="p1", defender="p2",
            step=CombatStep.DONE, winner="p1", outcome="winner",
        ),
    )


def test_labels_read_like_card_windows() -> None:
    assert timing_view.label(GameEvent.AGENDA_REVEALED, Moment.WHEN, {}) == (
        "When an agenda is revealed"
    )
    assert timing_view.label(GameEvent.COMBAT_ROUND, Moment.START, {}) == (
        "At the start of a combat round"
    )
    assert timing_view.label(GameEvent.COMBAT, Moment.START, {"kind": "ground"}) == (
        "At the start of ground combat"
    )
    assert timing_view.label(GameEvent.COMBAT_ROLL, Moment.BEFORE, {"kind": "afb"}) == (
        "Before Anti-Fighter Barrage dice are rolled"
    )


def test_finished_combat_shows_after_won_window() -> None:
    rows = timing_view.describe_open_windows(_done_combat_state())
    won = [r for r in rows if r["event"] == GameEvent.COMBAT_WON.value]
    assert len(won) == 1
    assert won[0]["label"] == "After a space combat is won"
    assert won[0]["subject"] == "p1"
    assert won[0]["position"] == "000"
    assert won[0]["closes"] == "Ends when the battle is closed"


def test_closing_battle_closes_window() -> None:
    closed = battle.close_combat(_done_combat_state())
    assert not any(
        r["event"] == GameEvent.COMBAT_WON.value
        for r in timing_view.describe_open_windows(closed)
    )


def test_close_combat_waits_for_pending_decisions() -> None:
    """Salvage Operations: oferta żyje danymi walki - zamknięcie bitwy nie może jej uśmiercić."""
    state = _done_combat_state()
    state.pending_offers = [
        PendingOffer(
            id="of1", player_id="p1", event=GameEvent.COMBAT_WON.value,
            moment=Moment.AFTER.value, hook_seq=0, label="Salvage Operations: produce 1 ship",
        )
    ]
    with pytest.raises(ValueError, match="decisions"):
        battle.close_combat(state)


def test_hidden_windows_are_not_listed() -> None:
    """Okno zależne od ręki (Acquiescence) nie trafia do jawnego paska (RULES.md 43.4)."""

    def provider(_state: GameState) -> list[reaction_cards.OpenWindow]:
        return [
            reaction_cards.OpenWindow(GameEvent.TRANSACTION, Moment.WHEN, {"player": "p1"}),
            reaction_cards.OpenWindow(
                GameEvent.STRATEGIC_ACTION, Moment.WHEN, {"player": "p1"}, public=False
            ),
        ]

    reaction_cards.open_windows(GameState())  # rejestracje dostawców przed doklejeniem testowego
    reaction_cards._PROVIDERS.append(provider)
    try:
        rows = timing_view.describe_open_windows(GameState())
    finally:
        reaction_cards._PROVIDERS.remove(provider)
    events = [r["event"] for r in rows]
    assert GameEvent.TRANSACTION.value in events
    assert GameEvent.STRATEGIC_ACTION.value not in events


def test_open_now_endpoint(registry: StaticDataRegistry) -> None:
    app = create_app(
        registry=registry, store=EventStore(":memory:"), initial_state=_done_combat_state()
    )
    body = TestClient(app).get("/window/open-now").json()
    labels = [w["label"] for w in body["windows"]]
    assert "After a space combat is won" in labels
