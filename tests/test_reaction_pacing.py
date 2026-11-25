"""Reaction-window pacing: component/agent muting, per-combat pass, AFK decay, quick jitter."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core import (
    card_hold,
    faction_components,
    reaction_pause,
    reaction_prefs,
    reaction_window,
    visibility,
)
from src.core.event_store import EventStore
from src.core.game_state import ActiveCombat, GameState
from src.core.registry import StaticDataRegistry
from tests.test_card_hold import NOW, _industrial, _own, _play, _state
from tests.test_reactions_agenda import DIRECTIVE, LAW, _revealed

AGENT = faction_components.effect_key(faction_components.LEADER, "naaluagent")


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _combat(state: GameState, position: str = "27") -> None:
    state.active_combat = ActiveCombat(
        kind="space", position=position, attacker="p1", defender="p2"
    )


def _agenda(registry: StaticDataRegistry, p3_hand: list[str]) -> GameState:
    return _revealed(registry, [LAW, DIRECTIVE], {"p1": ["lead_rider"], "p3": p3_hand})


def _fake_agent(monkeypatch: pytest.MonkeyPatch, owner: str) -> None:
    """``owner`` has a faction agent with a usable (non-standing) window."""

    def available(state: GameState, registry: Any, ids: list[str]) -> list[dict[str, Any]]:
        if owner not in ids:
            return []
        return [{
            "player_id": owner, "kind": faction_components.LEADER, "component_id": "naaluagent",
            "name": "Agent", "text": "", "standing": False,
        }]

    monkeypatch.setattr(faction_components, "available_now", available)


# --- component / agent muting ------------------------------------------------------------------


def test_component_counts_as_reaction_until_muted(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_agent(monkeypatch, "p2")
    state = _state([], [])
    assert reaction_window.has_playable_reaction(state, registry, "p2")
    muted = reaction_prefs.update(state, "p2", mute_components={AGENT: "always"})
    assert not reaction_window.has_playable_reaction(muted, registry, "p2")
    assert "p2" in reaction_window.auto_passers(muted, registry, ["p2"])
    # the (public) eligible list stays complete - the mute is private
    assert reaction_window.window_component_users(muted, registry, ["p2"]) == ["p2"]


def test_component_mute_expires_by_scope(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_agent(monkeypatch, "p2")
    state = reaction_prefs.update(_state([], []), "p2", mute_components={AGENT: "round"})
    assert reaction_prefs.is_component_muted(state, "p2", AGENT)
    state.round_number += 1
    assert not reaction_prefs.is_component_muted(state, "p2", AGENT)
    assert reaction_window.has_playable_reaction(state, registry, "p2")
    reaction_prefs.prune(state)
    assert state.players["p2"].private.reaction_prefs.muted_components == {}


def test_component_mute_for_combat_ends_with_combat(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_agent(monkeypatch, "p2")
    state = _state([], [])
    _combat(state)
    state = reaction_prefs.update(state, "p2", mute_components={AGENT: "combat"})
    assert not reaction_window.has_playable_reaction(state, registry, "p2")
    state.active_combat = None
    assert reaction_window.has_playable_reaction(state, registry, "p2")


def test_component_unmute_and_bad_scope() -> None:
    state = reaction_prefs.update(_state([], []), "p2", mute_components={AGENT: "turn"})
    state = reaction_prefs.update(state, "p2", mute_components={AGENT: None})
    assert state.players["p2"].private.reaction_prefs.muted_components == {}
    with pytest.raises(ValueError):
        reaction_prefs.update(state, "p2", mute_components={AGENT: "agenda"})


def test_component_mutes_are_private() -> None:
    state = reaction_prefs.update(_state([], []), "p2", mute_components={AGENT: "always"})
    seen = visibility.project_for_viewer(state, "p1")
    assert seen.players["p2"].private.reaction_prefs.muted_components == {}
    own = visibility.project_for_viewer(state, "p2")
    assert AGENT in own.players["p2"].private.reaction_prefs.muted_components


def test_component_mute_does_not_change_public_eligible(
    registry: StaticDataRegistry, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_agent(monkeypatch, "p2")
    state = _agenda(registry, [])
    plain = reaction_pause.eligible_players(state, registry, _key_window(state))
    muted = reaction_prefs.update(state, "p2", mute_components={AGENT: "always"})
    assert reaction_pause.eligible_players(muted, registry, _key_window(muted)) == plain
    assert "p2" in plain


def _key_window(state: GameState) -> Any:
    return reaction_pause._key_windows(state)[0]


# --- pass for this combat ----------------------------------------------------------------------


def test_combat_pass_applies_only_to_that_combat() -> None:
    state = _state([], [])
    _combat(state, "27")
    state = reaction_prefs.update(state, "p2", declare={"combat": "combat"})
    assert reaction_prefs.declares_pass(state, "p2", "combat")
    _combat(state, "28")  # a different combat gets a different stamp
    assert not reaction_prefs.declares_pass(state, "p2", "combat")
    reaction_prefs.prune(state)
    assert state.players["p2"].private.reaction_prefs.passes == {}


def test_combat_pass_for_all_categories_ends_with_combat() -> None:
    state = _state([], [])
    _combat(state)
    state = reaction_prefs.update(state, "p2", declare={"all": "combat"})
    assert reaction_prefs.declares_pass(state, "p2", "sabotage")
    state.active_combat = None
    assert not reaction_prefs.declares_pass(state, "p2", "combat")


def test_combat_pass_without_combat_is_dead() -> None:
    state = reaction_prefs.update(_state([], []), "p2", declare={"combat": "combat"})
    assert not reaction_prefs.declares_pass(state, "p2", "combat")


# --- AFK decay ---------------------------------------------------------------------------------


def _open(registry: StaticDataRegistry) -> GameState:
    state = _agenda(registry, ["imp_rider"])
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    return state


def _expire(state: GameState) -> GameState:
    assert state.reaction_pause is not None
    return reaction_pause.release(state, state.reaction_pause.opened_at + 999)


def _strikes(state: GameState, pid: str) -> int:
    return state.players[pid].private.reaction_prefs.afk_strikes


def test_timeout_without_reaction_is_a_strike(registry: StaticDataRegistry) -> None:
    state = _expire(_open(registry))
    assert _strikes(state, "p1") == 1 and _strikes(state, "p3") == 1
    assert _strikes(state, "p2") == 0  # was never asked


def test_pass_and_more_time_are_not_afk(registry: StaticDataRegistry) -> None:
    state = _open(registry)
    state = reaction_pause.pass_pause(state, "p1")
    state = reaction_pause.ask_for_time(state, "p3")
    state = _expire(state)
    assert _strikes(state, "p1") == 0 and _strikes(state, "p3") == 0


def test_engine_auto_pass_is_not_afk(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, ["salvage"])  # p3 has no matching card -> engine passes for them
    reaction_pause.sync(state, registry, now=100.0)
    state = _expire(state)
    assert _strikes(state, "p3") == 0 and _strikes(state, "p1") == 1


def test_activity_in_window_without_pass_is_not_afk(registry: StaticDataRegistry) -> None:
    state = _open(registry)
    assert reaction_prefs.mark_active(state, "p1")  # e.g. played a card, never clicked Pass
    state = _expire(state)
    assert _strikes(state, "p1") == 0 and _strikes(state, "p3") == 1


def test_engine_passes_for_afk_player(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, ["imp_rider"])
    state.players["p3"].private.reaction_prefs.afk_strikes = reaction_prefs.AFK_STRIKES
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    assert "p3" in state.reaction_pause.passed  # despite holding a rider
    assert "p1" not in state.reaction_pause.passed


def test_below_threshold_player_is_still_asked(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, ["imp_rider"])
    state.players["p3"].private.reaction_prefs.afk_strikes = reaction_prefs.AFK_STRIKES - 1
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None and "p3" not in state.reaction_pause.passed


def test_any_action_brings_afk_player_back(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, ["imp_rider"])
    state.players["p3"].private.reaction_prefs.afk_strikes = reaction_prefs.AFK_STRIKES
    assert reaction_prefs.is_afk(state, "p3")
    assert reaction_prefs.mark_active(state, "p3")
    assert not reaction_prefs.is_afk(state, "p3")
    assert not reaction_prefs.mark_active(state, "p3")  # idempotent: nothing to store
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None and "p3" not in state.reaction_pause.passed


def test_repeated_timeouts_reach_afk(registry: StaticDataRegistry) -> None:
    state = _expire(_open(registry))
    reaction_prefs.window_opened(state, ["p3"])
    state.players["p3"].private.reaction_prefs.afk_strikes += 1
    assert reaction_prefs.is_afk(state, "p3")


def test_sabotage_window_timeout_counts(registry: StaticDataRegistry) -> None:
    card, planets = _industrial(registry)
    state = _state([card], ["sabo1"])
    _own(state, planets)
    state = _play(state, registry, card)
    assert state.held_play is not None
    done = card_hold.release(state, registry, "p1", now=NOW + 999)
    assert _strikes(done, "p2") == 1


def test_afk_state_is_private() -> None:
    state = _state([], [])
    state.players["p2"].private.reaction_prefs.afk_strikes = 5
    seen = visibility.project_for_viewer(state, "p1")
    assert _strikes(seen, "p2") == 0


def test_api_any_post_resets_afk() -> None:
    state = _state([], [])
    state.players["p2"].private.reaction_prefs.afk_strikes = reaction_prefs.AFK_STRIKES
    app = create_app(store=EventStore(), initial_state=state, now=lambda: NOW)
    client = TestClient(app)
    client.post("/turn/end", json={"player_id": "p2"}, headers={"X-Actor-Id": "p2"})
    assert _strikes(app.state.service.current_state(), "p2") == 0


# --- quick windows + jitter --------------------------------------------------------------------


def test_quick_without_jitter_closes_immediately(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, [])
    state.quick_reaction_windows = True
    state.players["p1"].private.auto_pass_reactions = True
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is None


def test_quick_with_jitter_shortens_instead_of_closing(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, [])
    state.quick_reaction_windows = True
    state.reaction_jitter_seconds = 2.0
    state.players["p1"].private.auto_pass_reactions = True
    reaction_pause.sync(state, registry, now=100.0)
    pause = state.reaction_pause
    assert pause is not None and reaction_window.all_passed(pause)
    assert 1.0 <= pause.seconds <= 2.0
    assert pause.seconds == reaction_window.quick_delay(state, pause.key)  # deterministic
    assert reaction_pause.expired(pause, 100.0 + 2.0)


def test_jitter_ignored_without_quick(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, [])
    state.reaction_jitter_seconds = 2.0
    state.players["p1"].private.auto_pass_reactions = True
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    assert state.reaction_pause.seconds == reaction_window.window_seconds(state)


def test_jitter_range_is_validated() -> None:
    state = _state([], [])
    assert reaction_window.configure_jitter(state, 1.5).reaction_jitter_seconds == 1.5
    for bad in (-0.1, 2.5):
        with pytest.raises(ValueError):
            reaction_window.configure_jitter(state, bad)


def test_last_manual_pass_with_jitter_keeps_window(registry: StaticDataRegistry) -> None:
    state = _agenda(registry, [])
    state.quick_reaction_windows = True
    state.reaction_jitter_seconds = 1.0
    reaction_pause.sync(state, registry, now=100.0)
    assert state.reaction_pause is not None
    state = reaction_pause.pass_pause(state, "p1")
    assert state.reaction_pause is not None and state.reaction_pause.seconds <= 1.0
