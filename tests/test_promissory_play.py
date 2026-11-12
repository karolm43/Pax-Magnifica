"""Promissory notes: zagrywanie z ręki, strefa gry, zwrot i 5 notek ogólnych (RULES.md 61.2)."""

from __future__ import annotations

import pytest

from src.core import (
    action_cards,
    active_effects,
    economy,
    promissory_notes,
    promissory_play,
    rules_hooks,
    triggers,
)
from src.core.game_events import Duration, GameEvent, Moment
from src.core.game_state import GameState, Phase, PlayerState, SystemState, TacticalStep
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state() -> GameState:
    """p1 = red (Sol, aktywny), p2 = blue (Arborec); p2 trzyma notki p1."""
    state = GameState(
        phase=Phase.ACTION,
        active_player_id="p1",
        players={
            "p1": PlayerState(player_id="p1", color="red", faction="sol", commodity_value=4),
            "p2": PlayerState(player_id="p2", color="blue", faction="arborec", commodity_value=3),
        },
        systems={
            "101": SystemState(position="101", system_id="19"),
            "102": SystemState(position="102", system_id="20"),
        },
    )
    state.players["p1"].private.promissory_notes = ["blue_cf"]
    state.players["p2"].private.promissory_notes = ["red_cf", "red_ta", "blue_cf"]
    return state


def _activate(state: GameState, position: str) -> None:
    state.active_system = position
    state.tactical_step = TacticalStep.MOVEMENT
    state.tactical_moved = False


def _rows(state: GameState, registry: StaticDataRegistry, pid: str) -> dict[str, dict]:  # type: ignore[type-arg]
    return {r["note_id"]: r for r in promissory_play.playability(state, registry, pid)}


def test_wlasciciel_z_koloru_i_frakcji(registry: StaticDataRegistry) -> None:
    state = _state()
    assert promissory_play.resolve(state, registry, "red_cf") == ("<color>_cf", "p1")
    assert promissory_play.resolve(state, registry, "blue_ta") == ("<color>_ta", "p2")
    sol_note = registry.factions["sol"].promissory_notes[0]
    assert promissory_play.resolve(state, registry, sol_note) == (sol_note, "p1")
    name, text = promissory_play.note_text(state, registry, "red_cf")
    assert name == "Ceasefire" and "red player" in text and "<color>" not in text


def test_nie_mozna_zagrac_wlasnej_notki(registry: StaticDataRegistry) -> None:
    state = _state()
    rows = _rows(state, registry, "p2")
    assert rows["blue_cf"]["playable"] is False
    assert "own promissory note" in (rows["blue_cf"]["reason"] or "")
    with pytest.raises(ValueError, match="own promissory note"):
        promissory_play.play(state, registry, "p2", "blue_cf")


# ----------------------------------------------------------------------------------- Ceasefire


def test_ceasefire_bez_wlasnych_jednostek_niezagrywalny(registry: StaticDataRegistry) -> None:
    state = _state()
    _activate(state, "101")
    rows = _rows(state, registry, "p2")
    assert rows["red_cf"]["playable"] is False
    assert "does not contain any of your units" in (rows["red_cf"]["reason"] or "")


def test_ceasefire_blokuje_ruch_i_wraca(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["101"].space_units["p2"] = {"carrier": 1}
    _activate(state, "101")
    assert _rows(state, registry, "p2")["red_cf"]["playable"] is True
    new_state, implemented = promissory_play.play(state, registry, "p2", "red_cf")
    assert implemented is True
    assert promissory_play.ceasefire_blocks(new_state, "p1")
    assert "red_cf" in new_state.players["p1"].private.promissory_notes
    assert "red_cf" not in new_state.players["p2"].private.promissory_notes
    # Efekt trwa tylko do końca akcji taktycznej.
    active_effects.expire(new_state, Duration.TACTICAL_ACTION)
    assert not promissory_play.ceasefire_blocks(new_state, "p1")


def test_ceasefire_poza_oknem(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["101"].space_units["p2"] = {"carrier": 1}
    assert _rows(state, registry, "p2")["red_cf"]["playable"] is False


# ------------------------------------------------------------------------- Trade Agreement


def test_trade_agreement_po_uzupelnieniu(registry: StaticDataRegistry) -> None:
    state = _state()
    assert _rows(state, registry, "p2")["red_ta"]["playable"] is False
    economy.replenish_commodities(state, "p1")
    assert state.players["p1"].commodities == 4
    assert _rows(state, registry, "p2")["red_ta"]["playable"] is True
    new_state, _ = promissory_play.play(state, registry, "p2", "red_ta")
    assert new_state.players["p1"].commodities == 0
    assert new_state.players["p2"].trade_goods == 4  # commodities od innego gracza = TG
    assert "red_ta" in new_state.players["p1"].private.promissory_notes


# ------------------------------------------------------------------ Support for the Throne


def test_support_for_the_throne_vp_i_zwrot(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].private.promissory_notes.append("red_sftt")
    promissory_notes.transfer(state, "p1", "p2", "red_sftt")
    p2 = state.players["p2"]
    assert "red_sftt" in p2.promissory_notes_in_play and p2.victory_points == 1
    assert "red_sftt" not in p2.private.promissory_notes
    # Aktywacja systemu BEZ jednostek właściciela nic nie zmienia.
    ctx = {"player": "p2", "position": "102"}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2", ctx=ctx)
    assert p2.victory_points == 1
    state.systems["101"].space_units["p1"] = {"cruiser": 1}
    ctx = {"player": "p2", "position": "101"}
    triggers.fire(state, GameEvent.SYSTEM_ACTIVATED, Moment.AFTER, subject="p2", ctx=ctx)
    assert state.players["p2"].victory_points == 0
    assert "red_sftt" in state.players["p1"].private.promissory_notes
    assert "red_sftt" not in state.players["p2"].promissory_notes_in_play


def test_wlasna_sftt_wraca_do_reki_bez_vp(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].private.promissory_notes.append("red_sftt")
    promissory_notes.transfer(state, "p2", "p1", "red_sftt")
    assert state.players["p1"].victory_points == 0
    assert "red_sftt" in state.players["p1"].private.promissory_notes


# -------------------------------------------------------------------------------- Alliance


def test_alliance_daje_commandera_wlasciciela(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].private.promissory_notes.append("red_an")
    source = rules_hooks.HookSource(rules_hooks.SOURCE_LEADER, "solcommander")
    promissory_notes.transfer(state, "p1", "p2", "red_an")
    assert "red_an" in state.players["p2"].promissory_notes_in_play
    assert source not in rules_hooks.owned_sources(state, "p2")  # commander zablokowany
    state.players["p1"].leader_states = {"solcommander": "unlocked"}
    assert source in rules_hooks.owned_sources(state, "p2")


# ------------------------------------------------------------------------ Political Secret


def test_political_secret_blokuje_karty_akcji_i_zdolnosci(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].private.action_cards = ["sabotage"]
    active_effects.add_effect(
        state, promissory_play.POLITICAL_SECRET_EFFECT, Duration.AGENDA, owner="p1"
    )
    rows = action_cards.playability(state, registry, "p1")
    assert all("Political Secret" in (r["reason"] or "") for r in rows)
    with pytest.raises(ValueError, match="Political Secret"):
        action_cards.play_action_card(state, registry, "p1", "sabotage")
    from src.core import faction_components

    reason = faction_components.block_reason(state, registry, "p1", "ability", "orbital_drop")
    assert reason is not None and "Political Secret" in reason
    active_effects.expire(state, Duration.AGENDA)
    assert not promissory_play.silenced(state, "p1")
