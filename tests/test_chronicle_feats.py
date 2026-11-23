"""Testy nowych osiągnięć kroniki (``core/chronicle_feats.py``) i zapisów ``chronicle_log``."""

from __future__ import annotations

from typing import Any

import pytest

from src.core import chronicle, chronicle_log, step_settle
from src.core.game_state import ActiveCombat, GameState, Phase, PlayerState, SystemState
from src.core.registry import StaticDataRegistry


@pytest.fixture(scope="module")
def registry() -> StaticDataRegistry:
    return StaticDataRegistry()


def _state(n: int = 3) -> GameState:
    factions = (("p1", "sol"), ("p2", "hacan"), ("p3", "xxcha"), ("p4", "jolnar"))[:n]
    players = {
        pid: PlayerState(player_id=pid, color=pid, faction=fac, display_name=pid)
        for pid, fac in factions
    }
    return GameState(players=players, winner_id="p1", round_number=4)


def _combat(
    attacker: str,
    defender: str,
    winner: str | None,
    lost: dict[str, dict[str, int]],
    **extra: Any,
) -> ActiveCombat:
    return ActiveCombat(
        kind="space",
        position="101",
        attacker=attacker,
        defender=defender,
        winner=winner,
        log=[{"losses": lost}],
        **extra,
    )


def _system(space_units: dict[str, dict[str, int]]) -> SystemState:
    return SystemState(position="101", system_id="19", space_units=space_units)


def _keys(state: GameState, registry: StaticDataRegistry) -> dict[str, dict[str, Any]]:
    return {h["key"]: h for h in chronicle.highlights(state, registry)}


# --------------------------------------------------------------------------- zapisy


def test_battle_records_retreats_and_survivors() -> None:
    state = _state()
    state.systems["101"] = _system({"p2": {"cruiser": 1}})
    combat = _combat("p3", "p2", "p2", {"p3": {"fighter": 2}}, retreated={"p3": "102"})
    chronicle.record_battle(state, combat)
    battle = state.chronicle.battles[0]
    assert battle["retreated"] == ["p3"]
    assert battle["survivors"] == 1


def test_record_step_tracks_passes_speaker_cards_explores_mecatol_and_warsuns() -> None:
    before = _state()
    before.phase = Phase.ACTION
    before.players["p1"].private.action_cards = ["sabo1"]
    after = before.clone()
    after.players["p2"].passed = True
    after.players["p1"].private.action_cards = []
    after.decks.action_card_discard.append("sabo1")
    after.players["p1"].controlled_planets.append("mr")
    after.systems["101"] = _system({"p3": {"warsun": 2}})
    chronicle_log.record_step(before, after, "bot:pass")
    chron = after.chronicle
    assert chron.passes == [{"round": 4, "player": "p2"}]
    assert chron.cards_played == {"p1": ["sabo1"]}
    assert chron.mecatol == [{"round": 4, "player": "p1", "gained": True}]
    assert chron.peak_warsuns == {"p3": 2}

    strategy = _state()
    strategy.phase = Phase.STRATEGY
    strategy.speaker_id = "p3"
    chronicle_log.record_step(strategy.clone(), strategy, "strategy:pick:p3:1")
    assert strategy.chronicle.speakers == {"4": "p3"}


def test_settle_step_records_the_chronicle(registry: StaticDataRegistry) -> None:
    """Ta sama ścieżka dla serwera i bota: ``settle_step(before=...)`` dopisuje kronikę."""
    before = _state()
    before.phase = Phase.ACTION
    stepped = before.clone()
    stepped.players["p3"].passed = True
    after = step_settle.settle_step(stepped, registry, 0.0, "turn:pass", before=before)
    assert after.chronicle.passes == [{"round": 4, "player": "p3"}]
    assert stepped.chronicle.passes == []  # wejście nie jest mutowane


def test_godmode_steps_are_not_recorded() -> None:
    before = _state()
    before.phase = Phase.ACTION
    after = before.clone()
    after.players["p2"].passed = True
    chronicle_log.record_step(before, after, "god-mode-patch")
    assert after.chronicle.passes == []


def test_record_fire_ignores_empty_and_self_fire() -> None:
    state = _state()
    chronicle_log.record_fire(state, "p1", "p2", "space_cannon", {"fighter": 2})
    chronicle_log.record_fire(state, "p1", "p2", "space_cannon", {})
    chronicle_log.record_fire(state, None, "p2", "defense", {"infantry": 1})
    assert state.chronicle.fire == [
        {"round": 4, "by": "p1", "victim": "p2", "kind": "space_cannon", "units": 2}
    ]


# --------------------------------------------------------------------------- Treachery


def test_oathbreaker_and_vulture(registry: StaticDataRegistry) -> None:
    state = _state()
    for _ in range(2):
        chronicle.record_deal(state, "p2", "p3")
    chronicle.record_battle(state, _combat("p2", "p3", "p2", {"p3": {"fighter": 1}}))
    chronicle.record_conquest(state, "p3", "p1", "jord")
    chronicle.record_conquest(state, "p2", "p3", "jord")
    feats = _keys(state, registry)
    assert feats["oathbreaker"]["players"] == ["p2", "p3"]
    assert feats["vulture"]["players"] == ["p2"]


def test_kingmaker_by_support_for_the_throne(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p1"].promissory_notes_in_play.append("p3_sftt")
    assert _keys(state, registry)["kingmaker"]["players"] == ["p3", "p1"]


def test_kingmaker_by_attacking_runner_up_in_last_round(registry: StaticDataRegistry) -> None:
    state = _state()
    state.players["p2"].victory_points = 8
    chronicle.record_battle(state, _combat("p3", "p2", "p3", {"p2": {"fighter": 1}}))
    assert _keys(state, registry)["kingmaker"]["players"] == ["p3", "p1"]


def test_saboteur_counts_only_sabotage(registry: StaticDataRegistry) -> None:
    state = _state()
    state.chronicle.cards_played = {"p2": ["sabo1", "sabo2"], "p3": ["sabo3"]}
    feats = _keys(state, registry)
    assert feats["saboteur"]["players"] == ["p2"]
    assert "card_shark" not in feats  # 2 karty < próg 3


# --------------------------------------------------------------------------- Table


def test_table_politics(registry: StaticDataRegistry) -> None:
    state = _state()
    chron = state.chronicle
    chron.speakers = {"1": "p2", "2": "p2", "3": "p2", "4": "p1"}
    for outcome in ("for", "for"):
        chronicle_log.record_agenda(
            state,
            outcome,
            {"p1": {"outcome": "for", "votes": 5}, "p3": {"outcome": "against", "votes": 3}},
        )
    chron.passes = [
        {"round": r, "player": pid} for r in (1, 2, 3) for pid in ("p1", "p2", "p3")
    ]
    chronicle.record_deal(state, "p1", "p2")
    chronicle.record_deal(state, "p1", "p3")
    feats = _keys(state, registry)
    assert feats["voice_of_council"]["players"] == ["p2"]
    assert feats["senate_master"]["players"] == ["p1"]
    assert feats["dissident"]["players"] == ["p3"]
    assert feats["staller"]["players"] == ["p3"]
    assert feats["silk_road"]["players"] == ["p1"]


# --------------------------------------------------------------------------- War


def test_war_feats(registry: StaticDataRegistry) -> None:
    state = _state()
    state.systems["101"] = _system({"p2": {"dreadnought": 1}})
    chronicle.record_battle(
        state, _combat("p3", "p2", "p2", {"p3": {"warsun": 1, "cruiser": 2}})
    )
    for _ in range(3):
        chronicle.record_battle(
            state,
            _combat("p1", "p3", "p1", {"p3": {"fighter": 1}}, retreated={"p3": "102"}),
        )
    chronicle_log.record_fire(state, "p2", "p1", "bombardment", {"infantry": 3})
    feats = _keys(state, registry)
    assert feats["giant_slayer"]["players"] == ["p2"]
    assert feats["last_stand"]["players"] == ["p2"]
    assert feats["punching_bag"]["players"] == ["p3"]
    assert feats["tactical_retreat"]["players"] == ["p3"]
    assert feats["rain_of_fire"]["players"] == ["p2"]
    assert "bombardment" in feats["rain_of_fire"]["detail"]


# --------------------------------------------------------------------------- Empire & Race


def test_empire_feats(registry: StaticDataRegistry) -> None:
    state = _state()
    chron = state.chronicle
    state.objectives.scored["custodians"] = ["p2"]
    chron.mecatol = [
        {"round": 3, "player": "p3", "gained": True},
        {"round": 3, "player": "p3", "gained": False},
    ]
    chron.explorations = {"p1": 4, "p2": 1}
    chron.cards_played = {"p3": ["a", "b", "c"]}
    chron.peak_warsuns = {"p2": 2}
    feats = _keys(state, registry)
    assert feats["first_to_throne"]["players"] == ["p2"]
    assert feats["mecatol_tourist"]["players"] == ["p3"]
    assert feats["void_walker"]["players"] == ["p1"]
    assert feats["card_shark"]["players"] == ["p3"]
    assert feats["sun_forger"]["players"] == ["p2"]


def test_late_bloomer_needs_four_players(registry: StaticDataRegistry) -> None:
    state = _state(4)
    state.chronicle.rounds = [
        {"round": 1, "vp": {"p1": 1, "p2": 0, "p3": 2, "p4": 1}},
        {"round": 2, "vp": {"p1": 3, "p2": 0, "p3": 3, "p4": 2}},
    ]
    for pid, vp in (("p1", 10), ("p2", 8), ("p3", 5), ("p4", 4)):
        state.players[pid].victory_points = vp
    assert _keys(state, registry)["late_bloomer"]["players"] == ["p2"]
    del state.players["p4"]
    assert "late_bloomer" not in _keys(state, registry)
