"""Testy infrastruktury kart reakcji (okna otwarte teraz + zagranie z ręki) - RULES.md 53.5."""

from __future__ import annotations

from typing import Any

import pytest

from src.core import action_cards, reaction_cards, rules_hooks, triggers
from src.core.game_events import GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, SystemState, TacticalStep
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(hand: list[str], *, step: TacticalStep | None = TacticalStep.MOVEMENT) -> GameState:
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        active_system="101" if step is not None else None,
        tactical_step=step,
        players={
            "p1": PlayerState(player_id="p1", color="red"),
            "p2": PlayerState(player_id="p2", color="blue"),
        },
        systems={"101": SystemState(position="101", system_id="18")},
    )
    state.players["p2"].private.action_cards = list(hand)
    state.players["p1"].private.action_cards = list(hand)
    return state


def _playable(
    state: GameState, registry: StaticDataRegistry, player: str, card: str
) -> dict[str, Any]:
    rows = action_cards.playability(state, registry, player)
    return next(row for row in rows if row["card_id"] == card)


def test_okno_po_aktywacji_otwarte_tylko_przed_ruchem(registry: StaticDataRegistry) -> None:
    state = _state(["fs1"])
    windows = reaction_cards.open_windows(state)
    assert any(w.event is GameEvent.SYSTEM_ACTIVATED and w.moment is Moment.AFTER for w in windows)
    state.tactical_moved = True
    # po pierwszym ruchu zamyka się okno „po aktywacji”, otwiera „po ruchu” (Rescue)
    windows = reaction_cards.open_windows(state)
    assert not any(w.event is GameEvent.SYSTEM_ACTIVATED for w in windows)
    idle = reaction_cards.open_windows(_state(["fs1"], step=None))
    assert not any(w.event is GameEvent.SYSTEM_ACTIVATED for w in idle)


def test_flank_speed_zagrywalny_tylko_przez_aktywujacego(registry: StaticDataRegistry) -> None:
    state = _state(["fs1"])
    assert _playable(state, registry, "p1", "fs1")["playable"]
    other = _playable(state, registry, "p2", "fs1")  # „After YOU activate” - p2 nie aktywował
    assert not other["playable"]
    assert "no open window" in str(other["reason"]).lower()
    state.tactical_moved = True
    assert not _playable(state, registry, "p1", "fs1")["playable"]


def test_flank_speed_dodaje_ruch_i_wygasa_z_akcja(registry: StaticDataRegistry) -> None:
    state = _state(["fs1"])
    new, implemented = action_cards.play_action_card(state, registry, "p1", "fs1")
    assert implemented
    assert new.players["p1"].private.action_cards == []
    assert new.decks.action_card_discard == ["fs1"]
    assert not new.players["p1"].took_action_this_turn  # reakcja nie jest akcją tury
    assert rules_hooks.modify(rules_hooks.POINT_MOVEMENT_MOVE_VALUE, new, "p1", 2) == 3
    assert rules_hooks.modify(rules_hooks.POINT_MOVEMENT_MOVE_VALUE, new, "p2", 2) == 2
    triggers.fire(new, GameEvent.TACTICAL_ACTION, Moment.END, subject="p1")
    assert rules_hooks.modify(rules_hooks.POINT_MOVEMENT_MOVE_VALUE, new, "p1", 2) == 2


def test_zagranie_poza_oknem_to_blad_bez_zmian(registry: StaticDataRegistry) -> None:
    state = _state(["fs1"], step=None)
    with pytest.raises(ValueError, match="no open window"):
        action_cards.play_action_card(state, registry, "p1", "fs1")
    assert state.players["p1"].private.action_cards == ["fs1"]
